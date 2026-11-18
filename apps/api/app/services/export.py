"""Export service: turn an approved document into a deliverable file.

Only approved data leaves the platform: a document must carry
``status=approved`` before an export row is even minted, and only fields a
human endorsed (accepted or corrected) make it into the payload — pending
and rejected fields are held back by design, because export is the moment
the data stops being "our working copy" and becomes the customer's record.

Writing the file reuses the same two-step upload contract the client used
for the original PDF: the service mints a signed upload URL from the
storage provider and performs the PUT itself (``httpx`` is already a
dependency via storage3). The API server therefore never needs a fifth
"server-side write" storage method, and exports follow the identical path,
permissions, and audit surface as every other byte written to the bucket.
"""

import csv
import datetime
import io
import json
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Document, Export, ExtractedField, ExtractedTable, User
from app.domain.enums import DocumentStatus, ExportFormat, ExportStatus, FieldReviewStatus
from app.errors import NotFoundException, ValidationException
from app.services.audit import write_audit_log
from app.storage.base import StorageProvider

logger = structlog.get_logger(__name__)

# The field statuses that may leave the platform: accepted (human endorsed
# the machine value) or corrected (human replaced it). Rejected and pending
# fields are working state, not deliverable state.
EXPORTABLE_FIELD_STATUSES: tuple[FieldReviewStatus, ...] = (
    FieldReviewStatus.ACCEPTED,
    FieldReviewStatus.CORRECTED,
)


def _exportable_value(field: ExtractedField) -> str:
    """Render one field's value for the flat CSV ``value`` column.

    CSV has one value column, so the typed columns collapse in documented
    order: text first, then the number, then the date; a field whose value
    lives in ``value_json`` renders as its JSON encoding. A rejected field
    never reaches this function.
    """
    if field.value_text is not None:
        return field.value_text
    if field.value_number is not None:
        return str(field.value_number)
    if field.value_date is not None:
        return field.value_date.isoformat()
    if field.value_json is not None:
        return json.dumps(field.value_json)
    return ""


def _field_record(field: ExtractedField) -> dict[str, Any]:
    """Project one field row into the JSON export's field record."""
    return {
        "field_key": field.field_key,
        "field_label": field.field_label,
        "value_text": field.value_text,
        "value_number": float(field.value_number) if field.value_number is not None else None,
        "value_date": field.value_date.isoformat() if field.value_date is not None else None,
        "value_json": field.value_json,
        "confidence": float(field.confidence),
        "source": field.source,
        "page_number": field.page_number,
        "evidence_span": field.evidence_span,
        "review_status": field.review_status.value,
        "original_value_text": field.original_value_text,
        "is_required": field.is_required,
    }


def _build_json_payload(
    document: Document, fields: list[ExtractedField], tables: list[ExtractedTable]
) -> dict[str, Any]:
    """Build the JSON export structure with provenance metadata.

    ``extraction_mode`` travels with the export because a JSON file opened
    six months later must be interpretable: mock-mode output is demo data,
    vision-mode output is production data, and misreading one for the
    other changes downstream decisions about trusting the numbers.
    """
    settings = get_settings()
    return {
        "document_id": str(document.id),
        "file_name": document.file_name,
        "extraction_mode": settings.EXTRACTION_MODE,
        "exported_at": datetime.datetime.now(tz=datetime.UTC).isoformat(),
        "fields": [_field_record(f) for f in fields],
        "tables": [
            {
                "table_index": t.table_index,
                "title": t.title,
                "page_number": t.page_number,
                "headers": t.headers_json,
                "rows": t.rows_json,
                "confidence": float(t.confidence),
                "source": t.source,
                "review_status": t.review_status.value,
            }
            for t in tables
        ],
        "metadata": {
            "organization_id": str(document.organization_id),
            "extraction_mode": settings.EXTRACTION_MODE,
            "pipeline_version": settings.PIPELINE_VERSION,
            "schema_version": settings.SCHEMA_VERSION,
            "row_count": len(fields),
        },
    }


def _build_csv_payload(fields: list[ExtractedField]) -> str:
    """Build the CSV export: one header row plus one row per field.

    The four columns are the minimum a spreadsheet consumer needs to use
    the export: what the field is, what it says, how confident the machine
    was, and what the human decided about it.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["field_key", "value", "confidence", "review_status"])
    for field in fields:
        writer.writerow(
            [
                field.field_key,
                _exportable_value(field),
                str(field.confidence),
                field.review_status.value,
            ]
        )
    return buffer.getvalue()


def _upload_export_bytes(
    storage: StorageProvider, storage_path: str, data: bytes, content_type: str
) -> None:
    """Write export bytes to the bucket through the signed-URL contract.

    Reusing the client upload path (mint URL, then PUT the bytes) keeps the
    storage interface at its four documented operations: no server-side
    write method exists, and adding one would mean changing every provider.
    """
    signed = storage.create_upload_url(storage_path, content_type)
    headers = dict(signed.headers)
    response = httpx.request(signed.method, signed.url, content=data, headers=headers, timeout=30.0)
    response.raise_for_status()


def generate_export(
    db: Session,
    user: User,
    document_id: str,
    format: ExportFormat,
    storage: StorageProvider,
) -> Export:
    """Generate one export for an approved document and store it.

    The Export row is created PENDING before any work, so even a failure
    leaves an accountable record (status=FAILED, error_message) rather than
    an export that silently never existed. On success the row carries the
    storage path, row count, completion time, and the retention expiry the
    future sweeper will enforce.

    Args:
        db: The request-scoped session (caller owns commit/rollback).
        user: The user requesting the export.
        document_id: The document to export.
        format: ``json`` or ``csv``.
        storage: The storage provider (writes via signed upload URL).

    Returns:
        The completed Export row.

    Raises:
        NotFoundException: Document absent or outside the caller's org.
        ValidationException: Document is not approved.
    """
    document = db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == user.organization_id,
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundException(details={"document_id": str(document_id)})
    if document.status != DocumentStatus.APPROVED:
        raise ValidationException(details={"reason": "document_not_approved"})

    settings = get_settings()
    export = Export(
        organization_id=user.organization_id,
        document_id=document.id,
        requested_by=user.id,
        format=format,
        status=ExportStatus.PENDING,
    )
    db.add(export)
    db.flush()

    try:
        fields = list(
            db.execute(
                select(ExtractedField)
                .where(
                    ExtractedField.document_id == document.id,
                    ExtractedField.review_status.in_(EXPORTABLE_FIELD_STATUSES),
                )
                .order_by(ExtractedField.field_key)
            ).scalars()
        )
        tables = list(
            db.execute(
                select(ExtractedTable)
                .where(ExtractedTable.document_id == document.id)
                .order_by(ExtractedTable.table_index)
            ).scalars()
        )

        if format == ExportFormat.JSON:
            payload = _build_json_payload(document, fields, tables)
            data = json.dumps(payload, indent=2).encode("utf-8")
            storage_path = f"{document.organization_id}/exports/{export.id}.json"
            content_type = "application/json"
        else:
            data = _build_csv_payload(fields).encode("utf-8")
            storage_path = f"{document.organization_id}/exports/{export.id}.csv"
            content_type = "text/csv"

        _upload_export_bytes(storage, storage_path, data, content_type)

        export.status = ExportStatus.COMPLETED
        export.storage_path = storage_path
        export.row_count = len(fields)
        export.completed_at = datetime.datetime.now(tz=datetime.UTC)
        export.expires_at = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(
            days=settings.RETENTION_DAYS
        )
        db.flush()

        write_audit_log(
            db,
            user,
            action="document.exported",
            entity_type="export",
            entity_id=str(export.id),
            metadata={
                "document_id": str(document.id),
                "format": format.value,
                "row_count": len(fields),
                "storage_path": storage_path,
            },
        )
    except Exception as exc:
        export.status = ExportStatus.FAILED
        export.error_message = str(exc)
        db.flush()
        write_audit_log(
            db,
            user,
            action="export.failed",
            entity_type="export",
            entity_id=str(export.id),
            metadata={
                "document_id": str(document.id),
                "format": format.value,
                "error": str(exc),
            },
        )
        raise

    logger.info(
        "export_completed",
        export_id=str(export.id),
        document_id=str(document.id),
        format=format.value,
        row_count=len(fields),
    )
    return export


def list_document_exports(db: Session, user: User, document_id: str) -> list[Export]:
    """Return a document's exports, newest first.

    Args:
        db: The request-scoped session.
        user: The authenticated reader.
        document_id: Path parameter document id.

    Returns:
        The exports for the document ordered by created_at descending, so
        the most recent export a client re-downloads is first in the list.

    Raises:
        NotFoundException: Document absent or outside the caller's org.
    """
    document = db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == user.organization_id,
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundException(details={"document_id": str(document_id)})

    return list(
        db.execute(
            select(Export)
            .where(Export.document_id == document.id)
            .order_by(Export.created_at.desc())
        ).scalars()
    )

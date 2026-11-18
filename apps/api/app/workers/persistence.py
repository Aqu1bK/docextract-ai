"""Result persistence: turn an ExtractionResult into database rows.

The worker's write step. A result's in-memory shape (``ExtractedField``
with a union ``value``) is mapped onto the Phase 3 typed columns:
``value_text``/``value_number``/``value_json`` — the schema's answer to
"one value, many possible types" without a per-type table. Deletion
first makes the step idempotent: a retried job that already wrote a
partial result set never leaves stale rows behind, because retries and
fresh runs take exactly the same path — delete, then write what is true
now.
"""

import decimal
from typing import Any

import structlog
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Document, ExtractedField, ExtractedTable, ExtractionJob
from app.domain.enums import FieldReviewStatus
from app.schemas.extraction import ExtractionResult

logger = structlog.get_logger(__name__)


def _column_value(value: str | float | dict[str, Any] | None) -> dict[str, Any]:
    """Map one wire ``value`` union onto the typed value columns.

    The mapping follows the value's runtime type: numbers land in
    ``value_number`` (Quantized for Numeric), dicts land in
    ``value_json``, everything else (strings, dates as strings) lands in
    ``value_text``. A None value stays all-None: a field with no value
    is a field a reviewer must fill, not a zero.
    """
    if isinstance(value, bool):
        # bool is an int subclass; treating True as 1 in value_number
        # would corrupt the meaning. Strings keep booleans honest.
        return {"value_text": str(value)}
    if isinstance(value, (int, float)):
        return {"value_number": decimal.Decimal(str(value))}
    if isinstance(value, dict):
        return {"value_json": value}
    if value is None:
        return {}
    return {"value_text": value}


def persist_extraction_results(
    session: Session,
    job: ExtractionJob,
    document: Document,
    result: ExtractionResult,
    settings: Settings,
) -> None:
    """Replace the document's extracted rows with this result's rows.

    Deletion runs inside the same transaction as the inserts, so a
    crash between them rolls both back: a partial result is never
    visible. The delete-then-insert pair is what makes retries safe
    without a separate cleanup job.

    Args:
        session: The worker's session (caller owns commit).
        job: The job whose result is being persisted (fields carry job_id).
        document: The document the fields belong to.
        result: The provider's result for this run.
        settings: Application settings (signature parity with the
            processing step; threshold routing happens there).
    """
    session.execute(delete(ExtractedField).where(ExtractedField.job_id == job.id))
    session.execute(delete(ExtractedTable).where(ExtractedTable.job_id == job.id))

    for field in result.fields:
        session.add(
            ExtractedField(
                organization_id=job.organization_id,
                document_id=job.document_id,
                job_id=job.id,
                field_key=field.key,
                field_label=field.label,
                confidence=decimal.Decimal(str(field.confidence)),
                source=field.source,
                page_number=field.page_number,
                evidence_span=field.evidence_span,
                review_status=FieldReviewStatus.PENDING,
                is_required=False,
                **_column_value(field.value),
            )
        )

    for index, table in enumerate(result.tables):
        session.add(
            ExtractedTable(
                organization_id=job.organization_id,
                document_id=job.document_id,
                job_id=job.id,
                table_index=index,
                headers_json=list(table.headers),
                rows_json=[list(row) for row in table.rows],
                confidence=decimal.Decimal(str(table.confidence)),
                source=table.source,
                page_number=table.page_number,
                review_status=FieldReviewStatus.PENDING,
            )
        )
    session.flush()

    logger.info(
        "extraction_results_persisted",
        job_id=str(job.id),
        document_id=str(document.id),
        field_count=len(result.fields),
        table_count=len(result.tables),
    )

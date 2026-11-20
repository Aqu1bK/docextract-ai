# docextract-ai/apps/api/app/api/v1/endpoints/export.py

"""Export endpoints: getting approved data out, on demand.

Requesting an export is a reviewer action (ADMIN/REVIEWER) because it is
the act that publishes the document's data; listing past exports is
broader (any role) because the list contains only metadata, not data.
The POST commits before responding: the Export row, the stored object,
and the audit row become durable together or not at all.

Phase 9C adds the download: ``GET /documents/{id}/exports/{id}/download``
streams the stored export file through the API (bytes via the storage
provider's ``download_file``, which is the documented contract at this
product's ≤10 MB scale) with the response headers a browser needs to
save the file rather than render it.
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.db.models import Document, Export, User
from app.db.session import get_db
from app.domain.enums import RoleName
from app.errors import NotFoundException
from app.schemas.export import CreateExportRequest, ExportOut
from app.services.export import generate_export, list_document_exports
from app.storage.base import StorageProvider
from app.storage.factory import get_storage

router = APIRouter()

# Media types for the two export formats, by file extension.
EXPORT_MEDIA_TYPES: dict[str, str] = {"json": "application/json", "csv": "text/csv"}


@router.post(
    "/documents/{document_id}/export",
    response_model=ExportOut,
    status_code=status.HTTP_201_CREATED,
)
def create_export(
    document_id: str,
    req: CreateExportRequest,
    user: User = Depends(require_roles([RoleName.ADMIN, RoleName.REVIEWER])),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    storage: StorageProvider = Depends(get_storage),  # noqa: B008
) -> ExportOut:
    """Generate and store one export (JSON or CSV) for an approved document.

    The export flows through the real service path: only accepted or
    corrected fields enter the payload, the file lands in object storage
    under the organization's export namespace, and the audit row records
    the format and row count.
    """
    export = generate_export(db, user, document_id, req.format, storage)
    db.commit()
    return ExportOut.model_validate(export)


@router.get("/documents/{document_id}/exports", response_model=list[ExportOut])
def get_document_exports(
    document_id: str,
    user: User = Depends(  # noqa: B008
        require_roles(  # noqa: B008
            [RoleName.ADMIN, RoleName.REVIEWER, RoleName.UPLOADER, RoleName.VIEWER]
        )
    ),
    db: Session = Depends(get_db),  # noqa: B008
) -> list[ExportOut]:
    """List a document's past exports, newest first.

    Metadata only: statuses, row counts, retention expiries. The export
    bytes themselves are downloaded from storage paths the rows name.
    """
    return [
        ExportOut.model_validate(export) for export in list_document_exports(db, user, document_id)
    ]


@router.get("/documents/{document_id}/exports/{export_id}/download")
def download_export(
    document_id: str,
    export_id: str,
    user: User = Depends(  # noqa: B008
        require_roles(  # noqa: B008
            [RoleName.ADMIN, RoleName.REVIEWER, RoleName.UPLOADER, RoleName.VIEWER]
        )
    ),
    db: Session = Depends(get_db),  # noqa: B008
    storage: StorageProvider = Depends(get_storage),  # noqa: B008
) -> Response:
    """Stream one stored export file back as a download response.

    The export must belong to the caller's document and organization
    (both conditions on the lookup, so a foreign export is a 404), and
    only COMPLETED exports have bytes to download — PENDING exports have
    none yet and FAILED exports never will. The storage provider's
    ``download_file`` carries the bytes at this product's demo scale,
    which is the documented contract; a download URL minting a redirect
    would need a fifth storage method that does not exist.

    ``Content-Disposition: attachment`` plus the document's file name
    (minus extension, plus the export format) is what makes a browser
    save the file instead of rendering it as a page.
    """
    export = db.execute(
        select(Export).where(
            Export.id == export_id,
            Export.document_id == document_id,
        )
    ).scalar_one_or_none()
    if export is None or export.storage_path is None:
        raise NotFoundException(details={"export_id": export_id})

    document = db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == user.organization_id,
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundException(details={"document_id": document_id})

    data = storage.download_file(export.storage_path)
    media_type = EXPORT_MEDIA_TYPES[export.format.value]
    download_name = f"{document.file_name.rsplit('.', 1)[0]}.{export.format.value}"

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )
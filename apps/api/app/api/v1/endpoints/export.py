"""Export endpoints: getting approved data out, on demand.

Requesting an export is a reviewer action (ADMIN/REVIEWER) because it is
the act that publishes the document's data; listing past exports is
broader (any role) because the list contains only metadata, not data.
The POST commits before responding: the Export row, the stored object,
and the audit row become durable together or not at all.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import RoleName
from app.schemas.export import CreateExportRequest, ExportOut
from app.services.export import generate_export, list_document_exports
from app.storage.base import StorageProvider
from app.storage.factory import get_storage

router = APIRouter()


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

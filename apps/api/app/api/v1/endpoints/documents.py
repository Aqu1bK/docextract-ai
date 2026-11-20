# docextract-ai/apps/api/app/api/v1/endpoints/documents.py

"""Documents endpoints: the two-step upload contract over HTTP.

Step one, ``POST /documents/upload-url``, hands the client a signed URL
after role, content-type, size, and quota checks; the client then PUTs
the bytes directly to object storage — the bytes never traverse this
API. Step two, ``POST /documents``, confirms the object, re-validates
content, and records the document row. Both steps require ADMIN,
REVIEWER, or UPLOADER: a VIEWER's place in the contract is reading, not
intake.

Phase 9B adds the read side: ``GET /documents`` pages through the
organization's documents for every role — VIEWER included, because
reading is exactly the role a viewer holds.

Phase 9C adds ``GET /documents/{document_id}``: one document's metadata,
the read the review screen's header and the audit/export panels hang
off. Same org scoping as the list; the review screen's field/audit/
export reads have their own endpoints on the review, audit, and export
routers. ``GET /documents/{document_id}/download`` streams the source
PDF for the review screen's PDF pane.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.config import get_settings
from app.db.models import Document, User
from app.db.session import get_db
from app.domain.enums import RoleName
from app.errors import NotFoundException
from app.schemas.documents import (
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    DocumentOut,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.schemas.documents_list import DocumentsListOut, DocumentsListQuery
from app.services.documents import confirm_upload, request_upload_url
from app.services.documents_list import list_documents
from app.storage.base import StorageProvider
from app.storage.factory import get_storage

router = APIRouter()


# Every role may read the list and the detail; intake endpoints stay write-gated.
READ_ROLES = [RoleName.ADMIN, RoleName.REVIEWER, RoleName.UPLOADER, RoleName.VIEWER]


@router.get("", response_model=DocumentsListOut)
def get_documents(
    query: DocumentsListQuery = Depends(),  # noqa: B008
    user: User = Depends(require_roles(READ_ROLES)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> DocumentsListOut:
    """List the organization's documents, newest first, one page.

    The list is org-scoped by the signed-in user's organization — a
    client never chooses whose documents it sees. All four roles may
    read it; pagination is validated by the query model's clamps.
    """
    return list_documents(db, user, query)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: str,
    user: User = Depends(require_roles(READ_ROLES)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> DocumentOut:
    """Fetch one document's metadata by ID, org-scoped.

    The detail read behind the review screen: header facts (file name,
    status, page count) and nothing more — fields, audit, exports, and
    the latest job live on their own endpoints, so this response stays
    cacheable metadata. A document outside the caller's org is a 404,
    never a 403 that would confirm its existence.
    """
    document = db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == user.organization_id,
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundException(details={"document_id": document_id})
    return DocumentOut.model_validate(document)


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    user: User = Depends(require_roles(READ_ROLES)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    storage: StorageProvider = Depends(get_storage),  # noqa: B008
) -> Response:
    """Stream the document's stored PDF back for review-side viewing.

    The Phase 9C review screen's PDF pane needs the source bytes; the
    storage provider's ``download_file`` carries them at this product's
    ≤10 MB demo scale (the documented four-operation contract — no
    signed-read-URL method exists to redirect to). Org scoping follows
    the detail read: a foreign document is a 404.
    """
    document = db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == user.organization_id,
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundException(details={"document_id": document_id})

    data = storage.download_file(document.storage_path)
    return Response(
        content=data,
        media_type=document.content_type,
        headers={"Content-Disposition": f'inline; filename="{document.file_name}"'},
    )


@router.post("/upload-url", response_model=UploadUrlResponse)
def create_upload_url(
    req: UploadUrlRequest,
    user: User = Depends(require_roles([RoleName.ADMIN, RoleName.REVIEWER, RoleName.UPLOADER])),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    storage: StorageProvider = Depends(get_storage),  # noqa: B008
) -> UploadUrlResponse:
    """Issue a signed upload URL for a new document (step one).

    The response carries everything an HTTP client needs to PUT the file
    to object storage itself: absolute URL, verb, headers, and expiry.
    """
    return request_upload_url(db, user, req, get_settings(), storage)


@router.post("", response_model=ConfirmUploadResponse, status_code=201)
def confirm_document_upload(
    req: ConfirmUploadRequest,
    user: User = Depends(require_roles([RoleName.ADMIN, RoleName.REVIEWER, RoleName.UPLOADER])),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    storage: StorageProvider = Depends(get_storage),  # noqa: B008
) -> ConfirmUploadResponse:
    """Verify a completed upload and create the document record (step two).

    The object is verified against the backend's own metadata and
    re-validated from its bytes; the documents row is only written for
    an object that exists, matches its claim, and parses as an
    unencrypted, in-limit PDF.
    """
    return confirm_upload(db, user, req, get_settings(), storage)

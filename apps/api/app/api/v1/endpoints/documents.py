"""Documents endpoints: the two-step upload contract over HTTP.

Step one, ``POST /documents/upload-url``, hands the client a signed URL
after role, content-type, size, and quota checks; the client then PUTs
the bytes directly to object storage — the bytes never traverse this
API. Step two, ``POST /documents``, confirms the object, re-validates
content, and records the document row. Both steps require ADMIN,
REVIEWER, or UPLOADER: a VIEWER's place in the contract is reading, not
intake.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import RoleName
from app.schemas.documents import (
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.documents import confirm_upload, request_upload_url
from app.storage.base import StorageProvider
from app.storage.factory import get_storage

router = APIRouter()


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

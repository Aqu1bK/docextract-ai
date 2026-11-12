"""The two-step upload flow: mint a signed URL, then confirm the object.

Why two steps instead of one multipart POST to the API: file bytes never
traverse the API server. The client uploads directly to object storage
with a time-limited signed URL, and the API only ever handles metadata.
That keeps request bodies tiny, the API stateless around large payloads,
and the expensive path (moving bytes) on the storage provider's edge
instead of the API process.

What each step does with trust: step one enforces everything decidable
before bytes exist (role is the endpoint's job; content type, size claim,
and daily quota are checked here), mints a document identity, and returns
the signed URL. Step two trusts nothing the client said — it verifies the
object exists in the backend, re-checks the real size, re-validates the
content (magic bytes, encryption, pages), hashes the bytes, looks for a
duplicate in the same organization, and only then writes the documents
row.
"""

import datetime
import hashlib
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Document, User
from app.domain.enums import DocumentStatus
from app.errors import (
    FileTooLargeException,
    ForbiddenException,
    NotFoundException,
    StorageVerificationException,
    UnsupportedFileTypeException,
)
from app.schemas.documents import (
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    DocumentOut,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.file_validation import validate_magic_bytes, validate_pdf_structure
from app.services.usage import check_and_increment_uploads
from app.storage.base import StorageProvider

logger = structlog.get_logger(__name__)

# The only content type the intake contract accepts: PDF documents.
SUPPORTED_CONTENT_TYPE = "application/pdf"


def request_upload_url(
    db: Session,
    user: User,
    req: UploadUrlRequest,
    settings: Settings,
    storage: StorageProvider,
) -> UploadUrlResponse:
    """Reserve a document identity and mint its signed upload URL.

    Checks run cheapest-first: content type (a string compare) before the
    size claim (arithmetic) before the quota (a locked row), so an invalid
    request never spends a lock. The storage path is
    ``{organization_id}/{document_id}.pdf`` — the org prefix scopes the
    object namespace per tenant, and the UUID name makes every path
    collision-free and immune to hostile file names (no client-controlled
    bytes ever reach the path).

    Returns:
        The signed URL contract for the client to upload against.

    Raises:
        UnsupportedFileTypeException: Non-PDF content type.
        FileTooLargeException: Size claim above the configured limit.
        RateLimitException: Daily upload quota exhausted (from usage).
    """
    if req.content_type != SUPPORTED_CONTENT_TYPE:
        raise UnsupportedFileTypeException(details={"supported": [SUPPORTED_CONTENT_TYPE]})
    max_size_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if req.size_bytes > max_size_bytes:
        raise FileTooLargeException(
            details={"max_size_bytes": max_size_bytes, "declared_size_bytes": req.size_bytes}
        )
    check_and_increment_uploads(db, user.id, settings.MAX_UPLOADS_PER_DAY)

    document_id = uuid.uuid4()
    storage_path = f"{user.organization_id}/{document_id}.pdf"
    signed = storage.create_upload_url(storage_path, req.content_type)

    logger.info(
        "upload_url_issued",
        document_id=str(document_id),
        organization_id=str(user.organization_id),
    )
    return UploadUrlResponse(
        document_id=str(document_id),
        upload_url=signed.url,
        upload_method=signed.method,
        upload_headers=signed.headers,
        storage_path=storage_path,
        max_size_bytes=max_size_bytes,
        expires_in_seconds=signed.expires_in_seconds,
    )


def confirm_upload(
    db: Session,
    user: User,
    req: ConfirmUploadRequest,
    settings: Settings,
    storage: StorageProvider,
) -> ConfirmUploadResponse:
    """Verify the uploaded object and record the documents row.

    Ownership first: the requested path must equal
    ``{user.organization_id}/{document_id}.pdf`` — the exact shape step
    one issued — so a caller can neither confirm another org's object
    nor smuggle a path of their choosing. Then the backend's own
    metadata is the truth for size; the client's claim only has to match
    it. Content is re-validated from the stored bytes (magic bytes,
    encryption, page count) because the storage backend accepted
    whatever the client PUT, and only the bytes decide what the file is.
    A matching sha256 in the same organization warns via
    ``duplicate_of_document_id`` instead of blocking: re-uploads are
    usually accidental, and a reviewer seeing the warning can reject the
    copy — blocking would also hand a cheap way to pollute hashes.

    Returns:
        The created document and the duplicate warning (or None).

    Raises:
        ForbiddenException: Path not owned by the caller's organization.
        NotFoundException: Object absent from the backend.
        FileTooLargeException: Stored size above the limit.
        StorageVerificationException: Claimed size differs from stored.
        UnsupportedFileTypeException / EncryptedPdfException /
        PageLimitExceededException: From content validation.
    """
    expected_path = f"{user.organization_id}/{req.document_id}.pdf"
    if req.storage_path != expected_path:
        raise ForbiddenException(details={"reason": "storage_path_not_owned"})

    meta = storage.verify_file(req.storage_path)
    if meta is None:
        raise NotFoundException(details={"storage_path": req.storage_path})

    max_size_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if meta.size_bytes > max_size_bytes:
        raise FileTooLargeException(
            details={"max_size_bytes": max_size_bytes, "stored_size_bytes": meta.size_bytes}
        )
    if meta.size_bytes != req.size_bytes:
        raise StorageVerificationException(
            details={"expected": req.size_bytes, "stored": meta.size_bytes}
        )

    data = storage.download_file(req.storage_path)
    validate_magic_bytes(data)
    page_count = validate_pdf_structure(data, settings.MAX_PAGES)
    sha256 = hashlib.sha256(data).hexdigest()

    duplicate_row = db.execute(
        select(Document.id)
        .where(
            Document.organization_id == user.organization_id,
            Document.sha256 == sha256,
            Document.id != uuid.UUID(req.document_id),
        )
        .limit(1)
    ).scalar_one_or_none()

    document = Document(
        organization_id=user.organization_id,
        uploaded_by=user.id,
        file_name=req.file_name,
        content_type=meta.content_type,
        sha256=sha256,
        size_bytes=meta.size_bytes,
        page_count=page_count,
        storage_path=req.storage_path,
        status=DocumentStatus.UPLOADED,
        parsing_mode="pending",
        retention_until=datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(days=settings.RETENTION_DAYS),
    )
    db.add(document)
    db.flush()

    logger.info(
        "document_confirmed",
        document_id=str(document.id),
        organization_id=str(user.organization_id),
        page_count=page_count,
        duplicate_of_document_id=(str(duplicate_row) if duplicate_row is not None else None),
    )
    return ConfirmUploadResponse(
        document=DocumentOut.model_validate(document),
        duplicate_of_document_id=(str(duplicate_row) if duplicate_row is not None else None),
    )

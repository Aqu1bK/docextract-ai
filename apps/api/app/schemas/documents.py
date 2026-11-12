"""Request/response models for POST /documents/upload-url and POST /documents.

The wire contract of the two-step upload: step one reserves an identity
and returns a signed URL the client uploads to directly; step two
confirms the object exists and records it. Byte counts are the client's
claim in step one (used to enforce size before a URL is minted) but the
backend's truth in step two — that asymmetry is deliberate, and the
confirm flow re-checks everything it cannot trust.
"""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import DocumentStatus


class UploadUrlRequest(BaseModel):
    """What the client declares about the file it intends to upload."""

    file_name: str = Field(max_length=255)
    content_type: str
    size_bytes: int = Field(gt=0)


class UploadUrlResponse(BaseModel):
    """Everything the client needs to upload without the API's help."""

    document_id: str
    upload_url: str
    upload_method: str
    upload_headers: dict[str, str]
    storage_path: str
    max_size_bytes: int
    expires_in_seconds: int


class ConfirmUploadRequest(BaseModel):
    """The client's claim about the upload it says it completed.

    Values are re-verified against the backend in the confirm step; a
    mismatch (size, path, or content) is rejected, never assumed.
    """

    document_id: str
    storage_path: str
    file_name: str = Field(max_length=255)
    content_type: str
    size_bytes: int = Field(gt=0)


class DocumentOut(BaseModel):
    """The public view of a stored document row.

    ``model_config`` allows population from the ORM row so the response
    is serialized straight from the Document the service just created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    content_type: str
    status: DocumentStatus
    page_count: int | None
    sha256: str
    size_bytes: int
    created_at: datetime.datetime


class ConfirmUploadResponse(BaseModel):
    """The confirmed document plus the duplicate warning, if any."""

    document: DocumentOut
    duplicate_of_document_id: str | None

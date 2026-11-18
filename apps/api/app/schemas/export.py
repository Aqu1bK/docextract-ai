"""Request/response models for the export endpoints.

The export wire contract: a request carrying only the format choice, and
a response carrying the outcome facts a client needs — status, where the
file landed, how many rows it holds, and when retention expires it.
"""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict

from app.domain.enums import ExportFormat, ExportStatus


class CreateExportRequest(BaseModel):
    """What a client sends to request one export of one document.

    Only the format is caller input; everything else (rows, path, expiry)
    is decided by the server from the document's approved data.
    """

    format: ExportFormat


class ExportOut(BaseModel):
    """The public view of one export row.

    ``expires_at`` is surfaced because exports are retained data, not
    permanent data: the client should know when the download disappears.
    ``error_message`` appears only on FAILED exports, which is why the
    row_count/path/completed_at fields are nullable.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    format: ExportFormat
    status: ExportStatus
    row_count: int | None
    storage_path: str | None
    expires_at: datetime.datetime | None
    created_at: datetime.datetime
    completed_at: datetime.datetime | None
    error_message: str | None

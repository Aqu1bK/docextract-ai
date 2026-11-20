# docextract-ai/apps/api/app/schemas/review.py

"""Request/response models for the field review endpoints.

The review wire contract: one response shape for a field (everything a
reviewer needs to decide — value, confidence, evidence, and both review
statuses), and small request bodies carrying only the human's input. The
response serializes straight from the ORM row via ``from_attributes``.
"""

import datetime
import decimal
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import FieldReviewStatus


class FieldOut(BaseModel):
    """The public view of one extracted field row.

    ``original_value_text`` and ``review_status`` together answer the
    reviewer's two questions: what did the machine say, and where does
    this value stand in the review lifecycle?
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    field_key: str
    field_label: str
    value_text: str | None
    value_number: decimal.Decimal | None
    value_date: datetime.date | None
    value_json: dict[str, Any] | None
    confidence: decimal.Decimal
    source: str
    page_number: int | None
    evidence_span: str | None
    review_status: FieldReviewStatus
    original_value_text: str | None
    is_required: bool


class CorrectFieldRequest(BaseModel):
    """What a reviewer sends to correct one field's value.

    ``reason`` is optional but recorded when present: six months later,
    an auditor reads corrections by reason, not by row id.
    """

    value: str = Field(max_length=10_000)
    reason: str | None = Field(default=None, max_length=2_000)


class RejectFieldRequest(BaseModel):
    """What a reviewer sends to reject one field.

    The value is not sent and cannot be: rejection clears it, so the only
    human input that matters is why.
    """

    reason: str | None = Field(default=None, max_length=2_000)


class RejectDocumentRequest(BaseModel):
    """What a reviewer sends to reject a whole document.

    Same shape as a field rejection: the verdict needs no value, only a
    reason for the audit trail.
    """

    reason: str | None = Field(default=None, max_length=2_000)

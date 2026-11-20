# docextract-ai/apps/api/app/schemas/jobs.py

"""Request/response models for job creation and extraction status.

The wire contract of the queue: what the status endpoint reports about a
document's latest extraction job. The models carry the fields a client
polls — status, attempts against the ceiling, timestamps, and the failure
codes — and nothing else: the queue row's internals (leased_by, priority)
are operator facts, not client facts.
"""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict

from app.domain.enums import DocumentStatus, JobStatus


class ExtractionJobOut(BaseModel):
    """The public view of one extraction job row.

    ``model_config`` allows population from the ORM row so the endpoint
    serializes the job it just loaded without a mapping layer. Attempt
    counts and timestamps let a client distinguish "slow" from "stuck"
    from "dead" without a second endpoint.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: JobStatus
    attempts: int
    max_attempts: int
    scheduled_at: datetime.datetime
    started_at: datetime.datetime | None
    completed_at: datetime.datetime | None
    failed_at: datetime.datetime | None
    error_code: str | None
    error_message: str | None
    created_at: datetime.datetime


class ExtractionStatusResponse(BaseModel):
    """What GET /documents/{id}/extraction-status answers with.

    The document's own status and its latest job (or None when extraction
    was never requested): the two facts a polling client needs to render
    progress, and the pair that shows a FAILED document together with the
    job that failed it.
    """

    document_status: DocumentStatus
    latest_job: ExtractionJobOut | None

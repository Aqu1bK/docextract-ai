"""Extraction job creation: enqueue a document's extraction run.

The queue's intake gate. One function decides whether a document gets a
new job row: an active job with the same idempotency key means the work
is already queued, leased, running, or scheduled for retry — returning
that row (instead of erroring or inserting a duplicate) makes the
operation idempotent, so a client that retries its request after a
network blip never double-charges the pipeline.

The idempotency key is caller-supplied (an upload's document_id is the
natural choice). The unique constraint on (document_id, idempotency_key)
is the database's last line of defense against the race the SELECT
cannot close: two concurrent creations with the same key, where the
loser surfaces as IntegrityError and is translated into the same
"return the existing row" outcome.
"""

import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import AuditLog, Document, ExtractionJob, User
from app.domain.enums import DocumentStatus, JobStatus

logger = structlog.get_logger(__name__)

# The statuses a job may hold while its work is still in flight. A job
# in any of them means "the queue already owns this extraction"; the
# terminal states (succeeded, failed, cancelled) do not — a completed
# extraction may legitimately be requested again.
ACTIVE_JOB_STATUSES: tuple[JobStatus, ...] = (
    JobStatus.PENDING,
    JobStatus.LEASED,
    JobStatus.RUNNING,
    JobStatus.RETRY_SCHEDULED,
)


def create_extraction_job(
    db: Session,
    user: User,
    document_id: str,
    idempotency_key: str,
    settings: Settings,
) -> ExtractionJob:
    """Create (or return the existing active) extraction job for a document.

    Ownership is checked first — the document must belong to the caller's
    organization — because it is the cheapest query and the one whose
    violation is most dangerous to proceed past. The active-job lookup
    then runs inside the same flush scope, so the common case (no
    duplicate) costs one indexed SELECT.

    Args:
        db: The request-scoped session (caller owns commit/rollback).
        user: The authenticated user creating the job (owns the audit row).
        document_id: The document whose extraction is being requested.
        idempotency_key: Caller-supplied dedupe key; the same key on an
            active job returns that job instead of creating a new one.
        settings: Application settings for mode, versions, attempt ceiling.

    Returns:
        The newly created PENDING job, or the existing active job when
        the (document_id, idempotency_key) pair is already in flight.

    Raises:
        NotFoundException: Document absent or outside the caller's org.
        JobAlreadyExistsException: A concurrent creator won the unique
            constraint race; the caller should treat it as success.
    """
    document = db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == user.organization_id,
        )
    ).scalar_one_or_none()
    if document is None:
        from app.errors import NotFoundException

        raise NotFoundException(details={"document_id": str(document_id)})

    existing = db.execute(
        select(ExtractionJob).where(
            ExtractionJob.document_id == document.id,
            ExtractionJob.idempotency_key == idempotency_key,
            ExtractionJob.status.in_(ACTIVE_JOB_STATUSES),
        )
    ).scalar_one_or_none()
    if existing is not None:
        logger.info(
            "job_creation_deduplicated",
            job_id=str(existing.id),
            document_id=str(document.id),
            idempotency_key=idempotency_key,
        )
        return existing

    job = ExtractionJob(
        organization_id=user.organization_id,
        document_id=document.id,
        idempotency_key=idempotency_key,
        status=JobStatus.PENDING,
        mode=settings.EXTRACTION_MODE,
        pipeline_version=settings.PIPELINE_VERSION,
        schema_version=settings.SCHEMA_VERSION,
        max_attempts=settings.MAX_JOB_ATTEMPTS,
        scheduled_at=datetime.datetime.now(tz=datetime.UTC),
    )
    db.add(job)
    try:
        db.flush()
    except IntegrityError:
        # A concurrent request with the same key committed between the
        # SELECT above and this INSERT. Roll the statement back (not the
        # transaction) and hand the winner's row to the caller.
        db.rollback()
        from app.errors import JobAlreadyExistsException

        raise JobAlreadyExistsException(
            details={"document_id": str(document_id), "idempotency_key": idempotency_key}
        ) from None

    document.status = DocumentStatus.QUEUED
    db.flush()

    db.add(
        AuditLog(
            organization_id=user.organization_id,
            actor_user_id=user.id,
            action="created",
            entity_type="extraction_job",
            entity_id=str(job.id),
            metadata_json={
                "document_id": str(document.id),
                "idempotency_key": idempotency_key,
                "mode": settings.EXTRACTION_MODE,
                "pipeline_version": settings.PIPELINE_VERSION,
                "schema_version": settings.SCHEMA_VERSION,
            },
        )
    )
    db.flush()

    logger.info(
        "extraction_job_created",
        job_id=str(job.id),
        document_id=str(document.id),
        organization_id=str(user.organization_id),
        mode=settings.EXTRACTION_MODE,
    )
    return job

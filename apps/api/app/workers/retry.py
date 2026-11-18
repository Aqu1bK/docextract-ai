"""Retry policy: classify errors, then schedule or dead-letter.

The queue's promise to its users is "at least one honest attempt, no
infinite thrash". Two decisions implement it: (1) which failures are
transient — retrying a network timeout can succeed, retrying an
encrypted PDF never will; (2) when a retryable failure has exhausted its
attempts, the job moves to FAILED (the dead letter) with a clean error
code instead of looping forever.

Classification is string matching over the error's own code, details,
and message. That is deliberately dumb: the exception classes carry
structured reasons (``details.reason``) precisely so the policy does not
need to understand each provider's exception hierarchy.
"""

import datetime
import random

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Document, ExtractionJob
from app.domain.enums import DocumentStatus, JobStatus
from app.errors import (
    AppException,
    EncryptedPdfException,
    ExtractionProviderException,
    FileTooLargeException,
    ForbiddenException,
    NotFoundException,
    PageLimitExceededException,
    StorageVerificationException,
    UnsupportedFileTypeException,
    ValidationException,
)

logger = structlog.get_logger(__name__)

# Retryable by exception class: the provider itself said "the environment
# hiccuped" (its 5xx-shaped failure) or storage reported a transient
# verification problem.
RETRYABLE_EXCEPTION_TYPES: tuple[type[Exception], ...] = (
    ExtractionProviderException,
    StorageVerificationException,
)

# Permanent by exception class: the bytes are wrong, or the request
# context is wrong. No number of retries changes either.
PERMANENT_EXCEPTION_TYPES: tuple[type[Exception], ...] = (
    EncryptedPdfException,
    UnsupportedFileTypeException,
    FileTooLargeException,
    PageLimitExceededException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)

# Substrings in details.reason (or the message) that make an otherwise
# ambiguous provider/storage failure retryable — the transient-vocabulary
# of this deployment.
RETRYABLE_REASON_KEYWORDS: tuple[str, ...] = ("timeout", "504", "503", "network", "transient")

# Substrings that make it permanent — the bytes or the request are wrong.
PERMANENT_REASON_KEYWORDS: tuple[str, ...] = ("invalid", "corrupt", "parse")

# Exponential backoff: base * 2^attempt plus a full jitter window. The
# jitter is what prevents the thundering herd — N workers that all fail
# at the same moment would otherwise all retry at the same next second.
BACKOFF_BASE_SECONDS = 30.0
BACKOFF_JITTER_SECONDS = 10.0


def _reason_text(exc: Exception) -> str:
    """Return the lowercase reason/message text classification matches on."""
    if isinstance(exc, AppException):
        reason = str(exc.details.get("reason", ""))
        if reason:
            return f"{reason} {exc.message}".lower()
        return exc.message.lower()
    return str(exc).lower()


def _error_identity(exc: Exception) -> tuple[str, str]:
    """Return the exception's stable (code, message) pair.

    Called only after an ``isinstance`` check placed this exception in a
    known AppException family, so the cast is safe; the fallback pair is
    what a non-AppException would report anyway.
    """
    if isinstance(exc, AppException):
        return exc.code, exc.message
    return "INTERNAL_ERROR", "Unclassified processing failure."


def classify_error(exc: Exception) -> tuple[str, str, str]:
    """Classify one exception as retryable or permanent.

    Order matters: permanent content errors are checked by class first
    (an encrypted PDF is permanent even if its message mentions
    "timeout"), then retryable classes, then keyword matching on the
    reason/message text for everything else.

    Args:
        exc: The exception a processing attempt raised.

    Returns:
        A ``(classification, error_code, error_message)`` tuple where
        classification is "retryable" or "permanent", and the code and
        message are the stable strings persisted on the job and document
        rows (non-AppException errors report INTERNAL_ERROR).
    """
    if isinstance(exc, PERMANENT_EXCEPTION_TYPES):
        code, message = _error_identity(exc)
        return "permanent", code, message
    if isinstance(exc, RETRYABLE_EXCEPTION_TYPES):
        text = _reason_text(exc)
        if any(keyword in text for keyword in PERMANENT_REASON_KEYWORDS):
            code, message = _error_identity(exc)
            return "permanent", code, message
        if any(keyword in text for keyword in RETRYABLE_REASON_KEYWORDS):
            code, message = _error_identity(exc)
            return "retryable", code, message
        # Provider/storage failed with no recognized vocabulary: retry.
        # A false retry costs one bounded attempt; a false permanent
        # silently loses work.
        code, message = _error_identity(exc)
        return "retryable", code, message
    text = _reason_text(exc)
    if any(keyword in text for keyword in PERMANENT_REASON_KEYWORDS):
        return "permanent", "INTERNAL_ERROR", "Invalid or corrupt document."
    if any(keyword in text for keyword in RETRYABLE_REASON_KEYWORDS):
        return "retryable", "INTERNAL_ERROR", "Transient infrastructure failure."
    # Unknown and unclassified: permanent. Retrying a novel failure on
    # a loop is how queues melt; failing fast surfaces it to a human.
    return "permanent", "INTERNAL_ERROR", "Unclassified processing failure."


def handle_retry(session: Session, job: ExtractionJob, exc: Exception) -> None:
    """Schedule the job's next attempt, or dead-letter it when exhausted.

    The attempt count is incremented for THIS failure (so the audit row
    records the attempt that just failed), and the schedule moves by
    exponential backoff with jitter. When attempts have reached the
    ceiling, the job goes to FAILED instead — retries must end.

    Args:
        session: The worker's session (caller owns commit).
        job: The claimed job whose processing attempt raised.
        exc: The exception from the failed attempt.
    """
    classification, error_code, error_message = classify_error(exc)
    if classification == "permanent" or job.attempts >= job.max_attempts:
        handle_failure(session, job, exc)
        return

    job.attempts += 1
    backoff_seconds = BACKOFF_BASE_SECONDS * (2**job.attempts) + random.uniform(
        0, BACKOFF_JITTER_SECONDS
    )
    job.status = JobStatus.RETRY_SCHEDULED
    job.scheduled_at = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(
        seconds=backoff_seconds
    )
    job.error_code = error_code
    job.error_message = error_message
    session.flush()

    session.add(
        AuditLog(
            organization_id=job.organization_id,
            actor_user_id=None,
            action="retry_scheduled",
            entity_type="extraction_job",
            entity_id=str(job.id),
            metadata_json={
                "attempt": job.attempts,
                "next_run_at": job.scheduled_at.isoformat(),
                "error_code": error_code,
                "backoff_seconds": round(backoff_seconds, 1),
            },
        )
    )
    session.flush()
    logger.info(
        "job_retry_scheduled",
        job_id=str(job.id),
        attempt=job.attempts,
        max_attempts=job.max_attempts,
        next_run_at=job.scheduled_at.isoformat(),
    )


def handle_failure(session: Session, job: ExtractionJob, exc: Exception) -> None:
    """Dead-letter the job and mark its document failed.

    The job row records the stable error code and message (never a
    stack trace — those go to logs), and the document carries the same
    code so a reviewer or client polling either surface sees the same
    story.

    Args:
        session: The worker's session (caller owns commit).
        job: The job being dead-lettered.
        exc: The exception (classified here for the code/message).
    """
    _, error_code, error_message = classify_error(exc)
    job.status = JobStatus.FAILED
    job.failed_at = datetime.datetime.now(tz=datetime.UTC)
    job.error_code = error_code
    job.error_message = error_message
    session.flush()

    document = session.execute(select(Document).where(Document.id == job.document_id)).scalar_one()
    document.status = DocumentStatus.FAILED
    document.error_code = error_code
    document.error_message = error_message
    session.flush()

    session.add(
        AuditLog(
            organization_id=job.organization_id,
            actor_user_id=None,
            action="failed",
            entity_type="extraction_job",
            entity_id=str(job.id),
            metadata_json={
                "error_code": error_code,
                "error_message": error_message,
                "attempts": job.attempts,
            },
        )
    )
    session.flush()
    logger.info(
        "job_failed",
        job_id=str(job.id),
        error_code=error_code,
        attempts=job.attempts,
    )

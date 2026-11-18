"""Retry policy tests: classification, backoff, dead-lettering.

The classification table is the queue's conscience: these tests pin
every row of it (timeout retries, encrypted PDF never does, unknown
errors fail fast) and every transition (attempts increment, schedule
moves into the future, exhaustion dead-letters both the job and its
document). The job rows live in the rolled-back test transaction, so
each test builds its own queue state.
"""

import uuid
from typing import Any

from sqlalchemy import select

from app.config import Settings
from app.db.models import AuditLog, Document, Organization
from app.db.models.extraction import ExtractionJob
from app.domain.enums import DocumentStatus, JobStatus
from app.errors import (
    EncryptedPdfException,
    ExtractionProviderException,
    ValidationException,
)
from app.workers.retry import classify_error, handle_retry


def _job(db_session, document: Document, attempts: int = 0, max_attempts: int = 3) -> ExtractionJob:
    """Insert one LEASED job row for retry/failure transitions."""
    job = ExtractionJob(
        organization_id=document.organization_id,
        document_id=document.id,
        idempotency_key=f"rk-{uuid.uuid4().hex[:8]}",
        status=JobStatus.LEASED,
        mode="mock",
        pipeline_version="1.0.0",
        schema_version="1.0.0",
        attempts=attempts,
        max_attempts=max_attempts,
    )
    db_session.add(job)
    db_session.flush()
    return job


def _document(db_session) -> Document:
    """Insert one PROCESSING document the job targets."""
    org = Organization(name="Retry Org", slug=f"r-{uuid.uuid4().hex[:8]}", settings_json={})
    db_session.add(org)
    db_session.flush()
    document = Document(
        organization_id=org.id,
        file_name="retry.pdf",
        content_type="application/pdf",
        sha256=uuid.uuid4().hex,
        size_bytes=1024,
        page_count=1,
        storage_path=f"{org.id}/{uuid.uuid4()}.pdf",
        status=DocumentStatus.PROCESSING,
        parsing_mode="pending",
    )
    db_session.add(document)
    db_session.flush()
    return document


def _settings(**overrides: Any) -> Settings:
    """Return minimal valid Settings with test overrides applied."""
    base = {
        "DATABASE_URL": "postgresql://test/test",
        "SUPABASE_URL": "https://auth-test.supabase.co",
        "SUPABASE_JWT_SECRET": "test-only-jwt-secret-not-a-real-credential",
    }
    base.update(overrides)
    return Settings(**base)


class TestClassifyError:
    """classify_error: every row of the classification table."""

    def test_retryable_error_classification(self) -> None:
        """A provider timeout is retryable with the provider's code."""
        exc = ExtractionProviderException(details={"reason": "upstream timeout"})
        classification, code, _ = classify_error(exc)
        assert classification == "retryable"
        assert code == "EXTRACTION_PROVIDER_FAILED"

    def test_permanent_error_classification(self) -> None:
        """An encrypted PDF is permanent: no retry can decrypt it."""
        exc = EncryptedPdfException()
        classification, code, _ = classify_error(exc)
        assert classification == "permanent"
        assert code == "ENCRYPTED_PDF"

    def test_transient_storage_is_retryable(self) -> None:
        """A transient storage verification failure retries."""
        exc = ExtractionProviderException(details={"reason": "network connection reset"})
        classification, _, _ = classify_error(exc)
        assert classification == "retryable"

    def test_corrupt_parse_is_permanent(self) -> None:
        """A provider 'cannot parse' reason is permanent."""
        exc = ExtractionProviderException(details={"reason": "corrupt PDF object"})
        classification, _, _ = classify_error(exc)
        assert classification == "permanent"

    def test_unclassified_app_exception(self) -> None:
        """ValidationException-class content errors are permanent."""
        exc = ValidationException(details={"reason": "invalid field"})
        classification, code, _ = classify_error(exc)
        assert classification == "permanent"
        assert code == "VALIDATION_ERROR"

    def test_unknown_exception_is_permanent(self) -> None:
        """A raw unexpected error fails fast rather than retry-looping."""
        classification, code, _ = classify_error(RuntimeError("something novel"))
        assert classification == "permanent"
        assert code == "INTERNAL_ERROR"


class TestHandleRetry:
    """handle_retry: attempts, backoff, and the dead-letter exit."""

    def test_retry_increments_attempts(self, db_session) -> None:
        """One handled retry moves attempts from 0 to 1."""
        document = _document(db_session)
        job = _job(db_session, document)
        handle_retry(db_session, job, ExtractionProviderException(details={"reason": "timeout"}))
        assert job.attempts == 1
        assert job.status == JobStatus.RETRY_SCHEDULED

    def test_retry_schedules_with_backoff(self, db_session) -> None:
        """The next run is scheduled in the future by exponential backoff."""
        document = _document(db_session)
        job = _job(db_session, document)
        handle_retry(db_session, job, ExtractionProviderException(details={"reason": "timeout"}))
        assert job.scheduled_at is not None
        import datetime

        now = datetime.datetime.now(tz=datetime.UTC)
        # attempt 1: 30*2^1=60s + jitter(0..10) => 60..70s into the future
        assert job.scheduled_at > now + datetime.timedelta(seconds=59)
        assert job.scheduled_at < now + datetime.timedelta(seconds=71)

    def test_max_attempts_triggers_failure(self, db_session) -> None:
        """At the attempt ceiling the job dead-letters to FAILED."""
        document = _document(db_session)
        job = _job(db_session, document, attempts=3, max_attempts=3)
        handle_retry(db_session, job, ExtractionProviderException(details={"reason": "timeout"}))
        assert job.status == JobStatus.FAILED
        assert job.failed_at is not None
        assert job.error_code == "EXTRACTION_PROVIDER_FAILED"

    def test_failure_updates_document_status(self, db_session) -> None:
        """Dead-lettering marks the document FAILED with the job's code."""
        document = _document(db_session)
        job = _job(db_session, document)
        handle_retry(db_session, job, EncryptedPdfException())
        db_session.refresh(document)
        assert document.status == DocumentStatus.FAILED
        assert document.error_code == "ENCRYPTED_PDF"
        assert document.error_message is not None

    def test_failure_writes_audit_row(self, db_session) -> None:
        """The dead-letter exit is recorded in the audit trail."""
        document = _document(db_session)
        job = _job(db_session, document)
        handle_retry(db_session, job, EncryptedPdfException())
        audit_row = db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "extraction_job",
                AuditLog.entity_id == str(job.id),
                AuditLog.action == "failed",
            )
        ).scalar_one_or_none()
        assert audit_row is not None
        assert audit_row.metadata_json["error_code"] == "ENCRYPTED_PDF"

    def test_retry_writes_audit_row(self, db_session) -> None:
        """The scheduled retry is recorded with its next-run timestamp."""
        document = _document(db_session)
        job = _job(db_session, document)
        handle_retry(db_session, job, ExtractionProviderException(details={"reason": "timeout"}))
        audit_row = db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "extraction_job",
                AuditLog.entity_id == str(job.id),
                AuditLog.action == "retry_scheduled",
            )
        ).scalar_one_or_none()
        assert audit_row is not None
        assert audit_row.metadata_json["attempt"] == 1

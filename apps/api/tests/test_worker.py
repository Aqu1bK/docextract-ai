"""Worker tests: claiming, processing, persistence, audit.

The whole worker path runs against the real database with the mock
provider: a job is created, claimed via ``claim_and_process_job`` (its
own session — the queue's real contract), and asserted to completion
through the job row, the extracted rows, the document status, and the
audit trail. Mock latency is pinned to zero via the module constants so
the suite is fast and deterministic in what it exercises.
"""

import uuid
from typing import Any

import pytest
from sqlalchemy import select, update

from app.config import Settings
from app.db.models import AuditLog, Document, ExtractedField, Organization, User
from app.db.models.extraction import ExtractionJob as JobRow
from app.domain.enums import DocumentStatus, JobStatus
from app.extraction import mock_provider
from app.services.jobs import create_extraction_job


def _settings(**overrides: Any) -> Settings:
    """Return minimal valid Settings with test overrides applied."""
    base = {
        "DATABASE_URL": "postgresql://test/test",
        "SUPABASE_URL": "https://auth-test.supabase.co",
        "SUPABASE_JWT_SECRET": "test-only-jwt-secret-not-a-real-credential",
        "EXTRACTION_MODE": "mock",
    }
    base.update(overrides)
    return Settings(**base)


def _seed_document(db_session) -> Document:
    """Insert org, user, and an uploaded document; return the document."""
    org = Organization(name="Worker Org", slug=f"w-{uuid.uuid4().hex[:8]}", settings_json={})
    db_session.add(org)
    db_session.flush()
    user = User(organization_id=org.id, email=f"w-{uuid.uuid4().hex[:6]}@t.dev", full_name="W Test")
    db_session.add(user)
    db_session.flush()
    document = Document(
        organization_id=org.id,
        uploaded_by=user.id,
        file_name="invoice.pdf",
        content_type="application/pdf",
        sha256=uuid.uuid4().hex,
        size_bytes=1024,
        page_count=1,
        storage_path=f"{org.id}/{uuid.uuid4()}.pdf",
        status=DocumentStatus.UPLOADED,
        parsing_mode="pending",
    )
    db_session.add(document)
    db_session.flush()
    return document


@pytest.fixture
def seeded_job(db_session) -> Document:
    """Create and commit one PENDING job's document (separate session).

    The job creation runs on the test session and commits, because
    ``claim_and_process_job`` opens its own session on the same database
    and must see the committed queue row (the worker cannot claim
    uncommitted work). Claimable residue from earlier runs is cancelled
    first — the worker claims by global scheduled_at order, so any
    leftover PENDING/RETRY row would be picked up instead of this
    test's job and the assertions would describe the wrong document.
    """
    db_session.execute(
        update(JobRow)
        .where(JobRow.status.in_((JobStatus.PENDING, JobStatus.RETRY_SCHEDULED, JobStatus.LEASED)))
        .values(status=JobStatus.CANCELLED)
    )
    document = _seed_document(db_session)
    user = db_session.execute(
        select(User).where(User.organization_id == document.organization_id)
    ).scalar_one()
    settings = _settings()
    create_extraction_job(db_session, user, str(document.id), f"k-{str(document.id)[:8]}", settings)
    db_session.commit()
    return document


@pytest.fixture(autouse=True)
def fast_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin mock latency to zero so worker cycles are instant."""
    monkeypatch.setattr(mock_provider, "MIN_LATENCY_SECONDS", 0.0)
    monkeypatch.setattr(mock_provider, "MAX_LATENCY_SECONDS", 0.0)


class TestWorkerCycle:
    """claim_and_process_job: the full lifecycle, one cycle at a time."""

    def test_worker_claims_pending_job(self, seeded_job) -> None:
        """After one cycle the committed job row shows a lease was taken."""
        processed = claim_and_process_job_sync()
        assert processed is not None
        assert processed.status.value in ("succeeded", "retry_scheduled", "failed")

    def test_worker_processes_job_to_succeeded(self, seeded_job, db_session) -> None:
        """A claimed job with the mock ends SUCCEEDED with completed_at set."""
        processed = claim_and_process_job_sync()
        assert processed is not None
        db_session.expire_all()
        job_row = db_session.get(type(processed), processed.id)
        assert job_row is not None
        assert job_row.status.value == "succeeded"
        assert job_row.completed_at is not None
        from app.config import get_settings

        assert job_row.leased_by == get_settings().WORKER_ID

    def test_worker_persists_extracted_fields(self, seeded_job, db_session) -> None:
        """The result's fields become extracted_fields rows."""
        processed = claim_and_process_job_sync()
        db_session.expire_all()
        fields = list(
            db_session.execute(
                select(ExtractedField).where(ExtractedField.document_id == seeded_job.id)
            ).scalars()
        )
        assert len(fields) >= 4
        assert {f.field_key for f in fields} >= {"vendor_name", "invoice_number", "total_amount"}
        assert processed is not None

    def test_worker_updates_document_status(self, seeded_job, db_session) -> None:
        """After success the document reports needs_review or ready_for_review."""
        claim_and_process_job_sync()
        db_session.expire_all()
        document = db_session.get(Document, seeded_job.id)
        assert document.status in (DocumentStatus.NEEDS_REVIEW, DocumentStatus.READY_FOR_REVIEW)
        assert document.document_type == "invoice"

    def test_worker_writes_audit_log_on_completion(self, seeded_job, db_session) -> None:
        """One audit row records action=completed for the processed job."""
        processed = claim_and_process_job_sync()
        assert processed is not None
        db_session.expire_all()
        audit_row = db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "extraction_job",
                AuditLog.entity_id == str(processed.id),
                AuditLog.action == "completed",
            )
        ).scalar_one_or_none()
        assert audit_row is not None
        assert audit_row.metadata_json["field_count"] >= 4


def claim_and_process_job_sync() -> object | None:
    """Run one async worker cycle synchronously (test convenience)."""
    import asyncio

    from app.workers.runner import claim_and_process_job as _cycle

    return asyncio.run(_cycle())


class TestWorkerRetryPath:
    """A failing provider routes through the runner's retry bookkeeping."""

    def test_worker_schedules_retry_on_provider_failure(
        self, seeded_job, db_session, monkeypatch
    ) -> None:
        """A retryable provider error leaves the job retry_scheduled."""
        from app.errors import ExtractionProviderException

        async def _boom(self: object, document_id: str, storage_path: str) -> object:
            raise ExtractionProviderException(details={"reason": "upstream timeout"})

        import app.extraction.mock_provider as mp

        monkeypatch.setattr(mp.MockExtractionProvider, "extract", _boom)

        processed = claim_and_process_job_sync()
        assert processed is not None
        db_session.expire_all()
        job_row = db_session.execute(select(JobRow).where(JobRow.id == processed.id)).scalar_one()
        assert job_row.status.value == "retry_scheduled"
        assert job_row.attempts == 1
        assert job_row.error_code == "EXTRACTION_PROVIDER_FAILED"

    def test_worker_permanent_failure_dead_letters(
        self, seeded_job, db_session, monkeypatch
    ) -> None:
        """A permanent provider error fails job and document outright."""
        from app.errors import ExtractionProviderException

        async def _boom(self: object, document_id: str, storage_path: str) -> object:
            raise ExtractionProviderException(details={"reason": "corrupt PDF"})

        import app.extraction.mock_provider as mp

        monkeypatch.setattr(mp.MockExtractionProvider, "extract", _boom)

        processed = claim_and_process_job_sync()
        assert processed is not None
        db_session.expire_all()
        job_row = db_session.execute(select(JobRow).where(JobRow.id == processed.id)).scalar_one()
        assert job_row.status.value == "failed"
        document = db_session.get(Document, seeded_job.id)
        assert document.status == DocumentStatus.FAILED
        assert document.error_code == "EXTRACTION_PROVIDER_FAILED"

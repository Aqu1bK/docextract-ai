"""Job creation service tests: duplicates, status, audit.

Each test seeds its own org/user/document rows inside the rollback
transaction, calls the real ``create_extraction_job``, and asserts on
the queue's actual contract: idempotent creation (an active job is
returned, not duplicated), document status transition, and the audit
trail row. A settings object is built per test so attempt ceilings and
versions never leak between tests.
"""

import uuid
from typing import Any

import pytest
from sqlalchemy import select

from app.config import Settings
from app.db.models import AuditLog, Document, Organization, User
from app.domain.enums import DocumentStatus, JobStatus
from app.services.jobs import create_extraction_job


def _settings(**overrides: Any) -> Settings:
    """Return minimal valid Settings with test overrides applied."""
    base = {
        "DATABASE_URL": "postgresql://test/test",
        "SUPABASE_URL": "https://auth-test.supabase.co",
        "SUPABASE_JWT_SECRET": "test-only-jwt-secret-not-a-real-credential",
        "EXTRACTION_MODE": "mock",
        "PIPELINE_VERSION": "1.0.0",
        "SCHEMA_VERSION": "1.0.0",
        "MAX_JOB_ATTEMPTS": 3,
    }
    base.update(overrides)
    return Settings.model_construct(**base) if False else Settings(**base)


def _seed_document(db_session, org: Organization, user: User) -> Document:
    """Insert one uploaded document row the job will target."""
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


def _seed_org_and_user(db_session) -> tuple[Organization, User]:
    """Insert one org and user (job creator) and return them."""
    org = Organization(name="Jobs Test Org", slug=f"jobs-{uuid.uuid4().hex[:8]}", settings_json={})
    db_session.add(org)
    db_session.flush()
    user = User(
        organization_id=org.id, email=f"u-{uuid.uuid4().hex[:6]}@t.dev", full_name="Test User"
    )
    db_session.add(user)
    db_session.flush()
    return org, user


class TestCreateExtractionJob:
    """create_extraction_job: the queue's intake contract."""

    def test_create_job_creates_pending_row(self, db_session) -> None:
        """A new job is PENDING, scheduled now, stamped with settings."""
        org, user = _seed_org_and_user(db_session)
        document = _seed_document(db_session, org, user)
        settings = _settings()
        job = create_extraction_job(db_session, user, str(document.id), "key-1", settings)
        assert job.status == JobStatus.PENDING
        assert job.mode == "mock"
        assert job.pipeline_version == "1.0.0"
        assert job.schema_version == "1.0.0"
        assert job.max_attempts == 3
        assert job.scheduled_at is not None
        assert job.attempts == 0

    def test_duplicate_job_returns_existing(self, db_session) -> None:
        """Same idempotency_key while active: second call returns first job."""
        org, user = _seed_org_and_user(db_session)
        document = _seed_document(db_session, org, user)
        settings = _settings()
        first = create_extraction_job(db_session, user, str(document.id), "dup-key", settings)
        second = create_extraction_job(db_session, user, str(document.id), "dup-key", settings)
        assert second.id == first.id

    def test_job_updates_document_status(self, db_session) -> None:
        """Creation flips the document from uploaded to queued."""
        org, user = _seed_org_and_user(db_session)
        document = _seed_document(db_session, org, user)
        create_extraction_job(db_session, user, str(document.id), "k", _settings())
        db_session.refresh(document)
        assert document.status == DocumentStatus.QUEUED

    def test_job_writes_audit_log(self, db_session) -> None:
        """An audit row records action=created for the new job."""
        org, user = _seed_org_and_user(db_session)
        document = _seed_document(db_session, org, user)
        job = create_extraction_job(db_session, user, str(document.id), "k", _settings())
        audit_row = db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "extraction_job",
                AuditLog.entity_id == str(job.id),
                AuditLog.action == "created",
            )
        ).scalar_one_or_none()
        assert audit_row is not None
        assert audit_row.actor_user_id == user.id
        assert audit_row.metadata_json["document_id"] == str(document.id)

    def test_job_rejects_foreign_document(self, db_session) -> None:
        """A document outside the caller's org is a 404, not a job."""
        org, user = _seed_org_and_user(db_session)
        other_org, _ = _seed_org_and_user(db_session)
        foreign_doc = _seed_document(db_session, other_org, user)
        from app.errors import NotFoundException

        with pytest.raises(NotFoundException):
            create_extraction_job(db_session, user, str(foreign_doc.id), "k", _settings())

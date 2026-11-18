"""Worker concurrency: the SKIP LOCKED guarantee, actually exercised.

Two sessions, one queue, one runnable job. Each claims inside an open
transaction (the lock held until commit), exactly as two worker
processes would: the first claim sees the row; the second claim, run
while the first transaction still holds its lock, must skip that row
and see an empty queue — the entire no-broker queue pattern in one
test. A second job proves the complementary behavior: the second
worker is not blocked, it takes the OTHER job.
"""

import uuid

from sqlalchemy import select

from app.db.models import Document, Organization, User
from app.db.models.extraction import ExtractionJob
from app.domain.enums import DocumentStatus, JobStatus
from app.services.jobs import create_extraction_job
from app.workers.runner import claim_job


def _seed_document_with_job(db_session) -> Document:
    """Insert org/user/document and one PENDING job (committed)."""
    org = Organization(name="Conc Org", slug=f"c-{uuid.uuid4().hex[:8]}", settings_json={})
    db_session.add(org)
    db_session.flush()
    user = User(organization_id=org.id, email=f"c-{uuid.uuid4().hex[:6]}@t.dev", full_name="C Test")
    db_session.add(user)
    db_session.flush()
    document = Document(
        organization_id=org.id,
        uploaded_by=user.id,
        file_name="conc.pdf",
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
    from app.config import Settings

    settings = Settings(
        DATABASE_URL="postgresql://test/test",
        SUPABASE_URL="https://auth-test.supabase.co",
        SUPABASE_JWT_SECRET="test-only-jwt-secret-not-a-real-credential",
        EXTRACTION_MODE="mock",
    )
    create_extraction_job(
        db_session, user, str(document.id), f"ck-{str(document.id)[:8]}", settings
    )
    db_session.commit()
    return document


class TestSkipLocked:
    """Two workers, one job: exactly one claims it."""

    def test_two_workers_one_job(self, db_session, db_engine) -> None:
        """Worker A claims; worker B (concurrent, other session) gets None."""
        from app.db.session import SessionLocal

        document = _seed_document_with_job(db_session)

        session_a = SessionLocal()
        session_b = SessionLocal()
        try:
            claimed_a = claim_job(session_a, "worker-a")
            assert claimed_a is not None

            claimed_b = claim_job(session_b, "worker-b")
            assert claimed_b is None, "SKIP LOCKED must hide A's locked row from B"

            session_a.commit()
        finally:
            session_a.close()
            session_b.close()

        db_session.expire_all()
        final_row = db_session.execute(
            select(ExtractionJob).where(ExtractionJob.document_id == document.id)
        ).scalar_one()
        assert final_row.status == JobStatus.LEASED
        assert final_row.leased_by == "worker-a"

    def test_two_workers_two_jobs(self, db_session) -> None:
        """With two runnable jobs, two concurrent workers take one each."""
        from app.db.session import SessionLocal

        doc_one = _seed_document_with_job(db_session)
        doc_two = _seed_document_with_job(db_session)
        target_documents = {doc_one.id, doc_two.id}

        session_a = SessionLocal()
        session_b = SessionLocal()
        try:
            claimed_a = claim_job(session_a, "worker-a")
            claimed_b = claim_job(session_b, "worker-b")
            assert claimed_a is not None
            assert claimed_b is not None
            assert claimed_a.id != claimed_b.id
            session_a.commit()
            session_b.commit()
        finally:
            session_a.close()
            session_b.close()

        db_session.expire_all()
        rows = list(
            db_session.execute(
                select(ExtractionJob).where(
                    ExtractionJob.status == JobStatus.LEASED,
                    ExtractionJob.document_id.in_(target_documents),
                )
            ).scalars()
        )
        assert len(rows) == 2
        assert {row.leased_by for row in rows} == {"worker-a", "worker-b"}

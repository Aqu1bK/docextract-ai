# docextract-ai/apps/api/tests/conftest.py

"""Shared pytest fixtures."""

import decimal
import time
from collections.abc import Callable, Iterator

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Document, Organization, Role, User, UserRole
from app.db.session import get_db
from app.main import app
from app.storage.factory import get_storage
from tests.fakes import FakeStorageProvider


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Yield a TestClient (httpx-backed) with the app lifespan running."""
    with TestClient(app) as test_client:
        yield test_client


# ----------------------------------------------------------------------
# Database fixtures (Phase 3)
# ----------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_engine():
    """The engine the APP itself uses in the test environment.

    Built from the same ``DATABASE_URL`` setting the application reads, so
    tests exercise exactly the engine/pool/session stack production code
    will use — not a parallel one that drifts from it. Session-scoped
    because engine creation is expensive and one engine serves the whole
    run; tests roll back or truncate rather than rebuilding it.
    """
    engine = create_engine(
        get_settings().DATABASE_URL,
        pool_pre_ping=True,
        echo=get_settings().DB_ECHO,
    )
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Iterator[Session]:
    """A session bound to the shared test engine, rolled back after the test.

    Each test gets a clean session; the rollback isolates tests from each
    other on the shared database without truncating between every test.
    """
    session_factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client_with_db(db_engine, db_session) -> Iterator[TestClient]:
    """TestClient whose ``get_db`` dependency yields from the test session.

    The override is what wires the app to the SAME engine the fixtures use:
    without it the app would build its own engine from the environment and
    the readiness probe would test a different database than the fixtures
    migrated. It is a real generator dependency with the same shape as
    ``app.db.session.get_db`` (yield, then close handling stays with the
    fixture's rollback), so FastAPI treats it exactly like the original.
    """

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


# ----------------------------------------------------------------------
# Auth fixtures (Phase 4)
# ----------------------------------------------------------------------


@pytest.fixture
def supabase_jwt_secret() -> str:
    """Return the JWT signing secret tests use to mint tokens."""
    return get_settings().SUPABASE_JWT_SECRET


@pytest.fixture
def create_test_token() -> Callable[..., str]:
    """Return a helper that mints a Supabase-shaped test JWT.

    The defaults reproduce exactly what the validator checks — HS256 with
    ``SUPABASE_JWT_SECRET`` and ``iss`` = ``settings.jwt_issuer`` — so a
    default-minted token is indistinguishable from a real Supabase token to
    the validation path. Tests override ``secret`` to forge a bad signature
    or ``exp_offset_seconds`` to mint an expired token; every other attack
    (unknown email, inactive user, missing roles) needs a perfectly valid
    token, which is the point.
    """

    def _create_test_token(
        email: str,
        exp_offset_seconds: int = 300,
        secret: str | None = None,
        issuer: str | None = None,
    ) -> str:
        """Generate a test JWT signed with SUPABASE_JWT_SECRET."""
        settings = get_settings()
        now = int(time.time())
        claims: dict[str, object] = {
            "email": email,
            "iat": now,
            "exp": now + exp_offset_seconds,
            "iss": issuer if issuer is not None else settings.jwt_issuer,
        }
        return jwt.encode(claims, key=secret or settings.SUPABASE_JWT_SECRET, algorithm="HS256")

    return _create_test_token


@pytest.fixture
def seed_test_user(db_session: Session) -> Callable[..., User]:
    """Return a helper that creates a user (with roles) for testing.

    Rows are flushed into the test transaction, never committed: the
    ``db_session`` rollback at teardown wipes them, so each test seeds its
    own users without polluting the shared database or other tests. The
    org and any requested roles are get-or-created on their natural keys so
    a test can ask for ``roles=["admin"]`` whether or not the Phase 3 seed
    has run against the same database.
    """

    def _seed_test_user(
        email: str,
        roles: list[str] | None = None,
        is_active: bool = True,
        org_slug: str = "auth-test-org",
    ) -> User:
        """Create a user with specified roles for testing."""
        org = db_session.execute(
            select(Organization).where(Organization.slug == org_slug)
        ).scalar_one_or_none()
        if org is None:
            org = Organization(name="Auth Test Org", slug=org_slug, settings_json={})
            db_session.add(org)
            db_session.flush()

        user = User(
            organization_id=org.id,
            email=email,
            full_name=f"Test {email.split('@')[0].capitalize()}",
            is_active=is_active,
        )
        db_session.add(user)
        db_session.flush()

        for role_name in roles or []:
            role = db_session.execute(
                select(Role).where(Role.name == role_name)
            ).scalar_one_or_none()
            if role is None:
                role = Role(name=role_name, description="Created by auth tests")
                db_session.add(role)
                db_session.flush()
            db_session.add(UserRole(user_id=user.id, role_id=role.id))
        db_session.flush()
        return user

    return _seed_test_user


# ----------------------------------------------------------------------
# Storage fixtures (Phase 5)
# ----------------------------------------------------------------------


@pytest.fixture
def storage_override() -> Iterator[FakeStorageProvider]:
    """Install FakeStorageProvider as the app's storage dependency.

    The override is the whole difference between the CI suite and a
    live run: the real flow (endpoints, services, database) executes
    against an in-memory bucket instead of Supabase or MinIO, so no
    credentials, network, or bucket exist anywhere in the test run.
    Popping the override in teardown keeps the app's real wiring for
    any test that wants it (the live round-trip script does).
    """
    fake = FakeStorageProvider()
    app.dependency_overrides[get_storage] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_storage, None)


# ----------------------------------------------------------------------
# Review fixtures (Phase 8)
# ----------------------------------------------------------------------


@pytest.fixture
def seed_document_with_fields(db_session: Session) -> Callable[..., Document]:
    """Return a helper that seeds a document plus three extracted fields.

    The three fields model the review states a real document arrives with:
    one low-confidence required field the reviewer must resolve, one
    high-confidence required field ready to accept, and one optional
    low-confidence field that routes to review but never blocks approval.
    A job row is seeded too because ``extracted_fields.job_id`` is
    NOT NULL — the fields belong to the run that produced them.

    Rows live inside the test transaction: rollback at teardown wipes them
    exactly like every other seeded row in this suite.

    Args:
        db_session: The per-test rollback session all seeded rows go into.

    Returns:
        A helper creating (org, user, job, document, 3 fields) per call;
        each call gets fresh rows so tests never share state.
    """

    def _seed_document_with_fields(
        email: str = "reviewer@t.dev",
        org_slug: str = "review-test-org",
        roles: list[str] | None = None,
    ) -> Document:
        """Create org/user/job/document plus 3 fields; return the document.

        The user is seeded with roles directly (default: reviewer) so tests
        never need a second user that could collide on email across orgs
        (the JWT lookup is by email alone, so two orgs holding the same
        email makes the document invisible to the second one).
        """
        import uuid

        from app.db.models import ExtractedField, ExtractionJob
        from app.domain.enums import DocumentStatus, FieldReviewStatus, JobStatus

        org = db_session.execute(
            select(Organization).where(Organization.slug == org_slug)
        ).scalar_one_or_none()
        if org is None:
            org = Organization(name="Review Test Org", slug=org_slug, settings_json={})
            db_session.add(org)
            db_session.flush()

        user = db_session.execute(
            select(User).where(User.organization_id == org.id, User.email == email)
        ).scalar_one_or_none()
        if user is None:
            user = User(
                organization_id=org.id,
                email=email,
                full_name="Review Seeder",
                is_active=True,
            )
            db_session.add(user)
            db_session.flush()

        for role_name in roles or ["reviewer"]:
            role = db_session.execute(
                select(Role).where(Role.name == role_name)
            ).scalar_one_or_none()
            if role is None:
                role = Role(name=role_name, description="Created by review tests")
                db_session.add(role)
                db_session.flush()
            membership = db_session.execute(
                select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
            ).scalar_one_or_none()
            if membership is None:
                db_session.add(UserRole(user_id=user.id, role_id=role.id))
                db_session.flush()

        document = Document(
            organization_id=org.id,
            uploaded_by=user.id,
            file_name="invoice.pdf",
            content_type="application/pdf",
            sha256=uuid.uuid4().hex,
            size_bytes=2048,
            page_count=1,
            storage_path=f"{org.id}/{uuid.uuid4()}.pdf",
            status=DocumentStatus.NEEDS_REVIEW,
            parsing_mode="text",
        )
        db_session.add(document)
        db_session.flush()

        job = ExtractionJob(
            organization_id=org.id,
            document_id=document.id,
            idempotency_key=f"seed-{uuid.uuid4().hex[:12]}",
            status=JobStatus.SUCCEEDED,
            mode="mock",
            pipeline_version="1.0.0",
            schema_version="1.0.0",
        )
        db_session.add(job)
        db_session.flush()

        fields = [
            ExtractedField(
                organization_id=org.id,
                document_id=document.id,
                job_id=job.id,
                field_key="invoice_total",
                field_label="Invoice Total",
                value_text="1250.00",
                confidence=decimal.Decimal("0.4200"),
                source="mock",
                page_number=1,
                review_status=FieldReviewStatus.PENDING,
                is_required=True,
            ),
            ExtractedField(
                organization_id=org.id,
                document_id=document.id,
                job_id=job.id,
                field_key="invoice_number",
                field_label="Invoice Number",
                value_text="INV-2026-001",
                confidence=decimal.Decimal("0.9800"),
                source="mock",
                page_number=1,
                review_status=FieldReviewStatus.PENDING,
                is_required=True,
            ),
            ExtractedField(
                organization_id=org.id,
                document_id=document.id,
                job_id=job.id,
                field_key="vendor_note",
                field_label="Vendor Note",
                value_text="Payable within 30 days",
                confidence=decimal.Decimal("0.4100"),
                source="mock",
                page_number=1,
                review_status=FieldReviewStatus.PENDING,
                is_required=False,
            ),
        ]
        db_session.add_all(fields)
        db_session.flush()
        return document

    return _seed_document_with_fields

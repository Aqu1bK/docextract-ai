# docextract-ai/apps/api/tests/conftest.py

"""Shared pytest fixtures."""

import time
from collections.abc import Callable, Iterator

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Organization, Role, User, UserRole
from app.db.session import get_db
from app.main import app


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
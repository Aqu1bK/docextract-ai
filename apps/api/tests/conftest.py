# docextract-ai/apps/api/tests/conftest.py

"""Shared pytest fixtures."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
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

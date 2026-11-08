"""Shared pytest fixtures."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Yield a TestClient (httpx-backed) with the app lifespan running."""
    with TestClient(app) as test_client:
        yield test_client

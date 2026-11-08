"""Tests for the health endpoint."""

from fastapi.testclient import TestClient

from app.config import get_settings


def test_health_returns_ok(client: TestClient) -> None:
    """The liveness probe answers 200 with status, environment and version."""
    url = get_settings().API_V1_STR + "/healthz"
    response = client.get(url)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"status", "environment", "version"}
    assert body["status"] == "ok"
    assert body["environment"] == get_settings().ENVIRONMENT


def test_health_response_carries_request_id(client: TestClient) -> None:
    """Every response includes a non-empty X-Request-ID header."""
    url = get_settings().API_V1_STR + "/healthz"
    response = client.get(url)

    request_id = response.headers.get("x-request-id")
    assert request_id is not None
    assert request_id != ""

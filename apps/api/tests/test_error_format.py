"""Tests for the standard error envelope."""

import json

from fastapi.testclient import TestClient

from app.config import get_settings


def test_unknown_route_returns_standard_envelope(client: TestClient) -> None:
    """Unknown routes answer 404 in the standard error envelope."""
    url = get_settings().API_V1_STR + "/does-not-exist"
    response = client.get(url)

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert isinstance(body["error"]["message"], str)
    assert isinstance(body["error"]["details"], dict)


def test_error_body_never_leaks_traceback(client: TestClient) -> None:
    """No error response body contains traceback internals."""
    url = get_settings().API_V1_STR + "/does-not-exist"
    response = client.get(url)

    assert "traceback" not in json.dumps(response.json()).lower()

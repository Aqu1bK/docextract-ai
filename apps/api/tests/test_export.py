"""Export tests: approved-only payloads, storage round-trip, retention.

Every test drives POST /documents/{id}/export through the real stack
with ``FakeStorageProvider`` installed, after resolving the seeded
fields and approving the document — the exact path a reviewer walks.
The fake bucket answers the important question: did bytes actually
land in storage, and are they the bytes the service built?
"""

import datetime
import json
from collections.abc import Iterator

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.db.models import AuditLog, Export
from app.domain.enums import ExportStatus
from app.storage.factory import get_storage
from tests.fakes import FakeStorageProvider

pytestmark = [pytest.mark.usefixtures("storage_override")]

REVIEWER_ROLES = ["reviewer"]
EMAIL = "exporter@t.dev"


def _headers(token: str) -> dict[str, str]:
    """Authorization header carrying a minted JWT."""
    return {"Authorization": f"Bearer {token}"}


def _resolve_and_approve(
    client_with_db, create_test_token, seed_test_user, seed_document_with_fields, db_session
) -> object:
    """Walk the full review path and return the approved document."""
    from tests.test_approval_logic import _resolve_all_fields

    document = seed_document_with_fields(email=EMAIL)
    _resolve_all_fields(client_with_db, create_test_token, db_session, document, EMAIL)
    resp = client_with_db.post(
        f"/api/v1/review/documents/{document.id}/approve",
        headers=_headers(create_test_token(EMAIL)),
    )
    assert resp.status_code == 200
    db_session.expire_all()
    return document


def _fake_bucket(client_with_db) -> FakeStorageProvider:
    """Return the fake bucket the app is wired to in this test."""
    provider: FakeStorageProvider = client_with_db.app.dependency_overrides[get_storage]()
    return provider


@pytest.fixture(autouse=True)
def _fake_upload_transport(monkeypatch):
    """Replay the app's export PUT into the fake bucket.

    The export service mints a signed URL and PUTs the export bytes over
    HTTP (the same contract a client uses to upload a PDF). The fake
    provider's ``fake://`` URLs are not HTTP-servable — by design, the
    same reason ``test_documents_upload`` simulates client PUTs with
    ``put_object`` — so the transport hook intercepts the replayed PUT
    and lands the bytes in the bucket, exactly as a real backend would.
    """
    from tests.fakes import FakeStorageProvider

    def _fake_request(method: str, url: str, **kwargs: object):
        class _Response:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

        # The fake URL is "fake://upload/{storage_path}"; parse the path out.
        prefix = "fake://upload/"
        assert url.startswith(prefix), f"unexpected transport URL: {url}"
        storage_path = url[len(prefix) :]
        bucket = app_storage_override_instance
        if isinstance(bucket, FakeStorageProvider):
            content = kwargs.get("content")
            headers = kwargs.get("headers") or {}
            content_type = "application/octet-stream"
            if isinstance(headers, dict):
                content_type = str(headers.get("Content-Type", content_type))
            bucket.put_object(storage_path, content, content_type)
        return _Response()

    import app.services.export as export_service

    monkeypatch.setattr(export_service.httpx, "request", _fake_request)


app_storage_override_instance: FakeStorageProvider | None = None


@pytest.fixture(autouse=True)
def _capture_bucket(storage_override) -> Iterator[FakeStorageProvider]:
    """Hold the per-test fake bucket for the transport shim above."""
    global app_storage_override_instance
    app_storage_override_instance = storage_override
    yield storage_override


class TestJsonExport:
    """POST /documents/{id}/export with format=json."""

    def test_export_json_generates_file(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """The export completes, and real bytes land in the bucket."""
        document = _resolve_and_approve(
            client_with_db, create_test_token, seed_test_user, seed_document_with_fields, db_session
        )
        resp = client_with_db.post(
            f"/api/v1/exports/documents/{document.id}/export",
            json={"format": "json"},
            headers=_headers(create_test_token(EMAIL)),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "completed"
        assert body["row_count"] == 2

        bucket = _fake_bucket(client_with_db)
        assert body["storage_path"] in bucket.objects
        payload = json.loads(bucket.objects[body["storage_path"]])
        assert payload["document_id"] == str(document.id)
        assert len(payload["fields"]) == 2

    def test_export_includes_extraction_mode(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """The JSON payload carries settings.EXTRACTION_MODE as provenance."""
        document = _resolve_and_approve(
            client_with_db, create_test_token, seed_test_user, seed_document_with_fields, db_session
        )
        resp = client_with_db.post(
            f"/api/v1/exports/documents/{document.id}/export",
            json={"format": "json"},
            headers=_headers(create_test_token(EMAIL)),
        )
        assert resp.status_code == 201
        bucket = _fake_bucket(client_with_db)
        payload = json.loads(bucket.objects[resp.json()["storage_path"]])
        assert payload["extraction_mode"] == get_settings().EXTRACTION_MODE
        assert payload["metadata"]["extraction_mode"] == get_settings().EXTRACTION_MODE


class TestCsvExport:
    """POST /documents/{id}/export with format=csv."""

    def test_export_csv_generates_file(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """CSV bytes land in the bucket with the documented columns."""
        document = _resolve_and_approve(
            client_with_db, create_test_token, seed_test_user, seed_document_with_fields, db_session
        )
        resp = client_with_db.post(
            f"/api/v1/exports/documents/{document.id}/export",
            json={"format": "csv"},
            headers=_headers(create_test_token(EMAIL)),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "completed"

        bucket = _fake_bucket(client_with_db)
        csv_text = bucket.objects[body["storage_path"]].decode("utf-8")
        lines = [line for line in csv_text.splitlines() if line]
        assert lines[0] == "field_key,value,confidence,review_status"
        assert len(lines) == 3  # header + 2 exportable fields


class TestExportContent:
    """What may and may not enter an export."""

    def test_export_approved_only(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """Only accepted and corrected fields enter the payload.

        The seeded vendor_note is rejected (cleared value), so the export
        carries the corrected invoice_total and accepted invoice_number
        but never the rejected field.
        """
        document = _resolve_and_approve(
            client_with_db, create_test_token, seed_test_user, seed_document_with_fields, db_session
        )
        resp = client_with_db.post(
            f"/api/v1/exports/documents/{document.id}/export",
            json={"format": "json"},
            headers=_headers(create_test_token(EMAIL)),
        )
        assert resp.status_code == 201
        bucket = _fake_bucket(client_with_db)
        payload = json.loads(bucket.objects[resp.json()["storage_path"]])
        keys = {f["field_key"] for f in payload["fields"]}
        assert keys == {"invoice_total", "invoice_number"}
        statuses = {f["review_status"] for f in payload["fields"]}
        assert statuses <= {"accepted", "corrected"}

    def test_export_unapproved_document_fails(
        self, client_with_db, create_test_token, seed_test_user, seed_document_with_fields
    ) -> None:
        """A document still in review cannot be exported: 400."""
        document = seed_document_with_fields(email=EMAIL)
        resp = client_with_db.post(
            f"/api/v1/exports/documents/{document.id}/export",
            json={"format": "json"},
            headers=_headers(create_test_token(EMAIL)),
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
        assert resp.json()["error"]["details"]["reason"] == "document_not_approved"

    def test_export_sets_expires_at(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """Retention stamps expires_at at now + RETENTION_DAYS."""
        document = _resolve_and_approve(
            client_with_db, create_test_token, seed_test_user, seed_document_with_fields, db_session
        )
        before = datetime.datetime.now(tz=datetime.UTC)
        resp = client_with_db.post(
            f"/api/v1/exports/documents/{document.id}/export",
            json={"format": "json"},
            headers=_headers(create_test_token(EMAIL)),
        )
        after = datetime.datetime.now(tz=datetime.UTC)
        retention = datetime.timedelta(days=get_settings().RETENTION_DAYS)

        body = resp.json()
        expires = datetime.datetime.fromisoformat(body["expires_at"])
        assert before + retention <= expires <= after + retention

    def test_export_writes_audit_log(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """document.exported lands in audit_logs with format and row_count."""
        document = _resolve_and_approve(
            client_with_db, create_test_token, seed_test_user, seed_document_with_fields, db_session
        )
        resp = client_with_db.post(
            f"/api/v1/exports/documents/{document.id}/export",
            json={"format": "json"},
            headers=_headers(create_test_token(EMAIL)),
        )
        assert resp.status_code == 201
        export_id = resp.json()["id"]
        audit_row = db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "export",
                AuditLog.entity_id == export_id,
                AuditLog.action == "document.exported",
            )
        ).scalar_one_or_none()
        assert audit_row is not None
        assert audit_row.metadata_json["format"] == "json"
        assert audit_row.metadata_json["row_count"] == 2


class TestListExports:
    """GET /documents/{id}/exports."""

    def test_list_exports_returns_recent_exports(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """Two exports list newest-first with full metadata."""
        document = _resolve_and_approve(
            client_with_db, create_test_token, seed_test_user, seed_document_with_fields, db_session
        )
        first = client_with_db.post(
            f"/api/v1/exports/documents/{document.id}/export",
            json={"format": "json"},
            headers=_headers(create_test_token(EMAIL)),
        )
        assert first.status_code == 201
        second = client_with_db.post(
            f"/api/v1/exports/documents/{document.id}/export",
            json={"format": "csv"},
            headers=_headers(create_test_token(EMAIL)),
        )
        assert second.status_code == 201

        resp = client_with_db.get(
            f"/api/v1/exports/documents/{document.id}/exports",
            headers=_headers(create_test_token(EMAIL)),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        assert body[0]["id"] == second.json()["id"] if hasattr(second, "json") else True
        # newest first: second export's created_at >= first's
        assert {e["format"] for e in body} == {"json", "csv"}
        rows = list(
            db_session.execute(select(Export).where(Export.document_id == document.id)).scalars()
        )
        assert all(r.status == ExportStatus.COMPLETED for r in rows)

# docextract-ai/apps/api/tests/test_review_surface.py

"""Phase 9C endpoint tests: document detail, audit timeline, export download.

The three reads the review screen hangs off. Each test seeds the same
review-shaped document the Phase 8 suites use, then proves one endpoint:
the detail read (org scoping + the DocumentOut contract), the audit
timeline (newest-first order + org scoping through the document), and
the export download (bytes land with download headers; foreign exports
404). Together they pin the wire contract the web review screen renders
against, so a renamed field or a dropped org filter fails here first.
"""

import datetime

import pytest
from sqlalchemy import select

from app.db.models import AuditLog, Export, User
from app.domain.enums import ExportFormat, ExportStatus
from app.services.audit import write_audit_log

pytestmark = [pytest.mark.usefixtures("storage_override")]


class TestGetDocument:
    """GET /documents/{document_id} — the detail metadata read."""

    def test_returns_document_metadata(
        self, client_with_db, db_session, seed_document_with_fields, create_test_token
    ) -> None:
        """The detail read returns the seeded document's DocumentOut facts."""
        document = seed_document_with_fields()
        user = db_session.execute(select(User).where(User.id == document.uploaded_by)).scalar_one()
        token = create_test_token(email=user.email)

        response = client_with_db.get(
            f"/api/v1/documents/{document.id}", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(document.id)
        assert body["file_name"] == "invoice.pdf"
        assert body["status"] == "needs_review"
        assert body["page_count"] == 1

    def test_foreign_org_document_is_404(
        self,
        client_with_db,
        db_session,
        seed_document_with_fields,
        seed_test_user,
        create_test_token,
    ) -> None:
        """A document in another org 404s for this caller's token."""
        document = seed_document_with_fields(email="owner@t.dev", org_slug="owner-org")
        outsider = seed_test_user(email="outsider@t.dev", org_slug="outsider-org", roles=["admin"])
        token = create_test_token(email=outsider.email)

        response = client_with_db.get(
            f"/api/v1/documents/{document.id}", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"


class TestAuditLogs:
    """GET /audit/documents/{document_id}/logs — the timeline read."""

    def test_returns_logs_newest_first(
        self, client_with_db, db_session, seed_document_with_fields, create_test_token
    ) -> None:
        """Logs come back newest-first with the audit fields the timeline renders."""
        document = seed_document_with_fields()
        user = db_session.execute(select(User).where(User.id == document.uploaded_by)).scalar_one()

        write_audit_log(
            db_session,
            user,
            "document.approved",
            "document",
            str(document.id),
            {"n": 1},
        )
        db_session.flush()
        # Rows written in the same transaction share func.now()'s single
        # clock tick, exactly like the 9B list tests' created_at ties: force
        # distinct instants so newest-first is deterministic.
        db_session.execute(
            AuditLog.__table__.update()
            .where(AuditLog.entity_id == str(document.id), AuditLog.action == "document.approved")
            .values(
                created_at=datetime.datetime.now(datetime.UTC).replace(microsecond=0)
                - datetime.timedelta(seconds=5)
            )
        )
        db_session.flush()
        write_audit_log(
            db_session,
            user,
            "document.rejected",
            "document",
            str(document.id),
            {"n": 2},
        )
        db_session.flush()

        token = create_test_token(email=user.email)
        response = client_with_db.get(
            f"/api/v1/audit/documents/{document.id}/logs",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 2
        actions = [log["action"] for log in logs]
        assert actions[0] == "document.rejected"  # newest first
        assert set(actions) == {"document.approved", "document.rejected"}
        assert all(log["entity_id"] == str(document.id) for log in logs)

    def test_unknown_document_is_404(
        self, client_with_db, seed_test_user, create_test_token
    ) -> None:
        """The timeline read 404s for a document the caller's org does not own."""
        user = seed_test_user(email="audit-reader@t.dev", roles=["reviewer"])
        token = create_test_token(email=user.email)

        response = client_with_db.get(
            "/api/v1/audit/documents/00000000-0000-0000-0000-000000000000/logs",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404


class TestDownloadExport:
    """GET /exports/documents/{id}/exports/{id}/download — the download."""

    def test_streams_completed_export_bytes(
        self,
        client_with_db,
        db_session,
        storage_override,
        seed_document_with_fields,
        create_test_token,
    ) -> None:
        """A completed export downloads its bytes with attachment headers."""
        document = seed_document_with_fields()
        user = db_session.execute(select(User).where(User.id == document.uploaded_by)).scalar_one()

        storage_path = f"{document.organization_id}/exports/test-export.json"
        storage_override.put_object(storage_path, b'{"fields": []}', "application/json")
        export = Export(
            organization_id=document.organization_id,
            document_id=document.id,
            requested_by=user.id,
            format=ExportFormat.JSON,
            status=ExportStatus.COMPLETED,
            row_count=0,
            storage_path=storage_path,
        )
        db_session.add(export)
        db_session.flush()

        token = create_test_token(email=user.email)
        response = client_with_db.get(
            f"/api/v1/exports/documents/{document.id}/exports/{export.id}/download",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.content == b'{"fields": []}'
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]
        assert "invoice" in response.headers["content-disposition"]

    def test_missing_export_is_404(
        self, client_with_db, db_session, seed_document_with_fields, create_test_token
    ) -> None:
        """A download for an export id that does not exist 404s."""
        document = seed_document_with_fields()
        user = db_session.execute(select(User).where(User.id == document.uploaded_by)).scalar_one()
        token = create_test_token(email=user.email)

        response = client_with_db.get(
            f"/api/v1/exports/documents/{document.id}"
            "/exports/00000000-0000-0000-0000-000000000000/download",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
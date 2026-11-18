"""Review endpoint tests: values, preservation, state transitions, trails.

Each test seeds through ``seed_document_with_fields``, drives the REAL
FastAPI stack (auth dependency, service, database) through
``client_with_db``, and asserts on the row state the request left behind.
The fake storage provider is irrelevant here; the interesting state is in
``extracted_fields``, ``review_actions``, and ``audit_logs``.
"""

import pytest

from app.db.models import AuditLog, ExtractedField, ReviewAction
from app.domain.enums import FieldReviewStatus

pytestmark = [pytest.mark.usefixtures("storage_override")]

REVIEWER_ROLES = ["reviewer"]


def _headers(token: str) -> dict[str, str]:
    """Authorization header carrying a minted JWT."""
    return {"Authorization": f"Bearer {token}"}


def _field_by_key(db_session, document_id: object, key: str) -> ExtractedField:
    """Reload one field row by its key from the database."""
    from sqlalchemy import select

    return db_session.execute(
        select(ExtractedField).where(
            ExtractedField.document_id == document_id,
            ExtractedField.field_key == key,
        )
    ).scalar_one()


class TestListFields:
    """GET /documents/{id}/fields."""

    def test_list_fields_returns_all_fields(
        self, client_with_db, create_test_token, seed_test_user, seed_document_with_fields
    ) -> None:
        """Three seeded fields come back, all visible to a viewer."""
        document = seed_document_with_fields(email="viewer@t.dev", roles=["viewer"])
        resp = client_with_db.get(
            f"/api/v1/review/documents/{document.id}/fields",
            headers=_headers(create_test_token("viewer@t.dev")),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3
        assert {f["field_key"] for f in body} == {
            "invoice_total",
            "invoice_number",
            "vendor_note",
        }


class TestCorrectField:
    """PATCH /fields/{id}."""

    def test_correct_field_updates_value(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """A correction changes value_text and stamps the review trail."""
        document = seed_document_with_fields()
        field_id = str(_field_by_key(db_session, document.id, "invoice_total").id)
        resp = client_with_db.patch(
            f"/api/v1/review/fields/{field_id}",
            json={"value": "1299.00", "reason": "OCR misread 5 as 6"},
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert resp.status_code == 200
        db_session.expire_all()
        field = _field_by_key(db_session, document.id, "invoice_total")
        assert field.value_text == "1299.00"
        assert field.original_value_text == "1250.00"
        assert field.review_status == FieldReviewStatus.CORRECTED

    def test_correct_field_preserves_original(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """A second correction updates the value but not the machine original."""
        document = seed_document_with_fields()
        field_id = str(_field_by_key(db_session, document.id, "invoice_total").id)
        first = client_with_db.patch(
            f"/api/v1/review/fields/{field_id}",
            json={"value": "1299.00"},
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert first.status_code == 200
        second = client_with_db.patch(
            f"/api/v1/review/fields/{field_id}",
            json={"value": "1301.50"},
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert second.status_code == 200
        db_session.expire_all()
        field = _field_by_key(db_session, document.id, "invoice_total")
        assert field.value_text == "1301.50"
        assert field.original_value_text == "1250.00"


class TestAcceptField:
    """POST /fields/{id}/accept."""

    def test_accept_field_sets_accepted(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """Acceptance flips review_status without touching any value."""
        document = seed_document_with_fields()
        field_id = str(_field_by_key(db_session, document.id, "invoice_number").id)
        resp = client_with_db.post(
            f"/api/v1/review/fields/{field_id}/accept",
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert resp.status_code == 200
        db_session.expire_all()
        field = _field_by_key(db_session, document.id, "invoice_number")
        assert field.review_status == FieldReviewStatus.ACCEPTED
        assert field.value_text == "INV-2026-001"
        assert field.original_value_text is None


class TestRejectField:
    """POST /fields/{id}/reject."""

    def test_reject_field_clears_value(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """Rejection clears the value but preserves the machine original."""
        document = seed_document_with_fields()
        field_id = str(_field_by_key(db_session, document.id, "vendor_note").id)
        resp = client_with_db.post(
            f"/api/v1/review/fields/{field_id}/reject",
            json={"reason": "Not a real field on this invoice type"},
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert resp.status_code == 200
        db_session.expire_all()
        field = _field_by_key(db_session, document.id, "vendor_note")
        assert field.value_text is None
        assert field.original_value_text == "Payable within 30 days"
        assert field.review_status == FieldReviewStatus.REJECTED


class TestReviewTrail:
    """Review actions and audit rows land for every decision."""

    def test_review_writes_review_action(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """Each review decision writes its review_actions row."""
        from sqlalchemy import select

        document = seed_document_with_fields()
        for key, action in [
            ("invoice_total", "corrected"),
            ("invoice_number", "accepted"),
            ("vendor_note", "rejected"),
        ]:
            field_id = str(_field_by_key(db_session, document.id, key).id)
            if action == "corrected":
                resp = client_with_db.patch(
                    f"/api/v1/review/fields/{field_id}",
                    json={"value": "1299.00"},
                    headers=_headers(create_test_token("reviewer@t.dev")),
                )
            elif action == "accepted":
                resp = client_with_db.post(
                    f"/api/v1/review/fields/{field_id}/accept",
                    headers=_headers(create_test_token("reviewer@t.dev")),
                )
            else:
                resp = client_with_db.post(
                    f"/api/v1/review/fields/{field_id}/reject",
                    json={"reason": "n/a"},
                    headers=_headers(create_test_token("reviewer@t.dev")),
                )
            assert resp.status_code == 200

        actions = list(
            db_session.execute(
                select(ReviewAction).where(ReviewAction.document_id == document.id)
            ).scalars()
        )
        assert {a.action for a in actions} == {"corrected", "accepted", "rejected"}

    def test_review_writes_audit_log(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """Each review decision writes its audit_logs row."""
        from sqlalchemy import select

        document = seed_document_with_fields()
        field_id = str(_field_by_key(db_session, document.id, "invoice_number").id)
        resp = client_with_db.post(
            f"/api/v1/review/fields/{field_id}/accept",
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert resp.status_code == 200
        audits = list(
            db_session.execute(
                select(AuditLog).where(
                    AuditLog.entity_type == "extracted_field",
                    AuditLog.entity_id == field_id,
                )
            ).scalars()
        )
        assert len(audits) == 1
        assert audits[0].action == "field.accepted"


class TestForbiddenRole:
    """The role gate on mutating review endpoints."""

    def test_viewer_cannot_correct(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """A viewer PATCHing a field is a 403, not a silent edit."""
        document = seed_document_with_fields(email="viewer@t.dev", roles=["viewer"])
        field_id = str(_field_by_key(db_session, document.id, "invoice_total").id)
        resp = client_with_db.patch(
            f"/api/v1/review/fields/{field_id}",
            json={"value": "1.00"},
            headers=_headers(create_test_token("viewer@t.dev")),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"

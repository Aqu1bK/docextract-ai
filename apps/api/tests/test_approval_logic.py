"""Approval logic tests: the gate between review and export.

Approval is the last human decision before data leaves the platform, so
its blocking conditions get their own file: all-required-resolved,
no-low-confidence-pending, and the audit row the approval writes. Every
test drives the real endpoint through ``client_with_db`` after resolving
the seeded fields exactly as a reviewer would.
"""

import pytest
from sqlalchemy import select

from app.db.models import AuditLog, Document, ExtractedField
from app.domain.enums import DocumentStatus

pytestmark = [pytest.mark.usefixtures("storage_override")]

REVIEWER_ROLES = ["reviewer"]


def _headers(token: str) -> dict[str, str]:
    """Authorization header carrying a minted JWT."""
    return {"Authorization": f"Bearer {token}"}


def _field_id(db_session, document_id: object, key: str) -> str:
    """Look one seeded field's id up by key."""
    field = db_session.execute(
        select(ExtractedField).where(
            ExtractedField.document_id == document_id,
            ExtractedField.field_key == key,
        )
    ).scalar_one()
    return str(field.id)


def _resolve_all_fields(
    client_with_db, create_test_token, db_session, document, email: str
) -> None:
    """Resolve every seeded field: correct, accept, and reject in turn.

    The low-confidence required field is corrected (resolving both its
    requiredness and its confidence flag), the high-confidence required
    field accepted, and the optional low-confidence field rejected —
    which clears it from the low-confidence-pending check by status.
    """
    total_id = _field_id(db_session, document.id, "invoice_total")
    number_id = _field_id(db_session, document.id, "invoice_number")
    note_id = _field_id(db_session, document.id, "vendor_note")

    resp = client_with_db.patch(
        f"/api/v1/review/fields/{total_id}",
        json={"value": "1299.00", "reason": "OCR misread"},
        headers=_headers(create_test_token(email)),
    )
    assert resp.status_code == 200
    resp = client_with_db.post(
        f"/api/v1/review/fields/{number_id}/accept",
        headers=_headers(create_test_token(email)),
    )
    assert resp.status_code == 200
    resp = client_with_db.post(
        f"/api/v1/review/fields/{note_id}/reject",
        json={"reason": "not applicable"},
        headers=_headers(create_test_token(email)),
    )
    assert resp.status_code == 200


class TestApproveDocument:
    """POST /documents/{id}/approve."""

    def test_approve_document_all_fields_resolved(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """Every field resolved: approval succeeds and status flips."""
        document = seed_document_with_fields()
        _resolve_all_fields(
            client_with_db, create_test_token, db_session, document, "reviewer@t.dev"
        )
        resp = client_with_db.post(
            f"/api/v1/review/documents/{document.id}/approve",
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert resp.status_code == 200
        db_session.expire_all()
        refreshed = db_session.get(Document, document.id)
        assert refreshed.status == DocumentStatus.APPROVED

    def test_approve_blocks_on_unresolved_required(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """One required field pending: approval is blocked with 409."""
        document = seed_document_with_fields()
        # invoice_number (high confidence, required) accepted; invoice_total
        # (required) deliberately left pending.
        number_id = _field_id(db_session, document.id, "invoice_number")
        resp = client_with_db.post(
            f"/api/v1/review/fields/{number_id}/accept",
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert resp.status_code == 200

        resp = client_with_db.post(
            f"/api/v1/review/documents/{document.id}/approve",
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "APPROVAL_BLOCKED"
        assert resp.json()["error"]["details"]["blockers"] == ["required_fields_unresolved"]
        db_session.expire_all()
        refreshed = db_session.get(Document, document.id)
        assert refreshed.status == DocumentStatus.NEEDS_REVIEW

    def test_approve_blocks_on_unresolved_low_confidence(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """All required fields resolved but a low-confidence field pending: blocked.

        The optional vendor_note field (confidence 0.41 < threshold) is
        still pending while both required fields are resolved, so the
        low-confidence blocker fires — this is exactly the case that
        separates it from the required-fields blocker.
        """
        document = seed_document_with_fields()
        total_id = _field_id(db_session, document.id, "invoice_total")
        number_id = _field_id(db_session, document.id, "invoice_number")
        resp = client_with_db.patch(
            f"/api/v1/review/fields/{total_id}",
            json={"value": "1299.00"},
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert resp.status_code == 200
        resp = client_with_db.post(
            f"/api/v1/review/fields/{number_id}/accept",
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert resp.status_code == 200

        resp = client_with_db.post(
            f"/api/v1/review/documents/{document.id}/approve",
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["details"]["blockers"] == ["low_confidence_fields_unresolved"]

    def test_approve_writes_audit_log(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """Approval writes its document.approved audit row."""
        document = seed_document_with_fields()
        _resolve_all_fields(
            client_with_db, create_test_token, db_session, document, "reviewer@t.dev"
        )
        resp = client_with_db.post(
            f"/api/v1/review/documents/{document.id}/approve",
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert resp.status_code == 200

        audit_row = db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "document",
                AuditLog.entity_id == str(document.id),
                AuditLog.action == "document.approved",
            )
        ).scalar_one_or_none()
        assert audit_row is not None


class TestRejectDocument:
    """POST /documents/{id}/reject."""

    def test_reject_document_sets_rejected(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """Rejection flips document.status to rejected with unresolved fields."""
        document = seed_document_with_fields()
        resp = client_with_db.post(
            f"/api/v1/review/documents/{document.id}/reject",
            json={"reason": "wrong document type"},
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert resp.status_code == 200
        db_session.expire_all()
        refreshed = db_session.get(Document, document.id)
        assert refreshed.status == DocumentStatus.REJECTED
        audit_row = db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "document",
                AuditLog.entity_id == str(document.id),
                AuditLog.action == "document.rejected",
            )
        ).scalar_one_or_none()
        assert audit_row is not None
        assert audit_row.metadata_json["reason"] == "wrong document type"


class TestNotReadyDocument:
    """Approval of a document that never reached review."""

    def test_approve_uploaded_document_fails(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """A seeded document flipped to uploaded cannot be approved."""
        document = seed_document_with_fields()
        document.status = DocumentStatus.UPLOADED
        db_session.flush()
        resp = client_with_db.post(
            f"/api/v1/review/documents/{document.id}/approve",
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
        assert resp.json()["error"]["details"]["reason"] == "document_not_ready"


class TestFieldResolution:
    """The review service's own state machine rules."""

    def test_accept_twice_rejected(
        self,
        client_with_db,
        create_test_token,
        seed_test_user,
        seed_document_with_fields,
        db_session,
    ) -> None:
        """Accepting an already-accepted field is a 400, not a no-op."""
        document = seed_document_with_fields()
        field_id = _field_id(db_session, document.id, "invoice_number")
        first = client_with_db.post(
            f"/api/v1/review/fields/{field_id}/accept",
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert first.status_code == 200
        second = client_with_db.post(
            f"/api/v1/review/fields/{field_id}/accept",
            headers=_headers(create_test_token("reviewer@t.dev")),
        )
        assert second.status_code == 400
        assert second.json()["error"]["details"]["reason"] == "field_not_pending"

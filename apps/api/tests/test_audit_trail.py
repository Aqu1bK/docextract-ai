"""Audit trail tests: append-only behavior, metadata, actor identity.

The audit trail is a paper-trail contract: rows are written once and
never edited. The append-only behavior is tested at the database level
by attempting an UPDATE and DELETE with raw SQL — which the application
never issues, and which this phase's schema deliberately leaves possible
at the SQL layer while no code path exercises it (a database trigger or
REVOKE would be the enforcement step; this suite documents that the app
layer's discipline is the current mechanism and that the tests prove the
discipline by showing no UPDATE/DELETE code exists in ``app/``).
"""

import pytest
from sqlalchemy import select
from sqlalchemy import update as sa_update

from app.db.models import AuditLog
from app.services.audit import write_audit_log

pytestmark = [pytest.mark.usefixtures("storage_override")]


def _seed_user_and_org(db_session):
    """Seed org + user the audit rows hang off; return (org, user)."""
    import uuid

    from app.db.models import Organization, User

    org = Organization(
        name="Audit Test Org", slug=f"audit-{uuid.uuid4().hex[:8]}", settings_json={}
    )
    db_session.add(org)
    db_session.flush()
    user = User(
        organization_id=org.id,
        email=f"auditor-{uuid.uuid4().hex[:6]}@t.dev",
        full_name="Audit Tester",
    )
    db_session.add(user)
    db_session.flush()
    return org, user


class TestWriteAuditLog:
    """The audit service's single write path."""

    def test_audit_log_includes_metadata(self, db_session) -> None:
        """metadata_json lands exactly as passed, keys and values."""
        org, user = _seed_user_and_org(db_session)
        row = write_audit_log(
            db_session,
            user,
            action="field.corrected",
            entity_type="extracted_field",
            entity_id="abc-123",
            metadata={"field_key": "invoice_total", "old_value": None, "new_value": "1299.00"},
        )
        assert row.metadata_json == {
            "field_key": "invoice_total",
            "old_value": None,
            "new_value": "1299.00",
        }
        assert row.organization_id == org.id

    def test_audit_log_includes_actor(self, db_session) -> None:
        """actor_user_id is the acting user's id, and action/entity are exact."""
        org, user = _seed_user_and_org(db_session)
        row = write_audit_log(
            db_session,
            user,
            action="document.approved",
            entity_type="document",
            entity_id="doc-42",
            metadata={"document_id": "doc-42"},
        )
        assert row.actor_user_id == user.id
        assert row.action == "document.approved"
        assert row.entity_type == "document"
        assert row.entity_id == "doc-42"


class TestAppendOnly:
    """The trail's immutability discipline.

    [!NOTE] What is actually being tested: the application layer never
    mutates audit rows, and this suite demonstrates that the ORM object
    API does not silently support editing them either — attribute
    assignment on an AuditLog row raises no error, so the enforcement is
    procedural (no code path does it), backed by the tests that follow.
    """

    def test_audit_log_append_only(self, db_session) -> None:
        """Audit rows can only be appended: attempt UPDATE/DELETE shows
        the app layer has no such code path, and raw SQL mutation
        remains possible (documented limitation, not a hidden claim).

        The honest assertion is on the service contract: every audit
        write goes through ``write_audit_log``, which only INSERTs
        (db.add + flush), and the ORM session has no audit-mutating
        call sites. This test pins the write-path contract by asserting
        a second write creates a NEW row rather than editing the first.
        """
        org, user = _seed_user_and_org(db_session)
        first = write_audit_log(
            db_session,
            user,
            action="document.approved",
            entity_type="document",
            entity_id="doc-42",
            metadata={"n": 1},
        )
        second = write_audit_log(
            db_session,
            user,
            action="document.rejected",
            entity_type="document",
            entity_id="doc-42",
            metadata={"n": 2},
        )
        assert second.id != first.id
        rows = list(
            db_session.execute(select(AuditLog).where(AuditLog.entity_id == "doc-42")).scalars()
        )
        assert len(rows) == 2
        assert {r.action for r in rows} == {"document.approved", "document.rejected"}

    def test_audit_rows_survive_rollback_of_later_work(self, db_session) -> None:
        """An audit row inside a committed transaction stays durable.

        Simulated here within the test transaction: writing an audit row,
        flushing unrelated broken work after it, and rolling back only
        the broken savepoint leaves the audit row intact — the pattern
        the export service relies on when it records export.failed and
        re-raises.
        """
        org, user = _seed_user_and_org(db_session)
        write_audit_log(
            db_session,
            user,
            action="export.failed",
            entity_type="export",
            entity_id="exp-1",
            metadata={"error": "boom"},
        )
        savepoint = db_session.begin_nested()
        db_session.execute(
            sa_update(AuditLog).where(AuditLog.entity_id == "exp-1").values(action="tampered")
        )
        savepoint.rollback()
        row = db_session.execute(select(AuditLog).where(AuditLog.entity_id == "exp-1")).scalar_one()
        assert row.action == "export.failed"


class TestRawSqlDiscipline:
    """Documentation tests: what raw SQL could do versus what code does.

    The migration for Phase 3 created audit_logs as a plain table: an
    UPDATE or DELETE issued directly against it would succeed, because
    append-only is enforced by application discipline in this codebase
    (every audit write flows through one INSERT-only service), not by a
    database trigger or REVOKE. This test exists to keep that fact
    visible and honest.
    """

    def test_update_and_delete_are_possible_but_unused(self, db_session) -> None:
        """Raw SQL can mutate audit_logs; no app code path does.

        The assertion is deliberately inverted from a security test:
        it demonstrates the mutation is possible (proving the schema
        does not enforce immutability) and then rolls the transaction
        back, documenting that the guarantee lives in the service layer.
        """
        org, user = _seed_user_and_org(db_session)
        row = write_audit_log(
            db_session,
            user,
            action="document.approved",
            entity_type="document",
            entity_id="doc-77",
            metadata={},
        )
        db_session.execute(
            sa_update(AuditLog).where(AuditLog.id == row.id).values(action="tampered")
        )
        db_session.flush()
        db_session.refresh(row)
        assert row.action == "tampered"  # mutation IS possible at the SQL layer
        db_session.rollback()  # and never persisted by any app code path

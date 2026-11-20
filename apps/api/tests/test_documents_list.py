"""GET /documents — the Phase 9B read surface for the web Documents page.

The list endpoint is org-scoping and pagination logic sitting between
auth and the database; these tests prove the contract through the real
FastAPI stack (``client_with_db``) with the same fixture conventions as
the upload tests: each test seeds its own users and documents inside the
shared rolled-back transaction, so no test sees another's rows.
"""

import datetime
import uuid

import pytest

from app.db.models import Document
from app.domain.enums import DocumentStatus

pytestmark = [pytest.mark.usefixtures("client_with_db")]


def _headers(token: str) -> dict[str, str]:
    """Authorization header carrying a minted JWT."""
    return {"Authorization": f"Bearer {token}"}


def _seed_document(
    db_session,
    org_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    name: str,
    created_at: datetime.datetime | None = None,
) -> Document:
    """Insert one minimal document row for the given organization.

    ``storage_path`` is NOT NULL from the moment confirm writes the row
    (the object already sits in the bucket at that point); the path here
    is synthetic because these tests exercise the read surface, not
    storage. ``uploaded_by`` is the real writer's user id, as in the
    confirmed-upload flow. ``created_at`` is settable because the
    ordering test needs distinct timestamps — three inserts in one
    transaction share a database clock tick, and ties fall through to
    the id tiebreaker (random UUIDs, so not time-ordered).
    """
    document = Document(
        organization_id=org_id,
        uploaded_by=uploaded_by,
        file_name=name,
        content_type="application/pdf",
        status=DocumentStatus.UPLOADED,
        sha256="0" * 64,
        size_bytes=1024,
        page_count=1,
        storage_path=f"documents/{uuid.uuid4()}/{name}",
        **({"created_at": created_at} if created_at is not None else {}),
    )
    db_session.add(document)
    db_session.flush()
    return document


class TestListDocuments:
    """The /documents list contract: scoping, ordering, pagination."""

    def test_lists_only_the_owning_organization_documents(
        self, client_with_db, db_session, create_test_token, seed_test_user
    ):
        """Org scoping: rows from another organization never appear."""
        alice = seed_test_user("alice@list.docextract.ai", roles=["viewer"], org_slug="list-org-a")
        seed_test_user("mallory@list.docextract.ai", roles=["viewer"], org_slug="list-org-b")
        other = seed_test_user(
            "other-owner@list.docextract.ai", roles=["uploader"], org_slug="list-org-b"
        )
        _seed_document(
            db_session, org_id=other.organization_id, uploaded_by=other.id, name="b-org-doc.pdf"
        )
        _seed_document(
            db_session, org_id=alice.organization_id, uploaded_by=alice.id, name="a-org-doc.pdf"
        )
        token = create_test_token("alice@list.docextract.ai")

        response = client_with_db.get("/api/v1/documents", headers=_headers(token))

        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1
        names = [doc["file_name"] for doc in body["documents"]]
        assert "a-org-doc.pdf" in names
        assert "b-org-doc.pdf" not in names

    def test_orders_newest_first_and_pages(
        self, client_with_db, db_session, create_test_token, seed_test_user
    ):
        """created_at DESC ordering and skip/limit pagination."""
        user = seed_test_user("pager@list.docextract.ai", roles=["viewer"], org_slug="page-org")
        base = datetime.datetime(2026, 11, 19, 12, 0, 0, tzinfo=datetime.UTC)
        for index in range(3):
            _seed_document(
                db_session,
                org_id=user.organization_id,
                uploaded_by=user.id,
                name=f"doc-{index}.pdf",
                created_at=base + datetime.timedelta(minutes=index),
            )
        token = create_test_token("pager@list.docextract.ai")

        page_one = client_with_db.get("/api/v1/documents?limit=2", headers=_headers(token)).json()
        page_two = client_with_db.get(
            "/api/v1/documents?skip=2&limit=2", headers=_headers(token)
        ).json()

        assert page_one["total"] == 3
        assert [doc["file_name"] for doc in page_one["documents"]] == [
            "doc-2.pdf",
            "doc-1.pdf",
        ]
        assert [doc["file_name"] for doc in page_two["documents"]] == ["doc-0.pdf"]

    def test_all_four_roles_may_list(
        self, client_with_db, db_session, create_test_token, seed_test_user
    ):
        """Reading is the one thing every role — including VIEWER — can do."""
        for index, role in enumerate(["admin", "reviewer", "uploader", "viewer"]):
            email = f"{role}@list.docextract.ai"
            user = seed_test_user(email, roles=[role], org_slug=f"role-org-{index}")
            _seed_document(
                db_session, org_id=user.organization_id, uploaded_by=user.id, name=f"{role}-doc.pdf"
            )
            token = create_test_token(email)

            response = client_with_db.get("/api/v1/documents", headers=_headers(token))

            assert response.status_code == 200
            assert response.json()["total"] >= 1

    def test_rejects_unauthenticated_requests(self, client_with_db):
        """No Authorization header → the 401 envelope, not a document list."""
        response = client_with_db.get("/api/v1/documents")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"

    def test_clamps_invalid_pagination(self, client_with_db, create_test_token, seed_test_user):
        """limit=0 / limit>100 / skip=-1 fail validation with 422."""
        seed_test_user("clamp@list.docextract.ai", roles=["viewer"], org_slug="clamp-org")
        token = create_test_token("clamp@list.docextract.ai")

        for bad_query in ["limit=0", "limit=101", "skip=-1"]:
            response = client_with_db.get(f"/api/v1/documents?{bad_query}", headers=_headers(token))
            assert response.status_code == 422, bad_query
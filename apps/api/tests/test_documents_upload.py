# docextract-ai/apps/api/tests/test_documents_upload.py

"""End-to-end upload contract tests through the real FastAPI stack.

``client_with_db`` plus ``storage_override`` run the genuine request path
— auth dependency, services, database session — against
``FakeStorageProvider``, so every outcome below is the real logic on a
bucket we control. Each test seeds its own users, mints its own tokens,
and rolls back its own rows: no shared state, no order dependence.
"""

import pytest

from app.storage.factory import get_storage
from tests.fakes import FakeStorageProvider
from tests.test_file_validation import build_pdf

pytestmark = [pytest.mark.usefixtures("storage_override")]


def _headers(token: str) -> dict[str, str]:
    """Authorization header carrying a minted JWT."""
    return {"Authorization": f"Bearer {token}"}


class _Flow:
    """Minimal two-step runner so multi-request tests stay readable."""

    def __init__(self, client_with_db, create_test_token, seed_test_user) -> None:
        self.client = client_with_db
        self.create_test_token = create_test_token
        self.seed_test_user = seed_test_user

    def run(
        self,
        pdf: bytes,
        email: str,
        org_slug: str = "dup-org",
        claim_size: int | None = None,
        upload: bool = True,
    ) -> object:
        """Upload-url, optionally PUT to the fake bucket, confirm; return the confirm response."""
        self.seed_test_user(email, roles=["uploader"], org_slug=org_slug)
        token = self.create_test_token(email)
        url_resp = self.client.post(
            "/api/v1/documents/upload-url",
            json={
                "file_name": "doc.pdf",
                "content_type": "application/pdf",
                "size_bytes": len(pdf),
            },
            headers=_headers(token),
        ).json()
        provider: FakeStorageProvider = self.client.app.dependency_overrides[get_storage]()
        if upload:
            provider.put_object(url_resp["storage_path"], pdf, "application/pdf")
        return self.client.post(
            "/api/v1/documents",
            json={
                "document_id": url_resp["document_id"],
                "storage_path": url_resp["storage_path"],
                "file_name": "doc.pdf",
                "content_type": "application/pdf",
                "size_bytes": claim_size if claim_size is not None else len(pdf),
            },
            headers=_headers(token),
        )


class TestUploadUrlEndpoint:
    """POST /documents/upload-url: step one of the contract."""

    def test_happy_path_200(self, client_with_db, create_test_token, seed_test_user) -> None:
        """A valid request gets every contract field back."""
        seed_test_user("u1@t.dev", roles=["uploader"])
        resp = client_with_db.post(
            "/api/v1/documents/upload-url",
            json={
                "file_name": "invoice.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
            headers=_headers(create_test_token("u1@t.dev")),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert set(body) == {
            "document_id",
            "upload_url",
            "upload_method",
            "upload_headers",
            "storage_path",
            "max_size_bytes",
            "expires_in_seconds",
        }
        assert body["upload_method"] == "PUT"
        assert body["upload_headers"] == {"Content-Type": "application/pdf"}
        assert body["storage_path"].endswith(".pdf")
        assert body["max_size_bytes"] == 10 * 1024 * 1024

    def test_wrong_content_type_415(
        self, client_with_db, create_test_token, seed_test_user
    ) -> None:
        """Only application/pdf is intake; a PNG declaration is refused."""
        seed_test_user("u2@t.dev", roles=["uploader"])
        resp = client_with_db.post(
            "/api/v1/documents/upload-url",
            json={"file_name": "a.png", "content_type": "image/png", "size_bytes": 10},
            headers=_headers(create_test_token("u2@t.dev")),
        )
        assert resp.status_code == 415
        assert resp.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    def test_oversize_413(self, client_with_db, create_test_token, seed_test_user) -> None:
        """A size claim above the limit is refused before a URL exists."""
        seed_test_user("u3@t.dev", roles=["uploader"])
        resp = client_with_db.post(
            "/api/v1/documents/upload-url",
            json={
                "file_name": "big.pdf",
                "content_type": "application/pdf",
                "size_bytes": 10 * 1024 * 1024 + 1,
            },
            headers=_headers(create_test_token("u3@t.dev")),
        )
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "FILE_TOO_LARGE"

    def test_viewer_role_403(self, client_with_db, create_test_token, seed_test_user) -> None:
        """A viewer is authenticated but not authorized to intake."""
        seed_test_user("v@t.dev", roles=["viewer"])
        resp = client_with_db.post(
            "/api/v1/documents/upload-url",
            json={"file_name": "a.pdf", "content_type": "application/pdf", "size_bytes": 10},
            headers=_headers(create_test_token("v@t.dev")),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"

    def test_limit_exceeded_429(
        self, client_with_db, create_test_token, seed_test_user, monkeypatch
    ) -> None:
        """With a quota of 1 the second URL request is refused with 429."""
        from app.config import get_settings

        # Patch the cached instance, not the class: pydantic models store
        # field values on the instance, and get_settings() is lru_cached,
        # so the same object serves every request in this test.
        monkeypatch.setattr(get_settings(), "MAX_UPLOADS_PER_DAY", 1)
        seed_test_user("q@t.dev", roles=["uploader"])
        headers = _headers(create_test_token("q@t.dev"))
        first = client_with_db.post(
            "/api/v1/documents/upload-url",
            json={"file_name": "a.pdf", "content_type": "application/pdf", "size_bytes": 10},
            headers=headers,
        )
        second = client_with_db.post(
            "/api/v1/documents/upload-url",
            json={"file_name": "b.pdf", "content_type": "application/pdf", "size_bytes": 10},
            headers=headers,
        )
        assert first.status_code == 200
        assert second.status_code == 429
        assert second.json()["error"]["code"] == "RATE_LIMITED"


class TestConfirmEndpoint:
    """POST /documents: step two of the contract."""

    def test_happy_path_201(self, client_with_db, create_test_token, seed_test_user) -> None:
        """A completed upload becomes a documents row in state uploaded."""
        flow = _Flow(client_with_db, create_test_token, seed_test_user)
        resp = flow.run(build_pdf(1), email="c1@t.dev", org_slug="confirm-org")
        assert resp.status_code == 201
        body = resp.json()
        assert body["document"]["status"] == "uploaded"
        assert body["document"]["page_count"] == 1
        assert body["document"]["sha256"] is not None
        assert body["duplicate_of_document_id"] is None

    def test_missing_object_404(self, client_with_db, create_test_token, seed_test_user) -> None:
        """Confirming a path with no stored object is 404, not 500."""
        flow = _Flow(client_with_db, create_test_token, seed_test_user)
        resp = flow.run(build_pdf(1), email="c2@t.dev", org_slug="absent-org", upload=False)
        # No put_object: the client never actually uploaded, so
        # verify_file returns None and the service answers 404.
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"

    def test_bad_magic_bytes_415(self, client_with_db, create_test_token, seed_test_user) -> None:
        """Bytes that are not a PDF are rejected by content, not claim."""
        flow = _Flow(client_with_db, create_test_token, seed_test_user)
        resp = flow.run(
            b"not a pdf at all, just text pretending", email="c3@t.dev", org_slug="badmagic-org"
        )
        assert resp.status_code == 415
        assert resp.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    def test_wrong_org_path_403(self, client_with_db, create_test_token, seed_test_user) -> None:
        """A storage_path outside the caller's org namespace is 403."""
        pdf = build_pdf(1)
        seed_test_user("c4@t.dev", roles=["uploader"], org_slug="foreign-org")
        token = create_test_token("c4@t.dev")
        # A confirm whose storage_path claims an org namespace that is
        # not the caller's: the ownership check refuses before any
        # object is even looked up.
        foreign_path = "00000000-0000-0000-0000-000000000000/abcdef.pdf"
        resp = client_with_db.post(
            "/api/v1/documents",
            json={
                "document_id": "abcdef00-0000-0000-0000-000000000000",
                "storage_path": foreign_path,
                "file_name": "doc.pdf",
                "content_type": "application/pdf",
                "size_bytes": len(pdf),
            },
            headers=_headers(token),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"


class TestDuplicateDetection:
    """The sha256 duplicate warning across two uploads."""

    def test_second_upload_warns(self, client_with_db, create_test_token, seed_test_user) -> None:
        """Same bytes twice in one org: the second confirm warns via id."""
        flow = _Flow(client_with_db, create_test_token, seed_test_user)
        pdf = build_pdf(1)
        first = flow.run(pdf, email="d1@t.dev", org_slug="dup-org")
        second = flow.run(pdf, email="d2@t.dev", org_slug="dup-org")
        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["duplicate_of_document_id"] is None
        assert second.json()["duplicate_of_document_id"] == first.json()["document"]["id"]


class TestSizeMismatch:
    """409 STORAGE_VERIFICATION_FAILED when claim and backend disagree."""

    def test_size_mismatch_409(self, client_with_db, create_test_token, seed_test_user) -> None:
        """A claim of 10 bytes against a real PDF stored is rejected."""
        flow = _Flow(client_with_db, create_test_token, seed_test_user)
        pdf = build_pdf(1)
        resp = flow.run(pdf, email="m@t.dev", org_slug="mismatch-org", claim_size=10)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "STORAGE_VERIFICATION_FAILED"
        assert resp.json()["error"]["details"] == {"expected": 10, "stored": len(pdf)}

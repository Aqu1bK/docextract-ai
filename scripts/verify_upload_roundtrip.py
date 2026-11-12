"""Live upload round-trip against REAL Supabase Storage (opt-in).

CI never runs this: it executes only when STORAGE_LIVE_TEST=1 AND real
Supabase credentials exist in the environment; otherwise it prints the
skip reason and exits 0 so it can sit in a Makefile target or docs
without ever breaking a credential-free run.

When it does run, it walks the exact two-step contract with no storage
override — the real provider, the real bucket — and then cleans up after
itself: the object is deleted from the bucket and the documents row is
removed, so the live check leaves no residue.
"""

import io
import os
import sys
import time
import uuid

import httpx
import jwt
import structlog
from pypdf import PdfWriter
from sqlalchemy import delete

# Allow "python scripts/verify_upload_roundtrip.py" from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from app.config import get_settings  # noqa: E402
from app.db.models import Document  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from tests.fakes import FakeStorageProvider  # noqa: E402  (never used when live)

from fastapi.testclient import TestClient  # noqa: E402


def _skip_reason() -> str | None:
    """Return why the live run must be skipped, or None if it may run."""
    if os.environ.get("STORAGE_LIVE_TEST") != "1":
        return "STORAGE_LIVE_TEST is not '1' (opt-in flag missing)"
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        return "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not configured"
    return None


def _mint_token(email: str) -> str:
    """Mint a token exactly like tests/conftest.create_test_token."""
    settings = get_settings()
    now = int(time.time())
    claims = {
        "email": email,
        "iat": now,
        "exp": now + 300,
        "iss": settings.jwt_issuer,
    }
    return jwt.encode(claims, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


def _build_pdf() -> bytes:
    """Build a one-page PDF: the smallest honest document to upload."""
    writer = PdfWriter()
    writer.add_blank_page(width=200.0, height=200.0)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def main() -> int:
    """Run the live round-trip, or print the skip reason and exit 0."""
    reason = _skip_reason()
    if reason is not None:
        print(f"SKIP: {reason}")
        return 0

    settings = get_settings()
    structlog.configure()
    email = "uploader@demo.docextract.ai"
    pdf = _build_pdf()
    headers = {"Authorization": f"Bearer {_mint_token(email)}"}

    with TestClient(app) as client:
        # Step one: the signed URL.
        url_resp = client.post(
            f"{settings.API_V1_STR}/documents/upload-url",
            json={
                "file_name": "round-trip.pdf",
                "content_type": "application/pdf",
                "size_bytes": len(pdf),
            },
            headers=headers,
        )
        url_resp.raise_for_status()
        signed = url_resp.json()
        print(f"upload-url: 200, method={signed['upload_method']}, path={signed['storage_path']}")

        # The client's upload, replayed exactly as the contract specifies.
        upload_headers = {k: v for k, v in signed["upload_headers"].items()}
        upload = httpx.request(
            signed["upload_method"], signed["upload_url"], content=pdf, headers=upload_headers
        )
        upload.raise_for_status()
        print(f"client PUT: {upload.status_code} to real Supabase Storage")

        # Step two: confirm, then read the record.
        confirm = client.post(
            f"{settings.API_V1_STR}/documents",
            json={
                "document_id": signed["document_id"],
                "storage_path": signed["storage_path"],
                "file_name": "round-trip.pdf",
                "content_type": "application/pdf",
                "size_bytes": len(pdf),
            },
            headers=headers,
        )
        confirm.raise_for_status()
        body = confirm.json()
        assert confirm.status_code == 201
        assert body["document"]["status"] == "uploaded"
        assert body["document"]["page_count"] == 1
        print(f"confirm: 201, status={body['document']['status']}, pages=1")

        # Cleanup: no residue in bucket or table.
        from app.storage.factory import get_storage

        storage = get_storage()
        storage.delete_file(signed["storage_path"])
        document_id = uuid.UUID(body["document"]["id"])
        with SessionLocal() as session:
            session.execute(delete(Document).where(Document.id == document_id))
            session.commit()
        print("cleanup: object deleted, documents row removed")

    print("PASS: live upload round-trip complete (signed URL -> PUT -> confirm -> 201)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
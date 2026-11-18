"""Live export round-trip against REAL Supabase Storage (opt-in).

CI never runs this: it executes only when EXPORT_LIVE_TEST=1 AND real
Supabase credentials exist in the environment; otherwise it prints the
skip reason and exits 0 so it can sit in a Makefile target or docs
without ever breaking a credential-free run. The skip check runs before
ANY app import because the app's Settings load at import time.

When it does run, it walks the full Phase 8 governance path with no
storage override — seed a document and fields, review (correct, accept,
reject) and approve through the real endpoints, export to JSON, then
download the export from storage and verify its structure. Cleanup
removes the export object and the seeded rows, so the live check
leaves no residue.
"""

import os
import sys

# Allow "python scripts/verify_export_roundtrip.py" from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

EMAIL = "reviewer@roundtrip.docextract.ai"


def _skip_reason() -> str | None:
    """Return why the live run must be skipped, or None if it may run."""
    if os.environ.get("EXPORT_LIVE_TEST") != "1":
        return "EXPORT_LIVE_TEST is not '1' (opt-in flag missing)"
    if not os.environ.get("SUPABASE_URL") or not os.environ.get(
        "SUPABASE_SERVICE_ROLE_KEY"
    ):
        return "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not configured"
    return None


def main() -> int:
    """Run the live export round-trip, or print the skip reason and exit 0."""
    reason = _skip_reason()
    if reason is not None:
        print(f"SKIP: {reason}")
        return 0

    # Heavy imports live inside main() so the skip path never touches the
    # app (whose Settings demand a configured environment at import time).
    import decimal
    import json
    import time
    import uuid

    import jwt
    import structlog
    from app.config import get_settings
    from app.db.models import (
        AuditLog,
        Document,
        Export,
        ExtractedField,
        ExtractionJob,
        Organization,
        ReviewAction,
        Role,
        User,
        UserRole,
    )
    from app.db.session import SessionLocal
    from app.domain.enums import DocumentStatus, FieldReviewStatus, JobStatus
    from app.main import app
    from app.storage.factory import get_storage
    from fastapi.testclient import TestClient
    from sqlalchemy import delete, select

    settings = get_settings()

    def mint_token(email: str) -> str:
        """Mint a token exactly like tests/conftest.create_test_token."""
        now = int(time.time())
        claims = {
            "email": email,
            "iat": now,
            "exp": now + 300,
            "iss": settings.jwt_issuer,
        }
        return jwt.encode(claims, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

    def seed(db) -> tuple[Document, list[ExtractedField]]:
        """Seed org/role/user/job/document plus three fields directly."""
        org = Organization(
            name="Export Round-Trip Org",
            slug=f"roundtrip-{uuid.uuid4().hex[:8]}",
            settings_json={},
        )
        db.add(org)
        db.flush()

        role = db.execute(
            select(Role).where(Role.name == "reviewer")
        ).scalar_one_or_none()
        if role is None:
            role = Role(name="reviewer", description="Round-trip")
            db.add(role)
            db.flush()

        user = User(
            organization_id=org.id,
            email=EMAIL,
            full_name="Round-Trip Reviewer",
            is_active=True,
        )
        db.add(user)
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.flush()

        document = Document(
            organization_id=org.id,
            uploaded_by=user.id,
            file_name="round-trip-invoice.pdf",
            content_type="application/pdf",
            sha256=uuid.uuid4().hex,
            size_bytes=1024,
            page_count=1,
            storage_path=f"{org.id}/{uuid.uuid4()}.pdf",
            status=DocumentStatus.NEEDS_REVIEW,
            parsing_mode="text",
        )
        db.add(document)
        db.flush()

        job = ExtractionJob(
            organization_id=org.id,
            document_id=document.id,
            idempotency_key=f"rt-{uuid.uuid4().hex[:12]}",
            status=JobStatus.SUCCEEDED,
            mode="mock",
            pipeline_version="1.0.0",
            schema_version="1.0.0",
        )
        db.add(job)
        db.flush()

        fields = [
            ExtractedField(
                organization_id=org.id,
                document_id=document.id,
                job_id=job.id,
                field_key="invoice_total",
                field_label="Invoice Total",
                value_text="1250.00",
                confidence=decimal.Decimal("0.4200"),
                source="mock",
                page_number=1,
                review_status=FieldReviewStatus.PENDING,
                is_required=True,
            ),
            ExtractedField(
                organization_id=org.id,
                document_id=document.id,
                job_id=job.id,
                field_key="invoice_number",
                field_label="Invoice Number",
                value_text="INV-RT-001",
                confidence=decimal.Decimal("0.9800"),
                source="mock",
                page_number=1,
                review_status=FieldReviewStatus.PENDING,
                is_required=True,
            ),
            ExtractedField(
                organization_id=org.id,
                document_id=document.id,
                job_id=job.id,
                field_key="vendor_note",
                field_label="Vendor Note",
                value_text="Payable within 30 days",
                confidence=decimal.Decimal("0.4100"),
                source="mock",
                page_number=1,
                review_status=FieldReviewStatus.PENDING,
                is_required=False,
            ),
        ]
        db.add_all(fields)
        db.flush()
        db.commit()
        return document, fields

    def cleanup(db, document: Document) -> None:
        """Remove every seeded row plus the export object from the bucket."""
        db.execute(delete(ReviewAction).where(ReviewAction.document_id == document.id))
        db.execute(delete(AuditLog).where(AuditLog.entity_id == str(document.id)))
        db.execute(
            delete(ExtractedField).where(ExtractedField.document_id == document.id)
        )
        db.execute(
            delete(ExtractionJob).where(ExtractionJob.document_id == document.id)
        )
        db.execute(delete(Export).where(Export.document_id == document.id))
        db.execute(delete(Document).where(Document.id == document.id))
        db.commit()

    structlog.configure()
    with SessionLocal() as db:
        document, fields = seed(db)
        headers = {"Authorization": f"Bearer {mint_token(EMAIL)}"}
        api = settings.API_V1_STR

        with TestClient(app) as client:
            try:
                # Review: correct, accept, reject — the full human pass.
                correct = client.patch(
                    f"{api}/review/fields/{fields[0].id}",
                    json={"value": "1299.00", "reason": "OCR misread"},
                    headers=headers,
                )
                correct.raise_for_status()
                accepted = client.post(
                    f"{api}/review/fields/{fields[1].id}/accept", headers=headers
                )
                accepted.raise_for_status()
                rejected = client.post(
                    f"{api}/review/fields/{fields[2].id}/reject",
                    json={"reason": "not applicable"},
                    headers=headers,
                )
                rejected.raise_for_status()
                print("review: corrected + accepted + rejected (200s)")

                approved = client.post(
                    f"{api}/review/documents/{document.id}/approve", headers=headers
                )
                approved.raise_for_status()
                assert approved.json()["status"] == "approved"
                print("approve: 200, status=approved")

                exported = client.post(
                    f"{api}/exports/documents/{document.id}/export",
                    json={"format": "json"},
                    headers=headers,
                )
                exported.raise_for_status()
                body = exported.json()
                assert body["status"] == "completed"
                assert body["row_count"] == 2
                print(
                    f"export: 201, path={body['storage_path']}, rows={body['row_count']}"
                )

                # Download from real storage and verify structure.
                payload_bytes = get_storage().download_file(body["storage_path"])
                payload = json.loads(payload_bytes)
                assert payload["document_id"] == str(document.id)
                assert payload["extraction_mode"] == settings.EXTRACTION_MODE
                assert {f["field_key"] for f in payload["fields"]} == {
                    "invoice_total",
                    "invoice_number",
                }
                assert payload["fields"][0]["original_value_text"] == "1250.00"
                print(
                    "verify: structure ok "
                    f"(mode={payload['extraction_mode']}, fields={len(payload['fields'])})"
                )

                get_storage().delete_file(body["storage_path"])
                print("cleanup: export object deleted")
            finally:
                cleanup(db, document)
                print("cleanup: database rows removed")

    print(
        "PASS: live export round-trip complete "
        "(review -> approve -> export -> download -> verify -> cleanup)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
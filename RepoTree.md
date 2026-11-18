docextract-ai/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # 4-job gate: secrets scan, ruff, mypy, pytest
│   │   └── .gitkeep
│   ├── COMMIT_CONVENTION.md
│   ├── CONTRIBUTING.md
│   └── PULL_REQUEST_TEMPLATE.md
├── apps/
│   ├── api/
│   │   ├── alembic/
│   │   │   ├── versions/
│   │   │   │   └── 0001_initial_schema.py   # full schema (incl. review/audit/export tables) — no new migrations in Phases 7–8
│   │   │   ├── env.py
│   │   │   └── script.py.mako
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   └── v1/
│   │   │   │       ├── endpoints/
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   ├── auth.py        # (Phase 4) GET /auth/me
│   │   │   │       │   ├── documents.py   # (Phase 5) POST /documents/upload-url + POST /documents; (Phase 7) document/extraction result reads
│   │   │   │       │   ├── export.py      # NEW (Phase 8): create export (JSON/CSV) + list document exports — prefix /exports
│   │   │   │       │   ├── health.py
│   │   │   │       │   └── review.py      # NEW (Phase 8): list fields + correct/accept/reject field + approve/reject document — prefix /review
│   │   │   │       ├── __init__.py
│   │   │   │       └── router.py         # mounts /auth + /documents (Phases 4–7) + /review + /exports (Phase 8)
│   │   │   ├── auth/                    # (Phase 4) JWT validation + RBAC dependencies
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dependencies.py      # get_current_user, require_roles, load_role_names
│   │   │   │   └── jwt_validator.py     # validate_supabase_jwt (HS256 + iss + exp)
│   │   │   ├── db/
│   │   │   │   ├── models/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── core.py
│   │   │   │   │   ├── documents.py     # documents table + processing/review status machine
│   │   │   │   │   ├── extraction.py    # extracted_fields / extracted_tables rows (incl. review_status, original_value_text)
│   │   │   │   │   └── governance.py    # audit_logs (append-only), review_actions, exports
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── seed.py
│   │   │   │   └── session.py
│   │   │   ├── domain/
│   │   │   │   ├── __init__.py
│   │   │   │   └── enums.py             # domain enums incl. FieldReviewStatus (pending/accepted/corrected/rejected/missing)
│   │   │   ├── extraction/              # (Phase 6) the provider seam — pure library, no FastAPI/DB/queue
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py             # ExtractionProvider ABC (one async method)
│   │   │   │   ├── confidence.py        # calculate_confidence: source quality × evidence/validation penalties, required-field floor
│   │   │   │   ├── factory.py           # get_extraction_provider: mock|light_parser from EXTRACTION_MODE
│   │   │   │   ├── light_parser_provider.py  # pypdf text extraction, regex fields, keyword doc-type classifier
│   │   │   │   └── mock_provider.py    # seeded deterministic invoice fixture
│   │   │   ├── schemas/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── audit.py             # NEW (Phase 8): audit-log read models
│   │   │   │   ├── documents.py         # (Phase 5) UploadUrl*/ConfirmUpload*/DocumentOut models
│   │   │   │   ├── export.py            # NEW (Phase 8): ExportCreate (JSON/CSV) + ExportOut (status, URL, expires_at)
│   │   │   │   ├── extraction.py       # (Phase 6): DocumentTypePrediction, ExtractedField, ExtractedTable, ExtractionResult; SOURCES/DOCUMENT_TYPES vocabularies
│   │   │   │   └── review.py            # NEW (Phase 8): field-review + document-approval request/response models
│   │   │   ├── services/                 # business logic layer
│   │   │   │   ├── __init__.py
│   │   │   │   ├── approval.py          # NEW (Phase 8): check_approval_eligibility, approve_document, reject_document
│   │   │   │   ├── audit.py             # NEW (Phase 8): write_audit_log — append-only, no update/delete path
│   │   │   │   ├── documents.py         # (Phase 5) request_upload_url + confirm_upload → (Phase 7) hands off to pipeline
│   │   │   │   ├── export.py            # NEW (Phase 8): generate_export (accepted/corrected fields only; expires_at = now + RETENTION_DAYS), list_document_exports, failure write-back
│   │   │   │   ├── file_validation.py  # magic bytes, encryption, page count (pure)
│   │   │   │   ├── pipeline.py          # (Phase 7) Postgres-backed queue (ADR-004): claim FOR UPDATE SKIP LOCKED → run provider → persist fields/tables + confidence → low-confidence review routing
│   │   │   │   ├── review.py            # NEW (Phase 8): list_document_fields, correct_field (original_value_text preserved), accept_field, reject_field — SELECT ... FOR UPDATE
│   │   │   │   └── usage.py             # row-locked daily quota (FOR UPDATE)
│   │   │   ├── storage/                 # provider abstraction
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py              # StorageProvider ABC + SignedUpload/StorageObjectMeta
│   │   │   │   ├── factory.py           # get_storage: supabase|minio from STORAGE_PROVIDER
│   │   │   │   ├── minio_provider.py   # Local Docker backend (minio SDK 7.2.20)
│   │   │   │   └── supabase_provider.py # hosted demo backend (storage3 2.34.1)
│   │   │   ├── __init__.py
│   │   │   ├── config.py               # EXTRACTION_MODE (Phase 6); CONFIDENCE_THRESHOLD + RETENTION_DAYS consumed by Phases 7–8
│   │   │   ├── errors.py                # + EXTRACTION_PROVIDER_FAILED, CONFIDENCE_SCORING_FAILED (Phase 6); + APPROVAL_BLOCKED 409 ApprovalBlockedException (Phase 8)
│   │   │   ├── logging_config.py
│   │   │   ├── main.py
│   │   │   └── middleware.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py              # app/client + JWT-role fixtures, storage_override; EXTRACTION_MODE=mock drives pipeline/review tests (Phases 7–8)
│   │   │   ├── fakes.py                 # (Phase 5) FakeStorageProvider
│   │   │   ├── test_approval_logic.py   # NEW (Phase 8): 5 tests — eligibility, low-confidence pending → 409 APPROVAL_BLOCKED, required-field block, approve, reject
│   │   │   ├── test_audit_trail.py      # NEW (Phase 8): 3 tests — review actions logged, append-only immutability, audit trail query
│   │   │   ├── test_auth.py             # (Phase 4) 10 auth/RBAC tests
│   │   │   ├── test_confidence.py       # (Phase 6) 13 confidence-arithmetic tests
│   │   │   ├── test_documents_upload.py # (Phase 5) 11 end-to-end contract tests
│   │   │   ├── test_error_format.py
│   │   │   ├── test_export.py           # NEW (Phase 8): 6 tests — JSON, CSV, accepted/corrected-only, expires_at (+RETENTION_DAYS), list, failure write-back
│   │   │   ├── test_file_validation.py # (Phase 5) 7 pure validation tests
│   │   │   ├── test_health.py
│   │   │   ├── test_light_parser.py    # (Phase 6) 13 tests, builds real text-bearing PDFs with pypdf
│   │   │   ├── test_mock_provider.py   # (Phase 6) 10 determinism/fixture tests
│   │   │   ├── test_pipeline.py         # (Phase 7) queue claim, status transitions, field persistence, low-confidence routing
│   │   │   ├── test_review_fields.py    # NEW (Phase 8): 7 tests — list, correct+original preserved, accept, reject, RBAC write-gate, concurrent edit lock, status transitions
│   │   │   ├── test_schema.py
│   │   │   ├── test_seed.py
│   │   │   └── test_usage_limits.py    # (Phase 5) 5 quota tests
│   │   ├── alembic.ini
│   │   └── pyproject.toml              # no dependency changes through Phase 8 (export uses stdlib json/csv)
│   └── web/
│       └── .gitkeep
├── docker/
│   └── .gitkeep                        # Phase 10 (Local Docker Mode) stack lands here
├── docs/
│   ├── adr/
│   │   ├── ADR-001-public-demo-uses-mock-mode.md
│   │   ├── ADR-002-local-docker-uses-real-vision-llm.md
│   │   ├── ADR-003-use-pypdf-instead-of-pymupdf.md
│   │   └── ADR-004-postgres-queue-instead-of-redis.md
│   ├── architecture.md
│   ├── demo-mode-explanation.md
│   ├── local-docker-mode-explanation.md
│   ├── phase-plan.md                   # Phase 08 Review/Approval/Audit/Export → **Complete** (Phases 01–08 all Complete)
│   └── product-contract.md
├── scripts/
│   ├── init_project.ps1
│   ├── init_project.sh
│   ├── verify_export_roundtrip.py      # NEW (Phase 8): end-to-end upload → extract → review → approve → export round-trip with content checks
│   └── verify_upload_roundtrip.py      # (Phase 5) opt-in live Supabase round-trip
├── .editorconfig
├── .env.example                        # unchanged through Phase 8 (EXTRACTION_MODE, CONFIDENCE_THRESHOLD, RETENTION_DAYS predate Phase 6)
├── .gitignore
├── LICENSE
├── Makefile
└── README.md
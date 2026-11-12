docextract-ai/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # 4-job gate: secrets scan, ruff, mypy, pytest (+ auth env in Phase 4)
│   │   └── .gitkeep
│   ├── COMMIT_CONVENTION.md
│   ├── CONTRIBUTING.md
│   └── PULL_REQUEST_TEMPLATE.md
├── apps/
│   ├── api/
│   │   ├── alembic/
│   │   │   ├── versions/
│   │   │   │   └── 0001_initial_schema.py
│   │   │   ├── env.py
│   │   │   └── script.py.mako
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   └── v1/
│   │   │   │       ├── endpoints/
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   ├── auth.py          # NEW (Phase 4): GET /auth/me
│   │   │   │       │   ├── documents.py      # NEW (Phase 5): POST /documents/upload-url + POST /documents
│   │   │   │       │   └── health.py
│   │   │   │       ├── __init__.py
│   │   │   │       └── router.py           # mounts /auth + /documents routers
│   │   │   ├── auth/                          # NEW (Phase 4): JWT validation + RBAC dependencies
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dependencies.py          # get_current_user, require_roles, load_role_names
│   │   │   │   └── jwt_validator.py         # validate_supabase_jwt (HS256 + iss + exp)
│   │   │   ├── db/
│   │   │   │   ├── models/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── core.py
│   │   │   │   │   ├── documents.py
│   │   │   │   │   ├── extraction.py
│   │   │   │   │   └── governance.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── seed.py
│   │   │   │   └── session.py
│   │   │   ├── domain/
│   │   │   │   ├── __init__.py
│   │   │   │   └── enums.py
│   │   │   ├── schemas/                      # NEW (Phase 5): wire contract, no ORM imports
│   │   │   │   ├── __init__.py
│   │   │   │   └── documents.py            # UploadUrl*/ConfirmUpload*/DocumentOut models
│   │   │   ├── services/                     # NEW (Phase 5): business logic layer
│   │   │   │   ├── __init__.py
│   │   │   │   ├── documents.py            # request_upload_url + confirm_upload
│   │   │   │   ├── file_validation.py      # magic bytes, encryption, page count (pure)
│   │   │   │   └── usage.py                # row-locked daily quota (FOR UPDATE)
│   │   │   ├── storage/                      # NEW (Phase 5): provider abstraction
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py                 # StorageProvider ABC + SignedUpload/StorageObjectMeta
│   │   │   │   ├── factory.py              # get_storage: supabase|minio from STORAGE_PROVIDER
│   │   │   │   ├── minio_provider.py       # Local Docker backend (minio SDK 7.2.20)
│   │   │   │   └── supabase_provider.py    # hosted demo backend (storage3 2.34.1)
│   │   │   ├── __init__.py
│   │   │   ├── config.py                 # + STORAGE_*, MINIO_*, MAX_UPLOADS_PER_DAY
│   │   │   ├── errors.py                  # + FILE_TOO_LARGE, UNSUPPORTED_FILE_TYPE, ENCRYPTED_PDF, PAGE_LIMIT_EXCEEDED, STORAGE_VERIFICATION_FAILED
│   │   │   ├── logging_config.py
│   │   │   ├── main.py
│   │   │   └── middleware.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py              # + storage_override (FakeStorageProvider wiring)
│   │   │   ├── fakes.py                 # NEW (Phase 5): FakeStorageProvider
│   │   │   ├── test_auth.py             # NEW (Phase 4): 10 auth/RBAC tests
│   │   │   ├── test_documents_upload.py # NEW (Phase 5): 11 end-to-end contract tests
│   │   │   ├── test_error_format.py
│   │   │   ├── test_file_validation.py  # NEW (Phase 5): 7 pure validation tests
│   │   │   ├── test_health.py
│   │   │   ├── test_schema.py
│   │   │   ├── test_seed.py
│   │   │   └── test_usage_limits.py     # NEW (Phase 5): 5 quota tests
│   │   ├── alembic.ini
│   │   └── pyproject.toml               # + PyJWT, pypdf, storage3, minio
│   └── web/
│       └── .gitkeep
├── docker/
│   └── .gitkeep
├── docs/
│   ├── adr/
│   │   ├── ADR-001-public-demo-uses-mock-mode.md
│   │   ├── ADR-002-local-docker-uses-real-vision-llm.md
│   │   ├── ADR-003-use-pypdf-instead-of-pymupdf.md
│   │   └── ADR-004-postgres-queue-instead-of-redis.md
│   ├── architecture.md
│   ├── demo-mode-explanation.md
│   ├── local-docker-mode-explanation.md
│   ├── phase-plan.md                   # Phase 05 → **Complete**
│   └── product-contract.md
├── scripts/
│   ├── init_project.ps1
│   ├── init_project.sh
│   └── verify_upload_roundtrip.py       # NEW (Phase 5): opt-in live Supabase round-trip
├── .editorconfig
├── .env.example                        # + MAX_UPLOADS_PER_DAY
├── .gitignore
├── LICENSE
├── Makefile
└── README.md
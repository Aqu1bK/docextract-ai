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
│   │   │   │   └── 0001_initial_schema.py
│   │   │   ├── env.py
│   │   │   └── script.py.mako
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   └── v1/
│   │   │   │       ├── endpoints/
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   ├── auth.py        # (Phase 4) GET /auth/me
│   │   │   │       │   ├── documents.py   # (Phase 5) POST /documents/upload-url + POST /documents
│   │   │   │       │   └── health.py
│   │   │   │       ├── __init__.py
│   │   │   │       └── router.py         # mounts /auth + /documents routers
│   │   │   ├── auth/                    # (Phase 4) JWT validation + RBAC dependencies
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dependencies.py      # get_current_user, require_roles, load_role_names
│   │   │   │   └── jwt_validator.py     # validate_supabase_jwt (HS256 + iss + exp)
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
│   │   │   ├── extraction/               # NEW (Phase 6): the provider seam — pure library, no FastAPI/DB/queue
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py             # ExtractionProvider ABC (one async method)
│   │   │   │   ├── confidence.py        # calculate_confidence: source quality × evidence/validation penalties, required-field floor
│   │   │   │   ├── factory.py           # get_extraction_provider: mock|light_parser from EXTRACTION_MODE
│   │   │   │   ├── light_parser_provider.py  # pypdf text extraction, regex fields, keyword doc-type classifier
│   │   │   │   └── mock_provider.py    # seeded deterministic invoice fixture
│   │   │   ├── schemas/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── documents.py         # (Phase 5) UploadUrl*/ConfirmUpload*/DocumentOut models
│   │   │   │   └── extraction.py       # NEW (Phase 6): DocumentTypePrediction, ExtractedField, ExtractedTable, ExtractionResult; SOURCES/DOCUMENT_TYPES vocabularies
│   │   │   ├── services/                 # (Phase 5) business logic layer
│   │   │   │   ├── __init__.py
│   │   │   │   ├── documents.py         # request_upload_url + confirm_upload
│   │   │   │   ├── file_validation.py  # magic bytes, encryption, page count (pure)
│   │   │   │   └── usage.py             # row-locked daily quota (FOR UPDATE)
│   │   │   ├── storage/                 # (Phase 5) provider abstraction
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py              # StorageProvider ABC + SignedUpload/StorageObjectMeta
│   │   │   │   ├── factory.py           # get_storage: supabase|minio from STORAGE_PROVIDER
│   │   │   │   ├── minio_provider.py   # Local Docker backend (minio SDK 7.2.20)
│   │   │   │   └── supabase_provider.py # hosted demo backend (storage3 2.34.1)
│   │   │   ├── __init__.py
│   │   │   ├── config.py               # + EXTRACTION_MODE (Phase 6; reads pre-existing .env key)
│   │   │   ├── errors.py                # + EXTRACTION_PROVIDER_FAILED, CONFIDENCE_SCORING_FAILED (Phase 6)
│   │   │   ├── logging_config.py
│   │   │   ├── main.py
│   │   │   └── middleware.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py              # + storage_override (FakeStorageProvider wiring)
│   │   │   ├── fakes.py                 # (Phase 5) FakeStorageProvider
│   │   │   ├── test_auth.py             # (Phase 4) 10 auth/RBAC tests
│   │   │   ├── test_confidence.py       # NEW (Phase 6): 13 confidence-arithmetic tests
│   │   │   ├── test_documents_upload.py # (Phase 5) 11 end-to-end contract tests
│   │   │   ├── test_error_format.py
│   │   │   ├── test_file_validation.py # (Phase 5) 7 pure validation tests
│   │   │   ├── test_health.py
│   │   │   ├── test_light_parser.py    # NEW (Phase 6): 13 tests, builds real text-bearing PDFs with pypdf
│   │   │   ├── test_mock_provider.py   # NEW (Phase 6): 10 determinism/fixture tests
│   │   │   ├── test_schema.py
│   │   │   ├── test_seed.py
│   │   │   └── test_usage_limits.py    # (Phase 5) 5 quota tests
│   │   ├── alembic.ini
│   │   └── pyproject.toml              # unchanged in Phase 6 (pypdf already present since Phase 5)
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
│   ├── phase-plan.md                   # Phase 06 Extraction Engine → **Complete**
│   └── product-contract.md
├── scripts/
│   ├── init_project.ps1
│   ├── init_project.sh
│   └── verify_upload_roundtrip.py      # (Phase 5) opt-in live Supabase round-trip
├── .editorconfig
├── .env.example                        # unchanged in Phase 6 (EXTRACTION_MODE/CONFIDENCE_THRESHOLD predate it)
├── .gitignore
├── LICENSE
├── Makefile
└── README.md
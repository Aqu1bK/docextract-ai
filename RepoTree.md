docextract-ai/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # 4-job parallel gate: secrets scan, ruff, mypy, pytest (postgres:16 service)
│   │   └── .gitkeep
│   ├── COMMIT_CONVENTION.md
│   ├── CONTRIBUTING.md
│   └── PULL_REQUEST_TEMPLATE.md
├── apps/
│   ├── api/
│   │   ├── alembic/
│   │   │   ├── versions/
│   │   │   │   └── 0001_initial_schema.py   # still the single migration — full schema incl. extraction_jobs queue (Phase 7) + review/audit/export tables (Phase 8)
│   │   │   ├── env.py
│   │   │   └── script.py.mako
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   └── v1/
│   │   │   │       ├── endpoints/
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   ├── auth.py        # (Phase 4) GET /auth/me
│   │   │   │       │   ├── documents.py   # (Phase 5) POST /documents/upload-url + POST /documents (confirm → document PENDING; does not itself enqueue a job — see services/jobs.py)
│   │   │   │       │   ├── export.py      # (Phase 8) create export (JSON/CSV) + list document exports — prefix /exports
│   │   │   │       │   ├── extraction.py   # NEW (Phase 7) GET /documents/{document_id}/extraction-status — document status + latest job row for polling clients
│   │   │   │       │   ├── health.py
│   │   │   │       │   └── review.py      # (Phase 8) list fields + correct/accept/reject field + approve/reject document — prefix /review
│   │   │   │       ├── __init__.py
│   │   │   │       └── router.py         # mounts /auth + /documents (Phases 4–5) + /extraction (Phase 7) + /review + /exports (Phase 8)
│   │   │   ├── auth/                    # (Phase 4) JWT validation + RBAC dependencies
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dependencies.py      # get_current_user, require_roles, load_role_names
│   │   │   │   └── jwt_validator.py     # validate_supabase_jwt (HS256 + iss + exp)
│   │   │   ├── db/
│   │   │   │   ├── models/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── core.py
│   │   │   │   │   ├── documents.py     # documents table + processing/review status machine
│   │   │   │   │   ├── extraction.py    # extracted_fields / extracted_tables rows (review_status, original_value_text) + ExtractionJob (extraction_jobs queue: lease, attempts, failure codes) — Phase 7
│   │   │   │   │   └── governance.py    # audit_logs (append-only), review_actions, exports
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── seed.py
│   │   │   │   └── session.py
│   │   │   ├── domain/
│   │   │   │   ├── __init__.py
│   │   │   │   └── enums.py             # domain enums incl. JobStatus (Phase 7) + FieldReviewStatus (pending/accepted/corrected/rejected/missing, Phase 8)
│   │   │   ├── extraction/              # (Phase 6) the provider seam — pure library, no FastAPI/DB/queue
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py             # ExtractionProvider ABC (one async method)
│   │   │   │   ├── confidence.py        # calculate_confidence: source quality × evidence/validation penalties, required-field floor
│   │   │   │   ├── factory.py           # get_extraction_provider: mock|light_parser from EXTRACTION_MODE
│   │   │   │   ├── light_parser_provider.py  # pypdf text extraction, regex fields, keyword doc-type classifier
│   │   │   │   └── mock_provider.py    # seeded deterministic invoice fixture
│   │   │   ├── schemas/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── audit.py             # (Phase 8) audit-log read models
│   │   │   │   ├── documents.py         # (Phase 5) UploadUrl*/ConfirmUpload*/DocumentOut models
│   │   │   │   ├── export.py            # (Phase 8) ExportCreate (JSON/CSV) + ExportOut (status, URL, expires_at)
│   │   │   │   ├── extraction.py        # (Phase 6) DocumentTypePrediction, ExtractedField, ExtractedTable, ExtractionResult; SOURCES/DOCUMENT_TYPES vocabularies
│   │   │   │   ├── jobs.py              # NEW (Phase 7) ExtractionJobOut + ExtractionStatusResponse — the queue's wire contract (operator internals stay off the wire)
│   │   │   │   └── review.py            # (Phase 8) field-review + document-approval request/response models
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── approval.py          # (Phase 8) check_approval_eligibility, approve_document, reject_document
│   │   │   │   ├── audit.py             # (Phase 8) write_audit_log — append-only, no update/delete path
│   │   │   │   ├── documents.py         # (Phase 5) request_upload_url + confirm_upload
│   │   │   │   ├── export.py            # (Phase 8) generate_export (accepted/corrected fields only; expires_at = now + RETENTION_DAYS), list_document_exports, failure write-back
│   │   │   │   ├── file_validation.py   # magic bytes, encryption, page count (pure)
│   │   │   │   ├── jobs.py              # NEW (Phase 7) create_extraction_job — idempotent enqueue: unique (document_id, idempotency_key), IntegrityError race → return existing row (not yet invoked from any endpoint; exercised by test_job_creation)
│   │   │   │   ├── review.py            # (Phase 8) list_document_fields, correct_field (original_value_text preserved), accept_field, reject_field — SELECT ... FOR UPDATE
│   │   │   │   └── usage.py             # row-locked daily quota (FOR UPDATE)
│   │   │   ├── storage/                 # (Phase 5) provider abstraction
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py              # StorageProvider ABC + SignedUpload/StorageObjectMeta
│   │   │   │   ├── factory.py           # get_storage: supabase|minio from STORAGE_PROVIDER
│   │   │   │   ├── minio_provider.py   # Local Docker backend (minio SDK 7.2.20)
│   │   │   │   └── supabase_provider.py # hosted demo backend (storage3 2.34.1)
│   │   │   ├── workers/                 # NEW (Phase 7) standalone queue consumer — `python -m app.workers.runner`; imports nothing from FastAPI (ADR-004: the queue is the only integration point)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── job_processor.py    # the unit of work: a claimed LEASED job → SUCCEEDED or raise
│   │   │   │   ├── persistence.py      # ExtractionResult → typed field/table rows + confidence
│   │   │   │   ├── retry.py            # error classification → backoff retry or dead-letter FAILED
│   │   │   │   └── runner.py           # the boring main loop: claim → process → commit → sleep WORKER_POLL_SECONDS
│   │   │   ├── __init__.py
│   │   │   ├── config.py               # EXTRACTION_MODE (Phase 6); CONFIDENCE_THRESHOLD + RETENTION_DAYS (Phases 7–8); WORKER_ENABLED / WORKER_POLL_SECONDS / WORKER_ID (Phase 7)
│   │   │   ├── errors.py               # + ExtractionProvider/Confidence exceptions (6); + JobAlreadyExists/JobNotFound (7); + APPROVAL_BLOCKED 409 ApprovalBlockedException (8)
│   │   │   ├── logging_config.py
│   │   │   ├── main.py
│   │   │   └── middleware.py
│   │   ├── tests/                       # 141 tests across 19 modules (postgres:16-backed)
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py              # app/client + JWT-role fixtures + storage override; job/document/3-fields seeding helper (Phases 7–8)
│   │   │   ├── fakes.py                 # (Phase 5) FakeStorageProvider
│   │   │   ├── test_approval_logic.py   # (Phase 8) 7 tests — eligibility, low-confidence pending → 409, required-field block, approve, reject
│   │   │   ├── test_audit_trail.py      # (Phase 8) 5 tests — review actions logged, append-only immutability, audit trail query
│   │   │   ├── test_auth.py             # (Phase 4) 10 auth/RBAC tests
│   │   │   ├── test_confidence.py       # (Phase 6) 13 confidence-arithmetic tests
│   │   │   ├── test_documents_upload.py # (Phase 5) 11 end-to-end contract tests
│   │   │   ├── test_error_format.py    # 2 tests
│   │   │   ├── test_export.py           # (Phase 8) 8 tests — JSON, CSV, accepted/corrected-only, expires_at (+RETENTION_DAYS), list, failure write-back
│   │   │   ├── test_file_validation.py  # (Phase 5) 7 pure validation tests
│   │   │   ├── test_health.py           # 2 tests
│   │   │   ├── test_job_creation.py     # NEW (Phase 7) 5 tests — fresh insert, active-job idempotent return, IntegrityError race
│   │   │   ├── test_light_parser.py    # (Phase 6) 13 tests, builds real text-bearing PDFs with pypdf
│   │   │   ├── test_mock_provider.py   # (Phase 6) 10 determinism/fixture tests
│   │   │   ├── test_retry_policy.py    # NEW (Phase 7) 12 tests — classification, backoff, dead-lettering
│   │   │   ├── test_review_fields.py    # (Phase 8) 8 tests — list, correct+original preserved, accept, reject, RBAC write-gate, concurrent edit lock, status transitions
│   │   │   ├── test_schema.py           # 9 tests
│   │   │   ├── test_seed.py             # 5 tests
│   │   │   ├── test_usage_limits.py    # (Phase 5) 5 quota tests
│   │   │   ├── test_worker.py           # NEW (Phase 7) 7 tests — claim, process, persist, status transitions
│   │   │   └── test_worker_concurrency.py # NEW (Phase 7) 2 tests — SKIP LOCKED claiming
│   │   ├── alembic.ini
│   │   └── pyproject.toml              # no new runtime deps through Phase 9A (worker reuses sqlalchemy/structlog; export uses stdlib json/csv)
│   └── web/                             # NEW (Phase 9A) — Next.js 16 + React 19 + Tailwind v4 scaffold, Ink-on-Paper design system, app shell; business screens arrive in 9B
│       ├── app/
│       │   ├── (app)/
│       │   │   ├── dashboard/page.tsx   # placeholder overview — 9B documents module
│       │   │   └── layout.tsx           # authenticated route group — wraps children in AppShell (9B adds the auth guard here)
│       │   ├── (auth)/
│       │   │   └── login/page.tsx       # placeholder sign-in card — 9B Supabase Auth
│       │   ├── globals.css              # the design system: @theme tokens (ink/paper/rule/accent, confidence + status scales, radius 0/2/4, font bindings) — no tailwind.config.js exists
│       │   ├── layout.tsx               # root layout — Inter/JetBrains Mono CSS variables + theme-light on <html>
│       │   └── page.tsx                 # "/" owns no screen — redirect('/login')
│       ├── components/
│       │   ├── layout/
│       │   │   ├── __tests__/
│       │   │   │   ├── demo-mode-banner.test.tsx  # 2 tests — hidden when off, exact copy when on
│       │   │   │   └── sidebar.test.tsx           # 3 tests — nav renders, collapse, expand
│       │   │   ├── app-shell.tsx       # the frame: banner → sidebar + topbar → scrolling content (h-dvh, min-h-0, max-w-[1400px] column)
│       │   │   ├── demo-mode-banner.tsx  # 32px conditional strip (env.demoMode) + expandable explanation — honesty as a design feature
│       │   │   ├── nav-items.ts        # app-wide nav definition (6 destinations; `current` is static until 9B derives it from the route)
│       │   │   ├── sidebar.tsx         # 240px rail collapsing via CSS xl: variants (no JavaScript width switching — no flash), accent active marker
│       │   │   └── topbar.tsx          # 56px chrome — title prop (route data, not chrome data) + signed-in user placeholder
│       │   └── ui/
│       │       ├── badge.tsx           # variants = the domain model: confidence-high/mid/low (font-mono) + status-* mapping FieldReviewStatus
│       │       └── button.tsx          # shadcn-style, asChild via @radix-ui/react-slot, radius forced to rounded-none
│       ├── lib/
│       │   ├── env.ts                 # Zod-validated NEXT_PUBLIC_* — fail-fast at module load; typed env incl. demoMode
│       │   ├── fonts.ts               # Inter + JetBrains Mono via next/font (self-hosted, CSS variables, no runtime Google request)
│       │   └── utils.ts               # cn() = clsx + tailwind-merge
│       ├── .gitkeep                    # kept from the Phase 1 scaffold
│       ├── .prettierignore             # ignores components/ui (shadcn CLI-owned) + build artifacts
│       ├── .prettierrc
│       ├── components.json             # shadcn manifest — Tailwind v4 token mode (config: ""), tokens read from globals.css
│       ├── eslint.config.mjs           # ESLint 9 flat config on eslint-config-next's native flat exports (no FlatCompat)
│       ├── next-env.d.ts               # generated by Next 16
│       ├── next.config.ts              # empty — 9B adds API proxy rewrites
│       ├── package.json                # 9 scripts (dev --turbopack, build, start, lint, format, typecheck, test, test:watch); deps: next 16, react 19, zod, cva, lucide, @radix-ui/react-slot
│       ├── package-lock.json
│       ├── postcss.config.mjs          # @tailwindcss/postcss — without it every utility silently no-ops
│       ├── tsconfig.json               # strict, @/* → ./* alias
│       ├── vitest-setup/index.ts       # jest-dom matchers + jsdom matchMedia mock
│       └── vitest.config.ts            # jsdom, globals: true (RTL auto-cleanup engages), @ alias, setup file
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
│   ├── phase-2.5-ci-gate.md            # (Phase 2.5) CI gate learning note
│   ├── phase-03-database.md            # (Phase 3) database learning note
│   ├── phase-04-auth.md                # (Phase 4) auth learning note
│   ├── phase-05-storage-upload.md      # (Phase 5) storage/upload learning note
│   ├── phase-plan.md                   # Phase 09 In Progress (Phases 01–08 Complete; 10–11 Not Started)
│   └── product-contract.md
├── scripts/
│   ├── init_project.ps1
│   ├── init_project.sh
│   ├── verify_export_roundtrip.py      # (Phase 8) opt-in live round-trip (EXPORT_LIVE_TEST=1 + Supabase env)
│   └── verify_upload_roundtrip.py      # (Phase 5) opt-in live Supabase round-trip
├── .editorconfig
├── .env.example                        # FRONTEND section defines the four NEXT_PUBLIC_* values apps/web/lib/env.ts validates
├── .gitignore                          # + .vercel / .turbo / *.tsbuildinfo / coverage/ (Phase 9A)
├── LICENSE
├── Makefile                            # install now also runs `cd apps/web && npm install`; dual-end lint/format/typecheck/test; + dev-web, test-e2e, seed-demo, reset-demo, docker-up/down/clean
└── README.md
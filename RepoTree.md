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
│   │   │   │       │   ├── documents.py   # (Phase 5) POST /documents/upload-url + POST /documents (confirm → document PENDING) + NEW (9B) GET /documents — list, org-scoped, paginated, all four roles may read
│   │   │   │       │   ├── export.py      # (Phase 8) create export (JSON/CSV) + list document exports — prefix /exports
│   │   │   │       │   ├── extraction.py   # (Phase 7) GET /documents/{document_id}/extraction-status — document status + latest job row for polling clients
│   │   │   │       │   ├── health.py
│   │   │   │       │   └── review.py      # (Phase 8) list fields + correct/accept/reject field + approve/reject document — prefix /review
│   │   │   │       ├── __init__.py
│   │   │   │       └── router.py         # mounts /auth + /documents (Phases 4–5, 9B read) + /extraction (Phase 7) + /review + /exports (Phase 8)
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
│   │   │   │   ├── documents.py          # (Phase 5) UploadUrl*/ConfirmUpload*/DocumentOut models
│   │   │   │   ├── documents_list.py    # NEW (9B) DocumentsListQuery (skip ≥ 0, limit 1–100 clamp) + DocumentsListOut (documents + total, reuses DocumentOut)
│   │   │   │   ├── export.py            # (Phase 8) ExportCreate (JSON/CSV) + ExportOut (status, URL, expires_at)
│   │   │   │   ├── extraction.py        # (Phase 6) DocumentTypePrediction, ExtractedField, ExtractedTable, ExtractionResult; SOURCES/DOCUMENT_TYPES vocabularies
│   │   │   │   ├── jobs.py              # (Phase 7) ExtractionJobOut + ExtractionStatusResponse — the queue's wire contract
│   │   │   │   └── review.py            # (Phase 8) field-review + document-approval request/response models
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── approval.py          # (Phase 8) check_approval_eligibility, approve_document, reject_document
│   │   │   │   ├── audit.py             # (Phase 8) write_audit_log — append-only, no update/delete path
│   │   │   │   ├── documents.py         # (Phase 5) request_upload_url + confirm_upload
│   │   │   │   ├── documents_list.py    # NEW (9B) list_documents — org-scoped WHERE, count + page in one transaction, created_at DESC id DESC
│   │   │   │   ├── export.py            # (Phase 8) generate_export (accepted/corrected fields only; expires_at = now + RETENTION_DAYS), list_document_exports, failure write-back
│   │   │   │   ├── file_validation.py   # magic bytes, encryption, page count (pure)
│   │   │   │   ├── jobs.py              # (Phase 7) create_extraction_job — idempotent enqueue: unique (document_id, idempotency_key), IntegrityError race → return existing row
│   │   │   │   ├── review.py            # (Phase 8) list_document_fields, correct_field (original_value_text preserved), accept_field, reject_field — SELECT ... FOR UPDATE
│   │   │   │   └── usage.py             # row-locked daily quota (FOR UPDATE)
│   │   │   ├── storage/                 # (Phase 5) provider abstraction
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py              # StorageProvider ABC + SignedUpload/StorageObjectMeta
│   │   │   │   ├── factory.py           # get_storage: supabase|minio from STORAGE_PROVIDER
│   │   │   │   ├── minio_provider.py   # Local Docker backend (minio SDK 7.2.20)
│   │   │   │   └── supabase_provider.py # hosted demo backend (storage3 2.34.1)
│   │   │   ├── workers/                 # (Phase 7) standalone queue consumer — `python -m app.workers.runner`; imports nothing from FastAPI (ADR-004: the queue is the only integration point)
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
│   │   ├── tests/                       # 146 tests across 20 modules (postgres:16-backed)
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py              # app/client + JWT-role fixtures + storage override; job/document/3-fields seeding helper (Phases 7–8)
│   │   │   ├── fakes.py                 # (Phase 5) FakeStorageProvider
│   │   │   ├── test_approval_logic.py   # (Phase 8) 7 tests — eligibility, low-confidence pending → 409, required-field block, approve, reject
│   │   │   ├── test_audit_trail.py      # (Phase 8) 5 tests — review actions logged, append-only immutability, audit trail query
│   │   │   ├── test_auth.py             # (Phase 4) 10 auth/RBAC tests
│   │   │   ├── test_confidence.py       # (Phase 6) 13 confidence-arithmetic tests
│   │   │   ├── test_documents_list.py   # NEW (9B) 5 tests — org scoping, newest-first paging (distinct timestamps), all-four-roles read, 401 envelope, 422 pagination clamps
│   │   │   ├── test_documents_upload.py # (Phase 5) 11 end-to-end contract tests
│   │   │   ├── test_error_format.py    # 2 tests
│   │   │   ├── test_export.py          # (Phase 8) 8 tests — JSON, CSV, accepted/corrected-only, expires_at (+RETENTION_DAYS), list, failure write-back
│   │   │   ├── test_file_validation.py  # (Phase 5) 7 pure validation tests
│   │   │   ├── test_health.py           # 2 tests
│   │   │   ├── test_job_creation.py     # (Phase 7) 5 tests — fresh insert, active-job idempotent return, IntegrityError race
│   │   │   ├── test_light_parser.py    # (Phase 6) 13 tests, builds real text-bearing PDFs with pypdf
│   │   │   ├── test_mock_provider.py   # (Phase 6) 10 determinism/fixture tests
│   │   │   ├── test_retry_policy.py    # (Phase 7) 12 tests — classification, backoff, dead-lettering
│   │   │   ├── test_review_fields.py    # (Phase 8) 8 tests — list, correct+original preserved, accept, reject, RBAC write-gate, concurrent edit lock, status transitions
│   │   │   ├── test_schema.py           # 9 tests
│   │   │   ├── test_seed.py             # 5 tests
│   │   │   ├── test_usage_limits.py    # (Phase 5) 5 quota tests
│   │   │   ├── test_worker.py           # (Phase 7) 7 tests — claim, process, persist, status transitions
│   │   │   └── test_worker_concurrency.py # (Phase 7) 2 tests — SKIP LOCKED claiming
│   │   ├── alembic.ini
│   │   └── pyproject.toml              # no new runtime deps through 9B (the 9B read surface reuses sqlalchemy/pydantic)
│   └── web/                             # (Phase 9A scaffold) — Next.js 16 + React 19 + Tailwind v4, Ink-on-Paper design system; 9B wires auth, the documents register, and upload; 9C adds review/exports/audit screens
│       ├── app/
│       │   ├── (app)/
│       │   │   ├── dashboard/page.tsx   # placeholder overview — 9C replaces with real stats
│       │   │   ├── documents/page.tsx  # NEW (9B) server page (metadata) around DocumentsView
│       │   │   ├── upload/page.tsx     # NEW (9B) server page (metadata) around UploadView
│       │   │   └── layout.tsx           # (9B) the auth guard: requireUser() + fetchCurrentUserRoles() → AppShell with email + roles props
│       │   ├── (auth)/
│       │   │   ├── auth/callback/route.ts # NEW (9B) exchangeCodeForSession(code) → forward; failure → /login?authError=… (never a dead page)
│       │   │   └── login/page.tsx      # (9B) server wrapper + Suspense boundary around the real LoginForm
│       │   ├── globals.css              # the design system: @theme tokens (ink/paper/rule/accent, confidence + status scales, radius 0/2/4, font bindings) — no tailwind.config.js exists
│       │   ├── layout.tsx               # root layout — fonts + (9B) <Providers> (TanStack Query) + <Toaster> (sonner, square/hairline-styled)
│       │   └── page.tsx                 # (9B) root redirect by real auth state: signed in → /dashboard, signed out → /login (server-side check)
│       ├── components/
│       │   ├── auth/
│       │   │   ├── __tests__/
│       │   │   │   └── login.test.tsx     # NEW (9B) 3 tests
│       │   │   └── login-form.tsx      # NEW (9B) email/password form + 4 one-click demo buttons; toasts via sonner
│       │   ├── documents/
│       │   │   ├── __tests__/
│       │   │   │   └── documents-table.test.tsx # NEW (9B) 4 tests — rows+badges, empty→Upload, error+retry, pagination edge buttons
│       │   │   ├── document-row.tsx    # NEW (9B) one register row: mono filename/size/timestamp, status badge + square dot; formatBytes/formatTimestamp/statusMeta
│       │   │   ├── documents-table.tsx # NEW (9B) skeleton (row-shaped), error + retry, empty state, skip/limit pagination
│       │   │   └── documents-view.tsx  # NEW (9B) client half — owns skip state, hands query data/status to the table
│       │   ├── layout/
│       │   │   ├── __tests__/
│       │   │   │   ├── demo-mode-banner.test.tsx  # 2 tests — hidden when off, exact copy when on
│       │   │   │   └── sidebar.test.tsx           # 5 tests — nav renders, session footer, collapse, expand (updated in 9B for props)
│       │   │   ├── app-shell.tsx       # (9B) the frame — now threads userEmail/userRoles to Sidebar + Topbar
│       │   │   ├── demo-mode-banner.tsx  # 32px conditional strip (env.demoMode) + expandable explanation — honesty as a design feature
│       │   │   ├── nav-items.ts        # app-wide nav definition (6 destinations); sidebar derives `current` from the real pathname since 9B
│       │   │   ├── sidebar.tsx         # (9B) 240px→64px CSS rail + real session footer (initials square, email, first role); active item from usePathname
│       │   │   └── topbar.tsx          # (9B) 56px chrome — title prop + real Radix DropdownMenu user menu (email · role) with working sign-out
│       │   ├── providers.tsx           # NEW (9B) QueryClientProvider — one QueryClient per browser session (useState lazy init), 60s staleTime
│       │   ├── ui/
│       │   │   ├── badge.tsx           # variants = the domain model: confidence-high/mid/low (font-mono) + status-* mapping FieldReviewStatus
│       │   │   ├── button.tsx          # shadcn-style, asChild via @radix-ui/react-slot, radius forced to rounded-none
│       │   │   ├── card.tsx            # NEW (9B) shadcn primitive
│       │   │   ├── dropdown-menu.tsx   # NEW (9B) shadcn/Radix primitive — the topbar user menu
│       │   │   ├── input.tsx           # NEW (9B) shadcn primitive — login form fields
│       │   │   ├── label.tsx           # NEW (9B) shadcn primitive
│       │   │   ├── progress.tsx        # NEW (9B) shadcn primitive — upload coarse progress
│       │   │   ├── separator.tsx       # NEW (9B) shadcn primitive
│       │   │   └── table.tsx           # NEW (9B) shadcn primitive — the documents register
│       │   └── upload/
│       │       ├── __tests__/
│       │       │   └── dropzone.test.tsx # NEW (9B) 3 tests
│       │       ├── dropzone.tsx        # NEW (9B) react-dropzone wrapper: PDF-only, ≤10 MB client-side (mirrors backend), rejection reasons listed
│       │       └── upload-view.tsx     # NEW (9B) coarse 3-step progress (minted → in-flight → confirmed), file card, outcome toasts, success → /documents
│       ├── lib/
│       │   ├── api.ts                  # NEW (9B) typed API client — fetchWithAuth (bearer from session, error envelope → ApiError), documents + upload calls
│       │   ├── auth-client.ts          # NEW (9B) browser auth actions (signInWithPassword/signOut/getUser) + DEMO_ACCOUNTS
│       │   ├── auth.ts                 # NEW (9B) server-side: getCurrentUser/requireUser (redirect guard)/fetchCurrentUserRoles (GET /auth/me)
│       │   ├── env.ts                  # Zod-validated NEXT_PUBLIC_* — fail-fast; (9B) SUPABASE_URL + ANON_KEY tightened to required
│       │   ├── fonts.ts                # Inter + JetBrains Mono via next/font (self-hosted, CSS variables, no runtime Google request)
│       │   ├── queries.ts              # NEW (9B) useDocuments (keyed by page) + useUploadDocument (mint → PUT → confirm as one mutation; invalidates ['documents'])
│       │   ├── supabase-browser.ts    # NEW (9B) createBrowserClient singleton (lazy + cached) — the only cookie client from the tab's side
│       │   ├── supabase-server.ts     # NEW (9B) server-component client; setAll try/catch (render can't set cookies; middleware refreshes instead)
│       │   └── utils.ts                # cn() = clsx + tailwind-merge
│       ├── .gitkeep                    # kept from the Phase 1 scaffold
│       ├── .prettierignore             # ignores components/ui (shadcn CLI-owned) + build artifacts
│       ├── .prettierrc
│       ├── components.json             # shadcn manifest — Tailwind v4 token mode (config: ""), tokens read from globals.css
│       ├── eslint.config.mjs           # ESLint 9 flat config on eslint-config-next's native flat exports (no FlatCompat)
│       ├── middleware.ts               # NEW (9B) session refresh (getUser, cookies ride back on supabaseResponse) + guard for the six (app) routes
│       ├── next-env.d.ts               # generated by Next 16
│       ├── next.config.ts              # still empty — API calls go direct to NEXT_PUBLIC_API_URL
│       ├── package.json                # 8 scripts; +10 deps in 9B (@supabase/ssr, @supabase/supabase-js, @tanstack/react-query, react-dropzone, sonner, @radix-ui pieces)
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
├── Makefile                            # install also runs `cd apps/web && npm install`; dual-end lint/format/typecheck/test; + dev-web, test-e2e, seed-demo, reset-demo, docker-up/down/clean
└── README.md
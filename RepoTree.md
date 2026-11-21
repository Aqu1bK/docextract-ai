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
│   │   │   │       │   ├── audit.py      # NEW (9C) GET /audit/documents/{id}/logs — org-scoped through the document (foreign doc = 404), newest-first, all four roles read
│   │   │   │       │   ├── documents.py   # (Phase 5) upload-url + confirm; (9B) GET /documents list; NEW (9C) GET /documents/{id} detail + GET /documents/{id}/download — streams source PDF (Content-Disposition: inline) for the review pane
│   │   │   │       │   ├── export.py      # (Phase 8) create export + list; NEW (9C) GET /documents/{id}/exports/{id}/download — completed exports only, attachment + export filename
│   │   │   │       │   ├── extraction.py   # (Phase 7) GET /documents/{document_id}/extraction-status — document status + latest job row for polling clients
│   │   │   │       │   ├── health.py
│   │   │   │       │   └── review.py      # (Phase 8) list fields + correct/accept/reject field + approve/reject document — prefix /review
│   │   │   │       ├── __init__.py
│   │   │   │       └── router.py         # mounts /auth + /documents + /extraction (Phase 7) + /review + /exports (Phase 8) + NEW (9C) /audit
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
│   │   │   │   ├── audit.py             # (Phase 8) audit-log read models — 9C's timeline renders AuditLogOut rows
│   │   │   │   ├── documents.py          # (Phase 5) UploadUrl*/ConfirmUpload*/DocumentOut models
│   │   │   │   ├── documents_list.py    # (9B) DocumentsListQuery (skip ≥ 0, limit 1–100 clamp) + DocumentsListOut (documents + total, reuses DocumentOut)
│   │   │   │   ├── export.py            # (Phase 8) ExportCreate (JSON/CSV) + ExportOut (status, row_count, expires_at) — 9C's export rows
│   │   │   │   ├── extraction.py        # (Phase 6) DocumentTypePrediction, ExtractedField, ExtractedTable, ExtractionResult; SOURCES/DOCUMENT_TYPES vocabularies
│   │   │   │   ├── jobs.py              # (Phase 7) ExtractionJobOut + ExtractionStatusResponse — the queue's wire contract (9C Job tab polls it)
│   │   │   │   └── review.py            # (Phase 8) field-review + document-approval request/response models
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── approval.py          # (Phase 8) check_approval_eligibility, approve_document, reject_document — the 409 blockers the 9C panel previews
│   │   │   │   ├── audit.py             # (Phase 8) write_audit_log — append-only, no update/delete path (9C's audit router is read-only)
│   │   │   │   ├── documents.py         # (Phase 5) request_upload_url + confirm_upload
│   │   │   │   ├── documents_list.py    # (9B) list_documents — org-scoped WHERE, count + page in one transaction, created_at DESC id DESC
│   │   │   │   ├── export.py            # (Phase 8) generate_export (accepted/corrected fields only; expires_at = now + RETENTION_DAYS), list_document_exports, failure write-back
│   │   │   │   ├── file_validation.py   # magic bytes, encryption, page count (pure)
│   │   │   │   ├── jobs.py              # (Phase 7) create_extraction_job — idempotent enqueue
│   │   │   │   ├── review.py            # (Phase 8) list_document_fields, correct_field (original_value_text preserved), accept_field, reject_field — SELECT ... FOR UPDATE
│   │   │   │   └── usage.py             # row-locked daily quota (FOR UPDATE)
│   │   │   ├── storage/                 # (Phase 5) provider abstraction
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py              # StorageProvider ABC + SignedUpload/StorageObjectMeta — four operations, deliberately no signed read URL (why 9C downloads stream as bytes)
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
│   │   │   ├── config.py               # EXTRACTION_MODE (Phase 6); CONFIDENCE_THRESHOLD + RETENTION_DAYS (Phases 7–8); WORKER_* (Phase 7)
│   │   │   ├── errors.py               # + ExtractionProvider/Confidence exceptions (6); + Job* (7); + APPROVAL_BLOCKED 409 ApprovalBlockedException (8) — 9C's client throws ApiError from these envelopes
│   │   │   ├── logging_config.py
│   │   │   ├── main.py
│   │   │   └── middleware.py
│   │   ├── tests/                       # 152 tests across 21 modules (postgres:16-backed)
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py              # app/client + JWT-role fixtures + storage override; job/document/3-fields seeding helper (Phases 7–8)
│   │   │   ├── fakes.py                 # (Phase 5) FakeStorageProvider
│   │   │   ├── test_approval_logic.py   # (Phase 8) 7 tests — eligibility, low-confidence pending → 409, required-field block, approve, reject
│   │   │   ├── test_audit_trail.py      # (Phase 8) 5 tests — review actions logged, append-only immutability, audit trail query
│   │   │   ├── test_auth.py             # (Phase 4) 10 auth/RBAC tests
│   │   │   ├── test_confidence.py       # (Phase 6) 13 confidence-arithmetic tests
│   │   │   ├── test_documents_list.py   # (9B) 5 tests — org scoping, newest-first paging (distinct timestamps), all-four-roles read, 401 envelope, 422 pagination clamps
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
│   │   │   ├── test_review_surface.py  # NEW (9C) 6 tests — document detail read, source download, audit list, export download bytes + headers, org scoping, 401 envelope
│   │   │   ├── test_schema.py           # 9 tests
│   │   │   ├── test_seed.py             # 5 tests
│   │   │   ├── test_usage_limits.py    # (Phase 5) 5 quota tests
│   │   │   ├── test_worker.py           # (Phase 7) 7 tests — claim, process, persist, status transitions
│   │   │   └── test_worker_concurrency.py # (Phase 7) 2 tests — SKIP LOCKED claiming
│   │   ├── alembic.ini
│   │   └── pyproject.toml              # no new runtime deps in 9C (the read surface reuses sqlalchemy/pydantic)
│   └── web/                             # Next.js 16 + React 19 + Tailwind v4, Ink-on-Paper design system; 9B wired auth + register + upload; 9C adds the full review screen (fields/audit/export/job tabs + PDF pane)
│       ├── app/
│       │   ├── (app)/
│       │   │   ├── dashboard/page.tsx   # placeholder overview — 9C keeps it honest: real review-queue stats belong to a later phase
│       │   │   ├── documents/
│       │   │   │   ├── [id]/
│       │   │   │   │   ├── error.tsx    # NEW (9C) route-segment error boundary — client component, reset + route back to the register
│       │   │   │   │   ├── loading.tsx  # NEW (9C) route-segment skeleton in the real two-column shape (PDF pane + field rows)
│       │   │   │   │   └── page.tsx     # NEW (9C) server shell — metadata + await params (Next 16 dynamic-params-as-Promise) around DocumentDetailView
│       │   │   │   └── page.tsx        # (9B) server page around DocumentsView
│       │   │   ├── upload/page.tsx     # (9B) server page around UploadView
│       │   │   └── layout.tsx           # the auth guard: requireUser() + fetchCurrentUserRoles() → AppShell with email + roles props
│       │   ├── (auth)/
│       │   │   ├── auth/callback/route.ts # (9B) exchangeCodeForSession(code) → forward; failure → /login?authError=…
│       │   │   └── login/page.tsx      # (9B) server wrapper + Suspense boundary around the real LoginForm
│       │   ├── globals.css              # the design system: @theme tokens (ink/paper/rule/accent, confidence + status scales, radius 0/2/4, font bindings) — no tailwind.config.js exists
│       │   ├── layout.tsx               # root layout — fonts + <Providers> (TanStack Query) + <Toaster> (sonner, square/hairline-styled)
│       │   └── page.tsx                 # (9B) root redirect by real auth state: signed in → /dashboard, signed out → /login
│       ├── components/
│       │   ├── audit/                    # NEW in 9C
│       │   │   ├── __tests__/
│       │   │   │   └── audit-timeline.test.tsx # NEW (9C) 4 tests
│       │   │   ├── audit-event.tsx      # NEW (9C) one trail entry — square dot (ink=human, muted=system) + "field — corrected" verb title + field/reason as prose
│       │   │   └── audit-timeline.tsx  # NEW (9C) vertical rail (border-l hairline), newest first, honest empty state
│       │   ├── auth/
│       │   │   ├── __tests__/
│       │   │   │   └── login.test.tsx     # (9B) 3 tests
│       │   │   └── login-form.tsx      # (9B) email/password form + 4 one-click demo buttons; toasts via sonner
│       │   ├── documents/
│       │   │   ├── __tests__/
│       │   │   │   ├── document-detail.test.tsx # NEW (9C) 4 tests
│       │   │   │   └── documents-table.test.tsx # (9B) 4 tests
│       │   │   ├── document-detail-view.tsx # NEW (9C) the orchestrator: two-column grid (PDF left), tab strip (Fields/Audit/Export/Job), document verdict below
│       │   │   ├── document-row.tsx    # (9B) one register row — 9C makes the filename the link to /documents/{id}; nine-status badge map (two-tone rule)
│       │   │   ├── documents-table.tsx # (9B) skeleton (row-shaped), error + retry, empty state, skip/limit pagination
│       │   │   └── documents-view.tsx  # (9B) client half — owns skip state, hands query data/status to the table
│       │   ├── export/                  # NEW in 9C
│       │   │   ├── __tests__/
│       │   │   │   └── export-panel.test.tsx # NEW (9C) 5 tests — disabled-til-approved, rows, blob-URL download link, fetching state
│       │   │   ├── export-panel.tsx    # NEW (9C) Export JSON/CSV buttons (disabled until approved — honest UI for the backend's 409), past-export list
│       │   │   └── export-row.tsx      # NEW (9C) one export row — download via useExportDownloadUrl blob URL (Bearer header can't ride a plain link), fetching…/unavailable states
│       │   ├── jobs/                    # NEW in 9C
│       │   │   └── job-status-tab.tsx  # NEW (9C) document status + latest job (attempts vs ceiling, error codes) — 3s poll that returns false on terminal statuses
│       │   ├── layout/
│       │   │   ├── __tests__/
│       │   │   │   ├── demo-mode-banner.test.tsx  # 2 tests — hidden when off, exact copy when on
│       │   │   │   └── sidebar.test.tsx           # 5 tests — nav renders, session footer, collapse, expand (updated in 9B for props)
│       │   │   ├── app-shell.tsx       # (9B) the frame — threads userEmail/userRoles to Sidebar + Topbar
│       │   │   ├── demo-mode-banner.tsx  # 32px conditional strip (env.demoMode) + expandable explanation — honesty as a design feature
│       │   │   ├── nav-items.ts        # 6 destinations; 9C wiring: "Review" → /documents (the register row IS the review entry), Audit icon ScrollText
│       │   │   ├── sidebar.tsx         # (9B) 240px→64px CSS rail + real session footer; active item from usePathname
│       │   │   └── topbar.tsx          # (9B) 56px chrome — title prop + Radix DropdownMenu user menu with working sign-out
│       │   ├── pdf/                     # NEW in 9C
│       │   │   ├── pdf-toolbar.tsx     # NEW (9C) page n/N prev/next, zoom out/in clamped MIN_SCALE..MAX_SCALE
│       │   │   └── pdf-viewer.tsx      # NEW (9C) react-pdf Document/Page via next/dynamic { ssr: false }; base width 640px × scale; load-error state
│       │   ├── providers.tsx           # (9B) QueryClientProvider — one QueryClient per browser session, 60s staleTime
│       │   ├── review/                  # NEW in 9C
│       │   │   ├── __tests__/
│       │   │   │   └── field-row.test.tsx # NEW (9C) 6 tests
│       │   │   ├── correct-field-form.tsx # NEW (9C) react-hook-form inline replacement — optional reason travels to the audit trail verbatim
│       │   │   ├── document-actions.tsx # NEW (9C) document verdict — client-side blocker preview (same two conditions as the backend's 409), reject with optional reason
│       │   │   ├── field-list.tsx      # NEW (9C) owns the three field mutations + one correctingFieldId; invalidates fields/document/audit in one sweep
│       │   │   └── field-row.tsx      # NEW (9C) one field — mono value, confidence badge (≥0.9/≥0.75), status badge once decided, "machine:" provenance line, Accept/Correct/Reject
│       │   ├── ui/
│       │   │   ├── badge.tsx           # variants = the domain model: confidence-high/mid/low (font-mono) + status-* mapping FieldReviewStatus
│       │   │   ├── button.tsx          # shadcn-style, asChild via @radix-ui/react-slot, radius forced to rounded-none
│       │   │   ├── card.tsx            # (9B) shadcn primitive
│       │   │   ├── dropdown-menu.tsx   # (9B) shadcn/Radix primitive — the topbar user menu
│       │   │   ├── input.tsx           # (9B) shadcn primitive — login form fields
│       │   │   ├── label.tsx           # (9B) shadcn primitive
│       │   │   ├── progress.tsx        # (9B) shadcn primitive — upload coarse progress
│       │   │   ├── separator.tsx       # (9B) shadcn primitive
│       │   │   └── table.tsx           # (9B) shadcn primitive — the documents register
│       │   └── upload/
│       │       ├── __tests__/
│       │       │   └── dropzone.test.tsx # (9B) 3 tests
│       │       ├── dropzone.tsx        # (9B) react-dropzone wrapper: PDF-only, ≤10 MB client-side (mirrors backend), rejection reasons listed
│       │       └── upload-view.tsx     # (9B) coarse 3-step progress (minted → in-flight → confirmed), file card, outcome toasts, success → /documents
│       ├── lib/
│       │   ├── api.ts                  # (9B→9C) typed API client — fetchWithAuth (bearer, error envelope → ApiError); 9C adds review/export/audit/extraction calls + fetchBytesAsBlobUrl — the one Bearer-authenticated byte fetch both downloads share (source PDF + export files)
│       │   ├── auth-client.ts          # (9B) browser auth actions + DEMO_ACCOUNTS
│       │   ├── auth.ts                 # (9B) server-side: getCurrentUser/requireUser/fetchCurrentUserRoles
│       │   ├── env.ts                  # Zod-validated NEXT_PUBLIC_* — fail-fast; SUPABASE_URL + ANON_KEY required
│       │   ├── fonts.ts                # Inter + JetBrains Mono via next/font
│       │   ├── pdf-worker.ts          # NEW (9C) the one global pdf.js needs — workerSrc from new URL(pdf.worker.min.mjs, import.meta.url); guarded for jsdom
│       │   ├── queries.ts              # (9B→9C) useDocuments + useUploadDocument; 9C adds 13 more — detail, fields, audit, exports, extraction-status (terminal-aware poll), both download-URL queries (staleTime/gcTime Infinity), the six verdict mutations with their invalidation sweeps
│       │   ├── supabase-browser.ts    # (9B) createBrowserClient singleton
│       │   ├── supabase-server.ts     # (9B) server-component client; middleware refreshes cookies
│       │   └── utils.ts                # cn() = clsx + tailwind-merge
│       ├── .gitkeep                    # kept from the Phase 1 scaffold
│       ├── .prettierignore             # ignores components/ui + build artifacts
│       ├── .prettierrc
│       ├── components.json             # shadcn manifest — Tailwind v4 token mode
│       ├── eslint.config.mjs           # ESLint 9 flat config on eslint-config-next's native flat exports
│       ├── middleware.ts               # (9B) session refresh + guard for the six (app) routes — prefix match: '/documents' covers '/documents/[id]' (startsWith route + '/')
│       ├── next-env.d.ts               # generated by Next 16
│       ├── next.config.ts              # still empty — API calls go direct to NEXT_PUBLIC_API_URL
│       ├── package.json                # 8 scripts; 9C deps: react-pdf ^11.1.0 (pdfjs-dist 6.5.438 arrives transitively — imported directly only in pdf-worker.ts), react-hook-form ^7.64.0 (previously in upload-form, now the correct-field form)
│       ├── package-lock.json
│       ├── postcss.config.mjs          # @tailwindcss/postcss
│       ├── tsconfig.json               # strict, @/* → ./* alias
│       ├── vitest-setup/index.ts       # jest-dom matchers + jsdom matchMedia mock
│       └── vitest.config.ts            # jsdom, globals: true, @ alias, setup file — 36 tests across 9 suites (9C adds 4: document-detail, field-row, audit-timeline, export-panel)
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
│   ├── phase-plan.md                   # Phase 09 In Progress — 9A/9B/9C delivered (Phases 01–08 Complete; 10–12 Not Started)
│   └── product-contract.md
├── scripts/
│   ├── init_project.ps1
│   ├── init_project.sh
│   ├── verify_export_roundtrip.py      # (Phase 8) opt-in live round-trip
│   └── verify_upload_roundtrip.py      # (Phase 5) opt-in live Supabase round-trip
├── .editorconfig
├── .env.example                        # FRONTEND section defines the NEXT_PUBLIC_* values apps/web/lib/env.ts validates
├── .gitignore                          # + .vercel / .turbo / *.tsbuildinfo / coverage/ (Phase 9A)
├── LICENSE
├── Makefile                            # install also runs `cd apps/web && npm install`; dual-end lint/format/typecheck/test; dev-web, test-e2e, seed-demo, reset-demo, docker-up/down/clean
└── README.md
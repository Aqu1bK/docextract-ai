# DocExtract AI — Product Contract

## 1. Document Control

| Field | Value |
| --- | --- |
| Version | 1.0 |
| Date | 2026-11-07 |
| Author | Mohd Aquib Khan |
| Status | Active |

This document is the product requirements definition (PRD) for DocExtract AI. It is the source of truth for scope. Changes to scope require an update to this document and, for architectural choices, an Architecture Decision Record (ADR) in `docs/adr/`.

## 2. Executive Summary

DocExtract AI is an internal business tool that turns messy business PDFs — invoices, RFPs (requests for proposals), contracts, and bills of lading — into structured, reviewed, exportable data. It exists because manual re-typing of document fields is slow, error-prone, and leaves no audit trail. The system extracts fields and tables, scores each field's confidence, flags low-confidence results for a human reviewer, and records every action in an audit trail before the data can be exported as JSON or CSV. It ships in two operating modes from one code base: a free, deterministic, Mock Mode public demo, and a Local Docker Mode that runs real Vision LLM (large language model with image input) extraction on the operator's own machine and API key.

## 3. Problem Statement

**What pain does this solve?** Business documents arrive as PDFs, not as data. The fields inside them (invoice numbers, totals, dates, terms) must be re-entered into spreadsheets or internal systems by hand before anyone can use them.

**Who has this pain?** Small operations, finance, and procurement teams at startups and small enterprises that receive tens to hundreds of documents per week but cannot justify enterprise document-processing software. The same pain applies to any internal tool team that must demonstrate a document workflow before receiving a budget.

**What is the current manual process?** A person opens each PDF, reads the relevant fields, and types them into a spreadsheet or ERP (enterprise resource planning) system. A second person usually spot-checks the entries. Records of who entered or corrected what are informal or absent.

**What is the cost of the current process?** The cost is repeated manual labor per document, correction loops when values are mistyped, backlogs when volume spikes, and no reliable answer to "who changed this value, and when?" The project deliberately does not quote industry statistics for these costs; the qualitative cost is sufficient to justify the tool, and unverified numbers are not cited.

## 4. Target Users

| Role | Description | Key permissions |
| --- | --- | --- |
| **Admin** | Manages the system, users, and settings | List/deactivate users, view all documents and audit trails, view and retry failed jobs |
| **Reviewer** | Runs the review workflow end to end | Everything an Uploader can do, plus edit/approve/reject extractions and export approved data |
| **Uploader** | Feeds documents into the system | Upload PDFs, view and track their own documents |
| **Viewer** | Consumes approved results | Read-only access to approved documents and their extracted data |

The MVP has no self-service signup; accounts are seeded by an Admin or by a seed script (see FR-003).

## 5. User Stories

### Admin

- US-001: As an Admin, I want to log in with my email and password, so that I can access the admin area securely.
- US-002: As an Admin, I want to list users and their roles, so that I know exactly who has access to the system.
- US-003: As an Admin, I want to deactivate a user account, so that former team members lose access to business data.
- US-004: As an Admin, I want to view failed extraction jobs and retry them, so that a transient processing error does not lose a document.
- US-005: As an Admin, I want to view the audit trail across all documents, so that I can answer "who changed what, and when" questions.
- US-006: As an Admin, I want to see the currently active Extraction Provider (Mock or real), so that I always know how the data was produced.

### Reviewer

- US-007: As a Reviewer, I want to upload a PDF document, so that its data can be extracted without manual typing.
- US-008: As a Reviewer, I want a list of documents awaiting review with their statuses, so that I can work through the review queue in order.
- US-009: As a Reviewer, I want to see which extracted fields have low confidence scores, so that I only spend time on fields that actually need checking.
- US-010: As a Reviewer, I want the source PDF page displayed next to the extracted fields, so that I can verify every value against the original document.
- US-011: As a Reviewer, I want to edit an extracted field value, so that the data is correct before it is approved.
- US-012: As a Reviewer, I want to approve a reviewed document, so that its data becomes the official record and can be exported.
- US-013: As a Reviewer, I want to reject a document, so that unusable extractions never enter the approved data set.
- US-014: As a Reviewer, I want to export approved documents as JSON or CSV, so that downstream systems can load the data.
- US-015: As a Reviewer, I want to view a document's full audit history, so that I can trace every change made to its extraction.

### Uploader

- US-016: As an Uploader, I want to upload a PDF document, so that I do not have to retype its contents into other systems.
- US-017: As an Uploader, I want to see the processing status of my documents, so that I know when extraction is finished.
- US-018: As an Uploader, I want to view the extracted results of my own documents, so that I can confirm the upload was processed correctly.
- US-019: As an Uploader, I want a clear warning when my file exceeds the size or page limit, so that I can fix the file instead of wasting an upload.

### Viewer

- US-020: As a Viewer, I want to browse approved documents, so that I can look up extracted data without asking others.
- US-021: As a Viewer, I want to search and filter approved documents by type and date, so that I can find a specific document quickly.
- US-022: As a Viewer, I want extracted data in read-only mode, so that I cannot change approved data by accident.

## 6. Functional Requirements

Each requirement has a stable ID used in tests, commits, and pull requests.

### Authentication and Access Control

- FR-001: The system shall authenticate users with email and password and issue a session token (JWT — JSON Web Token) that must accompany every API request.
- FR-002: The system shall define four roles — Admin, Reviewer, Uploader, Viewer — and enforce their permissions (RBAC — role-based access control) on every API endpoint.
- FR-003: Admins shall be able to list users and deactivate accounts. The MVP has no self-service signup; accounts are created by seeding.
- FR-004: The system shall reject any API request with a missing, invalid, or expired token, except the API health check.

### Document Upload

- FR-005: Authenticated users with the Uploader, Reviewer, or Admin role shall be able to upload PDF files.
- FR-006: The system shall reject uploads larger than `MAX_UPLOAD_MB` (default 10 MB).
- FR-007: The system shall reject PDFs with more than `MAX_PAGES` (default 20) pages.
- FR-008: The system shall accept only valid PDF files and reject any other content with a clear error message.
- FR-009: The system shall store uploaded files in the configured storage provider — Supabase Storage on the hosted demo, MinIO in Local Docker Mode.
- FR-010: The system shall create a document record with status `uploaded` for every accepted file.

### Extraction Pipeline

- FR-011: The system shall enqueue an extraction job in the PostgreSQL job queue after every successful upload.
- FR-012: A worker shall poll the queue every `WORKER_POLL_SECONDS` (default 3) and claim jobs with row-level locking, so two workers never process the same job.
- FR-013: The worker shall retry a failed job up to `MAX_JOB_ATTEMPTS` (default 3) before marking it `failed`.
- FR-014: The worker shall run the Light Parser (pypdf) to extract text from native (text-based) PDF pages.
- FR-015: The system shall detect the document type: invoice, RFP, contract, bill of lading, or unknown.
- FR-016: The system shall extract the structured fields defined for the detected document type (for example invoice number, issue date, due date, total amount for invoices).
- FR-017: The system shall extract tables where present, preserving row and column structure.
- FR-018: The system shall assign every extracted field a confidence score between 0 and 1.
- FR-019: The system shall flag every field whose confidence is below `CONFIDENCE_THRESHOLD` (default 0.75) for human review.
- FR-020: In Mock Mode, the MockExtractionProvider shall return deterministic, pre-defined results: the same input always produces the same output.
- FR-021: In Mock Mode, the provider shall simulate realistic processing latency and realistic confidence values, including fields below the threshold.
- FR-022: Every extracted field shall record its source — `mock` in Mock Mode, or the provider name in real mode.
- FR-023: In real mode, the worker shall render pages to images with pdf2image + Poppler and send them to the configured Vision LLM (OpenAI or OpenAI-compatible), limited to `VISION_MAX_PAGES` (default 3) pages.
- FR-024: In real mode, the Vision LLM response shall be validated against the Pydantic schema before storage; invalid responses shall be retried and then failed.
- FR-025: The system shall track document status through the states `uploaded → queued → processing → extracted → approved | rejected`, plus `failed` for errors.

### Review Workflow

- FR-026: Reviewers shall see a document list with status and low-confidence flags.
- FR-027: Reviewers shall see the source PDF page and the extracted fields side by side.
- FR-028: Reviewers shall be able to edit extracted field values; every edit shall be recorded.
- FR-029: Reviewers shall be able to approve or reject a document's extraction.

### Audit Trail

- FR-030: The system shall record an audit entry for every state-changing action (upload, status change, field edit, approval, rejection, export) with actor, timestamp, and before/after values.
- FR-031: Audit entries shall include the extraction mode (`mock` or the real provider name).

### Export

- FR-032: Users shall be able to export approved document data as JSON.
- FR-033: Users shall be able to export approved document data as CSV.
- FR-034: Exports shall include the `extraction_mode` field so data consumers always know the origin of the values.

### Demo Mode and Data Limits

- FR-035: The hosted demo UI shall show a "Demo Mode" badge (with a "Demo AI Mode" tooltip) when `NEXT_PUBLIC_DEMO_MODE` is true.
- FR-036: The hosted demo shall delete documents older than `RETENTION_DAYS` (default 7 days).

## 7. Non-Functional Requirements

Categories follow ISO/IEC 25010 (an international standard for software quality). Note: ISO/IEC 25010 has no standalone "Observability" category — log- and monitoring-related qualities formally sit under Maintainability and Reliability — but they are listed separately here because they are operationally important for this project.

### Performance

- NFR-001: In the hosted demo, 95% of read API requests (document list, document detail) shall respond in under 1 second, excluding queue processing time.
- NFR-002: In Mock Mode, 95% of uploads shall reach status `extracted` within 10 seconds of upload, including simulated provider latency.
- NFR-003: Core demo pages shall score at least 85 on Lighthouse performance and accessibility checks.

### Security

- NFR-004: No secret values (service role keys, JWT secret, API keys) shall reach the browser; only variables prefixed `NEXT_PUBLIC_` may be exposed to the frontend.
- NFR-005: All API endpoints shall require authentication and role checks, except the health check endpoint.
- NFR-006: Role checks shall be enforced server-side; the frontend only hides UI, it never grants permission.
- NFR-007: Uploaded files shall be stored without public access and served through authenticated or signed access.
- NFR-008: The hosted demo shall be served over HTTPS.

### Reliability

- NFR-009: The hosted demo shall have no runtime dependency on any AI provider; an AI outage shall not affect demo availability.
- NFR-010: Failed extraction jobs shall be retried up to `MAX_JOB_ATTEMPTS` before being marked `failed`, with the failure reason stored.
- NFR-011: In Local Docker Mode, all services shall restart automatically after a process crash.

### Maintainability

- NFR-012: The frontend shall compile with TypeScript strict mode with zero errors.
- NFR-013: Python code shall pass ruff (lint and format) and mypy checks with zero errors.
- NFR-014: Extraction pipeline modules shall have at least 70% test coverage by the end of Phase 12.

### Observability

- NFR-015: The API and worker shall emit structured JSON logs that include a request or job identifier.
- NFR-016: The API shall expose a health check endpoint reporting service and database status; the worker shall log a heartbeat every poll cycle.
- NFR-017: Logs shall not contain document contents or user passwords.

### Portability

- NFR-018: The same application code shall run in the hosted demo and in Local Docker Mode; the only differences shall be environment variables.
- NFR-019: Extraction Providers shall be selectable through configuration (`EXTRACTION_MODE`) with no code changes.

## 8. In Scope (MVP)

- Email/password login with the four roles (Admin, Reviewer, Uploader, Viewer) and server-enforced RBAC
- Seeded demo accounts for all three demo personas (no self-service signup)
- Single-file PDF upload with validation, 10 MB and 20-page limits
- Storage abstraction over Supabase Storage (hosted) and MinIO (Local Docker Mode)
- Document records with the status lifecycle in FR-025
- PostgreSQL job queue and polling worker with retries (`MAX_JOB_ATTEMPTS`)
- Light Parser (pypdf) text extraction for native PDFs
- Document type detection for invoice, RFP, contract, bill of lading (plus unknown)
- Structured field extraction per document type and table extraction
- Per-field confidence scores and low-confidence flagging at `CONFIDENCE_THRESHOLD`
- MockExtractionProvider with deterministic results, simulated latency, and realistic confidences
- Vision LLM Extraction Provider (OpenAI or OpenAI-compatible) for Local Docker Mode, with page-image rendering (pdf2image + Poppler) and Pydantic response validation
- Review screen with side-by-side PDF viewing, field editing, approve/reject
- Audit trail with actor, timestamp, before/after values, and extraction mode
- JSON and CSV export of approved data, including `extraction_mode`
- "Demo Mode" UI labeling (badge + tooltip) and `extraction_mode` in exports and audit
- 7-day retention deletion for hosted demo data
- Health check endpoint, structured JSON logging, worker heartbeat
- Docker Compose environment for Local Docker Mode (PostgreSQL 16, MinIO, API, worker, web)
- `make` targets for setup, dev, lint, format, typecheck, tests, migrations, seeding, and Docker
- GitHub Actions checks on `main` (production) and `development` (preview) branches

## 9. Out of Scope (MVP)

The following are explicitly **not** built in the MVP:

- Billing and payments
- Real multi-tenant self-signup
- SSO / SAML
- Redis
- Kubernetes
- Microservices
- Webhooks
- SAP / Salesforce / NetSuite connectors
- Fine-tuned ML models
- Custom OCR training
- Real production SLA
- OpenRouter free provider
- Public real Vision LLM usage
- Heavy Docling pipeline in hosted demo
- Mobile native app
- Real-time collaborative editing
- Email notifications
- Batch upload (multiple files in one request)
- Multi-language UI (English only in the MVP)

## 10. Success Criteria

Each criterion is testable.

- SC-01: All 20 Phase 1 deliverable files exist in the repository and satisfy the Phase 1 verification checklist.
- SC-02: The hosted demo runs with $0 monthly infrastructure cost, confirmed on the billing pages of Vercel, Render, and Supabase.
- SC-03: All three demo accounts (Admin, Reviewer, Viewer) can log in to the deployed demo and complete their core flow.
- SC-04: In Mock Mode, 95% of uploads reach status `extracted` within 10 seconds.
- SC-05: At least one seeded demo document contains flagged low-confidence fields that a Reviewer can edit and then approve.
- SC-06: A Reviewer can export approved documents as both JSON and CSV, and both exports include `extraction_mode`.
- SC-07: Every state-changing API action produces an audit record, verified by an automated test.
- SC-08: The hosted demo runs 30 consecutive days with zero external AI API calls (verifiable in logs, since Mock Mode never calls an AI provider).
- SC-09: `make lint` and `make typecheck` pass with zero errors on the `main` branch from Phase 2 onward.
- SC-10: `docker compose -f docker/docker-compose.yml up --build` from a clean clone reaches a working Local Docker Mode within 10 minutes and extracts a sample invoice with a real Vision LLM.

## 11. Constraints

| Constraint | Detail |
| --- | --- |
| Budget | $0 per month for the public demo; free tiers only (Vercel, Render, Supabase, GitHub) |
| Time | One solo developer (Mohd Aquib Khan); delivery follows the 12-phase plan |
| Technology | Only free tiers for the public demo; no paid service is mandatory for any feature |
| Legal | No AGPL dependencies by default. PyMuPDF is excluded for this reason (ADR-003). MinIO (AGPLv3) and Poppler (GPL) run only as separate local processes in Local Docker Mode — they are not linked libraries, so they do not put AGPL/GPL code inside this MIT-licensed repository |
| Determinism | The public demo must be safe and repeatable: no external AI calls, no runtime cost per visitor |

## 12. Assumptions

- A-01: Demo visitors use a desktop-class browser; mobile layouts are best-effort only.
- A-02: Supabase free tier (Postgres, Auth, Storage) remains sufficient for demo-scale traffic.
- A-03: The identity provider for Local Docker Mode will be decided in Phase 4, keeping the same JWT contract as the hosted demo (Supabase Auth). One option is a self-hosted Supabase instance in the Compose stack; the choice will be recorded in an ADR when made.
- A-04: Demo documents are synthetic; no real client data will be uploaded to the public demo.
- A-05: MVP document types are limited to invoice, RFP, contract, and bill of lading.
- A-06: Documents are in English in the MVP.
- A-07: The Vision LLM used in Local Docker Mode is OpenAI or an OpenAI-compatible endpoint supplied by the operator with their own API key.
- A-08: Retention deletion (FR-036) runs as part of worker housekeeping; no external scheduler is introduced.

## 13. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| R-01 | Supabase pauses free-tier projects after about 7 days of low activity — demo outage | Medium | High | Documented warm-up routine (login cadence); monitoring; restore runbook in Phase 11 |
| R-02 | Render spins down free web services after 15 minutes without traffic — slow first request | High | Low | Documented expectation in README; acceptable for a demo |
| R-03 | Solo developer availability slips the schedule | Medium | Medium | Phased plan with independently shippable phases; strict scope lock |
| R-04 | Scope creep adds unplanned features | High | High | Out-of-scope list above; scope changes require a product contract update and an ADR |
| R-05 | Vision LLM returns malformed or drifting output | Medium | Medium | Pydantic validation with retry, then explicit failure; provider abstraction allows model swap |
| R-06 | Accidental AI cost in Local Docker Mode | Medium | Medium | `VISION_MAX_PAGES` page cap, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_OUTPUT_TOKENS`; mode defaults to `mock`; operator's own key |
| R-07 | Public demo credentials abused to upload junk | High | Low | Upload limits, 7-day retention, Mock Mode (abuse has no monetary cost), synthetic data |
| R-08 | Free-tier pricing or policy changes at any vendor | Medium | High | Portability requirement (NFR-018): environment-only differences; Local Docker Mode is a full offline fallback demo |
| R-09 | Encrypted, corrupt, or unusual PDFs break extraction | Medium | Low | Strict upload validation; per-job error capture; job marked `failed`, never silently dropped |
| R-10 | A visitor uploads confidential data to the public demo | Medium | High | Clear Demo Mode labeling, 7-day retention deletion, and Mock Mode: documents are never sent to a third-party AI from the hosted demo |
| R-11 | PostgreSQL queue becomes a throughput bottleneck under real workload | Low | Medium | Accepted trade-off (ADR-004) with a documented migration path to Redis if throughput ever demands it |
| R-12 | Mock results look "too perfect" and misrepresent the pipeline | Medium | Low | Realistic confidence distribution including flagged fields; `extraction_mode: mock` visible in UI, exports, and audit |

## 14. Dependencies

| Service | Used for | Tier | Notes |
| --- | --- | --- | --- |
| Supabase | Postgres database, Auth, Storage (hosted demo) | Free | Free projects pause after about 7 days of low activity (official docs) |
| Vercel | Next.js frontend hosting | Free (Hobby) | Hobby plan is intended for personal, non-commercial use |
| Render | FastAPI API and worker hosting | Free | Free web services spin down after 15 minutes without inbound traffic |
| GitHub + GitHub Actions | Repository and CI/CD | Free for public repos | Branch strategy: `main` (production), `development` (preview) |
| OpenAI or OpenAI-compatible endpoint | Vision LLM (Local Docker Mode only) | Paid, usage-based | Never called by the hosted demo |
| Docker Engine + Compose, MinIO, Poppler | Local Docker Mode runtime | Free, open source | Run only on the operator's machine |

## 15. Glossary

| Term | Definition |
| --- | --- |
| Mock Mode | Operating behavior in which the MockExtractionProvider returns deterministic, pre-defined extraction results; no AI is called |
| Demo Mode | The UI label shown on the public demo deployment, which runs in Mock Mode |
| Local Docker Mode | The environment that runs the full real pipeline with Docker Compose on a local machine |
| Extraction Provider | The abstraction behind extraction: any implementation (mock or Vision LLM) selected by `EXTRACTION_MODE` without code changes |
| Vision LLM | A large language model that accepts image input; used to read rendered PDF page images |
| Light Parser | The pypdf-based text extraction step for native (text-based) PDFs |
| JWT | JSON Web Token — a signed token used to authenticate API requests |
| RBAC | Role-based access control — permissions granted by role, enforced server-side |
| Audit trail | An append-only record of who changed what, when, and from which value to which |
| Confidence score | A value between 0 and 1 expressing how certain the system is about an extracted field |
| MVP | Minimum viable product — the smallest complete, useful version |
| FR | Functional requirement — what the system does (FR-001, FR-002, …) |
| NFR | Non-functional requirement — how well the system does it (NFR-001, …) |
| PostgreSQL queue | A job queue implemented as a table in PostgreSQL, claimed with row-level locking |
| Pydantic | A Python library that validates data against declared schemas |
| ADR | Architecture Decision Record — a short document capturing one architectural decision and its consequences |
| Native PDF | A PDF whose text is embedded as data and can be extracted directly |
| Scanned PDF | A PDF made of page images; its text requires OCR or a Vision LLM |
| Supabase | An open-source platform providing Postgres, authentication, and file storage with free-tier hosting |
| MinIO | An S3-compatible object storage server that runs locally in Docker |
| Poppler | An open-source PDF rendering toolkit; provides the page-to-image utilities used by pdf2image |
| Free tier | A hosting plan that costs $0 within usage limits |
| Retention | How long data is kept before automatic deletion (7 days in the demo) |

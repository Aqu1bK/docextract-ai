# DocExtract AI — Phase Plan

The project is delivered in 12 phases. Each phase has a single goal, concrete deliverables, and a status. A phase is marked Complete only when its acceptance criteria pass; nothing later than the current phase is considered started.

Status values: Not Started / In Progress / Complete.

| Phase | Name | Goal | Key Deliverables | Status |
| --- | --- | --- | --- | --- |
| 01 | Product Contract and Architecture Foundation | Define what will be built and why before any application code is written. | README, product contract (PRD), arc42 architecture documentation, demo and local mode explanations, 4 ADRs, `.env.example`, `.gitignore`, MIT LICENSE, `.editorconfig`, Makefile, `.github` contribution docs, `init_project.sh` / `init_project.ps1`, this phase plan | **Complete** |
| 02 | Backend Skeleton | Stand up the FastAPI application with a runnable, health-checkable entry point. | FastAPI app factory, `/api/v1` router, health check endpoint, Pydantic settings loading from environment, structured JSON logging, error envelope, ruff/mypy/pytest configuration | **Complete** |
| 2.5 | Minimal CI Gate | Verify every push and pull request automatically so broken code cannot merge. | GitHub Actions workflow (`.github/workflows/ci.yml`) with four parallel jobs — secrets scan, ruff lint, mypy strict, pytest — on push and pull request to `development` and `main`, pip dependency caching keyed on `pyproject.toml`, branch protection guidance for `main`, CI learning note (`phase-2.5-ci-gate.md`) | **Complete** |
| 03 | Database Schema and Migrations | Define and version the data model in PostgreSQL. | SQLAlchemy 2.x models (14 tables across 4 modules), naming-convention Base, domain enums, engine/session stack with `get_db`, Alembic setup and initial migration with verified round-trip, idempotent seed with `--reset-demo`, readiness probe `/healthz/ready`, DB-backed CI tests (`postgres:16` service), database learning note (`phase-03-database.md`) | **Complete** |
| 04 | Authentication and RBAC | Authenticate users and enforce the four roles on every endpoint. | JWT validation, role dependency for FastAPI, user listing and deactivation (FR-003), seeded demo accounts, Supabase Auth wiring; local identity decision (assumption A-03) | Not Started |
| 05 | Storage and Upload Flow | Accept, validate, and store uploaded PDFs. | Storage abstraction (Supabase Storage / MinIO), upload endpoint with size/page/PDF validation (FR-005 to FR-010), document records with status lifecycle | Not Started |
| 06 | Extraction Engine | Turn stored PDFs into validated structured data. | Extraction Provider abstraction, MockExtractionProvider (deterministic), Light Parser (pypdf) text extraction, document type detection, field/table extraction, confidence scoring and flagging | Not Started |
| 07 | Queue and Worker | Process extractions asynchronously with retries. | PostgreSQL queue table with SKIP LOCKED claiming, polling worker, retry and failure handling (FR-011 to FR-013), worker heartbeat and logs | Not Started |
| 08 | Review, Audit, Export | Close the human-in-the-loop workflow. | Review endpoints (edit, approve, reject), audit trail records (FR-030, FR-031), JSON and CSV export including `extraction_mode` | Not Started |
| 09 | Frontend Core | Deliver the full web UI on top of the API. | Next.js App Router structure, login, document list and detail, upload form (React Hook Form + Zod), review screen with react-pdf side-by-side view, TanStack Query data layer, "Demo Mode" badge and tooltip | Not Started |
| 10 | Local Docker Real Vision Setup | Run the complete real pipeline locally in Docker. | Docker Compose stack (web, api, worker, PostgreSQL 16, MinIO), pdf2image + Poppler rendering, OpenAI Vision provider with Pydantic validation, cost controls (`VISION_MAX_PAGES`, timeouts) | Not Started |
| 11 | Public Online Deployment | Ship the free hosted demo in Mock Mode. | Vercel frontend, Render API and worker, Supabase (Postgres, Auth, Storage) wiring, demo data seeding, free-tier monitoring and warm-up runbook, `[LIVE DEMO URL]` published | Not Started |
| 12 | Testing and Documentation | Prove quality and finish the record. | CI/CD pipelines on `main` and `development`, pytest and vitest coverage (≥70% pipeline coverage), Playwright end-to-end flows, README and docs final pass, verification checklist green | Not Started |

## Status Legend

- **Not Started** — no branch, no code, no partial work.
- **In Progress** — the phase's deliverables are being produced; acceptance criteria not yet all green.
- **Complete** — every deliverable exists and satisfies its acceptance criteria.

## Rules

1. One phase at a time; a phase is Complete before the next begins.
2. Scope changes require a product contract update and, for architecture, a new ADR (see ADR numbering continuing from ADR-004).
3. Application code, Docker, and CI/CD are deferred to their phases above; Phase 1 creates documentation and structure only.
4. The overall plan references `docs/phase-plan.md`; per-requirement detail lives in `docs/product-contract.md`.

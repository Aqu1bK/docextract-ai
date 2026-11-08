# Contributing to DocExtract AI

Thanks for your interest in contributing. This document explains how to set up a development environment, the branch and commit conventions, the pull request process, and the code style rules.

## Development Setup

Prerequisites: Git, Python 3.12, Node 20, and Docker (with Compose) for Local Docker Mode.

```bash
# 1. Clone the repository
git clone <repository-url>
cd docextract-ai

# 2. Create the folder structure (apps/, docker/, docs/adr/, ...)
bash scripts/init_project.sh        # Windows: powershell scripts/init_project.ps1

# 3. Install dependencies
make install

# 4. Configure environment
cp .env.example .env
# Edit .env — never commit it

# 5. Apply database migrations
make migrate
```

Then use `make dev-api` (FastAPI on :8000) and `make dev-web` (Next.js on :3000), or `make dev-docker` to run the full stack. See the `Makefile` (or `make help`) for all commands.

## Branch Naming

Branches are named by type with a short kebab-case description:

```
feature/<short-description>    # new functionality (e.g. feature/review-queue-endpoint)
fix/<short-description>        # bug fixes
docs/<short-description>       # documentation only
```

Work happens on feature branches; `development` is the preview integration branch and `main` is production. Pull requests target `development`.

## Commit Messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`. Allowed types are `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`. See [COMMIT_CONVENTION.md](COMMIT_CONVENTION.md) for the full rules and examples.

## Pull Request Process

1. Create a branch following the naming convention above.
2. Make your change; keep it focused — one logical change per PR.
3. Run the quality gate locally and make sure it passes:

   ```bash
   make lint
   make format
   make typecheck
   make test
   ```

4. Fill in the [pull request template](PULL_REQUEST_TEMPLATE.md), linking the phase and task your change belongs to.
5. Open the PR against `development`. PRs to `main` are reserved for phase releases.
6. CI must pass (lint, typecheck, tests) before review.
7. Address review comments by pushing additional commits; do not force-push over reviewed history.

## Code Style

**Python (apps/api)**

- Python 3.12; type annotations on all public functions.
- `ruff check` and `ruff format` are the single lint and format tools — run `make lint` and `make format`.
- `mypy` must pass with zero errors (`make typecheck`).
- Pydantic v2 models validate every external input; SQLAlchemy 2.x style ORM code.
- 4-space indentation; UTF-8; LF line endings (enforced by `.editorconfig`).

**TypeScript (apps/web)**

- TypeScript strict mode; no `any` in new code and no `@ts-ignore` without a comment explaining why.
- ESLint (via `npm run lint`) must pass; formatting follows Prettier (`make format`).
- React Hook Form + Zod for forms; TanStack Query for server data.
- 2-space indentation.

**All code**

- No hardcoded secrets, URLs, or credentials; everything environment-driven (`.env.example` is the reference).
- No commented-out code; delete it — git remembers.
- New endpoints and behaviors must map to a requirement ID (FR-xxx) from [docs/product-contract.md](../docs/product-contract.md); if no requirement exists, open an issue first.

## Running Tests

```bash
make test           # pytest (api) + vitest (web)
make test-e2e       # Playwright end-to-end tests
```

Extraction pipeline modules must keep at least 70% coverage (NFR-014). New features land with tests — unit tests for pipeline logic (providers, parsing, queue claiming), component tests for UI forms, and Playwright flows for the review workflow.

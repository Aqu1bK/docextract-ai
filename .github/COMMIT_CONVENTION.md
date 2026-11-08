# Commit Message Convention

This project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification (v1.0.0). Every commit message must be machine-parseable so that tooling can generate changelogs and reason about history.

## Format

```
<type>(<scope>): <short summary>

[optional body]

[optional footer(s)]
```

- **type** — one of the values listed below.
- **scope** — optional, the part of the code affected (for example `api`, `web`, `worker`, `docs`, `db`, `ci`).
- **summary** — imperative mood ("add", not "added" / "adds"), lowercase, no trailing period, 72 characters or fewer.
- **body** — optional; the what and why of the change (not the how). Wrap at 72 characters.
- **footer** — optional; breaking changes (`BREAKING CHANGE: <description>`) and issue references (`Refs #12`, `Closes #34`).

## Types

| Type | Meaning |
| --- | --- |
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `style` | Formatting, whitespace, naming — no logic change |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `build` | Build system or dependency changes |
| `ci` | CI/CD configuration changes |
| `chore` | Maintenance that touches no src or test files |

## Examples

**feat** — new functionality:

```
feat(api): add POST /documents upload endpoint (FR-005)
```

```
feat(web): review screen with side-by-side PDF and fields (FR-027)
```

**fix** — bug fix:

```
fix(worker): retry failed jobs up to MAX_JOB_ATTEMPTS
```

```
fix(web): demo badge not shown when NEXT_PUBLIC_DEMO_MODE unset
```

**docs** — documentation only:

```
docs: add ADR-003 use pypdf instead of PyMuPDF
```

```
docs(adr): record Postgres queue decision as ADR-004
```

**style** — formatting only:

```
style(api): apply ruff format to extraction package
```

**refactor** — no behavior change:

```
refactor(api): extract provider selection into factory
```

**perf** — performance:

```
perf(api): add index on documents.status for queue queries
```

**test** — tests:

```
test(worker): cover SKIP LOCKED job claiming
```

**build** — dependencies or build:

```
build(api): pin pydantic to 2.x in requirements
```

**ci** — CI/CD:

```
ci: run lint and typecheck on development branch
```

**chore** — maintenance:

```
chore: update .gitignore for coverage artifacts
```

## Breaking Changes

A breaking change uses an uppercase `!` after the type (and/or a `BREAKING CHANGE` footer):

```
feat(api)!: return 409 on invalid document state transitions

BREAKING CHANGE: approving a rejected document now returns 409
instead of 200.
```

## Rules

1. One logical change per commit; the summary must stand alone in `git log --oneline`.
2. Always imperative mood and lowercase first letter in the summary.
3. Reference requirement IDs (FR-xxx / NFR-xxx) or issue numbers when a commit implements or fixes something traceable.
4. Never commit secrets, `.env` files, or generated artifacts (see `.gitignore`).

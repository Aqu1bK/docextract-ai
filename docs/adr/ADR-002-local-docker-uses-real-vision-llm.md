# ADR-002: Local Docker Uses Real Vision LLM

## Status

Accepted

## Context

The project must demonstrate that the extraction pipeline really works: an actual PDF, rendered pages, a Vision LLM call, schema validation, and stored structured output. This matters in technical interviews and screen-share demonstrations, where a reviewer can ask "show me the real thing."

At the same time, the public demo cannot run real AI calls (cost, timeout, privacy, reliability, determinism — see ADR-001). The project also runs on a $0 infrastructure budget, so there is no paid, always-on environment for real extraction.

The remaining option is the operator's own machine: it has no hosting cost, keeps the API key private, and allows a real Vision LLM (OpenAI or any OpenAI-compatible endpoint) to be used deliberately and with cost controls. Docker Compose can reproduce the entire production-shaped topology — web, API, worker, PostgreSQL 16, and MinIO (an S3-compatible object store) — locally with one command.

The extraction pipeline is already designed around the Extraction Provider abstraction (`EXTRACTION_MODE`), so the same code base must be able to run the real provider without modification.

## Decision

Local Docker Mode runs the full real extraction pipeline — pypdf text extraction, pdf2image + Poppler page rendering, Vision LLM call via the OpenAI Python SDK (or OpenAI-compatible endpoint), Pydantic validation — activated by `EXTRACTION_MODE=openai_vision` with the operator's own `OPENAI_API_KEY`, inside Docker Compose.

## Rationale

- The same application code serves both modes; only environment variables differ (NFR-018, NFR-019), which proves the provider abstraction is real and not a demo scaffold.
- The API key stays on the operator's machine and is never committed or exposed to the public deployment.
- Cost is bounded and deliberate: `VISION_MAX_PAGES=3`, `LLM_TIMEOUT_SECONDS=45`, and `LLM_MAX_OUTPUT_TOKENS=3000` cap per-document spend, and the mode defaults to `mock` until explicitly switched.
- Docker Compose mirrors the hosted topology (API, worker, Postgres, S3-compatible storage), so interviews demonstrate an environment shaped like production, not a simplified script.
- Pydantic validation of the model's JSON response keeps bad model output out of the database; invalid responses are retried and then failed explicitly.

## Consequences

### Positive

- Real end-to-end extraction can be demonstrated live in interviews and screen-shares.
- The Vision LLM path (rendering, prompting, validation, retries) is exercised by real usage, surfacing issues the mock cannot.
- Zero additional hosting cost; the operator pays only for the API calls they actually trigger.
- Swapping to a different OpenAI-compatible provider is a configuration change, proving the abstraction to clients.
- The local environment doubles as the development environment, keeping "works locally" and "works in demo" the same code.

### Negative

- Requires Docker and a paid API key from whoever runs it — the demo is no longer one-click for outsiders.
- Real API calls introduce nondeterminism and latency; local runs are not repeatable the way Mock Mode is.
- Page rendering requires Poppler inside the container image, making the local stack heavier than the hosted one.
- The operator must watch cost and must not leave the worker running in real mode unattended.

## Alternatives Considered

### Alternative 1: Mock Mode everywhere (no real AI anywhere in the project)

- Description: Ship only the MockExtractionProvider in all environments and rely on documentation to describe the real pipeline.
- Why rejected: The claim "AI-powered extraction" would then be unverifiable anywhere, which undermines the project's purpose as a portfolio and interview artifact; the Vision LLM integration (rendering, prompting, response validation) could not be tested or shown.

### Alternative 2: A paid hosted environment running real extraction for invited reviewers

- Description: Keep a small always-on paid deployment (hosting + AI usage) with real extraction, shared by invitation.
- Why rejected: Contradicts the $0 public-demo constraint and introduces recurring cost for availability that is only occasionally needed; the interview use case is fully served by a local run on the operator's machine.

## References

- ADR-001 (public demo uses Mock Mode): `docs/adr/ADR-001-public-demo-uses-mock-mode.md`
- Local Docker Mode explanation: `docs/local-docker-mode-explanation.md`
- OpenAI API documentation (vision and image input): https://developers.openai.com/api/docs/guides/images-vision
- pdf2image (Python wrapper for Poppler rendering, MIT license): https://github.com/Belval/pdf2image
- Docker Compose documentation: https://docs.docker.com/compose/

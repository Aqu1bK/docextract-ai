# ADR-001: Public Demo Uses Mock Mode

## Status

Accepted

## Context

The public online demo is deployed on free tiers (Vercel + Render + Supabase) with shared, publicly documented credentials (admin@demo.docextract.ai, reviewer@demo.docextract.ai, viewer@demo.docextract.ai). Its purpose is to let recruiters, hiring managers, and potential clients walk through the complete product — upload, extraction, confidence flagging, review, approval, export — through a live link, with $0 monthly infrastructure cost.

Running real Vision LLM extraction on this deployment is not viable:

- **Cost:** Vision LLM API calls are billed per request and per page. Public credentials mean unbounded uploads, and therefore an unbounded bill. The project constraint is a $0 public demo.
- **Timeout:** Free-tier hosting services enforce request execution time limits. Multi-page Vision LLM calls can exceed them, producing unpredictable failures.
- **Privacy:** Visitor documents would be sent to a third-party AI service without informed consent. The project treats that as unacceptable by default.
- **Reliability:** Free AI endpoints are rate-limited and intermittently unavailable. The demo must not inherit that availability.
- **Determinism:** A demo must behave identically on every visit, so walkthroughs and recordings stay accurate. Live model output changes between runs.
- **Secrets:** A usable AI key for anonymous visitors would effectively be a published credential.

The system needs an extraction step on the public demo that is free, fast, private, reliable, and deterministic, while still exercising the real pipeline architecture (queue → parse → extract → validate → review → audit → export).

## Decision

The public online demo runs in Mock Mode: the MockExtractionProvider (an Extraction Provider implementation returning deterministic, pre-defined results) performs the extraction step, selected by the environment variable `EXTRACTION_MODE=mock`.

## Rationale

- The MockExtractionProvider implements the same Extraction Provider interface as the real Vision LLM provider, at the same position in the pipeline. Everything downstream — confidence scoring, low-confidence flagging, review workflow, audit trail, export — runs the real code path.
- Deterministic results make the demo repeatable and testable as an acceptance criterion (SC-08: zero external AI API calls, verifiable in logs).
- Simulated latency and realistic confidence values (including fields below the 0.75 threshold) let the demo show queue states and the human review step honestly.
- Every extracted field carries the source `mock`; UI, exports (`extraction_mode: mock`), and audit entries all state the mode explicitly, keeping the demo honest (see `docs/demo-mode-explanation.md`).
- The $0 budget, privacy, and availability constraints are satisfied by construction rather than by monitoring.

## Consequences

### Positive

- The public demo costs $0 in AI usage regardless of traffic.
- The demo cannot be broken by an AI provider outage, rate limit, or model deprecation.
- Visitor documents never leave the demo's storage for a third-party AI.
- Demo behavior is identical on every visit; recordings and walkthroughs stay accurate.
- No AI credentials exist on the public deployment, so there is nothing to leak.
- The review, audit, and export workflows are demonstrated with the real code.

### Negative

- Visitors do not see real AI output on the public demo; the extraction results are pre-defined.
- Uploaded demo documents are not actually parsed, which must be communicated clearly to avoid misunderstanding.
- Mock results require maintenance as the demo scenarios evolve.
- Some reviewers may initially read "mock" as "fake product" until the provider abstraction is explained.

## Alternatives Considered

### Alternative 1: Real Vision LLM calls on the public demo

- Description: Deploy with `EXTRACTION_MODE=openai_vision` and a server-side API key, letting any visitor trigger real extraction.
- Why rejected: Public credentials plus metered API calls create an unbounded cost and an abuse surface; free-tier request time limits make multi-page calls unreliable; visitor documents would go to a third-party AI without consent; the demo's availability would depend on an external AI provider; and the API key would be usable by anonymous traffic.

### Alternative 2: OpenRouter free providers on the public demo

- Description: Use a free-model aggregator provider so the public demo performs "real" AI calls at no cost.
- Why rejected: Out of scope by the product contract (§9, "OpenRouter free provider"). Free-provider availability and rate limits are not dependable for a public demo, it still sends visitor documents to a third party, and it adds an external dependency the demo cannot control — recreating the reliability and determinism problems without solving cost.

## References

- Product contract, §9 Out of Scope and §11 Constraints: `docs/product-contract.md`
- Demo Mode explanation: `docs/demo-mode-explanation.md`
- OpenAI API documentation (vision and image input): https://developers.openai.com/api/docs/guides/images-vision
- Render free tier documentation (spin-down and limits): https://render.com/docs/free
- ADR format popularized by Michael Nygard: https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions

# Demo Mode Explanation

This document explains Mock Mode in plain language. It is written for a non-technical reader as well as for engineers.

## 1. What is Demo Mode?

Demo Mode is the label the public online demo shows in the UI. Technically, the demo runs in **Mock Mode**: when a document is uploaded, the extraction step does not call any AI. Instead, a component called the **MockExtractionProvider** returns pre-defined results that look like real extraction output. It exists so that anyone can click through the full product — upload, extraction, confidence flags, review, approval, export — without the demo costing money, slowing down, or sending anyone's documents to a third-party AI service.

**What it does do:**

- Runs the complete product workflow: upload → queue → extraction results → confidence flags → review → approval → export.
- Returns the same results for the same input, every time (deterministic).
- Simulates processing latency, so the queue and status changes look realistic.
- Marks every extracted field with the source `mock`, and every export and audit entry with `extraction_mode: mock`.

**What it does not do:**

- It does not read the actual content of your uploaded PDF with AI.
- It does not call OpenAI or any other AI provider.
- It does not send your document anywhere outside the demo hosting.
- It does not produce extraction results that should be trusted as real data.

## 2. Why Not Real AI on the Public Demo?

Five reasons, each in plain language:

- **Cost:** Real Vision LLM API calls are billed per request and per page. A public link with shared demo credentials means anyone can upload unlimited documents, and the bill would go to the project owner. Mock Mode keeps the demo's cost at exactly $0.
- **Timeout:** Free-tier hosting services enforce execution time limits on requests. A Vision LLM call across many rendered pages can take longer than those limits allow, which would make the demo fail unpredictably. Mock Mode finishes quickly and reliably.
- **Privacy:** Sending a visitor's document to a third-party AI service without their informed consent is not acceptable by default. In Mock Mode, documents stay inside the demo's storage and are deleted after 7 days.
- **Reliability:** Free AI endpoints are rate-limited and can be temporarily unavailable. If the demo depended on one, it would break whenever the provider did. Mock Mode has no external dependency to break.
- **Determinism:** A demo should behave the same way on every visit, so a walkthrough or a screen recording made today still matches what a recruiter sees tomorrow. Mock Mode guarantees that; a live AI model does not.

## 3. How Does Mock Mode Work?

- **MockExtractionProvider returns pre-defined results.** The provider is an implementation of the Extraction Provider interface (the same interface the real Vision LLM provider implements). It returns a fixed set of fields and tables for the seeded demo documents.
- **Results are deterministic.** The same input always produces the same output. There is no randomness between runs, so tests and demos are repeatable.
- **Artificial latency simulates real processing.** The provider waits a short, fixed time before returning, so the document visibly moves through `queued → processing → extracted`, exactly like a real pipeline.
- **Confidence scores are realistic, not all 0.99.** Some fields are returned with confidence below the `CONFIDENCE_THRESHOLD` (default 0.75), so the low-confidence flagging and the human review step are demonstrated honestly.
- **Source is marked as `mock` in every field.** Each extracted field records where it came from, and in Mock Mode that value is always `mock` — visible in the UI, the exports, and the audit log.

## 4. What Is Labeled in the UI?

The public demo is explicit about what it is doing:

- A **"Demo Mode" badge** is visible on the interface whenever `NEXT_PUBLIC_DEMO_MODE` is true.
- A **"Demo AI Mode" tooltip** on the badge explains that extraction runs in Mock Mode and no real AI is called.
- **Exports include `extraction_mode: mock`** in both JSON and CSV output, so the data always states its own origin.
- **Audit log entries include `extraction_mode: mock`**, so every record shows which provider produced the data.

## 5. How to Switch to Real AI?

Switching is configuration, not code, thanks to the Extraction Provider abstraction:

1. Set `EXTRACTION_MODE=openai_vision` in the environment (`.env`).
2. Provide `OPENAI_API_KEY` and `OPENAI_MODEL` (an OpenAI or OpenAI-compatible endpoint).
3. Restart the API and worker.

No source code changes are required; the pipeline selects the provider from the environment at startup. Real AI usage is intended for Local Docker Mode (see [ADR-002](adr/ADR-002-local-docker-uses-real-vision-llm.md) and [local-docker-mode-explanation.md](local-docker-mode-explanation.md)) — running it on the public demo would reintroduce exactly the cost, timeout, privacy, and reliability problems described above.

## 6. Enterprise Justification

To a CTO, Mock Mode on the public demo is not a shortcut or a fake — it is a standard senior engineering decision, for four reasons:

1. **It is the same pattern as test doubles in CI.** Deterministic fakes are how production teams keep integration tests fast, free, and repeatable. The public demo is treated the same way: an environment in which the system's behavior must be predictable and free to exercise.
2. **The real pipeline is designed, built, and swappable — not simulated at the UI level.** The mock sits behind the same Extraction Provider interface as the Vision LLM provider, at the same point in the queue → parse → extract → validate pipeline. Swapping providers exercises the real architecture; nothing downstream (confidence scoring, flagging, review, audit, export) knows or cares which provider ran.
3. **Cost and abuse control are design requirements.** A public, credentials-shared demo with metered AI calls is an unbounded bill and an abuse surface. Making the hosted demo AI-free by construction (not by hope) is how you keep the $0 constraint honest.
4. **Honest labeling is a trust decision.** The badge, the tooltip, the `extraction_mode` field in every export and audit entry, and the limitations section in the README all state plainly what the demo does. Reviewers can verify the claim; nothing is oversold.

The trade-off is real and acknowledged: a visitor to the public demo does not see actual AI output. That is exactly why Local Docker Mode exists — the same code base, run locally with a real Vision LLM, demonstrates the full pipeline in interviews and screen-shares (see [ADR-001](adr/ADR-001-public-demo-uses-mock-mode.md)).

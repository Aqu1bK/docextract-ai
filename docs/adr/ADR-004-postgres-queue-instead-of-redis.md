# ADR-004: Use Postgres Queue Instead of Redis

## Status

Accepted

## Context

Extraction is asynchronous work: a Vision LLM call can take tens of seconds, and even Mock Mode simulates latency. The upload request must return immediately, so the system needs a job queue that decouples upload from processing, supports retries (`MAX_JOB_ATTEMPTS=3`), and lets a worker claim jobs safely.

The candidate mechanisms were Redis (a dedicated in-memory data store commonly used as a queue/broker) or a queue built on the PostgreSQL database the project already runs.

Constraints that drive this decision:

- The hosted demo runs on free tiers with a $0 budget; every additional managed service is another constrained free-tier resource to provision, monitor, and keep alive.
- The operator is a solo developer; each extra service in the local Docker stack is another moving part to configure and debug.
- Expected workload is demo-scale (single-digit concurrent jobs), not high-throughput fan-out.
- The queue's data (job state, attempts, failure reasons) is naturally transactional with the domain data: a document row and its job should be committed atomically.

PostgreSQL supports safe concurrent job claiming with `SELECT ... FOR UPDATE SKIP LOCKED`, a documented row-locking behavior that lets multiple workers claim distinct rows without blocking each other.

## Decision

The job queue is implemented as a table in PostgreSQL 16; the extraction worker polls it every `WORKER_POLL_SECONDS` (default 3) and claims jobs using `SELECT ... FOR UPDATE SKIP LOCKED`, with retries up to `MAX_JOB_ATTEMPTS`.

## Rationale

- **One fewer service.** No Redis to host, secure, monitor, or configure in either environment — and no free-tier Redis resource with eviction and persistence caveats to depend on.
- **Transactional consistency.** Inserting the document row and its job happens in one database transaction; extraction results and the audit entry are written together. With a separate broker, keeping job state and domain data consistent requires additional coordination.
- **Sufficient performance.** At demo scale, a 3-second poll interval adds negligible latency; SKIP LOCKED handles concurrent workers correctly.
- **Operational simplicity for a solo developer.** Queue problems are debuggable with plain SQL against the database that already holds all other data.
- **No new dependency.** Consistent with the phase-1 principle of adding no software beyond what the stack requires.

## Consequences

### Positive

- Simpler deployment: the API, worker, and queue all use the one database the project already needs, in both hosted and local modes.
- Job state is durable with domain data by default, and retry/failure semantics live in the same transactional store.
- The queue is observable with ordinary SQL queries and joins against documents and audit records.

### Negative

- Polling (rather than push notification) adds up to `WORKER_POLL_SECONDS` of latency before a job starts.
- Throughput is bounded by PostgreSQL row updates; this design would not serve high-volume fan-out without change.
- Queue features Redis users get for free (delayed jobs, pub/sub, priorities as first-class primitives) must be implemented explicitly if ever needed.
- The database becomes a shared bottleneck for OLTP traffic and queue traffic, which matters only far beyond demo scale.

## Alternatives Considered

### Alternative 1: Redis as the queue/broker

- Description: Run Redis (or a managed Redis service) as the queue backend, with the worker consuming from it.
- Why rejected: Adds a second always-on service in every environment — another free-tier resource with eviction/persistence caveats on the hosted demo and another container locally; job state and domain data can no longer be committed atomically; and the expected demo-scale workload does not need Redis's throughput. The migration path is documented below for the day that changes.

### Alternative 2: Synchronous processing inside the API request

- Description: Extract during the upload request; no queue and no worker.
- Why rejected: The request would have to wait for the full extraction (timeout risk with Vision LLM calls, or even simulated latency); transient failures could not be retried independently of the upload; and status updates (`queued → processing → extracted`) that the review UI depends on would not exist.

## References

- PostgreSQL SELECT documentation, including `FOR UPDATE SKIP LOCKED`: https://www.postgresql.org/docs/current/sql-select.html
- Redis: https://redis.io
- ADR-002 (worker and retry context): `docs/adr/ADR-002-local-docker-uses-real-vision-llm.md`
- Product contract FR-011 to FR-013: `docs/product-contract.md`

Migration path (not planned, documented for completeness): if throughput ever exceeds what table-based claiming supports, introduce Redis for job dispatch while keeping PostgreSQL as the system of record, recorded in a new ADR.

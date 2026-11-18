"""The worker main loop: claim, process, persist, sleep, repeat.

This is the entrypoint ``python -m app.workers.runner``. The loop is
deliberately boring: claim one job, run it, commit the outcome (or the
retry/failure bookkeeping), close the session, sleep the poll interval
when the queue was empty, repeat while WORKER_ENABLED. Every
interesting decision lives in the modules the loop calls — claiming
semantics, processing, retry policy — which is what keeps this file
readable and the loop itself honest.

Why one session per job (not one long-lived session): each job runs in
its own transaction, so a crash mid-job rolls back exactly that job and
the next process start re-reads the queue fresh. The commit is the
lease boundary: the claim's row lock ends with the commit, which is
what makes the lease durable in the queue's terms.
"""

import asyncio
import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import ExtractionJob
from app.db.session import SessionLocal
from app.domain.enums import JobStatus
from app.workers.job_processor import process_job
from app.workers.retry import handle_retry

logger = structlog.get_logger(__name__)

# The statuses a job must hold to be claimable: ready now (pending) or
# ready after its backoff elapsed (retry_scheduled, gated by
# scheduled_at in the claim query itself).
CLAIMABLE_STATUSES: tuple[JobStatus, ...] = (JobStatus.PENDING, JobStatus.RETRY_SCHEDULED)


def claim_job(session: Session, worker_id: str) -> ExtractionJob | None:
    """Claim the next runnable job FOR UPDATE SKIP LOCKED, or None.

    The lock strategy is the whole queue: two workers issuing this
    SELECT at the same moment get disjoint rows because each locked row
    is invisible to the other's scan (SKIP LOCKED), so no worker ever
    waits or double-claims. Ordering is priority DESC (the existing
    column, not a new mechanism) then scheduled_at ASC for fairness
    within a priority level; the index ``ix_extraction_jobs_status_scheduled_at``
    backs the status+time filter this scan runs on.

    Args:
        session: A fresh session the caller will commit the claim in.
        worker_id: Stamped into leased_by for operator visibility.

    Returns:
        The claimed job, updated to LEASED with lease fields set and
        flushed (the caller commits), or None when nothing is runnable.
    """
    job = session.execute(
        select(ExtractionJob)
        .where(
            ExtractionJob.status.in_(CLAIMABLE_STATUSES),
            ExtractionJob.scheduled_at <= datetime.datetime.now(tz=datetime.UTC),
        )
        .order_by(ExtractionJob.priority.desc(), ExtractionJob.scheduled_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    ).scalar_one_or_none()
    if job is None:
        return None

    job.status = JobStatus.LEASED
    job.leased_at = datetime.datetime.now(tz=datetime.UTC)
    job.leased_by = worker_id
    job.started_at = datetime.datetime.now(tz=datetime.UTC)
    session.flush()
    return job


async def claim_and_process_job() -> ExtractionJob | None:
    """Claim one job and run it to a committed outcome.

    Opens its own session (one transaction per job), claims, processes,
    and commits success, retry, or failure bookkeeping. A processing
    exception is never re-raised past this function: the retry policy
    owns it — the job row records the outcome either way. Only
    bookkeeping failures (the queue itself misbehaving) escape to the
    loop.

    Returns:
        The job that was processed, or None when the queue was empty.
    """
    settings = get_settings()
    session = SessionLocal()
    try:
        job = claim_job(session, settings.WORKER_ID)
        if job is None:
            return None
        try:
            await process_job(session, job, settings)
        except Exception as exc:
            handle_retry(session, job, exc)
        session.commit()
        return job
    except Exception as exc:
        session.rollback()
        logger.error("worker_cycle_failed", job_id="unknown", error=repr(exc))
        raise
    finally:
        session.close()


async def run_worker() -> None:
    """Run the polling loop while WORKER_ENABLED holds.

    Each iteration is one claim attempt. When no job was runnable the
    loop sleeps WORKER_POLL_SECONDS — the poll is what trades latency
    for simplicity; the sleep is what keeps an idle worker off the
    database. Settings are re-read each iteration so flipping
    WORKER_ENABLED (env-driven restart aside) governs a running loop.
    KeyboardInterrupt is the operator's stop signal and is caught so the
    shutdown line lands in the log.
    """
    try:
        while True:
            settings = get_settings()
            if not settings.WORKER_ENABLED:
                logger.info("worker_disabled", worker_id=settings.WORKER_ID)
                break
            job = await claim_and_process_job()
            if job is None:
                await asyncio.sleep(settings.WORKER_POLL_SECONDS)
    except KeyboardInterrupt:
        logger.info("worker_stopped_by_operator")


def main() -> None:
    """Run the worker loop until stopped (console entrypoint)."""
    logger.info("worker_booting")
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

# docextract-ai/apps/api/app/api/v1/endpoints/health.py

"""Health endpoints.

``GET /healthz`` is a LIVENESS probe: it answers "is the process alive and
serving HTTP at all?" with no dependency checks, so it stays cheap and
always-on. ``GET /healthz/ready`` is the READINESS probe added in Phase 3:
it verifies the database answers ``SELECT 1`` through the application's own
session stack, so an instance whose database is unreachable reports
not-ready and a load balancer stops routing traffic to it — while the
process stays alive for logs and debugging. Render and load balancers call
both probes and use them for different decisions: restart vs. reroute.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.errors import AppException

router = APIRouter(tags=["health"])


class ReadinessFailedError(AppException):
    """A readiness dependency (the database) did not answer."""

    status_code = 503
    code = "READINESS_FAILED"
    message = "Service is not ready to serve traffic."


@router.get("/healthz")
def health_check() -> dict[str, str]:
    """Report liveness with the running environment and app version."""
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION,
    }


@router.get("/healthz/ready")
# B008 (call in default) is the documented FastAPI idiom for declaring
# dependencies; there is no cleaner form this lint rule accepts.
def readiness_check(
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    """Report readiness by checking every runtime dependency.

    The database check reuses the application's own ``get_db`` dependency,
    so the probe exercises the same engine, pool, and session lifecycle a
    real request would — a readiness signal that tests a different path
    than production traffic tests is a green light that means nothing.

    Returns:
        ``{"status": "ok", "checks": {"database": "ok"}}`` on success.

    Raises:
        ReadinessFailedError: 503 envelope when the database check fails.
    """
    try:
        db.execute(text("SELECT 1"))
    except OperationalError:
        # Any failure to answer SELECT 1 — connection refused, timeout,
        # pool exhausted — means not-ready, which is exactly what the 503
        # envelope communicates to the load balancer.
        raise ReadinessFailedError(details={"checks": {"database": "unavailable"}}) from None
    return {"status": "ok", "checks": {"database": "ok"}}

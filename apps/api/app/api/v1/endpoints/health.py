"""Health endpoints.

``GET /healthz`` is a LIVENESS probe: it answers "is the process alive and
serving HTTP at all?" with no dependency checks, so it stays cheap and
always-on. A READINESS probe that verifies the database connection arrives
in Phase 3 with SQLAlchemy; until then there is nothing downstream to check.
Render and load balancers call this endpoint to decide whether to route
traffic to this instance.
"""

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
def health_check() -> dict[str, str]:
    """Report liveness with the running environment and app version."""
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION,
    }

"""Audit service: the single write path for the append-only trail.

Every governance-relevant action in Phase 8 (field corrected, accepted,
rejected, document approved, rejected, exported) funnels through
:func:`write_audit_log`. One function, not one inline ``AuditLog(...)`` per
call site, because a trail is only trustworthy when it is uniform: the
same actor resolution, the same request metadata capture, the same flush
discipline everywhere. A call site that hand-rolls its second audit write
will eventually forget one of those and the trail grows holes.

Rows are appended inside the caller's transaction and flushed (never
committed here): the action and its audit row commit atomically or not at
all, so the trail can never show an action that did not happen.
"""

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models import AuditLog, User


def write_audit_log(
    db: Session,
    user: User,
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: dict[str, Any],
    request: Request | None = None,
) -> AuditLog:
    """Append one immutable audit row and flush it.

    The ``request`` argument is optional because some actions are initiated
    by background workers with no request to describe; when a request is
    present, its client address and User-Agent are captured so an auditor
    can answer "from where was this approved?" months later.

    Args:
        db: The caller's session (caller owns commit/rollback).
        user: The authenticated actor; supplies organization and actor ids.
        action: Dot-separated verb, e.g. ``"field.corrected"``.
        entity_type: What was acted on, e.g. ``"extracted_field"``.
        entity_id: String id of the entity acted on.
        metadata: Structured context keys an auditor filters on.
        request: The FastAPI request, for ip/user-agent capture.

    Returns:
        The flushed AuditLog row (id and created_at populated).
    """
    audit_log = AuditLog(
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata,
        ip_address=(request.client.host if request.client else None) if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.add(audit_log)
    db.flush()
    return audit_log

# docextract-ai/apps/api/app/api/v1/endpoints/audit.py

"""Audit endpoints: reading the append-only trail over HTTP.

One route for Phase 9C: ``GET /audit/documents/{document_id}/logs`` — the
review screen's timeline. The read is org-scoped through the document the
rows describe (the trail itself carries organization_id, but scoping
through the document answers "may this caller read this document's
history?" with the same convention as every other org-scoped read here,
and a foreign document is a 404, not a 403 that confirms existence).

Rows are read-only: this router exists so the trail can be queried, and
every write continues to funnel through ``app.services.audit.write_audit_log``
exactly as before.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.db.models import AuditLog, Document, User
from app.db.session import get_db
from app.domain.enums import RoleName
from app.errors import NotFoundException
from app.schemas.audit import AuditLogOut

router = APIRouter()


@router.get("/documents/{document_id}/logs", response_model=list[AuditLogOut])
def get_document_audit_logs(
    document_id: str,
    user: User = Depends(  # noqa: B008
        require_roles(  # noqa: B008
            [RoleName.ADMIN, RoleName.REVIEWER, RoleName.UPLOADER, RoleName.VIEWER]
        )
    ),
    db: Session = Depends(get_db),  # noqa: B008
) -> list[AuditLogOut]:
    """List one document's audit logs, newest first.

    The caller's organization must own the document; the rows returned
    then include every actor's entries (a worker's system rows carry a
    null actor) because the timeline's job is to show what happened,
    not just what the caller did.
    """
    document = db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == user.organization_id,
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundException(details={"document_id": document_id})

    logs = (
        db.execute(
            select(AuditLog)
            .where(
                AuditLog.entity_type == "document",
                AuditLog.entity_id == document_id,
            )
            .order_by(AuditLog.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [AuditLogOut.model_validate(log) for log in logs]

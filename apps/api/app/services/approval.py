"""Approval service: the gate between review and export.

A document may be approved only when every human-required question has a
human-endorsed answer: each required field resolved (accepted or corrected),
and no low-confidence field still pending. Those are the two blocking
conditions; each surfaces as its own machine-readable blocker code so a
client can render exactly what stands between the reviewer and approval
instead of a generic "cannot approve".

The check and the state change run inside one FOR UPDATE-locked document
row, so approval is race-free against concurrent approvals: whichever
request locks first completes its eligibility check on data the second
cannot be simultaneously mutating.
"""

import decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Document, ExtractedField, User
from app.domain.enums import DocumentStatus, FieldReviewStatus
from app.errors import ApprovalBlockedException, NotFoundException, ValidationException
from app.services.audit import write_audit_log

# The field statuses that count as resolved for approval: a human either
# endorsed the machine value (accepted) or replaced it (corrected). A
# rejected required field is NOT resolved — the reviewer dismissed the
# value, so the required question still has no endorsed answer.
RESOLVED_FIELD_STATUSES: tuple[FieldReviewStatus, ...] = (
    FieldReviewStatus.ACCEPTED,
    FieldReviewStatus.CORRECTED,
)

# The statuses a document must hold before a human verdict is meaningful.
# Extraction must have finished and routed it to review; approving an
# "uploaded" or "queued" document would sign off data that does not exist yet.
REVIEWABLE_STATUSES: tuple[DocumentStatus, ...] = (
    DocumentStatus.NEEDS_REVIEW,
    DocumentStatus.READY_FOR_REVIEW,
)


def check_approval_eligibility(db: Session, document: Document) -> tuple[bool, list[str]]:
    """Report whether the document may be approved, and why not.

    Two blocking conditions, checked in order of severity:

    1. A required field is unresolved (pending, rejected, or missing):
       required fields are the fields the downstream consumer cannot live
       without, so an approval without them certifies an incomplete record.
    2. A low-confidence field is still pending: those are exactly the
       fields the pipeline flagged for human eyes; approving while one is
       unreviewed means the machine's guess silently became approved data.

    Args:
        db: The session to load the document's fields with.
        document: The document being checked.

    Returns:
        ``(eligible, blockers)``: True with an empty list when approvable;
        False with one ``"required_fields_unresolved"`` or
        ``"low_confidence_fields_unresolved"`` entry otherwise.
    """
    settings = get_settings()
    fields = list(
        db.execute(
            select(ExtractedField).where(ExtractedField.document_id == document.id)
        ).scalars()
    )

    required_unresolved = [
        f for f in fields if f.is_required and f.review_status not in RESOLVED_FIELD_STATUSES
    ]
    low_confidence_unresolved = [
        f
        for f in fields
        if f.confidence < decimal.Decimal(str(settings.CONFIDENCE_THRESHOLD))
        and f.review_status == FieldReviewStatus.PENDING
    ]

    if required_unresolved:
        return (False, ["required_fields_unresolved"])
    if low_confidence_unresolved:
        return (False, ["low_confidence_fields_unresolved"])
    return (True, [])


def _load_document_for_update_or_404(db: Session, user: User, document_id: str) -> Document:
    """Load one document row locked (FOR UPDATE), 404 when not owned.

    The lock is taken on the SELECT so the eligibility check that follows
    reads a row no concurrent approval or review edit can change while the
    verdict is being formed.
    """
    document = db.execute(
        select(Document)
        .where(
            Document.id == document_id,
            Document.organization_id == user.organization_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundException(details={"document_id": str(document_id)})
    return document


def approve_document(db: Session, user: User, document_id: str) -> Document:
    """Approve a document once every blocking condition is clear.

    Args:
        db: The request-scoped session (caller owns commit/rollback).
        user: The reviewer recording the approval.
        document_id: Path parameter document id.

    Returns:
        The updated document row (status=approved).

    Raises:
        NotFoundException: Document absent or outside the caller's org.
        ValidationException: Document is not in a reviewable status.
        ApprovalBlockedException: A blocking condition is unresolved.
    """
    document = _load_document_for_update_or_404(db, user, document_id)
    if document.status not in REVIEWABLE_STATUSES:
        raise ValidationException(details={"reason": "document_not_ready"})

    eligible, blockers = check_approval_eligibility(db, document)
    if not eligible:
        raise ApprovalBlockedException(details={"blockers": blockers})

    document.status = DocumentStatus.APPROVED
    db.flush()

    write_audit_log(
        db,
        user,
        action="document.approved",
        entity_type="document",
        entity_id=str(document.id),
        metadata={
            "document_id": str(document.id),
            "file_name": document.file_name,
            "reviewed_by": str(user.id),
        },
    )
    return document


def reject_document(
    db: Session, user: User, document_id: str, reason: str | None = None
) -> Document:
    """Reject a document: the human verdict that its extraction is unusable.

    Rejection has no eligibility gate beyond reviewability: the reviewer
    may reject at any point once the document has been routed to review,
    including with unresolved fields (rejecting is how they get resolved).

    Args:
        db: The request-scoped session (caller owns commit/rollback).
        user: The reviewer recording the rejection.
        document_id: Path parameter document id.
        reason: Optional explanation recorded with the action.

    Returns:
        The updated document row (status=rejected).

    Raises:
        NotFoundException: Document absent or outside the caller's org.
        ValidationException: Document is not in a reviewable status.
    """
    document = _load_document_for_update_or_404(db, user, document_id)
    if document.status not in REVIEWABLE_STATUSES:
        raise ValidationException(details={"reason": "document_not_ready"})

    document.status = DocumentStatus.REJECTED
    db.flush()

    write_audit_log(
        db,
        user,
        action="document.rejected",
        entity_type="document",
        entity_id=str(document.id),
        metadata={
            "document_id": str(document.id),
            "file_name": document.file_name,
            "reason": reason,
        },
    )
    return document

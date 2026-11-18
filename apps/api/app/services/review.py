"""Review service: human decisions on individually extracted fields.

The review state machine per field is
``pending -> accepted | corrected | rejected`` (terminal for this phase):
an accepted or corrected field carries a human-endorsed value, a rejected
field carries no value at all, and only ``pending`` may transition. Two
invariants make the trail worth reading later:

1. The machine's original value is never overwritten: the first human edit
   copies it into ``original_value_text`` BEFORE ``value_text`` changes, so
   the row simultaneously holds what the pipeline said and what the human
   said. Auditors and error analyses need the machine value after the fact.
2. Every decision writes a ``ReviewAction`` (the before/after pair, with a
   reason) and an audit row (the who/when/from-where) in the SAME
   transaction as the edit itself: commit together or not at all.

Edits run under ``SELECT ... FOR UPDATE`` so two reviewers opening the same
field at the same time serialize: the second request re-reads the state the
first committed and sees ``field_not_pending`` instead of silently
double-editing.
"""

import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, ExtractedField, ReviewAction, User
from app.domain.enums import FieldReviewStatus
from app.errors import NotFoundException, ValidationException
from app.services.audit import write_audit_log

# A field that already carries a terminal human verdict (accepted or
# rejected) cannot be edited again in this phase: corrections to a
# resolved field require a new review cycle, which is a deliberate
# workflow boundary, not an oversight. CORRECTED is deliberately absent:
# a correction may be superseded by a better correction, and each keeps
# only the machine value in original_value_text.
RESOLVED_STATUSES: tuple[FieldReviewStatus, ...] = (
    FieldReviewStatus.ACCEPTED,
    FieldReviewStatus.REJECTED,
)


def list_document_fields(db: Session, user: User, document_id: str) -> list[ExtractedField]:
    """Return every extracted field of one document, ordered by field_key.

    Ownership is the organization match, and a foreign document is a 404
    (same convention as every org-scoped read here): a 403 would confirm
    the document exists in another tenant.

    Args:
        db: The request-scoped session.
        user: The authenticated reader.
        document_id: Path parameter document id.

    Returns:
        All fields for the document, alphabetical by field_key so the
        review UI renders a stable order across polls.

    Raises:
        NotFoundException: Document absent or outside the caller's org.
    """
    document = db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == user.organization_id,
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundException(details={"document_id": str(document_id)})

    return list(
        db.execute(
            select(ExtractedField)
            .where(ExtractedField.document_id == document.id)
            .order_by(ExtractedField.field_key)
        ).scalars()
    )


def _load_field_for_update_or_404(db: Session, user: User, field_id: str) -> ExtractedField:
    """Load one field row locked (FOR UPDATE) and verify ownership.

    Shared by correct/accept/reject because the sequence is identical:
    lock the row, verify the org through the field's own organization_id
    (the column exists on the row; no join needed), 404 when absent. The
    lock is taken on the SELECT so the state check below it reads a row
    no concurrent transaction can be simultaneously editing.
    """
    field = db.execute(
        select(ExtractedField)
        .where(
            ExtractedField.id == field_id,
            ExtractedField.organization_id == user.organization_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if field is None:
        raise NotFoundException(details={"field_id": str(field_id)})
    return field


def _record_review(
    db: Session,
    user: User,
    field: ExtractedField,
    action: str,
    previous_value: dict[str, str | None] | None,
    new_value: dict[str, str | None] | None,
    reason: str | None,
) -> None:
    """Write the ReviewAction and audit rows for one field decision.

    Both rows are flushed in the caller's transaction: the decision, its
    before/after record, and its audit entry commit atomically.
    """
    db.add(
        ReviewAction(
            organization_id=field.organization_id,
            document_id=field.document_id,
            field_id=field.id,
            user_id=user.id,
            action=action,
            previous_value=previous_value,
            new_value=new_value,
            reason=reason,
        )
    )
    db.flush()
    write_audit_log(
        db,
        user,
        action=f"field.{action}",
        entity_type="extracted_field",
        entity_id=str(field.id),
        metadata={
            "field_key": field.field_key,
            "document_id": str(field.document_id),
            "old_value": previous_value,
            "new_value": new_value,
            "reason": reason,
        },
    )


def correct_field(
    db: Session, user: User, field_id: str, new_value: str, reason: str | None = None
) -> ExtractedField:
    """Correct a pending field's value, preserving the machine original.

    The first edit copies the pipeline's value into ``original_value_text``
    before overwriting ``value_text``; later edits on this phase's state
    machine never happen (resolved fields are terminal), so the preserved
    original is always the machine value, never a human intermediate.

    Args:
        db: The request-scoped session (caller owns commit/rollback).
        user: The reviewer performing the correction.
        field_id: Path parameter field id.
        new_value: The reviewer's replacement text value.
        reason: Optional explanation recorded with the action.

    Returns:
        The updated field row.

    Raises:
        NotFoundException: Field absent or outside the caller's org.
        ValidationException: Field already accepted or rejected.
    """
    field = _load_field_for_update_or_404(db, user, field_id)
    if field.review_status in RESOLVED_STATUSES:
        raise ValidationException(details={"reason": "field_already_resolved"})

    old_value = field.value_text
    # Only the FIRST correction preserves the machine value; a later
    # correction updates the human value while the original stays the
    # machine's, so the row always holds what the pipeline said.
    if field.review_status != FieldReviewStatus.CORRECTED:
        field.original_value_text = old_value
    field.value_text = new_value
    field.review_status = FieldReviewStatus.CORRECTED
    field.reviewed_by = user.id
    field.reviewed_at = datetime.datetime.now(tz=datetime.UTC)

    _record_review(
        db,
        user,
        field,
        action="corrected",
        previous_value={"value_text": old_value},
        new_value={"value_text": new_value},
        reason=reason,
    )
    return field


def accept_field(db: Session, user: User, field_id: str) -> ExtractedField:
    """Accept a pending field's machine value unchanged.

    Acceptance is the reviewer saying "the machine got it right"; no value
    changes, so ``original_value_text`` stays None — there is nothing human
    to distinguish from machine yet.

    Args:
        db: The request-scoped session (caller owns commit/rollback).
        user: The reviewer performing the acceptance.
        field_id: Path parameter field id.

    Returns:
        The updated field row.

    Raises:
        NotFoundException: Field absent or outside the caller's org.
        ValidationException: Field is not pending.
    """
    field = _load_field_for_update_or_404(db, user, field_id)
    if field.review_status != FieldReviewStatus.PENDING:
        raise ValidationException(details={"reason": "field_not_pending"})

    field.review_status = FieldReviewStatus.ACCEPTED
    field.reviewed_by = user.id
    field.reviewed_at = datetime.datetime.now(tz=datetime.UTC)

    _record_review(
        db, user, field, action="accepted", previous_value=None, new_value=None, reason=None
    )
    return field


def reject_field(
    db: Session, user: User, field_id: str, reason: str | None = None
) -> ExtractedField:
    """Reject a pending field: clear its value, preserve the machine original.

    A rejected field exports no value, but the machine's attempt is kept
    in ``original_value_text`` — the reviewer saw something, decided it was
    wrong, and the record of what it was stays queryable for extraction
    quality analysis. All typed value columns are cleared so a rejected
    field cannot leak a stale number/date/json into an export.

    Args:
        db: The request-scoped session (caller owns commit/rollback).
        user: The reviewer performing the rejection.
        field_id: Path parameter field id.
        reason: Optional explanation recorded with the action.

    Returns:
        The updated field row.

    Raises:
        NotFoundException: Field absent or outside the caller's org.
        ValidationException: Field is not pending.
    """
    field = _load_field_for_update_or_404(db, user, field_id)
    if field.review_status != FieldReviewStatus.PENDING:
        raise ValidationException(details={"reason": "field_not_pending"})

    old_value = field.value_text
    field.original_value_text = old_value
    field.value_text = None
    field.value_number = None
    field.value_json = None
    field.review_status = FieldReviewStatus.REJECTED
    field.reviewed_by = user.id
    field.reviewed_at = datetime.datetime.now(tz=datetime.UTC)

    _record_review(
        db,
        user,
        field,
        action="rejected",
        previous_value={"value_text": old_value},
        new_value={"value_text": None},
        reason=reason,
    )
    return field

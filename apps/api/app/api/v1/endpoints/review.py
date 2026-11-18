"""Review endpoints: the human-in-the-loop surface over HTTP.

Reading is broad (ADMIN, REVIEWER, UPLOADER, VIEWER — anyone trusted to
see the data); deciding is narrow (ADMIN, REVIEWER — the two roles whose
job is judgment). Every mutating endpoint commits before responding: the
service layer only flushes inside the caller's transaction, so the
endpoint is the transaction boundary where a review decision either
becomes durable together with its review_action and audit rows, or not
at all.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import RoleName
from app.schemas.documents import DocumentOut
from app.schemas.review import (
    CorrectFieldRequest,
    FieldOut,
    RejectDocumentRequest,
    RejectFieldRequest,
)
from app.services.approval import approve_document, reject_document
from app.services.review import (
    accept_field,
    correct_field,
    list_document_fields,
    reject_field,
)

router = APIRouter()


@router.get("/documents/{document_id}/fields", response_model=list[FieldOut])
def get_document_fields(
    document_id: str,
    user: User = Depends(  # noqa: B008
        require_roles(  # noqa: B008
            [RoleName.ADMIN, RoleName.REVIEWER, RoleName.UPLOADER, RoleName.VIEWER]
        )
    ),
    db: Session = Depends(get_db),  # noqa: B008
) -> list[FieldOut]:
    """List every extracted field of one document with its review status.

    The review screen's primary read: the reviewer sees all fields, their
    machine values, confidences, and which still need a decision.
    """
    return [FieldOut.model_validate(field) for field in list_document_fields(db, user, document_id)]


@router.patch("/fields/{field_id}", response_model=FieldOut)
def patch_field(
    field_id: str,
    req: CorrectFieldRequest,
    user: User = Depends(require_roles([RoleName.ADMIN, RoleName.REVIEWER])),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> FieldOut:
    """Correct one field's value, preserving the machine original.

    The service locks the field row, copies the machine value into
    ``original_value_text``, applies the reviewer's replacement, and writes
    the review_action and audit rows in the same transaction this endpoint
    commits.
    """
    field = correct_field(db, user, field_id, req.value, req.reason)
    db.commit()
    return FieldOut.model_validate(field)


@router.post("/fields/{field_id}/accept", response_model=FieldOut)
def post_accept_field(
    field_id: str,
    user: User = Depends(require_roles([RoleName.ADMIN, RoleName.REVIEWER])),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> FieldOut:
    """Accept one field's machine value unchanged.

    Acceptance is a decision without an edit; it exists as its own endpoint
    so the audit trail distinguishes "the human endorsed the machine" from
    "the human replaced the machine".
    """
    field = accept_field(db, user, field_id)
    db.commit()
    return FieldOut.model_validate(field)


@router.post("/fields/{field_id}/reject", response_model=FieldOut)
def post_reject_field(
    field_id: str,
    req: RejectFieldRequest,
    user: User = Depends(require_roles([RoleName.ADMIN, RoleName.REVIEWER])),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> FieldOut:
    """Reject one field: clear its value, keep the machine original.

    The cleared value keeps rejected fields out of exports by data, not
    by filtering: there is simply nothing to export for a rejected field.
    """
    field = reject_field(db, user, field_id, req.reason)
    db.commit()
    return FieldOut.model_validate(field)


@router.post("/documents/{document_id}/approve", response_model=DocumentOut)
def post_approve_document(
    document_id: str,
    user: User = Depends(require_roles([RoleName.ADMIN, RoleName.REVIEWER])),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> DocumentOut:
    """Approve a document after its blocking conditions are all clear.

    The eligibility check runs inside the document's FOR UPDATE lock, so
    the verdict is formed on data that cannot be concurrently edited.
    """
    document = approve_document(db, user, document_id)
    db.commit()
    return DocumentOut.model_validate(document)


@router.post("/documents/{document_id}/reject", response_model=DocumentOut)
def post_reject_document(
    document_id: str,
    req: RejectDocumentRequest,
    user: User = Depends(require_roles([RoleName.ADMIN, RoleName.REVIEWER])),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> DocumentOut:
    """Reject a document: mark its extraction unusable for export.

    The optional reason travels into the audit row verbatim, so the
    rejection can be explained months later without guessing.
    """
    document = reject_document(db, user, document_id, req.reason)
    db.commit()
    return DocumentOut.model_validate(document)

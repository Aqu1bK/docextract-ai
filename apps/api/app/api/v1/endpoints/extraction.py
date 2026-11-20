# docextract-ai/apps/api/app/api/v1/endpoints/extraction.py

"""Extraction status endpoint: the client's window onto the queue.

One route, GET /documents/{document_id}/extraction-status. It joins the
two rows a polling client needs — the document's own status and its
latest job row — so the same response renders "queued, waiting" ,
"processing" , "needs_review, done" , and "failed with code X". Ownership
is the organization match: a document outside the caller's org is a 404
(just like every other org-scoped read here), never a 403 that confirms
existence.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.db.models import Document, ExtractionJob, User
from app.db.session import get_db
from app.domain.enums import RoleName
from app.errors import NotFoundException
from app.schemas.jobs import ExtractionStatusResponse

router = APIRouter()


@router.get("/documents/{document_id}/extraction-status", response_model=ExtractionStatusResponse)
def get_extraction_status(
    document_id: str,
    user: User = Depends(require_roles([RoleName.ADMIN, RoleName.REVIEWER, RoleName.UPLOADER])),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ExtractionStatusResponse:
    """Return the document's status and its latest extraction job.

    The latest job is the newest by created_at (not the active one):
    a document with a FAILED history followed by a fresh PENDING job
    must report the retry in flight, and a document that was re-extracted
    reports the run that produced its current data.
    """
    document = db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == user.organization_id,
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundException(details={"document_id": str(document_id)})

    latest_job = db.execute(
        select(ExtractionJob)
        .where(ExtractionJob.document_id == document.id)
        .order_by(ExtractionJob.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    return ExtractionStatusResponse(
        document_status=document.status,
        latest_job=latest_job,
    )

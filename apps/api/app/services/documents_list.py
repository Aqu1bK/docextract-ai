"""List documents for the signed-in user's organization (GET /documents).

A read-only query with two rules baked in:

1. **Org scoping is the tenancy boundary.** The WHERE clause on
   ``organization_id`` is the only isolation this product needs — one
   shared database, many organizations, and no document row ever
   crossing between them. The roles dependency on the endpoint has
   already established identity; scoping here trusts nothing the client
   sent about which org's documents it wants.

2. **The count and the page come from the same transaction.** A separate
   count endpoint would answer "total: 42" from a moment that can differ
   from the moment the page's 20 rows were read; one transaction means
   one consistent answer, which is what a paginator renders.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Document, User
from app.schemas.documents_list import DocumentsListOut, DocumentsListQuery


def list_documents(db: Session, user: User, query: DocumentsListQuery) -> DocumentsListOut:
    """Return one page of the organization's documents, newest first.

    Newest-first is the review queue's working order: the document a
    reviewer most needs to see is the one that arrived last, and the
    ``ix_documents_organization_id_created_at DESC`` index serves exactly
    this ordering without a sort.
    """
    org_filter = Document.organization_id == user.organization_id

    count_query = select(func.count()).select_from(Document).where(org_filter)
    count_row = db.execute(count_query).scalar_one()
    rows = (
        db.execute(
            select(Document)
            .where(org_filter)
            .order_by(Document.created_at.desc(), Document.id.desc())
            .offset(query.skip)
            .limit(query.limit)
        )
        .scalars()
        .all()
    )

    return DocumentsListOut(documents=rows, total=count_row)
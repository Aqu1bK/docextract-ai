"""Read models for the documents list (GET /documents).

Phase 9B's first read surface: the web app's Documents page. The list
needs pagination (``skip``/``limit``) and a total, so a client can render
"page 2 of 7" from one response instead of a follow-up count request.
"""

import pydantic

from app.schemas.documents import DocumentOut


class DocumentsListQuery(pydantic.BaseModel):
    """Pagination parameters for the documents list.

    The clamp keeps ``limit`` within the 1–100 window this API offers: a
    client asking for a million rows gets 100, not a database strain —
    and ``skip`` stays non-negative so a negative offset never silently
    becomes a database-side offset of the wrong sign.
    """

    skip: int = pydantic.Field(default=0, ge=0)
    limit: int = pydantic.Field(default=20, ge=1, le=100)


class DocumentsListOut(pydantic.BaseModel):
    """One page of documents plus the total row count.

    ``documents`` reuses :class:`DocumentOut` — the same shape the upload
    flow returns — so a client renders one document model everywhere
    (upload response, list row, future detail page).
    """

    documents: list[DocumentOut]
    total: int
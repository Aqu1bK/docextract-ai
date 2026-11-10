# docextract-ai/apps/api/app/db/models/__init__.py

"""SQLAlchemy model packages re-exported for Alembic and the app.

Importing every model module here ensures all tables register on the shared
``Base.metadata`` the moment ``app.db.models`` is imported — which
``alembic/env.py`` does — so autogenerate and the initial migration always
see the complete schema, not whichever modules happened to be loaded.
"""

from app.db.models.core import Organization, Role, Setting, User, UserRole
from app.db.models.documents import Document, DocumentPage
from app.db.models.extraction import ExtractedField, ExtractedTable, ExtractionJob
from app.db.models.governance import (
    AuditLog,
    Export,
    ReviewAction,
    UsageLimit,
)

__all__ = [
    "AuditLog",
    "Document",
    "DocumentPage",
    "Export",
    "ExtractionJob",
    "ExtractedField",
    "ExtractedTable",
    "Organization",
    "ReviewAction",
    "Role",
    "Setting",
    "UsageLimit",
    "User",
    "UserRole",
]

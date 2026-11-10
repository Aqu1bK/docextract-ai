# docextract-ai/apps/api/app/domain/enums.py

"""Domain enums: the closed vocabularies of DocExtract AI.

These enums live in ``app.domain``, outside the SQLAlchemy models in
``app.db.models``, on purpose. Pydantic response schemas (Phase 4+), the
database models, and future worker code all need the exact same value sets,
and if the models owned the enums, importing them from a schema module would
drag the whole ORM (and its engine) into every import chain. A shared
vocabulary module keeps the dependency graph flat: schemas, models, and
migrations all import ``app.domain.enums`` and nothing else.

Each class subclasses ``str`` as well as ``Enum`` (``StrEnum``, Python 3.11+)
so every member IS its own string value: serialization, logging, and
SQLAlchemy column values all use the same literal without a conversion layer.
"""

from enum import StrEnum


class RoleName(StrEnum):
    """The four roles a user can hold inside an organization."""

    ADMIN = "admin"
    REVIEWER = "reviewer"
    UPLOADER = "uploader"
    VIEWER = "viewer"


class DocumentStatus(StrEnum):
    """Lifecycle of a document from upload through review to archive."""

    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    ARCHIVED = "archived"


class JobStatus(StrEnum):
    """Lifecycle of an extraction job on the PostgreSQL queue."""

    PENDING = "pending"
    LEASED = "leased"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY_SCHEDULED = "retry_scheduled"


class FieldReviewStatus(StrEnum):
    """Review state of one extracted field or table."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    CORRECTED = "corrected"
    REJECTED = "rejected"
    MISSING = "missing"


class ExportFormat(StrEnum):
    """Supported export output formats."""

    JSON = "json"
    CSV = "csv"


class ExportStatus(StrEnum):
    """Lifecycle of an export request."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

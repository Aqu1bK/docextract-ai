# docextract-ai/apps/api/app/db/models/extraction.py

"""Extraction pipeline tables: extraction_jobs, extracted_fields, extracted_tables.

``extraction_jobs`` is the PostgreSQL queue row a worker claims (Phase 7);
``extracted_fields`` and ``extracted_tables`` are what the job produced and
what reviewers edit (Phase 8). Phase 3 only defines their shape.
"""

import datetime
import decimal
import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import FieldReviewStatus, JobStatus


class ExtractionJob(Base):
    """One queued extraction run for one document.

    The row doubles as the queue entry: a worker claims it by setting
    ``status``/``leased_at``/``leased_by`` (Phase 7 uses SKIP LOCKED).
    ``attempts`` counts tries; ``scheduled_at`` is when the next try may run.
    """

    __tablename__ = "extraction_jobs"
    __table_args__ = (
        sa.UniqueConstraint("document_id", "idempotency_key"),
        sa.Index("ix_extraction_jobs_status_scheduled_at", "status", "scheduled_at"),
        sa.Index("ix_extraction_jobs_document_id", "document_id"),
        sa.Index(
            "ix_extraction_jobs_organization_id_created_at",
            "organization_id",
            sa.text("created_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("organizations.id"))
    document_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("documents.id", ondelete="CASCADE")
    )
    idempotency_key: Mapped[str] = mapped_column(sa.String(64))
    status: Mapped[JobStatus] = mapped_column(
        sa.Enum(JobStatus, native_enum=False, length=32),
        server_default=JobStatus.PENDING.value,
    )
    mode: Mapped[str] = mapped_column(sa.String(32))
    provider: Mapped[str | None] = mapped_column(sa.String(32))
    parser: Mapped[str | None] = mapped_column(sa.String(32))
    pipeline_version: Mapped[str] = mapped_column(sa.String(32))
    prompt_version: Mapped[str | None] = mapped_column(sa.String(32))
    schema_version: Mapped[str] = mapped_column(sa.String(32))
    priority: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("100"))
    attempts: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"))
    max_attempts: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("3"))
    scheduled_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    leased_at: Mapped[datetime.datetime | None] = mapped_column(sa.DateTime(timezone=True))
    leased_by: Mapped[str | None] = mapped_column(sa.String(128))
    started_at: Mapped[datetime.datetime | None] = mapped_column(sa.DateTime(timezone=True))
    completed_at: Mapped[datetime.datetime | None] = mapped_column(sa.DateTime(timezone=True))
    failed_at: Mapped[datetime.datetime | None] = mapped_column(sa.DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(sa.String(100))
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    result_metadata: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, server_default=sa.text("'{}'::jsonb")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class ExtractedField(Base):
    """One key/value the pipeline pulled out of a document.

    The typed value columns (``value_text``/``value_number``/``value_date``/
    ``value_json``) keep one value per declared type; ``confidence`` decides
    review routing (below CONFIDENCE_THRESHOLD -> needs_review).
    ``original_value_text`` preserves the machine value after a correction.
    """

    __tablename__ = "extracted_fields"
    __table_args__ = (
        sa.UniqueConstraint("document_id", "job_id", "field_key"),
        sa.Index("ix_extracted_fields_document_id_review_status", "document_id", "review_status"),
        sa.Index("ix_extracted_fields_job_id", "job_id"),
        sa.Index("ix_extracted_fields_organization_id", "organization_id"),
        sa.Index("ix_extracted_fields_reviewed_by", "reviewed_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("organizations.id"))
    document_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("documents.id", ondelete="CASCADE")
    )
    job_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("extraction_jobs.id"))
    field_key: Mapped[str] = mapped_column(sa.String(100))
    field_label: Mapped[str] = mapped_column(sa.String(255))
    value_text: Mapped[str | None] = mapped_column(sa.Text)
    value_number: Mapped[decimal.Decimal | None] = mapped_column(sa.Numeric(12, 2))
    value_date: Mapped[datetime.date | None] = mapped_column(sa.Date)
    value_json: Mapped[dict[str, Any] | None] = mapped_column(postgresql.JSONB)
    confidence: Mapped[decimal.Decimal] = mapped_column(sa.Numeric(5, 4))
    source: Mapped[str] = mapped_column(sa.String(32))
    page_number: Mapped[int | None] = mapped_column(sa.Integer)
    bbox: Mapped[dict[str, Any] | None] = mapped_column(postgresql.JSONB)
    evidence_span: Mapped[str | None] = mapped_column(sa.Text)
    review_status: Mapped[FieldReviewStatus] = mapped_column(
        sa.Enum(FieldReviewStatus, native_enum=False, length=32),
        server_default=FieldReviewStatus.PENDING.value,
    )
    original_value_text: Mapped[str | None] = mapped_column(sa.Text)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid, sa.ForeignKey("users.id"))
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(sa.DateTime(timezone=True))
    is_required: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class ExtractedTable(Base):
    """One table the pipeline extracted, as headers plus row records.

    ``headers_json``/``rows_json`` keep arbitrary column shapes (invoices,
    receipts, bank statements) without a per-document schema migration.
    """

    __tablename__ = "extracted_tables"
    __table_args__ = (
        sa.UniqueConstraint("document_id", "job_id", "table_index"),
        sa.Index("ix_extracted_tables_organization_id", "organization_id"),
        sa.Index("ix_extracted_tables_job_id", "job_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("organizations.id"))
    document_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("documents.id", ondelete="CASCADE")
    )
    job_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("extraction_jobs.id"))
    table_index: Mapped[int] = mapped_column(sa.Integer)
    title: Mapped[str | None] = mapped_column(sa.String(255))
    page_number: Mapped[int | None] = mapped_column(sa.Integer)
    confidence: Mapped[decimal.Decimal] = mapped_column(sa.Numeric(5, 4))
    headers_json: Mapped[list[Any]] = mapped_column(postgresql.JSONB)
    rows_json: Mapped[list[list[Any]]] = mapped_column(postgresql.JSONB)
    bbox: Mapped[dict[str, Any] | None] = mapped_column(postgresql.JSONB)
    source: Mapped[str] = mapped_column(sa.String(32))
    review_status: Mapped[FieldReviewStatus] = mapped_column(
        sa.Enum(FieldReviewStatus, native_enum=False, length=32),
        server_default=FieldReviewStatus.PENDING.value,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )

# docextract-ai/apps/api/app/db/models/governance.py

"""Governance tables: review_actions, audit_logs, exports, usage_limits.

These four tables record what humans decided, what the system did, what left
the platform, and how much of it — the accountability layer regulators and
auditors ask for.
"""

import datetime
import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import ExportFormat, ExportStatus


class ReviewAction(Base):
    """One human decision during review: approve, reject, or correct.

    ``previous_value``/``new_value`` capture before/after JSON so any edit is
    reversible in audit terms; ``field_id``/``table_id`` say what was acted
    on, and both are nullable because document-level decisions exist too.
    """

    __tablename__ = "review_actions"
    __table_args__ = (
        sa.Index("ix_review_actions_organization_id", "organization_id"),
        sa.Index("ix_review_actions_document_id", "document_id"),
        sa.Index("ix_review_actions_field_id", "field_id"),
        sa.Index("ix_review_actions_table_id", "table_id"),
        sa.Index("ix_review_actions_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("organizations.id"))
    document_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("documents.id", ondelete="CASCADE")
    )
    field_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("extracted_fields.id")
    )
    table_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("extracted_tables.id")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid, sa.ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(sa.String(32))
    previous_value: Mapped[dict[str, Any] | None] = mapped_column(postgresql.JSONB)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(postgresql.JSONB)
    reason: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )


class AuditLog(Base):
    """Append-only trail of system and human actions.

    The contract is APPEND-ONLY: nothing updates or deletes these rows at the
    application level — history is written once and queried, never edited,
    so the trail an auditor sees is the trail that happened. Rows record who
    acted (``actor_user_id``), on what (``entity_type``/``entity_id``), how
    (``action``), and with what context (``metadata_json``, ``ip_address``,
    ``user_agent``).
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        sa.Index(
            "ix_audit_logs_organization_id_created_at",
            "organization_id",
            sa.text("created_at DESC"),
        ),
        sa.Index("ix_audit_logs_entity_type_entity_id", "entity_type", "entity_id"),
        sa.Index("ix_audit_logs_action", "action"),
        sa.Index("ix_audit_logs_actor_user_id", "actor_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("organizations.id"))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid, sa.ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(sa.String(64))
    entity_type: Mapped[str] = mapped_column(sa.String(64))
    entity_id: Mapped[str] = mapped_column(sa.String(64))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, server_default=sa.text("'{}'::jsonb")
    )
    ip_address: Mapped[str | None] = mapped_column(sa.String(45))
    user_agent: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )


class Export(Base):
    """One export request and its outcome (Phase 8 fills these rows).

    ``expires_at`` marks when the stored export file is deleted; retention
    policy in a later phase sweeps expired paths.
    """

    __tablename__ = "exports"
    __table_args__ = (
        sa.Index("ix_exports_organization_id", "organization_id"),
        sa.Index("ix_exports_document_id", "document_id"),
        sa.Index("ix_exports_requested_by", "requested_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("organizations.id"))
    document_id: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid, sa.ForeignKey("documents.id"))
    requested_by: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid, sa.ForeignKey("users.id"))
    format: Mapped[ExportFormat] = mapped_column(
        sa.Enum(ExportFormat, native_enum=False, length=32)
    )
    status: Mapped[ExportStatus] = mapped_column(
        sa.Enum(ExportStatus, native_enum=False, length=32),
        server_default=ExportStatus.PENDING.value,
    )
    row_count: Mapped[int | None] = mapped_column(sa.Integer)
    storage_path: Mapped[str | None] = mapped_column(sa.String(500))
    expires_at: Mapped[datetime.datetime | None] = mapped_column(sa.DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(sa.DateTime(timezone=True))


class UsageLimit(Base):
    """Per-user, per-day counters backing the free-tier quota enforcement.

    One row per user per day: the composite primary key is also the lookup
    key, so increment-or-insert is a single upsert in the phase that uses it.
    """

    __tablename__ = "usage_limits"

    user_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("users.id"), primary_key=True)
    usage_date: Mapped[datetime.date] = mapped_column(sa.Date, primary_key=True)
    upload_count: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"))
    extraction_count: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"))
    real_extraction_count: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"))
    export_count: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"))

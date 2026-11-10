# docextract-ai/apps/api/app/db/models/documents.py

"""Uploaded document storage tables: documents and document_pages.

``documents`` is the upload record and status lifecycle; ``document_pages``
holds per-page knowledge (text presence, OCR need, geometry) used by the
extraction engine in Phase 6.
"""

import datetime
import decimal
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import DocumentStatus


class Document(Base):
    """One uploaded file and its review lifecycle.

    Status moves uploaded -> queued -> processing -> needs_review ->
    ready_for_review -> approved/rejected, with failed and archived as
    terminal side exits. ``deleted_at`` is a soft-delete marker so audit
    history can outlive the visible record.
    """

    __tablename__ = "documents"
    __table_args__ = (
        sa.Index("ix_documents_organization_id_status", "organization_id", "status"),
        sa.Index(
            "ix_documents_organization_id_created_at",
            "organization_id",
            sa.text("created_at DESC"),
        ),
        sa.Index("ix_documents_sha256", "sha256"),
        sa.Index("ix_documents_uploaded_by", "uploaded_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("organizations.id"))
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid, sa.ForeignKey("users.id"))
    file_name: Mapped[str] = mapped_column(sa.String(255))
    content_type: Mapped[str] = mapped_column(sa.String(100))
    sha256: Mapped[str] = mapped_column(sa.String(64))
    size_bytes: Mapped[int] = mapped_column(sa.BigInteger)
    page_count: Mapped[int | None] = mapped_column(sa.Integer)
    storage_path: Mapped[str] = mapped_column(sa.String(500))
    document_type: Mapped[str | None] = mapped_column(sa.String(50))
    document_type_confidence: Mapped[decimal.Decimal | None] = mapped_column(sa.Numeric(5, 4))
    parsing_mode: Mapped[str] = mapped_column(sa.String(32), server_default="pending")
    status: Mapped[DocumentStatus] = mapped_column(
        sa.Enum(DocumentStatus, native_enum=False, length=32),
        server_default=DocumentStatus.UPLOADED.value,
    )
    error_code: Mapped[str | None] = mapped_column(sa.String(100))
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    is_sample: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    retention_until: Mapped[datetime.datetime | None] = mapped_column(sa.DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(sa.DateTime(timezone=True))


class DocumentPage(Base):
    """Per-page facts for one document.

    ``has_text``/``is_scanned`` decide whether the Phase 6 extraction engine
    can read the page as text or must render it for the Vision LLM;
    ``text_content`` caches the extracted text so re-runs do not re-parse.
    """

    __tablename__ = "document_pages"
    __table_args__ = (sa.UniqueConstraint("document_id", "page_number"),)

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("documents.id", ondelete="CASCADE")
    )
    page_number: Mapped[int] = mapped_column(sa.Integer)
    has_text: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    is_scanned: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    text_content: Mapped[str | None] = mapped_column(sa.Text)
    width: Mapped[decimal.Decimal | None] = mapped_column(sa.Numeric)
    height: Mapped[decimal.Decimal | None] = mapped_column(sa.Numeric)
    ocr_status: Mapped[str] = mapped_column(sa.String(32), server_default="not_required")
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

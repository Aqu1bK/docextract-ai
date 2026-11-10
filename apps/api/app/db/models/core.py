# docextract-ai/apps/api/app/db/models/core.py

"""Core identity tables: organizations, roles, users, user_roles, settings.

These five tables answer "who is here and what may they do?" before any
document exists. Later phases hang documents, jobs, and audit rows off the
organization and user rows created here.
"""

import datetime
import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Organization(Base):
    """The tenant that owns every document, job, and export in the system.

    Multi-tenant from day one: every business table carries an
    ``organization_id`` so row-level scoping is a query filter, not a
    redesign.
    """

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(sa.String(255))
    slug: Mapped[str] = mapped_column(sa.String(100), unique=True)
    settings_json: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, server_default=sa.text("'{}'::jsonb")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class Role(Base):
    """A named permission role; membership is stored in ``user_roles``."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(sa.String(32), unique=True)
    description: Mapped[str | None] = mapped_column(sa.String(255))
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )


class User(Base):
    """A person in one organization; authentication arrives in Phase 4.

    ``email`` is unique per organization, not globally: two organizations may
    hold a person with the same address without collision.
    """

    __tablename__ = "users"
    __table_args__ = (sa.UniqueConstraint("organization_id", "email"),)

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("organizations.id"))
    email: Mapped[str] = mapped_column(sa.String(255))
    full_name: Mapped[str] = mapped_column(sa.String(255))
    is_active: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("true"))
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class UserRole(Base):
    """Assignment of one role to one user; the RBAC join table (Phase 4)."""

    __tablename__ = "user_roles"
    __table_args__ = (
        sa.Index("ix_user_roles_role_id", "role_id"),
        sa.Index("ix_user_roles_assigned_by", "assigned_by"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("roles.id"), primary_key=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid, sa.ForeignKey("users.id"))
    assigned_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )


class Setting(Base):
    """One organization-level configuration key; overrides defaults.

    Phase 3 seeds ``demo_mode_enabled`` here; the demo banner and mock-mode
    behavior read it in later phases.
    """

    __tablename__ = "organization_settings"
    __table_args__ = (sa.Index("ix_organization_settings_updated_by", "updated_by"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("organizations.id"), primary_key=True
    )
    key: Mapped[str] = mapped_column(sa.String(100), primary_key=True)
    value_json: Mapped[dict[str, Any]] = mapped_column(postgresql.JSONB)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid, sa.ForeignKey("users.id"))
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

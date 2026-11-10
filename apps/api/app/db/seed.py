# docextract-ai/apps/api/app/db/seed.py

"""Idempotent seed for the demo organization, roles, and demo users.

Running ``make seed`` twice must leave exactly one demo organization, four
roles, four users, and four user_roles links: every insert is an upsert on
the natural key (``organizations.slug``, ``roles.name``, ``users.email``),
so a re-run updates in place or does nothing — never duplicates and never
errors.

Supabase Auth demo accounts are created manually in Phase 4 and matched to
these rows by email; the seed only owns the database side of that pairing.
"""

import argparse

import structlog
from sqlalchemy import Connection, select, text
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Session

from app.db.models import Organization, Role, Setting, User, UserRole

DEMO_ORG_SLUG = "demo-org"
DEMO_ORG_NAME = "Demo Organization"

ROLES = (
    ("admin", "Full administrative access"),
    ("reviewer", "Reviews and corrects extracted fields"),
    ("uploader", "Uploads documents and monitors jobs"),
    ("viewer", "Read-only access to approved data"),
)

DEMO_USERS = (
    ("admin@demo.docextract.ai", "Demo Admin", "admin"),
    ("reviewer@demo.docextract.ai", "Demo Reviewer", "reviewer"),
    ("uploader@demo.docextract.ai", "Demo Uploader", "uploader"),
    ("viewer@demo.docextract.ai", "Demo Viewer", "viewer"),
)

# Children first: no foreign key is left pointing at a row being deleted.
TRUNCATE_ORDER = (
    "review_actions",
    "extracted_fields",
    "extracted_tables",
    "extraction_jobs",
    "exports",
    "audit_logs",
    "usage_limits",
    "organization_settings",
    "user_roles",
    "users",
    "roles",
    "documents",
    "document_pages",
    "organizations",
)


def seed(session: Session) -> None:
    """Upsert the demo data set; safe to run any number of times.

    Args:
        session: A session bound to the migrated database.
    """
    # Organization first: roles, users, and the setting all reference it.
    org_stmt = pg.insert(Organization).values(
        name=DEMO_ORG_NAME,
        slug=DEMO_ORG_SLUG,
        settings_json={},
    )
    org_stmt = org_stmt.on_conflict_do_update(
        constraint="uq_organizations_slug",
        set_={"name": org_stmt.excluded.name},
    )
    session.execute(org_stmt)
    org_id = session.execute(
        select(Organization.id).where(Organization.slug == DEMO_ORG_SLUG)
    ).scalar_one()

    # Roles second: users link to them via user_roles.
    role_stmt = pg.insert(Role).on_conflict_do_nothing(constraint="uq_roles_name")
    session.execute(
        role_stmt,
        [{"name": name, "description": description} for name, description in ROLES],
    )
    role_ids: dict[str, object] = {
        role_name: role_id
        for role_name, role_id in session.execute(select(Role.name, Role.id)).all()
    }

    # Users third: looked up by email for FK references; UUIDs are DB-generated.
    # The naming convention's "column_0_name" rule truncates multi-column
    # names, so the live constraint is uq_users_organization_id.
    user_stmt = pg.insert(User).on_conflict_do_nothing(constraint="uq_users_organization_id")
    session.execute(
        user_stmt,
        [
            {
                "organization_id": org_id,
                "email": email,
                "full_name": full_name,
                "is_active": True,
            }
            for email, full_name, _role_name in DEMO_USERS
        ],
    )

    # user_roles last: composite PK (user_id, role_id) dedupes re-runs.
    user_ids = {
        email: user_id
        for user_id, email in session.execute(
            select(User.id, User.email).where(User.organization_id == org_id)
        ).all()
    }
    user_role_stmt = pg.insert(UserRole).on_conflict_do_nothing()
    session.execute(
        user_role_stmt,
        [
            {"user_id": user_ids[email], "role_id": role_ids[role_name]}
            for email, _full_name, role_name in DEMO_USERS
        ],
    )

    # Org settings: demo_mode_enabled=true, upserted on the composite PK.
    setting_stmt = pg.insert(Setting).values(
        organization_id=org_id,
        key="demo_mode_enabled",
        value_json={"value": True},
    )
    setting_stmt = setting_stmt.on_conflict_do_update(
        constraint="pk_organization_settings",
        set_={"value_json": setting_stmt.excluded.value_json},
    )
    session.execute(setting_stmt)


def reset_demo(session: Session) -> None:
    """Truncate all 14 tables in child-first order, then re-seed.

    Children are truncated before parents so no foreign key blocks a delete.
    ``TRUNCATE`` (not DELETE) also resets identity-free sequences and is one
    fast statement per table; RESTART IDENTITY keeps this future-proof for
    any serial column later phases introduce.
    """
    _truncate_tables(session.connection())
    seed(session)


def _truncate_tables(connection: Connection) -> None:
    """(Internal) run TRUNCATE ... RESTART IDENTITY in TRUNCATE_ORDER."""
    for table in TRUNCATE_ORDER:
        connection.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY'))


def main(argv: list[str] | None = None) -> None:
    """CLI entry point: plain seed, ``--demo``, or ``--reset-demo``.

    ``--demo`` is accepted as the documented default behavior: it seeds the
    same demo data set as a bare invocation, because at Phase 3 the demo
    data IS the only data.
    """
    parser = argparse.ArgumentParser(description="Seed the DocExtract AI demo data.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--demo", action="store_true", help="Seed demo data (default).")
    group.add_argument("--reset-demo", action="store_true", help="Truncate tables, then re-seed.")
    args = parser.parse_args(argv)

    # Imported here so module import stays cheap for tests that only need
    # the seed() function and never a live engine.
    from app.db.session import SessionLocal

    logger = structlog.get_logger(__name__)
    session = SessionLocal()
    try:
        if args.reset_demo:
            reset_demo(session)
            action = "reset-demo"
        else:
            seed(session)
            action = "seed"
        session.commit()
        logger.info(
            "seed_completed",
            action=action,
            organization=DEMO_ORG_SLUG,
            roles=len(ROLES),
            users=len(DEMO_USERS),
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()

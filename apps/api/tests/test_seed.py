# docextract-ai/apps/api/tests/test_seed.py

"""Seed tests: running the seed twice must not duplicate rows.

The two-run structure is the whole point: the first run inserts, the
second run proves every upsert held (on-conflict on the natural keys), and
the counts after run two are the acceptance numbers from the phase spec.
"""

import pytest
from sqlalchemy import func, select

from app.db.models import Organization, Role, Setting, User, UserRole
from app.db.seed import seed


def test_seed_twice_is_idempotent(db_session) -> None:
    """Two seed runs leave one org, four roles, four users, four user_roles."""
    seed(db_session)
    db_session.commit()

    seed(db_session)
    db_session.commit()

    def count(model: object) -> int:
        return db_session.execute(select(func.count()).select_from(model)).scalar_one()

    assert count(Organization) == 1
    assert count(Role) == 4
    assert count(User) == 4
    assert count(UserRole) == 4


def test_seed_sets_demo_mode_enabled(db_session) -> None:
    """The org settings row demo_mode_enabled=true exists after seeding."""
    seed(db_session)
    db_session.commit()

    value_json = db_session.execute(
        select(Setting.value_json).where(Setting.key == "demo_mode_enabled")
    ).scalar_one()
    assert value_json == {"value": True}


def test_seed_users_have_expected_emails(db_session) -> None:
    """The four demo users exist with the demo emails and are active."""
    seed(db_session)
    db_session.commit()

    rows = db_session.execute(select(User.email, User.is_active).order_by(User.email)).all()
    assert [email for email, _ in rows] == [
        "admin@demo.docextract.ai",
        "reviewer@demo.docextract.ai",
        "uploader@demo.docextract.ai",
        "viewer@demo.docextract.ai",
    ]
    assert all(is_active for _email, is_active in rows)


def test_seed_links_each_user_to_one_role(db_session) -> None:
    """Each demo user is linked to exactly the one role from the seed data."""
    seed(db_session)
    db_session.commit()

    pairs = db_session.execute(
        select(User.email, Role.name)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .order_by(User.email)
    ).all()
    assert pairs == [
        ("admin@demo.docextract.ai", "admin"),
        ("reviewer@demo.docextract.ai", "reviewer"),
        ("uploader@demo.docextract.ai", "uploader"),
        ("viewer@demo.docextract.ai", "viewer"),
    ]


@pytest.mark.parametrize(
    "email,full_name",
    [
        ("admin@demo.docextract.ai", "Demo Admin"),
        ("reviewer@demo.docextract.ai", "Demo Reviewer"),
        ("uploader@demo.docextract.ai", "Demo Uploader"),
        ("viewer@demo.docextract.ai", "Demo Viewer"),
    ],
)
def test_seed_full_names(db_session, email: str, full_name: str) -> None:
    """Each demo user carries the documented full name."""
    seed(db_session)
    db_session.commit()

    stored = db_session.execute(select(User.full_name).where(User.email == email)).scalar_one()
    assert stored == full_name

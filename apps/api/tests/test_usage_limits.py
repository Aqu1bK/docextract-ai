# docextract-ai/apps/api/tests/test_usage_limits.py

"""Unit tests for the daily upload quota and its row lock.

The quota is a real ``usage_limits`` row per user per day, so these tests
run against the shared test database and roll back like every other
database test — the counter behavior, not the lock implementation, is
what matters here. Users are seeded through ``seed_test_user`` because the
``user_id`` foreign key demands a real users row.
"""

from sqlalchemy import select

from app.db.models import UsageLimit
from app.errors import RateLimitException
from app.services.usage import check_and_increment_uploads


class TestCheckAndIncrementUploads:
    """Counter arithmetic and refusal at the limit."""

    def test_first_increment_returns_one(self, db_session, seed_test_user) -> None:
        """A first-of-day upload creates the row at 1."""
        user = seed_test_user("quota-a@t.dev")
        assert check_and_increment_uploads(db_session, user.id, daily_limit=10) == 1

    def test_second_increment_returns_two(self, db_session, seed_test_user) -> None:
        """Sequential increments count up from the same row."""
        user = seed_test_user("quota-b@t.dev")
        first = check_and_increment_uploads(db_session, user.id, daily_limit=10)
        second = check_and_increment_uploads(db_session, user.id, daily_limit=10)
        assert (first, second) == (1, 2)

    def test_limit_reached_raises(self, db_session, seed_test_user) -> None:
        """With daily_limit=1, the second call refuses with 429."""
        user = seed_test_user("quota-c@t.dev")
        check_and_increment_uploads(db_session, user.id, daily_limit=1)
        try:
            check_and_increment_uploads(db_session, user.id, daily_limit=1)
        except RateLimitException as exc:
            assert exc.details["limit"] == "uploads_per_day"
            assert exc.details["current"] == 1
        else:
            raise AssertionError("the call past the limit must raise RateLimitException")

    def test_row_persists_per_user_and_date(self, db_session, seed_test_user) -> None:
        """After two increments one row exists holding the count 2."""
        user = seed_test_user("quota-d@t.dev")
        check_and_increment_uploads(db_session, user.id, daily_limit=10)
        check_and_increment_uploads(db_session, user.id, daily_limit=10)
        rows = (
            db_session.execute(select(UsageLimit).where(UsageLimit.user_id == user.id))
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].upload_count == 2

    def test_users_are_counted_separately(self, db_session, seed_test_user) -> None:
        """Two users share no quota row; each starts at 1."""
        alice = seed_test_user("quota-e@t.dev")
        bob = seed_test_user("quota-f@t.dev")
        first = check_and_increment_uploads(db_session, alice.id, daily_limit=10)
        second = check_and_increment_uploads(db_session, bob.id, daily_limit=10)
        assert (first, second) == (1, 1)

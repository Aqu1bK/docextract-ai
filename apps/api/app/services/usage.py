"""Daily upload quota: one row-locked check-then-increment.

Why the row lock matters: "read the counter, compare, write it back" is a
classic check-then-act race — two concurrent requests both read 9, both
 decide they are under the limit of 10, both write 10, and eleven uploads
exist. ``SELECT ... FOR UPDATE`` serializes the row: the second request
blocks until the first transaction commits, then reads the incremented
value and correctly refuses. The lock window is one short transaction,
and the alternative (an atomic ``UPDATE ... WHERE upload_count < limit``
check) cannot distinguish "incremented" from "refused" without a second
round-trip, so the explicit lock is the honest design.
"""

import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UsageLimit
from app.errors import RateLimitException


def check_and_increment_uploads(db: Session, user_id: uuid.UUID, daily_limit: int) -> int:
    """Increment today's upload counter and return the new count.

    The row for (user, today) is created if absent, then locked with
    ``FOR UPDATE`` inside this session's transaction so concurrent
    requests cannot interleave a read and a write. The caller commits
    (or rolls back) with the request, which is what releases the lock.

    Args:
        db: The request-scoped session owning the transaction.
        user_id: The uploading user.
        daily_limit: ``MAX_UPLOADS_PER_DAY`` from settings.

    Returns:
        The user's new upload count for today.

    Raises:
        RateLimitException: If the user is already at ``daily_limit``.
    """
    today = datetime.date.today()
    row = db.execute(
        select(UsageLimit)
        .where(UsageLimit.user_id == user_id, UsageLimit.usage_date == today)
        .with_for_update()
    ).scalar_one_or_none()
    if row is None:
        # INSERT then re-SELECT with the lock: two first-of-day requests
        # race on the INSERT, the composite PK rejects the duplicate, and
        # the re-SELECT finds the winner's row and locks it — the same
        # serialization as the steady-state path.
        db.add(UsageLimit(user_id=user_id, usage_date=today, upload_count=0))
        db.flush()
        row = db.execute(
            select(UsageLimit)
            .where(UsageLimit.user_id == user_id, UsageLimit.usage_date == today)
            .with_for_update()
        ).scalar_one()
    if row.upload_count >= daily_limit:
        raise RateLimitException(details={"limit": "uploads_per_day", "current": row.upload_count})
    row.upload_count += 1
    db.flush()
    return row.upload_count

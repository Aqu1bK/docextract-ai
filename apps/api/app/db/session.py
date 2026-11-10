# docextract-ai/apps/api/app/db/session.py

"""Engine and session factory plus the FastAPI database dependency.

One engine per process: creating engines is expensive (each one builds a
connection pool), and a module-level singleton bound to the loaded settings
is the documented SQLAlchemy pattern for process-scoped applications.

``pool_pre_ping=True`` makes the pool test each connection with a cheap
``SELECT 1`` before handing it out, so a connection the database dropped
idle (Supabase free tier reaps them, restarts do too) is replaced
transparently instead of surfacing as a random "server closed the connection
unexpectedly" error inside a request.

``expire_on_commit=False`` keeps attribute values usable after ``commit()``.
The default expires every loaded attribute at commit so the next access
re-SELECTs the row — correct for long transactions, wasteful for the
request-scoped pattern here, where the commit is the last write and the
response serializes values that are already in memory.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DB_ECHO,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Iterator[Session]:
    """Yield a request-scoped session, closing it when the request ends.

    FastAPI calls this generator once per request whose endpoint declares it
    as a dependency: the first ``next()`` runs to the ``yield``, the endpoint
    receives the session, and request completion resumes the generator after
    the ``yield`` so the ``finally`` block always closes the session, even
    when the endpoint raised an exception.
    """

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

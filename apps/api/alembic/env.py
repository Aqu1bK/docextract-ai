# docextract-ai/apps/api/alembic/env.py

"""Alembic environment: bridges the migration tool to the app's metadata.

The two load-bearing lines are the settings import (URL comes from the
environment, never from a committed file) and ``target_metadata`` — without
it, ``alembic revision --autogenerate`` has nothing to compare the database
against and can only emit an empty migration.
"""

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.config import get_settings
from app.db import models  # noqa: F401  (registers all tables on Base.metadata)
from app.db.base import Base

config = context.config

# Twelve-factor: the URL comes from app settings (env var or .env), not
# from the committed alembic.ini.
config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live database connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the live database from settings."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

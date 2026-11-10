# docextract-ai/apps/api/app/db/base.py

"""Declarative base and the database-wide naming convention.

Every constraint the ORM renders — primary keys, unique constraints, foreign
keys, indexes, check constraints — gets a deterministic, descriptive name
through ``NAMING_CONVENTION``. Unnamed constraints are an Alembic disaster:
PostgreSQL auto-generates names like ``organizations_pkey`` for some
constraints and leaves others with generated tokens, and when Alembic later
compares the database against the models it cannot tell whether an unnamed
constraint in the database "is" the one in the metadata. Autogenerate then
either emits spurious drop/create diffs on every run, or — worse — cannot
drop a constraint it needs to drop because no stable name exists to target.
Deterministic names make schema comparisons exact: same constraint, same
name, every time.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Single declarative base shared by every model in ``app.db.models``."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

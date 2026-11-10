# docextract-ai/apps/api/app/domain/__init__.py

"""Domain-level building blocks shared across layers.

The package holds vocabulary that belongs to the business domain, not to any
single technical layer, so that API schemas (Pydantic), database models
(SQLAlchemy), and Alembic migrations can import the same definitions without
importing each other.
"""

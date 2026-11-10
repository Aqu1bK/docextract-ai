# docextract-ai/apps/api/tests/test_schema.py

"""Schema tests: the migration round-trip and the readiness probe.

Session-scoped fixtures run ``alembic upgrade head`` once against
``DATABASE_URL`` (the CI service container or a local dev database), then
inspect the live database: the 14 table names must exist. Downgrading to
base must remove the user tables, and a final upgrade leaves the database
migrated for later fixtures in the same session.
"""

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from alembic import command
from app.config import get_settings

EXPECTED_TABLES = frozenset(
    {
        "organizations",
        "roles",
        "users",
        "user_roles",
        "organization_settings",
        "documents",
        "document_pages",
        "extraction_jobs",
        "extracted_fields",
        "extracted_tables",
        "review_actions",
        "audit_logs",
        "exports",
        "usage_limits",
    }
)

EXPECTED_TABLE_COUNT = 14


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    """Programmatic Alembic config pointing at the API package."""
    return Config("alembic.ini")


@pytest.fixture(scope="session")
def migrated_db(db_engine, alembic_config: Config):
    """Run ``alembic upgrade head`` once for the whole test session.

    The engine from the shared ``db_engine`` fixture is the same engine the
    app uses in the test environment, so the migration and the tests talk
    to one database. On teardown the database stays migrated at head — a
    bare downgrade would leave the dev database empty and break the next
    ``make seed`` run after a test session.
    """
    command.upgrade(alembic_config, "head")
    yield


def test_migration_creates_all_tables(db_engine, migrated_db) -> None:
    """Upgrade head creates the 14 business tables in the live database."""
    names = set(inspect(db_engine).get_table_names())
    missing = EXPECTED_TABLES - names
    assert not missing, f"missing tables after upgrade: {sorted(missing)}"
    assert len(names & EXPECTED_TABLES) == EXPECTED_TABLE_COUNT


def test_migration_round_trip_downgrade(db_engine, migrated_db, alembic_config: Config) -> None:
    """Downgrade to base drops every user table, and re-upgrade restores them."""
    command.downgrade(alembic_config, "base")
    names = set(inspect(db_engine).get_table_names())
    remaining = EXPECTED_TABLES & names
    assert not remaining, f"tables survived downgrade: {sorted(remaining)}"

    command.upgrade(alembic_config, "head")
    names = set(inspect(db_engine).get_table_names())
    assert names >= EXPECTED_TABLES, "re-upgrade did not restore all tables"


def test_readiness_returns_ok(client_with_db: TestClient, migrated_db) -> None:
    """GET /api/v1/healthz/ready answers 200 with the database check green."""
    response = client_with_db.get(get_settings().API_V1_STR + "/healthz/ready")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "checks": {"database": "ok"}}


def test_enum_columns_are_varchar_not_pg_enum(db_engine, migrated_db) -> None:
    """Enum columns render as VARCHAR + CHECK-free storage, not PG ENUM type.

    native_enum=False keeps the column a plain VARCHAR so adding an enum
    member is a model edit plus a migration, never the painful ALTER TYPE
    dance PostgreSQL native enums require.
    """
    insp = inspect(db_engine)
    documents_status = next(c for c in insp.get_columns("documents") if c["name"] == "status")
    assert documents_status["type"].length == 32
    extraction_status = next(
        c for c in insp.get_columns("extraction_jobs") if c["name"] == "status"
    )
    assert str(extraction_status["type"]) == "VARCHAR(32)"


def test_timestamps_are_timestamptz(db_engine, migrated_db) -> None:
    """Every timestamp column stores timezone-aware values (TIMESTAMPTZ)."""
    insp = inspect(db_engine)
    for table in ("organizations", "documents", "extraction_jobs"):
        for column in insp.get_columns(table):
            if column["name"].endswith("_at"):
                assert column["type"].timezone is True, (
                    f"{table}.{column['name']} is not timezone-aware"
                )


def test_uuid_defaults_generate_in_db(db_engine, migrated_db) -> None:
    """PK defaults are DB-side gen_random_uuid(), so inserts need no client id."""
    from sqlalchemy import text

    with db_engine.connect() as connection:
        connection.execute(
            text("INSERT INTO organizations (name, slug) VALUES ('t', 'uuid-check')")
        )
        row = connection.execute(
            text("SELECT id FROM organizations WHERE slug = 'uuid-check'")
        ).scalar()
        connection.rollback()
    assert row is not None and len(str(row)) == 36


def test_migration_convention_names(db_engine, migrated_db) -> None:
    """Naming convention constraints exist with deterministic names in the DB."""
    from sqlalchemy import text

    with db_engine.connect() as connection:
        names = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT conname FROM pg_constraint WHERE connamespace = 'public'::regnamespace"
                )
            )
        }
    for expected in (
        "pk_organizations",
        "uq_organizations_slug",
        "uq_roles_name",
        "uq_users_organization_id",
        "pk_user_roles",
        "uq_extraction_jobs_document_id",
    ):
        assert expected in names, f"constraint {expected} not found"


def test_naming_convention_all_present(db_engine, migrated_db) -> None:
    """Every table has a pk_<table> primary key per the naming convention."""
    from sqlalchemy import text

    with db_engine.connect() as connection:
        pks = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE contype = 'p' AND connamespace = 'public'::regnamespace"
                )
            )
        }
    for table in EXPECTED_TABLES:
        assert f"pk_{table}" in pks, f"missing pk_{table}"


def test_jsonb_columns_present(db_engine, migrated_db) -> None:
    """Flexible payload columns are JSONB in the database."""
    insp = inspect(db_engine)
    for table, column in (
        ("organizations", "settings_json"),
        ("extraction_jobs", "result_metadata"),
        ("audit_logs", "metadata_json"),
        ("extracted_tables", "headers_json"),
        ("extracted_tables", "rows_json"),
    ):
        columns = {c["name"]: c for c in insp.get_columns(table)}
        assert column in columns, f"{table}.{column} missing"
        assert str(columns[column]["type"]) == "JSONB", (
            f"{table}.{column} is {columns[column]['type']}, expected JSONB"
        )

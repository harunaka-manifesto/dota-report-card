from __future__ import annotations

import os
import subprocess
import sys
from uuid import uuid4

import pytest
from app.storage.database import (
    EXPECTED_SCHEMA_REVISION,
    check_database_revision,
    normalize_database_url,
)
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_POSTGRES_URL = os.getenv("TEST_POSTGRES_URL")
RUN_POSTGRES_MIGRATION_TEST = os.getenv("RUN_POSTGRES_MIGRATION_TEST") == "1"

pytestmark = pytest.mark.live


@pytest.mark.skipif(
    not (RUN_POSTGRES_MIGRATION_TEST and TEST_POSTGRES_URL),
    reason="Set RUN_POSTGRES_MIGRATION_TEST=1 and TEST_POSTGRES_URL for PostgreSQL integration.",
)
def test_clean_postgres_bootstrap_and_idempotent_retry() -> None:
    assert TEST_POSTGRES_URL is not None
    schema = f"migration_test_{uuid4().hex}"
    base_url = normalize_database_url(TEST_POSTGRES_URL)
    base_engine = create_engine(base_url)
    parsed_url = make_url(base_url)
    target_url = parsed_url.set(
        query={**parsed_url.query, "options": f"-csearch_path={schema}"}
    ).render_as_string(hide_password=False)
    target_engine = create_engine(target_url)

    try:
        with base_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        environment = os.environ.copy()
        environment["DATABASE_URL"] = target_url
        for _ in range(2):
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=REPO_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stderr

        with target_engine.connect() as connection:
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == EXPECTED_SCHEMA_REVISION
            )
            assert connection.execute(
                text(
                    "SELECT character_maximum_length FROM information_schema.columns "
                    "WHERE table_schema = current_schema() AND table_name = 'alembic_version' "
                    "AND column_name = 'version_num'"
                )
            ).scalar_one() == 64
        check_database_revision(target_engine)
    finally:
        target_engine.dispose()
        with base_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        base_engine.dispose()

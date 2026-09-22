from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]


def migrate(url: str, revision: str, direction: str = "upgrade") -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", direction, revision],
        cwd=ROOT, env={**os.environ, "DATABASE_URL": url},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture
def postgres() -> Iterator[Engine]:
    url = os.getenv("TEST_POSTGRES_URL")
    if not url:
        pytest.skip("TEST_POSTGRES_URL is required; tracker guarantees are tested on PostgreSQL")
    parsed = make_url(url)
    assert parsed.get_backend_name() == "postgresql", "SQLite cannot prove tracker storage guarantees"
    admin = create_engine(url)
    schema = "tracker_test_" + uuid4().hex
    target_url = parsed.set(query={**parsed.query, "options": f"-csearch_path={schema}"})
    engine = create_engine(target_url)
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def database(postgres: Engine) -> Engine:
    migrate(postgres.url.render_as_string(hide_password=False), "head")
    return postgres

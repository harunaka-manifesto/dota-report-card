from __future__ import annotations

from pathlib import Path

import pytest
from app.core.config import Settings
from app.storage.database import create_database_engine, normalize_database_url
from sqlalchemy.engine import make_url

REPO_ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL = (
    "postgres://release_user:p%40ss%3Aword@example.railway.internal:5432/reporting"
    "?sslmode=require&application_name=railway%20beta&connect_timeout=5"
)


@pytest.mark.parametrize("scheme", ("postgres", "postgresql"))
def test_bare_postgres_schemes_use_psycopg_v3(scheme: str) -> None:
    value = DATABASE_URL.replace("postgres", scheme, 1)

    normalized = normalize_database_url(value)

    assert make_url(normalized).drivername == "postgresql+psycopg"


def test_psycopg_v3_url_is_idempotent() -> None:
    value = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

    assert normalize_database_url(value) == value


def test_url_normalization_preserves_credentials_and_query_parameters() -> None:
    parsed = make_url(normalize_database_url(DATABASE_URL))

    assert parsed.username == "release_user"
    assert parsed.password == "p@ss:word"
    assert parsed.host == "example.railway.internal"
    assert parsed.port == 5432
    assert parsed.database == "reporting"
    assert dict(parsed.query) == {
        "sslmode": "require",
        "application_name": "railway beta",
        "connect_timeout": "5",
    }


def test_application_engine_uses_psycopg_v3() -> None:
    engine = create_database_engine(Settings(database_url=DATABASE_URL))

    try:
        assert engine.url.drivername == "postgresql+psycopg"
    finally:
        engine.dispose()


def test_alembic_uses_the_shared_normalizer_and_psycopg_engine() -> None:
    source = (REPO_ROOT / "migrations" / "env.py").read_text(encoding="utf-8")

    assert "from app.storage.database import normalize_database_url" in source
    assert "database_url = normalize_database_url(" in source
    assert "create_engine(database_url, poolclass=pool.NullPool)" in source

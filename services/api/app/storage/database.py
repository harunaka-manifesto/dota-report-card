from __future__ import annotations

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings

EXPECTED_SCHEMA_REVISION = "0005_v6_interactions_deep"


def create_database_engine(settings: Settings | None = None) -> Engine:
    settings = settings or get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True)


def create_session_factory(settings: Settings | None = None) -> sessionmaker:
    return sessionmaker(bind=create_database_engine(settings), expire_on_commit=False)


def check_database_revision(engine: Engine, *, expected: str = EXPECTED_SCHEMA_REVISION) -> None:
    """Fail readiness when migrations have not reached the application head."""

    revision = current_database_revision(engine)
    if revision != expected:
        raise RuntimeError(f"database schema revision is {revision!r}; expected {expected!r}")


def current_database_revision(engine: Engine) -> str | None:
    """Return the current Alembic revision without hiding a database failure."""

    with engine.connect() as connection:
        value = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    return str(value) if value is not None else None

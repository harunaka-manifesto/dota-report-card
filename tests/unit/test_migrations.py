from __future__ import annotations

from importlib import import_module
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from app.storage.database import EXPECTED_SCHEMA_REVISION, check_database_revision

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_HEAD = "0005_v6_interactions_deep"
MAX_VERSION_NUM_LENGTH = 64


def test_all_migration_ids_fit_the_widened_version_table() -> None:
    script = ScriptDirectory.from_config(Config(str(REPO_ROOT / "alembic.ini")))
    revisions = list(script.walk_revisions())

    assert revisions
    assert script.get_current_head() == EXPECTED_HEAD == EXPECTED_SCHEMA_REVISION
    assert list(script.iterate_revisions(EXPECTED_HEAD, EXPECTED_HEAD)) == []
    assert max(len(revision.revision) for revision in revisions) <= MAX_VERSION_NUM_LENGTH
    assert {revision.revision for revision in revisions} == {
        "0001_initial",
        "0001_version_table_width",
        "0002_persist_analysis_job_details",
        "0003_analysis_mode",
        "0004_raw_payload_metadata",
        EXPECTED_HEAD,
    }


def test_postgres_operation_widens_version_table() -> None:
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql",
        opts={"as_sql": True, "output_buffer": output},
    )
    migration = import_module("migrations.versions.0001_version_table_width")

    with Operations.context(context):
        migration.upgrade()

    assert "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)" in output.getvalue()


def test_application_readiness_accepts_migration_head() -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = EXPECTED_HEAD
    connection = MagicMock()
    connection.execute.return_value = result
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = connection

    check_database_revision(engine)

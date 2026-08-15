"""Persist job identity, failure messages, events, and active-job idempotency."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_persist_analysis_job_details"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {
        column["name"] for column in sa.inspect(bind).get_columns("analysis_jobs")
    }
    added_columns: set[str] = set()
    for name, column in (
        ("canonical_player", sa.Column("canonical_player", sa.String(length=300), nullable=True)),
        ("active_key", sa.Column("active_key", sa.String(length=128), nullable=True)),
        ("failure_detail", sa.Column("failure_detail", sa.String(length=500), nullable=True)),
        ("events_json", sa.Column("events_json", sa.JSON(), nullable=True)),
    ):
        if name not in existing_columns:
            op.add_column("analysis_jobs", column)
            added_columns.add(name)
    op.execute(
        "UPDATE analysis_jobs SET canonical_player = CAST(account_id AS VARCHAR(300)) "
        "WHERE canonical_player IS NULL"
    )
    op.execute("UPDATE analysis_jobs SET events_json = '[]' WHERE events_json IS NULL")
    op.execute(
        "UPDATE analysis_jobs SET active_key = CAST(account_id AS VARCHAR(32)) || ':' || model_version "
        "WHERE active_key IS NULL AND status IN ('queued', 'running')"
    )
    if "canonical_player" in added_columns:
        op.alter_column("analysis_jobs", "canonical_player", nullable=False)
    index_names = {index["name"] for index in sa.inspect(bind).get_indexes("analysis_jobs")}
    if "ix_analysis_jobs_active_key" not in index_names:
        op.create_index("ix_analysis_jobs_active_key", "analysis_jobs", ["active_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_analysis_jobs_active_key", table_name="analysis_jobs")
    op.drop_column("analysis_jobs", "events_json")
    op.drop_column("analysis_jobs", "failure_detail")
    op.drop_column("analysis_jobs", "active_key")
    op.drop_column("analysis_jobs", "canonical_player")

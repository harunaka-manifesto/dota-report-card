"""Persist whether a job is a free Player DNA or explicit Deep Scan."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_analysis_mode"
down_revision: str | None = "0002_persist_analysis_job_details"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("analysis_jobs")}
    if "analysis_mode" not in columns:
        op.add_column(
            "analysis_jobs",
            sa.Column("analysis_mode", sa.String(length=32), nullable=True),
        )
    op.execute("UPDATE analysis_jobs SET analysis_mode = 'free' WHERE analysis_mode IS NULL")
    op.alter_column("analysis_jobs", "analysis_mode", nullable=False)
    op.execute(
        "UPDATE analysis_jobs SET active_key = CAST(account_id AS VARCHAR(32)) || ':' "
        "|| model_version || ':' || analysis_mode WHERE active_key IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("analysis_jobs", "analysis_mode")

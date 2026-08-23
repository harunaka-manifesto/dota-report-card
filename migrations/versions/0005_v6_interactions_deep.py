"""Persist token-protected v6 interaction state and Deep continuation metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_v6_interactions_deep"
down_revision: str | None = "0004_raw_payload_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(bind: sa.Connection, table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def _indexes(bind: sa.Connection, table: str) -> set[str]:
    return {index["name"] for index in sa.inspect(bind).get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    jobs = _columns(bind, "analysis_jobs")
    for name, column in (
        ("parent_report_id", sa.Column("parent_report_id", sa.String(length=36), nullable=True)),
        (
            "diagnostic_question_id",
            sa.Column("diagnostic_question_id", sa.String(length=128), nullable=True),
        ),
        ("entitlement_decision_json", sa.Column("entitlement_decision_json", sa.JSON(), nullable=True)),
        ("selection_plan_json", sa.Column("selection_plan_json", sa.JSON(), nullable=True)),
        ("stopping_reason", sa.Column("stopping_reason", sa.String(length=64), nullable=True)),
    ):
        if name not in jobs:
            op.add_column("analysis_jobs", column)

    job_indexes = _indexes(bind, "analysis_jobs")
    for name, columns in (
        ("ix_analysis_jobs_parent_report_id", ["parent_report_id"]),
        ("ix_analysis_jobs_diagnostic_question_id", ["diagnostic_question_id"]),
    ):
        if name not in job_indexes:
            op.create_index(name, "analysis_jobs", columns, unique=False)

    tables = set(sa.inspect(bind).get_table_names())
    if "report_interaction_sessions" not in tables:
        op.create_table(
            "report_interaction_sessions",
            sa.Column("session_id", sa.String(length=36), primary_key=True),
            sa.Column(
                "report_id",
                sa.String(length=36),
                sa.ForeignKey("reports.report_id"),
                nullable=False,
            ),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("access_token_hash", sa.String(length=64), nullable=False),
            sa.Column("state_schema_version", sa.String(length=64), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("state_json", sa.JSON(), nullable=False),
            sa.Column("recommendation_baseline_json", sa.JSON(), nullable=False),
            sa.Column("history_cutoff", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("access_token_hash", name="uq_report_interaction_session_token_hash"),
        )
    session_indexes = _indexes(bind, "report_interaction_sessions")
    for name, columns in (
        ("ix_report_interaction_sessions_report_id", ["report_id"]),
        ("ix_report_interaction_sessions_account_id", ["account_id"]),
        ("ix_report_interaction_sessions_access_token_hash", ["access_token_hash"]),
        ("ix_report_interaction_sessions_expires_at", ["expires_at"]),
    ):
        if name not in session_indexes:
            op.create_index(name, "report_interaction_sessions", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if "report_interaction_sessions" in set(sa.inspect(bind).get_table_names()):
        op.drop_table("report_interaction_sessions")
    for name in (
        "ix_analysis_jobs_parent_report_id",
        "ix_analysis_jobs_diagnostic_question_id",
    ):
        if name in _indexes(bind, "analysis_jobs"):
            op.drop_index(name, table_name="analysis_jobs")
    jobs = _columns(bind, "analysis_jobs")
    for name in (
        "stopping_reason",
        "selection_plan_json",
        "entitlement_decision_json",
        "diagnostic_question_id",
        "parent_report_id",
    ):
        if name in jobs:
            op.drop_column("analysis_jobs", name)

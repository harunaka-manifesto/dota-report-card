"""Account-global discovery outcomes and acquisition-response correlation."""

import sqlalchemy as sa
from alembic import op

revision = "0007_tracker_discovery_journal"
down_revision = "0006_tracker_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tracker_provider_calls", sa.Column("account_id", sa.BigInteger(), nullable=True))
    op.add_column("tracker_provider_calls", sa.Column("job_id", sa.String(36), nullable=True))
    op.add_column("tracker_provider_calls", sa.Column("snapshot_id", sa.String(36), nullable=True))
    op.add_column("tracker_provider_calls", sa.Column("request_subject", sa.String(128), nullable=True))
    op.create_foreign_key(op.f("fk_tracker_provider_calls_job_id_tracker_ingest_jobs"), "tracker_provider_calls", "tracker_ingest_jobs", ["job_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(op.f("fk_tracker_provider_calls_snapshot_id_tracker_provider_snapshots"), "tracker_provider_calls", "tracker_provider_snapshots", ["snapshot_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_tracker_call_job_subject", "tracker_provider_calls", ["job_id", "request_subject"])
    op.create_table(
        "tracker_account_discoveries",
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("source_item_id", sa.String(128), nullable=False),
        sa.Column("snapshot_id", sa.String(36), nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=True),
        sa.Column("source_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(64), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("account_id", "provider", "source_item_id", name=op.f("pk_tracker_account_discoveries")),
        sa.ForeignKeyConstraint(["account_id"], ["tracker_dota_accounts.account_id"], ondelete="CASCADE", name=op.f("fk_tracker_account_discoveries_account_id_tracker_dota_accounts")),
        sa.ForeignKeyConstraint(["snapshot_id"], ["tracker_provider_snapshots.id"], name=op.f("fk_tracker_account_discoveries_snapshot_id_tracker_provider_snapshots")),
        sa.ForeignKeyConstraint(["match_id"], ["tracker_matches.match_id"], name=op.f("fk_tracker_account_discoveries_match_id_tracker_matches")),
        sa.CheckConstraint("outcome IN ('ACCEPTED', 'REJECTED', 'TERMINAL')", name=op.f("ck_tracker_account_discovery_outcome")),
        sa.CheckConstraint("outcome = 'ACCEPTED' OR reason IS NOT NULL", name=op.f("ck_tracker_account_discovery_reason")),
    )


def downgrade() -> None:
    op.drop_table("tracker_account_discoveries")
    op.drop_index("ix_tracker_call_job_subject", table_name="tracker_provider_calls")
    op.drop_constraint(op.f("fk_tracker_provider_calls_snapshot_id_tracker_provider_snapshots"), "tracker_provider_calls", type_="foreignkey")
    op.drop_constraint(op.f("fk_tracker_provider_calls_job_id_tracker_ingest_jobs"), "tracker_provider_calls", type_="foreignkey")
    for column in ("request_subject", "snapshot_id", "job_id", "account_id"):
        op.drop_column("tracker_provider_calls", column)

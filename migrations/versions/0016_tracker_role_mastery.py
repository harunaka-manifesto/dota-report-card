"""Append-only Role Mastery awards, scoped to a Steam profile."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0016_tracker_role_mastery"
down_revision = "0015_tracker_link_updated_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tracker_mastery_ledger",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("source_analysis_id", sa.String(36), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("source", JSONB(), nullable=False),
        sa.Column("dedup_key", sa.String(240), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dedup_key", name="uq_tracker_mastery_ledger_dedup_key"),
        sa.ForeignKeyConstraint(
            ["profile_id", "match_id"],
            ["tracker_account_matches.profile_id", "tracker_account_matches.match_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_analysis_id", "profile_id", "match_id"],
            ["tracker_analyses.id", "tracker_analyses.profile_id", "tracker_analyses.match_id"],
        ),
        sa.CheckConstraint("mode IN ('STANDARD', 'TURBO')", name="ck_tracker_mastery_mode"),
        sa.CheckConstraint("role IN ('CARRY', 'MID', 'OFFLANE', 'SUPPORT')", name="ck_tracker_mastery_role"),
        sa.CheckConstraint("kind IN ('AWARD', 'LATE_BONUS', 'REVERSAL', 'CORRECTION')", name="ck_tracker_mastery_kind"),
        sa.CheckConstraint("xp != 0 AND abs(xp) <= 160", name="ck_tracker_mastery_xp"),
    )
    op.create_index("ix_tracker_mastery_profile_role", "tracker_mastery_ledger", ["profile_id", "role", "created_at"])
    op.create_index("ix_tracker_mastery_profile_match", "tracker_mastery_ledger", ["profile_id", "match_id"])


def downgrade() -> None:
    op.drop_index("ix_tracker_mastery_profile_match", table_name="tracker_mastery_ledger")
    op.drop_index("ix_tracker_mastery_profile_role", table_name="tracker_mastery_ledger")
    op.drop_table("tracker_mastery_ledger")

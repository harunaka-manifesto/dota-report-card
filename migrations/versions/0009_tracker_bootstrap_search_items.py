"""Journal profile-owned bootstrap search items without selecting eligible matches."""

import sqlalchemy as sa
from alembic import op

revision = "0009_tracker_bootstrap_search_items"
down_revision = "0008_tracker_role_assignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tracker_bootstrap_search_items",
        sa.Column("profile_id", sa.String(36), sa.ForeignKey("tracker_profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("source_item_id", sa.String(128), primary_key=True),
        sa.Column("snapshot_id", sa.String(36), sa.ForeignKey("tracker_provider_snapshots.id"), nullable=False),
        sa.Column("match_id", sa.BigInteger()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("mode", sa.String(16)),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(64)),
        sa.CheckConstraint("mode IS NULL OR mode IN ('STANDARD', 'TURBO')", name="ck_tracker_bootstrap_item_mode"),
        sa.CheckConstraint("outcome IN ('CANDIDATE', 'REJECTED')", name="ck_tracker_bootstrap_item_outcome"),
        sa.CheckConstraint("(outcome = 'CANDIDATE') = (match_id IS NOT NULL AND started_at IS NOT NULL AND mode IS NOT NULL)", name="ck_tracker_bootstrap_item_candidate"),
    )
    op.create_index("ix_tracker_bootstrap_candidates", "tracker_bootstrap_search_items", ["profile_id", "mode", "started_at", "match_id"])


def downgrade() -> None:
    op.drop_index("ix_tracker_bootstrap_candidates", table_name="tracker_bootstrap_search_items")
    op.drop_table("tracker_bootstrap_search_items")

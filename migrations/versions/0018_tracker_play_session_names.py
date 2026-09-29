"""Player-renamed play sessions for the Matches list (matches/SSOT.md §3)."""

import sqlalchemy as sa
from alembic import op

revision = "0018_tracker_play_session_names"
down_revision = "0017_tracker_context_2026_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tracker_play_session_names",
        sa.Column("profile_id", sa.String(36), primary_key=True),
        sa.Column("match_id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id", "match_id"],
            ["tracker_account_matches.profile_id", "tracker_account_matches.match_id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("char_length(name) BETWEEN 1 AND 40", name="ck_tracker_play_session_name"),
    )


def downgrade() -> None:
    op.drop_table("tracker_play_session_names")

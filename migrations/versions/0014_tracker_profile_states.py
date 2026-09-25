"""Persist each Profile bucket's last coherent published projection."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014_tracker_profile_states"
down_revision = "0013_tracker_profile_relink"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tracker_profile_states",
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("checkpoint_seq", sa.BigInteger(), nullable=False),
        sa.Column("cause", sa.String(24), nullable=False),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mode IN ('STANDARD', 'TURBO')", name="ck_tracker_profile_state_mode"),
        sa.CheckConstraint("checkpoint_seq > 0", name="ck_tracker_profile_state_seq"),
        sa.ForeignKeyConstraint(["profile_id"], ["tracker_profiles.id"], ondelete="CASCADE",
                                name="fk_tracker_profile_states_profile_id_tracker_profiles"),
        sa.PrimaryKeyConstraint("profile_id", "mode", name="pk_tracker_profile_states"),
    )


def downgrade() -> None:
    op.drop_table("tracker_profile_states")

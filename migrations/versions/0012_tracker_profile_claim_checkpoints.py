"""Persist the latest Profile claim evaluation and its prior evidence."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_tracker_profile_claim_checkpoints"
down_revision = "0011_tracker_match_public_ref"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tracker_profile_claim_checkpoints",
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("profile_generation", sa.BigInteger(), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("scope", sa.String(80), nullable=False),
        sa.Column("claim_id", sa.String(80), nullable=False),
        sa.Column("claim_version", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("previous_evidence", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("lifecycle", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("inputs_digest", sa.String(64), nullable=False),
        sa.Column("evaluation_digest", sa.String(64), nullable=False),
        sa.Column("checkpoint_seq", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("profile_generation > 0 AND checkpoint_seq > 0", name="ck_tracker_claim_checkpoint_order"),
        sa.CheckConstraint("mode IN ('STANDARD', 'TURBO')", name="ck_tracker_claim_checkpoint_mode"),
        sa.CheckConstraint("state IN ('CANDIDATE', 'CONFIRMED', 'FADING', 'RETIRED')", name="ck_tracker_claim_checkpoint_state"),
        sa.ForeignKeyConstraint(["profile_id"], ["tracker_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id", "mode", "scope", "claim_id", "claim_version", name="pk_tracker_profile_claim_checkpoints"),
    )


def downgrade() -> None:
    op.drop_table("tracker_profile_claim_checkpoints")

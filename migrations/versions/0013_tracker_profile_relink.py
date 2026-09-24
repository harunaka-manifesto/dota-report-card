"""Allow a user to relink a prior Steam ID with a fresh isolated profile."""

from alembic import op

revision = "0013_tracker_profile_relink"
down_revision = "0012_tracker_profile_claim_checkpoints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_tracker_profiles_user_id", "tracker_profiles", type_="unique")


def downgrade() -> None:
    # A relinked identity can have several archived profile generations.
    # This reverse DDL requires those duplicates to be resolved first.
    op.create_unique_constraint("uq_tracker_profiles_user_id", "tracker_profiles", ["user_id", "account_id"])

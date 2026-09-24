"""Retain the exact classifier assignment selected by a private match."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_tracker_role_assignment"
down_revision = "0007_tracker_discovery_journal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tracker_matches", sa.Column("replay_role_assignment", JSONB(), nullable=True))
    op.add_column("tracker_account_matches", sa.Column("role_assignment", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("tracker_account_matches", "role_assignment")
    op.drop_column("tracker_matches", "replay_role_assignment")

"""Give each private tracker match link a stable opaque mobile reference."""

import sqlalchemy as sa
from alembic import op

revision = "0011_tracker_match_public_ref"
down_revision = "0010_tracker_bootstrap_selection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tracker_account_matches", sa.Column(
        "public_ref", sa.String(length=36), nullable=False,
        server_default=sa.text("gen_random_uuid()::text"),
    ))
    op.create_unique_constraint("uq_tracker_account_matches_public_ref", "tracker_account_matches", ["public_ref"])


def downgrade() -> None:
    op.drop_constraint("uq_tracker_account_matches_public_ref", "tracker_account_matches", type_="unique")
    op.drop_column("tracker_account_matches", "public_ref")

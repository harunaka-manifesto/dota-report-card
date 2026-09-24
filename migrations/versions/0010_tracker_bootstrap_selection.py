"""Mark selected bootstrap candidates separately from scanned source items."""

import sqlalchemy as sa
from alembic import op

revision = "0010_tracker_bootstrap_selection"
down_revision = "0009_tracker_bootstrap_search_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tracker_bootstrap_search_items", sa.Column("selected_at", sa.DateTime(timezone=True)))
    op.create_check_constraint("ck_tracker_bootstrap_item_selected", "tracker_bootstrap_search_items", "selected_at IS NULL OR outcome = 'CANDIDATE'")


def downgrade() -> None:
    op.drop_constraint("ck_tracker_bootstrap_item_selected", "tracker_bootstrap_search_items", type_="check")
    op.drop_column("tracker_bootstrap_search_items", "selected_at")

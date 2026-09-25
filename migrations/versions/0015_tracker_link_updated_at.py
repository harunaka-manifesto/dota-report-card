"""Stamp account-match changes for the mobile changes feed."""

import sqlalchemy as sa
from alembic import op

revision = "0015_tracker_link_updated_at"
down_revision = "0014_tracker_profile_states"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tracker_account_matches", sa.Column(
        "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("clock_timestamp()")))
    op.create_index("ix_tracker_link_updates", "tracker_account_matches", ["profile_id", "updated_at"])
    op.execute("""
        CREATE FUNCTION tracker_touch_link() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at := clock_timestamp();
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER tracker_link_touch BEFORE UPDATE ON tracker_account_matches
        FOR EACH ROW EXECUTE FUNCTION tracker_touch_link()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER tracker_link_touch ON tracker_account_matches")
    op.execute("DROP FUNCTION tracker_touch_link()")
    op.drop_index("ix_tracker_link_updates", table_name="tracker_account_matches")
    op.drop_column("tracker_account_matches", "updated_at")

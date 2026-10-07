"""Drop the removed report-card product's tables (owner decision 2026-10-07).

The report-card / Free DNA product was never live and had no users. Its sixteen
tables (created by ``0001_initial`` and altered by ``0002``-``0005``) are read
and written by nothing in the tracker. Tracker tables all carry the
``tracker_`` prefix and none reference these tables.

Downgrade recreates the empty tables from the frozen historical schema; it
cannot restore rows.
"""

from alembic import op
from migrations.historical_schema import Base

revision = "0019_drop_report_card_tables"
down_revision = "0018_tracker_play_session_names"
branch_labels = None
depends_on = None

# Children before parents, so foreign keys never block a drop.
REPORT_CARD_TABLES = tuple(table.name for table in reversed(Base.metadata.sorted_tables))


def upgrade() -> None:
    for name in REPORT_CARD_TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{name}"')


def downgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())

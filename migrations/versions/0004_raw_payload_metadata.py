"""Record request metadata alongside unchanged raw provider payloads."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_raw_payload_metadata"
down_revision: str | None = "0003_analysis_mode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("raw_payloads")}
    if "metadata_json" not in columns:
        op.add_column("raw_payloads", sa.Column("metadata_json", sa.JSON(), nullable=True))
    op.execute("UPDATE raw_payloads SET metadata_json = '{}' WHERE metadata_json IS NULL")


def downgrade() -> None:
    op.drop_column("raw_payloads", "metadata_json")

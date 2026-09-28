"""Register the owner-approved context parameter set context-2026-09-v1.

Owner sign-off 2026-09-28. Registering it turns Role Mastery on: finalized
matches that were never graded are graded once by the methodology sweep and
backfilled into XP quietly. Later parameter sets never re-grade them.
"""

import hashlib
import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, insert

revision = "0017_tracker_context_2026_09"
down_revision = "0016_tracker_role_mastery"
branch_labels = None
depends_on = None

VERSION = "context-2026-09-v1"
ARTIFACT = Path(__file__).resolve().parent.parent / "data" / f"{VERSION}.json"
DIGEST = "c3333c8223778ba3cefd06bcd10d146bb6d649c0a379951865f85e2715bb5707"

parameter_sets = sa.table(
    "tracker_parameter_sets",
    sa.column("version", sa.String), sa.column("kind", sa.String), sa.column("digest", sa.String),
    sa.column("status", sa.String), sa.column("parameters", JSONB), sa.column("provenance", JSONB),
    sa.column("created_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    artifact = json.loads(ARTIFACT.read_text())
    unsigned = {key: value for key, value in artifact.items() if key != "sha256"}
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if artifact.get("sha256") != DIGEST or hashlib.sha256(encoded).hexdigest() != DIGEST:
        raise RuntimeError(f"{ARTIFACT.name} does not match its approved digest")
    op.execute(insert(parameter_sets).values(
        version=VERSION, kind="CONTEXT_POPULATION", digest=DIGEST, status="APPROVED",
        parameters=artifact,
        provenance={"source": artifact["source"], "input_sha256": artifact["input_sha256"],
                    "approved_by": "owner", "approved_on": "2026-09-28"},
        created_at=sa.func.clock_timestamp(),
    ).on_conflict_do_nothing(index_elements=["version"]))


def downgrade() -> None:
    # Fails if any analysis already references the set; approved history is not erased silently.
    op.execute(parameter_sets.delete().where(parameter_sets.c.version == VERSION))

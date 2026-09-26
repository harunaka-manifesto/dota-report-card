"""Retained-evidence item insight rebuild. No provider calls or notifications.

DATABASE_URL=postgresql+psycopg://... uv run python -m scripts.rebuild_current_patch_items
Use --profile-id to rebuild one profile. Run after deploying a reviewed V2 client.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))

from app.tracker.rebuild import run_item_insight_rebuild  # noqa: E402
from app.tracker.schema import profiles, users  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-id")
    args = parser.parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url:
        parser.error("DATABASE_URL is required")
    engine = create_engine(url)
    with engine.connect() as connection:
        query = select(profiles.c.id).where(profiles.c.active.is_(True))
        if args.profile_id:
            query = query.where(profiles.c.id == args.profile_id)
        profile_ids = list(connection.scalars(query))
    for profile_id in profile_ids:
        with engine.begin() as connection:
            user_id = connection.scalar(select(profiles.c.user_id).where(profiles.c.id == profile_id))
            if user_id is None:
                continue
            connection.execute(select(users.c.id).where(users.c.id == user_id).with_for_update())
            rebuilt = run_item_insight_rebuild(connection, profile_id=profile_id)
            if rebuilt:
                print(f"profile {profile_id}: rebuilt {rebuilt}")


if __name__ == "__main__":
    main()

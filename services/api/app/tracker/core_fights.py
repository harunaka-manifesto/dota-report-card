"""Role-neutral public projection of the existing detected-fight calculation."""
from __future__ import annotations

from typing import Any

CONTRACT_VERSION = "core-fights-v1"


def from_offlane_fights(fights: dict[str, Any]) -> dict[str, Any]:
    segments = []
    for row in fights["segments"]:
        segment = {key: value for key, value in row.items() if key not in {
            "offlaner_damage", "offlaner_kills", "offlaner_deaths",
        }}
        segment.update(player_damage=row["offlaner_damage"], player_kills=row["offlaner_kills"],
                       player_deaths=row["offlaner_deaths"])
        segments.append(segment)
    return {"contract_version": CONTRACT_VERSION, "state": fights["state"],
            "reason": fights["reason"], "segments": segments}

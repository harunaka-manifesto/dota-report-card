"""Fail-closed competitive-integrity verdict from normalized provider facts."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

INTEGRITY_VERSION = "integrity-1"


@dataclass(frozen=True)
class Integrity:
    verdict: str | None
    reason: str | None


def verify(summary: Mapping[str, Any]) -> Integrity:
    """Positive proof requires a normal/ranked lobby, ten humans and ten finishers.

    OpenDota's published leaver status 1 is "Left Safely"; 2+ are abandon-like.
    STRATZ NONE is translated to 0 only when explicitly present. Unknown values
    are never silently treated as finishers.
    """
    lobby = summary.get("lobby_type")
    humans = summary.get("human_players")
    players = summary.get("players")
    if type(lobby) is int and lobby not in {0, 7}:
        return Integrity("INVALID", "NON_COMPETITIVE_LOBBY")
    if type(humans) is int and humans != 10:
        return Integrity("INVALID", "NON_HUMAN_MATCH")
    if not isinstance(players, list) or len(players) != 10:
        return Integrity(None, "ROSTER_UNKNOWN")
    statuses = [player.get("leaver_status") if isinstance(player, Mapping) else None for player in players]
    if any(type(status) is int and status != 0 for status in statuses):
        return Integrity("INVALID", "LEFT_OR_ABANDONED")
    if type(lobby) is not int or type(humans) is not int or any(type(status) is not int for status in statuses):
        return Integrity(None, "INTEGRITY_SIGNAL_MISSING")
    for player in players:
        values = player.get("values") if isinstance(player, Mapping) else None
        if not isinstance(values, Mapping) or any(type(values.get(field)) is not int for field in ("kills", "deaths", "assists")):
            return Integrity(None, "SCOREBOARD_INCOMPLETE")
    return Integrity("VALID", None)

"""Versioned provider translation. This module does not assign roles or eligibility."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

Provider = Literal["opendota", "stratz"]
SUMMARY_VERSION = "summary-1"

# Translation candidates; paired fixtures verify the jointly observed fields.
# Each derived feature must separately establish its required field equivalence.
_SCORE_FIELDS = {
    "kills": "kills", "deaths": "deaths", "assists": "assists",
    "last_hits": "numLastHits", "denies": "numDenies", "gold_per_min": "goldPerMinute",
    "xp_per_min": "experiencePerMinute", "hero_damage": "heroDamage",
    "tower_damage": "towerDamage", "hero_healing": "heroHealing",
    "net_worth": "networth", "gold_spent": "goldSpent", "level": "level",
}


class InvalidEvidence(ValueError):
    """Required source facts are malformed; do not advance summary readiness."""


def _required_int(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise InvalidEvidence(f"Invalid {label}")
    return value


def _optional_int(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def player_summary(raw: Mapping[str, Any], provider: Provider) -> dict[str, Any]:
    if provider not in {"opendota", "stratz"}:
        raise InvalidEvidence("Unsupported provider")
    od = provider == "opendota"
    slot = raw.get("player_slot" if od else "playerSlot")
    if type(slot) is not int or slot not in (*range(5), *range(128, 133)):
        raise InvalidEvidence("Invalid player slot")
    radiant = slot < 128
    if not od and raw.get("isRadiant") is not radiant:
        raise InvalidEvidence("Player slot and team disagree")
    canonical_slot = slot if radiant else slot - 123
    values: dict[str, Any] = {}
    unavailable = {}
    for target, stratz_field in _SCORE_FIELDS.items():
        source = target if od else stratz_field
        value = raw.get(source)
        values[target] = _optional_int(value)
        if values[target] is None:
            unavailable[target] = "MISSING" if value is None else "MALFORMED"
    # Do not let a vendor role, percentile, impact score or identity block cross.
    return {
        "player_slot": canonical_slot,
        "team": "RADIANT" if radiant else "DIRE",
        "hero_id": _required_int(raw.get("hero_id" if od else "heroId"), "hero", 1),
        "values": values,
        "unavailable": unavailable,
    }


def opendota_summary(raw: Mapping[str, Any]) -> dict[str, Any]:
    match_id = _required_int(raw.get("match_id"), "match ID", 1)
    if match_id >= 2**63:
        raise InvalidEvidence("Invalid match ID")
    started_at = _required_int(raw.get("start_time"), "start time", 1)
    duration = _required_int(raw.get("duration"), "duration")
    winner = raw.get("radiant_win")
    if type(winner) is not bool:
        raise InvalidEvidence("Missing winner")
    raw_players = raw.get("players")
    if not isinstance(raw_players, list) or len(raw_players) != 10:
        raise InvalidEvidence("Summary requires all ten players")
    players = []
    for raw_player in raw_players:
        if not isinstance(raw_player, Mapping):
            raise InvalidEvidence("Invalid player")
        player = player_summary(raw_player, "opendota")
        account = raw_player.get("account_id")
        player["account_id"] = account if type(account) is int and 0 < account < 2**32 - 1 else None
        players.append(player)
    if {p["player_slot"] for p in players} != set(range(10)):
        raise InvalidEvidence("Duplicate or missing player slot")
    game_mode = _optional_int(raw.get("game_mode"))
    return {
        "match_id": match_id, "started_at": started_at, "duration_seconds": duration,
        "radiant_win": winner,
        "mode": "TURBO" if game_mode == 23 else "STANDARD" if game_mode in {1, 22} else "UNSUPPORTED",
        "game_mode": game_mode, "lobby_type": _optional_int(raw.get("lobby_type")),
        "human_players": _optional_int(raw.get("human_players")),
        "players": sorted(players, key=lambda p: p["player_slot"]),
    }


def replay_available(raw: Mapping[str, Any], provider: Provider) -> bool:
    if provider == "opendota":
        return type(raw.get("version")) is int and raw["version"] > 0
    if provider == "stratz":
        # Ingestion time alone is never proof of replay statistics.
        stamp = raw.get("statsDateTime")
        return raw.get("isStats") is True and type(stamp) is int and stamp > 0
    raise InvalidEvidence("Unsupported provider")

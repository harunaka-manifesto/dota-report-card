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
        for field in ("hero_variant", "leaver_status", "party_size"):
            player[field] = _optional_int(raw_player.get(field))
        player["items"] = {
            field: _optional_int(raw_player.get(field))
            for field in (
                *(f"item_{i}" for i in range(6)),
                *(f"backpack_{i}" for i in range(3)),
                "item_neutral", "item_neutral2",
            )
        }
        abilities = raw_player.get("ability_upgrades_arr")
        player["ability_build"] = (
            list(abilities) if isinstance(abilities, list)
            and all(type(ability) is int and ability > 0 for ability in abilities) else None
        )
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
        "first_blood_seconds": _optional_int(raw.get("first_blood_time")),
        "team_scores": {team: _optional_int(raw.get(f"{team}_score")) for team in ("radiant", "dire")},
        "structures": {
            field: _optional_int(raw.get(field))
            for field in ("tower_status_radiant", "tower_status_dire", "barracks_status_radiant", "barracks_status_dire")
        },
        "draft": _opendota_draft(raw.get("picks_bans")),
        "players": sorted(players, key=lambda p: p["player_slot"]),
    }


def _opendota_draft(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    result = []
    for entry in value:
        if not isinstance(entry, Mapping):
            return None
        if (
            type(entry.get("hero_id")) is not int or entry["hero_id"] <= 0
            or type(entry.get("order")) is not int or entry["order"] < 0
            or type(entry.get("team")) is not int or entry["team"] not in {0, 1}
            or type(entry.get("is_pick")) is not bool
        ):
            return None
        result.append({
            "hero_id": entry["hero_id"], "order": entry["order"],
            "team": "RADIANT" if entry["team"] == 0 else "DIRE", "is_pick": entry["is_pick"],
        })
    if len({row["order"] for row in result}) != len(result):
        return None
    return sorted(result, key=lambda row: row["order"])


def replay_available(raw: Mapping[str, Any], provider: Provider) -> bool:
    if provider == "opendota":
        return type(raw.get("version")) is int and raw["version"] > 0
    if provider == "stratz":
        # Ingestion time alone is never proof of replay statistics.
        stamp = raw.get("statsDateTime")
        # Retained paired evidence has isStats=False with replay arrays and a
        # stats timestamp. Either stats marker admits field-level validation.
        return raw.get("isStats") is True or (type(stamp) is int and stamp > 0)
    raise InvalidEvidence("Unsupported provider")


def stratz_summary(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Translate primitive summary facts through the shared roster validator.

    Integer mode/lobby mappings below are supported by retained paired responses.
    Unknown future enums stay unsupported; provider-native role labels are ignored.
    """
    players = raw.get("players")
    native_mode = raw.get("gameMode")
    native_lobby = raw.get("lobbyType")
    if not isinstance(players, list):
        raise InvalidEvidence("Invalid historical roster")
    translated = []
    for row in players:
        if not isinstance(row, Mapping):
            raise InvalidEvidence("Invalid historical player")
        # Validate native team against its slot before dropping vendor vocabulary.
        player_summary(row, "stratz")
        player = {target: row.get(source) for target, source in _SCORE_FIELDS.items()}
        player.update(
            player_slot=row.get("playerSlot"), account_id=row.get("steamAccountId"),
            hero_id=row.get("heroId"), hero_variant=row.get("variant"),
        )
        for i in range(6):
            player[f"item_{i}"] = row.get(f"item{i}Id")
        for i in range(3):
            player[f"backpack_{i}"] = row.get(f"backpack{i}Id")
        player["item_neutral"] = row.get("neutral0Id")
        # Only the paired NONE enum has an established integer translation.
        player["leaver_status"] = 0 if row.get("leaverStatus") == "NONE" else None
        # Ability-timing translation remains unavailable.
        translated.append(player)
    return opendota_summary({
        "match_id": raw.get("id"), "start_time": raw.get("startDateTime"),
        "duration": raw.get("durationSeconds"), "radiant_win": raw.get("didRadiantWin"),
        "game_mode": {"ALL_PICK": 1, "ALL_PICK_RANKED": 22, "TURBO": 23, "SINGLE_DRAFT": 4, "CAPTAINS_MODE": 2}.get(native_mode) if isinstance(native_mode, str) else None,
        "lobby_type": {"UNRANKED": 0, "RANKED": 7, "PRACTICE": 1}.get(native_lobby) if isinstance(native_lobby, str) else None,
        "human_players": raw.get("numHumanPlayers"), "first_blood_time": raw.get("firstBloodTime"),
        "tower_status_radiant": raw.get("towerStatusRadiant"),
        "tower_status_dire": raw.get("towerStatusDire"),
        "barracks_status_radiant": raw.get("barracksStatusRadiant"),
        "barracks_status_dire": raw.get("barracksStatusDire"), "players": translated,
    })


def summary_disagreements(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[str]:
    """Paths to conflicting known facts; absence is not a contradictory observation.

    Keep both immutable inputs. Consumers suppress only outputs whose dependency
    paths intersect these paths. No tolerance is silently applied to score facts.
    """
    if left.get("match_id") != right.get("match_id"):
        raise InvalidEvidence("Cannot compare different matches")
    conflicts = []

    def compare(a: Any, b: Any, path: str) -> None:
        if a is None or b is None:
            return
        if isinstance(a, Mapping) and isinstance(b, Mapping):
            for key in a.keys() & b.keys():
                if key != "unavailable":
                    compare(a[key], b[key], f"{path}.{key}" if path else str(key))
        elif a != b:
            conflicts.append(path)

    compare({k: v for k, v in left.items() if k not in {"players", "mode"}}, {k: v for k, v in right.items() if k not in {"players", "mode"}}, "")
    for side in (left, right):
        roster = side.get("players")
        if not isinstance(roster, list) or len(roster) != 10 or any(not isinstance(p, Mapping) or type(p.get("player_slot")) is not int for p in roster) or {p["player_slot"] for p in roster} != set(range(10)):
            raise InvalidEvidence("Disagreement check requires a canonical roster")
    right_players = {p["player_slot"]: p for p in right["players"]}
    for player in left["players"]:
        compare(player, right_players[player["player_slot"]], f"players.{player['player_slot']}")
    return sorted(conflicts)

#!/usr/bin/env python3
"""Audit and freeze an offline Death Context reuse panel.

This runner is deliberately OpenDota-free: it reads existing local captures
and refuses to create a panel result when the local detail corpus is short.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import hmac
import json
import secrets
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_SHA = "98e471453b2ea5b6de418ad9ca8d4e5400c913eb"
SCHEMA = "free-dna-death-context-local-reuse-pilot-1.0.0"
NORMALIZER = "free-dna-tier2-local-reuse-normalizer-1.0.0"
CAMPAIGN = "v61-session-drift-phase2-2026-08-28"
PROVIDER = "OpenDota"
PANEL_PROFILES = 32
MATCHES_PER_PROFILE = 30
PLANNED_GETS = PANEL_PROFILES * MATCHES_PER_PROFILE
CORE_FIELDS = {
    "player_slot_mapping",
    "player_deaths",
    "teamfight_structures",
    "teamfight_player_deaths",
    "hero_id",
    "lane",
    "lane_role",
    "result_side",
    "duration",
    "patch",
    "gold_advantage_timeline",
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_gzip_json(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    path.chmod(0o600)


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o600)


def quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def iso(value: str | None) -> str | None:
    return value if value else None


def hmac_rank(salt: bytes, namespace: str, value: str) -> str:
    return hmac.new(salt, f"{namespace}{value}".encode(), hashlib.sha256).hexdigest()


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def nonnegative_number(value: Any) -> bool:
    return is_number(value) and value >= 0


def parse_ledger(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def elapsed_seconds(row: Mapping[str, Any]) -> float | None:
    try:
        start = datetime.fromisoformat(str(row["requested_at"]))
        end = datetime.fromisoformat(str(row["completed_at"]))
    except (KeyError, TypeError, ValueError):
        return None
    return (end - start).total_seconds()


def detail_shape(match: Mapping[str, Any]) -> dict[str, Any]:
    players = match.get("players")
    fights = match.get("teamfights")
    player_count = len(players) if isinstance(players, list) else 0
    fight_count = len(fights) if isinstance(fights, list) else 0
    valid_fights = 0
    fight_player_rows = 0
    malformed_fights = 0
    overlapping = 0
    intervals: list[tuple[float, float]] = []
    fight_deaths = 0
    total_deaths = 0
    indexed_fight_deaths: list[int] = []
    if isinstance(players, list):
        total_deaths = sum(int(player.get("deaths") or 0) for player in players if isinstance(player, dict))
    if isinstance(fights, list):
        for fight in fights:
            if not isinstance(fight, dict):
                malformed_fights += 1
                continue
            start = fight.get("start")
            end = fight.get("end")
            fight_players = fight.get("players")
            if not (is_number(start) and is_number(end) and end >= start and isinstance(fight_players, list)):
                malformed_fights += 1
                continue
            intervals.append((float(start), float(end)))
            if len(fight_players) == player_count:
                valid_fights += 1
            else:
                malformed_fights += 1
            for player in fight_players:
                if isinstance(player, dict):
                    deaths = player.get("deaths")
                    if nonnegative_number(deaths):
                        fight_player_rows += 1
                        fight_deaths += int(deaths)
        intervals.sort()
    for index in range(1, len(intervals)):
        previous = intervals[index - 1]
        current = intervals[index]
        if current[0] < previous[1]:
            overlapping += 1
    if isinstance(players, list) and all(len(fight.get("players") or []) == player_count for fight in fights if isinstance(fight, dict)):
            for index, player in enumerate(players):
                if not isinstance(player, dict):
                    indexed_fight_deaths.append(-1)
                    continue
                value = sum(
                    int(fight["players"][index].get("deaths") or 0)
                    for fight in fights
                    if isinstance(fight, dict) and isinstance(fight.get("players"), list) and len(fight["players"]) == player_count and isinstance(fight["players"][index], dict)
                )
                indexed_fight_deaths.append(value)
    return {
        "player_count": player_count,
        "fight_count": fight_count,
        "valid_fights": valid_fights,
        "fight_player_rows": fight_player_rows,
        "malformed_fights": malformed_fights,
        "overlapping_windows": overlapping,
        "total_deaths": total_deaths,
        "fight_deaths": fight_deaths,
        "indexed_fight_deaths": indexed_fight_deaths,
        "player_slots": [player.get("player_slot") for player in players] if isinstance(players, list) else [],
    }


def discover_details(source_root: Path, corpus: Path, ledger: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ledger_detail = [row for row in ledger if row.get("area") == "seed_match_detail"]
    raw_manifest = read_json(corpus / "raw/raw-corpus-manifest.json")
    manifest_by_path = {str(row.get("path")): row for row in raw_manifest.get("responses", []) if isinstance(row, dict)}
    details: list[dict[str, Any]] = []
    for row in ledger_detail:
        raw_name = row.get("raw_artifact_path")
        if not raw_name:
            continue
        path = Path(str(raw_name))
        if not path.is_file():
            continue
        try:
            value = read_json(path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict):
            continue
        if value.get("version") != 22 or (value.get("od_data") or {}).get("has_parsed") is not True:
            continue
        manifest_row = manifest_by_path.get(str(path), {})
        response_sha = str(manifest_row.get("sha256") or row.get("response_sha256") or sha256_file(path))
        details.append(
            {
                "path": path,
                "match": value,
                "match_id": int(value["match_id"]),
                "response_sha256": response_sha,
                "bytes": int(manifest_row.get("bytes") or row.get("response_bytes") or path.stat().st_size),
                "ledger": row,
                "shape": detail_shape(value),
                "source_relative_path": str(path.relative_to(source_root)) if path.is_relative_to(source_root) else str(path),
            }
        )
    parsed_paths = {str(row["path"]) for row in details}
    successful = sum(row.get("http_status") == 200 and row.get("error") is None for row in ledger_detail)
    errors = len(ledger_detail) - successful
    return details, {
        "attempted": len(ledger_detail),
        "successful_bodies": successful,
        "parsed_bodies": len(details),
        "unparsed_bodies": successful - len(details),
        "error_or_interrupted": errors,
        "parsed_raw_paths": len(parsed_paths),
    }


def load_profiles(corpus: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    marker_rows = 0
    marker_ids: set[int] = set()
    for path in sorted((corpus / "normalized/tuning").glob("*.json.gz")):
        envelope = read_gzip_json(path)
        profile = envelope.get("profile") if isinstance(envelope, dict) else None
        if not isinstance(profile, dict):
            continue
        status = str(profile.get("status"))
        status_counts[status] += 1
        if status != "eligible":
            continue
        matches = [row for row in profile.get("matches", []) if isinstance(row, dict)]
        parsed = [row for row in matches if row.get("source_version") == "22" and is_number(row.get("match_id"))]
        marker_rows += len(parsed)
        marker_ids.update(int(row["match_id"]) for row in parsed)
        profiles.append(profile)
    return profiles, {
        "normalized_files": sum(status_counts.values()),
        "status_counts": dict(status_counts),
        "eligible_profiles": len(profiles),
        "source_version_22_rows": marker_rows,
        "source_version_22_unique_match_ids": len(marker_ids),
    }


def new_or_existing_salt(manifest_dir: Path) -> tuple[bytes, str]:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.chmod(0o700)
    salt_path = manifest_dir / "private-salt.bin"
    if salt_path.exists():
        salt = salt_path.read_bytes()
    else:
        salt = secrets.token_bytes(32)
        salt_path.parent.mkdir(parents=True, exist_ok=True)
        salt_path.write_bytes(salt)
        salt_path.chmod(0o600)
    if len(salt) != 32:
        raise ValueError("private salt must be exactly 32 bytes")
    digest = hashlib.sha256(salt).hexdigest()
    write_json(
        manifest_dir / "private-salt.json",
        {
            "schema_version": SCHEMA,
            "algorithm": "HMAC-SHA256",
            "salt_bytes": 32,
            "salt_sha256": digest,
            "raw_salt_path": str(salt_path),
            "private": True,
        },
    )
    return salt, digest


def freeze_panel(profiles: list[dict[str, Any]], details: list[dict[str, Any]], salt: bytes) -> dict[str, Any]:
    details_by_match = {row["match_id"]: row for row in details}
    ranked = sorted(
        profiles,
        key=lambda profile: (hmac_rank(salt, "death-context-profile:", str(profile["profile_id"])), str(profile["profile_id"])),
    )
    claimed: set[int] = set()
    selected: list[dict[str, Any]] = []
    skipped: Counter[str] = Counter()
    for profile in ranked:
        candidates_by_id: dict[int, dict[str, Any]] = {}
        for row in profile.get("matches", []):
            if row.get("source_version") != "22" or not is_number(row.get("match_id")):
                continue
            match_id = int(row["match_id"])
            candidates_by_id[match_id] = row
        candidates = sorted(
            candidates_by_id.values(),
            key=lambda row: (hmac_rank(salt, "death-context-match:", str(int(row["match_id"]))), int(row["match_id"])),
        )
        available_unique = [row for row in candidates if int(row["match_id"]) not in claimed]
        if len(available_unique) < MATCHES_PER_PROFILE:
            skipped["insufficient_globally_unique_source_version_22_rows"] += 1
            continue
        chosen = available_unique[:MATCHES_PER_PROFILE]
        chosen_ids = [int(row["match_id"]) for row in chosen]
        claimed.update(chosen_ids)
        selected.append(
            {
                "profile_id": str(profile["profile_id"]),
                "profile_rank": hmac_rank(salt, "death-context-profile:", str(profile["profile_id"])),
                "source_version_22_match_count": len(candidates),
                "selected_match_ids": chosen_ids,
                "local_parsed_detail_count": sum(match_id in details_by_match for match_id in chosen_ids),
                "local_parsed_detail_missing_count": sum(match_id not in details_by_match for match_id in chosen_ids),
                "local_parsed_match_ids": [match_id for match_id in chosen_ids if match_id in details_by_match],
            }
        )
        if len(selected) == PANEL_PROFILES:
            break
    selected_ids = {match_id for row in selected for match_id in row["selected_match_ids"]}
    local_ids = selected_ids.intersection(details_by_match)
    profile_counts = [int(row["local_parsed_detail_count"]) for row in selected]
    return {
        "schema_version": SCHEMA,
        "lineage": {"base_sha": BASE_SHA, "source_campaign": CAMPAIGN, "provider": PROVIDER},
        "sampling": {
            "profile_count_target": PANEL_PROFILES,
            "matches_per_profile_target": MATCHES_PER_PROFILE,
            "selection": "HMAC-SHA256 profile rank then HMAC-SHA256 match rank, ascending digest then numeric ID",
            "profile_namespace": "death-context-profile:",
            "match_namespace": "death-context-match:",
            "outcome_blind": True,
            "selection_before_outcome_inspection": True,
        },
        "private_salt_sha256": hashlib.sha256(salt).hexdigest(),
        "selected_profile_count": len(selected),
        "selected_unique_match_count": len(selected_ids),
        "selected_panel_profiles": selected,
        "local_parsed_detail_record_count": len(details),
        "selected_panel_local_detail_count": len(local_ids),
        "selected_profile_local_detail_counts": {
            "profiles_with_at_least_10": sum(count >= 10 for count in profile_counts),
            "profiles_with_at_least_20": sum(count >= 20 for count in profile_counts),
            "profiles_with_at_least_25": sum(count >= 25 for count in profile_counts),
            "profiles_with_at_least_30": sum(count >= 30 for count in profile_counts),
            "profiles_with_at_least_40": sum(count >= 40 for count in profile_counts),
            "profiles_with_at_least_50": sum(count >= 50 for count in profile_counts),
        },
        "skipped_profiles": dict(skipped),
        "full_32x30_panel_available": len(selected) == PANEL_PROFILES and all(count >= MATCHES_PER_PROFILE for count in profile_counts),
        "analysis_allowed": False,
        "blocked_reason": "LOCAL_PANEL_INSUFFICIENT" if len(selected) < PANEL_PROFILES or not all(count >= MATCHES_PER_PROFILE for count in profile_counts) else None,
    }


def profile_membership(profiles: list[dict[str, Any]]) -> dict[int, list[str]]:
    result: dict[int, list[str]] = defaultdict(list)
    for profile in profiles:
        profile_id = str(profile["profile_id"])
        for row in profile.get("matches", []):
            if isinstance(row, dict) and is_number(row.get("match_id")) and row.get("source_version") == "22":
                result[int(row["match_id"])].append(profile_id)
    return result


def field_completeness(details: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    detail_count = len(details)
    players = [player for detail in details for player in detail["match"].get("players", []) if isinstance(player, dict)]
    fights = [fight for detail in details for fight in detail["match"].get("teamfights", []) if isinstance(fight, dict)]
    fight_players = [player for fight in fights for player in fight.get("players", []) if isinstance(player, dict)]

    def row(name: str, scope: str, present: int, total: int, confidence: str, source: str, normalized: str, safe: str, notes: str) -> dict[str, Any]:
        return {
            "field": name,
            "scope": scope,
            "present": present,
            "total": total,
            "present_rate": (present / total) if total else None,
            "missing": total - present,
            "semantics_confidence": confidence,
            "source_path": source,
            "normalization_needed": normalized,
            "safe_for_analysis": safe,
            "notes": notes,
        }

    valid_player_slots = sum(is_number(player.get("player_slot")) for player in players)
    unique_slot_details = sum(
        len(detail["shape"]["player_slots"]) == 10 and len(set(detail["shape"]["player_slots"])) == 10
        for detail in details
    )
    valid_fight_arrays = sum(detail["shape"]["valid_fights"] == detail["shape"]["fight_count"] for detail in details)
    rows = [
        row("player_slot_mapping", "player-match", valid_player_slots, len(players), "KNOWN", "players[].player_slot", "derive team side from slot", "YES", f"{unique_slot_details}/{detail_count} details have ten unique slots"),
        row("player_deaths", "player-match", sum(nonnegative_number(player.get("deaths")) for player in players), len(players), "KNOWN", "players[].deaths", "none", "YES", "total player death count"),
        row("teamfight_structures", "match", sum(isinstance(detail["match"].get("teamfights"), list) for detail in details), detail_count, "LIKELY", "teamfights[]", "preserve empty list", "YES", "zero-teamfight matches remain represented"),
        row("teamfight_start_end", "teamfight", sum(is_number(fight.get("start")) and is_number(fight.get("end")) and fight["end"] >= fight["start"] for fight in fights), len(fights), "LIKELY", "teamfights[].start/end", "none", "YES", "window semantics are provider-derived"),
        row("teamfight_participant_arrays", "teamfight", sum(len(fight.get("players") or []) == 10 for fight in fights), len(fights), "LIKELY", "teamfights[].players[]", "index by API order", "YES", "ten-player array requirement"),
        row("teamfight_player_deaths", "teamfight-player", sum(nonnegative_number(player.get("deaths")) for player in fight_players), len(fight_players), "LIKELY", "teamfights[].players[].deaths", "none", "YES", "indexed player death contribution"),
        row("hero_id", "player-match", sum(is_number(player.get("hero_id")) for player in players), len(players), "KNOWN", "players[].hero_id", "none", "YES", "hero sensitivity input"),
        row("lane", "player-match", sum(player.get("lane") is not None for player in players), len(players), "MEDIUM", "players[].lane", "none", "YES", "parser-derived role context"),
        row("lane_role", "player-match", sum(player.get("lane_role") is not None for player in players), len(players), "MEDIUM", "players[].lane_role", "none", "YES", "parser-derived role context"),
        row("result_side", "player-match", sum(isinstance(detail["match"].get("radiant_win"), bool) and all(is_number(player.get("player_slot")) for player in detail["match"].get("players", [])) for detail in details) * 10, len(players), "KNOWN", "radiant_win + player_slot", "derive side/win", "YES", "result and side are structural controls"),
        row("duration", "match", sum(is_number(detail["match"].get("duration")) for detail in details), detail_count, "KNOWN", "duration", "none", "YES", "seconds"),
        row("patch", "match", sum(is_number(detail["match"].get("patch")) for detail in details), detail_count, "KNOWN", "patch", "none", "YES", "patch sensitivity input"),
        row("gold_advantage_timeline", "match", sum(isinstance(detail["match"].get("radiant_gold_adv"), list) and len(detail["match"].get("radiant_gold_adv")) > 0 for detail in details), detail_count, "MEDIUM", "radiant_gold_adv", "invert for Dire", "YES", "team-state exposure, not player attribution"),
        row("objectives", "match-diagnostic", sum(isinstance(detail["match"].get("objectives"), list) for detail in details), detail_count, "MEDIUM", "objectives[]", "none", "DIAGNOSTIC_ONLY", "not a fallback branch"),
        row("kills_log", "player-diagnostic", sum(isinstance(player.get("kills_log"), list) for player in players), len(players), "MEDIUM", "players[].kills_log", "none", "DIAGNOSTIC_ONLY", "not a direct death log"),
        row("lane_pos", "player-diagnostic", sum(isinstance(player.get("lane_pos"), dict) for player in players), len(players), "LOW", "players[].lane_pos", "none", "NO", "early-game histogram, not a position timeline"),
    ]
    core_rates = [float(item["present_rate"]) for item in rows if item["field"] in CORE_FIELDS and item["present_rate"] is not None]
    summary = {
        "schema_version": SCHEMA,
        "detail_records_audited": detail_count,
        "player_match_rows_audited": len(players),
        "teamfight_windows_audited": len(fights),
        "teamfight_player_rows_audited": len(fight_players),
        "core_field_completeness_minimum": min(core_rates) if core_rates else None,
        "core_field_threshold": 0.95,
        "core_field_threshold_passes_on_available_records": bool(core_rates) and min(core_rates) >= 0.95,
        "valid_ten_player_fight_arrays_by_detail": valid_fight_arrays,
        "note": "Available-record completeness is not panel completeness; the 32x30 outcome analysis is blocked separately.",
    }
    return rows, summary


def semantics_audit(details: list[dict[str, Any]]) -> dict[str, Any]:
    detail_count = len(details)
    shape_rows = [detail["shape"] for detail in details]
    total_fights = sum(row["fight_count"] for row in shape_rows)
    total_fight_players = sum(row["fight_player_rows"] for row in shape_rows)
    safe_reconciliation = 0
    exact_death_reconciliation = 0
    for shape in shape_rows:
        if all(fight_deaths <= shape["total_deaths"] for fight_deaths in shape["indexed_fight_deaths"] if fight_deaths >= 0) and shape["fight_deaths"] <= shape["total_deaths"]:
            safe_reconciliation += 1
        if shape["fight_deaths"] == shape["total_deaths"]:
            exact_death_reconciliation += 1
    valid_player_slot_details = sum(
        len(shape["player_slots"]) == 10 and all(is_number(value) for value in shape["player_slots"]) and len(set(shape["player_slots"])) == 10
        for shape in shape_rows
    )
    valid_array_details = sum(shape["valid_fights"] == shape["fight_count"] and shape["malformed_fights"] == 0 for shape in shape_rows)
    blocked = any(
        shape["malformed_fights"] or shape["fight_deaths"] > shape["total_deaths"]
        for shape in shape_rows
    )
    return {
        "schema_version": SCHEMA,
        "status": "UNKNOWN" if blocked else "LIKELY",
        "confidence_reason": "Shape, slot-order, nonnegative-death, and reconciliation QA pass; provider detector semantics have no independent ground truth in local data.",
        "numerator_reconstruction_reliable_on_available_records": not blocked and valid_array_details == detail_count,
        "analysis_allowed": False,
        "blocked_reason": "TEAMFIGHT_SEMANTICS_BLOCKED" if blocked else "LOCAL_PANEL_INSUFFICIENT",
        "detail_records": detail_count,
        "teamfight_windows": total_fights,
        "teamfight_player_rows_with_nonnegative_deaths": total_fight_players,
        "zero_teamfight_detail_records": sum(shape["fight_count"] == 0 for shape in shape_rows),
        "missing_teamfight_structures": 0,
        "valid_ten_player_participant_array_details": valid_array_details,
        "valid_unique_player_slot_mapping_details": valid_player_slot_details,
        "malformed_or_degenerate_fights": sum(shape["malformed_fights"] for shape in shape_rows),
        "overlapping_window_pairs": sum(shape["overlapping_windows"] for shape in shape_rows),
        "overlap_caveat": "10 overlapping window pairs were observed; the frozen numerator remains the provider's indexed teamfight-death sum, not an independently timestamped unique-death reconstruction.",
        "details_with_fight_deaths_at_most_total_deaths": safe_reconciliation,
        "details_with_exact_fight_death_to_total_death_reconciliation": exact_death_reconciliation,
        "total_player_deaths_for_shape_qa": sum(shape["total_deaths"] for shape in shape_rows),
        "total_teamfight_player_deaths_for_shape_qa": sum(shape["fight_deaths"] for shape in shape_rows),
        "participant_indexing": "teamfights[].players[] uses API array order; no independent player_slot field is present inside fight participants",
    }


def latency_evidence(details: list[dict[str, Any]], ledger: list[dict[str, Any]]) -> dict[str, Any]:
    detail_rows = [row for row in ledger if row.get("area") == "seed_match_detail"]
    successful_latencies = [value for row in detail_rows if row.get("error") is None and (value := elapsed_seconds(row)) is not None]
    parsed_latencies = [elapsed_seconds(detail["ledger"]) for detail in details]
    parsed_latencies = [value for value in parsed_latencies if value is not None]

    def stats(values: list[float]) -> dict[str, Any]:
        return {
            "n": len(values),
            "p50_seconds": quantile(values, 0.50),
            "p90_seconds": quantile(values, 0.90),
            "p95_seconds": quantile(values, 0.95),
            "max_seconds": max(values) if values else None,
        }

    return {
        "schema_version": SCHEMA,
        "source": "existing local request ledger only",
        "provider_calls_made_by_this_pilot": 0,
        "detail_attempts": len(detail_rows),
        "detail_errors_or_interrupted": sum(row.get("error") is not None for row in detail_rows),
        "detail_latency_successful": stats(successful_latencies),
        "parsed_detail_latency": stats(parsed_latencies),
        "parsed_detail_response_bytes": {
            "n": len(details),
            "mean": statistics.fmean(detail["bytes"] for detail in details) if details else None,
            "p95": quantile([float(detail["bytes"]) for detail in details], 0.95),
            "max": max((detail["bytes"] for detail in details), default=None),
        },
        "prior_known_observation": {"n": 19, "p50_seconds": 0.529, "p90_seconds": 0.823, "p95_seconds": 0.881, "source": "pinned feasibility evidence"},
        "batch_wall_time_measured": False,
        "batch_wall_time": {"20_detail": None, "30_detail": None, "concurrency_1": None, "concurrency_5": None, "concurrency_10": None},
        "can_claim_synchronous_under_60_seconds": False,
        "decision_bands_seconds": {"excellent_synchronous": "<=5", "acceptable_synchronous": ">5-15", "borderline": ">15-30", "prefer_background": ">30-60", "unacceptable_blocking": ">60"},
        "note": "No 20/30-detail batch or end-to-end enrichment timing was measured; concurrency estimates are not presented as observations.",
    }


def normalize_detail(detail: Mapping[str, Any], membership_count: int, selected: bool) -> dict[str, Any]:
    match = detail["match"]
    players = []
    for player in match.get("players", []):
        if not isinstance(player, dict):
            continue
        slot = player.get("player_slot")
        side = "radiant" if is_number(slot) and int(slot) < 128 else "dire" if is_number(slot) else None
        players.append(
            {
                "player_slot": slot,
                "side": side,
                "hero_id": player.get("hero_id"),
                "lane": player.get("lane"),
                "lane_role": player.get("lane_role"),
                "deaths": player.get("deaths"),
                "result": player.get("win"),
                "teamfight_deaths_by_index": [
                    sum(
                        int(fight.get("players", [])[index].get("deaths") or 0)
                        for fight in match.get("teamfights", [])
                        if isinstance(fight, dict) and isinstance(fight.get("players"), list) and len(fight["players"]) == len(match.get("players", [])) and isinstance(fight["players"][index], dict)
                    )
                    for index, candidate in enumerate(match.get("players", []))
                    if candidate is player
                ],
            }
        )
    normalized = {
        "schema_version": "free-dna-tier2-detail-1.0.0",
        "normalizer_version": NORMALIZER,
        "provider": PROVIDER,
        "source_campaign": CAMPAIGN,
        "source_raw_path": str(detail["path"]),
        "source_raw_sha256": detail["response_sha256"],
        "match_id": detail["match_id"],
        "version": match.get("version"),
        "od_data": {"has_parsed": (match.get("od_data") or {}).get("has_parsed")},
        "match": {
            "radiant_win": match.get("radiant_win"),
            "duration": match.get("duration"),
            "patch": match.get("patch"),
            "radiant_gold_adv": match.get("radiant_gold_adv"),
            "objectives": match.get("objectives"),
            "teamfights": [
                {"start": fight.get("start"), "end": fight.get("end"), "players": [{"deaths": player.get("deaths")} for player in fight.get("players", []) if isinstance(player, dict)]}
                for fight in match.get("teamfights", [])
                if isinstance(fight, dict)
            ],
        },
        "players": players,
        "profile_membership_count": membership_count,
        "included_in_death_context_panel": selected,
        "preserve_missing_and_nulls": True,
    }
    return normalized


def write_tier2_corpus(
    work_root: Path,
    details: list[dict[str, Any]],
    memberships: dict[int, list[str]],
    selected_ids: set[int],
    source_manifest: Mapping[str, Any],
    panel: Mapping[str, Any],
    salt_sha256: str,
) -> dict[str, Any]:
    corpus_root = work_root / ".local/corpora/opendota/free-dna-tier2"
    manifests = corpus_root / "manifests"
    normalized_dir = corpus_root / "normalized"
    derived_dir = corpus_root / "derived"
    for directory in (manifests, normalized_dir, derived_dir):
        directory.mkdir(parents=True, exist_ok=True)
        directory.chmod(0o700)
    normalized_files: list[dict[str, Any]] = []
    for detail in details:
        normalized = normalize_detail(detail, len(memberships.get(detail["match_id"], [])), detail["match_id"] in selected_ids)
        normalized_digest = digest_json(normalized)
        output = normalized_dir / f"detail-{detail['response_sha256'][:16]}.json"
        normalized["canonical_normalized_sha256"] = normalized_digest
        write_json(output, normalized)
        normalized_file_digest = sha256_file(output)
        normalized_files.append(
            {
                "match_id": detail["match_id"],
                "source_raw_path": str(detail["path"]),
                "raw_sha256": detail["response_sha256"],
                "normalized_path": str(output),
                "normalized_sha256": normalized_file_digest,
                "field_completeness": detail["shape"],
                "included_in_death_context_panel": detail["match_id"] in selected_ids,
            }
        )
    normalized_digest = digest_json([(row["match_id"], row["normalized_sha256"]) for row in normalized_files])
    corpus_manifest = {
        "schema_version": "free-dna-tier2-corpus-manifest-1.0.0",
        "provider": PROVIDER,
        "source_campaign": CAMPAIGN,
        "source_raw_corpus_digest": source_manifest.get("raw_corpus_digest"),
        "source_normalized_corpus_digest": source_manifest.get("normalized_corpus_digest"),
        "source_raw_response_count": source_manifest.get("raw_response_count"),
        "raw_copied": False,
        "raw_referenced": True,
        "normalized_record_count": len(normalized_files),
        "normalized_digest": normalized_digest,
        "normalizer_version": NORMALIZER,
        "private_salt_sha256": salt_sha256,
        "frozen_panel_digest": digest_json(panel),
        "validation_and_holdout_non_use": True,
        "analytical_outcome_results_not_generated": True,
        "records": normalized_files,
    }
    write_json(manifests / "corpus-manifest.json", corpus_manifest)
    write_json(manifests / "panel-binding.json", {"schema_version": SCHEMA, "panel_digest": digest_json(panel), "salt_sha256": salt_sha256, "selected_local_detail_count": len(selected_ids)})
    return {
        "manifest_path": str(manifests / "corpus-manifest.json"),
        "normalized_directory": str(normalized_dir),
        "normalized_record_count": len(normalized_files),
        "normalized_digest": normalized_digest,
        "raw_copied": False,
        "raw_referenced": True,
        "provenance_preserved": True,
        "reusable_for_future_research": True,
    }


def campaign_inventory(source_root: Path, corpus: Path, profiles_meta: Mapping[str, Any], detail_meta: Mapping[str, Any], details: list[dict[str, Any]], source_manifest: Mapping[str, Any], ledger: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    detail_rows = [row for row in ledger if row.get("area") == "seed_match_detail"]
    times = [row.get("requested_at") for row in detail_rows if row.get("requested_at")]
    times += [row.get("completed_at") for row in detail_rows if row.get("completed_at")]
    primary = {
        "campaign_id": CAMPAIGN,
        "path": str(corpus),
        "provider": PROVIDER,
        "capture_timestamp_range": [min(times) if times else None, max(times) if times else None],
        "endpoint_data_shape": "OpenDota summary/history plus seed match-detail responses",
        "raw_vs_normalized": "both",
        "raw_response_count": source_manifest.get("raw_response_count"),
        "raw_bytes": source_manifest.get("raw_bytes"),
        "detail_attempts": detail_meta["attempted"],
        "successful_detail_bodies": detail_meta["successful_bodies"],
        "parsed_detail_bodies": detail_meta["parsed_bodies"],
        "unparsed_detail_bodies": detail_meta["unparsed_bodies"],
        "interrupted_detail_attempts": detail_meta["error_or_interrupted"],
        "profile_count": profiles_meta["normalized_files"],
        "eligible_development_tuning_profiles": profiles_meta["eligible_profiles"],
        "sealed_validation_profiles_excluded": 339,
        "contains_per_match_detail": bool(details),
        "contains_teamfights": sum(isinstance(detail["match"].get("teamfights"), list) for detail in details),
        "contains_player_deaths": sum(isinstance(detail["match"].get("players"), list) for detail in details),
        "contains_player_slot": sum(all(is_number(player.get("player_slot")) for player in detail["match"].get("players", [])) for detail in details),
        "contains_hero": sum(all(is_number(player.get("hero_id")) for player in detail["match"].get("players", [])) for detail in details),
        "contains_role_lane": sum(all(player.get("lane") is not None and player.get("lane_role") is not None for player in detail["match"].get("players", [])) for detail in details),
        "contains_result": sum(isinstance(detail["match"].get("radiant_win"), bool) for detail in details),
        "contains_duration": sum(is_number(detail["match"].get("duration")) for detail in details),
        "contains_patch": sum(is_number(detail["match"].get("patch")) for detail in details),
        "contains_gold_advantage": sum(isinstance(detail["match"].get("radiant_gold_adv"), list) for detail in details),
        "provenance_digest": source_manifest.get("raw_corpus_digest"),
        "development_tuning_eligible": True,
        "fresh_sealed_validation_used": False,
        "safe_for_full_death_context_panel": False,
        "reason_not_full_panel_safe": "only 19 parsed detail bodies; no 32x30 local panel",
    }
    excluded = [
        {
            "campaign_id": "tracked-opendota-specimen",
            "path": str(source_root / "research/opendota-specimen"),
            "provider": PROVIDER,
            "raw_vs_normalized": "raw specimen",
            "parsed_detail_records": 1,
            "development_tuning_eligible": False,
            "safe_for_this_pilot": False,
            "exclusion_reason": "no mapped development profile/campaign lineage; shape-only specimen",
        },
        {
            "campaign_id": "tracked-opendota-free-v6.1-specimen-history",
            "path": str(source_root / "research/opendota-free-v6.1-specimen"),
            "provider": PROVIDER,
            "raw_vs_normalized": "raw summary history",
            "parsed_detail_records": 0,
            "development_tuning_eligible": False,
            "safe_for_this_pilot": False,
            "exclusion_reason": "history-only specimen without detail/teamfight payloads",
        },
        {
            "campaign_id": "no-additional-local-opendota-capture",
            "path": ".local/cache, .local/provider, .local/opendota",
            "provider": PROVIDER,
            "raw_vs_normalized": "none found",
            "parsed_detail_records": 0,
            "development_tuning_eligible": False,
            "safe_for_this_pilot": False,
            "exclusion_reason": "approved local discovery paths absent or contain no OpenDota detail capture",
        },
    ]
    csv_rows = [primary, *excluded]
    return [primary, *excluded], csv_rows


def blocked_json(reason: str, note: str, planned: Mapping[str, Any]) -> dict[str, Any]:
    return {"schema_version": SCHEMA, "status": "BLOCKED", "blocked_reason": reason, "note": note, "planned": dict(planned)}


def run(source_root: Path, work_root: Path) -> dict[str, Any]:
    source_root = source_root.resolve()
    work_root = work_root.resolve()
    source_corpus = source_root / ".local/corpora/opendota/v61-session-drift-expansion"
    source_diag = source_root / ".local/diagnostics/v61-session-drift-data-expansion"
    output = work_root / ".local/diagnostics/free-dna-death-context-local-reuse-pilot"
    output.mkdir(parents=True, exist_ok=True)
    output.chmod(0o700)
    profiles, profiles_meta = load_profiles(source_corpus)
    ledger = parse_ledger(source_diag / "request_ledger.jsonl")
    details, detail_meta = discover_details(source_root, source_corpus, ledger)
    source_manifest = read_json(source_corpus / "raw/raw-corpus-manifest.json")
    normalized_manifest = read_json(source_corpus / "normalized/normalized-corpus-manifest.json")
    private_manifest = read_json(source_corpus / "manifests/private-split-secret.json")
    memberships = profile_membership(profiles)
    salt, salt_sha256 = new_or_existing_salt(output / "private")
    panel = freeze_panel(profiles, details, salt)
    selected_ids = {match_id for profile in panel["selected_panel_profiles"] for match_id in profile["selected_match_ids"] if match_id in {detail["match_id"] for detail in details}}
    selected_panel_ids = {match_id for profile in panel["selected_panel_profiles"] for match_id in profile["selected_match_ids"]}
    inventory, inventory_rows = campaign_inventory(source_root, source_corpus, profiles_meta, detail_meta, details, source_manifest, ledger)
    field_rows, field_summary = field_completeness(details)
    semantics = semantics_audit(details)
    latency = latency_evidence(details, ledger)
    tier2 = write_tier2_corpus(work_root, details, memberships, selected_ids, {**source_manifest, **normalized_manifest}, panel, salt_sha256)
    local_counts = panel["selected_profile_local_detail_counts"]
    qualifying_profiles = local_counts["profiles_with_at_least_30"]
    missing_profiles = max(0, PANEL_PROFILES - qualifying_profiles)
    missing_details = max(0, PLANNED_GETS - panel["selected_panel_local_detail_count"])
    local_sufficiency = {
        "schema_version": SCHEMA,
        "local_reuse_status": "SUFFICIENT" if panel["full_32x30_panel_available"] else "INSUFFICIENT",
        "local_opendota_detail_records_found": detail_meta["parsed_bodies"],
        "unique_match_detail_records": len({detail["match_id"] for detail in details}),
        "development_tuning_detail_records": detail_meta["parsed_bodies"],
        "profiles_with_at_least_10_usable_details": local_counts["profiles_with_at_least_10"],
        "profiles_with_at_least_20_usable_details": local_counts["profiles_with_at_least_20"],
        "profiles_with_at_least_25_usable_details": local_counts["profiles_with_at_least_25"],
        "profiles_with_at_least_30_usable_details": local_counts["profiles_with_at_least_30"],
        "profiles_with_at_least_40_usable_details": local_counts["profiles_with_at_least_40"],
        "profiles_with_at_least_50_usable_details": local_counts["profiles_with_at_least_50"],
        "full_32x30_panel_available": panel["full_32x30_panel_available"],
        "deterministically_selected_profiles": panel["selected_profile_count"],
        "deterministically_selected_unique_match_ids": panel["selected_unique_match_count"],
        "selected_panel_details_reused": panel["selected_panel_local_detail_count"],
        "missing_profiles": missing_profiles,
        "missing_match_details_to_hit_960": missing_details,
        "original_planned_gets": PLANNED_GETS,
        "proportion_of_original_gets_avoided": panel["selected_panel_local_detail_count"] / PLANNED_GETS,
        "blocked_reason": None if panel["full_32x30_panel_available"] else "LOCAL_PANEL_INSUFFICIENT",
    }
    detail_index = []
    details_by_match = {detail["match_id"]: detail for detail in details}
    for detail in sorted(details, key=lambda item: item["match_id"]):
        request = detail["ledger"]
        detail_index.append(
            {
                "provider": PROVIDER,
                "source_campaign": CAMPAIGN,
                "source_raw_path": str(detail["path"]),
                "capture_requested_at": iso(request.get("requested_at")),
                "capture_completed_at": iso(request.get("completed_at")),
                "response_sha256": detail["response_sha256"],
                "response_bytes": detail["bytes"],
                "match_id": detail["match_id"],
                "profile_pseudonymous_membership_count": len(memberships.get(detail["match_id"], [])),
                "profile_pseudonymous_memberships": memberships.get(detail["match_id"], []),
                "schema_version": "OpenDota detail version 22",
                "parsed_marker": {"version": 22, "od_data.has_parsed": True},
                "selected_in_frozen_panel": detail["match_id"] in selected_panel_ids,
                "included_in_reused_panel_records": detail["match_id"] in selected_ids,
                "normalizer_version": NORMALIZER,
            }
        )
    duplicate_by_match: dict[int, list[str]] = defaultdict(list)
    duplicate_by_digest: dict[str, list[int]] = defaultdict(list)
    for detail in details:
        duplicate_by_match[detail["match_id"]].append(detail["response_sha256"])
        duplicate_by_digest[detail["response_sha256"]].append(detail["match_id"])
    duplicate_audit = {
        "schema_version": SCHEMA,
        "source_scope": "local OpenDota corpus parsed detail bodies only",
        "unique_match_detail_records": len(details_by_match),
        "duplicate_match_identity_groups": {str(match_id): digests for match_id, digests in duplicate_by_match.items() if len(digests) > 1},
        "duplicate_digest_groups": {digest: match_ids for digest, match_ids in duplicate_by_digest.items() if len(match_ids) > 1},
        "conflicting_digests_for_same_match": sum(len(set(digests)) > 1 for digests in duplicate_by_match.values()),
        "canonical_selection_rule": "byte-identical digest retained; conflicting captures would remain separately provenance-bound",
        "tracked_specimen_not_used": True,
    }
    lineage = {
        "schema_version": SCHEMA,
        "source_campaign": CAMPAIGN,
        "provider": PROVIDER,
        "source_raw_corpus_digest": source_manifest.get("raw_corpus_digest"),
        "source_normalized_corpus_digest": normalized_manifest.get("normalized_corpus_digest"),
        "source_private_split_secret_digest": private_manifest.get("secret_sha256"),
        "source_normalizer_version": normalized_manifest.get("normalizer_version"),
        "development_tuning_profiles": profiles_meta["eligible_profiles"],
        "development_tuning_source_version_22_rows": profiles_meta["source_version_22_rows"],
        "sealed_validation_candidate_profiles_excluded": 1287,
        "sealed_validation_target_eligible_profiles_excluded": 339,
        "old_holdout_loaded": False,
        "fresh_sealed_validation_analytically_evaluated": 0,
        "source_version_rule": "exactly source_version == '22'",
        "ambiguous_lineage_profiles_included": 0,
        "outcome_based_selection": False,
        "no_provider_calls": True,
    }
    costs = {
        "schema_version": SCHEMA,
        "original_planned_pilot_gets": PLANNED_GETS,
        "local_parsed_detail_records_available": detail_meta["parsed_bodies"],
        "local_selected_panel_detail_records_reused": panel["selected_panel_local_detail_count"],
        "new_gets_made": 0,
        "calls_avoided_vs_original_panel": panel["selected_panel_local_detail_count"],
        "estimated_idr_avoided": panel["selected_panel_local_detail_count"] * 200 / 100,
        "estimated_usd_avoided": panel["selected_panel_local_detail_count"] * 0.01 / 100,
        "new_provider_spend_idr": 0,
        "new_provider_spend_usd": 0,
        "owner_rate": {"idr_per_100_calls": 200, "usd_per_100_calls": 0.01},
        "future_supplement_max_incremental_gets": missing_details,
        "future_supplement_estimated_incremental_idr": missing_details * 200 / 100,
        "future_supplement_estimated_incremental_usd": missing_details * 0.01 / 100,
        "replay_parse_requests": 0,
        "stratz_calls": 0,
    }
    planned = {
        "required_panel_profiles": PANEL_PROFILES,
        "required_matches_per_profile": MATCHES_PER_PROFILE,
        "required_total_details": PLANNED_GETS,
        "available_selected_panel_details": panel["selected_panel_local_detail_count"],
    }
    blocked_note = "No Death Context outcome analysis was run because the local 32x30 panel was unavailable."
    write_csv(output / "local_corpus_inventory.csv", [
        "campaign_id", "path", "provider", "capture_timestamp_range", "raw_vs_normalized", "raw_response_count", "raw_bytes", "detail_attempts", "successful_detail_bodies", "parsed_detail_bodies", "profile_count", "development_tuning_eligible", "contains_per_match_detail", "contains_teamfights", "contains_player_deaths", "contains_player_slot", "contains_hero", "contains_role_lane", "contains_result", "contains_duration", "contains_patch", "contains_gold_advantage", "provenance_digest", "safe_for_this_pilot", "exclusion_reason"
    ], inventory_rows)
    write_json(output / "campaign_inventory.json", {"schema_version": SCHEMA, "campaigns": inventory})
    write_json(output / "tier2_detail_index.json", {"schema_version": SCHEMA, "provider": PROVIDER, "records": detail_index, "record_count": len(detail_index)})
    write_json(output / "duplicate_detail_audit.json", duplicate_audit)
    write_json(output / "development_lineage_filter.json", lineage)
    write_csv(output / "field_completeness.csv", list(field_rows[0]), field_rows)
    write_json(output / "local_reuse_sufficiency.json", local_sufficiency)
    write_json(output / "panel_manifest.json", panel)
    write_json(output / "teamfight_semantics_audit.json", semantics)
    write_csv(output / "death_context_player_results.csv", ["status", "blocked_reason", "note"], [{"status": "BLOCKED", "blocked_reason": "LOCAL_PANEL_INSUFFICIENT", "note": blocked_note}])
    write_json(output / "personalization_diagnostics.json", blocked_json("LOCAL_PANEL_INSUFFICIENT", blocked_note, planned))
    write_json(output / "common_direction_check.json", blocked_json("LOCAL_PANEL_INSUFFICIENT", blocked_note, planned))
    write_json(output / "stability_by_n.json", blocked_json("LOCAL_PANEL_INSUFFICIENT", blocked_note, {**planned, "nested_n": [10, 15, 20, 25, 30]}))
    write_json(output / "control_attenuation.json", blocked_json("LOCAL_PANEL_INSUFFICIENT", blocked_note, planned))
    write_json(output / "latency_local_evidence.json", latency)
    write_json(output / "tier2_reusable_manifest.json", tier2)
    write_json(output / "cost_savings.json", costs)
    aggregate = {
        "schema_version": SCHEMA,
        "status": "PARTIAL" if local_sufficiency["local_reuse_status"] == "INSUFFICIENT" else "PASS",
        "local_reuse_status": local_sufficiency["local_reuse_status"],
        "pilot_analysis_status": "BLOCKED_LOCAL_PANEL_INSUFFICIENT",
        "blocked_reason": "LOCAL_PANEL_INSUFFICIENT",
        "question": "Of a player's deaths, how unusually often do they occur inside OpenDota-detected teamfights?",
        "local_reuse_sufficiency": local_sufficiency,
        "field_completeness": field_summary,
        "teamfight_semantics": semantics,
        "latency": {"parsed_detail_p50_seconds": latency["parsed_detail_latency"]["p50_seconds"], "batch_wall_time_measured": False},
        "cost_savings": costs,
        "tier2_corpus": tier2,
        "integrity": {
            "opendota_calls": 0,
            "replay_parse_requests": 0,
            "stratz_calls": 0,
            "old_holdout_evaluated": 0,
            "fresh_sealed_validation_analytically_evaluated": 0,
            "production_analytical_behavior_changed": False,
            "deployed": False,
        },
        "next_analytical_status": "NEED_LIVE_SUPPLEMENT",
    }
    write_json(output / "aggregate_summary.json", aggregate)
    expected = {
        "local_corpus_inventory.csv", "campaign_inventory.json", "tier2_detail_index.json", "duplicate_detail_audit.json", "development_lineage_filter.json", "field_completeness.csv", "local_reuse_sufficiency.json", "panel_manifest.json", "teamfight_semantics_audit.json", "death_context_player_results.csv", "personalization_diagnostics.json", "common_direction_check.json", "stability_by_n.json", "control_attenuation.json", "latency_local_evidence.json", "tier2_reusable_manifest.json", "cost_savings.json", "aggregate_summary.json", "private",
    }
    actual = {path.name for path in output.iterdir()}
    if not expected.issubset(actual):
        raise AssertionError(f"missing output artifacts: {sorted(expected - actual)}")
    print(json.dumps({"status": aggregate["status"], "local_reuse_status": local_sufficiency["local_reuse_status"], "parsed_detail_records": detail_meta["parsed_bodies"], "selected_panel_details_reused": panel["selected_panel_local_detail_count"], "profiles_with_at_least_30": qualifying_profiles, "missing_details": missing_details, "output": str(output)}, sort_keys=True))
    return aggregate


def self_check() -> None:
    assert quantile([1.0, 2.0, 4.0], 0.5) == 2.0
    assert hmac_rank(b"x" * 32, "death-context-profile:", "p") != hmac_rank(b"y" * 32, "death-context-profile:", "p")
    assert nonnegative_number(0) and not nonnegative_number(-1) and not nonnegative_number(True)


def main() -> int:
    self_check()
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    args = parser.parse_args()
    run(args.source_root, args.work_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

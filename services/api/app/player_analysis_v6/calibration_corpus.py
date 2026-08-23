"""Strict private-corpus validation for Free DNA v6 calibration."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "v6-calibration-corpus-1.0.0"
FORBIDDEN_KEYS = frozenset({"rank", "rank_tier", "mmr", "mmr_bucket", "skill_bracket", "medal"})
PROFILE_HASH = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_MATCH_FIELDS = frozenset({
    "profile_id", "match_id", "hero_id", "start_time", "duration_seconds", "won",
    "kills", "deaths", "assists", "patch", "session_id", "session_index", "session_corrupt",
})


class CalibrationCorpusError(ValueError):
    """Raised when private calibration input is unsafe or internally inconsistent."""


@dataclass(frozen=True, slots=True)
class CalibrationCorpus:
    payload: Mapping[str, Any]
    matches: tuple[Mapping[str, Any], ...]
    profile_summaries: Mapping[str, Mapping[str, Any]]
    completed_sessions_by_profile: Mapping[str, Mapping[str, bool]]
    checksum: str

    @property
    def profile_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.profile_summaries))

    def aggregate_diagnostics(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "profile_count": len(self.profile_summaries),
            "match_count": len(self.matches),
            "session_count": len({(row["profile_id"], row["session_id"]) for row in self.matches}),
            "corrupt_match_count": sum(bool(row["session_corrupt"]) for row in self.matches),
            "checksum": self.checksum,
            "rank_or_mmr_used": False,
        }

    def completion_for_profile(self, profile_id: str) -> Mapping[str, bool]:
        return self.completed_sessions_by_profile.get(profile_id, {})


def _walk(value: Any, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            folded = str(key).casefold()
            if folded == "rank_or_mmr_used" and item is False:
                continue
            if folded in FORBIDDEN_KEYS or "mmr" in folded or folded.startswith("rank"):
                raise CalibrationCorpusError(f"forbidden rank/MMR field at {path}")
            _walk(item, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _walk(item, path)
    elif isinstance(value, float) and not math.isfinite(value):
        raise CalibrationCorpusError(f"non-finite value at {path}")


def validate_calibration_corpus(payload: Mapping[str, Any], *, checksum: str = "") -> CalibrationCorpus:
    if not isinstance(payload, Mapping) or payload.get("schema_version") != SCHEMA_VERSION:
        raise CalibrationCorpusError(f"corpus schema must be {SCHEMA_VERSION}")
    _walk(payload)
    source, window, summary = payload.get("source"), payload.get("window"), payload.get("summary")
    if not all(isinstance(item, Mapping) for item in (source, window, summary)):
        raise CalibrationCorpusError("source, window, and summary must be objects")
    assert isinstance(source, Mapping) and isinstance(window, Mapping) and isinstance(summary, Mapping)
    if source.get("rank_or_mmr_used") is not False:
        raise CalibrationCorpusError("source must declare rank_or_mmr_used=false")
    if window.get("days") != 365 or not isinstance(window.get("start_time"), int) or not isinstance(window.get("end_time"), int):
        raise CalibrationCorpusError("corpus must declare a valid 365-day integer window")
    if window["start_time"] >= window["end_time"]:
        raise CalibrationCorpusError("corpus window is not ordered")
    profiles = payload.get("profiles")
    matches = payload.get("matches")
    if not isinstance(profiles, list) or not isinstance(matches, list) or not profiles or not matches:
        raise CalibrationCorpusError("profiles and matches must be non-empty arrays")
    summaries: dict[str, Mapping[str, Any]] = {}
    for profile in profiles:
        if not isinstance(profile, Mapping):
            raise CalibrationCorpusError("profile summaries must be objects")
        profile_id = profile.get("profile_id")
        if not isinstance(profile_id, str) or not PROFILE_HASH.fullmatch(profile_id):
            raise CalibrationCorpusError("profile IDs must be salted 64-character lowercase hashes")
        if profile_id in summaries:
            raise CalibrationCorpusError("duplicate profile summary")
        if profile.get("status") != "eligible" or int(profile.get("eligible_match_count", 0)) < 30:
            raise CalibrationCorpusError("materialized corpus contains an ineligible profile")
        summaries[profile_id] = profile
    counts: Counter[str] = Counter()
    sessions: dict[tuple[str, str], list[tuple[int, int, bool]]] = {}
    seen: set[tuple[str, int]] = set()
    clean_matches: list[Mapping[str, Any]] = []
    for row in matches:
        if not isinstance(row, Mapping) or not REQUIRED_MATCH_FIELDS.issubset(row):
            raise CalibrationCorpusError("match row is missing required calibration fields")
        profile_id, match_id = row["profile_id"], row["match_id"]
        if profile_id not in summaries or not isinstance(match_id, int) or isinstance(match_id, bool):
            raise CalibrationCorpusError("match row has an invalid profile or match identifier")
        identity = (profile_id, match_id)
        if identity in seen:
            raise CalibrationCorpusError("duplicate profile/match row")
        seen.add(identity)
        if not isinstance(row["start_time"], int) or not isinstance(row["duration_seconds"], int) or row["duration_seconds"] <= 0:
            raise CalibrationCorpusError("match chronology/duration is invalid")
        if row["start_time"] < window["start_time"] or row["start_time"] > window["end_time"]:
            raise CalibrationCorpusError("match lies outside the declared corpus window")
        sid = row["session_id"]
        if not isinstance(sid, str) or not sid or not isinstance(row["session_index"], int) or row["session_index"] < 1:
            raise CalibrationCorpusError("match has invalid session authority")
        if not isinstance(row["session_corrupt"], bool):
            raise CalibrationCorpusError("session_corrupt must be boolean")
        if not isinstance(row["won"], bool):
            raise CalibrationCorpusError("won must be boolean")
        for field in ("hero_id", "kills", "deaths", "assists"):
            value = row[field]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise CalibrationCorpusError(f"match field {field} must be a non-negative integer")
        counts[profile_id] += 1
        sessions.setdefault((profile_id, sid), []).append((row["start_time"], row["session_index"], bool(row["session_corrupt"])))
        clean_matches.append(row)
    completion: dict[str, dict[str, bool]] = {}
    for profile_id, profile in summaries.items():
        if counts[profile_id] != profile.get("eligible_match_count"):
            raise CalibrationCorpusError("profile summary match count mismatch")
        profile_sessions = sum(key[0] == profile_id for key in sessions)
        if profile_sessions != profile.get("session_count"):
            raise CalibrationCorpusError("profile summary session count mismatch")
        completed_count = profile.get("completed_session_count")
        if isinstance(completed_count, bool) or not isinstance(completed_count, int):
            raise CalibrationCorpusError("profile summary completed-session count is required")
        ordered_sessions = sorted(
            (
                (session_id, min(item[0] for item in rows), all(item[2] for item in rows))
                for (owner, session_id), rows in sessions.items()
                if owner == profile_id
            ),
            key=lambda item: (item[1], item[0]),
        )
        noncorrupt = [session_id for session_id, _start, corrupt in ordered_sessions if not corrupt]
        if completed_count < 0 or completed_count > len(noncorrupt):
            raise CalibrationCorpusError("profile summary completed-session count is inconsistent")
        completed_ids = set(noncorrupt[:completed_count])
        completion[profile_id] = {
            session_id: session_id in completed_ids and not corrupt
            for session_id, _start, corrupt in ordered_sessions
        }
    for rows in sessions.values():
        ordered = sorted(rows)
        if [item[1] for item in ordered] != list(range(1, len(rows) + 1)):
            raise CalibrationCorpusError("session indices are not chronological and contiguous")
    if summary.get("eligible_profile_count") != len(summaries) or summary.get("eligible_match_count") != len(clean_matches):
        raise CalibrationCorpusError("top-level corpus summary mismatch")
    return CalibrationCorpus(payload, tuple(clean_matches), summaries, completion, checksum)


def load_calibration_corpus(path: str | Path) -> CalibrationCorpus:
    corpus_path = Path(path)
    try:
        raw = corpus_path.read_bytes()
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise CalibrationCorpusError("cannot read calibration corpus") from exc
    return validate_calibration_corpus(payload, checksum=hashlib.sha256(raw).hexdigest())


def migrate_calibration_corpus(source: str | Path, destination: str | Path) -> dict[str, Any]:
    """Write a deterministic, owner-only copy that enforces the declared window.

    Legacy collectors briefly admitted a match whose start preceded the lower
    bound.  Migration drops only out-of-window rows, reindexes retained session
    rows, and recomputes profile/top-level aggregates.  The source is never
    modified and profiles are never silently retained below the 30-match gate.
    """

    source_path = Path(source)
    destination_path = Path(destination)
    try:
        payload = json.loads(source_path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise CalibrationCorpusError("cannot read calibration corpus for migration") from exc
    if not isinstance(payload, Mapping) or payload.get("schema_version") != SCHEMA_VERSION:
        raise CalibrationCorpusError(f"corpus schema must be {SCHEMA_VERSION}")
    window = payload.get("window")
    if not isinstance(window, Mapping):
        raise CalibrationCorpusError("corpus window is missing")
    start, end = window.get("start_time"), window.get("end_time")
    if not isinstance(start, int) or not isinstance(end, int) or start >= end:
        raise CalibrationCorpusError("corpus window is invalid")
    raw_matches = payload.get("matches")
    raw_profiles = payload.get("profiles")
    if not isinstance(raw_matches, list) or not isinstance(raw_profiles, list):
        raise CalibrationCorpusError("profiles and matches must be arrays")
    retained = [dict(row) for row in raw_matches if isinstance(row, Mapping) and isinstance(row.get("start_time"), int) and start <= row["start_time"] <= end]
    removed_match_count = len(raw_matches) - len(retained)
    by_session: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in retained:
        by_session[(str(row.get("profile_id")), str(row.get("session_id")))].append(row)
    for rows in by_session.values():
        for index, row in enumerate(sorted(rows, key=lambda item: (int(item["start_time"]), int(item["match_id"]))), start=1):
            row["session_index"] = index
    by_profile: Counter[str] = Counter(str(row.get("profile_id")) for row in retained)
    kept_profiles: list[dict[str, Any]] = []
    dropped_profiles = 0
    for raw in raw_profiles:
        if not isinstance(raw, Mapping):
            raise CalibrationCorpusError("profile summaries must be objects")
        profile = dict(raw)
        profile_id = str(profile.get("profile_id"))
        if by_profile[profile_id] < 30:
            dropped_profiles += 1
            continue
        profile["eligible_match_count"] = by_profile[profile_id]
        profile["session_count"] = sum(owner == profile_id for owner, _sid in by_session)
        profile["completed_session_count"] = min(
            int(profile.get("completed_session_count", 0)),
            profile["session_count"],
        )
        kept_profiles.append(profile)
    kept_ids = {str(profile["profile_id"]) for profile in kept_profiles}
    retained = [row for row in retained if str(row.get("profile_id")) in kept_ids]
    migrated = dict(payload)
    migrated["profiles"] = sorted(kept_profiles, key=lambda item: str(item["profile_id"]))
    migrated["matches"] = sorted(retained, key=lambda item: (str(item["profile_id"]), int(item["start_time"]), int(item["match_id"])))
    summary = dict(payload.get("summary") or {})
    summary["eligible_profile_count"] = len(kept_profiles)
    summary["eligible_match_count"] = len(retained)
    migrated["summary"] = summary
    encoded = (json.dumps(migrated, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    migrated_checksum = hashlib.sha256(encoded).hexdigest()
    validated = validate_calibration_corpus(migrated, checksum=migrated_checksum)
    destination_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination_path.parent.chmod(0o700)
    temporary = destination_path.with_name(f".{destination_path.name}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    temporary.replace(destination_path)
    return {
        **validated.aggregate_diagnostics(),
        "removed_out_of_window_matches": removed_match_count,
        "dropped_profiles": dropped_profiles,
        "destination": str(destination_path),
    }


__all__ = [
    "CalibrationCorpus",
    "CalibrationCorpusError",
    "load_calibration_corpus",
    "migrate_calibration_corpus",
    "validate_calibration_corpus",
]

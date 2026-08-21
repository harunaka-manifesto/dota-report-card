"""Normalize the nullable contract exposed by OpenDota's player history.

This module is deliberately independent from the detail-match normalizer.  Free
DNA is allowed to reason only about the fields returned by
``/players/{account_id}/matches`` and keeps a small eligibility ledger so a
missing field never silently becomes a behavioural zero.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Literal

EligibilityKey = Literal[
    "overall",
    "breadth",
    "role",
    "adaptability",
    "activity",
    "orientation",
    "resilience",
    "endurance",
    "rhythm",
]

ROLE_HINTS = {
    # OpenDota lane_role is a lane/context enum, not a position-1..5 enum.
    # The summary endpoint can identify safe/mid/off lane and roaming, but it
    # cannot reliably split hard vs soft support without detail evidence.
    1: "carry",
    2: "mid",
    3: "offlane",
    4: "jungle",
    5: "roamer",
}
SUPPORTED_LOBBY_TYPES = frozenset({0, 7})  # public unranked / ranked matchmaking

SUPPORTED_ALL_PICK_MODES = frozenset({1, 22})
_MATERIAL_ABANDON_STATUSES = frozenset({2, 3, 4, 5})


@dataclass(frozen=True, slots=True)
class EligibilityFlag:
    included: bool
    reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"included": self.included, "reasons": list(self.reasons)}


@dataclass(frozen=True, slots=True)
class NormalizedSummaryMatch:
    match_id: int
    source_index: int
    account_id: int
    hero_id: int | None
    hero_variant: int | None
    started_at: int | None
    duration_seconds: int | None
    ended_at: int | None
    side: Literal["radiant", "dire"] | None
    won: bool | None
    game_mode: int | None
    lobby_type: int | None
    leaver_status: int | None
    kills: int | None
    deaths: int | None
    assists: int | None
    party_size: int | None
    lane_role: int | None
    lane: int | None
    is_roaming: bool | None
    role_hint: str | None
    role_confidence: float | None
    patch: str | None
    source_version: str | None
    skill_bracket: int | None
    region: int | None
    session_id: str | None = None
    session_index: int | None = None
    session_corrupt: bool = False
    eligibility: dict[str, EligibilityFlag] | None = None

    @property
    def start_time(self) -> int | None:
        """Compatibility alias used by the repository's older summary code."""

        return self.started_at

    @property
    def duration_minutes(self) -> float | None:
        return self.duration_seconds / 60 if self.duration_seconds is not None else None

    @property
    def role(self) -> str | None:
        return self.role_hint

    @property
    def is_common_eligible(self) -> bool:
        return bool(self.eligibility and self.eligibility["overall"].included)

    def with_session(self, session_id: str | None, session_index: int | None, *, corrupt: bool = False) -> NormalizedSummaryMatch:
        return replace(
            self,
            session_id=session_id,
            session_index=session_index,
            session_corrupt=corrupt,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "source_index": self.source_index,
            "account_id": self.account_id,
            "hero_id": self.hero_id,
            "hero_variant": self.hero_variant,
            "started_at": self.started_at,
            "start_time": self.started_at,
            "duration_seconds": self.duration_seconds,
            "ended_at": self.ended_at,
            "side": self.side,
            "won": self.won,
            "game_mode": self.game_mode,
            "lobby_type": self.lobby_type,
            "leaver_status": self.leaver_status,
            "kills": self.kills,
            "deaths": self.deaths,
            "assists": self.assists,
            "party_size": self.party_size,
            "lane_role": self.lane_role,
            "lane": self.lane,
            "is_roaming": self.is_roaming,
            "role_hint": self.role_hint,
            "role_confidence": self.role_confidence,
            "patch": self.patch,
            "source_version": self.source_version,
            "skill_bracket": self.skill_bracket,
            "region": self.region,
            "session_id": self.session_id,
            "session_index": self.session_index,
            "session_corrupt": self.session_corrupt,
            "eligibility": {
                key: value.as_dict() for key, value in (self.eligibility or {}).items()
            },
        }


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    matches: tuple[NormalizedSummaryMatch, ...]
    exclusion_ledger: tuple[dict[str, Any], ...]
    duplicate_conflicts: tuple[dict[str, Any], ...]
    source_count: int

    @property
    def eligible_matches(self) -> tuple[NormalizedSummaryMatch, ...]:
        return tuple(item for item in self.matches if item.is_common_eligible)

    def as_dict(self) -> dict[str, Any]:
        return {
            "matches": [item.as_dict() for item in self.matches],
            "exclusion_ledger": list(self.exclusion_ledger),
            "duplicate_conflicts": list(self.duplicate_conflicts),
            "source_count": self.source_count,
            "unique_count": len(self.matches),
            "eligible_count": len(self.eligible_matches),
        }


def previous_year_window(*, window_end: int | None = None, days: int = 365) -> tuple[int, int]:
    """Return the inclusive Unix-second bounds for the Free history window."""

    end = int(window_end if window_end is not None else datetime.now(UTC).timestamp())
    start = end - max(1, int(days)) * 24 * 60 * 60
    return start, end


def filter_history_window(
    matches: tuple[NormalizedSummaryMatch, ...] | list[NormalizedSummaryMatch],
    *,
    window_start: int,
    window_end: int,
) -> tuple[NormalizedSummaryMatch, ...]:
    """Keep only matches whose validated start time belongs to the window.

    Rows with no usable timestamp stay in the normalization ledger but cannot
    be claimed as part of a time-bounded population.  This is intentionally a
    fail-closed boundary for chronology-dependent analysis.
    """

    return tuple(
        item
        for item in matches
        if item.started_at is not None and window_start <= item.started_at <= window_end
    )


def normalize_summary_rows(
    rows: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    account_id: int,
) -> NormalizationResult:
    """Return a deterministic, deduplicated summary corpus.

    Rows are retained in source order metadata, while analytics consumers can
    sort by ``started_at``.  A conflicting duplicate is resolved in favour of
    the row with more useful non-null fields and is recorded explicitly.
    """

    source_rows = [row for row in rows if isinstance(row, dict)]
    chosen: dict[int, tuple[int, dict[str, Any]]] = {}
    conflicts: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []

    for source_index, row in enumerate(source_rows):
        match_id = _as_int(row.get("match_id"))
        if match_id is None or match_id <= 0:
            exclusions.append(
                {"source_index": source_index, "match_id": match_id, "reasons": ["invalid_match_id"]}
            )
            continue
        previous = chosen.get(match_id)
        if previous is None:
            chosen[match_id] = (source_index, row)
            continue
        previous_index, previous_row = previous
        if _row_fingerprint(previous_row) == _row_fingerprint(row):
            continue
        previous_score = _nonnull_score(previous_row)
        current_score = _nonnull_score(row)
        current_fingerprint = _row_fingerprint(row)
        previous_fingerprint = _row_fingerprint(previous_row)
        if current_score > previous_score or (
            current_score == previous_score and current_fingerprint < previous_fingerprint
        ):
            chosen[match_id] = (source_index, row)
            kept_index = source_index
        else:
            kept_index = previous_index
        conflicts.append(
            {
                "match_id": match_id,
                "source_indices": [previous_index, source_index],
                "kept_source_index": kept_index,
                "reason": "duplicate_conflict",
            }
        )

    normalized: list[NormalizedSummaryMatch] = []
    for match_id, (source_index, row) in sorted(chosen.items(), key=lambda item: item[1][0]):
        item = _normalize_row(row, source_index=source_index, account_id=account_id, match_id=match_id)
        normalized.append(item)
        common_reasons = list(item.eligibility["overall"].reasons) if item.eligibility else []
        if common_reasons:
            exclusions.append(
                {
                    "source_index": source_index,
                    "match_id": match_id,
                    "reasons": common_reasons,
                }
            )

    normalized.sort(
        key=lambda item: (item.started_at is None, item.started_at or 0, item.match_id)
    )
    return NormalizationResult(
        matches=tuple(normalized),
        exclusion_ledger=tuple(exclusions),
        duplicate_conflicts=tuple(conflicts),
        source_count=len(source_rows),
    )


def _normalize_row(
    row: dict[str, Any],
    *,
    source_index: int,
    account_id: int,
    match_id: int,
) -> NormalizedSummaryMatch:
    raw_started_at = row.get("start_time")
    if raw_started_at is None:
        raw_started_at = row.get("started_at")
    started_at = _as_int(raw_started_at)
    raw_duration = row.get("duration")
    if raw_duration is None:
        raw_duration = row.get("duration_seconds")
    duration = _as_int(raw_duration)
    duration = duration if duration is not None and duration >= 0 else None
    player_slot = _as_int(row.get("player_slot"))
    side_value = row.get("side")
    if side_value in {"radiant", "dire"}:
        side: Literal["radiant", "dire"] | None = side_value
    elif player_slot is not None:
        side = "radiant" if player_slot < 128 else "dire"
    else:
        side = None

    radiant_win = _as_bool(row.get("radiant_win"))
    won = _as_bool(row.get("won"))
    if won is None and radiant_win is not None and side is not None:
        won = radiant_win == (side == "radiant")
    lane_role = _as_int(row.get("lane_role"))
    lane = _as_int(row.get("lane"))
    is_roaming = _as_bool(row.get("is_roaming"))
    role_hint, role_confidence = _role_hint(lane_role, lane, is_roaming)
    hero_id = _as_int(row.get("hero_id"))
    game_mode = _as_int(row.get("game_mode"))
    lobby_type = _as_int(row.get("lobby_type"))
    leaver_status = _as_int(row.get("leaver_status"))
    pro_or_league = bool(row.get("leagueid") or row.get("league_id"))
    invalid_numeric_reasons = _invalid_numeric_reasons(row)
    row_account_id = _as_int(row.get("account_id"))
    if row_account_id is not None and row_account_id != account_id:
        invalid_numeric_reasons += ("account_id_mismatch",)
    if started_at is None:
        invalid_numeric_reasons += ("missing_start_time",)
    elif started_at <= 0:
        invalid_numeric_reasons += ("invalid_start_time",)
        started_at = None
    ended_at = started_at + duration if started_at is not None and duration is not None else None
    eligibility = _eligibility(
        match_id=match_id,
        hero_id=hero_id,
        started_at=started_at,
        duration=duration,
        side=side,
        won=won,
        game_mode=game_mode,
        lobby_type=lobby_type,
        leaver_status=leaver_status,
        role_hint=role_hint,
        role_confidence=role_confidence,
        kills=_as_nonnegative_int(row.get("kills")),
        assists=_as_nonnegative_int(row.get("assists")),
        pro_or_league=pro_or_league,
        invalid_numeric_reasons=invalid_numeric_reasons,
    )
    return NormalizedSummaryMatch(
        match_id=match_id,
        source_index=source_index,
        account_id=account_id,
        hero_id=hero_id,
        hero_variant=_as_int(row.get("hero_variant")),
        started_at=started_at,
        duration_seconds=duration,
        ended_at=ended_at,
        side=side,
        won=won,
        game_mode=game_mode,
        lobby_type=lobby_type,
        leaver_status=leaver_status,
        kills=_as_nonnegative_int(row.get("kills")),
        deaths=_as_nonnegative_int(row.get("deaths")),
        assists=_as_nonnegative_int(row.get("assists")),
        party_size=_as_nonnegative_int(row.get("party_size")),
        lane_role=lane_role,
        lane=lane,
        is_roaming=is_roaming,
        role_hint=role_hint,
        role_confidence=role_confidence,
        patch=_as_str(row.get("patch")),
        skill_bracket=_as_int(row.get("skill_bracket") or row.get("skill")),
        region=_as_int(row.get("region")),
        eligibility=eligibility,
        source_version=_as_str(row.get("version")),
    )


def _eligibility(
    *,
    match_id: int,
    hero_id: int | None,
    started_at: int | None,
    duration: int | None,
    side: str | None,
    won: bool | None,
    game_mode: int | None,
    lobby_type: int | None,
    leaver_status: int | None,
    role_hint: str | None,
    role_confidence: float | None,
    kills: int | None,
    assists: int | None,
    pro_or_league: bool,
    invalid_numeric_reasons: tuple[str, ...] = (),
) -> dict[str, EligibilityFlag]:
    common_reasons: list[str] = list(invalid_numeric_reasons)
    if match_id <= 0:
        common_reasons.append("invalid_match_id")
    if hero_id is None or hero_id <= 0:
        common_reasons.append("missing_hero")
    if side is None:
        common_reasons.append("missing_side")
    if won is None:
        common_reasons.append("missing_outcome")
    if game_mode not in SUPPORTED_ALL_PICK_MODES:
        common_reasons.append("unsupported_game_mode")
    if duration is None or duration < 300:
        common_reasons.append("invalid_duration")
    if leaver_status in _MATERIAL_ABANDON_STATUSES:
        common_reasons.append("abandoned")
    if lobby_type not in SUPPORTED_LOBBY_TYPES:
        common_reasons.append("unsupported_lobby_type")
    if pro_or_league:
        common_reasons.append("pro_or_league")
    common_reasons = list(dict.fromkeys(common_reasons))

    common = not common_reasons
    flags: dict[str, EligibilityFlag] = {
        "overall": EligibilityFlag(common, tuple(common_reasons)),
        "breadth": EligibilityFlag(common and hero_id is not None, tuple(common_reasons)),
        "role": EligibilityFlag(
            common and role_hint is not None and (role_confidence or 0.0) >= 0.60,
            tuple(common_reasons)
            + (("low_role_confidence",) if role_hint and (role_confidence or 0.0) < 0.60 else ())
            + (() if role_hint else ("missing_role_hint",)),
        ),
        "adaptability": EligibilityFlag(common and hero_id is not None and won is not None, tuple(common_reasons)),
        "activity": EligibilityFlag(
            common and kills is not None and assists is not None and duration is not None and duration >= 600,
            tuple(common_reasons) + (() if kills is not None and assists is not None else ("missing_kda",)),
        ),
        "orientation": EligibilityFlag(
            common and kills is not None and assists is not None and (kills + assists) > 0,
            tuple(common_reasons) + (() if kills is not None and assists is not None else ("missing_kda",)),
        ),
        "resilience": EligibilityFlag(common and started_at is not None and won is not None, tuple(common_reasons)),
        "endurance": EligibilityFlag(common and started_at is not None and won is not None, tuple(common_reasons)),
        "rhythm": EligibilityFlag(common and started_at is not None, tuple(common_reasons)),
    }
    return flags


def _role_hint(
    lane_role: int | None,
    lane: int | None,
    is_roaming: bool | None,
) -> tuple[str | None, float | None]:
    if is_roaming is True:
        return "roamer", 0.72
    if lane_role in ROLE_HINTS:
        return ROLE_HINTS[lane_role], 0.86
    # ``lane`` is a spatial lane enum, not a player-position enum. Without a
    # trustworthy lane_role/roaming signal, retain the row but do not invent a
    # role from lane placement alone.
    return None, None


def _row_fingerprint(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(key), repr(value)) for key, value in row.items()))


def _nonnull_score(row: dict[str, Any]) -> int:
    required = (
        "match_id", "start_time", "duration", "hero_id", "player_slot",
        "radiant_win", "won", "game_mode", "lobby_type", "kills", "deaths", "assists",
    )
    useful = sum(row.get(key) is not None for key in required)
    return useful * 10 + sum(value is not None for value in row.values())


def _invalid_numeric_reasons(row: dict[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    for field in ("kills", "deaths", "assists", "duration", "duration_seconds"):
        if field not in row or row.get(field) is None:
            continue
        parsed = _as_int(row.get(field))
        if parsed is None or parsed < 0:
            reasons.append(f"invalid_{field}")
    return tuple(dict.fromkeys(reasons))


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_nonnegative_int(value: Any) -> int | None:
    parsed = _as_int(value)
    return parsed if parsed is not None and parsed >= 0 else None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    return None


def _as_str(value: Any) -> str | None:
    return str(value) if value is not None else None

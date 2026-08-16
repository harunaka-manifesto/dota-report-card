from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.features.summary_models import PlayerSession, SummaryFeatureSet, SummaryMatchFeature


def calculate_summary_feature(
    summary: dict[str, Any], *, account_id: int | None = None, source_index: int = 0
) -> SummaryMatchFeature | None:
    """Convert one player-history row without requiring a detail request."""

    match_id = _as_int(summary.get("match_id"))
    duration = _as_int(summary.get("duration"))
    hero_id = _as_int(summary.get("hero_id"))
    start_time = _as_int(summary.get("start_time"))
    player_slot = _as_int(summary.get("player_slot"))
    radiant_win = _as_bool(summary.get("radiant_win"))
    if match_id is None or duration is None or hero_id is None:
        return None
    if player_slot is None or radiant_win is None:
        return None

    side = "radiant" if player_slot < 128 else "dire"
    return SummaryMatchFeature(
        match_id=match_id,
        start_time=start_time,
        duration_seconds=duration,
        hero_id=hero_id,
        side=side,
        won=radiant_win == (side == "radiant"),
        kills=_as_optional_int(summary.get("kills")),
        deaths=_as_optional_int(summary.get("deaths")),
        assists=_as_optional_int(summary.get("assists")),
        game_mode=_as_optional_int(summary.get("game_mode")),
        lobby_type=_as_optional_int(summary.get("lobby_type")),
        average_rank=_as_optional_int(summary.get("average_rank")),
        party_size=_as_optional_int(summary.get("party_size")),
        parser_version_hint=_as_optional_int(summary.get("version")),
        gold_per_min=_as_optional_float(summary.get("gold_per_min")),
        xp_per_min=_as_optional_float(summary.get("xp_per_min")),
        lane_role=_as_optional_int(summary.get("lane_role")),
        source_index=source_index,
        account_id=account_id,
        hero_variant=_as_optional_int(summary.get("hero_variant")),
        lane=_as_optional_int(summary.get("lane")),
        is_roaming=_as_bool(summary.get("is_roaming")),
        role_hint=_role_hint(summary),
        role_confidence=_role_confidence(summary),
        patch=_as_optional_str(summary.get("patch") or summary.get("version")),
        skill_bracket=_as_optional_int(summary.get("skill_bracket") or summary.get("skill")),
        region=_as_optional_int(summary.get("region")),
        leaver_status=_as_optional_int(summary.get("leaver_status")),
        ended_at=start_time + duration if start_time is not None else None,
    )


def calculate_summary_features(
    summaries: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    account_id: int | None = None,
    session_gap_minutes: int = 90,
) -> SummaryFeatureSet:
    """Build deterministic summary features and session positions.

    Input order is intentionally ignored.  Unknown timestamps are retained as
    independent matches but do not get assigned a made-up session relationship.
    """

    features = [
        feature
        for index, summary in enumerate(summaries)
        if isinstance(summary, dict)
        and (feature := calculate_summary_feature(
            summary, account_id=account_id, source_index=index
        )) is not None
    ]
    features.sort(key=_chronological_key)
    # The legacy summary feature set has always promised order invariance.  A
    # source-order provenance index belongs to the richer DNA normalizer; keep
    # this compatibility view stable across equivalent input permutations.
    features = [replace(feature, source_index=index) for index, feature in enumerate(features)]
    sessions: list[PlayerSession] = []
    current: list[SummaryMatchFeature] = []
    gap_seconds = max(1, session_gap_minutes) * 60

    for feature in features:
        if current and _starts_new_session(current[-1], feature, gap_seconds):
            sessions.append(_make_session(len(sessions) + 1, current))
            current = []
        current.append(feature)
    if current:
        sessions.append(_make_session(len(sessions) + 1, current))

    by_id: dict[int, tuple[str, int]] = {}
    for session in sessions:
        for index, match_id in enumerate(session.match_ids, start=1):
            by_id[match_id] = (session.session_id, index)
    assigned = [
        replace(feature, session_id=by_id[feature.match_id][0], session_index=by_id[feature.match_id][1])
        for feature in features
    ]
    return SummaryFeatureSet(
        matches=tuple(assigned),
        sessions=tuple(sessions),
    )


def _starts_new_session(
    previous: SummaryMatchFeature, current: SummaryMatchFeature, gap_seconds: int
) -> bool:
    if previous.start_time is None or current.start_time is None:
        return True
    previous_end = previous.start_time + max(0, previous.duration_seconds)
    return current.start_time - previous_end > gap_seconds


def _make_session(index: int, matches: list[SummaryMatchFeature]) -> PlayerSession:
    return PlayerSession(
        session_id=f"session-{index}",
        match_ids=tuple(match.match_id for match in matches),
        start_time=matches[0].start_time,
        end_time=(
            matches[-1].start_time + matches[-1].duration_seconds
            if matches[-1].start_time is not None
            else None
        ),
    )


def _chronological_key(feature: SummaryMatchFeature) -> tuple[bool, int, int]:
    return (feature.start_time is None, feature.start_time or 0, feature.match_id)


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_optional_int(value: Any) -> int | None:
    return _as_int(value)


def _as_optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None


def _role_hint(summary: dict[str, Any]) -> str | None:
    if summary.get("is_roaming") is True:
        return "roamer"
    lane_role = _as_int(summary.get("lane_role"))
    if lane_role is None:
        lane = _as_int(summary.get("lane"))
        return {1: "carry", 2: "mid", 3: "offlane"}.get(lane) if lane is not None else None
    return {
        1: "carry",
        2: "mid",
        3: "offlane",
        4: "soft_support",
        5: "hard_support",
    }.get(lane_role)


def _role_confidence(summary: dict[str, Any]) -> float | None:
    if _role_hint(summary) is not None:
        if _as_int(summary.get("lane_role")) is not None:
            return 0.86
        return 0.62 if _as_int(summary.get("lane")) is not None else 0.72
    return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    return None

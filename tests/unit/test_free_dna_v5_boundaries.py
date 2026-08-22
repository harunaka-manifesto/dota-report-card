from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from app.analysis.source import MappingSource
from app.api.report_schemas import SessionCurveActionSchema
from app.behavior.actions import build_session_curve_action
from app.core.config import FREE_HISTORY_WINDOW_DAYS, Settings
from app.dna.breakpoints import detect_breakpoint
from app.dna.performance import build_performance_map, performance_proxy
from app.dna.recency import effective_sample_size, recency_weight, session_weight
from app.dna.sessions import SessionPolicy, infer_sessions
from app.heroes.taxonomy import HeroTaxonomy
from app.ingestion.summary_normalize import (
    filter_history_window,
    normalize_summary_rows,
)
from app.storage.repository import InMemoryRepository


def _row(
    match_id: int,
    start_time: int | None,
    *,
    duration: int = 1_800,
    hero_id: int = 1,
    won: bool = True,
    lane_role: int = 3,
    kills: int = 6,
    deaths: int = 3,
    assists: int = 9,
) -> dict[str, object]:
    return {
        "match_id": match_id,
        "start_time": start_time,
        "duration": duration,
        "hero_id": hero_id,
        "player_slot": 0,
        "radiant_win": won,
        "game_mode": 1,
        "lobby_type": 0,
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        "lane_role": lane_role,
        "leaver_status": 0,
    }


def test_history_window_is_previous_year_and_inclusive_at_both_edges() -> None:
    window_end = 2_000_000_000
    window_start = window_end - FREE_HISTORY_WINDOW_DAYS * 24 * 60 * 60
    normalized = normalize_summary_rows(
        [
            _row(1, window_start - 1),
            _row(2, window_start),
            _row(3, window_end),
            _row(4, window_end + 1),
        ],
        account_id=42,
    )

    eligible = filter_history_window(
        normalized.eligible_matches,
        window_start=window_start,
        window_end=window_end,
    )

    assert [item.match_id for item in eligible] == [2, 3]


def test_normalization_deduplicates_by_match_id_and_keeps_invalid_fields_explicit() -> None:
    duplicate = _row(1, 1_700_000_000)
    richer_duplicate = {**duplicate, "party_size": 2, "patch": "7.38"}
    result = normalize_summary_rows(
        [
            duplicate,
            richer_duplicate,
            _row(2, None),
            _row(3, 0),
            _row(4, 1_700_000_100, duration=-1),
        ],
        account_id=42,
    )

    assert result.source_count == 5
    assert len(result.matches) == 4
    assert len(result.duplicate_conflicts) == 1
    by_id = {item.match_id: item for item in result.matches}
    assert by_id[1].party_size == 2
    assert "missing_start_time" in by_id[2].eligibility["overall"].reasons  # type: ignore[index]
    assert "invalid_start_time" in by_id[3].eligibility["overall"].reasons  # type: ignore[index]
    assert "invalid_duration" in by_id[4].eligibility["overall"].reasons  # type: ignore[index]


def test_default_history_source_is_not_silently_capped_at_500() -> None:
    rows = [_row(index, 1_700_000_000 + index * 1_800) for index in range(1_001)]
    source = MappingSource(
        player={"profile": {"account_id": 42}},
        matches=rows,
        details={},
    )

    assert Settings().effective_free_history_limit is None
    returned = asyncio.run(source.get_matches(42, limit=None, days=365))
    assert len(returned) == 1_001


def test_summary_history_repository_cache_has_an_explicit_ttl() -> None:
    repository = InMemoryRepository()
    payload = [{"match_id": 1}]
    repository.persist_raw_payload(
        "/players/42/matches",
        "42",
        payload,
        {"window_days": 365},
    )

    assert repository.get_cached_raw_payload(
        "/players/42/matches", "42", max_age_seconds=120
    ) == payload
    repository.raw_payloads[-1]["fetched_at"] = (
        datetime.now(UTC) - timedelta(seconds=121)
    ).isoformat()
    assert repository.get_cached_raw_payload(
        "/players/42/matches", "42", max_age_seconds=120
    ) is None


def test_sessionization_uses_match_end_and_does_not_split_midnight() -> None:
    day = 86_400
    first_start = day - 600
    rows = normalize_summary_rows(
        [
            _row(1, first_start, duration=600),
            _row(2, day + 1_200, duration=1_800),
            _row(3, day + 1_200 + 1_800 + 90 * 60, duration=1_800),
            _row(4, day + 1_200 + 1_800 + 90 * 60 + 1_800 + 90 * 60 + 1),
        ],
        account_id=42,
    ).matches

    result = infer_sessions(rows, SessionPolicy(gap_minutes=90))

    assert [session.match_ids for session in result.sessions] == [(1, 2, 3), (4,)]
    assert result.matches[0].session_index == 1
    assert result.matches[-1].session_index == 1


def test_implausible_overlap_splits_and_marks_only_affected_rows() -> None:
    rows = normalize_summary_rows(
        [
            _row(1, 1_700_000_000, duration=1_800),
            _row(2, 1_700_000_000 + 1_800 - 301, duration=1_800),
            _row(3, 1_700_100_000, duration=1_800),
        ],
        account_id=42,
    ).matches

    result = infer_sessions(rows)

    assert [session.match_ids for session in result.sessions] == [(1,), (2,), (3,)]
    assert result.matches[0].session_corrupt is True
    assert result.matches[1].session_corrupt is True
    assert result.matches[2].session_corrupt is False


def test_session_boundary_censoring_requires_observed_inactivity() -> None:
    start = 1_700_000_000
    rows = normalize_summary_rows(
        [
            _row(1, start, duration=1_800),
            _row(2, start + 2_400, duration=1_800),
        ],
        account_id=42,
    ).matches
    last_end = start + 2_400 + 1_800

    censored = infer_sessions(
        rows,
        window_start=start,
        window_end=last_end + 1_000,
    )
    confirmed = infer_sessions(
        rows,
        window_start=start,
        window_end=last_end + 90 * 60 + 1,
    )

    assert censored.sessions[0].left_censored is True
    assert censored.sessions[0].right_censored is True
    assert not censored.completed_sessions
    assert confirmed.sessions[0].right_censored is False
    assert len(confirmed.completed_sessions) == 1


def test_recency_and_session_weights_expose_effective_sample_size() -> None:
    now = 2_000_000_000
    old = now - 180 * 24 * 60 * 60
    weights = [recency_weight(old, window_end=now), recency_weight(now, window_end=now)]

    assert weights[1] > weights[0]
    assert 1.0 <= effective_sample_size(weights) <= 2.0
    assert session_weight(old, window_end=now) == weights[0]


def test_performance_proxy_handles_zero_kda_and_rejects_short_matches() -> None:
    zero = normalize_summary_rows(
        [_row(1, 1_700_000_000, kills=0, deaths=0, assists=0)],
        account_id=42,
    ).matches[0]
    short = normalize_summary_rows(
        [_row(2, 1_700_001_000, duration=300)],
        account_id=42,
    ).matches[0]

    assert performance_proxy(zero) is not None
    assert performance_proxy(short) is None
    values, observations = build_performance_map((zero,))
    assert values[1] == observations[1].value


def test_breakpoint_requires_persistent_direction_and_labels_gradual_curves() -> None:
    stable = detect_breakpoint(
        {"G1": -0.01, "G2": -0.03, "G3": -0.11, "G4": -0.12, "G5+": -0.14},
        direction="fade",
        counts={bucket: 8 for bucket in ("G1", "G2", "G3", "G4", "G5+")},
    )
    isolated = detect_breakpoint(
        {"G1": -0.01, "G2": -0.12, "G3": -0.01, "G4": -0.01},
        direction="fade",
        counts={bucket: 8 for bucket in ("G1", "G2", "G3", "G4")},
    )

    assert stable.state == "stable_breakpoint"
    assert stable.bucket == "G3"
    assert isolated.state == "gradual"


def test_session_curve_action_is_session_balanced_and_typed_even_when_unresolved() -> None:
    rows = []
    for session_number in range(4):
        base = 1_700_000_000 + session_number * 100_000
        rows.extend(
            [
                _row(session_number * 10 + 1, base, won=True),
                _row(session_number * 10 + 2, base + 2_400, won=False),
                _row(session_number * 10 + 3, base + 4_800, won=True),
            ]
        )
    normalized = normalize_summary_rows(rows, account_id=42).matches
    sessions = infer_sessions(normalized, window_end=1_700_500_000)
    taxonomy = HeroTaxonomy("fixture", {}, {})

    action = build_session_curve_action(sessions.matches, taxonomy, direction="fade")

    assert len(action.curve) == 5
    assert action.independent_session_count == 4
    assert action.status in {"fallback", "unresolved"}
    SessionCurveActionSchema.model_validate(action.as_dict())


def test_session_curve_action_excludes_right_censored_latest_session() -> None:
    rows = []
    for session_number in range(4):
        base = 1_700_000_000 + session_number * 100_000
        rows.extend(
            [
                _row(session_number * 10 + 1, base, won=True),
                _row(session_number * 10 + 2, base + 2_400, won=False),
                _row(session_number * 10 + 3, base + 4_800, won=True),
            ]
        )
    normalized = normalize_summary_rows(rows, account_id=42).matches
    latest_end = 1_700_000_000 + 3 * 100_000 + 4_800 + 1_800
    sessions = infer_sessions(normalized, window_end=latest_end + 1_000)
    taxonomy = HeroTaxonomy("fixture", {}, {})

    assert sessions.sessions[-1].right_censored is True
    action = build_session_curve_action(
        sessions.matches,
        taxonomy,
        direction="fade",
        sessions=sessions,
    )

    assert action.independent_session_count == 3
    assert action.evidence_summary is not None
    assert action.evidence_summary.independent_group_count == 3

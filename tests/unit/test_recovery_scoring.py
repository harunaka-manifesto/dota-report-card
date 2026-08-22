from __future__ import annotations

import pytest
from app.behavior.context_baseline import BaselineResolution
from app.behavior.elements.service import (
    SummaryBehaviorContext,
    _score_post_loss_performance_response,
)
from app.dna.features.models import DnaFeatureSet
from app.dna.sessions import infer_sessions
from app.heroes.taxonomy import HeroTaxonomy
from app.ingestion.summary_normalize import normalize_summary_rows


def _context(transitions_by_session: tuple[int, ...], residual_by_session: tuple[float, ...]) -> SummaryBehaviorContext:
    rows: list[dict[str, object]] = []
    performance: dict[int, float] = {}
    match_id = 1
    for session_index, transition_count in enumerate(transitions_by_session):
        session_start = 1_700_000_000 + session_index * 300_000
        residual = residual_by_session[session_index]
        for transition_index in range(transition_count):
            previous_id = match_id
            current_id = match_id + 1
            start = session_start + transition_index * 4_000
            rows.extend(
                [
                    {
                        "match_id": previous_id,
                        "start_time": start,
                        "duration": 1_800,
                        "hero_id": 1,
                        "player_slot": 0,
                        "radiant_win": False,
                        "game_mode": 1,
                        "lobby_type": 0,
                        "kills": 4,
                        "deaths": 4,
                        "assists": 8,
                        "lane_role": 3,
                    },
                    {
                        "match_id": current_id,
                        "start_time": start + 1_800,
                        "duration": 1_800,
                        "hero_id": 1,
                        "player_slot": 0,
                        "radiant_win": True,
                        "game_mode": 1,
                        "lobby_type": 0,
                        "kills": 8,
                        "deaths": 3,
                        "assists": 10,
                        "lane_role": 3,
                    },
                ]
            )
            performance[previous_id] = 0.5
            performance[current_id] = 0.5 + residual
            match_id += 2
    normalized = normalize_summary_rows(rows, account_id=42).matches
    sessions = infer_sessions(normalized, window_end=2_000_000_000)
    features = DnaFeatureSet(
        matches=sessions.matches,
        sessions=sessions.sessions,
        sample_size=len(sessions.matches),
        performance_by_match=performance,
        weights_by_match={item.match_id: 1.0 for item in sessions.matches},
        session_weights={session.session_id: 1.0 for session in sessions.sessions},
        source_match_ids=tuple(item.match_id for item in sessions.matches),
    )
    return SummaryBehaviorContext(
        matches=sessions.matches,
        sessions=sessions,
        features=features,
        taxonomy=HeroTaxonomy("empty", {}, {}),
    )


def test_recovery_authority_is_session_clustered(monkeypatch) -> None:
    context = _context((24, 3, 3), (0.90, 0.10, 0.10))

    def fixed_baseline(**_kwargs) -> BaselineResolution:
        return BaselineResolution(
            value=0.5,
            level="overall",
            reference_sample_size=3,
            effective_sample_size=3.0,
            reference_match_ids=(100, 101, 102),
        )

    monkeypatch.setattr("app.behavior.elements.service.resolve_leave_group_out_baseline", fixed_baseline)
    result = _score_post_loss_performance_response(context)

    assert result.status != "unavailable"
    assert result.sample_size == 30
    assert result.raw_metrics["independent_sessions"] == 3
    assert result.raw_metrics["max_transitions_in_one_session"] == 24
    assert result.raw_metrics["session_clustered_delta"] == pytest.approx(0.10)
    assert result.raw_metrics["session_clustered_delta"] != pytest.approx(0.90)


def test_recovery_availability_keeps_transition_session_and_context_gates(monkeypatch) -> None:
    def fixed_baseline(**_kwargs) -> BaselineResolution:
        return BaselineResolution(
            value=0.5,
            level="overall",
            reference_sample_size=3,
            effective_sample_size=3.0,
            reference_match_ids=(100, 101, 102),
        )

    monkeypatch.setattr("app.behavior.elements.service.resolve_leave_group_out_baseline", fixed_baseline)

    too_few_transitions = _score_post_loss_performance_response(_context((10, 10, 9), (0.1, 0.1, 0.1)))
    assert too_few_transitions.score is None
    assert "insufficient_comparable_post_loss_transitions" in too_few_transitions.missing_reasons

    too_few_sessions = _score_post_loss_performance_response(_context((15, 15), (0.1, 0.1)))
    assert too_few_sessions.score is None
    assert "insufficient_independent_post_loss_sessions" in too_few_sessions.missing_reasons

    context = _context((10, 10, 10), (0.1, 0.1, 0.1))
    current_ids = {
        item.match_id
        for item in context.matches
        if item.won is True
    }
    unmatched = set(sorted(current_ids)[:16])

    def partial_baseline(**kwargs):
        if kwargs["target"].match_id in unmatched:
            return None
        return fixed_baseline()

    monkeypatch.setattr("app.behavior.elements.service.resolve_leave_group_out_baseline", partial_baseline)
    too_little_context = _score_post_loss_performance_response(context)
    assert too_little_context.score is None
    assert "insufficient_role_function_context_overlap" in too_little_context.missing_reasons
    assert too_little_context.raw_metrics["matched_context_coverage"] < 0.50

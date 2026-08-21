"""Feature extraction shared by the 18 independent Element scorers."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import replace
from statistics import median
from typing import Any

from app.dna.features.models import DnaFeatureSet
from app.dna.performance import PERFORMANCE_PROXY_VERSION, build_performance_map
from app.dna.recency import (
    DEFAULT_HALF_LIFE_DAYS,
    RECENCY_WEIGHTING_VERSION,
    effective_sample_size,
    recency_weight,
    session_weight,
)
from app.dna.sessions import SessionResult
from app.ingestion.summary_normalize import NormalizedSummaryMatch


def extract_dna_features(
    matches: tuple[NormalizedSummaryMatch, ...] | list[NormalizedSummaryMatch],
    sessions: SessionResult,
    *,
    include_sensitivity: bool = True,
    window_start: int | None = None,
    window_end: int | None = None,
    recency_half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> DnaFeatureSet:
    corpus = tuple(
        sorted(
            (item for item in matches if item.is_common_eligible),
            key=lambda item: (item.started_at is None, item.started_at or 0, item.match_id),
        )
    )
    hero_counts = Counter(item.hero_id for item in corpus if item.hero_id is not None)
    role_rows = tuple(
        item
        for item in corpus
        if item.eligibility
        and item.eligibility["role"].included
        and item.role_hint is not None
    )
    role_counts = Counter(item.role_hint for item in role_rows if item.role_hint is not None)
    activity_rows = tuple(
        item
        for item in corpus
        if item.eligibility and item.eligibility["activity"].included
    )
    orientation_rows = tuple(
        item
        for item in corpus
        if item.eligibility and item.eligibility["orientation"].included
    )

    activity_rate_by_match = {
        item.match_id: ((item.kills or 0) + (item.assists or 0)) / max((item.duration_seconds or 1) / 60, 1 / 60)
        for item in activity_rows
    }
    orientation_by_match = {
        item.match_id: (item.kills or 0) / max((item.kills or 0) + (item.assists or 0), 1)
        for item in orientation_rows
    }
    resolved_window_end = window_end or max(
        (item.started_at or 0 for item in corpus),
        default=0,
    )
    resolved_window_start = (
        window_start
        if window_start is not None
        else resolved_window_end - 365 * 24 * 60 * 60
        if resolved_window_end
        else None
    )
    weights_by_match = {
        item.match_id: (
            recency_weight(
                item.started_at,
                window_end=resolved_window_end,
                half_life_days=recency_half_life_days,
            )
            if item.started_at is not None and resolved_window_end
            else 0.0
        )
        for item in corpus
    }
    performance_by_match, _performance_observations = build_performance_map(corpus)
    role_performance: dict[str, list[float]] = defaultdict(list)
    for item in role_rows:
        if item.match_id in performance_by_match:
            role_performance[item.role_hint or "unknown"].append(performance_by_match[item.match_id])

    familiar_heroes = _familiar_heroes(hero_counts, len(corpus))
    familiar_values = tuple(
        performance_by_match[item.match_id]
        for item in corpus
        if item.hero_id in familiar_heroes and item.match_id in performance_by_match
    )
    off_pool_values = tuple(
        performance_by_match[item.match_id]
        for item in corpus
        if item.hero_id not in familiar_heroes and item.match_id in performance_by_match
    )
    transition_values = _transition_values(sessions, performance_by_match)
    endurance_values = _endurance_values(sessions, performance_by_match)
    # A right-censored latest session is not evidence of a completed-session
    # length.  Keep the empty result when every observed session is censored;
    # E15 must fail closed rather than quietly reintroducing the old fallback.
    completed_sessions = sessions.completed_sessions
    session_lengths = tuple(session.match_count for session in completed_sessions)
    session_durations = tuple(session.elapsed_seconds for session in completed_sessions)
    session_weights = {
        session.session_id: session_weight(
            session.start_time,
            window_end=resolved_window_end,
            half_life_days=recency_half_life_days,
        )
        for session in sessions.sessions
        if resolved_window_end
    }
    dated_ids = tuple(item.match_id for item in corpus if item.started_at is not None)
    familiar_ids = tuple(
        item.match_id for item in corpus
        if item.hero_id in familiar_heroes and item.match_id in performance_by_match
    )
    off_pool_ids = tuple(
        item.match_id for item in corpus
        if item.hero_id not in familiar_heroes and item.match_id in performance_by_match
    )
    familiar_roles = frozenset(
        role for role, count in role_counts.items() if count >= 3
    )

    base = DnaFeatureSet(
        matches=corpus,
        sessions=sessions.sessions,
        sample_size=len(corpus),
        hero_counts=dict(sorted(hero_counts.items())),
        hero_entropy=_entropy(hero_counts.values()),
        normalized_hero_entropy=_normalized_entropy(hero_counts.values()),
        effective_hero_count=math.exp(_entropy(hero_counts.values())) if hero_counts else 0.0,
        top_hero_shares=_top_shares(hero_counts, len(corpus)),
        role_counts=dict(sorted(role_counts.items())),
        role_coverage=len(role_rows) / len(corpus) if corpus else 0.0,
        role_entropy=_entropy(role_counts.values()),
        normalized_role_entropy=_normalized_entropy(role_counts.values()),
        dominant_role=role_counts.most_common(1)[0][0] if role_counts else None,
        familiar_heroes=frozenset(familiar_heroes),
        activity_by_match=activity_rate_by_match,
        orientation_by_match=orientation_by_match,
        performance_by_match=performance_by_match,
        role_performance={key: tuple(values) for key, values in role_performance.items()},
        familiar_performance=familiar_values,
        off_pool_performance=off_pool_values,
        transitions_after_win=transition_values[0],
        transitions_after_loss=transition_values[1],
        transitions_after_two_losses=transition_values[2],
        endurance_by_position=endurance_values,
        session_lengths=session_lengths,
        session_durations=session_durations,
        source_match_ids=tuple(item.match_id for item in corpus),
        dated_match_ids=dated_ids,
        role_match_ids=tuple(item.match_id for item in role_rows),
        activity_match_ids=tuple(item.match_id for item in activity_rows),
        orientation_match_ids=tuple(item.match_id for item in orientation_rows),
        familiar_match_ids=familiar_ids,
        off_pool_match_ids=off_pool_ids,
        familiar_roles=familiar_roles,
        session_sensitivity=sessions.sensitivity,
        weights_by_match=weights_by_match,
        session_weights=session_weights,
        effective_sample_size=effective_sample_size(tuple(weights_by_match.values())),
        recency_half_life_days=recency_half_life_days,
        recency_weighting_version=RECENCY_WEIGHTING_VERSION,
        performance_proxy_version=PERFORMANCE_PROXY_VERSION,
        window_start=resolved_window_start,
        window_end=resolved_window_end or None,
        left_censored_session_count=sessions.left_censored_session_count,
        right_censored_session_count=sessions.right_censored_session_count,
    )
    if not include_sensitivity:
        return base

    # Session sensitivity reruns the session-dependent feature/scoring path at
    # each policy gap. It compares score direction, not exact partition IDs.
    from app.dna.dimensions.service import score_dimensions
    from app.dna.sessions import SessionPolicy, infer_sessions

    sensitivity_scores: dict[int, dict[str, float | None]] = {}
    for gap in (60, 90, 120):
        alternate_sessions = infer_sessions(
            corpus,
            SessionPolicy(gap_minutes=gap),
            sensitivity_gaps=(),
            window_start=resolved_window_start,
            window_end=resolved_window_end or None,
        )
        alternate_features = extract_dna_features(
            alternate_sessions.matches,
            alternate_sessions,
            include_sensitivity=False,
            window_start=resolved_window_start,
            window_end=resolved_window_end or None,
            recency_half_life_days=recency_half_life_days,
        )
        sensitivity_scores[gap] = {
            item.key: item.centered_score
            for item in score_dimensions(alternate_features)
        }
    return replace(base, session_sensitivity_scores=sensitivity_scores)


def _familiar_heroes(counts: Counter[int], sample_size: int) -> set[int]:
    if not counts:
        return set()
    stable = {hero_id: count for hero_id, count in counts.items() if count >= 5}
    if not stable:
        return set()
    counts = Counter(stable)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    selected: list[int] = []
    total = 0
    target = max(1, math.ceil(sample_size * 0.50))
    for hero_id, count in ordered:
        selected.append(hero_id)
        total += count
        if (total >= target and len(selected) >= 3) or len(selected) >= 10:
            break
    return set(selected)


def _performance_by_match(
    corpus: tuple[NormalizedSummaryMatch, ...], activity_rates: dict[int, float]
) -> dict[int, float]:
    del activity_rates
    return build_performance_map(corpus)[0]


def _transition_values(
    sessions: SessionResult, performance: dict[int, float]
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    after_win: list[float] = []
    after_loss: list[float] = []
    after_two_losses: list[float] = []
    by_id = {item.match_id: item for item in sessions.matches}
    for session in sessions.sessions:
        previous_losses = 0
        for previous_id, current_id in zip(session.match_ids, session.match_ids[1:], strict=False):
            previous = by_id[previous_id]
            current = by_id[current_id]
            # Missing/short/corrupt rows cannot establish a valid transition.
            # Reset the streak so a later valid game is never attributed to an
            # unseen result.
            if (
                previous.session_corrupt
                or current.session_corrupt
                or previous_id not in performance
                or current_id not in performance
            ):
                previous_losses = 0
                continue
            if previous.won:
                after_win.append(performance[current_id])
                previous_losses = 0
            else:
                after_loss.append(performance[current_id])
                previous_losses += 1
                if previous_losses >= 2:
                    after_two_losses.append(performance[current_id])
    return tuple(after_win), tuple(after_loss), tuple(after_two_losses)


def _endurance_values(
    sessions: SessionResult, performance: dict[int, float]
) -> dict[int, tuple[float, ...]]:
    values: dict[int, list[float]] = defaultdict(list)
    for session in sessions.sessions:
        if len(session.match_ids) < 2:
            continue
        for position, match_id in enumerate(session.match_ids, start=1):
            row = next((item for item in sessions.matches if item.match_id == match_id), None)
            if match_id in performance and row is not None and not row.session_corrupt:
                values[min(position, 4)].append(performance[match_id])
    return {key: tuple(value) for key, value in sorted(values.items())}


def _top_shares(counts: Counter[int], sample_size: int) -> dict[int, float]:
    if not sample_size:
        return {3: 0.0, 5: 0.0, 10: 0.0}
    ordered = [count for _, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]
    return {
        3: sum(ordered[:3]) / sample_size,
        5: sum(ordered[:5]) / sample_size,
        10: sum(ordered[:10]) / sample_size,
    }


def _entropy(values: Any) -> float:
    numbers = [float(value) for value in values if value]
    total = sum(numbers)
    if not total or len(numbers) <= 1:
        return 0.0
    return -sum((value / total) * math.log(value / total) for value in numbers)


def _normalized_entropy(values: Any) -> float:
    numbers = [value for value in values if value]
    if len(numbers) <= 1:
        return 0.0
    return _entropy(numbers) / math.log(len(numbers))


def _mad(values: list[float]) -> float:
    if not values:
        return 0.0
    centre = median(values)
    return median([abs(value - centre) for value in values])


def _sigmoid(value: float) -> float:
    value = max(-12.0, min(12.0, value))
    return 1 / (1 + math.exp(-value))

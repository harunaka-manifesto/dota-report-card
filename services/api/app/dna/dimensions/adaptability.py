from __future__ import annotations

import math
from statistics import median

from app.dna.dimensions.common import clamp, result
from app.dna.features.models import DnaFeatureSet, FeatureEvidence
from app.ingestion.summary_normalize import NormalizedSummaryMatch

ADAPTABILITY_VERSION = "adaptability-1.1.0"
_PRIOR_STRENGTH = 8.0


def score(features: DnaFeatureSet):
    rows = sorted(
        (
            item for item in features.matches
            if item.hero_id is not None and item.won is not None
        ),
        # Timestamped rows use chronological order. Undated rows remain
        # eligible for this hero/outcome comparison and fall back to the
        # stable match ID order so input ordering cannot change the split.
        key=lambda item: (item.started_at is None, item.started_at or 0, item.match_id),
    )
    if len(rows) < 40:
        return result(
            "adaptability", score=None, sample_size=len(rows),
            effective_sample_size=len(rows), coverage=len(rows) / max(features.sample_size, 1),
            minimum_sample=40, missing_reasons=("insufficient_evaluation_history",),
        )

    split = max(1, int(len(rows) * 0.70))
    familiar = _familiar_heroes(rows[:split])
    evaluation = rows[split:]
    familiar_eval = [item for item in evaluation if item.hero_id in familiar]
    off_pool_eval = [item for item in evaluation if item.hero_id not in familiar]
    methodology = (
        "time_split_70_30"
        if all(item.started_at is not None for item in rows)
        else "stable_match_id_split_missing_timestamps"
    )
    if len(familiar_eval) < 20 or len(off_pool_eval) < 20:
        # A leave-one-window-out fallback still keeps familiarity outcome-free.
        methodology = "leave_one_window_out_fallback"
        familiar, familiar_eval, off_pool_eval = _fallback_windows(rows)
    if len(familiar_eval) < 20 or len(off_pool_eval) < 20:
        return result(
            "adaptability", score=None,
            sample_size=len(familiar_eval) + len(off_pool_eval),
            effective_sample_size=min(len(familiar_eval), len(off_pool_eval)),
            coverage=(len(familiar_eval) + len(off_pool_eval)) / max(features.sample_size, 1),
            minimum_sample=40,
            missing_reasons=("familiar_or_off_pool_evaluation_too_small",),
        )

    outcome_delta, role_confounder, role_cells = _role_stratified_outcome_delta(
        familiar_eval, off_pool_eval
    )
    activity_delta, activity_available = _activity_delta(familiar_eval, off_pool_eval)
    combined: float
    confounders: list[str] = ["patch, draft quality, and hero learning can differ between windows"]
    quality = 1.0
    if role_confounder:
        confounders.append("role_mix_confounder")
        quality = 0.72
    if activity_available:
        combined = 0.60 * _scaled(outcome_delta, 0.25) + 0.40 * _scaled(activity_delta, 1.0)
    else:
        combined = _scaled(outcome_delta, 0.25)
        confounders.append("outcome_only_fallback")
        quality *= 0.65
    value = clamp(0.5 + combined / 2.0)
    neutral = abs(combined) < 0.08
    evidence = [
        FeatureEvidence("familiar_evaluation_matches", len(familiar_eval), "matches", len(familiar_eval)),
        FeatureEvidence("off_pool_evaluation_matches", len(off_pool_eval), "matches", len(off_pool_eval)),
        FeatureEvidence("familiar_win_rate_delta", round(outcome_delta, 6), "rate_delta", len(familiar_eval) + len(off_pool_eval)),
        FeatureEvidence("evaluation_method", methodology, "method", len(familiar_eval) + len(off_pool_eval)),
    ]
    if activity_available:
        evidence.append(FeatureEvidence("standardized_ka_per_min_delta", round(activity_delta, 6), "z_delta", len(familiar_eval) + len(off_pool_eval)))
    evidence.extend(
        FeatureEvidence(f"role_cell_{role}", round(delta, 6), "rate_delta", count)
        for role, (delta, count) in sorted(role_cells.items())
    )
    return result(
        "adaptability",
        score=value,
        sample_size=len(familiar_eval) + len(off_pool_eval),
        effective_sample_size=min(len(familiar_eval), len(off_pool_eval)) * 2,
        coverage=(len(familiar_eval) + len(off_pool_eval)) / max(features.sample_size, 1),
        minimum_sample=40,
        stability=0.85 if methodology == "time_split_70_30" else 0.60,
        quality=quality,
        evidence=tuple(evidence),
        confounders=tuple(confounders),
        source_match_ids=tuple(item.match_id for item in familiar_eval + off_pool_eval),
        neutral=neutral,
    )


def _familiar_heroes(rows: list[NormalizedSummaryMatch]) -> set[int]:
    counts: dict[int, int] = {}
    for item in rows:
        hero_id = item.hero_id
        if hero_id is not None:
            counts[hero_id] = counts.get(hero_id, 0) + 1
    ordered = [(hero_id, count) for hero_id, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])) if count >= 5]
    if not ordered:
        return set()
    target = max(1, math.ceil(len(rows) * 0.50))
    chosen: list[int] = []
    total = 0
    for hero_id, count in ordered[:10]:
        chosen.append(hero_id)
        total += count
        if total >= target and len(chosen) >= min(3, len(ordered)):
            break
    return set(chosen)


def _fallback_windows(
    rows: list[NormalizedSummaryMatch],
) -> tuple[set[int], list[NormalizedSummaryMatch], list[NormalizedSummaryMatch]]:
    windows: list[tuple[set[int], list[NormalizedSummaryMatch], list[NormalizedSummaryMatch]]] = []
    for start, end in ((0, 0.30), (0.35, 0.65), (0.70, 1.0)):
        left = rows[: max(1, int(len(rows) * end))]
        right = rows[max(1, int(len(rows) * start)):]
        familiar = _familiar_heroes(left)
        familiar_eval = [item for item in right if item.hero_id in familiar]
        off_pool = [item for item in right if item.hero_id not in familiar]
        windows.append((familiar, familiar_eval, off_pool))
    familiar, familiar_eval, off_pool = max(
        windows, key=lambda item: min(len(item[1]), len(item[2]))
    )
    return familiar, familiar_eval, off_pool


def _smoothed_rate(rows: list[NormalizedSummaryMatch]) -> float:
    wins = sum(1 for item in rows if getattr(item, "won", False))
    return (wins + _PRIOR_STRENGTH * 0.5) / (len(rows) + _PRIOR_STRENGTH)


def _role_stratified_outcome_delta(
    familiar: list[NormalizedSummaryMatch], off_pool: list[NormalizedSummaryMatch]
) -> tuple[float, bool, dict[str, tuple[float, int]]]:
    roles = sorted({item.role_hint for item in familiar + off_pool if item.role_hint is not None})
    cells: dict[str, tuple[float, int]] = {}
    weighted: list[tuple[float, int]] = []
    for role in roles:
        left = [item for item in familiar if item.role_hint == role]
        right = [item for item in off_pool if item.role_hint == role]
        if len(left) < 8 or len(right) < 8:
            continue
        delta = _smoothed_rate(right) - _smoothed_rate(left)
        count = len(left) + len(right)
        cells[role] = (delta, count)
        weighted.append((delta, count))
    if not weighted:
        return _smoothed_rate(off_pool) - _smoothed_rate(familiar), True, cells
    total = sum(count for _, count in weighted)
    return sum(delta * count for delta, count in weighted) / total, len(weighted) < len(roles), cells


def _activity_delta(
    familiar: list[NormalizedSummaryMatch], off_pool: list[NormalizedSummaryMatch]
) -> tuple[float, bool]:
    values: list[float] = []
    groups: dict[str, list[float]] = {"familiar": [], "off_pool": []}
    for label, rows in (("familiar", familiar), ("off_pool", off_pool)):
        for item in rows:
            duration = item.duration_seconds
            kills = item.kills
            assists = item.assists
            if duration and duration > 0 and kills is not None and assists is not None:
                value = (kills + assists) / (duration / 60)
                groups[label].append(value)
                values.append(value)
    if len(groups["familiar"]) < 12 or len(groups["off_pool"]) < 12:
        return 0.0, False
    centre = median(values)
    mad = median([abs(value - centre) for value in values]) or 1.0
    return ((median(groups["off_pool"]) - median(groups["familiar"])) / mad), True


def _scaled(value: float, scale: float) -> float:
    return math.tanh(value / max(scale, 1e-6))

from __future__ import annotations

from app.dna.dimensions.common import clamp, result
from app.dna.features.models import DnaFeatureSet, FeatureEvidence


def score(features: DnaFeatureSet):
    sample = features.sample_size
    effective = features.effective_hero_count
    if sample == 0 or not features.hero_counts:
        return result(
            "breadth", score=None, sample_size=sample, effective_sample_size=0,
            coverage=0.0, minimum_sample=30, missing_reasons=("missing_hero_history",),
        )
    top5 = features.top_hero_shares.get(5, 0.0)
    concentration = (
        0.45 * top5
        + 0.35 * (1.0 - features.normalized_hero_entropy)
        + 0.20 * min(1.0, 10.0 / max(effective, 1.0))
    )
    value = clamp(1.0 - concentration)
    return result(
        "breadth",
        score=value,
        sample_size=sample,
        effective_sample_size=effective,
        coverage=len([item for item in features.matches if item.hero_id is not None]) / sample,
        minimum_sample=30,
        stability=_window_stability(features),
        evidence=(
            FeatureEvidence("unique_heroes", len(features.hero_counts), "heroes", sample, features.source_match_ids),
            FeatureEvidence("top_5_share", round(top5, 4), "share", sample, features.source_match_ids),
        ),
        confounders=("hero availability and patch changes can shape the pool",),
        source_match_ids=features.source_match_ids,
    )


def _window_stability(features: DnaFeatureSet) -> float:
    dated = [item for item in features.matches if item.started_at is not None]
    if len(dated) < 20:
        return 0.65
    windows = [dated[-min(50, len(dated)):], dated[-min(100, len(dated)):], dated]
    scores = []
    for window in windows:
        counts: dict[int, int] = {}
        for item in window:
            if item.hero_id is not None:
                counts[item.hero_id] = counts.get(item.hero_id, 0) + 1
        if not counts:
            continue
        total = len(window)
        top5 = sum(sorted(counts.values(), reverse=True)[:5]) / total
        scores.append(1.0 - top5)
    if len(scores) < 2:
        return 0.65
    spread = max(scores) - min(scores)
    return clamp(1.0 - spread * 2.0, 0.55, 1.0)

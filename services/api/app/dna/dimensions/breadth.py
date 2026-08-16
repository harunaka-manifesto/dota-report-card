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
    half = max(1, len(dated) // 2)
    first = len({item.hero_id for item in dated[:half] if item.hero_id is not None})
    second = len({item.hero_id for item in dated[half:] if item.hero_id is not None})
    return 1.0 if abs(first - second) <= max(2, half // 4) else 0.65

from __future__ import annotations

from app.dna.dimensions.common import clamp, result
from app.dna.features.models import DnaFeatureSet, FeatureEvidence


def score(features: DnaFeatureSet):
    sample = len(features.role_match_ids)
    coverage = features.role_coverage
    if not features.role_counts:
        return result(
            "role", score=None, sample_size=sample, effective_sample_size=0,
            coverage=coverage, minimum_sample=30, minimum_coverage=0.40,
            missing_reasons=("missing_credible_role_hints",),
        )
    dominant = max(features.role_counts.values()) / sample if sample else 0.0
    anchoring = 0.65 * dominant + 0.35 * (1.0 - features.normalized_role_entropy)
    value = clamp(1.0 - anchoring)
    return result(
        "role",
        score=value,
        sample_size=sample,
        effective_sample_size=sample * coverage,
        coverage=coverage,
        minimum_sample=30,
        minimum_coverage=0.40,
        stability=1.0 if coverage >= 0.65 else 0.70,
        quality=coverage,
        evidence=(
            FeatureEvidence("dominant_role", features.dominant_role or "unknown", "role", sample, features.role_match_ids),
            FeatureEvidence("dominant_role_share", round(dominant, 4), "share", sample, features.role_match_ids),
        ),
        confounders=("summary lane labels are hints and may miss role swaps",),
        source_match_ids=features.role_match_ids,
    )

from __future__ import annotations

from statistics import median

from app.dna.dimensions.common import clamp, result
from app.dna.features.models import DnaFeatureSet, FeatureEvidence


def score(features: DnaFeatureSet):
    familiar = features.familiar_performance
    off_pool = features.off_pool_performance
    sample = len(familiar) + len(off_pool)
    if len(familiar) < 20 or len(off_pool) < 20:
        return result(
            "adaptability", score=None, sample_size=sample,
            effective_sample_size=min(len(familiar), len(off_pool)), coverage=sample / max(features.sample_size, 1),
            minimum_sample=40, missing_reasons=("familiar_or_off_pool_sample_too_small",),
        )
    familiar_mean = sum(familiar) / len(familiar)
    off_pool_mean = sum(off_pool) / len(off_pool)
    delta = off_pool_mean - familiar_mean
    # A 0.15 performance delta is a meaningful practical range for this
    # summary-only proxy.  Flat or positive off-pool output is transferable.
    value = clamp(0.5 + delta / 0.30)
    return result(
        "adaptability",
        score=value,
        sample_size=sample,
        effective_sample_size=min(len(familiar), len(off_pool)) * 2,
        coverage=sample / max(features.sample_size, 1),
        minimum_sample=40,
        stability=1.0 if abs(median(familiar) - median(off_pool)) < 0.35 else 0.70,
        evidence=(
            FeatureEvidence(
                "familiar_performance", round(familiar_mean, 4), "proxy", len(familiar), features.familiar_match_ids
            ),
            FeatureEvidence(
                "off_pool_performance", round(off_pool_mean, 4), "proxy", len(off_pool), features.off_pool_match_ids
            ),
            FeatureEvidence(
                "off_pool_delta", round(delta, 4), "proxy_delta", sample,
                features.familiar_match_ids + features.off_pool_match_ids,
            ),
        ),
        confounders=("hero learning, draft quality, patch, and role mix can differ between groups",),
        source_match_ids=features.source_match_ids,
    )

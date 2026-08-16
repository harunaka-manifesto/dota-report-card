from __future__ import annotations

from statistics import median

from app.dna.baselines import DEFAULT_BASELINE
from app.dna.dimensions.common import clamp, result
from app.dna.features.models import DnaFeatureSet, FeatureEvidence

ROLE_EXPECTED_KILL_SHARE = DEFAULT_BASELINE.kill_share_by_role


def score(features: DnaFeatureSet):
    values = tuple(features.orientation_by_match.values())
    total_involvement = sum(
        (item.kills or 0) + (item.assists or 0)
        for item in features.matches
        if item.match_id in features.orientation_by_match
    )
    sample = len(values)
    if sample < 30 or total_involvement < 100:
        return result(
            "orientation", score=None, sample_size=sample,
            effective_sample_size=float(total_involvement), coverage=sample / max(features.sample_size, 1),
            minimum_sample=30, missing_reasons=("insufficient_involvement_sample",),
        )
    adjusted_values = []
    for item in features.matches:
        value = features.orientation_by_match.get(item.match_id)
        if value is None:
            continue
        expected = DEFAULT_BASELINE.kill_share(item.role_hint)
        adjusted_values.append(value - expected if features.role_coverage >= 0.40 else value - median(values))
    residual = median(adjusted_values) if adjusted_values else 0.0
    value = clamp(0.5 + residual / 0.40)
    return result(
        "orientation",
        score=value,
        sample_size=sample,
        effective_sample_size=min(float(total_involvement), 300.0),
        coverage=sample / max(features.sample_size, 1),
        minimum_sample=30,
        quality=1.0 if features.role_coverage >= 0.40 else 0.55,
        evidence=(
            FeatureEvidence("median_kill_share", round(median(values), 4), "share", sample, features.orientation_match_ids),
            FeatureEvidence("total_involvements", total_involvement, "events", sample, features.orientation_match_ids),
            FeatureEvidence("baseline_version", DEFAULT_BASELINE.version, "version", sample),
        ),
        confounders=("team kill totals are unavailable in summary history",),
        source_match_ids=features.orientation_match_ids,
    )

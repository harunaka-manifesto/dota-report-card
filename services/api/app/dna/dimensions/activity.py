from __future__ import annotations

import math
from statistics import median

from app.dna.baselines import DEFAULT_BASELINE
from app.dna.dimensions.common import cap_confidence, clamp, result
from app.dna.features.models import DnaFeatureSet, FeatureEvidence

ACTIVITY_VERSION = "activity-1.1.0"


def score(features: DnaFeatureSet):
    values = tuple(features.activity_by_match.values())
    sample = len(values)
    coverage = sample / max(features.sample_size, 1)
    if sample < 30:
        return result(
            "activity", score=None, sample_size=sample, effective_sample_size=sample,
            coverage=coverage, minimum_sample=30,
            missing_reasons=("missing_kills_assists_or_duration",),
        )
    role_rows = [
        item for item in features.matches
        if item.match_id in features.activity_by_match
        and item.role_hint is not None
        and (item.role_confidence or 0.0) >= 0.60
    ]
    role_adjusted = len(role_rows) >= 20
    if role_adjusted:
        residuals = [
            features.activity_by_match[item.match_id] - DEFAULT_BASELINE.activity(item.role_hint)
            for item in role_rows
        ]
    else:
        centre = median(values)
        residuals = [value - centre for value in values]
    central = median(residuals) if residuals else 0.0
    # The neutral band is intentionally expressed in the observable unit,
    # then mapped through a bounded normalizer so extreme games cannot dominate.
    value = clamp(0.5 + 0.5 * math.tanh(central / 0.30))
    scored = result(
        "activity",
        score=value,
        sample_size=sample,
        effective_sample_size=sample,
        coverage=coverage,
        minimum_sample=30,
        stability=0.85 if sample >= 50 else 0.65,
        quality=0.75 if role_adjusted else 0.55,
        evidence=(
            FeatureEvidence("median_involvement_rate", round(median(values), 4), "events_per_minute", sample, features.activity_match_ids),
            FeatureEvidence("role_adjusted", role_adjusted, "boolean", len(role_rows)),
            FeatureEvidence("role_adjusted_sample", len(role_rows), "matches", len(role_rows)),
            FeatureEvidence("neutral_residual_band", 0.15, "events_per_minute", sample),
            FeatureEvidence("baseline_version", DEFAULT_BASELINE.version, "version", sample),
        ),
        confounders=("team tempo and hero style affect observable involvement rate",)
        + (() if role_adjusted else ("role support is below 20 matches; role-relative wording is suppressed",)),
        source_match_ids=features.activity_match_ids,
        descriptor_eligible=role_adjusted,
        neutral=abs(central) <= 0.15,
    )
    # Baseline cells are explicitly provisional until a calibrated cohort is
    # available, so this dimension cannot publish high-confidence role claims.
    return cap_confidence(scored, 0.70)

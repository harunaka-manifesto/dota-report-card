from __future__ import annotations

from statistics import median

from app.dna.baselines import DEFAULT_BASELINE
from app.dna.dimensions.common import clamp, result
from app.dna.features.models import DnaFeatureSet, FeatureEvidence

ROLE_EXPECTED_ACTIVITY = DEFAULT_BASELINE.activity_by_role


def score(features: DnaFeatureSet):
    values = tuple(features.activity_by_match.values())
    sample = len(values)
    if sample < 30:
        return result(
            "activity", score=None, sample_size=sample, effective_sample_size=sample,
            coverage=sample / max(features.sample_size, 1), minimum_sample=30,
            missing_reasons=("missing_kills_assists_or_duration",),
        )
    residuals = []
    adjusted = features.role_coverage >= 0.40
    for item in features.matches:
        value = features.activity_by_match.get(item.match_id)
        if value is None:
            continue
        expected = DEFAULT_BASELINE.activity(item.role_hint)
        residuals.append(value - expected if adjusted else value - median(values))
    central = median(residuals) if residuals else 0.0
    value = clamp(0.5 + central / 0.90)
    return result(
        "activity",
        score=value,
        sample_size=sample,
        effective_sample_size=sample,
        coverage=sample / max(features.sample_size, 1),
        minimum_sample=30,
        stability=0.85 if len(residuals) >= 40 else 0.65,
        quality=1.0 if adjusted else 0.55,
        evidence=(
            FeatureEvidence("median_involvement_rate", round(median(values), 4), "events_per_minute", sample, features.activity_match_ids),
            FeatureEvidence("role_adjusted", adjusted, "boolean", sample, features.activity_match_ids),
            FeatureEvidence("baseline_version", DEFAULT_BASELINE.version, "version", sample),
        ),
        confounders=("team tempo and hero style affect observable involvement rate",)
        + (() if adjusted else ("role coverage is limited; this is not a role-relative claim",)),
        source_match_ids=features.activity_match_ids,
    )

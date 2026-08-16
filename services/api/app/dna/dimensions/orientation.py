from __future__ import annotations

from statistics import median

from app.dna.baselines import DEFAULT_BASELINE
from app.dna.dimensions.common import cap_confidence, clamp, result
from app.dna.features.models import DnaFeatureSet, FeatureEvidence

ORIENTATION_VERSION = "orientation-1.1.0"


def score(features: DnaFeatureSet):
    rows = [item for item in features.matches if item.match_id in features.orientation_by_match]
    sample = len(rows)
    total_kills = sum(item.kills or 0 for item in rows)
    total_assists = sum(item.assists or 0 for item in rows)
    total_involvement = total_kills + total_assists
    coverage = sample / max(features.sample_size, 1)
    if sample < 30 or total_involvement < 100:
        return result(
            "orientation", score=None, sample_size=sample,
            effective_sample_size=float(total_involvement), coverage=coverage,
            minimum_sample=30, missing_reasons=("insufficient_involvement_sample",),
            descriptor_eligible=False,
        )
    aggregate_share = total_kills / total_involvement if total_involvement else 0.5
    role_rows = [
        item for item in rows
        if item.role_hint is not None and (item.role_confidence or 0.0) >= 0.60
    ]
    role_adjusted = len(role_rows) >= 20
    if role_adjusted:
        role_involvement: dict[str, int] = {}
        for item in role_rows:
            role_involvement[item.role_hint or "unknown"] = role_involvement.get(item.role_hint or "unknown", 0) + (item.kills or 0) + (item.assists or 0)
        denominator = sum(role_involvement.values()) or 1
        expected = sum(
            DEFAULT_BASELINE.kill_share(role) * involvement
            for role, involvement in role_involvement.items()
        ) / denominator
    else:
        expected = 0.5
    residual = aggregate_share - expected
    shrink = total_involvement / (total_involvement + 100.0)
    shrunk_residual = residual * shrink
    value = clamp(0.5 + shrunk_residual / 0.40)
    scored = result(
        "orientation",
        score=value,
        sample_size=sample,
        effective_sample_size=min(float(total_involvement), 300.0),
        coverage=coverage,
        minimum_sample=30,
        quality=0.75 if role_adjusted else 0.55,
        evidence=(
            FeatureEvidence("aggregate_kill_share", round(aggregate_share, 6), "share", total_involvement, features.orientation_match_ids),
            FeatureEvidence("median_match_kill_share", round(median(features.orientation_by_match.values()), 6), "share", sample, features.orientation_match_ids),
            FeatureEvidence("role_expected_kill_share", round(expected, 6), "share", len(role_rows)),
            FeatureEvidence("involvement_shrinkage", round(shrink, 6), "multiplier", total_involvement),
            FeatureEvidence("total_involvements", total_involvement, "events", sample, features.orientation_match_ids),
            FeatureEvidence("baseline_version", DEFAULT_BASELINE.version, "version", sample),
        ),
        confounders=("team kill totals are unavailable in summary history",)
        + (() if role_adjusted else ("role adjustment requires 20 credible role-classified matches",)),
        source_match_ids=features.orientation_match_ids,
        descriptor_eligible=role_adjusted,
        neutral=abs(shrunk_residual) <= 0.04,
    )
    return cap_confidence(scored, 0.70)

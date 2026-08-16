from __future__ import annotations

from statistics import median

from app.dna.dimensions.common import clamp, result, session_sensitivity_stability
from app.dna.features.models import DnaFeatureSet, FeatureEvidence


def score(features: DnaFeatureSet):
    lengths = features.session_lengths
    sample = len(features.dated_match_ids)
    if len(lengths) < 10 or sample < 25:
        return result(
            "rhythm", score=None, sample_size=sample, effective_sample_size=len(lengths),
            coverage=len(features.dated_match_ids) / max(features.sample_size, 1), minimum_sample=25,
            missing_reasons=("insufficient_dated_sessions",),
        )
    median_length = float(median(lengths))
    share_long = sum(length >= 5 for length in lengths) / len(lengths)
    duration_hours = median(features.session_durations) / 3600 if features.session_durations else 0.0
    # Three matches over roughly three hours is deliberately neutral. Two
    # matches over two hours reads as a short burst; five over five hours as a
    # grinder. The signal uses only session shape, never outcomes.
    value = clamp(
        0.5
        + 0.35 * (median_length - 3.0) / 2.0
        + 0.20 * (duration_hours - 3.0) / 2.0
        + 0.15 * (share_long - 0.5)
    )
    sensitivity = session_sensitivity_stability(features, "rhythm")
    return result(
        "rhythm",
        score=value,
        sample_size=sample,
        effective_sample_size=len(lengths),
        coverage=len(features.dated_match_ids) / max(features.sample_size, 1),
        minimum_sample=25,
        stability=min(0.85 if len(lengths) >= 20 else 0.65, sensitivity),
        evidence=(
            FeatureEvidence("median_matches_per_session", round(median_length, 2), "matches", len(lengths), features.dated_match_ids),
            FeatureEvidence("share_five_plus_sessions", round(share_long, 4), "share", len(lengths), features.dated_match_ids),
            FeatureEvidence("median_session_duration", round(duration_hours, 2), "hours", len(lengths), features.dated_match_ids),
            FeatureEvidence("session_gap_agreement", sensitivity, "agreement", 3),
            FeatureEvidence("boundary_session_caveat", "oldest_or_newest_window_boundary", "method", sample),
        ),
        confounders=("the history limit can truncate the oldest session",),
        source_match_ids=features.dated_match_ids,
    )

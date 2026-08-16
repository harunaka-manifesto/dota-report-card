from __future__ import annotations

from app.dna.dimensions.common import clamp, result, session_sensitivity_stability
from app.dna.features.models import DnaFeatureSet, FeatureEvidence


def score(features: DnaFeatureSet):
    positions = features.endurance_by_position
    independent_sessions = sum(1 for session in features.sessions if session.match_count >= 2 and not session.corrupt)
    first = positions.get(1, ())
    late = positions.get(3, ()) + positions.get(4, ())
    sample = len(first) + len(late)
    if independent_sessions < 12 or len(first) < 15 or len(late) < 12:
        return result(
            "endurance", score=None, sample_size=sample,
            effective_sample_size=min(len(first), len(late)), coverage=sample / max(features.sample_size, 1),
            minimum_sample=27, missing_reasons=("insufficient_multi_game_sessions_or_late_games",),
        )
    first_mean = sum(first) / len(first)
    late_mean = sum(late) / len(late)
    delta = late_mean - first_mean
    value = clamp(0.5 + delta / 0.40)
    sensitivity = session_sensitivity_stability(features)
    return result(
        "endurance",
        score=value,
        sample_size=sample,
        effective_sample_size=min(len(first), len(late)) * 2,
        coverage=sample / max(features.sample_size, 1),
        minimum_sample=27,
        stability=min(0.85 if independent_sessions >= 20 else 0.65, sensitivity),
        evidence=(
            FeatureEvidence("early_session_performance", round(first_mean, 4), "proxy", len(first)),
            FeatureEvidence("late_session_performance", round(late_mean, 4), "proxy", len(late)),
            FeatureEvidence("late_minus_early", round(delta, 4), "proxy_delta", sample),
            FeatureEvidence("session_gap_agreement", sensitivity, "agreement", 3),
        ),
        confounders=("players may stop after difficult or successful games; role mix can change",),
        source_match_ids=features.dated_match_ids,
    )

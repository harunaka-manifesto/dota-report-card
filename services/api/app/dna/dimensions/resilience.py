from __future__ import annotations

from app.dna.dimensions.common import clamp, mean, result, session_sensitivity_stability
from app.dna.features.models import DnaFeatureSet, FeatureEvidence


def score(features: DnaFeatureSet):
    after_win = features.transitions_after_win
    after_loss = features.transitions_after_loss
    sample = len(after_win) + len(after_loss)
    paired_sessions = sum(
        session.match_count >= 2 and not session.corrupt
        for session in features.sessions
    )
    if len(after_win) < 15 or len(after_loss) < 15 or paired_sessions < 10:
        return result(
            "resilience", score=None, sample_size=sample,
            effective_sample_size=min(len(after_win), len(after_loss)) * 2,
            coverage=sample / max(features.sample_size, 1), minimum_sample=30,
            missing_reasons=(
                "insufficient_within_session_transitions"
                if paired_sessions >= 10
                else "insufficient_independent_sessions",
            ),
        )
    delta = (mean(after_loss) or 0.0) - (mean(after_win) or 0.0)
    value = clamp(0.5 + delta / 0.50)
    sensitivity = session_sensitivity_stability(features, "resilience")
    receipt_gating = len(features.transitions_after_two_losses) >= 8
    return result(
        "resilience",
        score=value,
        sample_size=sample,
        effective_sample_size=min(len(after_win), len(after_loss)) * 2,
        coverage=sample / max(features.sample_size, 1),
        minimum_sample=30,
        stability=min(0.85 if abs(delta) > 0.08 else 0.70, sensitivity),
        quality=0.90 if receipt_gating else 0.65,
        evidence=(
            FeatureEvidence("after_win_performance", round(mean(after_win) or 0.0, 4), "proxy", len(after_win)),
            FeatureEvidence("after_loss_performance", round(mean(after_loss) or 0.0, 4), "proxy", len(after_loss)),
            FeatureEvidence("outcome_conditioned_delta", round(delta, 4), "proxy_delta", sample),
            FeatureEvidence("effect_direction", "more_after_loss" if delta > 0 else "less_after_loss" if delta < 0 else "neutral", "direction", sample),
            FeatureEvidence("effect_magnitude", round(abs(delta), 4), "absolute_proxy_delta", sample),
            FeatureEvidence("two_loss_receipts", len(features.transitions_after_two_losses), "transitions", len(features.transitions_after_two_losses)),
            FeatureEvidence("session_gap_agreement", sensitivity, "agreement", 3),
        ),
        confounders=("matchmaking, stopping behaviour, parties, and hero changes can affect the next game",)
        + (() if receipt_gating else ("fewer than eight two-loss receipts; magnitude is provisional",)),
        source_match_ids=features.dated_match_ids,
    )

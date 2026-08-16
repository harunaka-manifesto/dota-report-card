from __future__ import annotations

from collections import Counter

from app.dna.dimensions.common import clamp, result, session_sensitivity_stability
from app.dna.features.models import DnaFeatureSet, FeatureEvidence

ENDURANCE_VERSION = "endurance-1.1.0"


def score(features: DnaFeatureSet):
    by_id = {item.match_id: item for item in features.matches}
    slopes: list[float] = []
    session_ids: list[int] = []
    first_count = 0
    late_count = 0
    game4_count = 0
    early_roles: Counter[str] = Counter()
    late_roles: Counter[str] = Counter()
    for session in features.sessions:
        if session.match_count < 2:
            continue
        rows = [
            by_id[match_id]
            for match_id in session.match_ids
            if match_id in by_id
            and not by_id[match_id].session_corrupt
            and match_id in features.performance_by_match
        ]
        if len(rows) < 2:
            continue
        xs = [
            min(item.session_index or index + 1, 4)
            for index, item in enumerate(rows)
        ]
        ys = [features.performance_by_match[item.match_id] for item in rows]
        mean_x = sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        denominator = sum((value - mean_x) ** 2 for value in xs)
        if denominator <= 0:
            continue
        slopes.append(sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / denominator)
        session_ids.extend(item.match_id for item in rows)
        first_count += sum(x == 1 for x in xs)
        late_count += sum(x >= 3 for x in xs)
        game4_count += sum(x >= 4 for x in xs)
        for x, item in zip(xs, rows, strict=True):
            if item.role_hint and x == 1:
                early_roles[item.role_hint] += 1
            elif item.role_hint and x >= 3:
                late_roles[item.role_hint] += 1
    independent_sessions = len(slopes)
    sample = first_count + late_count
    if independent_sessions < 12 or first_count < 15 or late_count < 12:
        return result(
            "endurance", score=None, sample_size=sample,
            effective_sample_size=independent_sessions,
            coverage=sample / max(features.sample_size, 1), minimum_sample=27,
            missing_reasons=("insufficient_multi_game_sessions_or_late_games",),
            descriptor_eligible=False,
        )
    role_confounder = _role_mix_confounder(early_roles, late_roles)
    slope = sum(slopes) / len(slopes)
    value = clamp(0.5 + slope / 0.80)
    sensitivity = session_sensitivity_stability(features, "endurance")
    confounders: tuple[str, ...] = ("players may stop after difficult or successful games",)
    if role_confounder:
        confounders += ("role mix changes across session positions",)
    return result(
        "endurance",
        score=value,
        sample_size=sample,
        effective_sample_size=independent_sessions,
        coverage=sample / max(features.sample_size, 1),
        minimum_sample=27,
        stability=min(0.85 if independent_sessions >= 20 else 0.65, sensitivity),
        quality=0.70 if role_confounder else 0.90,
        evidence=(
            FeatureEvidence("within_session_slope", round(slope, 6), "performance_per_game", independent_sessions),
            FeatureEvidence("game_one_observations", first_count, "matches", first_count),
            FeatureEvidence("game_three_plus_observations", late_count, "matches", late_count),
            FeatureEvidence("game_four_plus_observations", game4_count, "matches", game4_count),
            FeatureEvidence("independent_sessions", independent_sessions, "sessions", independent_sessions),
            FeatureEvidence("session_gap_agreement", sensitivity, "agreement", 3),
        ),
        confounders=confounders,
        source_match_ids=tuple(session_ids),
    )


def _role_mix_confounder(early: Counter[str], late: Counter[str]) -> bool:
    if not early or not late:
        return True
    roles = set(early) | set(late)
    early_total = sum(early.values()) or 1
    late_total = sum(late.values()) or 1
    distance = sum(abs(early.get(role, 0) / early_total - late.get(role, 0) / late_total) for role in roles)
    return distance > 0.60

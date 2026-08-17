"""Hero Mirror: closest sufficiently sampled observable behavior, not lore."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from typing import Literal

from app.hero_portfolio.eligibility import build_hero_eligibility, eligible_heroes
from app.hero_portfolio.models import HeroEligibility, HeroMirrorResult
from app.hero_portfolio.version import HERO_MIRROR_VERSION
from app.heroes.taxonomy import HeroTaxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch

_ROLE_KEYS = ("carry", "mid", "offlane", "soft_support", "hard_support", "roamer", "jungle")
_DIMENSION_SCALES = {
    "involvement": 8.0,
    "finishing": 0.5,
    "deaths": 1.5,
    **{f"role:{key}": 0.5 for key in _ROLE_KEYS},
}


def compute_hero_mirror(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    eligibility: Sequence[HeroEligibility] | None = None,
) -> HeroMirrorResult:
    eligibility = tuple(eligibility or build_hero_eligibility(matches, taxonomy))
    candidates = eligible_heroes(eligibility, insight="mirror")
    if not candidates:
        return _unavailable("No sufficiently sampled hero has the required summary metrics.")

    rows_by_hero: dict[int, list[NormalizedSummaryMatch]] = {item.hero_id: [] for item in candidates}
    for item in matches:
        if item.hero_id is not None and item.hero_id in rows_by_hero:
            rows_by_hero[item.hero_id].append(item)
    ranked: list[tuple[float, float, float, HeroEligibility, dict[str, float], dict[str, float]]] = []
    for candidate in candidates:
        hero_rows = rows_by_hero[candidate.hero_id]
        reference_rows = [item for item in matches if item.hero_id != candidate.hero_id]
        if len(reference_rows) < 12:
            # Keep the candidate's contribution capped when exclusion would make
            # the reference too small, while still requiring independent rows.
            independent = list(reference_rows)
            if not independent:
                continue
            reference_rows = independent + hero_rows[: min(len(hero_rows), max(3, len(independent) // 2))]
        reference = _aggregate(reference_rows)
        observed = _aggregate(hero_rows)
        if not reference or not observed:
            continue
        shrunk = _shrink(observed, reference, candidate.matches)
        score, coverage = _similarity(shrunk, reference)
        confidence = min(1.0, candidate.matches / 12.0) * coverage
        ranked.append((score, confidence, coverage, candidate, reference, shrunk))
    if not ranked:
        return _unavailable("Candidate-excluded comparison could not form a stable reference.")
    ranked.sort(key=lambda item: (-item[0], -item[1], item[3].hero_id))
    score, confidence, coverage, winner, reference, hero_vector = ranked[0]
    runner_score = ranked[1][0] if len(ranked) > 1 else 0.0
    margin = score - runner_score
    player_vector = _aggregate(matches) or reference
    # Three core summary metrics can form a useful comparison when credible
    # role hints are absent; the missing dimensions still reduce confidence.
    status: Literal["available", "no_clear_mirror"] = "available" if coverage >= 0.30 and confidence >= 0.30 and margin >= 0.04 else "no_clear_mirror"
    entry = taxonomy.get(winner.hero_id)
    limitations: tuple[str, ...] = (
        "This is not a personality test.",
        "The comparison uses involvement, finishing, death exposure, and credible role context from summary history only.",
    )
    if status != "available":
        limitations += ("No candidate clears the confidence and runner-up margin yet.",)
    return HeroMirrorResult(
        status=status,
        hero_id=winner.hero_id if status == "available" else None,
        hero_name=entry.name if entry and status == "available" else None,
        similarity_score=score,
        runner_up_hero_id=ranked[1][3].hero_id if len(ranked) > 1 else None,
        margin=margin,
        player_behavior=_behavior_labels(player_vector),
        hero_behavior=_behavior_labels(hero_vector),
        confidence_score=confidence,
        limitations=limitations,
    )


def _aggregate(rows: Sequence[NormalizedSummaryMatch]) -> dict[str, float] | None:
    valid = [item for item in rows if _row_has_metrics(item)]
    if not valid:
        return None
    activity = sum((item.kills or 0) + (item.assists or 0) for item in valid) / sum((item.duration_seconds or 1) / 60.0 for item in valid)
    kills = sum(item.kills or 0 for item in valid)
    assists = sum(item.assists or 0 for item in valid)
    finishing = kills / max(kills + assists, 1)
    deaths = sum(item.deaths or 0 for item in valid) / sum((item.duration_seconds or 1) / 600.0 for item in valid)
    role_counts = Counter(item.role_hint for item in valid if item.role_hint in _ROLE_KEYS)
    total_roles = sum(role_counts.values())
    vector: dict[str, float] = {
        "involvement": activity,
        "finishing": finishing,
        "deaths": deaths,
    }
    if total_roles:
        for role in _ROLE_KEYS:
            vector[f"role:{role}"] = role_counts[role] / total_roles
    return vector


def _row_has_metrics(item: NormalizedSummaryMatch) -> bool:
    return (
        item.duration_seconds is not None
        and item.duration_seconds >= 600
        and item.kills is not None
        and item.deaths is not None
        and item.assists is not None
    )


def _shrink(observed: dict[str, float], reference: dict[str, float], sample: int) -> dict[str, float]:
    observed_weight = min(1.0, sample / 12.0)
    return {
        key: reference[key] + (observed.get(key, reference[key]) - reference[key]) * observed_weight
        for key in reference
        if key in observed
    }


def _similarity(left: dict[str, float], right: dict[str, float]) -> tuple[float, float]:
    distances = []
    for key, scale in _DIMENSION_SCALES.items():
        if key not in left or key not in right:
            continue
        distances.append(min(2.0, abs(left[key] - right[key]) / scale))
    if not distances:
        return 0.0, 0.0
    coverage = len(distances) / len(_DIMENSION_SCALES)
    return math.exp(-sum(distances) / len(distances)) * coverage, coverage


def _behavior_labels(vector: dict[str, float]) -> dict[str, str]:
    involvement = vector.get("involvement", 0.0)
    finishing = vector.get("finishing", 0.5)
    deaths = vector.get("deaths", 1.0)
    role_values = {key.removeprefix("role:"): value for key, value in vector.items() if key.startswith("role:")}
    dominant_role = max(role_values, key=lambda value: role_values[value]) if role_values else None
    return {
        "involvement": _five_zone(involvement, (5.0, 7.0, 9.0, 12.0), ("Quiet", "Selective", "Present", "Active", "Everywhere")),
        "finishing": _five_zone(finishing, (0.25, 0.40, 0.60, 0.75), ("Setup", "Support", "Split", "Closer", "Cleanup")),
        "deaths": _five_zone(deaths, (0.50, 0.75, 1.00, 1.35), ("Elusive", "Safe", "Mixed", "Exposed", "Frequent")),
        "role_context": _role_label(dominant_role),
    }


def _five_zone(value: float, cutoffs: tuple[float, float, float, float], labels: tuple[str, ...]) -> str:
    for index, cutoff in enumerate(cutoffs):
        if value < cutoff:
            return labels[index]
    return labels[-1]


def _role_label(role: str | None) -> str:
    return {
        "carry": "Carry-heavy",
        "mid": "Mid-heavy",
        "offlane": "Offlane-heavy",
        "soft_support": "Support-heavy",
        "hard_support": "Support-heavy",
        "roamer": "Roam-heavy",
        "jungle": "Jungle-heavy",
    }.get(role or "", "Role context mixed")


def _unavailable(reason: str) -> HeroMirrorResult:
    return HeroMirrorResult(
        status="unavailable",
        hero_id=None,
        hero_name=None,
        similarity_score=None,
        runner_up_hero_id=None,
        margin=None,
        player_behavior={},
        hero_behavior={},
        confidence_score=0.0,
        limitations=(reason, "This is not a personality test."),
    )


__all__ = ["HERO_MIRROR_VERSION", "compute_hero_mirror"]

"""Common Thread: the recurring functional trait across established heroes."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from app.content.renderer import resolve_portfolio_copy
from app.hero_portfolio.eligibility import build_hero_eligibility, eligible_heroes
from app.hero_portfolio.models import ChoiceOption, CommonThreadResult, HeroEligibility
from app.hero_portfolio.ordering import stable_pseudo_shuffle
from app.heroes.taxonomy import TRAITS, HeroTaxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch


def compute_common_thread(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    eligibility: Sequence[HeroEligibility] | None = None,
) -> CommonThreadResult:
    eligibility = tuple(eligibility or build_hero_eligibility(matches, taxonomy))
    candidates = eligible_heroes(eligibility, insight="common_thread")
    if len(candidates) < 3:
        return _unavailable("At least three established taxonomy-covered heroes are needed.")

    counts: defaultdict[int, int] = defaultdict(int)
    for item in matches:
        if item.hero_id is not None:
            counts[int(item.hero_id)] += 1
    total_usage = sum(counts[item.hero_id] for item in candidates)
    cap = max(3.0, total_usage * 0.35)
    trait_scores: dict[str, float] = {}
    trait_spread: dict[str, int] = {}
    for trait in TRAITS:
        weighted = 0.0
        spread = 0
        for candidate in candidates:
            entry = taxonomy.get(candidate.hero_id)
            if entry is None:
                continue
            weight = min(float(counts[candidate.hero_id]), cap)
            trait_value = float(entry.traits.get(trait, 0.0))
            weighted += weight * trait_value
            spread += trait_value >= 0.55
        trait_scores[trait] = weighted / max(sum(min(float(counts[item.hero_id]), cap) for item in candidates), 1.0)
        trait_spread[trait] = spread

    ranked = sorted(
        trait_scores,
        key=lambda trait: (
            -(0.70 * trait_scores[trait] + 0.30 * trait_spread[trait] / max(len(candidates), 1)),
            trait,
        ),
    )
    winner = ranked[0]
    winner_value = 0.70 * trait_scores[winner] + 0.30 * trait_spread[winner] / max(len(candidates), 1)
    runner_value = (
        0.70 * trait_scores[ranked[1]] + 0.30 * trait_spread[ranked[1]] / max(len(candidates), 1)
        if len(ranked) > 1 else 0.0
    )
    margin = winner_value - runner_value
    if trait_scores[winner] < 0.35 or margin < 0.03:
        return _unavailable("No single recurring trait clears the dominance margin.")

    seed = "|".join(
        [
            winner,
            *(f"{candidate.hero_id}:{counts[candidate.hero_id]}" for candidate in candidates),
            *ranked[:4],
        ]
    )
    options = _options(ranked, winner, seed=seed)
    confidence = min(
        1.0,
        0.45 * winner_value + 0.30 * min(1.0, len(candidates) / 8.0) + 0.25 * min(1.0, margin / 0.20),
    )
    return CommonThreadResult(
        status="available",
        trait_key=winner,
        trait_label=_trait_label(winner),
        weighted_coverage=trait_scores[winner],
        hero_count=trait_spread[winner],
        denominator=len(candidates),
        secondary_traits=tuple(_trait_label(item) for item in ranked[1:4]),
        options=options,
        correct_option_key=winner,
        confidence_score=confidence,
        limitations=("This describes what the heroes tend to offer; it does not prove those tools were used correctly in every match.",),
    )


def _options(ranked: list[str], winner: str, *, seed: str) -> tuple[ChoiceOption, ...]:
    distractors = [item for item in ranked if item != winner][:3]
    choices = [winner, *distractors]
    ordered = stable_pseudo_shuffle(choices, seed=f"common-thread|{seed}", key=str)
    return tuple(
        ChoiceOption(
            key=trait,
            label=_trait_label(trait),
            feedback=(
                resolve_portfolio_copy("common_thread.correct_feedback", trait=_trait_label(trait))
                if trait == winner
                else resolve_portfolio_copy(
                    "common_thread.incorrect_feedback",
                    selected=_trait_label(trait),
                    trait=_trait_label(winner),
                )
            ),
        )
        for trait in ordered
    )


def _unavailable(reason: str) -> CommonThreadResult:
    return CommonThreadResult(
        status="unavailable",
        trait_key=None,
        trait_label=None,
        weighted_coverage=0.0,
        hero_count=0,
        denominator=0,
        secondary_traits=(),
        options=(),
        correct_option_key=None,
        confidence_score=0.0,
        limitations=(reason,),
    )


def _trait_label(trait: str) -> str:
    return trait.replace("_", " ").title()


__all__ = ["compute_common_thread"]

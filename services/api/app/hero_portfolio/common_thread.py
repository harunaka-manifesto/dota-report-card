"""Common Thread: the recurring functional trait across established heroes."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from app.behavior.display_bands import job_display_label
from app.content.renderer import resolve_portfolio_copy
from app.hero_portfolio.config import PORTFOLIO_CONFIG
from app.hero_portfolio.eligibility import build_hero_eligibility, eligible_heroes
from app.hero_portfolio.models import ChoiceOption, CommonThreadResult, HeroEligibility
from app.hero_portfolio.ordering import stable_pseudo_shuffle
from app.heroes.knowledge import FUNCTIONAL_JOBS, HeroKnowledgeProvider
from app.heroes.taxonomy import TRAITS, HeroTaxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch


def compute_common_thread(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    eligibility: Sequence[HeroEligibility] | None = None,
    *,
    report_seed: str | None = None,
    hero_knowledge: HeroKnowledgeProvider | None = None,
) -> CommonThreadResult:
    eligibility = tuple(
        eligibility
        or build_hero_eligibility(matches, taxonomy, hero_knowledge=hero_knowledge)
    )
    candidates = eligible_heroes(eligibility, insight="common_thread")
    if len(candidates) < 3:
        return _unavailable("At least three established heroes with readable hero notes are needed.")
    if hero_knowledge is not None:
        return _compute_semantic_common_thread(
            matches, candidates, hero_knowledge, report_seed=report_seed
        )

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
    if (
        trait_scores[winner] < PORTFOLIO_CONFIG.common_thread_min_coverage
        or margin < PORTFOLIO_CONFIG.common_thread_min_margin
    ):
        return _unavailable("No single recurring trait clears the dominance margin.")

    derived_seed = "|".join(
        [
            winner,
            *(f"{candidate.hero_id}:{counts[candidate.hero_id]}" for candidate in candidates),
            *ranked[:4],
        ]
    )
    options = _options(ranked, winner, seed=report_seed or derived_seed)
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


def _compute_semantic_common_thread(
    matches: Sequence[NormalizedSummaryMatch],
    candidates: Sequence[HeroEligibility],
    provider: HeroKnowledgeProvider,
    *,
    report_seed: str | None,
) -> CommonThreadResult:
    counts: defaultdict[int, int] = defaultdict(int)
    for item in matches:
        if item.hero_id is not None:
            counts[int(item.hero_id)] += 1
    total_usage = sum(counts[item.hero_id] for item in candidates)
    cap = max(3.0, total_usage * 0.35)
    scores: dict[str, float] = {}
    spread: dict[str, int] = {}
    for function in FUNCTIONAL_JOBS:
        weighted = 0.0
        count = 0
        for candidate in candidates:
            entry = provider.get(candidate.hero_id)
            if entry is None:
                continue
            weight = min(float(counts[candidate.hero_id]), cap)
            jobs = set(entry.primary_functions) | set(entry.secondary_functions)
            weighted += weight * (function in jobs)
            count += function in jobs
        scores[function] = weighted / max(
            sum(min(float(counts[item.hero_id]), cap) for item in candidates), 1.0
        )
        spread[function] = count
    ranked = sorted(
        FUNCTIONAL_JOBS,
        key=lambda function: (
            -(0.70 * scores[function] + 0.30 * spread[function] / max(len(candidates), 1)),
            function,
        ),
    )
    winner = ranked[0]
    winner_value = 0.70 * scores[winner] + 0.30 * spread[winner] / max(len(candidates), 1)
    runner_value = (
        0.70 * scores[ranked[1]] + 0.30 * spread[ranked[1]] / max(len(candidates), 1)
        if len(ranked) > 1
        else 0.0
    )
    margin = winner_value - runner_value
    if (
        scores[winner] < PORTFOLIO_CONFIG.common_thread_min_coverage
        or margin < PORTFOLIO_CONFIG.common_thread_min_margin
    ):
        return _unavailable("No single recurring way of helping clears the difference needed for a clear answer.")
    derived_seed = "|".join(
        [winner, *(f"{item.hero_id}:{counts[item.hero_id]}" for item in candidates), *ranked[:4]]
    )
    options = _options(
        ranked,
        winner,
        seed=report_seed or derived_seed,
        semantic=True,
    )
    confidence = min(
        1.0,
        0.45 * winner_value
        + 0.30 * min(1.0, len(candidates) / 8.0)
        + 0.25 * min(1.0, margin / 0.20),
    )
    return CommonThreadResult(
        status="available",
        trait_key=winner,
        trait_label=job_display_label(winner),
        weighted_coverage=scores[winner],
        hero_count=spread[winner],
        denominator=len(candidates),
        secondary_traits=tuple(job_display_label(item) for item in ranked[1:4]),
        options=options,
        correct_option_key=winner,
        confidence_score=confidence,
        limitations=(
            "This describes the ways the established heroes tend to help; it does not prove those tools were used correctly in every match.",
        ),
    )


def _options(
    ranked: list[str],
    winner: str,
    *,
    seed: str,
    semantic: bool = False,
) -> tuple[ChoiceOption, ...]:
    distractors = [item for item in ranked if item != winner][:3]
    choices = [winner, *distractors]
    ordered = stable_pseudo_shuffle(choices, seed=f"common-thread|{seed}", key=str)
    label = job_display_label if semantic else _trait_label
    return tuple(
        ChoiceOption(
            key=trait,
            label=label(trait),
            feedback=(
                resolve_portfolio_copy("common_thread.correct_feedback", trait=label(trait))
                if trait == winner
                else resolve_portfolio_copy(
                    "common_thread.incorrect_feedback",
                    selected=label(trait),
                    trait=label(winner),
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

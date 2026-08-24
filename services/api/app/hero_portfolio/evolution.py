"""Pool Evolution: hero-name movement versus toolkit movement."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from app.behavior.display_bands import job_display_label
from app.hero_portfolio.config import PORTFOLIO_CONFIG
from app.hero_portfolio.models import PoolEvolutionResult
from app.heroes.knowledge import HeroKnowledgeProvider, canonical_function_key
from app.heroes.taxonomy import HeroTaxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch

EVOLUTION_MIN_WINDOW_SIZE = PORTFOLIO_CONFIG.evolution_min_window_size
EVOLUTION_MAX_WINDOW_SIZE = PORTFOLIO_CONFIG.evolution_max_window_size
EVOLUTION_TAXONOMY_COVERAGE_GATE = PORTFOLIO_CONFIG.evolution_taxonomy_coverage_gate
EVOLUTION_HERO_SHIFT_THRESHOLD = PORTFOLIO_CONFIG.evolution_hero_shift_threshold
EVOLUTION_TOOLKIT_SHIFT_THRESHOLD = PORTFOLIO_CONFIG.evolution_toolkit_shift_threshold
EVOLUTION_CORE_OVERLAP_THRESHOLD = PORTFOLIO_CONFIG.evolution_core_overlap_threshold


def compute_pool_evolution(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    hero_knowledge: HeroKnowledgeProvider | None = None,
) -> PoolEvolutionResult:
    ordered = sorted(
        (item for item in matches if item.started_at is not None and item.hero_id is not None),
        key=lambda item: (item.started_at or 0, item.match_id),
    )
    if len(ordered) < EVOLUTION_MIN_WINDOW_SIZE * 2:
        return _unavailable(
            "A balanced Pool Evolution comparison needs at least 12 chronologically usable matches in both windows.",
            earlier_size=len(ordered) // 2,
            recent_size=len(ordered) // 2,
        )

    window_size = min(EVOLUTION_MAX_WINDOW_SIZE, len(ordered) // 2)
    earlier = ordered[-(2 * window_size):-window_size]
    recent = ordered[-window_size:]
    earlier_coverage = _semantic_coverage(earlier, taxonomy, hero_knowledge)
    recent_coverage = _semantic_coverage(recent, taxonomy, hero_knowledge)
    if min(earlier_coverage, recent_coverage) < EVOLUTION_TAXONOMY_COVERAGE_GATE:
        return _unavailable(
            "Pool Evolution is unavailable because readable hero information covers less than 80% of one balanced window.",
            earlier_size=len(earlier),
            recent_size=len(recent),
            earlier_coverage=earlier_coverage,
            recent_coverage=recent_coverage,
        )

    earlier_hero_ids = [int(item.hero_id) for item in earlier if item.hero_id is not None]
    recent_hero_ids = [int(item.hero_id) for item in recent if item.hero_id is not None]
    hero_shift = _distribution_shift(Counter(earlier_hero_ids), Counter(recent_hero_ids))
    earlier_toolkit = _toolkit_distribution(earlier, taxonomy, hero_knowledge)
    recent_toolkit = _toolkit_distribution(recent, taxonomy, hero_knowledge)
    toolkit_shift = _distribution_shift(earlier_toolkit, recent_toolkit)
    earlier_traits = _top_distribution_keys(earlier_toolkit, semantic=hero_knowledge is not None)
    recent_traits = _top_distribution_keys(recent_toolkit, semantic=hero_knowledge is not None)
    overlap = _top_overlap(earlier_toolkit, recent_toolkit)
    if hero_shift >= EVOLUTION_HERO_SHIFT_THRESHOLD and toolkit_shift >= EVOLUTION_TOOLKIT_SHIFT_THRESHOLD:
        variant = "new_heroes_new_toolkit"
    elif hero_shift >= EVOLUTION_HERO_SHIFT_THRESHOLD and toolkit_shift < EVOLUTION_TOOLKIT_SHIFT_THRESHOLD:
        variant = "new_heroes_same_toolkit"
    elif toolkit_shift >= EVOLUTION_TOOLKIT_SHIFT_THRESHOLD and overlap >= EVOLUTION_CORE_OVERLAP_THRESHOLD:
        variant = "stable_core_new_branch"
    else:
        variant = "broadly_stable"
    patches = {item.patch for item in (*earlier, *recent) if item.patch}
    limitations = ["The output describes observed movement inside two balanced chronological windows."]
    patch_penalty = 1.0
    if len(patches) > 1:
        limitations.append("Patch or time context changed inside the comparison window.")
        patch_penalty = 0.72
    confidence = patch_penalty * min(
        1.0,
        0.55 * min(1.0, min(len(earlier), len(recent)) / EVOLUTION_MAX_WINDOW_SIZE)
        + 0.25 * min(earlier_coverage, recent_coverage)
        + 0.20 * min(1.0, (hero_shift + toolkit_shift) / 0.5),
    )
    semantic_quality = _semantic_review_quality(
        (*earlier, *recent), hero_knowledge
    )
    confidence *= semantic_quality
    earlier_start, earlier_end = _window_dates(earlier)
    recent_start, recent_end = _window_dates(recent)
    return PoolEvolutionResult(
        status="available",
        variant=variant,
        earlier_hero_ids=tuple(sorted(set(earlier_hero_ids))),
        recent_hero_ids=tuple(sorted(set(recent_hero_ids))),
        earlier_traits=earlier_traits,
        recent_traits=recent_traits,
        hero_distribution_shift=hero_shift,
        toolkit_distribution_shift=toolkit_shift,
        confidence_score=confidence,
        earlier_sample_size=len(earlier),
        recent_sample_size=len(recent),
        earlier_taxonomy_coverage=earlier_coverage,
        recent_taxonomy_coverage=recent_coverage,
        earlier_start=earlier_start,
        earlier_end=earlier_end,
        recent_start=recent_start,
        recent_end=recent_end,
        limitations=tuple(limitations),
    )


def _unavailable(
    reason: str,
    *,
    earlier_size: int = 0,
    recent_size: int = 0,
    earlier_coverage: float = 0.0,
    recent_coverage: float = 0.0,
) -> PoolEvolutionResult:
    return PoolEvolutionResult(
        status="unavailable",
        variant=None,
        earlier_hero_ids=(),
        recent_hero_ids=(),
        earlier_traits=(),
        recent_traits=(),
        hero_distribution_shift=None,
        toolkit_distribution_shift=None,
        confidence_score=0.0,
        earlier_sample_size=earlier_size,
        recent_sample_size=recent_size,
        earlier_taxonomy_coverage=earlier_coverage,
        recent_taxonomy_coverage=recent_coverage,
        limitations=(reason,),
    )


def _taxonomy_coverage(rows: Sequence[NormalizedSummaryMatch], taxonomy: HeroTaxonomy) -> float:
    covered = sum(
        1
        for item in rows
        if (entry := taxonomy.get(item.hero_id)) is not None and entry.available and bool(entry.traits)
    )
    return covered / max(len(rows), 1)


def _semantic_coverage(
    rows: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    provider: HeroKnowledgeProvider | None,
) -> float:
    if provider is None:
        return _taxonomy_coverage(rows, taxonomy)
    covered = sum(
        1
        for item in rows
        if (entry := provider.get(item.hero_id)) is not None
        and entry.review_status in {"approved", "reviewed"}
        and (entry.primary_functions or entry.secondary_functions)
    )
    return covered / max(len(rows), 1)


def _toolkit_distribution(
    rows: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    provider: HeroKnowledgeProvider | None = None,
) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in rows:
        if provider is not None:
            entry = provider.get(item.hero_id)
            if entry is None or entry.review_status not in {"approved", "reviewed"}:
                continue
            for function in tuple(dict.fromkeys((*entry.primary_functions, *entry.secondary_functions))):
                key = canonical_function_key(function)
                values[key] = values.get(key, 0.0) + 1.0
            continue
        hero = taxonomy.get(item.hero_id)
        if hero is None or not hero.available:
            continue
        for trait, value in hero.traits.items():
            values[trait] = values.get(trait, 0.0) + float(value)
    return values


def _distribution_shift(left: Mapping[Any, float], right: Mapping[Any, float]) -> float:
    keys = set(left) | set(right)
    left_total = sum(float(value) for value in left.values())
    right_total = sum(float(value) for value in right.values())
    if not keys or not left_total or not right_total:
        return 0.0
    p = {key: float(left.get(key, 0.0)) / left_total for key in keys}
    q = {key: float(right.get(key, 0.0)) / right_total for key in keys}
    midpoint = {key: (p[key] + q[key]) / 2.0 for key in keys}
    jsd = 0.5 * sum(p[key] * math.log(p[key] / midpoint[key]) for key in keys if p[key] > 0) + 0.5 * sum(q[key] * math.log(q[key] / midpoint[key]) for key in keys if q[key] > 0)
    return max(0.0, min(1.0, math.sqrt(jsd / math.log(2))))


def _top_distribution_keys(
    values: Mapping[str, float], *, semantic: bool = False
) -> tuple[str, ...]:
    total = sum(float(value) for value in values.values())
    if not total:
        return ()
    keys = tuple(
        trait
        for trait, value in sorted(values.items(), key=lambda item: (-item[1], item[0]))[:5]
        if float(value) / total >= 0.06
    )
    return tuple(job_display_label(key) for key in keys) if semantic else keys


def _top_overlap(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    return len(set(_top_distribution_keys(left)[:3]) & set(_top_distribution_keys(right)[:3])) / 3.0


def _semantic_review_quality(
    rows: Sequence[NormalizedSummaryMatch], provider: HeroKnowledgeProvider | None
) -> float:
    if provider is None:
        return 1.0
    usable = [provider.get(item.hero_id) for item in rows]
    reviewed = sum(
        entry is not None and entry.review_status in {"approved", "reviewed"}
        for entry in usable
    )
    return 0.55 + 0.45 * reviewed / max(len(rows), 1)


def _window_dates(rows: Sequence[NormalizedSummaryMatch]) -> tuple[str | None, str | None]:
    dated = [item.started_at for item in rows if item.started_at is not None]
    if not dated:
        return None, None
    return str(_utc_date(min(dated))), str(_utc_date(max(dated)))


def _utc_date(timestamp: int):
    from datetime import UTC, datetime

    return datetime.fromtimestamp(timestamp, tz=UTC).date()


__all__ = [
    "EVOLUTION_HERO_SHIFT_THRESHOLD",
    "EVOLUTION_MAX_WINDOW_SIZE",
    "EVOLUTION_MIN_WINDOW_SIZE",
    "EVOLUTION_TAXONOMY_COVERAGE_GATE",
    "compute_pool_evolution",
]

"""Pool Evolution: hero-name movement versus toolkit movement."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from app.hero_portfolio.models import PoolEvolutionResult
from app.heroes.taxonomy import HeroTaxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch


def compute_pool_evolution(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
) -> PoolEvolutionResult:
    ordered = sorted(
        (item for item in matches if item.started_at is not None and item.hero_id is not None),
        key=lambda item: (item.started_at or 0, item.match_id),
    )
    if len(ordered) < 24:
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
            limitations=("Chronology needs at least 24 established matches on both sides of a stable comparison.",),
        )
    recent_size = max(12, min(len(ordered) // 3, len(ordered) - 12))
    earlier = ordered[:-recent_size]
    recent = ordered[-recent_size:]
    earlier_hero_ids = [int(item.hero_id) for item in earlier if item.hero_id is not None]
    recent_hero_ids = [int(item.hero_id) for item in recent if item.hero_id is not None]
    hero_shift = _distribution_shift(Counter(earlier_hero_ids), Counter(recent_hero_ids))
    earlier_toolkit = _toolkit_distribution(earlier, taxonomy)
    recent_toolkit = _toolkit_distribution(recent, taxonomy)
    toolkit_shift = _distribution_shift(earlier_toolkit, recent_toolkit)
    earlier_traits = _top_distribution_keys(earlier_toolkit)
    recent_traits = _top_distribution_keys(recent_toolkit)
    overlap = _top_overlap(earlier_toolkit, recent_toolkit)
    if hero_shift >= 0.22 and toolkit_shift >= 0.18:
        variant = "new_heroes_new_toolkit"
    elif hero_shift >= 0.22 and toolkit_shift < 0.18:
        variant = "new_heroes_same_toolkit"
    elif toolkit_shift >= 0.18 and overlap >= 0.35:
        variant = "stable_core_new_branch"
    else:
        variant = "broadly_stable"
    patches = {item.patch for item in (*earlier, *recent) if item.patch}
    limitations = ["The output describes observed movement inside the analysis window."]
    if len(patches) > 1:
        limitations.append("Patch or time context changed inside the comparison window.")
    confidence = min(
        1.0,
        0.55 * min(1.0, min(len(earlier), len(recent)) / 30.0)
        + 0.25 * (1.0 if len(patches) <= 1 else 0.72)
        + 0.20 * min(1.0, (hero_shift + toolkit_shift) / 0.5),
    )
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
        limitations=tuple(limitations),
    )


def _toolkit_distribution(
    rows: Sequence[NormalizedSummaryMatch], taxonomy: HeroTaxonomy
) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in rows:
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
    p = {key: float(left[key]) / left_total for key in keys}
    q = {key: float(right[key]) / right_total for key in keys}
    midpoint = {key: (p[key] + q[key]) / 2.0 for key in keys}
    jsd = 0.5 * sum(p[key] * math.log(p[key] / midpoint[key]) for key in keys if p[key] > 0) + 0.5 * sum(q[key] * math.log(q[key] / midpoint[key]) for key in keys if q[key] > 0)
    return max(0.0, min(1.0, math.sqrt(jsd / math.log(2))))


def _top_distribution_keys(values: Mapping[str, float]) -> tuple[str, ...]:
    total = sum(float(value) for value in values.values())
    if not total:
        return ()
    return tuple(
        trait
        for trait, value in sorted(values.items(), key=lambda item: (-item[1], item[0]))[:5]
        if float(value) / total >= 0.06
    )


def _top_overlap(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    return len(set(_top_distribution_keys(left)[:3]) & set(_top_distribution_keys(right)[:3])) / 3.0


__all__ = ["compute_pool_evolution"]

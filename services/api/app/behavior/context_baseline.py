"""Shared leave-group-out comparable baselines for Drift and Recovery.

Elements and Pattern actions must not maintain subtly different definitions of
"comparable personal baseline".  This module owns the context hierarchy,
exclusion semantics, weighting, and provenance returned to both callers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from app.dna.recency import effective_sample_size, weighted_median
from app.heroes.taxonomy import HeroTaxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch

CONTEXT_BASELINE_VERSION = "context-baseline-1.0.0"
BaselineLevel = Literal[
    "hero_role_function",
    "hero_function",
    "function",
    "role",
    "overall",
]

_FUNCTION_TRAITS = (
    "initiation",
    "mobility",
    "pickoff",
    "teamfight",
    "save",
    "sustain",
    "burst",
    "sustained_damage",
    "wave_clear",
    "push",
    "frontline",
    "scaling",
    "global_presence",
    "repositioning",
)


@dataclass(frozen=True, slots=True)
class ComparableContext:
    hero_id: int | None
    function_family: str | None
    role_context: str | None


@dataclass(frozen=True, slots=True)
class BaselineResolution:
    value: float
    level: BaselineLevel
    reference_sample_size: int
    effective_sample_size: float
    reference_match_ids: tuple[int, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "version": CONTEXT_BASELINE_VERSION,
            "value": round(self.value, 6),
            "level": self.level,
            "reference_sample_size": self.reference_sample_size,
            "effective_sample_size": round(self.effective_sample_size, 6),
            "reference_match_ids": list(self.reference_match_ids),
        }


def primary_function(
    item: NormalizedSummaryMatch,
    taxonomy: HeroTaxonomy | None,
) -> str | None:
    if taxonomy is None or item.hero_id is None:
        return None
    entry = taxonomy.get(item.hero_id)
    if entry is None or not entry.available:
        return None
    ranked = sorted(
        ((entry.traits.get(key, 0.0), key) for key in _FUNCTION_TRAITS),
        reverse=True,
    )
    return ranked[0][1] if ranked and ranked[0][0] >= 0.60 else None


def comparable_context(
    target: NormalizedSummaryMatch,
    taxonomy: HeroTaxonomy | None,
) -> ComparableContext:
    return ComparableContext(
        hero_id=target.hero_id,
        function_family=primary_function(target, taxonomy),
        role_context=target.role_hint,
    )


def _matches_level(
    row: NormalizedSummaryMatch,
    target_context: ComparableContext,
    level: BaselineLevel,
    taxonomy: HeroTaxonomy | None,
) -> bool:
    row_function = primary_function(row, taxonomy)
    if level == "hero_role_function":
        return (
            target_context.hero_id is not None
            and target_context.role_context is not None
            and target_context.function_family is not None
            and row.hero_id == target_context.hero_id
            and row.role_hint == target_context.role_context
            and row_function == target_context.function_family
        )
    if level == "hero_function":
        return (
            target_context.hero_id is not None
            and target_context.function_family is not None
            and row.hero_id == target_context.hero_id
            and row_function == target_context.function_family
        )
    if level == "function":
        return (
            target_context.function_family is not None
            and row_function == target_context.function_family
        )
    if level == "role":
        return target_context.role_context is not None and row.role_hint == target_context.role_context
    return True


def resolve_leave_group_out_baseline(
    *,
    target: NormalizedSummaryMatch,
    candidate_rows: Sequence[NormalizedSummaryMatch],
    performance_by_match: Mapping[int, float],
    taxonomy: HeroTaxonomy | None,
    weights_by_match: Mapping[int, float],
    exclusion_group_id: str | None,
    minimum_reference_sample: int = 3,
) -> BaselineResolution | None:
    """Resolve the narrowest supported baseline without group leakage.

    A candidate in the target session is excluded even if the caller passes a
    broad candidate list.  The target row itself is always excluded as well.
    This makes the resolver safe for both session-level Element and action
    callers.
    """

    target_context = comparable_context(target, taxonomy)
    candidates = [
        row
        for row in candidate_rows
        if row.match_id != target.match_id
        and row.match_id in performance_by_match
        and (exclusion_group_id is None or row.session_id != exclusion_group_id)
    ]
    for level in (
        "hero_role_function",
        "hero_function",
        "function",
        "role",
        "overall",
    ):
        rows = [
            row
            for row in candidates
            if _matches_level(row, target_context, level, taxonomy)
        ]
        if len(rows) < max(1, minimum_reference_sample):
            continue
        pairs = [
            (
                float(performance_by_match[row.match_id]),
                max(0.0, float(weights_by_match.get(row.match_id, 1.0))),
            )
            for row in rows
        ]
        value = weighted_median(
            [item[0] for item in pairs],
            [item[1] for item in pairs],
        )
        if value is None:
            continue
        weights = [item[1] for item in pairs]
        return BaselineResolution(
            value=value,
            level=level,
            reference_sample_size=len(rows),
            effective_sample_size=effective_sample_size(weights),
            reference_match_ids=tuple(sorted(row.match_id for row in rows)),
        )
    return None


__all__ = [
    "BaselineLevel",
    "BaselineResolution",
    "ComparableContext",
    "CONTEXT_BASELINE_VERSION",
    "comparable_context",
    "primary_function",
    "resolve_leave_group_out_baseline",
]

"""Structured, deterministic presentation contracts for Free DNA v5.2.

Pattern qualification remains owned by ``behavior.patterns``.  This module
only translates a qualified (or explicitly unavailable) Pattern and its
reviewed action into a finite story contract.  It never writes prose and it
never calls an LLM.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from app.behavior.display_bands import (
    death_exposure_label,
    job_display_label,
    presence_label,
    relative_performance_label,
    session_bucket_label,
    session_curve_label,
)
from app.behavior.models import ElementResult, PatternResult
from app.behavior.outcomes import (
    SEMANTIC_OUTCOME_BRANCHES,
    SEMANTIC_OUTCOME_VERSION,
    SEMANTIC_RECOMMENDATION_BRANCHES,
    SEMANTIC_RECOMMENDATION_IDS,
    classify_pattern_outcome,
    classify_recommendation_state,
)
from app.heroes.knowledge import (
    FUNCTIONAL_JOBS,
    HERO_DEMAND_FAMILIES,
    JOB_GLOSSARY,
    HeroKnowledgeProvider,
    TaxonomyHeroKnowledgeProvider,
)
from app.heroes.recommendations import SEMANTIC_RECOMMENDATION_VERSION
from app.heroes.relationships import build_pool_profile, build_semantic_pool_profile
from app.heroes.taxonomy import HeroTaxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch

PATTERN_PRESENTATION_VERSION = "pattern-presentation-5.2.0"

PATTERN_PRESENTATION_CONTRACT: dict[str, dict[str, str]] = {
    "same_playbook": {
        "outcome_id": "P01_BROAD_HERO_NARROW_JOB",
        "visual_variant": "hero_job_cluster",
        "interpretation_id": "P01_BROAD_HERO_NARROW_JOB",
        "recommendation_id": "P01_ADD_MISSING_FUNCTION",
        "deep_dive_id": "P01_DRAFT_SPECIFIC_EXPANSION",
    },
    "comfort_edge": {
        "outcome_id": "P02_RELIABILITY_LADDER",
        "visual_variant": "hero_reliability_ladder",
        "interpretation_id": "P02_RELIABILITY_LADDER",
        "recommendation_id": "P02_FOCUS_DEVELOPMENT_ORDER",
        "deep_dive_id": "P02_HERO_DEMAND_COMPARISON",
    },
    "partial_transfer": {
        "outcome_id": "P03_PRESENCE_HOLDS_RESULT_BENDS",
        "visual_variant": "transfer_split",
        "interpretation_id": "P03_PRESENCE_HOLDS_RESULT_BENDS",
        "recommendation_id": "P03_PRACTICE_TRANSFER_DEMAND",
        "deep_dive_id": "P03_ENTRY_HOLD_REENTRY",
    },
    "versatile_core": {
        "outcome_id": "P04_COMPACT_POOL_BROAD_JOBS",
        "visual_variant": "toolkit_orbit",
        "interpretation_id": "P04_COMPACT_POOL_BROAD_JOBS",
        "recommendation_id": "P04_ADD_MISSING_FUNCTION",
        "deep_dive_id": "P04_DRAFT_SPECIFIC_EXPANSION",
    },
    "proven_flexibility": {
        "outcome_id": "P05_PROVEN_FLEX_WINDOW",
        "visual_variant": "flex_window_grid",
        "interpretation_id": "P05_PROVEN_FLEX_WINDOW",
        "recommendation_id": "P05_PROTECT_RELIABLE_ANCHORS",
        "deep_dive_id": "P05_CONTEXT_TRANSFER",
    },
    "bounceback": {
        "outcome_id": "P06_POST_LOSS_STRONGER",
        "visual_variant": "post_loss_transition",
        "interpretation_id": "P06_POST_LOSS_STRONGER",
        "recommendation_id": "P06_REPEAT_POST_LOSS_ANCHOR",
        "deep_dive_id": "P06_POST_LOSS_MECHANISM",
    },
    "performance_slide": {
        "outcome_id": "P07_POST_LOSS_WEAKER",
        "visual_variant": "post_loss_transition",
        "interpretation_id": "P07_POST_LOSS_WEAKER",
        "recommendation_id": "P07_CHANGE_ONE_TRANSITION",
        "deep_dive_id": "P07_POST_LOSS_MECHANISM",
    },
    "controlled_presence": {
        "outcome_id": "P08_HIGH_PRESENCE_LOW_COST",
        "visual_variant": "presence_exposure_map",
        "interpretation_id": "P08_HIGH_PRESENCE_LOW_COST",
        "recommendation_id": "P08_PRESERVE_LOW_COST_PRESENCE",
        "deep_dive_id": "P08_FIGHT_CONTEXTS",
    },
    "presence_tax": {
        "outcome_id": "P09_HIGH_PRESENCE_HIGH_COST",
        "visual_variant": "presence_exposure_map",
        "interpretation_id": "P09_HIGH_PRESENCE_HIGH_COST",
        "recommendation_id": "P09_INVESTIGATE_PRESENCE_COST",
        "deep_dive_id": "P09_DEATH_VALUE_CONTEXT",
    },
    "session_fade": {
        "outcome_id": "P10_SESSION_FADE",
        "visual_variant": "session_curve",
        "interpretation_id": "P10_SESSION_FADE",
        "recommendation_id": "P10_CHECKPOINT_AT_BREAKPOINT",
        "deep_dive_id": "P10_SESSION_BREAKPOINT",
    },
    "session_rise": {
        "outcome_id": "P11_SESSION_RISE",
        "visual_variant": "session_curve",
        "interpretation_id": "P11_SESSION_RISE",
        "recommendation_id": "P11_FRONTLOAD_FAMILIARITY",
        "deep_dive_id": "P11_SESSION_BREAKPOINT",
    },
}

PRESENTATION_VISUAL_VARIANTS = frozenset(
    item["visual_variant"] for item in PATTERN_PRESENTATION_CONTRACT.values()
)
PRESENTATION_OUTCOME_IDS = frozenset(
    item["outcome_id"] for item in PATTERN_PRESENTATION_CONTRACT.values()
)
PRESENTATION_RECOMMENDATION_IDS = frozenset(
    item["recommendation_id"] for item in PATTERN_PRESENTATION_CONTRACT.values()
)
PRESENTATION_DEEP_DIVE_IDS = frozenset(
    item["deep_dive_id"] for item in PATTERN_PRESENTATION_CONTRACT.values()
)

_JOB_KEYS = FUNCTIONAL_JOBS


@dataclass(frozen=True, slots=True)
class PatternPresentationPayload:
    """Finite story inputs consumed by the web renderer."""

    pattern_id: str
    outcome_id: str
    visual_variant: str
    proof_data: Mapping[str, Any] = field(default_factory=dict)
    interpretation_id: str = ""
    recommendation_id: str | None = None
    recommendation_context: Mapping[str, Any] | None = None
    deep_dive_id: str | None = None
    semantic_outcome_id: str | None = None
    semantic_recommendation_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    raw_metrics: Mapping[str, float | int | str | bool | None] = field(default_factory=dict)
    confidence: str = "unavailable"
    presentation_version: str = PATTERN_PRESENTATION_VERSION

    def __post_init__(self) -> None:
        if self.pattern_id not in PATTERN_PRESENTATION_CONTRACT:
            raise ValueError(f"Unknown Pattern presentation: {self.pattern_id}")
        contract = PATTERN_PRESENTATION_CONTRACT[self.pattern_id]
        if self.outcome_id != contract["outcome_id"]:
            raise ValueError(f"Unexpected outcome for Pattern {self.pattern_id}")
        if self.visual_variant != contract["visual_variant"]:
            raise ValueError(f"Unexpected visual variant for Pattern {self.pattern_id}")
        if self.interpretation_id != contract["interpretation_id"]:
            raise ValueError(f"Unexpected interpretation for Pattern {self.pattern_id}")
        if self.recommendation_id is not None and self.recommendation_id != contract["recommendation_id"]:
            raise ValueError(f"Unexpected recommendation for Pattern {self.pattern_id}")
        if self.deep_dive_id is not None and self.deep_dive_id != contract["deep_dive_id"]:
            raise ValueError(f"Unexpected deep dive for Pattern {self.pattern_id}")
        if self.semantic_outcome_id is not None and self.semantic_outcome_id not in SEMANTIC_OUTCOME_BRANCHES[self.pattern_id]:
            raise ValueError(f"Unexpected semantic outcome for Pattern {self.pattern_id}")
        if (
            self.semantic_recommendation_id is not None
            and self.semantic_recommendation_id not in SEMANTIC_RECOMMENDATION_IDS
        ):
            raise ValueError(f"Unexpected semantic recommendation for Pattern {self.pattern_id}")
        if (
            self.semantic_recommendation_id is not None
            and self.semantic_recommendation_id
            not in SEMANTIC_RECOMMENDATION_BRANCHES[self.pattern_id]
        ):
            raise ValueError(f"Unexpected recommendation branch for Pattern {self.pattern_id}")
        if self.presentation_version != PATTERN_PRESENTATION_VERSION:
            raise ValueError(f"Unexpected presentation version for Pattern {self.pattern_id}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "outcome_id": self.outcome_id,
            "visual_variant": self.visual_variant,
            "proof_data": _json_safe(dict(self.proof_data)),
            "interpretation_id": self.interpretation_id,
            "recommendation_id": self.recommendation_id,
            "recommendation_context": (
                _json_safe(dict(self.recommendation_context))
                if self.recommendation_context is not None
                else None
            ),
            "deep_dive_id": self.deep_dive_id,
            "semantic_outcome_id": self.semantic_outcome_id,
            "semantic_recommendation_id": self.semantic_recommendation_id,
            "semantic_outcome_version": SEMANTIC_OUTCOME_VERSION,
            "semantic_recommendation_version": SEMANTIC_RECOMMENDATION_VERSION,
            "evidence_refs": list(self.evidence_refs),
            "raw_metrics": dict(self.raw_metrics),
            "confidence": self.confidence,
            "presentation_version": self.presentation_version,
        }


def build_pattern_presentation(
    pattern: PatternResult,
    elements: Mapping[str, ElementResult],
    *,
    matches: Sequence[NormalizedSummaryMatch] = (),
    taxonomy: HeroTaxonomy | None = None,
    hero_knowledge: HeroKnowledgeProvider | None = None,
) -> PatternPresentationPayload:
    """Build one deterministic presentation payload for every active Pattern."""

    contract = PATTERN_PRESENTATION_CONTRACT.get(pattern.key)
    if contract is None:
        raise ValueError(f"No v5.2 presentation contract for Pattern {pattern.key}")
    action_data = pattern.action.as_dict() if pattern.action is not None else {}
    knowledge = hero_knowledge or (TaxonomyHeroKnowledgeProvider(taxonomy) if taxonomy else None)
    proof_data = _proof_data(
        pattern,
        elements,
        action_data,
        matches=matches,
        taxonomy=taxonomy,
        hero_knowledge=knowledge,
    )
    evidence_refs = tuple(
        dict.fromkeys(
            [item.key for item in pattern.evidence]
            + list((action_data.get("evidence_summary") or {}).get("evidence_keys", []))
        )
    )
    recommendation_available = _recommendation_is_supported(pattern)
    recommendation_id = contract["recommendation_id"] if recommendation_available else None
    semantic_outcome_id = classify_pattern_outcome(pattern.key, action_data)
    semantic_recommendation_id = (
        classify_recommendation_state(pattern.key, action_data)
        if recommendation_available
        else None
    )
    recommendation_context = (
        _recommendation_context(pattern.key, action_data, proof_data, hero_knowledge=knowledge)
        if recommendation_available
        else None
    )
    semantic_outcome_id, semantic_recommendation_id = _safe_semantic_presentation_state(
        semantic_outcome_id,
        semantic_recommendation_id,
        recommendation_context,
    )
    return PatternPresentationPayload(
        pattern_id=pattern.key,
        outcome_id=contract["outcome_id"],
        visual_variant=contract["visual_variant"],
        proof_data=proof_data,
        interpretation_id=contract["interpretation_id"],
        recommendation_id=recommendation_id,
        recommendation_context=recommendation_context,
        deep_dive_id=contract["deep_dive_id"] if recommendation_available else None,
        semantic_outcome_id=semantic_outcome_id,
        semantic_recommendation_id=semantic_recommendation_id,
        evidence_refs=evidence_refs,
        raw_metrics=dict(pattern.effect_metrics),
        confidence=pattern.confidence,
    )


def _safe_semantic_presentation_state(
    outcome_id: str,
    recommendation_id: str | None,
    recommendation_context: Mapping[str, Any] | None,
) -> tuple[str, str | None]:
    """Keep serialized semantic IDs aligned with candidate-backed public copy."""

    hero_name = (recommendation_context or {}).get("hero_name")
    requires_hero = outcome_id in {
        "P01_NARROW_JOB_BRIDGE_FOUND",
        "P04_GAP_WITH_BRIDGE",
    } or recommendation_id in {
        "HR_DOUBLE_DOWN",
        "HR_ADJACENT_MOVE_ADD_FUNCTION",
        "HR_CHANGE_ANGLE",
        "HR_FILL_GAP_ADD_FUNCTION",
        "HR_SPECIALIST",
    }
    if not requires_hero or (isinstance(hero_name, str) and hero_name.strip()):
        return outcome_id, recommendation_id
    return (
        {
            "P01_NARROW_JOB_BRIDGE_FOUND": "P01_NARROW_JOB_NO_BRIDGE",
            "P04_GAP_WITH_BRIDGE": "P04_GAP_NO_BRIDGE",
        }.get(outcome_id, outcome_id),
        "HR_PRACTICE_FALLBACK",
    )


def _recommendation_is_supported(pattern: PatternResult) -> bool:
    """Keep weak or unavailable evidence on the non-semantic fallback path."""

    return (
        pattern.status == "qualified"
        and pattern.confidence in {"moderate", "high"}
        and pattern.confidence_score >= 0.45
        and pattern.evidence_coverage >= 0.45
    )


def _proof_data(
    pattern: PatternResult,
    elements: Mapping[str, ElementResult],
    action: Mapping[str, Any],
    *,
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy | None,
    hero_knowledge: HeroKnowledgeProvider | None,
) -> dict[str, Any]:
    proof: dict[str, Any] = {
        "pattern_status": pattern.status,
        "confidence": pattern.confidence,
        "confidence_score": round(pattern.confidence_score, 6),
        "evidence_coverage": round(pattern.evidence_coverage, 6),
    }
    if pattern.key == "same_playbook":
        proof.update(_same_playbook_proof(action, matches, taxonomy, hero_knowledge))
    elif pattern.key == "comfort_edge":
        ranked = action.get("ranked_heroes", [])
        proof["ranked_heroes"] = [
            {
                "hero_name": item.get("hero_name"),
                "rank": item.get("reliability_rank"),
                "band": _reliability_band(item.get("reliability_rank")),
                "matches": item.get("matches", 0),
            }
            for item in ranked
        ]
        development = action.get("development", [])
        proof["reference_core_names"] = (
            list(development[0].get("reference_core_hero_names", []))
            if development
            else []
        )
        proof["reference_core_ids"] = list(action.get("reference_core_hero_ids", []))
    elif pattern.key == "partial_transfer":
        proof.update(_partial_transfer_proof(action))
    elif pattern.key == "versatile_core":
        coverage = action.get("coverage_summary", {})
        proof.update(
            {
                "hero_job_maps": action.get("hero_job_maps", []),
                "coverage": {
                    "strongly_covered": coverage.get("strongly_covered", []),
                    "thin": coverage.get("thin_coverage", []),
                    "missing": coverage.get("missing", []),
                    "family_map": coverage.get("family_map", {}),
                    "family_descriptions": coverage.get("family_descriptions", {}),
                    "primary_gap": coverage.get("primary_gap"),
                    "secondary_gaps": coverage.get("secondary_gaps", []),
                    "semantic_coverage": coverage.get("semantic_coverage"),
                    "role_adjusted_coverage": coverage.get("role_adjusted_coverage"),
                },
                "recommended_addition": action.get("recommended_addition"),
                "complementarity_qualified": action.get("complementarity_qualified", True),
            }
        )
    elif pattern.key == "proven_flexibility":
        hero_ids = action.get("hero_ids", [])
        hero_names = action.get("hero_names", [])
        counts = dict(action.get("hero_game_counts", []))
        proof.update(
            {
                "window_label": _window_label(action),
                "hero_names": hero_names,
                "hero_game_counts": action.get("hero_game_counts", []),
                "hero_rows": [
                    {"hero_name": name, "game_count": counts.get(hero_id, 0)}
                    for hero_id, name in zip(hero_ids, hero_names, strict=False)
                ],
                "total_games": action.get("total_games", 0),
                "functional_jobs": action.get("functional_jobs", []),
                "functional_job_count": action.get("functional_job_count", 0),
                "repeated_hero_count": action.get("repeated_hero_count", 0),
            }
        )
        if hero_knowledge is not None:
            proof["hero_semantics"] = [
                {
                    "hero_id": hero_id,
                    "hero_name": hero_name,
                    **_hero_semantic_context(semantic),
                }
                for hero_id, hero_name in zip(hero_ids, hero_names, strict=False)
                if (semantic := hero_knowledge.get(hero_id)) is not None
            ]
    elif pattern.key in {"bounceback", "performance_slide"}:
        strongest = action.get("strongest_context") or {}
        proof.update(
            {
                "transition_label": "LOSS → NEXT GAME: STRONGER"
                if pattern.key == "bounceback"
                else "LOSS → NEXT GAME: WEAKER",
                "context_label": strongest.get("label", "Overall"),
                "hero_name": strongest.get("label") if strongest.get("hero_id") else None,
                "function_family": strongest.get("function_family"),
                "primary_jobs": strongest.get("primary_jobs", []),
                "comparison_contexts": action.get("comparison_contexts", []),
            }
        )
        if strongest.get("hero_id") is not None and hero_knowledge is not None:
            semantic = hero_knowledge.get(int(strongest["hero_id"]))
            if semantic is not None:
                proof["hero_semantics"] = _hero_semantic_context(semantic)
    elif pattern.key in {"controlled_presence", "presence_tax"}:
        contexts = action.get("comparison_rows") or action.get("comparison_contexts") or []
        proof["contexts"] = [_presence_proof(item) for item in contexts]
        proof["shape"] = action.get("shape")
        proof["deep_analysis_candidate"] = action.get("deep_analysis_candidate", False)
        strongest = contexts[0] if contexts else None
        if isinstance(strongest, Mapping) and strongest.get("hero_id") is not None and hero_knowledge is not None:
            semantic = hero_knowledge.get(int(strongest["hero_id"]))
            if semantic is not None:
                proof["hero_semantics"] = _hero_semantic_context(semantic)
    elif pattern.key in {"session_fade", "session_rise"}:
        direction: Literal["fade", "rise"] = "fade" if pattern.key == "session_fade" else "rise"
        curve = action.get("curve", [])
        proof["curve"] = [
            {
                **item,
                "bucket_label": session_bucket_label(str(item.get("bucket", ""))),
                "display_label": session_curve_label(item.get("relative_delta"), direction=direction),
            }
            for item in curve
        ]
        proof["direction"] = direction
        proof["breakpoint_label"] = (
            session_bucket_label(str(action["breakpoint_bucket"]))
            if action.get("breakpoint_bucket")
            else None
        )
        proof["breakpoint_state"] = action.get("breakpoint_state", "unresolved")
        proof["independent_session_count"] = action.get("independent_session_count", 0)
    if elements:
        proof["element_zones"] = {
            key: item.zone for key, item in elements.items() if key in pattern.element_keys
        }
    return proof


def _same_playbook_proof(
    action: Mapping[str, Any],
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy | None,
    hero_knowledge: HeroKnowledgeProvider | None,
) -> dict[str, Any]:
    proof: dict[str, Any] = {
        "hero_names": [],
        "regular_hero_count": 0,
        "strongest_jobs": action.get("dominant_traits", [])[:4],
        "missing_functions": action.get("underrepresented_traits", [])[:4],
        "recommended_hero": (action.get("stretch") or [None])[0],
    }
    if taxonomy is None or not matches:
        proof["hero_names"] = [
            item.get("hero_name")
            for item in (*action.get("deepen", []), *action.get("stretch", []))
            if item.get("hero_name")
        ][:4]
        proof["regular_hero_count"] = len(proof["hero_names"])
        return proof
    profile = (
        build_semantic_pool_profile(matches, hero_knowledge)
        if hero_knowledge is not None
        else build_pool_profile(matches, taxonomy)
    )
    names = []
    for hero_id in sorted(profile.hero_ids, key=lambda item: (-profile.usage_counts.get(item, 0), item)):
        knowledge_entry = hero_knowledge.get(hero_id) if hero_knowledge else None
        if knowledge_entry is not None:
            names.append(knowledge_entry.display_name)
        elif taxonomy_entry := taxonomy.get(hero_id):
            names.append(taxonomy_entry.name)
    clusters: dict[str, list[str]] = defaultdict(list)
    for hero_id in profile.hero_ids:
        knowledge = hero_knowledge.get(hero_id) if hero_knowledge else None
        if knowledge is not None:
            for job in tuple(dict.fromkeys((*knowledge.primary_functions, *knowledge.secondary_functions))):
                clusters[job_display_label(job)].append(knowledge.display_name)
        elif taxonomy is not None:
            taxonomy_entry = taxonomy.get(hero_id)
            if taxonomy_entry is None:
                continue
            for job in _JOB_KEYS:
                if taxonomy_entry.traits.get(job, 0.0) >= 0.60:
                    clusters[job_display_label(job)].append(taxonomy_entry.name)
    proof["hero_names"] = names
    proof["regular_hero_count"] = len(names)
    proof["job_clusters"] = [
        {"job": job, "hero_names": sorted(hero_names), "hero_count": len(hero_names)}
        for job, hero_names in sorted(clusters.items(), key=lambda item: (-len(item[1]), item[0]))[:4]
    ]
    return proof


def _partial_transfer_proof(action: Mapping[str, Any]) -> dict[str, Any]:
    differences = action.get("summary_differences", [])
    involvement = next((item for item in differences if item.get("signal_key") == "combat_involvement"), None)
    result = next((item for item in differences if item.get("signal_key") == "result_distribution"), None)
    demand = (action.get("capability_hypotheses") or [None])[0]
    off_value = involvement.get("off_pool_value") if involvement else None
    core_value = involvement.get("core_value") if involvement else None
    result_delta = (
        (result.get("off_pool_value") or 0.0) - (result.get("core_value") or 0.0)
        if result
        else None
    )
    return {
        "familiar_presence": presence_label(core_value),
        "off_pool_presence": presence_label(off_value),
        "result_direction": relative_performance_label(result_delta),
        "strongest_demand": (
            job_display_label(str(demand.get("capability_key"))) if demand else None
        ),
        "direct_signals": differences,
        "hypotheses": action.get("capability_hypotheses", []),
    }


def _presence_proof(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "label": item.get("label", "Overall"),
        "involvement_label": presence_label(item.get("involvement_level")),
        "death_exposure_label": death_exposure_label(item.get("death_exposure_level")),
        "involvement_level": item.get("involvement_level"),
        "death_exposure_level": item.get("death_exposure_level"),
        "sample_size": item.get("sample_size", 0),
        "confidence_score": item.get("confidence_score", 0.0),
    }


def _hero_semantic_context(hero: Any) -> dict[str, Any]:
    return {
        "primary_functions": [job_display_label(item) for item in hero.primary_functions],
        "secondary_functions": [job_display_label(item) for item in hero.secondary_functions],
        "function_definitions": {
            job_display_label(item): str(JOB_GLOSSARY.get(item, {}).get("public_short_description", ""))
            for item in (*hero.primary_functions, *hero.secondary_functions)
            if item in JOB_GLOSSARY
        },
        "demands": dict(hero.demands),
        "empirical_support": hero.empirical_support,
        "confidence": hero.confidence,
        "provenance_versions": dict(hero.provenance_versions),
        "evidence_refs": list(hero.evidence_refs),
    }


def _recommendation_context(
    pattern_key: str,
    action: Mapping[str, Any],
    proof: Mapping[str, Any],
    *,
    hero_knowledge: HeroKnowledgeProvider | None,
) -> dict[str, Any] | None:
    candidate: Mapping[str, Any] | None = None
    if pattern_key == "same_playbook":
        candidate = proof.get("recommended_hero") or None
    elif pattern_key == "versatile_core":
        candidate = action.get("recommended_addition") or None
    elif pattern_key == "comfort_edge":
        development = action.get("development", [])
        candidate = development[0] if development else None
    elif pattern_key == "partial_transfer":
        hypotheses = action.get("capability_hypotheses") or []
        hypothesis = hypotheses[0] if hypotheses and isinstance(hypotheses[0], Mapping) else None
        evidence = action.get("evidence_summary") or {}
        if hypothesis is not None:
            demand = hypothesis.get("capability_key")
            new_demands = [demand] if demand in HERO_DEMAND_FAMILIES else []
            hypothesis_confidence = float(hypothesis.get("confidence_score") or 0.0)
            return {
                "kind": "practice",
                "hero_id": None,
                "hero_name": None,
                "familiar_jobs": proof.get("strongest_jobs", []),
                "adds": [],
                "intent": "change_angle",
                "familiar_anchors": proof.get("strongest_jobs", []),
                "new_demands": new_demands,
                "learning_distance": None,
                "role_fit": None,
                "empirical_support": "unknown",
                "confidence": (
                    "high"
                    if hypothesis_confidence >= 0.75
                    else "medium"
                    if hypothesis_confidence >= 0.50
                    else "low"
                ),
                "limitations": list(action.get("limitations", []))
                + ["This is a demand hypothesis, not a causal explanation."],
                "provenance_versions": dict(evidence.get("provenance_versions", {})),
                "evidence_refs": list(evidence.get("evidence_keys", [])),
            }
    if not candidate:
        return {
            "kind": "practice",
            "hero_id": None,
            "hero_name": None,
            "familiar_jobs": proof.get("strongest_jobs", []),
            "adds": proof.get("missing_functions", []),
            "intent": None,
            "familiar_anchors": proof.get("strongest_jobs", []),
            "new_demands": [],
            "learning_distance": None,
            "role_fit": None,
            "empirical_support": "unknown",
            "confidence": "low",
            "limitations": ["no_eligible_hero_candidate"],
            "provenance_versions": {},
        }
    knowledge = hero_knowledge.get(candidate.get("hero_id")) if hero_knowledge else None
    if candidate.get("hero_id") is not None and knowledge is None:
        return {
            "kind": "practice",
            "hero_id": None,
            "hero_name": None,
            "familiar_jobs": proof.get("strongest_jobs", []),
            "adds": proof.get("missing_functions", []),
            "intent": None,
            "familiar_anchors": proof.get("strongest_jobs", []),
            "new_demands": [],
            "learning_distance": None,
            "role_fit": None,
            "empirical_support": "unknown",
            "confidence": "low",
            "limitations": ["hero_knowledge_missing"],
            "provenance_versions": {},
        }
    rationale = candidate.get("semantic_rationale") or {}
    if not isinstance(rationale, Mapping):
        rationale = {}
    return {
        "kind": "hero" if candidate.get("hero_id") else "practice",
        "hero_id": candidate.get("hero_id"),
        "hero_name": knowledge.display_name if knowledge else candidate.get("hero_name"),
        "familiar_jobs": candidate.get("anchor_traits") or candidate.get("shared_anchors") or proof.get("strongest_jobs", []),
        "adds": candidate.get("added_traits") or candidate.get("adds_jobs") or proof.get("missing_functions", []),
        "intent": rationale.get("intent"),
        "familiar_anchors": rationale.get("familiar_anchors", candidate.get("anchor_traits") or candidate.get("shared_anchors") or []),
        "new_demands": rationale.get("new_demands", []),
        "learning_distance": rationale.get("learning_distance"),
        "role_fit": rationale.get("role_fit"),
        "empirical_support": rationale.get("empirical_support", knowledge.empirical_support if knowledge else "unknown"),
        "confidence": rationale.get("confidence", knowledge.confidence if knowledge else "low"),
        "limitations": rationale.get("limitations", []),
        "provenance_versions": dict(
            rationale.get("provenance_versions", knowledge.provenance_versions if knowledge else {})
        ),
        "evidence_refs": rationale.get("evidence_refs", knowledge.evidence_refs if knowledge else []),
    }


def _reliability_band(rank: Any) -> str:
    try:
        numeric = int(rank)
    except (TypeError, ValueError):
        return "Still developing"
    if numeric <= 2:
        return "Anchor"
    if numeric == 3:
        return "Close"
    return "Still developing"


def _window_label(action: Mapping[str, Any]) -> str | None:
    start = action.get("window_start")
    end = action.get("window_end")
    if not start or not end:
        return None
    return f"{start} – {end}"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(child) for child in value]
    return value


__all__ = [
    "PATTERN_PRESENTATION_CONTRACT",
    "PATTERN_PRESENTATION_VERSION",
    "PRESENTATION_DEEP_DIVE_IDS",
    "PRESENTATION_OUTCOME_IDS",
    "PRESENTATION_RECOMMENDATION_IDS",
    "PRESENTATION_VISUAL_VARIANTS",
    "PatternPresentationPayload",
    "build_pattern_presentation",
]

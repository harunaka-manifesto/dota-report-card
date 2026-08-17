"""Canonical organizational dimensions for the behavioral model."""

from __future__ import annotations

from dataclasses import dataclass

from app.behavior.tiers import EvidenceTier, ModelStatus, ProductTier


@dataclass(frozen=True, slots=True)
class DimensionDefinition:
    key: str
    label: str
    description: str
    free_status: ModelStatus
    deep_status: ModelStatus
    product_tier: ProductTier = "free"
    minimum_evidence_tier: EvidenceTier = "summary_history"
    version: str = "dimension-1.0.0"


DIMENSION_DEFINITIONS: tuple[DimensionDefinition, ...] = (
    DimensionDefinition("hero_identity", "Hero Identity", "How hero choice and toolkit shape observable identity.", "active", "active"),
    DimensionDefinition("role_identity", "Role Identity", "How stable or varied credible role-context hints are.", "active", "active"),
    DimensionDefinition("combat_expression", "Combat Expression", "How often the player joins kill events and how those events are distributed.", "active", "active"),
    DimensionDefinition("economy", "Economy", "Farm, item timing, and resource conversion behavior.", "planned", "planned", "paid", "match_detail"),
    DimensionDefinition("map_objectives", "Map & Objectives", "Objective pressure, vision, and map movement.", "planned", "planned", "paid", "parsed_replay"),
    DimensionDefinition("risk_survival", "Risk & Survival", "Observable death exposure and survival context.", "active", "active"),
    DimensionDefinition("adaptability", "Adaptability", "How observable performance and activity transfer across contexts.", "active", "active"),
    DimensionDefinition("consistency_form", "Consistency & Form", "Variation and recent movement in observable performance and activity.", "active", "active"),
    DimensionDefinition("session_response", "Session Response", "Session shape and what changes as a session continues.", "active", "active"),
    DimensionDefinition("progression", "Progression", "Future change-over-time comparisons beyond the current bounded report.", "planned", "planned", "free", "summary_history"),
)

DIMENSIONS_BY_KEY = {item.key: item for item in DIMENSION_DEFINITIONS}


def dimension_label(key: str) -> str:
    definition = DIMENSIONS_BY_KEY.get(key)
    return definition.label if definition else key.replace("_", " ").title()

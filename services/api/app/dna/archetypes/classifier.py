from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.dna.dimensions.models import DimensionResult

CLASSIFIER_VERSION = "archetypes-1.0.0"
_FALLBACK_KEY = "developing_competitor"


@dataclass(frozen=True, slots=True)
class ArchetypeResult:
    key: str
    label: str
    fit: float
    runner_up: dict[str, Any] | None
    descriptors: tuple[dict[str, str], ...]
    contributing_dimensions: tuple[dict[str, Any], ...]
    confidence: str
    explanation_evidence: tuple[str, ...]
    classifier_version: str = CLASSIFIER_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "fit": round(self.fit, 6),
            "runner_up": self.runner_up,
            "descriptors": [dict(item) for item in self.descriptors],
            "contributing_dimensions": [dict(item) for item in self.contributing_dimensions],
            "confidence": self.confidence,
            "explanation_evidence": list(self.explanation_evidence),
            "classifier_version": self.classifier_version,
        }


def load_prototypes(path: str | Path | None = None) -> list[dict[str, Any]]:
    source = Path(path) if path else Path(__file__).with_name("v1.json")
    value = json.loads(source.read_text(encoding="utf-8"))
    return list(value.get("prototypes", []))


def classify(
    dimensions: tuple[DimensionResult, ...] | list[DimensionResult],
    prototypes: list[dict[str, Any]] | None = None,
) -> ArchetypeResult:
    prototypes = prototypes or load_prototypes()
    reliable = [
        item for item in dimensions
        if item.score is not None and item.confidence_score > 0.0
    ]
    groups = {_dimension_group(item.key) for item in reliable}
    if len(reliable) < 4 or len(groups) < 3:
        return ArchetypeResult(
            key=_FALLBACK_KEY,
            label="The Developing Competitor",
            fit=0.0,
            runner_up=None,
            descriptors=(),
            contributing_dimensions=(),
            confidence="low",
            explanation_evidence=("fewer than four reliable signals across three groups",),
        )

    ranked: list[tuple[float, dict[str, Any], list[dict[str, Any]]]] = []
    for prototype in prototypes:
        expected = prototype.get("expected", {})
        weights = prototype.get("weights", {})
        contributions: list[dict[str, Any]] = []
        weighted_distance = 0.0
        total_weight = 0.0
        for dimension in reliable:
            if dimension.key not in expected:
                continue
            weight = float(weights.get(dimension.key, 1.0)) * dimension.confidence_score
            distance = (dimension.score or 0.5) - float(expected[dimension.key])
            contribution = max(0.0, weight * distance * distance)
            weighted_distance += contribution
            total_weight += weight
            contributions.append({
                "key": dimension.key,
                "weight": round(weight, 6),
                "contribution": round(contribution, 6),
            })
        if not total_weight:
            continue
        fit = max(0.0, min(1.0, 1.0 - weighted_distance / total_weight))
        ranked.append((fit, prototype, contributions))

    if not ranked:
        return ArchetypeResult(
            key=_FALLBACK_KEY,
            label="The Developing Competitor",
            fit=0.0,
            runner_up=None,
            descriptors=(),
            contributing_dimensions=(),
            confidence="low",
            explanation_evidence=("no prototype had an active dimension",),
        )

    ranked.sort(key=lambda item: (-item[0], item[1].get("key", "")))
    winner_fit, winner, contributions = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else None
    low_margin = runner is not None and winner_fit - runner[0] < 0.03
    confidence = "low" if low_margin else "high" if winner_fit >= 0.72 else "moderate"
    runner_up = {"key": runner[1]["key"], "fit": round(runner[0], 6)} if runner else None
    explanation = tuple(
        f"{item['key']} contributed {item['contribution']:.3f} distance"
        for item in sorted(contributions, key=lambda value: value["contribution"])[:3]
    )
    return ArchetypeResult(
        key=winner["key"],
        label=winner["label"],
        fit=winner_fit,
        runner_up=runner_up,
        descriptors=(),
        contributing_dimensions=tuple(contributions),
        confidence=confidence,
        explanation_evidence=explanation,
    )


def _dimension_group(key: str) -> str:
    if key in {"breadth", "role", "adaptability"}:
        return "hero_identity"
    if key in {"activity", "orientation"}:
        return "combat_expression"
    return "session_response"

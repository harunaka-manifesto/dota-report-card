from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.dna.dimensions.models import DimensionResult

CLASSIFIER_VERSION = "archetypes-1.1.0"
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
        return _fallback("fewer than four reliable signals across three groups")

    ranked: list[dict[str, Any]] = []
    for prototype in prototypes:
        expected = prototype.get("expected", {})
        weights = prototype.get("weights", {})
        required_groups = set(prototype.get("required_groups", prototype.get("groups", [])))
        contributions: list[dict[str, Any]] = []
        weighted_distance = 0.0
        active_weight = 0.0
        high_confidence = 0
        for dimension in reliable:
            if dimension.key not in expected:
                continue
            weight = float(weights.get(dimension.key, 1.0)) * dimension.confidence_score
            if weight <= 0:
                continue
            observed = dimension.centered_score if dimension.centered_score is not None else (dimension.score or 0.5) * 2 - 1
            expected_centered = _expected_centered(expected[dimension.key], prototype)
            distance = (observed - expected_centered) ** 2
            weighted_distance += weight * distance
            active_weight += weight
            high_confidence += dimension.confidence_score >= 0.75
            contributions.append({
                "key": dimension.key,
                "weight": round(weight, 6),
                "contribution": round(weight * distance, 6),
            })
        if not active_weight:
            continue
        covered_groups = {_dimension_group(item["key"]) for item in contributions}
        if required_groups and not required_groups.issubset(covered_groups):
            # A prototype is only meaningful when every declared evidence
            # group contributed.  Do not let a partial match win by treating
            # an absent group as a neutral signal.
            continue
        missing_group_fraction = (
            len(required_groups - covered_groups) / len(required_groups)
            if required_groups else 0.0
        )
        missingness = max(0.0, 1.0 - len(contributions) / 8.0)
        distance = weighted_distance / active_weight
        fit = max(0.0, min(1.0, 1.0 - math.sqrt(distance) / 2.0))
        fit -= 0.08 * missingness + 0.08 * missing_group_fraction
        ranked.append({
            "fit": max(0.0, fit),
            "prototype": prototype,
            "contributions": contributions,
            "high_confidence": high_confidence,
            "coverage": len(contributions),
            "extreme_assumptions": sum(abs(_expected_centered(value, prototype)) > 0.75 for value in expected.values()),
        })

    if not ranked:
        return _fallback("no prototype had an active dimension")

    ranked.sort(
        key=lambda item: (
            -item["fit"], -item["high_confidence"], -item["coverage"],
            item["extreme_assumptions"], item["prototype"].get("key", ""),
        )
    )
    winner = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else None
    low_margin = runner is not None and winner["fit"] - runner["fit"] < 0.03
    confidence = "low" if low_margin else "high" if winner["fit"] >= 0.72 else "moderate"
    runner_up = (
        {"key": runner["prototype"]["key"], "fit": round(runner["fit"], 6)}
        if runner else None
    )
    explanation = tuple(
        f"{item['key']} contributed {item['contribution']:.3f} distance"
        for item in sorted(winner["contributions"], key=lambda value: value["contribution"])[:3]
    )
    return ArchetypeResult(
        key=winner["prototype"]["key"],
        label=winner["prototype"]["label"],
        fit=winner["fit"],
        runner_up=runner_up,
        descriptors=(),
        contributing_dimensions=tuple(winner["contributions"]),
        confidence=confidence,
        explanation_evidence=explanation,
    )


def _fallback(reason: str) -> ArchetypeResult:
    return ArchetypeResult(
        key=_FALLBACK_KEY,
        label="The Developing Competitor",
        fit=0.0,
        runner_up=None,
        descriptors=(),
        contributing_dimensions=(),
        confidence="low",
        explanation_evidence=(reason,),
    )


def _expected_centered(value: Any, prototype: dict[str, Any]) -> float:
    number = float(value)
    if prototype.get("coordinate_system") == "centered":
        return max(-1.0, min(1.0, number))
    return max(-1.0, min(1.0, number * 2.0 - 1.0))


def _dimension_group(key: str) -> str:
    if key in {"breadth", "role", "adaptability"}:
        return "hero_identity"
    if key in {"activity", "orientation"}:
        return "combat_expression"
    return "session_response"

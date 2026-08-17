from __future__ import annotations

from app.behavior.archetypes.classifier import classify_archetypes
from app.behavior.elements.registry import ELEMENT_REGISTRY
from app.behavior.models import ElementResult


def _element(key: str, score: float = 0.5, *, status: str = "available") -> ElementResult:
    definition = ELEMENT_REGISTRY[key]
    return ElementResult(
        key=key,
        label=definition.label,
        dimension_key=definition.dimension_key,
        status=status,  # type: ignore[arg-type]
        score=score if status != "unavailable" else None,
        centered_score=2 * score - 1 if status != "unavailable" else None,
        confidence="high" if status != "unavailable" else "unavailable",
        confidence_score=0.90 if status != "unavailable" else 0.0,
        sample_size=60,
        effective_sample_size=60,
        coverage=1.0,
        stability=0.9,
        quality=0.9,
        methodology_version=definition.version,
        axis_left=definition.axis_left,
        axis_right=definition.axis_right,
    )


def test_classifier_returns_one_local_result_per_context_group() -> None:
    values = {key: _element(key) for key in ELEMENT_REGISTRY}
    values.update({
        "hero_pool_breadth": _element("hero_pool_breadth", 0.20),
        "hero_pool_stability": _element("hero_pool_stability", 0.80),
        "hero_exploration_rate": _element("hero_exploration_rate", 0.20),
        "toolkit_breadth": _element("toolkit_breadth", 0.20),
        "signature_dependence": _element("signature_dependence", 0.80),
        "combat_involvement": _element("combat_involvement", 0.75),
        "finisher_orientation": _element("finisher_orientation", 0.30),
        "death_exposure": _element("death_exposure", 0.35),
        "session_length_tendency": _element("session_length_tendency", 0.75),
        "late_session_performance": _element("late_session_performance", 0.60),
    })

    results = classify_archetypes(tuple(values.values()), ())

    assert {item.group_key for item in results} == {
        "hero_identity",
        "combat_expression",
        "session_style",
    }
    assert next(item for item in results if item.group_key == "hero_identity").key == "specialist"
    assert all(0.0 <= item.fit <= 1.0 for item in results)


def test_classifier_falls_back_without_treating_missing_as_neutral() -> None:
    values = [
        _element(key, status="unavailable")
        if key in {"session_length_tendency", "late_session_performance"}
        else _element(key)
        for key in ELEMENT_REGISTRY
    ]
    result = next(item for item in classify_archetypes(tuple(values), ()) if item.group_key == "session_style")

    assert result.key == "unclassified"
    assert result.confidence == "unavailable"
    assert result.fit == 0.0

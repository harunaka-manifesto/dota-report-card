from __future__ import annotations

from app.behavior.elements.registry import ELEMENT_REGISTRY
from app.behavior.evidence import BehaviorEvidence
from app.behavior.models import ElementResult
from app.behavior.patterns.service import evaluate_patterns


def _element(key: str, score: float | None = 0.5, *, status: str = "available") -> ElementResult:
    definition = ELEMENT_REGISTRY[key]
    return ElementResult(
        key=key,
        label=definition.label,
        dimension_key=definition.dimension_key,
        status=status,  # type: ignore[arg-type]
        score=score,
        centered_score=2 * score - 1 if score is not None else None,
        confidence="high" if score is not None else "unavailable",
        confidence_score=0.90 if score is not None else 0.0,
        sample_size=60,
        effective_sample_size=60,
        coverage=1.0,
        stability=0.9,
        quality=0.9,
        evidence=(BehaviorEvidence("fixture", score, "score", 60),) if score is not None else (),
        methodology_version=definition.version,
        axis_left=definition.axis_left,
        axis_right=definition.axis_right,
    )


def test_patterns_use_upstream_elements_and_qualify_only_reviewed_pairs() -> None:
    values = {key: _element(key) for key in ELEMENT_REGISTRY}
    values["hero_pool_breadth"] = _element("hero_pool_breadth", 0.82)
    values["toolkit_breadth"] = _element("toolkit_breadth", 0.18)

    patterns = {item.key: item for item in evaluate_patterns(tuple(values.values()))}
    result = patterns["same_playbook"]

    assert result.status == "qualified"
    assert set(result.element_keys) == {"hero_pool_breadth", "toolkit_breadth"}
    assert len(result.evidence) == 2
    assert all(receipt.key.startswith("element.") for receipt in result.evidence)


def test_pattern_stays_unavailable_when_an_upstream_element_is_missing() -> None:
    values = [
        _element(key, None, status="unavailable") if key == "toolkit_breadth" else _element(key)
        for key in ELEMENT_REGISTRY
    ]
    result = next(item for item in evaluate_patterns(values) if item.key == "same_playbook")

    assert result.status == "unavailable"
    assert result.strength == 0.0
    assert result.evidence == ()


def test_modifier_elements_do_not_block_pattern_qualification() -> None:
    values = {key: _element(key) for key in ELEMENT_REGISTRY}
    values["combat_involvement"] = _element("combat_involvement", 0.54)
    values["finisher_orientation"] = _element("finisher_orientation", 0.82)
    values["death_exposure"] = _element("death_exposure", None, status="unavailable")

    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == "selective_closer")

    assert result.status == "qualified"
    assert result.modifier_element_keys == ("death_exposure",)

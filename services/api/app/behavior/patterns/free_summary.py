"""Public entry point for the finite Free summary Pattern registry."""

from app.behavior.models import ElementResult, PatternResult
from app.behavior.patterns.service import evaluate_patterns


def evaluate(elements: tuple[ElementResult, ...] | list[ElementResult]) -> tuple[PatternResult, ...]:
    return evaluate_patterns(elements)


__all__ = ["evaluate"]

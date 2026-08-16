"""Finding-specific copy seam over the versioned Free DNA catalog."""

from __future__ import annotations

from typing import Any

from app.content.renderer import resolve_finding_copy

FORBIDDEN_CLAIM_TERMS = (
    "because",
    "causes",
    "makes you lose",
    "you tilt",
    "you panic",
    "you are afraid",
    "you are greedy",
    "diagnos",
)


def render_finding_copy(key: str, **params: str) -> dict[str, str]:
    """Resolve and lint one finding's public copy."""

    copy = resolve_finding_copy(key, **params)
    combined = " ".join(copy.values()).casefold()
    forbidden = [term for term in FORBIDDEN_CLAIM_TERMS if term in combined]
    if forbidden:
        raise ValueError(f"Finding copy contains forbidden claim language: {forbidden}")
    for field, value in copy.items():
        if "  " in value:
            raise ValueError(f"Finding copy contains double spaces: {key}.{field}")
    return copy


def copy_lint_value(value: Any) -> list[str]:
    """Return copy lint violations for QA tests without mutating content."""

    if not isinstance(value, str):
        return []
    lowered = value.casefold()
    return [term for term in FORBIDDEN_CLAIM_TERMS if term in lowered]

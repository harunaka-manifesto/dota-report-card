"""Typed, versioned copy resolution for public Free DNA v4 snapshots."""

from __future__ import annotations

from string import Formatter
from typing import Any

from app.behavior.elements.registry import EXPECTED_ELEMENT_KEYS
from app.behavior.patterns.registry import EXPECTED_PATTERN_KEYS
from app.content.catalog import load_free_dna_copy

_FORBIDDEN_TERMS = ("diagnos", "bad player", "good player", "grade", "personality type")
_PAGE_KEYS = ("analysis", "report_reveal", "element_scan", "final_card", "deep_dive")
_PORTFOLIO_KEYS = ("common_thread", "exception", "evolution", "hero_mirror")
_EVOLUTION_VARIANTS = (
    "new_heroes_new_toolkit",
    "new_heroes_same_toolkit",
    "stable_core_new_branch",
    "broadly_stable",
)


def resolve_page_copy(key: str, **params: str) -> dict[str, str]:
    catalog = validate_copy_catalog()
    page = catalog["pages"].get(key)
    if not isinstance(page, dict) or not isinstance(page.get("title"), str):
        raise ValueError(f"Unknown Free DNA page copy key: {key}")
    return _render_pair(page, params, label="page")


def resolve_element_copy(key: str, **params: str) -> dict[str, str]:
    catalog = validate_copy_catalog()
    return _resolve_model_copy(catalog, "elements", key, params)


def resolve_pattern_copy(key: str, **params: str) -> dict[str, str]:
    catalog = validate_copy_catalog()
    return _resolve_model_copy(catalog, "patterns", key, params)


def resolve_portfolio_copy(key: str, **params: str) -> str:
    catalog = validate_copy_catalog()
    parts = key.split(".", 1)
    if len(parts) != 2 or parts[0] not in _PORTFOLIO_KEYS:
        raise ValueError(f"Unknown Hero Portfolio copy key: {key}")
    value: Any = catalog["portfolio"].get(parts[0])
    if not isinstance(value, dict) or not isinstance(value.get(parts[1]), str):
        raise ValueError(f"Unknown Hero Portfolio copy key: {key}")
    template = value[parts[1]]
    fields = {name for _, name, _, _ in Formatter().parse(template) if name}
    missing = fields - set(params)
    extra = set(params) - fields
    if missing:
        raise ValueError(f"Missing copy parameters: {sorted(missing)}")
    if extra:
        raise ValueError(f"Unexpected copy parameters: {sorted(extra)}")
    return template.format(**params)


def validate_copy_catalog() -> dict[str, Any]:
    catalog = load_free_dna_copy()
    pages = catalog.get("pages")
    if not isinstance(pages, dict) or set(pages) != set(_PAGE_KEYS):
        raise ValueError("Free DNA copy catalog must cover every v4 story page family")
    for key in _PAGE_KEYS:
        value = pages[key]
        if not isinstance(value, dict) or not isinstance(value.get("title"), str) or not isinstance(value.get("body"), str):
            raise ValueError(f"Incomplete page copy: {key}")

    for section, expected in (("elements", EXPECTED_ELEMENT_KEYS), ("patterns", EXPECTED_PATTERN_KEYS)):
        values = catalog.get(section)
        if not isinstance(values, dict) or set(values) != set(expected):
            raise ValueError(f"Free DNA copy catalog must cover every active {section[:-1]}")
        for key in expected:
            value = values[key]
            if not isinstance(value, dict) or not isinstance(value.get("title"), str) or not isinstance(value.get("body"), str):
                raise ValueError(f"Incomplete {section[:-1]} copy: {key}")

    portfolio = catalog.get("portfolio")
    if not isinstance(portfolio, dict) or set(portfolio) != set(_PORTFOLIO_KEYS):
        raise ValueError("Free DNA copy catalog must cover the Hero Portfolio")
    for key in ("common_thread", "exception"):
        value = portfolio[key]
        required = ("question", "correct", "incorrect", "answer", "reveal", "boundary")
        if not isinstance(value, dict) or any(not isinstance(value.get(item), str) for item in required):
            raise ValueError(f"Incomplete portfolio copy: {key}")
    mirror = portfolio["hero_mirror"]
    if not isinstance(mirror, dict) or any(not isinstance(mirror.get(key), str) for key in ("closed", "available", "unavailable", "qualifier", "guardrail")):
        raise ValueError("Incomplete portfolio copy: hero_mirror")
    evolution = portfolio["evolution"]
    if not isinstance(evolution, dict) or not isinstance(evolution.get("question"), str) or not isinstance(evolution.get("check"), str):
        raise ValueError("Incomplete portfolio copy: evolution")
    if any(not isinstance(evolution.get(key), str) for key in _EVOLUTION_VARIANTS):
        raise ValueError("Evolution copy must cover every public variant")
    _lint_forbidden_terms(catalog)
    return catalog


def _resolve_model_copy(
    catalog: dict[str, Any], section: str, key: str, params: dict[str, str]
) -> dict[str, str]:
    value = catalog[section].get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Unknown Free DNA {section[:-1]} copy key: {key}")
    return _render_pair(value, params, label=section[:-1])


def _render_pair(value: dict[str, Any], params: dict[str, str], *, label: str) -> dict[str, str]:
    title = value.get("title")
    body = value.get("body")
    if not isinstance(title, str) or not isinstance(body, str):
        raise ValueError(f"Incomplete {label} copy")
    fields = {name for template in (title, body) for _, name, _, _ in Formatter().parse(template) if name}
    missing = fields - set(params)
    extra = set(params) - fields
    if missing:
        raise ValueError(f"Missing copy parameters: {sorted(missing)}")
    if extra:
        raise ValueError(f"Unexpected copy parameters: {sorted(extra)}")
    return {"title": title.format(**params), "body": body.format(**params)}


def _lint_forbidden_terms(value: Any) -> None:
    if isinstance(value, str):
        lowered = value.casefold()
        if any(term in lowered for term in _FORBIDDEN_TERMS):
            raise ValueError("Free DNA copy contains forbidden evaluative or diagnostic language")
        return
    if isinstance(value, dict):
        for child in value.values():
            _lint_forbidden_terms(child)
    elif isinstance(value, list):
        for child in value:
            _lint_forbidden_terms(child)


__all__ = [
    "resolve_element_copy",
    "resolve_page_copy",
    "resolve_pattern_copy",
    "resolve_portfolio_copy",
    "validate_copy_catalog",
]

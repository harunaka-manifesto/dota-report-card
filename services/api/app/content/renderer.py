"""Typed, versioned copy resolution for public Free DNA snapshots."""

from __future__ import annotations

from string import Formatter
from typing import Any, Literal

from app.content.catalog import load_free_dna_copy

DimensionStatus = Literal["available", "limited", "unavailable"]
_DIMENSION_KEYS = (
    "breadth", "role", "adaptability", "activity", "orientation",
    "resilience", "endurance", "rhythm",
)
_FORBIDDEN_TERMS = ("diagnos", "bad player", "good player", "grade", "personality type")
_FINDING_KEYS = (
    "broad_pool_narrow_safety_zone",
    "many_heroes_same_toolkit",
    "activity_travels_better_than_results",
    "losses_change_trust_more_than_pace",
    "long_session_tax",
    "long_game_edge",
    "long_game_leak",
    "form_identity_divergence",
    "strength_with_tax",
    "signature_hero_mechanism",
    "role_vs_hero_identity",
    "volatile_results_stable_style",
    "hidden_strength_fallback",
)


def resolve_dimension_copy(key: str, status: DimensionStatus) -> dict[str, Any]:
    if status not in {"available", "limited", "unavailable"}:
        raise ValueError(f"Unknown Free DNA dimension status: {status}")
    catalog = validate_copy_catalog()
    dimension = catalog["dimensions"].get(key)
    if not isinstance(dimension, dict):
        raise ValueError(f"Unknown Free DNA dimension copy key: {key}")
    return {
        "headline_key": f"free_dna.dimension.{key}.headline",
        "receipt_key": f"free_dna.dimension.{key}.receipt",
        "receipt_params": {"status": status},
        "headline": str(dimension["headline"]),
        "body": str(catalog["dimension"].get(status, "Signal available.")),
        "left_label": str(dimension.get("left", "Lower")),
        "right_label": str(dimension.get("right", "Higher")),
    }


def resolve_page_copy(key: str, **params: str) -> dict[str, str]:
    catalog = validate_copy_catalog()
    pages = catalog["pages"]
    page = pages.get(key)
    if not isinstance(page, dict) or not isinstance(page.get("title"), str):
        raise ValueError(f"Unknown Free DNA page copy key: {key}")
    title_template = str(page["title"])
    body_template = str(page.get("body", ""))
    fields = {
        field_name
        for template in (title_template, body_template)
        for _, field_name, _, _ in Formatter().parse(template)
        if field_name
    }
    unknown = fields - set(params)
    extra = set(params) - fields
    if unknown:
        raise ValueError(f"Missing copy parameters: {sorted(unknown)}")
    if extra:
        raise ValueError(f"Unexpected copy parameters: {sorted(extra)}")
    title = title_template.format(**params)
    body = body_template.format(**params)
    return {"title": title, "body": body}


def resolve_finding_copy(key: str, **params: str) -> dict[str, str]:
    """Resolve one versioned finding template with explicit parameters."""

    catalog = validate_copy_catalog()
    finding = catalog["findings"].get(key)
    if not isinstance(finding, dict):
        raise ValueError(f"Unknown Free DNA finding copy key: {key}")
    output: dict[str, str] = {}
    for field in ("eyebrow", "headline", "body", "interpretation", "share"):
        template = finding.get(field)
        if not isinstance(template, str):
            raise ValueError(f"Finding copy is missing {field}: {key}")
        fields = {
            field_name
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name
        }
        unknown = fields - set(params)
        if unknown:
            raise ValueError(f"Missing finding copy parameters: {sorted(unknown)}")
        output[field] = template.format(**params)
    return output


def resolve_experiment_title(key: str) -> str:
    catalog = validate_copy_catalog()
    experiment = catalog["experiments"].get(key)
    if not isinstance(experiment, dict) or not isinstance(experiment.get("title"), str):
        raise ValueError(f"Unknown Free DNA experiment copy key: {key}")
    return str(experiment["title"])


def validate_copy_catalog() -> dict[str, Any]:
    catalog = load_free_dna_copy()
    dimensions = catalog.get("dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(_DIMENSION_KEYS):
        raise ValueError("Free DNA copy catalog must cover all eight dimensions")
    pages = catalog.get("pages")
    if not isinstance(pages, dict):
        raise ValueError("Free DNA copy catalog is missing page copy")
    for key in _DIMENSION_KEYS:
        dimension = dimensions[key]
        if not isinstance(dimension, dict) or not dimension.get("headline"):
            raise ValueError(f"Missing headline copy for dimension: {key}")
    for key in ("steam_input", "player_found", "analysis", "report_reveal", "dna_intro", "dna_summary", "archetype", "heroes_intro", "signature_hero", "comfort_picks", "hero_pattern", "hero_recommendations", "heroes_summary", "final_card", "deep_dive"):
        page = pages.get(key)
        if not isinstance(page, dict) or not page.get("title"):
            raise ValueError(f"Missing page copy: {key}")
    findings = catalog.get("findings")
    if not isinstance(findings, dict) or set(findings) != set(_FINDING_KEYS):
        raise ValueError("Free DNA copy catalog must cover every registered finding")
    for key in _FINDING_KEYS:
        value = findings[key]
        if not isinstance(value, dict) or any(not isinstance(value.get(field), str) for field in ("eyebrow", "headline", "body", "interpretation", "share")):
            raise ValueError(f"Incomplete finding copy: {key}")
        if len(value["headline"]) > 90 or len(value["share"]) > 120:
            raise ValueError(f"Finding headline/share copy is too long: {key}")
    experiments = catalog.get("experiments")
    if not isinstance(experiments, dict):
        raise ValueError("Free DNA copy catalog is missing experiments")
    _lint_forbidden_terms(catalog)
    return catalog


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

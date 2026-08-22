"""Typed, versioned copy resolution for public Free DNA v5 snapshots."""

from __future__ import annotations

from string import Formatter
from typing import Any

from app.behavior.elements.registry import EXPECTED_ELEMENT_KEYS
from app.behavior.patterns.registry import EXPECTED_PATTERN_KEYS
from app.behavior.presentation import (
    PATTERN_PRESENTATION_CONTRACT,
    PATTERN_PRESENTATION_VERSION,
)
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
_STORY_TEMPLATE_KEYS = {
    "element": ("observation", "distinctive", "evidence", "notice", "guardrail"),
    "pattern": ("observation", "worth_noticing", "player_read", "takeaway", "guardrail"),
    "pattern_action": (
        "same_playbook_kicker",
        "same_playbook_heading",
        "same_playbook_intro",
        "same_playbook_deepen_label",
        "same_playbook_deepen_description",
        "same_playbook_stretch_label",
        "same_playbook_stretch_description",
        "same_playbook_recurring_core_label",
        "same_playbook_familiar_label",
        "same_playbook_changes_label",
        "same_playbook_empty_direction",
        "comfort_edge_kicker",
        "comfort_edge_heading",
        "comfort_edge_intro",
        "comfort_edge_reliability_label",
        "comfort_edge_why_learn_label",
        "comfort_edge_useful_when_label",
        "comfort_edge_enemy_examples_label",
        "comfort_edge_teammate_examples_label",
        "comfort_edge_tradeoff_label",
        "partial_transfer_kicker",
        "partial_transfer_heading",
        "partial_transfer_direct_label",
        "partial_transfer_hypothesis_label",
        "partial_transfer_unresolved_heading",
        "partial_transfer_deep_label",
        "versatile_core_kicker",
        "versatile_core_heading",
        "versatile_core_jobs_label",
        "versatile_core_coverage_label",
        "versatile_core_next_tool_label",
        "versatile_core_alternatives_label",
        "versatile_core_no_gap_heading",
        "proven_flexibility_kicker",
        "proven_flexibility_heading",
        "proven_flexibility_roster_label",
        "proven_flexibility_proof_label",
        "proven_flexibility_distributed_heading",
        "controlled_presence_kicker",
        "controlled_presence_heading",
        "controlled_presence_context_label",
        "controlled_presence_finishing_label",
        "presence_tax_kicker",
        "presence_tax_heading",
        "presence_tax_deep_label",
        "presence_tax_unresolved_body",
        "bounceback_kicker",
        "bounceback_heading",
        "performance_slide_kicker",
        "performance_slide_heading",
        "recovery_context_label",
        "recovery_delta_label",
        "session_fade_kicker",
        "session_fade_heading",
        "session_fade_breakpoint_label",
        "session_fade_gradual_label",
        "session_rise_kicker",
        "session_rise_heading",
        "session_rise_breakpoint_label",
        "session_rise_gradual_label",
    ),
}


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


def resolve_pattern_presentation_copy(
    pattern_key: str,
    outcome_id: str,
    *,
    recommendation_id: str | None = None,
    deep_dive_id: str | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve the complete v5.2 story copy for one finite outcome."""

    catalog = validate_copy_catalog()
    presentation = catalog["presentation"]
    pattern = presentation["patterns"].get(pattern_key)
    contract = PATTERN_PRESENTATION_CONTRACT.get(pattern_key)
    if not isinstance(pattern, dict) or contract is None:
        raise ValueError(f"Unknown Pattern presentation copy key: {pattern_key}")
    outcome = pattern["outcomes"].get(outcome_id)
    if not isinstance(outcome, dict):
        raise ValueError(f"Unknown Pattern outcome copy key: {pattern_key}.{outcome_id}")
    values: dict[str, Any] = {
        "outcome": outcome,
        "recommendation": None,
        "deep_dive": None,
    }
    if recommendation_id is not None:
        recommendation = pattern["recommendations"].get(recommendation_id)
        if not isinstance(recommendation, dict):
            raise ValueError(f"Unknown Pattern recommendation copy key: {pattern_key}.{recommendation_id}")
        values["recommendation"] = recommendation
    if deep_dive_id is not None:
        deep_dive = pattern["deep_dives"].get(deep_dive_id)
        if not isinstance(deep_dive, dict):
            raise ValueError(f"Unknown Pattern deep-dive copy key: {pattern_key}.{deep_dive_id}")
        values["deep_dive"] = deep_dive
    params = params or {}
    fields = {
        field
        for value in values.values()
        for field in _presentation_fields(value)
    }
    allowed = {"hero_name", "match_count", "date_range", "role_name", "session_game_label"}
    if not fields.issubset(allowed):
        raise ValueError(f"Unapproved Pattern presentation placeholders: {sorted(fields - allowed)}")
    missing = fields - set(params)
    extra = set(params) - fields
    if missing:
        raise ValueError(f"Missing Pattern presentation parameters: {sorted(missing)}")
    if extra:
        raise ValueError(f"Unexpected Pattern presentation parameters: {sorted(extra)}")
    resolved = {
        "headline": _render_presentation_value(outcome["headline"], params),
        "subheadline": _render_presentation_value(outcome["subheadline"], params),
        "interpretation": _render_presentation_value(outcome["interpretation"], params),
        "recommendation": (
            _render_presentation_value(values["recommendation"], params)
            if values["recommendation"] is not None
            else None
        ),
        "deep_dive": (
            _render_presentation_value(values["deep_dive"], params)
            if values["deep_dive"] is not None
            else None
        ),
        "fallback": _render_presentation_value(outcome.get("fallback", {}), params),
    }
    if outcome_id != contract["outcome_id"]:
        raise ValueError(f"Outcome {outcome_id} is not registered for Pattern {pattern_key}")
    return resolved


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


def resolve_story_copy(section: str, key: str, **params: str) -> str:
    catalog = validate_copy_catalog()
    templates = catalog["story_templates"].get(section)
    if not isinstance(templates, dict) or not isinstance(templates.get(key), str):
        raise ValueError(f"Unknown Free DNA story template: {section}.{key}")
    template = templates[key]
    fields = {name for _, name, _, _ in Formatter().parse(template) if name}
    missing = fields - set(params)
    extra = set(params) - fields
    if missing:
        raise ValueError(f"Missing story copy parameters: {sorted(missing)}")
    if extra:
        raise ValueError(f"Unexpected story copy parameters: {sorted(extra)}")
    return template.format(**params)


def validate_copy_catalog() -> dict[str, Any]:
    catalog = load_free_dna_copy()
    pages = catalog.get("pages")
    if not isinstance(pages, dict) or set(pages) != set(_PAGE_KEYS):
        raise ValueError("Free DNA copy catalog must cover every active story page family")
    for key in _PAGE_KEYS:
        value = pages[key]
        if not isinstance(value, dict) or not isinstance(value.get("title"), str) or not isinstance(value.get("body"), str):
            raise ValueError(f"Incomplete page copy: {key}")
    element_scan = pages["element_scan"]
    if any(not isinstance(element_scan.get(key), str) for key in ("scanning_body", "ready_body")):
        raise ValueError("Element scan copy must include scanning and ready states")

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
        required: tuple[str, ...] = ("question", "correct", "incorrect", "correct_feedback", "incorrect_feedback", "answer", "reveal", "boundary")
        if key == "exception":
            required = (*required, "no_clear_feedback")
        if not isinstance(value, dict) or any(not isinstance(value.get(item), str) for item in required):
            raise ValueError(f"Incomplete portfolio copy: {key}")
    mirror = portfolio["hero_mirror"]
    if not isinstance(mirror, dict) or any(not isinstance(mirror.get(key), str) for key in ("closed", "available", "unavailable", "qualifier", "guardrail")):
        raise ValueError("Incomplete portfolio copy: hero_mirror")
    evolution = portfolio["evolution"]
    if not isinstance(evolution, dict) or any(not isinstance(evolution.get(key), str) for key in ("question", "check", "unavailable", "locked")):
        raise ValueError("Incomplete portfolio copy: evolution")
    if any(not isinstance(evolution.get(key), str) for key in _EVOLUTION_VARIANTS):
        raise ValueError("Evolution copy must cover every public variant")
    story_templates = catalog.get("story_templates")
    if not isinstance(story_templates, dict) or set(story_templates) != set(_STORY_TEMPLATE_KEYS):
        raise ValueError("Free DNA copy catalog must cover story presentation templates")
    for section, keys in _STORY_TEMPLATE_KEYS.items():
        values = story_templates[section]
        if not isinstance(values, dict) or any(not isinstance(values.get(key), str) for key in keys):
            raise ValueError(f"Incomplete story presentation templates: {section}")
    _lint_forbidden_terms(catalog)
    _validate_presentation_catalog(catalog)
    return catalog


def _validate_presentation_catalog(catalog: dict[str, Any]) -> None:
    presentation = catalog.get("presentation")
    if not isinstance(presentation, dict) or presentation.get("version") != PATTERN_PRESENTATION_VERSION:
        raise ValueError("Free DNA copy catalog must include the v5.2 presentation catalog")
    patterns = presentation.get("patterns")
    if not isinstance(patterns, dict) or set(patterns) != set(EXPECTED_PATTERN_KEYS):
        raise ValueError("Pattern presentation copy must cover every active Pattern")
    required_outcome_keys = {item["outcome_id"] for item in PATTERN_PRESENTATION_CONTRACT.values()}
    for key, contract in PATTERN_PRESENTATION_CONTRACT.items():
        value = patterns[key]
        if not isinstance(value, dict):
            raise ValueError(f"Incomplete Pattern presentation copy: {key}")
        outcomes = value.get("outcomes")
        recommendations = value.get("recommendations")
        deep_dives = value.get("deep_dives")
        if not isinstance(outcomes, dict) or set(outcomes) != {contract["outcome_id"]}:
            raise ValueError(f"Incomplete Pattern outcome copy: {key}")
        if not isinstance(recommendations, dict) or contract["recommendation_id"] not in recommendations:
            raise ValueError(f"Incomplete Pattern recommendation copy: {key}")
        if not isinstance(deep_dives, dict) or contract["deep_dive_id"] not in deep_dives:
            raise ValueError(f"Incomplete Pattern deep-dive copy: {key}")
        outcome = outcomes[contract["outcome_id"]]
        if not isinstance(outcome, dict) or any(
            not isinstance(outcome.get(field), (str, dict))
            for field in ("headline", "subheadline", "interpretation")
        ):
            raise ValueError(f"Incomplete Pattern outcome copy: {key}")
        for section_name, section in (
            ("recommendation", recommendations[contract["recommendation_id"]]),
            ("deep_dive", deep_dives[contract["deep_dive_id"]]),
        ):
            if not isinstance(section, dict) or any(
                not isinstance(section.get(field), str)
                for field in (("eyebrow", "title", "body") if section_name == "recommendation" else ("title", "body"))
            ):
                raise ValueError(f"Incomplete Pattern {section_name} copy: {key}")
    if not required_outcome_keys:
        raise ValueError("Pattern presentation catalog cannot be empty")


def _render_presentation_value(value: Any, params: dict[str, str]) -> Any:
    if isinstance(value, str):
        fields = {name for _, name, _, _ in Formatter().parse(value) if name}
        missing = fields - set(params)
        if missing:
            raise ValueError(f"Missing Pattern presentation parameters: {sorted(missing)}")
        return value.format(**params)
    if isinstance(value, dict):
        return {key: _render_presentation_value(child, params) for key, child in value.items()}
    if isinstance(value, list):
        return [_render_presentation_value(child, params) for child in value]
    return value


def _presentation_fields(value: Any) -> set[str]:
    if isinstance(value, str):
        return {name for _, name, _, _ in Formatter().parse(value) if name}
    if isinstance(value, dict):
        return {field for child in value.values() for field in _presentation_fields(child)}
    if isinstance(value, list):
        return {field for child in value for field in _presentation_fields(child)}
    return set()


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
    templates = [item for item in value.values() if isinstance(item, str)]
    fields = {name for template in templates for _, name, _, _ in Formatter().parse(template) if name}
    missing = fields - set(params)
    extra = set(params) - fields
    if missing:
        raise ValueError(f"Missing copy parameters: {sorted(missing)}")
    if extra:
        raise ValueError(f"Unexpected copy parameters: {sorted(extra)}")
    return {key: item.format(**params) for key, item in value.items() if isinstance(item, str)}


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
    "resolve_pattern_presentation_copy",
    "resolve_portfolio_copy",
    "resolve_story_copy",
    "validate_copy_catalog",
]

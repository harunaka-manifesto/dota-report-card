"""Deterministic dynamic identity synthesis for v6 (no archetype labels)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from .constants import FINDING_FAMILY_KEYS
from .findings import forbidden_inference_violations
from .models import ElementResultV6, FindingFamilyResult, IdentitySummary

_HEADLINES: Mapping[tuple[str, str], str] = {
    ("pool_shape", "positive"): "You make your hero pool do more than one job.",
    ("pool_shape", "negative"): "You keep a clear shape to the jobs you repeat.",
    ("pool_shape", "mixed"): "Your hero pool carries a useful tension between range and repetition.",
    ("transfer", "positive"): "You carry your game beyond familiar heroes.",
    ("transfer", "negative"): "Your strongest expression is clearest in familiar heroes.",
    ("transfer", "mixed"): "Your transfer story changes by signal, not by a single score.",
    ("post_loss_response", "positive"): "A loss changes what you choose in a visible way.",
    ("post_loss_response", "negative"): "Your next choice after a loss often stays close to your established path.",
    ("post_loss_response", "mixed"): "Your post-loss response has more than one observable shape.",
    ("combat_expression", "positive"): "You show up often in the action with lower death exposure in context.",
    ("combat_expression", "negative"): "Your participation and exposure pull in different directions.",
    ("combat_expression", "mixed"): "Your combat expression is a balance of participation and exposure.",
    ("session_drift", "positive"): "Your summary expression holds its shape across sessions.",
    ("session_drift", "negative"): "Your summary expression shifts as sessions run longer.",
    ("session_drift", "mixed"): "Longer sessions reveal more than one expression pattern.",
}

_SUPPORT_LINES: Mapping[str, str] = {
    "pool_shape": "Breadth and toolkit coverage provide the pool evidence.",
    "transfer": "Outcome, activity, and survival are compared as separate signals.",
    "post_loss_response": "The comparison uses observed transitions and comparable context.",
    "combat_expression": "Involvement and death exposure are reported without judging death quality.",
    "session_drift": "Completed sessions provide the time-order context for this finding.",
}


def _map_findings(findings: Sequence[FindingFamilyResult] | Mapping[str, FindingFamilyResult]) -> tuple[FindingFamilyResult, ...]:
    values = tuple(findings.values()) if isinstance(findings, Mapping) else tuple(findings)
    order = {family: index for index, family in enumerate(FINDING_FAMILY_KEYS)}
    return tuple(sorted(values, key=lambda item: (-item.confidence_score, -item.identity_value, order.get(item.family, 999))))


def _anchor_value(hero_portfolio: Mapping[str, Any] | None) -> tuple[str | None, str | None]:
    if not hero_portfolio:
        return None, None
    for key in ("anchor", "common_thread", "hero_anchor", "common_thread_label"):
        value = hero_portfolio.get(key)
        if isinstance(value, Mapping):
            value = value.get("label", value.get("headline", value.get("text")))
        if value:
            text = str(value).strip()
            if text and not forbidden_inference_violations(text):
                return key, text
    return None, None


def synthesize_identity(
    findings: Sequence[FindingFamilyResult] | Mapping[str, FindingFamilyResult],
    *,
    elements: Sequence[ElementResultV6] | Mapping[str, Any] | None = None,
    hero_portfolio: Mapping[str, Any] | None = None,
) -> IdentitySummary:
    """Choose copy through stable family order and evidence, never randomness."""

    ordered = _map_findings(findings)
    eligible = [
        item
        for item in ordered
        if item.status == "qualified" and item.confidence in {"high", "moderate"}
    ]
    if not eligible:
        eligible = [item for item in ordered if item.status == "qualified"]
    anchor_key, anchor = _anchor_value(hero_portfolio)
    if not eligible:
        headline = "Your identity is still forming from this sample."
        fallback_lines = ("More stable evidence will make the identity more specific.",)
        fallback_confidence: Literal["descriptive", "unavailable"] = "descriptive" if ordered else "unavailable"
        return IdentitySummary(headline, fallback_lines, fallback_confidence, (), anchor, (),)

    strongest = eligible[0]
    headline = _HEADLINES.get((strongest.family, strongest.direction), _HEADLINES.get((strongest.family, "mixed"), "Your summary history has a distinct expression."))
    if strongest.confidence == "moderate":
        headline = headline.replace("You ", "You tend to ", 1)
    lines: list[str] = []
    base_line = _SUPPORT_LINES.get(strongest.family)
    if base_line:
        lines.append(base_line)
    second = next((item for item in eligible[1:] if item.family != strongest.family), None)
    if second is not None:
        second_line = _SUPPORT_LINES.get(second.family)
        if second_line:
            lines.append(second_line)
    if anchor:
        lines.append(f"A recurring portfolio thread: {anchor}.")
    # A supplied claim may be used only when it passes the summary-copy guard.
    if strongest.claim and not forbidden_inference_violations(strongest.claim):
        lines.insert(0, strongest.claim)
    evidence_refs = tuple(dict.fromkeys(ref for item in (strongest, second) if item is not None for ref in item.evidence_refs))
    confidence: Literal["high", "moderate"] = "high" if strongest.confidence == "high" else "moderate"
    families = tuple(item.family for item in (strongest, second) if item is not None)
    return IdentitySummary(headline, tuple(lines[:3]), confidence, evidence_refs, anchor, families)


deterministic_identity = synthesize_identity
build_identity_summary = synthesize_identity


__all__ = ["synthesize_identity", "deterministic_identity", "build_identity_summary"]

"""Deterministic dynamic identity synthesis for v6 without fixed labels."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from .constants import FINDING_FAMILY_KEYS
from .copy import forbidden_copy_violations
from .findings import forbidden_inference_violations
from .models import ElementResultV6, FindingFamilyResult, IdentitySummary

_HEADLINES: Mapping[tuple[str, str], str] = {
    ("pool_shape", "broad_names_narrow_jobs"): "Your hero pool covers many names around a narrower set of jobs.",
    ("pool_shape", "focused_names_versatile_jobs"): "Your focused hero set covers more than one functional job.",
    ("pool_shape", "broad_names_versatile_jobs"): "Your hero pool covers many names and functional jobs.",
    ("pool_shape", "focused_names_narrow_jobs"): "Your repeated hero set and jobs have a compact shape.",
    ("pool_shape", "mixed_or_typical"): "Your hero pool has more than one observable shape.",
    ("transfer", "transfers"): "You carry your game beyond familiar heroes.",
    ("transfer", "does_not_transfer"): "Your strongest expression is clearest in familiar heroes.",
    ("transfer", "mixed_transfer"): "Your transfer story changes by signal, not by a single score.",
    ("transfer", "unknown_transfer"): "Your transfer evidence is still forming.",
    ("post_loss_response", "post_loss_shift_positive"): "A loss changes what you choose in a visible way.",
    ("post_loss_response", "post_loss_shift_negative"): "Your next choice after a loss stays close to your established path.",
    ("post_loss_response", "post_loss_shift_mixed"): "Your post-loss response has more than one observable shape.",
    ("post_loss_response", "post_loss_no_clear_shift"): "Your post-loss evidence does not yet show one clear shift.",
    ("combat_expression", "high_involvement_low_exposure"): "Your involvement is high while exposure stays lower in context.",
    ("combat_expression", "high_involvement_high_exposure"): "Your involvement and exposure are both high in context.",
    ("combat_expression", "low_involvement_low_exposure"): "Your involvement and exposure are both lower in context.",
    ("combat_expression", "low_involvement_high_exposure"): "Your involvement is lower while exposure is higher in context.",
    ("combat_expression", "typical_or_mixed"): "Your combat expression is a balance of participation and exposure.",
    ("session_drift", "session_rise"): "Your summary expression rises across completed session positions.",
    ("session_drift", "session_fade"): "Your summary expression shifts across completed session positions.",
    ("session_drift", "session_mixed"): "Completed sessions reveal more than one expression pattern.",
    ("session_drift", "session_no_clear_shift"): "Completed sessions do not yet show one clear shift.",
}

_SUPPORT_LINES: Mapping[str, str] = {
    "pool_shape": "Breadth and toolkit coverage provide the pool evidence.",
    "transfer": "Outcome, activity, and survival are compared as separate signals.",
    "post_loss_response": "The comparison uses observed transitions and comparable context.",
    "combat_expression": "Involvement and exposure remain separate summary signals.",
    "session_drift": "Completed sessions provide the time-order context for this finding.",
}


def _map_findings(findings: Sequence[FindingFamilyResult] | Mapping[str, FindingFamilyResult]) -> tuple[FindingFamilyResult, ...]:
    values = tuple(findings.values()) if isinstance(findings, Mapping) else tuple(findings)
    order = {family: index for index, family in enumerate(FINDING_FAMILY_KEYS)}
    return tuple(sorted(values, key=lambda item: (-item.confidence_score, -item.identity_value, order.get(item.family, 999))))


def _descriptive_element_support(
    elements: Sequence[ElementResultV6] | Mapping[str, Any] | None,
) -> tuple[tuple[ElementResultV6, ...], tuple[str, ...]]:
    if not elements:
        return (), ()
    values = tuple(elements.values()) if isinstance(elements, Mapping) else tuple(elements)
    available = tuple(
        item
        for item in values
        if isinstance(item, ElementResultV6)
        and item.status in {"available", "limited"}
        and item.confidence != "unavailable"
    )
    refs = tuple(
        dict.fromkeys(
            ref
            for item in available
            for ref in (item.evidence_refs or item.estimate.evidence_refs)
        )
    )
    return available, refs


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
        descriptive_elements, element_refs = _descriptive_element_support(elements)
        if len(descriptive_elements) >= 3 and element_refs:
            labels = ", ".join(item.label for item in descriptive_elements[:3])
            return IdentitySummary(
                "Your identity is still forming across the available summary elements.",
                (f"{labels} provide the current descriptive evidence.",),
                "descriptive",
                element_refs,
                anchor,
                (),
            )
        headline = "Your identity is still forming from this sample."
        fallback_lines = ("More stable evidence will make the identity more specific.",)
        fallback_confidence: Literal["descriptive", "unavailable"] = "descriptive" if ordered else "unavailable"
        return IdentitySummary(headline, fallback_lines, fallback_confidence, (), anchor, (),)

    strongest = eligible[0]
    headline = _HEADLINES.get((strongest.family, strongest.outcome_key), "Your summary history has a distinct expression.")
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
    public_text = {"headline": headline, "supporting_lines": lines[:3]}
    if forbidden_copy_violations(public_text):
        return IdentitySummary(
            "Your identity is still forming from this sample.",
            ("More stable evidence will make the identity more specific.",),
            "descriptive",
            evidence_refs,
            anchor,
            families,
        )
    return IdentitySummary(headline, tuple(lines[:3]), confidence, evidence_refs, anchor, families)


deterministic_identity = synthesize_identity
build_identity_summary = synthesize_identity


__all__ = ["synthesize_identity", "deterministic_identity", "build_identity_summary"]

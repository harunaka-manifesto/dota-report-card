"""Typed PRIMARY/TWIST/ANCHOR identity composition for V6.1."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def compose_identity_slots(
    identity_summary: Mapping[str, Any],
    findings: Sequence[Mapping[str, Any]],
    hero_portfolio: Mapping[str, Any],
    portfolio_shape: Mapping[str, Any],
) -> dict[str, Any]:
    thirds = portfolio_shape.get("chronological_thirds", [])
    stable_thirds = sum(
        isinstance(third, Mapping) and int(third.get("match_count", 0)) >= 10
        for third in thirds
    )
    refs = list(identity_summary.get("evidence_refs", []))
    primary = None
    if (
        stable_thirds >= 2
        and identity_summary.get("confidence") in {"moderate", "high"}
        and str(identity_summary.get("headline", "")).strip()
    ):
        primary = {
            "kind": "PRIMARY",
            "scope": "This year",
            "text": str(identity_summary["headline"]),
            "evidence_refs": refs,
            "stability": {"qualified_chronological_thirds": stable_thirds},
        }
    published = [
        finding
        for finding in findings
        if finding.get("published")
        and finding.get("confidence") in {"moderate", "high"}
        and str(finding.get("claim_contract", {}).get("claim") or "").strip()
    ]
    twist = None
    if published:
        finding = published[0]
        family = str(finding.get("family", ""))
        scope = {
            "post_loss_response": "After a result",
            "session_drift": "In longer sessions",
        }.get(family, "Within supported contexts")
        twist = {
            "kind": "TWIST",
            "scope": scope,
            "text": finding.get("claim_contract", {}).get("claim"),
            "family": family,
            "semantic_outcome_key": finding.get("semantic_outcome_key"),
            "evidence_refs": list(finding.get("evidence_refs", [])),
        }
    anchor_text = hero_portfolio.get("anchor") or hero_portfolio.get("common_thread")
    if not anchor_text:
        core = portfolio_shape.get("stable_core_hero_ids") or portfolio_shape.get("core_hero_ids")
        anchor_text = f"Stable core: {', '.join(map(str, core[:3]))}" if core else None
    anchor = (
        {
            "kind": "ANCHOR",
            "scope": "Observed annual core",
            "text": str(anchor_text),
            "evidence_refs": ["supporting:portfolio_shape"],
        }
        if anchor_text
        else None
    )
    return {
        "version": "identity-slots-1.0.0",
        "primary": primary,
        "twist": twist,
        "anchor": anchor,
        "compatibility": "identity-slot-compatibility-1.0.0",
        "compatibility_checks": {
            "primary_stability_gate": primary is None or stable_thirds >= 2,
            "twist_qualified_only": twist is None or bool(published),
            "anchor_portfolio_owned": anchor is None
            or anchor["evidence_refs"] == ["supporting:portfolio_shape"],
        },
    }


__all__ = ["compose_identity_slots"]

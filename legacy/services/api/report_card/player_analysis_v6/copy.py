"""Deterministic, reviewable semantic copy for Free DNA v6.

This module is deliberately small.  It turns already-computed evidence into
bounded copy and structured recommendation records; it never asks a model to
invent a public claim.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .constants import FORBIDDEN_FREE_TERMS, SEMANTIC_COPY_VERSION


def forbidden_copy_terms(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    lowered = value.casefold()
    return tuple(term for term in FORBIDDEN_FREE_TERMS if term in lowered)


def forbidden_copy_violations(value: Any) -> tuple[str, ...]:
    """Scan a nested public payload without treating structured keys as copy."""

    if isinstance(value, str):
        return forbidden_copy_terms(value)
    if isinstance(value, Mapping):
        return tuple(dict.fromkeys(term for child in value.values() for term in forbidden_copy_violations(child)))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(dict.fromkeys(term for child in value for term in forbidden_copy_violations(child)))
    return ()


def safe_copy(value: str | None) -> str | None:
    if value is None or forbidden_copy_terms(value):
        return None
    return value


def claim_contract(
    *,
    claim: str | None = None,
    evidence: str | None = None,
    interpretation: str | None = None,
    recommendation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return nullable public layers with the v6 semantic-copy version."""

    return {
        "claim": safe_copy(claim),
        "evidence": safe_copy(evidence),
        "interpretation": safe_copy(interpretation),
        "recommendation": dict(recommendation) if recommendation is not None else None,
        "copy_version": SEMANTIC_COPY_VERSION,
    }


def family_copy(
    family: str,
    *,
    direction: str,
    evidence_labels: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    recommendation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build conservative copy from a finite family/direction vocabulary."""

    labels = tuple(str(item) for item in evidence_labels if str(item).strip())
    evidence_text = ", ".join(labels) if labels else None
    claim_templates = {
        "pool_shape": {
            "positive": "Your hero choices cover a wider set of repeatable jobs.",
            "negative": "Your hero choices keep a narrower, more repeated job shape.",
            "mixed": "Your hero-pool width and job coverage do not move as one signal.",
        },
        "transfer": {
            "positive": "Several summary signals carry from familiar choices into stretch choices.",
            "negative": "Several summary signals are clearer in familiar choices than in stretch choices.",
            "mixed": "Transfer differs by signal: outcome, activity, and survival do not agree.",
        },
        "post_loss_response": {
            "positive": "The next choice after a loss changes in the observed sample.",
            "negative": "The next choice after a loss stays close to the established sample pattern.",
            "mixed": "The next choice after a loss changes in some observed signals and not others.",
        },
        "combat_expression": {
            "positive": "Participation and exposure move together in the supported sample.",
            "negative": "Participation and exposure pull in different directions in the supported sample.",
            "mixed": "Participation and exposure do not resolve to one supported direction.",
        },
        "session_drift": {
            "positive": "The measured expression rises between earlier and later session positions.",
            "negative": "The measured expression fades between earlier and later session positions.",
            "mixed": "Completed sessions show more than one direction of change.",
        },
    }
    family_templates = claim_templates.get(family, {})
    claim = family_templates.get(direction) or family_templates.get("mixed")
    interpretation = (
        "This is a summary-history association with the listed evidence; it does not establish cause."
        if claim
        else None
    )
    return {
        **claim_contract(
            claim=claim,
            evidence=evidence_text,
            interpretation=interpretation,
            recommendation=recommendation,
        ),
        "evidence_refs": list(dict.fromkeys(str(item) for item in evidence_refs)),
    }


__all__ = ["forbidden_copy_terms", "forbidden_copy_violations", "safe_copy", "claim_contract", "family_copy"]

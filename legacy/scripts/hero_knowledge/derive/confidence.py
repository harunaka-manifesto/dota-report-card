"""Confidence labels for source completeness and empirical sample context."""

from __future__ import annotations

from typing import Any

from .. import BEHAVIOR_RULE_VERSION


def source_confidence(
    *,
    valve: dict[str, Any] | None,
    opendota: dict[str, Any] | None,
    valve_plus: dict[str, Any] | None = None,
    minimum_matches: int = 20,
) -> dict[str, Any]:
    evidence: list[str] = []
    if valve:
        evidence.append("valve:mechanics")
    if opendota:
        evidence.append("opendota:aggregate")
    if valve_plus and valve_plus.get("status") in {"available", "partial"}:
        evidence.append("valve_plus:optional")
    if valve and opendota:
        samples = [
            int(row.get("picks") or 0)
            for row in opendota.get("bracket_performance", [])
            if isinstance(row, dict) and row.get("population") == "public_aggregate"
        ]
        band = "high" if sum(samples) >= minimum_matches else "moderate"
    elif valve:
        band = "moderate"
    elif opendota:
        total = sum(
            int(row.get("picks") or 0)
            for row in opendota.get("bracket_performance", [])
            if isinstance(row, dict) and row.get("population") == "public_aggregate"
        )
        band = "moderate" if total >= minimum_matches else "low"
    else:
        band = "unknown"
    return {
        "band": band,
        "derived_from": evidence,
        "rule_version": BEHAVIOR_RULE_VERSION,
        "sample_requirement": minimum_matches,
    }

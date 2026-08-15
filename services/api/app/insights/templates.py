from __future__ import annotations

from app.insights.models import EvidenceObject


def render_statement(evidence: EvidenceObject) -> str:
    player_value = _format_value(evidence.player.get("value"), evidence.unit)
    cohort_value = (
        _format_value(evidence.cohort.get("value"), evidence.unit)
        if evidence.cohort and evidence.cohort.get("value") is not None
        else None
    )
    if cohort_value:
        return f"{evidence.concept_id.replace('_', ' ').capitalize()}: {player_value} versus {cohort_value}."
    return f"{evidence.concept_id.replace('_', ' ').capitalize()}: {player_value}."


def render_action(evidence: EvidenceObject) -> str:
    return str(
        evidence.action.get("behavior") or "Use this evidence to choose one repeatable behavior."
    )


def _format_value(value: object, unit: str) -> str:
    if value is None:
        return "not available"
    if not isinstance(value, (int, float)):
        return str(value)
    if unit in {"rate", "win rate"}:
        return f"{float(value) * 100:.0f}%"
    if unit == "entropy":
        return f"{float(value):.2f} bits"
    if unit in {"ratio", "efficiency"}:
        return f"{float(value):.4f}"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)

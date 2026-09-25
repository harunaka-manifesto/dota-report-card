"""Structured, deterministic Free DNA v6 recommendations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

RECOMMENDATION_VERSION = "free-dna-recommendations-6.0.0"

_CATALOG: Mapping[str, tuple[str, str, str]] = {
    "pool_shape": (
        "REC_POOL_SHAPE_REVIEW",
        "Review one repeated job before adding another hero.",
        "Choose one job represented by the pool evidence and review five matches for that job.",
    ),
    "transfer": (
        "REC_TRANSFER_COMPARE",
        "Compare one familiar choice with one stretch choice.",
        "Commit to five matches while holding the comparison context constant.",
    ),
    "post_loss_response": (
        "REC_POST_LOSS_OBSERVE",
        "Observe the next choice after a loss.",
        "For the next five qualifying transitions, record the next choice before changing your plan.",
    ),
    "combat_expression": (
        "REC_COMBAT_EXPRESSION_REVIEW",
        "Review participation and exposure together.",
        "Compare the two displayed signals across five qualifying matches.",
    ),
    "session_drift": (
        "REC_SESSION_DRIFT_CHECK",
        "Check the first and later parts of a completed session.",
        "Use five qualifying matches to compare the two session positions.",
    ),
}

_FOLLOW_UP_METRIC: Mapping[str, str] = {
    "pool_shape": "core_hero_share",
    "transfer": "win_rate",
    "post_loss_response": "win_rate",
    "combat_expression": "involvement_per_minute",
    "session_drift": "win_rate",
}

_BEHAVIOR_CHANGE_FAMILIES = frozenset({"combat_expression", "post_loss_response", "session_drift"})


def structured_recommendation(
    family: str,
    *,
    evidence_refs: Sequence[str] = (),
    supported_metric_keys: Sequence[str] = (),
    context: Mapping[str, Any] | None = None,
    baseline_value: float | None = None,
) -> dict[str, Any] | None:
    item = _CATALOG.get(family)
    if item is None:
        return None
    recommendation_id, title, instruction = item
    metric = _FOLLOW_UP_METRIC[family]
    context_value = dict(context or {})
    return {
        "recommendation_id": recommendation_id,
        "id": recommendation_id,
        "title": title,
        "label": title,
        "instruction": instruction,
        "action": instruction,
        "body": instruction,
        "rationale": "Selected from independently supported summary metrics.",
        "evidence_requirement": "Use the first five qualifying summary matches in the declared context.",
        "verification_rule": "Compare the predeclared baseline with those five matches.",
        "family": family,
        "supported_metric_keys": [metric],
        "evidence_refs": list(dict.fromkeys(str(ref) for ref in evidence_refs)),
        "context": context_value,
        "metric": metric,
        "baseline_value": baseline_value,
        "follow_up": {
            "metric": metric,
            "baseline_value": baseline_value,
            "context": context_value,
            "direction": "observe",
            "target_games": 5,
        },
        "causal": False,
        "identity_updated": False,
        "baseline_locked_on_commit": True,
        "version": RECOMMENDATION_VERSION,
    }


def recommendation_for_family(
    family: str,
    *,
    status: str,
    confidence: str,
    published: bool,
    evidence_refs: Sequence[str] = (),
    supported_metric_keys: Sequence[str] = (),
) -> dict[str, Any] | None:
    if status != "qualified" or not published or confidence not in {"moderate", "high"}:
        return None
    if family in _BEHAVIOR_CHANGE_FAMILIES and confidence != "high":
        return None
    return structured_recommendation(
        family,
        evidence_refs=evidence_refs,
        supported_metric_keys=supported_metric_keys,
    )


def bind_recommendation_baselines(
    findings: Sequence[Any],
    matches: Sequence[Any],
) -> tuple[Any, ...]:
    """Attach a report-time, server-derived five-game baseline to each rec."""

    from collections import Counter
    from dataclasses import replace

    def row_get(row: Any, key: str, default: Any = None) -> Any:
        value = row.get(key) if isinstance(row, Mapping) else getattr(row, key, None)
        if value is not None:
            return value
        target = row.get("target_participant") if isinstance(row, Mapping) else getattr(row, "target_participant", None)
        if target is not None:
            nested = target.get(key) if isinstance(target, Mapping) else getattr(target, key, None)
            if nested is not None:
                return nested
        return default

    def value(row: Any, metric: str) -> float | None:
        if metric == "win_rate":
            raw = row_get(row, "won", row_get(row, "win", row_get(row, "radiant_win")))
            return float(bool(raw)) if raw is not None else None
        if metric == "involvement_per_minute":
            duration = row_get(row, "duration_seconds", row_get(row, "duration"))
            if duration in (None, 0):
                return None
            return (float(row_get(row, "kills", 0) or 0) + float(row_get(row, "assists", 0) or 0)) / (float(duration) / 60.0)
        return None

    def baseline(family: str, metric: str) -> tuple[float | None, dict[str, Any]]:
        context: dict[str, Any] = {}
        if family in {"pool_shape", "transfer"}:
            counts = Counter(row_get(row, "hero_id") for row in matches if row_get(row, "hero_id") is not None)
            ordered = sorted(counts, key=lambda hero: (-counts[hero], repr(hero)))
            target = max(1, sum(counts.values()) * 0.60)
            core_ids: list[Any] = []
            running = 0
            for hero in ordered:
                core_ids.append(hero)
                running += counts[hero]
                if running >= target:
                    break
            context["core_hero_ids"] = core_ids
            context["stretch_hero_ids"] = [hero for hero in counts if hero not in core_ids]
            total = sum(counts.values())
            if family == "pool_shape":
                return ((sum(count for hero, count in counts.items() if hero in core_ids) / total) if total else None), context
            core_values = [result for row in matches if row_get(row, "hero_id") in core_ids if (result := value(row, metric)) is not None]
            return (sum(core_values) / len(core_values) if core_values else None), context
        values = [result for row in matches if (result := value(row, metric)) is not None]
        return (sum(values) / len(values) if values else None), context

    result: list[Any] = []
    for finding in findings:
        recommendation = finding.recommendation
        if not isinstance(recommendation, Mapping):
            result.append(finding)
            continue
        follow_up_source = recommendation.get("follow_up")
        metric = str(recommendation.get("metric") or (follow_up_source.get("metric") if isinstance(follow_up_source, Mapping) else None) or "win_rate")
        baseline_value, context = baseline(finding.family, metric)
        existing_context = recommendation.get("context")
        merged_context = {**(existing_context if isinstance(existing_context, Mapping) else {}), **context}
        follow_up = {
            **(follow_up_source if isinstance(follow_up_source, Mapping) else {}),
            "metric": metric,
            "baseline_value": baseline_value,
            "context": merged_context,
            "direction": "observe",
            "target_games": 5,
        }
        result.append(replace(finding, recommendation={**dict(recommendation), "metric": metric, "baseline_value": baseline_value, "context": merged_context, "follow_up": follow_up}))
    return tuple(result)


__all__ = ["RECOMMENDATION_VERSION", "structured_recommendation", "recommendation_for_family", "bind_recommendation_baselines"]

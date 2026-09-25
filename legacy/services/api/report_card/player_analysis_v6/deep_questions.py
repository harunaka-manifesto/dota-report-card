"""Full, immutable diagnostic question specifications offered by Free v6."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from .constants import DIAGNOSTICS_VERSION

_QUESTIONS: Mapping[str, Mapping[str, Any]] = {
    "pool_shape": {
        "statement": "Which part of your hero pool creates the most reusable toolkit?",
        "context": {"comparison": "hero_pool_to_functional_jobs", "causal": False},
        "required_summary_metrics": ["hero_id", "won", "duration_seconds", "kills", "assists", "deaths"],
        "required_detail_metrics": [],
        "required_parse_metrics": [],
        "primary_hypothesis": {
            "hypothesis_id": "v6-pool-shape-primary",
            "statement": "The established pool's job coverage differs from its observed outcome mix.",
            "explanation_type": "functional_job_reuse",
            "required_data_families": ["summary", "role", "hero_pool"],
            "positive_definition": {"name": "hero", "params": {}},
            "negative_definition": {"name": "non_hero_same_role", "params": {}},
            "control_definition": {"name": "duration_bucket", "params": {"bucket": "medium"}},
            "min_positive": 3, "min_negative": 3, "min_control": 3,
            "target_positive": 5, "target_negative": 5, "target_control": 5,
            "confounders_to_control": ["duration_bucket"],
        },
    },
    "transfer": {
        "statement": "What changes when you leave familiar heroes?",
        "context": {"comparison": "established_heroes_to_stretch_heroes", "causal": False},
        "required_summary_metrics": ["hero_id", "won", "duration_seconds", "kills", "assists", "deaths"],
        "required_detail_metrics": ["match_context"],
        "required_parse_metrics": ["events"],
        "primary_hypothesis": {
            "hypothesis_id": "v6-transfer-primary",
            "statement": "Outcome, activity, and survival change differently between familiar and stretch choices.",
            "explanation_type": "core_to_stretch_transfer",
            "required_data_families": ["summary", "role", "economy", "events"],
            "positive_definition": {"name": "hero", "params": {}},
            "negative_definition": {"name": "non_hero_same_role", "params": {}},
            "control_definition": {"name": "duration_bucket", "params": {"bucket": "medium"}},
            "min_positive": 3, "min_negative": 3, "min_control": 3,
            "target_positive": 8, "target_negative": 8, "target_control": 8,
            "confounders_to_control": ["duration_bucket", "lane_context"],
        },
        "secondary_hypothesis": {
            "hypothesis_id": "v6-transfer-secondary",
            "statement": "The transfer difference remains visible after controlling for session position.",
            "explanation_type": "session_position_reuse",
            "required_data_families": ["summary", "role", "events"],
            "positive_definition": {"name": "session_position_and_outcome", "params": {"operator": ">=", "value": 1, "won": True}},
            "negative_definition": {"name": "session_position_and_outcome", "params": {"operator": ">=", "value": 1, "won": False}},
            "control_definition": {"name": "session_position", "params": {"operator": "<=", "value": 0}},
            "min_positive": 3, "min_negative": 3, "min_control": 3,
            "target_positive": 5, "target_negative": 5, "target_control": 5,
            "confounders_to_control": ["session_position"],
        },
        "secondary_reuse_fraction": 0.5,
    },
    "post_loss_response": {
        "statement": "How does your next game differ after a loss?",
        "context": {"comparison": "post_loss_transition_to_non_post_loss", "causal": False},
        "required_summary_metrics": ["won", "hero_id", "duration_seconds", "kills", "assists", "deaths", "session_id"],
        "required_detail_metrics": ["match_context"],
        "required_parse_metrics": [],
        "primary_hypothesis": {
            "hypothesis_id": "v6-post-loss-primary",
            "statement": "The next observed match after a loss differs in at least two summary signals.",
            "explanation_type": "same_session_post_loss_transition",
            "required_data_families": ["summary", "role", "events"],
            "positive_definition": {"name": "outcome", "params": {"won": True}},
            "negative_definition": {"name": "outcome", "params": {"won": False}},
            "control_definition": {"name": "duration_bucket", "params": {"bucket": "medium"}},
            "min_positive": 5, "min_negative": 5, "min_control": 5,
            "target_positive": 10, "target_negative": 10, "target_control": 10,
            "confounders_to_control": ["patch", "lane_context", "hero_function"],
        },
    },
    "combat_expression": {
        "statement": "Where do participation and exposure diverge?",
        "context": {"comparison": "involvement_to_death_exposure", "causal": False},
        "required_summary_metrics": ["kills", "assists", "deaths", "duration_seconds", "won"],
        "required_detail_metrics": [],
        "required_parse_metrics": ["events"],
        "primary_hypothesis": {
            "hypothesis_id": "v6-combat-expression-primary",
            "statement": "Participation and exposure show a stable two-signal relationship in the sample.",
            "explanation_type": "participation_exposure_quadrant",
            "required_data_families": ["summary", "role", "events"],
            "positive_definition": {"name": "outcome", "params": {"won": True}},
            "negative_definition": {"name": "outcome", "params": {"won": False}},
            "control_definition": {"name": "duration_bucket", "params": {"bucket": "medium"}},
            "min_positive": 5, "min_negative": 5, "min_control": 5,
            "target_positive": 10, "target_negative": 10, "target_control": 10,
            "confounders_to_control": ["duration_bucket"],
        },
    },
    "session_drift": {
        "statement": "What changes as a play session gets longer?",
        "context": {"comparison": "early_completed_session_to_late_completed_session", "causal": False},
        "required_summary_metrics": ["session_id", "won", "kills", "assists", "deaths", "duration_seconds"],
        "required_detail_metrics": [],
        "required_parse_metrics": [],
        "primary_hypothesis": {
            "hypothesis_id": "v6-session-drift-primary",
            "statement": "Later completed-session matches differ from earlier matches in at least two signals.",
            "explanation_type": "session_position_shift",
            "required_data_families": ["summary", "events", "economy"],
            "positive_definition": {"name": "session_position_and_outcome", "params": {"operator": ">=", "value": 1, "won": True}},
            "negative_definition": {"name": "session_position_and_outcome", "params": {"operator": "<=", "value": 0, "won": False}},
            "control_definition": {"name": "duration_bucket", "params": {"bucket": "medium"}},
            "min_positive": 5, "min_negative": 5, "min_control": 5,
            "target_positive": 10, "target_negative": 10, "target_control": 10,
            "confounders_to_control": ["duration_bucket"],
        },
    },
}


def question_spec(
    family: str,
    question_id: str | None = None,
    *,
    evidence_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    raw = _QUESTIONS.get(family)
    if raw is None:
        raise KeyError(f"unknown v6 diagnostic family: {family}")
    result = deepcopy(dict(raw))
    result["diagnostic_question_id"] = question_id or f"deep-v6-{family}"
    result["family"] = family
    result["version"] = DIAGNOSTICS_VERSION
    result["required_data_families"] = list(result["primary_hypothesis"].get("required_data_families", ()))
    context = dict(evidence_context or {})
    core_ids = tuple(context.get("core_hero_ids", ()))
    stretch_ids = tuple(context.get("stretch_hero_ids", ()))
    lane_context = context.get("lane_context")
    primary = result["primary_hypothesis"]
    if family == "pool_shape":
        dominant_ids = tuple(context.get("dominant_job_hero_ids", ())) or core_ids
        if not dominant_ids:
            raise ValueError("pool-shape Deep requires source hero evidence")
        primary["positive_definition"] = {"name": "hero_set", "params": {"hero_ids": list(dominant_ids)}}
        primary["negative_definition"] = {"name": "outside_hero_set", "params": {"hero_ids": list(dominant_ids)}}
        primary["control_definition"] = {"name": "hero_set_lane", "params": {"hero_ids": list(core_ids or dominant_ids), "lane_context": lane_context}}
    elif family == "transfer":
        if not core_ids or not stretch_ids:
            raise ValueError("transfer Deep requires source core and stretch hero evidence")
        positive_ids = stretch_ids if context.get("direction") != "negative" else core_ids
        negative_ids = core_ids if context.get("direction") != "negative" else stretch_ids
        primary["positive_definition"] = {"name": "hero_set", "params": {"hero_ids": list(positive_ids)}}
        primary["negative_definition"] = {"name": "hero_set", "params": {"hero_ids": list(negative_ids)}}
        primary["control_definition"] = {"name": "hero_set_lane", "params": {"hero_ids": list(core_ids), "lane_context": lane_context}}
    elif family == "post_loss_response":
        transition_ids = tuple(context.get("post_loss_match_ids", ()))
        if not transition_ids or not core_ids:
            raise ValueError("post-loss Deep requires source transition and hero evidence")
        primary["positive_definition"] = {"name": "post_loss_transition", "params": {"match_ids": list(transition_ids)}}
        primary["negative_definition"] = {"name": "outside_match_id_set", "params": {"match_ids": list(transition_ids)}}
        primary["control_definition"] = {"name": "hero_set_lane", "params": {"hero_ids": list(core_ids), "lane_context": lane_context}}
    elif family == "combat_expression":
        quadrant = context.get("combat_quadrant")
        if not isinstance(quadrant, Mapping):
            raise ValueError("combat Deep requires source expression evidence")
        if quadrant.get("involvement_zone") not in {"high", "low"} or quadrant.get("exposure_zone") not in {"high", "low"}:
            raise ValueError("combat Deep requires two non-typical source expression zones")
        positive = {"name": "expression_quadrant", "params": dict(quadrant)}
        negative_params = dict(quadrant)
        negative_params["involvement_zone"] = "low" if quadrant["involvement_zone"] == "high" else "high"
        negative_params["exposure_zone"] = "low" if quadrant["exposure_zone"] == "high" else "high"
        control_params = dict(quadrant)
        control_params["involvement_zone"] = "typical"
        control_params["exposure_zone"] = "typical"
        control_params["typical_band"] = max(
            0.01,
            float(quadrant.get("typical_band", 0.0)),
        )
        control_params["involvement_typical_band"] = max(
            0.01,
            float(quadrant.get("involvement_typical_band", quadrant.get("typical_band", 0.0))),
        )
        control_params["exposure_typical_band"] = max(
            0.01,
            float(quadrant.get("exposure_typical_band", quadrant.get("typical_band", 0.0))),
        )
        primary["positive_definition"] = positive
        primary["negative_definition"] = {"name": "expression_quadrant", "params": negative_params}
        primary["control_definition"] = {"name": "expression_quadrant", "params": control_params}
    elif family == "session_drift":
        if not context.get("session_ids"):
            raise ValueError("session-drift Deep requires completed session evidence")
        primary["positive_definition"] = {"name": "session_position_range", "params": {"min": 3}}
        primary["negative_definition"] = {"name": "session_position_range", "params": {"min": 1, "max": 2}}
        primary["control_definition"] = {"name": "duration_bucket", "params": {"bucket": "medium"}}
    return result


def all_question_specs() -> Mapping[str, Mapping[str, Any]]:
    return {family: question_spec(family) for family in _QUESTIONS}


__all__ = ["question_spec", "all_question_specs", "DIAGNOSTICS_VERSION"]

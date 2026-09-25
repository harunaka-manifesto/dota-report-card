from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateAnalysisRequest(BaseModel):
    player: str = Field(min_length=1, max_length=300)
    refresh: bool = False
    mode: Literal["free"] = "free"


class CreateAnalysisResponse(BaseModel):
    job_id: str
    status: str
    analysis_mode: str = "free"
    reused: bool
    events_url: str


class AnalysisStatusResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_id: str
    account_id: int
    analysis_mode: Literal["free", "deep_scan"] = "free"
    status: str
    stage: str
    processed_matches: int
    eligible_matches: int
    warnings: list[str]
    failure_code: str | None
    message: str | None
    report_id: str | None
    events_url: str
    completed_stages: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    code: str
    message: str


class HealthResponse(BaseModel):
    status: str
    api: str
    postgres: str
    redis: str
    worker: str
    artifacts: str
    auth: str
    source: str


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insight_id: str
    publication_status: str
    confidence: str
    payload: dict[str, Any] = Field(default_factory=dict)


INTERACTION_STATE_SCHEMA_VERSION = "report-interactions-1.0.0"
MAX_INTERACTION_STATE_BYTES = 64 * 1024
MAX_INTERACTION_STATE_DEPTH = 8
MAX_INTERACTION_BASELINE_BYTES = 8 * 1024


class InteractionSessionCreateRequest(BaseModel):
    """Initial state accepted by the resumable report story.

    The client may submit only user-owned state. Server-owned baseline and
    history-cutoff fields are intentionally absent from this request model.
    """

    model_config = ConfigDict(extra="forbid")

    state: dict[str, Any] | None = None
    initial_state: dict[str, Any] | None = None
    user_reported: dict[str, Any] | None = None
    state_schema_version: str | None = None


class InteractionSessionPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: dict[str, Any] | None = None
    user_reported: dict[str, Any] | None = None
    state_schema_version: str | None = None


class FollowUpRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    # The endpoint is intentionally useful with an empty body.  These fields
    # are optional extensions for clients that want to ask for a context view.
    context: dict[str, Any] | None = None


class InteractionSessionResponse(BaseModel):
    session_id: str
    report_id: str
    state_schema_version: str
    revision: int
    state: dict[str, Any]
    recommendation_baseline: dict[str, Any]
    history_cutoff: int | None
    created_at: str
    updated_at: str
    expires_at: str


class InteractionSessionCreatedResponse(InteractionSessionResponse):
    access_token: str


class DeepAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    diagnostic_question_id: str = Field(min_length=1, max_length=128)
    interaction_session_id: str | None = Field(default=None, min_length=1, max_length=36)
    interaction_session: str | None = Field(default=None, min_length=1, max_length=36)
    interaction_session_ref: str | None = Field(default=None, min_length=1, max_length=36)


class DeepAnalysisResponse(BaseModel):
    job_id: str
    analysis_job_id: str | None = None
    status: str
    analysis_mode: str = "deep_scan"
    parent_report_id: str
    diagnostic_question_id: str
    entitlement_decision: dict[str, Any]
    selection_plan: dict[str, Any]
    stopping_reason: str
    events_url: str


def normalize_interaction_state(payload: InteractionSessionCreateRequest) -> dict[str, Any]:
    """Normalize wrapped and additive request forms into a user-owned state."""

    if payload.state is not None:
        state = dict(payload.state)
        if payload.user_reported is not None and "user_reported" not in state:
            state["user_reported"] = dict(payload.user_reported)
    elif payload.initial_state is not None:
        state = dict(payload.initial_state)
        if payload.user_reported is not None and "user_reported" not in state:
            state["user_reported"] = dict(payload.user_reported)
    else:
        extras = payload.model_extra or {}
        known = {"state", "initial_state", "user_reported", "state_schema_version"}
        state = {
            key: value
            for key, value in extras.items()
            if key not in known
        }
        if payload.user_reported is not None:
            state["user_reported"] = dict(payload.user_reported)
    return validate_interaction_state(state)


def normalize_interaction_patch(payload: InteractionSessionPatchRequest) -> dict[str, Any]:
    if payload.state is not None:
        return validate_interaction_state(dict(payload.state))
    known = {"state", "user_reported", "state_schema_version"}
    extras = payload.model_extra or {}
    state = {key: value for key, value in extras.items() if key not in known}
    if payload.user_reported is not None:
        state["user_reported"] = dict(payload.user_reported)
    return validate_interaction_state(state)


def validate_interaction_state(state: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise ValueError("Interaction state must be an object")
    forbidden = {"observed", "computed", "evidence", "analytical_truth", "recommendation_baseline", "baseline"}
    if _contains_forbidden_namespace(state, forbidden):
        raise ValueError("Computed and evidence state is server-owned")
    try:
        encoded = json.dumps(state, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("Interaction state must contain JSON values") from exc
    if len(encoded.encode("utf-8")) > MAX_INTERACTION_STATE_BYTES:
        raise ValueError("Interaction state is too large")
    if _json_depth(state) > MAX_INTERACTION_STATE_DEPTH:
        raise ValueError("Interaction state is too deeply nested")
    return state


def validate_recommendation_baseline(value: dict[str, Any] | None) -> dict[str, Any]:
    baseline = dict(value or {})
    try:
        encoded = json.dumps(baseline, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("Recommendation baseline must contain JSON values") from exc
    if len(encoded.encode("utf-8")) > MAX_INTERACTION_BASELINE_BYTES:
        raise ValueError("Recommendation baseline is too large")
    if _json_depth(baseline) > MAX_INTERACTION_STATE_DEPTH:
        raise ValueError("Recommendation baseline is too deeply nested")
    return baseline


def _json_depth(value: Any, current: int = 0) -> int:
    if isinstance(value, dict):
        return max(((_json_depth(item, current + 1)) for item in value.values()), default=current)
    if isinstance(value, list):
        return max((_json_depth(item, current + 1) for item in value), default=current)
    return current


def _contains_forbidden_namespace(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        return any(key in forbidden or _contains_forbidden_namespace(item, forbidden) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_forbidden_namespace(item, forbidden) for item in value)
    return False

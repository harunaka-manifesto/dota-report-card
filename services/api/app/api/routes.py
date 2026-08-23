from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, NoReturn

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from app.api.schemas import (
    AnalysisStatusResponse,
    CreateAnalysisRequest,
    CreateAnalysisResponse,
    DeepAnalysisRequest,
    DeepAnalysisResponse,
    FollowUpRequest,
    HealthResponse,
    InteractionSessionCreatedResponse,
    InteractionSessionCreateRequest,
    InteractionSessionPatchRequest,
    InteractionSessionResponse,
    normalize_interaction_patch,
    normalize_interaction_state,
    validate_recommendation_baseline,
)
from app.core.errors import AnalysisNotFound, AnalysisRateLimited, AppError, ReportNotFound
from app.core.metrics import record_metric
from app.core.security import RateLimiter, parse_player_identifier
from app.share.service import RENDERER_VERSION, build_share_svg
from app.storage.repository import (
    InteractionRevisionConflict,
    InteractionSessionExpired,
    InteractionSessionNotFound,
    InteractionSessionUnauthorized,
)

router = APIRouter(prefix="/v1")
_rate_limiter = RateLimiter()


def _service(request: Request) -> Any:
    return request.app.state.analysis_service


class _InteractionApiError(AppError):
    def __init__(self, code: str, status_code: int, message: str) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def _interaction_error(code: str, status_code: int, message: str) -> NoReturn:
    raise _InteractionApiError(code, status_code, message)


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        _interaction_error(
            "INTERACTION_AUTH_REQUIRED", 401, "Use a bearer token for this interaction session"
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > 512:
        _interaction_error("INTERACTION_TOKEN_INVALID", 401, "The bearer token is invalid")
    return token.strip()


def _session_or_error(repository: Any, session_id: str, authorization: str | None) -> tuple[Any, str]:
    token = _bearer_token(authorization)
    try:
        session = repository.authenticate_interaction_session(session_id, token)
    except InteractionSessionNotFound:
        _interaction_error("INTERACTION_SESSION_NOT_FOUND", 404, "Interaction session was not found")
    except InteractionSessionExpired:
        _interaction_error("INTERACTION_SESSION_EXPIRED", 410, "Interaction session has expired")
    except InteractionSessionUnauthorized:
        _interaction_error("INTERACTION_TOKEN_INVALID", 401, "The bearer token is invalid")
    return session, token


def _session_response(session: Any) -> dict[str, Any]:
    value = session.as_dict() if hasattr(session, "as_dict") else dict(session)
    # Player ownership remains persisted for follow-up authorization but is
    # not needed by the browser's resumable-state contract.
    value.pop("account_id", None)
    value.pop("access_token_hash", None)
    return value


def _if_match_revision(value: str | None) -> int:
    if value is None:
        _interaction_error(
            "INTERACTION_REVISION_REQUIRED",
            428,
            "PATCH requires the current revision in If-Match",
        )
    candidate = value.strip()
    if candidate.startswith("W/"):
        candidate = candidate[2:].strip()
    candidate = candidate.strip('"')
    if "," in candidate:
        candidate = candidate.split(",", 1)[0].strip().strip('"')
    try:
        revision = int(candidate)
    except (TypeError, ValueError):
        _interaction_error("INTERACTION_REVISION_INVALID", 400, "If-Match must contain a revision")
    if revision < 1:
        _interaction_error("INTERACTION_REVISION_INVALID", 400, "If-Match must contain a revision")
    return revision


def _raise_state_validation(exc: ValueError) -> None:
    _interaction_error("INTERACTION_STATE_INVALID", 422, str(exc))


def _report_question(report: Mapping[str, Any], question_id: str) -> dict[str, Any] | None:
    """Return a report-offered diagnostic question without trusting client IDs."""

    ids = report.get("diagnostic_question_ids")
    if isinstance(ids, list) and question_id in ids:
        return {"diagnostic_question_id": question_id}
    containers: list[Any] = [report.get("diagnostic_questions")]
    for key in ("deep", "deep_analysis", "diagnostics", "story"):
        value = report.get(key)
        if isinstance(value, Mapping):
            containers.append(value.get("diagnostic_questions"))
    for container in containers:
        if isinstance(container, Mapping):
            mapped = container.get(question_id)
            if isinstance(mapped, Mapping):
                return {"diagnostic_question_id": question_id, **dict(mapped)}
            continue
        if not isinstance(container, list):
            continue
        for item in container:
            if isinstance(item, str) and item == question_id:
                return {"diagnostic_question_id": item}
            if not isinstance(item, Mapping):
                continue
            candidate_id = (
                item.get("diagnostic_question_id")
                or item.get("question_id")
                or item.get("id")
                or item.get("key")
            )
            if candidate_id == question_id:
                return dict(item)
            nested = item.get("diagnostic_questions")
            if isinstance(nested, list):
                for nested_item in nested:
                    if isinstance(nested_item, Mapping) and (
                        nested_item.get("diagnostic_question_id")
                        or nested_item.get("question_id")
                        or nested_item.get("id")
                    ) == question_id:
                        return dict(nested_item)
    return None


def _selection_plan_for_question(question: Mapping[str, Any]) -> dict[str, Any]:
    primary = (
        question.get("primary_hypothesis_id")
        or question.get("primary_hypothesis")
        or question.get("hypothesis_id")
        or question.get("diagnostic_question_id")
    )
    if isinstance(primary, Mapping):
        primary_id = primary.get("hypothesis_id") or primary.get("id") or question.get("diagnostic_question_id")
    else:
        primary_id = str(primary)
    secondary = question.get("secondary_hypothesis_id") or question.get("secondary_hypothesis")
    reuse = question.get("secondary_reuse_fraction")
    if reuse is None:
        reuse = question.get("reuse_fraction", question.get("evidence_reuse", question.get("reuse", 0.0)))
    try:
        reuse = float(reuse)
    except (TypeError, ValueError):
        reuse = 0.0
    if isinstance(secondary, Mapping):
        secondary_id = secondary.get("hypothesis_id") or secondary.get("id")
    else:
        secondary_id = secondary
    # A secondary is only retained when the report explicitly declares at
    # least half of its evidence reusable from the primary hypothesis.
    if reuse < 0.5:
        secondary_id = None
    return {
        "version": "deep-diagnostics-2.0.0",
        "primary_hypothesis_id": str(primary_id) if primary_id else None,
        "secondary_hypothesis_id": str(secondary_id) if secondary_id else None,
        "secondary_reuse_fraction": round(max(0.0, min(1.0, reuse)), 4),
        "limits": {
            "max_detail_requests": 25,
            "max_parse_requests": 25,
            "max_data_cost": 160.0,
            "detail_min_marginal_information_gain": 0.05,
            "parse_min_marginal_information_gain": 0.10,
            "min_marginal_information_gain": 0.05,
        },
        "cached_evidence_preferred": True,
        "evidence_sufficiency": {
            "moderate": {"positive": 3, "negative": 3, "control": 3},
            "high": {"positive": 8, "negative": 8, "control": 8, "practical_effect": 0.15},
        },
        "stopping_reason": "awaiting_evidence",
        "abstention_reasons": [],
    }


async def _resolve_entitlement(request: Request, *, report_id: str, account_id: int, diagnostic_question_id: str) -> dict[str, Any]:
    provider = getattr(request.app.state, "entitlement_provider", None) or getattr(
        request.app.state, "entitlement", None
    )
    service = _service(request)
    if provider is None:
        provider = getattr(service, "entitlement_provider", None) or getattr(service, "entitlement", None)
    if provider is None:
        # Development has no billing integration.  Keeping this as an
        # interface decision makes the eventual provider a drop-in seam.
        return {"allowed": True, "source": "entitlement_interface", "reason": "not_configured"}
    kwargs = {
        "report_id": report_id,
        "account_id": account_id,
        "diagnostic_question_id": diagnostic_question_id,
    }
    if hasattr(provider, "resolve"):
        result = provider.resolve(**kwargs)
    elif hasattr(provider, "decide"):
        result = provider.decide(**kwargs)
    elif hasattr(provider, "check"):
        result = provider.check(**kwargs)
    elif callable(provider):
        result = provider(**kwargs)
    else:
        result = {"allowed": False, "reason": "invalid_entitlement_provider"}
    if inspect.isawaitable(result):
        result = await result
    if isinstance(result, bool):
        return {"allowed": result, "source": "entitlement_interface"}
    if isinstance(result, Mapping):
        decision = dict(result)
        decision["allowed"] = bool(decision.get("allowed", decision.get("entitled", False)))
        return decision
    return {"allowed": False, "source": "entitlement_interface", "reason": "invalid_decision"}


def _epoch(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
            except ValueError:
                return None
    return None


async def _follow_up_history(service: Any, repository: Any, account_id: int) -> list[dict[str, Any]]:
    cached: list[dict[str, Any]] = []
    getter = getattr(repository, "get_cached_raw_payload", None)
    if getter is not None:
        cached_value = getter(f"/players/{account_id}/matches", str(account_id))
        if isinstance(cached_value, list):
            cached = [item for item in cached_value if isinstance(item, dict)]
    try:
        rows = await service.source.get_matches(account_id, limit=None, days=365)
    except TypeError:
        # Small test/integration sources often expose the narrow historical
        # signature; the persistence contract does not depend on ``days``.
        rows = await service.source.get_matches(account_id)
    if getter is not None and hasattr(repository, "persist_raw_payload"):
        repository.persist_raw_payload(f"/players/{account_id}/matches", str(account_id), rows)
    fetched = [item for item in rows if isinstance(item, dict)]
    # Merge source refreshes with a cached snapshot so a provider that returns
    # only a bounded recent page cannot erase older post-cutoff rows.
    by_id = {
        item.get("match_id"): item
        for item in [*cached, *fetched]
        if item.get("match_id") is not None
    }
    return list(by_id.values()) if by_id else fetched or cached


def _context_matches(row: Mapping[str, Any], baseline: Mapping[str, Any]) -> bool:
    raw_context = baseline.get("context")
    context: Mapping[str, Any] = raw_context if isinstance(raw_context, Mapping) else baseline
    keys = ("hero_id", "lane_role", "role", "patch", "game_mode", "lobby_type")
    comparisons = []
    for key in keys:
        expected = context.get(key)
        actual = row.get(key)
        if key == "hero_id" and expected is None:
            expected = context.get("hero")
        if expected is None and actual is None:
            continue
        if expected is not None and actual is not None:
            comparisons.append(actual == expected)
    return all(comparisons) if comparisons else True


def _follow_up_metric(rows: Sequence[Mapping[str, Any]], metric: str) -> float | None:
    if not rows:
        return None
    if metric in {"win_rate", "wins"}:
        win_values = [row.get("won", row.get("radiant_win", row.get("win"))) for row in rows]
        known_win_values = [bool(value) for value in win_values if value is not None]
        return sum(known_win_values) / len(known_win_values) if known_win_values else None
    metric_values: list[float] = []
    for row in rows:
        value = row.get(metric)
        if value is None and metric in {"deaths_per_match", "death_exposure"}:
            value = row.get("deaths")
        if value is None and metric == "duration_minutes":
            value = row.get("duration")
            value = float(value) / 60.0 if value is not None else None
        if isinstance(value, (int, float)):
            metric_values.append(float(value))
    return sum(metric_values) / len(metric_values) if metric_values else None


@router.post("/analyses", response_model=CreateAnalysisResponse, status_code=202)
async def create_analysis(
    payload: CreateAnalysisRequest, request: Request
) -> CreateAnalysisResponse:
    identifier = parse_player_identifier(payload.player)
    client_ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.allow(
        client_ip, identifier.account_id, unresolved_key=identifier.vanity
    ):
        raise AnalysisRateLimited("Too many analysis requests; try again later")
    job, reused = await _service(request).create_analysis(
        payload.player,
        refresh=payload.refresh,
        mode=payload.mode,
    )
    return CreateAnalysisResponse(
        job_id=job.job_id,
        status=job.status,
        analysis_mode=job.analysis_mode,
        reused=reused,
        events_url=f"/v1/analyses/{job.job_id}/events",
    )


@router.post(
    "/reports/{report_id}/interaction-sessions",
    response_model=InteractionSessionCreatedResponse,
    status_code=201,
)
async def create_interaction_session(
    report_id: str,
    request: Request,
    payload: InteractionSessionCreateRequest | None = None,
) -> Response:
    payload = payload or InteractionSessionCreateRequest()
    repository = _service(request).repository
    report = repository.get_report(report_id)
    if report is None:
        raise ReportNotFound("Report was not found")
    try:
        state = normalize_interaction_state(payload)
        baseline = validate_recommendation_baseline(
            payload.recommendation_baseline
            or payload.baseline
            or report.get("recommendation_baseline")
            or (report.get("metadata") or {}).get("recommendation_baseline")
        )
    except ValueError as exc:
        _raise_state_validation(exc)
    if payload.history_cutoff is not None and payload.history_cutoff < 0:
        _interaction_error("INTERACTION_STATE_INVALID", 422, "history_cutoff must be non-negative")
    try:
        session, access_token = repository.create_interaction_session(
            report_id,
            state=state,
            recommendation_baseline=baseline,
            history_cutoff=payload.history_cutoff,
        )
    except InteractionSessionNotFound as exc:
        raise ReportNotFound(str(exc)) from exc
    body = _session_response(session)
    body["access_token"] = access_token
    response = JSONResponse(content=body, status_code=201)
    response.headers["ETag"] = '"1"'
    return response


@router.get(
    "/report-interactions/{session_id}",
    response_model=InteractionSessionResponse,
)
async def get_interaction_session(
    session_id: str,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> Response:
    session, _token = _session_or_error(_service(request).repository, session_id, authorization)
    response = JSONResponse(content=_session_response(session))
    response.headers["ETag"] = f'"{session.revision}"'
    return response


@router.patch(
    "/report-interactions/{session_id}",
    response_model=InteractionSessionResponse,
)
async def patch_interaction_session(
    session_id: str,
    payload: InteractionSessionPatchRequest,
    request: Request,
    if_match: str | None = Header(default=None, alias="If-Match"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> Response:
    repository = _service(request).repository
    session, token = _session_or_error(repository, session_id, authorization)
    expected_revision = _if_match_revision(if_match)
    try:
        state = normalize_interaction_patch(payload)
    except ValueError as exc:
        _raise_state_validation(exc)
    # PATCH is additive at the beat level; the revision still guards the
    # whole document so concurrent browser tabs cannot silently overwrite a
    # newer answer.
    state = {**dict(session.state), **state}
    try:
        updated = repository.update_interaction_session(
            session_id,
            token,
            expected_revision=expected_revision,
            state=state,
        )
    except InteractionRevisionConflict as exc:
        _interaction_error(
            "INTERACTION_REVISION_CONFLICT",
            409,
            f"Revision conflict; current revision is {exc.actual}",
        )
    except InteractionSessionExpired:
        _interaction_error("INTERACTION_SESSION_EXPIRED", 410, "Interaction session has expired")
    except InteractionSessionUnauthorized:
        _interaction_error("INTERACTION_TOKEN_INVALID", 401, "The bearer token is invalid")
    response = JSONResponse(content=_session_response(updated))
    response.headers["ETag"] = f'"{updated.revision}"'
    return response


@router.delete("/report-interactions/{session_id}", status_code=204)
async def delete_interaction_session(
    session_id: str,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> Response:
    repository = _service(request).repository
    _session, token = _session_or_error(repository, session_id, authorization)
    try:
        repository.delete_interaction_session(session_id, token)
    except InteractionSessionExpired:
        _interaction_error("INTERACTION_SESSION_EXPIRED", 410, "Interaction session has expired")
    except InteractionSessionUnauthorized:
        _interaction_error("INTERACTION_TOKEN_INVALID", 401, "The bearer token is invalid")
    return Response(status_code=204)


@router.post("/report-interactions/{session_id}/follow-up")
async def interaction_follow_up(
    session_id: str,
    request: Request,
    payload: FollowUpRequest | None = None,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    del payload  # Reserved for future client-selected context views.
    repository = _service(request).repository
    session, token = _session_or_error(repository, session_id, authorization)
    service = _service(request)
    rows = await _follow_up_history(service, repository, session.account_id)
    cutoff = session.history_cutoff
    new_rows = [
        row
        for row in rows
        if cutoff is None or (_epoch(row.get("start_time")) or -1) > cutoff
    ]
    # Summary eligibility is intentionally checked without detail.  This
    # keeps follow-up within the Free cost boundary and avoids a new identity.
    from app.ingestion.eligibility import assess_match

    def _eligible_summary(row: Mapping[str, Any]) -> bool:
        candidate = dict(row)
        if candidate.get("duration") is None and candidate.get("duration_seconds") is not None:
            candidate["duration"] = candidate["duration_seconds"]
        return assess_match(candidate).eligible

    eligible = [row for row in new_rows if _eligible_summary(row)]
    baseline = session.recommendation_baseline
    context_rows = [row for row in eligible if _context_matches(row, baseline)]
    context_rows.sort(key=lambda row: (_epoch(row.get("start_time")) or 0, row.get("match_id", 0)))
    selected = context_rows[-5:]
    completed = min(5, len(context_rows))
    ready = completed >= 5
    metric = str(baseline.get("metric") or "win_rate")
    observed_value = _follow_up_metric(selected, metric) if ready else None
    baseline_value = baseline.get("value", baseline.get("baseline_value"))
    if not isinstance(baseline_value, (int, float)):
        baseline_value = None
    comparison = None
    if ready and observed_value is not None and baseline_value is not None:
        comparison = {
            "label": "what_changed_in_these_five_games",
            "metric": metric,
            "baseline": float(baseline_value),
            "follow_up": round(observed_value, 6),
            "delta": round(observed_value - float(baseline_value), 6),
            "match_ids": [row.get("match_id") for row in selected],
            "causal": False,
            "identity_updated": False,
        }
    status = "ready" if ready else "progress"
    stop_reason = "five_context_matches_ready" if ready else "awaiting_five_context_matches"
    if ready and comparison is None:
        status = "abstained"
        stop_reason = "abstained_missing_predeclared_baseline"
    follow_up = {
        "eligible_new_matches": len(eligible),
        "context_matching_matches": len(context_rows),
        "completed_context_matches": completed,
        "required_context_matches": 5,
        "metric": metric,
        "status": status,
        "comparison": comparison,
    }
    try:
        updated = repository.record_interaction_follow_up(
            session_id,
            token,
            follow_up=follow_up,
        )
    except InteractionSessionExpired:
        _interaction_error("INTERACTION_SESSION_EXPIRED", 410, "Interaction session has expired")
    return {
        "session_id": session_id,
        "revision": updated.revision,
        "status": follow_up["status"],
        "eligible_new_matches": len(eligible),
        "context_matching_matches": len(context_rows),
        "progress": {
            "completed": completed,
            "required": 5,
            "remaining": max(0, 5 - completed),
        },
        "comparison": comparison,
        "stop_reason": stop_reason,
    }


@router.post(
    "/reports/{report_id}/deep-analyses",
    response_model=DeepAnalysisResponse,
    status_code=202,
)
async def create_deep_analysis(
    report_id: str,
    payload: DeepAnalysisRequest,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    repository = _service(request).repository
    report = repository.get_report(report_id)
    if report is None:
        raise ReportNotFound("Report was not found")
    question = _report_question(report, payload.diagnostic_question_id)
    if question is None:
        _interaction_error(
            "DIAGNOSTIC_QUESTION_NOT_OFFERED",
            422,
            "The diagnostic question was not offered by this report",
        )
    interaction_session_id = (
        payload.interaction_session_id
        or payload.interaction_session
        or payload.interaction_session_ref
    )
    if interaction_session_id:
        session, _token = _session_or_error(repository, interaction_session_id, authorization)
        if session.report_id != report_id:
            _interaction_error(
                "INTERACTION_SESSION_REPORT_MISMATCH",
                403,
                "The interaction session belongs to a different report",
            )
    owner_getter = getattr(repository, "get_report_owner", None)
    owner_value: Any = owner_getter(report_id) if owner_getter is not None else None
    account_id: int | None = None
    if owner_value is not None:
        try:
            account_id = int(owner_value)
        except (TypeError, ValueError):
            account_id = None
    if account_id is None:
        identity = report.get("identity") or {}
        metadata = report.get("metadata") or {}
        account_value: Any = identity.get("account_id", metadata.get("account_id"))
        if account_value is None:
            _interaction_error("REPORT_OWNER_UNAVAILABLE", 422, "The report owner is unavailable")
        try:
            account_id = int(account_value)
        except (TypeError, ValueError):
            _interaction_error("REPORT_OWNER_UNAVAILABLE", 422, "The report owner is unavailable")
    entitlement = await _resolve_entitlement(
        request,
        report_id=report_id,
        account_id=account_id,
        diagnostic_question_id=payload.diagnostic_question_id,
    )
    if not entitlement.get("allowed"):
        _interaction_error("DEEP_ENTITLEMENT_REQUIRED", 403, "Deep Analysis is not entitled for this request")
    selection_plan = _selection_plan_for_question(question)
    canonical_player = str(account_id)
    identity = report.get("identity") or {}
    if identity.get("canonical_url"):
        canonical_player = str(identity["canonical_url"])
    job = repository.create_job(
        account_id,
        canonical_player,
        "deep-diagnostics-2.0.0",
        "deep_scan",
        parent_report_id=report_id,
        diagnostic_question_id=payload.diagnostic_question_id,
        entitlement_decision=entitlement,
        selection_plan=selection_plan,
        stopping_reason=selection_plan["stopping_reason"],
    )
    if hasattr(repository, "update_job"):
        repository.update_job(job, stage="deep_selection")
    dispatcher = getattr(_service(request), "enqueue_deep_continuation", None)
    if dispatcher is not None:
        result = dispatcher(
            job,
            parent_report_id=report_id,
            diagnostic_question_id=payload.diagnostic_question_id,
            interaction_session_id=interaction_session_id,
        )
        if inspect.isawaitable(result):
            await result
    return {
        "job_id": job.job_id,
        "analysis_job_id": job.job_id,
        "status": job.status,
        "analysis_mode": job.analysis_mode,
        "parent_report_id": report_id,
        "diagnostic_question_id": payload.diagnostic_question_id,
        "entitlement_decision": entitlement,
        "selection_plan": selection_plan,
        "stopping_reason": selection_plan["stopping_reason"],
        "events_url": f"/v1/analyses/{job.job_id}/events",
    }


@router.get("/analyses/{job_id}", response_model=AnalysisStatusResponse)
async def get_analysis(job_id: str, request: Request) -> AnalysisStatusResponse:
    job = _service(request).repository.get_job(job_id)
    if job is None:
        raise AnalysisNotFound("Analysis job was not found")
    return AnalysisStatusResponse(**job.as_dict())


@router.get("/analyses/{job_id}/events")
async def analysis_events(job_id: str, request: Request) -> StreamingResponse:
    repository = _service(request).repository
    job = repository.get_job(job_id)
    if job is None:
        raise AnalysisNotFound("Analysis job was not found")

    async def stream() -> Any:
        offset = 0
        while True:
            current = repository.get_job(job_id)
            if current is None:
                return
            events = (
                repository.get_events(job_id, offset)
                if hasattr(repository, "get_events")
                else current.events[offset:]
            )
            for event in events:
                yield f"data: {json.dumps(event.as_dict(), sort_keys=True)}\n\n"
                offset += 1
            if current.status in {"completed", "failed"}:
                yield "event: end\ndata: {}\n\n"
                return
            if await request.is_disconnected():
                return
            yield ": heartbeat\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/reports/{report_id}")
async def get_report(report_id: str, request: Request) -> Response:
    report = _service(request).repository.get_report(report_id)
    if report is None:
        raise ReportNotFound("Report was not found")
    return JSONResponse(
        content=report,
        headers={"X-Robots-Tag": "noindex, nofollow, noarchive"},
    )


@router.get("/reports/{report_id}/evidence/{insight_id}")
async def get_evidence(report_id: str, insight_id: str, request: Request) -> dict[str, Any]:
    values = _service(request).repository.get_evidence(report_id, insight_id)
    if not values:
        raise ReportNotFound("Evidence was not found")
    return values[0]


@router.get("/reports/{report_id}/share/{card_type}")
async def get_share_card(
    report_id: str,
    card_type: str,
    request: Request,
) -> Response:
    report = _service(request).repository.get_report(report_id)
    if report is None:
        raise ReportNotFound("Report was not found")
    show_name = request.query_params.get("show_name", "true").lower() in {"1", "true", "yes"}
    show_avatar = request.query_params.get("show_avatar", "true").lower() in {"1", "true", "yes"}
    try:
        svg, cache_key = build_share_svg(
            report,
            card_type=card_type,
            show_name=show_name,
            show_avatar=show_avatar,
        )
    except ValueError as exc:
        record_metric("share.render.failed", tags={"card_type": card_type})
        return Response(str(exc), status_code=422, media_type="text/plain")
    record_metric("share.render.completed", tags={"card_type": card_type, "renderer": RENDERER_VERSION})
    return Response(
        svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=3600, immutable",
            "ETag": cache_key,
            "X-Share-Renderer": RENDERER_VERSION,
            "X-Robots-Tag": "noindex, nofollow, noarchive",
        },
    )


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        api="ok",
        postgres="not_configured",
        redis="not_configured",
        worker="in_process",
        source=settings.opendota_source,
    )

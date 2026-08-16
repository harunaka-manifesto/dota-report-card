from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse

from app.api.schemas import (
    AnalysisStatusResponse,
    CreateAnalysisRequest,
    CreateAnalysisResponse,
    HealthResponse,
)
from app.core.errors import AnalysisNotFound, AnalysisRateLimited, ReportNotFound
from app.core.security import RateLimiter, parse_player_identifier
from app.share.service import build_share_svg

router = APIRouter(prefix="/v1")
_rate_limiter = RateLimiter()


def _service(request: Request) -> Any:
    return request.app.state.analysis_service


@router.post("/analyses", response_model=CreateAnalysisResponse, status_code=202)
async def create_analysis(
    payload: CreateAnalysisRequest, request: Request
) -> CreateAnalysisResponse:
    identifier = parse_player_identifier(payload.player)
    client_ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.allow(client_ip, identifier.account_id):
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
async def get_report(report_id: str, request: Request) -> dict[str, Any]:
    report = _service(request).repository.get_report(report_id)
    if report is None:
        raise ReportNotFound("Report was not found")
    return report


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
        return Response(str(exc), status_code=422, media_type="text/plain")
    return Response(
        svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=3600, immutable", "ETag": cache_key},
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

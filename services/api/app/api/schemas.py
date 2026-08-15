from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateAnalysisRequest(BaseModel):
    player: str = Field(min_length=1, max_length=300)
    refresh: bool = False


class CreateAnalysisResponse(BaseModel):
    job_id: str
    status: str
    reused: bool
    events_url: str


class AnalysisStatusResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_id: str
    account_id: int
    status: str
    stage: str
    processed_matches: int
    eligible_matches: int
    warnings: list[str]
    failure_code: str | None
    message: str | None
    report_id: str | None
    events_url: str


class ErrorResponse(BaseModel):
    code: str
    message: str


class HealthResponse(BaseModel):
    status: str
    api: str
    postgres: str
    redis: str
    worker: str
    source: str


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    insight_id: str
    publication_status: str
    confidence: str
    payload: dict[str, Any] = Field(default_factory=dict)

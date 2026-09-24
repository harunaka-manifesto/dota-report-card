"""Isolated, typed mobile V1 boundary over tracker-owned persisted state."""
from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from enum import StrEnum
from typing import Annotated, Literal, cast
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, JsonValue
from redis import Redis
from sqlalchemy import Connection, Engine, and_, func, or_, select, true
from sqlalchemy.dialects.postgresql import insert

from app.core.config import Settings
from app.storage.database import create_database_engine
from app.tracker.account_lifecycle import AccountLifecycleError, switch_preflight
from app.tracker.authentication import (
    AuthenticationError,
    HttpJwksSource,
    IdentityCollision,
    VerifiedIdentity,
    attach_identity,
    authenticate_access_token,
    login_with_identity_token,
    revoke_access_session,
    rotate_refresh_token,
    verify_identity_token,
)
from app.tracker.evidence import canonical_json
from app.tracker.metrics import METRICS
from app.tracker.retry import retry_match
from app.tracker.schema import (
    account_matches,
    analyses,
    bootstrap,
    coverage,
    devices,
    idempotency_keys,
    identities,
    insight_results,
    match_players,
    matches,
    metric_observations,
    personal_bests,
    profiles,
    sync_state,
    users,
)
from app.tracker.steam_identity import (
    HttpSteamAssertionVerifier,
    RedisLike,
    SteamLinkError,
    complete_steam_link,
    complete_steam_switch,
    start_steam_link,
    start_steam_switch,
)
from app.tracker.sync import request_account_sync
from app.tracker.trend import TrendPoint
from app.tracker.trend import evaluate as evaluate_trend


class Mode(StrEnum):
    STANDARD = "STANDARD"
    TURBO = "TURBO"


class Role(StrEnum):
    CARRY = "CARRY"
    MID = "MID"
    OFFLANE = "OFFLANE"
    SUPPORT = "SUPPORT"


class Readiness(StrEnum):
    PENDING = "PENDING"
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class Lifecycle(StrEnum):
    WAITING_FOR_DATA = "WAITING_FOR_DATA"
    ANALYZING = "ANALYZING"
    WAITING_FOR_PRIOR_MATCH = "WAITING_FOR_PRIOR_MATCH"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    READY = "READY"
    UNAVAILABLE = "UNAVAILABLE"


class SignInRequest(BaseModel):
    identity_token: str = Field(min_length=20, max_length=16384)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=512)


class SessionView(BaseModel):
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    expires_at: datetime


class AccountView(BaseModel):
    state: Literal["ACTIVE", "DELETION_PENDING"]
    steam_linked: bool
    scope: Literal["FREE", "PRO"]
    revision: int
    identity_methods: list[Literal["apple", "google", "email"]]


class SteamStartView(BaseModel):
    authorization_url: str
    state: str


class SteamCompleteRequest(BaseModel):
    fields: dict[str, str]


class SteamCompleteView(BaseModel):
    linked: Literal[True] = True


class SwitchPreflightView(BaseModel):
    available: bool
    cause: str | None
    days_remaining: int


class BootstrapModeView(BaseModel):
    mode: Mode
    status: Literal["NOT_STARTED", "SEARCHING", "PROCESSING", "COMPLETE"]
    outcome: Literal["NO_STEAM_LINKED", "DATA_ACCESS_BLOCKED", "NO_MATCHES_FOUND", "NO_ELIGIBLE_MATCHES", "READY", "READY_WITH_GAPS"] | None
    discovered_count: int
    eligible_count: int
    settled_count: int


class BootstrapView(BaseModel):
    modes: list[BootstrapModeView]


class PlayerFacts(BaseModel):
    hero_id: int
    team: Literal["RADIANT", "DIRE"]
    kills: int | None
    deaths: int | None
    assists: int | None


class MetricView(BaseModel):
    metric_id: str
    state: Literal["MEASURED", "NOT_AVAILABLE"]
    raw_value: float | None
    comparison_value: float | None
    unavailable_reason: str | None
    baseline_state: Literal["BUILDING", "READY", "NOT_AVAILABLE"]
    baseline_value: float | None
    prior_count: int
    performance_state: Literal["ABOVE", "IN_LINE", "BELOW", "NOT_READY"] | None


class InsightCardView(BaseModel):
    template_id: str
    slots: dict[str, JsonValue]


class InsightView(BaseModel):
    state: Readiness
    contract_version: str | None
    reason: str | None
    cards: list[InsightCardView]


class MatchView(BaseModel):
    ref: str
    mode: Mode | None
    started_at: datetime
    duration_seconds: int
    lifecycle: Lifecycle
    facts: Readiness
    performance: Readiness
    insights: InsightView
    role: Role | None
    progression: Literal["STANDARD", "TURBO", "NONE"] | None
    progression_reason: str | None
    won: bool
    players: list[PlayerFacts]
    metrics: list[MetricView]


class HistoryView(BaseModel):
    matches: list[MatchView]
    next_cursor: str | None


class MatchSummary(BaseModel):
    ref: str
    mode: Mode
    started_at: datetime
    lifecycle: Lifecycle
    role: Role | None
    hero_id: int
    won: bool


class HomeView(BaseModel):
    mode: Mode
    local_date: str
    today_matches: list[MatchSummary]
    last_matches: list[MatchSummary]
    focus: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    challenge: Literal["UNAVAILABLE"] = "UNAVAILABLE"


class CoverageInterval(BaseModel):
    capability: Literal["MATCH_FACTS", "DETAILED_METRICS"]
    start_at: datetime
    end_at: datetime
    state: Literal["KNOWN", "GAP", "PENDING"]


class CoverageView(BaseModel):
    mode: Mode
    intervals: list[CoverageInterval]


class ProgressPoint(BaseModel):
    match_ref: str
    started_at: datetime
    value: float
    baseline_value: float | None
    prior_count: int


class PersonalBestView(BaseModel):
    match_ref: str
    value: float


class TrendView(BaseModel):
    state: Literal["IMPROVING", "STABLE", "DECLINING", "INSUFFICIENT_HISTORY"] | None
    reason: Literal["CALIBRATION_UNAVAILABLE"] | None
    point_count: int


class ProgressView(BaseModel):
    mode: Mode
    role: Role
    metric_id: str
    points: list[ProgressPoint]
    personal_best: PersonalBestView | None
    trend: TrendView


class MethodsView(BaseModel):
    methods: list[Literal["apple", "google", "email"]]


class SyncView(BaseModel):
    state: Literal["IDLE", "CHECKING", "UP_TO_DATE", "SYNC_ERROR"]
    last_checked_at: datetime | None


class SyncRequestView(BaseModel):
    accepted: bool


class RetryView(BaseModel):
    accepted: bool


class DeviceRequest(BaseModel):
    permission: Literal["UNKNOWN", "GRANTED", "DENIED"]
    push_token: str | None = Field(default=None, max_length=4096)


class ChangesView(BaseModel):
    cursor: str
    changed_refs: list[str]
    full_refresh: bool


bearer = HTTPBearer(auto_error=False)


def _engine(request: Request) -> Engine:
    engine = request.app.state.database
    if engine is None:
        engine = create_database_engine(request.app.state.settings)
        request.app.state.database = engine
    return engine


def _redis(request: Request) -> Redis:
    client = request.app.state.redis
    if client is None:
        client = Redis.from_url(request.app.state.settings.redis_url, decode_responses=True)
        request.app.state.redis = client
    return client


def _user(request: Request, credential: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> str:
    if credential is None or credential.scheme.lower() != "bearer":
        raise HTTPException(401, "AUTH_REQUIRED")
    try:
        return authenticate_access_token(_engine(request), credential.credentials)
    except AuthenticationError as exc:
        raise HTTPException(401, "SESSION_INVALID") from exc


def _active_profile(connection, user_id: str):
    return connection.execute(select(profiles).where(
        profiles.c.user_id == user_id, profiles.c.active.is_(True),
    )).mappings().one_or_none()


def _visible(profile):
    if profile["active_scope"] == "PRO":
        return true()
    return or_(account_matches.c.origin == "BOOTSTRAP",
               account_matches.c.provider_started_at >= profile["original_linked_at"])


def _problem(status: int, code: str) -> JSONResponse:
    return JSONResponse(status_code=status, media_type="application/problem+json", content={
        "type": "about:blank", "title": code.replace("_", " ").title(), "status": status,
        "code": code, "detail": code.replace("_", " ").lower(),
    })


def _lifecycle(value: str) -> Lifecycle:
    return Lifecycle.WAITING_FOR_DATA if value == "WAITING_FOR_PROVIDER" else Lifecycle(value)


def _session_view(tokens) -> SessionView:
    return SessionView(
        access_token=tokens.access_token, refresh_token=tokens.refresh_token,
        access_expires_at=tokens.access_expires_at, expires_at=tokens.expires_at,
    )


def _match_view(connection, row) -> MatchView:
    match = connection.execute(select(matches).where(matches.c.match_id == row["match_id"])).mappings().one()
    roster = connection.execute(select(match_players.c.summary).where(
        match_players.c.match_id == row["match_id"],
    ).order_by(match_players.c.player_slot)).scalars().all()
    players = [PlayerFacts(
        hero_id=player["hero_id"], team=player["team"],
        kills=player.get("values", {}).get("kills"),
        deaths=player.get("values", {}).get("deaths"),
        assists=player.get("values", {}).get("assists"),
    ) for player in roster]
    metrics: list[MetricView] = []
    insight = InsightView(state=Readiness.PENDING, contract_version=None, reason=None, cards=[])
    if row["active_analysis_id"] is not None:
        observed = connection.execute(select(metric_observations).where(
            metric_observations.c.analysis_id == row["active_analysis_id"],
        ).order_by(metric_observations.c.metric_id)).mappings()
        for metric in observed:
            baseline = metric["baseline_snapshot"]
            metrics.append(MetricView(
                metric_id=metric["metric_id"],
                state="MEASURED" if metric["raw_value"] is not None else "NOT_AVAILABLE",
                raw_value=metric["raw_value"], comparison_value=metric["comparison_value"],
                unavailable_reason=metric["unavailable_reason"],
                baseline_state="READY" if baseline.get("state") == "BASELINE_READY" else "BUILDING",
                baseline_value=baseline.get("value"), prior_count=baseline.get("prior_count", 0),
                performance_state=metric["performance_state"],
            ))
        result = connection.execute(select(insight_results).where(
            insight_results.c.analysis_id == row["active_analysis_id"],
        )).mappings().one_or_none()
        if result is not None:
            analysis = connection.execute(select(analyses.c.result).where(
                analyses.c.id == row["active_analysis_id"],
            )).scalar_one()
            status = analysis.get("insight_status", "NOT_ELIGIBLE(SOURCE_EVIDENCE)")
            eligible = status == "EVALUATED"
            insight = InsightView(
                state=Readiness.AVAILABLE if eligible else Readiness.UNAVAILABLE,
                contract_version=result["contract_version"],
                reason=None if eligible else status.removeprefix("NOT_ELIGIBLE(").removesuffix(")"),
                cards=[InsightCardView(template_id=card["candidate_id"], slots=card["slots"])
                       for card in result["cards"]],
            )
    return MatchView(
        ref=row["public_ref"], mode=match["mode"] if match["mode"] in {"STANDARD", "TURBO"} else None,
        started_at=row["provider_started_at"], duration_seconds=match["duration_seconds"],
        lifecycle=_lifecycle(row["lifecycle"]), facts=Readiness.AVAILABLE,
        performance=Readiness.AVAILABLE if row["lifecycle"] == "READY" else Readiness.PENDING,
        insights=insight, role=row["effective_role"], progression=row["progression"],
        progression_reason=row["progression_reason"],
        won=match["radiant_win"] == (row["player_slot"] < 5), players=players, metrics=metrics,
    )


def _summary_view(connection, row) -> MatchSummary:
    match = connection.execute(select(matches.c.radiant_win).where(
        matches.c.match_id == row["match_id"],
    )).one()
    hero_id = connection.scalar(select(match_players.c.hero_id).where(
        match_players.c.match_id == row["match_id"],
        match_players.c.player_slot == row["player_slot"],
    ))
    return MatchSummary(
        ref=row["public_ref"], mode=row["mode"], started_at=row["provider_started_at"],
        lifecycle=_lifecycle(row["lifecycle"]), role=row["effective_role"], hero_id=hero_id,
        won=match.radiant_win == (row["player_slot"] < 5),
    )


def _cursor(profile_id: str, ref: str, mode: str, role: str | None, revision: int) -> str:
    message = f"{ref}:{mode}:{role or ''}:{revision}".encode("ascii")
    signature = hmac.new(profile_id.encode("ascii"), message, hashlib.sha256).hexdigest()[:24]
    return f"{ref}.{signature}"


def _methods(connection, owner: str) -> list[Literal["apple", "google", "email"]]:
    methods: list[Literal["apple", "google", "email"]] = []
    for issuer in connection.scalars(select(identities.c.issuer).where(identities.c.user_id == owner)):
        methods.append("apple" if issuer == "https://appleid.apple.com" else
                       "google" if issuer == "https://accounts.google.com" else "email")
    return sorted(set(methods))


def _attach_and_list(connection: Connection, owner: str, verified: VerifiedIdentity) -> list[Literal["apple", "google", "email"]]:
    attach_identity(connection, owner, verified)
    return _methods(connection, owner)


def _idempotent(connection: Connection, *, owner: str, operation: str, key: str,
                body: dict[str, object], publish: Callable[[], dict[str, object]]) -> dict[str, object]:
    digest = hashlib.sha256(canonical_json(body)).hexdigest()
    identity = dict(user_id=owner, operation=operation, key=key)
    inserted = connection.execute(insert(idempotency_keys).values(
        **identity, request_digest=digest, response={}, status_code=0,
        created_at=func.clock_timestamp(),
    ).on_conflict_do_nothing().returning(idempotency_keys.c.key)).scalar_one_or_none()
    if inserted is None:
        prior = connection.execute(select(idempotency_keys).where(
            idempotency_keys.c.user_id == owner,
            idempotency_keys.c.operation == operation,
            idempotency_keys.c.key == key,
        ).with_for_update()).mappings().one()
        if prior["request_digest"] != digest:
            raise HTTPException(409, "IDEMPOTENCY_CONFLICT")
        return prior["response"]
    response = publish()
    connection.execute(idempotency_keys.update().where(
        idempotency_keys.c.user_id == owner,
        idempotency_keys.c.operation == operation,
        idempotency_keys.c.key == key,
    ).values(response=response, status_code=200))
    return response


def create_mobile_app(settings: Settings, *, database: Engine | None = None, redis: Redis | None = None,
                      audiences: dict[str, set[str]] | None = None, steam_callback_url: str | None = None) -> FastAPI:
    app = FastAPI(title="Dota Tracker Mobile API", version="1.0.0", openapi_url="/openapi.json")
    app.state.settings = settings
    app.state.database = database
    app.state.redis = redis
    app.state.audiences = audiences or {}
    app.state.steam_callback_url = steam_callback_url
    app.state.jwks = HttpJwksSource()
    app.state.steam_verifier = HttpSteamAssertionVerifier()

    @app.exception_handler(HTTPException)
    async def http_problem(_request: Request, exc: HTTPException) -> JSONResponse:
        return _problem(exc.status_code, str(exc.detail))

    @app.exception_handler(AuthenticationError)
    async def auth_problem(_request: Request, _exc: AuthenticationError) -> JSONResponse:
        return _problem(401, "IDENTITY_INVALID")

    @app.exception_handler(IdentityCollision)
    async def collision_problem(_request: Request, _exc: IdentityCollision) -> JSONResponse:
        return _problem(409, "IDENTITY_COLLISION")

    @app.exception_handler(SteamLinkError)
    async def steam_problem(_request: Request, _exc: SteamLinkError) -> JSONResponse:
        return _problem(400, "STEAM_LINK_INVALID")

    @app.exception_handler(AccountLifecycleError)
    async def lifecycle_problem(_request: Request, exc: AccountLifecycleError) -> JSONResponse:
        return _problem(409, exc.cause)

    async def sign_in(request: Request, body: SignInRequest, method: Literal["apple", "google"]) -> SessionView:
        allowed = app.state.audiences.get(method)
        if not allowed:
            raise HTTPException(503, "SIGN_IN_UNAVAILABLE")
        _, tokens = login_with_identity_token(_engine(request), body.identity_token, method, allowed, app.state.jwks)
        return _session_view(tokens)

    @app.post("/auth/apple", response_model=SessionView)
    async def apple(request: Request, body: SignInRequest) -> SessionView:
        return await sign_in(request, body, "apple")

    @app.post("/auth/google", response_model=SessionView)
    async def google(request: Request, body: SignInRequest) -> SessionView:
        return await sign_in(request, body, "google")

    @app.post("/auth/email")
    async def email_auth() -> JSONResponse:
        return _problem(503, "EMAIL_METHOD_UNAVAILABLE")

    @app.post("/sessions/refresh", response_model=SessionView)
    async def refresh(request: Request, body: RefreshRequest) -> SessionView:
        return _session_view(rotate_refresh_token(_engine(request), body.refresh_token))

    @app.post("/sessions/logout", status_code=204)
    async def logout(request: Request, credential: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
                     _owner: Annotated[str, Depends(_user)]) -> None:
        assert credential is not None
        revoke_access_session(_engine(request), credential.credentials)

    @app.get("/account", response_model=AccountView)
    async def account(request: Request, owner: Annotated[str, Depends(_user)]) -> AccountView:
        with _engine(request).connect() as connection:
            user = connection.execute(select(users).where(users.c.id == owner)).mappings().one()
            profile = _active_profile(connection, owner)
            methods = _methods(connection, owner)
        return AccountView(state=user["state"], steam_linked=profile is not None,
                           scope=profile["active_scope"] if profile else "FREE",
                           revision=profile["active_revision"] if profile else 0,
                           identity_methods=methods)

    @app.get("/account/identities", response_model=MethodsView)
    async def account_identities(request: Request, owner: Annotated[str, Depends(_user)]) -> MethodsView:
        with _engine(request).connect() as connection:
            return MethodsView(methods=_methods(connection, owner))

    @app.post("/account/identities/{method}", response_model=MethodsView)
    async def add_identity(request: Request, body: SignInRequest, method: Literal["apple", "google"],
                           owner: Annotated[str, Depends(_user)],
                           idempotency_key: Annotated[str, Header(min_length=8, max_length=200)]) -> MethodsView:
        allowed = app.state.audiences.get(method)
        if not allowed or not idempotency_key:
            raise HTTPException(503, "IDENTITY_METHOD_UNAVAILABLE")
        verified = verify_identity_token(body.identity_token, method, allowed, app.state.jwks)
        with _engine(request).begin() as connection:
            result = _idempotent(connection, owner=owner, operation=f"IDENTITY_{method}",
                key=idempotency_key, body={"token_digest": hashlib.sha256(body.identity_token.encode()).hexdigest()},
                publish=lambda: {"methods": _attach_and_list(connection, owner, verified)})
        return MethodsView.model_validate(result)

    @app.post("/steam/links", response_model=SteamStartView)
    async def steam_start(request: Request, owner: Annotated[str, Depends(_user)],
                          idempotency_key: Annotated[str, Header(min_length=8, max_length=200)]) -> SteamStartView:
        if not app.state.steam_callback_url:
            raise HTTPException(503, "STEAM_LINK_UNAVAILABLE")
        def publish() -> dict[str, object]:
            started = start_steam_link(_engine(request), cast(RedisLike, _redis(request)),
                                       user_id=owner, callback_url=app.state.steam_callback_url)
            return {"authorization_url": started.authorization_url, "state": started.state}
        with _engine(request).begin() as connection:
            result = _idempotent(connection, owner=owner, operation="STEAM_START", key=idempotency_key,
                body={}, publish=publish)
        return SteamStartView.model_validate(result)

    @app.post("/steam/links/complete", response_model=SteamCompleteView)
    async def steam_complete(request: Request, body: SteamCompleteRequest,
                             owner: Annotated[str, Depends(_user)],
                             idempotency_key: Annotated[str, Header(min_length=8, max_length=200)]) -> SteamCompleteView:
        with _engine(request).begin() as connection:
            result = _idempotent(connection, owner=owner, operation="STEAM_COMPLETE", key=idempotency_key,
                body={"fields": body.fields}, publish=lambda: {"linked": bool(complete_steam_link(
                    connection, cast(RedisLike, _redis(request)), user_id=owner,
                    callback_fields=body.fields, verifier=app.state.steam_verifier,
                ))})
        return SteamCompleteView.model_validate(result)

    @app.get("/account/steam-switch/preflight", response_model=SwitchPreflightView)
    async def steam_switch_preflight(request: Request, owner: Annotated[str, Depends(_user)]) -> SwitchPreflightView:
        status = switch_preflight(_engine(request), user_id=owner)
        return SwitchPreflightView(available=status["available"], cause=status["cause"],
                                   days_remaining=status["days_remaining"])

    @app.post("/account/steam-switch/start", response_model=SteamStartView)
    async def steam_switch_start(request: Request, owner: Annotated[str, Depends(_user)],
                                 idempotency_key: Annotated[str, Header(min_length=8, max_length=200)]) -> SteamStartView:
        status = switch_preflight(_engine(request), user_id=owner)
        if not status["available"]:
            raise HTTPException(409, status["cause"])
        if not app.state.steam_callback_url:
            raise HTTPException(503, "STEAM_LINK_UNAVAILABLE")
        def publish() -> dict[str, object]:
            started = start_steam_switch(_engine(request), cast(RedisLike, _redis(request)),
                                         user_id=owner, callback_url=app.state.steam_callback_url)
            return {"authorization_url": started.authorization_url, "state": started.state}
        with _engine(request).begin() as connection:
            result = _idempotent(connection, owner=owner, operation="STEAM_SWITCH_START",
                key=idempotency_key, body={}, publish=publish)
        return SteamStartView.model_validate(result)

    @app.post("/account/steam-switch/complete", response_model=SteamCompleteView)
    async def steam_switch_complete(request: Request, body: SteamCompleteRequest,
                                    owner: Annotated[str, Depends(_user)],
                                    idempotency_key: Annotated[str, Header(min_length=8, max_length=200)]) -> SteamCompleteView:
        with _engine(request).begin() as connection:
            result = _idempotent(connection, owner=owner, operation="STEAM_SWITCH_COMPLETE",
                key=idempotency_key, body={"fields": body.fields},
                publish=lambda: {"linked": bool(complete_steam_switch(
                    connection, cast(RedisLike, _redis(request)), user_id=owner,
                    callback_fields=body.fields, verifier=app.state.steam_verifier,
                ))})
        return SteamCompleteView.model_validate(result)

    @app.get("/bootstrap", response_model=BootstrapView)
    async def bootstrap_status(request: Request, owner: Annotated[str, Depends(_user)]) -> BootstrapView:
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            found = {row["mode"]: row for row in connection.execute(select(bootstrap).where(
                bootstrap.c.profile_id == profile["id"],
            )).mappings()} if profile else {}
        return BootstrapView(modes=[BootstrapModeView(
            mode=mode, status="COMPLETE" if found.get(mode) and found[mode]["completed_at"] else
            "PROCESSING" if found.get(mode) and found[mode]["search_finished"] else
            "SEARCHING" if found.get(mode) else "NOT_STARTED",
            outcome=found[mode]["outcome"] if mode in found else "NO_STEAM_LINKED",
            discovered_count=found[mode]["discovered_count"] if mode in found else 0,
            eligible_count=found[mode]["eligible_count"] if mode in found else 0,
            settled_count=found[mode]["settled_count"] if mode in found else 0,
        ) for mode in Mode])

    @app.get("/readiness", response_model=SyncView)
    async def readiness(request: Request, owner: Annotated[str, Depends(_user)]) -> SyncView:
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            row = connection.execute(select(sync_state).where(
                sync_state.c.account_id == (profile["account_id"] if profile else -1),
                sync_state.c.provider == "opendota",
            )).mappings().one_or_none()
        return SyncView(state=row["state"] if row else "IDLE",
                        last_checked_at=row["last_checked_at"] if row else None)

    @app.post("/sync", response_model=SyncRequestView)
    async def sync(request: Request, owner: Annotated[str, Depends(_user)],
                   idempotency_key: Annotated[str, Header(min_length=8, max_length=200)]) -> SyncRequestView:
        with _engine(request).begin() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                raise HTTPException(409, "STEAM_LINK_REQUIRED")
            response = _idempotent(connection, owner=owner, operation="SYNC", key=idempotency_key,
                body={}, publish=lambda: {"accepted": request_account_sync(
                    connection, profile["account_id"], scope_days=7,
                ) is not None})
        return SyncRequestView.model_validate(response)

    @app.put("/devices/{device_ref}", status_code=204)
    async def register_device(request: Request, device_ref: UUID, body: DeviceRequest,
                              owner: Annotated[str, Depends(_user)]) -> None:
        with _engine(request).begin() as connection:
            existing = connection.scalar(select(devices.c.user_id).where(devices.c.id == str(device_ref)))
            if existing is not None and existing != owner:
                raise HTTPException(404, "DEVICE_NOT_FOUND")
            connection.execute(insert(devices).values(
                id=str(device_ref), user_id=owner, permission=body.permission,
                push_token=body.push_token, last_active_at=func.clock_timestamp(),
            ).on_conflict_do_update(index_elements=[devices.c.id], set_={
                "permission": body.permission, "push_token": body.push_token,
                "last_active_at": func.clock_timestamp(),
            }))

    @app.delete("/devices/{device_ref}", status_code=204)
    async def remove_device(request: Request, device_ref: UUID,
                            owner: Annotated[str, Depends(_user)]) -> None:
        with _engine(request).begin() as connection:
            connection.execute(devices.delete().where(
                devices.c.id == str(device_ref), devices.c.user_id == owner,
            ))

    @app.get("/matches/{match_ref}", response_model=MatchView)
    async def match_detail(request: Request, match_ref: str, owner: Annotated[str, Depends(_user)]) -> MatchView:
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            row = connection.execute(select(account_matches).where(
                account_matches.c.profile_id == (profile["id"] if profile else ""),
                account_matches.c.public_ref == match_ref,
                _visible(profile) if profile else true(),
            )).mappings().one_or_none()
            if row is None:
                raise HTTPException(404, "MATCH_NOT_FOUND")
            return _match_view(connection, row)

    @app.post("/matches/{match_ref}/retry", response_model=RetryView)
    async def retry(request: Request, match_ref: str, owner: Annotated[str, Depends(_user)],
                    idempotency_key: Annotated[str, Header(min_length=8, max_length=200)]) -> RetryView:
        with _engine(request).begin() as connection:
            def publish() -> dict[str, object]:
                try:
                    return {"accepted": retry_match(connection, user_id=owner, match_ref=match_ref)}
                except ValueError as exc:
                    code = str(exc)
                    raise HTTPException(404 if code == "MATCH_NOT_FOUND" else 409, code) from exc

            response = _idempotent(connection, owner=owner, operation="MATCH_RETRY",
                                   key=idempotency_key, body={"match_ref": match_ref}, publish=publish)
        return RetryView.model_validate(response)

    @app.get("/history", response_model=HistoryView)
    async def history(request: Request, owner: Annotated[str, Depends(_user)], mode: Mode,
                      role: Role | None = None, cursor: str | None = None,
                      limit: Annotated[int, Query(ge=1, le=50)] = 20) -> HistoryView:
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                return HistoryView(matches=[], next_cursor=None)
            query = select(account_matches).where(account_matches.c.profile_id == profile["id"],
                                                   account_matches.c.mode == mode.value, _visible(profile))
            if role is not None:
                query = query.where(account_matches.c.effective_role == role.value)
            if cursor is not None:
                pieces = cursor.split(".")
                if len(pieces) != 2 or not hmac.compare_digest(
                    cursor, _cursor(profile["id"], pieces[0], mode.value,
                                    role.value if role else None, profile["active_revision"]),
                ):
                    raise HTTPException(400, "CURSOR_INVALID")
                anchor = connection.execute(select(account_matches).where(
                    account_matches.c.profile_id == profile["id"],
                    account_matches.c.public_ref == pieces[0],
                    account_matches.c.mode == mode.value,
                )).mappings().one_or_none()
                if anchor is None or role is not None and anchor["effective_role"] != role.value:
                    raise HTTPException(400, "CURSOR_INVALID")
                query = query.where(or_(
                    account_matches.c.provider_started_at < anchor["provider_started_at"],
                    and_(account_matches.c.provider_started_at == anchor["provider_started_at"],
                         account_matches.c.provider_source_match_id < anchor["provider_source_match_id"]),
                ))
            rows = connection.execute(query.order_by(
                account_matches.c.provider_started_at.desc(),
                account_matches.c.provider_source_match_id.desc(),
            ).limit(limit + 1)).mappings().all()
            visible = rows[:limit]
            next_cursor = (_cursor(profile["id"], visible[-1]["public_ref"], mode.value,
                                   role.value if role else None, profile["active_revision"])
                           if len(rows) > limit else None)
            return HistoryView(matches=[_match_view(connection, row) for row in visible],
                               next_cursor=next_cursor)

    @app.get("/home", response_model=HomeView)
    async def home(request: Request, owner: Annotated[str, Depends(_user)], mode: Mode,
                   time_zone: str) -> HomeView:
        try:
            zone = ZoneInfo(time_zone)
        except ZoneInfoNotFoundError as exc:
            raise HTTPException(400, "TIME_ZONE_INVALID") from exc
        today = datetime.now(zone).date()
        start = datetime.combine(today, time.min, zone).astimezone(UTC)
        end = datetime.combine(today + timedelta(days=1), time.min, zone).astimezone(UTC)
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                return HomeView(mode=mode, local_date=today.isoformat(), today_matches=[], last_matches=[])
            base = select(account_matches).where(account_matches.c.profile_id == profile["id"], _visible(profile))
            today_rows = connection.execute(base.where(
                account_matches.c.provider_started_at >= start,
                account_matches.c.provider_started_at < end,
                account_matches.c.mode.in_(("STANDARD", "TURBO")),
            ).order_by(account_matches.c.provider_started_at.desc(),
                       account_matches.c.provider_source_match_id.desc()).limit(100)).mappings().all()
            last_rows = connection.execute(base.where(
                account_matches.c.mode == mode.value,
            ).order_by(account_matches.c.provider_started_at.desc(),
                       account_matches.c.provider_source_match_id.desc()).limit(5)).mappings().all()
            return HomeView(mode=mode, local_date=today.isoformat(),
                            today_matches=[_summary_view(connection, row) for row in today_rows],
                            last_matches=[_summary_view(connection, row) for row in last_rows])

    @app.get("/coverage", response_model=CoverageView)
    async def coverage_status(request: Request, owner: Annotated[str, Depends(_user)], mode: Mode) -> CoverageView:
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            rows = connection.execute(select(coverage).where(
                coverage.c.profile_id == (profile["id"] if profile else ""),
                coverage.c.mode == mode.value,
            ).order_by(coverage.c.start_at, coverage.c.evidence_class)).mappings().all()
        return CoverageView(mode=mode, intervals=[CoverageInterval(
            capability="MATCH_FACTS" if row["evidence_class"] == "SUMMARY" else "DETAILED_METRICS",
            start_at=row["start_at"], end_at=row["end_at"], state=row["state"],
        ) for row in rows])

    @app.get("/progress", response_model=ProgressView)
    async def progress(request: Request, owner: Annotated[str, Depends(_user)], mode: Mode,
                       role: Role, metric_id: str) -> ProgressView:
        if metric_id not in METRICS or not metric_id.startswith(role.value.lower() + "."):
            raise HTTPException(400, "METRIC_INVALID")
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                return ProgressView(mode=mode, role=role, metric_id=metric_id, points=[],
                                    personal_best=None, trend=TrendView(state="INSUFFICIENT_HISTORY",
                                                                          reason=None, point_count=0))
            rows = connection.execute(select(
                account_matches.c.public_ref, account_matches.c.match_id,
                account_matches.c.provider_started_at, metric_observations.c.comparison_value,
                metric_observations.c.baseline_snapshot,
            ).join(analyses, analyses.c.id == account_matches.c.active_analysis_id).join(
                metric_observations, metric_observations.c.analysis_id == analyses.c.id,
            ).where(
                account_matches.c.profile_id == profile["id"],
                _visible(profile),
                account_matches.c.lifecycle == "READY", account_matches.c.progression == mode.value,
                account_matches.c.effective_role == role.value,
                metric_observations.c.metric_id == metric_id,
                metric_observations.c.comparison_value.is_not(None),
            ).order_by(account_matches.c.provider_started_at,
                       account_matches.c.provider_source_match_id)).mappings().all()
            points = [ProgressPoint(
                match_ref=row["public_ref"], started_at=row["provider_started_at"],
                value=row["comparison_value"], baseline_value=row["baseline_snapshot"].get("value"),
                prior_count=row["baseline_snapshot"].get("prior_count", 0),
            ) for row in rows]
            trend = evaluate_trend(metric_id, [TrendPoint(
                row["match_id"], row["provider_started_at"], row["baseline_snapshot"].get("value"),
            ) for row in rows])
            pb = connection.execute(select(personal_bests.c.analysis_id,
                                           personal_bests.c.comparison_value).where(
                personal_bests.c.profile_id == profile["id"],
                personal_bests.c.revision == profile["active_revision"],
                personal_bests.c.mode == mode.value, personal_bests.c.role == role.value,
                personal_bests.c.metric_id == metric_id,
            )).one_or_none()
            pb_ref = connection.scalar(select(account_matches.c.public_ref).where(
                account_matches.c.active_analysis_id == pb.analysis_id,
                account_matches.c.profile_id == profile["id"],
            )) if pb else None
            personal = (PersonalBestView(match_ref=pb_ref, value=pb.comparison_value)
                        if pb is not None and pb_ref is not None else None)
        return ProgressView(mode=mode, role=role, metric_id=metric_id, points=points,
                            personal_best=personal, trend=TrendView(
                                state=cast(Literal["IMPROVING", "STABLE", "DECLINING", "INSUFFICIENT_HISTORY"] | None,
                                           trend["state"]),
                                reason="CALIBRATION_UNAVAILABLE" if trend["reason"] == "UNCALIBRATED" else None,
                                point_count=cast(int, trend["point_count"]),
                            ))

    return app

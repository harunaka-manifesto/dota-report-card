"""Isolated, typed mobile V1 boundary over tracker-owned persisted state."""
from __future__ import annotations

import hashlib
import hmac
import os
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from datetime import date as date_type
from enum import StrEnum
from typing import Annotated, Any, Literal, cast
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, JsonValue, field_validator
from redis import Redis
from sqlalchemy import Connection, Engine, and_, func, or_, select, text, true, tuple_
from sqlalchemy.dialects.postgresql import insert

from app.core.config import Settings
from app.storage.database import create_database_engine
from app.tracker import activity, hero_pool, match_list
from app.tracker.account_lifecycle import (
    AccountLifecycleError,
    request_account_deletion,
    switch_preflight,
)
from app.tracker.achievement_catalog import catalog_entry, rarity
from app.tracker.achievement_rules import REPEATABLE_FEATS, rules_digest
from app.tracker.achievement_rules import THRESHOLDS as ACHIEVEMENT_THRESHOLDS
from app.tracker.achievements import IDS as ACHIEVEMENT_IDS
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
from app.tracker.backfill import historical_work_pending
from app.tracker.bootstrap import resume_bootstrap_search
from app.tracker.context import METRIC_CLASS
from app.tracker.data_access import data_access_state, restore_access
from app.tracker.entitlement import AppStoreVerifier, EntitlementError, submit_transaction
from app.tracker.evidence import canonical_json
from app.tracker.mastery import (
    CURRENT_RULE,
    CURVE_VERSION,
    ROLES,
    level_for_xp,
    mastery_state,
    role_total,
)
from app.tracker.metrics import METRICS
from app.tracker.profile import more_arriving
from app.tracker.retry import retry_match
from app.tracker.role_correction import (
    RoleCorrectionConflict,
    RoleCorrectionUnavailable,
    correct_role,
    correction_available,
)
from app.tracker.roles import RolePolicy
from app.tracker.schema import (
    account_matches,
    analyses,
    bootstrap,
    coverage,
    devices,
    events,
    history_operations,
    idempotency_keys,
    identities,
    ingest_jobs,
    insight_results,
    mastery_ledger,
    match_players,
    matches,
    metric_observations,
    personal_bests,
    play_session_names,
    positions,
    profile_states,
    profiles,
    role_assertions,
    shares,
    subscriptions,
    sync_state,
    users,
)
from app.tracker.scope import entitled
from app.tracker.shares import ShareUnavailable, create_share, render_svg
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


class MasteryRoleView(BaseModel):
    role: Role
    state: Literal["UNSTARTED", "STARTED"]
    level: int | None
    xp_into_level: int | None
    xp_to_next_level: int | None
    total_xp: int | None
    saved_progress: bool


class MasteryMilestoneView(BaseModel):
    role: Role
    level: int
    created_at: datetime


class MasteryView(BaseModel):
    state: Literal["AVAILABLE", "BACKFILLING", "CALIBRATION_PENDING", "STEAM_LINK_REQUIRED"]
    curve_version: str
    roles: list[MasteryRoleView]
    milestones: list[MasteryMilestoneView]


class MasteryAwardView(BaseModel):
    kind: Literal["AWARD", "LATE_BONUS", "REVERSAL", "CORRECTION"]
    xp: int
    mode: Mode
    role: Role
    match_ref: str
    reason: str
    from_role: Role | None
    above_metric_ids: list[str]
    pb_metric_ids: list[str]
    rule_version: str
    analysis_version: str
    baseline_version: str
    parameter_set_version: str | None
    created_at: datetime


class MasteryAwardsView(BaseModel):
    awards: list[MasteryAwardView]
    next_cursor: str | None


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


class SubscriptionView(BaseModel):
    billing_state: Literal["NONE", "ACTIVE", "EXPIRED", "REVOKED"]
    expires_at: datetime | None
    auto_renew: bool | None
    scope: Literal["FREE", "PRO"]
    scope_revision: int
    scope_change: Literal["NONE", "PENDING", "RUNNING"]
    target_scope: Literal["FREE", "PRO"] | None


class TransactionRequest(BaseModel):
    signed_transaction: str = Field(min_length=20, max_length=64000)


class DeletionView(BaseModel):
    state: Literal["DELETION_PENDING"]


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
    diagnostic_only: bool = False
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
    # Versioned annex wording; it always states its sample size N.
    history_line: str | None = None


class InsightView(BaseModel):
    state: Readiness
    contract_version: str | None
    reason: str | None
    cards: list[InsightCardView]


class ItemTimingComparisonView(BaseModel):
    kind: Literal["POPULATION_USUAL", "PERSONAL_PREVIOUS_BEST", "PERSONAL_USUAL"]
    baseline_seconds: int
    delta_seconds: int
    sample_size: int
    cohort_patch: str


class ItemTimingView(BaseModel):
    item_id: int
    item_key: str
    item_name: str
    purchase_time_seconds: int
    key_item_order: int
    comparison: ItemTimingComparisonView | None


class ItemTimingsView(BaseModel):
    state: Readiness
    contract_version: Literal["item-timings-v1"] | None
    reason: str | None
    reference_digest: str | None
    items: list[ItemTimingView]


class OfflaneMinuteView(BaseModel):
    time_seconds: int
    you: int
    enemy_carry: int
    difference: int


class OfflanePanelView(BaseModel):
    state: Readiness
    reason: str | None
    points: list[OfflaneMinuteView]


class OfflaneFightSegmentView(BaseModel):
    segment_index: int
    start_seconds: int
    end_seconds: int
    offlaner_damage: int
    allied_damage_total: int
    damage_share: float | None
    damage_participated: bool
    offlaner_kills: int
    offlaner_deaths: int
    allied_hero_deaths: int
    enemy_hero_deaths: int
    death_trade: Literal["FAVORABLE", "EVEN", "UNFAVORABLE"]


class OfflaneFightsView(BaseModel):
    state: Readiness
    reason: str | None
    segments: list[OfflaneFightSegmentView]


class OfflaneContextView(BaseModel):
    contract_version: Literal["offlane-context-v2"]
    enemy_carry_hero_id: int | None
    net_worth: OfflanePanelView
    xp: OfflanePanelView
    fights: OfflaneFightsView


class CarryItemMarkerView(BaseModel):
    item_id: int
    item_key: str
    item_name: str
    purchase_time_seconds: int
    key_item_order: int


class CarryItemMarkersView(BaseModel):
    state: Readiness
    reason: str | None
    items: list[CarryItemMarkerView]


class CarryKillEventView(BaseModel):
    time_seconds: int


class CarryKillsView(BaseModel):
    state: Readiness
    reason: str | None
    events: list[CarryKillEventView]


class CarryContextView(BaseModel):
    contract_version: Literal["carry-context-v1"]
    enemy_carry_hero_id: int | None
    net_worth: OfflanePanelView
    hero_damage: OfflanePanelView
    enemy_key_items: CarryItemMarkersView
    you_kills: CarryKillsView
    enemy_carry_kills: CarryKillsView


class MidMinuteView(BaseModel):
    time_seconds: int
    you: int
    enemy_mid: int
    difference: int


class MidPanelView(BaseModel):
    state: Readiness
    reason: str | None
    points: list[MidMinuteView]


class MidContextView(BaseModel):
    contract_version: Literal["mid-context-v1"]
    enemy_mid_hero_id: int | None
    net_worth: MidPanelView


class CoreFightSegmentView(BaseModel):
    segment_index: int
    start_seconds: int
    end_seconds: int
    player_damage: int
    allied_damage_total: int
    damage_share: float | None
    damage_participated: bool
    player_kills: int
    player_deaths: int
    allied_hero_deaths: int
    enemy_hero_deaths: int
    death_trade: Literal["FAVORABLE", "EVEN", "UNFAVORABLE"]


class CoreFightsView(BaseModel):
    contract_version: Literal["core-fights-v1"]
    state: Readiness
    reason: str | None
    segments: list[CoreFightSegmentView]


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
    role_source: Literal["INFERRED", "USER_CONFIRMED"] | None = None
    role_confidence: Literal["HIGH", "LOW"] | None = None
    lane_context: Literal["DIFFICULT", "TYPICAL", "FAVOURABLE", "UNAVAILABLE"] = "UNAVAILABLE"
    progression: Literal["STANDARD", "TURBO", "NONE"] | None
    progression_reason: str | None
    won: bool
    players: list[PlayerFacts]
    metrics: list[MetricView]


class AchievementAwardView(BaseModel):
    id: int
    proof: dict[str, JsonValue]


class AchievementUnavailableView(BaseModel):
    id: int
    reason: Literal["EVIDENCE_MISSING", "MATCH_TOO_SHORT", "INSUFFICIENT_HISTORY"]


class AchievementMatchView(BaseModel):
    match_ref: str
    started_at: datetime
    proof: dict[str, JsonValue]


class AchievementRarityView(BaseModel):
    version: str
    tier: Literal["COMMON", "RARE", "EPIC", "LEGENDARY"]
    rate: float | None
    numerator: int | None
    denominator: int | None
    source: Literal["CORPUS", "MODEL"]
    provisional: bool


class AchievementProgressView(BaseModel):
    current: int
    target: int


class AchievementEntryView(BaseModel):
    id: int
    order: int
    key: str
    asset_key: str
    rule_version: str
    roles: list[str]
    name: str
    description: str
    how_to: str
    proof_template: str
    earned_count: int
    rarity: AchievementRarityView | None
    progress: AchievementProgressView | None
    latest_match: AchievementMatchView | None


class AchievementCollectionView(BaseModel):
    state: Literal["AVAILABLE", "BACKFILLING", "STEAM_LINK_REQUIRED"]
    entries: list[AchievementEntryView]


class MatchDetailView(MatchView):
    item_timings: ItemTimingsView
    offlane_context: OfflaneContextView | None
    carry_context: CarryContextView | None
    mid_context: MidContextView | None
    core_fights: CoreFightsView | None
    role_revision: int
    correction_available: bool
    # Current ownership (can change silently) versus the one-time celebration.
    owns_personal_best: list[str] = Field(default_factory=list)
    celebrated_personal_best: list[str] = Field(default_factory=list)
    achievement_state: Readiness = Readiness.PENDING
    achievements: list[AchievementAwardView] = Field(default_factory=list)
    # Role-eligible badges this match could not judge; absent from `achievements` by design.
    achievement_unavailable: list[AchievementUnavailableView] = Field(default_factory=list)


class RoleEditRequest(BaseModel):
    role: Role
    expected_role_revision: int = Field(ge=0)


class RoleEditView(BaseModel):
    role: Role
    role_revision: int
    rebuilt: bool
    rebuilt_match_count: int | None = None


class HistoryRow(BaseModel):
    """An identity row, never a miniature Match Detail (history §4)."""
    ref: str
    mode: Mode | None
    started_at: datetime
    duration_seconds: int
    hero_id: int
    won: bool
    role: Role | None
    lifecycle: Lifecycle
    progression: Literal["STANDARD", "TURBO", "NONE"] | None
    progression_reason: str | None
    has_insight_cards: bool
    owns_personal_best: bool


class HistoryView(BaseModel):
    matches: list[HistoryRow]
    next_cursor: str | None


class MatchSummary(BaseModel):
    ref: str
    mode: Mode | None
    started_at: datetime
    lifecycle: Lifecycle
    role: Role | None
    hero_id: int
    won: bool
    progression: Literal["STANDARD", "TURBO", "NONE"] | None = None
    progression_reason: str | None = None


class MetricTrendView(BaseModel):
    metric_id: str
    state: Literal["IMPROVING", "STABLE", "DECLINING", "INSUFFICIENT_HISTORY"] | None
    reason: Literal["CALIBRATION_UNAVAILABLE"] | None
    point_count: int


class RoleSummaryView(BaseModel):
    """Metric-named states only; no composite role verdict (home §6.2)."""
    role: Role
    state: Literal["UNSTARTED", "ACTIVE"]
    last_played_at: datetime | None
    metrics: list[MetricTrendView]


class SlotView(BaseModel):
    """An honest, non-fabricated slot: no content model is contracted (home §4–§5)."""
    state: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    reason: Literal["NOT_CONTRACTED"] = "NOT_CONTRACTED"


class ActivityRole(StrEnum):
    ALL = "ALL"
    CARRY = "CARRY"
    MID = "MID"
    OFFLANE = "OFFLANE"
    SUPPORT = "SUPPORT"


class ActivityDayView(BaseModel):
    date: date_type
    count: int = Field(ge=1)
    level: int = Field(ge=1, le=4)


class ActivitySeriesView(BaseModel):
    role: ActivityRole
    total_matches: int
    days: list[ActivityDayView]


class ActivityWindowView(BaseModel):
    start_date: date_type
    end_date: date_type


class ActivityPartialRangeView(BaseModel):
    start_date: date_type
    end_date: date_type
    reason: Literal["BOOTSTRAP_SAMPLE"]


class ActivityView(BaseModel):
    """READY Standard+Turbo matches per local day and role; presentation only (activity/SSOT.md)."""
    contract_version: Literal["activity-heatmap-v1"] = activity.CONTRACT
    levels_version: Literal["heatmap-levels-v1"] = activity.LEVELS_VERSION
    time_zone: str
    today: date_type
    window: ActivityWindowView | None
    available_years: list[int]
    partial_ranges: list[ActivityPartialRangeView]
    series: list[ActivitySeriesView]


class HeroPoolRole(StrEnum):
    CARRY = "CARRY"
    MID = "MID"
    OFFLANE = "OFFLANE"
    SUPPORT = "SUPPORT"


class HeroPoolWindow(StrEnum):
    LAST_7_DAYS = "LAST_7_DAYS"
    LAST_30_DAYS = "LAST_30_DAYS"
    LAST_365_DAYS = "LAST_365_DAYS"


class HeroPoolHeroView(BaseModel):
    hero_id: int = Field(ge=1)
    matches: int = Field(ge=1)


class HeroPoolWindowView(BaseModel):
    window: HeroPoolWindow
    start_date: date_type
    end_date: date_type
    total_matches: int
    heroes: list[HeroPoolHeroView]


class HeroPoolRoleView(BaseModel):
    role: HeroPoolRole
    windows: list[HeroPoolWindowView]


class HeroPoolView(BaseModel):
    """Most played heroes per role over trailing 7/30/365 days; presentation only (hero_pool/SSOT.md)."""
    contract_version: Literal["hero-pool-v1"] = hero_pool.CONTRACT
    time_zone: str
    today: date_type
    partial_ranges: list[ActivityPartialRangeView]
    roles: list[HeroPoolRoleView]


class MatchListRow(BaseModel):
    """History §4 identity row plus plain K/D/A; never a per-metric state or composite (matches/SSOT.md §2)."""
    ref: str
    mode: Mode
    started_at: datetime
    duration_seconds: int | None
    hero_id: int
    role: Role | None
    won: bool | None
    kills: int | None
    deaths: int | None
    assists: int | None
    lifecycle: Lifecycle
    progression: Literal["STANDARD", "TURBO", "NONE"] | None
    progression_reason: str | None
    has_insight_cards: bool
    owns_personal_best: bool


class PlaySessionHeaderView(BaseModel):
    """Whole-session facts, independent of the list's filters and search."""
    session_ref: str
    name: str
    name_is_custom: bool
    local_date: date_type
    started_at: datetime
    ended_at: datetime
    wins: int
    losses: int
    match_count: int


class PlaySessionView(PlaySessionHeaderView):
    matches: list[MatchListRow]


class MatchListView(BaseModel):
    """Standard and Turbo matches grouped into play sessions; presentation only (matches/SSOT.md)."""
    contract_version: Literal["matches-list-v1"] = match_list.CONTRACT
    time_zone: str
    has_matches: bool
    sessions: list[PlaySessionView]
    next_cursor: str | None


class PlaySessionNameRequest(BaseModel):
    """None restores the placeholder name."""
    name: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def _clean(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        if not value or len(value) > match_list.NAME_MAX or not value.isprintable():
            raise ValueError("SESSION_NAME_INVALID")
        return value


class HomeView(BaseModel):
    mode: Mode
    local_date: str
    today_matches: list[MatchSummary]
    last_matches: list[MatchSummary]
    role_summaries: list[RoleSummaryView] = Field(default_factory=list)
    focus: SlotView = Field(default_factory=SlotView)
    challenge: SlotView = Field(default_factory=SlotView)


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
    hero_id: int | None = None
    achieved_at: datetime | None = None


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
    data_access: Literal["ACCESSIBLE", "BLOCKED", "UNKNOWN"] = "UNKNOWN"


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


Tier = Literal["ANCHOR", "REGULAR", "OCCASIONAL", "RARE"]


class RoleRowView(BaseModel):
    role: Role
    count: int
    share: float | None
    tier: Tier | None


class IdentityLineView(BaseModel):
    template_id: Literal["MOSTLY_ROLE_SO_FAR", "BIT_OF_EVERYTHING"]
    role: Role | None
    confirmed: bool


class HeroCountView(BaseModel):
    hero_id: int
    count: int


class RoleHeroesView(BaseModel):
    role: Role
    role_matches: int
    most_played: list[HeroCountView]
    tags_state: Literal["INSUFFICIENT_MATCHES", "CALIBRATION_PENDING"]


class ProfileHeaderView(BaseModel):
    tracked_count: int
    eligible_count: int
    first_match_at: datetime | None
    last_played_at: datetime | None
    getting_to_know: bool
    bucket_phrase: Literal["MOSTLY_THIS_MODE", "STANDARD_AND_TURBO"]


class ProfilePersonalBestView(BaseModel):
    role: Role
    metric_id: str
    value: float
    match_ref: str | None
    hero_id: int | None
    achieved_at: datetime | None


class CelebrationView(BaseModel):
    metric_id: str
    match_ref: str | None
    celebrated_at: datetime


class ProfileChangeView(BaseModel):
    changed_at: datetime
    cause: Literal["PLAY", "ROLE_CORRECTION", "IMPORT", "ENTITLEMENT", "METHODOLOGY"]
    updated: bool


class ProfileCoverageView(BaseModel):
    earliest_known_at: datetime | None
    more_arriving: bool


class ProfileView(BaseModel):
    mode: Mode
    state: Literal["READY", "NOT_READY", "DATA_ACCESS_BLOCKED"]
    revision: int
    bucket_selector_visible: bool
    default_mode: Mode
    header: ProfileHeaderView | None
    identity: IdentityLineView | None
    role_shape_withheld: Literal["UNASSIGNED_ROLES"] | None
    role_map: list[RoleRowView]
    unassigned_count: int
    heroes: list[RoleHeroesView]
    favourite_hero_id: int | None
    claims_state: Literal["CALIBRATION_PENDING", "EVALUATED"]
    claims: list[InsightCardView]
    right_now_state: Literal["CALIBRATION_PENDING"]
    personal_bests_state: Literal["READY", "INSUFFICIENT"]
    personal_bests: list[ProfilePersonalBestView]
    recent_celebrations: list[CelebrationView]
    changes: list[ProfileChangeView]
    coverage: ProfileCoverageView


class FavouriteRequest(BaseModel):
    hero_id: int | None = Field(default=None, gt=0, lt=1000)


class ShareRequest(BaseModel):
    kind: Literal["PROFILE", "PERSONAL_BEST"]
    mode: Mode
    metric_id: str | None = None


class ShareView(BaseModel):
    ref: str
    kind: Literal["PROFILE", "PERSONAL_BEST"]
    mode: Mode
    generated_at: datetime
    role: Role | None = None
    metric_id: str | None = None
    label: str | None = None
    value: float | None = None
    hero_id: int | None = None
    achieved_on: str | None = None


class SettingsView(BaseModel):
    notifications_enabled: bool


class SettingsPatch(BaseModel):
    notifications_enabled: bool | None = None


class RecoveryView(BaseModel):
    data_access: Literal["ACCESSIBLE", "BLOCKED", "UNKNOWN"]
    identity_recovery: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    identity_recovery_reason: Literal["NOT_CONTRACTED"] = "NOT_CONTRACTED"


class DataAccessConfirmView(BaseModel):
    recovery: Literal["STARTED", "NOT_NEEDED"]


class HistoryOperationView(BaseModel):
    bootstrap: list[BootstrapModeView]
    scope_change: Literal["NONE", "PENDING", "RUNNING"]
    target_scope: Literal["FREE", "PRO"] | None
    history_import: Literal["NONE", "RUNNING", "COMPLETE"]
    access_recovery: Literal["NONE", "RUNNING", "COMPLETE"]
    data_access: Literal["ACCESSIBLE", "BLOCKED", "UNKNOWN"]


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
    return entitled(profile, account_matches)


def _achievements_current(data: Any) -> bool:
    return isinstance(data, dict) and data.get("rules_digest") == rules_digest()


def _achievement_state(row, data: Any) -> Readiness:
    if row["mode"] != "STANDARD" or row["lifecycle"] in {"UNAVAILABLE", "ACTION_REQUIRED"}:
        return Readiness.UNAVAILABLE
    if row["lifecycle"] != "READY" or not _achievements_current(data):
        return Readiness.PENDING  # not judged yet, or judged under older rules and awaiting the quiet rebuild
    return Readiness.UNAVAILABLE if data.get("eligible") is False else Readiness.AVAILABLE


def _achievement_collection(connection: Connection, profile, locale: str) -> AchievementCollectionView:
    locale = "id" if locale == "id" else "en"
    rows = [] if profile is None else connection.execute(select(
        account_matches.c.public_ref, account_matches.c.provider_started_at, match_players.c.hero_id,
        analyses.c.result["achievements"].label("achievements"),
        analyses.c.result["achievement_pb_metrics"].label("pb"),
    ).join(analyses, analyses.c.id == account_matches.c.active_analysis_id).join(
        match_players, (match_players.c.match_id == account_matches.c.match_id) &
        (match_players.c.player_slot == account_matches.c.player_slot),
    ).where(
        account_matches.c.profile_id == profile["id"], account_matches.c.mode == "STANDARD",
        account_matches.c.progression == "STANDARD", account_matches.c.lifecycle == "READY",
        _visible(profile),
    ).order_by(account_matches.c.provider_started_at, account_matches.c.provider_source_match_id)).mappings().all()
    counts: dict[int, int] = {ident: 0 for ident in ACHIEVEMENT_IDS}
    latest: dict[int, AchievementMatchView] = {}
    pb_heroes: dict[str, set[int]] = {}
    feat_matches: dict[tuple[int, int], int] = {}
    # Still importing history, or analyses awaiting the quiet rebuild: the counts are not final.
    backfilling = profile is not None and (
        connection.scalar(select(bootstrap.c.mode).where(
            bootstrap.c.profile_id == profile["id"], bootstrap.c.completed_at.is_(None)).limit(1)) is not None
        or historical_work_pending(connection, profile["id"]))
    for row in rows:
        data = row["achievements"]
        if not _achievements_current(data):
            backfilling = True
            continue
        for metric in row["pb"] or []:
            pb_heroes.setdefault(metric, set()).add(row["hero_id"])
        for award in data.get("awards", []):
            ident = award.get("id")
            if ident in counts:
                counts[ident] += 1
                latest[ident] = AchievementMatchView(match_ref=row["public_ref"],
                    started_at=row["provider_started_at"], proof=award["proof"])
                if ident in REPEATABLE_FEATS:
                    key = (row["hero_id"], ident)
                    feat_matches[key] = feat_matches.get(key, 0) + 1
    # Cross-match progress is computed from all visible current analyses, never from the latest match.
    progress = {
        4: AchievementProgressView(current=max((len(h) for h in pb_heroes.values()), default=0),
                                   target=ACHIEVEMENT_THRESHOLDS[4]["progress_target_heroes"]),
        30: AchievementProgressView(current=max(feat_matches.values(), default=0),
                                    target=ACHIEVEMENT_THRESHOLDS[30]["distinct_matches"]),
    }
    entries = [AchievementEntryView(**catalog_entry(ident, locale), earned_count=counts[ident],
        rarity=AchievementRarityView(**cast(dict[str, Any], rarity(ident))) if counts[ident] else None,
        progress=progress.get(ident) if not counts[ident] else None,
        latest_match=latest.get(ident)) for ident in ACHIEVEMENT_IDS]
    return AchievementCollectionView(state="STEAM_LINK_REQUIRED" if profile is None else
                                     "BACKFILLING" if backfilling else "AVAILABLE", entries=entries)


def _problem(status: int, code: str) -> JSONResponse:
    from uuid import uuid4

    return JSONResponse(status_code=status, media_type="application/problem+json", content={
        "type": "about:blank", "title": code.replace("_", " ").title(), "status": status,
        "code": code, "detail": code.replace("_", " ").lower(), "request_id": uuid4().hex,
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
        # Only canonical metrics: an analysis awaiting its methodology rebuild may still hold retired ones.
        observed = connection.execute(select(metric_observations).where(
            metric_observations.c.analysis_id == row["active_analysis_id"],
            metric_observations.c.metric_id.in_(METRICS),
        ).order_by(metric_observations.c.metric_id)).mappings()
        eligible = row["progression"] in {"STANDARD", "TURBO"}
        for metric in observed:
            baseline = metric["baseline_snapshot"]
            diagnostic = METRIC_CLASS.get(metric["metric_id"]) == "E"
            measured = metric["raw_value"] is not None
            metrics.append(MetricView(
                metric_id=metric["metric_id"], diagnostic_only=diagnostic,
                state="MEASURED" if measured else "NOT_AVAILABLE",
                raw_value=metric["raw_value"], comparison_value=metric["comparison_value"],
                unavailable_reason=metric["unavailable_reason"],
                # An ineligible match is fully viewable with no comparisons (match detail §7).
                baseline_state=("NOT_AVAILABLE" if not eligible else
                                "READY" if baseline.get("state") == "BASELINE_READY" else "BUILDING"),
                baseline_value=baseline.get("value") if eligible else None,
                prior_count=baseline.get("prior_count", 0) if eligible else 0,
                # Absent for N/A and diagnostic-only metrics (mobile draft state table).
                performance_state=metric["performance_state"] if eligible and measured and not diagnostic else None,
            ))
        result = connection.execute(select(insight_results).where(
            insight_results.c.analysis_id == row["active_analysis_id"],
        )).mappings().one_or_none()
        if result is not None:
            analysis = connection.execute(select(analyses.c.result).where(
                analyses.c.id == row["active_analysis_id"],
            )).scalar_one()
            status = analysis.get("insight_status", "NOT_ELIGIBLE(SOURCE_EVIDENCE)")
            evaluated = status == "EVALUATED"
            # A match whose replay never arrived shows the normal zero-card state.
            zero_card = (not evaluated and match["evidence_state"] == "REPLAY_UNAVAILABLE"
                         and row["progression"] in {"STANDARD", "TURBO"})
            insight = InsightView(
                state=Readiness.AVAILABLE if evaluated or zero_card else Readiness.UNAVAILABLE,
                contract_version=result["contract_version"],
                reason=None if evaluated or zero_card else status.removeprefix("NOT_ELIGIBLE(").removesuffix(")"),
                cards=[InsightCardView(template_id=card["candidate_id"], slots=card["slots"],
                                       history_line=card.get("history_line"))
                       for card in result["cards"]],
            )
    lane_context = "UNAVAILABLE"
    if row["active_analysis_id"] is not None:
        result = connection.scalar(select(analyses.c.result).where(analyses.c.id == row["active_analysis_id"]))
        lane_context = (result or {}).get("lane_context") or "UNAVAILABLE"
    confirmed = connection.scalar(select(role_assertions.c.revision).where(
        role_assertions.c.profile_id == row["profile_id"], role_assertions.c.match_id == row["match_id"],
    ).limit(1)) is not None
    confidence = None
    assignment = row["role_assignment"]
    if isinstance(assignment, dict) and row["effective_role"] is not None:
        if assignment.get("evidence_profile") == "SUMMARY":
            confidence = "LOW"  # summary-only classification is always low confidence
        else:
            score = connection.scalar(select(positions.c.confidence).where(
                positions.c.match_id == row["match_id"], positions.c.player_slot == row["player_slot"],
                positions.c.evidence_profile == assignment.get("evidence_profile"),
                positions.c.version == assignment.get("version"),
                positions.c.inputs_digest == assignment.get("inputs_digest"),
            ))
            if score is not None:
                confidence = "HIGH" if score >= RolePolicy().confidence_threshold else "LOW"
    terminal = row["lifecycle"] in {"UNAVAILABLE", "ACTION_REQUIRED"}
    if terminal and row["active_analysis_id"] is None:
        # No endless pending section: a failed match states a terminal outcome.
        insight = InsightView(state=Readiness.UNAVAILABLE, contract_version=None,
                              reason="MATCH_" + row["lifecycle"], cards=[])
    return MatchView(
        ref=row["public_ref"], mode=match["mode"] if match["mode"] in {"STANDARD", "TURBO"} else None,
        role_source=None if row["effective_role"] is None else "USER_CONFIRMED" if confirmed else "INFERRED",
        role_confidence=None if confirmed else cast(Literal["HIGH", "LOW"] | None, confidence),
        lane_context=cast(Literal["DIFFICULT", "TYPICAL", "FAVOURABLE", "UNAVAILABLE"], lane_context),
        started_at=row["provider_started_at"], duration_seconds=match["duration_seconds"],
        lifecycle=_lifecycle(row["lifecycle"]), facts=Readiness.AVAILABLE,
        performance=(Readiness.AVAILABLE if row["lifecycle"] == "READY" else
                     Readiness.UNAVAILABLE if terminal else Readiness.PENDING),
        insights=insight, role=row["effective_role"], progression=row["progression"],
        progression_reason=row["progression_reason"],
        won=match["radiant_win"] == (row["player_slot"] < 5), players=players, metrics=metrics,
    )


def _item_timings_view(connection: Connection, row) -> ItemTimingsView:
    if row["active_analysis_id"] is None:
        terminal = row["lifecycle"] in {"UNAVAILABLE", "ACTION_REQUIRED"}
        return ItemTimingsView(
            state=Readiness.UNAVAILABLE if terminal else Readiness.PENDING,
            contract_version=None,
            reason="MATCH_" + row["lifecycle"] if terminal else None,
            reference_digest=None,
            items=[],
        )
    result = connection.scalar(select(analyses.c.result).where(
        analyses.c.id == row["active_analysis_id"],
    ))
    timing = result.get("item_timings") if isinstance(result, dict) else None
    if not isinstance(timing, dict):
        return ItemTimingsView(
            state=Readiness.UNAVAILABLE,
            contract_version=None,
            reason="ANALYSIS_VERSION",
            reference_digest=None,
            items=[],
        )
    return ItemTimingsView(
        state=timing.get("state", "UNAVAILABLE"),
        contract_version=timing.get("contract_version"),
        reason=timing.get("reason"),
        reference_digest=timing.get("reference_digest"),
        items=timing.get("items", []),
    )


def _offlane_context_view(connection: Connection, row) -> OfflaneContextView | None:
    if row["effective_role"] != "OFFLANE":
        return None
    if row["active_analysis_id"] is None:
        terminal = row["lifecycle"] in {"UNAVAILABLE", "ACTION_REQUIRED"}
        state = Readiness.UNAVAILABLE if terminal else Readiness.PENDING
        reason = "MATCH_" + row["lifecycle"] if terminal else None
        panel = OfflanePanelView(state=state, reason=reason, points=[])
        fights = OfflaneFightsView(state=state, reason=reason, segments=[])
        return OfflaneContextView(contract_version="offlane-context-v2", enemy_carry_hero_id=None,
                                  net_worth=panel, xp=panel.model_copy(deep=True), fights=fights)
    result = connection.scalar(select(analyses.c.result).where(
        analyses.c.id == row["active_analysis_id"],
    ))
    context = result.get("offlane_context") if isinstance(result, dict) else None
    if isinstance(context, dict) and context.get("contract_version") == "offlane-context-v2":
        return OfflaneContextView.model_validate(context)
    panel = OfflanePanelView(state=Readiness.UNAVAILABLE, reason="ANALYSIS_VERSION", points=[])
    fights = OfflaneFightsView(state=Readiness.UNAVAILABLE, reason="ANALYSIS_VERSION", segments=[])
    return OfflaneContextView(contract_version="offlane-context-v2", enemy_carry_hero_id=None,
                              net_worth=panel, xp=panel.model_copy(deep=True), fights=fights)


def _carry_context_view(connection: Connection, row) -> CarryContextView | None:
    if row["effective_role"] != "CARRY":
        return None
    context = None
    if row["active_analysis_id"] is not None:
        result = connection.scalar(select(analyses.c.result).where(
            analyses.c.id == row["active_analysis_id"],
        ))
        context = result.get("carry_context") if isinstance(result, dict) else None
    if isinstance(context, dict) and context.get("contract_version") == "carry-context-v1":
        return CarryContextView.model_validate(context)
    terminal = row["lifecycle"] in {"UNAVAILABLE", "ACTION_REQUIRED"}
    state = Readiness.UNAVAILABLE if terminal or row["active_analysis_id"] is not None else Readiness.PENDING
    reason = "MATCH_" + row["lifecycle"] if terminal else "ANALYSIS_VERSION" if row["active_analysis_id"] is not None else None
    panel = OfflanePanelView(state=state, reason=reason, points=[])
    items = CarryItemMarkersView(state=state, reason=reason, items=[])
    kills = CarryKillsView(state=state, reason=reason, events=[])
    return CarryContextView(contract_version="carry-context-v1", enemy_carry_hero_id=None,
                            net_worth=panel, hero_damage=panel.model_copy(deep=True),
                            enemy_key_items=items, you_kills=kills,
                            enemy_carry_kills=kills.model_copy(deep=True))


def _mid_context_view(connection: Connection, row) -> MidContextView | None:
    if row["effective_role"] != "MID":
        return None
    context = None
    if row["active_analysis_id"] is not None:
        result = connection.scalar(select(analyses.c.result).where(
            analyses.c.id == row["active_analysis_id"],
        ))
        context = result.get("mid_context") if isinstance(result, dict) else None
    if isinstance(context, dict) and context.get("contract_version") == "mid-context-v1":
        return MidContextView.model_validate(context)
    terminal = row["lifecycle"] in {"UNAVAILABLE", "ACTION_REQUIRED"}
    state = Readiness.UNAVAILABLE if terminal or row["active_analysis_id"] is not None else Readiness.PENDING
    reason = "MATCH_" + row["lifecycle"] if terminal else "ANALYSIS_VERSION" if row["active_analysis_id"] is not None else None
    return MidContextView(contract_version="mid-context-v1", enemy_mid_hero_id=None,
                          net_worth=MidPanelView(state=state, reason=reason, points=[]))


def _core_fights_view(connection: Connection, row) -> CoreFightsView | None:
    if row["effective_role"] not in {"CARRY", "MID", "OFFLANE"}:
        return None
    context = None
    if row["active_analysis_id"] is not None:
        result = connection.scalar(select(analyses.c.result).where(
            analyses.c.id == row["active_analysis_id"],
        ))
        context = result.get("core_fights") if isinstance(result, dict) else None
    if isinstance(context, dict) and context.get("contract_version") == "core-fights-v1":
        return CoreFightsView.model_validate(context)
    terminal = row["lifecycle"] in {"UNAVAILABLE", "ACTION_REQUIRED"}
    state = Readiness.UNAVAILABLE if terminal or row["active_analysis_id"] is not None else Readiness.PENDING
    reason = "MATCH_" + row["lifecycle"] if terminal else "ANALYSIS_VERSION" if row["active_analysis_id"] is not None else None
    return CoreFightsView(contract_version="core-fights-v1", state=state, reason=reason, segments=[])


def _summary_view(connection, row) -> MatchSummary:
    match = connection.execute(select(matches.c.radiant_win).where(
        matches.c.match_id == row["match_id"],
    )).one()
    hero_id = connection.scalar(select(match_players.c.hero_id).where(
        match_players.c.match_id == row["match_id"],
        match_players.c.player_slot == row["player_slot"],
    ))
    return MatchSummary(
        ref=row["public_ref"], mode=row["mode"] if row["mode"] in {"STANDARD", "TURBO"} else None,
        started_at=row["provider_started_at"],
        lifecycle=_lifecycle(row["lifecycle"]), role=row["effective_role"], hero_id=hero_id,
        won=match.radiant_win == (row["player_slot"] < 5),
        progression=row["progression"], progression_reason=row["progression_reason"],
    )


def _history_row(connection, row) -> HistoryRow:
    match = connection.execute(select(matches.c.radiant_win, matches.c.duration_seconds).where(
        matches.c.match_id == row["match_id"])).one()
    hero_id = connection.scalar(select(match_players.c.hero_id).where(
        match_players.c.match_id == row["match_id"], match_players.c.player_slot == row["player_slot"]))
    cards = connection.scalar(select(insight_results.c.cards).where(
        insight_results.c.analysis_id == row["active_analysis_id"])) if row["active_analysis_id"] else None
    owns = connection.scalar(select(personal_bests.c.metric_id).join(
        profiles, (profiles.c.id == personal_bests.c.profile_id)
        & (profiles.c.active_revision == personal_bests.c.revision)).where(
        personal_bests.c.analysis_id == row["active_analysis_id"]).limit(1)) if row["active_analysis_id"] else None
    return HistoryRow(
        ref=row["public_ref"], mode=row["mode"] if row["mode"] in {"STANDARD", "TURBO"} else None,
        started_at=row["provider_started_at"], duration_seconds=match.duration_seconds, hero_id=hero_id,
        won=match.radiant_win == (row["player_slot"] < 5), role=row["effective_role"],
        lifecycle=_lifecycle(row["lifecycle"]), progression=row["progression"],
        progression_reason=row["progression_reason"], has_insight_cards=bool(cards), owns_personal_best=owns is not None,
    )


def _role_summaries(connection, profile, mode: str) -> list[RoleSummaryView]:
    summaries = []
    for role in Role:
        last = connection.scalar(select(func.max(account_matches.c.provider_started_at)).where(
            account_matches.c.profile_id == profile["id"], account_matches.c.progression == mode,
            account_matches.c.effective_role == role.value, account_matches.c.lifecycle == "READY",
            _visible(profile)))
        trends = []
        for metric_id in sorted(metric for metric in METRICS if metric.startswith(role.value.lower() + ".")):
            rows = connection.execute(select(
                account_matches.c.match_id, account_matches.c.provider_started_at,
                metric_observations.c.baseline_snapshot,
            ).join(metric_observations, metric_observations.c.analysis_id == account_matches.c.active_analysis_id).where(
                account_matches.c.profile_id == profile["id"], _visible(profile),
                account_matches.c.lifecycle == "READY", account_matches.c.progression == mode,
                account_matches.c.effective_role == role.value, metric_observations.c.metric_id == metric_id,
                metric_observations.c.comparison_value.is_not(None),
            ).order_by(account_matches.c.provider_started_at, account_matches.c.provider_source_match_id)).mappings().all()
            trend = evaluate_trend(metric_id, [TrendPoint(r["match_id"], r["provider_started_at"],
                                                          r["baseline_snapshot"].get("value")) for r in rows])
            trends.append(MetricTrendView(
                metric_id=metric_id,
                state=cast(Literal["IMPROVING", "STABLE", "DECLINING", "INSUFFICIENT_HISTORY"] | None, trend["state"]),
                reason="CALIBRATION_UNAVAILABLE" if trend["reason"] == "UNCALIBRATED" else None,
                point_count=cast(int, trend["point_count"])))
        summaries.append(RoleSummaryView(role=role, state="ACTIVE" if last else "UNSTARTED",
                                         last_played_at=last, metrics=trends))
    return summaries


DEVELOPMENT_CURSOR_SECRET = b"tracker-development-cursor-secret"


def cursor_secret(settings: Settings) -> bytes | None:
    """Server-held MAC key for opaque cursors; None when production lacks one.

    This app is mounted inside the live legacy API, so a missing secret must
    not stop startup: cursor endpoints fail closed instead. Rotating the secret
    invalidates outstanding cursors (History answers CURSOR_INVALID, Changes
    asks for a full refresh), so clients recover by refetching.
    """
    value = os.getenv("TRACKER_CURSOR_SECRET", "")
    if len(value) >= 32:
        return value.encode("utf-8")
    if settings.app_env == "production":
        return None
    return DEVELOPMENT_CURSOR_SECRET


def _cursor_key(request: Request) -> bytes:
    key: bytes | None = request.app.state.cursor_key
    if key is None:
        raise HTTPException(503, "CURSOR_SECRET_UNCONFIGURED")
    return key


def _mac(key: bytes, profile_id: str, message: str) -> str:
    return hmac.new(key, f"{profile_id}|{message}".encode("ascii"), hashlib.sha256).hexdigest()[:24]


def _cursor(key: bytes, profile_id: str, ref: str, mode: str, role: str | None, revision: int,
            day: str = "") -> str:
    # `day` binds the optional local-day drill-in filter; unfiltered cursors keep their shape.
    message = f"{ref}:{mode}:{role or ''}:{revision}" + (f":{day}" if day else "")
    return f"{ref}.{_mac(key, profile_id, message)}"


_TIME_ZONES = frozenset(available_timezones())


def _zone(time_zone: str) -> ZoneInfo:
    # Only real tz database names: ZoneInfo also opens files such as `posixrules`.
    if time_zone not in _TIME_ZONES:
        raise HTTPException(400, "TIME_ZONE_INVALID")
    try:
        return ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise HTTPException(400, "TIME_ZONE_INVALID") from exc


def _counted(profile: Any) -> Any:
    """READY Standard+Turbo matches in the entitled scope (activity/SSOT.md §1, hero_pool/SSOT.md)."""
    return and_(account_matches.c.profile_id == profile["id"], _visible(profile),
                account_matches.c.lifecycle == "READY",
                account_matches.c.mode.in_(("STANDARD", "TURBO")))


def _play_rows(connection: Connection, profile: Any) -> list[Any]:
    """Every visible Standard and Turbo link; unsupported modes never show or bridge sessions."""
    return list(connection.execute(select(
        account_matches.c.match_id, account_matches.c.public_ref, account_matches.c.provider_started_at,
        account_matches.c.provider_source_match_id, account_matches.c.player_slot, account_matches.c.mode,
        account_matches.c.effective_role, account_matches.c.lifecycle, account_matches.c.progression,
        account_matches.c.progression_reason, account_matches.c.active_analysis_id,
        matches.c.duration_seconds, matches.c.radiant_win, match_players.c.hero_id,
    ).select_from(account_matches.join(matches, matches.c.match_id == account_matches.c.match_id).join(
        match_players, (match_players.c.match_id == account_matches.c.match_id) &
        (match_players.c.player_slot == account_matches.c.player_slot),
    )).where(account_matches.c.profile_id == profile["id"], _visible(profile),
             account_matches.c.mode.in_(("STANDARD", "TURBO")))).mappings())


def _fact(row: Any) -> match_list.Fact:
    won = None if row["radiant_win"] is None else row["radiant_win"] == (row["player_slot"] < 5)
    return match_list.Fact(ref=row["public_ref"], started_at=row["provider_started_at"],
                           source_id=row["provider_source_match_id"], duration_seconds=row["duration_seconds"],
                           hero_id=row["hero_id"], role=row["effective_role"], mode=row["mode"], won=won)


def _play_sessions(connection: Connection, profile: Any, zone: ZoneInfo,
                   rows: list[Any]) -> list[tuple[PlaySessionHeaderView, list[Any]]]:
    """Newest first; each session's rows newest first, with its custom or placeholder name."""
    by_ref = {row["public_ref"]: row for row in rows}
    names = {row.match_id: (row.name, row.updated_at) for row in connection.execute(select(
        play_session_names.c.match_id, play_session_names.c.name, play_session_names.c.updated_at,
    ).where(play_session_names.c.profile_id == profile["id"]))}
    result = []
    for members in reversed(match_list.sessions(_fact(row) for row in rows)):
        member_rows = [by_ref[fact.ref] for fact in members]
        # A merge (a late match bridging two sessions) keeps the most recently chosen name.
        custom = max((names[row["match_id"]] for row in member_rows if row["match_id"] in names),
                     key=lambda item: item[1], default=None)
        head = PlaySessionHeaderView.model_validate({
            "session_ref": members[0].ref,
            "name": custom[0] if custom else match_list.placeholder_name(members, zone),
            "name_is_custom": custom is not None,
            "local_date": members[0].started_at.astimezone(zone).date(),
            **match_list.header(members)})
        result.append((head, list(reversed(member_rows))))
    return result


def _list_rows(connection: Connection, rows: list[Any]) -> dict[int, MatchListRow]:
    """Page rows with K/D/A, insight and PB markers in three batched reads."""
    if not rows:
        return {}
    summaries = {row.match_id: row.summary for row in connection.execute(select(
        match_players.c.match_id, match_players.c.summary,
    ).where(tuple_(match_players.c.match_id, match_players.c.player_slot).in_(
        [(row["match_id"], row["player_slot"]) for row in rows])))}
    analysis_ids = [row["active_analysis_id"] for row in rows if row["active_analysis_id"]]
    carded = set(connection.scalars(select(insight_results.c.analysis_id).where(
        insight_results.c.analysis_id.in_(analysis_ids),
        func.jsonb_array_length(insight_results.c.cards) > 0,
    ))) if analysis_ids else set()
    owning = set(connection.scalars(select(personal_bests.c.analysis_id).join(
        profiles, (profiles.c.id == personal_bests.c.profile_id)
        & (profiles.c.active_revision == personal_bests.c.revision)).where(
        personal_bests.c.analysis_id.in_(analysis_ids)))) if analysis_ids else set()
    views = {}
    for row in rows:
        fact = _fact(row)
        values = (summaries.get(row["match_id"]) or {}).get("values", {})
        views[row["match_id"]] = MatchListRow(
            ref=row["public_ref"], mode=row["mode"], started_at=row["provider_started_at"],
            duration_seconds=row["duration_seconds"], hero_id=row["hero_id"], role=row["effective_role"],
            won=fact.won, kills=values.get("kills"), deaths=values.get("deaths"), assists=values.get("assists"),
            lifecycle=_lifecycle(row["lifecycle"]), progression=row["progression"],
            progression_reason=row["progression_reason"],
            has_insight_cards=row["active_analysis_id"] in carded,
            owns_personal_best=row["active_analysis_id"] in owning)
    return views


def _bootstrap_partial(connection: Connection, profile: Any, zone: ZoneInfo, start: date_type,
                       end: date_type) -> ActivityPartialRangeView | None:
    """Bootstrap-only pre-link span inside start..end; Pro backfill covers it fully."""
    first_at, historical = connection.execute(select(
        func.min(account_matches.c.provider_started_at),
        func.count().filter(account_matches.c.origin == "HISTORICAL"),
    ).where(_counted(profile), or_(account_matches.c.origin == "BOOTSTRAP",
                                   account_matches.c.origin == "HISTORICAL"))).one()
    if first_at is None or historical:
        return None
    span_start = max(start, first_at.astimezone(zone).date())
    span_end = min(end, profile["original_linked_at"].astimezone(zone).date())
    if span_start > span_end:
        return None
    return ActivityPartialRangeView(start_date=span_start, end_date=span_end, reason="BOOTSTRAP_SAMPLE")


def _mastery_cursor(key: bytes, profile_id: str, ref: str, role: str, revision: int) -> str:
    return f"{ref}.{_mac(key, profile_id, f'mastery:{role}:{revision}:{ref}')}"


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


def _bootstrap_views(connection: Connection, profile) -> list[BootstrapModeView]:
    found = {row["mode"]: row for row in connection.execute(select(bootstrap).where(
        bootstrap.c.profile_id == profile["id"],
    )).mappings()} if profile else {}
    return [BootstrapModeView(
        mode=mode, status="COMPLETE" if found.get(mode) and found[mode]["completed_at"] else
        "PROCESSING" if found.get(mode) and found[mode]["search_finished"] else
        "SEARCHING" if found.get(mode) else "NOT_STARTED",
        outcome=found[mode]["outcome"] if mode in found else "NO_STEAM_LINKED",
        discovered_count=found[mode]["discovered_count"] if mode in found else 0,
        eligible_count=found[mode]["eligible_count"] if mode in found else 0,
        settled_count=found[mode]["settled_count"] if mode in found else 0,
    ) for mode in Mode]


def _job_state(connection: Connection, profile_id: str, job_type: str) -> Literal["NONE", "RUNNING", "COMPLETE"]:
    states = set(connection.scalars(select(ingest_jobs.c.state).where(
        ingest_jobs.c.profile_id == profile_id, ingest_jobs.c.job_type == job_type)))
    if states & {"PENDING", "RUNNING"}:
        return "RUNNING"
    return "COMPLETE" if states else "NONE"


def _profile_view(connection: Connection, profile, mode: Mode) -> ProfileView:
    states = {row["mode"]: row for row in connection.execute(select(profile_states).where(
        profile_states.c.profile_id == profile["id"])).mappings()}
    headers = {key: row["state"]["header"] for key, row in states.items()}
    selector = all(headers.get(m.value, {}).get("eligible_count", 0) >= 30 for m in Mode)
    recent = {m: headers.get(m.value, {}).get("recent_eligible_count", 0) for m in Mode}
    default_mode = Mode.TURBO if recent[Mode.TURBO] > recent[Mode.STANDARD] else Mode.STANDARD
    blocked = data_access_state(connection, profile["account_id"]) == "BLOCKED"
    stored = states.get(mode.value)
    state = stored["state"] if stored else None
    revision = profile["active_revision"]
    pbs = connection.execute(select(
        personal_bests.c.role, personal_bests.c.metric_id, personal_bests.c.comparison_value,
        account_matches.c.public_ref, account_matches.c.provider_started_at, match_players.c.hero_id,
    ).join(analyses, analyses.c.id == personal_bests.c.analysis_id).outerjoin(
        account_matches, (account_matches.c.profile_id == personal_bests.c.profile_id)
        & (account_matches.c.match_id == analyses.c.match_id)).outerjoin(
        match_players, (match_players.c.match_id == account_matches.c.match_id)
        & (match_players.c.player_slot == account_matches.c.player_slot)).where(
        personal_bests.c.profile_id == profile["id"], personal_bests.c.revision == revision,
        personal_bests.c.mode == mode.value,
    ).order_by(personal_bests.c.role, personal_bests.c.metric_id)).mappings().all()
    celebrated = connection.execute(select(events.c.payload, events.c.created_at).where(
        events.c.profile_id == profile["id"], events.c.kind == "NEW_PB",
    ).order_by(events.c.created_at.desc())).mappings().all()
    celebrations: list[CelebrationView] = []
    for event in celebrated:
        link = connection.execute(select(account_matches.c.public_ref, account_matches.c.mode).where(
            account_matches.c.profile_id == profile["id"],
            account_matches.c.match_id == event["payload"].get("match_id"), _visible(profile),
        )).first()
        if link is None or link.mode != mode.value:
            continue
        celebrations.append(CelebrationView(metric_id=event["payload"]["metric_id"], match_ref=link.public_ref,
                                            celebrated_at=event["created_at"]))
        if len(celebrations) == 3:
            break
    changes_rows = connection.execute(select(events.c.payload, events.c.created_at).where(
        events.c.profile_id == profile["id"], events.c.kind == "PROFILE_CHANGE",
        events.c.payload["mode"].astext == mode.value,
    ).order_by(events.c.created_at.desc())).mappings().all()
    changes = [ProfileChangeView(
        changed_at=row["created_at"], cause=row["payload"]["cause"],
        updated=any(later["payload"]["cause"] == "ROLE_CORRECTION" for later in changes_rows[:index]),
    ) for index, row in enumerate(changes_rows)]
    header = None
    if state:
        head = state["header"]
        header = ProfileHeaderView(
            tracked_count=head["tracked_count"], eligible_count=head["eligible_count"],
            first_match_at=head["first_match_at"], last_played_at=head["last_played_at"],
            getting_to_know=head["getting_to_know"],
            bucket_phrase="MOSTLY_THIS_MODE" if head["mostly_this_mode"] else "STANDARD_AND_TURBO")
    identity = state.get("identity") if state else None
    return ProfileView(
        mode=mode, state="DATA_ACCESS_BLOCKED" if blocked else "READY" if state else "NOT_READY",
        revision=revision, bucket_selector_visible=selector, default_mode=default_mode, header=header,
        identity=IdentityLineView(template_id=identity["template_id"], role=identity["slots"].get("role"),
                                  confirmed=identity["confirmed"]) if identity else None,
        role_shape_withheld=state.get("role_shape_withheld") if state else None,
        role_map=[RoleRowView(**row) for row in state["role_map"]] if state else [],
        unassigned_count=state["unassigned_count"] if state else 0,
        heroes=[RoleHeroesView(**row) for row in state["heroes"]] if state else [],
        favourite_hero_id=profile["favourite_hero_id"],
        claims_state=state["claims_state"] if state else "CALIBRATION_PENDING", claims=[],
        right_now_state="CALIBRATION_PENDING",
        personal_bests_state="READY" if pbs else "INSUFFICIENT",
        personal_bests=[ProfilePersonalBestView(
            role=row["role"], metric_id=row["metric_id"], value=row["comparison_value"],
            match_ref=row["public_ref"], hero_id=row["hero_id"], achieved_at=row["provider_started_at"],
        ) for row in pbs],
        recent_celebrations=celebrations, changes=changes,
        coverage=ProfileCoverageView(
            earliest_known_at=state["coverage"]["earliest_known_at"] if state else None,
            more_arriving=more_arriving(connection, profile["id"], mode.value)),
    )


def _changes_cursor(key: bytes, profile_id: str, at: datetime, revision: int) -> str:
    micros = round(at.timestamp() * 1_000_000)
    return f"{micros}.{revision}.{_mac(key, profile_id, f'changes:{micros}|{revision}')}"


def _subscription_view(connection: Connection, owner: str) -> SubscriptionView:
    now = connection.execute(select(func.clock_timestamp())).scalar_one()
    profile = _active_profile(connection, owner)
    receipts = connection.execute(select(subscriptions).where(
        subscriptions.c.user_id == owner,
    ).order_by(subscriptions.c.signed_at.desc())).mappings().all()
    active = next((receipt for receipt in receipts if receipt["expires_at"] > now and
                   (receipt["revoked_at"] is None or receipt["revoked_at"] > now)), None)
    latest = active or (receipts[0] if receipts else None)
    operation = connection.execute(select(
        history_operations.c.state, history_operations.c.target_scope,
    ).where(
        history_operations.c.profile_id == (profile["id"] if profile else ""),
        history_operations.c.kind == "ENTITLEMENT_REBUILD",
        history_operations.c.state.in_(("PENDING", "RUNNING")),
    ).limit(1)).first()
    billing_state: Literal["NONE", "ACTIVE", "EXPIRED", "REVOKED"] = "ACTIVE" if active else (
        "NONE" if latest is None else "REVOKED" if latest["revoked_at"] is not None and
        latest["revoked_at"] <= now else "EXPIRED")
    return SubscriptionView(
        billing_state=billing_state, expires_at=latest["expires_at"] if latest else None,
        auto_renew=latest["auto_renew"] if latest else None,
        scope=profile["active_scope"] if profile else "FREE",
        scope_revision=profile["active_revision"] if profile else 0,
        scope_change=operation.state if operation else "NONE",
        target_scope=operation.target_scope if operation else None,
    )


def create_mobile_app(settings: Settings, *, database: Engine | None = None, redis: Redis | None = None,
                      audiences: dict[str, set[str]] | None = None, steam_callback_url: str | None = None,
                      store_verifier: AppStoreVerifier | None = None) -> FastAPI:
    app = FastAPI(title="Dota Tracker Mobile API", version="1.0.0", openapi_url="/openapi.json")
    app.state.settings = settings
    app.state.database = database
    app.state.redis = redis
    app.state.audiences = audiences or {}
    app.state.steam_callback_url = steam_callback_url
    app.state.jwks = HttpJwksSource()
    app.state.steam_verifier = HttpSteamAssertionVerifier()
    app.state.store_verifier = store_verifier
    app.state.cursor_key = cursor_secret(settings)

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

    @app.get("/subscription", response_model=SubscriptionView)
    async def subscription(request: Request, owner: Annotated[str, Depends(_user)]) -> SubscriptionView:
        with _engine(request).connect() as connection:
            return _subscription_view(connection, owner)

    @app.post("/subscription/transactions", response_model=SubscriptionView)
    async def submit_store_transaction(
        request: Request, body: TransactionRequest, owner: Annotated[str, Depends(_user)],
        idempotency_key: Annotated[str, Header(min_length=8, max_length=200)],
    ) -> SubscriptionView:
        verifier = app.state.store_verifier
        if verifier is None:
            raise HTTPException(503, "STORE_UNAVAILABLE")
        digest = hashlib.sha256(body.signed_transaction.encode()).hexdigest()
        with _engine(request).begin() as connection:
            # Reserve the key first so a replay returns the earlier outcome
            # without re-verifying or re-applying the transaction.
            def publish() -> dict[str, object]:
                return {"submitted": True}

            _idempotent(connection, owner=owner, operation="STORE_TRANSACTION", key=idempotency_key,
                        body={"transaction_digest": digest}, publish=publish)
        try:
            submit_transaction(_engine(request), user_id=owner, signed_transaction=body.signed_transaction,
                               verifier=verifier)
        except EntitlementError as exc:
            message = str(exc)
            code = ("STEAM_LINK_REQUIRED" if "Steam" in message else
                    "TRANSACTION_OWNED_ELSEWHERE" if "another account" in message or "does not match" in message else
                    "TRANSACTION_INVALID")
            raise HTTPException(409 if code != "TRANSACTION_INVALID" else 400, code) from exc
        with _engine(request).connect() as connection:
            return _subscription_view(connection, owner)

    @app.delete("/account", response_model=DeletionView)
    async def delete_account(request: Request, owner: Annotated[str, Depends(_user)]) -> DeletionView:
        result = request_account_deletion(_engine(request), user_id=owner)
        return DeletionView(state=result["state"])

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
            return BootstrapView(modes=_bootstrap_views(connection, _active_profile(connection, owner)))

    @app.get("/readiness", response_model=SyncView)
    async def readiness(request: Request, owner: Annotated[str, Depends(_user)]) -> SyncView:
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            row = connection.execute(select(sync_state).where(
                sync_state.c.account_id == (profile["account_id"] if profile else -1),
                sync_state.c.provider == "opendota",
            )).mappings().one_or_none()
            access = data_access_state(connection, profile["account_id"]) if profile else "UNKNOWN"
        return SyncView(state=row["state"] if row else "IDLE",
                        last_checked_at=row["last_checked_at"] if row else None,
                        data_access=cast(Literal["ACCESSIBLE", "BLOCKED", "UNKNOWN"], access))

    @app.post("/sync", response_model=SyncRequestView)
    async def sync(request: Request, owner: Annotated[str, Depends(_user)],
                   idempotency_key: Annotated[str, Header(min_length=8, max_length=200)]) -> SyncRequestView:
        with _engine(request).begin() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                raise HTTPException(409, "STEAM_LINK_REQUIRED")
            def publish() -> dict[str, object]:
                resume_bootstrap_search(connection, profile["id"])
                return {"accepted": request_account_sync(connection, profile["account_id"], scope_days=7) is not None}

            response = _idempotent(connection, owner=owner, operation="SYNC", key=idempotency_key,
                                   body={}, publish=publish)
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

    @app.get("/matches/{match_ref}", response_model=MatchDetailView)
    async def match_detail(request: Request, match_ref: str, owner: Annotated[str, Depends(_user)]) -> MatchDetailView:
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            row = connection.execute(select(account_matches).where(
                account_matches.c.profile_id == (profile["id"] if profile else ""),
                account_matches.c.public_ref == match_ref,
                _visible(profile) if profile else true(),
            )).mappings().one_or_none()
            if row is None:
                raise HTTPException(404, "MATCH_NOT_FOUND")
            owns = sorted(connection.scalars(select(personal_bests.c.metric_id).where(
                personal_bests.c.profile_id == profile["id"],
                personal_bests.c.revision == profile["active_revision"],
                personal_bests.c.analysis_id == row["active_analysis_id"],
            ))) if row["active_analysis_id"] else []
            celebrated = sorted(connection.scalars(select(events.c.payload["metric_id"].astext).where(
                events.c.profile_id == profile["id"], events.c.kind == "NEW_PB",
                events.c.payload["match_id"].astext == str(row["match_id"]),
            )))
            achievement_result = connection.scalar(select(analyses.c.result).where(
                analyses.c.id == row["active_analysis_id"])) if row["active_analysis_id"] else None
            achievement_data = (achievement_result or {}).get("achievements") or {}
            return MatchDetailView(**_match_view(connection, row).model_dump(),
                item_timings=_item_timings_view(connection, row),
                offlane_context=_offlane_context_view(connection, row),
                carry_context=_carry_context_view(connection, row),
                mid_context=_mid_context_view(connection, row),
                core_fights=_core_fights_view(connection, row),
                role_revision=row["role_revision"],
                correction_available=correction_available(
                    connection, profile_id=profile["id"], match_id=row["match_id"],
                ), owns_personal_best=owns, celebrated_personal_best=celebrated,
                achievement_state=_achievement_state(row, achievement_data),
                achievements=achievement_data.get("awards", []) if _achievements_current(achievement_data) else [],
                achievement_unavailable=achievement_data.get("unavailable", [])
                if _achievements_current(achievement_data) else [])

    @app.get("/achievements", response_model=AchievementCollectionView)
    async def achievements_collection(request: Request, owner: Annotated[str, Depends(_user)],
                                      locale: str = Query("en")) -> AchievementCollectionView:
        with _engine(request).connect() as connection:
            return _achievement_collection(connection, _active_profile(connection, owner), locale)

    @app.get("/achievements/{achievement_id}", response_model=AchievementEntryView)
    async def achievement_detail(request: Request, achievement_id: int,
                                 owner: Annotated[str, Depends(_user)],
                                 locale: str = Query("en")) -> AchievementEntryView:
        if achievement_id not in ACHIEVEMENT_IDS:
            raise HTTPException(404, "ACHIEVEMENT_NOT_FOUND")
        with _engine(request).connect() as connection:
            collection = _achievement_collection(connection, _active_profile(connection, owner), locale)
            return next(entry for entry in collection.entries if entry.id == achievement_id)

    @app.post("/matches/{match_ref}/role", response_model=RoleEditView)
    async def edit_role(request: Request, match_ref: str, body: RoleEditRequest,
                        owner: Annotated[str, Depends(_user)],
                        idempotency_key: Annotated[str, Header(min_length=8, max_length=200)]) -> RoleEditView:
        with _engine(request).begin() as connection:
            if connection.scalar(select(users.c.id).where(users.c.id == owner).with_for_update()) is None:
                raise HTTPException(401, "SESSION_INVALID")
            profile = _active_profile(connection, owner)
            row = connection.execute(select(account_matches.c.match_id).where(
                account_matches.c.profile_id == (profile["id"] if profile else ""),
                account_matches.c.public_ref == match_ref,
                _visible(profile) if profile else true(),
            )).first()
            if row is None or profile is None:
                raise HTTPException(404, "MATCH_NOT_FOUND")

            def publish() -> dict[str, object]:
                try:
                    result = correct_role(connection, profile_id=profile["id"], match_id=row.match_id,
                                          role=body.role.value,
                                          expected_role_revision=body.expected_role_revision)
                except RoleCorrectionConflict as exc:
                    raise HTTPException(409, "ROLE_REVISION_STALE") from exc
                except RoleCorrectionUnavailable as exc:
                    raise HTTPException(409, "ROLE_CORRECTION_UNAVAILABLE") from exc
                return {"role": result["effective_role"], "role_revision": result["role_revision"],
                        "rebuilt": result["rebuilt"],
                        "rebuilt_match_count": result.get("rebuilt_match_count")}

            response = _idempotent(connection, owner=owner, operation="MATCH_ROLE", key=idempotency_key,
                                   body={"match_ref": match_ref, "role": body.role.value,
                                         "expected_role_revision": body.expected_role_revision},
                                   publish=publish)
        return RoleEditView.model_validate(response)

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
    async def history(request: Request, owner: Annotated[str, Depends(_user)], mode: Mode | None = None,
                      role: Role | None = None, cursor: str | None = None,
                      limit: Annotated[int, Query(ge=1, le=50)] = 20,
                      local_date: date_type | None = None, time_zone: str | None = None,
                      ready_only: bool = False) -> HistoryView:
        """Every retained match, ineligible and unsupported-mode ones included when unfiltered.

        `local_date` + `time_zone` narrow to one local day; with `ready_only` the list equals
        an activity heatmap cell (activity/SSOT.md §5).
        """
        scope = mode.value if mode else "ALL"
        # `time_zone` alone is ignored, so clients may always send it; a day needs its zone.
        if local_date is not None and time_zone is None:
            raise HTTPException(400, "TIME_ZONE_REQUIRED")
        day = ""
        if local_date is not None and time_zone is not None:
            start, end = activity.utc_bounds(local_date, local_date, _zone(time_zone))
            day = f"{local_date.isoformat()}@{time_zone}"
        if ready_only:
            day += ":READY"
        key = _cursor_key(request)
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                return HistoryView(matches=[], next_cursor=None)
            query = select(account_matches).where(account_matches.c.profile_id == profile["id"], _visible(profile))
            if mode is not None:
                query = query.where(account_matches.c.mode == mode.value)
            if role is not None:
                query = query.where(account_matches.c.effective_role == role.value)
            if local_date is not None:
                query = query.where(account_matches.c.provider_started_at >= start,
                                    account_matches.c.provider_started_at < end)
            if ready_only:
                query = query.where(account_matches.c.lifecycle == "READY",
                                    account_matches.c.mode.in_(("STANDARD", "TURBO")))
            if cursor is not None:
                pieces = cursor.split(".")
                if len(pieces) != 2 or not hmac.compare_digest(
                    cursor, _cursor(key, profile["id"], pieces[0], scope,
                                    role.value if role else None, profile["active_revision"], day),
                ):
                    raise HTTPException(400, "CURSOR_INVALID")
                anchor = connection.execute(select(account_matches).where(
                    account_matches.c.profile_id == profile["id"],
                    account_matches.c.public_ref == pieces[0],
                )).mappings().one_or_none()
                if (anchor is None or mode is not None and anchor["mode"] != mode.value
                        or role is not None and anchor["effective_role"] != role.value):
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
            next_cursor = (_cursor(key, profile["id"], visible[-1]["public_ref"], scope,
                                   role.value if role else None, profile["active_revision"], day)
                           if len(rows) > limit else None)
            return HistoryView(matches=[_history_row(connection, row) for row in visible],
                               next_cursor=next_cursor)

    @app.get("/mastery", response_model=MasteryView)
    async def mastery(request: Request, owner: Annotated[str, Depends(_user)]) -> MasteryView:
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                return MasteryView(state="STEAM_LINK_REQUIRED", curve_version=CURVE_VERSION,
                                   roles=[], milestones=[])
            state = mastery_state(connection, profile)
            if state != "AVAILABLE":
                return MasteryView(state=state, curve_version=CURVE_VERSION,
                                   roles=[], milestones=[])
            pro = profile["active_scope"] == "PRO"
            roles = []
            for role in ROLES:
                total = role_total(connection, profile["id"], role)
                earned, within, needed = level_for_xp(total)
                capped = not pro and earned is not None and earned >= 5
                roles.append(MasteryRoleView(
                    role=Role(role), state="STARTED" if earned is not None else "UNSTARTED",
                    level=earned if pro or earned is None else min(earned, 5),
                    xp_into_level=within if earned is not None and not capped else None,
                    xp_to_next_level=needed if earned is not None and not capped else None,
                    total_xp=total if pro else None, saved_progress=capped,
                ))
            milestones = connection.execute(select(events.c.payload, events.c.created_at).where(
                events.c.profile_id == profile["id"], events.c.kind == "MASTERY_LEVEL",
            ).order_by(events.c.created_at.desc()).limit(50)).all()
            return MasteryView(state="AVAILABLE", curve_version=CURVE_VERSION, roles=roles,
                               milestones=[MasteryMilestoneView(role=Role(row.payload["role"]),
                                             level=row.payload["level"], created_at=row.created_at)
                                           for row in milestones if pro or row.payload["level"] <= 5])

    @app.get("/mastery/{role}/awards", response_model=MasteryAwardsView)
    async def mastery_awards(request: Request, owner: Annotated[str, Depends(_user)], role: Role,
                            cursor: str | None = None,
                            limit: Annotated[int, Query(ge=1, le=50)] = 20) -> MasteryAwardsView:
        key = _cursor_key(request)
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                return MasteryAwardsView(awards=[], next_cursor=None)
            state = mastery_state(connection, profile)
            if state != "AVAILABLE":
                raise HTTPException(503, f"MASTERY_{state}")
            query = select(mastery_ledger, account_matches.c.public_ref).join(
                account_matches,
                (account_matches.c.profile_id == mastery_ledger.c.profile_id)
                & (account_matches.c.match_id == mastery_ledger.c.match_id),
            ).where(mastery_ledger.c.profile_id == profile["id"],
                    mastery_ledger.c.role == role.value, CURRENT_RULE, _visible(profile))
            if cursor is not None:
                pieces = cursor.split(".")
                if (len(pieces) != 2 or not hmac.compare_digest(cursor,
                    _mastery_cursor(key, profile["id"], pieces[0], role.value, profile["active_revision"]))):
                    raise HTTPException(400, "CURSOR_INVALID")
                anchor = connection.execute(select(mastery_ledger).where(
                    mastery_ledger.c.id == pieces[0], mastery_ledger.c.profile_id == profile["id"],
                    mastery_ledger.c.role == role.value, CURRENT_RULE,
                )).mappings().one_or_none()
                if anchor is None:
                    raise HTTPException(400, "CURSOR_INVALID")
                query = query.where(or_(mastery_ledger.c.created_at < anchor["created_at"],
                    and_(mastery_ledger.c.created_at == anchor["created_at"],
                         mastery_ledger.c.id < anchor["id"])))
            rows = connection.execute(query.order_by(mastery_ledger.c.created_at.desc(),
                mastery_ledger.c.id.desc()).limit(limit + 1)).mappings().all()
            visible = rows[:limit]
            next_cursor = None
            if len(rows) > limit:
                ref = visible[-1]["id"]
                next_cursor = _mastery_cursor(key, profile["id"], ref, role.value, profile["active_revision"])
            return MasteryAwardsView(awards=[MasteryAwardView(
                kind=row["kind"], xp=row["xp"], mode=Mode(row["mode"]), role=role,
                match_ref=row["public_ref"], reason=row["source"]["reason"],
                from_role=Role(row["source"]["from_role"]) if row["source"].get("from_role") else None,
                above_metric_ids=row["source"]["above_metric_ids"],
                pb_metric_ids=row["source"]["pb_metric_ids"], rule_version=row["rule_version"],
                analysis_version=row["source"]["analysis_version"],
                baseline_version=row["source"]["baseline_version"],
                parameter_set_version=row["source"]["parameter_set_version"],
                created_at=row["created_at"],
            ) for row in visible], next_cursor=next_cursor)

    @app.get("/home", response_model=HomeView)
    async def home(request: Request, owner: Annotated[str, Depends(_user)], mode: Mode,
                   time_zone: str) -> HomeView:
        zone = _zone(time_zone)
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
            ).order_by(account_matches.c.provider_started_at.desc(),
                       account_matches.c.provider_source_match_id.desc()).limit(100)).mappings().all()
            # Last 5 spans both buckets and every lifecycle (home §7).
            last_rows = connection.execute(base.order_by(
                account_matches.c.provider_started_at.desc(),
                account_matches.c.provider_source_match_id.desc()).limit(5)).mappings().all()
            return HomeView(mode=mode, local_date=today.isoformat(),
                            today_matches=[_summary_view(connection, row) for row in today_rows],
                            last_matches=[_summary_view(connection, row) for row in last_rows],
                            role_summaries=_role_summaries(connection, profile, mode.value))

    @app.get("/activity", response_model=ActivityView)
    async def activity_heatmap(request: Request, owner: Annotated[str, Depends(_user)], time_zone: str,
                               year: int | None = None) -> ActivityView:
        zone = _zone(time_zone)
        today = datetime.now(zone).date()
        try:
            window_start, window_end = activity.resolve_window(today, year)
        except ValueError as exc:
            raise HTTPException(400, "YEAR_INVALID") from exc
        empty = ActivityView(time_zone=time_zone, today=today, window=None, available_years=[],
                             partial_ranges=[], series=[ActivitySeriesView(role=ActivityRole(name),
                                                                          total_matches=0, days=[])
                                                       for name in activity.SERIES])
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                return empty
            # Local days are bucketed in Python with the same ZoneInfo as /history and /hero-pool:
            # PostgreSQL reads names such as CET as fixed-offset abbreviations and ships its own
            # tz database, so SQL bucketing could disagree with the drill-in.
            started = connection.execute(select(
                account_matches.c.provider_started_at, account_matches.c.effective_role,
            ).where(_counted(profile))).all()
            days = [(row.provider_started_at.astimezone(zone).date(), row.effective_role) for row in started]
            # Out-of-range dates (clock skew, bad provider data) are never advertised as a year.
            days = [(day, role) for day, role in days if activity.FIRST_YEAR <= day.year and day <= today]
            if not days:
                return empty
            first_day = min(day for day, _ in days)
            start = max(window_start, first_day)
            window = ActivityWindowView(start_date=start, end_date=window_end) if start <= window_end else None
            span = _bootstrap_partial(connection, profile, zone, start, window_end) if window is not None else None
            partial = [span] if span is not None else []
            return ActivityView(
                time_zone=time_zone, today=today, window=window,
                available_years=sorted({day.year for day, _ in days}, reverse=True),
                partial_ranges=partial,
                series=[ActivitySeriesView.model_validate(series) for series in activity.build_series(
                    (day, role, 1) for day, role in days if window_start <= day <= window_end)],
            )

    @app.get("/hero-pool", response_model=HeroPoolView)
    async def hero_pool_view(request: Request, owner: Annotated[str, Depends(_user)],
                             time_zone: str) -> HeroPoolView:
        zone = _zone(time_zone)
        today = datetime.now(zone).date()
        starts = hero_pool.window_starts(today)
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            rows: list[Any] = []
            partial: list[ActivityPartialRangeView] = []
            if profile is not None:
                b365, end_utc = activity.utc_bounds(starts[2], today, zone)
                b7, _ = activity.utc_bounds(starts[0], today, zone)
                b30, _ = activity.utc_bounds(starts[1], today, zone)
                started = account_matches.c.provider_started_at
                rows = list(connection.execute(select(
                    account_matches.c.effective_role, match_players.c.hero_id,
                    func.count().filter(started >= b7), func.count().filter(started >= b30),
                    func.count(), func.max(started),
                ).select_from(account_matches.join(
                    match_players, (match_players.c.match_id == account_matches.c.match_id) &
                    (match_players.c.player_slot == account_matches.c.player_slot),
                )).where(_counted(profile), started >= b365, started < end_utc,
                ).group_by(account_matches.c.effective_role, match_players.c.hero_id)).all())
                span = _bootstrap_partial(connection, profile, zone, starts[2], today)
                partial = [span] if span is not None else []
            return HeroPoolView(time_zone=time_zone, today=today, partial_ranges=partial,
                                roles=[HeroPoolRoleView.model_validate(role)
                                       for role in hero_pool.build_roles(rows, today)])

    @app.get("/matches", response_model=MatchListView)
    async def match_list_view(
        request: Request, owner: Annotated[str, Depends(_user)], time_zone: str,
        q: Annotated[str | None, Query(max_length=match_list.QUERY_MAX)] = None,
        hero: Annotated[list[int], Query(max_length=10)] = [],  # noqa: B006 (FastAPI query list)
        role: Role | None = None, mode: Mode | None = None,
        from_date: Annotated[date_type | None, Query(alias="from")] = None,
        to_date: Annotated[date_type | None, Query(alias="to")] = None,
        cursor: str | None = None, limit: Annotated[int, Query(ge=1, le=50)] = 20,
    ) -> MatchListView:
        """Every visible Standard and Turbo match, newest first, grouped into play sessions.

        Sessions are derived from the whole visible history, so filters and search narrow rows
        but never change a session's identity, name or header (matches/SSOT.md §3).
        """
        zone = _zone(time_zone)
        if any(not 0 < hero_id < 1000 for hero_id in hero):
            raise HTTPException(400, "HERO_INVALID")
        if from_date is not None and to_date is not None and from_date > to_date:
            raise HTTPException(400, "DATE_RANGE_INVALID")
        lower = activity.utc_bounds(from_date, from_date, zone)[0] if from_date is not None else None
        upper = activity.utc_bounds(to_date, to_date, zone)[1] if to_date is not None else None
        terms = match_list.parse_query(q)
        heroes = frozenset(hero)
        scope = canonical_json({
            "q": [term.text for term in terms], "hero": sorted(heroes), "role": role, "mode": mode,
            "from": from_date.isoformat() if from_date else None,
            "to": to_date.isoformat() if to_date else None, "time_zone": time_zone,
        })
        digest = hashlib.sha256(scope).hexdigest()[:16]
        key = _cursor_key(request)
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                return MatchListView(time_zone=time_zone, has_matches=False, sessions=[], next_cursor=None)

            revision = profile["active_revision"]

            def sign(ref: str) -> str:
                return f"{ref}.{_mac(key, profile['id'], f'matches:{ref}:{revision}:{digest}')}"

            rows = _play_rows(connection, profile)
            listed = [(head, row) for head, members in _play_sessions(connection, profile, zone, rows)
                      for row in members
                      if (not heroes or row["hero_id"] in heroes)
                      and (role is None or row["effective_role"] == role.value)
                      and (mode is None or row["mode"] == mode.value)
                      and (lower is None or row["provider_started_at"] >= lower)
                      and (upper is None or row["provider_started_at"] < upper)
                      and match_list.matches_query(terms, _fact(row), head.name)]
            if cursor is not None:
                ref = cursor.split(".")[0]
                anchor = next((row for row in rows if row["public_ref"] == ref), None)
                if anchor is None or not hmac.compare_digest(cursor, sign(ref)):
                    raise HTTPException(400, "CURSOR_INVALID")
                after = (anchor["provider_started_at"], anchor["provider_source_match_id"])
                listed = [(head, row) for head, row in listed
                          if (row["provider_started_at"], row["provider_source_match_id"]) < after]
            page = listed[:limit]
            views = _list_rows(connection, [row for _, row in page])
            grouped: list[PlaySessionView] = []
            for head, row in page:
                if not grouped or grouped[-1].session_ref != head.session_ref:
                    grouped.append(PlaySessionView(**head.model_dump(), matches=[]))
                grouped[-1].matches.append(views[row["match_id"]])
            return MatchListView(time_zone=time_zone, has_matches=bool(rows), sessions=grouped,
                                 next_cursor=sign(page[-1][1]["public_ref"]) if len(listed) > limit else None)

    @app.post("/matches/sessions/{session_ref}/name", response_model=PlaySessionHeaderView)
    async def rename_play_session(
        request: Request, session_ref: str, body: PlaySessionNameRequest,
        owner: Annotated[str, Depends(_user)], time_zone: str,
        idempotency_key: Annotated[str, Header(min_length=8, max_length=200)],
    ) -> PlaySessionHeaderView:
        """Name a play session by its first match; null restores the placeholder."""
        zone = _zone(time_zone)

        def session(connection: Connection, profile: Any) -> tuple[PlaySessionHeaderView, list[Any]]:
            found = next(((head, members) for head, members in _play_sessions(
                connection, profile, zone, _play_rows(connection, profile)) if head.session_ref == session_ref), None)
            if found is None:
                raise HTTPException(404, "SESSION_NOT_FOUND")
            return found

        with _engine(request).begin() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                raise HTTPException(409, "STEAM_LINK_REQUIRED")
            _, members = session(connection, profile)

            def publish() -> dict[str, object]:
                # One label per session, on its first match; presentation only.
                connection.execute(play_session_names.delete().where(
                    play_session_names.c.profile_id == profile["id"],
                    play_session_names.c.match_id.in_([row["match_id"] for row in members])))
                if body.name is not None:
                    connection.execute(play_session_names.insert().values(
                        profile_id=profile["id"], match_id=members[-1]["match_id"], name=body.name,
                        updated_at=func.clock_timestamp()))
                return {"session_ref": session_ref, "name": body.name}

            _idempotent(connection, owner=owner, operation="PLAY_SESSION_NAME", key=idempotency_key,
                        body={"session_ref": session_ref, "name": body.name}, publish=publish)
        with _engine(request).connect() as connection:
            return session(connection, _active_profile(connection, owner))[0]

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
            source = connection.execute(select(
                account_matches.c.public_ref, account_matches.c.provider_started_at, match_players.c.hero_id,
            ).join(match_players, (match_players.c.match_id == account_matches.c.match_id)
                   & (match_players.c.player_slot == account_matches.c.player_slot)).where(
                account_matches.c.active_analysis_id == pb.analysis_id,
                account_matches.c.profile_id == profile["id"],
            )).first() if pb else None
            personal = (PersonalBestView(match_ref=source.public_ref, value=pb.comparison_value,
                                         hero_id=source.hero_id, achieved_at=source.provider_started_at)
                        if pb is not None and source is not None else None)
        return ProgressView(mode=mode, role=role, metric_id=metric_id, points=points,
                            personal_best=personal, trend=TrendView(
                                state=cast(Literal["IMPROVING", "STABLE", "DECLINING", "INSUFFICIENT_HISTORY"] | None,
                                           trend["state"]),
                                reason="CALIBRATION_UNAVAILABLE" if trend["reason"] == "UNCALIBRATED" else None,
                                point_count=cast(int, trend["point_count"]),
                            ))

    @app.get("/profile", response_model=ProfileView)
    async def profile_view(request: Request, owner: Annotated[str, Depends(_user)], mode: Mode) -> ProfileView:
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                raise HTTPException(409, "STEAM_LINK_REQUIRED")
            return _profile_view(connection, profile, mode)

    @app.post("/profile/favourite-hero", response_model=ProfileView)
    async def favourite_hero(request: Request, body: FavouriteRequest, owner: Annotated[str, Depends(_user)],
                             mode: Mode,
                             idempotency_key: Annotated[str, Header(min_length=8, max_length=200)]) -> ProfileView:
        with _engine(request).begin() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                raise HTTPException(409, "STEAM_LINK_REQUIRED")

            def publish() -> dict[str, object]:
                # Player-pinned only; never read by any analytical path.
                connection.execute(profiles.update().where(profiles.c.id == profile["id"])
                                   .values(favourite_hero_id=body.hero_id))
                return {"hero_id": body.hero_id}

            _idempotent(connection, owner=owner, operation="FAVOURITE_HERO", key=idempotency_key,
                        body={"hero_id": body.hero_id}, publish=publish)
        with _engine(request).connect() as connection:
            return _profile_view(connection, _active_profile(connection, owner), mode)

    @app.post("/shares", response_model=ShareView)
    async def create_share_route(request: Request, body: ShareRequest, owner: Annotated[str, Depends(_user)],
                                 idempotency_key: Annotated[str, Header(min_length=8, max_length=200)]) -> ShareView:
        with _engine(request).begin() as connection:
            profile = _active_profile(connection, owner)
            if profile is None:
                raise HTTPException(409, "STEAM_LINK_REQUIRED")

            def publish() -> dict[str, object]:
                try:
                    created = create_share(connection, profile_id=profile["id"], kind=body.kind,
                                           mode=body.mode.value, metric_id=body.metric_id)
                except ShareUnavailable as exc:
                    raise HTTPException(409, f"SHARE_UNAVAILABLE_{exc}") from exc
                return {key: value for key, value in created.items()
                        if key in ShareView.model_fields}

            result = _idempotent(connection, owner=owner, operation="SHARE", key=idempotency_key,
                                 body=body.model_dump(mode="json"), publish=publish)
        return ShareView.model_validate(result)

    def _owned_share(connection: Connection, owner: str, share_ref: str):
        try:
            UUID(share_ref)
        except ValueError as exc:
            raise HTTPException(404, "SHARE_NOT_FOUND") from exc
        row = connection.execute(select(shares.c.id, shares.c.projection).join(
            profiles, profiles.c.id == shares.c.profile_id).where(
            shares.c.id == share_ref, profiles.c.user_id == owner)).first()
        if row is None:
            raise HTTPException(404, "SHARE_NOT_FOUND")
        return row

    @app.get("/shares/{share_ref}", response_model=ShareView)
    async def read_share(request: Request, share_ref: str, owner: Annotated[str, Depends(_user)]) -> ShareView:
        with _engine(request).connect() as connection:
            row = _owned_share(connection, owner, share_ref)
        return ShareView.model_validate({"ref": row.id, **{key: value for key, value in row.projection.items()
                                                           if key in ShareView.model_fields}})

    @app.get("/shares/{share_ref}/image.svg", response_class=Response)
    async def share_image(request: Request, share_ref: str, owner: Annotated[str, Depends(_user)]) -> Response:
        with _engine(request).connect() as connection:
            row = _owned_share(connection, owner, share_ref)
        return Response(render_svg(row.projection), media_type="image/svg+xml")

    @app.get("/settings", response_model=SettingsView)
    async def settings_view(request: Request, owner: Annotated[str, Depends(_user)]) -> SettingsView:
        with _engine(request).connect() as connection:
            enabled = connection.scalar(select(users.c.notifications_enabled).where(users.c.id == owner))
        return SettingsView(notifications_enabled=bool(enabled))

    @app.patch("/settings", response_model=SettingsView)
    async def settings_patch(request: Request, body: SettingsPatch,
                             owner: Annotated[str, Depends(_user)]) -> SettingsView:
        with _engine(request).begin() as connection:
            if body.notifications_enabled is not None:
                connection.execute(users.update().where(users.c.id == owner)
                                   .values(notifications_enabled=body.notifications_enabled))
            enabled = connection.scalar(select(users.c.notifications_enabled).where(users.c.id == owner))
        return SettingsView(notifications_enabled=bool(enabled))

    @app.get("/recovery", response_model=RecoveryView)
    async def recovery(request: Request, owner: Annotated[str, Depends(_user)]) -> RecoveryView:
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            access = data_access_state(connection, profile["account_id"]) if profile else "UNKNOWN"
        return RecoveryView(data_access=cast(Literal["ACCESSIBLE", "BLOCKED", "UNKNOWN"], access))

    @app.post("/data-access/confirm", response_model=DataAccessConfirmView)
    async def confirm_data_access(request: Request, owner: Annotated[str, Depends(_user)],
                                  idempotency_key: Annotated[str, Header(min_length=8, max_length=200)]) -> DataAccessConfirmView:
        with _engine(request).begin() as connection:
            connection.execute(select(users.c.id).where(users.c.id == owner).with_for_update())
            profile = _active_profile(connection, owner)
            if profile is None:
                raise HTTPException(409, "STEAM_LINK_REQUIRED")

            def publish() -> dict[str, object]:
                if data_access_state(connection, profile["account_id"]) != "BLOCKED":
                    return {"recovery": "NOT_NEEDED"}
                # Recovery re-anchors to the original link date (onboarding §8).
                restore_access(connection, account_id=profile["account_id"])
                return {"recovery": "STARTED"}

            result = _idempotent(connection, owner=owner, operation="DATA_ACCESS_CONFIRM", key=idempotency_key,
                                 body={}, publish=publish)
        return DataAccessConfirmView.model_validate(result)

    @app.get("/history-operation", response_model=HistoryOperationView)
    async def history_operation(request: Request, owner: Annotated[str, Depends(_user)]) -> HistoryOperationView:
        with _engine(request).connect() as connection:
            profile = _active_profile(connection, owner)
            subscription = _subscription_view(connection, owner)
            if profile is None:
                return HistoryOperationView(bootstrap=_bootstrap_views(connection, None), scope_change="NONE",
                                            target_scope=None, history_import="NONE", access_recovery="NONE",
                                            data_access="UNKNOWN")
            return HistoryOperationView(
                bootstrap=_bootstrap_views(connection, profile), scope_change=subscription.scope_change,
                target_scope=subscription.target_scope,
                history_import=_job_state(connection, profile["id"], "PRO_BACKFILL"),
                access_recovery=_job_state(connection, profile["id"], "ACCESS_RECOVERY"),
                data_access=cast(Literal["ACCESSIBLE", "BLOCKED", "UNKNOWN"],
                                 data_access_state(connection, profile["account_id"])))

    @app.get("/changes", response_model=ChangesView)
    async def changes(request: Request, owner: Annotated[str, Depends(_user)],
                      after: str | None = None) -> ChangesView:
        key = _cursor_key(request)
        with _engine(request).connect() as connection:
            # updated_at is stamped at write time, not commit time: the cursor may not
            # pass the oldest in-flight writing transaction, or its change is skipped.
            now = connection.execute(text(
                "SELECT least(clock_timestamp(), (SELECT min(xact_start) FROM pg_stat_activity"
                " WHERE datname = current_database() AND backend_xid IS NOT NULL AND pid <> pg_backend_pid()))"
            )).scalar_one()
            profile = _active_profile(connection, owner)
            if profile is None:
                return ChangesView(cursor=_changes_cursor(key, owner, now, 0), changed_refs=[], full_refresh=True)
            cursor = _changes_cursor(key, profile["id"], now, profile["active_revision"])
            since = None
            if after is not None:
                pieces = after.split(".")
                try:
                    stamp = datetime.fromtimestamp(int(pieces[0]) / 1_000_000, UTC)
                    revision = int(pieces[1])
                except (ValueError, IndexError, OverflowError):
                    stamp, revision = None, -1
                if (stamp is not None and len(pieces) == 3 and revision == profile["active_revision"]
                        and hmac.compare_digest(after, _changes_cursor(key, profile["id"], stamp, revision))):
                    since = stamp
            if since is None:
                # Unknown, foreign or pre-revision cursor: the client refetches.
                return ChangesView(cursor=cursor, changed_refs=[], full_refresh=True)
            refs = connection.scalars(select(account_matches.c.public_ref).where(
                account_matches.c.profile_id == profile["id"], account_matches.c.updated_at > since,
                _visible(profile),
            ).order_by(account_matches.c.updated_at).limit(201)).all()
        if len(refs) > 200:
            return ChangesView(cursor=cursor, changed_refs=[], full_refresh=True)
        return ChangesView(cursor=cursor, changed_refs=list(refs), full_refresh=False)

    @app.middleware("http")
    async def entity_tags(request: Request, call_next):
        response = await call_next(request)
        if request.method != "GET" or response.status_code != 200 or \
                not response.headers.get("content-type", "").startswith("application/json"):
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])
        tag = '"' + hashlib.sha256(body).hexdigest()[:32] + '"'
        headers = {key: value for key, value in response.headers.items() if key.lower() != "content-length"}
        headers["ETag"] = tag
        headers["Cache-Control"] = "private, no-cache"
        if request.headers.get("if-none-match") == tag:
            return Response(status_code=304, headers={"ETag": tag, "Cache-Control": "private, no-cache"})
        return Response(content=body, status_code=200, headers=headers, media_type="application/json")

    return app

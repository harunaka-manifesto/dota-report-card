"""Deterministic V7 facts derived from one canonical match history.

These are factual aggregations, not Findings.  They deliberately stop at the
provider's reported coverage boundary and never upgrade a recorded maximum to
an annual maximum when history was truncated.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from pydantic import Field, model_validator

from app.player_analysis_v7.report_contract import PublicV7Model
from app.player_analysis_v7.research.tables import is_product_context
from app.providers.base import V7CanonicalHistory, V7CanonicalMatch

DESCRIPTIVE_PRODUCER_VERSION = "v7-descriptive-facts-1.0.0"


class TimeWindow(PublicV7Model):
    start: int = Field(ge=0)
    end: int = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self) -> TimeWindow:
        if self.end < self.start:
            raise ValueError("window end precedes start")
        return self


class ReportScope(PublicV7Model):
    requested_window: TimeWindow
    observed_window: TimeWindow | None
    eligible_match_count: int = Field(ge=0)
    parsed_match_count: int = Field(ge=0)
    acquired_match_count: int = Field(ge=0)
    acquisition_depth_limit: int = Field(ge=1)
    coverage_status: Literal["complete", "truncated"]
    coverage_boundary_reason: Literal["provider_reported_complete", "provider_or_depth_limit"]
    generated_at: str = Field(min_length=1)

    @model_validator(mode="after")
    def counts_are_coherent(self) -> ReportScope:
        if self.parsed_match_count > self.eligible_match_count:
            raise ValueError("parsed count exceeds eligible count")
        if self.eligible_match_count > self.acquired_match_count:
            raise ValueError("eligible count exceeds acquired count")
        return self


class HeroUsage(PublicV7Model):
    hero_id: int = Field(gt=0)
    display_name: str = Field(min_length=1)
    eligible_match_count: int = Field(gt=0)
    tied_for_most_played: bool


class HeroCast(PublicV7Model):
    heroes: list[HeroUsage]
    missing_display_metadata_hero_ids: list[int]
    has_unique_most_played: bool


class ActivityMemory(PublicV7Model):
    start_date: date
    end_date: date
    eligible_match_count: int = Field(ge=3)
    claim_status: Literal["busiest", "recorded"]
    timezone: Literal["UTC"] = "UTC"

    @model_validator(mode="after")
    def is_seven_consecutive_dates(self) -> ActivityMemory:
        if self.end_date - self.start_date != timedelta(days=6):
            raise ValueError("activity memory must span seven consecutive UTC dates")
        return self


class MonthlyHeroLeader(PublicV7Model):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    hero_id: int = Field(gt=0)
    display_name: str = Field(min_length=1)
    eligible_match_count: int = Field(ge=10)
    leader_match_count: int = Field(gt=0)
    leader_share: float = Field(ge=0, le=1)
    coverage: Literal["full"] = "full"


class MonthlyHeroContrast(PublicV7Model):
    earlier: MonthlyHeroLeader
    later: MonthlyHeroLeader

    @model_validator(mode="after")
    def is_adjacent_and_changed(self) -> MonthlyHeroContrast:
        earlier = date.fromisoformat(f"{self.earlier.month}-01")
        later = date.fromisoformat(f"{self.later.month}-01")
        if _next_month(earlier) != later:
            raise ValueError("monthly hero contrast months must be adjacent")
        if self.earlier.hero_id == self.later.hero_id:
            raise ValueError("monthly hero contrast leaders must differ")
        return self


class CompletedLossRun(PublicV7Model):
    loss_count: int = Field(ge=3)
    first_loss_at: int = Field(ge=0)
    final_loss_at: int = Field(ge=0)
    following_win_at: int = Field(ge=0)
    visibility: Literal["private"] = "private"
    share_safe: Literal[False] = False
    maximum_claim_safe: bool

    @model_validator(mode="after")
    def chronology_is_ordered(self) -> CompletedLossRun:
        if not self.first_loss_at <= self.final_loss_at < self.following_win_at:
            raise ValueError("completed loss-run chronology is invalid")
        return self


class DescriptiveFacts(PublicV7Model):
    version: Literal["v7-descriptive-facts-1.0.0"] = "v7-descriptive-facts-1.0.0"
    scope: ReportScope
    hero_cast: HeroCast
    activity_memory: ActivityMemory | None = None
    monthly_hero_contrast: MonthlyHeroContrast | None = None
    completed_loss_run: CompletedLossRun | None = None


def _eligible(match: V7CanonicalMatch) -> bool:
    return is_product_context(
        {
            "game_mode_native": match.game_mode_native,
            "lobby_type_native": match.lobby_native,
            "leaver_status_native": match.leaver_status_native,
        }
    )


def _utc_date(timestamp: int) -> date:
    return datetime.fromtimestamp(timestamp, UTC).date()


def derive_descriptive_facts(
    history: V7CanonicalHistory,
    hero_metadata: Mapping[int, Mapping[str, object]],
    *,
    generated_at: str,
    acquisition_depth_limit: int = 500,
    known_gap_after_match_ids: Sequence[int] = (),
) -> DescriptiveFacts:
    eligible = [match for match in history.matches if _eligible(match)]
    timestamps = [match.started_at for match in eligible if match.started_at is not None]
    complete = history.provenance.completeness == "complete"
    scope = ReportScope(
        requested_window=TimeWindow(
            start=history.window.start_timestamp, end=history.window.end_timestamp
        ),
        observed_window=(
            TimeWindow(start=min(timestamps), end=max(timestamps)) if timestamps else None
        ),
        eligible_match_count=len(eligible),
        parsed_match_count=sum(match.is_parsed for match in eligible),
        acquired_match_count=len(history.matches),
        acquisition_depth_limit=acquisition_depth_limit,
        coverage_status="complete" if complete else "truncated",
        coverage_boundary_reason=(
            "provider_reported_complete" if complete else "provider_or_depth_limit"
        ),
        generated_at=generated_at,
    )
    return DescriptiveFacts(
        scope=scope,
        hero_cast=_hero_cast(eligible, hero_metadata),
        activity_memory=_activity_memory(eligible, complete=complete),
        monthly_hero_contrast=_monthly_contrast(
            eligible, history, hero_metadata, complete=complete
        ),
        completed_loss_run=_completed_loss_run(
            eligible,
            known_gap_after_match_ids=frozenset(known_gap_after_match_ids),
            complete=complete,
        ),
    )


def _hero_cast(
    matches: Sequence[V7CanonicalMatch],
    metadata: Mapping[int, Mapping[str, object]],
) -> HeroCast:
    counts = Counter(match.hero_id for match in matches if match.hero_id is not None)
    missing: list[int] = []
    rows: list[HeroUsage] = []
    maximum = max(counts.values(), default=0)
    for hero_id, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        name = str(metadata.get(hero_id, {}).get("display_name") or "").strip()
        if not name:
            missing.append(hero_id)
            continue
        rows.append(
            HeroUsage(
                hero_id=hero_id,
                display_name=name,
                eligible_match_count=count,
                tied_for_most_played=count == maximum,
            )
        )
    leaders = sum(row.tied_for_most_played for row in rows)
    return HeroCast(
        heroes=rows,
        missing_display_metadata_hero_ids=missing,
        has_unique_most_played=leaders == 1
        and not any(counts[hero_id] == maximum for hero_id in missing),
    )


def _activity_memory(
    matches: Sequence[V7CanonicalMatch], *, complete: bool
) -> ActivityMemory | None:
    daily = Counter(
        _utc_date(match.started_at) for match in matches if match.started_at is not None
    )
    if not daily:
        return None
    starts = sorted(daily)
    windows = [
        (start, sum(daily[start + timedelta(days=offset)] for offset in range(7)))
        for start in starts
    ]
    populated = [item for item in windows if item[1] > 0]
    # Require two non-overlapping observed stretches; overlapping views of one
    # cluster are not independent evidence that activity varies over time.
    if not any((right - left).days >= 7 for left, _ in populated for right, _ in populated):
        return None
    start, count = max(populated, key=lambda item: (item[1], item[0]))
    if count < 3:
        return None
    return ActivityMemory(
        start_date=start,
        end_date=start + timedelta(days=6),
        eligible_match_count=count,
        claim_status="busiest" if complete else "recorded",
    )


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _next_month(value: date) -> date:
    return (value.replace(day=28) + timedelta(days=4)).replace(day=1)


def _monthly_contrast(
    matches: Sequence[V7CanonicalMatch],
    history: V7CanonicalHistory,
    metadata: Mapping[int, Mapping[str, object]],
    *,
    complete: bool,
) -> MonthlyHeroContrast | None:
    if not complete:
        return None
    requested_start = _utc_date(history.window.start_timestamp)
    requested_end = _utc_date(history.window.end_timestamp)
    by_month: dict[date, Counter[int]] = {}
    for match in matches:
        if match.started_at is None or match.hero_id is None:
            continue
        month = _month_start(_utc_date(match.started_at))
        by_month.setdefault(month, Counter())[match.hero_id] += 1
    leaders: dict[date, MonthlyHeroLeader] = {}
    for month, counts in by_month.items():
        month_end = _next_month(month) - timedelta(days=1)
        if month < requested_start or month_end > requested_end:
            continue
        total = sum(counts.values())
        top = max(counts.values(), default=0)
        hero_ids = sorted(hero_id for hero_id, count in counts.items() if count == top)
        if total < 10 or len(hero_ids) != 1 or top / total < 0.30:
            continue
        hero_id = hero_ids[0]
        name = str(metadata.get(hero_id, {}).get("display_name") or "").strip()
        if not name:
            continue
        leaders[month] = MonthlyHeroLeader(
            month=month.strftime("%Y-%m"),
            hero_id=hero_id,
            display_name=name,
            eligible_match_count=total,
            leader_match_count=top,
            leader_share=top / total,
        )
    candidates = [
        (
            min(leaders[month].eligible_match_count, leaders[later].eligible_match_count),
            later,
            leaders[month],
            leaders[later],
        )
        for month in sorted(leaders)
        for later in [_next_month(month)]
        if later in leaders and leaders[month].hero_id != leaders[later].hero_id
    ]
    if not candidates:
        return None
    _, _, earlier, later = max(
        candidates,
        key=lambda item: (item[0], item[1], -item[2].hero_id, -item[3].hero_id),
    )
    return MonthlyHeroContrast(earlier=earlier, later=later)


def _completed_loss_run(
    matches: Sequence[V7CanonicalMatch],
    *,
    known_gap_after_match_ids: frozenset[int],
    complete: bool,
) -> CompletedLossRun | None:
    if any(match.started_at is None for match in matches):
        return None
    ordered = sorted(
        matches,
        key=lambda match: (match.started_at or 0, match.match_id),
    )
    candidates: list[CompletedLossRun] = []
    losses: list[V7CanonicalMatch] = []
    for match in ordered:
        if losses and losses[-1].match_id in known_gap_after_match_ids:
            losses = []
        if match.won is None:
            losses = []
            continue
        if match.won is False:
            losses.append(match)
            continue
        if len(losses) >= 3:
            first_loss_at = losses[0].started_at
            final_loss_at = losses[-1].started_at
            following_win_at = match.started_at
            assert first_loss_at is not None
            assert final_loss_at is not None
            assert following_win_at is not None
            candidates.append(
                CompletedLossRun(
                    loss_count=len(losses),
                    first_loss_at=first_loss_at,
                    final_loss_at=final_loss_at,
                    following_win_at=following_win_at,
                    maximum_claim_safe=complete,
                )
            )
        losses = []
    return (
        max(candidates, key=lambda item: (item.loss_count, item.following_win_at))
        if candidates
        else None
    )


__all__ = [
    "DESCRIPTIVE_PRODUCER_VERSION",
    "ActivityMemory",
    "CompletedLossRun",
    "DescriptiveFacts",
    "HeroCast",
    "HeroUsage",
    "MonthlyHeroContrast",
    "MonthlyHeroLeader",
    "ReportScope",
    "TimeWindow",
    "derive_descriptive_facts",
]

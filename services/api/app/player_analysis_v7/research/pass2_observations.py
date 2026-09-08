"""Per-observation series for the Pass-2 Finding dimensions.

``pass2_features`` answers "what is this player's value on this dimension".
That is the right shape for a census and the wrong shape for ranking: the
ranking model needs a standard error, and a standard error needs the series
the value was computed from, not the value.

This module supplies that series. Every dimension here emits
``features.Opportunity`` records in the player's chronological order, so a
Pass-2 dimension goes through exactly the same estimation path as a Pass-1
family: ``inference.build_matrix`` removes additive context, blocked means
give ``delta_hat`` and ``SE``, and ``inference.variance_ratio_curve`` gives
the dependence inflation ``D``. One estimator, one population fit, one
comparable ``reliability``. A bespoke Pass-2 standard error would put two
incomparable scales into the same ranking.

Two estimands differ, on purpose, from their ``pass2_features`` counterparts,
because a blocked *mean* is the estimator the inference layer implements:

* ``spike_usage`` here is the **mean** gap in seconds; the census reports the
  median. The mean of a heavy-tailed gap is the less robust summary of the
  two, and the number this module produces should be read as "mean seconds
  to first impact", not as the census figure under another name.
* ``deaths_alone_share`` and ``vision_coverage`` are means of a per-match
  share in both places, so they agree.

The rate dimensions (``fight_conversion``, ``death_clustering``) are pooled
Bernoulli series here and pooled ratios in the census. Those agree only when
every match contributes equally; the mean of the 0/1 series is the pooled
rate by construction, so they do agree.

Read-only. No provider call. DISCOVERY only, enforced upstream by
``pass2_tables.iter_pass2_players``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.player_analysis_v7.research import pass2_tables as pt
from app.player_analysis_v7.research import tables as pass1_tables
from app.player_analysis_v7.research.features import Opportunity, base_ctx
from app.player_analysis_v7.research.pass2_features import (
    _OUTCOME_FIELD_BY_MAP_LANE,
    DEATH_CLUSTER_WINDOW_SECONDS,
    LANE_TO_MAP_MINUTE,
    LEAD_THRESHOLD_GOLD,
    _first_real_item_purchase_time,
    _item_vocabulary,
    _map_own_lane_to_map_lane,
    _match_vision_coverage,
    _next_kill_or_assist_time,
    _observer_ward_events,
    _won_own_lane,
)

Row = dict[str, Any]

OBSERVATION_VERSION = "v7-pass2-observations-1.0.0"

#: Arm labels for the two Pass-2 contrast dimensions.
ARM_WON_LANE = "won_lane"
ARM_LOST_LANE = "lost_lane"
ARM_AHEAD = "ahead"
ARM_BEHIND = "behind"


def _self(row: Row) -> Mapping[str, Any] | None:
    self_ = row.get("self")
    return self_ if isinstance(self_, Mapping) else None


def _pass2_context_available(row: Row) -> bool:
    """Reject explicitly unavailable identity fields before projection.

    The deep normalizer includes nullable ``hero_id`` and ``is_radiant`` keys.
    A row that omits either key is equally unable to support the corresponding
    context level, so it is unavailable rather than an ``UNKNOWN`` projection
    level.
    """

    self_ = _self(row)
    if self_ is None:
        return False
    if "hero_id" not in self_ or self_.get("hero_id") is None:
        return False
    side = self_.get("is_radiant")
    if "is_radiant" not in self_ or not isinstance(side, bool):
        return False
    return True


def pass2_ctx(row: Row) -> tuple[tuple[str, str], ...]:
    """Context factors for one Pass-2 row.

    Reuses Pass-1's ``base_ctx`` rather than re-deriving the factor set, via
    a thin adapter: Pass 2 nests ``hero_id`` and ``is_radiant`` under
    ``self`` where Pass 1 has them at the row's top level. Position and lane
    are added because every Pass-2 match is parsed by construction, so the
    parsed-linked factors are always available here (Pass 1 has to declare
    that dependence per family).
    """

    self_ = _self(row) or {}
    adapter = dict(row)
    adapter["hero_id"] = self_.get("hero_id")
    adapter["is_radiant"] = self_.get("is_radiant")
    factors = list(base_ctx(adapter))
    factors.append(("position", str(self_.get("position_native"))))
    factors.append(("lane", str(self_.get("lane_native"))))
    return tuple(factors)


# ---------------------------------------------------------------------------
# 1. deaths_alone_share - one observation per match in which the player died
# ---------------------------------------------------------------------------


def deaths_alone_share(rows: Sequence[Row]) -> list[Opportunity]:
    out: list[Opportunity] = []
    for row in rows:
        if not _pass2_context_available(row):
            continue
        share = pt.deaths_alone_share(row)
        if share is None:
            continue
        out.append(Opportunity(float(share), pass2_ctx(row)))
    return out


# ---------------------------------------------------------------------------
# 2. fight_conversion - one observation per won-fight minute
# ---------------------------------------------------------------------------


def _enemy_tower_fell_soon_after(
    row: Row, is_radiant: bool, fight_minute: int
) -> bool | None:
    tower_deaths = row.get("tower_deaths")
    if tower_deaths is None:
        return None
    window = {fight_minute + 1, fight_minute + 2}
    for event in tower_deaths:
        died_is_radiant = event.get("is_radiant")
        time = event.get("time")
        if died_is_radiant is None or time is None:
            continue
        if died_is_radiant == is_radiant:
            continue  # own-side tower, not a conversion
        if (time // 60) in window:
            return True
    return False


def fight_conversion(rows: Sequence[Row]) -> list[Opportunity]:
    out: list[Opportunity] = []
    for row in rows:
        if not _pass2_context_available(row):
            continue
        self_ = _self(row)
        if self_ is None:
            continue
        is_radiant = self_.get("is_radiant")
        if is_radiant is None:
            continue
        adapter = {
            "radiant_kills": row.get("radiant_kills"),
            "dire_kills": row.get("dire_kills"),
            "radiant_networth_leads": row.get("radiant_networth_leads"),
            "duration_seconds": row.get("duration_seconds"),
            "is_radiant": is_radiant,
        }
        pair = pass1_tables.team_kill_trajectories(adapter)
        if pair is None:
            continue
        own_kills, enemy_kills = pair
        ctx = pass2_ctx(row)
        for minute in range(min(len(own_kills), len(enemy_kills))):
            own = own_kills[minute]
            enemy = enemy_kills[minute]
            if own is None or enemy is None:
                continue
            if own < pt.FIGHT_KILL_THRESHOLD or enemy != 0:
                continue
            converted = _enemy_tower_fell_soon_after(row, is_radiant, minute)
            if converted is None:
                continue
            out.append(Opportunity(1.0 if converted else 0.0, ctx))
    return out


# ---------------------------------------------------------------------------
# 3. spike_usage - one observation per match with a purchase and a follow-up
# ---------------------------------------------------------------------------


def spike_usage(rows: Sequence[Row]) -> list[Opportunity]:
    vocabulary = _item_vocabulary()
    out: list[Opportunity] = []
    for row in rows:
        if not _pass2_context_available(row):
            continue
        purchase_time = _first_real_item_purchase_time(row, vocabulary)
        if purchase_time is None:
            continue
        next_event_time = _next_kill_or_assist_time(row, purchase_time)
        if next_event_time is None:
            continue
        out.append(Opportunity(float(next_event_time - purchase_time), pass2_ctx(row)))
    return out


# ---------------------------------------------------------------------------
# 4. death_clustering - one observation per death-to-death gap
# ---------------------------------------------------------------------------


def death_clustering(rows: Sequence[Row]) -> list[Opportunity]:
    out: list[Opportunity] = []
    for row in rows:
        if not _pass2_context_available(row):
            continue
        self_ = _self(row)
        if self_ is None:
            continue
        events = self_.get("events")
        death_events = events.get("death_events") if isinstance(events, Mapping) else None
        if not death_events:
            continue
        times = sorted(event["time"] for event in death_events if event.get("time") is not None)
        ctx = pass2_ctx(row)
        for previous, current in zip(times, times[1:], strict=False):
            clustered = (current - previous) <= DEATH_CLUSTER_WINDOW_SECONDS
            out.append(Opportunity(1.0 if clustered else 0.0, ctx))
    return out


# ---------------------------------------------------------------------------
# 5. lane_to_map - contrast, one observation per match with a resolved lane
# ---------------------------------------------------------------------------


def lane_to_map(rows: Sequence[Row]) -> list[Opportunity]:
    out: list[Opportunity] = []
    for row in rows:
        if not _pass2_context_available(row):
            continue
        self_ = _self(row)
        if self_ is None:
            continue
        is_radiant = self_.get("is_radiant")
        if is_radiant is None:
            continue
        map_lane = _map_own_lane_to_map_lane(is_radiant, self_.get("lane_native"))
        if map_lane is None:
            continue
        won = _won_own_lane(is_radiant, row.get(_OUTCOME_FIELD_BY_MAP_LANE[map_lane]))
        if won is None:
            continue
        curve = pt.own_networth_curve(row)
        if curve is None or len(curve) <= LANE_TO_MAP_MINUTE:
            continue
        net_worth = curve[LANE_TO_MAP_MINUTE]
        if net_worth is None:
            continue
        out.append(
            Opportunity(
                float(net_worth),
                pass2_ctx(row),
                ARM_WON_LANE if won else ARM_LOST_LANE,
            )
        )
    return out


# ---------------------------------------------------------------------------
# 6. closer_vs_comeback - contrast; a single match may serve both arms
# ---------------------------------------------------------------------------


def closer_vs_comeback(rows: Sequence[Row]) -> list[Opportunity]:
    out: list[Opportunity] = []
    for row in rows:
        if not _pass2_context_available(row):
            continue
        self_ = _self(row)
        if self_ is None:
            continue
        is_victory = self_.get("is_victory")
        if is_victory is None:
            continue
        curve = pt.team_lead_curve(row)
        if not curve:
            continue
        ctx = pass2_ctx(row)
        won = 1.0 if is_victory else 0.0
        if max(curve) >= LEAD_THRESHOLD_GOLD:
            out.append(Opportunity(won, ctx, ARM_AHEAD))
        if min(curve) <= -LEAD_THRESHOLD_GOLD:
            out.append(Opportunity(won, ctx, ARM_BEHIND))
    return out


# ---------------------------------------------------------------------------
# 7. vision_coverage - one observation per match, for players who ward at all
# ---------------------------------------------------------------------------


def vision_coverage(rows: Sequence[Row]) -> list[Opportunity]:
    """Empty for a player who never placed an observer ward.

    The gate is the one ``pass2_features.vision_coverage`` sets and for the
    same reason: a core who never wards is out of scope for the dimension,
    not the worst warder in the corpus.
    """

    ever_warded = False
    out: list[Opportunity] = []
    for row in rows:
        if not _pass2_context_available(row):
            continue
        observer_wards = _observer_ward_events(row)
        if observer_wards is None:
            continue
        if observer_wards:
            ever_warded = True
        coverage = _match_vision_coverage(row, observer_wards)
        if coverage is None:
            continue
        out.append(Opportunity(float(coverage), pass2_ctx(row)))
    return out if ever_warded else []


# ---------------------------------------------------------------------------
# 8. lane_vs_jungle_share - one observation per match with creep gold
# ---------------------------------------------------------------------------


def lane_vs_jungle_share(rows: Sequence[Row]) -> list[Opportunity]:
    out: list[Opportunity] = []
    for row in rows:
        if not _pass2_context_available(row):
            continue
        split = pt.lane_vs_jungle_gold(row)
        if split is None:
            continue
        lane_gold, jungle_gold = split
        total = lane_gold + jungle_gold
        if total <= 0:
            continue
        out.append(Opportunity(jungle_gold / total, pass2_ctx(row)))
    return out


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pass2Dimension:
    """One Pass-2 dimension as the ranking pipeline consumes it."""

    key: str
    fn: Callable[[Sequence[Row]], list[Opportunity]]
    section: str
    arm_family: bool
    treated: str | None
    control: str | None
    estimand: str


OBSERVATION_REGISTRY: dict[str, Pass2Dimension] = {
    dimension.key: dimension
    for dimension in (
        Pass2Dimension(
            "deaths_alone_share",
            deaths_alone_share,
            "what_is_costing_you",
            False,
            None,
            None,
            "mean per-match share of deaths in a minute with no team kill activity",
        ),
        Pass2Dimension(
            "fight_conversion",
            fight_conversion,
            "what_is_costing_you",
            False,
            None,
            None,
            "rate a won fight minute is followed by an enemy tower within two minutes",
        ),
        Pass2Dimension(
            "spike_usage",
            spike_usage,
            "what_is_good",
            False,
            None,
            None,
            "mean seconds from first real item to next kill or assist "
            "(the census reports the median of the same series)",
        ),
        Pass2Dimension(
            "death_clustering",
            death_clustering,
            "what_is_costing_you",
            False,
            None,
            None,
            "share of death-to-death gaps at or under 90 seconds",
        ),
        Pass2Dimension(
            "lane_to_map",
            lane_to_map,
            "what_is_costing_you",
            True,
            ARM_WON_LANE,
            ARM_LOST_LANE,
            "own net worth at minute 20, won lane minus lost lane",
        ),
        Pass2Dimension(
            "closer_vs_comeback",
            closer_vs_comeback,
            "response_to_a_loss",
            True,
            ARM_AHEAD,
            ARM_BEHIND,
            "win rate given a 10k lead minus win rate given a 10k deficit",
        ),
        Pass2Dimension(
            "vision_coverage",
            vision_coverage,
            "what_is_good",
            False,
            None,
            None,
            "mean per-match share of minutes with an own observer ward alive",
        ),
        Pass2Dimension(
            "lane_vs_jungle_share",
            lane_vs_jungle_share,
            "what_is_good",
            False,
            None,
            None,
            "mean per-match share of creep gold taken from neutrals",
        ),
    )
}


def chronological(rows: Sequence[Row]) -> list[Row]:
    """One player's rows, oldest first.

    The blocked-means standard error and the variance-ratio curve both read
    order as time. Pass-2 documents are not stored in time order, so every
    caller must sort before building a series; doing it here means no caller
    has to remember.
    """

    return sorted(rows, key=lambda row: (row.get("started_at") or 0, row.get("match_id") or 0))


__all__ = [
    "OBSERVATION_REGISTRY",
    "OBSERVATION_VERSION",
    "Pass2Dimension",
    "chronological",
    "closer_vs_comeback",
    "death_clustering",
    "deaths_alone_share",
    "fight_conversion",
    "lane_to_map",
    "lane_vs_jungle_share",
    "pass2_ctx",
    "spike_usage",
    "vision_coverage",
]

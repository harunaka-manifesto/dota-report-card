"""Per-player Finding estimands over the V7 Pass-2 corpus.

This module is **feature extraction only**: one function per Finding
dimension (`docs/evidence/v7-report-narrative-and-data-requirements-2026-09-04.md`
§2.10), each folding a player's own product-context rows into a single
value (or a win/loss-style contrast) plus the observation count it rests
on. It does not rank, z-score, or assess reliability — that is a separate
worker's module (`scripts/v7_research/ranking.py`, not owned here).

Every semantics decision below defers to ``pass2_tables`` (alignment,
orientation, event handling) or to a specific, cited piece of corpus
evidence gathered while writing this module. Nothing here re-derives a
rule ``pass2_tables`` already settled.

--------------------------------------------------------------------------
The lane-side mapping (dimension 5, ``lane_to_map``)
--------------------------------------------------------------------------

The corpus carries two different lane concepts that must not be conflated:

- ``self.lane_native``: the player's own lane, described from *their own
  side's* point of view — one of ``SAFE_LANE``, ``MID_LANE``, ``OFF_LANE``,
  plus ``JUNGLE`` / ``ROAMING`` for players who did not lane.
- ``{bottom,mid,top}_lane_outcome_native``: the match-level outcome of a
  fixed *map* lane (bottom / mid / top), each one of ``RADIANT_VICTORY``,
  ``DIRE_VICTORY``, ``RADIANT_STOMP``, ``DIRE_STOMP``, ``TIE``.

"Safe lane" and "off lane" are side-relative in Dota by long-standing map
convention: Radiant's base sits bottom-left, so Radiant's safe (easy) lane
is the map's bottom lane and Radiant's off lane is the map's top lane;
for Dire, holding the top-right base, the assignment is the mirror image
(safe lane = top, off lane = bottom). Mid is mid for both sides. Sampling
the corpus (30 accounts, ~13,000 rows) confirms the two fields are
independently populated and not redundant: ``lane_native`` values
(``OFF_LANE`` 4,861, ``SAFE_LANE`` 4,644, ``MID_LANE`` 3,396, ``None`` 205,
``JUNGLE`` 62, ``ROAMING`` 20, ``UNKNOWN`` 7) and outcome values
(``RADIANT_VICTORY`` 12,067, ``DIRE_VICTORY`` 11,409, ``TIE`` 9,548,
``RADIANT_STOMP`` 2,896, ``DIRE_STOMP`` 2,603, ``None`` 1,062, summed
across the three map-lane fields) are exactly the shapes the mapping
predicts, with no field carrying a spurious extra value. The mapping
implemented in ``_map_own_lane_to_map_lane`` is therefore:

    MID_LANE                          -> "mid"
    SAFE_LANE, is_radiant=True        -> "bottom"
    SAFE_LANE, is_radiant=False       -> "top"
    OFF_LANE,  is_radiant=True        -> "top"
    OFF_LANE,  is_radiant=False       -> "bottom"
    JUNGLE / ROAMING / UNKNOWN / None -> no map lane (excluded)

A player's lane counts as "won" if the outcome on their mapped map lane
names their own side (``RADIANT_VICTORY``/``RADIANT_STOMP`` for a Radiant
player, the Dire equivalents for a Dire player). ``TIE`` is deliberately
folded into "did not win" rather than dropped: the Finding asks "did
winning your lane mean anything," and a tied lane is, by definition, not
one the player won. A missing or unrecognized outcome value excludes the
match from the contrast entirely (fails closed rather than guessing a
side).

--------------------------------------------------------------------------
The observer-ward type assumption (dimension 7, ``vision_coverage``)
--------------------------------------------------------------------------

``self.events.wards[].type`` is not documented in the collection notes.
Sampling the corpus (40 accounts, ~104,000 ward events) finds exactly two
values: ``0`` (37,703 occurrences) and ``1`` (66,291 occurrences). This
module treats ``0`` as OBSERVER and ``1`` as SENTRY, on two supporting
signals: STRATZ's own enum ordering elsewhere in this corpus is
consistently alphabetical-by-role (index 0 is the "first" or more basic
variant), and the frequency skew matches expectation — sentries are
bought in greater number per game than observers under Dota's economy
(more slots, shorter effective coverage need, frequently rebought after
being killed).

**Verified 2026-09-05** against the item-purchase stream, which is an
independent record of the same act. Over 12,164 matches carrying both
wards and purchases, the count of ``type == 0`` wards is closer to the
player's observer purchases than to their sentry purchases in 78.0% of
matches, and ``type == 1`` is closer to sentry purchases in 72.9%. The
contingency is decisive in the same direction: of matches where the
player bought more observers than sentries, 2,748 placed more type-0
wards against 222 that did not. The reading is no longer an inference.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from scripts.v7_research import pass2_tables as pt
from scripts.v7_research import tables as pass1_tables
from services.api.app.stratz.item_vocabulary import (
    ItemInfo,
    is_real_item,
    load_item_vocabulary,
)

FEATURE_VERSION = "v7-pass2-features-1"

Row = dict[str, Any]

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

# The floor below which a per-player estimand is reported as unsupported
# (``None``) rather than as a number resting on too little evidence. Kept
# as a single named constant so every dimension states the same bar; a
# contrast dimension applies it to *each* side independently.
MIN_OBSERVATIONS = 5

# Dimension 6: the net-worth-lead threshold a "closer / comeback" episode
# must cross, in gold. Matches the Finding's own wording ("+/-10k").
LEAD_THRESHOLD_GOLD = 10_000

# Dimension 3: a death counts as "clustered" if it follows the player's
# previous death by no more than this many seconds. The report's own
# wording ("within 90 seconds") is inclusive of the boundary.
DEATH_CLUSTER_WINDOW_SECONDS = 90

# Dimension 7: how long a placed observer ward stays alive/useful, in
# seconds (an observer ward's in-game duration is 6 minutes).
OBSERVER_WARD_DURATION_SECONDS = 6 * 60

# Dimension 7: the ward-event "type" value this module reads as observer
# (as opposed to sentry). See the module docstring for the evidence and
# its confidence level.
OBSERVER_WARD_TYPE = 0

# Dimension 5: outcome strings the lane-outcome fields are observed to
# carry (rule verified in the module docstring). Any other value fails
# closed rather than being guessed at.
_KNOWN_LANE_OUTCOMES = frozenset(
    {"RADIANT_VICTORY", "DIRE_VICTORY", "RADIANT_STOMP", "DIRE_STOMP", "TIE"}
)
_RADIANT_WON_LANE_OUTCOMES = frozenset({"RADIANT_VICTORY", "RADIANT_STOMP"})
_DIRE_WON_LANE_OUTCOMES = frozenset({"DIRE_VICTORY", "DIRE_STOMP"})

# Dimension 5: minute at which the lane-versus-map-lead contrast is taken.
LANE_TO_MAP_MINUTE = 20

_ITEM_VOCABULARY: dict[int, ItemInfo] | None = None


def _item_vocabulary() -> dict[int, ItemInfo]:
    """Lazily load and cache the STRATZ item vocabulary (no network call;
    reads the committed JSON file once per process)."""

    global _ITEM_VOCABULARY
    if _ITEM_VOCABULARY is None:
        _ITEM_VOCABULARY = load_item_vocabulary()
    return _ITEM_VOCABULARY


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeatureValue:
    """One numeric estimand and the observation count it rests on."""

    value: float
    observations: int


@dataclass(frozen=True)
class FeatureResult:
    """The outcome of one dimension's feature function for one player.

    ``secondary`` is populated only for contrast dimensions (win value vs
    loss value, or "closing" rate vs "recovering" rate); it is ``None``
    for a plain per-player rate or share. A dimension with insufficient
    support returns ``None`` for the whole result, never a
    ``FeatureResult`` built on a value that should not be trusted.
    """

    primary: FeatureValue
    secondary: FeatureValue | None = None


# ---------------------------------------------------------------------------
# 1. deaths_alone_share
# ---------------------------------------------------------------------------


def deaths_alone_share(rows: Sequence[Row]) -> FeatureResult | None:
    """Mean, across the player's matches, of the per-match
    ``pass2_tables.deaths_alone_share``.

    Minimum support: at least ``MIN_OBSERVATIONS`` matches in which the
    player died at least once (a match with zero deaths contributes no
    per-match value to average, per ``pass2_tables.deaths_alone_share``'s
    own ``None`` convention).
    """

    per_match = [
        share
        for row in rows
        if (share := pt.deaths_alone_share(row)) is not None
    ]
    if len(per_match) < MIN_OBSERVATIONS:
        return None
    return FeatureResult(FeatureValue(statistics.mean(per_match), len(per_match)))


# ---------------------------------------------------------------------------
# 2. fight_conversion
# ---------------------------------------------------------------------------


def _enemy_tower_fell_soon_after(row: Row, is_radiant: bool, fight_minute: int) -> bool:
    """Whether a tower belonging to the *enemy* side died in the two
    minutes following ``fight_minute`` (rule 3 ownership semantics)."""

    tower_deaths = row.get("tower_deaths") or []
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


def fight_conversion(rows: Sequence[Row]) -> FeatureResult | None:
    """Rate at which a minute where the player's team scored >= 2 kills and
    conceded 0 is followed, within the next two minutes, by an enemy
    tower falling.

    One observation per qualifying minute, pooled across all of the
    player's matches (not one observation per match — a single long game
    can supply several qualifying minutes). Minimum support:
    ``MIN_OBSERVATIONS`` qualifying minutes.
    """

    converted = 0
    total = 0
    for row in rows:
        self_ = row.get("self")
        if not isinstance(self_, Mapping):
            continue
        is_radiant = self_.get("is_radiant")
        if is_radiant is None:
            continue
        # pass1_tables.team_kill_trajectories reads is_radiant off the row's
        # top level (its own row shape); pass2 nests it under "self" (same
        # adaptation team_lead_curve makes in pass2_tables).
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
        for minute in range(len(own_kills)):
            own = own_kills[minute] or 0
            enemy = enemy_kills[minute] if minute < len(enemy_kills) else 0
            enemy = enemy or 0
            if own < pt.FIGHT_KILL_THRESHOLD or enemy != 0:
                continue
            total += 1
            if _enemy_tower_fell_soon_after(row, is_radiant, minute):
                converted += 1

    if total < MIN_OBSERVATIONS:
        return None
    return FeatureResult(FeatureValue(converted / total, total))


# ---------------------------------------------------------------------------
# 3. spike_usage
# ---------------------------------------------------------------------------


def _first_real_item_purchase_time(row: Row, vocabulary: Mapping[int, ItemInfo]) -> int | None:
    self_ = row.get("self")
    if not isinstance(self_, Mapping):
        return None
    events = self_.get("events")
    purchases = (events or {}).get("item_purchases") if isinstance(events, Mapping) else None
    if not purchases:
        return None
    real_purchase_times = [
        purchase["time"]
        for purchase in purchases
        if purchase.get("time") is not None
        and (item := vocabulary.get(purchase.get("item_id")))
        and is_real_item(item)
    ]
    if not real_purchase_times:
        return None
    return min(real_purchase_times)


def _next_kill_or_assist_time(row: Row, after: int) -> int | None:
    self_ = row.get("self")
    if not isinstance(self_, Mapping):
        return None
    events = self_.get("events")
    if not isinstance(events, Mapping):
        return None
    candidates: list[int] = []
    for key in ("kill_events", "assist_events"):
        for event in events.get(key) or []:
            time = event.get("time")
            if time is not None and time > after:
                candidates.append(time)
    if not candidates:
        return None
    return min(candidates)


def spike_usage(rows: Sequence[Row]) -> FeatureResult | None:
    """Median, across the player's matches, of the gap (seconds) between
    their first real-item purchase and their next kill or assist.

    A match contributes only if it has both a qualifying purchase and a
    subsequent kill/assist event; a match with neither is excluded, not
    counted as a zero or an infinite gap. Minimum support:
    ``MIN_OBSERVATIONS`` contributing matches.
    """

    vocabulary = _item_vocabulary()
    gaps: list[int] = []
    for row in rows:
        purchase_time = _first_real_item_purchase_time(row, vocabulary)
        if purchase_time is None:
            continue
        next_event_time = _next_kill_or_assist_time(row, purchase_time)
        if next_event_time is None:
            continue
        gaps.append(next_event_time - purchase_time)

    if len(gaps) < MIN_OBSERVATIONS:
        return None
    return FeatureResult(FeatureValue(float(statistics.median(gaps)), len(gaps)))


# ---------------------------------------------------------------------------
# 4. death_clustering
# ---------------------------------------------------------------------------


def death_clustering(rows: Sequence[Row]) -> FeatureResult | None:
    """Share of the player's deaths occurring within
    ``DEATH_CLUSTER_WINDOW_SECONDS`` of their previous death, in the same
    match (a match boundary never counts as "the previous death" — deaths
    in different matches are unrelated events).

    A match's first death has no "previous death" and does not contribute
    a gap. Minimum support: ``MIN_OBSERVATIONS`` eligible gaps (i.e. death
    pairs), pooled across matches.
    """

    clustered = 0
    total_gaps = 0
    for row in rows:
        self_ = row.get("self")
        if not isinstance(self_, Mapping):
            continue
        events = self_.get("events")
        death_events = (
            (events or {}).get("death_events") if isinstance(events, Mapping) else None
        )
        if not death_events:
            continue
        times = sorted(
            event["time"] for event in death_events if event.get("time") is not None
        )
        for previous, current in zip(times, times[1:], strict=False):
            total_gaps += 1
            if current - previous <= DEATH_CLUSTER_WINDOW_SECONDS:
                clustered += 1

    if total_gaps < MIN_OBSERVATIONS:
        return None
    return FeatureResult(FeatureValue(clustered / total_gaps, total_gaps))


# ---------------------------------------------------------------------------
# 5. lane_to_map
# ---------------------------------------------------------------------------


def _map_own_lane_to_map_lane(is_radiant: bool, lane_native: str | None) -> str | None:
    """Map the player's own-side lane onto a fixed map lane. See the
    module docstring for the evidence behind this mapping."""

    if lane_native == "MID_LANE":
        return "mid"
    if lane_native == "SAFE_LANE":
        return "bottom" if is_radiant else "top"
    if lane_native == "OFF_LANE":
        return "top" if is_radiant else "bottom"
    return None  # JUNGLE, ROAMING, UNKNOWN, None: no fixed map lane


_OUTCOME_FIELD_BY_MAP_LANE = {
    "bottom": "bottom_lane_outcome_native",
    "mid": "mid_lane_outcome_native",
    "top": "top_lane_outcome_native",
}


def _won_own_lane(is_radiant: bool, outcome: str | None) -> bool | None:
    if outcome not in _KNOWN_LANE_OUTCOMES:
        return None  # missing or unrecognized: exclude the match
    won_outcomes = _RADIANT_WON_LANE_OUTCOMES if is_radiant else _DIRE_WON_LANE_OUTCOMES
    return outcome in won_outcomes


def lane_to_map(rows: Sequence[Row]) -> FeatureResult | None:
    """Contrast: the player's own net worth at minute
    ``LANE_TO_MAP_MINUTE`` when they won their lane versus when they did
    not (a tied lane counts as "did not win" — see the module docstring).

    Minimum support: ``MIN_OBSERVATIONS`` matches on *each* side of the
    contrast.
    """

    won_values: list[int] = []
    not_won_values: list[int] = []
    for row in rows:
        self_ = row.get("self")
        if not isinstance(self_, Mapping):
            continue
        is_radiant = self_.get("is_radiant")
        lane_native = self_.get("lane_native")
        if is_radiant is None:
            continue
        map_lane = _map_own_lane_to_map_lane(is_radiant, lane_native)
        if map_lane is None:
            continue
        outcome = row.get(_OUTCOME_FIELD_BY_MAP_LANE[map_lane])
        won = _won_own_lane(is_radiant, outcome)
        if won is None:
            continue
        curve = pt.own_networth_curve(row)
        if curve is None or len(curve) <= LANE_TO_MAP_MINUTE:
            continue
        net_worth_at_20 = curve[LANE_TO_MAP_MINUTE]
        if net_worth_at_20 is None:
            continue
        (won_values if won else not_won_values).append(net_worth_at_20)

    if len(won_values) < MIN_OBSERVATIONS or len(not_won_values) < MIN_OBSERVATIONS:
        return None
    return FeatureResult(
        primary=FeatureValue(statistics.mean(won_values), len(won_values)),
        secondary=FeatureValue(statistics.mean(not_won_values), len(not_won_values)),
    )


# ---------------------------------------------------------------------------
# 6. closer_vs_comeback
# ---------------------------------------------------------------------------


def closer_vs_comeback(rows: Sequence[Row]) -> FeatureResult | None:
    """Given the player's team ever reached a lead of at least
    ``LEAD_THRESHOLD_GOLD`` (oriented to the player), the rate at which
    that game was won ("closing when ahead"); and, separately, given the
    team was ever that far behind, the rate at which the game was still
    won ("recovering when behind").

    A single match can qualify for both sides of the contrast (a large
    enough swing) and is counted independently in each. Minimum support:
    ``MIN_OBSERVATIONS`` matches on *each* side.
    """

    ahead_wins = ahead_total = 0
    behind_wins = behind_total = 0
    for row in rows:
        self_ = row.get("self")
        if not isinstance(self_, Mapping):
            continue
        is_victory = self_.get("is_victory")
        if is_victory is None:
            continue
        curve = pt.team_lead_curve(row)
        if not curve:
            continue
        if max(curve) >= LEAD_THRESHOLD_GOLD:
            ahead_total += 1
            ahead_wins += bool(is_victory)
        if min(curve) <= -LEAD_THRESHOLD_GOLD:
            behind_total += 1
            behind_wins += bool(is_victory)

    if ahead_total < MIN_OBSERVATIONS or behind_total < MIN_OBSERVATIONS:
        return None
    return FeatureResult(
        primary=FeatureValue(ahead_wins / ahead_total, ahead_total),
        secondary=FeatureValue(behind_wins / behind_total, behind_total),
    )


# ---------------------------------------------------------------------------
# 7. vision_coverage
# ---------------------------------------------------------------------------


def _observer_ward_events(row: Row) -> list[Mapping[str, Any]]:
    wards = pt.ward_events(row) or []
    return [ward for ward in wards if ward.get("type") == OBSERVER_WARD_TYPE]


def _match_vision_coverage(row: Row, observer_wards: Sequence[Mapping[str, Any]]) -> float | None:
    duration = row.get("duration_seconds")
    if duration is None:
        return None
    grid_length = pass1_tables.expected_trajectory_length(duration)
    if grid_length <= 0:
        return None
    covered: set[int] = set()
    for ward in observer_wards:
        time = ward.get("time")
        if time is None:
            continue
        start_minute = max(0, time // 60)
        end_minute = (time + OBSERVER_WARD_DURATION_SECONDS - 1) // 60
        for minute in range(start_minute, min(end_minute, grid_length - 1) + 1):
            covered.add(minute)
    return len(covered) / grid_length


def vision_coverage(rows: Sequence[Row]) -> FeatureResult | None:
    """Mean, across the player's matches, of the share of game minutes
    with at least one of the player's observer wards plausibly alive.

    Only meaningful for a player who wards at all: if the player placed
    zero observer wards across every one of their rows, this returns
    ``None`` rather than a misleading 0.0 (a core who never wards is not
    "the worst warder in the corpus," they are out of scope for the
    dimension). A match with zero observer wards, once the player has
    warded at least once elsewhere, is a legitimate 0.0-coverage
    observation and is included.

    Minimum support: ``MIN_OBSERVATIONS`` matches with a computable
    coverage value.
    """

    ever_warded = False
    coverages: list[float] = []
    for row in rows:
        observer_wards = _observer_ward_events(row)
        if observer_wards:
            ever_warded = True
        coverage = _match_vision_coverage(row, observer_wards)
        if coverage is not None:
            coverages.append(coverage)

    if not ever_warded:
        return None
    if len(coverages) < MIN_OBSERVATIONS:
        return None
    return FeatureResult(FeatureValue(statistics.mean(coverages), len(coverages)))


# ---------------------------------------------------------------------------
# 8. lane_vs_jungle_share
# ---------------------------------------------------------------------------


def lane_vs_jungle_share(rows: Sequence[Row]) -> FeatureResult | None:
    """Mean, across the player's matches, of the share of creep gold that
    came from neutrals (``lane_vs_jungle_gold``: jungle / (lane + jungle)).

    A match with zero recorded creep gold of either kind is excluded (the
    share is undefined, not 0.0). Minimum support: ``MIN_OBSERVATIONS``
    matches with a computable share.
    """

    shares: list[float] = []
    for row in rows:
        split = pt.lane_vs_jungle_gold(row)
        if split is None:
            continue
        lane_gold, jungle_gold = split
        total = lane_gold + jungle_gold
        if total <= 0:
            continue
        shares.append(jungle_gold / total)

    if len(shares) < MIN_OBSERVATIONS:
        return None
    return FeatureResult(FeatureValue(statistics.mean(shares), len(shares)))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

REPORT_SECTIONS = frozenset(
    {"what_is_good", "what_is_costing_you", "response_to_a_loss"}
)


@dataclass(frozen=True)
class FeatureSpec:
    """One Finding dimension: its callable and the fixed, by-design
    properties another module (ranking, recommendation) reads off it."""

    key: str
    fn: Any
    description: str
    report_section: str
    is_contrast: bool
    is_actionable: bool

    def __post_init__(self) -> None:
        if self.report_section not in REPORT_SECTIONS:
            raise ValueError(f"unknown report_section {self.report_section!r}")


def _spec(
    key: str,
    fn: Any,
    description: str,
    report_section: str,
    *,
    is_contrast: bool,
    is_actionable: bool,
) -> FeatureSpec:
    return FeatureSpec(
        key=key,
        fn=fn,
        description=description,
        report_section=report_section,
        is_contrast=is_contrast,
        is_actionable=is_actionable,
    )


FEATURE_REGISTRY: dict[str, FeatureSpec] = {
    spec.key: spec
    for spec in (
        _spec(
            "deaths_alone_share",
            deaths_alone_share,
            "Share of the player's deaths falling in a minute with no team "
            "kill activity on either side.",
            "what_is_costing_you",
            is_contrast=False,
            is_actionable=True,
        ),
        _spec(
            "fight_conversion",
            fight_conversion,
            "Rate at which a minute where the player's team scored >= 2 "
            "kills and lost nobody is followed by an enemy tower falling "
            "within the next two minutes.",
            "what_is_costing_you",
            is_contrast=False,
            # Actionable, against the first reading. The tower falling is a
            # team result, but the behaviour being measured is the player's own
            # decision after a won fight - go to the tower, or go back to the
            # jungle. "When you win a fight, take the tower" is a thing a
            # player does in their next game, which is the test the
            # recommendation model sets. Contrast lane_to_map and
            # closer_vs_comeback, which are scoreboard readings the player
            # receives rather than behaviours they emit.
            is_actionable=True,
        ),
        _spec(
            "spike_usage",
            spike_usage,
            "Median seconds between the player's first real-item purchase "
            "and their next kill or assist.",
            "what_is_good",
            is_contrast=False,
            is_actionable=True,
        ),
        _spec(
            "death_clustering",
            death_clustering,
            "Share of the player's deaths occurring within 90 seconds of "
            "their previous death.",
            "what_is_costing_you",
            is_contrast=False,
            is_actionable=True,
        ),
        _spec(
            "lane_to_map",
            lane_to_map,
            "Contrast: own net worth at minute 20 when the player won "
            "their lane versus when they did not.",
            "what_is_costing_you",
            is_contrast=True,
            is_actionable=False,
        ),
        _spec(
            "closer_vs_comeback",
            closer_vs_comeback,
            "Contrast: win rate when the player's team ever led by 10k "
            "('closing when ahead') versus when it was ever down 10k "
            "('recovering when behind').",
            "response_to_a_loss",
            is_contrast=True,
            is_actionable=False,
        ),
        _spec(
            "vision_coverage",
            vision_coverage,
            "Share of game minutes with at least one of the player's "
            "observer wards plausibly alive (None if the player never "
            "warded).",
            "what_is_good",
            is_contrast=False,
            is_actionable=True,
        ),
        _spec(
            "lane_vs_jungle_share",
            lane_vs_jungle_share,
            "Share of the player's creep gold that came from neutrals.",
            "what_is_good",
            is_contrast=False,
            is_actionable=True,
        ),
    )
}


def compute_all(rows: Sequence[Row]) -> dict[str, FeatureResult | None]:
    """Compute every registered dimension for one player's rows."""

    return {key: spec.fn(rows) for key, spec in FEATURE_REGISTRY.items()}


def group_rows_by_account(
    rows: Iterable[Row],
) -> dict[str, list[Row]]:
    """Group product-context rows by ``account_pseudonym``.

    Callers are expected to have already filtered ``rows`` to
    ``is_pass2_product_context`` and to ``iter_pass2_players``'s
    enrichment (which sets ``account_pseudonym`` on every row).
    """

    grouped: dict[str, list[Row]] = {}
    for row in rows:
        account = row.get("account_pseudonym")
        if account is None:
            raise ValueError("pass2 row is missing account_pseudonym")
        grouped.setdefault(account, []).append(row)
    return grouped


__all__ = [
    "FEATURE_REGISTRY",
    "FEATURE_VERSION",
    "FeatureResult",
    "FeatureSpec",
    "FeatureValue",
    "closer_vs_comeback",
    "compute_all",
    "death_clustering",
    "deaths_alone_share",
    "fight_conversion",
    "group_rows_by_account",
    "lane_to_map",
    "lane_vs_jungle_share",
    "spike_usage",
    "vision_coverage",
]

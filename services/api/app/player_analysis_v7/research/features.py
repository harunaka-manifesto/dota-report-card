"""Deterministic V7 candidate feature layer.

Every function here derives *opportunities* — the unit of observation for one
candidate family — from the canonical corpus only, through
``app.player_analysis_v7.research.tables`` semantics. Nothing here issues a provider call,
reads a reserved split, or touches a forbidden provider surface.

Design rules enforced in this module
------------------------------------

1. **Mode is context, never a filter.** Turbo is 65% of the corpus. Every
   extractor pools ``TURBO`` and ``STANDARD`` and emits ``mode`` as a context
   key, per the capability atlas section 5.1.
2. **Minute-indexed quantities use normalised game progress**, not wall-clock
   minutes, because Turbo compresses the clock.
3. **Parsed dependence is declared, never silent.** A family whose extractor
   reads the parsed table declares ``parsed=True`` in the registry; role,
   position and lane are parsed-linked and carry the same declaration.
4. **The player's own net worth / last hits / denies / hero damage curves and
   own death timings do not exist in this corpus.** No extractor references
   them.
5. ``assist_events`` supplies **timing shape only**. Nothing here uses it as a
   count that must reconcile with the history table; count-based participation
   uses ``kill_events`` alone and says so.

Feature version is bumped whenever any extractor's semantics change.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from app.player_analysis_v7.research.corpus import DISCOVERY, CorpusPaths, iter_players
from app.player_analysis_v7.research.rank_fence import assert_row_is_analysis_safe
from app.player_analysis_v7.research.tables import (
    SESSION_GAP_SECONDS,
    is_product_context,
    iter_sessions,
    minute_grid_length,
    mode_stratum,
    order_by_time,
    player_networth_lead,
    team_kill_trajectories,
)

FEATURE_VERSION = "v7-luna-b-features-1.0.0"

#: Seconds of absence that make a returning match a "return from layoff".
LAYOFF_SECONDS = 3 * 24 * 3600

#: Net-worth-lead magnitude (gold) that defines a decided game state. Chosen
#: once, before any screening, and never tuned against an outcome.
STATE_LEAD_GOLD = 5_000

#: Ordinal of the item purchase used as the build-tempo landmark. Chosen as a
#: mid-build landmark reachable in both Turbo and standard games.
PURCHASE_LANDMARK = 8

#: Size of the causal "comfort pool" used by the Transfer family: the heroes a
#: player has played most in the matches *strictly before* the current one.
COMFORT_POOL_SIZE = 5

#: A hero counts as novel when it has not appeared in this many prior days.
NOVELTY_DAYS = 30

LANE_OUTCOME_LOSS = frozenset({"DIRE_STOMP", "DIRE_VICTORY", "RADIANT_STOMP", "RADIANT_VICTORY"})


@dataclass(frozen=True)
class Opportunity:
    """One unit of observation for one candidate family.

    ``value`` is the response. ``ctx`` maps context-factor name to a
    categorical level; the screen removes additive context effects before any
    between-player comparison. ``arm`` is ``None`` for level families and a
    two-level string for contrast families, in which case the per-player
    estimand is the treated-minus-control residual difference.
    """

    value: float
    ctx: tuple[tuple[str, str], ...]
    arm: str | None = None


@dataclass
class PlayerFrame:
    """A single sampled account's product-context evidence, time-ordered."""

    pseudonym: str
    split: str
    completeness: str
    rows: list[dict[str, Any]]
    parsed: dict[int, dict[str, Any]] = field(default_factory=dict)

    @property
    def truncated(self) -> bool:
        return self.completeness != "complete"

    def sessions(self) -> list[tuple[int, int]]:
        return [(s.start_index, s.end_index) for s in iter_sessions(self.rows, SESSION_GAP_SECONDS)]


def load_frames(
    paths: CorpusPaths,
    splits: frozenset[str] = frozenset({DISCOVERY}),
    with_parsed: bool = True,
) -> list[PlayerFrame]:
    """Load product-context frames for ``splits``.

    ``iter_players`` fails closed on reserved splits, so this cannot reach
    ``CALIBRATION_RESERVED`` or ``SEALED_VALIDATION`` whatever is passed.
    """

    frames: dict[str, PlayerFrame] = {}
    for document in iter_players(paths, "history", splits):
        rows = []
        for row in document["rows"]:
            assert_row_is_analysis_safe(row, source="pass1 history")
            if is_product_context(row):
                rows.append(row)
        frames[document["account_pseudonym"]] = PlayerFrame(
            pseudonym=document["account_pseudonym"],
            split=document["split"],
            completeness=document.get("completeness", "unknown"),
            rows=order_by_time(rows),
        )
    if with_parsed:
        for document in iter_players(paths, "parsed", splits):
            frame = frames.get(document["account_pseudonym"])
            if frame is None:
                continue
            parsed: dict[int, dict[str, Any]] = {}
            for row in document["rows"]:
                assert_row_is_analysis_safe(row, source="pass1 parsed")
                if row.get("radiant_networth_leads") is not None:
                    parsed[row["match_id"]] = row
            frame.parsed = parsed
    return list(frames.values())


# ---------------------------------------------------------------------------
# shared context helpers
# ---------------------------------------------------------------------------


def duration_bucket(row: dict[str, Any]) -> str:
    """Duration bucket on a *mode-relative* scale.

    Turbo games are structurally shorter, so a fixed wall-clock cut would make
    the bucket a proxy for the mode. Cuts are the mode's own quartile-like
    landmarks, declared here once.
    """

    seconds = row["duration_seconds"]
    if mode_stratum(row) == "TURBO":
        edges = (1_200, 1_500, 1_800)
    else:
        edges = (2_000, 2_400, 2_900)
    for index, edge in enumerate(edges):
        if seconds < edge:
            return f"D{index}"
    return f"D{len(edges)}"


def base_ctx(row: dict[str, Any]) -> list[tuple[str, str]]:
    """Context factors available for *every* product-context row."""

    return [
        ("mode", mode_stratum(row)),
        ("patch", str(row.get("game_version_id"))),
        ("hero", str(row.get("hero_id"))),
        ("duration", duration_bucket(row)),
        ("side", "R" if row.get("is_radiant") else "D"),
        ("lobby", str(row.get("lobby_type_native"))),
    ]


def role_ctx(row: dict[str, Any]) -> list[tuple[str, str]]:
    """Parsed-linked role context. Callers must declare the dependence."""

    return [
        ("position", str(row.get("position_native"))),
        ("role", str(row.get("role_native"))),
        ("lane", str(row.get("lane_native"))),
    ]


def per_ten_minutes(count: int, row: dict[str, Any]) -> float:
    return 600.0 * count / max(row["duration_seconds"], 1)


def progress(time_seconds: float, row: dict[str, Any]) -> float:
    """Normalised game progress in [0, 1] for a within-match timestamp."""

    return min(max(time_seconds / max(row["duration_seconds"], 1), 0.0), 1.0)


def _hour_of_day(row: dict[str, Any]) -> int:
    return (row["started_at"] // 3600) % 24


def _weekday(row: dict[str, Any]) -> int:
    # 1970-01-01 was a Thursday; day 0 -> index 4.
    return (row["started_at"] // 86400 + 4) % 7


# ---------------------------------------------------------------------------
# history-only extractors
# ---------------------------------------------------------------------------


def _transitions(frame: PlayerFrame) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    """Yield adjacent (current, next) pairs that lie wholly inside a session."""

    for start, end in frame.sessions():
        for index in range(start, end):
            yield frame.rows[index], frame.rows[index + 1]


def post_loss_next_outcome(frame: PlayerFrame) -> list[Opportunity]:
    out = []
    for current, following in _transitions(frame):
        arm = "loss" if not current["is_victory"] else "win"
        out.append(
            Opportunity(
                value=1.0 if following["is_victory"] else 0.0,
                ctx=tuple(base_ctx(following)),
                arm=arm,
            )
        )
    return out


def post_loss_requeue_latency(frame: PlayerFrame) -> list[Opportunity]:
    out = []
    for current, following in _transitions(frame):
        gap = max(following["started_at"] - current["ended_at"], 1)
        out.append(
            Opportunity(
                value=math.log(gap),
                ctx=tuple(base_ctx(current)),
                arm="loss" if not current["is_victory"] else "win",
            )
        )
    return out


def post_loss_session_continuation(frame: PlayerFrame) -> list[Opportunity]:
    """Does a loss make this player keep queueing, or stop for the day?"""

    out = []
    rows = frame.rows
    for start, end in frame.sessions():
        for index in range(start, end + 1):
            row = rows[index]
            continued = index < end
            if index == len(rows) - 1:
                # Right-censored: we cannot know whether they would have
                # continued after the last observed match.
                continue
            out.append(
                Opportunity(
                    value=1.0 if continued else 0.0,
                    ctx=tuple(base_ctx(row) + [("hour", str(_hour_of_day(row) // 4))]),
                    arm="loss" if not row["is_victory"] else "win",
                )
            )
    return out


def post_loss_hero_switch(frame: PlayerFrame) -> list[Opportunity]:
    out = []
    for current, following in _transitions(frame):
        out.append(
            Opportunity(
                value=0.0 if following["hero_id"] == current["hero_id"] else 1.0,
                ctx=tuple(base_ctx(current)),
                arm="loss" if not current["is_victory"] else "win",
            )
        )
    return out


def post_loss_mode_switch(frame: PlayerFrame) -> list[Opportunity]:
    out = []
    for current, following in _transitions(frame):
        out.append(
            Opportunity(
                value=0.0 if mode_stratum(following) == mode_stratum(current) else 1.0,
                ctx=tuple(base_ctx(current)),
                arm="loss" if not current["is_victory"] else "win",
            )
        )
    return out


def post_loss_risk_shift(frame: PlayerFrame) -> list[Opportunity]:
    out = []
    for current, following in _transitions(frame):
        out.append(
            Opportunity(
                value=per_ten_minutes(following["deaths"], following),
                ctx=tuple(base_ctx(following)),
                arm="loss" if not current["is_victory"] else "win",
            )
        )
    return out


def _session_halves(frame: PlayerFrame, minimum: int = 4) -> Iterator[tuple[str, dict[str, Any]]]:
    for start, end in frame.sessions():
        length = end - start + 1
        if length < minimum:
            continue
        half = length // 2
        for index in range(start, start + half):
            yield "early", frame.rows[index]
        for index in range(end - half + 1, end + 1):
            yield "late", frame.rows[index]


def session_drift_outcome(frame: PlayerFrame) -> list[Opportunity]:
    return [
        Opportunity(1.0 if row["is_victory"] else 0.0, tuple(base_ctx(row)), arm)
        for arm, row in _session_halves(frame)
    ]


def session_drift_activity(frame: PlayerFrame) -> list[Opportunity]:
    return [
        Opportunity(
            per_ten_minutes(row["kills"] + row["assists"], row), tuple(base_ctx(row)), arm
        )
        for arm, row in _session_halves(frame)
    ]


def session_drift_risk(frame: PlayerFrame) -> list[Opportunity]:
    return [
        Opportunity(per_ten_minutes(row["deaths"], row), tuple(base_ctx(row)), arm)
        for arm, row in _session_halves(frame)
    ]


def warmup_first_match(frame: PlayerFrame) -> list[Opportunity]:
    """Level shift at the first match of a session, not a within-session trend."""

    out = []
    for start, end in frame.sessions():
        if end - start + 1 < 3:
            continue
        for index in range(start, end + 1):
            row = frame.rows[index]
            out.append(
                Opportunity(
                    per_ten_minutes(row["kills"] + row["assists"], row),
                    tuple(base_ctx(row)),
                    "first" if index == start else "later",
                )
            )
    return out


def layoff_return(frame: PlayerFrame) -> list[Opportunity]:
    out = []
    rows = frame.rows
    for index, row in enumerate(rows):
        if index == 0:
            continue
        gap = row["started_at"] - rows[index - 1]["ended_at"]
        if gap <= SESSION_GAP_SECONDS:
            arm = "steady"
        elif gap >= LAYOFF_SECONDS:
            arm = "return"
        else:
            continue
        out.append(
            Opportunity(
                per_ten_minutes(row["kills"] + row["assists"], row), tuple(base_ctx(row)), arm
            )
        )
    return out


def requeue_tempo(frame: PlayerFrame) -> list[Opportunity]:
    """Level family: how fast this player re-queues inside a session."""

    out = []
    for current, following in _transitions(frame):
        gap = max(following["started_at"] - current["ended_at"], 1)
        out.append(
            Opportunity(
                math.log(gap),
                tuple(base_ctx(current) + [("hour", str(_hour_of_day(current) // 4))]),
            )
        )
    return out


def session_length(frame: PlayerFrame) -> list[Opportunity]:
    out = []
    for start, end in frame.sessions():
        row = frame.rows[start]
        out.append(
            Opportunity(
                math.log(end - start + 1),
                (
                    ("hour", str(_hour_of_day(row) // 4)),
                    ("weekday", "WE" if _weekday(row) >= 5 else "WD"),
                    ("mode", mode_stratum(row)),
                    ("patch", str(row.get("game_version_id"))),
                ),
            )
        )
    return out


def _own_late_window(frame: PlayerFrame) -> set[int] | None:
    """The four hours a player plays *least*, relative to their own clock.

    No timezone field exists in the corpus, so the reference is the player's
    own modal playing hour rather than any wall-clock notion of "late".
    """

    counts = [0] * 24
    for row in frame.rows:
        counts[_hour_of_day(row)] += 1
    if sum(counts) < 24:
        return None
    best_start, best_total = 0, None
    for start in range(24):
        total = sum(counts[(start + offset) % 24] for offset in range(4))
        if best_total is None or total > best_total:
            best_start, best_total = start, total
    # "off-peak" is the four-hour block diametrically opposite the peak block.
    off_start = (best_start + 12) % 24
    return {(off_start + offset) % 24 for offset in range(4)}


def offpeak_shift(frame: PlayerFrame) -> list[Opportunity]:
    window = _own_late_window(frame)
    if window is None:
        return []
    out = []
    for row in frame.rows:
        arm = "offpeak" if _hour_of_day(row) in window else "peak"
        out.append(
            Opportunity(
                per_ten_minutes(row["kills"] + row["assists"], row), tuple(base_ctx(row)), arm
            )
        )
    return out


def weekend_shift(frame: PlayerFrame) -> list[Opportunity]:
    return [
        Opportunity(
            per_ten_minutes(row["kills"] + row["assists"], row),
            tuple(base_ctx(row)),
            "weekend" if _weekday(row) >= 5 else "weekday",
        )
        for row in frame.rows
    ]


def hero_novelty(frame: PlayerFrame) -> list[Opportunity]:
    """Level family: appetite for heroes this player has not touched recently."""

    last_seen: dict[int, int] = {}
    out = []
    for index, row in enumerate(frame.rows):
        if index < 30:
            last_seen[row["hero_id"]] = row["started_at"]
            continue
        previous = last_seen.get(row["hero_id"])
        novel = previous is None or row["started_at"] - previous > NOVELTY_DAYS * 86400
        out.append(
            Opportunity(
                1.0 if novel else 0.0,
                (
                    ("mode", mode_stratum(row)),
                    ("patch", str(row.get("game_version_id"))),
                    ("lobby", str(row.get("lobby_type_native"))),
                ),
            )
        )
        last_seen[row["hero_id"]] = row["started_at"]
    return out


def _comfort_arms(frame: PlayerFrame, warmup: int = 50) -> Iterator[tuple[str, dict[str, Any]]]:
    """Causal comfort-pool membership: counted from strictly prior matches."""

    counts: dict[int, int] = {}
    for index, row in enumerate(frame.rows):
        if index >= warmup:
            ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            pool = {hero for hero, _ in ranked[:COMFORT_POOL_SIZE]}
            yield ("comfort" if row["hero_id"] in pool else "stretch"), row
        counts[row["hero_id"]] = counts.get(row["hero_id"], 0) + 1


def transfer_outcome(frame: PlayerFrame) -> list[Opportunity]:
    return [
        Opportunity(1.0 if row["is_victory"] else 0.0, tuple(base_ctx(row)), arm)
        for arm, row in _comfort_arms(frame)
    ]


def transfer_activity(frame: PlayerFrame) -> list[Opportunity]:
    return [
        Opportunity(
            per_ten_minutes(row["kills"] + row["assists"], row), tuple(base_ctx(row)), arm
        )
        for arm, row in _comfort_arms(frame)
    ]


def transfer_risk(frame: PlayerFrame) -> list[Opportunity]:
    return [
        Opportunity(per_ten_minutes(row["deaths"], row), tuple(base_ctx(row)), arm)
        for arm, row in _comfort_arms(frame)
    ]


def risk_appetite(frame: PlayerFrame) -> list[Opportunity]:
    return [
        Opportunity(per_ten_minutes(row["deaths"], row), tuple(base_ctx(row))) for row in frame.rows
    ]


def involvement_level(frame: PlayerFrame) -> list[Opportunity]:
    return [
        Opportunity(per_ten_minutes(row["kills"] + row["assists"], row), tuple(base_ctx(row)))
        for row in frame.rows
    ]


def side_sensitivity(frame: PlayerFrame) -> list[Opportunity]:
    """Declared negative control: side is randomised by the matchmaker."""

    return [
        Opportunity(
            1.0 if row["is_victory"] else 0.0,
            tuple(
                item for item in base_ctx(row) if item[0] != "side"
            ),
            "R" if row["is_radiant"] else "D",
        )
        for row in frame.rows
    ]


def duration_tempo(frame: PlayerFrame) -> list[Opportunity]:
    return [
        Opportunity(
            math.log(max(row["duration_seconds"], 1)),
            (
                ("mode", mode_stratum(row)),
                ("patch", str(row.get("game_version_id"))),
                ("hero", str(row.get("hero_id"))),
                ("lobby", str(row.get("lobby_type_native"))),
                ("result", "W" if row["is_victory"] else "L"),
            ),
        )
        for row in frame.rows
    ]


# ---------------------------------------------------------------------------
# parsed-dependent extractors
# ---------------------------------------------------------------------------


def _parsed_pairs(frame: PlayerFrame) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    """Yield (history_row, parsed_row) for product-context parsed matches.

    The parsed table carries no game mode, lobby, or leaver status, so mode
    context and product eligibility can only come from the history join. A
    parsed row with no product-context history row is dropped.
    """

    for row in frame.rows:
        parsed = frame.parsed.get(row["match_id"])
        if parsed is not None:
            yield row, parsed


def _event_progress(parsed: dict[str, Any], row: dict[str, Any]) -> list[float]:
    """Own fight-participation timings on normalised game progress.

    ``assist_events`` contributes **timing shape only**; this list is never
    used as a count that must reconcile with the history table.
    """

    stats = parsed.get("stats") or {}
    times = [event["time"] for event in (stats.get("kill_events") or [])]
    times += [event["time"] for event in (stats.get("assist_events") or [])]
    return sorted(progress(time, row) for time in times if time is not None)


def fight_timing_centroid(frame: PlayerFrame) -> list[Opportunity]:
    out = []
    for row, parsed in _parsed_pairs(frame):
        points = _event_progress(parsed, row)
        if len(points) < 3:
            continue
        out.append(
            Opportunity(
                sum(points) / len(points), tuple(base_ctx(row) + role_ctx(parsed))
            )
        )
    return out


def first_fight_timing(frame: PlayerFrame) -> list[Opportunity]:
    out = []
    for row, parsed in _parsed_pairs(frame):
        points = _event_progress(parsed, row)
        if not points:
            continue
        out.append(Opportunity(points[0], tuple(base_ctx(row) + role_ctx(parsed))))
    return out


def _state_minutes(row: dict[str, Any], parsed: dict[str, Any]) -> tuple[list[int], list[int]]:
    """Minute indices where the player's own team was clearly behind / ahead."""

    lead = player_networth_lead(parsed)
    if not lead:
        return [], []
    behind = [index for index, value in enumerate(lead) if value <= -STATE_LEAD_GOLD]
    ahead = [index for index, value in enumerate(lead) if value >= STATE_LEAD_GOLD]
    return behind, ahead


def state_responsive_participation(frame: PlayerFrame) -> list[Opportunity]:
    """Own fight participation while behind versus while ahead.

    The rate denominator is minutes spent in that state, so the contrast is not
    a function of how long the game or the state lasted.
    """

    out = []
    for row, parsed in _parsed_pairs(frame):
        behind, ahead = _state_minutes(row, parsed)
        if len(behind) < 3 or len(ahead) < 3:
            continue
        stats = parsed.get("stats") or {}
        times = [event["time"] for event in (stats.get("kill_events") or [])]
        times += [event["time"] for event in (stats.get("assist_events") or [])]
        minutes = [int(time // 60) for time in times if time is not None and time >= 0]
        behind_set, ahead_set = set(behind), set(ahead)
        behind_events = sum(1 for minute in minutes if minute in behind_set)
        ahead_events = sum(1 for minute in minutes if minute in ahead_set)
        ctx = tuple(base_ctx(row) + role_ctx(parsed))
        out.append(Opportunity(behind_events / len(behind), ctx, "behind"))
        out.append(Opportunity(ahead_events / len(ahead), ctx, "ahead"))
    return out


def state_responsive_purchasing(frame: PlayerFrame) -> list[Opportunity]:
    """Purchase rate while behind versus while ahead — build tempo, not identity.

    Item identity is *not* used: the corpus has raw item ids whose tiering is
    unverified, so only the timing of a purchase event is read.
    """

    out = []
    for row, parsed in _parsed_pairs(frame):
        behind, ahead = _state_minutes(row, parsed)
        if len(behind) < 3 or len(ahead) < 3:
            continue
        stats = parsed.get("stats") or {}
        minutes = [
            int(event["time"] // 60)
            for event in (stats.get("item_purchases") or [])
            if event.get("time") is not None and event["time"] >= 0
        ]
        behind_set, ahead_set = set(behind), set(ahead)
        ctx = tuple(base_ctx(row) + role_ctx(parsed))
        out.append(
            Opportunity(sum(1 for m in minutes if m in behind_set) / len(behind), ctx, "behind")
        )
        out.append(
            Opportunity(sum(1 for m in minutes if m in ahead_set) / len(ahead), ctx, "ahead")
        )
    return out


def kill_share(frame: PlayerFrame) -> list[Opportunity]:
    """Own kill events as a share of the team's kills.

    Counts come from ``kill_events`` only. ``assist_events`` is excluded here
    on purpose: its count disagrees with the history table in 48% of rows, so
    it may not enter a count-based estimand.
    """

    out = []
    for row, parsed in _parsed_pairs(frame):
        trajectories = team_kill_trajectories(parsed)
        if trajectories is None:
            continue
        own_team = sum(trajectories[0])
        if own_team < 8:
            continue
        stats = parsed.get("stats") or {}
        own = len(stats.get("kill_events") or [])
        out.append(
            Opportunity(own / own_team, tuple(base_ctx(row) + role_ctx(parsed)))
        )
    return out


def purchase_tempo(frame: PlayerFrame) -> list[Opportunity]:
    """Normalised game progress at the Nth item purchase."""

    out = []
    for row, parsed in _parsed_pairs(frame):
        stats = parsed.get("stats") or {}
        times = sorted(
            event["time"]
            for event in (stats.get("item_purchases") or [])
            if event.get("time") is not None
        )
        if len(times) < PURCHASE_LANDMARK:
            continue
        out.append(
            Opportunity(
                progress(times[PURCHASE_LANDMARK - 1], row),
                tuple(base_ctx(row) + role_ctx(parsed)),
            )
        )
    return out


_LANE_FIELD = {
    ("SAFE_LANE", True): "bottom_lane_outcome_native",
    ("OFF_LANE", True): "top_lane_outcome_native",
    ("SAFE_LANE", False): "top_lane_outcome_native",
    ("OFF_LANE", False): "bottom_lane_outcome_native",
    ("MID_LANE", True): "mid_lane_outcome_native",
    ("MID_LANE", False): "mid_lane_outcome_native",
}


def own_lane_result(parsed: dict[str, Any]) -> str | None:
    """Map the team-level lane outcome onto the sampled player's own lane.

    Radiant safe lane is bottom and Radiant off lane is top; the sides swap for
    Dire. The outcome is a *team-level* lane verdict, not a player verdict, and
    every consumer must say so.
    """

    key = (parsed.get("lane_native"), parsed.get("is_radiant"))
    field_name = _LANE_FIELD.get(key)  # type: ignore[arg-type]
    if field_name is None:
        return None
    outcome = parsed.get(field_name)
    if outcome is None or outcome == "TIE":
        return None
    winner_is_radiant = outcome.startswith("RADIANT")
    return "won" if winner_is_radiant == bool(parsed["is_radiant"]) else "lost"


def lane_recovery_participation(frame: PlayerFrame) -> list[Opportunity]:
    """After a lost lane, does own late-game participation hold up?"""

    out = []
    for row, parsed in _parsed_pairs(frame):
        result = own_lane_result(parsed)
        if result is None:
            continue
        points = _event_progress(parsed, row)
        late = sum(1 for point in points if point >= 0.5)
        out.append(
            Opportunity(
                per_ten_minutes(late, row) * 2.0,
                tuple(base_ctx(row) + role_ctx(parsed)),
                result,
            )
        )
    return out


def lane_recovery_outcome(frame: PlayerFrame) -> list[Opportunity]:
    out = []
    for row, parsed in _parsed_pairs(frame):
        result = own_lane_result(parsed)
        if result is None:
            continue
        out.append(
            Opportunity(
                1.0 if row["is_victory"] else 0.0,
                tuple(base_ctx(row) + role_ctx(parsed)),
                result,
            )
        )
    return out


def lead_retention(frame: PlayerFrame) -> list[Opportunity]:
    """Given a decided mid-game state, does the game convert?

    Explicitly team-level: four teammates share the trajectory, so player
    attribution is weak by construction and the screen is expected to show it.
    """

    out = []
    for row, parsed in _parsed_pairs(frame):
        lead = player_networth_lead(parsed)
        length = minute_grid_length(parsed)
        if not lead or length < 8:
            continue
        midpoint = lead[length // 2]
        if abs(midpoint) < STATE_LEAD_GOLD:
            continue
        arm = "ahead" if midpoint > 0 else "behind"
        out.append(
            Opportunity(
                1.0 if row["is_victory"] else 0.0,
                tuple(base_ctx(row) + role_ctx(parsed)),
                arm,
            )
        )
    return out


def comeback_participation(frame: PlayerFrame) -> list[Opportunity]:
    """Share of own fight events that land while the team is behind."""

    out = []
    for row, parsed in _parsed_pairs(frame):
        lead = player_networth_lead(parsed)
        if not lead or len(lead) < 8:
            continue
        stats = parsed.get("stats") or {}
        times = [event["time"] for event in (stats.get("kill_events") or [])]
        times += [event["time"] for event in (stats.get("assist_events") or [])]
        minutes = [int(time // 60) for time in times if time is not None and time >= 0]
        if len(minutes) < 4:
            continue
        behind_minutes = {index for index, value in enumerate(lead) if value < 0}
        if not behind_minutes or len(behind_minutes) == len(lead):
            continue
        share = sum(1 for minute in minutes if minute in behind_minutes) / len(minutes)
        exposure = len(behind_minutes) / len(lead)
        out.append(
            Opportunity(share - exposure, tuple(base_ctx(row) + role_ctx(parsed)))
        )
    return out


def early_fight_rate(frame: PlayerFrame) -> list[Opportunity]:
    """Fight events in the first 25% of game progress, per minute of that span."""

    out = []
    for row, parsed in _parsed_pairs(frame):
        points = _event_progress(parsed, row)
        span_minutes = max(row["duration_seconds"] * 0.25 / 60.0, 1.0)
        early = sum(1 for point in points if point <= 0.25)
        out.append(
            Opportunity(early / span_minutes, tuple(base_ctx(row) + role_ctx(parsed)))
        )
    return out


def position_flexibility(frame: PlayerFrame) -> list[Opportunity]:
    """Does this player change position from one match to the next?

    Position is parsed-linked, so this conditions on parsed availability and
    additionally on two *consecutive* parsed matches.
    """

    out = []
    rows = [(row, frame.parsed[row["match_id"]]) for row in frame.rows if row["match_id"] in frame.parsed]
    for index in range(1, len(rows)):
        previous_row, previous = rows[index - 1]
        row, parsed = rows[index]
        if row["started_at"] - previous_row["ended_at"] > SESSION_GAP_SECONDS:
            continue
        if not previous.get("position_native") or not parsed.get("position_native"):
            continue
        out.append(
            Opportunity(
                0.0 if parsed["position_native"] == previous["position_native"] else 1.0,
                tuple(base_ctx(row) + [("prev_position", str(previous["position_native"]))]),
            )
        )
    return out


def state_responsive_participation_minutes(frame: PlayerFrame) -> list[Opportunity]:
    """Minute-level variant of ``state_responsive_participation``.

    The per-match-ratio form makes each player's arm mean an average of noisy
    small-denominator ratios. Emitting one opportunity per *state minute*
    instead makes the player's arm mean a ratio of sums and puts the sampling
    model on the minute, which is where the events actually occur. This is a
    recorded estimator variant of the same family, not a new behavioural idea.
    """

    out = []
    for row, parsed in _parsed_pairs(frame):
        behind, ahead = _state_minutes(row, parsed)
        if len(behind) < 3 or len(ahead) < 3:
            continue
        stats = parsed.get("stats") or {}
        times = [event["time"] for event in (stats.get("kill_events") or [])]
        times += [event["time"] for event in (stats.get("assist_events") or [])]
        per_minute: dict[int, int] = {}
        for time in times:
            if time is not None and time >= 0:
                minute = int(time // 60)
                per_minute[minute] = per_minute.get(minute, 0) + 1
        ctx = tuple(base_ctx(row) + role_ctx(parsed))
        for minute in behind:
            out.append(Opportunity(float(per_minute.get(minute, 0)), ctx, "behind"))
        for minute in ahead:
            out.append(Opportunity(float(per_minute.get(minute, 0)), ctx, "ahead"))
    return out


EXTRACTORS: dict[str, Callable[[PlayerFrame], list[Opportunity]]] = {
    "post_loss_next_outcome": post_loss_next_outcome,
    "post_loss_requeue_latency": post_loss_requeue_latency,
    "post_loss_session_continuation": post_loss_session_continuation,
    "post_loss_hero_switch": post_loss_hero_switch,
    "post_loss_mode_switch": post_loss_mode_switch,
    "post_loss_risk_shift": post_loss_risk_shift,
    "session_drift_outcome": session_drift_outcome,
    "session_drift_activity": session_drift_activity,
    "session_drift_risk": session_drift_risk,
    "warmup_first_match": warmup_first_match,
    "layoff_return": layoff_return,
    "requeue_tempo": requeue_tempo,
    "session_length": session_length,
    "offpeak_shift": offpeak_shift,
    "weekend_shift": weekend_shift,
    "hero_novelty": hero_novelty,
    "transfer_outcome": transfer_outcome,
    "transfer_activity": transfer_activity,
    "transfer_risk": transfer_risk,
    "risk_appetite": risk_appetite,
    "involvement_level": involvement_level,
    "side_sensitivity": side_sensitivity,
    "duration_tempo": duration_tempo,
    "fight_timing_centroid": fight_timing_centroid,
    "first_fight_timing": first_fight_timing,
    "state_responsive_participation": state_responsive_participation,
    "state_responsive_participation_minutes": state_responsive_participation_minutes,
    "state_responsive_purchasing": state_responsive_purchasing,
    "kill_share": kill_share,
    "purchase_tempo": purchase_tempo,
    "lane_recovery_participation": lane_recovery_participation,
    "lane_recovery_outcome": lane_recovery_outcome,
    "lead_retention": lead_retention,
    "comeback_participation": comeback_participation,
    "early_fight_rate": early_fight_rate,
    "position_flexibility": position_flexibility,
}


def extract(name: str, frame: PlayerFrame) -> list[Opportunity]:
    try:
        extractor = EXTRACTORS[name]
    except KeyError as error:  # pragma: no cover - guarded by the registry
        raise KeyError(f"unknown candidate family: {name}") from error
    return extractor(frame)


__all__ = [
    "COMFORT_POOL_SIZE",
    "EXTRACTORS",
    "FEATURE_VERSION",
    "LAYOFF_SECONDS",
    "NOVELTY_DAYS",
    "PURCHASE_LANDMARK",
    "STATE_LEAD_GOLD",
    "Opportunity",
    "PlayerFrame",
    "base_ctx",
    "duration_bucket",
    "extract",
    "load_frames",
    "own_lane_result",
    "per_ten_minutes",
    "progress",
    "role_ctx",
]

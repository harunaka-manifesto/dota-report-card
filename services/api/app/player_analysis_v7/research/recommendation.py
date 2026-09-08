"""Section 5: the single improvement, chosen from the player's own gap.

Implements `docs/evidence/v7-improvement-recommendation-model-2026-09-05.md`.

The Finding ranking answers *what is most distinctively you*. This answers a
different question, and reusing the ranking for it would be wrong: the most
distinctive thing about a player is often the thing they should keep doing.

For player `p` and dimension `d`, over the player's own matches split into
their wins and their losses:

    gap   = E[d | loss] - E[d | win]        context-adjusted, per player
    g     = gap / tau_d                     population spread sets the scale
    prio  = |g| * r_d * A_d                 reliability- and actionability-weighted

`tau_d` sets the *scale* only. The player is compared to themselves, never to
the population — constraint 3 of the model.

Two design-time properties live in the registry and are not negotiable at
ranking time:

* `upstream` — whether the dimension is a behaviour the player emits rather
  than a result they receive. "You lose when you die more" is circular.
* `actionability` — a fixed weight in [0, 1], assigned by design and never
  fitted to data.

Read-only. No provider call.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.player_analysis_v7.research import inference
from app.player_analysis_v7.research import pass2_tables as pt
from app.player_analysis_v7.research import tables as pass1_tables
from app.player_analysis_v7.research.features import Opportunity
from app.player_analysis_v7.research.pass2_features import (
    DEATH_CLUSTER_WINDOW_SECONDS,
    _first_real_item_purchase_time,
    _item_vocabulary,
    _match_vision_coverage,
    _next_kill_or_assist_time,
    _observer_ward_events,
)
from app.player_analysis_v7.research.pass2_observations import _enemy_tower_fell_soon_after
from app.player_analysis_v7.research.screen import encode, fit_context_projection

Row = dict[str, Any]

RECOMMENDATION_VERSION = "v7-improvement-recommendation-1.0.0"

ARM_WIN = "win"
ARM_LOSS = "loss"

#: Share of players who may share the sign of a gap before the dimension is
#: judged to be tracking the match outcome rather than the player. Fixed
#: before the shares were measured; see OUTCOME_CONTAMINATED_EXCLUSIONS.
MODAL_SIGN_SHARE_LIMIT = 0.95

#: Minute the laning dimension is cumulated to.
LANING_MINUTE = 10

#: Constraint 2 of the model: no recommendation without a denominator. A
#: player needs this many matches on *each* side of their own win/loss split
#: before a gap on that dimension is offered at all. The model defers the
#: final number to calibration; this is the working minimum, and it is stated
#: rather than hidden inside the inference layer's block geometry.
MIN_PER_ARM = 15


def _self(row: Row) -> Mapping[str, Any] | None:
    self_ = row.get("self")
    return self_ if isinstance(self_, Mapping) else None


def outcome_arm(row: Row) -> str | None:
    self_ = _self(row)
    if self_ is None:
        return None
    is_victory = self_.get("is_victory")
    if is_victory is None:
        return None
    return ARM_WIN if is_victory else ARM_LOSS


def recommendation_ctx(row: Row) -> tuple[tuple[str, str], ...]:
    """Context factors for a win/loss gap.

    Deliberately **not** ``pass2_observations.pass2_ctx``. The model names the
    controls: hero, position, role, lane, patch and game mode. Duration and
    side are absent on purpose — duration is downstream of the outcome (a
    stomped loss is short), so controlling for it would absorb the very gap
    being measured rather than a confounder of it.
    """

    self_ = _self(row) or {}
    return (
        ("mode", pass1_tables.mode_stratum(row)),
        ("patch", str(row.get("game_version_id"))),
        ("hero", str(self_.get("hero_id"))),
        ("position", str(self_.get("position_native"))),
        ("role", str(self_.get("role_native"))),
        ("lane", str(self_.get("lane_native"))),
    )


# ---------------------------------------------------------------------------
# Per-match measurements
# ---------------------------------------------------------------------------


def last_hits_at_ten(row: Row) -> float | None:
    """Cumulative last hits through minute ``LANING_MINUTE``.

    ``last_hits_per_minute`` is a per-minute *increment* (Pass-2 semantics
    rule 2), so this sums rather than indexes.
    """

    series = pt.trajectory(row, "last_hits_per_minute")
    if series is None or len(series) <= LANING_MINUTE:
        return None
    window = series[: LANING_MINUTE + 1]
    if any(value is None for value in window):
        return None
    return float(sum(value for value in window if value is not None))


def deaths_alone_share(row: Row) -> float | None:
    return pt.deaths_alone_share(row)


def first_real_item_time(row: Row) -> float | None:
    time = _first_real_item_purchase_time(row, _item_vocabulary())
    return float(time) if time is not None else None


def first_ward_time(row: Row) -> float | None:
    wards = _observer_ward_events(row)
    times = [ward["time"] for ward in wards if ward.get("time") is not None]
    return float(min(times)) if times else None


def lane_vs_jungle_share(row: Row) -> float | None:
    split = pt.lane_vs_jungle_gold(row)
    if split is None:
        return None
    lane_gold, jungle_gold = split
    total = lane_gold + jungle_gold
    if total <= 0:
        return None
    return jungle_gold / total


def death_clustering(row: Row) -> float | None:
    self_ = _self(row)
    if self_ is None:
        return None
    events = self_.get("events")
    death_events = events.get("death_events") if isinstance(events, Mapping) else None
    if not death_events:
        return None
    times = sorted(event["time"] for event in death_events if event.get("time") is not None)
    if len(times) < 2:
        return None
    gaps = list(zip(times, times[1:], strict=False))
    clustered = sum(
        1 for previous, current in gaps if current - previous <= DEATH_CLUSTER_WINDOW_SECONDS
    )
    return clustered / len(gaps)


def vision_coverage(row: Row) -> float | None:
    return _match_vision_coverage(row, _observer_ward_events(row))


def spike_usage(row: Row) -> float | None:
    purchase_time = _first_real_item_purchase_time(row, _item_vocabulary())
    if purchase_time is None:
        return None
    next_event_time = _next_kill_or_assist_time(row, purchase_time)
    if next_event_time is None:
        return None
    return float(next_event_time - purchase_time)


def fight_conversion(row: Row) -> float | None:
    self_ = _self(row)
    if self_ is None:
        return None
    is_radiant = self_.get("is_radiant")
    if is_radiant is None:
        return None
    adapter = {
        "radiant_kills": row.get("radiant_kills"),
        "dire_kills": row.get("dire_kills"),
        "radiant_networth_leads": row.get("radiant_networth_leads"),
        "duration_seconds": row.get("duration_seconds"),
        "is_radiant": is_radiant,
    }
    pair = pass1_tables.team_kill_trajectories(adapter)
    if pair is None:
        return None
    own_kills, enemy_kills = pair
    converted = total = 0
    for minute in range(len(own_kills)):
        own = own_kills[minute] or 0
        enemy = enemy_kills[minute] if minute < len(enemy_kills) else 0
        if own < pt.FIGHT_KILL_THRESHOLD or (enemy or 0) != 0:
            continue
        total += 1
        if _enemy_tower_fell_soon_after(row, is_radiant, minute):
            converted += 1
    return converted / total if total else None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecommendationDimension:
    """One candidate improvement.

    ``recommendation`` is imperative and doable in the next game.
    ``verification`` names the exact measurement that will confirm or refute
    it, from fields already collected — that field is what separates this from
    advice.
    """

    key: str
    fn: Callable[[Row], float | None]
    actionability: float
    upstream: bool
    outcome_contaminated: bool
    higher_is_worse: bool
    recommendation: str
    verification: str
    upstream_rationale: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.actionability <= 1.0:
            raise ValueError(f"{self.key}: actionability must lie in [0, 1]")


RECOMMENDATION_REGISTRY: dict[str, RecommendationDimension] = {
    dimension.key: dimension
    for dimension in (
        RecommendationDimension(
            "last_hits_at_ten",
            last_hits_at_ten,
            actionability=0.95,
            upstream=True,
            outcome_contaminated=False,
            higher_is_worse=False,
            recommendation="For five games, care about nothing but last hits until minute 10.",
            verification="last_hits_per_minute cumulated to minute 10",
            upstream_rationale="Pure execution inside the player's own lane.",
        ),
        RecommendationDimension(
            "deaths_alone_share",
            deaths_alone_share,
            actionability=0.90,
            upstream=True,
            outcome_contaminated=False,
            higher_is_worse=True,
            recommendation="Do not cross the river without a teammate on screen.",
            verification="share of your death minutes with no team kill activity",
            upstream_rationale="Describes how the player moves, not what the scoreboard did.",
        ),
        RecommendationDimension(
            "first_real_item_time",
            first_real_item_time,
            actionability=0.85,
            upstream=True,
            outcome_contaminated=False,
            higher_is_worse=True,
            recommendation="Buy your first big item before your damage item.",
            verification="time of your first real-item purchase",
            upstream_rationale="A purchase is an action the player takes alone.",
        ),
        RecommendationDimension(
            "first_ward_time",
            first_ward_time,
            actionability=0.80,
            upstream=True,
            outcome_contaminated=False,
            higher_is_worse=True,
            recommendation="Place your first ward before the horn.",
            verification="time of your first observer ward placement",
            upstream_rationale="A ward placement is an action the player takes alone.",
        ),
        RecommendationDimension(
            "lane_vs_jungle_share",
            lane_vs_jungle_share,
            actionability=0.75,
            upstream=True,
            outcome_contaminated=False,
            higher_is_worse=True,
            recommendation="Take the lane creeps when they are there.",
            verification="share of your creep gold taken from neutrals",
            upstream_rationale="Where the player chooses to farm.",
        ),
        RecommendationDimension(
            "death_clustering",
            death_clustering,
            actionability=0.70,
            upstream=True,
            outcome_contaminated=True,
            higher_is_worse=True,
            recommendation="After you die, take the long way back.",
            verification="share of your death-to-death gaps at or under 90 seconds",
            upstream_rationale="Describes what the player does on respawn.",
        ),
        RecommendationDimension(
            "vision_coverage",
            vision_coverage,
            actionability=0.60,
            upstream=True,
            outcome_contaminated=False,
            higher_is_worse=False,
            recommendation="Replace your ward the moment the old one expires.",
            verification="share of minutes with one of your observer wards alive",
            upstream_rationale="Ward uptime is a purchasing and placement habit.",
        ),
        RecommendationDimension(
            "fight_conversion",
            fight_conversion,
            actionability=0.50,
            upstream=True,
            outcome_contaminated=True,
            higher_is_worse=False,
            recommendation="When you win a fight, go to the tower.",
            verification="rate a won fight minute is followed by an enemy tower falling",
            upstream_rationale=(
                "The measurement records a team result, but the behaviour behind it is the "
                "player's own decision after a won fight: go to the tower, or go back to the "
                "jungle. Weighted low because the result is not theirs alone."
            ),
        ),
        RecommendationDimension(
            "spike_usage",
            spike_usage,
            actionability=0.45,
            upstream=True,
            outcome_contaminated=False,
            higher_is_worse=True,
            recommendation="When your item finishes, go and use it.",
            verification="seconds from your first real item to your next kill or assist",
            upstream_rationale=(
                "Same judgement as fight_conversion, and weighted lower for the same reason: "
                "whether a kill follows is not the player's alone, but seeking the fight once "
                "the item lands is."
            ),
        ),
    )
}

#: A second exclusion, distinct from the upstream rule and discovered by
#: running the selection. The upstream rule (model section 3) asks whether a
#: dimension is a behaviour the player emits. The *gap* estimand adds a
#: requirement the level estimand does not have: the measurement must not be
#: tracking the match result.
#:
#: The screen is measured, not judged. **A personal gap should vary in sign
#: across people**: some players ward later in their losses, some earlier. A
#: gap that runs the same way for essentially everybody is not describing the
#: player, it is restating the outcome. The cut is a modal-sign share of
#: ``MODAL_SIGN_SHARE_LIMIT``, fixed before the shares were computed.
#:
#: Measured over 250-265 DISCOVERY players per dimension:
#:
#: ===========================  =================  ==============
#: dimension                    modal-sign share   verdict
#: ===========================  =================  ==============
#: fight_conversion             1.0000             contaminated
#: death_clustering             0.9886             contaminated
#: last_hits_at_ten             0.9466             eligible
#: spike_usage                  0.8415             eligible
#: lane_vs_jungle_share         0.6868             eligible
#: first_real_item_time         0.6566             eligible
#: deaths_alone_share           0.6340             eligible
#: first_ward_time              0.5800             eligible
#: vision_coverage              0.5321             eligible
#: ===========================  =================  ==============
#:
#: ``fight_conversion`` is the clearest case: it runs the same way for all 262
#: players, without exception. It passes the upstream rule -- going to the
#: tower after a won fight is the player's own decision, which is why it
#: remains a legitimate Finding -- and fails this one, because measured across
#: a whole match "you converted fights into towers less" in a game you lost is
#: close to restating that you lost. Before this screen existed it won 168 of
#: 265 single slots on the second-lowest actionability weight in the table.
#:
#: The screen also overturned a hand-classification: ``spike_usage`` was
#: excluded by the same verbal argument as ``fight_conversion`` and the
#: measurement does not support that -- 42 of 265 players show the opposite
#: sign, so it is describing players, not results. The judgement was wrong and
#: the measurement is what settles it.
#:
#: ``last_hits_at_ten`` sits just under the line at 0.9466 and is kept. It is
#: also the one dimension structurally protected from this failure mode, being
#: measured entirely in a window that closes at minute 10, before most games
#: are decided.
OUTCOME_CONTAMINATED_EXCLUSIONS: dict[str, str] = {
    "fight_conversion": "gap runs the same way for all 262 players (modal-sign share 1.0000)",
    "death_clustering": (
        "gap runs the same way for 260 of 263 players (modal-sign share 0.9886)"
    ),
}

#: Dimensions deliberately excluded by the upstream rule (model section 3).
#: Recorded rather than omitted so the exclusion is reviewable.
DOWNSTREAM_EXCLUSIONS: dict[str, str] = {
    "lane_to_map": "net worth at minute 20 is a scoreboard reading, not a behaviour",
    "closer_vs_comeback": "win rate given a lead is the result itself; recommending it is circular",
    "lead_retention": "whether a lead survives is a team outcome the player receives",
}


def modal_sign_share(gaps: Sequence[float]) -> float:
    """Share of players whose gap carries the more common sign.

    0.5 means the dimension splits the population; 1.0 means it runs the same
    way for everyone, which is the outcome-tracking signature. Exact zeros
    count toward neither sign.
    """

    if not gaps:
        return float("nan")
    positive = sum(1 for gap in gaps if gap > 0)
    negative = sum(1 for gap in gaps if gap < 0)
    return max(positive, negative) / len(gaps)


def eligible_dimensions() -> dict[str, RecommendationDimension]:
    """The dimensions a recommendation may be drawn from.

    Both exclusion rules are applied here, once, rather than at ranking time:
    the model is explicit that eligibility is a design-time property and "not
    negotiable at ranking time".
    """

    return {
        key: dimension
        for key, dimension in RECOMMENDATION_REGISTRY.items()
        if dimension.upstream and not dimension.outcome_contaminated
    }


def opportunities(rows: Sequence[Row], dimension: RecommendationDimension) -> list[Opportunity]:
    """One win/loss-armed observation per match the dimension can measure."""

    out: list[Opportunity] = []
    for row in rows:
        arm = outcome_arm(row)
        if arm is None:
            continue
        value = dimension.fn(row)
        if value is None:
            continue
        out.append(Opportunity(float(value), recommendation_ctx(row), arm))
    return out


def build_personal_contrast_matrix(
    per_player: Sequence[tuple[str, Sequence[Opportunity]]],
) -> inference.FamilyMatrix:
    """A win/loss contrast matrix that does **not** project the arm out.

    ``inference.build_matrix(arm_family=True)`` encodes the arm as an ordinary
    context factor, so the projection removes the *population-wide* win/loss
    effect and every player's estimate becomes a deviation from how the
    average player differs between wins and losses. That is exactly right for
    a Finding — a shared population response is not personal identity — and
    exactly wrong here.

    Section 5 asks whether *this player's own* behaviour differs between their
    wins and their losses. Removing the population's win/loss effect first
    would answer "is your gap unusual", which constraint 3 of the model
    forbids in as many words: never present a population comparison as a
    personal gap. Measured on the real corpus, the difference is not
    academic — projecting the arm out drives ``tau`` to exactly zero on every
    dimension, because once the average gap is removed players do not reliably
    differ in what is left.

    Context is still projected out (hero, position, role, lane, patch, mode),
    so "you lose more on harder heroes" still cannot present itself as a
    behavioural gap.
    """

    encoded = encode(per_player, include_arm_as_factor=False)
    context_fit = fit_context_projection(encoded)
    residual = list(context_fit.residual)
    order: dict[str, list[int]] = {}
    for index, pid in enumerate(encoded.player):
        order.setdefault(encoded.player_names[pid], []).append(index)
    return inference.FamilyMatrix(
        encoded=encoded,
        context_fit=context_fit,
        residual=residual,
        projection_drift=context_fit.drift,
        arm_family=True,
        treated_code=encoded.arm_names.index(ARM_LOSS) if ARM_LOSS in encoded.arm_names else None,
        control_code=encoded.arm_names.index(ARM_WIN) if ARM_WIN in encoded.arm_names else None,
        order=order,
    )


def has_denominator(series: Sequence[Opportunity]) -> bool:
    """Constraint 2: enough matches on *each* side of the player's own split."""

    wins = sum(1 for o in series if o.arm == ARM_WIN)
    losses = sum(1 for o in series if o.arm == ARM_LOSS)
    return wins >= MIN_PER_ARM and losses >= MIN_PER_ARM


# ---------------------------------------------------------------------------
# Priority and selection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoredRecommendation:
    key: str
    gap: float
    standard_error: float
    standardized_gap: float
    reliability: float
    actionability: float
    priority: float
    direction: str
    wins: int
    losses: int
    recommendation: str
    verification: str


def dimension_scale(matrix: inference.FamilyMatrix) -> float:
    """The dimension's own match-to-match spread, in its own units.

    This is the denominator the standardized gap uses, and it is deliberately
    **not** the between-player spread of gaps that the model as first written
    called ``tau_d``.

    Measured on the real corpus, ``tau_d`` is exactly zero on every dimension:
    for last hits at minute 10, the between-player variance of the gap is 3.19
    against a dependence-inflated measurement variance of 5.55, so the spread
    of gaps is not measurable at all. The gaps themselves are not in doubt --
    the median player takes 2.4 fewer last hits by minute 10 in their losses,
    and 95% of players have a negative gap. What is unmeasurable is how much
    players *differ* in it.

    Dividing by ``tau_d`` would therefore have silenced section 5 entirely,
    and silenced it for the wrong reason: it asks "is your gap unusual", which
    constraint 3 forbids in as many words, and which is the same mistake the
    Finding model was already corrected for. If every player's last hits drop
    in their losses, each player should still be told that theirs do.

    The pooled residual spread is a *unit* conversion, identical for every
    player, so it makes a 2.4-last-hit gap and a 0.06-share gap comparable
    without ever ranking one player against another.
    """

    values = matrix.residual
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return variance**0.5


def standardized_gap(gap: float, scale: float) -> float:
    """``gap / scale`` -- the player's own gap in units of ordinary variation."""

    if scale <= 0.0 or scale != scale:
        return 0.0
    return gap / scale


def gap_reliability(se: float, scale: float, dependence_inflation: float) -> float:
    """How much of the measured gap is signal, on the dimension's own scale.

    Same functional form as the Finding reliability -- ``s^2 / (s^2 + SE^2 D)``
    -- with the between-player spread replaced by the dimension scale, and the
    same dependence inflation, so a noisy gap still cannot be promoted to
    advice (constraint 1).
    """

    if scale <= 0.0 or scale != scale:
        return 0.0
    noise = se * se * dependence_inflation
    if noise != noise or noise < 0.0:
        return 0.0
    denominator = scale * scale + noise
    if denominator <= 0.0:
        return 0.0
    return (scale * scale) / denominator


def priority(standardized: float, reliability: float, actionability: float) -> float:
    return abs(standardized) * reliability * actionability


def select(
    scored: Sequence[ScoredRecommendation],
) -> tuple[ScoredRecommendation | None, list[ScoredRecommendation]]:
    """The single recommendation, plus two runners-up retained for the paid tier.

    Ties break toward the higher actionability weight, then the larger sample,
    then the key — fully deterministic, never dependent on input order.
    """

    ordered = sorted(
        scored,
        key=lambda s: (-s.priority, -s.actionability, -(s.wins + s.losses), s.key),
    )
    if not ordered:
        return None, []
    return ordered[0], list(ordered[1:3])


__all__ = [
    "ARM_LOSS",
    "ARM_WIN",
    "DOWNSTREAM_EXCLUSIONS",
    "OUTCOME_CONTAMINATED_EXCLUSIONS",
    "MIN_PER_ARM",
    "MODAL_SIGN_SHARE_LIMIT",
    "RECOMMENDATION_REGISTRY",
    "RECOMMENDATION_VERSION",
    "RecommendationDimension",
    "ScoredRecommendation",
    "build_personal_contrast_matrix",
    "dimension_scale",
    "eligible_dimensions",
    "gap_reliability",
    "has_denominator",
    "modal_sign_share",
    "opportunities",
    "outcome_arm",
    "priority",
    "recommendation_ctx",
    "select",
    "standardized_gap",
]

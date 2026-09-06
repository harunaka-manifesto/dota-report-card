"""Section 6 axes: tempo, fight style, and the session modifier.

The narrative document is explicit that this section is "for fun, not for
science" — but every axis is still computed from data, and the grid it lands
on is fixed by the report contract: ``3 x 3 x 2 = 18`` combinations plus two
rare specials.

The three axes are deliberately *not* Findings. A Finding is ranked against
the population spread and carries a reliability; an archetype is a label. The
axes here are plain per-player descriptive statistics cut at population
quantiles, and nothing in this module feeds the ranking model. Keeping them
separate is what stops a label from acquiring the authority of a measurement.

Two axes need per-event Pass-2 data (kill, assist and death times against the
match's fight minutes); the modifier needs the full Pass-1 session history.
A player therefore needs both corpora to receive an archetype, which in
research means the Pass-2 subset and in production means the report fetches
parsed matches for the one player it is about.

**Every axis is measured and cut within one game-mode stratum.** Turbo is 63%
of the Pass-2 corpus and its games are structurally shorter and bloodier, so a
mode-blind axis measures mode composition instead of the player: a fixed
15-minute "early impact" share correlates 0.89 with how much turbo a player
queues, and even the duration-normalised centroid moves substantially (0.52
between the all-matches and non-turbo versions). Fight participation is 0.59
correlated with turbo share on its own. A player is therefore assigned to the
stratum they mostly play and labelled against the other players in it — "early
for the games you actually play", which is both the honest claim and the one a
reader would assume was being made.

Read-only. No provider call.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from scripts.v7_research import pass2_tables as pt
from scripts.v7_research import tables as pass1_tables

Row = dict[str, Any]

ARCHETYPE_VERSION = "v7-archetype-axes-1.0.0"

#: A player needs this many usable matches *within their own mode stratum*
#: before an axis is computed. Below it the axis is ``None`` and the player
#: receives no archetype rather than a label resting on a handful of games.
MIN_MATCHES = 20

#: Mode strata the axes are measured within. ``UNKNOWN`` is not a stratum a
#: player can be assigned to: it is the fail-closed bucket from
#: ``tables.mode_stratum`` and a label must not rest on it.
MODE_STRATA = ("STANDARD", "TURBO")

#: A session shorter than this says nothing about within-session consistency.
MIN_SESSION_MATCHES = 3

#: A player needs this many usable sessions for the modifier.
MIN_SESSIONS = 8

#: Population quantiles that cut the two three-level axes.
TERCILES = (1 / 3, 2 / 3)

#: A special archetype is meant to be rare. Both are cut at the top of the
#: population, and both are strengths: section 7 turns the archetype into a
#: share card, and a share card "must be true and must not be an insult".
SPECIAL_PERCENTILE = 0.98

TEMPO_LEVELS = ("early", "mid", "late")
FIGHT_STYLE_LEVELS = ("frontliner", "opportunist", "ghost")
MODIFIER_LEVELS = ("metronome", "streaky")

SPECIAL_LIGHTHOUSE = "the_lighthouse"
SPECIAL_CLOSER = "the_closer"


class ArchetypeError(RuntimeError):
    """An axis was asked for something the data cannot answer."""


def _self(row: Row) -> Mapping[str, Any] | None:
    self_ = row.get("self")
    return self_ if isinstance(self_, Mapping) else None


def _event_times(row: Row, *keys: str) -> list[int]:
    self_ = _self(row)
    if self_ is None:
        return []
    events = self_.get("events")
    if not isinstance(events, Mapping):
        return []
    times: list[int] = []
    for key in keys:
        for event in events.get(key) or []:
            time = event.get("time")
            if time is not None:
                times.append(int(time))
    return times


def rows_in_stratum(rows: Sequence[Row], stratum: str) -> list[Row]:
    return [row for row in rows if pass1_tables.mode_stratum(row) == stratum]


def dominant_stratum(rows: Sequence[Row]) -> str | None:
    """The mode stratum holding most of the player's matches.

    ``None`` when neither real stratum reaches ``MIN_MATCHES``: a player split
    thinly across modes has no population to be compared against, and
    borrowing the other stratum's cuts is exactly the mode confound this
    module exists to avoid.
    """

    counts = {s: len(rows_in_stratum(rows, s)) for s in MODE_STRATA}
    best = max(counts, key=lambda s: counts[s])
    return best if counts[best] >= MIN_MATCHES else None


# ---------------------------------------------------------------------------
# Raw per-player axis measurements
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AxisMeasurements:
    """One player's raw axis inputs. ``None`` where support is missing."""

    impact_centroid: float | None
    fight_participation: float | None
    deaths_per_fight_minute: float | None
    session_dispersion: float | None
    matches: int
    sessions: int
    stratum: str | None


def impact_centroid(rows: Sequence[Row]) -> float | None:
    """Mean, across matches, of when the player's kills and assists happen,
    as a fraction of that match's duration.

    Normalising by duration is what makes the axis about *tempo* rather than
    about game length: a 60-minute game and a 30-minute game both run 0 to 1,
    so a player is not called "late" for playing long games.
    """

    per_match: list[float] = []
    for row in rows:
        duration = row.get("duration_seconds")
        if not duration:
            continue
        times = _event_times(row, "kill_events", "assist_events")
        if not times:
            continue
        per_match.append(statistics.fmean(min(max(t / duration, 0.0), 1.0) for t in times))
    if len(per_match) < MIN_MATCHES:
        return None
    return statistics.fmean(per_match)


def _fight_style_inputs(row: Row) -> tuple[float, float] | None:
    """``(participation, deaths per fight minute)`` for one match."""

    fights = pt.fight_minutes(row)
    if not fights:
        return None
    involved = {t // 60 for t in _event_times(row, "kill_events", "assist_events", "death_events")}
    deaths = [t // 60 for t in _event_times(row, "death_events")]
    participation = len(fights & involved) / len(fights)
    deaths_in_fights = sum(1 for minute in deaths if minute in fights)
    return participation, deaths_in_fights / len(fights)


def fight_style_axes(rows: Sequence[Row]) -> tuple[float | None, float | None]:
    """Mean participation in fight minutes, and mean deaths per fight minute.

    Participation counts a fight minute in which the player recorded a kill,
    an assist *or* a death: showing up and dying is still showing up, and the
    axis that separates those two is the second one.
    """

    participation: list[float] = []
    deaths: list[float] = []
    for row in rows:
        try:
            pair = _fight_style_inputs(row)
        except ValueError:
            continue  # fails closed upstream on missing kill arrays
        if pair is None:
            continue
        participation.append(pair[0])
        deaths.append(pair[1])
    if len(participation) < MIN_MATCHES:
        return None, None
    return statistics.fmean(participation), statistics.fmean(deaths)


def session_dispersion(history_rows: Sequence[Row]) -> float | None:
    """Observed between-session spread in win rate over the spread chance alone
    would produce.

    For a session of ``n`` matches at the player's own overall win rate ``p``,
    an independent-games model predicts the session win rate to vary with
    variance ``p(1 - p) / n``. The ratio of what is observed to what is
    predicted is the streakiness measure: at 1.0 the player's sessions are
    exactly as varied as coin flips at their own rate, above 1.0 their good
    and bad nights cluster more than chance explains.

    Using the ratio rather than the raw variance is what keeps the axis from
    simply re-reporting win rate — variance is largest at ``p = 0.5``, so a
    raw-variance cut would label every average player streaky.
    """

    sessions = [
        history_rows[session.start_index : session.end_index + 1]
        for session in pass1_tables.iter_sessions(
            list(history_rows), pass1_tables.SESSION_GAP_SECONDS
        )
    ]
    usable = [s for s in sessions if len(s) >= MIN_SESSION_MATCHES]
    if len(usable) < MIN_SESSIONS:
        return None

    outcomes = [[1.0 if row.get("is_victory") else 0.0 for row in session] for session in usable]
    total = sum(len(o) for o in outcomes)
    wins = sum(sum(o) for o in outcomes)
    p = wins / total
    if p <= 0.0 or p >= 1.0:
        return None  # no variance to explain either way

    # Sample variance, not population variance. The session rates are a
    # sample from the player's own process, and dividing by ``k`` instead of
    # ``k - 1`` biases the observed spread down by ``(k - 1) / k`` — around
    # 12% at the eight-session minimum, which is enough on its own to push a
    # genuinely coin-flip player below the 1.0 line and label them a
    # metronome.
    rates = [statistics.fmean(o) for o in outcomes]
    observed = statistics.variance(rates)
    expected = statistics.fmean(p * (1 - p) / len(o) for o in outcomes)
    if expected <= 0.0:
        return None
    return observed / expected


def measure(pass2_rows: Sequence[Row], history_rows: Sequence[Row]) -> AxisMeasurements:
    """One player's axis inputs, measured inside their dominant mode stratum.

    The session modifier is deliberately *not* stratified: it is a property of
    how the player's nights go, not of how a single match is shaped, and
    splitting a year of sessions by mode would break the very sessions it
    measures.
    """

    stratum = dominant_stratum(pass2_rows)
    in_stratum = rows_in_stratum(pass2_rows, stratum) if stratum else []
    participation, deaths = fight_style_axes(in_stratum)
    return AxisMeasurements(
        stratum=stratum,
        impact_centroid=impact_centroid(in_stratum),
        fight_participation=participation,
        deaths_per_fight_minute=deaths,
        session_dispersion=session_dispersion(history_rows),
        matches=len(in_stratum),
        sessions=len(
            [
                s
                for s in pass1_tables.iter_sessions(
                    list(history_rows), pass1_tables.SESSION_GAP_SECONDS
                )
                if (s.end_index - s.start_index + 1) >= MIN_SESSION_MATCHES
            ]
        ),
    )


# ---------------------------------------------------------------------------
# Population cuts
# ---------------------------------------------------------------------------


def quantile(ordered: Sequence[float], q: float) -> float:
    if not ordered:
        raise ArchetypeError("cannot take a quantile of an empty population")
    index = min(len(ordered) - 1, int(q * (len(ordered) - 1) + 0.5))
    return ordered[index]


@dataclass(frozen=True)
class PopulationCuts:
    """The population quantiles every label is assigned against."""

    tempo_low: float
    tempo_high: float
    participation_low: float
    deaths_median: float
    lighthouse_cut: float | None
    closer_cut: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "tempo_low": round(self.tempo_low, 6),
            "tempo_high": round(self.tempo_high, 6),
            "participation_low": round(self.participation_low, 6),
            "deaths_median": round(self.deaths_median, 6),
            "lighthouse_cut": (
                round(self.lighthouse_cut, 6) if self.lighthouse_cut is not None else None
            ),
            "closer_cut": round(self.closer_cut, 6) if self.closer_cut is not None else None,
        }


def population_cuts(
    measurements: Sequence[AxisMeasurements],
    *,
    vision_coverage: Sequence[float] = (),
    closing_rate: Sequence[float] = (),
) -> PopulationCuts:
    """Cuts for one mode stratum. Callers pass only that stratum's players."""

    centroids = sorted(m.impact_centroid for m in measurements if m.impact_centroid is not None)
    participations = sorted(
        m.fight_participation for m in measurements if m.fight_participation is not None
    )
    deaths = sorted(
        m.deaths_per_fight_minute for m in measurements if m.deaths_per_fight_minute is not None
    )
    if not centroids or not participations or not deaths:
        raise ArchetypeError("no player supports the archetype axes; cannot cut a population")
    return PopulationCuts(
        tempo_low=quantile(centroids, TERCILES[0]),
        tempo_high=quantile(centroids, TERCILES[1]),
        participation_low=quantile(participations, TERCILES[0]),
        deaths_median=quantile(deaths, 0.5),
        lighthouse_cut=(
            quantile(sorted(vision_coverage), SPECIAL_PERCENTILE) if vision_coverage else None
        ),
        closer_cut=(quantile(sorted(closing_rate), SPECIAL_PERCENTILE) if closing_rate else None),
    )


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Archetype:
    """A label, plus the stratum whose population it was cut against.

    ``stratum`` is not decoration: "mid tempo" means mid *among the players
    who mostly queue this mode*, and dropping it would let two labels that
    were never comparable be read side by side.
    """

    stratum: str
    tempo: str
    fight_style: str
    modifier: str
    label: str
    is_special: bool = False
    special_label: str | None = None


#: The 18 grid labels. Unserious by licence of the narrative document, and
#: none of them is an insult -- section 7 puts this string on a share card.
GRID_LABELS: dict[tuple[str, str, str], str] = {
    ("early", "frontliner", "metronome"): "The Alarm Clock",
    ("early", "frontliner", "streaky"): "The Opening Act",
    ("early", "opportunist", "metronome"): "The Early Bird",
    ("early", "opportunist", "streaky"): "The Ambusher",
    ("early", "ghost", "metronome"): "The Quiet Start",
    ("early", "ghost", "streaky"): "The Slow Burn",
    ("mid", "frontliner", "metronome"): "The Engine Room",
    ("mid", "frontliner", "streaky"): "The Brawler",
    ("mid", "opportunist", "metronome"): "The Timekeeper",
    ("mid", "opportunist", "streaky"): "The Pickpocket",
    ("mid", "ghost", "metronome"): "The Understudy",
    ("mid", "ghost", "streaky"): "The Wildcard",
    ("late", "frontliner", "metronome"): "The Last Word",
    ("late", "frontliner", "streaky"): "The Overtime",
    ("late", "opportunist", "metronome"): "The Long Game",
    ("late", "opportunist", "streaky"): "The Closer's Apprentice",
    ("late", "ghost", "metronome"): "The Patient One",
    ("late", "ghost", "streaky"): "The Late Bloomer",
}

SPECIAL_LABELS = {
    SPECIAL_LIGHTHOUSE: "The Lighthouse",
    SPECIAL_CLOSER: "The Closer",
}


def assign(
    measurements: AxisMeasurements,
    cuts: PopulationCuts,
    *,
    vision_coverage: float | None = None,
    closing_rate: float | None = None,
) -> Archetype | None:
    """One player's archetype, or ``None`` if any axis lacks support.

    Refusing to label a player with a missing axis is the point: an archetype
    assembled from two measured axes and one default is a guess wearing the
    same clothes as a measurement.
    """

    if (
        measurements.stratum is None
        or measurements.impact_centroid is None
        or measurements.fight_participation is None
        or measurements.deaths_per_fight_minute is None
        or measurements.session_dispersion is None
    ):
        return None

    if measurements.impact_centroid < cuts.tempo_low:
        tempo = "early"
    elif measurements.impact_centroid < cuts.tempo_high:
        tempo = "mid"
    else:
        tempo = "late"

    if measurements.fight_participation < cuts.participation_low:
        fight_style = "ghost"
    elif measurements.deaths_per_fight_minute >= cuts.deaths_median:
        fight_style = "frontliner"
    else:
        fight_style = "opportunist"

    # An absolute cut, not a population one: "streaky" is a claim that the
    # player's nights cluster more than independent games would, and 1.0 is
    # where that claim becomes true. Splitting the population at its own
    # median would guarantee half of everyone is streaky by construction,
    # which would make the modifier a ranking rather than a description.
    modifier = "streaky" if measurements.session_dispersion > 1.0 else "metronome"

    special: str | None = None
    if (
        cuts.lighthouse_cut is not None
        and vision_coverage is not None
        and vision_coverage >= cuts.lighthouse_cut
    ):
        special = SPECIAL_LIGHTHOUSE
    if (
        cuts.closer_cut is not None
        and closing_rate is not None
        and closing_rate >= cuts.closer_cut
        and special is None
    ):
        special = SPECIAL_CLOSER

    return Archetype(
        stratum=measurements.stratum,
        tempo=tempo,
        fight_style=fight_style,
        modifier=modifier,
        label=GRID_LABELS[(tempo, fight_style, modifier)],
        is_special=special is not None,
        special_label=SPECIAL_LABELS[special] if special else None,
    )


__all__ = [
    "ARCHETYPE_VERSION",
    "Archetype",
    "ArchetypeError",
    "AxisMeasurements",
    "FIGHT_STYLE_LEVELS",
    "GRID_LABELS",
    "MODE_STRATA",
    "MODIFIER_LEVELS",
    "PopulationCuts",
    "SPECIAL_LABELS",
    "TEMPO_LEVELS",
    "assign",
    "dominant_stratum",
    "fight_style_axes",
    "impact_centroid",
    "measure",
    "population_cuts",
    "session_dispersion",
]

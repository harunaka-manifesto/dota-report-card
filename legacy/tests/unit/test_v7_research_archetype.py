"""Section 6 archetype axes.

The grid is "for fun, not for science", which makes it *more* important that
the axes underneath refuse to invent a label: a playful string is exactly the
kind of output nobody audits.
"""

from __future__ import annotations

import statistics
from typing import Any

import pytest
from report_card.player_analysis_v7.research.archetype import (
    FIGHT_STYLE_LEVELS,
    GRID_LABELS,
    MIN_MATCHES,
    MIN_SESSIONS,
    MODE_STRATA,
    MODIFIER_LEVELS,
    SPECIAL_LABELS,
    TEMPO_LEVELS,
    ArchetypeError,
    AxisMeasurements,
    assign,
    dominant_stratum,
    fight_style_axes,
    impact_centroid,
    measure,
    population_cuts,
    session_dispersion,
)

from legacy.tests.unit.test_v7_research_pass2_features import row


def event_row(match_id: int, *, kills: list[int], deaths: list[int], turbo: bool = False) -> dict[str, Any]:
    radiant = [0] * 31
    radiant[10] = 2  # one fight minute at minute 10
    return row(
        match_id=match_id,
        game_mode_native="TURBO" if turbo else "ALL_PICK_RANKED",
        radiant_kills=radiant,
        self={
            "events": {
                "kill_events": [{"time": t} for t in kills],
                "assist_events": [],
                "death_events": [{"time": t} for t in deaths],
            }
        },
    )


def history_row(match_id: int, started_at: int, *, won: bool) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "started_at": started_at,
        "ended_at": started_at + 1_800,
        "is_victory": won,
    }


# --------------------------------------------------------------------------
# grid shape
# --------------------------------------------------------------------------


def test_grid_covers_every_combination_exactly_once() -> None:
    assert len(GRID_LABELS) == 18
    assert set(GRID_LABELS) == {
        (tempo, style, modifier)
        for tempo in TEMPO_LEVELS
        for style in FIGHT_STYLE_LEVELS
        for modifier in MODIFIER_LEVELS
    }


def test_grid_labels_are_distinct() -> None:
    assert len(set(GRID_LABELS.values())) == 18


def test_there_are_exactly_two_specials() -> None:
    assert len(SPECIAL_LABELS) == 2
    assert len(set(SPECIAL_LABELS.values())) == 2


def test_grid_and_specials_are_twenty_distinct_labels() -> None:
    assert len(set(GRID_LABELS.values()) | set(SPECIAL_LABELS.values())) == 20


# --------------------------------------------------------------------------
# mode stratification
# --------------------------------------------------------------------------


def test_dominant_stratum_picks_the_mode_the_player_actually_plays() -> None:
    rows = [event_row(i, kills=[600], deaths=[], turbo=True) for i in range(MIN_MATCHES)]
    rows += [event_row(100 + i, kills=[600], deaths=[]) for i in range(3)]
    assert dominant_stratum(rows) == "TURBO"


def test_dominant_stratum_is_none_when_neither_mode_has_support() -> None:
    rows = [event_row(i, kills=[600], deaths=[], turbo=i % 2 == 0) for i in range(10)]
    assert dominant_stratum(rows) is None


def test_measure_reads_only_the_dominant_stratum() -> None:
    """A handful of standard games must not move a turbo player's axes."""

    turbo = [event_row(i, kills=[300], deaths=[], turbo=True) for i in range(MIN_MATCHES)]
    standard = [event_row(100 + i, kills=[1_700], deaths=[]) for i in range(3)]
    both = measure(turbo + standard, [])
    turbo_only = measure(turbo, [])
    assert both.stratum == "TURBO"
    assert both.matches == MIN_MATCHES
    assert both.impact_centroid == pytest.approx(turbo_only.impact_centroid)


def test_mode_strata_excludes_the_fail_closed_bucket() -> None:
    assert "UNKNOWN" not in MODE_STRATA


# --------------------------------------------------------------------------
# axes
# --------------------------------------------------------------------------


def test_impact_centroid_is_normalised_by_duration() -> None:
    """The same event at the same fraction of two different-length games
    yields the same tempo, which is what stops the axis measuring game
    length."""

    short = [
        row(match_id=i, duration_seconds=1_800, self={"events": {"kill_events": [{"time": 900}]}})
        for i in range(MIN_MATCHES)
    ]
    long = [
        row(match_id=i, duration_seconds=3_600, self={"events": {"kill_events": [{"time": 1_800}]}})
        for i in range(MIN_MATCHES)
    ]
    assert impact_centroid(short) == pytest.approx(0.5)
    assert impact_centroid(long) == pytest.approx(0.5)


def test_impact_centroid_needs_minimum_support() -> None:
    rows = [event_row(i, kills=[900], deaths=[]) for i in range(MIN_MATCHES - 1)]
    assert impact_centroid(rows) is None


def test_fight_participation_counts_a_death_as_showing_up() -> None:
    # minute 10 is the only fight minute; the player only dies there.
    rows = [event_row(i, kills=[], deaths=[615]) for i in range(MIN_MATCHES)]
    participation, deaths = fight_style_axes(rows)
    assert participation == pytest.approx(1.0)
    assert deaths == pytest.approx(1.0)


def test_fight_participation_is_zero_when_the_player_misses_every_fight() -> None:
    rows = [event_row(i, kills=[60], deaths=[], turbo=False) for i in range(MIN_MATCHES)]
    participation, deaths = fight_style_axes(rows)
    assert participation == pytest.approx(0.0)
    assert deaths == pytest.approx(0.0)


def test_fight_style_refuses_unavailable_own_event_streams() -> None:
    rows = [event_row(i, kills=[60], deaths=[]) for i in range(MIN_MATCHES)]
    for candidate in rows:
        candidate["self"]["events"] = {
            "kill_events": None,
            "assist_events": None,
            "death_events": None,
        }
    assert fight_style_axes(rows) == (None, None)


def test_impact_centroid_does_not_treat_a_missing_event_stream_as_empty() -> None:
    rows = [
        row(
            match_id=i,
            self={
                "events": {
                    "kill_events": [{"time": 900}],
                    "assist_events": None,
                }
            },
        )
        for i in range(MIN_MATCHES)
    ]
    assert impact_centroid(rows) is None


def test_session_dispersion_is_about_one_for_independent_sessions() -> None:
    """Alternating win/loss inside every session is as close to a coin flip
    as a fixture can be, so the ratio must land near 1, not near 0."""

    rows = []
    match_id = 0
    for session in range(20):
        base = session * 86_400
        for game in range(6):
            rows.append(
                history_row(match_id, base + game * 2_000, won=(match_id % 2 == 0))
            )
            match_id += 1
    dispersion = session_dispersion(rows)
    assert dispersion is not None
    assert 0.0 <= dispersion <= 0.5  # every session identical: far below chance


def test_session_dispersion_is_high_when_whole_sessions_swing() -> None:
    rows = []
    match_id = 0
    for session in range(20):
        base = session * 86_400
        won = session % 2 == 0
        for game in range(6):
            rows.append(history_row(match_id, base + game * 2_000, won=won))
            match_id += 1
    dispersion = session_dispersion(rows)
    assert dispersion is not None
    assert dispersion > 1.0


def test_session_dispersion_needs_enough_sessions() -> None:
    rows = []
    match_id = 0
    for session in range(MIN_SESSIONS - 1):
        base = session * 86_400
        for game in range(6):
            rows.append(history_row(match_id, base + game * 2_000, won=game % 2 == 0))
            match_id += 1
    assert session_dispersion(rows) is None


def test_session_dispersion_uses_sample_variance() -> None:
    """Population variance would divide by ``k`` and bias a coin-flip player
    below 1.0 for free. Checked against the closed form."""

    rows = []
    match_id = 0
    rates = []
    for session in range(10):
        base = session * 86_400
        wins = session % 5  # 0..4 wins out of 4 games
        for game in range(4):
            rows.append(history_row(match_id, base + game * 2_000, won=game < wins))
            match_id += 1
        rates.append(wins / 4)
    p = statistics.fmean(rates)
    expected = statistics.variance(rates) / (p * (1 - p) / 4)
    assert session_dispersion(rows) == pytest.approx(expected)


# --------------------------------------------------------------------------
# assignment
# --------------------------------------------------------------------------


def _measurements(**overrides: Any) -> AxisMeasurements:
    base: dict[str, Any] = {
        "impact_centroid": 0.5,
        "fight_participation": 0.5,
        "deaths_per_fight_minute": 0.2,
        "session_dispersion": 0.9,
        "matches": 100,
        "sessions": 30,
        "stratum": "STANDARD",
    }
    base.update(overrides)
    return AxisMeasurements(**base)


def _cuts() -> Any:
    return population_cuts(
        [
            _measurements(impact_centroid=c, fight_participation=p, deaths_per_fight_minute=d)
            for c, p, d in ((0.4, 0.3, 0.1), (0.5, 0.5, 0.2), (0.6, 0.7, 0.3))
        ]
    )


def test_assign_refuses_a_player_with_a_missing_axis() -> None:
    cuts = _cuts()
    for missing in (
        "impact_centroid",
        "fight_participation",
        "deaths_per_fight_minute",
        "session_dispersion",
        "stratum",
    ):
        assert assign(_measurements(**{missing: None}), cuts) is None


def test_assign_produces_a_grid_label() -> None:
    archetype = assign(_measurements(), _cuts())
    assert archetype is not None
    assert archetype.label == GRID_LABELS[
        (archetype.tempo, archetype.fight_style, archetype.modifier)
    ]
    assert archetype.is_special is False
    assert archetype.special_label is None
    assert archetype.stratum == "STANDARD"


def test_modifier_cut_is_absolute_not_a_population_median() -> None:
    cuts = _cuts()
    assert assign(_measurements(session_dispersion=0.99), cuts).modifier == "metronome"
    assert assign(_measurements(session_dispersion=1.01), cuts).modifier == "streaky"


def test_low_participation_is_a_ghost_regardless_of_deaths() -> None:
    cuts = _cuts()
    archetype = assign(
        _measurements(fight_participation=0.05, deaths_per_fight_minute=9.0), cuts
    )
    assert archetype is not None
    assert archetype.fight_style == "ghost"


def test_special_requires_the_population_cut_to_exist() -> None:
    cuts = _cuts()  # built without vision or closing populations
    archetype = assign(_measurements(), cuts, vision_coverage=0.99, closing_rate=0.99)
    assert archetype is not None
    assert archetype.is_special is False


def test_special_fires_at_the_top_of_the_population() -> None:
    cuts = population_cuts(
        [
            _measurements(impact_centroid=c, fight_participation=p, deaths_per_fight_minute=d)
            for c, p, d in ((0.4, 0.3, 0.1), (0.5, 0.5, 0.2), (0.6, 0.7, 0.3))
        ],
        vision_coverage=[0.1, 0.2, 0.3],
    )
    archetype = assign(_measurements(), cuts, vision_coverage=0.9)
    assert archetype is not None
    assert archetype.is_special is True
    assert archetype.special_label == SPECIAL_LABELS["the_lighthouse"]


def test_population_cuts_refuse_an_unsupported_population() -> None:
    with pytest.raises(ArchetypeError):
        population_cuts([_measurements(impact_centroid=None)])

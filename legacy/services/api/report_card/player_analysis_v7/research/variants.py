"""Declared robustness variants of the frozen candidate definitions.

Nothing in this module changes a frozen candidate. Each helper produces an
*alternative* view of the same evidence so that a specific judgement call made
during discovery can be tested rather than trusted, and every use is reported
alongside the primary result.

The frozen feature layer (``report_card.player_analysis_v7.research.features``) is never edited;
these helpers either build modified :class:`PlayerFrame` copies or temporarily
override a declared modelling constant, which keeps the frozen feature version
and the frozen registry digest meaningful.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator, Sequence
from typing import Any

from report_card.player_analysis_v7.research import features as _features
from report_card.player_analysis_v7.research.features import Opportunity, PlayerFrame

#: Draft modes in which the player does not choose their own hero. Any family
#: whose estimand is about hero *choice* is contaminated by these rows.
NON_CHOSEN_HERO_MODES = frozenset({"SINGLE_DRAFT", "RANDOM_DRAFT"})


@contextlib.contextmanager
def session_gap_override(seconds: int) -> Iterator[None]:
    """Temporarily change the session-boundary gap used by every extractor.

    The 3-hour gap is a modelling choice, not a measurement. Extractors read
    ``features.SESSION_GAP_SECONDS`` at call time, so overriding it here
    reproduces each session-dependent family under an alternative definition
    without touching the frozen code path.
    """

    original = _features.SESSION_GAP_SECONDS
    _features.SESSION_GAP_SECONDS = seconds
    try:
        yield
    finally:
        _features.SESSION_GAP_SECONDS = original


def _clone(frame: PlayerFrame, rows: list[dict[str, Any]]) -> PlayerFrame:
    return PlayerFrame(
        pseudonym=frame.pseudonym,
        split=frame.split,
        completeness=frame.completeness,
        rows=rows,
        parsed=frame.parsed,
    )


def without_non_chosen_hero_modes(frames: Sequence[PlayerFrame]) -> list[PlayerFrame]:
    """Drop single-draft and random-draft matches.

    In those modes the hero is not the player's choice, so a hero-choice
    estimand computed over them measures the game, not the player. Dropping the
    rows also joins the matches on either side of a dropped one, which is the
    intended semantics for adjacency-based families: the previous *chosen* hero
    is the relevant comparison.
    """

    return [
        _clone(
            frame,
            [row for row in frame.rows if row.get("game_mode_native") not in NON_CHOSEN_HERO_MODES],
        )
        for frame in frames
    ]


def volume_capped(frames: Sequence[PlayerFrame], cap: int) -> list[PlayerFrame]:
    """Keep each player's first ``cap`` product-context matches.

    Equalises exposure across players. Any family whose response is mechanically
    a function of how much a player has played — ``hero_novelty`` above all,
    where a hero seen recently is likelier the more you play — must survive this
    before its between-player spread can be called behaviour.
    """

    return [_clone(frame, frame.rows[:cap]) for frame in frames]


def parsed_only(frames: Sequence[PlayerFrame]) -> list[PlayerFrame]:
    """Keep only matches for which parsed detail exists.

    Parsed availability is close to deterministic given observable context, so
    it is a selection mechanism rather than a random thinning. Recomputing a
    history-only family over the parsed subset alone measures how much that
    selection would move the estimand if a candidate were ever restricted to it.
    """

    return [
        _clone(frame, [row for row in frame.rows if row["match_id"] in frame.parsed])
        for frame in frames
    ]


def restrict_to_level(
    per_player: Sequence[tuple[str, Sequence[Opportunity]]],
    factor: str,
    level: str,
) -> list[tuple[str, list[Opportunity]]]:
    """Keep only opportunities whose context ``factor`` equals ``level``."""

    out: list[tuple[str, list[Opportunity]]] = []
    for pseudonym, opportunities in per_player:
        kept = [
            opportunity
            for opportunity in opportunities
            if dict(opportunity.ctx).get(factor) == level
        ]
        if kept:
            out.append((pseudonym, kept))
    return out


__all__ = [
    "NON_CHOSEN_HERO_MODES",
    "parsed_only",
    "restrict_to_level",
    "session_gap_override",
    "volume_capped",
    "without_non_chosen_hero_modes",
]

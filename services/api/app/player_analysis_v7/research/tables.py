"""Canonical V7 research-table views and verified provider semantics.

Everything here is derived from the immutable corpus only. Fields whose
provider semantics are not established by payload evidence are marked
unavailable rather than guessed, per the V7 fail-closed rule.
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any

# Verified from payload evidence over the completed corpus (see
# docs/evidence/v7-canonical-tables-and-capability-atlas-2026-09-03.md):
#
#   radiant_networth_leads[i]  cumulative signed Radiant-minus-Dire net worth
#                              LEVEL at minute i, not an increment
#   radiant_kills[i]           kills scored BY Radiant DURING minute i (interval)
#   dire_kills[i]              kills scored BY Dire DURING minute i (interval)
#
# All three arrays always share a length, and that length is
# ``ceil(duration_seconds / 60) + 1`` for 98.4% of rows and one greater for the
# remainder. Index 0 covers the pre-horn period and the first minute, so it can
# legitimately carry kills. Consumers must clip to the shorter of the array and
# the duration-implied grid rather than assume either.
TRAJECTORY_FIELDS = ("radiant_networth_leads", "radiant_kills", "dire_kills")

# Turbo changes gold/experience rates, tower values, and pacing. It is not a
# harmless extra game mode: it is a different economy. It is retained as an
# explicit context stratum, never silently pooled with the standard modes.
TURBO_MODES = frozenset({"TURBO"})
STANDARD_MODES = frozenset(
    {"ALL_PICK", "ALL_PICK_RANKED", "CAPTAINS_MODE", "RANDOM_DRAFT", "SINGLE_DRAFT"}
)

# Lobby types that are not ordinary matchmaking product context.
NON_PRODUCT_LOBBIES = frozenset({"PRACTICE", "BATTLE_CUP"})

# A match a player did not finish cannot support a behavioural estimand about
# how that player responded during it.
CLEAN_LEAVER_STATUS = "NONE"

# Session boundary. Dota "sessions" are runs of matches played back to back;
# the gap threshold is a modelling choice, declared here once so every
# candidate that needs sessions uses the same definition.
SESSION_GAP_SECONDS = 3 * 3600


def expected_trajectory_length(duration_seconds: int) -> int:
    return math.ceil(duration_seconds / 60) + 1


def minute_grid_length(row: dict[str, Any]) -> int:
    """Number of trustworthy minute slots for ``row``'s trajectories."""

    trajectory = row.get("radiant_networth_leads")
    duration = row.get("duration_seconds")
    if not trajectory or duration is None:
        return 0
    limit = expected_trajectory_length(duration)
    # A nullable slot is not an observed zero.  The lead curve is a single
    # derived series, so a hole in the usable grid makes the whole row
    # unavailable to consumers that need minute alignment.
    if any(value is None for value in trajectory[:limit]):
        return 0
    return min(len(trajectory), limit)


def player_networth_lead(row: dict[str, Any]) -> list[int] | None:
    """Return the net-worth lead trajectory oriented to the sampled player.

    The provider reports the lead from Radiant's point of view. A Dire player's
    own lead is the negation; failing to flip it would invert the sign of every
    comeback and lead-retention estimand.
    """

    trajectory = row.get("radiant_networth_leads")
    if trajectory is None:
        return None
    length = minute_grid_length(row)
    if length == 0:
        return None
    oriented = trajectory[:length]
    if row.get("is_radiant") is True:
        return list(oriented)
    if row.get("is_radiant") is False:
        return [-value for value in oriented]
    return None


def team_kill_trajectories(row: dict[str, Any]) -> tuple[list[int], list[int]] | None:
    """Return ``(own_team_kills, enemy_team_kills)`` per minute, or ``None``."""

    radiant = row.get("radiant_kills")
    dire = row.get("dire_kills")
    if radiant is None or dire is None:
        return None
    length = minute_grid_length(row)
    if length == 0:
        return None
    if row.get("is_radiant") is True:
        return list(radiant[:length]), list(dire[:length])
    if row.get("is_radiant") is False:
        return list(dire[:length]), list(radiant[:length])
    return None


def is_structurally_observable(row: dict[str, Any]) -> bool:
    """Whether the enums that define *match context* are known for this row.

    Deliberately excludes ``position``, ``role`` and ``lane``. The canonical
    table carries a single ``enum_failure`` flag that also fires when any of
    those three is missing, and in this corpus they are missing almost exactly
    when the match is unparsed. Gating structural eligibility on that flag
    would silently condition the whole research population on
    ``isParsed = true`` under a name that does not say so.

    Match context — game mode, lobby, leaver status — is present for every row
    regardless of parsed availability, so it is the honest structural gate.
    Role context availability is a separate question; see ``has_role_context``.
    """

    for field in ("game_mode_native", "lobby_type_native", "leaver_status_native"):
        value = row.get(field)
        if not value or value == "UNKNOWN":
            return False
    return True


def is_product_context(row: dict[str, Any]) -> bool:
    """Ordinary matchmaking context the player actually finished."""

    if not is_structurally_observable(row):
        return False
    if row["lobby_type_native"] in NON_PRODUCT_LOBBIES:
        return False
    if row["leaver_status_native"] != CLEAN_LEAVER_STATUS:
        return False
    mode = row["game_mode_native"]
    return mode in STANDARD_MODES or mode in TURBO_MODES


def mode_stratum(row: dict[str, Any]) -> str:
    mode = row.get("game_mode_native")
    if mode in TURBO_MODES:
        return "TURBO"
    if mode in STANDARD_MODES:
        return "STANDARD"
    return "UNKNOWN"


def has_role_context(row: dict[str, Any]) -> bool:
    """Whether native role/position/lane are all present for this row.

    ``position``, ``role`` and ``lane`` stay separate: they are three different
    provider concepts and are never collapsed into one legacy role word.

    In this corpus these three fields are populated essentially only for parsed
    matches, so requiring role context is equivalent to requiring parsed
    availability. Any candidate that conditions on it inherits the parsed
    selection mechanism and must justify that, not assume it away.
    """

    return all(
        row.get(field) not in (None, "", "UNKNOWN")
        for field in ("position_native", "role_native", "lane_native")
    )


@dataclass(frozen=True)
class Session:
    start_index: int
    end_index: int

    @property
    def length(self) -> int:
        return self.end_index - self.start_index + 1


def order_by_time(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (row["started_at"], row["match_id"]))


def iter_sessions(
    ordered_rows: Sequence[dict[str, Any]],
    gap_seconds: int = SESSION_GAP_SECONDS,
) -> Iterator[Session]:
    """Yield sessions over time-ordered rows.

    A session break is a gap between the previous match's end and the next
    match's start that exceeds ``gap_seconds``.
    """

    if not ordered_rows:
        return
    start = 0
    for index in range(1, len(ordered_rows)):
        previous = ordered_rows[index - 1]
        current = ordered_rows[index]
        if current["started_at"] - previous["ended_at"] > gap_seconds:
            yield Session(start, index - 1)
            start = index
    yield Session(start, len(ordered_rows) - 1)

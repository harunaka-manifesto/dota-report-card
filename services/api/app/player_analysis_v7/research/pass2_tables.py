"""Canonical read/semantics layer for the V7 Pass-2 corpus.

Pass 2 deepens the frozen DISCOVERY cohort with fields Pass 1 never
collected (own-player per-minute trajectories, tower-death events, farm
distribution, ability timings, ward and dewarding events). This module is
the *only* place those provider semantics are decided. It is read-only,
makes no network calls, and fails closed: an unexpected shape raises rather
than returning a plausible-looking default.

Every rule below states the measurement that established it. The
measurements were run over a throwaway analysis script (not committed) on
the corpus at
``.local/corpora/stratz/v7-pass2-2026-09-04/canonical/v7p_*.json``
(278 accounts, 104,982 matches), sampling 20,000-30,000+ matches per
question as noted. Re-verify against a new corpus before trusting these
numbers unchanged.

Where Pass-1 semantics carry over unchanged (product-context gating, the
match-level ``radiant_kills`` / ``dire_kills`` / ``radiant_networth_leads``
grid), this module imports and reuses ``app.player_analysis_v7.research.tables`` rather
than re-deriving or duplicating the rule.

--------------------------------------------------------------------------
Verified semantics, and the measurement that established each one
--------------------------------------------------------------------------

1. TRAJECTORY ALIGNMENT DOES NOT INHERIT PASS 1'S GRID LENGTH UNCHANGED.

   Pass 1 established ``len(trajectory) == ceil(duration/60) + 1`` for the
   match-level radiant/dire arrays. Pass 2's *own-player* per-minute arrays
   are shorter, and two different fields disagree on the offset:

   - The ten "standard" per-minute fields (``gold_per_minute``,
     ``experience_per_minute``, ``last_hits_per_minute``,
     ``denies_per_minute``, ``hero_damage_per_minute``,
     ``hero_damage_received_per_minute``, ``tower_damage_per_minute``,
     ``heal_per_minute``, ``camp_stack``, ``trips_fountain_per_minute``)
     always agree with each other on length: 32,361/32,361 rows (100%,
     80-account sample). That shared length is
     ``ceil(duration/60) + 1 - 2`` for 28,961/29,419 rows (98.4%,
     30,333-match sample) and ``ceil(duration/60) + 1 - 1`` for the
     remaining 458/29,419 (1.6%). Pass 1's own rule (offset 0) never
     occurs.
   - ``networth_per_minute`` is always exactly one element *longer* than
     the ten standard fields: 31,416/31,416 (100%, 80-account sample).
   - ``level`` is measured to NOT be a per-minute grid at all. Its length
     varies unrelated to the other fields (e.g. length 30 alongside
     standard-field length 23 in one 1,380s match; length 14 alongside
     standard-field length 31 in a 1,907s match), and its raw values are
     non-decreasing large integers with no per-minute character. They are
     non-decreasing rather than strictly increasing in 100% of rows against
     51.5% (supervisor re-measurement, 13,399 rows): two level-ups can land
     in the same second, so a strict-monotonicity assumption would be wrong
     for about half the corpus
     (observed: ``[-89, 49, 107, 168, 244, 336, ..., 1791]`` for a 1,907s
     match) — consistent with "elapsed seconds at which each level was
     reached," one entry per level gained, not one entry per minute. It is
     therefore excluded from ``PASS2_TRAJECTORY_FIELDS`` and reachable
     only through ``level_up_times()``, which does not apply a minute grid
     to it.

   No field, across the full sampled corpus, was ever observed *longer*
   than ``ceil(duration/60) + 1`` (the Pass-1 upper bound). ``trajectory()``
   therefore still clips to that bound as a safety net, exactly as Pass 1
   does, even though the true grid is shorter.

2. ``networth_per_minute`` IS CUMULATIVE; ``last_hits_per_minute`` IS A
   PER-MINUTE INCREMENT. They must not be treated the same way.

   - ``networth_per_minute``: strictly non-decreasing in 12,190/23,349 rows
     (52%) and "non-decreasing except for drops of gold lost on death"
     (dips of more than 50 gold treated as real) in the rest; genuine
     decreases do occur (median decrease -129 gold, observed as large as
     -22,898), which is expected for Dota net worth — dying costs gold —
     and is evidence *for* cumulative semantics, not against it. The final
     trajectory entry is within 10% of the match-level ``self.networth``
     scalar for 21,328/23,345 rows (91.4%); the residual gap is explained
     by the trajectory's last populated minute preceding the exact
     match-end timestamp, not by the field being an increment.
   - ``last_hits_per_minute``: only 11/29,419 rows (0.04%) are monotonic;
     values swing between 0 and roughly 10 per entry with no running
     total. The final entry matches the ``self.num_last_hits`` scalar
     within 2% for only 13/29,419 rows (0.04%), undershooting by a mean of
     145 last hits — conclusive evidence it is last hits gained *during*
     that minute, not a cumulative count.

   The other eight standard per-minute fields were not separately
   re-verified to the same depth; ``trajectory()`` returns them unmodified
   and callers must not assume either cumulative or incremental semantics
   without checking, same as Pass 1's fail-closed posture.

3. ``tower_deaths.is_radiant`` MEANS "the tower that died belonged to
   Radiant" (ownership), NOT "Radiant destroyed it."

   Tested by whether the ownership or the destroyer hypothesis better
   predicts the match's own recorded winner, over 16,675 matches (40
   accounts) whose tower-death counts were imbalanced between sides. The
   ownership hypothesis ("Radiant won -> more *Dire-owned* towers died,
   i.e. more ``is_radiant=False`` events") was consistent with the
   recorded ``did_radiant_win`` in 16,236/16,675 rows (97.4%). The
   destroyer hypothesis ("Radiant won -> more towers destroyed *by*
   Radiant, i.e. more ``is_radiant=True`` events") was consistent in only
   439/16,675 rows (2.6%) — the complementary, and much weaker, result.
   This sign governs every objective-related Finding: ``is_radiant=True``
   is a loss for Radiant, a gain for Dire.

4. DEATH EVENT TIMES: range -65s to 5,598s in a 30,333-match sample.
   Negative times occur (568 occurrences) and are genuine pre-horn deaths,
   matching Pass 1's identical finding for ``kill_events``. The
   ``death_events`` count equals the ``self.deaths`` scalar for
   29,165/30,333 rows (96.2%); the residual differs in both directions
   (some counts higher, most lower). Per the same rule Pass 1 applies to
   ``assist_events``: usable for timing and participation shape, not as an
   exact count expected to reconcile with the scalar.

5. ``farm_distribution`` LOCATION BUCKETS: both ``creep_location`` and
   ``neutral_location`` carry ``id`` values ranging over 0-12 (13 distinct
   sub-location ids each, 30,333-match sample). ``sum(gold)`` across both
   buckets is a tight, consistent fraction of ``gold_spent`` — median ratio
   0.302, mean 0.303 — and does NOT approximate ``gold_spent`` or
   ``networth`` as a whole (mean/median ratio to ``networth`` is far off
   and highly variable). This is expected: per
   ``docs/evidence/v7-pass2-production-collection-2026-09-04.md`` §2b,
   ancient-camp and bounty-rune gold were traded away for the complexity
   budget, and kill/tower/comeback gold were never in these buckets to
   begin with. ``lane_vs_jungle_gold()`` therefore answers "how much of
   your farm came from lane creeps versus jungle creeps," not "how much
   gold did you have."

6. ``party_id``: present in 40.9% of a 30,333-match sample (the brief's
   ~46% figure is in the same range; the difference is sample composition,
   not a contradiction). Verified as a genuine "queued together" grouping
   identifier, not inert or "unknown" noise: across 155 matches where two
   or more DISCOVERY-cohort accounts both appear as players (found by
   joining canonical documents on ``match_id``), teammates share an
   identical ``party_id`` in 16 pairs, teammates carry *different*
   ``party_id`` values in 5 pairs (so it is not a match-wide constant), and
   zero pairs on *opposite* teams ever share a ``party_id``. This supports
   treating ``party_id is not None`` as "queued in a party" with the
   expected teammate-only grouping structure. It does not, by itself, prove
   that ``None`` means "solo queue" rather than "not reported" — the
   provider gives no in-band label for ``None`` — so that reading is
   MEDIUM confidence and callers should treat ``party_id is None`` as "not
   known to be partied," not assert solo queue outright.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from app.player_analysis_v7.research import tables as pass1_tables
from app.player_analysis_v7.research.durability import assert_durable_corpus_root
from app.player_analysis_v7.research.rank_fence import assert_row_is_analysis_safe

# Pass 2 collects DISCOVERY only (see
# docs/evidence/v7-pass2-production-collection-2026-09-04.md §4). Mirrors
# the runner's own constant; not imported from the runner to avoid pulling
# in its network/collection dependencies for a read-only reader.
PASS2_SPLIT = "DISCOVERY"

# The eleven per-minute-indexed fields whose grid semantics are covered by
# rule 1 above. Deliberately excludes:
#   - "level": not a per-minute grid at all (rule 1); use level_up_times().
#   - "actions_per_minute": quarantined (see the guard at the end of this
#     module); reachable only via the deliberately alarming accessor name.
PASS2_TRAJECTORY_FIELDS: tuple[str, ...] = (
    "networth_per_minute",
    "gold_per_minute",
    "experience_per_minute",
    "last_hits_per_minute",
    "denies_per_minute",
    "hero_damage_per_minute",
    "hero_damage_received_per_minute",
    "tower_damage_per_minute",
    "heal_per_minute",
    "camp_stack",
    "trips_fountain_per_minute",
)

# A "fight minute" is one where either team scored at least this many
# kills. Declared once, as tables.py declares SESSION_GAP_SECONDS once, so
# every consumer (fight_minutes, deaths_alone_share) uses the same
# definition.
FIGHT_KILL_THRESHOLD = 2


def _self(row: dict[str, Any]) -> Mapping[str, Any]:
    """Return ``row["self"]``, failing closed if the shape is wrong.

    Every Pass-2 row nests the sampled player's own data under ``self``
    (see ``normalize_deep_batch`` in the Pass-2 runner). A row without a
    mapping there is not a Pass-2 row this module knows how to read.
    """

    self_ = row.get("self")
    if not isinstance(self_, Mapping):
        raise ValueError("pass2 row is missing a valid 'self' player block")
    return self_


def iter_pass2_players(root: str | Path) -> Iterator[dict[str, Any]]:
    """Read-only iteration over every player-match row in the Pass-2 corpus.

    Yields one dict per row (one player's view of one match), each
    carrying its parent document's ``account_pseudonym`` and
    ``source_position`` for callers that need to group rows by account
    (e.g. the party_id cross-check in rule 6 above).

    Fails closed: refuses any document whose ``split`` is not
    ``"DISCOVERY"`` (Pass 2 collected DISCOVERY only; CANDIDATE_TEST and
    CALIBRATION_RESERVED / SEALED_VALIDATION must never be read here), and
    refuses a document or row of unexpected shape rather than skipping it
    silently.
    """

    # The Pass-2 canonical directory is a corpus loader root like any other,
    # and it is reached by an explicit path rather than through corpus_paths,
    # so the durability guard is applied here as well.
    root = assert_durable_corpus_root(root, purpose="pass-2 corpus loader root")
    if (root / "canonical").is_dir():
        root = root / "canonical"
    for path in sorted(root.glob("v7p_*.json")):
        with path.open(encoding="utf-8") as handle:
            document = json.load(handle)
        if not isinstance(document, Mapping):
            raise ValueError(f"{path.name}: canonical document is not a mapping")
        split = document.get("split")
        if split != PASS2_SPLIT:
            raise ValueError(
                f"{path.name}: pass2 reader refuses non-DISCOVERY split {split!r}"
            )
        rows = document.get("rows")
        if not isinstance(rows, list):
            raise ValueError(f"{path.name}: canonical document has no 'rows' list")
        account_pseudonym = document.get("account_pseudonym")
        source_position = document.get("source_position")
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                raise ValueError(f"{path.name}: row {index} is not a mapping")
            enriched = dict(row)
            enriched.setdefault("account_pseudonym", account_pseudonym)
            enriched.setdefault("source_position", source_position)
            assert_row_is_analysis_safe(enriched, source=f"pass2 {path.name}")
            yield enriched


def trajectory(row: dict[str, Any], name: str) -> list[int | None] | None:
    """Return the raw per-minute array ``name``, clipped to a safe upper bound.

    ``name`` must be one of ``PASS2_TRAJECTORY_FIELDS``. ``level`` and
    ``actions_per_minute`` are deliberately excluded — see rule 1 and the
    quarantine guard at the end of this module.

    Clips to ``ceil(duration/60) + 1`` (Pass 1's upper bound, measured in
    rule 1 to never be exceeded by any Pass-2 field) as a defensive
    ceiling. It does not attempt to correct the field-specific shorter
    length from rule 1, because that offset differs between
    ``networth_per_minute`` and the other ten fields and inventing a
    single "corrected" length would be a guess, not a measurement.
    """

    if name not in PASS2_TRAJECTORY_FIELDS:
        raise ValueError(
            f"{name!r} is not an ordinary pass2 trajectory field; "
            "'level' and 'actions_per_minute' each require a dedicated accessor"
        )
    self_ = _self(row)
    trajectories = self_.get("trajectories")
    if trajectories is None:
        return None
    if not isinstance(trajectories, Mapping):
        raise ValueError("pass2 row has a malformed 'trajectories' block")
    array = trajectories.get(name)
    if array is None:
        return None
    if not isinstance(array, list):
        raise ValueError(f"pass2 trajectory {name!r} is not a list")
    duration = row.get("duration_seconds")
    if duration is None:
        raise ValueError("pass2 row is missing duration_seconds")
    max_len = pass1_tables.expected_trajectory_length(duration)
    return list(array[:max_len])


def level_up_times(row: dict[str, Any]) -> list[int | None] | None:
    """Return the raw ``level`` array: elapsed seconds at which each level
    was reached, one entry per level gained (rule 1). NOT a per-minute grid
    — do not index it by minute or pass it through ``trajectory()``.
    """

    self_ = _self(row)
    trajectories = self_.get("trajectories")
    if not isinstance(trajectories, Mapping):
        return None
    array = trajectories.get("level")
    if array is None:
        return None
    if not isinstance(array, list):
        raise ValueError("pass2 trajectory 'level' is not a list")
    return list(array)


def own_networth_curve(row: dict[str, Any]) -> list[int | None] | None:
    """The player's own net worth over time (cumulative level; rule 2).

    Pass 2 carries this directly, which is strictly better than Pass 1's
    team-networth-lead proxy: it is not relative to the enemy team and
    needs no side-orientation flip.
    """

    return trajectory(row, "networth_per_minute")


def team_lead_curve(row: dict[str, Any]) -> list[int] | None:
    """The team net-worth lead, oriented to the sampled player.

    The provider reports the lead from Radiant's point of view (verified
    in Pass 1; see ``docs/evidence/v7-canonical-tables-and-capability-atlas-2026-09-03.md``
    §2). Pass 2 rows carry the same match-level ``radiant_networth_leads``
    array as Pass 1, so this reuses ``tables.player_networth_lead`` rather
    than re-deriving the sign rule — only the ``is_radiant`` field has
    moved, from the row's top level in Pass 1 to ``row["self"]`` in Pass 2.
    """

    self_ = _self(row)
    adapter = {
        "radiant_networth_leads": row.get("radiant_networth_leads"),
        "duration_seconds": row.get("duration_seconds"),
        "is_radiant": self_.get("is_radiant"),
    }
    return pass1_tables.player_networth_lead(adapter)


def fight_minutes(row: dict[str, Any]) -> frozenset[int] | None:
    """Minute indices where either team scored >= FIGHT_KILL_THRESHOLD kills.

    Uses the match-level ``radiant_kills`` / ``dire_kills`` arrays, which
    are unchanged from Pass 1 and share Pass 1's verified grid
    (``tables.minute_grid_length``), not the Pass-2-specific per-player
    grid from rule 1.

    Returns ``None`` if either kill array is unavailable.  A fight-minute
    computation with no kill data must not silently mean "no fights anywhere,"
    which is a different, false claim.  Malformed non-list arrays still raise.
    """

    radiant = row.get("radiant_kills")
    dire = row.get("dire_kills")
    if radiant is None or dire is None:
        return None
    if not isinstance(radiant, list) or not isinstance(dire, list):
        raise ValueError("pass2 row has malformed radiant_kills/dire_kills arrays")
    # A shorter provider series has no value for the missing tail.  Do not
    # pad it with zero kills: that would manufacture non-fight minutes.
    length = min(pass1_tables.minute_grid_length(row), len(radiant), len(dire))
    fights: set[int] = set()
    for index in range(length):
        r = radiant[index]
        d = dire[index]
        if r is None or d is None:
            continue
        if r >= FIGHT_KILL_THRESHOLD or d >= FIGHT_KILL_THRESHOLD:
            fights.add(index)
    return frozenset(fights)


def deaths_alone_share(row: dict[str, Any]) -> float | None:
    """Share of the player's deaths that happened in a minute with no team
    kill activity on either side ("died alone", not as part of a fight).

    Definition: for each of the player's ``death_events``, map its ``time``
    to a minute index (``time // 60``, clamped into ``[0, grid_length - 1]``
    — index 0 legitimately covers the pre-horn period, matching Pass 1's
    convention for index 0 of the match-level arrays). A death is "alone"
    if that minute is not in ``fight_minutes(row)``. The share is
    ``alone_deaths / total_deaths``.

    This is the single most important derived signal in the project: it
    approximates dying to a gank or a solo mistake rather than dying inside
    a teamfight both sides were already engaged in.

    Zero-death case: returns ``None`` (the share is undefined, not zero —
    a player who never died has no "alone-death rate" to report, and
    reporting 0.0 would misleadingly read as "never dies alone").

    Fails closed if a death event has no ``time``, or if there is no
    trajectory grid to place deaths on (duration/kill data missing) despite
    there being deaths to place — an incomplete row must not silently
    produce a plausible-looking share.
    """

    self_ = _self(row)
    events = self_.get("events")
    death_events = (events or {}).get("death_events") if isinstance(events, Mapping) else None
    if not death_events:
        return None

    fights = fight_minutes(row)
    if fights is None:
        return None
    length = pass1_tables.minute_grid_length(row)
    if length == 0:
        raise ValueError(
            "pass2 row has recorded deaths but no trajectory grid to place them on"
        )

    alone = 0
    for event in death_events:
        time = event.get("time")
        if time is None:
            raise ValueError("death event is missing 'time'")
        minute = max(0, time // 60)
        minute = min(minute, length - 1)
        if minute not in fights:
            alone += 1
    return alone / len(death_events)


def own_team_tower_kills(row: dict[str, Any]) -> int | None:
    """Count of tower deaths attributable to the player's own team.

    Uses the verified semantics of rule 3: ``tower_deaths[i].is_radiant``
    means the tower that died *belonged to* Radiant, not that Radiant
    destroyed it. A tower dying on the *enemy* side is therefore a kill
    credited to the player's own team, so this counts events where
    ``is_radiant != self.is_radiant``.

    Returns ``None`` when ``tower_deaths`` was not recorded for this row
    (distinct from an empty list, which means zero towers died in a very
    short match). Fails closed if the player's own side, or an individual
    event's side, is unknown — attribution is impossible without both.
    """

    self_ = _self(row)
    is_radiant = self_.get("is_radiant")
    if is_radiant is None:
        raise ValueError("cannot attribute tower kills without self.is_radiant")
    tower_deaths = row.get("tower_deaths")
    if tower_deaths is None:
        return None
    if not isinstance(tower_deaths, list):
        raise ValueError("pass2 row has a malformed 'tower_deaths' list")

    count = 0
    for event in tower_deaths:
        died_is_radiant = event.get("is_radiant")
        if died_is_radiant is None:
            raise ValueError("tower_deaths event is missing 'is_radiant'")
        if died_is_radiant != is_radiant:
            count += 1
    return count


def lane_vs_jungle_gold(row: dict[str, Any]) -> tuple[int, int] | None:
    """Return ``(lane_gold, jungle_gold)`` from ``farm_distribution`` (rule 5).

    ``lane_gold`` sums ``gold`` across ``creep_location`` buckets;
    ``jungle_gold`` sums ``gold`` across ``neutral_location`` buckets.
    Neither total approximates ``gold_spent`` or ``networth`` as a whole —
    see rule 5 — this answers lane-versus-jungle mix only.

    Returns ``None`` when ``farm_distribution`` was not recorded for this
    row.
    """

    self_ = _self(row)
    farm = self_.get("farm_distribution")
    if farm is None:
        return None
    if not isinstance(farm, Mapping):
        raise ValueError("pass2 row has a malformed 'farm_distribution' block")
    lane_buckets = farm.get("creep_location")
    jungle_buckets = farm.get("neutral_location")
    if lane_buckets is None or jungle_buckets is None:
        return None
    if not isinstance(lane_buckets, list) or not isinstance(jungle_buckets, list):
        raise ValueError("pass2 farm distribution locations must be lists")
    buckets = [*lane_buckets, *jungle_buckets]
    if any(not isinstance(bucket, Mapping) or bucket.get("gold") is None for bucket in buckets):
        return None
    lane_gold = sum(bucket["gold"] for bucket in lane_buckets)
    jungle_gold = sum(bucket["gold"] for bucket in jungle_buckets)
    return lane_gold, jungle_gold


def ward_events(row: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Return the player's ward-placement events (``self.events.wards``)."""

    self_ = _self(row)
    events = self_.get("events")
    if not isinstance(events, Mapping):
        return None
    # Older persisted/test-shaped rows omitted the optional key entirely;
    # retain their established observed-empty meaning.  Normalized provider
    # rows always carry the key, so an explicit ``None`` remains unavailable.
    if "wards" not in events:
        return []
    wards = events.get("wards")
    if wards is None:
        return None
    if not isinstance(wards, list):
        raise ValueError("pass2 row has a malformed 'wards' event list")
    return wards


def first_ward_time(row: dict[str, Any]) -> int | None:
    """Earliest ``time`` among the player's ward-placement events, if any."""

    wards = ward_events(row)
    if not wards:
        return None
    times: list[int] = [
        ward["time"] for ward in wards if ward.get("time") is not None
    ]
    if not times:
        return None
    return min(times)


def is_pass2_product_context(row: dict[str, Any]) -> bool:
    """Ordinary matchmaking context the player actually finished.

    Reuses ``tables.is_product_context`` — the Pass-1 rule for "ordinary
    lobby, player finished the match, mode known" is not re-derived here.
    Only the field locations differ between the two corpora:
    ``leaver_status_native`` lives under ``row["self"]`` in Pass 2 rather
    than at the row's top level as in Pass 1's flat history rows; the other
    two fields (``game_mode_native``, ``lobby_type_native``) are already at
    the top level in both.
    """

    self_ = _self(row)
    adapter = {
        "game_mode_native": row.get("game_mode_native"),
        "lobby_type_native": row.get("lobby_type_native"),
        "leaver_status_native": self_.get("leaver_status_native"),
    }
    return pass1_tables.is_product_context(adapter)


# ---------------------------------------------------------------------------
# Quarantine
# ---------------------------------------------------------------------------
#
# stats.actionsPerMinute is collected but stored under
# quarantined_trajectories, never alongside the analytical trajectories
# (see docs/evidence/v7-pass2-production-collection-2026-09-04.md §2).
# Click rate is a legitimate behavioural descriptor AND correlates with
# skill, so it must never drift into a Finding unreviewed. trajectory()
# raises if asked for it; the only way to reach it is the function below,
# whose name says exactly what using its output requires.


def actions_per_minute_requires_hidden_skill_proxy_review(
    row: dict[str, Any],
) -> list[int | None] | None:
    """Raw ``quarantined_trajectories.actions_per_minute``.

    Do not use this in a Finding without an explicit hidden-skill-proxy
    review. It is deliberately not reachable through ``trajectory()`` or
    ``PASS2_TRAJECTORY_FIELDS``.
    """

    self_ = _self(row)
    quarantined = self_.get("quarantined_trajectories")
    if not isinstance(quarantined, Mapping):
        return None
    array = quarantined.get("actions_per_minute")
    if array is None:
        return None
    if not isinstance(array, list):
        raise ValueError("pass2 quarantined trajectory 'actions_per_minute' is not a list")
    return list(array)

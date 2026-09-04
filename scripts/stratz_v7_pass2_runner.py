#!/usr/bin/env python3
"""Production Pass-2 STRATZ acquisition: deep parsed detail for DISCOVERY.

Pass 1 collected player history plus a shallow parsed projection. Pass 2
deepens the *existing* frozen cohort with the fields the V7 report narrative
needs and pass 1 does not have: death timings, every per-minute trajectory,
wards, runes, item usage, tower deaths, draft order, and a scalars-only
projection of the other nine players.

Responsibility boundary: this module turns STRATZ into a validated, versioned
Pass-2 corpus. It derives no Finding, computes no feature, and takes no
analytical position. Feature derivation happens afterwards, from the corpus.

Operational contract, inherited from ``stratz_v7_corpus_runner``:

* the frozen cohort is authoritative and is never regenerated or topped up;
* only ``DISCOVERY`` is collected — ``CANDIDATE_TEST`` is the confirmation
  split and this runner refuses to touch it;
* account order and match order are deterministic;
* every physical attempt is ledgered before any decision is taken on it;
* a completed request is keyed and never re-issued, so a rerun is idempotent
  and a resume refetches nothing;
* writes are atomic and raw bodies are write-once;
* the token never reaches a log, an output, an exception, or an evidence file.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
for _candidate in (str(ROOT), str(API_ROOT)):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from app.stratz.client import parse_rate_limit_headers  # noqa: E402
from app.stratz.queries import GET_DEEP_MATCH_BATCH, GraphQLOperation  # noqa: E402

# The pass-1 runner is the established acquisition architecture. Its transport,
# ledger, redaction, atomic-write and rate-control primitives are reused rather
# than reimplemented, so both passes fail and resume the same way. The
# underscore-prefixed helpers are module-internal to that script by convention,
# not by intent; importing them here keeps one implementation of each rule.
from scripts.stratz_v7_corpus_runner import (  # noqa: E402
    DEFAULT_ENDPOINT,
    DEFAULT_FREEZE_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_FRAME,
    MAX_BACKOFF_SECONDS,
    MAX_WAIT_SECONDS,
    CohortTarget,
    FrozenCohort,
    PauseRun,
    RateController,
    RunnerError,
    Sleep,
    StopRun,
    _assert_no_forbidden_fields,
    _assert_operation_safe,
    _error_text,
    _is_immutable_success_response,
    _is_schema_error,
    _optional_bool,
    _optional_int,
    _optional_sequence,
    _optional_str,
    _read_json,
    _write_json,
    _write_once,
    digest,
    load_frozen_cohort,
    load_stratz_token,
    parse_retry_after,
    redact_bytes,
    redact_text,
    request_key,
    safe_rate_headers,
    safe_response_headers,
    sha256_file,
)

#: Markers the shared helper does not carry. A selection-set mistake comes back
#: as HTTP 400 with this wording, and must stop the run rather than be retried.
_PASS2_SCHEMA_MARKERS = ("must have a sub selection", "must not have a sub selection")


def _is_pass2_schema_error(reason: str | None) -> bool:
    lowered = (reason or "").casefold()
    return _is_schema_error(reason) or any(
        marker in lowered for marker in _PASS2_SCHEMA_MARKERS
    )


PASS2_RUNNER_SCHEMA = "stratz-v7-pass2-runner-1.0.0"
PASS2_NORMALIZED_SCHEMA = "stratz-v7-pass2-provider-native-1.0.0"
PASS2_CANONICAL_SCHEMA = "stratz-v7-pass2-canonical-1.0.0"
PASS2_LEDGER_SCHEMA = "stratz-v7-pass2-request-ledger-1.0.0"

#: The only split this runner will read. CANDIDATE_TEST is the one-shot
#: confirmation split and pass 2 has no claim on it.
PASS2_SPLIT = "DISCOVERY"

#: Owner decision of 2026-09-04: deepen 300 DISCOVERY accounts. Taken in frozen
#: manifest order rather than by who has the most data, because picking the
#: richest accounts turns a frozen cohort into a convenience sample.
PASS2_TARGET_ACCOUNTS = 300

#: Per-account match ceiling. Matches are the most recent parsed matches inside
#: the frozen 365-day window, so the slice is the product-relevant one and is
#: still fully determined by the pass-1 corpus.
PASS2_MATCH_TARGET = 500

#: Measured by the 2026-09-04 sizing probe: batch 8 succeeded on the first rung
#: at 66,123 bytes and no complexity failure. Production does not re-probe.
PASS2_BATCH_SIZE = 8

DEFAULT_PASS2_OUTPUT_DIR = ROOT / ".local/corpora/stratz/v7-pass2-2026-09-04"

#: A smoke run must not be able to turn into a real collection by accident.
#: Three accounts at 24 matches each is nine requests: enough to exercise
#: multi-batch collection, a short final batch, the canonical writer, the
#: checkpoint and the verifier, and small enough to be free.
SMOKE_MAX_ACCOUNTS = 3
SMOKE_MATCH_TARGET = 24
SMOKE_MAX_REQUESTS = 15



# ---------------------------------------------------------------------------
# Rate control
# ---------------------------------------------------------------------------

#: The provider's advertised ceilings, measured from live response headers on
#: 2026-09-04: 8/second, 150/minute, 1,500/hour, 15,000/day.
#:
#: Pass 1 ran under hardcoded local ceilings of 1,000/hour and a planned daily
#: cap of 9,000. Those were a sensible default when nothing about the account's
#: real limits was known, but they are strictly below what this key actually
#: allows, and they cost real time: the first pass-2 run paused at exactly 1,000
#: attempts while the provider's own header still reported 1,129 requests
#: remaining that hour.
PASS2_PROVIDER_LIMITS = {"second": 8, "minute": 150, "hour": 1_500, "day": 15_000}

#: Headroom left unused in each window. The provider's counter is authoritative
#: and shared across every client using this key, so stopping short of zero is
#: what keeps a concurrent session from turning our last request into a 429.
PASS2_RESERVES = {"second": 1, "minute": 10, "hour": 40, "day": 150}


def _next_boundary(now: float, seconds: float) -> float:
    """Start of the next aligned window of ``seconds`` length."""

    return (int(now // seconds) + 1) * seconds


class Pass2RateController(RateController):
    """Rate control that believes the provider's counters over its own guesses.

    Two differences from the pass-1 controller, both measured rather than
    assumed:

    * the local window ceilings start at the provider's advertised limits
      instead of a conservative fraction of them;
    * there is no hardcoded daily cap. The pause decision comes from the live
      ``x-ratelimit-remaining-*`` headers, which account for other sessions
      sharing the key and for windows that reset mid-run.

    STRATZ sends a reset header only for the per-second window, so an exhausted
    minute, hour or day window waits to the next aligned boundary and re-checks.
    Waiting slightly too long is cheap; guessing an early reset is a 429.
    """

    def __init__(self, *, sleep: Sleep, attempt_times: Sequence[float] = ()) -> None:
        super().__init__(sleep=sleep, attempt_times=attempt_times)
        self.limits = dict(PASS2_PROVIDER_LIMITS)

    def _provider_pause(self, now: float) -> tuple[str, float] | None:
        """The longest window the provider says is spent, and when it resets."""

        windows = {"minute": 60.0, "hour": 3_600.0, "day": 86_400.0}
        worst: tuple[str, float] | None = None
        for bucket, length in windows.items():
            remaining = self.remaining.get(bucket)
            if remaining is None or remaining > PASS2_RESERVES[bucket]:
                continue
            resume = _next_boundary(now, length)
            if worst is None or resume > worst[1]:
                worst = (bucket, resume)
        return worst

    async def before_attempt(self, planned_attempts: int = 0) -> None:
        now = time.time()
        self._purge(now)

        spent = self._provider_pause(now)
        if spent is not None:
            bucket, resume = spent
            raise PauseRun(
                f"provider {bucket} window exhausted "
                f"({self.remaining.get(bucket)} left, reserve {PASS2_RESERVES[bucket]})",
                resume_at=datetime.fromtimestamp(resume, UTC).isoformat(),
            )

        delay = 0.0
        second_remaining = self.remaining.get("second")
        if second_remaining is not None and second_remaining <= PASS2_RESERVES["second"]:
            delay = max(delay, self._reset_delay(now) or 1.0)

        # Local windows are a backstop for the case where the provider stops
        # sending headers, and *only* that case.
        #
        # They count a rolling window; STRATZ resets on the clock. A rolling
        # hour therefore straddles two provider hours and hits 1,500 while the
        # provider is still offering hundreds — measured on 2026-09-04, the run
        # stalled with 1,194 remaining on the header. Where the provider tells
        # us what is left, its number is the only one that means anything.
        windows = {"second": 1.0, "minute": 60.0, "hour": 3_600.0, "day": 86_400.0}
        for bucket, limit in self._effective_limits().items():
            if self.remaining.get(bucket) is not None:
                continue
            active = [stamp for stamp in self.times if now - stamp < windows[bucket]]
            if len(active) >= limit:
                delay = max(delay, active[0] + windows[bucket] - now)

        if delay > MAX_WAIT_SECONDS:
            raise PauseRun(
                "rate-window reset exceeds bounded wait; resume from checkpoint",
                resume_at=datetime.fromtimestamp(now + delay, UTC).isoformat(),
            )
        if delay > 0:
            await self._sleep(delay)
        self.times.append(time.time())


class Pass2Error(RunnerError):
    """Pass-2 specific failure."""


class ReservedSplitRequested(Pass2Error):
    """Something asked pass 2 for a split it must never read."""


# ---------------------------------------------------------------------------
# Deterministic planning
# ---------------------------------------------------------------------------


def pass2_targets(
    cohort: FrozenCohort, *, limit: int = PASS2_TARGET_ACCOUNTS
) -> tuple[CohortTarget, ...]:
    """The accounts pass 2 collects, in the order it collects them.

    Frozen manifest order, ``DISCOVERY`` only, first ``limit``. Deterministic
    and non-adaptive: the list does not depend on how much data an account
    turns out to have, so a rerun after a partial collection selects exactly
    the same accounts.
    """

    if limit < 0:
        raise Pass2Error("account limit cannot be negative")
    selected = [target for target in cohort.targets if target.split == PASS2_SPLIT]
    selected.sort(key=lambda target: target.source_position)
    chosen = tuple(selected[:limit])
    for target in chosen:
        if target.split != PASS2_SPLIT:  # pragma: no cover - defensive
            raise ReservedSplitRequested(f"pass 2 refuses split {target.split}")
    return chosen


def planned_match_ids(
    history_document: Mapping[str, Any], *, target: int = PASS2_MATCH_TARGET
) -> list[int]:
    """Deterministic per-account match plan, drawn from the pass-1 corpus.

    Only matches pass 1 saw as parsed are worth a deep request; an unparsed
    match has no trajectories to return. Ordering is most-recent-first with the
    match id as a tie-break, so the slice is stable across runs and does not
    depend on dictionary or filesystem ordering.
    """

    rows = history_document.get("rows")
    if not isinstance(rows, Sequence):
        raise Pass2Error("history document has no rows")
    eligible: list[tuple[int, int]] = []
    seen: set[int] = set()
    for row in rows:
        if not isinstance(row, Mapping) or not row.get("is_parsed"):
            continue
        match_id = row.get("match_id")
        started_at = row.get("started_at")
        if not isinstance(match_id, int) or isinstance(match_id, bool):
            continue
        if not isinstance(started_at, int) or isinstance(started_at, bool):
            continue
        if match_id in seen:
            continue
        seen.add(match_id)
        eligible.append((started_at, match_id))
    eligible.sort(key=lambda item: (-item[0], -item[1]))
    return [match_id for _, match_id in eligible[:target]]


def batches(match_ids: Sequence[int], *, size: int = PASS2_BATCH_SIZE) -> list[list[int]]:
    """Split a match plan into request batches, final batch short."""

    if size < 1:
        raise Pass2Error("batch size must be positive")
    return [list(match_ids[start : start + size]) for start in range(0, len(match_ids), size)]


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

_TRAJECTORY_FIELDS = (
    "networthPerMinute",
    "goldPerMinute",
    "experiencePerMinute",
    "lastHitsPerMinute",
    "deniesPerMinute",
    "heroDamagePerMinute",
    "heroDamageReceivedPerMinute",
    "towerDamagePerMinute",
    "healPerMinute",
    "campStack",
    "level",
    "tripsFountainPerMinute",
)

#: Quarantined. Click-rate style measures correlate with skill and must not
#: become a Finding input without an explicit hidden-skill-proxy review, so the
#: canonical table keeps them behind a name that says so.
_QUARANTINED_TRAJECTORY_FIELDS = ("actionsPerMinute",)

_EVENT_FIELDS = (
    ("killEvents", "kill_events", ("time",)),
    ("deathEvents", "death_events", ("time",)),
    ("assistEvents", "assist_events", ("time",)),
    ("itemPurchases", "item_purchases", ("time", "itemId")),
    ("wards", "wards", ("time", "type", "positionX", "positionY")),
    ("runes", "runes", ("time", "rune")),
    ("itemUsed", "item_used", ("itemId", "count")),
    ("wardDestruction", "ward_destruction", ("time", "isWard", "gold", "experience")),
    ("matchPlayerBuffEvent", "buff_events", ("time", "itemId", "abilityId", "stackCount")),
)

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _snake(name: str) -> str:
    """camelCase provider field to snake_case canonical field.

    Derived rather than table-driven: a hand-maintained map silently leaves a
    new field in camelCase, which then reads as a different column downstream.
    """

    return _CAMEL_BOUNDARY.sub("_", name).lower()


# Field kinds are declared rather than inferred. Guessing from the name is how
# ``wards.type`` (an Int in the payload) and ``towerDeaths.isRadiant`` (a
# Boolean) both got parsed as the wrong kind on the first attempt.
_BOOL_EVENT_FIELDS = frozenset(
    {
        "isWard",
        "isRadiant",
        "isPick",
        "isCaptain",
        "wasBannedSuccessfully",
        "isTalent",
        "isVictory",
        "isRandom",
    }
)
_STR_EVENT_FIELDS = frozenset({"rune", "position", "role", "lane"})


def _event_list(
    value: Any, fields: Sequence[str], path: str
) -> list[dict[str, Any]] | None:
    if value is None:
        return None
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise StopRun(f"schema drift at {path}", kind="schema_drift")
    out: list[dict[str, Any]] = []
    for index, event in enumerate(value):
        if not isinstance(event, Mapping):
            raise StopRun(f"schema drift at {path}[{index}]", kind="schema_drift")
        row: dict[str, Any] = {}
        for field in fields:
            raw = event.get(field)
            where = f"{path}[{index}].{field}"
            if field in _BOOL_EVENT_FIELDS:
                row[_snake(field)] = _optional_bool(raw, where)
            elif field in _STR_EVENT_FIELDS:
                row[_snake(field)] = _optional_str(raw, where)
            else:
                row[_snake(field)] = _optional_int(raw, where)
        out.append(row)
    return out


def _int_series(value: Any, path: str) -> list[int | None] | None:
    series = _optional_sequence(value, path)
    if series is None:
        return None
    return [_optional_int(item, f"{path}[{index}]") for index, item in enumerate(series)]



#: Where a player's gold and experience came from. ``id`` is a location
#: identifier; these two buckets answer the lane-versus-jungle question the
#: field audit asked for, and nothing else in the payload exposes it.
#:
#: Only two, because STRATZ prices the *selection set* rather than the batch:
#: measured on 2026-09-04, four buckets plus the damage report put the query at
#: 379,382 against a 310,000 ceiling, and the same number came back at every
#: batch size from 8 down to 1. Ancient and bounty buckets, and the per-tower
#: damage report, were traded away to fit this one in.
_FARM_BUCKETS = ("creepLocation", "neutralLocation")

def _farm_distribution(farm: Mapping[str, Any], path: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "buy_back_gold": _optional_int(farm.get("buyBackGold"), f"{path}.buyBackGold"),
        "abandon_gold": _optional_int(farm.get("abandonGold"), f"{path}.abandonGold"),
    }
    for bucket in _FARM_BUCKETS:
        out[_snake(bucket)] = _event_list(
            farm.get(bucket), ("id", "count", "gold", "xp"), f"{path}.{bucket}"
        )
    return out


def normalize_deep_batch(
    payload: Mapping[str, Any],
    *,
    requested_ids: Sequence[int],
    pseudonym: str,
    split: str,
    source_position: int,
    batch_index: int,
    operation: GraphQLOperation = GET_DEEP_MATCH_BATCH,
) -> dict[str, Any]:
    """Provider-native projection of one deep batch.

    Fails closed. An unexpected shape, a forbidden field, an unrequested match
    id, or a missing own-player row stops the run rather than producing a row
    that silently means something else.
    """

    if split != PASS2_SPLIT:
        raise ReservedSplitRequested(f"pass 2 refuses to normalise split {split}")
    _assert_no_forbidden_fields(payload)
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise StopRun("STRATZ response has no data", kind="response_shape")
    player = data.get("player")
    if not isinstance(player, Mapping):
        raise StopRun("STRATZ response has no player", kind="response_shape")
    matches = player.get("matches")
    if not isinstance(matches, Sequence) or isinstance(matches, (str, bytes)):
        raise StopRun("STRATZ response has no matches", kind="response_shape")

    requested = list(dict.fromkeys(int(value) for value in requested_ids))
    rows: list[dict[str, Any]] = []
    returned: list[int] = []

    for index, match in enumerate(matches):
        path = f"data.player.matches[{index}]"
        if not isinstance(match, Mapping):
            raise StopRun(f"schema drift at {path}", kind="schema_drift")
        match_id = _optional_int(match.get("id"), f"{path}.id")
        if match_id is None:
            raise StopRun(f"match without an id at {path}", kind="schema_drift")
        returned.append(match_id)

        own = match.get("players")
        if not isinstance(own, Sequence) or isinstance(own, (str, bytes)) or len(own) != 1:
            raise StopRun(f"expected exactly one own-player row at {path}", kind="response_shape")
        me = own[0]
        if not isinstance(me, Mapping):
            raise StopRun(f"schema drift at {path}.players[0]", kind="schema_drift")
        stats = me.get("stats")
        if stats is not None and not isinstance(stats, Mapping):
            raise StopRun(f"schema drift at {path}.players[0].stats", kind="schema_drift")
        stats = stats or {}

        everyone = match.get("allPlayers")
        if everyone is not None and (
            not isinstance(everyone, Sequence) or isinstance(everyone, (str, bytes))
        ):
            raise StopRun(f"schema drift at {path}.allPlayers", kind="schema_drift")

        trajectories = {
            _snake(field): _int_series(stats.get(field), f"{path}.stats.{field}")
            for field in _TRAJECTORY_FIELDS
        }
        quarantined = {
            _snake(field): _int_series(stats.get(field), f"{path}.stats.{field}")
            for field in _QUARANTINED_TRAJECTORY_FIELDS
        }
        events = {
            target: _event_list(stats.get(source), fields, f"{path}.stats.{source}")
            for source, target, fields in _EVENT_FIELDS
        }
        farm = stats.get("farmDistributionReport")
        if farm is not None and not isinstance(farm, Mapping):
            raise StopRun(f"schema drift at {path}.stats.farmDistributionReport", kind="schema_drift")

        rows.append(
            {
                "match_id": match_id,
                "did_radiant_win": _optional_bool(
                    match.get("didRadiantWin"), f"{path}.didRadiantWin"
                ),
                "duration_seconds": _optional_int(
                    match.get("durationSeconds"), f"{path}.durationSeconds"
                ),
                "started_at": _optional_int(match.get("startDateTime"), f"{path}.startDateTime"),
                "ended_at": _optional_int(match.get("endDateTime"), f"{path}.endDateTime"),
                "parsed_at": _optional_int(match.get("parsedDateTime"), f"{path}.parsedDateTime"),
                "stats_at": _optional_int(match.get("statsDateTime"), f"{path}.statsDateTime"),
                "is_stats": _optional_bool(match.get("isStats"), f"{path}.isStats"),
                "num_human_players": _optional_int(
                    match.get("numHumanPlayers"), f"{path}.numHumanPlayers"
                ),
                "game_mode_native": _optional_str(match.get("gameMode"), f"{path}.gameMode"),
                "lobby_type_native": _optional_str(match.get("lobbyType"), f"{path}.lobbyType"),
                "game_version_id": _optional_int(
                    match.get("gameVersionId"), f"{path}.gameVersionId"
                ),
                "region_id": _optional_int(match.get("regionId"), f"{path}.regionId"),
                "first_blood_time": _optional_int(
                    match.get("firstBloodTime"), f"{path}.firstBloodTime"
                ),
                "tower_status_radiant": _optional_int(
                    match.get("towerStatusRadiant"), f"{path}.towerStatusRadiant"
                ),
                "tower_status_dire": _optional_int(
                    match.get("towerStatusDire"), f"{path}.towerStatusDire"
                ),
                "barracks_status_radiant": _optional_int(
                    match.get("barracksStatusRadiant"), f"{path}.barracksStatusRadiant"
                ),
                "barracks_status_dire": _optional_int(
                    match.get("barracksStatusDire"), f"{path}.barracksStatusDire"
                ),
                "radiant_kills": _int_series(match.get("radiantKills"), f"{path}.radiantKills"),
                "dire_kills": _int_series(match.get("direKills"), f"{path}.direKills"),
                "radiant_networth_leads": _int_series(
                    match.get("radiantNetworthLeads"), f"{path}.radiantNetworthLeads"
                ),
                "radiant_experience_leads": _int_series(
                    match.get("radiantExperienceLeads"), f"{path}.radiantExperienceLeads"
                ),
                "bottom_lane_outcome_native": _optional_str(
                    match.get("bottomLaneOutcome"), f"{path}.bottomLaneOutcome"
                ),
                "mid_lane_outcome_native": _optional_str(
                    match.get("midLaneOutcome"), f"{path}.midLaneOutcome"
                ),
                "top_lane_outcome_native": _optional_str(
                    match.get("topLaneOutcome"), f"{path}.topLaneOutcome"
                ),
                "tower_deaths": _event_list(
                    match.get("towerDeaths"),
                    ("time", "isRadiant", "npcId", "attacker"),
                    f"{path}.towerDeaths",
                ),
                "pick_bans": _event_list(
                    match.get("pickBans"),
                    (
                        "isPick",
                        "isRadiant",
                        "heroId",
                        "bannedHeroId",
                        "order",
                        "playerIndex",
                        "isCaptain",
                        "wasBannedSuccessfully",
                    ),
                    f"{path}.pickBans",
                ),
                "all_players": _event_list(
                    everyone,
                    (
                        "playerSlot",
                        "isRadiant",
                        "isVictory",
                        "heroId",
                        "position",
                        "role",
                        "lane",
                        "kills",
                        "deaths",
                        "assists",
                        "numLastHits",
                        "numDenies",
                        "goldPerMinute",
                        "experiencePerMinute",
                        "networth",
                        "heroDamage",
                        "towerDamage",
                        "heroHealing",
                    ),
                    f"{path}.allPlayers",
                )
                if everyone is not None
                else None,
                "self": {
                    "is_radiant": _optional_bool(me.get("isRadiant"), f"{path}.p.isRadiant"),
                    "is_victory": _optional_bool(me.get("isVictory"), f"{path}.p.isVictory"),
                    "hero_id": _optional_int(me.get("heroId"), f"{path}.p.heroId"),
                    "variant": _optional_int(me.get("variant"), f"{path}.p.variant"),
                    "player_slot": _optional_int(me.get("playerSlot"), f"{path}.p.playerSlot"),
                    "position_native": _optional_str(me.get("position"), f"{path}.p.position"),
                    "role_native": _optional_str(me.get("role"), f"{path}.p.role"),
                    "lane_native": _optional_str(me.get("lane"), f"{path}.p.lane"),
                    "leaver_status_native": _optional_str(
                        me.get("leaverStatus"), f"{path}.p.leaverStatus"
                    ),
                    "is_random": _optional_bool(me.get("isRandom"), f"{path}.p.isRandom"),
                    "party_id": _optional_int(me.get("partyId"), f"{path}.p.partyId"),
                    "invisible_seconds": _optional_int(
                        me.get("invisibleSeconds"), f"{path}.p.invisibleSeconds"
                    ),
                    "kills": _optional_int(me.get("kills"), f"{path}.p.kills"),
                    "deaths": _optional_int(me.get("deaths"), f"{path}.p.deaths"),
                    "assists": _optional_int(me.get("assists"), f"{path}.p.assists"),
                    "num_last_hits": _optional_int(me.get("numLastHits"), f"{path}.p.numLastHits"),
                    "num_denies": _optional_int(me.get("numDenies"), f"{path}.p.numDenies"),
                    "gold_per_minute": _optional_int(
                        me.get("goldPerMinute"), f"{path}.p.goldPerMinute"
                    ),
                    "experience_per_minute": _optional_int(
                        me.get("experiencePerMinute"), f"{path}.p.experiencePerMinute"
                    ),
                    "networth": _optional_int(me.get("networth"), f"{path}.p.networth"),
                    "level": _optional_int(me.get("level"), f"{path}.p.level"),
                    "gold": _optional_int(me.get("gold"), f"{path}.p.gold"),
                    "gold_spent": _optional_int(me.get("goldSpent"), f"{path}.p.goldSpent"),
                    "hero_damage": _optional_int(me.get("heroDamage"), f"{path}.p.heroDamage"),
                    "tower_damage": _optional_int(me.get("towerDamage"), f"{path}.p.towerDamage"),
                    "hero_healing": _optional_int(me.get("heroHealing"), f"{path}.p.heroHealing"),
                    "final_inventory": [
                        _optional_int(me.get(field), f"{path}.p.{field}")
                        for field in (
                            "item0Id",
                            "item1Id",
                            "item2Id",
                            "item3Id",
                            "item4Id",
                            "item5Id",
                        )
                    ],
                    "backpack": [
                        _optional_int(me.get(field), f"{path}.p.{field}")
                        for field in ("backpack0Id", "backpack1Id", "backpack2Id")
                    ],
                    "neutral_item": _optional_int(me.get("neutral0Id"), f"{path}.p.neutral0Id"),
                    "abilities": _event_list(
                        me.get("abilities"),
                        ("abilityId", "level", "time", "isTalent"),
                        f"{path}.p.abilities",
                    ),
                    "trajectories": trajectories,
                    "quarantined_trajectories": quarantined,
                    "events": events,
                    "farm_distribution": _farm_distribution(farm, f"{path}.stats.farm")
                    if farm is not None
                    else None,
                },
            }
        )

    unexpected = sorted(set(returned) - set(requested))
    if unexpected:
        raise StopRun("STRATZ returned a match that was not requested", kind="response_shape")
    if len(returned) != len(set(returned)):
        raise StopRun("STRATZ returned a duplicate match in one batch", kind="response_shape")

    return {
        "schema_version": PASS2_NORMALIZED_SCHEMA,
        "provider": "stratz",
        "operation": operation.name,
        "operation_version": operation.version,
        "operation_document_sha256": operation.document_sha256,
        "account_pseudonym": pseudonym,
        "split": split,
        "source_position": source_position,
        "batch_index": batch_index,
        "requested_match_ids": requested,
        "returned_match_ids": sorted(returned),
        "missing_match_ids": sorted(set(requested) - set(returned)),
        "rows": rows,
    }


def canonicalize_account(
    batches_normalized: Sequence[Mapping[str, Any]],
    *,
    pseudonym: str,
    split: str,
    source_position: int,
    planned_ids: Sequence[int],
) -> dict[str, Any]:
    """Fold an account's batches into one canonical document.

    Deduplicates by match id so that a rerun, an overlapping resume, or a
    retried batch cannot produce two logical records for one match. Rows are
    ordered by match id so the document is byte-stable.
    """

    by_match: dict[int, dict[str, Any]] = {}
    duplicates = 0
    for document in batches_normalized:
        for row in document.get("rows", []):
            match_id = row["match_id"]
            if match_id in by_match:
                duplicates += 1
                continue
            by_match[match_id] = row
    rows = [by_match[key] for key in sorted(by_match)]
    planned = list(dict.fromkeys(int(value) for value in planned_ids))
    return {
        "schema_version": PASS2_CANONICAL_SCHEMA,
        "provider": "stratz",
        "account_pseudonym": pseudonym,
        "split": split,
        "source_position": source_position,
        "planned_match_count": len(planned),
        "collected_match_count": len(rows),
        "missing_match_ids": sorted(set(planned) - set(by_match)),
        "duplicate_rows_dropped": duplicates,
        "rows": rows,
    }


class Pass2Runner:
    """Resumable, idempotent Pass-2 collector over the frozen DISCOVERY split."""

    def __init__(
        self,
        cohort: FrozenCohort,
        *,
        pass1_dir: Path = DEFAULT_OUTPUT_DIR,
        output_dir: Path = DEFAULT_PASS2_OUTPUT_DIR,
        token: str | None = None,
        endpoint: str = DEFAULT_ENDPOINT,
        network: bool = False,
        timeout_seconds: float = 45.0,
        max_retries: int = 3,
        max_accounts: int = PASS2_TARGET_ACCOUNTS,
        match_target: int = PASS2_MATCH_TARGET,
        batch_size: int = PASS2_BATCH_SIZE,
        max_requests: int | None = None,
        http_client: httpx.AsyncClient | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        _assert_operation_safe(GET_DEEP_MATCH_BATCH)
        if network and not token:
            raise Pass2Error("network collection requires STRATZ_API_TOKEN")
        if batch_size != PASS2_BATCH_SIZE:
            # The probe measured 8. Changing it silently would invalidate the
            # ledger's comparability and re-open a question already answered.
            raise Pass2Error(
                f"pass 2 batch size is fixed at {PASS2_BATCH_SIZE} by the sizing probe"
            )
        self.cohort = cohort
        self.pass1_dir = pass1_dir
        self.output_dir = output_dir
        self.token = token
        self.endpoint = endpoint
        self.network = network
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, int(max_retries))
        self.match_target = int(match_target)
        self.batch_size = int(batch_size)
        self.max_requests = max_requests
        self._http = http_client
        self._owns_http = http_client is None
        self._sleep = sleep

        self.targets = pass2_targets(cohort, limit=max_accounts)
        self.state_path = output_dir / "manifests/state.json"
        self.manifest_path = output_dir / "manifests/run-manifest.json"
        self.ledger_path = output_dir / "ledgers/request-ledger.jsonl"
        self.raw_dir = output_dir / "raw"
        self.normalized_dir = output_dir / "normalized"
        self.canonical_dir = output_dir / "canonical"
        for directory in (
            self.raw_dir,
            self.normalized_dir,
            self.canonical_dir,
            self.ledger_path.parent,
            self.state_path.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)

        self.ledger_rows = self._load_ledger()
        self._success_by_key: dict[str, dict[str, Any]] = {}
        for _row in self.ledger_rows:
            self._index_success(_row)
        self.state = self._load_state()
        self.physical_this_run = 0
        attempt_times = [
            float(row["timestamp_epoch"]) for row in self.ledger_rows if row.get("timestamp_epoch")
        ]
        self.rate = Pass2RateController(sleep=sleep, attempt_times=attempt_times)
        for row in self.ledger_rows:
            headers = row.get("safe_rate_headers")
            if isinstance(headers, Mapping):
                for bucket, limit in parse_rate_limit_headers(headers).limits.items():
                    self.rate.observed[bucket] = limit

    async def __aenter__(self) -> Pass2Runner:
        if self._http is None and self.network:
            self._http = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._http is not None and self._owns_http:
            await self._http.aclose()
            self._http = None

    # -- state and ledger ---------------------------------------------------

    def _load_ledger(self) -> list[dict[str, Any]]:
        if not self.ledger_path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise Pass2Error("pass-2 request ledger is corrupt") from exc
            if isinstance(row, dict):
                rows.append(row)
        return rows

    def _load_state(self) -> dict[str, Any]:
        if self.state_path.is_file():
            state = _read_json(self.state_path)
            if state.get("schema_version") != PASS2_RUNNER_SCHEMA:
                raise Pass2Error("pass-2 state was written by a different runner version")
            if state.get("operation_document_sha256") != GET_DEEP_MATCH_BATCH.document_sha256:
                raise Pass2Error(
                    "pass-2 state was collected with a different query document; "
                    "resume would mix two contracts in one corpus"
                )
            return state
        return {
            "schema_version": PASS2_RUNNER_SCHEMA,
            "status": "PENDING",
            "phase": "V7_PASS2_DEEP_ACQUISITION",
            "split": PASS2_SPLIT,
            "operation": GET_DEEP_MATCH_BATCH.name,
            "operation_version": GET_DEEP_MATCH_BATCH.version,
            "operation_document_sha256": GET_DEEP_MATCH_BATCH.document_sha256,
            "batch_size": self.batch_size,
            "match_target": self.match_target,
            "accounts": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "physical_attempts": 0,
            "resume_at": None,
            "stop_kind": None,
            "stop_reason": None,
        }

    def _save_state(self) -> None:
        self.state["rate_observed"] = dict(self.rate.observed)
        _write_json(self.state_path, self.state)

    def _append_ledger(self, row: Mapping[str, Any]) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.ledger_rows.append(dict(row))
        self._index_success(row)

    def _index_success(self, row: Mapping[str, Any]) -> None:
        key = row.get("request_key")
        if isinstance(key, str) and row.get("immutable_success") and row.get("raw_body_path"):
            self._success_by_key[key] = dict(row)

    def _success_index(self) -> dict[str, dict[str, Any]]:
        return self._success_by_key

    def _account_state(self, target: CohortTarget) -> dict[str, Any]:
        accounts = self.state.setdefault("accounts", {})
        return accounts.setdefault(
            target.pseudonym,
            {"status": "pending", "next_batch": 0, "batches": [], "planned_matches": None},
        )

    # -- transport ----------------------------------------------------------

    def _archive(
        self,
        *,
        ordinal: int,
        operation: GraphQLOperation,
        variables_hash: str,
        content: bytes,
        response: httpx.Response,
        latency: float,
        attempt: int,
        error_kind: str | None,
    ) -> tuple[Path, Path, str]:
        stem = f"{ordinal:06d}-{operation.name}"
        body_path = self.raw_dir / f"{stem}.body"
        metadata_path = self.raw_dir / f"{stem}.json"
        # A run that died between writing the body and appending its ledger row
        # comes back with the same ordinal, and a write-once archive would then
        # abort the whole collection. Take the next free suffix instead; the
        # ledger is what binds a body to a request, not the filename.
        collision = 0
        while body_path.exists() or metadata_path.exists():
            collision += 1
            stem = f"{ordinal:06d}-{operation.name}-r{collision}"
            body_path = self.raw_dir / f"{stem}.body"
            metadata_path = self.raw_dir / f"{stem}.json"
        body = redact_bytes(content, self.token)
        _write_once(body_path, body)
        archived_sha = sha256_file(body_path)
        _write_json(
            metadata_path,
            {
                "schema_version": "stratz-v7-pass2-raw-response-1.0.0",
                "provider": "stratz",
                "physical_ordinal": ordinal,
                "operation": operation.name,
                "operation_version": operation.version,
                "operation_document_sha256": operation.document_sha256,
                "variables_sha256": variables_hash,
                "http_status": response.status_code,
                "response_bytes": len(content),
                "response_sha256": archived_sha,
                "archived_body_sha256": archived_sha,
                "latency_seconds": round(latency, 6),
                "attempt": attempt,
                "error_kind": error_kind,
                "captured_at": datetime.now(UTC).isoformat(),
                "safe_headers": safe_response_headers(response.headers),
                "safe_rate_headers": safe_rate_headers(response.headers),
                "body_path": body_path.relative_to(self.output_dir).as_posix(),
            },
        )
        return body_path, metadata_path, archived_sha

    def _load_archived(self, row: Mapping[str, Any]) -> Mapping[str, Any]:
        body_path = self.output_dir / str(row["raw_body_path"])
        try:
            payload = json.loads(body_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise Pass2Error("archived pass-2 response is unreadable") from exc
        if not isinstance(payload, Mapping):
            raise Pass2Error("archived pass-2 response is not an object")
        return payload

    async def request(
        self, operation: GraphQLOperation, variables: Mapping[str, Any]
    ) -> tuple[Mapping[str, Any], dict[str, Any]]:
        key = request_key(operation, variables)
        variables_hash = digest(dict(variables))
        existing = self._success_index().get(key)
        if existing is not None:
            self.state["cache_hits"] = int(self.state.get("cache_hits", 0)) + 1
            return self._load_archived(existing), {"cache_hit": True, "physical_attempts": 0}
        if not self.network:
            raise Pass2Error("network disabled; offline validation made zero provider calls")
        if self.max_requests is not None and self.physical_this_run >= self.max_requests:
            raise PauseRun(
                f"request ceiling of {self.max_requests} reached",
                resume_at=datetime.now(UTC).isoformat(),
            )
        self.state["cache_misses"] = int(self.state.get("cache_misses", 0)) + 1

        attempts: list[dict[str, Any]] = []
        last_payload: Mapping[str, Any] | None = None
        last_reason: str | None = None
        for attempt in range(self.max_retries + 1):
            await self.rate.before_attempt()
            if self._http is None:
                self._http = httpx.AsyncClient(timeout=self.timeout_seconds)
            ordinal = len(self.ledger_rows) + 1
            started = time.monotonic()
            timestamp_epoch = time.time()
            status: int | None = None
            response_sha: str | None = None
            archived_sha: str | None = None
            raw_body_path: str | None = None
            raw_metadata_path: str | None = None
            response_bytes = 0
            headers: Mapping[str, str] = {}
            retryable = False
            retry_after: float | None = None
            error_kind: str | None = None
            error: str | None = None
            latency = 0.0
            try:
                response = await self._http.post(
                    self.endpoint,
                    json={"query": operation.document, "variables": dict(variables)},
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                        "User-Agent": "STRATZ_API_DOTA_REPORT_CARD_V7_PASS2",
                    },
                )
                latency = time.monotonic() - started
                status = response.status_code
                headers = safe_response_headers(response.headers)
                response_bytes = len(response.content)
                retry_after = parse_retry_after(response.headers.get("Retry-After"))
                try:
                    payload: Mapping[str, Any] | None = response.json()
                except ValueError:
                    payload = None
                reason = _error_text(payload, self.token)
                if status == 200 and payload is not None and reason is None:
                    if not isinstance(payload.get("data"), Mapping):
                        error_kind, error = "missing_data", "STRATZ response has no data"
                    else:
                        last_payload = payload
                elif status == 200 and reason is not None:
                    error_kind = (
                        "schema_drift" if _is_pass2_schema_error(reason) else "graphql_error"
                    )
                    error = reason
                elif status == 200:
                    error_kind, error = "invalid_response", "STRATZ returned invalid JSON"
                else:
                    error = reason or f"HTTP {status}"
                    if _is_pass2_schema_error(error):
                        error_kind, retryable = "schema_drift", False
                    elif status == 401:
                        error_kind, retryable = "authentication_failure", False
                    elif status == 403:
                        # Cloudflare can return an isolated 403 during an
                        # otherwise healthy authenticated collection.
                        error_kind, retryable = "transient_forbidden", True
                        retry_after = max(retry_after or 0.0, 60.0)
                    else:
                        error_kind = "http_error"
                        retryable = status == 429 or (status is not None and status >= 500)
                body_path, metadata_path, archived_sha = self._archive(
                    ordinal=ordinal,
                    operation=operation,
                    variables_hash=variables_hash,
                    content=response.content,
                    response=response,
                    latency=latency,
                    attempt=attempt,
                    error_kind=error_kind,
                )
                response_sha = archived_sha
                raw_body_path = body_path.relative_to(self.output_dir).as_posix()
                raw_metadata_path = metadata_path.relative_to(self.output_dir).as_posix()
                self.rate.observe(response.headers)
                self.state["rate_observed"] = dict(self.rate.observed)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                latency = time.monotonic() - started
                error_kind, error, retryable = "transport_error", type(exc).__name__, True

            self.physical_this_run += 1
            self.state["physical_attempts"] = int(self.state.get("physical_attempts", 0)) + 1
            row = {
                "schema_version": PASS2_LEDGER_SCHEMA,
                "timestamp": datetime.now(UTC).isoformat(),
                "timestamp_epoch": timestamp_epoch,
                "physical_ordinal": ordinal,
                "attempt": attempt,
                "operation": operation.name,
                "operation_version": operation.version,
                "operation_document_sha256": operation.document_sha256,
                "request_key": key,
                "variables_sha256": variables_hash,
                "variable_keys": sorted(str(name) for name in variables),
                "batch_size": len(variables.get("matchIds", ()))
                if "matchIds" in variables
                else None,
                "http_status": status,
                "response_sha256": response_sha,
                "archived_body_sha256": archived_sha,
                "response_bytes": response_bytes,
                "latency_seconds": round(latency, 6),
                "safe_headers": dict(headers),
                "safe_rate_headers": safe_rate_headers(headers),
                "retrying": retryable and attempt < self.max_retries,
                "retry_after_seconds": retry_after,
                "cache_hit": False,
                "cache_miss": True,
                "immutable_success": _is_immutable_success_response(status, error_kind),
                "error_kind": error_kind,
                "error": redact_text(error, self.token) if error else None,
                "raw_body_path": raw_body_path,
                "raw_metadata_path": raw_metadata_path,
            }
            self._append_ledger(row)
            attempts.append(row)
            last_reason = error

            if status == 401:
                raise StopRun("persistent STRATZ authentication failure", kind="authentication_failure")
            if error_kind == "schema_drift":
                raise StopRun("STRATZ schema drift observed", kind="schema_drift")
            if error_kind == "graphql_error":
                raise StopRun("STRATZ returned a GraphQL error", kind="graphql_error")
            if error_kind == "missing_data":
                raise StopRun("STRATZ response has no data", kind="response_shape")
            if error_kind == "invalid_response":
                raise StopRun("STRATZ returned invalid JSON", kind="invalid_response")
            if status == 429 and attempt >= self.max_retries:
                raise StopRun("persistent STRATZ rate limit response", kind="rate_limited")
            if last_payload is not None:
                break
            if not retryable or attempt >= self.max_retries:
                break
            delay = max(retry_after or 0.0, min(MAX_BACKOFF_SECONDS, 0.25 * (2**attempt)))
            if delay > MAX_WAIT_SECONDS:
                raise PauseRun(
                    "retry reset exceeds bounded wait",
                    resume_at=datetime.fromtimestamp(time.time() + delay, UTC).isoformat(),
                )
            await self._sleep(delay)

        if last_payload is None:
            raise StopRun(
                redact_text(last_reason or "STRATZ request failed", self.token),
                kind=str(attempts[-1].get("error_kind") or "provider_error"),
            )
        return last_payload, {"cache_hit": False, "physical_attempts": len(attempts)}

    # -- acquisition --------------------------------------------------------

    def _pass1_history(self, target: CohortTarget) -> Mapping[str, Any] | None:
        path = self.pass1_dir / "canonical/history" / f"{target.pseudonym}.json"
        if not path.is_file():
            return None
        document = _read_json(path)
        if document.get("split") != PASS2_SPLIT:
            raise ReservedSplitRequested(
                "pass-1 history document is not from the DISCOVERY split"
            )
        return document

    def _normalized_path(self, target: CohortTarget, batch_index: int) -> Path:
        return self.normalized_dir / target.pseudonym / f"batch-{batch_index:04d}.json"

    async def _acquire_account(self, target: CohortTarget) -> None:
        account_state = self._account_state(target)
        if account_state.get("status") == "complete":
            canonical_path = self.canonical_dir / f"{target.pseudonym}.json"
            if not canonical_path.is_file():
                history = self._pass1_history(target)
                if history is not None:
                    self._canonicalize(target, planned_match_ids(history, target=self.match_target))
            return

        history = self._pass1_history(target)
        if history is None:
            account_state.update(status="no_pass1_history", next_batch=0, planned_matches=0)
            self._save_state()
            return
        plan = planned_match_ids(history, target=self.match_target)
        account_state["planned_matches"] = len(plan)
        if not plan:
            account_state["status"] = "no_parsed_opportunities"
            self._save_state()
            return

        planned_batches = batches(plan, size=self.batch_size)
        account_state["planned_batches"] = len(planned_batches)
        done = {entry["batch"] for entry in account_state.get("batches", [])}

        for index, match_ids in enumerate(planned_batches):
            if index in done:
                continue
            payload, meta = await self.request(
                GET_DEEP_MATCH_BATCH,
                {"steamAccountId": target.account_id, "matchIds": list(match_ids)},
            )
            document = normalize_deep_batch(
                payload,
                requested_ids=match_ids,
                pseudonym=target.pseudonym,
                split=target.split,
                source_position=target.source_position,
                batch_index=index,
            )
            path = self._normalized_path(target, index)
            _write_json(path, document)
            account_state.setdefault("batches", []).append(
                {
                    "batch": index,
                    "requested": len(match_ids),
                    "returned": len(document["returned_match_ids"]),
                    "missing": len(document["missing_match_ids"]),
                    "cache_hit": bool(meta["cache_hit"]),
                    "normalized_path": path.relative_to(self.output_dir).as_posix(),
                }
            )
            account_state["next_batch"] = index + 1
            self._save_state()

        account_state["status"] = "complete"
        self._save_state()
        self._canonicalize(target, plan)

    def _canonicalize(self, target: CohortTarget, plan: Sequence[int]) -> None:
        documents = []
        directory = self.normalized_dir / target.pseudonym
        for path in sorted(directory.glob("batch-*.json")):
            documents.append(_read_json(path))
        canonical = canonicalize_account(
            documents,
            pseudonym=target.pseudonym,
            split=target.split,
            source_position=target.source_position,
            planned_ids=plan,
        )
        _write_json(self.canonical_dir / f"{target.pseudonym}.json", canonical)

    async def run(self) -> dict[str, Any]:
        self.state["status"] = "RUNNING"
        self.state["started_at"] = self.state.get("started_at") or datetime.now(UTC).isoformat()
        self._save_state()
        try:
            for target in self.targets:
                await self._acquire_account(target)
        except PauseRun as exc:
            self.state.update(status="PARTIAL_PAUSED", resume_at=exc.resume_at, stop_reason=str(exc))
            self._save_state()
            self.write_manifest()
            return self.state
        except StopRun as exc:
            self.state.update(status="STOP", stop_kind=exc.kind, stop_reason=str(exc))
            self._save_state()
            self.write_manifest()
            return self.state
        except Pass2Error as exc:
            # A setup or contract failure is still a failure the operator has to
            # see in the checkpoint, not only in a traceback.
            self.state.update(
                status="STOP",
                stop_kind="configuration_error",
                stop_reason=redact_text(str(exc), self.token),
            )
            self._save_state()
            self.write_manifest()
            return self.state
        self.state.update(status="COMPLETE", resume_at=None, stop_kind=None, stop_reason=None)
        self._save_state()
        self.write_manifest()
        return self.state

    def write_manifest(self) -> dict[str, Any]:
        accounts = self.state.get("accounts", {})
        statuses: dict[str, int] = {}
        for entry in accounts.values():
            statuses[str(entry.get("status"))] = statuses.get(str(entry.get("status")), 0) + 1
        manifest = {
            "schema_version": PASS2_RUNNER_SCHEMA,
            "phase": "V7_PASS2_DEEP_ACQUISITION",
            "status": self.state.get("status"),
            "split": PASS2_SPLIT,
            "reserved_or_sealed_touched": False,
            "candidate_test_touched": False,
            "operation": {
                "name": GET_DEEP_MATCH_BATCH.name,
                "version": GET_DEEP_MATCH_BATCH.version,
                "document_sha256": GET_DEEP_MATCH_BATCH.document_sha256,
            },
            "batch_size": self.batch_size,
            "match_target": self.match_target,
            "planned_accounts": len(self.targets),
            "account_status_counts": statuses,
            "physical_attempts": int(self.state.get("physical_attempts", 0)),
            "cache_hits": int(self.state.get("cache_hits", 0)),
            "raw_committed": False,
            "identities_included": False,
        }
        _write_json(self.manifest_path, manifest)
        return manifest


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify(output_dir: Path, *, pass1_dir: Path, cohort: FrozenCohort, limit: int) -> dict[str, Any]:
    """Mechanically check that a Pass-2 corpus is complete and coherent.

    Independent of the runner's own bookkeeping: it recomputes from the files
    on disk rather than trusting ``state.json``.
    """

    findings: list[str] = []
    state_path = output_dir / "manifests/state.json"
    state = _read_json(state_path) if state_path.is_file() else {}
    ledger_path = output_dir / "ledgers/request-ledger.jsonl"

    ledger_rows: list[dict[str, Any]] = []
    if ledger_path.is_file():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                ledger_rows.append(json.loads(line))

    body_files = sorted((output_dir / "raw").glob("*.body")) if (output_dir / "raw").is_dir() else []
    referenced = {row["raw_body_path"] for row in ledger_rows if row.get("raw_body_path")}
    hash_mismatch = 0
    for row in ledger_rows:
        rel = row.get("raw_body_path")
        expected = row.get("archived_body_sha256")
        if not rel or not expected:
            continue
        path = output_dir / str(rel)
        if not path.is_file():
            findings.append("ledger references a missing raw body")
            break
        if sha256_file(path) != expected:
            hash_mismatch += 1
    if hash_mismatch:
        findings.append(f"{hash_mismatch} archived bodies do not match their ledgered digest")

    orphans = [p.name for p in body_files if f"raw/{p.name}" not in referenced]
    if orphans:
        findings.append(f"{len(orphans)} raw bodies are not referenced by the ledger")

    documents = {}
    canonical_dir = output_dir / "canonical"
    if canonical_dir.is_dir():
        for path in sorted(canonical_dir.glob("v7p_*.json")):
            documents[path.stem] = _read_json(path)

    targets = pass2_targets(cohort, limit=limit)
    expected_pseudonyms = {target.pseudonym for target in targets}
    stray = sorted(set(documents) - expected_pseudonyms)
    if stray:
        findings.append(f"{len(stray)} canonical documents are outside the planned account set")

    wrong_split = [name for name, doc in documents.items() if doc.get("split") != PASS2_SPLIT]
    if wrong_split:
        findings.append(f"{len(wrong_split)} canonical documents carry a non-DISCOVERY split")

    incomplete: list[str] = []
    duplicate_rows = 0
    total_rows = 0
    for name, document in documents.items():
        total_rows += int(document.get("collected_match_count", 0))
        duplicate_rows += int(document.get("duplicate_rows_dropped", 0))
        if document.get("missing_match_ids"):
            incomplete.append(name)
        ids = [row["match_id"] for row in document.get("rows", [])]
        if len(ids) != len(set(ids)):
            findings.append(f"duplicate match rows inside {name}")

    accounts = state.get("accounts", {})
    statuses: dict[str, int] = {}
    for entry in accounts.values():
        statuses[str(entry.get("status"))] = statuses.get(str(entry.get("status")), 0) + 1
    terminal = {"complete", "no_parsed_opportunities", "no_pass1_history"}
    unfinished = [name for name, entry in accounts.items() if entry.get("status") not in terminal]

    stamped = state.get("operation_document_sha256")
    if stamped and stamped != GET_DEEP_MATCH_BATCH.document_sha256:
        findings.append("corpus was collected with a different query document than the current one")

    return {
        "output_dir": str(output_dir),
        "pass1_dir": str(pass1_dir),
        "planned_accounts": len(targets),
        "canonical_documents": len(documents),
        "account_status_counts": statuses,
        "accounts_not_terminal": len(unfinished),
        "accounts_with_missing_matches": len(incomplete),
        "collected_matches": total_rows,
        "duplicate_rows_dropped": duplicate_rows,
        "ledger_rows": len(ledger_rows),
        "raw_bodies": len(body_files),
        "orphan_raw_bodies": len(orphans),
        "operation_document_sha256": GET_DEEP_MATCH_BATCH.document_sha256,
        "operation_version": GET_DEEP_MATCH_BATCH.version,
        "run_status": state.get("status"),
        "critical_findings": findings,
        "complete": (
            not findings
            and bool(documents)
            and not unfinished
            and len(documents) + statuses.get("no_parsed_opportunities", 0)
            + statuses.get("no_pass1_history", 0)
            >= len(accounts)
        ),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cohort(args: argparse.Namespace) -> FrozenCohort:
    return load_frozen_cohort(Path(args.freeze_dir), source_frame_path=Path(args.source_frame))


async def _collect(args: argparse.Namespace) -> int:
    cohort = _cohort(args)
    token = load_stratz_token(Path(args.dotenv)) if args.network else None
    max_accounts = args.max_accounts
    max_requests = args.max_requests
    match_target = args.match_target
    if args.smoke:
        max_accounts = min(max_accounts or SMOKE_MAX_ACCOUNTS, SMOKE_MAX_ACCOUNTS)
        max_requests = min(max_requests or SMOKE_MAX_REQUESTS, SMOKE_MAX_REQUESTS)
        match_target = min(match_target, SMOKE_MATCH_TARGET)
    async with Pass2Runner(
        cohort,
        pass1_dir=Path(args.pass1_dir),
        output_dir=Path(args.output_dir),
        token=token,
        endpoint=args.endpoint,
        network=args.network,
        max_accounts=max_accounts or PASS2_TARGET_ACCOUNTS,
        match_target=match_target,
        max_requests=max_requests,
    ) as runner:
        state = await runner.run()
    print(f"status: {state['status']}")
    print(f"physical attempts: {state.get('physical_attempts')}")
    print(f"cache hits: {state.get('cache_hits')}")
    counts: dict[str, int] = {}
    for entry in state.get("accounts", {}).values():
        counts[str(entry.get("status"))] = counts.get(str(entry.get("status")), 0) + 1
    print(f"accounts: {counts}")
    if state.get("stop_reason"):
        print(f"stop: {state.get('stop_kind')} — {state.get('stop_reason')}")
    return 0 if state["status"] in {"COMPLETE", "PARTIAL_PAUSED"} else 2


def _verify(args: argparse.Namespace) -> int:
    report = verify(
        Path(args.output_dir),
        pass1_dir=Path(args.pass1_dir),
        cohort=_cohort(args),
        limit=args.max_accounts or PASS2_TARGET_ACCOUNTS,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["complete"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("collect", "verify"):
        stage = sub.add_parser(name)
        stage.add_argument("--freeze-dir", default=str(DEFAULT_FREEZE_DIR))
        stage.add_argument("--source-frame", default=str(DEFAULT_SOURCE_FRAME))
        stage.add_argument("--pass1-dir", default=str(DEFAULT_OUTPUT_DIR))
        stage.add_argument("--output-dir", default=str(DEFAULT_PASS2_OUTPUT_DIR))
        stage.add_argument("--max-accounts", type=int, default=None)
        if name == "collect":
            stage.add_argument("--dotenv", default=".env")
            stage.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
            stage.add_argument("--match-target", type=int, default=PASS2_MATCH_TARGET)
            stage.add_argument("--max-requests", type=int, default=None)
            stage.add_argument(
                "--smoke",
                action="store_true",
                help=(
                    f"clamp to {SMOKE_MAX_ACCOUNTS} accounts and {SMOKE_MAX_REQUESTS} requests; "
                    "exercises the real query, parser, writer, checkpoint and verifier"
                ),
            )
            stage.add_argument(
                "--acknowledge-network-collection",
                dest="network",
                action="store_true",
                help="required for any live request; without it the run is offline and makes none",
            )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "verify":
        return _verify(args)
    return asyncio.run(_collect(args))


if __name__ == "__main__":
    raise SystemExit(main())

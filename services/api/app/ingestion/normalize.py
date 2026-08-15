from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from app.ingestion.coverage import ParseCoverage, coverage_for_match
from app.ingestion.eligibility import EligibilityResult


@dataclass(frozen=True, slots=True)
class NormalizedEvent:
    event_type: str
    time_seconds: int | None
    value: float | None = None
    actor_account_id: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NormalizedParticipant:
    account_id: int | None
    player_slot: int | None
    hero_id: int | None
    lane_role: int | None
    won: bool
    kills: int
    deaths: int
    assists: int
    last_hits: int
    denies: int
    gold_per_min: float
    xp_per_min: float
    net_worth: float
    gold_spent: float
    hero_damage: float
    tower_damage: float
    hero_healing: float
    obs_placed: int
    sen_placed: int
    party_size: int | None
    rank_tier: int | None
    item_ids: tuple[int, ...]
    item_timings: tuple[tuple[int, int], ...]
    role: int | None = None
    role_probability: float = 0.0
    role_method: str | None = None
    role_signals: dict[str, float] = field(default_factory=dict)
    events: tuple[NormalizedEvent, ...] = ()
    death_events_available: bool = False


@dataclass(frozen=True, slots=True)
class NormalizedMatch:
    match_id: int
    account_id: int
    start_time: int | None
    duration_seconds: int
    radiant: bool
    won: bool
    game_mode: int | None
    lobby_type: int | None
    patch: str | None
    rank_tier: int | None
    party_size: int | None
    participants: tuple[NormalizedParticipant, ...]
    target_participant: NormalizedParticipant
    coverage: ParseCoverage
    time_series: tuple[float, ...] = ()
    objectives: tuple[NormalizedEvent, ...] = ()
    teamfights: tuple[dict[str, Any], ...] = ()
    normalized_at: str = ""
    eligibility: EligibilityResult | None = None


def normalize_match(
    detail: dict[str, Any],
    *,
    account_id: int,
    eligibility: EligibilityResult | None = None,
) -> NormalizedMatch:
    match_id = int(detail["match_id"])
    players = [
        _normalize_participant(row, detail)
        for row in detail.get("players") or []
        if isinstance(row, dict)
    ]
    target_index = next(
        (index for index, row in enumerate(players) if row.account_id == account_id),
        None,
    )
    if target_index is None:
        raise ValueError(f"player {account_id} not present in match {match_id}")

    radiant_win = bool(detail.get("radiant_win"))
    radiant = _is_radiant(players[target_index].player_slot)
    target = players[target_index]
    target = replace(target, won=radiant_win == radiant)
    players[target_index] = target
    # The source's radiant_win applies to every participant, not just the target.
    players = [replace(row, won=radiant_win == _is_radiant(row.player_slot)) for row in players]
    target = players[target_index]
    coverage = coverage_for_match(detail, _target_raw(detail, account_id))
    duration = int(detail.get("duration") or 0)
    time_series = tuple(
        float(value)
        for value in (detail.get("radiant_gold_adv") or [])
        if isinstance(value, (int, float))
    )
    objectives = tuple(_event_from_objective(item) for item in detail.get("objectives") or [])
    return NormalizedMatch(
        match_id=match_id,
        account_id=account_id,
        start_time=_as_int(detail.get("start_time")),
        duration_seconds=duration,
        radiant=radiant,
        won=target.won,
        game_mode=_as_int(detail.get("game_mode")),
        lobby_type=_as_int(detail.get("lobby_type")),
        patch=_as_str(detail.get("patch") or detail.get("version")),
        rank_tier=target.rank_tier,
        party_size=target.party_size,
        participants=tuple(players),
        target_participant=target,
        coverage=coverage,
        time_series=time_series,
        objectives=objectives,
        teamfights=tuple(item for item in detail.get("teamfights") or [] if isinstance(item, dict)),
        normalized_at=datetime.now(UTC).isoformat(),
        eligibility=eligibility,
    )


def _normalize_participant(row: dict[str, Any], detail: dict[str, Any]) -> NormalizedParticipant:
    item_ids_list: list[int] = []
    for key in ("item_0", "item_1", "item_2", "item_3", "item_4", "item_5", "item_neutral"):
        item_id = _as_int(row.get(key))
        if item_id is not None and item_id != 0:
            item_ids_list.append(item_id)
    item_ids = tuple(item_ids_list)
    item_timings = tuple(
        (item_id, _as_int(item.get("time")) or 0)
        for item in row.get("purchase_log") or []
        if isinstance(item, dict)
        and (item_id := _as_int(item.get("item_id") or item.get("item"))) is not None
    )
    events = tuple(_participant_events(row, detail))
    return NormalizedParticipant(
        account_id=_as_int(row.get("account_id")),
        player_slot=_as_int(row.get("player_slot")),
        hero_id=_as_int(row.get("hero_id")),
        lane_role=_as_int(row.get("lane_role")),
        won=bool(detail.get("radiant_win")) == _is_radiant(_as_int(row.get("player_slot"))),
        kills=_as_int(row.get("kills")) or 0,
        deaths=_as_int(row.get("deaths")) or 0,
        assists=_as_int(row.get("assists")) or 0,
        last_hits=_as_int(row.get("last_hits")) or 0,
        denies=_as_int(row.get("denies")) or 0,
        gold_per_min=_as_float(row.get("gold_per_min")),
        xp_per_min=_as_float(row.get("xp_per_min")),
        net_worth=_as_float(row.get("net_worth")),
        gold_spent=_as_float(row.get("gold_spent")),
        hero_damage=_as_float(row.get("hero_damage")),
        tower_damage=_as_float(row.get("tower_damage")),
        hero_healing=_as_float(row.get("hero_healing")),
        obs_placed=_as_int(row.get("obs_placed")) or 0,
        sen_placed=_as_int(row.get("sen_placed")) or 0,
        party_size=_as_int(row.get("party_size")),
        rank_tier=_as_int(row.get("rank_tier")),
        item_ids=item_ids,
        item_timings=item_timings,
        events=events,
        death_events_available=_death_event_source_available(row, detail),
    )


def _participant_events(row: dict[str, Any], detail: dict[str, Any] | None = None) -> list[NormalizedEvent]:
    events: list[NormalizedEvent] = []
    for item in row.get("kills_log") or []:
        if isinstance(item, dict):
            events.append(
                NormalizedEvent(
                    event_type="kill",
                    time_seconds=_as_int(item.get("time")),
                    actor_account_id=_as_int(row.get("account_id")),
                    payload={"victim": item.get("unit")},
                )
            )
    for item in row.get("buyback_log") or []:
        if isinstance(item, dict):
            events.append(
                NormalizedEvent(
                    event_type="buyback",
                    time_seconds=_as_int(item.get("time")),
                    actor_account_id=_as_int(row.get("account_id")),
                )
            )
    for item in row.get("death_log") or row.get("deaths_log") or []:
        if isinstance(item, dict):
            events.append(
                NormalizedEvent(
                    event_type="death",
                    time_seconds=_as_int(item.get("time")),
                    actor_account_id=_as_int(row.get("account_id")),
                    payload={"source": "death_log"},
                )
            )
    if detail is not None and _as_int(row.get("account_id")) is not None:
        account_id = _as_int(row.get("account_id"))
        for killer in detail.get("players") or []:
            if not isinstance(killer, dict) or killer is row:
                continue
            for item in killer.get("kills_log") or []:
                if not isinstance(item, dict):
                    continue
                victim_id = _as_int(
                    item.get("victim_account_id")
                    or item.get("victim_id")
                    or item.get("victim")
                )
                if victim_id == account_id:
                    events.append(
                        NormalizedEvent(
                            event_type="death",
                            time_seconds=_as_int(item.get("time")),
                            actor_account_id=account_id,
                            payload={
                                "killer_account_id": _as_int(killer.get("account_id")),
                                "source": "opponent_kills_log",
                            },
                        )
                    )
    for item in row.get("purchase_log") or []:
        if isinstance(item, dict):
            events.append(
                NormalizedEvent(
                    event_type="purchase",
                    time_seconds=_as_int(item.get("time")),
                    actor_account_id=_as_int(row.get("account_id")),
                    payload={"item_id": _as_int(item.get("item_id") or item.get("item"))},
                )
            )
    return events


def _event_from_objective(item: Any) -> NormalizedEvent:
    if not isinstance(item, dict):
        return NormalizedEvent("objective", None)
    return NormalizedEvent(
        event_type=str(item.get("type") or "objective"),
        time_seconds=_as_int(item.get("time")),
        actor_account_id=_as_int(item.get("player_slot")),
        payload={key: value for key, value in item.items() if key not in {"type", "time"}},
    )


def _target_raw(detail: dict[str, Any], account_id: int) -> dict[str, Any] | None:
    return next(
        (
            row
            for row in detail.get("players") or []
            if isinstance(row, dict) and _as_int(row.get("account_id")) == account_id
        ),
        None,
    )


def _death_event_source_available(row: dict[str, Any], detail: dict[str, Any]) -> bool:
    if "death_log" in row or "deaths_log" in row:
        return True
    account_id = _as_int(row.get("account_id"))
    if account_id is None:
        return False
    for killer in detail.get("players") or []:
        if not isinstance(killer, dict) or killer is row:
            continue
        for item in killer.get("kills_log") or []:
            if not isinstance(item, dict):
                continue
            victim_id = _as_int(
                item.get("victim_account_id") or item.get("victim_id") or item.get("victim")
            )
            if victim_id == account_id:
                return True
    return False


def _is_radiant(player_slot: int | None) -> bool:
    return bool(player_slot is not None and player_slot < 128)


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _as_str(value: Any) -> str | None:
    return str(value) if value is not None else None

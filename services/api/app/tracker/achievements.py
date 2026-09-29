"""Versioned Standard-match achievements from retained tracker facts."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy import Connection, select, tuple_

from .achievement_rules import RULE_VERSION, THRESHOLDS
from .schema import account_matches, analyses, match_players, profiles
from .scope import entitled

IDS = (1, 2, 4, 6, 8, 10, 11, 13, 14, 15, 17, 18, 20, 22, 23, 25, 30, 37, 41, 42, 44, 45, 49, 50)
CORE = {"CARRY", "MID", "OFFLANE"}
ROLES: dict[int, set[str]] = {
    6: {"CARRY"}, 8: {"MID", "OFFLANE"}, 10: CORE, 11: {"MID"},
    20: CORE, 22: CORE, 23: CORE, 25: CORE,
    37: {"SUPPORT"}, 41: {"SUPPORT"}, 42: {"SUPPORT"},
    44: {"OFFLANE"}, 45: {"CARRY", "MID"}, 49: {"SUPPORT"}, 50: {"SUPPORT"},
}


def _point(player: Mapping[str, Any], field: str, second: int) -> int | None:
    checkpoints = player.get("checkpoints")
    series = checkpoints.get(field) if isinstance(checkpoints, dict) else None
    value = series.get(str(second)) if isinstance(series, dict) else None
    return value if type(value) is int and value >= 0 else None


def _value(player: Mapping[str, Any], field: str) -> int | None:
    summary = player.get("summary")
    values = summary.get("values") if isinstance(summary, dict) else None
    value = values.get(field) if isinstance(values, dict) else None
    return value if type(value) is int and value >= 0 else None


def _conflict(paths: list[str], slots: set[int], fields: set[str]) -> bool:
    return any(path in {"duration_seconds", "mode", "game_mode", "lobby_type"} or
               any(path.startswith(f"players.{slot}.") and
                   any(f".{field}" in path for field in fields) for slot in slots)
               for path in paths if isinstance(path, str))


def prior_award_rows(connection: Connection, *, profile_id: str, link: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Current, entitled, chronological history for cross-match feats."""
    profile = connection.execute(select(profiles).where(profiles.c.id == profile_id)).mappings().one()
    return [dict(row) for row in connection.execute(select(
        account_matches.c.match_id, match_players.c.hero_id, analyses.c.result,
    ).join(analyses, analyses.c.id == account_matches.c.active_analysis_id).join(
        match_players, (match_players.c.match_id == account_matches.c.match_id) &
        (match_players.c.player_slot == account_matches.c.player_slot),
    ).where(
        account_matches.c.profile_id == profile_id,
        account_matches.c.mode == "STANDARD", account_matches.c.progression == "STANDARD",
        account_matches.c.lifecycle == "READY", entitled(profile, account_matches),
        tuple_(account_matches.c.provider_started_at, account_matches.c.provider_source_match_id)
        < (link["provider_started_at"], link["provider_source_match_id"]),
    ).order_by(account_matches.c.provider_started_at,
               account_matches.c.provider_source_match_id)).mappings().all()]


def gold_advantage_valid(advantage: Any, duration: int) -> bool:
    """Minute map must start at 0:00 with 0, be contiguous, and cover the match."""
    if not isinstance(advantage, dict) or not advantage:
        return False
    try:
        seconds = sorted(int(key) for key in advantage)
    except ValueError:
        return False
    return (seconds == list(range(0, 60 * len(seconds), 60)) and advantage.get("0") == 0
            and all(type(v) is int for v in advantage.values())
            and seconds[-1] >= (duration // 60) * 60)


def evaluate_match(*, features: list[dict[str, Any]], slot: int, role: str,
                   mode: str, progression: str, duration: int,
                   positions: Mapping[int, int | None],
                   core_fights: Mapping[str, Any] | None,
                   pb_metrics: list[str], pb_ready_count: int, prior: list[dict[str, Any]],
                   repeatable: set[int], quarantined: list[str]) -> dict[str, Any]:
    """Return earned facts and evaluability; never turn a missing value into zero."""
    result: dict[str, Any] = {"rule_version": RULE_VERSION, "awards": [], "evaluable_ids": [],
                              "unavailable": [], "pb_metrics": pb_metrics, "progress": {}}
    if mode != "STANDARD" or progression != "STANDARD" or role not in {"CARRY", "MID", "OFFLANE", "SUPPORT"}:
        return result
    player = features[slot]
    own = player.get("summary", {})
    hero_id = own.get("hero_id")
    allies = set(range(0, 5)) if slot < 5 else set(range(5, 10))
    enemies = set(range(10)) - allies
    awards: list[dict[str, Any]] = result["awards"]
    evaluable: list[int] = result["evaluable_ids"]
    T = THRESHOLDS

    def check(ident: int, facts: dict[str, Any] | None, qualifies: bool) -> None:
        if role not in ROLES.get(ident, {"CARRY", "MID", "OFFLANE", "SUPPORT"}) or facts is None:
            return
        evaluable.append(ident)
        if qualifies:
            awards.append({"id": ident, "proof": facts})

    # Strict at-time PBs have already passed the same five-prior gate as the PB engine.
    check(1, {"strict_pb_metrics": pb_metrics} if pb_ready_count >= 2 else None, len(pb_metrics) >= 2)
    check(2, {"strict_pb_metrics": pb_metrics} if pb_ready_count >= 3 else None, len(pb_metrics) >= 3)
    earlier_heroes: dict[str, set[int]] = {}
    for row in prior:
        for metric in row["result"].get("achievement_pb_metrics", []):
            earlier_heroes.setdefault(metric, set()).add(row["hero_id"])
    repeated_metrics = [metric for metric in pb_metrics if earlier_heroes.get(metric, set()) - {hero_id}]
    progress_4 = max((len(heroes) for heroes in earlier_heroes.values()), default=0)
    result["progress"]["4"] = {"distinct_heroes": progress_4, "target": 2}
    check(4, {"hero_id": hero_id, "metric_ids": repeated_metrics,
              "previous_distinct_heroes": sorted({h for metric in repeated_metrics
                                                     for h in earlier_heroes[metric]})} if pb_ready_count else None,
          bool(repeated_metrics) and any(hero_id not in earlier_heroes[metric] for metric in repeated_metrics))

    nw10, nw20, cs10 = _point(player, "net_worth", 600), _point(player, "net_worth", 1200), _point(player, "last_hits", 600)
    t = T[6]
    if duration >= t["min_duration"] and not _conflict(quarantined, {slot}, {"net_worth", "last_hits"}):
        check(6, {"last_hits_at_10": cs10, "net_worth_at_20": nw20} if cs10 is not None and nw20 is not None else None,
              cs10 is not None and nw20 is not None and cs10 >= t["last_hits_at_600"]
              and nw20 >= t["net_worth_at_1200"])
    # The unique enemy player holding the same effective role. Both sides must sit at that
    # role's position in the role assignment, so a corrected own role or an ambiguous
    # assignment leaves #8/#11 unavailable instead of comparing the wrong player.
    expected_peer = 2 if role == "MID" else 3 if role == "OFFLANE" else None
    peer = ([s for s in enemies if positions.get(s) == expected_peer]
            if expected_peer and positions.get(slot) == expected_peer else [])
    t = T[8]
    if role in {"MID", "OFFLANE"} and len(peer) == 1 and duration >= t["min_duration"] \
            and not _conflict(quarantined, {slot, peer[0]}, {"net_worth"}):
        enemy10, enemy20 = _point(features[peer[0]], "net_worth", 600), _point(features[peer[0]], "net_worth", 1200)
        if nw10 is not None and nw20 is not None and enemy10 is not None and enemy20 is not None:
            check(8, {"net_worth_gap_at_10": nw10 - enemy10, "net_worth_gap_at_20": nw20 - enemy20},
                  nw10 - enemy10 <= t["gap_at_600_max"] and nw20 - enemy20 >= t["gap_at_1200_min"])
    deaths = _value(player, "deaths")
    t = T[10]
    if duration >= t["min_duration"] and not _conflict(quarantined, {slot}, {"net_worth", "deaths"}):
        if nw10 is not None and nw20 is not None and deaths is not None:
            check(10, {"net_worth_gain_10_to_20": nw20 - nw10, "deaths": deaths},
                  nw20 - nw10 >= t["gain_600_to_1200_min"] and deaths <= t["deaths_max"])
    tower = _value(player, "tower_damage")
    team_towers = [_value(features[s], "tower_damage") for s in allies]
    tower_total = sum(v for v in team_towers if v is not None) if all(v is not None for v in team_towers) else 0
    tower_share = tower / tower_total if tower is not None and tower_total > 0 else None
    t = T[11]
    if role == "MID" and len(peer) == 1 and not _conflict(quarantined, allies | {peer[0]}, {"tower_damage", "net_worth"}):
        enemy10 = _point(features[peer[0]], "net_worth", 600)
        if nw10 is not None and enemy10 is not None and tower is not None and tower_share is not None:
            check(11, {"net_worth_lead_at_10": nw10 - enemy10, "tower_damage": tower,
                       "team_tower_damage_share": tower_share},
                  nw10 - enemy10 >= t["lead_at_600_min"] and tower >= t["tower_damage_min"]
                  and tower_share >= t["tower_share_min"])

    kills, assists = _value(player, "kills"), _value(player, "assists")
    team_kills = [_value(features[s], "kills") for s in allies]
    team_kill_total = sum(k for k in team_kills if k is not None) if all(k is not None for k in team_kills) else 0
    involvement = ((kills + assists) / team_kill_total
                   if kills is not None and assists is not None and team_kill_total >= T[13]["team_kills_min"] else None)
    if not _conflict(quarantined, allies, {"kills", "assists", "deaths"}):
        check(13, {"kills": kills, "assists": assists, "deaths": deaths,
                   "team_kills": team_kill_total, "kill_involvement": involvement}
              if involvement is not None and deaths is not None else None,
              involvement is not None and deaths is not None and involvement >= T[13]["involvement_min"]
              and deaths <= T[13]["deaths_max"])
        check(14, {"assists": assists, "deaths": deaths} if None not in {assists, deaths} else None,
              assists is not None and deaths is not None and deaths <= T[14]["deaths_max"]
              and assists >= T[14]["assists_min"])
        check(15, {"kills": kills, "deaths": deaths} if None not in {kills, deaths} else None,
              kills is not None and deaths is not None and deaths <= T[15]["deaths_max"]
              and kills >= T[15]["kills_min"])

    events = player.get("events", {})
    source = player.get("achievement_source", {})
    kill_events = source.get("hero_kill_times") if isinstance(source, dict) else None
    death_intervals = events.get("dead_intervals") if isinstance(events, dict) else None
    if isinstance(kill_events, list) and all(type(t_) is int for t_ in kill_events) and not _conflict(quarantined, {slot}, {"events", "kills"}):
        n, window = T[17]["kills"], T[17]["window_seconds"]
        times = sorted(x for x in kill_events if 0 <= x <= duration)
        windows = [(times[i], times[i + n - 1]) for i in range(len(times) - n + 1)
                   if times[i + n - 1] - times[i] <= window]
        check(17, {"first_kill_seconds": windows[0][0], "fifth_kill_seconds": windows[0][1]}
              if windows else {"timed_kill_count": len(times)}, bool(windows))
        if isinstance(death_intervals, list) and events.get("dead_intervals_complete") is True:
            t = T[18]
            early = [x for x in times if x < t["before_seconds"]]
            early_deaths = sum(1 for e in death_intervals if 0 <= e["start"] < t["before_seconds"])
            check(18, {"kills_before_10": len(early), "deaths_before_10": early_deaths},
                  len(early) >= t["kills_min"] and early_deaths <= t["deaths_max"])

    segments = core_fights.get("segments") if core_fights and core_fights.get("state") == "AVAILABLE" else None
    if isinstance(segments, list):
        t = T[20]
        check(20, {"fight": next((s for s in segments if s["player_kills"] >= t["player_kills_min"]
                                  and s["player_deaths"] <= t["player_deaths_max"]), None)},
              any(s["player_kills"] >= t["player_kills_min"] and s["player_deaths"] <= t["player_deaths_max"]
                  for s in segments))
        t = T[22]
        strong = sorted((s for s in segments if s["player_damage"] >= t["player_damage_min"]
                         and s["damage_share"] is not None and s["damage_share"] >= t["damage_share_min"]),
                        key=lambda s: (s["end_seconds"], s["start_seconds"]))
        pair = next(((a, b) for i, a in enumerate(strong) for b in strong[i + 1:]
                     if a["end_seconds"] <= b["start_seconds"]), None)
        check(22, {"fights": list(pair)} if pair else {"qualifying_fights": len(strong)}, pair is not None)
        t = T[23]
        clean = next((s for s in segments if s["enemy_hero_deaths"] >= t["enemy_deaths_min"]
                      and s["allied_hero_deaths"] <= t["allied_deaths_max"]
                      and s["player_damage"] >= t["player_damage_min"]), None)
        check(23, {"fight": clean} if clean else {"detected_fights": len(segments)}, clean is not None)
        advantage = features[slot].get("match", {}).get("radiant_gold_advantage")
        if gold_advantage_valid(advantage, duration):
            t = T[25]
            behind = []
            for fight in segments:
                checkpoints = [int(k) for k in advantage if int(k) < fight["start_seconds"]]
                second = max(checkpoints) if checkpoints else None
                value = advantage.get(str(second)) if second is not None else None
                team_gap = (value if slot < 5 else -value) if type(value) is int else None
                if (team_gap is not None and team_gap <= t["team_gold_gap_max"]
                        and fight["player_damage"] >= t["player_damage_min"]
                        and fight["damage_share"] is not None and fight["damage_share"] >= t["damage_share_min"]
                        and fight["death_trade"] == "FAVORABLE"):
                    behind.append({"gold_checkpoint_seconds": second, "team_gold_gap": team_gap, "fight": fight})
            check(25, behind[0] if behind else {"detected_fights": len(segments)}, bool(behind))

    observer_kills = source.get("observer_kills") if isinstance(source, dict) else None
    observers = events.get("wards") if isinstance(events, dict) else None
    if isinstance(observers, list) and type(observer_kills) is int and not _conflict(quarantined, {slot}, {"obs_log", "observer_kills"}):
        placed = sum(e.get("type") == "OBSERVER" for e in observers)
        check(37, {"observers_placed": placed, "credited_observer_kills": observer_kills},
              placed >= T[37]["observers_placed_min"] and observer_kills >= T[37]["observer_kills_min"])
    stacks = _point(player, "camps_stacked", 1200)
    if stacks is not None and involvement is not None and not _conflict(quarantined, allies, {"camps_stacked", "kills", "assists"}):
        check(41, {"stacks_at_20": stacks, "kill_involvement": involvement,
                   "team_kills": team_kill_total},
              stacks >= T[41]["stacks_at_1200_min"] and involvement >= T[41]["involvement_min"])
    if involvement is not None and type(observer_kills) is int and not _conflict(quarantined, allies, {"kills", "assists", "observer_kills"}):
        check(42, {"kill_involvement": involvement, "team_kills": team_kill_total,
                   "credited_observer_kills": observer_kills},
              involvement >= T[42]["involvement_min"] and observer_kills >= T[42]["observer_kills_min"])
    if tower_share is not None and tower is not None and not _conflict(quarantined, allies, {"tower_damage", "deaths"}):
        check(44, {"tower_damage": tower, "team_tower_damage_share": tower_share},
              tower >= T[44]["tower_damage_min"] and tower_share >= T[44]["tower_share_min"])
        check(45, {"tower_damage": tower, "team_tower_damage_share": tower_share,
                   "deaths": deaths} if deaths is not None else None,
              deaths is not None and deaths <= T[45]["deaths_max"] and tower_share >= T[45]["tower_share_min"])
    healing = _value(player, "hero_healing")
    if healing is not None and assists is not None and not _conflict(quarantined, {slot}, {"hero_healing", "assists"}):
        check(49, {"hero_healing": healing, "assists": assists},
              healing >= T[49]["hero_healing_min"] and assists >= T[49]["assists_min"])
    disable = source.get("disable_seconds") if isinstance(source, dict) else None
    if type(disable) in {int, float} and assists is not None and not _conflict(quarantined, {slot}, {"stuns", "assists"}):
        check(50, {"disable_seconds": disable, "assists": assists},
              cast(float, disable) >= T[50]["disable_seconds_min"] and assists >= T[50]["assists_min"])

    # Hero Specialist counts one matching non-Common feat per distinct prior match.
    bases = {award["id"] for award in awards} & repeatable - {4, 30}
    repeats = {ident: 1 + sum(row["hero_id"] == hero_id and
               ident in {a["id"] for a in row["result"].get("achievements", {}).get("awards", [])}
               for row in prior) for ident in bases}
    best = max(repeats.values(), default=0)
    target = T[30]["distinct_matches"]
    result["progress"]["30"] = {"same_hero_feat_matches": best, "target": target}
    check(30, {"hero_id": hero_id, "feat_id": min((ident for ident, count in repeats.items() if count >= target), default=0),
               "distinct_matches": best} if len(prior) >= target - 1 else None, best >= target)

    # Say why a role-eligible badge could not be judged, instead of leaving a silent gap.
    for ident in IDS:
        if ident in evaluable or role not in ROLES.get(ident, {"CARRY", "MID", "OFFLANE", "SUPPORT"}):
            continue
        reason = ("INSUFFICIENT_HISTORY" if ident in {1, 2, 4, 30} else
                  "MATCH_TOO_SHORT" if ident in {6, 8, 10} and duration < T[ident]["min_duration"] else
                  "EVIDENCE_MISSING")
        result["unavailable"].append({"id": ident, "reason": reason})
    return result

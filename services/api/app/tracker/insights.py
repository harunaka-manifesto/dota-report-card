"""Deterministic post-match insight primitives, versioned by the frozen V1 contract."""

from __future__ import annotations

import math
import statistics
from itertools import pairwise
from typing import Any, TypedDict, cast

CONTRACT_VERSION = "post-match-insights 1.0.0"
TIER_B_VERSION = "tier-b-match-shape 2.0"
LEAVERS = frozenset(
    {
        "ABANDONED",
        "AFK",
        "DISCONNECTED_TOO_LONG",
        "NEVER_CONNECTED",
        "NEVER_CONNECTED_TOO_LONG",
        "FAILED_TO_READY_UP",
        "DECLINED_READY_UP",
    }
)
STORY = (
    "COMEBACK_WIN",
    "LOST_FROM_AHEAD",
    "CLOSE_MOST_OF_GAME",
    "EVEN_THEN_SEPARATED",
    "LEAD_FLIP",
    "LEAD_ERODED",
    "DEFICIT_RECOVERED",
    "LATE_REVERSAL",
)
TIE_ORDER = (
    "COMEBACK_WIN",
    "LOST_FROM_AHEAD",
    "EVEN_THEN_SEPARATED",
    "OWN_LANE_VS_USUAL",
    "ENEMY_SMOKE_VOLUME",
    "ENEMY_STACKING",
    "LEAD_ERODED",
    "OWN_ITEM_VS_HISTORY",
    "VISION_QUICK_CLEARS",
    "CLOSE_MOST_OF_GAME",
    "LEAD_FLIP",
    "DEFICIT_RECOVERED",
    "ENEMY_EARLY_RICH",
    "OPP_START_VS_HISTORY",
    "LATE_REVERSAL",
    "ENEMY_EARLY_ITEM",
    "VISION_REGION_SWEEP",
)
OWN_ITEMS = (
    ("item_black_king_bar", "Black King Bar"),
    ("item_blink", "Blink Dagger"),
    ("item_radiance", "Radiance"),
    ("item_hand_of_midas", "Hand of Midas"),
    ("item_manta", "Manta Style"),
    ("item_desolator", "Desolator"),
    ("item_bfury", "Battle Fury"),
    ("item_maelstrom", "Maelstrom"),
    ("item_ultimate_scepter", "Aghanim's Scepter"),
    ("item_orchid", "Orchid Malevolence"),
)
ENEMY_ITEMS = (
    ("item_black_king_bar", "Black King Bar", (1288, 639), (1718, 930)),
    ("item_blink", "Blink Dagger", (593, 267), (879, 450)),
    ("item_manta", "Manta Style", (936, 462), (1372, 689)),
    ("item_bfury", "Battle Fury", (721, 348), (945, 498)),
    ("item_radiance", "Radiance", (826, 391), (1079, 558)),
    ("item_desolator", "Desolator", (838, 389), (1280, 632)),
    ("item_maelstrom", "Maelstrom", (669, 307), (915, 470)),
    ("item_orchid", "Orchid Malevolence", (761, 363), (1330, 662)),
)
CLASS1 = frozenset({"COMEBACK_WIN", "LOST_FROM_AHEAD"})
CLASS3 = frozenset({"ENEMY_EARLY_ITEM", "VISION_REGION_SWEEP"})
PHASE_EDGES = {"STANDARD": (20, 30, 40), "TURBO": (14, 20, 26)}
START = {"STANDARD": 10, "TURBO": 8}
REF = {
    "STANDARD": (
        (0.0567, 0.0637, 0.072, 0.0865, 0.0943, 0.1052, 0.1335, 0.1563, 0.1861),
        (0.0564, 0.0653, 0.0732, 0.092, 0.1032, 0.1162, 0.1507, 0.1803, 0.2163),
        (0.0499, 0.0568, 0.0635, 0.081, 0.0914, 0.1026, 0.1258, 0.1429, 0.1706),
        (0.0365, 0.0409, 0.0463, 0.0575, 0.0641, 0.0693, 0.0904, 0.1073, 0.1261),
    ),
    "TURBO": (
        (0.0567, 0.0649, 0.0726, 0.0895, 0.1008, 0.1125, 0.1394, 0.1638, 0.1913),
        (0.059, 0.0657, 0.0743, 0.0898, 0.0994, 0.1119, 0.1442, 0.1687, 0.1986),
        (0.0454, 0.0522, 0.0591, 0.0738, 0.0798, 0.0881, 0.1119, 0.131, 0.1448),
        (0.0365, 0.0407, 0.0462, 0.0545, 0.0635, 0.069, 0.095, 0.1054, 0.1207),
    ),
}
PCTS = {45: 0, 50: 1, 55: 2, 65: 3, 70: 4, 75: 5, 85: 6, 90: 7, 95: 8}


class IdentifiedClear(TypedDict):
    time: int
    placed_at: int
    life: int
    x: int
    y: int
    region: str
    match_tier: str


def _players(match: dict[str, Any]) -> list[dict[str, Any]] | None:
    value = match.get("players")
    return value if isinstance(value, list) and all(isinstance(p, dict) for p in value) else None


def global_ineligibility(match: dict[str, Any]) -> str | None:
    bucket, duration, players = match.get("bucket"), match.get("duration_seconds"), _players(match)
    if bucket not in START:
        return "MODE"
    if (
        type(match.get("num_human_players")) is not int
        or match["num_human_players"] != 10
        or players is None
        or len(players) != 10
    ):
        return "ROSTER"
    if type(duration) is not int or duration < 600:
        return "DURATION"
    teams: dict[str, list[str]] = {"RADIANT": [], "DIRE": []}
    for p in players:
        team, position = p.get("team"), p.get("position")
        if team not in teams or position not in {f"POSITION_{i}" for i in range(1, 6)}:
            return "POSITIONS"
        teams[team].append(position)
        stats = p.get("stats")
        nw = stats.get("networthPerMinute") if isinstance(stats, dict) else None
        if not isinstance(nw, list) or not nw:
            return "NET_WORTH"
        leaver = p.get("leaverStatus")
        if leaver in LEAVERS:
            return "LEAVER"
        if leaver not in {"NONE", None}:
            return "LEAVER_EVIDENCE"
        if leaver is None:
            return "LEAVER_EVIDENCE"
    if any(
        sorted(positions) != [f"POSITION_{i}" for i in range(1, 6)] for positions in teams.values()
    ):
        return "POSITIONS"
    return None


def feeding_guard(match: dict[str, Any]) -> bool:
    players = _players(match) or []
    cutoff = 600 if match.get("bucket") == "STANDARD" else 480
    for player in players:
        deaths = player.get("deathEvents")
        if deaths is None:
            continue
        if not isinstance(deaths, list):
            return True
        early = 0
        for death in deaths:
            if not isinstance(death, dict) or type(death.get("time")) is not int:
                return True
            early += death["time"] < cutoff
        if early >= 8:
            return True
    return False


def _median(values: list[float]) -> float:
    return statistics.median(values)


def _runs(state: list[int], minimum: int) -> list[tuple[int, int, int]]:
    out, i = [], 0
    while i < len(state):
        j = i
        while j + 1 < len(state) and state[j + 1] == state[i]:
            j += 1
        if state[i] and j - i + 1 >= minimum:
            out.append((state[i], i, j))
        i = j + 1
    return out


def _structure_events(match: dict[str, Any]) -> list[dict[str, Any]] | None:
    rows = match.get("towerDeaths")
    if not isinstance(rows, list):
        return None
    result = []
    for row in rows:
        if not isinstance(row, dict) or type(row.get("time")) is not int:
            return None
        name = row.get("npcName", row.get("npcId"))
        kind = row.get("kind")
        if (
            kind in {"tower", "barracks"}
            or isinstance(name, str)
            and ("tower" in name.lower() or "rax" in name.lower() or "barracks" in name.lower())
        ):
            if type(row.get("isRadiant")) is not bool:
                return None
            result.append({"time": row["time"], "owner": "RADIANT" if row["isRadiant"] else "DIRE"})
        elif isinstance(name, str) and any(
            word in name.lower() for word in ("fort", "filler", "ancient", "shrine")
        ):
            continue
        else:
            # ponytail: unknown npc ids cannot distinguish towers from excluded structures; add a frozen NPC map when this blocks enough matches.
            return None
    return result


def _structures(match: dict[str, Any], team: str, start: int, end: int) -> int | None:
    events = _structure_events(match)
    if events is None:
        return None
    return sum(
        -1 if event["owner"] == team else 1 for event in events if start <= event["time"] < end
    )


def _analyze(
    match: dict[str, Any],
    team: str,
    R: list[float],
    L: list[float],
    *,
    p: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bucket, duration = match["bucket"], match["duration_seconds"]
    p = {
        "start_shift": 0,
        "end_excl": 3,
        "close_p": 50,
        "edge_p": 70,
        "strong_p": 90,
        "run": 3,
        "os_share": 0.70,
        "se_share": 0.50,
        "ets_close": 0.65,
        "ets_final": 0.60,
        "erosion": 0.50,
        "ct_close": 0.60,
        "se_lean": 0.80,
        "ct_gold": 7500,
        "le_gold_floor": {"STANDARD": 5000, "TURBO": 8000},
        **(p or {}),
    }
    s = START[bucket] + p["start_shift"]
    e = min(len(R) - 1, math.floor((duration - p["end_excl"] * 60) / 60))
    n = e - s + 1
    if n < 9:
        return {"label": "SHORT_WINDOW", "S": s, "E": e, "n": n, "runs": [], "detail": {}}
    # Centered median, with the curve truncated at E.
    smooth = [_median(R[max(0, i - 1) : min(e + 1, i + 2)]) for i in range(e + 1)]
    a = smooth[s : e + 1]
    bins = [sum(edge <= s + i for edge in PHASE_EDGES[bucket]) for i in range(n)]
    table = REF[bucket]
    c = [table[b][PCTS[p["close_p"]]] for b in bins]
    edge = [table[b][PCTS[p["edge_p"]]] for b in bins]
    strong = [table[b][PCTS[p["strong_p"]]] for b in bins]
    state = [1 if v >= edge[i] else -1 if v <= -edge[i] else 0 for i, v in enumerate(a)]
    runs = _runs(state, p["run"])
    rs = {side: [r for r in runs if r[0] == side] for side in (1, -1)}
    inrun = {
        side: {i for side2, a0, b0 in runs if side2 == side for i in range(a0, b0 + 1)}
        for side in (1, -1)
    }
    close = [abs(v) <= c[i] for i, v in enumerate(a)]
    close_share = sum(close) / n
    t3, half, h = max(1, n // 3), n // 2, math.ceil(2 * n / 3)
    absL = L[s : e + 1]
    msg = max(
        (min(abs(absL[i]), abs(absL[i + 1]), abs(absL[i + 2])) for i in range(n - 2)), default=0
    )
    net = _structures(match, team, s * 60, (e + 1) * 60)
    # absolute argmax preserves the first peak on ties.
    detail: dict[str, Any] = {
        "close_share": close_share,
        "latest_close_minute": s + max((i for i, v in enumerate(close) if v), default=-1)
        if any(close)
        else None,
        "msg": msg,
        "runs": [(side, s + a0, s + b0) for side, a0, b0 in runs],
        "net_structures": net,
    }
    labels: dict[str, tuple[str, int]] = {}
    for side in (1, -1):
        # Even then separated, thirds path.
        sep = next((r for r in rs[side] if r[1] >= 0.30 * n), None)
        if sep and sum(close[:t3]) / t3 >= p["ets_close"]:
            earlier = [r for r in runs if r[1] < sep[1]]
            final = sum(i in inrun[side] for i in range(n - t3, n)) / t3
            if (
                not earlier
                and final >= p["ets_final"]
                and not [r for r in rs[-side] if r[1] >= sep[1]]
            ):
                labels["ETS"] = ("ETS_FOR" if side > 0 else "ETS_AGAINST", side)
        # LE / DR
        early = [r for r in rs[side] if r[1] < h]
        if early and not rs[-side]:
            ref = max(side * v for v in a[:h])
            late = _median([side * v for v in a[-3:]])
            pk = max(range(h), key=lambda i: side * L[s + i])
            gold_peak, gold_late = side * L[s + pk], _median([side * v for v in L[e - 2 : e + 1]])
            gold_erosion = (gold_peak - gold_late) / gold_peak if gold_peak else -math.inf
            floor = p["le_gold_floor"][bucket]
            if (
                ref > 0
                and (ref - late) / ref >= p["erosion"]
                and gold_peak > 0
                and gold_erosion >= p["erosion"]
                and gold_peak >= floor
            ):
                labels["LE" if side > 0 else "DR"] = ("LE" if side > 0 else "DR", side)
                detail.update(
                    ref=ref,
                    late=late,
                    gold_peak=gold_peak,
                    gold_late=gold_late,
                    gold_erosion=gold_erosion,
                    peak_minute=s + pk,
                )
        # One-sided.
        share = len(inrun[side]) / n
        strong_minutes = max(
            (
                b0 - a0 + 1
                for a0 in range(n)
                for b0 in range(a0, n)
                if all(side * a[i] >= strong[i] for i in range(a0, b0 + 1))
            ),
            default=0,
        )
        if (
            rs[side]
            and share >= p["os_share"]
            and rs[side][0][1] <= 0.33 * n
            and not rs[-side]
            and (strong_minutes >= 3 or net is not None and side * net >= 3)
        ):
            labels.setdefault("OS", (f"OS_{'FOR' if side > 0 else 'AGAINST'}", side))
        med_first, med_second = _median(a[:half]), _median(a[half:])
        if (
            share >= p["se_share"]
            and side * med_first > 0
            and side * med_second > 0
            and not rs[-side]
        ):
            labels.setdefault("SE", (f"SE_{'FOR' if side > 0 else 'AGAINST'}", side))
        elif (
            not rs[-side]
            and sum(side * v > 0 for v in a) / n >= p["se_lean"]
            and side * _median(a) >= _median(c)
            and side * med_first > 0
            and side * med_second > 0
        ):
            labels.setdefault("SE", (f"SE_{'FOR' if side > 0 else 'AGAINST'}", side))
    if rs[1] and rs[-1]:
        labels["SWAP"] = (f"SWAP_{'FOR' if runs[-1][0] > 0 else 'AGAINST'}", runs[-1][0])
    if not runs and close_share >= p["ct_close"] and msg < p["ct_gold"]:
        labels["CT"] = ("CT", 0)
    for key in ("ETS", "LE", "DR", "OS", "SE", "SWAP", "CT"):
        if key in labels:
            detail["label"] = labels[key][0]
            if key == "ETS":
                side = labels[key][1]
                sep = next(r for r in rs[side] if r[1] >= 0.30 * n)
                detail.update(
                    sep_minute=s + sep[1],
                    lead_at_separation=L[s + sep[1]],
                    lead_at_window_end=L[e],
                    pre_max=max(
                        (abs(L[t]) for t in range(s, max(s, s + sep[1] - 3) + 1)), default=0
                    ),
                )
            if key == "LE":
                detail["label"] = "LE"
            return {
                "label": detail["label"],
                "S": s,
                "E": e,
                "n": n,
                "runs": detail["runs"],
                "detail": detail,
            }
    return {"label": "UNCLEAR", "S": s, "E": e, "n": n, "runs": detail["runs"], "detail": detail}


def classify_tier_b(match: dict[str, Any], team: str) -> dict[str, Any]:
    """Frozen sign-symmetric classifier on stats-only team net-worth curves."""
    if team not in {"RADIANT", "DIRE"}:
        raise ValueError("team must be RADIANT or DIRE")
    players = _players(match) or []
    curves = []
    for player in players:
        stats = player.get("stats")
        values = stats.get("networthPerMinute") if isinstance(stats, dict) else None
        if not isinstance(values, list) or any(type(v) is not int or v < 0 for v in values):
            raise ValueError("Tier B requires complete non-negative net-worth values")
        curves.append((player.get("team"), values))
    length = min(map(lambda row: len(row[1]), curves), default=0)
    L = [
        sum(v[i] for t, v in curves if t == team) - sum(v[i] for t, v in curves if t != team)
        for i in range(length)
    ]
    total = [sum(v[i] for _, v in curves) for i in range(length)]
    R = [L[i] / total[i] if total[i] else 0.0 for i in range(length)]
    base = _analyze(match, team, R, L)
    if base["label"] == "SHORT_WINDOW":
        return {**base, "confidence": 0.0, "version": TIER_B_VERSION}
    variants: list[dict[str, Any]] = []
    for percentile in ("close_p", "edge_p", "strong_p"):
        for percentile_delta in (-5, 5):
            variants.append(
                {
                    percentile: {"close_p": 50, "edge_p": 70, "strong_p": 90}[percentile]
                    + percentile_delta
                }
            )
    for run_delta in (-1, 1):
        variants.append({"run": 3 + run_delta})
    for field, field_delta in (
        ("os_share", -0.05),
        ("os_share", 0.05),
        ("se_share", -0.05),
        ("se_share", 0.05),
        ("ets_close", -0.05),
        ("ets_close", 0.05),
        ("ets_final", -0.05),
        ("ets_final", 0.05),
        ("erosion", -0.1),
        ("erosion", 0.1),
        ("start_shift", -2),
        ("start_shift", -1),
        ("start_shift", 1),
        ("start_shift", 2),
        ("end_excl", 1),
        ("end_excl", 2),
        ("end_excl", 4),
        ("end_excl", 5),
        ("ct_close", -0.05),
        ("ct_close", 0.05),
        ("se_lean", -0.05),
        ("se_lean", 0.05),
        ("ct_gold", -1000),
        ("ct_gold", 1000),
    ):
        variants.append(
            {
                field: {
                    "os_share": 0.70,
                    "se_share": 0.50,
                    "ets_close": 0.65,
                    "ets_final": 0.60,
                    "erosion": 0.50,
                    "start_shift": 0,
                    "end_excl": 3,
                    "ct_close": 0.60,
                    "se_lean": 0.80,
                    "ct_gold": 7500,
                }[field]
                + field_delta
            }
        )
    for gold_delta in (-1000, 1000):
        variants.append(
            {"le_gold_floor": {"STANDARD": 5000 + gold_delta, "TURBO": 8000 + gold_delta}}
        )
    # end-exclusion perturbations are -2,-1,+1,+2, not shifts in absolute value.
    for index, end_delta in zip(range(22, 26), (-2, -1, 1, 2), strict=True):
        variants[index] = {"end_excl": 3 + end_delta}
    same = sum(
        _analyze(match, team, R, L, p=variant)["label"] == base["label"] for variant in variants
    )
    return {**base, "confidence": same / 34, "version": TIER_B_VERSION}


def severity(value: float, ladder: tuple[float, float, float]) -> tuple[int, float] | None:
    q, s, e = ladder
    if value < q:
        return None
    level = (
        (value - q) / (s - q)
        if value < s
        else 1 + (value - s) / (e - s)
        if value < e
        else min(3, 2 + (value - e) / (e - s))
    )
    level = round(level, 3)
    return (1 if level < 1 else 2 if level < 2 else 3, level)


def rank_class(candidate_id: str) -> int:
    return 1 if candidate_id in CLASS1 else 3 if candidate_id in CLASS3 else 2


def _curves(
    match: dict[str, Any], team: str
) -> tuple[list[int], list[list[int]], list[dict[str, Any]]]:
    players = _players(match) or []
    length = min(len(p["stats"]["networthPerMinute"]) for p in players)
    curves = [p["stats"]["networthPerMinute"][:length] for p in players]
    own = [
        sum(curves[i][minute] for i, p in enumerate(players) if p["team"] == team)
        for minute in range(length)
    ]
    enemy = [
        sum(curves[i][minute] for i, p in enumerate(players) if p["team"] != team)
        for minute in range(length)
    ]
    return [a - b for a, b in zip(own, enemy, strict=True)], curves, players


def _card(
    candidate_id: str,
    tier: str,
    family: str,
    slots: dict[str, Any],
    band_level: tuple[int, float],
    *,
    copy: str,
) -> dict[str, Any]:
    band, level = band_level
    return {
        "candidate_id": candidate_id,
        "tier": tier,
        "family": family,
        "band": band,
        "level": round(level, 3),
        "rank_class": rank_class(candidate_id),
        "slots": slots,
        "enrichments": [],
        "copy": copy,
    }


def _ladder_card(
    candidate_id: str,
    value: float,
    ladder: tuple[float, float, float],
    slots: dict[str, Any],
    *,
    tier: str = "A",
    family: str = "Hidden Enemy Activity",
    copy: str,
) -> dict[str, Any] | None:
    result = severity(value, ladder)
    return _card(candidate_id, tier, family, slots, result, copy=copy) if result else None


def _lead_cards(match: dict[str, Any], team: str, won: bool, L: list[int]) -> list[dict[str, Any]]:
    bucket = match["bucket"]
    core = L[: max(1, len(L) - 3)]
    comeback = (12000, 19500, 31000) if bucket == "STANDARD" else (18300, 23700, 33500)
    threshold = comeback[0]
    cards = []
    if won and core:
        deficit = max(-v for v in core)
        if deficit >= threshold:
            minute = next(i for i, v in enumerate(core) if -v == deficit)
            last = max((i for i, v in enumerate(core) if v < 0), default=None)
            band = severity(deficit, comeback)
            assert band is not None
            cards.append(
                _card(
                    "COMEBACK_WIN",
                    "A",
                    "Match Lead Story",
                    {
                        "deficit": deficit,
                        "deficit_minute": minute,
                        "last_minute_behind": last,
                        "final_lead_sign": (L[-1] > 0) - (L[-1] < 0),
                        "win_time": match.get("end_time"),
                    },
                    band,
                    copy=f"You trailed by {deficit:,} gold at {minute}:00 and won.",
                )
            )
    if not won and core:
        lead = max(core)
        if lead >= threshold:
            minute = core.index(lead)
            band = severity(lead, comeback)
            assert band is not None
            cards.append(
                _card(
                    "LOST_FROM_AHEAD",
                    "A",
                    "Match Lead Story",
                    {
                        "lead": lead,
                        "lead_minute": minute,
                        "final_lead": L[-1],
                    },
                    band,
                    copy=f"Your team led by {lead:,} gold at {minute}:00 and lost.",
                )
            )
    lane_end = 12 if bucket == "STANDARD" else 9
    flip_ladder = (7900, 12100, 21900) if bucket == "STANDARD" else (14200, 19400, 27500)
    sign = [1 if x >= 1500 else -1 if x <= -1500 else 0 for x in core]
    runs = _runs(sign, 3)
    flips = [
        (
            left,
            right,
            min(
                max(abs(v) for v in core[left[1] : left[2] + 1]),
                max(abs(v) for v in core[right[1] : right[2] + 1]),
            ),
        )
        for left, right in pairwise(runs)
        if left[0] != right[0] and right[1] >= lane_end
    ]
    qualified = [row for row in flips if row[2] >= flip_ladder[0]]
    if qualified:
        left, right, magnitude = qualified[-1]
        band = severity(magnitude, flip_ladder)
        assert band is not None
        cards.append(
            _card(
                "LEAD_FLIP",
                "A",
                "Match Lead Story",
                {
                    "direction": "FLIP_FOR" if right[0] > 0 else "FLIP_AGAINST",
                    "peak_before": max(abs(v) for v in core[left[1] : left[2] + 1]),
                    "run_before": (left[1], left[2]),
                    "peak_after": max(abs(v) for v in core[right[1] : right[2] + 1]),
                    "run_after": (right[1], right[2]),
                    "result": "WIN" if won else "LOSS",
                },
                band,
                copy=f"The net-worth lead changed sides during the match; your team {'won' if won else 'lost'}.",
            )
        )
    return cards


def _tier_b_cards(
    match: dict[str, Any], team: str, won: bool, L: list[int], shape: dict[str, Any]
) -> list[dict[str, Any]]:
    bucket, d = match["bucket"], shape["detail"]
    label, n, s, e = shape["label"], shape["n"], shape["S"], shape["E"]
    if (
        label in {"SHORT_WINDOW", "UNCLEAR"}
        or shape["confidence"] < 0.7
        or not isinstance(match.get("towerDeaths"), list)
    ):
        return []
    cards = []
    if label == "CT" and d["close_share"] >= 0.75 and n >= (20 if bucket == "STANDARD" else 16):
        strong = (
            d["close_share"] >= 0.9
            and d["latest_close_minute"] is not None
            and d["latest_close_minute"] >= e - 2
            and n >= (30 if bucket == "STANDARD" else 20)
        )
        level = (
            1 + (d["close_share"] - 0.9) * 5 if strong else (d["close_share"] - 0.75) / 0.15 * 0.99
        )
        band = 2 if strong else 1
        cards.append(
            _card(
                "CLOSE_MOST_OF_GAME",
                "B",
                "Match Lead Story",
                {
                    "window_start": s,
                    "window_end": e,
                    "close_share": d["close_share"],
                    "max_3min_gap": d["msg"],
                    "latest_close_minute": d["latest_close_minute"],
                },
                (band, level),
                copy=f"The net-worth gap stayed within the reference close range for most of {s}:00–{e}:00.",
            )
        )
    if (
        label.startswith("ETS_")
        and won
        and n >= (18 if bucket == "STANDARD" else 20)
        and d["pre_max"] <= 7500
    ):
        strong = d["sep_minute"] >= (30 if bucket == "STANDARD" else 20) and d["pre_max"] <= 5000
        cards.append(
            _card(
                "EVEN_THEN_SEPARATED",
                "B",
                "Match Lead Story",
                {
                    "side": label,
                    "even_until": max(s, d["sep_minute"] - 3),
                    "max_gap_before": d["pre_max"],
                    "separation_minute": d["sep_minute"],
                    "lead_at_separation": d["lead_at_separation"],
                    "lead_at_window_end": d["lead_at_window_end"],
                    "result": "WIN",
                },
                (2, 1.0) if strong else (1, 0.5),
                copy=f"The game stayed within {d['pre_max']:,} gold until {d['sep_minute']}:00; your team won.",
            )
        )
    if label in {"LE", "DR"}:
        side = 1 if label == "LE" else -1
        peak = d["gold_peak"]
        floor = 5000 if bucket == "STANDARD" else 10000
        remaining = side * L[e]
        relevant = L[s : e + 1]
        if (
            peak >= floor
            and d["peak_minute"] >= s + 6
            and -floor <= remaining <= max(0.5 * floor, 0.25 * peak)
            and min(side * v for v in relevant[d["peak_minute"] - s :]) >= -2 * floor
        ):
            erosion = d["gold_erosion"]
            extreme_peak = 15000 if bucket == "STANDARD" else 22000
            strong_peak = 10000 if bucket == "STANDARD" else 15000
            if peak >= extreme_peak and erosion >= 0.90:
                level = (3, 2.0)
            elif peak >= strong_peak and erosion >= 0.75:
                level = (2, 1 + min(0.99, (erosion - 0.75) * 4))
            else:
                level = (1, min(0.99, (erosion - 0.5) * 2))
            candidate = "LEAD_ERODED" if label == "LE" else "DEFICIT_RECOVERED"
            slots = {
                "peak": peak,
                "peak_minute": d["peak_minute"],
                "value_at_window_end": L[e],
                "window_end_minute": e,
                "result": "WIN" if won else "LOSS",
            }
            copy = (
                f"Your {peak:,} gold lead at {d['peak_minute']}:00 was down to {L[e]:,} by {e}:00."
                if label == "LE"
                else f"You cut the enemy lead of {peak:,} gold to {side * L[e]:,} by {e}:00; the enemy {'lost' if won else 'won'}."
            )
            cards.append(_card(candidate, "B", "Match Lead Story", slots, level, copy=copy))
    if won and shape["runs"]:
        last = shape["runs"][-1]
        if last[0] < 0 and last[2] >= s + 0.75 * n - 1:
            run_values = [-L[t] for t in range(last[1], last[2] + 1)]
            peak = max(run_values, default=0)
            floor = 5000 if bucket == "STANDARD" else 8000
            if peak >= floor:
                cards.append(
                    _card(
                        "LATE_REVERSAL",
                        "B",
                        "Match Lead Story",
                        {
                            "run_start": last[1],
                            "run_end": last[2],
                            "max_enemy_lead": peak,
                            "lead_at_window_end": L[e],
                            "win_time": match.get("end_time"),
                        },
                        (2, 1.0)
                        if peak >= (10000 if bucket == "STANDARD" else 15000)
                        else (1, 0.5),
                        copy=f"The enemy led by up to {peak:,} gold until {last[2]}:00; your team won.",
                    )
                )
    for card in cards:
        enrichment = _structure_contradiction(match, team, shape)
        if enrichment:
            card["enrichments"].append(enrichment)
    return cards


def _structure_contradiction(
    match: dict[str, Any], team: str, shape: dict[str, Any]
) -> dict[str, Any] | None:
    events = _structure_events(match)
    if events is None:
        return None
    enemy = "DIRE" if team == "RADIANT" else "RADIANT"
    minimum = 8 if match["bucket"] == "STANDARD" else 5
    runs = shape.get("runs", [])
    for side, start, end in runs:
        leader = team if side > 0 else enemy
        if end - start + 1 >= minimum:
            net = sum(
                -1 if event["owner"] == leader else 1
                for event in events
                if start * 60 <= event["time"] < (end + 1) * 60
            )
            if net == 0:
                return {
                    "kind": "STRUCTURE_CONTRADICTION",
                    "type": "NO_STRUCTURE_CONVERSION",
                    "copy": f"{leader.title()} led for {end - start + 1} minutes ({start}:00–{end}:00) with no net tower or barracks change.",
                }
    for side in (1, -1):
        side_runs = [(start, end) for run_side, start, end in runs if run_side == side]
        if not side_runs:
            continue
        leader = team if side > 0 else enemy
        net = sum(
            (-1 if event["owner"] == leader else 1)
            for event in events
            if any(start * 60 <= event["time"] < (end + 1) * 60 for start, end in side_runs)
        )
        if net <= -2:
            return {
                "kind": "STRUCTURE_CONTRADICTION",
                "type": "STRUCTURE_COUNTERTREND",
                "copy": f"During {leader.title()}'s sustained lead, the other team destroyed at least two more towers or barracks.",
            }
    return None


def _team_cards(match: dict[str, Any], team: str, L: list[int]) -> list[dict[str, Any]]:
    bucket, duration, players = match["bucket"], match["duration_seconds"], _players(match) or []
    cards = []
    teams = {side: [p for p in players if p["team"] == side] for side in ("RADIANT", "DIRE")}
    enemy = "DIRE" if team == "RADIANT" else "RADIANT"
    if (
        bucket == "STANDARD"
        and duration >= 1200
        and all(
            isinstance(p.get("campStack"), list)
            and len(p["campStack"]) >= 20
            and all(type(v) is int and v >= 0 for v in p["campStack"][:20])
            for p in players
        )
    ):
        own = sum(p["campStack"][19] for p in teams[team])
        opposing = sum(p["campStack"][19] for p in teams[enemy])
        if opposing >= 7 and opposing - own >= 4:
            card = _ladder_card(
                "ENEMY_STACKING",
                opposing,
                (7, 9, 13),
                {"enemy": opposing, "own": own},
                copy=f"Their team stacked {opposing} camps by 20:00; yours stacked {own}.",
            )
            if card:
                cards.append(card)
    if bucket == "STANDARD" and all(
        isinstance((p.get("stats") or {}).get("itemUsed"), list)
        and all(
            isinstance(row, dict)
            and type(row.get("itemId")) is int
            and type(row.get("count")) is int
            and row["count"] >= 0
            for row in p["stats"]["itemUsed"]
        )
        for p in players
    ):

        def count(group: list[dict[str, Any]]) -> int:
            return sum(
                row["count"]
                for p in group
                for row in p["stats"]["itemUsed"]
                if row["itemId"] == 188
            )

        own, opposing = count(teams[team]), count(teams[enemy])
        edge = opposing - own
        if opposing >= 4 and edge >= 4 and opposing * 600 / duration >= 1.6:
            card = _ladder_card(
                "ENEMY_SMOKE_VOLUME",
                edge,
                (4, 6, 8),
                {
                    "enemy_uses": opposing,
                    "own_uses": own,
                    "rate": opposing * 600 / duration,
                },
                copy=f"They used Smoke {opposing} times; your team used it {own} times.",
            )
            if card:
                cards.append(card)
    goal = 10000 if bucket == "STANDARD" else 15000
    enemy_times: list[tuple[int, int, int, dict[str, Any]]] = []
    own_times: list[tuple[int, int, int, dict[str, Any]]] = []
    for p in players:
        curve = p["stats"]["networthPerMinute"]
        minute = next((i for i, value in enumerate(curve) if value >= goal), None)
        if minute is not None:
            position = p.get("position")
            position_num = (
                int(position[-1])
                if isinstance(position, str) and position[-1:].isdigit()
                else position
                if type(position) is int
                else None
            )
            hero_id = p.get("heroId")
            if type(position_num) is not int or type(hero_id) is not int:
                continue
            row = (minute, position_num, hero_id, p)
            (own_times if p["team"] == team else enemy_times).append(row)
    if enemy_times and own_times:
        minute, position, hero_id, p = min(enemy_times)
        own_min = min(row[0] for row in own_times)
        gap = own_min - minute
        alchemist = hero_id == 73
        if (
            minute <= (18 if bucket == "STANDARD" else 12)
            and gap >= 3
            and duration / 60 - minute >= 8
            and not alchemist
        ):
            value = min(gap, 12)
            ladder = (3, 5, 7) if bucket == "STANDARD" else (3, 4, 6)
            card = _ladder_card(
                "ENEMY_EARLY_RICH",
                value,
                ladder,
                {
                    "hero": hero_id,
                    "position": position,
                    "minute": minute,
                    "your_team_minute": own_min,
                },
                copy=f"An enemy reached {goal:,} net worth at {minute}:00; your team's first hero reached it at {own_min}:00.",
            )
            if card:
                cards.append(card)
    core_opponents = []
    for player in teams[enemy]:
        position = player.get("position")
        position = (
            int(position[-1]) if isinstance(position, str) and position[-1:].isdigit() else position
        )
        if position in {1, 2, 3}:
            core_opponents.append((position, player))
    if len(core_opponents) == 3 and all(
        isinstance(player.get("itemPurchases"), list) for _, player in core_opponents
    ):
        best = None
        for item, label, standard, turbo in ENEMY_ITEMS:
            p5, typical = standard if bucket == "STANDARD" else turbo
            purchases = []
            for position, player in core_opponents:
                times = [
                    row["time"]
                    for row in player["itemPurchases"]
                    if isinstance(row, dict)
                    and row.get("item") == item
                    and type(row.get("time")) is int
                ]
                if times:
                    purchases.append((min(times), position, player.get("heroId")))
            if not purchases:
                continue
            time, position, hero = min(purchases)
            margin = (p5 - time) / p5
            if best is None or margin > best[0]:
                best = (margin, item, label, time, position, hero, typical)
        if best and best[0] >= 0.10:
            margin, item, label, time, position, hero, typical = best
            card = _ladder_card(
                "ENEMY_EARLY_ITEM",
                margin,
                (0.10, 0.15, 0.22),
                {
                    "item": item,
                    "item_name": label,
                    "time": time,
                    "position": position,
                    "hero": hero,
                    "typical_core_time": typical,
                },
                family="Power Spikes & Item Timings",
                copy=f"Their {label} was bought at {_clock(time)}, about {max(0, round((typical - time) / 60))} minutes earlier than a typical core {label}.",
            )
            if card:
                cards.append(card)
    return cards


def _region(x: int, y: int, side: str) -> str:
    cell = (x // 8, y // 8)
    cells = {
        "RADIANT_BASE": (
            (8, 12),
            (9, 9),
            (9, 10),
            (9, 11),
            (9, 12),
            (10, 9),
            (10, 10),
            (10, 11),
            (10, 12),
            (11, 9),
            (11, 10),
            (11, 11),
            (11, 12),
            (12, 8),
            (12, 9),
            (12, 10),
        ),
        "DIRE_BASE": (
            (19, 19),
            (19, 20),
            (19, 21),
            (19, 22),
            (20, 19),
            (20, 20),
            (20, 21),
            (20, 22),
            (21, 18),
            (21, 19),
            (21, 20),
            (21, 21),
            (21, 22),
            (22, 18),
            (22, 19),
            (22, 20),
            (23, 18),
            (23, 19),
            (23, 20),
        ),
        "DIRE_FOUNTAIN": ((22, 21), (22, 22), (23, 21)),
        "RIVER": (
            (11, 18),
            (12, 18),
            (13, 16),
            (13, 17),
            (14, 16),
            (14, 17),
            (14, 18),
            (17, 14),
            (19, 13),
            (20, 13),
        ),
        "ROSHAN": ((13, 18),),
    }
    label = next((name for name, group in cells.items() if cell in group), None)
    if label and (label.endswith("BASE") or label.endswith("FOUNTAIN")):
        return "OWN_BASE" if label.startswith(side) else "ENEMY_BASE"
    if abs(x + y - 252) <= 10 or label in {"RIVER", "ROSHAN"}:
        return "RIVER"
    radiant_half = x + y < 252
    return "OWN_HALF" if radiant_half == (side == "RADIANT") else "ENEMY_HALF"


def _clock(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


def _vision(
    match: dict[str, Any], team: str, L: list[int]
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    players = _players(match) or []
    enemy = "DIRE" if team == "RADIANT" else "RADIANT"
    if any(not isinstance((p.get("stats") or {}).get("wards"), list) for p in players):
        return [], None
    if any(
        not isinstance((p.get("stats") or {}).get("wardDestruction"), list)
        for p in players
        if p["team"] == enemy
    ):
        return [], None
    own_raw: list[dict[str, Any]] = [
        dict(t0=row.get("time"), x=row.get("x"), y=row.get("y"))
        for p in players
        if p["team"] == team
        for row in p["stats"]["wards"]
        if isinstance(row, dict) and row.get("type") == 0
    ]
    sentries = [
        row
        for p in players
        if p["team"] == enemy
        for row in p["stats"]["wards"]
        if isinstance(row, dict) and row.get("type") == 1
    ]
    clears: list[int] = sorted(
        row["time"]
        for p in players
        if p["team"] == enemy
        for row in p["stats"]["wardDestruction"]
        if isinstance(row, dict) and row.get("isWard") is True and type(row.get("time")) is int
    )
    # Malformed observer rows cannot be interpreted as zero evidence.
    if any(type(w[k]) is not int for w in own_raw for k in ("t0", "x", "y")):
        return [], None
    own_observers = [
        {"t0": cast(int, w["t0"]), "x": cast(int, w["x"]), "y": cast(int, w["y"])} for w in own_raw
    ]
    own_observers.sort(key=lambda w: (w["t0"], w["x"], w["y"]))
    duration = cast(int, match["duration_seconds"])
    taken = set()
    identified: list[IdentifiedClear] = []
    for clear in clears:
        active = [
            i
            for i, w in enumerate(own_observers)
            if i not in taken and w["t0"] <= clear < min(w["t0"] + 360, duration)
        ]
        scored = []
        for i in active:
            w = own_observers[i]
            evidence = [
                s
                for s in sentries
                if type(s.get("time")) is int
                and clear - 90 <= cast(int, s["time"]) <= clear
                and type(s.get("x")) is int
                and type(s.get("y")) is int
                and math.hypot(cast(int, s["x"]) - w["x"], cast(int, s["y"]) - w["y"]) <= 10
            ]
            if evidence:
                scored.append(
                    (
                        min(
                            math.hypot(cast(int, s["x"]) - w["x"], cast(int, s["y"]) - w["y"])
                            for s in evidence
                        ),
                        min(clear - cast(int, s["time"]) for s in evidence),
                        i,
                    )
                )
        scored.sort()
        pick = None
        tier = None
        if len(scored) == 1 or len(scored) >= 2 and scored[0][0] + 3 < scored[1][0]:
            pick, tier = scored[0][2], "A"
        elif len(active) == 1:
            pick, tier = active[0], "C"
        if pick is not None:
            assert tier is not None
            taken.add(pick)
            ward = own_observers[pick]
            identified.append(
                {
                    "time": clear,
                    "placed_at": ward["t0"],
                    "life": clear - ward["t0"],
                    "x": ward["x"],
                    "y": ward["y"],
                    "region": _region(ward["x"], ward["y"], team),
                    "match_tier": tier,
                }
            )
    quick = [w for w in identified if w["life"] <= 90 and w["time"] < duration - 300]
    summary = {
        "placed": len(own_observers),
        "destroyed_total": len(clears),
        "identified": len(identified),
        "quick": len(quick),
        "within_60s": sum(w["life"] <= 60 for w in quick),
        "clears": identified,
    }
    cards = []
    if len(quick) >= 4 and len(own_observers) >= 1 and len(quick) >= 0.25 * len(own_observers):
        card = _ladder_card(
            "VISION_QUICK_CLEARS",
            len(quick),
            (4, 5, 6),
            {
                "count": len(quick),
                "count_within_60s": summary["within_60s"],
                "placed": len(own_observers),
                "destroyed_total": len(clears),
                "lower_bound_flag": True,
            },
            copy=f"At least {len(quick)} of your {len(own_observers)} observers were destroyed within 90 seconds of being placed.",
        )
        if card:
            cards.append(card)
    sweep_candidates = []
    for first in identified:
        group = [
            w
            for w in identified
            if w["region"] == first["region"] and first["time"] <= w["time"] <= first["time"] + 300
        ]
        if len(group) < 3 or first["time"] < 300 or max(w["time"] for w in group) >= duration - 300:
            continue
        minute = min(len(L) - 1, first["time"] // 60)
        if (
            minute < 0
            or abs(L[minute]) >= 10000
            or statistics.median(w["life"] for w in group) > 180
        ):
            continue
        sweep_candidates.append(group)
    sweep = max(sweep_candidates, key=lambda group: (len(group), -group[0]["time"]), default=[])
    if len(sweep) >= 3:
        start, end = sweep[0]["time"], sweep[-1]["time"]
        sentry_count = sum(
            1
            for row in sentries
            if type(row.get("x")) is int
            and type(row.get("y")) is int
            and _region(row["x"], row["y"], team) == sweep[0]["region"]
            and type(row.get("time")) is int
            and start - 90 <= row["time"] <= end
        )
        card = _ladder_card(
            "VISION_REGION_SWEEP",
            len(sweep),
            (3, 4, 5),
            {
                "region": sweep[0]["region"],
                "start": start,
                "end": end,
                "lifetimes_rounded": [round(w["life"] / 10) * 10 for w in sweep],
                "enemy_sentries_in_region": sentry_count or None,
            },
            copy=f"At least {len(sweep)} of your observers in {sweep[0]['region']} were destroyed between {_clock(start)} and {_clock(end)}.",
        )
        if card:
            cards.append(card)
    return cards, summary


def _smoke_enrichment(match: dict[str, Any], team: str, enemy_uses: int) -> dict[str, Any] | None:
    players = _players(match) or []
    enemy = "DIRE" if team == "RADIANT" else "RADIANT"
    smoke_times: list[int] = []
    playback_count = 0
    all_events = []
    for p in players:
        playback = p.get("playbackData")
        events = playback.get("itemUsedEvents", []) if isinstance(playback, dict) else []
        if not isinstance(events, list):
            return None
        all_events.extend(events)
        if p["team"] == enemy:
            matching = [e for e in events if isinstance(e, dict) and e.get("itemId") == 188]
            playback_count += len(matching)
            smoke_times.extend(e["time"] for e in matching if type(e.get("time")) is int)
    if not all_events or playback_count != enemy_uses or len(smoke_times) != playback_count:
        return None
    smoke_times.sort()
    if len(smoke_times) < 3:
        return None
    enemy_heroes = {p.get("heroId") for p in players if p["team"] == enemy}
    kills = []
    confirmed = set()
    for p in players:
        playback = p.get("playbackData")
        death_events = p.get("deathEvents")
        if p["team"] == team and isinstance(death_events, list):
            for row in death_events:
                if (
                    isinstance(row, dict)
                    and row.get("attackerHeroId") in enemy_heroes
                    and type(row.get("time")) is int
                ):
                    kills.append((row["time"], p.get("heroId")))
        if p["team"] == enemy and isinstance(playback, dict):
            for row in playback.get("killEvents", []):
                if isinstance(row, dict) and row.get("isSmoke") is True:
                    confirmed.add((row.get("time"), row.get("targetHeroId")))
    k = f = 0
    for i, time in enumerate(smoke_times):
        end = min(time + 60, smoke_times[i + 1] if i + 1 < len(smoke_times) else time + 60)
        matched = [row for row in kills if time < row[0] <= end]
        if matched:
            k += 1
            if any((t, hero) in confirmed for t, hero in matched):
                f += 1
    return (
        {"kind": "SMOKE_TO_KILLS", "k": k, "n": len(smoke_times)}
        if k >= 3 and k >= 0.70 * len(smoke_times) and f >= 2
        else None
    )


def _candidates(
    match: dict[str, Any], viewer: dict[str, Any], history: dict[str, Any] | None
) -> list[dict[str, Any]]:
    team, won = viewer.get("team"), viewer.get("won")
    if team not in {"RADIANT", "DIRE"} or type(won) is not bool:
        return []
    L, _, _ = _curves(match, team)
    cards = _lead_cards(match, team, won, L)
    cards.extend(_team_cards(match, team, L))
    vision_cards, _ = _vision(match, team, L)
    cards.extend(vision_cards)
    cards.extend(_tier_b_cards(match, team, won, L, classify_tier_b(match, team)))
    smoke = next((card for card in cards if card["candidate_id"] == "ENEMY_SMOKE_VOLUME"), None)
    if smoke:
        enrichment = _smoke_enrichment(match, team, smoke["slots"]["enemy_uses"])
        if enrichment:
            smoke["enrichments"].append(enrichment)
    cards.extend(_history_cards(match, viewer, history))
    _attach_optional_history(match, viewer, history, cards)
    return cards


def _history_window(
    match: dict[str, Any],
    history: dict[str, Any] | None,
    *,
    metric: str,
    role: str | None = None,
    item: str | None = None,
    patch: str | None = None,
) -> list[float]:
    if not isinstance(history, dict) or not isinstance(history.get("observations"), list):
        return []
    start = match.get("startDateTime")
    match_id = match.get("matchId")
    if start is None or type(match_id) is not int:
        return []
    rows = []
    for row in history["observations"]:
        if (
            not isinstance(row, dict)
            or row.get("metric") != metric
            or row.get("bucket") != match.get("bucket")
        ):
            continue
        if role is not None and row.get("role") != role:
            continue
        if item is not None and row.get("item") != item:
            continue
        if patch is not None and row.get("patch") != patch:
            continue
        when = row.get("startDateTime")
        prior_id = row.get("matchId")
        value = row.get("value")
        if (
            when is None
            or type(prior_id) is not int
            or type(value) not in {int, float}
            or not math.isfinite(cast(float, value))
        ):
            continue
        if (when, prior_id) < (start, match_id):
            rows.append((when, prior_id, float(cast(float, value))))
    rows.sort(key=lambda row: (row[0], row[1]))
    return [row[2] for row in rows[-50:]]


def _history_band(count: int, population_extreme: bool) -> tuple[int, float]:
    band = (
        3 if count == 50 and population_extreme else 2 if count == 50 or population_extreme else 1
    )
    return band, round((band - 1) + min(0.99, count / 50), 3)


def _counterpart(
    players: list[dict[str, Any]], viewer: dict[str, Any], role: str
) -> dict[str, Any] | None:
    team = viewer.get("team")
    position = {"CARRY": 3, "MID": 2, "OFFLANE": 1}.get(role)
    lane = viewer.get("lane")
    if (
        position is None
        or team not in {"RADIANT", "DIRE"}
        or lane not in {"MID_LANE", "SAFE_LANE", "OFF_LANE"}
    ):
        return None

    def physical(value: str, side: str) -> str:
        if value == "MID_LANE":
            return "MID"
        if value == "SAFE_LANE":
            return "BOT" if side == "RADIANT" else "TOP"
        return "TOP" if side == "RADIANT" else "BOT"

    own_lane = physical(lane, team)
    enemy = "DIRE" if team == "RADIANT" else "RADIANT"
    def position_number(value: Any) -> int | None:
        if type(value) is int:
            return value
        if isinstance(value, str) and value.startswith("POSITION_"):
            suffix = value.removeprefix("POSITION_")
            return int(suffix) if suffix.isdigit() else None
        return None

    candidates = [
        p
        for p in players
        if p.get("team") == enemy
        and position_number(p.get("position")) == position
        and p.get("lane") in {"MID_LANE", "SAFE_LANE", "OFF_LANE"}
        and physical(p["lane"], enemy) == own_lane
    ]
    return candidates[0] if len(candidates) == 1 else None


def _history_cards(
    match: dict[str, Any], viewer: dict[str, Any], history: dict[str, Any] | None
) -> list[dict[str, Any]]:
    players = _players(match) or []
    slot = viewer.get("player_slot")
    role = viewer.get("effective_role")
    if (
        type(slot) is not int
        or slot not in range(10)
        or role not in {"CARRY", "MID", "OFFLANE", "SUPPORT"}
    ):
        return []
    player = next((p for p in players if p.get("player_slot") == slot), None)
    if player is None:
        return []
    bucket = match["bucket"]
    late = 10 if bucket == "STANDARD" else 8
    margin = 100 if bucket == "STANDARD" else 200
    cards = []
    other = _counterpart(players, viewer, role) if role in {"CARRY", "MID", "OFFLANE"} else None
    if other:
        my_nw = player.get("stats", {}).get("networthPerMinute")
        other_nw = other.get("stats", {}).get("networthPerMinute")
        if (
            isinstance(my_nw, list)
            and isinstance(other_nw, list)
            and len(my_nw) > late
            and len(other_nw) > late
            and type(my_nw[late]) is int
            and type(other_nw[late]) is int
        ):
            value = my_nw[late] - other_nw[late]
            window = _history_window(match, history, metric="LANE_GAP", role=role)
            if len(window) >= 20:
                direction = (
                    "BEST"
                    if value - max(window) >= margin
                    else "WORST"
                    if min(window) - value >= margin
                    else None
                )
                if direction:
                    band = _history_band(
                        len(window), abs(value) >= (2254 if bucket == "STANDARD" else 4449)
                    )
                    previous = max(window) if direction == "BEST" else min(window)
                    cards.append(
                        _card(
                            "OWN_LANE_VS_USUAL",
                            "A",
                            "Lane Story",
                            {
                                "value": value,
                                "direction": direction,
                                "N": len(window),
                                "window_median": statistics.median(window),
                                "previous_record": previous,
                                "counterpart_hero": other.get("heroId"),
                                "counterpart_position": other.get("position"),
                            },
                            band,
                            copy=f"Your lane gap at {_clock(late * 60)} was {value:,}: your {direction.lower()} across your last {len(window)} {bucket.title()} {role.title()} matches.",
                        )
                    )
        last_hits = (other.get("stats") or {}).get("lastHitsPerMinute")
        pos = other.get("position")
        pos = int(pos[-1]) if isinstance(pos, str) and pos[-1:].isdigit() else pos
        if (
            isinstance(last_hits, list)
            and len(last_hits) >= late
            and all(type(v) is int and v >= 0 for v in last_hits[:late])
            and type(pos) is int
        ):
            value = sum(last_hits[:late])
            p90 = {"STANDARD": {3: 60, 2: 63, 1: 53}, "TURBO": {3: 48, 2: 48, 1: 39}}[bucket].get(
                pos
            )
            p95 = {"STANDARD": {3: 64, 2: 70, 1: 57}, "TURBO": {3: 53, 2: 53, 1: 42}}[bucket].get(
                pos
            )
            window = _history_window(match, history, metric="COUNTERPART_CS", role=role)
            if (
                p90 is not None
                and p95 is not None
                and value >= p90
                and len(window) >= 20
                and value > max(window)
            ):
                band = _history_band(len(window), value >= p95)
                cards.append(
                    _card(
                        "OPP_START_VS_HISTORY",
                        "A",
                        "Lane Story",
                        {
                            "counterpart_hero": other.get("heroId"),
                            "counterpart_position": pos,
                            "value": value,
                            "N": len(window),
                            "window_median": statistics.median(window),
                            "previous_high": max(window),
                            "your_lane_diff": None,
                        },
                        band,
                        copy=f"Their hero had {value} last hits by {_clock(late * 60)}: the most an opposing {role.title()} has had against you across your last {len(window)} {bucket.title()} matches.",
                    )
                )
    purchases = player.get("itemPurchases")
    if isinstance(purchases, list) and match.get("major_patch"):
        for item, label in OWN_ITEMS:
            times = [
                row["time"]
                for row in purchases
                if isinstance(row, dict)
                and row.get("item") == item
                and type(row.get("time")) is int
            ]
            if not times:
                continue
            time = min(times)
            window = _history_window(
                match,
                history,
                metric="FIRST_PURCHASE",
                role=role,
                item=item,
                patch=match["major_patch"],
            )
            margin = 60 if bucket == "STANDARD" else 30
            if len(window) < 20 or time > min(window) - margin:
                continue
            extreme = min(window) - time >= (120 if bucket == "STANDARD" else 60)
            band = _history_band(len(window), extreme)
            cards.append(
                _card(
                    "OWN_ITEM_VS_HISTORY",
                    "A",
                    "Power Spikes & Item Timings",
                    {
                        "item": item,
                        "item_name": label,
                        "time": time,
                        "previous_fastest": min(window),
                        "window_median": statistics.median(window),
                        "N": len(window),
                        "hero": player.get("heroId"),
                    },
                    band,
                    copy=f"Your {label} at {_clock(time)} was fastest across your last {len(window)} {bucket.title()} {role.title()} {label} purchases (previous {_clock(int(min(window)))}).",
                )
            )
            break
    return cards


def _attach_optional_history(
    match: dict[str, Any],
    viewer: dict[str, Any],
    history: dict[str, Any] | None,
    cards: list[dict[str, Any]],
) -> None:
    bucket = match.get("bucket")
    metrics = {
        "ENEMY_STACKING": "STACKS",
        "ENEMY_EARLY_RICH": "GOAL_MINUTE",
        "ENEMY_SMOKE_VOLUME": "SMOKE_RATE",
        "ENEMY_EARLY_ITEM": "ENEMY_ITEM_TIME",
    }
    for card in cards:
        metric = metrics.get(card["candidate_id"])
        if metric is None:
            continue
        item = card["slots"].get("item")
        patch = match.get("major_patch") if item else None
        value = card["slots"].get(
            {
                "STACKS": "enemy",
                "GOAL_MINUTE": "minute",
                "SMOKE_RATE": "rate",
                "ENEMY_ITEM_TIME": "time",
            }[metric]
        )
        window = _history_window(match, history, metric=metric, role=None, item=item, patch=patch)
        n = len(window)
        if type(value) not in {int, float} or not isinstance(bucket, str):
            continue
        if n < 10:
            continue
        if n >= 20 and metric in {"STACKS", "GOAL_MINUTE"}:
            record = value > max(window) if metric == "STACKS" else value < min(window)
            if record:
                card["history_line"] = f"A record across your last {n} {bucket.title()} matches."
                continue
        if n >= 20 and metric in {"SMOKE_RATE", "ENEMY_ITEM_TIME"}:
            record = value > max(window) if metric == "SMOKE_RATE" else value < min(window)
            if record:
                card["history_line"] = f"A record across your last {n} {bucket.title()} matches."
                continue
        card["history_line"] = (
            f"The median across your last {n} {bucket.title()} matches was {statistics.median(window):g}."
        )


def select(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    family = [c for c in cards if c.get("candidate_id") in STORY]
    keep = min(family, key=lambda c: STORY.index(c["candidate_id"])) if family else None
    pool = [c for c in cards if c.get("candidate_id") not in STORY] + ([keep] if keep else [])
    tie = {key: i for i, key in enumerate(TIE_ORDER)}
    pool.sort(
        key=lambda c: (
            c.get("rank_class", rank_class(c["candidate_id"])),
            -c["band"],
            -round(c["level"], 3),
            tie.get(c["candidate_id"], len(tie)),
        )
    )
    return pool[:3]


def evaluate(
    match: dict[str, Any],
    viewer: dict[str, Any] | None = None,
    history: dict[str, Any] | None = None,
    *,
    cards: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    reason = global_ineligibility(match)
    if reason is None and any(
        not isinstance(p.get("deathEvents"), list) for p in (_players(match) or [])
    ):
        reason = "FEEDING_EVIDENCE"
    if reason is None and feeding_guard(match):
        reason = "FEEDING"
    if reason:
        return {
            "status": f"NOT_ELIGIBLE({reason})",
            "contract_version": CONTRACT_VERSION,
            "cards": [],
        }
    if cards is None and viewer is not None:
        cards = _candidates(match, viewer, history)
    return {
        "status": "EVALUATED",
        "contract_version": CONTRACT_VERSION,
        "cards": select(cards or []),
    }


def from_provider_snapshot(
    raw: dict[str, Any], provider: str, positions: dict[int, int | str | None]
) -> dict[str, Any]:
    """Adapt retained immutable OpenDota/STRATZ payloads; never performs provider I/O.

    Position values may be 1..5 or POSITION_1..POSITION_5 from the role resolver.
    Trajectories are read from the versioned replay projection. Missing minute points
    truncate every player's curve at the first shared gap instead of being filled.
    """
    from app.tracker.normalization import Provider, opendota_summary, stratz_summary
    from app.tracker.replay import replay_checkpoints

    if provider not in {"opendota", "stratz"}:
        raise ValueError("Unsupported provider")
    summary = opendota_summary(raw) if provider == "opendota" else stratz_summary(raw)
    checkpoint = replay_checkpoints(raw, cast(Provider, provider))
    native_players = raw.get("players")
    if not isinstance(native_players, list):
        raise ValueError("Missing retained source roster")
    raw_by_slot = {}
    for row in native_players:
        native_slot = row.get("player_slot") if provider == "opendota" else row.get("playerSlot")
        slot = (
            native_slot
            if type(native_slot) is int and native_slot < 128
            else native_slot - 123
            if type(native_slot) is int
            else None
        )
        if slot is not None:
            raw_by_slot[slot] = row
    projected = {row["player_slot"]: row for row in checkpoint["players"]}
    players = []
    for source in summary["players"]:
        slot = source["player_slot"]
        native = raw_by_slot[slot]
        replay = projected[slot]["series"]
        nw_points = replay.get("net_worth")
        nw = []
        if isinstance(nw_points, dict):
            minute = 0
            while str(minute * 60) in nw_points and type(nw_points[str(minute * 60)]) is int:
                nw.append(nw_points[str(minute * 60)])
                minute += 1
        if provider == "stratz":
            raw_stats = native.get("stats") if isinstance(native.get("stats"), dict) else {}
            deaths = raw_stats.get("deathEvents")
            leaver = native.get("leaverStatus")
            item_used = raw_stats.get("itemUsed")
            wards = raw_stats.get("wards")
            ward_destruction = raw_stats.get("wardDestruction")
            item_purchases = native.get("itemPurchases")
            playback = native.get("playbackData")
            position_raw = native.get("position")
            lane = native.get("lane")
        else:
            raw_stats = native
            deaths = raw_stats.get("deaths_log")
            leaver = (
                "NONE"
                if raw_stats.get("leaver_status") == 0
                else "UNKNOWN"
                if raw_stats.get("leaver_status") is not None
                else None
            )
            item_used = None
            wards = None
            ward_destruction = None
            playback = None
            item_purchases = (
                [
                    {"item": row.get("key"), "time": row.get("time")}
                    for row in raw_stats.get("purchase_log", [])
                    if isinstance(row, dict)
                    and type(row.get("time")) is int
                    and isinstance(row.get("key"), str)
                ]
                if isinstance(raw_stats.get("purchase_log"), list)
                else None
            )
            position_raw = None
            lane = None
        stack_points = replay.get("camps_stacked")
        stacks = (
            [stack_points.get(str(second)) for second in range(60, 1201, 60)]
            if isinstance(stack_points, dict)
            else None
        )
        last_points = replay.get("last_hits")
        last_hits = None
        if isinstance(last_points, dict) and all(
            str(second) in last_points and type(last_points[str(second)]) is int
            for second in range(60, 601, 60)
        ):
            cumulative = [last_points[str(second)] for second in range(60, 601, 60)]
            last_hits = [
                value - (cumulative[index - 1] if index else 0)
                for index, value in enumerate(cumulative)
            ]
        position = positions.get(slot)
        position = (
            f"POSITION_{position}"
            if type(position) is int and position in range(1, 6)
            else position
        )
        if position is None and position_raw in range(1, 6):
            position = f"POSITION_{position_raw}"
        stats = {"networthPerMinute": nw}
        if last_hits is not None:
            stats["lastHitsPerMinute"] = last_hits
        if stacks is not None and all(type(value) is int for value in stacks):
            stats["campStack"] = stacks
        if isinstance(item_used, list):
            stats["itemUsed"] = item_used
        if isinstance(wards, list):
            stats["wards"] = wards
        if isinstance(ward_destruction, list):
            stats["wardDestruction"] = ward_destruction
        player = {
            "player_slot": slot,
            "team": source["team"],
            "position": position,
            "lane": lane,
            "heroId": source["hero_id"],
            "leaverStatus": leaver,
            "stats": stats,
            "deathEvents": deaths if isinstance(deaths, list) else None,
        }
        if isinstance(item_purchases, list):
            player["itemPurchases"] = item_purchases
        if isinstance(playback, dict):
            player["playbackData"] = playback
        if stacks is not None and all(type(value) is int for value in stacks):
            player["campStack"] = stacks
        players.append(player)
    bucket = summary["mode"]
    lobby = summary["lobby_type"]
    if bucket == "STANDARD" and lobby not in {0, 7}:
        bucket = "UNSUPPORTED"
    if bucket == "STANDARD" and summary["game_mode"] not in {1, 22}:
        bucket = "UNSUPPORTED"
    towers = None
    if provider == "stratz" and isinstance(raw.get("towerDeaths"), list):
        towers = [
            {"time": row.get("time"), "npcId": row.get("npcId"), "isRadiant": row.get("isRadiant")}
            for row in raw["towerDeaths"]
            if isinstance(row, dict)
        ]
    return {
        "bucket": bucket,
        "duration_seconds": summary["duration_seconds"],
        "num_human_players": summary["human_players"],
        "matchId": summary["match_id"],
        "startDateTime": summary["started_at"],
        "radiant_win": summary["radiant_win"],
        "major_patch": raw.get("majorPatch"),
        "players": players,
        "towerDeaths": towers,
    }

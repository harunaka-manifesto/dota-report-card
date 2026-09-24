"""Deterministic post-match insight primitives, versioned by the frozen V1 contract."""

from __future__ import annotations

import math
import statistics
from typing import Any

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


def _structures(match: dict[str, Any], team: str, start: int, end: int) -> int | None:
    rows = match.get("towerDeaths")
    if not isinstance(rows, list):
        return None
    result = 0
    for row in rows:
        if not isinstance(row, dict) or type(row.get("time")) is not int:
            continue
        name = row.get("npcId")
        if not isinstance(name, str) or not (
            "tower" in name.lower() or "rax" in name.lower() or "barracks" in name.lower()
        ):
            continue
        if start <= row["time"] < end and type(row.get("isRadiant")) is bool:
            owner_team = "RADIANT" if row["isRadiant"] else "DIRE"
            result += -1 if owner_team == team else 1
    return result


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


def evaluate(match: dict[str, Any], cards: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    reason = global_ineligibility(match)
    if reason is None and feeding_guard(match):
        reason = "FEEDING"
    if reason:
        return {
            "status": f"NOT_ELIGIBLE({reason})",
            "contract_version": CONTRACT_VERSION,
            "cards": [],
        }
    return {
        "status": "EVALUATED",
        "contract_version": CONTRACT_VERSION,
        "cards": select(cards or []),
    }

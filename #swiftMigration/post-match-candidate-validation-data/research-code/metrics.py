"""Per-viewpoint metric extraction. One row per (match, player viewpoint).
Team-level metrics are included for the viewpoint's side; evaluation dedupes by (match, side)."""
from __future__ import annotations
import json, statistics as st
from primitives import *

CHECK = {"STANDARD": {"early": 5, "late": 10, "lane_end": 12, "econ": 20, "stack": 20, "swing_w": 8, "nw_goal": 10000},
         "TURBO":    {"early": 4, "late": 8,  "lane_end": 9,  "econ": 12, "stack": 15, "swing_w": 5, "nw_goal": 15000}}

def lane_metrics(m, p, rep):
    b = bucket(m); C = CHECK[b]; out = {}
    q, why = counterpart(m, p)
    out["lane_status"] = why or "ok"
    if not q: return out
    out["opp_hero"] = HEROES.get(q["heroId"]); out["opp_pos"] = pos_num(q)
    for lab in ("early", "late"):
        t = C[lab]
        a, o = nw(p, t), nw(q, t)
        out[f"nw_{lab}"] = a; out[f"opp_nw_{lab}"] = o
        out[f"nwdiff_{lab}"] = (a - o) if a is not None and o is not None else None
        ca, co = cs(p, t), cs(q, t)
        out[f"csdiff_{lab}"] = (ca - co) if ca is not None and co is not None else None
        out[f"cs_{lab}"] = ca; out[f"opp_cs_{lab}"] = co
        xa, xo = xp(p, t), xp(q, t)
        out[f"xpdiff_{lab}"] = (xa - xo) if xa is not None and xo is not None else None
    # per-minute diff path for flips
    path = []
    for t in range(1, C["lane_end"] + 1):
        a, o = nw(p, t), nw(q, t)
        if a is None or o is None: break
        path.append(a - o)
    out["nwdiff_path"] = path
    l6a, l6o = level_time(p, 6), level_time(q, 6)
    out["lvl6_diff"] = (l6a - l6o) if l6a is not None and l6o is not None else None   # negative = user earlier
    out["lvl6"] = l6a; out["opp_lvl6"] = l6o
    t_sec = C["late"] * 60
    out["kill_gold_late"] = gold_from_kills_before(p, t_sec); out["opp_kill_gold_late"] = gold_from_kills_before(q, t_sec)
    out["deaths_late"] = deaths_before(p, t_sec); out["opp_deaths_late"] = deaths_before(q, t_sec)
    # first key item race (both players, key items, any)
    fa = first_purchase(p, KEY_ITEM_IDS); fo = first_purchase(q, KEY_ITEM_IDS)
    out["first_key_item"] = fa; out["opp_first_key_item"] = fo
    # same key item race: earliest item both bought
    pa = {}; po = {}
    for t, i in purchases(p):
        if i in KEY_ITEM_IDS: pa.setdefault(i, t)
    for t, i in purchases(q):
        if i in KEY_ITEM_IDS: po.setdefault(i, t)
    common = sorted((min(pa[i], po[i]), i) for i in set(pa) & set(po))
    if common:
        i = common[0][1]; out["same_item_race"] = (ITEMS[i], pa[i], po[i])
    # lane duo (all players in the user's map lane, both teams) — for supports
    ml = map_lane(p)
    if ml:
        mine = [x for x in team(m, p["isRadiant"]) if map_lane(x) == ml]; theirs = [x for x in team(m, not p["isRadiant"]) if map_lane(x) == ml]
        t = C["late"]
        if mine and theirs and all(nw(x, t) is not None for x in mine + theirs):
            out["laneset_sizes"] = (len(mine), len(theirs)); out["laneset_nwdiff_late"] = sum(nw(x, t) for x in mine) - sum(nw(x, t) for x in theirs)
    return out

def turning_metrics(m, side, viewer=None):
    b = bucket(m); C = CHECK[b]; out = {}
    lc = lead_curve(m, side)
    out["lead_len"] = len(lc); out["win"] = (m["didRadiantWin"] == side)
    if len(lc) < C["swing_w"] + 2: return out
    out["lead_max"] = max(lc); out["lead_min"] = min(lc); out["lead_final"] = lc[-1]
    W = C["swing_w"]
    best_adv = min(((lc[t + W] - lc[t], t) for t in range(len(lc) - W)), default=(0, 0))
    best_fav = max(((lc[t + W] - lc[t], t) for t in range(len(lc) - W)), default=(0, 0))
    out["swing_adverse"] = (best_adv[0], best_adv[1], lc[best_adv[1]], lc[best_adv[1] + W])
    out["swing_favourable"] = (best_fav[0], best_fav[1], lc[best_fav[1]], lc[best_fav[1] + W])
    S = structures(m); out["structures"] = S
    def lost_in(t0, t1, owner_side):
        return [s for s in S if t0 * 60 <= s["time"] <= t1 * 60 and s["owner_radiant"] == owner_side and s["kind"] in ("tower", "barracks", "ancient")]
    a = out["swing_adverse"]; f = out["swing_favourable"]
    out["adverse_own_structures_lost"] = len(lost_in(a[1], a[1] + W, side)); out["adverse_enemy_structures_lost"] = len(lost_in(a[1], a[1] + W, not side))
    out["fav_enemy_structures_lost"] = len(lost_in(f[1], f[1] + W, not side)); out["fav_own_structures_lost"] = len(lost_in(f[1], f[1] + W, side))
    deaths = all_deaths(m)
    def deaths_in(t0, t1, victim_side): return sum(1 for d in deaths if t0 * 60 <= d["time"] <= t1 * 60 and d["victim_radiant"] == victim_side)
    out["adverse_own_deaths"] = deaths_in(a[1], a[1] + W, side); out["adverse_enemy_deaths"] = deaths_in(a[1], a[1] + W, not side)
    out["fav_own_deaths"] = deaths_in(f[1], f[1] + W, side); out["fav_enemy_deaths"] = deaths_in(f[1], f[1] + W, not side)
    # lead flips: sustained sign changes with |lead| >= 1500 held >= 3 minutes
    signs = []
    for t, v in enumerate(lc):
        s = 1 if v >= 1500 else (-1 if v <= -1500 else 0)
        signs.append(s)
    runs = []
    cur, start = 0, 0
    for t, s in enumerate(signs + [None]):
        if s != cur:
            if cur != 0 and t - start >= 3: runs.append((cur, start, t - 1))
            cur, start = s, t
    out["sustained_runs"] = runs
    out["sustained_flips"] = sum(1 for x, y in zip(runs, runs[1:]) if x[0] != y[0])
    # stalled advantage: longest stretch with lead >= +stall_thr and <=1 enemy tower/rax lost
    stall_thr = 5000 if b == "STANDARD" else 8000
    best = (0, None)
    t = 0
    while t < len(lc):
        if lc[t] >= stall_thr:
            u = t
            while u + 1 < len(lc) and lc[u + 1] >= stall_thr: u += 1
            dur = u - t + 1
            n = len(lost_in(t, u, not side))
            if dur >= 6 and (best[1] is None or dur > best[0]): best = (dur, (t, u, n, max(lc[t:u + 1])))
            t = u + 1
        else: t += 1
    out["stall"] = best[1]
    # clash → structures
    out["clashes"] = clashes(m)
    conv = []
    for c in out["clashes"]:
        rd, dd = c["radiant_deaths"], c["dire_deaths"]
        if abs(rd - dd) < 2: continue
        loser_radiant = rd > dd
        lost = [s for s in S if c["end"] < s["time"] <= c["end"] + 90 and s["owner_radiant"] == loser_radiant and s["kind"] in ("tower", "barracks", "ancient")]
        if len(lost) >= 2: conv.append((c, loser_radiant == side, len(lost), lost[-1]["time"] - c["end"]))
    out["clash_conversions"] = conv
    out["tormentor_chat"] = None
    return out

def viewer_dead_structures(m, p):
    S = structures(m); side = p["isRadiant"]; n = 0; windows = 0; max_in_one = 0
    for d in p["stats"]["deathEvents"] or []:
        lost = [s for s in S if d["time"] <= s["time"] <= d["time"] + (d.get("timeDead") or 0) and s["owner_radiant"] == side and s["kind"] in ("tower", "barracks", "ancient")]
        n += len(lost); max_in_one = max(max_in_one, len(lost))
    return {"structures_lost_while_dead": n, "max_structures_one_death": max_in_one,
            "time_dead": sum((d.get("timeDead") or 0) for d in p["stats"]["deathEvents"] or [])}

def hidden_metrics(m, side, rep, pb):
    """Metrics about the ENEMY of `side`."""
    b = bucket(m); C = CHECK[b]; out = {}; enemy = not side
    st_t = C["stack"]
    if m["durationSeconds"] >= st_t * 60:
        es = [stacks_by(p, st_t) for p in team(m, enemy)]; os_ = [stacks_by(p, st_t) for p in team(m, side)]
        if None not in es and None not in os_: out["enemy_stacks"] = sum(es); out["own_stacks"] = sum(os_)
    out["enemy_obs"] = observers_placed(m, enemy); out["own_obs"] = observers_placed(m, side)
    out["enemy_obs_killed_our"] = observers_destroyed_by(m, enemy); out["own_obs_killed_their"] = observers_destroyed_by(m, side)
    out["our_obs_destroyed_share"] = out["enemy_obs_killed_our"] / out["own_obs"] if out["own_obs"] else None
    out["enemy_smokes"] = sum(item_uses(p, "item_smoke_of_deceit") for p in team(m, enemy)); out["own_smokes"] = sum(item_uses(p, "item_smoke_of_deceit") for p in team(m, side))
    out["enemy_roshan"] = sum(farm_other_count(p, ROSHAN_NPC) for p in team(m, enemy)); out["own_roshan"] = sum(farm_other_count(p, ROSHAN_NPC) for p in team(m, side))
    out["enemy_tormentor"] = sum(farm_other_count(p, TORMENTOR_NPC) for p in team(m, enemy)); out["own_tormentor"] = sum(farm_other_count(p, TORMENTOR_NPC) for p in team(m, side))
    # enemy economy
    t = C["econ"]
    vals = [(nw(p, t), p) for p in team(m, enemy)]
    if all(v is not None for v, _ in vals):
        tot = sum(v for v, _ in vals); top = max(vals, key=lambda x: x[0])
        out["enemy_top_share"] = top[0] / tot if tot else None; out["enemy_top_hero"] = HEROES.get(top[1]["heroId"]); out["enemy_top_pos"] = pos_num(top[1])
        ov = [nw(p, t) for p in team(m, side)]; out["own_top_share"] = max(ov) / sum(ov) if sum(ov) else None
    goal = C["nw_goal"]
    fast = []
    for p in team(m, enemy):
        a = p["stats"]["networthPerMinute"]; mnt = next((i for i, v in enumerate(a) if v is not None and v >= goal), None)
        if mnt is not None: fast.append((mnt, HEROES.get(p["heroId"]), pos_num(p)))
    out["enemy_fastest_goal"] = min(fast) if fast else None
    ownfast = [next((i for i, v in enumerate(p["stats"]["networthPerMinute"]) if v is not None and v >= goal), None) for p in team(m, side)]
    ownfast = [x for x in ownfast if x is not None]; out["own_fastest_goal"] = min(ownfast) if ownfast else None
    cores = sorted([p for p in team(m, enemy) if pos_num(p) in (1, 2, 3)], key=lambda p: -(p["networth"] or 0))
    if cores:
        js = jungle_share(cores[0]); out["enemy_top_core_jungle_share"] = js; out["enemy_top_core_hero"] = HEROES.get(cores[0]["heroId"])
    # playback-dependent
    if pb:
        slot_side = {p["playerSlot"]: p["isRadiant"] for p in m["players"]}
        smokes = []
        for pp in pb.get("players") or []:
            for e in ((pp.get("playbackData") or {}).get("itemUsedEvents") or []):
                if ITEMS.get(e["itemId"]) == "item_smoke_of_deceit" and slot_side.get(pp["playerSlot"]) == enemy: smokes.append(e["time"])
        if pb.get("players") and any((pp.get("playbackData") or {}).get("itemUsedEvents") is not None for pp in pb["players"]):
            ekills = sorted(k["time"] for p in team(m, enemy) for k in p["stats"]["killEvents"] or [])
            smokes = sorted(set(smokes))
            out["pb_enemy_smokes"] = len(smokes)
            out["pb_enemy_smoke_kills"] = sum(1 for s in smokes if any(s < k <= s + 60 for k in ekills))
        we = ((pb.get("playbackData") or {}).get("wardEvents")) or []
        if we:
            byi = {}
            for w in we: byi.setdefault(w["indexId"], []).append(w)
            short = 0; tot = 0
            for v in byi.values():
                sp = [w for w in v if w["action"] == "SPAWN" and w.get("wardType") == "OBSERVER"]
                if not sp or slot_side.get(sp[0]["fromPlayer"]) != side: continue
                tot += 1
                dp = [w for w in v if w["action"] == "DESPAWN" and w.get("playerDestroyed") is not None]
                if dp and dp[0]["time"] - sp[0]["time"] <= 90: short += 1
            out["pb_own_obs"] = tot; out["pb_own_obs_killed_90s"] = short
        rt = sorted({e["time"] for pp in pb.get("players") or [] for e in ((pp.get("playbackData") or {}).get("goldEvents") or []) if e.get("reason") == "ROSHAN"})
        out["pb_roshan_gold_times"] = rt
    if rep:
        out["tormentor_chat_times"] = [(c["time"], c.get("fromHeroId")) for c in rep.get("chatEvents") or [] if c.get("type") == 117]
    return out

def item_metrics(m, p, rep, pb):
    b = bucket(m); out = {}
    rp = None
    if rep:
        rp = next((x for x in rep.get("players") or [] if x.get("playerSlot") == p["playerSlot"]), None)
    uses = {u["itemId"]: (u.get("count") or 0) for u in p["stats"]["itemUsed"] or []}
    unused = []
    first_buy = {}
    for t, i in purchases(p):
        first_buy.setdefault(i, t)
    final_main = {p.get(f"item{k}Id") for k in range(6)} - {None, 0}
    final_bp = {p.get(f"backpack{k}Id") for k in range(3)} - {None, 0}
    for i, t in first_buy.items():
        if i not in ACTIVE_ITEM_IDS: continue
        remaining = (m["durationSeconds"] - t) / 60
        rec = {"item": ITEMS[i], "bought": t, "remaining_min": round(remaining, 1), "cost": ITEM_COST.get(i), "uses": uses.get(i, 0),
               "final_main": i in final_main, "final_backpack": i in final_bp}
        out.setdefault("active_items", []).append(rec)
        if uses.get(i, 0) > 0: continue
        out.setdefault("unused_active", []).append(rec)
    out["active_bought"] = sum(1 for i in first_buy if i in ACTIVE_ITEM_IDS)
    out["key_first"] = {ITEMS[i]: t for i, t in first_buy.items() if i in KEY_ITEM_IDS}
    # enemy key item earliest per item, and enemy cores' completion times of big items (cost >= 4000)
    enemy = [q for q in m["players"] if q["isRadiant"] != p["isRadiant"]]
    ek = {}
    for q in enemy:
        for t, i in purchases(q):
            if i in KEY_ITEM_IDS and (ITEMS[i] not in ek or t < ek[ITEMS[i]][0]): ek[ITEMS[i]] = (t, HEROES.get(q["heroId"]), pos_num(q))
    out["enemy_key_first"] = ek
    big = sorted((t, HEROES.get(q["heroId"]), ITEMS[i]) for q in enemy if pos_num(q) in (1, 2, 3) for t, i in purchases(q) if ITEM_COST.get(i, 0) >= 4000 and i in KEY_ITEM_IDS)
    out["enemy_big_items"] = big
    if pb:
        pp = next((x for x in pb.get("players") or [] if x.get("playerSlot") == p["playerSlot"]), None)
        iu = ((pp or {}).get("playbackData") or {}).get("itemUsedEvents")
        if iu is not None:
            delays = []
            for i, t in first_buy.items():
                if i in ACTIVE_ITEM_IDS and ITEMS[i] in ("item_black_king_bar", "item_blink", "item_glimmer_cape", "item_force_staff", "item_lotus_orb", "item_manta", "item_satanic"):
                    fu = min((e["time"] for e in iu if e["itemId"] == i and e["time"] >= t), default=None)
                    delays.append((ITEMS[i], t, fu))
            out["pb_first_use"] = delays
    return out

def build_rows(core, rep, pb):
    rows = []; excluded = {}
    for mid, m in core.items():
        ok, why = eligible_match(m)
        if not ok: excluded[mid] = why; continue
        rp = rep.get(mid); pbm = pb.get(mid)
        side_turn = {s: turning_metrics(m, s) for s in (True, False)}
        side_hidden = {s: hidden_metrics(m, s, rp, pbm) for s in (True, False)}
        for p in m["players"]:
            rows.append({"match_id": mid, "start": m["startDateTime"], "bucket": bucket(m), "duration": m["durationSeconds"], "patch": m.get("gameVersionId"),
                         "slot": p["playerSlot"], "side_radiant": p["isRadiant"], "win": p["isVictory"], "pos": pos_num(p), "role": role(p), "hero": HEROES.get(p["heroId"]),
                         "has_reports": rp is not None, "has_playback": pbm is not None,
                         "lane": lane_metrics(m, p, rp), "turn": side_turn[p["isRadiant"]], "dead": viewer_dead_structures(m, p),
                         "hidden": side_hidden[p["isRadiant"]], "items": item_metrics(m, p, rp, pbm)})
    return rows, excluded

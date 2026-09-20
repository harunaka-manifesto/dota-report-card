"""Moderate (sub-Tier-A) factual signals and Phase 11/16 composites, thresholds fitted on DEVELOPMENT matches only.

Every signal is a fact with a percentile position `pp` (0-100, higher = more notable) inside its bucket's development distribution.
Composite renderings use factual connectors only.
"""
import bisect, contextlib, io, json, pickle
from collections import Counter, defaultdict
with contextlib.redirect_stdout(io.StringIO()):
    import evaluate_v2 as E
from primitives import *
from metrics import CHECK
import shape as SH

DEV, HOLD = SH.split()
rows, core = E.rows, E.core
gate = pickle.load(open("tier_a_gate.pkl", "rb")); feed = gate["feed"]
R = [r for r in rows if r["match_id"] not in feed]
def mins(r): return r["duration"] / 60
def fmt(s): return f"{int(s) // 60}:{int(s) % 60:02d}"
def k(g): return f"{'+' if g >= 0 else '-'}{abs(g) / 1000:.1f}k"
def lane_diffs(m, b):
    t = CHECK[b]["late"]; out = {}
    for lane in ("top", "mid", "bot"):
        rad = [p for p in m["players"] if p["isRadiant"] and map_lane(p) == lane]; dire = [p for p in m["players"] if not p["isRadiant"] and map_lane(p) == lane]
        if rad and dire and all(nw(p, t) is not None for p in rad + dire): out[lane] = (sum(nw(p, t) for p in rad) - sum(nw(p, t) for p in dire), len(rad), len(dire))
    return out
LD = {mid: lane_diffs(core[mid], E.bucket(core[mid])) for mid in {r["match_id"] for r in R}}

# ---------------- development distributions ----------------
DV = defaultdict(list); seen_team = set(); seen_match = set()
for r in R:
    if r["match_id"] not in DEV: continue
    b = r["bucket"]; L = r["lane"]; h = r["hidden"]
    if L.get("lane_status") == "ok" and L.get("nwdiff_late") is not None:
        DV[("lane_nw", b, E.rg(r))].append(abs(L["nwdiff_late"]))
        if E.rg(r) == "core" and L.get("csdiff_late") is not None:
            DV[("lane_cs", b)].append(abs(L["csdiff_late"]))
            DV[("pair_nw", b, r["pos"], L["opp_pos"])].append(L["nwdiff_late"]); DV[("pair_cs", b, r["pos"], L["opp_pos"])].append(L["csdiff_late"])
    if r["match_id"] not in seen_match:
        seen_match.add(r["match_id"])
        for lane, (d, a, o) in LD[r["match_id"]].items(): DV[("lanes_abs", b)].append(abs(d))
    tk = (r["match_id"], r["side_radiant"])
    if tk in seen_team: continue
    seen_team.add(tk)
    if "enemy_stacks" in h: DV[("stacks", b)].append(h["enemy_stacks"]); DV[("stackedge", b)].append(h["enemy_stacks"] - h["own_stacks"])
    if h.get("enemy_fastest_goal"): DV[("fast", b)].append(h["enemy_fastest_goal"][0])
    DV[("krate", b)].append(h["enemy_obs_killed_our"] / mins(r) * 10)
    if h["own_obs"] >= 8: DV[("dshare", b)].append(h["our_obs_destroyed_share"] or 0)
    DV[("srate", b)].append(h["enemy_smokes"] / mins(r) * 10)
    for n, (t, hero, pos) in r["items"]["enemy_key_first"].items():
        if n in E.SPIKE_ITEMS and pos in (1, 2, 3): DV[("item", b, n)].append(t)
DV = {kk: sorted(v) for kk, v in DV.items()}
def pp(key_, v, lower_is_notable=False):
    arr = DV.get(key_)
    if not arr: return None
    f = bisect.bisect_right(arr, v) / len(arr) if not lower_is_notable else 1 - bisect.bisect_left(arr, v) / len(arr)
    return round(100 * f, 1)
def q(key_, p):
    arr = DV[key_]; return arr[min(len(arr) - 1, int(round(p / 100 * (len(arr) - 1))))]

# ---------------- signals per viewpoint ----------------
SIG = defaultdict(list); META = {}
for r in R:
    kk = (r["match_id"], r["slot"]); b = r["bucket"]; L = r["lane"]; h = r["hidden"]; C = CHECK[b]
    META[kk] = dict(mid=r["match_id"], slot=r["slot"], side=r["side_radiant"], bucket=b, role=r["role"], hero=r["hero"], win=r["win"], dur=r["duration"],
                    dev=r["match_id"] in DEV)
    add = lambda **x: SIG[kk].append(x)
    # ---- Lane: moderate NW gap + CS gap in same direction (cores)
    if E.rg(r) == "core" and L.get("lane_status") == "ok" and L.get("nwdiff_late") is not None and L.get("csdiff_late") is not None:
        n_, c_ = L["nwdiff_late"], L["csdiff_late"]; pk_ = (b, r["pos"], L["opp_pos"])
        # v2: signed position relative to the same position pairing (an offlaner trailing a safe-lane carry in last hits is normal)
        if len(DV.get(("pair_nw",) + pk_, [])) >= 40:
            pn = pp(("pair_nw",) + pk_, n_); pc = pp(("pair_cs",) + pk_, c_)
            ahead = pn >= 75 and pc >= 75 and n_ > 0 and c_ > 0; behind = pn <= 25 and pc <= 25 and n_ < 0 and c_ < 0
            # v2.1: an offlaner trailing the enemy safe-lane carry reads as an ordinary lane even when beyond the pairing's p25 (rated MISLEADING in review)
            if behind and (r["pos"], L["opp_pos"]) == (3, 1): behind = False
            if (ahead or behind) and abs(n_) >= 500:
                add(id="C_LANE_NW_CS", family="lane", level="counterpart", pp=round(min(pn, pc) if ahead else 100 - max(pn, pc), 1), value=n_, components=["PAIR_NW", "PAIR_CS"],
                    text=f"by {C['late']}:00 you were {k(n_)} net worth and {c_:+d} last hits against {L['opp_hero']} (P{L['opp_pos']})")
    # ---- Lane: your lane vs the other two lanes (Phase 16)
    ml = map_lane(next(p for p in core[r["match_id"]]["players"] if p["playerSlot"] == r["slot"]))
    ld = LD[r["match_id"]]
    if ml in ld and len(ld) == 3:
        sg = 1 if r["side_radiant"] else -1
        mine = sg * ld[ml][0]; others = {ln: sg * d for ln, (d, a, o) in ld.items() if ln != ml}
        floor = q(("lanes_abs", b), 25); pm = pp(("lanes_abs", b), abs(mine))
        if pm >= 50 and all(abs(v) >= floor for v in others.values()) and all((v > 0) != (mine > 0) for v in others.values()):
            add(id="X_LANE_VS_OTHER_LANES", family="lane", level="user_lane", pp=pm, value=mine,
                text=f"at {C['late']}:00 your lane was the only one {'ahead' if mine > 0 else 'behind'} ({k(mine)}); " + ", ".join(f"{ln} {k(v)}" for ln, v in others.items()))
    # ---- Hidden (team level; one copy per viewpoint)
    comps = {}
    if b == "STANDARD" and "enemy_stacks" in h:
        e_, o_ = h["enemy_stacks"], h["own_stacks"]; p1 = pp(("stacks", b), e_); p2 = pp(("stackedge", b), e_ - o_)
        if p1 >= 75 and p2 >= 75 and e_ - o_ >= 4: comps["STACK_MOD"] = (min(p1, p2), f"enemy stacked {e_} camps by {C['stack']}:00 (your team {o_})")
    if h.get("enemy_fastest_goal"):
        mnt, hero, pos = h["enemy_fastest_goal"]; own = h.get("own_fastest_goal"); p_ = pp(("fast", b), mnt, lower_is_notable=True)
        if p_ >= 75 and (own is None or own - mnt >= 3): comps["RICH_MOD"] = (p_, f"{hero} (P{pos}) reached {C['nw_goal']:,} net worth at {mnt}:00 (your team's first at {own}:00)" if own is not None else f"{hero} (P{pos}) reached {C['nw_goal']:,} net worth at {mnt}:00", hero, mnt)
    if h["own_obs"] >= 8:
        kr = h["enemy_obs_killed_our"] / mins(r) * 10; ds = h["our_obs_destroyed_share"] or 0
        pk_, ps_ = pp(("krate", b), kr), pp(("dshare", b), ds)
        if pk_ >= 75 and ds >= 0.45 and h["enemy_obs_killed_our"] >= 4: comps["OBSCLEAR_MOD"] = (min(pk_, ps_), f"the enemy destroyed {h['enemy_obs_killed_our']} of your team's {h['own_obs']} observers ({ds:.0%})")
    sr = h["enemy_smokes"] / mins(r) * 10; p_ = pp(("srate", b), sr)
    if p_ >= 75 and h["enemy_smokes"] >= h["own_smokes"] + 4: comps["SMOKE_MOD"] = (p_, f"the enemy used Smoke {h['enemy_smokes']} times (your team {h['own_smokes']})")
    if h["enemy_roshan"] >= 1 and h["own_roshan"] == 0: comps["BOSS_MOD"] = (60.0, f"the enemy took Roshan {h['enemy_roshan']}x and your team 0x")
    early_items = []
    for n, (t, hero, pos) in r["items"]["enemy_key_first"].items():
        if n in E.SPIKE_ITEMS and pos in (1, 2, 3) and len(DV.get(("item", b, n), [])) >= 30:
            p_ = pp(("item", b, n), t, lower_is_notable=True)
            if p_ >= 75: early_items.append((p_, n, t, hero, pos))
    if early_items:
        best = max(early_items); comps["ITEM_EARLY_MOD"] = (best[0], f"{best[3]} (P{best[4]}) bought {best[1].replace('item_', '').replace('_', ' ').title()} at {fmt(best[2])}", best[3])
    for cid, v in comps.items():
        if cid in ("ITEM_EARLY_MOD", "BOSS_MOD"): continue          # v2: component-only (63% fire / 9x loss-skewed and boring)
        add(id=cid, family="hidden", level="team", pp=v[0], text=v[1])
    if "STACK_MOD" in comps and "RICH_MOD" in comps:
        add(id="C_ECON_STACK_RICH", family="hidden", level="team", pp=min(comps["STACK_MOD"][0], comps["RICH_MOD"][0]), components=["STACK_MOD", "RICH_MOD"],
            text=f"{comps['STACK_MOD'][1]}, while {comps['RICH_MOD'][1]}")
    if "RICH_MOD" in comps and "ITEM_EARLY_MOD" in comps and comps["RICH_MOD"][2] == comps["ITEM_EARLY_MOD"][2]:
        item_t = best[2]; goal_t = comps["RICH_MOD"][3] * 60
        text = (f"{best[3]} (P{best[4]}) bought {best[1].replace('item_', '').replace('_', ' ').title()} at {fmt(item_t)} and {comps['RICH_MOD'][1].split(') ', 1)[1]}" if item_t <= goal_t
                else f"{comps['RICH_MOD'][1]}, then bought {best[1].replace('item_', '').replace('_', ' ').title()} at {fmt(item_t)}")
        add(id="C_SPIKE_RICH_ITEM", family="items", level="team", pp=min(comps["RICH_MOD"][0], comps["ITEM_EARLY_MOD"][0]), components=["RICH_MOD", "ITEM_EARLY_MOD"], text=text)
    hid = [c for c in ("STACK_MOD", "OBSCLEAR_MOD", "SMOKE_MOD", "RICH_MOD") if c in comps]
    if len(hid) >= 2:
        add(id="X_HIDDEN_MULTI", family="hidden", level="team", pp=min(comps[c][0] for c in hid), components=hid, text="; ".join(comps[c][1] for c in hid))
pickle.dump(dict(SIG=dict(SIG), META=META, DV_sizes={str(kk): len(v) for kk, v in DV.items()}), open("signals.pkl", "wb"))
cnt = Counter(s["id"] for v in SIG.values() for s in v)
empty = [kk for kk in META if not [c for c in gate["FIRE"].get(kk, []) if c != "L4*"]]
cnt_e = Counter(s["id"] for kk in empty for s in SIG.get(kk, []))
print("viewpoints", len(META), "tier-A-empty", len(empty))
for sid in sorted(cnt): print(f"{sid:32s} all {100 * cnt[sid] / len(META):5.1f}%  tierA-empty {100 * cnt_e[sid] / len(empty):5.1f}%")

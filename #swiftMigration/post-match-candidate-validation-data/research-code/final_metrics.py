"""Final pass: tuned variants (I4 restricted race, H2/H3 rate-based, H1 Turbo floor, feeding guard),
pool coverage per family, key co-fire pairs, frequency tiers."""
import json, random, collections, statistics as st
from collections import Counter, defaultdict
import evaluate_v2 as E
from primitives import *
from metrics import CHECK
random.seed(11)
rows, core, TH, F, EV, CANDS = E.rows, E.core, E.TH, E.F, E.EV, E.CANDS
def mins(r): return core[r["match_id"]]["durationSeconds"] / 60
def Q(v, q): v = sorted(x for x in v if x is not None); return v[min(len(v)-1, int(round(q*(len(v)-1))))] if v else None
feed = set()
for r in rows:
    m = core[r["match_id"]]; t = CHECK[r["bucket"]]["late"] * 60
    if r["match_id"] not in feed and any(sum(1 for d in p["stats"]["deathEvents"] or [] if d["time"] < t) >= 8 for p in m["players"]): feed.add(r["match_id"])
X = {}
# ---- I4 restricted lane item race: same item is within each player's first 2 key items, both bought before bucket cap
cap = {"STANDARD": 35 * 60, "TURBO": 20 * 60}
race = defaultdict(list)
for r in rows:
    L = r["lane"]
    if E.rg(r) != "core" or L.get("lane_status") != "ok": continue
    m = core[r["match_id"]]; p = next(x for x in m["players"] if x["playerSlot"] == r["slot"])
    q = next(x for x in m["players"] if x["isRadiant"] != p["isRadiant"] and pos_num(x) == COUNTER[pos_num(p)])
    fa = []; fo = []
    for t, i in purchases(p):
        if i in KEY_ITEM_IDS and i not in [x[1] for x in fa]: fa.append((t, i))
    for t, i in purchases(q):
        if i in KEY_ITEM_IDS and i not in [x[1] for x in fo]: fo.append((t, i))
    a2 = {i: t for t, i in fa[:2]}; o2 = {i: t for t, i in fo[:2]}
    common = [(i, a2[i], o2[i]) for i in set(a2) & set(o2) if a2[i] <= cap[r["bucket"]] and o2[i] <= cap[r["bucket"]]]
    if common:
        i, a, o = min(common, key=lambda c: min(c[1], c[2]))
        race[r["bucket"]].append((r, ITEMS[i], a, o))
X["I4r"] = {}
for b, lst in race.items():
    gaps = [abs(a - o) for _, _, a, o in lst]; p75, p90 = Q(gaps, .75), Q(gaps, .9)
    elig_base = sum(1 for r in rows if r["bucket"] == b and E.rg(r) == "core" and r["lane"].get("lane_status") == "ok")
    tuned = [x for x in lst if abs(x[2] - x[3]) >= p90]
    X["I4r"][b] = dict(eligible_pct_of_core=round(100 * len(lst) / elig_base, 1), gap_p75=p75, gap_p90=p90, tuned_pct_of_eligible=round(100 * len(tuned) / len(lst), 1),
                       tuned_pct_of_core=round(100 * len(tuned) / elig_base, 1), items=Counter(x[1] for x in tuned).most_common(6),
                       examples=[f"{r['role']} {r['hero']} vs {r['lane']['opp_hero']}: {it.replace('item_','')} you {E.fmt(a)} vs {E.fmt(o)}" for r, it, a, o in random.sample(tuned, min(5, len(tuned)))])
# ---- H2 rate-based cleared / light, H3 rate-based, H1 floors
X["H2r"] = {}; X["H3r"] = {}; X["H1f"] = {}
for b in ("STANDARD", "TURBO"):
    UB = [u for u in E.U if u["bucket"] == b]
    orate = [u["hidden"]["enemy_obs"] / mins(u) * 10 for u in UB]; krate = [u["hidden"]["enemy_obs_killed_our"] / mins(u) * 10 for u in UB]
    share75 = Q([u["hidden"]["our_obs_destroyed_share"] for u in UB if u["hidden"]["own_obs"] >= 8], .75)
    cleared = [u for u in UB if u["hidden"]["own_obs"] >= 8 and (u["hidden"]["our_obs_destroyed_share"] or 0) >= share75 and u["hidden"]["enemy_obs_killed_our"] / mins(u) * 10 >= Q(krate, .9)]
    light = [u for u in UB if u["hidden"]["enemy_obs"] / mins(u) * 10 <= Q(orate, .1)]
    X["H2r"][b] = dict(obs_rate_p10=round(Q(orate, .1), 2), obs_rate_p50=round(Q(orate, .5), 2), obs_rate_p90=round(Q(orate, .9), 2),
                       cleared_pct=round(100 * len(cleared) / len(UB), 1), light_pct=round(100 * len(light) / len(UB), 1),
                       cleared_examples=[f"{round(mins(u))}m: they destroyed {u['hidden']['enemy_obs_killed_our']} of your team's {u['hidden']['own_obs']} observers" for u in random.sample(cleared, min(4, len(cleared)))],
                       light_examples=[f"{round(mins(u))}m: enemy placed {u['hidden']['enemy_obs']} observers ({u['hidden']['enemy_obs']/mins(u)*10:.1f}/10m); yours {u['hidden']['own_obs']}" for u in random.sample(light, min(4, len(light)))])
    srate = [u["hidden"]["enemy_smokes"] / mins(u) * 10 for u in UB]
    sm = [u for u in UB if u["hidden"]["enemy_smokes"] / mins(u) * 10 >= Q(srate, .9) and u["hidden"]["enemy_smokes"] >= (4 if b == "STANDARD" else 3) and u["hidden"]["enemy_smokes"] >= u["hidden"]["own_smokes"] + 2]
    X["H3r"][b] = dict(rate_p90=round(Q(srate, .9), 2), pct=round(100 * len(sm) / len(UB), 1))
    for fl in (5, 6, 7, 8):
        X["H1f"].setdefault(b, {})[fl] = round(100 * sum(1 for u in UB if u["hidden"].get("enemy_stacks", 0) >= fl and u["hidden"]["enemy_stacks"] - u["hidden"]["own_stacks"] >= 4) / len(UB), 1)
# ---- feeding guard effect on lane candidates
X["feeding"] = dict(matches=len(feed), total=len({r["match_id"] for r in rows}))
for cid in ("L1_LANE_LEAD_PATH", "L3_CS_NW_SPLIT", "L7_LANE_DEATH_TRADE"):
    el = [(r, x) for r, x in EV[cid] if x and x.get("eligible")]
    X["feeding"][cid] = dict(tuned_all=round(100 * sum(1 for _, x in el if x["tuned"]) / len(el), 2), tuned_no_feed=round(100 * sum(1 for r, x in el if x["tuned"] and r["match_id"] not in feed) / max(1, sum(1 for r, _ in el if r["match_id"] not in feed)), 2))
# ---- recommended-pool coverage per family (viewpoint level)
def fired(cid, r_key):
    return r_key in FIRES[cid]
FIRES = defaultdict(set)
for cid, v in EV.items():
    for r, x in v:
        if x and x.get("tuned") and r["match_id"] not in feed: FIRES[cid].add((r["match_id"], r["slot"]))
POOL = {"lane": ["L1_LANE_LEAD_PATH", "L5_COUNTERPART_EXTREME_START", "L4_LEVEL6_RACE", "L3_CS_NW_SPLIT", "L8_SUPPORT_LANE_PAIR"],
        "turning": ["T1_TURN_WINDOW", "T2_LEAD_FLIP", "T3_COMEBACK_OR_LOST_LEAD", "T6_STRUCTURES_WHILE_DEAD"],
        "hidden": ["H1_ENEMY_STACKING", "H3_ENEMY_SMOKES", "H5_ENEMY_BOSS_CONTROL", "H6_ENEMY_FAST_CORE"],
        "items": ["I3_ENEMY_EARLY_SPIKE_ITEM"]}
vp = [(r["match_id"], r["slot"], r["bucket"], r["role"]) for r in rows if r["match_id"] not in feed]
cov = {}
for fam, cids in POOL.items():
    hit = [k for k in vp if any((k[0], k[1]) in FIRES[c] for c in cids)]
    cov[fam] = dict(pct=round(100 * len(hit) / len(vp), 1), std=round(100 * sum(1 for k in hit if k[2] == "STANDARD") / sum(1 for k in vp if k[2] == "STANDARD"), 1),
                    turbo=round(100 * sum(1 for k in hit if k[2] == "TURBO") / sum(1 for k in vp if k[2] == "TURBO"), 1),
                    roles={ro: round(100 * sum(1 for k in hit if k[3] == ro) / sum(1 for k in vp if k[3] == ro), 1) for ro in ("carry", "mid", "offlane", "support")})
anyfam = Counter(sum(1 for fam, cids in POOL.items() if any((k[0], k[1]) in FIRES[c] for c in cids)) for k in vp)
cov["families_with_any"] = dict(sorted(anyfam.items()))
X["pool_coverage"] = cov
# ---- key co-fire pairs (conditional probability both | A, both | B)
pairs = [("L1_LANE_LEAD_PATH", "L5_COUNTERPART_EXTREME_START"), ("L1_LANE_LEAD_PATH", "L7_LANE_DEATH_TRADE"), ("L1_LANE_LEAD_PATH", "L3_CS_NW_SPLIT"), ("L1_LANE_LEAD_PATH", "L4_LEVEL6_RACE"),
         ("L1_LANE_LEAD_PATH", "L2_LANE_SUSTAINED_FLIP"), ("L1_LANE_LEAD_PATH", "L8_SUPPORT_LANE_PAIR"), ("L5_COUNTERPART_EXTREME_START", "L4_LEVEL6_RACE"),
         ("T1_TURN_WINDOW", "T2_LEAD_FLIP"), ("T1_TURN_WINDOW", "T3_COMEBACK_OR_LOST_LEAD"), ("T2_LEAD_FLIP", "T3_COMEBACK_OR_LOST_LEAD"), ("T1_TURN_WINDOW", "T5_CLASH_TO_STRUCTURES"),
         ("T1_TURN_WINDOW", "T6_STRUCTURES_WHILE_DEAD"), ("T1_TURN_WINDOW", "T7_OBJECTIVE_HEAVY_TURN"), ("T1_TURN_WINDOW", "T8_DEATH_HEAVY_TURN"), ("T5_CLASH_TO_STRUCTURES", "T6_STRUCTURES_WHILE_DEAD"),
         ("H1_ENEMY_STACKING", "H8_ENEMY_JUNGLE_RELIANCE"), ("H6_ENEMY_FAST_CORE", "H7_ENEMY_ECONOMY_CONCENTRATION"), ("H6_ENEMY_FAST_CORE", "I3_ENEMY_EARLY_SPIKE_ITEM"),
         ("H3_ENEMY_SMOKES", "H4_SMOKE_TO_KILLS"), ("H2_ENEMY_VISION", "H9_SHORT_LIVED_OBSERVERS"), ("H5_ENEMY_BOSS_CONTROL", "T3_COMEBACK_OR_LOST_LEAD"),
         ("I1_UNUSED_ACTIVE_ITEM", "I2_ACTIVATION_RATE_EXTREME"), ("I3_ENEMY_EARLY_SPIKE_ITEM", "I5_ENEMY_SPIKE_CLUSTER"), ("I6_SPIKE_BEFORE_TURN", "T1_TURN_WINDOW"),
         ("H6_ENEMY_FAST_CORE", "T1_TURN_WINDOW"), ("L5_COUNTERPART_EXTREME_START", "H6_ENEMY_FAST_CORE"), ("I4_LANE_ITEM_RACE", "L1_LANE_LEAD_PATH")]
ALL = defaultdict(set)
for cid, v in EV.items():
    for r, x in v:
        if x and x.get("tuned"): ALL[cid].add((r["match_id"], r["slot"]))
X["cofire_pairs"] = {f"{a} & {b}": dict(n_a=len(ALL[a]), n_b=len(ALL[b]), both=len(ALL[a] & ALL[b]), p_b_given_a=round(len(ALL[a] & ALL[b]) / max(1, len(ALL[a])), 2), p_a_given_b=round(len(ALL[a] & ALL[b]) / max(1, len(ALL[b])), 2)) for a, b in pairs}
# ---- same-direction lane redundancy: L1 CRUSHED with L5 STRONG
crushed_strong = sum(1 for r, x in EV["L1_LANE_LEAD_PATH"] if x and x.get("shape") in ("CRUSHED", "FELL_BEHIND") and (F["L5_COUNTERPART_EXTREME_START"](r) or {}).get("tuned"))
crushed = sum(1 for r, x in EV["L1_LANE_LEAD_PATH"] if x and x.get("shape") in ("CRUSHED", "FELL_BEHIND"))
X["L1_behind_with_L5_strong"] = (crushed_strong, crushed)
json.dump(X, open("final_metrics.json", "w"), indent=1, default=str)
print(json.dumps(X, indent=1, default=str)[:12000])

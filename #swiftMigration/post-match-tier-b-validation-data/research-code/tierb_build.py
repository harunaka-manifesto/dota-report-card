"""Build Tier B candidates per viewpoint (shape + modifiers + moderate signals), score them, and export the review sample."""
import json, math, pickle, random, statistics as st, sys
from collections import Counter, defaultdict
from shape import *
from modifiers import modifiers, MP_BASE

F = pickle.load(open("final.pkl", "rb")); RES, CONF, P, TT = F["RES"], F["CONF"], F["P_FINAL"], F["TT"]; DEV, HOLD = F["DEV"], F["HOLD"]
G = pickle.load(open("tier_a_gate.pkl", "rb")); FIRE, HIST, FEED = G["FIRE"], G["HISTINFO"], G["feed"]
SG = pickle.load(open("signals.pkl", "rb")); SIG, META = SG["SIG"], SG["META"]
UNIT = {key(u): u for u in U_ALL}
MP = dict(MP_BASE)
def clip(x): return max(0.0, min(1.0, x))
def ka(g): return f"{abs(g) / 1000:.1f}k"
def mmss(s): return f"{int(s) // 60}:{int(s) % 60:02d}"
def side(s, cap=False): w = "your team" if s > 0 else "the enemy"; return w[0].upper() + w[1:] if cap else w
TIER_A_IDS = {"L1", "L8", "L5", "L3", "L6", "T2", "T3", "T6", "H1", "H2r-a", "H2r-b", "H3r", "H5", "H6", "I3", "I8"}

def shape_render(u, r):
    lab = r["label"]; b = base_of(lab); d = r.get("detail") or {}; lc = u["lc"]; S0, E0 = r["S"], r["Emin"]; s = r.get("dir", 0)
    if b == "ETS":
        sep = d["sep_minute"]; pre_end = max(S0, sep - 3); mx = max(abs(lc[t]) for t in range(S0, pre_end + 1))
        return f"Until {pre_end}:00 the net-worth gap stayed within {ka(mx)}. From {sep}:00 {side(s)} held a sustained lead: {ka(s * lc[sep])} at {sep}:00, {ka(s * lc[E0])} at {E0}:00."
    if b in ("LE", "DR"):
        pk = d["ref_minute"]; gl = d["gold_late"]; who = side(s)
        late = f"{ka(gl)} by {E0}:00" if gl > 0 else (f"gone by {E0}:00 (even)" if gl == 0 else f"gone by {E0}:00 ({side(-s)} {ka(gl)} ahead)")
        return f"{side(s, True)}'s lead peaked at {ka(d['gold_ref'])} at {pk}:00 and was {late}; {side(-s)} never held a sustained lead."
    if b == "OS":
        pm = max(range(S0, E0 + 1), key=lambda t: s * lc[t])
        return f"{side(s, True)} held a clear net-worth lead for {d['edge_share']:.0%} of {S0}:00-{E0}:00, from {d['first_edge_minute']}:00 (peak {ka(s * lc[pm])} at {pm}:00)."
    if b == "SE":
        pm = max(range(S0, E0 + 1), key=lambda t: s * lc[t]); ahead = sum(1 for t in range(S0, E0 + 1) if s * lc[t] > 0) / (E0 - S0 + 1)
        return f"{side(s, True)} was ahead in net worth for {ahead:.0%} of {S0}:00-{E0}:00 and {side(-s)} never held a clear lead for 3 straight minutes (largest lead {ka(s * lc[pm])} at {pm}:00)."
    if b == "SWAP":
        (s1, a1, b1), (s2, a2, b2) = d["first"], d["last"]
        p1 = max(s1 * lc[S0 + i] for i in range(a1, b1 + 1)); p2 = max(s2 * lc[S0 + i] for i in range(a2, b2 + 1))
        return f"Both teams held sustained leads: {side(s1)} {S0 + a1}:00-{S0 + b1}:00 (up to {ka(p1)}), then {side(s2)} {S0 + a2}:00-{S0 + b2}:00 (up to {ka(p2)})."
    if b == "CT":
        t = f"Between {S0}:00 and {E0}:00 the net-worth gap never stayed above {ka(r['max_sustained_gold'])} for 3 straight minutes."
        if r.get("latest_close_minute") is not None and r["latest_close_minute"] >= E0 - 2: t += f" The game was still close at {r['latest_close_minute']}:00."
        return t
    if b == "UNCLEAR": return "No clear net-worth shape (brief leads only)."
    return "Window too short for a match shape."

def mod_render(u, r, m):
    out = []
    for x in m.get("STRUCTURE_COUNTERTREND", []): out.append(("STRUCTURE_COUNTERTREND", f"During {side(x['leader'])}'s {x['edge_minutes']} lead minutes, {side(-x['leader'])} destroyed {-x['leader_net']} more towers/barracks than it lost."))
    for x in m.get("NO_STRUCTURE_CONVERSION", []): out.append(("NO_STRUCTURE_CONVERSION", f"{side(x['leader'], True)} led for {x['end'] - x['start'] + 1} minutes ({x['start']}:00-{x['end']}:00) with no net tower/barracks change."))
    return out

def shape_candidate(u, r, m):
    b = base_of(r["label"]); d = r.get("detail") or {}
    if b in ("SHORT_WINDOW", "UNCLEAR"): return None
    T0 = TT[(u["bucket"], 0)]; C0, S0t = T0["C"], T0["S"]
    if b == "ETS": ss = clip((abs(d["lead_after"]) - C0) / (S0t - C0))
    elif b in ("LE", "DR"): ss = clip((d["ref"] - C0) / (S0t - C0)) * clip(d["erosion"])
    elif b == "OS": ss = 0.5 * clip((d["edge_share"] - 0.7) / 0.3) + 0.5 * clip(d["strong_minutes"] / (r["n"] / 2))
    elif b == "SE": ss = clip((d["edge_share"] - 0.5) / 0.3) if d.get("path") != "lean" else clip((d["ahead_share"] - 0.8) / 0.2)
    elif b == "SWAP": ss = 0.8
    else: ss = 0.5 * clip((r["close_share"] - 0.5) / 0.5) + 0.5 * (1 if (r.get("latest_close_minute") or 0) >= r["Emin"] - 2 else 0)
    # v2 (fitted on the v1 review): a one-sided/steady label mostly restates the result, so it earns little structure credit
    es = {"ETS": 1.0, "LE": 1.0, "DR": 1.0, "SWAP": 1.0, "CT": 0.6, "SE": 0.4, "OS": 0.2}[b]
    s = r.get("dir", 0)
    co = 0.0   # STRUCTURE_ALIGNED (97% of OS/SE) and STRUCTURE_BURST (87% of all) carry no information and give no credit
    if m.get("NO_STRUCTURE_CONVERSION"): co = 0.5
    if m.get("STRUCTURE_COUNTERTREND"): es = 1.0; co = 0.5
    rel = CONF[key(u)]
    score = (35 * ss + 25 * es + 20 * 0.5 + 15 * co + 5 * 0) * rel
    mods = mod_render(u, r, m)
    return dict(id=f"SHAPE_{b}", family="shape", label=r["label"], ss=round(ss, 3), es=es, pr=0.5, co=co, hi=0, rel=round(rel, 3), score=round(score, 1),
                text=shape_render(u, r), mods=[x[0] for x in mods], mod_text=" ".join(x[1] for x in mods))

SIG_ES = {"C_SPIKE_RICH_ITEM": 1.0, "C_ECON_STACK_RICH": 0.8, "X_HIDDEN_MULTI": 0.8, "X_LANE_VS_OTHER_LANES": 0.8, "C_LANE_NW_CS": 0.6, "C_VISION_CLEARED_LOW_SURVIVAL": 0.5,
          "STACK_MOD": 0.5, "SMOKE_MOD": 0.5, "OBSCLEAR_MOD": 0.5, "RICH_MOD": 0.5, "BOSS_MOD": 0.5, "LANE_NW_MODERATE": 0.4, "ITEM_EARLY_MOD": 0.2}
SIG_PR = {"counterpart": 0.75, "user_lane": 0.9, "team": 0.5}
SIG_REL = {"C_LANE_NW_CS": 0.9, "LANE_NW_MODERATE": 0.9, "X_LANE_VS_OTHER_LANES": 0.85}
def signal_candidate(sg):
    ss = clip((sg["pp"] - 50) / 40); es = SIG_ES[sg["id"]]; pr = SIG_PR[sg["level"]]; rel = SIG_REL.get(sg["id"], 1.0)
    co = (0.5 if sg["id"] == "C_LANE_NW_CS" else 1.0) if sg.get("components") else 0.0   # NW and CS gaps are not independent
    return dict(id=sg["id"], family=sg["family"], label=sg["id"], ss=round(ss, 3), es=es, pr=pr, co=co, hi=0, rel=rel, score=round((35 * ss + 25 * es + 20 * pr + 15 * co) * rel, 1), text=sg["text"], pp=sg["pp"])

# ---------------- per viewpoint ----------------
VP = {}
for kk, meta in META.items():
    u = UNIT[(meta["mid"], meta["side"])]; r = RES[key(u)]; m = modifiers(u, r, MP)
    tierA = sorted(c for c in FIRE.get(kk, []) if c in TIER_A_IDS)
    cands = [c for c in [shape_candidate(u, r, m)] if c] + [signal_candidate(s) for s in SIG.get(kk, [])]
    cands.sort(key=lambda c: -c["score"])
    VP[kk] = dict(meta, tierA=tierA, shape=r["label"], conf=CONF[key(u)], mods=sorted(m), cands=cands,
                  split="dev" if meta["mid"] in DEV else "holdout", established=HIST.get(kk, {}).get("prior_bucket", 0) >= 10, tracked=kk in HIST)
pickle.dump(VP, open("tierb_vp.pkl", "wb"))

# ---------------- review sample ----------------
rng = random.Random(20260916)
def timeline(u, r):
    step = 3 if u["bucket"] == "STANDARD" else 2; last = len(u["lc"]) - 1; pts = list(range(max(0, r["S"] - step), last + 1, step))
    if pts[-1] != last: pts.append(last)
    return " ".join(f"{t}:{'+' if u['lc'][t] >= 0 else '-'}{ka(u['lc'][t])}" for t in pts)
def structs(u):
    return " ".join(f"{mmss(t)}{'-' if us else '+'}" for t, us, kd, tr in u["structs"])
def item_for(kk, cand, why):
    v = VP[kk]; u = UNIT[(v["mid"], v["side"])]; r = RES[key(u)]
    return dict(rid=None, why=why, kind=cand["id"], label=cand["label"], mid=v["mid"], slot=v["slot"], bucket=v["bucket"], win=v["win"], dur_min=v["dur"] // 60, role=v["role"], hero=v["hero"],
                split=v["split"], tierA=v["tierA"] or "EMPTY", shape=v["shape"], conf=round(v["conf"], 2), score=cand["score"], parts=dict(ss=cand["ss"], es=cand["es"], pr=cand["pr"], co=cand["co"], rel=cand["rel"]),
                text=cand["text"], mod_text=cand.get("mod_text", ""), timeline=timeline(u, r), structures=structs(u),
                window=f"{r['S']}:00-{r['Emin']}:00", diag=dict(close_share=round(r.get("close_share", 0), 2), max_sustained_gold=r.get("max_sustained_gold"), lead_changes=r.get("lead_changes"),
                                                                  first_edge=r.get("first_edge_minute"), latest_close=r.get("latest_close_minute")), other_cands=[(c["id"], c["score"]) for c in v["cands"] if c is not cand][:4])
EMPTY = [kk for kk, v in VP.items() if not v["tierA"]]
V2 = len(sys.argv) > 1 and sys.argv[1] == "v2"
if V2:   # fresh, holdout-only sample that shares no match side with the v1 review
    rated = json.load(open("review_items_v1.json"))
    seen_vp = {(x["mid"], x["slot"]) for x in rated}; seen_team = {(x["mid"], x["slot"] < 128) for x in rated}
    EMPTY = [kk for kk in EMPTY if VP[kk]["split"] == "holdout" and kk not in seen_vp and (VP[kk]["mid"], VP[kk]["side"]) not in seen_team]
NR, NB, NS = (12, 0, 0) if V2 else (15, 10, 10)
ITEMS = []
by_team = defaultdict(list)
for kk in EMPTY: by_team[(VP[kk]["mid"], VP[kk]["side"])].append(kk)
team_keys = list(by_team)
for sh in ("ETS", "LE", "DR", "OS", "SE", "SWAP", "CT", "UNCLEAR"):
    pool = []
    for tk in team_keys:
        kk = rng.choice(sorted(by_team[tk])); v = VP[kk]
        if base_of(v["shape"]) != sh: continue
        c = next((c for c in v["cands"] if c["family"] == "shape"), None) or dict(id=f"SHAPE_{sh}", label=v["shape"], score=0, ss=0, es=0, pr=0, co=0, rel=v["conf"], text=shape_render(UNIT[tk], RES[tk]), mod_text="")
        pool.append((kk, c))
    strata = defaultdict(list)
    for kk, c in pool: strata[(VP[kk]["bucket"], VP[kk]["win"])].append((kk, c))
    chosen = set(); order = []
    for s_ in strata.values(): rng.shuffle(s_)
    while len(order) < min(NR, len(pool)):
        progressed = False
        for s_ in sorted(strata):
            lst = [x for x in strata[s_] if x[0] not in chosen]
            if lst and len(order) < NR: order.append((lst[0], "random")); chosen.add(lst[0][0]); progressed = True
        if not progressed: break
    rest = [x for x in pool if x[0] not in chosen]
    for x in sorted(rest, key=lambda x: (x[1]["rel"], x[1]["score"]))[:NB]: order.append((x, "borderline")); chosen.add(x[0])
    rest = [x for x in pool if x[0] not in chosen]
    if sh != "UNCLEAR":
        for x in sorted(rest, key=lambda x: -x[1]["score"])[:NS]: order.append((x, "strongest"))
    for (kk, c), why in order: ITEMS.append(item_for(kk, c, why))
    print(sh, "pool", len(pool), "review", len(order))
for sid in SIG_ES:
    pool = [(kk, c) for kk in EMPTY for c in VP[kk]["cands"] if c["id"] == sid]
    seen = set(); pool2 = []
    for kk, c in pool:
        tk = (VP[kk]["mid"], VP[kk]["side"]) if c["pr"] == 0.5 else kk
        if tk not in seen: seen.add(tk); pool2.append((kk, c))
    for kk, c in rng.sample(pool2, min(10, len(pool2))): ITEMS.append(item_for(kk, c, "random"))
    print(sid, "pool", len(pool2))
for kk in rng.sample(EMPTY, 60):
    v = VP[kk]
    if v["cands"]: ITEMS.append(item_for(kk, v["cands"][0], "funnel_best"))
    else: ITEMS.append(dict(rid=None, why="funnel_best", kind="NONE", label="NONE", mid=v["mid"], slot=v["slot"], bucket=v["bucket"], win=v["win"], dur_min=v["dur"] // 60, role=v["role"], hero=v["hero"], split=v["split"], tierA="EMPTY", shape=v["shape"], score=0, text="(no Tier B candidate)"))
for i, it in enumerate(ITEMS): it["rid"] = f"R{i:03d}"
SUF = "_v2" if V2 else ""
if V2:
    for it in ITEMS: it["rid"] = "V" + it["rid"][1:]
json.dump(ITEMS, open(f"review_items{SUF}.json", "w"), indent=1, default=str)
with open(f"review_compact{SUF}.txt", "w") as fh:
    for it in ITEMS:
        fh.write(f"{it['rid']} {it['kind']} [{it['label']}] {it['why']} | {it['bucket'][:3]} {'W' if it['win'] else 'L'} {it['dur_min']}m {it['role']} | score {it['score']} conf {it.get('conf')} | {it['text']} {it.get('mod_text', '')}"
                 + (f" || win {it['window']} diag {it['diag']} lead {it['timeline']}" + ("" if V2 else f" || str {it['structures']}") if it["kind"].startswith("SHAPE") else "") + "\n")
print("review items", len(ITEMS))

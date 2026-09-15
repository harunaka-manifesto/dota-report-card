"""Phases 12/13/15/16 + Tier A overlap, computed from tierb_vp.pkl / final.pkl (no ratings needed)."""
import json, math, pickle, random, statistics as st
from collections import Counter, defaultdict
from shape import *
from render import describe
from primitives import load_matches, BAD_LEAVER

VP = pickle.load(open("tierb_vp.pkl", "rb")); F = pickle.load(open("final.pkl", "rb")); RES, CONF, P, TT = F["RES"], F["CONF"], F["P_FINAL"], F["TT"]
G = pickle.load(open("tier_a_gate.pkl", "rb"))
UNIT = {key(u): u for u in U_ALL}
rng = random.Random(3)
OUT = {}
def corr(x, y):
    mx, my = st.fmean(x), st.fmean(y); sx = math.sqrt(sum((a - mx) ** 2 for a in x)); sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else 0
ALL = list(VP.values()); EMPTY = [v for v in ALL if not v["tierA"]]
med = {b: st.median(v["dur"] for v in ALL if v["bucket"] == b) for b in ("STANDARD", "TURBO")}
terc = {b: (pctl([v["dur"] for v in ALL if v["bucket"] == b], 100 / 3), pctl([v["dur"] for v in ALL if v["bucket"] == b], 200 / 3)) for b in med}
def dcat(v): t = terc[v["bucket"]]; return "short" if v["dur"] <= t[0] else ("medium" if v["dur"] <= t[1] else "long")
SHAPES = ("ETS", "LE", "DR", "OS", "SE", "SWAP", "CT", "UNCLEAR", "SHORT_WINDOW")
SIGS = sorted({c["id"] for v in ALL for c in v["cands"] if c["family"] != "shape"})
def has(v, x): return base_of(v["shape"]) == x if x in SHAPES else any(c["id"] == x for c in v["cands"])
def bias(pop):
    res = {}
    W = [v for v in pop if v["win"]]; L = [v for v in pop if not v["win"]]
    for x in SHAPES + tuple(SIGS):
        n = sum(1 for v in pop if has(v, x))
        if not n: continue
        w = sum(1 for v in W if has(v, x)) / len(W); l = sum(1 for v in L if has(v, x)) / len(L)
        res[x] = dict(rate=round(100 * n / len(pop), 1), win=round(100 * w, 1), loss=round(100 * l, 1), loss_to_win=round(l / w, 2) if w else None,
                      dur_corr=round(corr([1 if has(v, x) else 0 for v in pop], [v["dur"] / med[v["bucket"]] for v in pop]), 2),
                      by_dur={c: round(100 * sum(1 for v in pop if dcat(v) == c and has(v, x)) / max(1, sum(1 for v in pop if dcat(v) == c)), 1) for c in ("short", "medium", "long")},
                      std=round(100 * sum(1 for v in pop if v["bucket"] == "STANDARD" and has(v, x)) / max(1, sum(1 for v in pop if v["bucket"] == "STANDARD")), 1),
                      turbo=round(100 * sum(1 for v in pop if v["bucket"] == "TURBO" and has(v, x)) / max(1, sum(1 for v in pop if v["bucket"] == "TURBO")), 1))
    return res
OUT["bias_all"] = bias(ALL); OUT["bias_tierA_empty"] = bias(EMPTY)
OUT["tierA_empty_share_by_shape"] = {x: round(100 * sum(1 for v in EMPTY if has(v, x)) / max(1, sum(1 for v in ALL if has(v, x))), 1) for x in SHAPES}
OUT["tierA_empty_win_share"] = round(100 * sum(1 for v in EMPTY if v["win"]) / len(EMPTY), 1)
# overlap: Tier A candidate rates inside each shape, and shape mix inside each Tier A candidate
TA = ("L1", "L8", "L5", "L3", "L6", "T2", "T3", "T6", "H1", "H2r-a", "H2r-b", "H3r", "H5", "H6", "I3", "I8")
ov = []
for x in SHAPES:
    pop = [v for v in ALL if base_of(v["shape"]) == x]
    if not pop: continue
    row = dict(shape=x, viewpoints=len(pop), tierA_empty_pct=round(100 * sum(1 for v in pop if not v["tierA"]) / len(pop), 1))
    for a in TA: row[a] = round(100 * sum(1 for v in pop if a in v["tierA"]) / len(pop), 1)
    ov.append(row)
OUT["overlap_rows"] = ov
OUT["shape_mix_within_tierA"] = {a: dict(Counter(base_of(v["shape"]) for v in ALL if a in v["tierA"]).most_common()) for a in ("T2", "T3", "T6", "H5", "H6", "L1", "I3")}
# ---------------- Phase 15 edge cases (team units, current corpus incl. feed) ----------------
core, rep, pb = load_matches()
cur_units = [u for u in U_ALL if u["src"] == "current"]
gate_team = defaultdict(set)
for (mid, slot), cs in G["FIRE"].items():
    for c in cs: gate_team[(mid, slot < 128)].add(c)
def lab(u): return RES[key(u)]["label"]
def show(us, k=3): return [describe(u, RES[key(u)])[:700] for u in rng.sample(us, min(k, len(us)))]
edge = {}
def case(name, us):
    edge[name] = dict(units=len(us), labels=dict(Counter(base_of(lab(u)) for u in us).most_common()), mean_conf=round(st.fmean([CONF[key(u)] for u in us]), 3) if us else None, examples=show(us))
case("very_short_eligible (<20m Turbo / <25m Std)", [u for u in cur_units if u["dur"] < (20 * 60 if u["bucket"] == "TURBO" else 25 * 60)])
case("60+ minutes", [u for u in cur_units if u["dur"] >= 3600])
case("extreme one-sided (OS with strong edge >= half the window)", [u for u in cur_units if base_of(lab(u)) == "OS" and RES[key(u)]["detail"]["strong_minutes"] >= RES[key(u)]["n"] / 2])
case("repeated lead changes (>=4 crossings of the close band)", [u for u in cur_units if RES[key(u)].get("lead_changes", 0) >= 4])
case("decided late (CT still close <=2 min before window end, or ETS separating in last 5 window minutes)", [u for u in cur_units if (lab(u) == "CT" and (RES[key(u)].get("latest_close_minute") or 0) >= RES[key(u)]["Emin"] - 2) or (base_of(lab(u)) == "ETS" and RES[key(u)]["detail"]["sep_minute"] >= RES[key(u)]["Emin"] - 4)])
from modifiers import modifiers
case("NW vs structure disagreement (STRUCTURE_COUNTERTREND)", [u for u in cur_units if "STRUCTURE_COUNTERTREND" in modifiers(u, RES[key(u)])])
case("comeback wins (Tier A T3, winner view)", [u for u in cur_units if "T3" in gate_team[key(u)] and u["win"]])
case("lost large leads (Tier A T3, loser view)", [u for u in cur_units if "T3" in gate_team[key(u)] and not u["win"]])
case("Turbo extremes (<=16m or >=45m)", [u for u in cur_units if u["bucket"] == "TURBO" and (u["dur"] <= 16 * 60 or u["dur"] >= 45 * 60)])
case("grief/feed outliers (feeding guard matches)", [u for u in cur_units if u["feed"]])
leaver_adj = {mid for mid, m in core.items() if any((p.get("leaverStatus") not in (None, "NONE")) and p.get("leaverStatus") not in BAD_LEAVER for p in m["players"])}
case("leaver-adjacent (non-abandon leaver status present)", [u for u in cur_units if u["mid"] in leaver_adj])
contra = [u for u in cur_units if (u["win"] and lab(u) in ("OS_AGAINST", "SE_AGAINST", "ETS_AGAINST")) or (not u["win"] and lab(u) in ("OS_FOR", "SE_FOR", "ETS_FOR"))]
case("result contradicts the classified economy (winner labelled *_AGAINST)", [u for u in contra if u["win"]])
OUT["edge_cases"] = edge
OUT["leaver_status_values"] = dict(Counter(p.get("leaverStatus") for mid in {u["mid"] for u in cur_units} for p in core[mid]["players"]))
# ---------------- Phase 16: other fallback observations on Tier-A-empty ----------------
p16 = {}
def team_of(v): return UNIT[(v["mid"], v["side"])]
def regains(u, r):
    """Episodes where this team fell to a clear deficit for 1-2 minutes (not sustained) and was back within the close band within 3 minutes."""
    if r["label"] == "SHORT_WINDOW": return 0
    S0, E0, n, a = series(u, P); cnt = 0; i = 0
    while i < n:
        th = TT[(u["bucket"], phase_bin(u["bucket"], S0 + i, P))]
        if a[i] <= -th["E"]:
            j = i
            while j + 1 < n and a[j + 1] <= -TT[(u["bucket"], phase_bin(u["bucket"], S0 + j + 1, P))]["E"]: j += 1
            if j - i + 1 < P["run"] and any(abs(a[t]) <= TT[(u["bucket"], phase_bin(u["bucket"], S0 + t, P))]["C"] for t in range(j + 1, min(n, j + 4))): cnt += 1
            i = j + 1
        else: i += 1
    return cnt
emp_team = {}
for v in EMPTY: emp_team.setdefault((v["mid"], v["side"]), v)
TE = list(emp_team.values())
def frac(pred): return round(100 * sum(1 for v in TE if pred(v)) / len(TE), 1)
p16["team_units_tierA_empty_any_viewpoint"] = len(TE)
p16["prolonged_parity (CT, close share >= 80%)"] = frac(lambda v: v["shape"] == "CT" and RES[(v["mid"], v["side"])]["close_share"] >= .8)
p16["late_first_sustained_edge (first edge after 60% of window)"] = frac(lambda v: RES[(v["mid"], v["side"])].get("first_edge_minute") is not None and RES[(v["mid"], v["side"])]["first_edge_minute"] >= RES[(v["mid"], v["side"])]["S"] + 0.6 * RES[(v["mid"], v["side"])]["n"])
p16["repeated_parity_regaining (>=2 regains, no sustained edge against)"] = frac(lambda v: regains(team_of(v), RES[(v["mid"], v["side"])]) >= 2 and not [x for x in RES[(v["mid"], v["side"])]["runs"] if x[0] < 0])
p16["never_trailed_clearly (no minute at or below -edge)"] = frac(lambda v: RES[(v["mid"], v["side"])]["label"] != "SHORT_WINDOW" and RES[(v["mid"], v["side"])].get("peak_against", 1) < RES[(v["mid"], v["side"])].get("edge_thr", 0))
p16["regain_examples"] = [describe(team_of(v), RES[(v["mid"], v["side"])])[:600] for v in [v for v in TE if regains(team_of(v), RES[(v["mid"], v["side"])]) >= 2 and not [x for x in RES[(v["mid"], v["side"])]["runs"] if x[0] < 0]][:3]]
p16["viewpoints_with_any_moderate_signal"] = round(100 * sum(1 for v in EMPTY if any(c["family"] != "shape" for c in v["cands"])) / len(EMPTY), 1)
p16["viewpoints_with_no_candidate_at_all"] = round(100 * sum(1 for v in EMPTY if not v["cands"]) / len(EMPTY), 1)
OUT["phase16"] = p16
json.dump(OUT, open("analysis_results.json", "w"), indent=1, default=str)
print(json.dumps({k: OUT[k] for k in ("tierA_empty_share_by_shape", "tierA_empty_win_share", "phase16", "shape_mix_within_tierA")}, indent=0, default=str))
for nm in ("bias_all", "bias_tierA_empty"):
    print(nm); [print(" ", x, d) for x, d in OUT[nm].items()]
for nm, e in edge.items(): print("EDGE", nm, e["units"], e["labels"], e["mean_conf"]); [print("     ", x) for x in e["examples"]]
print("leaver statuses", OUT["leaver_status_values"])

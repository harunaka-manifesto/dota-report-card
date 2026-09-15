"""Phase 8-14 evaluation from the reviews + machine-readable outputs. Usage: tierb_eval.py [cutoff]"""
import csv, html, json, math, os, pickle, statistics as st, sys
from collections import Counter, defaultdict
from shape import *

CUT = float(sys.argv[1]) if len(sys.argv) > 1 else 50
OUT = "../../../#swiftMigration/post-match-tier-b-validation-data"; os.makedirs(OUT, exist_ok=True)
VP = pickle.load(open("tierb_vp.pkl", "rb")); VP1 = pickle.load(open("tierb_vp_v1.pkl", "rb"))
F2 = pickle.load(open("final.pkl", "rb")); F1 = pickle.load(open("final_v1.pkl", "rb"))
G = pickle.load(open("tier_a_gate.pkl", "rb"))
I1 = json.load(open("review_items_v1.json")); R1 = json.load(open("ratings_v1.json"))
I2 = json.load(open("review_items_v2.json")); R2 = json.load(open("ratings_v2.json"))
for it in I1: it["rating_as_rendered"], it["rating"] = R1[it["rid"]]; it["review_round"] = "v1"
for it in I2: it["rating_as_rendered"] = it["rating"] = R2[it["rid"]]; it["review_round"] = "v2"
EXCLUDE = {"SHAPE_OS", "SHAPE_UNCLEAR", "SHAPE_SHORT_WINDOW", "BOSS_MOD", "ITEM_EARLY_MOD", "LANE_NW_MODERATE", "C_VISION_CLEARED_LOW_SURVIVAL"}
RES = {}
def pct(n, d): return round(100 * n / d, 1) if d else None

# ---------- pooled ratings valid under v2 ----------
def v2cand(kk, kind, label):
    for c in VP.get(kk, {}).get("cands", []):
        if c["id"] == kind and (not kind.startswith("SHAPE") or c["label"] == label): return c
    return None
POOL = []; seen = set()
for it in I2 + I1:
    if it["kind"] == "NONE": continue
    kk = (it["mid"], it["slot"]); c = v2cand(kk, it["kind"], it["label"])   # only ratings of candidates that still exist under the final rules
    if not c: continue
    dk = (it["kind"], it["mid"], it["slot"])
    if dk in seen: continue
    seen.add(dk); POOL.append(dict(kind=it["kind"], score=c["score"], rating=it["rating"], round=it["review_round"], why=it["why"], win=it["win"], bucket=it["bucket"]))
def rates(rs):
    c = Counter(rs); n = len(rs)
    return dict(n=n, **{k: pct(c.get(k, 0), n) for k in "GABMW"})
KIND = {k: rates([p["rating"] for p in POOL if p["kind"] == k]) for k in sorted({p["kind"] for p in POOL})}
RES["pooled_kind_rates_v2_valid"] = KIND
RES["v1_kind_rates"] = {k: dict(as_rendered=rates([it["rating_as_rendered"] for it in I1 if it["kind"] == k]), content=rates([it["rating"] for it in I1 if it["kind"] == k])) for k in sorted({it["kind"] for it in I1})}
RES["v2_kind_rates_fresh"] = {k: rates([it["rating"] for it in I2 if it["kind"] == k and it["why"] == "random"]) for k in sorted({it["kind"] for it in I2})}
# shrunk probabilities for the coverage model
fam = lambda k: "shape" if k.startswith("SHAPE") else "signal"
FAMP = {f: Counter(p["rating"] for p in POOL if fam(p["kind"]) == f and p["kind"] not in EXCLUDE) for f in ("shape", "signal")}
def probs(kind):
    c = Counter(p["rating"] for p in POOL if p["kind"] == kind); n = sum(c.values()); fc = FAMP[fam(kind)]; fn = sum(fc.values())
    return {k: (c.get(k, 0) + 3 * fc.get(k, 0) / fn) / (n + 3) for k in "GABMW"}
PROB = {k: probs(k) for k in {c["id"] for v in VP.values() for c in v["cands"]}}

# ---------- score cutoffs ----------
disp = [p for p in POOL if p["kind"] not in EXCLUDE]
RES["cutoff_pooled_rated"] = {cut: rates([p["rating"] for p in disp if p["score"] >= cut]) for cut in (0, 40, 45, 50, 55, 60, 65, 70)}
val = {"G": 3, "A": 2, "B": 1, "M": 0, "W": 0}
def spearman(a, b):
    def rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v); i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]: j += 1
            for t in range(i, j + 1): r[o[t]] = (i + j) / 2
            i = j + 1
        return r
    ra, rb = rk(a), rk(b); ma, mb = st.fmean(ra), st.fmean(rb)
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
RES["spearman_v2_score_vs_rating_all_pooled"] = round(spearman([p["score"] for p in POOL], [val[p["rating"]] for p in POOL]), 3)
RES["spearman_v2_score_vs_rating_displayable"] = round(spearman([p["score"] for p in disp], [val[p["rating"]] for p in disp]), 3)
# empirical funnel on the fresh holdout sample (v2 funnel_best): suppressed kinds / below-cut become "N" unless another displayable candidate exists (then kind-expected)
def empirical(cut):
    tot = Counter(); fb = [it for it in I2 if it["why"] == "funnel_best"]
    for it in fb:
        v = VP[(it["mid"], it["slot"])]
        best = next((c for c in v["cands"] if c["id"] not in EXCLUDE and c["score"] >= cut), None)
        if not best: tot["N"] += 1
        elif best["id"] == it["kind"] and abs(best["score"] - it["score"]) < 1e-6: tot[it["rating"]] += 1
        else:
            for k2, p2 in PROB[best["id"]].items(): tot[k2] += p2
    return {k: round(100 * tot.get(k, 0) / len(fb), 1) for k in "GABMWN"} | {"n": len(fb)}
RES["empirical_holdout_funnel_by_cut"] = {cut: empirical(cut) for cut in (0, 40, 45, 50, 55, 60)}

# ---------- coverage model over all viewpoints ----------
TIERA = lambda v: bool(v["tierA"])
def model(vs, cut):
    e = Counter(); ta = sum(1 for v in vs if TIERA(v)); empty = [v for v in vs if not TIERA(v)]
    kinds = Counter()
    for v in empty:
        best = next((c for c in v["cands"] if c["id"] not in EXCLUDE and c["score"] >= cut), None)
        if not best: e["N"] += 1; continue
        kinds[best["id"]] += 1
        for k2, p2 in PROB[best["id"]].items(): e[k2] += p2
    n = len(vs); ne = len(empty)
    return dict(viewpoints=n, tierA_pct=pct(ta, n), tierA_empty_pct=pct(ne, n),
                within_empty={k: pct(e.get(k, 0), ne) for k in "GABMWN"},
                of_all={"tierB_good": pct(e["G"], n), "tierB_acceptable": pct(e["A"], n), "tierB_boring_shown": pct(e["B"], n), "tierB_misleading_shown": pct(e["M"] + e["W"], n), "nothing": pct(e["N"], n)},
                useful_all_pct=pct(ta + e["G"] + e["A"], n), best_kind_mix=dict(kinds.most_common()))
ALL = list(VP.values())
RES["model_by_cut"] = {cut: model(ALL, cut) for cut in (0, 40, 45, 50, 55, 60, 65)}
seg = {}
for name, fn in (("STANDARD", lambda v: v["bucket"] == "STANDARD"), ("TURBO", lambda v: v["bucket"] == "TURBO"), ("carry", lambda v: v["role"] == "carry"), ("mid", lambda v: v["role"] == "mid"),
                 ("offlane", lambda v: v["role"] == "offlane"), ("support", lambda v: v["role"] == "support"), ("win", lambda v: v["win"]), ("loss", lambda v: not v["win"]),
                 ("established (tracked, >=10 prior same mode)", lambda v: v["established"]), ("new / no history", lambda v: not v["established"]), ("dev", lambda v: v["split"] == "dev"), ("holdout", lambda v: v["split"] == "holdout")):
    seg[name] = model([v for v in ALL if fn(v)], CUT)
RES["model_segments_at_cut"] = seg
# v1 score-cutoff failure (as proposed)
fb1 = [it for it in I1 if it["why"] == "funnel_best"]
RES["v1_funnel_cutoffs_content"] = {cut: dict(coverage=pct(sum(1 for it in fb1 if it["score"] >= cut), len(fb1)), **rates([it["rating"] for it in fb1 if it["score"] >= cut])) for cut in (0, 50, 55, 60, 65, 70)}
RES["v1_spearman_score_vs_content"] = round(spearman([it["score"] for it in I1 if it["kind"] != "NONE"], [val[it["rating"]] if it["rating"] in val else 0 for it in I1 if it["kind"] != "NONE"]), 3)
# outcome skew of what would be displayed
disp_wl = {}
for w in (True, False):
    vs = [v for v in ALL if not TIERA(v) and v["win"] == w]
    shown = [next((c for c in v["cands"] if c["id"] not in EXCLUDE and c["score"] >= CUT), None) for v in vs]
    disp_wl["win" if w else "loss"] = dict(tierA_empty_viewpoints=len(vs), shown_pct=pct(sum(1 for c in shown if c), len(vs)), kind_mix=dict(Counter(c["id"] for c in shown if c).most_common()))
RES["displayed_by_outcome_at_cut"] = disp_wl
json.dump(RES, open("eval_results.json", "w"), indent=1, default=str)
for k in ("pooled_kind_rates_v2_valid", "cutoff_pooled_rated", "spearman_v2_score_vs_rating_all_pooled", "spearman_v2_score_vs_rating_displayable", "empirical_holdout_funnel_by_cut", "v1_funnel_cutoffs_content", "v1_spearman_score_vs_content"):
    print(k, json.dumps(RES[k], indent=0) if isinstance(RES[k], dict) else RES[k])
for cut, m in RES["model_by_cut"].items(): print("MODEL cut", cut, m["tierA_pct"], m["tierA_empty_pct"], m["within_empty"], m["of_all"], "useful_all", m["useful_all_pct"])
for s_, m in seg.items(): print("SEG", s_, m["viewpoints"], m["tierA_pct"], m["within_empty"], "useful_all", m["useful_all_pct"])
print("displayed by outcome", json.dumps(disp_wl, indent=0))

# ======================= machine-readable outputs =======================
P2 = F2["P_FINAL"]; TT2 = F2["TT"]
defs = dict(
    status="RECOMMENDATION FOR PRODUCT REVIEW — NOT YET SSOT", version="tier-b-match-shape-research-2.0", generated="2026-09-15",
    inputs=["players[].stats.networthPerMinute (all 10 players)", "towerDeaths (time, npcId, isRadiant = owner)", "durationSeconds", "gameMode/lobbyType", "didRadiantWin (context only, never used for detection)"],
    normalization="L(t) = team NW(t) - enemy NW(t); R(t) = L(t) / (team NW(t) + enemy NW(t)) at t:00",
    smoothing="centered 3-minute median of R, computed on R truncated at the window end (no post-window leakage)",
    window=dict(start_minute={"STANDARD": 10, "TURBO": 8}, end="floor((duration - 3 min) / 60)", min_window_minutes=9, below_minimum="SHORT_WINDOW (no shape)"),
    phase_bins=dict(edges=PHASE_EDGES, meaning="thresholds are looked up by absolute minute bin; bin k = number of edges <= minute"),
    band_percentiles=dict(close="p50 of |R| (dev, same mode, same phase bin)", meaningful_edge="p70", strong_edge="p90"),
    thresholds={f"{b}|phase_bin_{k}": {kk: round(vv, 4) for kk, vv in t.items() if kk != "ES"} for (b, k), t in sorted(TT2.items())},
    sustained_run_minutes=3, hysteresis="none (tested; no stability gain)",
    shapes=[
        dict(id="EVEN_THEN_SEPARATED", internal="ETS", direction="FOR/AGAINST", rule="Path 1 (thirds): first third >= 65% CLOSE minutes; the first sustained edge of side s starts at >= 30% of the window; no sustained edge of either side before it; final third >= 60% inside side-s sustained runs; no side(-s) sustained run after separation. Path 2 (transition): the first sustained run of the window belongs to s and starts at >= max(30% of window, 3 min); >= 65% CLOSE before it; >= 60% of the minutes after it inside s runs; >= 3 minutes after it; no -s sustained run.",
             slots=["direction", "separation_minute", "gap_before_max_gold (window start .. separation-3)", "lead_at_separation", "lead_at_window_end", "close_share_before", "edge_share_after", "net_structures_after"]),
        dict(id="LEAD_ERODED", internal="LE (s=+1)", rule="A sustained +edge run starts in the first 2/3 of the window; no sustained -edge run anywhere; relative erosion (peak R in first 2/3 minus median R of last 3 window minutes) / peak >= 50%; gold erosion from the gold peak in the first 2/3 >= 50%; gold peak >= 5,000 (Standard) / 8,000 (Turbo).",
             slots=["gold_peak", "gold_peak_minute", "gold_at_window_end (median of last 3)", "relative_erosion"]),
        dict(id="DEFICIT_RECOVERED", internal="DR (s=-1)", rule="Exact mirror of LEAD_ERODED for the opponent's lead.", slots=["enemy_gold_peak", "enemy_gold_peak_minute", "enemy_gold_at_window_end"]),
        dict(id="ONE_SIDED", internal="OS", rule="Side s owns >= 70% of window minutes inside sustained edge runs; first s run starts within the first 33%; no -s sustained run; and (strong edge >= 3 consecutive minutes or s gains >= 3 net structures). Structure clause is non-binding in practice.", display="never as Tier B (97% BORING in review)"),
        dict(id="STEADY_EDGE", internal="SE", rule="Path 1: s owns >= 50% of window minutes inside sustained runs, first-half and second-half medians of R both favour s, no -s sustained run. Path 2 (lean): s ahead (R>0) in >= 80% of window minutes, median(s*R) >= median CLOSE threshold, both half-medians favour s, no -s sustained run.", slots=["direction", "ahead_share", "largest_lead_gold", "largest_lead_minute"]),
        dict(id="LEAD_SWAPPED", internal="SWAP", rule="Sustained runs of both sides inside the window (not part of the original six; required for exhaustive labels; ~2% of matches, 0.3% of Tier-A-empty; mostly covered by Tier A T2/T3).", slots=["first_run", "last_run"]),
        dict(id="CLOSE_THROUGHOUT", internal="CT", rule="Positive rule: no sustained edge run of either side; CLOSE share >= 60% of window minutes; the largest gap held for 3 straight minutes (either direction) < 7,500 gold.", slots=["max_3min_gap_gold", "latest_close_minute", "close_share"]),
        dict(id="UNCLEAR", internal="fallback", rule="Everything else. Never displayed.")],
    priority=["EVEN_THEN_SEPARATED", "LEAD_ERODED", "DEFICIT_RECOVERED", "ONE_SIDED", "STEADY_EDGE", "LEAD_SWAPPED", "CLOSE_THROUGHOUT", "UNCLEAR"],
    mirror_rule="label(opponent view) = mirror(label): LE<->DR, *_FOR<->*_AGAINST, CT<->CT, UNCLEAR<->UNCLEAR",
    shape_confidence="share of 34 deterministic perturbations (percentiles +-5, run +-1, shares +-5pp, erosion +-10pp, start +-1/2, end exclusion +-1/2, CT close share +-5pp, lean share +-5pp, CT gold +-1000, LE gold floor +-1000) that return the same label",
    modifiers=dict(kept=dict(NO_STRUCTURE_CONVERSION="a sustained edge run of >= 8 (Standard) / 5 (Turbo) minutes with 0 net towers/barracks for the leader (enrichment text only)",
                                STRUCTURE_COUNTERTREND="during the leader's sustained edge minutes the trailing side destroyed >= 2 more towers/barracks (enrichment text only; 0.7% of matches)"),
                   rejected=dict(STRUCTURE_ALIGNED="97% of ONE_SIDED/STEADY_EDGE and 90% of EVEN_THEN_SEPARATED: restates the shape", STRUCTURE_BURST="87% of matches (3 in 5 min); end-game pushes")),
    moderate_signals=dict(
        C_LANE_NW_CS="core; lane-end NW gap and CS gap both beyond p75 (ahead) or p25 (behind) of the SAME position pairing (dev), same direction, |NW gap| >= 500",
        X_LANE_VS_OTHER_LANES="user's map lane is the only lane of three with that sign at the lane checkpoint; |own lane gap| >= p50 of lane gaps; both other lanes >= p25",
        C_SPIKE_RICH_ITEM="an enemy hero reaches the NW goal (Std 10k / Turbo 15k) at <= p25 timing and >= 3 min before your team's first, AND the same hero's spike item is <= p25 timing for that item; connector ordered by time ('bought X at t and reached ...' / '..., then bought X at t')",
        RICH_MOD="enemy fastest to NW goal <= p25 timing and >= 3 min before your team's first",
        STACK_MOD="Standard only; enemy stacks by 20:00 >= p75, stack edge >= p75 and >= 4",
        SMOKE_MOD="enemy smokes per 10 min >= p75 and enemy smokes >= own + 4",
        OBSCLEAR_MOD="own observers >= 8; enemy destroyed-observer rate >= p75; share destroyed >= 45%; >= 4 destroyed",
        X_HIDDEN_MULTI=">= 2 of STACK_MOD / OBSCLEAR_MOD / SMOKE_MOD / RICH_MOD", C_ECON_STACK_RICH="STACK_MOD and RICH_MOD",
        rejected=dict(BOSS_MOD="enemy Roshan >= 1 vs 0: 100% BORING, 9.3x loss-skewed in Tier-A-empty", ITEM_EARLY_MOD="any enemy core spike item <= p25: fires 63% (multiple comparisons); component only",
                      LANE_NW_MODERATE="superseded by C_LANE_NW_CS", C_VISION_CLEARED_LOW_SURVIVAL="82% BORING; same metric counted twice")),
    score=dict(formula="TierBScore = (35*SignalStrength + 25*ExplanatoryStructure + 20*PlayerRelevance + 15*Corroboration + 5*HistoryContext) * Reliability",
               signal_strength="signals: clip((percentile - 50)/40); ETS: clip((|median R after separation| - CLOSE)/(STRONG - CLOSE)); LE/DR: clip((peak R - CLOSE)/(STRONG - CLOSE)) * min(1, erosion); SE: edge-share or lean-share scaled; CT: 0.5*close-share scaled + 0.5 if still close within 2 min of window end",
               explanatory_structure=dict(ETS=1.0, LE=1.0, DR=1.0, SWAP=1.0, CT=0.6, SE=0.4, OS=0.2, C_SPIKE_RICH_ITEM=1.0, X_HIDDEN_MULTI=0.8, C_ECON_STACK_RICH=0.8, X_LANE_VS_OTHER_LANES=0.8, C_LANE_NW_CS=0.6, single_hidden_signal=0.5),
               player_relevance=dict(user_lane=0.9, counterpart=0.75, team=0.5), corroboration="1.0 for independent-metric composites, 0.5 for C_LANE_NW_CS (NW and CS dependent) and shape + NO_STRUCTURE_CONVERSION/COUNTERTREND, else 0",
               history_context="0 in this research (no Tier-B history signals validated)", reliability="shape_confidence for shapes; 1.0 raw facts; 0.9 lane counterpart; 0.85 lane-vs-lanes",
               recommended_cutoff=CUT, display_exclusions=sorted(EXCLUDE)),
    perturbation_variants=[n for n, _ in perturbations(P2)], rule_parameters={k: (v if not isinstance(v, dict) else v) for k, v in P2.items()})
json.dump(defs, open(f"{OUT}/tier-b-shape-definitions.json", "w"), indent=1, default=str)
# classifications
U = {key(u): u for u in U_ALL}
team_fire = defaultdict(lambda: [0, 0])
for mid_slot, cs in G["FIRE"].items(): pass
vp_by_team = defaultdict(list)
for kk, v in VP.items(): vp_by_team[(v["mid"], v["side"])].append(v)
from modifiers import modifiers
with open(f"{OUT}/tier-b-match-classifications.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["match_id", "team_is_radiant", "source", "split", "mode", "patch", "duration_min", "team_won", "shape_v2", "shape_confidence_v2", "shape_v1", "window_start", "window_end", "window_minutes",
                "close_share", "edge_share_for", "edge_share_against", "first_edge_minute", "latest_close_minute", "max_3min_gap_gold", "net_structures_for_in_window", "modifiers_v2",
                "viewpoints_tierA_empty", "viewpoints_total", "feeding_guard"])
    for k, u in sorted(U.items(), key=lambda kv: (kv[1]["src"], kv[0])):
        r2 = F2["RES"][k]; r1 = F1["RES"].get(k, {}); m = modifiers(u, r2)
        vs = vp_by_team.get(k, [])
        w.writerow([u["mid"], u["side"], u["src"], ("dev" if u["mid"] in F2["DEV"] else ("holdout" if u["mid"] in F2["HOLD"] else "n/a")), u["bucket"], u["patch"], round(u["dur"] / 60, 1), u["win"],
                    r2["label"], round(F2["CONF"][k], 3), r1.get("label"), r2["S"], r2["Emin"], r2["n"], round(r2.get("close_share", 0), 3) if "close_share" in r2 else "",
                    round(r2.get("es_for", 0), 3) if "es_for" in r2 else "", round(r2.get("es_against", 0), 3) if "es_against" in r2 else "", r2.get("first_edge_minute"), r2.get("latest_close_minute"),
                    r2.get("max_sustained_gold"), r2.get("net_structs_for"), "|".join(kx for kx in sorted(m) if kx in ("NO_STRUCTURE_CONVERSION", "STRUCTURE_COUNTERTREND")),
                    sum(1 for v in vs if not v["tierA"]), len(vs), u["feed"]])
# overlap with Tier A
A = json.load(open("analysis_results.json"))
rows = A["overlap_rows"]
with open(f"{OUT}/tier-b-overlap-with-tier-a.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); [w.writerow(r) for r in rows]
# threshold grid (v1 grid + finalists + v2 ablation)
grid = [dict(stage="grid_v1_dev", **r) for r in csv.DictReader(open("tier-b-threshold-grid.csv"))]
for name, rec in json.load(open("stab_results.json")).items():
    if name.startswith("C"): grid.append(dict(stage="finalists_dev", config=name, mean_conf=rec["mean_conf"], stable=rec["stable"], borderline=rec["borderline"], unstable=rec["unstable"],
                                              T3_shape_recall=rec["T3_shape_recall"], T3_contradicted=rec["T3_contradicted"], **{f"pct_{k}": v for k, v in rec["dist"].items()}))
for name, rec in json.load(open("stab_v2_results.json")).items():
    if isinstance(rec, dict) and "dev_all_variants" in rec:
        d = rec["dev_all_variants"]; h = rec["holdout_all_variants"]
        grid.append(dict(stage="v2_ablation_dev", config=name, mean_conf=d["mean_conf"], stable=d["stable"], unstable=d["unstable"], core_variant_conf=rec["dev_core_variants"]["mean_conf"],
                         holdout_mean_conf=h["mean_conf"], mirror_mismatch=rec["mirror_mismatch"], T3_contradicted=rec["T3_contradicted"], **{f"pct_{k}": v for k, v in d["dist"].items()}, **{f"holdout_pct_{k}": v for k, v in h["dist"].items()}))
keys = []
for g in grid:
    for kx in g:
        if kx not in keys: keys.append(kx)
with open(f"{OUT}/tier-b-threshold-grid.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); [w.writerow(g) for g in grid]
# review examples
json.dump(dict(rubric=R1["_rubric"] if "_rubric" in R1 else "", reviewer="single rater (research model) applying the written rubric; owner re-rating recommended", items=I1 + I2),
          open(f"{OUT}/tier-b-review-examples.json", "w"), indent=1, default=str)
# review sheet (Markdown + HTML)
LAB = {"G": "GOOD", "A": "ACCEPTABLE", "B": "BORING", "M": "MISLEADING", "W": "WRONG", "N": "NOTHING"}
with open(f"{OUT}/tier-b-review-sheet.md", "w") as fh:
    fh.write("# Tier B Review Sheet\n\nSingle-rater review (research model, written rubric). v1 = first classifier, dev+holdout sample; v2 = revised classifier, fresh holdout-only sample. `as rendered / content` differ only where a rendering defect was fixed in v2.\n\n")
    for rnd, items in (("v1", I1), ("v2", I2)):
        fh.write(f"## Review round {rnd}\n\n")
        for kind in sorted({it["kind"] for it in items}):
            xs = [it for it in items if it["kind"] == kind]
            fh.write(f"### {kind} ({len(xs)})\n\n| id | sample | match | Tier A | score | conf | rendering | rating |\n|---|---|---|---|---:|---:|---|---|\n")
            for it in xs:
                txt = (it["text"] + " " + it.get("mod_text", "")).strip().replace("|", "/")
                rt = LAB[it["rating_as_rendered"]] + ("" if it["rating_as_rendered"] == it["rating"] else f" / {LAB[it['rating']]}")
                fh.write(f"| {it['rid']} | {it['why']} | {it['bucket'][:3]} {'W' if it['win'] else 'L'} {it['dur_min']}m {it['role']} | {it['tierA'] if isinstance(it['tierA'], str) else ','.join(it['tierA'])} | {it['score']} | {it.get('conf')} | {txt} | {rt} |\n")
            fh.write("\n")
css = """:root{--bg:#fbfaf8;--fg:#1d1d1f;--mut:#6b6b70;--card:#fff;--line:#e5e3df;--g:#1f7a4d;--a:#3d6fb6;--b:#8a8a8a;--m:#b54708;--w:#b42318}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#141416;--fg:#ececef;--mut:#9a9aa2;--card:#1c1c20;--line:#2c2c31;--g:#4cc38a;--a:#7aa7ee;--b:#9a9a9a;--m:#f5a05b;--w:#f97066}}
:root[data-theme="dark"]{--bg:#141416;--fg:#ececef;--mut:#9a9aa2;--card:#1c1c20;--line:#2c2c31;--g:#4cc38a;--a:#7aa7ee;--b:#9a9a9a;--m:#f5a05b;--w:#f97066}
body{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,sans-serif;margin:0;padding:24px 16px}main{max-width:1100px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 8px}h3{font-size:14px;margin:18px 0 6px;color:var(--mut)}p{color:var(--mut)}
.it{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:6px 0}.hd{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--mut)}
.b{font-weight:600;border-radius:4px;padding:1px 6px;font-size:11px;color:#fff}.G{background:var(--g)}.A{background:var(--a)}.B{background:var(--b)}.M{background:var(--m)}.W{background:var(--w)}.N{background:var(--b)}
.tx{margin:6px 0 0}details{margin-top:4px;font-size:12px;color:var(--mut)}code{font-size:11px;word-break:break-word}select{font-size:12px}"""
with open(f"{OUT}/tier-b-review-sheet.html", "w") as fh:
    fh.write(f"<title>Tier B Review Sheet</title><style>{css}</style><main><h1>Tier B Review Sheet</h1><p>Research review of deterministic Tier B outputs. Ratings are a single rater (research model) applying the written rubric. Use the selector to record your own rating; it stays in this browser only.</p>")
    for rnd, items in (("v1 (first classifier)", I1), ("v2 (revised classifier, fresh holdout)", I2)):
        fh.write(f"<h2>Round {html.escape(rnd)}</h2>")
        for kind in sorted({it["kind"] for it in items}):
            xs = [it for it in items if it["kind"] == kind]; cnt = Counter(it["rating"] for it in xs)
            fh.write(f"<h3>{html.escape(kind)} — {len(xs)} items · " + " ".join(f"{LAB[k2]} {cnt.get(k2, 0)}" for k2 in "GABMW" if cnt.get(k2)) + "</h3>")
            for it in xs:
                ta = it["tierA"] if isinstance(it["tierA"], str) else ",".join(it["tierA"])
                fh.write(f"<div class='it'><div class='hd'><b>{it['rid']}</b><span>{html.escape(it['why'])}</span><span>{it['bucket'][:3]} {'W' if it['win'] else 'L'} {it['dur_min']}m {html.escape(str(it['role']))}</span><span>Tier A: {html.escape(ta)}</span><span>score {it['score']}</span><span>conf {it.get('conf')}</span>"
                         f"<span class='b {it['rating_as_rendered']}'>{LAB[it['rating_as_rendered']]}</span>" + ("" if it["rating_as_rendered"] == it["rating"] else f"<span class='b {it['rating']}'>fixed: {LAB[it['rating']]}</span>") +
                         f"<select data-rid='{it['rid']}'><option value=''>your rating</option>" + "".join(f"<option>{LAB[k2]}</option>" for k2 in "GABMW") + "</select></div>"
                         f"<div class='tx'>{html.escape((it['text'] + ' ' + it.get('mod_text', '')).strip())}</div>" +
                         (f"<details><summary>lead timeline</summary><code>window {html.escape(str(it.get('window')))} · {html.escape(str(it.get('diag')))} · {html.escape(str(it.get('timeline')))}</code></details>" if it.get("timeline") else "") + "</div>")
    fh.write("""<h2>Your ratings (copy)</h2><textarea id='exp' rows='6' style='width:100%'></textarea></main>
<script>const K='tierb-review';let s={};try{s=JSON.parse(localStorage.getItem(K)||'{}')}catch(e){}
function upd(){document.getElementById('exp').value=JSON.stringify(s)}
document.querySelectorAll('select[data-rid]').forEach(el=>{if(s[el.dataset.rid])el.value=s[el.dataset.rid];el.addEventListener('change',()=>{s[el.dataset.rid]=el.value;try{localStorage.setItem(K,JSON.stringify(s))}catch(e){}upd()})});upd();</script>""")
print("outputs written to", OUT)

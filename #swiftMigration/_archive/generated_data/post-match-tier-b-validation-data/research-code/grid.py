"""Phase 2/4/5/6/7 grid: smoothing x bands x run x hysteresis on DEVELOPMENT units; one-factor tests for the rest."""
import csv, itertools, json, pickle, statistics as st, time
from collections import Counter, defaultdict
from shape import *

gate = pickle.load(open("tier_a_gate.pkl", "rb"))
DEV, HOLD = split()
U = [u for u in U_ALL if u["src"] == "current" and not u["feed"]]
UD = [u for u in U if u["mid"] in DEV and u["side"]]          # one perspective per match for label counting
teamA = defaultdict(set)
for (mid, slot), cs in gate["FIRE"].items():
    for c in cs: teamA[(mid, slot < 128)].add(c)
print("dev matches", len(DEV), "holdout", len(HOLD), Counter(u["bucket"] for u in U if u["side"] and u["mid"] in HOLD))

def evaluate(P, B, units):
    TT = thresholds(B, P); res = {key(u): analyze(u, P, TT) for u in units}
    labs = {k: r["label"] for k, r in res.items()}
    dist = Counter(base_of(l) for l in labs.values()); n = len(labs)
    t2 = [k for k in labs if "T2" in teamA[k]]
    cb = [k for k in labs if "T3" in teamA[k]]      # comeback win (our side won) or lost lead (our side lost)
    wins = {k: u["win"] for u in units for k in [key(u)]}
    cb_recall = sum(1 for k in cb if (labs[k] in ("DR", "SWAP_FOR", "ETS_FOR") if wins[k] else labs[k] in ("LE", "SWAP_AGAINST", "ETS_AGAINST"))) / max(1, len(cb))
    cb_contra = sum(1 for k in cb if (labs[k] in ("OS_AGAINST", "SE_AGAINST", "ETS_AGAINST") if wins[k] else labs[k] in ("OS_FOR", "SE_FOR", "ETS_FOR"))) / max(1, len(cb))
    flick = [sum(1 for x, y in zip(r["runs"], r["runs"][1:])) for r in res.values() if r["label"] != "SHORT_WINDOW"]
    raw_multi = sum(1 for r in res.values() if len({nm for nm, s in r["raw"] if nm not in ("SWAP",)}) > 1) / n
    none_before_fb = sum(1 for r in res.values() if r["label"] != "SHORT_WINDOW" and not r["raw"]) / n
    rec = dict(n=n, **{f"pct_{s}": round(100 * dist.get(s, 0) / n, 1) for s in ORDER + ("SHORT_WINDOW",)},
               t2_swap_recall=round(100 * sum(1 for k in t2 if base_of(labs[k]) in ("SWAP",)) / max(1, len(t2)), 1),
               comeback_shape_recall=round(100 * cb_recall, 1), comeback_contradicted=round(100 * cb_contra, 1),
               mean_runs=round(st.fmean(len(r["runs"]) for r in res.values() if r["label"] != "SHORT_WINDOW"), 2),
               raw_multi_pct=round(100 * raw_multi, 1), none_before_fallback_pct=round(100 * none_before_fb, 1))
    return rec, labs, res

GRID = []; LABS = {}
t0 = time.time()
for sm in ("raw", "med3", "mean3", "med5"):
    P0 = dict(BASE, smooth=sm); B = fit_bands(UD, P0)
    for cp, ep, sp, run, hy in itertools.product((40, 50, 60), (60, 65, 70, 75), (85, 90), (2, 3, 4), (False, True)):
        if cp >= ep: continue
        P = dict(P0, close_p=cp, edge_p=ep, strong_p=sp, run=run, stay_p=(ep - 10 if hy else None))
        rec, labs, _ = evaluate(P, B, UD)
        cfg = dict(axis="bands", smooth=sm, close_p=cp, edge_p=ep, strong_p=sp, run=run, hysteresis=hy, end_excl=3, min_window=9)
        GRID.append(dict(cfg, **rec)); LABS[tuple(cfg.values())] = labs
print("band grid", len(GRID), round(time.time() - t0), "s")
# neighbour agreement inside the band grid (edge +-5, close +-10, run +-1, strong +-5, hysteresis toggle)
idx = {tuple(g[k] for k in ("smooth", "close_p", "edge_p", "strong_p", "run", "hysteresis")): g for g in GRID}
def lab_of(t): return LABS[("bands",) + t[:6] + (3, 9)]
for t, g in idx.items():
    sm, cp, ep, sp, run, hy = t; neigh = []
    for alt in ((sm, cp, ep - 5, sp, run, hy), (sm, cp, ep + 5, sp, run, hy), (sm, cp, ep, 90 if sp == 85 else 85, run, hy), (sm, cp, ep, sp, run - 1, hy), (sm, cp, ep, sp, run + 1, hy),
                (sm, cp - 10, ep, sp, run, hy), (sm, cp + 10, ep, sp, run, hy), (sm, cp, ep, sp, run, not hy)):
        if alt in idx: neigh.append(alt)
    A = lab_of(t)
    ag = [sum(1 for k in A if A[k] == lab_of(n)[k]) / len(A) for n in neigh]
    g["neighbour_agreement"] = round(100 * st.fmean(ag), 1); g["neighbour_min_agreement"] = round(100 * min(ag), 1)
    g["hysteresis_effect_agreement"] = round(100 * sum(1 for k in A if A[k] == lab_of((sm, cp, ep, sp, run, not hy))[k]) / len(A), 1)
# smoothing comparison at the default bands: flicker (edge-state entries per 10 window minutes) on raw vs smoothed
flick = {}
for sm in ("raw", "med3", "mean3", "med5"):
    P = dict(BASE, smooth=sm); B = fit_bands(UD, P); TT = thresholds(B, P); ent = []; mins = 0
    for u in UD:
        S, Emin, n, a = series(u, P)
        if n < 9: continue
        E = TT[u["bucket"]]["E"]; stt = [1 if v >= E else (-1 if v <= -E else 0) for v in a]
        ent.append(sum(1 for x, y in zip(stt, stt[1:]) if x != y)); mins += n
    flick[sm] = round(10 * sum(ent) / mins, 3)
print("state changes per 10 window-minutes", flick)
# one-factor axes around BASE
B_base = fit_bands(UD, BASE)
def one(axis, **kw):
    P = dict(BASE, **kw); B = fit_bands(UD, P) if any(k in kw for k in ("smooth", "end_excl", "start_shift", "min_window")) else B_base
    rec, labs, res = evaluate(P, B, UD)
    GRID.append(dict(axis=axis, **{k: (json.dumps(v) if isinstance(v, (dict, tuple, list)) else v) for k, v in kw.items()}, **rec)); return labs, res
BASE_LABS, BASE_RES = one("base")
for ex in (0, 2, 3, 5): one("end_excl", end_excl=ex)
for mw in (6, 9, 12): one("min_window", min_window=mw)
for ss in (-2, -1, 1, 2): one("start_shift", start_shift=ss)
for mode in ("thirds", "transition"):
    for clean in (True, False): one("ets_mode", ets=mode, ets_clean=clean)
for ec in (.55, .65, .75): one("ets_close", ets_close=ec)
for ef in (.5, .6, .7): one("ets_final", ets_final=ef)
for ero in (.35, .50, .65):
    for ref in ("peak", "runmed", "p90"):
        for lbe in (False, True): one("erosion", erosion=ero, ref=ref, le_below_edge=lbe)
for osh in (.60, .65, .70, .75): one("os_share", os_share=osh)
for osf in (.25, .33, .40): one("os_first", os_first=osf)
for ost in (2, 3, 4): one("os_struct", os_struct=ost)
for se in (.45, .50, .55, .60): one("se_share", se_share=se)
for ct in (None, .5, .6, .7): one("ct_close", ct_close=ct, fallback="UNCLEAR")
# end-exclusion diagnostics: final-push-defined labels (separation / erosion located in the last 5 window minutes) under each exclusion
fp = {}
for ex in (0, 2, 3, 5):
    P = dict(BASE, end_excl=ex); B = fit_bands(UD, P); TT = thresholds(B, P); c = Counter(); tot = 0
    for u in UD:
        r = analyze(u, P, TT)
        if r["label"] == "SHORT_WINDOW": continue
        tot += 1; nm = base_of(r["label"])
        if nm == "ETS" and r["detail"]["sep_minute"] >= r["Emin"] - 4: c["ETS_sep_in_last5"] += 1
        if nm in ("LE", "DR"):
            # erosion only visible in last 5 window minutes: median of window minus the last 5 still >= 75% of ref
            s = r["dir"]; a = series(u, P)[3]; pre = st.median([s * v for v in a[-8:-5]]) if len(a) > 8 else None
            if pre is not None and pre >= 0.75 * r["detail"]["ref"]: c["LEDR_only_last5"] += 1
        if nm == "SWAP" and r["runs"][-1][1] >= r["Emin"] - 4: c["SWAP_last_run_in_last5"] += 1
    fp[ex] = {k: round(100 * v / tot, 1) for k, v in c.items()}
print("final-push diagnostics", fp)
# raw overlaps at base
ov = Counter(); multi = Counter()
for r in BASE_RES.values():
    names = sorted({nm for nm, s in r["raw"]})
    multi[len(names)] += 1
    for i, a_ in enumerate(names):
        for b_ in names[i + 1:]: ov[f"{a_}&{b_}"] += 1
print("raw shape count per unit", dict(multi), "overlaps", dict(ov))
with open("tier-b-threshold-grid.csv", "w", newline="") as fh:
    keys = []
    for g in GRID:
        for k in g:
            if k not in keys: keys.append(k)
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); [w.writerow(g) for g in GRID]
json.dump(dict(flicker=flick, final_push=fp, overlaps=dict(ov), multi=dict(multi), bands_base={b: {p: pctl(v, p) for p in (30, 40, 50, 60, 65, 70, 75, 80, 85, 90, 95)} for b, v in B_base.items()}),
          open("grid_diag.json", "w"), indent=1)
pickle.dump(dict(DEV=DEV, HOLD=HOLD), open("split.pkl", "wb"))
print("done", round(time.time() - t0), "s")

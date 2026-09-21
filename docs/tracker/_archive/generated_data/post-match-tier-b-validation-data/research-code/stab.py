"""Finalist configurations: perturbation stability, duration/outcome bias, comeback sanity, mirror, end-exclusion transitions (DEV only)."""
import json, math, pickle, statistics as st, sys
from collections import Counter, defaultdict
from shape import *
DEV, HOLD = split()
U = [u for u in U_ALL if u["src"] == "current" and not u["feed"]]
UD = [u for u in U if u["mid"] in DEV and u["side"]]; UD2 = [u for u in U if u["mid"] in DEV]
gate = pickle.load(open("tier_a_gate.pkl", "rb"))
teamA = defaultdict(set)
for (mid, slot), cs in gate["FIRE"].items():
    for c in cs: teamA[(mid, slot < 128)].add(c)
med = {b: st.median([u["dur"] for u in UD if u["bucket"] == b]) for b in ("STANDARD", "TURBO")}
terc = {b: (pctl([u["dur"] for u in UD if u["bucket"] == b], 100 / 3), pctl([u["dur"] for u in UD if u["bucket"] == b], 200 / 3)) for b in med}
def dcat(u): t = terc[u["bucket"]]; return "short" if u["dur"] <= t[0] else ("medium" if u["dur"] <= t[1] else "long")
def corr(x, y):
    mx, my = st.fmean(x), st.fmean(y); sx = math.sqrt(sum((a - mx) ** 2 for a in x)); sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else 0
CFG = {"C1_base": {}, "C2_edge75": dict(edge_p=75), "C3_med5_edge75": dict(smooth="med5", edge_p=75), "C4_phase": dict(phase_bands=True),
       "C5_gold": dict(le_gold_confirm=True), "C6_phase_gold": dict(phase_bands=True, le_gold_confirm=True),
       "C7_pg_transition": dict(phase_bands=True, le_gold_confirm=True, ets="transition"), "C8_pg_osshare": dict(phase_bands=True, le_gold_confirm=True, os_mode="share_only"),
       "C9_pg_ctpos60": dict(phase_bands=True, le_gold_confirm=True, ct_close=.6, fallback="UNCLEAR"), "C10_pg_hyst": dict(phase_bands=True, le_gold_confirm=True, stay_p=60),
       "C11_pg_med5": dict(phase_bands=True, le_gold_confirm=True, smooth="med5"), "C12_pg_edge75": dict(phase_bands=True, le_gold_confirm=True, edge_p=75),
       "C13_pg_ctpos50": dict(phase_bands=True, le_gold_confirm=True, ct_close=.5, fallback="UNCLEAR")}
OUT = {}
for name, kw in CFG.items():
    P = dict(BASE, **kw); B = fit_bands(UD, P); TT = thresholds(B, P)
    base, conf, byvar = stability(UD, P, B, True)
    res = {key(u): analyze(u, P, TT) for u in UD2}
    n = len(UD); labs1 = {key(u): res[key(u)]["label"] for u in UD}
    dist = Counter(base_of(l) for l in labs1.values())
    rec = dict(dist={k: round(100 * v / n, 1) for k, v in sorted(dist.items(), key=lambda kv: -kv[1])},
               mean_conf=round(st.fmean(conf.values()), 3), stable=round(100 * sum(1 for c in conf.values() if c >= .9) / n, 1),
               borderline=round(100 * sum(1 for c in conf.values() if .7 <= c < .9) / n, 1), unstable=round(100 * sum(1 for c in conf.values() if c < .7) / n, 1),
               worst_variants=dict(sorted(((k, round(100 * v, 1)) for k, v in byvar.items()), key=lambda kv: kv[1])[:6]))
    ps = {}
    for sh in ORDER + ("SHORT_WINDOW",):
        ks = [k for k, l in labs1.items() if base_of(l) == sh]
        if not ks: continue
        us = [u for u in UD2 if base_of(res[key(u)]["label"]) == sh]
        ind = [1 if base_of(res[key(u)]["label"]) == sh else 0 for u in UD]
        ps[sh] = dict(n=len(ks), conf=round(st.fmean(conf[k] for k in ks), 3), stable=round(100 * sum(1 for k in ks if conf[k] >= .9) / len(ks), 1),
                      dur_corr=round(corr(ind, [u["dur"] / med[u["bucket"]] for u in UD]), 2),
                      by_dur={c: round(100 * sum(1 for u in UD if dcat(u) == c and base_of(res[key(u)]["label"]) == sh) / sum(1 for u in UD if dcat(u) == c), 1) for c in ("short", "medium", "long")},
                      win=round(100 * sum(1 for u in UD2 if u["win"] and base_of(res[key(u)]["label"]) == sh) / sum(1 for u in UD2 if u["win"]), 1),
                      loss=round(100 * sum(1 for u in UD2 if not u["win"] and base_of(res[key(u)]["label"]) == sh) / sum(1 for u in UD2 if not u["win"]), 1),
                      std=round(100 * sum(1 for u in UD if u["bucket"] == "STANDARD" and base_of(res[key(u)]["label"]) == sh) / sum(1 for u in UD if u["bucket"] == "STANDARD"), 1),
                      turbo=round(100 * sum(1 for u in UD if u["bucket"] == "TURBO" and base_of(res[key(u)]["label"]) == sh) / sum(1 for u in UD if u["bucket"] == "TURBO"), 1))
    rec["per_shape"] = ps
    rec["conf_by_window"] = {w: round(st.fmean([conf[key(u)] for u in UD if lo <= res[key(u)]["n"] <= hi] or [0]), 3) for w, (lo, hi) in (("9-11", (9, 11)), ("12-19", (12, 19)), ("20-34", (20, 34)), ("35+", (35, 999)))}
    cb = [u for u in UD2 if "T3" in teamA[key(u)]]
    def good_cb(u, l): return l in (("DR", "SWAP_FOR", "ETS_FOR") if u["win"] else ("LE", "SWAP_AGAINST", "ETS_AGAINST"))
    def contra_cb(u, l): return l in (("OS_AGAINST", "SE_AGAINST", "ETS_AGAINST") if u["win"] else ("OS_FOR", "SE_FOR", "ETS_FOR"))
    rec["T3_units"] = len(cb); rec["T3_shape_recall"] = round(100 * sum(good_cb(u, res[key(u)]["label"]) for u in cb) / len(cb), 1)
    rec["T3_contradicted"] = round(100 * sum(contra_cb(u, res[key(u)]["label"]) for u in cb) / len(cb), 1)
    rec["T3_label_mix"] = dict(Counter(base_of(res[key(u)]["label"]) for u in cb).most_common())
    allres = {key(u): analyze(u, P, TT) for u in U}
    rec["mirror_mismatch_all_current"] = sum(1 for u in U if u["side"] and allres[(u["mid"], False)]["label"] != mirror(allres[key(u)]["label"]))
    rec["thresholds"] = {f"{k[0][:3]}_{k[1]}": {kk: round(vv, 4) for kk, vv in v.items() if kk != "ES"} for k, v in TT.items()}
    OUT[name] = rec
    print(name, json.dumps({k: rec[k] for k in ("dist", "mean_conf", "stable", "borderline", "unstable", "T3_shape_recall", "T3_contradicted", "mirror_mismatch_all_current")}), flush=True)
    print("   per-shape", {sh: (v["n"], v["conf"], v["stable"], v["dur_corr"], v["by_dur"], v["win"], v["loss"]) for sh, v in ps.items()}, flush=True)
    print("   worst", rec["worst_variants"], "by window", rec["conf_by_window"], "T3 mix", rec["T3_label_mix"], flush=True)
# end-exclusion transitions for C6
P6 = dict(BASE, **CFG["C6_phase_gold"]); B6 = fit_bands(UD, P6); T6 = thresholds(B6, P6)
L3 = {key(u): analyze(u, P6, T6)["label"] for u in UD}
for ex in (0, 2, 5):
    Px = dict(P6, end_excl=ex); Lx = {key(u): analyze(u, Px, T6)["label"] for u in UD}
    tr = Counter((base_of(L3[k]), base_of(Lx[k])) for k in L3 if base_of(L3[k]) != base_of(Lx[k]))
    OUT.setdefault("end_excl_transitions_vs3", {})[ex] = dict(agree=round(100 * sum(1 for k in L3 if L3[k] == Lx[k]) / len(L3), 1), top=[(f"{a}->{b}", c) for (a, b), c in tr.most_common(8)])
print("end-excl transitions", OUT["end_excl_transitions_vs3"])
json.dump(OUT, open("stab_results.json", "w"), indent=1, default=str)

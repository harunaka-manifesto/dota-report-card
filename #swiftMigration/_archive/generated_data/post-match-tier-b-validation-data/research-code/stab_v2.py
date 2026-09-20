"""Ablation of the v2 changes (each alone and together): stability, mirror, holdout, T3 sanity."""
import json, pickle, statistics as st
from collections import Counter, defaultdict
from shape import *
DEV, HOLD = split()
CUR = [u for u in U_ALL if u["src"] == "current" and not u["feed"]]
UD = [u for u in CUR if u["mid"] in DEV and u["side"]]; UH = [u for u in CUR if u["mid"] in HOLD and u["side"]]; UD2 = [u for u in CUR if u["mid"] in DEV]
gate = pickle.load(open("tier_a_gate.pkl", "rb")); teamA = defaultdict(set)
for (mid, slot), cs in gate["FIRE"].items():
    for c in cs: teamA[(mid, slot < 128)].add(c)
P0 = dict(BASE, phase_bands=True, le_gold_confirm=True, fallback="UNCLEAR"); B = fit_bands(UD, P0)
V1 = dict(P0, ct_gold={"STANDARD": 16101, "TURBO": 17717})
G2 = dict(ct_close=.6, ct_gold={"STANDARD": 7500, "TURBO": 7500}); L2 = dict(le_ref_gold=True, le_gold_floor={"STANDARD": 5000, "TURBO": 8000})
CFG = {"v1 (sign-agnostic gap)": V1, "+ets_both": dict(V1, ets="both"), "+se_lean": dict(V1, se_lean=.8), "+ct_guard": dict(P0, **G2), "+le_gold_ref_floor": dict(V1, **L2),
       "v2_all": dict(P0, ets="both", se_lean=.8, **G2, **L2), "v2_all_se_lean_0.75": dict(P0, ets="both", se_lean=.75, **G2, **L2), "v2_all_ct_gold_6500": dict(P0, ets="both", se_lean=.8, ct_close=.6, ct_gold={"STANDARD": 6500, "TURBO": 6500}, **L2)}
CORE = {n for n, _ in perturbations(V1)}
OUT = {}; LAB = {}
for name, P in CFG.items():
    TT = thresholds(B, P)
    def run(units):
        base = {key(u): analyze(u, P, TT)["label"] for u in units}; ag_all = Counter(); ag_core = Counter(); V = perturbations(P); nc = 0
        for vn, Pv in V:
            TTv = thresholds(B, Pv); core = vn in CORE; nc += core
            for u in units:
                if analyze(u, Pv, TTv)["label"] == base[key(u)]: ag_all[key(u)] += 1; ag_core[key(u)] += core
        return base, {k: ag_all[k] / len(V) for k in base}, {k: ag_core[k] / nc for k in base}
    bd, ca, cc = run(UD); bh, ha, hc = run(UH)
    LAB[name] = bd
    def summ(base, conf):
        n = len(base); d = Counter(base_of(l) for l in base.values())
        per = {s: dict(n=sum(1 for l in base.values() if base_of(l) == s), conf=round(st.fmean([conf[k] for k, l in base.items() if base_of(l) == s] or [0]), 3)) for s in ORDER + ("SHORT_WINDOW",)}
        return dict(dist={s: round(100 * d.get(s, 0) / n, 1) for s in ORDER + ("SHORT_WINDOW",)}, mean_conf=round(st.fmean(conf.values()), 3),
                    stable=round(100 * sum(1 for c in conf.values() if c >= .9) / n, 1), unstable=round(100 * sum(1 for c in conf.values() if c < .7) / n, 1), per_shape=per)
    allres = {key(u): analyze(u, P, TT)["label"] for u in CUR}
    t3 = [u for u in UD2 if "T3" in teamA[key(u)]]; lab2 = {key(u): analyze(u, P, TT)["label"] for u in t3}
    OUT[name] = dict(dev_all_variants=summ(bd, ca), dev_core_variants=summ(bd, cc), holdout_all_variants=summ(bh, ha),
                     mirror_mismatch=sum(1 for u in CUR if u["side"] and allres[(u["mid"], False)] != mirror(allres[key(u)])),
                     T3_label_mix=dict(Counter(base_of(l) for l in lab2.values()).most_common()),
                     T3_contradicted=round(100 * sum(1 for u in t3 if (lab2[key(u)] in ("OS_AGAINST", "SE_AGAINST", "ETS_AGAINST") if u["win"] else lab2[key(u)] in ("OS_FOR", "SE_FOR", "ETS_FOR"))) / len(t3), 1))
    o = OUT[name]
    print(f"{name:26s} dev dist {o['dev_all_variants']['dist']} conf all {o['dev_all_variants']['mean_conf']} core {o['dev_core_variants']['mean_conf']} stable {o['dev_all_variants']['stable']} unstable {o['dev_all_variants']['unstable']} | hold conf {o['holdout_all_variants']['mean_conf']} dist {o['holdout_all_variants']['dist']} | mirror {o['mirror_mismatch']} | T3 {o['T3_label_mix']} contra {o['T3_contradicted']}", flush=True)
tr = Counter((base_of(LAB["v1 (sign-agnostic gap)"][k]), base_of(LAB["v2_all"][k])) for k in LAB["v2_all"] if base_of(LAB["v1 (sign-agnostic gap)"][k]) != base_of(LAB["v2_all"][k]))
OUT["v1_to_v2_transitions_dev"] = [(f"{a}->{b}", c) for (a, b), c in tr.most_common()]
print("v1->v2", OUT["v1_to_v2_transitions_dev"])
print("per-shape conf v2 dev", OUT["v2_all"]["dev_all_variants"]["per_shape"])
json.dump(OUT, open("stab_v2_results.json", "w"), indent=1)

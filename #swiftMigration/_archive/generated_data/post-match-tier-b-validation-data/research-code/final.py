"""Freeze the classifier on DEV, then: CT gold guard, all-unit classification + confidence, structure-modifier grid,
holdout evaluation, patch/time drift (older-patch independent sample)."""
import json, pickle, statistics as st, sys
from collections import Counter, defaultdict
from shape import *
from modifiers import modifiers, MP_BASE

DEV, HOLD = split()
CUR = [u for u in U_ALL if u["src"] == "current"]; OLD = [u for u in U_ALL if u["src"] == "old"]
UD = [u for u in CUR if u["mid"] in DEV and u["side"] and not u["feed"]]
UH = [u for u in CUR if u["mid"] in HOLD and u["side"] and not u["feed"]]
UO = [u for u in OLD if u["side"]]
gate = pickle.load(open("tier_a_gate.pkl", "rb"))
teamA = defaultdict(set)
for (mid, slot), cs in gate["FIRE"].items():
    for c in cs: teamA[(mid, slot < 128)].add(c)
OUT = {}
P0 = dict(BASE, phase_bands=True, le_gold_confirm=True, fallback="UNCLEAR")
B = fit_bands(UD, P0); TT0 = thresholds(B, P0)
msg = defaultdict(list)
for u in UD:
    r = analyze(u, P0, TT0)
    if r["label"] != "SHORT_WINDOW": msg[u["bucket"]].append(r["max_sustained_gold"])
GUARDS = {p: {b: pctl(v, p) for b, v in msg.items()} for p in (40, 50, 60, 70, 80)}
OUT["ct_gold_guard_grid"] = {}
for p in (None, 40, 50, 60, 70, 80):
    P = dict(P0, ct_gold=GUARDS[p] if p else None); TT = thresholds(B, P)
    both = [u for u in CUR if u["mid"] in DEV and not u["feed"]]
    labs = {key(u): analyze(u, P, TT)["label"] for u in both}
    t3 = [k for k in labs if "T3" in teamA[k]]; t2 = [k for k in labs if "T2" in teamA[k]]
    OUT["ct_gold_guard_grid"][str(p)] = dict(guard=GUARDS[p] if p else None, CT=round(100 * sum(1 for u in UD if labs[key(u)] == "CT") / len(UD), 1),
                                            UNCLEAR=round(100 * sum(1 for u in UD if labs[key(u)] == "UNCLEAR") / len(UD), 1),
                                            T3_units_labeled_CT=round(100 * sum(1 for k in t3 if labs[k] == "CT") / len(t3), 1),
                                            T2_units_labeled_CT=round(100 * sum(1 for k in t2 if labs[k] == "CT") / len(t2), 1))
print("guard grid", json.dumps(OUT["ct_gold_guard_grid"], indent=0))
ARG = sys.argv[1] if len(sys.argv) > 1 else "60"
if ARG == "v2":
    GUARD_P = "absolute 7500 (both modes) + close_share >= 0.6"
    P_FINAL = dict(P0, ets="both", se_lean=0.8, ct_close=0.6, ct_gold={"STANDARD": 7500, "TURBO": 7500}, le_ref_gold=True, le_gold_floor={"STANDARD": 5000, "TURBO": 8000})
else:
    GUARD_P = int(ARG); P_FINAL = dict(P0, ct_gold=GUARDS[GUARD_P])
TT = thresholds(B, P_FINAL)
OUT["P_FINAL"] = {k: v for k, v in P_FINAL.items()}; OUT["thresholds"] = {f"{k[0]}|bin{k[1]}": v for k, v in TT.items()}
OUT["phase_edges"] = PHASE_EDGES
# ---------- classify everything + confidence ----------
ALLU = CUR + OLD
RES = {key(u): analyze(u, P_FINAL, TT) for u in ALLU}
base, CONF, byvar = stability(ALLU, P_FINAL, B, True)
assert all(base[k] == RES[k]["label"] for k in base)
MODS = {key(u): modifiers(u, RES[key(u)]) for u in ALLU}
OUT["mirror_mismatch"] = dict(current=sum(1 for u in CUR if u["side"] and RES[(u["mid"], False)]["label"] != mirror(RES[key(u)]["label"])),
                              old=sum(1 for u in OLD if u["side"] and RES[(u["mid"], False)]["label"] != mirror(RES[key(u)]["label"])),
                              units_checked=sum(1 for u in ALLU if u["side"]))
def summary(units, name):
    n = len(units); d = Counter(base_of(RES[key(u)]["label"]) for u in units); c = [CONF[key(u)] for u in units]
    return dict(set=name, matches=n, dist={s: round(100 * d.get(s, 0) / n, 1) for s in ORDER + ("SHORT_WINDOW",)}, mean_conf=round(st.fmean(c), 3),
                stable=round(100 * sum(1 for x in c if x >= .9) / n, 1), borderline=round(100 * sum(1 for x in c if .7 <= x < .9) / n, 1), unstable=round(100 * sum(1 for x in c if x < .7) / n, 1),
                by_bucket={b: {s: round(100 * sum(1 for u in units if u["bucket"] == b and base_of(RES[key(u)]["label"]) == s) / max(1, sum(1 for u in units if u["bucket"] == b)), 1) for s in ORDER + ("SHORT_WINDOW",)} for b in ("STANDARD", "TURBO")})
OUT["dev"] = summary(UD, "dev"); OUT["holdout"] = summary(UH, "holdout"); OUT["old_patch"] = summary(UO, "old_patch")
OUT["holdout_accounts"] = {a: summary([u for u in UH if a in ACCT.get(u["mid"], [])], a) for a in HOLD_ACCTS}
# threshold transfer: refit bands on holdout / old sample, compare values and label agreement
for nm, US in (("holdout", UH), ("old_patch", UO)):
    Bx = fit_bands(US, P_FINAL); TTx = thresholds(Bx, P_FINAL)
    agree = sum(1 for u in US if analyze(u, P_FINAL, TTx)["label"] == RES[key(u)]["label"]) / len(US)
    OUT[f"{nm}_refit"] = dict(label_agreement_refit_vs_frozen=round(100 * agree, 1),
                              thresholds={f"{k[0][:3]}|bin{k[1]}": {kk: (round(TT[k][kk], 4), round(v[kk], 4)) for kk, v2 in [("C", 0), ("E", 0), ("S", 0)] for v in [TTx[k]]} for k in TTx if k in TT})
# chronological split inside the current corpus
cur1 = sorted([u for u in CUR if u["side"] and not u["feed"]], key=lambda u: u["start"])
h = len(cur1) // 2
OUT["chronology"] = dict(patches=dict(Counter(u["patch"] for u in cur1)), early=summary(cur1[:h], "early_half"), late=summary(cur1[h:], "late_half"))
# ---------- structure modifiers ----------
def mod_rates(units, MP):
    n = len(units); out = Counter(); byshape = defaultdict(Counter); shp = Counter()
    for u in units:
        r = RES[key(u)]; m = modifiers(u, r, MP); s = base_of(r["label"]); shp[s] += 1
        for kk in m: out[kk] += 1; byshape[s][kk] += 1
    return dict(overall={kk: round(100 * v / n, 1) for kk, v in out.items()}, by_shape={s: {kk: round(100 * v / shp[s], 1) for kk, v in c.items()} for s, c in byshape.items()})
grid = []
for ak in (1, 2, 3):
    for lag in (0, 2):
        grid.append(dict(axis="align/counter k, lag", align_k=ak, counter_k=ak, lag=lag, **mod_rates(UD, dict(MP_BASE, align_k=ak, counter_k=ak, lag=lag))))
for nm_, tol in (((8, 5), 0), ((8, 5), 1), ((6, 4), 0), ((10, 6), 0)):
    grid.append(dict(axis="no-conversion", nsc_min=nm_, nsc_tol=tol, **mod_rates(UD, dict(MP_BASE, nsc_min={"STANDARD": nm_[0], "TURBO": nm_[1]}, nsc_tol=tol))))
for bn in (2, 3, 4):
    for bw in (3, 5, 7):
        grid.append(dict(axis="burst", burst_n=bn, burst_w=bw, **mod_rates(UD, dict(MP_BASE, burst_n=bn, burst_w=bw))))
OUT["modifier_grid"] = grid
OUT["modifier_holdout_base"] = mod_rates(UH, MP_BASE); OUT["modifier_old_base"] = mod_rates(UO, MP_BASE)
for g in grid: print({k: v for k, v in g.items() if k not in ("by_shape",)})
print(json.dumps({k: OUT[k] for k in ("mirror_mismatch", "dev", "holdout", "old_patch")}, indent=0))
print(json.dumps(OUT["holdout_refit"], indent=0)[:1500]); print(json.dumps(OUT["old_patch_refit"], indent=0)[:1500])
print(json.dumps(OUT["chronology"], indent=0)[:2500]); print(json.dumps(OUT["holdout_accounts"], indent=0)[:1600])
print("modifier by shape (dev, base MP)", json.dumps(mod_rates(UD, MP_BASE)["by_shape"], indent=0))
json.dump(OUT, open("final_results.json", "w"), indent=1, default=str)
pickle.dump(dict(P_FINAL=P_FINAL, B=B, TT=TT, RES=RES, CONF=CONF, MODS=MODS, DEV=DEV, HOLD=HOLD, GUARD_P=GUARD_P, byvar=byvar), open("final.pkl", "wb"))

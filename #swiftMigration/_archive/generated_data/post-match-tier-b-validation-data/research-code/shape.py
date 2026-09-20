"""Tier B match-shape classifier (research, deterministic, sign-symmetric by construction).

Unit = one team perspective of one match. R(t) = (team NW - enemy NW) / (team NW + enemy NW) at t:00.
The opposite perspective has exactly R' = -R, so every rule is written as s * value with s in {+1, -1}.
"""
from __future__ import annotations
import math, pickle, random, statistics as st
from collections import Counter, defaultdict

D = pickle.load(open("units.pkl", "rb"))
U_ALL = D["U"]; ACCT = D["acct_of"]
HOLD_ACCTS = ("acct2", "acct6")   # one Standard-heavy and one Turbo-heavy tracked account, held out completely
ORDER = ("ETS", "LE", "DR", "OS", "SE", "SWAP", "CT", "UNCLEAR")
PHASE_EDGES = {"STANDARD": (20, 30, 40), "TURBO": (14, 20, 26)}

BASE = dict(smooth="med3", start={"STANDARD": 10, "TURBO": 8}, start_shift=0, end_excl=3, min_window=9,
            close_p=50, edge_p=70, strong_p=90, stay_p=None, run=3, phase_bands=False,
            ets="thirds", ets_close=.65, ets_sep=.30, ets_final=.60, ets_clean=True,
            erosion=.50, ref="peak", late_k=3, le_start_frac=2 / 3, le_below_edge=False, le_gold_confirm=False,
            os_share=.70, os_first=.33, os_struct=3, os_strong_min=3, os_mode="strong_or_struct",
            se_share=.50, ct_close=None, priority=("ETS", "LE", "DR", "OS", "SE", "SWAP", "CT"), fallback="CT")

def key(u): return (u["mid"], u["side"])
def pctl(v, p):
    v = sorted(v); return v[min(len(v) - 1, max(0, int(round(p / 100 * (len(v) - 1)))))]

def split():
    """~70/30 development/holdout. Holdout = two complete tracked accounts + stratified random matches."""
    cur = [u for u in U_ALL if u["src"] == "current" and not u["feed"] and u["side"]]
    info = {u["mid"]: u for u in cur}; mids = sorted(info)
    hold = {m for m in mids if set(ACCT.get(m, [])) & set(HOLD_ACCTS)}
    rest = [m for m in mids if m not in hold]
    target = round(0.30 * len(mids)) - len(hold)
    by_b = defaultdict(list)
    for m in rest: by_b[info[m]["bucket"]].append(info[m]["dur"])
    terc = {b: (pctl(v, 100 / 3), pctl(v, 200 / 3)) for b, v in by_b.items()}
    strata = defaultdict(list)
    for m in rest:
        u = info[m]; t = terc[u["bucket"]]; d = 0 if u["dur"] <= t[0] else (1 if u["dur"] <= t[1] else 2)
        strata[(u["bucket"], d, u["win"])].append(m)
    rng = random.Random(20260915); frac = target / len(rest)
    for k in sorted(strata):
        lst = sorted(strata[k]); rng.shuffle(lst); hold |= set(lst[:round(frac * len(lst))])
    return set(mids) - hold, hold

def smooth(x, how):
    if how == "raw": return list(x)
    k = 2 if how == "med5" else 1
    f = st.median if how.startswith("med") else st.fmean
    return [f(x[max(0, i - k):i + k + 1]) for i in range(len(x))]

def excl_of(P, b): return P["end_excl"][b] if isinstance(P["end_excl"], dict) else P["end_excl"]
def window(u, P):
    S = P["start"][u["bucket"]] + P.get("start_shift", 0)
    Emin = min(len(u["R"]) - 1, (u["dur"] - excl_of(P, u["bucket"]) * 60) // 60)
    return S, Emin, Emin - S + 1

def series(u, P):
    S, Emin, n = window(u, P)
    return S, Emin, n, smooth(u["R"][:Emin + 1], P["smooth"])[S:Emin + 1] if n > 0 else []

def phase_bin(b, minute, P): return sum(1 for e in PHASE_EDGES[b] if minute >= e) if P.get("phase_bands") else 0

def fit_bands(units, P):
    vals = defaultdict(list)
    for u in units:
        if not u["side"]: continue          # |R| identical for both perspectives
        S, Emin, n, a = series(u, P)
        if n < P["min_window"]: continue
        for i, v in enumerate(a): vals[(u["bucket"], phase_bin(u["bucket"], S + i, P))].append(abs(v))
    return {k: sorted(v) for k, v in vals.items()}

def thresholds(B, P):
    q = lambda v, p: v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))]
    return {k: dict(C=q(v, P["close_p"]), E=q(v, P["edge_p"]), S=q(v, P["strong_p"]), ES=q(v, P["stay_p"] if P.get("stay_p") else P["edge_p"])) for k, v in B.items()}

def runs_of(state, k):
    out = []; i = 0; n = len(state)
    while i < n:
        j = i
        while j + 1 < n and state[j + 1] == state[i]: j += 1
        if state[i] != 0 and j - i + 1 >= k: out.append((state[i], i, j))
        i = j + 1
    return out

def net_structs(u, t0, t1):
    """Net structures FOR this perspective (enemy towers/barracks lost minus ours) with t0 <= time < t1 (seconds)."""
    return sum(-1 if us else 1 for t, us, k, tier in u["structs"] if t0 <= t < t1)

def dname(name, s): return name if name in ("LE", "DR", "CT") else f"{name}_{'FOR' if s > 0 else 'AGAINST'}"
MIRROR_BASE = {"LE": "DR", "DR": "LE", "CT": "CT", "SHORT_WINDOW": "SHORT_WINDOW", "UNCLEAR": "UNCLEAR"}
def mirror(label):
    if label in MIRROR_BASE: return MIRROR_BASE[label]
    n, d = label.rsplit("_", 1); return f"{n}_{'AGAINST' if d == 'FOR' else 'FOR'}"
def base_of(label): return label if label in ("LE", "DR", "CT", "SHORT_WINDOW", "UNCLEAR") else label.rsplit("_", 1)[0]

def analyze(u, P, TT):
    b = u["bucket"]; S, Emin, n, a = series(u, P)
    out = dict(mid=u["mid"], side=u["side"], bucket=b, n=n, S=S, Emin=Emin)
    if n < P["min_window"]:
        out.update(label="SHORT_WINDOW", raw={}, runs=[], detail={}, dir=0); return out
    Ts = [TT[(b, phase_bin(b, S + i, P))] for i in range(n)]
    C = [t["C"] for t in Ts]; E = [t["E"] for t in Ts]; SS = [t["S"] for t in Ts]; ES = [t["ES"] for t in Ts]
    state = []; cur = 0
    for i, v in enumerate(a):
        if cur and cur * v >= ES[i]: pass
        elif v >= E[i]: cur = 1
        elif v <= -E[i]: cur = -1
        else: cur = 0
        state.append(cur)
    runs = runs_of(state, P["run"])
    rs = {s: [r for r in runs if r[0] == s] for s in (1, -1)}
    inrun = {1: set(), -1: set()}
    for s, i, j in runs: inrun[s].update(range(i, j + 1))
    es = {s: len(inrun[s]) / n for s in (1, -1)}
    close = [abs(v) <= C[i] for i, v in enumerate(a)]; close_share = sum(close) / n
    smax = {1: 0, -1: 0}
    for s, i, j in runs_of([1 if v >= SS[i] else (-1 if v <= -SS[i] else 0) for i, v in enumerate(a)], 1): smax[s] = max(smax[s], j - i + 1)
    k = P["run"]; msl = 0.0
    for i in range(n - k + 1):
        seg = a[i:i + k]
        if all(v > 0 for v in seg) or all(v < 0 for v in seg): msl = max(msl, min(abs(v) for v in seg))
    lc = u["lc"]; msg = 0
    for i in range(n - k + 1):
        msg = max(msg, min(abs(v) for v in lc[S + i:S + i + k]))   # largest gap (either direction) held for k straight minutes
    out["max_sustained_gold"] = msg
    band = [1 if v > C[i] else (-1 if v < -C[i] else 0) for i, v in enumerate(a)]; nz = [x for x in band if x]
    lead_changes = sum(1 for x, y in zip(nz, nz[1:]) if x != y)
    net_for = net_structs(u, S * 60, (Emin + 1) * 60)
    out.update(close_share=close_share, es_for=es[1], es_against=es[-1], strong_for=smax[1], strong_against=smax[-1], max_sustained_lead=msl,
               latest_close_minute=(S + max(i for i, c in enumerate(close) if c)) if any(close) else None,
               first_edge_minute=(S + runs[0][1]) if runs else None, lead_changes=lead_changes, net_structs_for=net_for,
               runs=[(s, S + i, S + j) for s, i, j in runs], end_R=a[-1], peak_for=max(a), peak_against=-min(a), edge_thr=E[0], close_thr=C[0])
    raw = {}
    t3 = max(1, n // 3); half = n // 2; h = math.ceil(n * P["le_start_frac"])
    lc = u["lc"]
    for s in (1, -1):
        # ---- EVEN_THEN_SEPARATED
        if P["ets"] == "thirds":
            sep = next((r for r in rs[s] if r[1] >= P["ets_sep"] * n), None)
            if sep and sum(close[:t3]) / t3 >= P["ets_close"]:
                earlier = [r for r in runs if r[1] < sep[1]]
                final = sum(1 for i in range(n - t3, n) if i in inrun[s]) / t3
                if not (P["ets_clean"] and earlier) and final >= P["ets_final"] and not [r for r in rs[-s] if r[1] >= sep[1]]:
                    raw[("ETS", s)] = dict(sep_minute=S + sep[1], close_share_before=sum(close[:sep[1]]) / max(1, sep[1]), edge_share_after=final,
                                           lead_before=st.median(a[:sep[1]]) if sep[1] else 0, lead_after=st.median(a[sep[1]:]), structs_after=s * net_structs(u, (S + sep[1]) * 60, (Emin + 1) * 60))
        if P["ets"] in ("transition", "both") and ("ETS", s) not in raw:
            if runs and runs[0][0] == s:
                tau = runs[0][1]
                if tau >= max(P["ets_sep"] * n, 3):
                    pre = sum(close[:tau]) / tau; post = sum(1 for i in range(tau, n) if i in inrun[s]) / (n - tau)
                    if pre >= P["ets_close"] and post >= P["ets_final"] and not rs[-s] and n - tau >= P["run"]:
                        raw[("ETS", s)] = dict(sep_minute=S + tau, close_share_before=pre, edge_share_after=post, lead_before=st.median(a[:tau]),
                                               lead_after=st.median(a[tau:]), structs_after=s * net_structs(u, (S + tau) * 60, (Emin + 1) * 60))
        # ---- LEAD_ERODED (s=+1: our lead) / DEFICIT_RECOVERED (s=-1: their lead, seen from us)
        early = [r for r in rs[s] if r[1] < h]
        if early and not rs[-s]:
            seg = [s * v for v in a[:h]]
            if P["ref"] == "peak": ref = max(seg)
            elif P["ref"] == "p90": ref = pctl(seg, 90)
            else: ref = max(st.median([s * v for v in a[i:j + 1]]) for _, i, j in early)
            late = st.median([s * v for v in a[-P["late_k"]:]])
            pk = max(range(h), key=lambda i: s * a[i])
            if P.get("le_ref_gold"): pk = max(range(h), key=lambda i: s * lc[S + i])   # report/confirm against the gold peak, not the relative peak
            g_ref = s * lc[S + pk]; g_late = st.median([s * lc[t] for t in range(Emin - P["late_k"] + 1, Emin + 1)])
            gold_ok = (not P["le_gold_confirm"]) or (g_ref > 0 and (g_ref - g_late) / g_ref >= P["erosion"])
            if P.get("le_gold_floor") and g_ref < P["le_gold_floor"][b]: gold_ok = False
            if ref > 0 and (ref - late) / ref >= P["erosion"] and (not P["le_below_edge"] or late < E[-1]) and gold_ok:
                raw[("LE" if s > 0 else "DR", s)] = dict(ref=ref, ref_minute=S + pk, late=late, erosion=(ref - late) / ref, gold_ref=g_ref, gold_late=g_late,
                                                        structs_after_peak=s * net_structs(u, (S + pk) * 60, (Emin + 1) * 60))
        # ---- ONE_SIDED
        if rs[s] and es[s] >= P["os_share"] and rs[s][0][1] <= P["os_first"] * n and not rs[-s]:
            extra = {"strong_or_struct": smax[s] >= P["os_strong_min"] or s * net_for >= P["os_struct"], "strong": smax[s] >= P["os_strong_min"], "share_only": True}[P["os_mode"]]
            if extra: raw[("OS", s)] = dict(edge_share=es[s], first_edge_minute=S + rs[s][0][1], strong_minutes=smax[s], net_structs=s * net_for)
        # ---- STEADY_EDGE
        if es[s] >= P["se_share"] and s * st.median(a[:half]) > 0 and s * st.median(a[half:]) > 0 and not rs[-s]:
            raw[("SE", s)] = dict(edge_share=es[s], first_edge_minute=S + rs[s][0][1] if rs[s] else None, net_structs=s * net_for, path="edge_share")
        elif P.get("se_lean") and not rs[-s] and sum(1 for v in a if s * v > 0) / n >= P["se_lean"] and s * st.median(a) >= st.median(C) \
                and s * st.median(a[:half]) > 0 and s * st.median(a[half:]) > 0:
            raw[("SE", s)] = dict(edge_share=es[s], first_edge_minute=S + rs[s][0][1] if rs[s] else None, net_structs=s * net_for, path="lean",
                                  ahead_share=sum(1 for v in a if s * v > 0) / n, median_lead=s * st.median(a))
    if rs[1] and rs[-1]:
        s = runs[-1][0]; raw[("SWAP", s)] = dict(n_runs=len(runs), first=runs[0], last=runs[-1])
    if not runs and (P["ct_close"] is None or close_share >= P["ct_close"]) and (not P.get("ct_gold") or msg < P["ct_gold"][b]):
        raw[("CT", 0)] = dict(close_share=close_share, max_sustained_lead=msl)
    out["raw"] = raw
    for name in P["priority"]:
        hit = [(nm, s) for nm, s in raw if nm == name]
        if hit:
            nm, s = hit[0]; out["label"] = dname(nm, s); out["detail"] = raw[hit[0]]; out["dir"] = s; break
    else:
        out["label"] = P["fallback"]; out["detail"] = {}; out["dir"] = 0
    return out

def perturbations(P):
    V = []
    for k in ("close_p", "edge_p", "strong_p"):
        for d in (-5, 5):
            extra = {"stay_p": P["stay_p"] + d} if (k == "edge_p" and P.get("stay_p")) else {}
            V.append((f"{k}{d:+d}", dict(P, **{k: P[k] + d}, **extra)))
    for d in (-1, 1): V.append((f"run{d:+d}", dict(P, run=max(1, P["run"] + d))))
    for k in ("os_share", "se_share", "ets_close", "ets_final"):
        for d in (-.05, .05): V.append((f"{k}{d:+.2f}", dict(P, **{k: P[k] + d})))
    for d in (-.10, .10): V.append((f"erosion{d:+.2f}", dict(P, erosion=P["erosion"] + d)))
    for d in (-2, -1, 1, 2): V.append((f"start{d:+d}", dict(P, start_shift=d)))
    for d in (-2, -1, 1, 2):
        ex = P["end_excl"]
        V.append((f"end{d:+d}", dict(P, end_excl=({b: max(0, v + d) for b, v in ex.items()} if isinstance(ex, dict) else max(0, ex + d)))))
    if P.get("ct_close"):
        for d in (-.05, .05): V.append((f"ct_close{d:+.2f}", dict(P, ct_close=P["ct_close"] + d)))
    if P.get("se_lean"):
        for d in (-.05, .05): V.append((f"se_lean{d:+.2f}", dict(P, se_lean=P["se_lean"] + d)))
    if isinstance(P.get("ct_gold"), dict):
        for d in (-1000, 1000): V.append((f"ct_gold{d:+d}", dict(P, ct_gold={b: v + d for b, v in P["ct_gold"].items()})))
    if P.get("le_gold_floor"):
        for d in (-1000, 1000): V.append((f"le_gold_floor{d:+d}", dict(P, le_gold_floor={b: v + d for b, v in P["le_gold_floor"].items()})))
    return V

def stability(units, P, B, per_variant=False):
    """Thresholds stay those fitted with P (production freezes values); only the rule parameters move."""
    base = {key(u): analyze(u, P, thresholds(B, P))["label"] for u in units}
    agree = Counter(); byvar = {}
    V = perturbations(P)
    for name, Pv in V:
        TTv = thresholds(B, Pv); same = 0
        for u in units:
            if analyze(u, Pv, TTv)["label"] == base[key(u)]: agree[key(u)] += 1; same += 1
        byvar[name] = same / len(units)
    conf = {k: agree[k] / len(V) for k in base}
    return (base, conf, byvar) if per_variant else (base, conf)

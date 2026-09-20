import json, itertools, random, statistics as st
from collections import defaultdict
exec(open("rank_eval.py").read().split("# ---- full-sample")[0])
LEAD_SUB = {"LEAD_FLIP", "LATE_REVERSAL", "DEFICIT_RECOVERED", "LEAD_ERODED"}
def guard(cards):
    """specific Match-Lead-Story guard: if COMEBACK_WIN/LOST_FROM_AHEAD present, drop weaker lead-story subtypes"""
    if any(c["cid"] in ("COMEBACK_WIN", "LOST_FROM_AHEAD") for c in cards):
        return [c for c in cards if c["cid"] not in LEAD_SUB]
    return cards
def gold_after(it, kept):
    ks = {c["label"] for c in kept}
    return [l for l in gold[it["i"]] if l in ks]
def evalf(keyf, subset, use_guard=True, rng=None):
    top1 = ok = n = 0; t3 = []; cnt = 0; bad = 0
    for it in subset:
        cards = guard(it["cards"]) if use_guard else it["cards"]
        if len(cards) < 2: continue
        g = gold_after(it, cards)
        cc = list(cards)
        if rng: rng.shuffle(cc)
        m = [c["label"] for c in sorted(cc, key=keyf)]
        cnt += 1; top1 += g[0] == m[0]; pos = {l: k for k, l in enumerate(m)}
        for a, b in itertools.combinations(g, 2): n += 1; ok += pos[a] < pos[b]
        if len(g) >= 4:
            t3.append(len(set(g[:3]) & set(m[:3])) / 3)
            bad += g[-1] in m[:3] and any(x not in m[:3] for x in g[:2])
    return dict(n=cnt, top1=round(100 * top1 / cnt, 1), pairwise=round(100 * ok / n, 1), top3=round(100 * st.mean(t3), 1) if t3 else None, bad=bad)
C1 = {"COMEBACK_WIN", "LOST_FROM_AHEAD"}; C3 = {"ENEMY_EARLY_ITEM", "DEFICIT_RECOVERED", "VISION_REGION_SWEEP"}
def k_class(c): return 1 if c["cid"] in C1 else (3 if c["cid"] in C3 else 2)
V = {
 "bands only (band>lvl)": lambda c: (-c["band"], -c["lvl"]),
 "exceedance only": lambda c: (-c["exc"],),
 "class only (random ties)": lambda c: (k_class(c),),
 "class>band (random ties)": lambda c: (k_class(c), -c["band"]),
 "class>band>lvl": lambda c: (k_class(c), -c["band"], -c["lvl"], c["cid"]),
 "class>lvl": lambda c: (k_class(c), -c["lvl"], c["cid"]),
 "2-class (C1 vs rest)>band>lvl": lambda c: (c["cid"] not in C1, -c["band"], -c["lvl"], c["cid"]),
 "class(+ETS in C1)>band>lvl": lambda c: (1 if c["cid"] in C1 | {"EVEN_THEN_SEPARATED"} else k_class(c), -c["band"], -c["lvl"], c["cid"]),
 "class(no C3)>band>lvl = C1 then band": lambda c: (0 if c["cid"] in C1 else 1, -c["band"], -c["lvl"], c["cid"]),
}
out = {}
for name, kf in V.items():
    rs = [evalf(kf, items, True, random.Random(s)) for s in range(50)] if "random" in name else [evalf(kf, items, True)]
    out[name] = {m: round(st.mean(r[m] for r in rs), 1) if rs[0][m] is not None else None for m in ("n", "top1", "pairwise", "top3", "bad")}
    print(f"{name:40s}", out[name])
print("no guard, class>band>lvl:", evalf(V["class>band>lvl"], items, False))
print("no guard, bands only:", evalf(V["bands only (band>lvl)"], items, False))
# 2-fold CV of the class assignment: classes learned from the other half by standalone mean position thresholds
def learn(train):
    sc = defaultdict(list)
    for it in train:
        cards = guard(it["cards"]); g = gold_after(it, cards)
        if len(g) < 2: continue
        lab = {c["label"]: c["cid"] for c in cards}
        for k, l in enumerate(g): sc[lab[l]].append(k / (len(g) - 1))
    m = {c: st.mean(v) for c, v in sc.items() if len(v) >= 3}
    return {c for c, v in m.items() if v <= 0.15}, {c for c, v in m.items() if v >= 0.80}
cvres = []
for seed in range(20):
    rng = random.Random(seed); idx = list(items); rng.shuffle(idx); A, B = idx[::2], idx[1::2]
    for tr, te in ((A, B), (B, A)):
        c1, c3 = learn(tr)
        kf = lambda c, c1=c1, c3=c3: (1 if c["cid"] in c1 else (3 if c["cid"] in c3 else 2), -c["band"], -c["lvl"], c["cid"])
        cvres.append((evalf(kf, te), sorted(c1), sorted(c3)))
print("CV class>band>lvl:", {m: round(st.mean(r[0][m] for r in cvres), 1) for m in ("top1", "pairwise")})
from collections import Counter
print("learned C1 sets:", Counter(tuple(r[1]) for r in cvres).most_common(4))
print("learned C3 sets:", Counter(tuple(r[2]) for r in cvres).most_common(4))
json.dump(dict(variants=out), open("rank_results3.json", "w"), indent=1)

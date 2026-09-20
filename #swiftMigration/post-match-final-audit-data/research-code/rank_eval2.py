import json, itertools, random, statistics as st
from collections import defaultdict, Counter
exec(open("rank_eval.py").read().split("# ---- full-sample")[0])
# standalone value: exclude dup-losers
score = defaultdict(list); duploss = Counter()
for it in items:
    g = gold[it["i"]]; lab = {c["label"]: c["cid"] for c in it["cards"]}
    losers = set()
    for a, b in dups[it["i"]]:
        losers.add(a if g.index(a) > g.index(b) else b)
    g2 = [l for l in g if l not in losers]
    for l in losers: duploss[(lab[l], lab[[x for x in g if x not in losers][0]])] += 1
    if len(g2) < 2: continue
    for k, l in enumerate(g2): score[lab[l]].append(k / (len(g2) - 1))
print("standalone mean position:", sorted(((c, round(st.mean(v), 2), len(v)) for c, v in score.items()), key=lambda x: x[1]))
print("dup losers (loser, winner-top):", duploss.most_common())
# same-story pairs observed
pairs = Counter()
for it in items:
    lab = {c["label"]: c["cid"] for c in it["cards"]}; g = gold[it["i"]]
    for a, b in dups[it["i"]]:
        w, l = (a, b) if g.index(a) < g.index(b) else (b, a)
        pairs[(lab[w], lab[l])] += 1
print("dup pairs winner>loser:", pairs.most_common())
CLASSES = {
 "C3": {1: ["COMEBACK_WIN", "LOST_FROM_AHEAD", "LEAD_FLIP", "LATE_REVERSAL", "EVEN_THEN_SEPARATED", "OWN_LANE_VS_USUAL", "OWN_ITEM_VS_HISTORY"],
        2: ["ENEMY_STACKING", "ENEMY_SMOKE_VOLUME", "VISION_QUICK_CLEARS", "ENEMY_EARLY_RICH", "CLOSE_MOST_OF_GAME", "OPP_START_VS_HISTORY", "LEAD_ERODED"],
        3: ["ENEMY_EARLY_ITEM", "DEFICIT_RECOVERED", "VISION_REGION_SWEEP"]},
 "C2": {1: ["COMEBACK_WIN", "LOST_FROM_AHEAD", "LEAD_FLIP", "LATE_REVERSAL", "EVEN_THEN_SEPARATED", "OWN_LANE_VS_USUAL", "OWN_ITEM_VS_HISTORY",
            "ENEMY_STACKING", "ENEMY_SMOKE_VOLUME", "VISION_QUICK_CLEARS"],
        2: ["ENEMY_EARLY_RICH", "CLOSE_MOST_OF_GAME", "OPP_START_VS_HISTORY", "LEAD_ERODED", "ENEMY_EARLY_ITEM", "DEFICIT_RECOVERED", "VISION_REGION_SWEEP"]},
 "C3s": {1: ["COMEBACK_WIN", "LOST_FROM_AHEAD"],
         2: ["LEAD_FLIP", "LATE_REVERSAL", "EVEN_THEN_SEPARATED", "OWN_LANE_VS_USUAL", "OWN_ITEM_VS_HISTORY", "ENEMY_STACKING", "ENEMY_SMOKE_VOLUME", "VISION_QUICK_CLEARS", "ENEMY_EARLY_RICH", "CLOSE_MOST_OF_GAME", "OPP_START_VS_HISTORY", "LEAD_ERODED"],
         3: ["ENEMY_EARLY_ITEM", "DEFICIT_RECOVERED", "VISION_REGION_SWEEP"]},
}
def cls(C, cid): return next(k for k, v in C.items() if cid in v)
def variants():
    V = {}
    for cn, C in CLASSES.items():
        V[f"{cn}: class>band>lvl"] = rank_by(lambda c, C=C: (cls(C, c["cid"]), -c["band"], -c["lvl"], c["cid"]))
        V[f"{cn}: class-promote(EXTREME +1)>band>lvl"] = rank_by(lambda c, C=C: (cls(C, c["cid"]) - (1 if c["band"] == 3 else 0), -c["band"], -c["lvl"], c["cid"]))
        V[f"{cn}: additive class+(3-band)"] = rank_by(lambda c, C=C: (cls(C, c["cid"]) + (3 - c["band"]) * 0.5, -c["lvl"], c["cid"]))
        V[f"{cn}: class>lvl"] = rank_by(lambda c, C=C: (cls(C, c["cid"]), -c["lvl"], c["cid"]))
    return V
def strip_dups(it, model_order):
    g = gold[it["i"]]; losers = set()
    for a, b in dups[it["i"]]: losers.add(a if g.index(a) > g.index(b) else b)
    return [l for l in g if l not in losers], [l for l in model_order if l not in losers]
res = {}
for name, f in variants().items():
    res[name] = metrics(f, items)
    # after removing dup-losers from both lists (same-story guard assumed)
    ok = n = t1 = 0; t3 = []
    for it in items:
        g2, m2 = strip_dups(it, f(it["cards"]))
        if len(g2) < 2: continue
        t1 += g2[0] == m2[0]; pos = {l: k for k, l in enumerate(m2)}
        for a, b in itertools.combinations(g2, 2): n += 1; ok += pos[a] < pos[b]
        if len(g2) >= 4: t3.append(len(set(g2[:3]) & set(m2[:3])) / 3)
    res[name]["nodup_pairwise"] = round(100 * ok / n, 1); res[name]["nodup_top1_n"] = t1
    print(f"{name:45s}", res[name])
json.dump(res, open("rank_results2.json", "w"), indent=1)
# failures of the chosen candidate
f = variants()["C3: class-promote(EXTREME +1)>band>lvl"]
print("\nFAILURES (top-1 mismatch) for C3 promote:")
for it in items:
    g = gold[it["i"]]; m = f(it["cards"])
    if g[0] != m[0]:
        lab = {c["label"]: (c["cid"], c["band"]) for c in it["cards"]}
        print(it["i"], "gold", [lab[x] for x in g], "| model top", lab[m[0]])

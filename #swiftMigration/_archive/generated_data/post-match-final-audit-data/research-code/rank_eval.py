"""Evaluate simple threshold-based rankers against the manual gold ranking."""
import json, itertools, random, statistics as st
from collections import defaultdict
items = json.load(open("rank_items.json"))
gold = {}
dups = {}
for line in open("rank_gold.txt"):
    line = line.strip()
    if not line or line.startswith("#"): continue
    parts = line.split()
    i = int(parts[0]); gold[i] = parts[1].split(">")
    dups[i] = [tuple(p[4:].split("=")) for p in parts[2:] if p.startswith("dup:")]
assert len(gold) == len(items)
for it in items:
    assert sorted(gold[it["i"]]) == sorted(c["label"] for c in it["cards"]), it["i"]

STORY = {"COMEBACK_WIN", "LOST_FROM_AHEAD"}
def feat(c): return c
def rank_by(key):
    def f(cards): return [c["label"] for c in sorted(cards, key=key)]
    return f
TYPEORDER_DEFAULT = ["COMEBACK_WIN", "LOST_FROM_AHEAD", "LEAD_FLIP", "OPP_START_VS_HISTORY", "OWN_LANE_VS_USUAL", "OWN_ITEM_VS_HISTORY",
                     "ENEMY_STACKING", "VISION_QUICK_CLEARS", "ENEMY_SMOKE_VOLUME", "ENEMY_EARLY_RICH", "LATE_REVERSAL", "CLOSE_MOST_OF_GAME",
                     "EVEN_THEN_SEPARATED", "DEFICIT_RECOVERED", "LEAD_ERODED", "VISION_REGION_SWEEP", "ENEMY_EARLY_ITEM"]
def mk_models(prio):
    P = {c: i for i, c in enumerate(prio)}
    return {
        "M1 band>lvl": rank_by(lambda c: (-c["band"], -c["lvl"], c["cid"])),
        "M1b band>exc": rank_by(lambda c: (-c["band"], -c["exc"], c["cid"])),
        "M2 exceedance ratio": rank_by(lambda c: (-c["exc"], c["cid"])),
        "M3 piecewise level": rank_by(lambda c: (-c["lvl"], c["cid"])),
        "M1+tierA tiebreak": rank_by(lambda c: (-c["band"], c["tier"] != "A", -c["lvl"], c["cid"])),
        "M4 band>type priority": rank_by(lambda c: (-c["band"], P.get(c["cid"], 99), -c["lvl"])),
        "M5 type priority only": rank_by(lambda c: (P.get(c["cid"], 99), -c["band"], -c["lvl"])),
        "M6 priority class>band": rank_by(lambda c: (PCLASS(c["cid"], P), -c["band"], -c["lvl"])),
    }
def PCLASS(cid, P):
    # 3 coarse classes derived from the learned order (top third / middle / bottom)
    n = len(P); p = P.get(cid, n)
    return 0 if p < n / 3 else (1 if p < 2 * n / 3 else 2)
def metrics(model, subset):
    top1 = pair_ok = pair_n = 0; top3 = []; taus = []; bad = 0; n4 = 0
    for it in subset:
        g = gold[it["i"]]; m = model(it["cards"])
        top1 += g[0] == m[0]
        pos = {l: k for k, l in enumerate(m)}
        ok = n = 0
        for a, b in itertools.combinations(g, 2):   # a ranked above b in gold
            n += 1; ok += pos[a] < pos[b]
        pair_ok += ok; pair_n += n
        taus.append((2 * ok - n) / n)
        if len(g) >= 4:
            n4 += 1; top3.append(len(set(g[:3]) & set(m[:3])) / 3)
            if g[-1] in m[:3] and any(x not in m[:3] for x in g[:2]): bad += 1
    return dict(top1=round(100 * top1 / len(subset), 1), pairwise=round(100 * pair_ok / pair_n, 1), kendall=round(st.mean(taus), 3),
                top3_set=round(100 * st.mean(top3), 1) if top3 else None, bad_displacement=bad, n4=n4)
def learn_priority(train):
    score = defaultdict(list)
    for it in train:
        g = gold[it["i"]]; L = len(g)
        lab2cid = {c["label"]: c["cid"] for c in it["cards"]}
        for k, l in enumerate(g): score[lab2cid[l]].append(k / (L - 1))
    order = sorted(TYPEORDER_DEFAULT, key=lambda c: (st.mean(score[c]) if score[c] else 0.5, TYPEORDER_DEFAULT.index(c)))
    return order, {c: (round(st.mean(v), 2), len(v)) for c, v in score.items()}
# ---- full-sample (in-sample) results with a priority learned on all items (upper bound) and 2-fold CV
res = {}
order_all, sc = learn_priority(items)
print("learned mean normalized gold position (0=top):", sorted(sc.items(), key=lambda kv: kv[1][0]))
rng = random.Random(1); idx = list(items); rng.shuffle(idx)
folds = [idx[::2], idx[1::2]]
for name in mk_models(order_all):
    full = metrics(mk_models(order_all)[name], items)
    cv = []
    for k in (0, 1):
        o, _ = learn_priority(folds[1 - k]); cv.append(metrics(mk_models(o)[name], folds[k]))
    cvm = {m: round(st.mean(x[m] for x in cv), 1) if cv[0][m] is not None else None for m in ("top1", "pairwise", "top3_set")}
    res[name] = dict(in_sample=full, cv=cvm)
# random baseline
rb = []
for s in range(200):
    r = random.Random(s)
    rb.append(metrics(lambda cards: r.sample([c["label"] for c in cards], len(cards)), items))
res["M0 random"] = dict(in_sample={m: round(st.mean(x[m] for x in rb), 1) for m in ("top1", "pairwise", "top3_set", "kendall", "bad_displacement")})
for k, v in res.items(): print(f"{k:26s}", v)
# subsets: tier A vs B competition, enemy vs own, history vs non-history
def sub(pred): return [it for it in items if pred(it)]
SUBS = {"TierA_vs_TierB": sub(lambda it: len({c["tier"] for c in it["cards"]}) == 2),
        "history_vs_nonhistory": sub(lambda it: any(c["cid"].endswith(("HISTORY", "USUAL")) for c in it["cards"]) and any(not c["cid"].endswith(("HISTORY", "USUAL")) for c in it["cards"])),
        "enemy_vs_match_or_own": sub(lambda it: any(c["side"] == "enemy" for c in it["cards"]) and any(c["side"] != "enemy" for c in it["cards"])),
        ">=3 cards": sub(lambda it: len(it["cards"]) >= 3), ">=4 cards": sub(lambda it: len(it["cards"]) >= 4)}
out = dict(overall=res, subsets={}, learned=sc, order=order_all)
for sn, s in SUBS.items():
    out["subsets"][sn] = {name: metrics(f, s) for name, f in mk_models(order_all).items() if name in ("M1 band>lvl", "M2 exceedance ratio", "M3 piecewise level", "M4 band>type priority", "M6 priority class>band")}
    out["subsets"][sn]["n"] = len(s)
    print(sn, len(s), {k: (v["top1"], v["pairwise"]) for k, v in out["subsets"][sn].items() if k != "n"})
json.dump(out, open("rank_results.json", "w"), indent=1)

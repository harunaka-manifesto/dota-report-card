import pickle, json, random, sys
from collections import Counter, defaultdict
import pool as P
P.G["v2"] = True
R = [r for r in P.D["rows"] if not r["feed"]]
IDX = {(r["mid"], r["slot"]): r for r in R}
per_vp = {}; fires = defaultdict(list)
for r in R:
    cs = P.generate(r); per_vp[(r["mid"], r["slot"])] = cs
    for c in cs: fires[c["cid"]].append((r, c))
N = len(R)
for cid, v in sorted(fires.items()):
    std = sum(1 for r, _ in v if r["bucket"] == "STANDARD") / sum(1 for r in R if r["bucket"] == "STANDARD")
    tur = sum(1 for r, _ in v if r["bucket"] == "TURBO") / sum(1 for r in R if r["bucket"] == "TURBO")
    w = sum(1 for r, _ in v if r["win"]) / sum(1 for r in R if r["win"]); l = sum(1 for r, _ in v if not r["win"]) / sum(1 for r in R if not r["win"])
    print(f"{cid:22s} vp {100*len(v)/N:5.1f}% std {100*std:5.1f} tur {100*tur:5.1f} W {100*w:5.1f} L {100*l:5.1f} bands {dict(sorted(Counter(c['band'] for _, c in v).items()))}")
print("cards per vp", dict(sorted(Counter(min(len(v), 5) for v in per_vp.values()).items())))
pickle.dump(per_vp, open("cards_v2.pkl", "wb"))
# fresh holdout: team-level dedupe, exclude matches+cid rated in round-1 audit split
aud = json.load(open("audit_items.json"))
rated = {(a["cid"], a["mid"]) for a in aud if a["split"] == "audit"}
from sample_audit import ctx
rng = random.Random(99)
out = []; seen = set()
with open("holdout_sheet.txt", "w") as fh:
    for cid in ["COMEBACK_WIN", "LOST_FROM_AHEAD", "LEAD_FLIP", "LEAD_ERODED", "DEFICIT_RECOVERED", "CLOSE_MOST_OF_GAME", "EVEN_THEN_SEPARATED", "LATE_REVERSAL",
                "ENEMY_SMOKE_VOLUME", "VISION_QUICK_CLEARS", "VISION_REGION_SWEEP", "ENEMY_EARLY_RICH", "ENEMY_EARLY_ITEM", "ENEMY_STACKING"]:
        pool_ = [(r, c) for r, c in fires[cid] if (cid, r["mid"]) not in rated]
        ded = {}
        for r, c in pool_: ded.setdefault(r["mid"] if cid not in ("LEAD_FLIP",) else (r["mid"], r["side"]), (r, c))
        lst = list(ded.values()); rng.shuffle(lst)
        strata = defaultdict(list)
        for r, c in lst: strata[(r["bucket"], r["win"])].append((r, c))
        order = []
        while any(strata.values()):
            for s_ in sorted(strata):
                if strata[s_]: order.append(strata[s_].pop())
        fh.write(f"\n######## {cid} (fresh pool {len(lst)})\n")
        for i, (r, c) in enumerate(order[:20]):
            out.append(dict(id=f"{cid}:H{i}", cid=cid, mid=r["mid"], slot=r["slot"], band=c["band"], text=c["text"], ctx=ctx(r)))
            fh.write(f"{cid}:H{i} b{c['band']} | {ctx(r)}\n    {c['text']}\n")
json.dump(out, open("holdout_items.json", "w"), indent=0)

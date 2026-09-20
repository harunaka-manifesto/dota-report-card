import pickle, json
from collections import defaultdict
import pool as P
R = [r for r in P.D["rows"] if not r["feed"]]
P.G["v2"] = False
v1 = {(r["mid"], r["slot"]): {c["cid"] for c in P.generate(r)} for r in R}
P.G["v2"] = True
v3 = {(r["mid"], r["slot"]): {c["cid"] for c in P.generate(r)} for r in R}
N = len(R)
def cov(d): return round(100 * sum(1 for v in d.values() if v) / N, 1)
steps = []
cur = {k: set(v) for k, v in v1.items()}
steps.append(("v1 locked pool, pre-audit definitions (incl. LANE_DRAMATIC blowouts)", cov(cur)))
order = ["LANE_DRAMATIC", "ENEMY_EARLY_ITEM", "EVEN_THEN_SEPARATED", "CLOSE_MOST_OF_GAME", "ENEMY_SMOKE_VOLUME", "LEAD_ERODED", "DEFICIT_RECOVERED",
         "VISION_REGION_SWEEP", "VISION_QUICK_CLEARS", "ENEMY_EARLY_RICH", "LEAD_FLIP", "COMEBACK_WIN", "LOST_FROM_AHEAD", "LATE_REVERSAL", "ENEMY_STACKING"]
for cid in order:
    for k in cur:
        cur[k].discard(cid)
        if cid in v3[k]: cur[k].add(cid)
    steps.append((f"apply v3 definition/guard to {cid}", cov(cur)))
# sole-coverage per candidate in v3
sole = defaultdict(int)
for v in v3.values():
    if len(v) == 1: sole[next(iter(v))] += 1
out = dict(steps=steps, v3_sole_share={k: round(100 * n / N, 2) for k, n in sorted(sole.items(), key=lambda kv: -kv[1])})
json.dump(out, open("coverage_attribution.json", "w"), indent=1)
for s in steps: print(s)
print(out["v3_sole_share"])

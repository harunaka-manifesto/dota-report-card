import pickle, json, random
from collections import defaultdict
import pool as P
from sample_audit import ctx
P.G["v2"] = True
R = [r for r in P.D["rows"] if not r["feed"]]
used = {(a["cid"], a["mid"]) for a in json.load(open("audit_items.json")) if a["split"] == "audit"} | {(a["cid"], a["mid"]) for a in json.load(open("holdout_items.json"))}
rng = random.Random(2026)
C = defaultdict(dict)
for r in R:
    for c in P.generate(r):
        if (c["cid"], r["mid"]) in used: continue
        C[c["cid"]].setdefault(r["mid"], (r, c))
out = []
with open("holdout2_sheet.txt", "w") as fh:
    for cid in ["EVEN_THEN_SEPARATED", "LEAD_ERODED", "DEFICIT_RECOVERED", "CLOSE_MOST_OF_GAME", "VISION_REGION_SWEEP", "ENEMY_EARLY_RICH", "ENEMY_SMOKE_VOLUME"]:
        lst = list(C[cid].values()); rng.shuffle(lst)
        fh.write(f"\n######## {cid} (fresh pool {len(lst)})\n")
        for i, (r, c) in enumerate(lst[:12]):
            out.append(dict(id=f"{cid}:K{i}", cid=cid, mid=r["mid"]))
            fh.write(f"{cid}:K{i} b{c['band']} | {ctx(r)}\n    {c['text']}\n")
json.dump(out, open("holdout2_items.json", "w"))

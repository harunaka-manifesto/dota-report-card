import json, pickle
from collections import defaultdict, Counter
import pool as P
P.G["v2"] = True
R = {(r["mid"], r["slot"]): r for r in P.D["rows"] if not r["feed"]}
aud = [a for a in json.load(open("audit_items.json")) if a["split"] == "audit"]
r1 = json.load(open("ratings_round1.json"))
def lab(rs, i):
    for k in "GABM":
        if i in rs.get(k, []): return k
out = {}
cache = {}
for a in aud:
    cid = a["cid"]; i = int(a["id"].split(":")[-1]); k = (a["mid"], a["slot"])
    if k not in cache: cache[k] = {c["cid"] for c in P.generate(R[k])}
    L = lab(r1[cid], i)
    d = out.setdefault(cid, dict(r1=Counter(), kept=Counter(), removed=Counter()))
    d["r1"][L] += 1
    (d["kept"] if cid in cache[k] else d["removed"])[L] += 1
hv2 = json.load(open("ratings_holdout_v2.json")); hv3 = json.load(open("ratings_holdout2_v3.json")); h3 = json.load(open("ratings_holdout3_v3.json"))
def cnt(rs): return Counter({k: len(rs.get(k, [])) for k in "GABM"})
fin = {}
for cid in sorted(set(out) | set(h3) | set(hv3)):
    if cid.startswith("_"): continue
    d = out.get(cid, {})
    row = dict(round1=dict(d.get("r1", {})), round1_still_firing_v3=dict(d.get("kept", {})), round1_removed_by_guard=dict(d.get("removed", {})),
               holdout_v2=dict(cnt(hv2[cid])) if cid in hv2 else None, holdout2_v3=dict(cnt(hv3[cid])) if cid in hv3 else None, holdout3_v3=dict(cnt(h3[cid])) if cid in h3 else None)
    fin[cid] = row
    print(cid, row)
json.dump(fin, open("audit_tally.json", "w"), indent=1)

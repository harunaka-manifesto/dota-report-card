import pickle, random, json
from collections import defaultdict
import pool as P
from sample_audit import ctx as ctx886
rng = random.Random(42)
C886 = pickle.load(open("cards_v2.pkl", "rb"))
IDX = {(r["mid"], r["slot"]): r for r in P.D["rows"] if not r["feed"]}
L = {(r["acct"], r["mid"]): r for r in pickle.load(open("lean_rows.pkl", "rb"))}
CL = pickle.load(open("lean_cards.pkl", "rb"))
def ctxl(r):
    lc = r["lc"]; pts = list(range(5, len(lc), 5))
    return f"{r['bucket'][:3]} {r['role']}(P{r['pos']}) {r['hero']} {'WIN' if r['win'] else 'LOSS'} {r['dur']//60}m | lead " + " ".join(f"{t}:{lc[t]/1000:+.0f}k" for t in pts) + f" | end({len(lc)-1}):{lc[-1]/1000:+.0f}k [no vision data]"
items = []
# 886 corpus
seen = set(); pools = defaultdict(list)
keys = list(C886); rng.shuffle(keys)
for k in keys:
    cs = C886[k]; r = IDX[k]
    if len(cs) < 2 or (r["mid"], r["side"]) in seen: continue
    seen.add((r["mid"], r["side"]))
    pools[min(len(cs), 4)].append(("C", k, cs, ctx886(r), r))
for n, want in ((2, 28), (3, 26), (4, 16)):
    items += pools[n][:want]
# lean with history cards
lk = list(CL); rng.shuffle(lk)
hist = [k for k in lk if len(CL[k]) >= 2 and any(c["cid"] in ("OWN_LANE_VS_USUAL", "OPP_START_VS_HISTORY", "OWN_ITEM_VS_HISTORY") for c in CL[k])]
gen = [k for k in lk if len(CL[k]) >= 3 and k not in hist]
for k in hist[:38] + gen[:12]:
    items.append(("L", k, CL[k], ctxl(L[k]), L[k]))
out = []
with open("rank_sheet.txt", "w") as fh:
    for i, (src, k, cs, cx, r) in enumerate(items):
        order = list(range(len(cs))); rng.shuffle(order)
        labs = "abcdefg"
        rec = dict(i=i, src=src, key=[str(x) for x in k], cards=[])
        fh.write(f"\n[{i}] {cx}\n")
        for j, o in enumerate(order):
            c = cs[o]
            rec["cards"].append(dict(label=labs[j], cid=c["cid"], tier=c["tier"], band=c["band"], lvl=c["lvl"], exc=c["exc"], side=c["side"], family=c["family"]))
            fh.write(f"   {labs[j]}) {c['text']}\n")
        out.append(rec)
json.dump(out, open("rank_items.json", "w"), indent=0)
print(len(out), sum(len(o["cards"]) for o in out))

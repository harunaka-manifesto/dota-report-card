"""Final card sets (contract v3) for fresh lean viewpoints, including history cards."""
import pickle
from collections import Counter, defaultdict
import pool as P
import histcards as HC
P.G["v2"] = True
V3_HIST = dict(lane_margin={"STANDARD": 100, "TURBO": 200}, item_margin={"STANDARD": 60, "TURBO": 30}, item_dirs=("fast",), lane_cores_only=True)
def hist_index(**kw):
    C = HC.replay(**kw); idx = defaultdict(list)
    for a, lst in C.items():
        for r, c in lst:
            c = dict(c); c.setdefault("tier", "A"); c.setdefault("exc", float(c["band"] - 1)); c.setdefault("lvl", float(c["band"] - 1) + min(0.99, c.get("N", 20) / 50))
            idx[(a, r["mid"])].append(c)
    return idx
if __name__ == "__main__":
    L = pickle.load(open("lean_rows.pkl", "rb"))
    HI = hist_index(**V3_HIST)
    out = {}
    for r in L:
        out[(r["acct"], r["mid"])] = P.generate(r, HI.get((r["acct"], r["mid"]), []))
    pickle.dump(out, open("lean_cards.pkl", "wb"))
    N = len(L); c = Counter(); k = Counter()
    for v in out.values():
        k[min(len(v), 4)] += 1
        for x in v: c[x["cid"]] += 1
    print("viewpoints", N, "cards per vp", dict(sorted(k.items())))
    for cid, n in sorted(c.items()): print(f"  {cid:22s} {100*n/N:5.1f}%")

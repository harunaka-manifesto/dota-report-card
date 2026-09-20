import pickle, random, json
from collections import defaultdict
import pool as P
rng = random.Random(20260916)
R = [r for r in P.D["rows"] if not r["feed"]]
IDX = {(r["mid"], r["slot"]): r for r in R}
CARDS = pickle.load(open("cards_nohist.pkl", "rb"))
TEAMC = {"COMEBACK_WIN", "LOST_FROM_AHEAD", "LEAD_FLIP", "ENEMY_STACKING", "VISION_QUICK_CLEARS", "VISION_REGION_SWEEP", "ENEMY_SMOKE_VOLUME", "ENEMY_EARLY_RICH", "ENEMY_EARLY_ITEM",
         "CLOSE_MOST_OF_GAME", "EVEN_THEN_SEPARATED", "LEAD_ERODED", "DEFICIT_RECOVERED", "LATE_REVERSAL"}
by = defaultdict(list)
seen_team = set()
for k, cs in CARDS.items():
    r = IDX[k]
    for c in cs:
        if c["cid"] in TEAMC:
            tk = (c["cid"], r["mid"], r["side"])
            if tk in seen_team: continue
            seen_team.add(tk)
        by[c["cid"]].append((k, c))
def dur_t(r): return "S" if r["dur"] < (1800 if r["bucket"] == "STANDARD" else 1200) else ("M" if r["dur"] < (2700 if r["bucket"] == "STANDARD" else 1800) else "L")
def lead_summary(r):
    lc = r["lc"]; pts = list(range(5, len(lc), 5))
    return " ".join(f"{t}:{lc[t]/1000:+.0f}k" for t in pts) + f" | end({len(lc)-1}):{lc[-1]/1000:+.0f}k"
def ctx(r):
    return f"{r['bucket'][:3]} {r['role']}(P{r['pos']}) {r['hero']} {'WIN' if r['win'] else 'LOSS'} {r['dur']//60}m | lead {lead_summary(r)}"
AUD = {}
for cid, lst in by.items():
    rng.shuffle(lst)
    # stratify: take borderline (band1, lvl<.3) and strong (band>=2) and random mix; balance mode and W/L
    strata = defaultdict(list)
    for k, c in lst:
        r = IDX[k]; strata[(r["bucket"], r["win"])].append((k, c))
    order = []
    while any(strata.values()):
        for s in sorted(strata):
            if strata[s]: order.append(strata[s].pop())
    first = order[:30]; rest = order[30:]
    # force some borderline and extreme into the 30 if missing
    AUD[cid] = dict(audit=first, holdout=rest[:20])
out = []
for cid, d in AUD.items():
    for split in ("audit", "holdout"):
        for i, (k, c) in enumerate(d[split]):
            r = IDX[k]
            out.append(dict(id=f"{cid}:{split}:{i}", cid=cid, split=split, mid=r["mid"], slot=r["slot"], band=c["band"], lvl=c["lvl"], sub=c.get("sub"),
                            bucket=r["bucket"], win=r["win"], role=r["role"], dur=r["dur"], ctx=ctx(r), text=c["text"], others=[x["cid"] for x in CARDS[k] if x is not c]))
json.dump(out, open("audit_items.json", "w"), indent=0)
with open("audit_sheet.txt", "w") as fh:
    for cid in sorted(AUD):
        fh.write(f"\n######## {cid}  (audit n={len(AUD[cid]['audit'])}, holdout avail {len(AUD[cid]['holdout'])})\n")
        for it in out:
            if it["cid"] == cid and it["split"] == "audit":
                fh.write(f"{it['id']} b{it['band']} | {it['ctx']}\n    {it['text']}\n")
print({cid: (len(d["audit"]), len(d["holdout"])) for cid, d in AUD.items()})

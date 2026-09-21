"""Final deterministic selection (contract under recommendation) + coverage + recap sample."""
import pickle, json, random, statistics as st
from collections import Counter, defaultdict
LEAD_FAMILY_PRECEDENCE = ["COMEBACK_WIN", "LOST_FROM_AHEAD", "CLOSE_MOST_OF_GAME", "EVEN_THEN_SEPARATED", "LEAD_FLIP", "LEAD_ERODED", "DEFICIT_RECOVERED", "LATE_REVERSAL"]
CLASS1 = {"COMEBACK_WIN", "LOST_FROM_AHEAD"}
CLASS3 = {"ENEMY_EARLY_ITEM", "VISION_REGION_SWEEP"}
TIE_ORDER = ["COMEBACK_WIN", "LOST_FROM_AHEAD", "EVEN_THEN_SEPARATED", "OWN_LANE_VS_USUAL", "ENEMY_SMOKE_VOLUME", "ENEMY_STACKING", "LEAD_ERODED",
             "OWN_ITEM_VS_HISTORY", "VISION_QUICK_CLEARS", "CLOSE_MOST_OF_GAME", "LEAD_FLIP", "DEFICIT_RECOVERED", "ENEMY_EARLY_RICH",
             "OPP_START_VS_HISTORY", "LATE_REVERSAL", "ENEMY_EARLY_ITEM", "VISION_REGION_SWEEP"]
def rank_class(cid): return 1 if cid in CLASS1 else (3 if cid in CLASS3 else 2)
def select(cards, k=3):
    lead = [c for c in cards if c["cid"] in LEAD_FAMILY_PRECEDENCE]
    keep_lead = min(lead, key=lambda c: LEAD_FAMILY_PRECEDENCE.index(c["cid"])) if lead else None
    pool = [c for c in cards if c["cid"] not in LEAD_FAMILY_PRECEDENCE] + ([keep_lead] if keep_lead else [])
    pool.sort(key=lambda c: (rank_class(c["cid"]), -c["band"], -c["lvl"], TIE_ORDER.index(c["cid"])))
    return pool[:k]
if __name__ == "__main__":
    import pool as P
    P.G["v2"] = True
    C886 = pickle.load(open("cards_v2.pkl", "rb"))
    R886 = {(r["mid"], r["slot"]): r for r in P.D["rows"] if not r["feed"]}
    CL = pickle.load(open("lean_cards.pkl", "rb"))
    RL = {(r["acct"], r["mid"]): r for r in pickle.load(open("lean_rows.pkl", "rb"))}
    def cov(cards_by, rows_by, label):
        sel = {k: select(v) for k, v in cards_by.items()}
        segs = defaultdict(Counter)
        for k, s in sel.items():
            r = rows_by[k]; n = len(s)
            for seg in ("all", r["bucket"], "win" if r["win"] else "loss", r["role"]):
                segs[seg]["n"] += 1; segs[seg][">=1"] += n >= 1; segs[seg][">=2"] += n >= 2; segs[seg][">=3"] += n >= 3
        out = {seg: {m: round(100 * c[m] / c["n"], 1) for m in (">=1", ">=2", ">=3")} | {"none": round(100 - 100 * c[">=1"] / c["n"], 1), "n": c["n"]} for seg, c in segs.items()}
        top = Counter(s[0]["cid"] for s in sel.values() if s); shown = Counter(c["cid"] for s in sel.values() for c in s)
        print(label, json.dumps(out)); print("  top card share", {k: round(100 * v / len(sel), 1) for k, v in top.most_common()})
        return out, sel, shown
    o886, s886, sh886 = cov(C886, R886, "CORPUS-886 (no history, with vision)")
    oL, sL, shL = cov(CL, RL, "LEAN-FRESH (established accounts, history, no vision)")
    # suppression counts of the lead-story guard
    sup = Counter()
    for cards_by in (C886, CL):
        for v in cards_by.values():
            cids = [c["cid"] for c in v if c["cid"] in LEAD_FAMILY_PRECEDENCE]
            if len(cids) > 1:
                keep = min(cids, key=LEAD_FAMILY_PRECEDENCE.index)
                for c in cids:
                    if c != keep: sup[(keep, c)] += 1
    print("guard suppressions (kept, suppressed):", sup.most_common())
    # co-occurrence of shape cards with lead story cards (contradiction check)
    co = Counter()
    for v in list(C886.values()) + list(CL.values()):
        ids = {c["cid"] for c in v}
        for a in ("CLOSE_MOST_OF_GAME", "EVEN_THEN_SEPARATED"):
            for b in LEAD_FAMILY_PRECEDENCE:
                if a in ids and b in ids: co[(a, b)] += 1
    print("shape x lead co-occurrence:", co.most_common())
    json.dump(dict(corpus886=o886, lean=oL, shown886=sh886, shownLean=shL, suppressions={f"{a}|{b}": n for (a, b), n in sup.items()},
                   shape_lead_cooccurrence={f"{a}|{b}": n for (a, b), n in co.items()}), open("final_coverage.json", "w"), indent=1)
    # recap sample for the cross-card audit (complete selected sets, 1-3 cards)
    from sample_audit import ctx
    rng = random.Random(77)
    def ctxl(r):
        lc = r["lc"]; pts = list(range(5, len(lc), 5))
        return f"{r['bucket'][:3]} {r['role']}(P{r['pos']}) {r['hero']} {'WIN' if r['win'] else 'LOSS'} {r['dur']//60}m | lead " + " ".join(f"{t}:{lc[t]/1000:+.0f}k" for t in pts) + f" | end({len(lc)-1}):{lc[-1]/1000:+.0f}k"
    pick = []
    for src, sel, rows, cx in (("C", s886, R886, lambda r: ctx(r)), ("L", sL, RL, ctxl)):
        ks = [k for k, s in sel.items() if s]; rng.shuffle(ks)
        byn = defaultdict(list)
        for k in ks: byn[len(sel[k])].append(k)
        for n, want in ((1, 6), (2, 10), (3, 14)):
            for k in byn[n][:want]: pick.append((src, k, sel[k], cx(rows[k])))
    with open("recap_sheet_final.txt", "w") as fh:
        for i, (src, k, s, cx) in enumerate(pick):
            fh.write(f"\n[R{i}] {cx}\n")
            for j, c in enumerate(s): fh.write(f"   {j+1}. ({c['cid']} b{c['band']}) {c['text']}\n")
    print("recaps", len(pick))

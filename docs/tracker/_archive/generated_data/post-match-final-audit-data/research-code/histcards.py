"""History cards (candidate contract v1) replayed on real chronological histories.
Contract under test:
  window = most recent W=50 comparable eligible prior matches (cohort key per card), N = len(window)
  record claim requires N >= NMIN (20)
  OWN_LANE_VS_USUAL: key bucket+role; value lane NW diff at late checkpoint; best or worst of window (strict)
  OPP_START_VS_HISTORY: key bucket+role; counterpart CS@late (P1-3) / NW@late (P4-5) >= population p90 for that counterpart position AND strict max of window
  OWN_ITEM_VS_HISTORY: key bucket+role+item (+ same major patch); first purchase time strictly fastest (or slowest) of window
Severity: NOTABLE record with N<50; STRONG record with N==50 (full window); EXTREME = STRONG and population-extreme (see POP)."""
import pickle, json, statistics as st, random
from collections import defaultdict, Counter
H = pickle.load(open("hist_rows.pkl", "rb"))
W, NMIN = 50, 20
MAJOR = {180: "7.39", 181: "7.40", 182: "7.40"}
# population ladders from the 886-match corpus (base thresholds)
B = pickle.load(open("base.pkl", "rb")); TH = B["TH"]
OPP90 = {b: {pos: TH[b]["opp"][pos][1] for pos in (1, 2, 3, 4, 5)} for b in TH}
OPP95 = {b: {pos: TH[b]["opp"][pos][3] for pos in (1, 2, 3, 4, 5)} for b in TH}
LANE = {b: {g: (TH[b][g]["l90"], TH[b][g]["l95"]) for g in ("core", "support")} for b in TH}
SPIKE = ["item_black_king_bar", "item_blink", "item_radiance", "item_hand_of_midas", "item_manta", "item_desolator", "item_bfury", "item_maelstrom", "item_ultimate_scepter", "item_orchid"]

def mm(s): return f"{int(s)//60}:{int(s)%60:02d}"
def ka(x): return f"{x/1000:+.1f}k"

def replay(item_patch_scope=True, nmin=NMIN, directions=("best", "worst"), item_dirs=("fast", "slow"), lane_margin=None, item_margin=None, lane_cores_only=False):
    cards = defaultdict(list)   # acct -> list of (row, card)
    for a, rows in H.items():
        pl = defaultdict(list); po = defaultdict(list); pi = defaultdict(list)
        for i, r in enumerate(rows):
            if r["feed"]:
                continue
            b = r["bucket"]; g = "support" if r["role"] == "support" else "core"
            k = (b, r["role"])
            # ---- own lane
            if r.get("lane_diff") is not None and not (lane_cores_only and r["role"] == "support"):
                win = pl[k][-W:]; v = r["lane_diff"]
                if len(win) >= nmin:
                    best, worst = v > max(win), v < min(win)
                    if lane_margin:
                        mg = lane_margin[b]
                        best = best and v - max(win) >= mg; worst = worst and min(win) - v >= mg
                    if (best and "best" in directions) or (worst and "worst" in directions):
                        full = len(win) >= W; pop = abs(v) >= LANE[b][g][1]
                        band = 3 if full and pop else (2 if full or pop else 1)
                        prev = max(win) if best else min(win)
                        cards[a].append((r, dict(cid="OWN_LANE_VS_USUAL", tier="A", family="lane", side="personal", band=band, dir="best" if best else "worst", N=len(win),
                                         text=f"[OWN_LANE_{'BEST' if best else 'WORST'}] lane NW diff {ka(v)} at late checkpoint vs {r.get('opp_hero')} (P{r.get('opp_pos')}); previous {'best' if best else 'worst'} {ka(prev)}, median {ka(st.median(win))} across last {len(win)} {b[:3]} {r['role']} matches",
                                         value=v, prev=prev, med=st.median(win))))
                pl[k].append(v)
            # ---- opponent start
            if r.get("opp_val") is not None:
                win = po[k][-W:]; v = r["opp_val"]; pos = r["opp_pos"]
                if len(win) >= nmin and v > max(win) and v >= OPP90[b][pos]:
                    full = len(win) >= W; pop = v >= OPP95[b][pos]
                    band = 3 if full and pop else (2 if full or pop else 1)
                    unit = "CS" if pos <= 3 else "NW"
                    cards[a].append((r, dict(cid="OPP_START_VS_HISTORY", tier="A", family="lane", side="enemy", band=band, N=len(win),
                                     text=f"[OPP_START_RECORD] {r.get('opp_hero')} (P{pos}) had {v} {unit} at late checkpoint — highest faced across your last {len(win)} {b[:3]} {r['role']} matches (previous high {max(win)}, median {st.median(win)}); your lane diff {ka(r['lane_diff']) if r.get('lane_diff') is not None else 'n/a'}",
                                     value=v, prev=max(win))))
                po[k].append(v)
            # ---- own item timing
            hit = []
            for n, t in r["own_items"].items():
                kk = (b, r["role"], n) + ((MAJOR.get(r["patch"], r["patch"]),) if item_patch_scope else ())
                win = pi[kk][-W:]
                if len(win) >= nmin:
                    im = item_margin[b] if item_margin else 0
                    if t <= min(win) - max(im, 1) and "fast" in item_dirs: hit.append((n, t, "fastest", min(win), st.median(win), len(win)))
                    elif t >= max(win) + max(im, 1) and "slow" in item_dirs: hit.append((n, t, "slowest", max(win), st.median(win), len(win)))
                pi[kk].append(t)
            for n, t, d, prev, med, N in hit[:1] if hit else []:
                full = N >= W; margin = abs(prev - t) >= (60 if b == "TURBO" else 120)
                band = 3 if full and margin else (2 if full or margin else 1)
                cards[a].append((r, dict(cid="OWN_ITEM_VS_HISTORY", item=n, tier="A", family="power", side="personal", band=band, dir=d, N=N,
                                 text=f"[OWN_ITEM_{d.upper()}] {r['hero']} {n.replace('item_','')} at {mm(t)} — {d} across your last {N} {b[:3]} {r['role']} {n.replace('item_','')} purchases (previous {mm(prev)}, median {mm(med)})",
                                 value=t, prev=prev, med=med)))
    return cards

if __name__ == "__main__":
    C = replay()
    ev = Counter(); fires = Counter()
    for a, rows in H.items():
        for r in rows:
            if not r["feed"]: ev[r["bucket"]] += 1
    for a, lst in C.items():
        for r, c in lst: fires[(c["cid"], c.get("dir"), c["band"])] += 1
    tot = sum(ev.values())
    for k in sorted(fires): print(k, fires[k], f"{100*fires[k]/tot:.2f}% of evaluations")
    rng = random.Random(7)
    items = defaultdict(list)
    for a, lst in C.items():
        for r, c in lst: items[c["cid"]].append((a, r, c))
    out = []
    with open("hist_audit_sheet.txt", "w") as fh:
        for cid, lst in items.items():
            rng.shuffle(lst)
            # stratify by direction and mode
            strata = defaultdict(list)
            for x in lst: strata[(x[2].get("dir"), x[1]["bucket"])].append(x)
            order = []
            while any(strata.values()):
                for s in sorted(strata, key=str):
                    if strata[s]: order.append(strata[s].pop())
            fh.write(f"\n######## {cid} total {len(lst)}\n")
            for i, (a, r, c) in enumerate(order[:50]):
                split = "audit" if i < 30 else "holdout"
                out.append(dict(id=f"{cid}:{split}:{i}", acct=a, mid=r["mid"], band=c["band"], dir=c.get("dir"), text=c["text"]))
                if split == "audit":
                    fh.write(f"{cid}:{i} b{c['band']} | {r['bucket'][:3]} {r['role']} {r['hero']} {'WIN' if r['win'] else 'LOSS'} {r['dur']//60}m\n    {c['text']}\n")
    json.dump(out, open("hist_audit_items.json", "w"), indent=0)

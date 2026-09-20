"""Corpus-wide candidates using historical identity reconstruction (tier A: enemy sentry <=10 cells in prior 90 s)."""
import math, statistics as st, collections, pickle, random
from common import *
from geo import *
from ident import reconstruct
core, rep, pb = load_all()
H = {(r["mid"], r["side"]): r for r in pickle.load(open("hist_units.pkl", "rb"))}
def dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])
def Q(v, q): v = sorted(v); return v[min(len(v) - 1, int(round(q * (len(v) - 1))))] if v else None
units = []; seqs = []
for (mid, s_), h in H.items():
    if h["feed"]: continue
    m = core[mid]; dur = m["durationSeconds"]
    own = sorted((w["time"], w["positionX"], w["positionY"]) for p in m["players"] if p["isRadiant"] == s_ for w in p["stats"]["wards"] or [] if w["type"] == 0)
    esent = [(w["time"], w["positionX"], w["positionY"]) for p in m["players"] if p["isRadiant"] != s_ for w in p["stats"]["wards"] or [] if w["type"] == 1]
    kills = sorted(d["time"] for p in m["players"] if p["isRadiant"] != s_ for d in p["stats"]["wardDestruction"] or [] if d.get("isWard"))
    res = [(t, i) for t, i, tier in reconstruct(own, kills, esent, dur, W=90, R=10, W2=0, R2=0) if tier in ("A", "C")]
    deaths = [(d["time"], d["positionX"], d["positionY"]) for p in m["players"] if p["isRadiant"] == s_ for d in p["stats"]["deathEvents"] or [] if d.get("positionX") is not None]
    idd = [dict(t=t, t0=own[i][0], x=own[i][1], y=own[i][2], life=t - own[i][0], region=region(own[i][1], own[i][2], s_), rosh=near_rosh(own[i][1], own[i][2])) for t, i in res]
    # region clusters: >=3 identified clears in one region within 5 min
    best = (0, None)
    for a in idd:
        c = [b for b in idd if b["region"] == a["region"] and a["t"] <= b["t"] <= a["t"] + 300]
        if len(c) > best[0]: best = (len(c), (a["region"], a["t"], max(b["t"] for b in c)))
    agg = [w for w in own if region(w[1], w[2], s_) in ("ENEMY_HALF", "ENEMY_BASE")]
    aggk = [a for a in idd if a["region"] in ("ENEMY_HALF", "ENEMY_BASE")]
    sent_own_half = sum(1 for t, x, y in esent if region(x, y, s_) in ("OWN_HALF", "OWN_BASE"))
    u = dict(h, identified=len(idd), quick90=sum(1 for a in idd if a["life"] <= 90), quick60=sum(1 for a in idd if a["life"] <= 60),
             cleared_life_median=st.median(a["life"] for a in idd) if idd else None, cluster=best[0], cluster_info=best[1],
             agg=len(agg), aggk=len(aggk), rosh_k=sum(1 for a in idd if a["rosh"]), esent=len(esent), esent_ownhalf=sent_own_half,
             region_k=collections.Counter(a["region"] for a in idd), idd=idd)
    units.append(u)
    for a in idd:
        t, xy = a["t"], (a["x"], a["y"])
        if t + 120 > dur or t < 120: continue
        f = lambda tc: sum(1 for d in deaths if tc < d[0] <= tc + 120 and dist(xy, d[1:]) <= VISION_R)
        before = sum(1 for d in deaths if t - 120 <= d[0] <= t and dist(xy, d[1:]) <= VISION_R)
        ctl = [f(t + k) for k in (-600, -420, -240, 240, 420, 600) if 0 <= t + k and t + k + 120 <= dur]
        seqs.append((f(t), before, ctl, h["bucket"]))
print("units", len(units), "identified share of kills", round(sum(u["identified"] for u in units) / sum(u["killed"] for u in units), 3))
for b in ("STANDARD", "TURBO"):
    R = [u for u in units if u["bucket"] == b]; n = len(R)
    pct = lambda f: round(100 * sum(1 for u in R if f(u)) / n, 1)
    print(f"\n{b} n={n}")
    print("  quick90 dist", dict(sorted(collections.Counter(min(u['quick90'], 6) for u in R).items())), "p90", Q([u['quick90'] for u in R], .9))
    print("  QUICK: >=3 cleared <=90s:", pct(lambda u: u['quick90'] >= 3), "| >=4:", pct(lambda u: u['quick90'] >= 4), "| >=3 & >=25% of placed:", pct(lambda u: u['quick90'] >= 3 and u['quick90'] / max(1, u['placed']) >= .25))
    print("  CLUSTER same region >=3 in 5 min:", pct(lambda u: u['cluster'] >= 3), ">=4:", pct(lambda u: u['cluster'] >= 4), "regions:", collections.Counter(u['cluster_info'][0] for u in R if u['cluster'] >= 3))
    print("  AGGRESSIVE: agg>=4 & >=60% cleared:", pct(lambda u: u['agg'] >= 4 and u['aggk'] / u['agg'] >= .6), "| agg>=5 & >=50%:", pct(lambda u: u['agg'] >= 5 and u['aggk'] / u['agg'] >= .5), "| agg placed p50", Q([u['agg'] for u in R], .5))
    print("  ROSHAN-area clears >=3:", pct(lambda u: u['rosh_k'] >= 3))
    print("  existing H2r-a style (placed>=8, share>=p75, rate>=p90):", "see candidate doc 10.1/9.2%")
    print("  enemy sentries placed p50/p90", Q([u['esent'] for u in R], .5), Q([u['esent'] for u in R], .9), "in our half p50/p90", Q([u['esent_ownhalf'] for u in R], .5), Q([u['esent_ownhalf'] for u in R], .9))
    for nm, f in (("QUICK>=3", lambda u: u['quick90'] >= 3), ("CLUSTER>=3", lambda u: u['cluster'] >= 3), ("SPECIALIST", lambda u: u['top_count'] >= 5 and u['top_count'] / max(1, u['killed']) >= .6)):
        w = [u for u in R if u['win']]; l = [u for u in R if not u['win']]
        fw = sum(1 for u in w if f(u)) / len(w); fl = sum(1 for u in l if f(u)) / len(l)
        dm = st.median(u['dur'] for u in R)
        print(f"  {nm}: win {fw:.3f} loss {fl:.3f} | fire rate short/long half {sum(1 for u in R if f(u) and u['dur'] <= dm)/sum(1 for u in R if u['dur'] <= dm):.3f}/{sum(1 for u in R if f(u) and u['dur'] > dm)/sum(1 for u in R if u['dur'] > dm):.3f}")
n = len(seqs)
P = lambda xs: round(sum(1 for x in xs if x >= 1) / len(xs), 3)
print("\nidentified clears, allied deaths within 25 cells next 2 min: P", P([s[0] for s in seqs]), "vs same-spot control", round(st.fmean(st.fmean(1 if c >= 1 else 0 for c in s[2]) for s in seqs if s[2]), 3), "n", n,
      "| before-window P", P([s[1] for s in seqs]))
cl = [s for s in seqs if s[1] == 0]
print("clean (no nearby death prior 2 min): P", P([s[0] for s in cl]), "vs control", round(st.fmean(st.fmean(1 if c >= 1 else 0 for c in s[2]) for s in cl if s[2]), 3), "n", len(cl),
      "| >=2 deaths", round(sum(1 for s in cl if s[0] >= 2) / len(cl), 3), "vs", round(st.fmean(st.fmean(1 if c >= 2 else 0 for c in s[2]) for s in cl if s[2]), 3))
pickle.dump(units, open("hist_ident_units.pkl", "wb"))

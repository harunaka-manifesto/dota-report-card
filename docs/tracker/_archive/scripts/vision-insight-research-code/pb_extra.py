"""Playback-truth tests: sentry-proximity identity, quick kills, aggressive wards, region clusters, coverage ratios, clean death sequences."""
import math, statistics as st, collections, pickle, random
from common import *
from geo import *
core, rep, pb = load_all()
X = pickle.load(open("pb_exact.pkl", "rb")); TEAM = X["TEAM"]
SENT_R = 14            # sentry true-sight 900 units ~ 14 cells (assumed; tested at 10/14/20)
def dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])
out = collections.Counter(); ident = collections.Counter(); units = []
for (mid, s_), rec in TEAM.items():
    m = core[mid]; dur = m["durationSeconds"]
    esent = [(w["time"], w["positionX"], w["positionY"]) for p in m["players"] if p["isRadiant"] != s_ for w in p["stats"]["wards"] or [] if w["type"] == 1]
    own = rec["wards"]
    for R in (10, 14, 20):
        for w in own:
            if w["end"] not in ("enemy", "natural"): continue
            near = any(w["t0"] - 420 <= t <= w["t1"] and dist((x, y), (w["x"], w["y"])) <= R for t, x, y in esent)
            out[(R, near, w["end"])] += 1
    # historical identity heuristic: for each stats deward, candidates alive; prefer candidate with an enemy sentry placed within R in [t-120, t]
    kills = sorted((d["time"]) for p in m["players"] if p["isRadiant"] != s_ for d in p["stats"]["wardDestruction"] or [] if d.get("isWard"))
    truth_by_t = {w["t1"]: w for w in own if w["end"] == "enemy"}
    for t in kills:
        tw = next((w for tt, w in truth_by_t.items() if abs(tt - t) <= 1), None)
        cands = [w for w in own if w["t0"] <= t < min(w["t0"] + 360, dur)]
        if not tw or not cands: ident["no_truth_or_cands"] += 1; continue
        sc = [(sum(1 for ts, x, y in esent if t - 150 <= ts <= t and dist((x, y), (w["x"], w["y"])) <= SENT_R), w) for w in cands]
        best = max(sc, key=lambda z: z[0])
        top = [w for c, w in sc if c == best[0]]
        if best[0] > 0 and len(top) == 1:
            ident["sentry_unique"] += 1; ident["sentry_unique_ok"] += top[0] is tw
        elif len(cands) == 1:
            ident["single"] += 1; ident["single_ok"] += cands[0] is tw
        else: ident["unresolved"] += 1
        ident["total"] += 1
    killed = [w for w in own if w["end"] == "enemy"]
    agg = [w for w in own if w["region"] in ("ENEMY_HALF", "ENEMY_BASE")]
    aggk = [w for w in agg if w["end"] == "enemy"]
    # same-region cluster: >=3 killed in one region within 300 s
    clus = 0
    for w in killed:
        c = [v for v in killed if v["region"] == w["region"] and w["t1"] <= v["t1"] <= w["t1"] + 300]
        clus = max(clus, len(c))
    units.append(dict(mid=mid, side=s_, bucket=rec["bucket"], win=rec["win"], placed=rec["placed"], killed=rec["killed"],
                      quick60=sum(1 for w in killed if w["t1"] - w["t0"] <= 60), quick90=sum(1 for w in killed if w["t1"] - w["t0"] <= 90),
                      agg=len(agg), aggk=len(aggk), agg_life=[w["t1"] - w["t0"] for w in agg if w["end"] in ("enemy", "natural")],
                      safe_life=[w["t1"] - w["t0"] for w in own if w["region"] in ("OWN_HALF", "OWN_BASE") and w["end"] in ("enemy", "natural")],
                      cluster=clus, cov=rec["cov_own"], ecov=rec["cov_enemy"], upr=rec["uptime"] / max(1, rec["nominal"]), eupr=rec["enemy_uptime"] / max(1, rec["enemy_nominal"]),
                      removed=rec["removed"], nominal=rec["nominal"], gaps=rec["gaps"]))
print("sentry proximity vs fate (R, enemy sentry near during life, end): counts")
for R in (10, 14, 20):
    a = out[(R, True, "enemy")]; b = out[(R, True, "natural")]; c = out[(R, False, "enemy")]; d = out[(R, False, "natural")]
    print(f"  R={R}: P(killed | sentry near) {a/(a+b):.2f} (n {a+b}) vs P(killed | none) {c/(c+d):.2f} (n {c+d}); recall of kills {a/(a+c):.2f}")
print("historical identity via recent nearby enemy sentry:", dict(ident), "precision sentry_unique", round(ident["sentry_unique_ok"] / max(1, ident["sentry_unique"]), 2), "single", round(ident["single_ok"] / max(1, ident["single"]), 2),
      "coverage", round((ident["sentry_unique"] + ident["single"]) / max(1, ident["total"]), 2))
print("\nper-unit (36):")
print(" quick60 dist", dict(sorted(collections.Counter(min(u['quick60'], 6) for u in units).items())), "quick90", dict(sorted(collections.Counter(min(u['quick90'], 6) for u in units).items())))
print(" aggressive wards placed p50", st.median(u["agg"] for u in units), "kill rate aggressive", round(sum(u["aggk"] for u in units) / sum(u["agg"] for u in units), 2),
      "| units agg>=4 & >=60% killed", sum(1 for u in units if u["agg"] >= 4 and u["aggk"] / u["agg"] >= .6))
al = [x for u in units for x in u["agg_life"]]; sl = [x for u in units for x in u["safe_life"]]
print(" life aggressive median", st.median(al), "share<=90", round(sum(1 for x in al if x <= 90) / len(al), 2), "| own-half median", st.median(sl), "share<=90", round(sum(1 for x in sl if x <= 90) / len(sl), 2))
print(" same-region cluster >=3 in 5 min:", sum(1 for u in units if u["cluster"] >= 3), ">=4:", sum(1 for u in units if u["cluster"] >= 4))
print(" coverage own/enemy ratio p10/p50/p90", [round(sorted(u["cov"] / max(1e-9, u["ecov"]) for u in units)[int(q * 35)], 2) for q in (.1, .5, .9)],
      "| uptime ratio own vs enemy diff p10/p90", [round(sorted(u["upr"] - u["eupr"] for u in units)[int(q * 35)], 2) for q in (.1, .9)])
print(" corr coverage ratio vs killed share", round(st.correlation([u["cov"] / u["ecov"] for u in units], [u["killed"] / u["placed"] for u in units]), 2),
      "corr coverage ratio vs placed ratio", round(st.correlation([u["cov"] / u["ecov"] for u in units], [u["placed"] / max(1, TEAM[(u['mid'], not u['side'])]['placed']) for u in units]), 2))
print(" removed minutes p50/p90", round(st.median(u["removed"] for u in units) / 60, 1), round(sorted(u["removed"] for u in units)[31] / 60, 1), "removed share of nominal p50", round(st.median(u["removed"] / u["nominal"] for u in units), 2))
pickle.dump(units, open("pb_units.pkl", "wb"))
# clean sequence test: cleared ward, no allied death within 25 cells in prior 120 s, then deaths within 120 s
SEQ = X["SEQ"][120]
clean = [s for s in SEQ if s["near_before"] == 0]
cp = sum(1 for s in clean if s["near_after"] >= 1) / len(clean)
cc = st.fmean(st.fmean(1 if c[0] >= 1 else 0 for c in s["ctrl"]) for s in clean if s["ctrl"])
print(f"\nclean-sequence (no nearby allied death in prior 2 min): n {len(clean)} P(nearby allied death next 2 min) {cp:.3f} vs same-spot control {cc:.3f}")
two = sum(1 for s in clean if s["near_after"] >= 2) / len(clean); two_c = st.fmean(st.fmean(1 if c[0] >= 2 else 0 for c in s["ctrl"]) for s in clean if s["ctrl"])
print(f"   >=2 nearby deaths: {two:.3f} vs control {two_c:.3f}")

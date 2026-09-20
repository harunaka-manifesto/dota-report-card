"""Historical (stats-only) vision metrics on the eligible corpus + validation of bound/estimate methods against playback truth."""
import json, math, random, statistics as st, collections, pickle
from common import *
from geo import *
core, rep, pb = load_all()
EX = pickle.load(open("pb_exact.pkl", "rb"))["TEAM"]
rng = random.Random(7)
def Q(v, q): v = sorted(v); return v[min(len(v) - 1, int(round(q * (len(v) - 1))))] if v else None
feed = set()
elig = []
for mid, m in core.items():
    ok, _ = eligible_match(m)
    if not ok: continue
    t = CHECK[bucket(m)]["late"] * 60
    if any(sum(1 for d in p["stats"]["deathEvents"] or [] if d["time"] < t) >= 8 for p in m["players"]): feed.add(mid)
    elig.append(mid)
U = []
for mid in elig:
    m = core[mid]; dur = m["durationSeconds"]; S = structures(m)
    for s_ in (True, False):
        own = sorted((w["time"], w["positionX"], w["positionY"]) for p in m["players"] if p["isRadiant"] == s_ for w in p["stats"]["wards"] or [] if w["type"] == 0)
        eobs = [w for p in m["players"] if p["isRadiant"] != s_ for w in p["stats"]["wards"] or [] if w["type"] == 0]
        kills = sorted((d["time"], HEROES.get(p["heroId"]), pos_num(p)) for p in m["players"] if p["isRadiant"] != s_ for d in p["stats"]["wardDestruction"] or [] if d.get("isWard"))
        deaths = sorted((d["time"], d["positionX"], d["positionY"]) for p in m["players"] if p["isRadiant"] == s_ for d in p["stats"]["deathEvents"] or [] if d.get("positionX") is not None)
        # alive bounds per 10 s
        ts = list(range(600, dur - 60, 10))
        amin = []; amax = []
        for t in ts:
            A = sum(1 for w in own if w[0] <= t); D = sum(1 for k in kills if k[0] <= t); N = sum(1 for w in own if w[0] + 360 <= t)
            amin.append(max(A - D - N, 0)); amax.append(max(min(A - N, A - D), 0))
        # uptime bounds (whole game): nominal minus removed; removed per kill in [min remaining, max remaining] over alive candidates
        nominal = sum(min(w[0] + 360, dur) - w[0] for w in own)
        rem_lo = rem_hi = rem_mid = 0; resolvable_region = 0; quick_certain = 0; cand_counts = []
        for k in kills:
            cands = [w for w in own if w[0] <= k[0] < min(w[0] + 360, dur)]
            cand_counts.append(len(cands))
            if not cands: continue
            rems = [min(w[0] + 360, dur) - k[0] for w in cands]
            rem_lo += min(rems); rem_hi += max(rems); rem_mid += st.fmean(rems)
            regs = {region(w[1], w[2], s_) for w in cands}
            resolvable_region += len(regs) == 1
            quick_certain += max(k[0] - w[0] for w in cands) <= 90
        tb = [k[0] for k in kills]
        burst120 = max((sum(1 for x in tb if t <= x <= t + 120) for t in tb), default=0)
        burst180 = max((sum(1 for x in tb if t <= x <= t + 180) for t in tb), default=0)
        tops = collections.Counter((h, p_) for _, h, p_ in kills).most_common(1)
        rec = dict(mid=mid, side=s_, bucket=bucket(m), dur=dur, win=m["didRadiantWin"] == s_, feed=mid in feed, placed=len(own), enemy_placed=len(eobs), killed=len(kills),
                   early10=sum(1 for x in tb if x < 600), early15=sum(1 for x in tb if x < 900), burst120=burst120, burst180=burst180,
                   top_killer=tops[0][0] if tops else None, top_count=tops[0][1] if tops else 0,
                   own_region=collections.Counter(region(w[1], w[2], s_) for w in own),
                   zero_certain=sum(1 for a in amax if a == 0) / max(1, len(ts)), zero_possible=sum(1 for a in amin if a == 0) / max(1, len(ts)),
                   determined=sum(1 for a, b in zip(amin, amax) if a == b) / max(1, len(ts)),
                   nominal=nominal, removed_lo=rem_lo, removed_hi=rem_hi, removed_mid=rem_mid, kills_with_cands=sum(1 for c in cand_counts if c),
                   single_cand=sum(1 for c in cand_counts if c == 1), resolvable_region=resolvable_region, quick_certain=quick_certain,
                   kill_times=tb, deaths=deaths, S=[x for x in S if x["owner_radiant"] == s_ and x["kind"] in ("tower", "barracks")],
                   lc=lead_curve(m, s_))
        # longest certain gap after 10:00
        best = 0; run = 0
        for a in amax:
            run = run + 10 if a == 0 else 0; best = max(best, run)
        rec["longest_certain_gap"] = best
        U.append(rec)
print("team units", len(U))
# ---------- validation vs playback truth ----------
val = []
for r in U:
    e = EX.get((r["mid"], r["side"]))
    if not e: continue
    true_removed = e["removed"]
    val.append((r["killed"], e["killed"], r["removed_lo"], r["removed_hi"], r["removed_mid"], true_removed, r["zero_certain"], e["zero_share"], r["placed"], e["placed"]))
print("validation units", len(val))
print(" placed stats==playback", sum(1 for v in val if v[8] == v[9]), "| killed stats==playback", sum(1 for v in val if v[0] == v[1]), "abs diff", Counter(abs(v[0] - v[1]) for v in val) if False else collections.Counter(abs(v[0] - v[1]) for v in val))
print(" removed truth within [lo,hi]", sum(1 for v in val if v[2] - 30 <= v[5] <= v[3] + 30), "| mid-estimate abs err median s", st.median(abs(v[4] - v[5]) for v in val), "truth median", st.median(v[5] for v in val), "| interval width median", st.median(v[3] - v[2] for v in val))
print(" certain-zero share <= true zero share", sum(1 for v in val if v[6] <= v[7] + 1e-9), "| certain zero median", st.median(v[6] for v in val), "true zero median", st.median(v[7] for v in val))
# ---------- corpus distributions ----------
N = [r for r in U if not r["feed"]]
for b in ("STANDARD", "TURBO"):
    R = [r for r in N if r["bucket"] == b]
    share = [r["killed"] / r["placed"] for r in R if r["placed"] >= 8]
    rate = [r["killed"] / r["dur"] * 600 for r in R]
    print(f"\n{b}: units {len(R)} placed p50 {Q([r['placed'] for r in R], .5)} killed p50/p75/p90 {Q([r['killed'] for r in R], .5)}/{Q([r['killed'] for r in R], .75)}/{Q([r['killed'] for r in R], .9)} share(p>=8) p50/p75/p90 {round(Q(share,.5),2)}/{round(Q(share,.75),2)}/{round(Q(share,.9),2)} rate10 p90 {round(Q(rate,.9),2)}")
    print("   early15 p90", Q([r["early15"] for r in R], .9), "burst120 dist", dict(sorted(collections.Counter(min(r['burst120'], 5) for r in R).items())), "burst180>=4", round(sum(1 for r in R if r['burst180'] >= 4) / len(R), 3))
    print("   top dewarder count dist", dict(sorted(collections.Counter(min(r['top_count'], 8) for r in R).items())),
          "| specialist (>=5 and >=60% of kills)", round(sum(1 for r in R if r['top_count'] >= 5 and r['top_count'] / max(1, r['killed']) >= .6) / len(R), 3),
          "| (>=4 & >=70%)", round(sum(1 for r in R if r['top_count'] >= 4 and r['top_count'] / max(1, r['killed']) >= .7) / len(R), 3))
    print("   top dewarder position mix", collections.Counter(r['top_killer'][1] for r in R if r['top_killer'] and r['top_count'] >= 4))
    print("   certain gap >=240s share", round(sum(1 for r in R if r['longest_certain_gap'] >= 240) / len(R), 3), ">=480s", round(sum(1 for r in R if r['longest_certain_gap'] >= 480) / len(R), 3), "determined share p50", round(Q([r['determined'] for r in R], .5), 2))
    print("   removed-minutes mid p50/p90", round(Q([r['removed_mid'] for r in R], .5) / 60, 1), round(Q([r['removed_mid'] for r in R], .9) / 60, 1), "nominal p50 min", round(Q([r['nominal'] for r in R], .5) / 60, 1))
    tot_k = sum(r['kills_with_cands'] for r in R)
    print("   of dewards with candidates: single candidate", round(sum(r['single_cand'] for r in R) / tot_k, 3), "region-resolvable", round(sum(r['resolvable_region'] for r in R) / tot_k, 3), "certain <=90s", round(sum(r['quick_certain'] for r in R) / tot_k, 3))
    print("   win/loss killed>=p90:", round(sum(1 for r in R if r['win'] and r['killed'] >= Q([x['killed'] for x in R], .9)) / sum(1 for r in R if r['win']), 3), round(sum(1 for r in R if not r['win'] and r['killed'] >= Q([x['killed'] for x in R], .9)) / sum(1 for r in R if not r['win']), 3))
# ---------- temporal sequence base rates (historical, time only) ----------
def seq(events_fn, W=180, label=""):
    obs = []; ctl = []
    for r in N:
        for t in events_fn(r):
            if t < 300 or t + W > r["dur"]: continue
            f = lambda a: (sum(1 for d in r["deaths"] if a < d[0] <= a + W), sum(1 for x in r["S"] if a < x["time"] <= a + W),
                           (r["lc"][min(len(r["lc"]) - 1, (a + W) // 60)] - r["lc"][min(len(r["lc"]) - 1, a // 60)]))
            obs.append(f(t))
            for k in (-540, -360, -180, 180, 360, 540):
                if 300 <= t + k and t + k + W <= r["dur"]: ctl.append(f(t + k))
    def P(xs, i): return round(sum(1 for x in xs if x[i] >= 1) / len(xs), 3)
    def M(xs, i): return round(st.fmean(x[i] for x in xs), 2)
    print(f"{label} W={W}: n {len(obs)} | own deaths P>=1 {P(obs,0)} vs ctl {P(ctl,0)} (mean {M(obs,0)} vs {M(ctl,0)}) | own structures lost P>=1 {P(obs,1)} vs {P(ctl,1)} | NW lead change mean {M(obs,2)} vs {M(ctl,2)}; P(lead drop >2k) {round(sum(1 for x in obs if x[2] <= -2000)/len(obs),3)} vs {round(sum(1 for x in ctl if x[2] <= -2000)/len(ctl),3)}")
print()
seq(lambda r: r["kill_times"], 180, "every deward")
def burst_starts(r, n=3, w=120):
    out = []; last = -999
    for t in r["kill_times"]:
        if sum(1 for x in r["kill_times"] if t <= x <= t + w) >= n and t > last + w: out.append(max(x for x in r["kill_times"] if t <= x <= t + w)); last = t
    return out
seq(burst_starts, 180, "after a 3-in-2-min burst (from last deward)")
seq(burst_starts, 300, "after a 3-in-2-min burst (from last deward)")
seq(lambda r: burst_starts(r, 4, 180), 300, "after a 4-in-3-min burst")
pickle.dump([{k: v for k, v in r.items() if k not in ("deaths", "S", "lc")} for r in U], open("hist_units.pkl", "wb"))

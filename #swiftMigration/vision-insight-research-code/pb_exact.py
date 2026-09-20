"""Exact observer lifecycles (playback) joined with historical stats: metrics, coverage, sequences with controls."""
import json, math, random, statistics as st, collections, pickle
from common import *
from geo import *
core, rep, pb = load_all()
MIDS = sorted(m for m in pb if m in core)
rng = random.Random(16)
TEAM = {}   # (mid, side) -> dict
SEQ = collections.defaultdict(list)
def dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])
for mid in MIDS:
    m = core[mid]; pm = pb[mid]; dur = m["durationSeconds"]
    side = {p["playerSlot"]: p["isRadiant"] for p in m["players"]}
    hero = {p["playerSlot"]: HEROES.get(p["heroId"]) for p in m["players"]}
    pos = {p["playerSlot"]: pos_num(p) if p.get("position") else None for p in m["players"]}
    L = [w for w in ward_life(pm, dur) if w["type"] == "OBSERVER" and w["owner"] in side]
    deaths = [(d["time"], d["positionX"], d["positionY"], p["isRadiant"]) for p in m["players"] for d in p["stats"]["deathEvents"] or [] if d.get("positionX") is not None]
    S = structures(m)
    smokes = [(e["time"], side.get(pp.get("playerSlot"))) for pp in pm["players"] for e in ((pp.get("playbackData") or {}).get("itemUsedEvents") or []) if ITEMS.get(e["itemId"]) == "item_smoke_of_deceit"]
    for w in L:
        w["side"] = side[w["owner"]]
        w["nominal_end"] = min(w["t0"] + 360, dur)
        if w["killer"] is not None: w["end"] = "enemy" if side.get(w["killer"]) != w["side"] else "own"
        elif not w["ended"]: w["end"] = "match_end"
        elif w["t1"] - w["t0"] >= 350: w["end"] = "natural"
        else: w["end"] = "other"
        w["region"] = region(w["x"], w["y"], w["side"]); w["rosh"] = near_rosh(w["x"], w["y"])
    for s_ in (True, False):
        own = [w for w in L if w["side"] == s_]; enemyw = [w for w in L if w["side"] != s_]
        killed = [w for w in own if w["end"] == "enemy"]
        rec = dict(mid=mid, side=s_, bucket=bucket(m), dur=dur, win=m["didRadiantWin"] == s_, placed=len(own), killed=len(killed),
                   own_denied=sum(1 for w in own if w["end"] == "own"), other_end=sum(1 for w in own if w["end"] == "other"),
                   life_killed=[w["t1"] - w["t0"] for w in killed],
                   uptime=sum(w["t1"] - w["t0"] for w in own), nominal=sum(w["nominal_end"] - w["t0"] for w in own),
                   removed=sum(w["nominal_end"] - w["t1"] for w in killed),
                   enemy_uptime=sum(w["t1"] - w["t0"] for w in enemyw), enemy_nominal=sum(w["nominal_end"] - w["t0"] for w in enemyw),
                   regions_placed=collections.Counter(w["region"] for w in own), regions_killed=collections.Counter(w["region"] for w in killed),
                   life_by_region={g: [w["t1"] - w["t0"] for w in own if w["region"] == g and w["end"] in ("enemy", "natural")] for g in ("OWN_HALF", "RIVER", "ENEMY_HALF", "OWN_BASE", "ENEMY_BASE")},
                   rosh_placed=sum(w["rosh"] for w in own), rosh_killed=sum(w["rosh"] for w in killed),
                   killers=collections.Counter((hero[w["killer"]], pos[w["killer"]]) for w in killed),
                   kill_times=sorted(w["t1"] for w in killed), wards=own)
        # presence per 10 s from 10:00 to end-60
        ts = list(range(600, dur - 60, 10))
        alive = [sum(1 for w in own if w["t0"] <= t < w["t1"]) for t in ts]
        rec["zero_share"] = sum(1 for a in alive if a == 0) / max(1, len(alive))
        gaps = []; i = 0
        while i < len(ts):
            if alive[i] == 0:
                j = i
                while j + 1 < len(ts) and alive[j + 1] == 0: j += 1
                if (j - i + 1) * 10 >= 180:
                    prev = [w for w in own if w["t1"] <= ts[i] + 10]
                    last = max(prev, key=lambda w: w["t1"]) if prev else None
                    gaps.append((ts[i], ts[j] + 10, last["end"] if last else None))
                i = j + 1
            else: i += 1
        rec["gaps"] = gaps
        # geometric coverage, sampled each 60 s from 10:00
        cs, ce, cn = [], [], []
        for t in range(600, dur - 60, 60):
            cs.append(coverage([(w["x"], w["y"]) for w in own if w["t0"] <= t < w["t1"]]))
            ce.append(coverage([(w["x"], w["y"]) for w in enemyw if w["t0"] <= t < w["t1"]]))
            cn.append(coverage([(w["x"], w["y"]) for w in own if w["t0"] <= t < w["nominal_end"]]))
        rec["cov_own"] = st.fmean(cs) if cs else 0; rec["cov_enemy"] = st.fmean(ce) if ce else 0; rec["cov_nominal"] = st.fmean(cn) if cn else 0
        # sequences
        for w in killed:
            t, xy = w["t1"], (w["x"], w["y"])
            for W in (120, 300):
                if t + W > dur: continue
                near_after = sum(1 for d in deaths if d[3] == s_ and t < d[0] <= t + W and dist(xy, d[1:3]) <= VISION_R)
                any_after = sum(1 for d in deaths if d[3] == s_ and t < d[0] <= t + W)
                near_before = sum(1 for d in deaths if d[3] == s_ and t - W <= d[0] <= t and dist(xy, d[1:3]) <= VISION_R)
                enemy_near_after = sum(1 for d in deaths if d[3] != s_ and t < d[0] <= t + W and dist(xy, d[1:3]) <= VISION_R)
                towers = sum(1 for x in S if x["owner_radiant"] == s_ and x["kind"] in ("tower", "barracks") and t < x["time"] <= t + W)
                esmoke = sum(1 for a, b in smokes if b != s_ and t - 60 <= a <= t + W)
                ctrl = []
                for k in (-600, -420, -240, 240, 420, 600):
                    tc = t + k
                    if 0 <= tc and tc + W <= dur:
                        ctrl.append((sum(1 for d in deaths if d[3] == s_ and tc < d[0] <= tc + W and dist(xy, d[1:3]) <= VISION_R),
                                     sum(1 for d in deaths if d[3] == s_ and tc < d[0] <= tc + W),
                                     sum(1 for x in S if x["owner_radiant"] == s_ and x["kind"] in ("tower", "barracks") and tc < x["time"] <= tc + W)))
                SEQ[W].append(dict(mid=mid, side=s_, t=t, life=w["t1"] - w["t0"], region=w["region"], near_after=near_after, any_after=any_after, near_before=near_before,
                                   enemy_near_after=enemy_near_after, towers=towers, esmoke=esmoke, ctrl=ctrl))
            # natural-expiry control at same kind of spot
        for w in own:
            if w["end"] == "natural" and w["t1"] + 300 <= dur:
                t, xy = w["t1"], (w["x"], w["y"])
                SEQ["natural300"].append(dict(near_after=sum(1 for d in deaths if d[3] == s_ and t < d[0] <= t + 300 and dist(xy, d[1:3]) <= VISION_R),
                                             any_after=sum(1 for d in deaths if d[3] == s_ and t < d[0] <= t + 300)))
        TEAM[(mid, s_)] = rec
pickle.dump(dict(TEAM=TEAM, SEQ=dict(SEQ)), open("pb_exact.pkl", "wb"))
T = list(TEAM.values())
print("team units", len(T), "matches", len(MIDS), Counter(r["bucket"] for r in T) if False else collections.Counter(r["bucket"] for r in T))
allk = [x for r in T for x in r["life_killed"]]
print("observers placed", sum(r["placed"] for r in T), "enemy-killed", sum(r["killed"] for r in T), "own-denied", sum(r["own_denied"] for r in T), "other early end", sum(r["other_end"] for r in T))
print("killed lifetime median", st.median(allk), "share <=60s", round(sum(1 for x in allk if x <= 60) / len(allk), 2), "<=120s", round(sum(1 for x in allk if x <= 120) / len(allk), 2))
for r in T: r["share"] = r["killed"] / max(1, r["placed"]); r["upr"] = r["uptime"] / max(1, r["nominal"]); r["eupr"] = r["enemy_uptime"] / max(1, r["enemy_nominal"])
print("corr(share killed, uptime ratio)", round(st.correlation([r["share"] for r in T], [r["upr"] for r in T]), 3))
print("uptime ratio p10/p50/p90", [round(sorted(r["upr"] for r in T)[int(q * (len(T) - 1))], 2) for q in (.1, .5, .9)])
print("coverage own mean p50", round(st.median(r["cov_own"] for r in T), 3), "p10/p90", [round(sorted(r["cov_own"] for r in T)[int(q * (len(T) - 1))], 3) for q in (.1, .9)])
print("nominal minus actual coverage p50", round(st.median(r["cov_nominal"] - r["cov_own"] for r in T), 3))
print("zero-presence share after 10:00 p50", round(st.median(r["zero_share"] for r in T), 3), "units with a >=3-min gap", sum(1 for r in T if r["gaps"]), "gap causes", collections.Counter(g[2] for r in T for g in r["gaps"]))
reg_p = collections.Counter(); reg_k = collections.Counter(); life = collections.defaultdict(list)
for r in T:
    reg_p.update(r["regions_placed"]); reg_k.update(r["regions_killed"])
    for g, v in r["life_by_region"].items(): life[g] += v
print("region placed/killed/kill-rate/median life (enemy or natural end):", {g: (reg_p[g], reg_k[g], round(reg_k[g] / max(1, reg_p[g]), 2), st.median(life[g]) if life[g] else None) for g in reg_p})
print("roshan-area placed/killed", sum(r["rosh_placed"] for r in T), sum(r["rosh_killed"] for r in T))
tops = [(r["killers"].most_common(1)[0][1] / r["killed"], r["killed"]) for r in T if r["killed"] >= 5]
print("top dewarder share (units with >=5 killed):", sorted(round(a, 2) for a, b in tops))
for W in (120, 300):
    s = SEQ[W]; n = len(s)
    def m_(k): return round(st.fmean(x[k] for x in s), 3)
    def c_(i): return round(st.fmean(st.fmean(c[i] for c in x["ctrl"]) for x in s if x["ctrl"]), 3)
    def p_(k): return round(sum(1 for x in s if x[k] >= 1) / n, 3)
    def pc_(i): return round(st.fmean(st.fmean(1 if c[i] >= 1 else 0 for c in x["ctrl"]) for x in s if x["ctrl"]), 3)
    print(f"W={W}s events {n}: allied deaths near ward after mean {m_('near_after')} P>=1 {p_('near_after')} | control same spot other times mean {c_(0)} P>=1 {pc_(0)} | before-window near {m_('near_before')} P>=1 {p_('near_before')}")
    print(f"   allied deaths anywhere after mean {m_('any_after')} P>=1 {p_('any_after')} | control {c_(1)} P>=1 {pc_(1)} | own towers after P>=1 {p_('towers')} control {pc_(2)} | enemy deaths near after P>=1 {p_('enemy_near_after')} | enemy smoke in [-60,+W] P {p_('esmoke')}")
nat = SEQ["natural300"]
print("natural-expiry control W=300: near P>=1", round(sum(1 for x in nat if x["near_after"] >= 1) / len(nat), 3), "mean", round(st.fmean(x["near_after"] for x in nat), 3), "n", len(nat))

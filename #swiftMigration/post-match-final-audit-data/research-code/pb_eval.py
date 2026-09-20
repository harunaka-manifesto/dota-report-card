import os, sys, json, math, pickle, statistics as st
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); VI = os.path.join(HERE, "../vision-2026-09-16")
D = pickle.load(open("pb_holdout_raw.pkl", "rb")); core, pbd = D["core"], D["pb"]
os.chdir(VI); sys.path.insert(0, VI)
from common import ward_life, bucket, eligible_match, HEROES, pos_num
from geo import region
from ident import reconstruct
os.chdir(HERE)
SMOKE = 188
def elig(m):
    if bucket(m) is None or m.get("numHumanPlayers") != 10 or m["durationSeconds"] < 600: return False
    return all((p.get("stats") or {}).get("networthPerMinute") for p in m["players"]) and not any(p.get("leaverStatus") in ("ABANDONED", "AFK", "DISCONNECTED_TOO_LONG", "NEVER_CONNECTED", "NEVER_CONNECTED_TOO_LONG", "FAILED_TO_READY_UP", "DECLINED_READY_UP") for p in m["players"])
def lead_curve(m, side):
    out = []; t = 0
    while True:
        a = [p["stats"]["networthPerMinute"][t] if t < len(p["stats"]["networthPerMinute"]) else None for p in m["players"] if p["isRadiant"] == side]
        b = [p["stats"]["networthPerMinute"][t] if t < len(p["stats"]["networthPerMinute"]) else None for p in m["players"] if p["isRadiant"] != side]
        if None in a or None in b: break
        out.append(sum(a) - sum(b)); t += 1
    return out
V = Counter(); units = []; rule = Counter(); examples = []
for mid, pm in pbd.items():
    if not (pm.get("playbackData") or {}).get("wardEvents"): continue
    m = core.get(mid)
    if not m or not elig(m): V["inelig"] += 1; continue
    dur = m["durationSeconds"]; b = bucket(m)
    side = {p["playerSlot"]: p["isRadiant"] for p in m["players"]}
    L = [w for w in ward_life(pm, dur) if w["type"] == "OBSERVER" and w["owner"] in side]
    for w in L:
        w["side"] = side[w["owner"]]
        w["end"] = ("enemy" if side.get(w["killer"]) != w["side"] else "own") if w["killer"] is not None else ("match_end" if not w["ended"] else "natural_or_other")
    for s_ in (True, False):
        own = sorted((w["time"], w["positionX"], w["positionY"]) for p in m["players"] if p["isRadiant"] == s_ for w in p["stats"]["wards"] or [] if w["type"] == 0)
        esent = [(w["time"], w["positionX"], w["positionY"]) for p in m["players"] if p["isRadiant"] != s_ for w in p["stats"]["wards"] or [] if w["type"] == 1]
        kills = sorted(d["time"] for p in m["players"] if p["isRadiant"] != s_ for d in p["stats"]["wardDestruction"] or [] if d.get("isWard"))
        truth = [w for w in L if w["side"] == s_ and w["end"] == "enemy"]
        V["placed_stats"] += len(own); V["placed_pb"] += sum(1 for w in L if w["side"] == s_)
        V["kills_stats"] += len(kills); V["kills_pb"] += len(truth)
        res = reconstruct(own, kills, esent, dur, W=90, R=10, W2=0, R2=0)
        idd = []
        for t, i, tier in res:
            V[("n", tier)] += 1
            tw = next((w for w in truth if abs(w["t1"] - t) <= 1), None)
            if i is None or tier not in ("A", "C"): continue
            est = dict(t=t, t0=own[i][0], x=own[i][1], y=own[i][2], life=t - own[i][0], region=region(own[i][1], own[i][2], s_))
            idd.append(est)
            if tw is None: V[("no_truth", tier)] += 1; continue
            ok = abs(own[i][0] - tw["t0"]) <= 1 and own[i][1] == tw["x"] and own[i][2] == tw["y"]
            V[("ok", tier)] += ok; V[("eval", tier)] += 1
            V["region_eval"] += 1; V["region_ok"] += region(own[i][1], own[i][2], s_) == region(tw["x"], tw["y"], s_)
            V["quick_class_eval"] += 1; V["quick_class_ok"] += (est["life"] <= 90) == (tw["t1"] - tw["t0"] <= 90)
        # rules: estimate vs truth (v3 definitions)
        lc = lead_curve(m, s_)
        def quick(ws, placed):
            k = sum(1 for w in ws if w["t"] < dur - 300 and w["life"] <= 90)
            return k >= 4 and placed and k / placed >= .25, k
        tw_ = [dict(t=w["t1"], life=w["t1"] - w["t0"], region=region(w["x"], w["y"], s_)) for w in truth]
        qe, ke = quick(idd, len(own)); qt, kt = quick(tw_, len(own))
        def sweep(ws):
            best = 0
            for a in ws:
                c = [x for x in ws if x["region"] == a["region"] and a["t"] <= x["t"] <= a["t"] + 300]
                if max(x["t"] for x in c) >= dur - 300 or a["t"] < 300: continue
                lead0 = lc[min(len(lc) - 1, a["t"] // 60)] if lc else 0
                if abs(lead0) >= 10000 or st.median(x["life"] for x in c) > 180: continue
                best = max(best, len(c))
            return best >= 3, best
        se, sne = sweep(idd); stt, snt = sweep(tw_)
        rule[("quick", qt, qe)] += 1; rule[("sweep", stt, se)] += 1
        V["quick_abs_err"] += abs(ke - kt); V["units"] += 1
        units.append(dict(mid=mid, side=s_, bucket=b, quick_true=kt, quick_est=ke, sweep_true=snt, sweep_est=sne, identified=len(idd), kills=len(kills), truth=len(truth)))
prec = {t: round(V[("ok", t)] / V[("eval", t)], 3) for t in "AC" if V[("eval", t)]}
tot = sum(v for k, v in V.items() if isinstance(k, tuple) and k[0] == "n")
cov = {str(t): round(V[("n", t)] / tot, 3) for t in ("A", "C", None)}
out = dict(units=V["units"], matches=len({u["mid"] for u in units}), placed_stats=V["placed_stats"], placed_pb=V["placed_pb"], kills_stats=V["kills_stats"], kills_truth=V["kills_pb"],
           identity_precision=prec, overall_precision=round((V[("ok", "A")] + V[("ok", "C")]) / max(1, V[("eval", "A")] + V[("eval", "C")]), 3),
           coverage=cov, region_correct=round(V["region_ok"] / max(1, V["region_eval"]), 3), quick_class_agree=round(V["quick_class_ok"] / max(1, V["quick_class_eval"]), 3),
           quick_count_mean_abs_err=round(V["quick_abs_err"] / max(1, V["units"]), 2),
           rules={f"{k[0]}|truth={k[1]}|est={k[2]}": n for k, n in sorted(rule.items())}, bucket=dict(Counter(u["bucket"] for u in units)))
print(json.dumps(out, indent=1))
# ---------- smoke -> kills (modified rule) on fresh units
S = []; val = Counter()
for mid, pm in pbd.items():
    m = core.get(mid)
    if not m or not elig(m) or not pm.get("players"): continue
    side = {p["playerSlot"]: p["isRadiant"] for p in m["players"]}
    pbp = {p["playerSlot"]: p for p in pm["players"]}
    iu_total = sum(len(((pbp.get(s) or {}).get("playbackData") or {}).get("itemUsedEvents") or []) for s in side)
    if iu_total == 0: val["no_item_events"] += 1; continue
    herosid = {p["heroId"]: p["isRadiant"] for p in m["players"]}
    for s_ in (True, False):
        ev = sorted(e["time"] for s, p in pbp.items() if side.get(s) == s_ for e in ((p.get("playbackData") or {}).get("itemUsedEvents") or []) if e["itemId"] == SMOKE)
        cnt = sum(u["count"] for p in m["players"] if p["isRadiant"] == s_ for u in p["stats"]["itemUsed"] or [] if u["itemId"] == SMOKE)
        val["units"] += 1; val["count_match"] += len(ev) == cnt
        if len(ev) != cnt: continue
        kev = {(k["target"], k["time"]): k.get("isSmoke") for p in m["players"] if p["isRadiant"] == s_ for k in p["stats"]["killEvents"] or []}
        kills = [(d["time"], kev.get((d["target"], d["time"]))) for p in m["players"] if p["isRadiant"] != s_ for d in p["stats"]["deathEvents"] or [] if herosid.get(d.get("attacker")) == s_]
        n = len(ev)
        end = lambda i, t: min(t + 60, ev[i + 1]) if i + 1 < n else t + 60
        k = sum(1 for i, t in enumerate(ev) if any(t < x <= end(i, t) for x, _ in kills))
        f = sum(1 for i, t in enumerate(ev) if any(t < x <= end(i, t) and fl for x, fl in kills))
        # matched control: kill within 60 s at ordinary moments (same unit, +-5 min, >=120 s from any smoke)
        ctl = []
        for t in ev:
            for g in range(t - 300, t + 301, 5):
                if 0 < g < m["durationSeconds"] - 60 and all(abs(g - s) >= 120 for s in ev):
                    ctl.append(any(g < x <= g + 60 for x, _ in kills))
        fire = n >= 3 and k >= 3 and k >= 0.7 * n and f >= 2
        rate10 = n / m["durationSeconds"] * 600
        S.append(dict(mid=mid, side=s_, bucket=bucket(m), n=n, k=k, f=f, fire=fire, exp=round(n * (sum(ctl) / len(ctl)), 1) if ctl else None, base=round(sum(ctl) / len(ctl), 2) if ctl else None,
                      h3=(bucket(m) == "STANDARD" and n >= 4 and rate10 >= 1.60)))
fired = [u for u in S if u["fire"]]
sm = dict(val=dict(val), units=len(S), with3=sum(1 for u in S if u["n"] >= 3), fires=len(fired), fires_h3=sum(1 for u in fired if u["h3"]), h3_units=sum(1 for u in S if u["h3"]),
          fired_k_vs_expected=(sum(u["k"] for u in fired), round(sum(u["exp"] or 0 for u in fired), 1)),
          suppressed_ge3_k_vs_expected=(sum(u["k"] for u in S if not u["fire"] and u["n"] >= 3), round(sum(u["exp"] or 0 for u in S if not u["fire"] and u["n"] >= 3), 1)),
          smokes_followed=round(sum(u["k"] for u in S) / max(1, sum(u["n"] for u in S)), 3), base_rate=round(st.mean(u["base"] for u in S if u["base"] is not None), 3),
          fired_units=fired)
print(json.dumps({k: v for k, v in sm.items() if k != "fired_units"}, indent=1))
for u in fired: print(u)
json.dump(dict(vision=out, smoke=sm), open("pb_holdout_results.json", "w"), indent=1, default=str)

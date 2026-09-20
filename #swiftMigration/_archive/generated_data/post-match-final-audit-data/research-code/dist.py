import pickle, statistics as st
from collections import Counter
D = pickle.load(open("base.pkl", "rb")); R = [r for r in D["rows"] if not r["feed"]]; TH = D["TH"]
def Q(v, qs): v = sorted(x for x in v if x is not None); return [v[min(len(v)-1, int(round(q*(len(v)-1))))] for q in qs] if v else None
QS = (.5, .75, .9, .95, .975, .99)
U = {}
for r in R: U.setdefault((r["mid"], r["side"]), r)
U = list(U.values())
for b in ("STANDARD", "TURBO"):
    print("=====", b, "team units", sum(1 for u in U if u["bucket"] == b))
    RB = [r for r in R if r["bucket"] == b]; UB = [u for u in U if u["bucket"] == b]
    cores = [r for r in RB if r["role"] != "support" and r["lane"].get("lane_status") == "ok"]
    print("core |early| q", Q([abs(r["lane"]["nwdiff_early"]) for r in cores], QS), "\ncore |late| q", Q([abs(r["lane"]["nwdiff_late"]) for r in cores], QS))
    print("core |late-early| swing q", Q([abs(r["lane"]["nwdiff_late"] - r["lane"]["nwdiff_early"]) for r in cores], QS))
    print("L1 shapes cores", Counter(r["L1"]["shape"] for r in cores if r["L1"]))
    rev = [r for r in cores if r["L1"] and r["L1"]["shape"] in ("LOST_LEAD", "RECOVERED")]
    print("reversals", [(r["lane"]["nwdiff_early"], r["lane"]["nwdiff_late"]) for r in rev])
    pa = [r for r in cores if r["L1"] and r["L1"]["shape"] in ("PULLED_AWAY", "FELL_BEHIND")]
    print("pulled/fell", [(r["lane"]["nwdiff_early"], r["lane"]["nwdiff_late"]) for r in pa])
    wins = [u for u in UB if u["win"] and u["turn"].get("lead_min") is not None]; loss = [u for u in UB if not u["win"] and u["turn"].get("lead_max") is not None]
    print("comeback deficit (winners) q", Q([-u["turn"]["lead_min"] for u in wins], QS), "\nlost lead (losers) q", Q([u["turn"]["lead_max"] for u in loss], QS))
    fl = [max(u["flips"])[0] for u in UB if u["flips"]]
    print("flip minpeak q (units with flip)", Q(fl, QS), "n", len(fl), "TH flip75", TH[b]["flip75"])
    h = [u["hidden"] for u in UB]
    print("enemy stacks q", Q([x.get("enemy_stacks") for x in h], QS), "edge q", Q([x["enemy_stacks"] - x["own_stacks"] for x in h if "enemy_stacks" in x], QS))
    sr = [u["hidden"]["enemy_smokes"] / u["dur"] * 600 for u in UB]
    print("smoke rate q", [round(x, 2) for x in Q(sr, QS)], "count q", Q([x["enemy_smokes"] for x in h], QS))
    print("fastest goal q (low)", Q([x["enemy_fastest_goal"][0] for x in h if x.get("enemy_fastest_goal")], (.01, .025, .05, .1, .25)))
    gap = [ (x["own_fastest_goal"] - x["enemy_fastest_goal"][0]) if x.get("own_fastest_goal") is not None else 99 for x in h if x.get("enemy_fastest_goal")]
    print("goal gap q", Q(gap, QS))
    v = [u["vis"] for u in UB if u["vis"]]
    print("quick90 q", Q([x["quick90"] for x in v], QS), "cluster q", Q([x["cluster"] for x in v], QS))
    tb = Counter(u["tb"]["label"] for u in UB); print("tier B labels", tb)
    ct = [u["tb"] for u in UB if u["tb"]["label"] == "CT"]
    print("CT close share q", Q([t["close_share"] for t in ct], QS), "CT msg q", Q([t["max_sustained_gold"] for t in ct], (.1,.25,.5,.75,.9)), "CT window n q", Q([t["n"] for t in ct], QS))
    le = [u["tb"] for u in UB if u["tb"]["label"] in ("LE", "DR")]
    print("LE/DR erosion q", Q([t["detail"]["erosion"] for t in le], QS), "gold peak q", Q([t["detail"]["gold_ref"] for t in le], QS), "gold late q", Q([t["detail"]["gold_late"] for t in le], (.1,.25,.5,.75,.9)))
    ets = [u["tb"] for u in UB if u["tb"]["label"].startswith("ETS")]
    print("ETS sep minute q", Q([t["detail"]["sep_minute"] for t in ets], QS), "lead_after q", Q([abs(t["detail"]["lead_after"]) for t in ets], QS))

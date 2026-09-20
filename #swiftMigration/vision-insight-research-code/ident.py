"""Historical ward-identity reconstruction from enemy sentry placements; tuned and scored against playback truth."""
import math, statistics as st, collections, pickle, itertools
from common import *
from geo import *
def dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])
def reconstruct(own, kills, esent, dur, W=150, R=10, W2=300, R2=16):
    """own: [(t0,x,y)], kills: sorted times; returns list of (kill_time, ward index or None, confidence tier)."""
    life_end = {i: min(w[0] + 360, dur) for i, w in enumerate(own)}
    taken = set(); res = []
    for t in kills:
        cands = [i for i, w in enumerate(own) if w[0] <= t < life_end[i] and i not in taken]
        pick = None; tier = None
        for (ww, rr, tr) in ((W, R, "A"), (W2, R2, "B")):
            sc = []
            for i in cands:
                ds = [(t - ts, dist((x, y), own[i][1:])) for ts, x, y in esent if t - ww <= ts <= t and dist((x, y), own[i][1:]) <= rr]
                if ds: sc.append((min(d for _, d in ds), min(a for a, _ in ds), i))
            if len(sc) == 1 or (len(sc) > 1 and sorted(sc)[0][0] + 3 < sorted(sc)[1][0]):
                pick = sorted(sc)[0][2]; tier = tr; break
        if pick is None and len(cands) == 1: pick = cands[0]; tier = "C"
        if pick is not None: taken.add(pick)
        res.append((t, pick, tier))
    return res
if __name__ == "__main__":
    core, rep, pb = load_all()
    X = pickle.load(open("pb_exact.pkl", "rb"))["TEAM"]
    def evaluate(**kw):
        c = collections.Counter(); reg_ok = reg_n = 0; q_true = q_est = 0; per_unit = []
        for (mid, s_), rec in X.items():
            m = core[mid]; dur = m["durationSeconds"]
            own = sorted((w["time"], w["positionX"], w["positionY"]) for p in m["players"] if p["isRadiant"] == s_ for w in p["stats"]["wards"] or [] if w["type"] == 0)
            esent = [(w["time"], w["positionX"], w["positionY"]) for p in m["players"] if p["isRadiant"] != s_ for w in p["stats"]["wards"] or [] if w["type"] == 1]
            kills = sorted(d["time"] for p in m["players"] if p["isRadiant"] != s_ for d in p["stats"]["wardDestruction"] or [] if d.get("isWard"))
            res = reconstruct(own, kills, esent, dur, **kw)
            truth = [w for w in rec["wards"] if w["end"] == "enemy"]
            est_quick = 0
            for t, i, tier in res:
                tw = next((w for w in truth if abs(w["t1"] - t) <= 1), None)
                c[("n", tier)] += 1
                if i is None or tw is None: continue
                ok = abs(own[i][0] - tw["t0"]) <= 1 and own[i][1] == tw["x"] and own[i][2] == tw["y"]
                c[("ok", tier)] += ok
                reg_n += 1; reg_ok += region(own[i][1], own[i][2], s_) == tw["region"]
                est_quick += t - own[i][0] <= 90
            per_unit.append((sum(1 for w in truth if w["t1"] - w["t0"] <= 90), est_quick))
        tot = sum(v for k, v in c.items() if k[0] == "n")
        prec = {tr: round(c[("ok", tr)] / max(1, c[("n", tr)]), 2) for tr in "ABC"}
        cov = {tr: round(c[("n", tr)] / tot, 2) for tr in ("A", "B", "C", None)}
        return prec, cov, round(reg_ok / max(1, reg_n), 2), per_unit
    for W, R in itertools.product((60, 90, 150, 240), (8, 10, 14)):
        prec, cov, rg, pu = evaluate(W=W, R=R)
        print(f"W={W} R={R}: precision {prec} coverage {cov} region-correct {rg}")
    prec, cov, rg, pu = evaluate()
    print("chosen W=150 R=10 then W2=300 R2=16:", prec, cov, rg)
    print("quick<=90 per unit (true, estimated from identified only):", pu)

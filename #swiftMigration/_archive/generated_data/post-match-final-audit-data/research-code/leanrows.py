"""Fresh validation rows from the lean corpus (matches NOT in the 886 tuning corpus).
Produces pool-compatible viewpoint rows for the tracked account's player only (one viewpoint per match per account),
with Tier B classification (frozen thresholds) + perturbation confidence, lead story, hidden (stacks/smokes/rich), enemy items.
Vision is unavailable in the lean query (vis=None)."""
import os, sys, pickle, json
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
TB = os.path.join(HERE, "../tier-b-2026-09-15")
import histbuild as HB                       # loads M (all matches) + helpers (chdir-safe)
os.chdir(TB); sys.path.insert(0, TB)
import shape as SH
from modifiers import modifiers
F = pickle.load(open("final.pkl", "rb"))
os.chdir(HERE)
P_FINAL, B, TT = F["P_FINAL"], F["B"], F["TT"]
from primitives import structures, bucket, pos_num, HEROES
base = pickle.load(open("base.pkl", "rb"))
TUNING = {r["mid"] for r in base["rows"]}
CHECK = {"STANDARD": dict(late=10, lane_end=12, stack=20, goal=10000), "TURBO": dict(late=8, lane_end=9, stack=15, goal=15000)}

def team_nw(m, side, t):
    v = [HB.nw(p, t) for p in m["players"] if p["isRadiant"] == side]
    return None if any(x is None for x in v) else sum(v)
def lead_curve(m, side):
    out = []; t = 0
    while True:
        a, b = team_nw(m, side, t), team_nw(m, not side, t)
        if a is None or b is None: break
        out.append(a - b); t += 1
    return out

H = json.load(open("long_histories.json"))
want = {}
for a, seq in H.items():
    for s in seq:
        if s["id"] not in TUNING and s["slot"] is not None: want.setdefault(s["id"], []).append((a, s["slot"]))
rows = []; exc = Counter(); units = []
for mid, lst in want.items():
    m = HB.M.get(mid)
    if m is None: exc["missing"] += 1; continue
    e = HB.elig(m)
    if e: exc[e] += 1; continue
    b = bucket(m)
    lc_r = lead_curve(m, True)
    tot = [team_nw(m, True, t) + team_nw(m, False, t) for t in range(len(lc_r))]
    S = [s for s in structures(m) if s["kind"] in ("tower", "barracks")]
    feed = any(sum(1 for d in (x["stats"].get("deathEvents") or []) if d["time"] < CHECK[b]["late"] * 60) >= 8 for x in m["players"])
    U = {}
    for side in (True, False):
        sg = 1 if side else -1; lc = [sg * v for v in lc_r]
        U[side] = dict(mid=mid, side=side, bucket=b, dur=m["durationSeconds"], src="lean", win=(m["didRadiantWin"] == side), lc=lc, tot=tot,
                       R=[l / t if t else 0.0 for l, t in zip(lc, tot)], structs=[(s["time"], s["owner_radiant"] == side, s["kind"], s["tier"]) for s in S], feed=feed)
    for acct, slot in lst:
        p = next((x for x in m["players"] if x["playerSlot"] == slot), None)
        if p is None: continue
        side = p["isRadiant"]; u = U[side]
        units.append(u)
        hr = HB.row(m, slot)
        enemy = [x for x in m["players"] if x["isRadiant"] != side]
        ek = {}
        for x in enemy:
            for n, t in HB.first_buy(x).items():
                if n not in ek or t < ek[n][0]: ek[n] = (t, HEROES.get(x["heroId"]), pos_num(x))
        eg = hr["enemy_goal"]
        hidden = dict(enemy_smokes=hr["enemy_smokes"], own_smokes=hr["own_smokes"],
                      enemy_fastest_goal=(eg[0], eg[1], next(pos_num(x) for x in enemy if HEROES.get(x["heroId"]) == eg[1])) if eg else None,
                      own_fastest_goal=hr["own_goal"])
        if "enemy_stacks" in hr: hidden.update(enemy_stacks=hr["enemy_stacks"], own_stacks=hr["own_stacks"])
        lc = u["lc"]
        rows.append(dict(mid=mid, slot=slot, side=side, acct=acct, bucket=b, dur=m["durationSeconds"], patch=m.get("gameVersionId"), start=m["startDateTime"],
                         win=p["isVictory"], pos=pos_num(p), role=hr["role"], hero=hr["hero"], feed=feed, has_pb=False,
                         lane={"lane_status": "lean"}, turn=dict(lead_min=min(lc), lead_max=max(lc), win=p["isVictory"]) if lc else {},
                         hidden=hidden, enemy_key_first=ek, lc=lc, flips=[], vis=None, hist=hr))
# ---- Tier B classification with frozen thresholds + perturbation confidence
uu = {(u["mid"], u["side"]): u for u in units}
UL = list(uu.values())
RES = {k: SH.analyze(u, P_FINAL, TT) for k, u in uu.items()}
_, CONF = SH.stability(UL, P_FINAL, B)
for r in rows:
    k = (r["mid"], r["side"]); r["tb"] = RES[k]; r["tb_conf"] = CONF[k]; r["tb_mods"] = modifiers(uu[k], RES[k])
pickle.dump(rows, open("lean_rows.pkl", "wb"))
print("rows", len(rows), "matches", len({r['mid'] for r in rows}), "excluded", dict(exc), Counter(r["bucket"] for r in rows))
print("labels", Counter(SH.base_of(RES[k]["label"]) for k in uu))

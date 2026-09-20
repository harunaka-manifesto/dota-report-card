"""Build one per-viewpoint fact table for the final locked pool (research). Reuses the validated calculators.
Outputs base.pkl: rows (viewpoint facts), TH (thresholds), TURN, per-team vision/tier-B facts."""
import os, sys, io, contextlib, pickle, statistics as st
from collections import defaultdict, Counter
HERE = os.path.dirname(os.path.abspath(__file__))
CV = os.path.join(HERE, "../candidate-validation-2026-09-15")
TB = os.path.join(HERE, "../tier-b-2026-09-15")
VI = os.path.join(HERE, "../vision-2026-09-16")
os.chdir(CV); sys.path.insert(0, CV)
with contextlib.redirect_stdout(io.StringIO()):
    import evaluate_v2 as E
from primitives import *
from metrics import CHECK
os.chdir(HERE)
rows, core, TH, TURN, F = E.rows, E.core, E.TH, E.TURN, E.F
TBF = pickle.load(open(f"{TB}/final.pkl", "rb"))
TBU = {(u["mid"], u["side"]): u for u in pickle.load(open(f"{TB}/units.pkl", "rb"))["U"]}
GATE = pickle.load(open(f"{TB}/tier_a_gate.pkl", "rb"))
VIS = {(u["mid"], u["side"]): u for u in pickle.load(open(f"{VI}/hist_ident_units.pkl", "rb"))}
feed = GATE["feed"]
mins = lambda mid: core[mid]["durationSeconds"] / 60
out = []
for r in rows:
    mid, side = r["match_id"], r["side_radiant"]
    m = core[mid]
    p = next(x for x in m["players"] if x["playerSlot"] == r["slot"])
    x = dict(mid=mid, slot=r["slot"], side=side, bucket=r["bucket"], dur=r["duration"], patch=r["patch"], start=r["start"], win=r["win"],
             pos=r["pos"], role=r["role"], hero=r["hero"], feed=mid in feed, has_pb=r["has_playback"])
    x["lane"] = r["lane"]; x["turn"] = {k: v for k, v in r["turn"].items() if k not in ("structures", "clashes", "clash_conversions")}
    x["hidden"] = r["hidden"]; x["items_key_first"] = r["items"]["key_first"]; x["enemy_key_first"] = r["items"]["enemy_key_first"]
    x["L1"] = F["L1_LANE_LEAD_PATH"](r); x["L5"] = F["L5_COUNTERPART_EXTREME_START"](r); x["T2"] = F["T2_LEAD_FLIP"](r)
    x["T3"] = F["T3_COMEBACK_OR_LOST_LEAD"](r); x["H1"] = F["H1_ENEMY_STACKING"](r); x["H3"] = F["H3_ENEMY_SMOKES"](r)
    x["H6"] = F["H6_ENEMY_FAST_CORE"](r); x["I3"] = F["I3_ENEMY_EARLY_SPIKE_ITEM"](r)
    x["lc"] = TURN[(mid, side)]["lc"]; x["flips"] = TURN[(mid, side)]["flips"]
    x["tb"] = TBF["RES"].get((mid, side)); x["tb_conf"] = TBF["CONF"].get((mid, side)); x["tb_mods"] = TBF["MODS"].get((mid, side))
    x["vis"] = {k: v for k, v in VIS[(mid, side)].items() if k not in ("kill_times",)} if (mid, side) in VIS else None
    x["deaths_before_late"] = deaths_before(p, CHECK[r["bucket"]]["late"] * 60)
    out.append(x)
pickle.dump(dict(rows=out, TH=TH, CHECK=CHECK, TB_TT=TBF["TT"], TBU=TBU, SPIKE=E.SPIKE_ITEMS, HIST=E.HIST and {a: [(q["match_id"], q["slot"]) for q in seq] for a, seq in E.HIST.items()}), open("base.pkl", "wb"))
print(len(out), Counter(x["bucket"] for x in out), "feed vps", sum(x["feed"] for x in out), "vis missing", sum(1 for x in out if x["vis"] is None), "tb missing", sum(1 for x in out if x["tb"] is None))

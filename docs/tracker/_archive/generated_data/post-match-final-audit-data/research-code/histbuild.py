"""Build chronological per-account history rows from the lean corpus (+ full corpus where cached).
Output hist_rows.pkl: {acct: [row ...]} sorted by start. Row = the account's viewpoint metrics needed by history cards
and by history-enriched enemy cards. No account ids leave this directory; accounts are h00..h30."""
import os, sys, json, glob, pickle
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
CV = os.path.join(HERE, "../candidate-validation-2026-09-15")
os.chdir(CV); sys.path.insert(0, CV)
from primitives import (ITEMS, ITEM_ID, HEROES, bucket, BAD_LEAVER, pos_num, map_lane, COUNTER)
os.chdir(HERE)
CHECK = {"STANDARD": dict(early=5, late=10, stack=20, goal=10000), "TURBO": dict(early=4, late=8, stack=15, goal=15000)}
SPIKE = ["item_black_king_bar", "item_blink", "item_radiance", "item_hand_of_midas", "item_manta", "item_desolator", "item_bfury", "item_maelstrom", "item_ultimate_scepter", "item_orchid"]
SPIKE_IDS = {ITEM_ID[n]: n for n in SPIKE}
SMOKE = ITEM_ID["item_smoke_of_deceit"]

M = {}
for f in glob.glob("raw/lean_*.json") + glob.glob("../deep-research-2026-09-14/raw/cvA_*.json") + glob.glob("../deep-research-2026-09-14/raw/corpusA_*.json") + glob.glob("../deep-research-2026-09-14/raw/historyA_*.json"):
    for m in (json.load(open(f)).get("data") or {}).values():
        if m and m.get("players") and m["id"] not in M: M[m["id"]] = m

def elig(m):
    if bucket(m) is None: return "mode"
    if m.get("numHumanPlayers") != 10: return "humans"
    if (m.get("durationSeconds") or 0) < 600: return "short"
    ps = m["players"]
    if len(ps) != 10 or any(not (p.get("stats") or {}).get("networthPerMinute") for p in ps): return "no_stats"
    if any(p.get("leaverStatus") in BAD_LEAVER for p in ps): return "leaver"
    if sorted(p.get("position") or "" for p in ps) != sorted(["POSITION_1", "POSITION_2", "POSITION_3", "POSITION_4", "POSITION_5"] * 2): return "positions"
    return None

def nw(p, t):
    a = p["stats"]["networthPerMinute"]; return a[t] if 0 <= t < len(a) and a[t] is not None else None
def cs(p, t):
    a = p["stats"].get("lastHitsPerMinute") or []; return sum(x or 0 for x in a[:t]) if len(a) >= t else None
def stacks(p, t):
    a = p["stats"].get("campStack") or []; return a[t - 1] if len(a) >= t else None
def first_buy(p):
    out = {}
    for e in sorted(p["stats"].get("itemPurchases") or [], key=lambda e: e["time"]):
        if e["itemId"] in SPIKE_IDS and SPIKE_IDS[e["itemId"]] not in out: out[SPIKE_IDS[e["itemId"]]] = e["time"]
    return out
def goal_min(p, goal):
    return next((i for i, v in enumerate(p["stats"]["networthPerMinute"]) if v is not None and v >= goal), None)

def row(m, slot):
    b = bucket(m); C = CHECK[b]
    p = next((x for x in m["players"] if x["playerSlot"] == slot), None)
    if p is None: return None
    side = p["isRadiant"]; team = [x for x in m["players"] if x["isRadiant"] == side]; enemy = [x for x in m["players"] if x["isRadiant"] != side]
    feed = any(sum(1 for d in (x["stats"].get("deathEvents") or []) if d["time"] < C["late"] * 60) >= 8 for x in m["players"])
    r = dict(mid=m["id"], start=m["startDateTime"], bucket=b, dur=m["durationSeconds"], patch=m.get("gameVersionId"), win=p["isVictory"],
             pos=pos_num(p), role={1: "carry", 2: "mid", 3: "offlane", 4: "support", 5: "support"}[pos_num(p)], hero=HEROES.get(p["heroId"]), feed=feed)
    opp = [q for q in enemy if pos_num(q) == COUNTER[pos_num(p)]]
    q = opp[0] if len(opp) == 1 and map_lane(p) and map_lane(p) == map_lane(opp[0]) else None
    if q is not None:
        a, o = nw(p, C["late"]), nw(q, C["late"])
        r["lane_diff"] = a - o if a is not None and o is not None else None
        r["opp_pos"] = pos_num(q); r["opp_hero"] = HEROES.get(q["heroId"])
        r["opp_val"] = cs(q, C["late"]) if pos_num(q) <= 3 else nw(q, C["late"])
    r["own_items"] = first_buy(p)
    if m["durationSeconds"] >= C["stack"] * 60:
        es = [stacks(x, C["stack"]) for x in enemy]; os_ = [stacks(x, C["stack"]) for x in team]
        if None not in es and None not in os_: r["enemy_stacks"] = sum(es); r["own_stacks"] = sum(os_)
    iu = lambda x: sum((u.get("count") or 0) for u in (x["stats"].get("itemUsed") or []) if u["itemId"] == SMOKE)
    r["enemy_smokes"] = sum(iu(x) for x in enemy); r["own_smokes"] = sum(iu(x) for x in team)
    eg = [(goal_min(x, C["goal"]), HEROES.get(x["heroId"])) for x in enemy]; eg = [g for g in eg if g[0] is not None]
    r["enemy_goal"] = min(eg) if eg else None
    og = [goal_min(x, C["goal"]) for x in team]; og = [g for g in og if g is not None]
    r["own_goal"] = min(og) if og else None
    ek = {}
    for x in enemy:
        if pos_num(x) > 3: continue
        for n, t in first_buy(x).items():
            if n not in ek or t < ek[n][0]: ek[n] = (t, HEROES.get(x["heroId"]), pos_num(x))
    r["enemy_items"] = ek
    return r

H = json.load(open("long_histories.json"))
T = json.load(open("../candidate-validation-2026-09-15/tracked_histories.json"))
OUT = {}; exc = Counter(); pat = Counter()
for a, seq in H.items():
    rows = []
    for s in sorted(seq, key=lambda x: x["start"]):
        m = M.get(s["id"])
        if m is None: exc["missing"] += 1; continue
        e = elig(m)
        if e: exc[e] += 1; continue
        if s["slot"] is None: exc["noslot"] += 1; continue
        x = row(m, s["slot"])
        if x: rows.append(x); pat[x["patch"]] += 1
    OUT[a] = rows
pickle.dump(OUT, open("hist_rows.pkl", "wb"))
print("accounts", len(OUT), "rows", sum(len(v) for v in OUT.values()), "excluded", dict(exc), "patches", dict(pat))
print("bucket", Counter(r["bucket"] for v in OUT.values() for r in v), "role", Counter(r["role"] for v in OUT.values() for r in v))
print("per-account rows", sorted(len(v) for v in OUT.values()))

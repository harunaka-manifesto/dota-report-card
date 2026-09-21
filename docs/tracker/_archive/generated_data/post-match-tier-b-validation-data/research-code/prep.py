"""Extract team-unit trajectories (lead, totals, structures) for current corpus + older-patch sample."""
import json, glob, pickle, collections
from collections import Counter, defaultdict
from primitives import *
from metrics import CHECK
core, rep, pb = load_matches()
gate = pickle.load(open("tier_a_gate.pkl", "rb"))
def units_of(m, src):
    b = bucket(m); out = []
    lc_r = lead_curve(m, True)
    tot = []
    for t in range(len(lc_r)):
        tot.append(team_nw(m, True, t) + team_nw(m, False, t))
    S = [s for s in structures(m) if s["kind"] in ("tower", "barracks")]
    for side in (True, False):
        sg = 1 if side else -1
        lc = [sg * v for v in lc_r]
        out.append(dict(mid=m["id"], side=side, bucket=b, patch=m.get("gameVersionId"), start=m["startDateTime"], dur=m["durationSeconds"], src=src,
                        win=(m["didRadiantWin"] == side), lc=lc, tot=tot, R=[l / t if t else 0.0 for l, t in zip(lc, tot)],
                        structs=[(s["time"], s["owner_radiant"] == side, s["kind"], s["tier"]) for s in S], feed=m["id"] in gate["feed"]))
    return out
U = []; exc = Counter()
for mid, m in core.items():
    ok, why = eligible_match(m)
    if ok: U += units_of(m, "current")
    else: exc[why] += 1
old = {}
for f in sorted(glob.glob("../deep-research-2026-09-14/raw/tbOld_*.json")):
    for m in (json.load(open(f)).get("data") or {}).values():
        if m and m["id"] not in core: old[m["id"]] = m
oexc = Counter()
for mid, m in old.items():
    ok, why = eligible_match(m)
    if ok: U += units_of(m, "old")
    else: oexc[why] += 1
T = json.load(open("tracked_histories.json"))
hs = json.load(open("../deep-research-2026-09-14/history_self.json"))["self"]
T["acct8"] = [{"id": h["id"], "slot": h["slot"], "start": h["start"]} for h in hs]
acct_of = defaultdict(set)
for a, ms in T.items():
    for x in ms: acct_of[x["id"]].add(a)
cur = {u["mid"]: u for u in U if u["src"] == "current" and u["side"]}
print("current units", sum(1 for u in U if u["src"] == "current"), "old units", sum(1 for u in U if u["src"] == "old"), "excluded", exc, "old excluded", oexc)
print("old patches", Counter(u["patch"] for u in U if u["src"] == "old" and u["side"]), Counter(u["bucket"] for u in U if u["src"] == "old" and u["side"]))
print("multi-account matches", sum(1 for m in cur if len(acct_of[m]) > 1))
for a in sorted(T):
    ms = [m for m in cur if a in acct_of[m]]
    print(a, len(ms), Counter(cur[m]["bucket"] for m in ms), "feed", sum(cur[m]["feed"] for m in ms))
print("untracked", sum(1 for m in cur if not acct_of[m]), Counter(cur[m]["bucket"] for m in cur if not acct_of[m]))
pickle.dump(dict(U=U, acct_of={k: sorted(v) for k, v in acct_of.items()}), open("units.pkl", "wb"))

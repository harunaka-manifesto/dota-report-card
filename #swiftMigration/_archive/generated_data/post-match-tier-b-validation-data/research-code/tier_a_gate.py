"""Phase 1: reconstruct the Tier A gate with the product pool from the Tier B prompt (no playback, no L4, no T1)."""
import io, json, pickle, contextlib, collections, statistics as st
from collections import defaultdict, Counter
with contextlib.redirect_stdout(io.StringIO()):
    import evaluate_v2 as E
from primitives import *
from metrics import CHECK
rows, core, F, TH = E.rows, E.core, E.F, E.TH
def Q(v, q): v = sorted(x for x in v if x is not None); return v[min(len(v)-1, int(round(q*(len(v)-1))))] if v else None
mins = lambda r: core[r["match_id"]]["durationSeconds"] / 60
feed = set()
for r in rows:
    m = core[r["match_id"]]; t = CHECK[r["bucket"]]["late"] * 60
    if r["match_id"] not in feed and any(sum(1 for d in p["stats"]["deathEvents"] or [] if d["time"] < t) >= 8 for p in m["players"]): feed.add(r["match_id"])
# rate-based hidden thresholds (as final_metrics.py)
HT = {}
for b in ("STANDARD", "TURBO"):
    UB = [u for u in E.U if u["bucket"] == b]
    HT[b] = dict(orate10=Q([u["hidden"]["enemy_obs"] / mins(u) * 10 for u in UB], .1), krate90=Q([u["hidden"]["enemy_obs_killed_our"] / mins(u) * 10 for u in UB], .9),
                 share75=Q([u["hidden"]["our_obs_destroyed_share"] for u in UB if u["hidden"]["own_obs"] >= 8], .75), srate90=Q([u["hidden"]["enemy_smokes"] / mins(u) * 10 for u in UB], .9))
def H2ra(r):
    h = r["hidden"]; T = HT[r["bucket"]]
    return h["own_obs"] >= 8 and (h["our_obs_destroyed_share"] or 0) >= T["share75"] and h["enemy_obs_killed_our"] / mins(r) * 10 >= T["krate90"]
def H2rb(r): return r["hidden"]["enemy_obs"] / mins(r) * 10 <= HT[r["bucket"]]["orate10"]
def H3r(r):
    h = r["hidden"]; b = r["bucket"]
    return h["enemy_smokes"] / mins(r) * 10 >= HT[b]["srate90"] and h["enemy_smokes"] >= (4 if b == "STANDARD" else 3) and h["enemy_smokes"] >= h["own_smokes"] + 2
def tuned(cid, r): x = F[cid](r); return bool(x and x.get("tuned"))
FIRE = defaultdict(list)   # (match, slot) -> [candidate ids]
for r in rows:
    k = (r["match_id"], r["slot"]); core_role = E.rg(r) == "core"
    if core_role and tuned("L1_LANE_LEAD_PATH", r): FIRE[k].append("L1")
    if tuned("L8_SUPPORT_LANE_PAIR", r): FIRE[k].append("L8")
    if tuned("L5_COUNTERPART_EXTREME_START", r): FIRE[k].append("L5")
    if tuned("L3_CS_NW_SPLIT", r): FIRE[k].append("L3")
    if tuned("T2_LEAD_FLIP", r): FIRE[k].append("T2")
    if tuned("T3_COMEBACK_OR_LOST_LEAD", r): FIRE[k].append("T3")
    if tuned("T6_STRUCTURES_WHILE_DEAD", r): FIRE[k].append("T6")
    if r["bucket"] == "STANDARD" and tuned("H1_ENEMY_STACKING", r): FIRE[k].append("H1")
    if H2ra(r): FIRE[k].append("H2r-a")
    if H2rb(r): FIRE[k].append("H2r-b")
    if H3r(r): FIRE[k].append("H3r")
    if tuned("H5_ENEMY_BOSS_CONTROL", r): FIRE[k].append("H5")
    if tuned("H6_ENEMY_FAST_CORE", r): FIRE[k].append("H6")
    if tuned("I3_ENEMY_EARLY_SPIKE_ITEM", r): FIRE[k].append("I3")
    if core_role and tuned("L4_LEVEL6_RACE", r): FIRE[k].append("L4*")      # sensitivity only
# history-gated L6 / I8 on tracked accounts
HISTINFO = {}
for acct, seq in E.HIST.items():
    prior_l6 = defaultdict(list); prior_i8 = defaultdict(list); nb = Counter()
    for r in seq:
        k = (r["match_id"], r["slot"]); L = r["lane"]
        HISTINFO[k] = dict(acct=acct, prior_bucket=nb[r["bucket"]])
        if L.get("lane_status") == "ok" and L.get("nwdiff_late") is not None:
            pr = prior_l6[(r["bucket"], r["role"])]
            if len(pr) >= 10 and (L["nwdiff_late"] > max(pr) or L["nwdiff_late"] < min(pr)): FIRE[k].append("L6")
            pr.append(L["nwdiff_late"])
        hit = False
        for n, t in r["items"]["key_first"].items():
            if n not in E.SPIKE_ITEMS: continue
            pr = prior_i8[(r["bucket"], n)]
            if len(pr) >= 10 and (t < min(pr) or t > max(pr)): hit = True
            pr.append(t)
        if hit: FIRE[k].append("I8")
        nb[r["bucket"]] += 1
FAM = {"L1": "lane", "L8": "lane", "L5": "lane", "L3": "lane", "L6": "lane", "T2": "turning", "T3": "turning", "T6": "turning",
       "H1": "hidden", "H2r-a": "hidden", "H2r-b": "hidden", "H3r": "hidden", "H5": "hidden", "H6": "hidden", "I3": "items", "I8": "items"}
VP = [r for r in rows if r["match_id"] not in feed]
def empty(r, with_l4=False):
    f = FIRE.get((r["match_id"], r["slot"]), [])
    return not [c for c in f if c in FAM or (with_l4 and c == "L4*")]
def pctf(rs, fn): return round(100 * sum(1 for r in rs if fn(r)) / len(rs), 1) if rs else None
out = dict(viewpoints=len(VP), matches=len({r["match_id"] for r in VP}), feed_excluded_matches=len(feed), hidden_rate_thresholds=HT,
           empty_pct=pctf(VP, empty), empty_pct_with_L4=pctf(VP, lambda r: empty(r, True)),
           empty_by_bucket={b: pctf([r for r in VP if r["bucket"] == b], empty) for b in ("STANDARD", "TURBO")},
           empty_by_role={ro: pctf([r for r in VP if r["role"] == ro], empty) for ro in ("carry", "mid", "offlane", "support")},
           empty_by_outcome={w: pctf([r for r in VP if r["win"] == (w == "win")], empty) for w in ("win", "loss")},
           empty_tracked_established=pctf([r for r in VP if HISTINFO.get((r["match_id"], r["slot"]), {}).get("prior_bucket", 0) >= 10], empty),
           empty_untracked_or_new=pctf([r for r in VP if HISTINFO.get((r["match_id"], r["slot"]), {}).get("prior_bucket", 0) < 10], empty),
           candidate_vp_rate={c: pctf(VP, lambda r, c=c: c in FIRE.get((r["match_id"], r["slot"]), [])) for c in list(FAM) + ["L4*"]},
           families_with_any=dict(sorted(Counter(len({FAM[c] for c in FIRE.get((r["match_id"], r["slot"]), []) if c in FAM}) for r in VP).items())),
           team_units_both_viewpoints_all_empty=None)
# match-level: share of matches where every viewpoint empty; team-level: every viewpoint of team empty
bym = defaultdict(list)
for r in VP: bym[(r["match_id"], r["side_radiant"])].append(empty(r))
out["team_units_all_5_empty_pct"] = round(100 * sum(1 for v in bym.values() if all(v)) / len(bym), 1)
out["tracked_viewpoints"] = sum(1 for r in VP if (r["match_id"], r["slot"]) in HISTINFO)
# leave-one-out ablation: what each candidate removes from the empty pool
out["unique_coverage_pct"] = {c: pctf(VP, lambda r, c=c: FIRE.get((r["match_id"], r["slot"]), []) and set(x for x in FIRE[(r["match_id"], r["slot"])] if x in FAM) == {c}) for c in FAM}
print(json.dumps(out, indent=1, default=str))
json.dump(out, open("tier_a_gate.json", "w"), indent=1, default=str)
pickle.dump(dict(FIRE=dict(FIRE), HISTINFO=HISTINFO, feed=feed, HT=HT), open("tier_a_gate.pkl", "wb"))

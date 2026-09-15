"""v3 patches: duration-normalised vision/smoke, Turbo stacking floor, feeding guard, support flip noise."""
import json, collections, statistics as st, random
from collections import Counter
from primitives import *
from metrics import build_rows, CHECK
random.seed(7)
core, rep, pb = load_matches()
rows, exc = build_rows(core, rep, pb)
def units(rs):
    s = {}
    for r in rs: s.setdefault((r["match_id"], r["side_radiant"]), r)
    return list(s.values())
U = units(rows)
def Q(v, q): v = sorted(x for x in v if x is not None); return v[min(len(v)-1, int(round(q*(len(v)-1))))] if v else None
out = {}
# feeding guard: any player with >=8 deaths before late checkpoint
feed = set()
for mid, m in core.items():
    ok, _ = eligible_match(m)
    if not ok: continue
    t = CHECK[bucket(m)]["late"] * 60
    if any(sum(1 for d in p["stats"]["deathEvents"] or [] if d["time"] < t) >= 8 for p in m["players"]): feed.add(mid)
out["feeding_matches"] = (len(feed), len({r["match_id"] for r in rows}))
print("feeding-guard matches (any player >=8 deaths before lane end):", out["feeding_matches"])
for b in ("STANDARD", "TURBO"):
    UB = [u for u in U if u["bucket"] == b]
    mins = lambda u: core[u["match_id"]]["durationSeconds"] / 60
    obs_rate = [u["hidden"]["enemy_obs"] / mins(u) * 10 for u in UB]
    smoke_rate = [u["hidden"]["enemy_smokes"] / mins(u) * 10 for u in UB]
    killed_rate = [u["hidden"]["enemy_obs_killed_our"] / mins(u) * 10 for u in UB]
    th = dict(obs_rate90=Q(obs_rate, .9), obs_rate95=Q(obs_rate, .95), smoke_rate90=Q(smoke_rate, .9), smoke_rate95=Q(smoke_rate, .95), killed_rate90=Q(killed_rate, .9))
    # corr with duration for raw counts vs rates
    import math
    def corr(a, b):
        ma, mb = st.mean(a), st.mean(b); sa = math.sqrt(sum((x-ma)**2 for x in a)); sb = math.sqrt(sum((y-mb)**2 for y in b))
        return sum((x-ma)*(y-mb) for x, y in zip(a, b)) / (sa*sb) if sa and sb else 0
    dur = [mins(u) for u in UB]
    th["corr_duration"] = dict(obs_count=round(corr([u["hidden"]["enemy_obs"] for u in UB], dur), 2), obs_rate=round(corr(obs_rate, dur), 2),
                               smoke_count=round(corr([u["hidden"]["enemy_smokes"] for u in UB], dur), 2), smoke_rate=round(corr(smoke_rate, dur), 2),
                               stacks_count=round(corr([u["hidden"].get("enemy_stacks", 0) for u in UB], dur), 2))
    # H2' rate-based: heavy = enemy obs rate >= p90 and >=8 obs; cleared = own_obs>=8 & destroyed share>=p75 & destroyed rate>=p90
    share75 = Q([u["hidden"]["our_obs_destroyed_share"] for u in UB if u["hidden"]["own_obs"] >= 8], .75)
    heavy = [u for u in UB if u["hidden"]["enemy_obs"] / mins(u) * 10 >= th["obs_rate90"] and u["hidden"]["enemy_obs"] >= 8]
    cleared = [u for u in UB if u["hidden"]["own_obs"] >= 8 and (u["hidden"]["our_obs_destroyed_share"] or 0) >= share75 and u["hidden"]["enemy_obs_killed_our"] / mins(u) * 10 >= th["killed_rate90"]]
    th["H2r_heavy_pct"] = round(100 * len(heavy) / len(UB), 1); th["H2r_cleared_pct"] = round(100 * len(cleared) / len(UB), 1)
    th["H2r_union_pct"] = round(100 * len({(u["match_id"], u["side_radiant"]) for u in heavy + cleared}) / len(UB), 1)
    th["H2r_heavy_duration_p50"] = Q([mins(u) for u in heavy], .5); th["all_duration_p50"] = Q(dur, .5)
    smoke = [u for u in UB if u["hidden"]["enemy_smokes"] / mins(u) * 10 >= th["smoke_rate90"] and u["hidden"]["enemy_smokes"] >= (4 if b == "STANDARD" else 3) and u["hidden"]["enemy_smokes"] >= u["hidden"]["own_smokes"] + 2]
    th["H3r_pct"] = round(100 * len(smoke) / len(UB), 1); th["H3r_duration_p50"] = Q([mins(u) for u in smoke], .5)
    # H1 Turbo absolute floor
    if b == "TURBO":
        st5 = [u for u in UB if u["hidden"].get("enemy_stacks", 0) >= 5 and u["hidden"]["enemy_stacks"] - u["hidden"]["own_stacks"] >= 3]
        st4 = [u for u in UB if u["hidden"].get("enemy_stacks", 0) >= 4 and u["hidden"]["enemy_stacks"] - u["hidden"]["own_stacks"] >= 3]
        th["H1_turbo_floor5_pct"] = round(100 * len(st5) / len(UB), 1); th["H1_turbo_floor4_pct"] = round(100 * len(st4) / len(UB), 1)
    th["examples_heavy"] = [f"{round(mins(u))}m enemy obs {u['hidden']['enemy_obs']} (rate {u['hidden']['enemy_obs']/mins(u)*10:.1f}/10m), own {u['hidden']['own_obs']}, destroyed ours {u['hidden']['enemy_obs_killed_our']}" for u in random.sample(heavy, min(4, len(heavy)))]
    th["examples_smoke"] = [f"{round(mins(u))}m enemy smokes {u['hidden']['enemy_smokes']} ({u['hidden']['enemy_smokes']/mins(u)*10:.1f}/10m) own {u['hidden']['own_smokes']}" for u in random.sample(smoke, min(4, len(smoke)))]
    # support lane flips: magnitude of support LOST/RECOVERED vs cores
    R = [r for r in rows if r["bucket"] == b and r["lane"].get("lane_status") == "ok" and r["lane"].get("nwdiff_late") is not None]
    th["support_counterpart_same_lane_2v2_pct"] = round(100 * sum(1 for r in R if r["role"] == "support" and r["lane"].get("laneset_sizes") == (2, 2)) / max(1, sum(1 for r in R if r["role"] == "support")), 1)
    # feeding exclusion effect on L7 (deaths diff>=3) rate
    L = [r for r in R]
    l7 = lambda rs: round(100 * sum(1 for r in rs if abs(r["lane"]["deaths_late"] - r["lane"]["opp_deaths_late"]) >= 3) / max(1, len(rs)), 1)
    th["L7_rate_all"] = l7(L); th["L7_rate_no_feed"] = l7([r for r in L if r["match_id"] not in feed])
    out[b] = th
    print(b, json.dumps(th, indent=0))
json.dump(out, open("patch_v3_results.json", "w"), indent=1)

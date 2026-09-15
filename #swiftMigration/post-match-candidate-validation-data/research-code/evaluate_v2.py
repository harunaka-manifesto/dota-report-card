"""Candidate evaluation v2 (re-tuned after first empirical pass)."""
from __future__ import annotations
import json, csv, random, math, collections, statistics as st
from collections import defaultdict, Counter
from primitives import *
from metrics import build_rows, CHECK
random.seed(20260915)
core, rep, pb = load_matches()
rows, excluded = build_rows(core, rep, pb)
BUCKETS = ("STANDARD", "TURBO")
def rg(r): return "support" if r["role"] == "support" else "core"
def P(vals, q): return pct([v for v in vals if v is not None], q)
def units(rs):
    seen = {}
    for r in rs: seen.setdefault((r["match_id"], r["side_radiant"]), r)
    return list(seen.values())
U = units(rows)
def fmt(sec): return None if sec is None else ("-" if sec < 0 else "") + f"{abs(int(sec))//60}:{abs(int(sec))%60:02d}"
def sgn(x): return "+" if x >= 0 else ""
END_EXCL = 180
SPIKE_ITEMS = ["item_black_king_bar", "item_blink", "item_radiance", "item_hand_of_midas", "item_manta", "item_desolator", "item_bfury", "item_maelstrom", "item_ultimate_scepter", "item_orchid"]
RATE_ITEMS = ["item_black_king_bar", "item_blink", "item_glimmer_cape", "item_force_staff", "item_lotus_orb", "item_manta", "item_satanic", "item_pipe",
              "item_crimson_guard", "item_guardian_greaves", "item_solar_crest", "item_shivas_guard", "item_blade_mail", "item_harpoon", "item_sheepstick", "item_abyssal_blade"]

# ---------- shared derived per unit: mid/late turn window and sustained flips ----------
TURN = {}
for u in U:
    b = u["bucket"]; C = CHECK[b]; m = core[u["match_id"]]; side = u["side_radiant"]; lc = lead_curve(m, side); W = C["swing_w"]
    best = None
    for t in range(C["lane_end"], len(lc) - W):
        d = lc[t + W] - lc[t]; tot = team_nw(m, True, t + W) + team_nw(m, False, t + W)
        v = abs(d) / tot if tot else 0
        if best is None or v > best[0]: best = (v, t, lc[t], lc[t + W], d)
    S = [s for s in structures(m) if s["kind"] in ("tower", "barracks", "ancient")]
    deaths = all_deaths(m)
    info = {"lc": lc, "window": best, "S": S}
    if best:
        v, t, s0, e0, d = best
        against = d < 0
        loser = side if against else (not side)
        info["w_structs"] = sum(1 for s in S if t * 60 <= s["time"] <= (t + W) * 60 and s["owner_radiant"] == loser)
        info["w_death_margin"] = sum(1 for x in deaths if t * 60 <= x["time"] <= (t + W) * 60 and x["victim_radiant"] == loser) - sum(1 for x in deaths if t * 60 <= x["time"] <= (t + W) * 60 and x["victim_radiant"] != loser)
    runs = u["turn"].get("sustained_runs") or []
    flips = []
    for a, c in zip(runs, runs[1:]):
        if a[0] != c[0] and c[1] >= C["lane_end"]:
            pa = max(abs(x) for x in lc[a[1]:a[2] + 1]); pc = max(abs(x) for x in lc[c[1]:c[2] + 1])
            flips.append((min(pa, pc), a, c, pa, pc))
    info["flips"] = flips
    TURN[(u["match_id"], side)] = info

TH = {}
for b in BUCKETS:
    R = [r for r in rows if r["bucket"] == b]; UB = [u for u in U if u["bucket"] == b]; t = {}
    for g in ("core", "support"):
        L = [r["lane"] for r in R if rg(r) == g and r["lane"].get("lane_status") == "ok"]
        ae = [abs(x["nwdiff_early"]) for x in L if x.get("nwdiff_early") is not None]; al = [abs(x["nwdiff_late"]) for x in L if x.get("nwdiff_late") is not None]
        t[g] = {"e50": P(ae, .5), "e25": P(ae, .25), "l25": P(al, .25), "l50": P(al, .5), "l75": P(al, .75), "l90": P(al, .9), "l95": P(al, .95),
                "cs50": P([abs(x["csdiff_late"]) for x in L if x.get("csdiff_late") is not None], .5),
                "laneset90": P([abs(x["laneset_nwdiff_late"]) for x in L if x.get("laneset_nwdiff_late") is not None], .9)}
    t["lvl6_90"] = {role: P([abs(r["lane"]["lvl6_diff"]) for r in R if r["role"] == role and r["lane"].get("lvl6_diff") is not None], .9) for role in ("carry", "mid", "offlane")}
    t["opp"] = {}
    for pos in (1, 2, 3, 4, 5):
        k = "opp_cs_late" if pos <= 3 else "opp_nw_late"
        v = [r["lane"][k] for r in R if r["lane"].get("lane_status") == "ok" and r["lane"].get("opp_pos") == pos]
        t["opp"][pos] = (k, P(v, .9), P(v, .1), P(v, .95))
    wins = [TURN[(u["match_id"], u["side_radiant"])]["window"] for u in UB if TURN[(u["match_id"], u["side_radiant"])]["window"]]
    t["turn75"] = P([w[0] for w in wins], .75); t["turn90"] = P([w[0] for w in wins], .9); t["turn95"] = P([w[0] for w in wins], .95)
    t["flip_x"] = 2000 if b == "STANDARD" else 3000
    fl = [f[0] for u in UB for f in TURN[(u["match_id"], u["side_radiant"])]["flips"]]
    t["flip75"] = P(fl, .75); t["flip50"] = P(fl, .5)
    deficits_w = [-u["turn"]["lead_min"] for u in UB if u["turn"].get("lead_min") is not None and u["turn"]["win"]]
    t["comeback75"] = P(deficits_w, .75); t["comeback90"] = P(deficits_w, .9); t["comeback95"] = P(deficits_w, .95)
    econ = CHECK[b]["econ"]
    t["stall_lead"] = P([TURN[(u["match_id"], u["side_radiant"])]["lc"][econ] for u in UB if len(TURN[(u["match_id"], u["side_radiant"])]["lc"]) > econ and TURN[(u["match_id"], u["side_radiant"])]["lc"][econ] > 0], .75)
    H = [u["hidden"] for u in UB]
    t["stacks75"] = P([h.get("enemy_stacks") for h in H], .75); t["stacks90"] = P([h.get("enemy_stacks") for h in H], .9); t["stacks95"] = P([h.get("enemy_stacks") for h in H], .95)
    t["stackdiff90"] = P([h["enemy_stacks"] - h["own_stacks"] for h in H if "enemy_stacks" in h], .9)
    t["obs90"] = P([h["enemy_obs"] for h in H], .9); t["obs95"] = P([h["enemy_obs"] for h in H], .95); t["obs10"] = P([h["enemy_obs"] for h in H], .1)
    t["obs_killed90"] = P([h["enemy_obs_killed_our"] for h in H], .9); t["obs_share75"] = P([h["our_obs_destroyed_share"] for h in H if h["own_obs"] >= 8], .75)
    t["smokes75"] = P([h["enemy_smokes"] for h in H], .75); t["smokes90"] = P([h["enemy_smokes"] for h in H], .9); t["smokes95"] = P([h["enemy_smokes"] for h in H], .95)
    t["fast10"] = P([h["enemy_fastest_goal"][0] for h in H if h.get("enemy_fastest_goal")], .1); t["fast5"] = P([h["enemy_fastest_goal"][0] for h in H if h.get("enemy_fastest_goal")], .05)
    t["topshare90"] = P([h.get("enemy_top_share") for h in H], .9); t["topshare95"] = P([h.get("enemy_top_share") for h in H], .95)
    t["jungle90"] = P([h.get("enemy_top_core_jungle_share") for h in H], .9); t["jungle95"] = P([h.get("enemy_top_core_jungle_share") for h in H], .95)
    t["enemy_item"] = {}
    for it in SPIKE_ITEMS:
        vals = [u["items"]["enemy_key_first"][it][0] for u in UB if it in u["items"]["enemy_key_first"] and u["items"]["enemy_key_first"][it][2] in (1, 2, 3)]
        if len(vals) >= 30: t["enemy_item"][it] = (P(vals, .1), P(vals, .05), len(vals))
    races = [abs(r["lane"]["same_item_race"][1] - r["lane"]["same_item_race"][2]) for r in R if r["lane"].get("same_item_race")]
    t["race75"] = P(races, .75); t["race90"] = P(races, .9)
    t["hold_min"] = 10 if b == "STANDARD" else 6
    t["rate"] = {}
    for it in RATE_ITEMS:
        rates = [x["uses"] / x["remaining_min"] * 10 for r in R for x in r["items"].get("active_items", []) if x["item"] == it and x["final_main"] and x["remaining_min"] >= 15]
        if len(rates) >= 30: t["rate"][it] = (P(rates, .1), P(rates, .95), len(rates))
    clusters = []
    for u in UB:
        big = u["items"]["enemy_big_items"]; first = None
        for tt, h, n in big:
            win = [x for x in big if tt <= x[0] <= tt + 240]
            if len({x[1] for x in win}) >= 2 and len(win) >= 3: first = tt; break
        clusters.append(first)
    t["cluster10"] = P([c for c in clusters if c is not None], .1)
    TH[b] = t

CANDS = {}
def reg(cid, family, name, question, unit, playback=False, history=None, roles="all", redundancy=None, why=""):
    CANDS[cid] = dict(candidate_id=cid, family=family, name=name, question_answered=question, unit=unit, playback_required=playback, history_scope=history, role_scope=roles, redundancy_group=redundancy, why_player_cares=why)
F = {}

# ================= Family 1: Lane Story =================
reg("L1_LANE_LEAD_PATH", "lane", "Lane net-worth path vs counterpart", "How did my lane go against the player I actually laned with?", "viewpoint", redundancy="lane_path",
    why="Separates 'I had a bad lane' from impressions; names the opponent and shows early vs lane-end state.")
def L1(r):
    L = r["lane"]; b = r["bucket"]; T = TH[b][rg(r)]
    if L.get("lane_status") != "ok" or L.get("nwdiff_early") is None or L.get("nwdiff_late") is None: return None
    e, l = L["nwdiff_early"], L["nwdiff_late"]; C = CHECK[b]
    if e >= T["e50"] and l <= -T["l50"]: shape = "LOST_LEAD"
    elif e <= -T["e50"] and l >= T["l50"]: shape = "RECOVERED"
    elif l >= T["l90"]: shape = "DOMINATED" if e >= T["e50"] else "PULLED_AWAY"
    elif l <= -T["l90"]: shape = "CRUSHED" if e <= -T["e50"] else "FELL_BEHIND"
    elif abs(e) <= T["e25"] and abs(l) <= T["l25"]: shape = "DEAD_EVEN"
    elif abs(l) >= T["l50"]: shape = "MODERATE_AHEAD" if l > 0 else "MODERATE_BEHIND"
    else: shape = "SMALL_GAP"
    tuned = shape in ("LOST_LEAD", "RECOVERED", "DOMINATED", "PULLED_AWAY", "CRUSHED", "FELL_BEHIND")
    strong = shape in ("LOST_LEAD", "RECOVERED") or abs(l) >= T["l95"]
    return dict(eligible=True, raw=shape not in ("SMALL_GAP",), tuned=tuned, strong=strong, shape=shape, mag=abs(l),
                text=f"[{shape}] {sgn(e)}{e} @{C['early']}:00 → {sgn(l)}{l} @{C['late']}:00 vs {L['opp_hero']} (P{L['opp_pos']}); CS {L['cs_late']}-{L['opp_cs_late']}, deaths {L['deaths_late']}-{L['opp_deaths_late']}")
F["L1_LANE_LEAD_PATH"] = L1

reg("L2_LANE_SUSTAINED_FLIP", "lane", "Sustained lane lead flip minute", "When exactly did my lane turn?", "viewpoint", redundancy="lane_path", why="Pinpoints the minute a lane changed hands.")
def L2(r):
    L = r["lane"]; b = r["bucket"]; T = TH[b][rg(r)]
    if L.get("lane_status") != "ok" or len(L.get("nwdiff_path") or []) < CHECK[b]["late"]: return None
    path = L["nwdiff_path"]; thr = T["e50"]
    state = [1 if v >= thr else (-1 if v <= -thr else 0) for v in path]
    runs = []; cur = 0; start = 0
    for i, s in enumerate(state + [None]):
        if s != cur:
            if cur != 0 and i - start >= 3: runs.append((cur, start + 1, i))
            cur, start = s, i
    flips = [(a, c) for a, c in zip(runs, runs[1:]) if a[0] != c[0]]
    if not flips: return dict(eligible=True, raw=False, tuned=False, strong=False, shape=None, mag=0, text="")
    a, c = flips[0]; shape = "FLIP_TO_BEHIND" if a[0] > 0 else "FLIP_TO_AHEAD"
    peak = max(path[a[1]-1:a[2]], key=abs); trough = max(path[c[1]-1:c[2]], key=abs)
    return dict(eligible=True, raw=True, tuned=abs(trough) >= T["l50"], strong=abs(trough) >= T["l75"] and abs(peak) >= T["l50"], shape=shape, mag=abs(trough - peak),
                text=f"[{shape}] {sgn(peak)}{peak} (min {a[1]}–{a[2]}) → {sgn(trough)}{trough} from min {c[1]} vs {L['opp_hero']}")
F["L2_LANE_SUSTAINED_FLIP"] = L2

reg("L3_CS_NW_SPLIT", "lane", "CS vs net-worth disagreement", "Was my lane net worth from farm or from kills/deaths?", "viewpoint", roles="core", redundancy="lane_path",
    why="Reframes a lane: behind in last hits but ahead in gold (or the reverse).")
def L3(r):
    L = r["lane"]; b = r["bucket"]
    if rg(r) != "core" or L.get("lane_status") != "ok" or L.get("csdiff_late") is None: return None
    T = TH[b]["core"]; c, n = L["csdiff_late"], L["nwdiff_late"]
    split = (c > 0) != (n > 0) and c != 0 and n != 0
    kg = L["kill_gold_late"] - L["opp_kill_gold_late"]
    shape = ("CS_BEHIND_GOLD_AHEAD" if c < 0 else "CS_AHEAD_GOLD_BEHIND") if split else None
    return dict(eligible=True, raw=split and abs(c) >= 5, tuned=split and abs(c) >= T["cs50"] and abs(n) >= T["l25"], strong=split and abs(c) >= T["cs50"] and abs(n) >= T["l50"], shape=shape, mag=abs(c),
                text=f"[{shape}] CS {sgn(c)}{c}, NW {sgn(n)}{n} @{CHECK[b]['late']}:00 vs {L['opp_hero']} | kill+assist gold {L['kill_gold_late']} vs {L['opp_kill_gold_late']}, deaths {L['deaths_late']} vs {L['opp_deaths_late']}")
F["L3_CS_NW_SPLIT"] = L3

reg("L4_LEVEL6_RACE", "lane", "Level-6 race vs counterpart", "Who reached level 6 first, and by how much?", "viewpoint", roles="core", redundancy="lane_xp", why="Level 6 is a felt power moment; the gap is rarely known.")
def L4(r):
    L = r["lane"]; b = r["bucket"]
    if rg(r) != "core" or L.get("lane_status") != "ok" or L.get("lvl6_diff") is None: return None
    thr = TH[b]["lvl6_90"][r["role"]]; d = L["lvl6_diff"]; shape = "OPP_FIRST" if d > 0 else "USER_FIRST"
    return dict(eligible=True, raw=abs(d) >= thr / 2, tuned=abs(d) >= thr, strong=abs(d) >= thr * 1.3, shape=shape, mag=abs(d),
                text=f"[{shape}] L6 you {fmt(L['lvl6'])} vs {L['opp_hero']} {fmt(L['opp_lvl6'])} (Δ{abs(d)}s; role p90 {thr}s)")
F["L4_LEVEL6_RACE"] = L4

reg("L5_COUNTERPART_EXTREME_START", "lane", "Unusually strong/weak lane counterpart", "Was the player I laned against unusually strong or weak?", "viewpoint", history="bucket+role", redundancy="lane_opp",
    why="Contextualises a bad lane: the opponent had an exceptional start.")
def L5(r):
    L = r["lane"]; b = r["bucket"]
    if L.get("lane_status") != "ok": return None
    k, hi, lo, hi95 = TH[b]["opp"][L["opp_pos"]]; v = L[k]
    shape = "STRONG" if v >= hi else ("WEAK" if v <= lo else None)
    return dict(eligible=True, raw=shape is not None, tuned=shape == "STRONG", strong=v >= hi95, shape=shape, mag=v, hist_val=v,
                text=f"[{shape}] {L['opp_hero']} (P{L['opp_pos']}) {k}={v} @{CHECK[b]['late']}:00 (bucket p90 for P{L['opp_pos']}: {hi})")
F["L5_COUNTERPART_EXTREME_START"] = L5

reg("L6_OWN_LANE_VS_USUAL", "lane", "Lane result vs your usual", "Was this lane unusually good or bad for me in this role?", "viewpoint", history="bucket+role", redundancy="lane_path",
    why="Personal: 'your worst lane in 30 Mid games'.")
def L6(r):
    L = r["lane"]
    if L.get("lane_status") != "ok" or L.get("nwdiff_late") is None: return None
    return dict(eligible=True, raw=False, tuned=False, strong=False, shape=None, mag=L["nwdiff_late"], hist_val=L["nwdiff_late"], text=f"lane NW diff {L['nwdiff_late']} vs {L['opp_hero']}")
F["L6_OWN_LANE_VS_USUAL"] = L6

reg("L7_LANE_DEATH_TRADE", "lane", "Lopsided lane deaths", "Were there many more deaths on one side of my lane?", "viewpoint", redundancy="lane_path", why="Explains a lane gap in felt terms.")
def L7(r):
    L = r["lane"]
    if L.get("lane_status") != "ok": return None
    a, o = L["deaths_late"], L["opp_deaths_late"]; d = a - o
    shape = "USER_DIED_MORE" if d > 0 else ("OPP_DIED_MORE" if d < 0 else None)
    return dict(eligible=True, raw=abs(d) >= 2, tuned=abs(d) >= 3, strong=abs(d) >= 4, shape=shape, mag=abs(d), text=f"[{shape}] deaths before {CHECK[r['bucket']]['late']}:00 you {a} vs {L['opp_hero']} {o}")
F["L7_LANE_DEATH_TRADE"] = L7

reg("L8_SUPPORT_LANE_PAIR", "lane", "Support lane pair net worth", "How did my whole 2v2 lane do?", "viewpoint", roles="support", redundancy="lane_path", why="Supports' own NW is a poor lane indicator; the pair's is better.")
def L8(r):
    L = r["lane"]; b = r["bucket"]
    if rg(r) != "support" or L.get("laneset_nwdiff_late") is None or L.get("laneset_sizes") != (2, 2): return None
    v = L["laneset_nwdiff_late"]; T = TH[b]["support"]
    return dict(eligible=True, raw=abs(v) >= T["laneset90"] * 0.6, tuned=abs(v) >= T["laneset90"], strong=abs(v) >= T["laneset90"] * 1.3, shape="PAIR_AHEAD" if v > 0 else "PAIR_BEHIND", mag=abs(v),
                text=f"[PAIR] your lane pair {sgn(v)}{v} NW @{CHECK[b]['late']}:00 vs their pair")
F["L8_SUPPORT_LANE_PAIR"] = L8

# ================= Family 2: Match Turning Point =================
reg("T1_TURN_WINDOW", "turning", "Largest relative swing after laning", "When did the game change most?", "team", redundancy="turn",
    why="Gives the match a single 'this is when it changed' moment, with what fell in it.")
def T1(r):
    b = r["bucket"]; info = TURN[(r["match_id"], r["side_radiant"])]; w = info["window"]
    if not w: return None
    v, t, s, e, d = w; X = TH[b]["flip_x"]; W = CHECK[b]["swing_w"]
    if d < 0: shape = "FLIPPED_AGAINST" if s >= X and e <= -X else ("LEAD_EVAPORATED" if s >= X else ("DEFICIT_DEEPENED" if s <= 0 else "SWUNG_AGAINST"))
    else: shape = "FLIPPED_FOR" if s <= -X and e >= X else ("DEFICIT_ERASED" if s <= -X else ("LEAD_EXTENDED" if s >= 0 else "SWUNG_FOR"))
    return dict(eligible=True, raw=v >= TH[b]["turn75"], tuned=v >= TH[b]["turn90"], strong=v >= TH[b]["turn95"], shape=shape, mag=v,
                text=f"[{shape}] {t}:00–{t+W}:00 lead {sgn(s)}{s} → {sgn(e)}{e} (Δ{abs(d)}, {v:.0%} of all NW) | structures fell (losing side) {info['w_structs']}, death margin {info['w_death_margin']}",
                extra=dict(t0=t, against=d < 0, structs=info["w_structs"], dm=info["w_death_margin"]))
F["T1_TURN_WINDOW"] = T1

reg("T2_LEAD_FLIP", "turning", "Sustained team-lead flip after laning", "Did the game change hands, and how big were the leads on each side?", "team", redundancy="turn",
    why="'You led by 9k, then trailed by 11k' is a memorable story.")
def T2(r):
    b = r["bucket"]; info = TURN[(r["match_id"], r["side_radiant"])]
    if len(info["lc"]) < CHECK[b]["lane_end"] + 6: return None
    if not info["flips"]: return dict(eligible=True, raw=False, tuned=False, strong=False, shape=None, mag=0, text="")
    f = max(info["flips"]); mn, a, c, pa, pc = f
    shape = "GAME_FLIPPED_AGAINST" if a[0] > 0 else "GAME_FLIPPED_FOR"
    return dict(eligible=True, raw=True, tuned=mn >= TH[b]["flip75"], strong=mn >= TH[b]["flip75"] * 1.3, shape=shape, mag=mn,
                text=f"[{shape}] peak {'+' if a[0] > 0 else '-'}{pa} ({a[1]}:00–{a[2]}:00) → {'+' if c[0] > 0 else '-'}{pc} ({c[1]}:00–{c[2]}:00); flips in match {len(info['flips'])}")
F["T2_LEAD_FLIP"] = T2

reg("T3_COMEBACK_OR_LOST_LEAD", "turning", "Won from far behind / lost from far ahead", "Was this a comeback or a lost lead?", "team", redundancy="turn_outcome",
    why="Outcome-anchored; player remembers the result but not the size.")
def T3(r):
    tu = r["turn"]; b = r["bucket"]
    if tu.get("lead_min") is None: return None
    if tu["win"]: mag, shape = -tu["lead_min"], "COMEBACK_WIN"
    else: mag, shape = tu["lead_max"], "LOST_FROM_AHEAD"
    return dict(eligible=True, raw=mag >= TH[b]["comeback75"], tuned=mag >= TH[b]["comeback90"], strong=mag >= TH[b]["comeback95"], shape=shape, mag=mag,
                text=f"[{shape}] {'trailed' if shape == 'COMEBACK_WIN' else 'led'} by {mag} at worst/best")
F["T3_COMEBACK_OR_LOST_LEAD"] = T3

reg("T4_STALLED_ADVANTAGE", "turning", "Big lead with few structures taken", "Were we ahead for a long time without taking buildings?", "team", redundancy="turn_conversion",
    why="Names a match pattern players feel but can't quantify.")
def T4(r):
    b = r["bucket"]; info = TURN[(r["match_id"], r["side_radiant"])]; lc = info["lc"]; thr = TH[b]["stall_lead"]; K = 10 if b == "STANDARD" else 6
    if len(lc) < CHECK[b]["econ"] + 2: return None
    best = None; t = 0
    while t < len(lc):
        if lc[t] >= thr:
            u = t
            while u + 1 < len(lc) and lc[u + 1] >= thr: u += 1
            n = sum(1 for s in info["S"] if t * 60 <= s["time"] <= u * 60 and s["owner_radiant"] != r["side_radiant"])
            if u - t + 1 >= K and n <= 2 and (best is None or u - t > best[1] - best[0]): best = (t, u, n, max(lc[t:u + 1]))
            t = u + 1
        else: t += 1
    if not best: return dict(eligible=True, raw=False, tuned=False, strong=False, shape=None, mag=0, text="")
    dur = best[1] - best[0] + 1
    return dict(eligible=True, raw=True, tuned=dur >= K, strong=dur >= int(K * 1.5), shape="STALLED_ADVANTAGE", mag=dur,
                text=f"[STALLED_ADVANTAGE] lead ≥{thr} for {dur} min ({best[0]}:00–{best[1]}:00, peak +{best[3]}); enemy structures taken {best[2]}")
F["T4_STALLED_ADVANTAGE"] = T4

reg("T5_CLASH_TO_STRUCTURES", "turning", "Lopsided clash followed by structures", "What fell right after a lopsided clash?", "team", redundancy="turn_conversion",
    why="Concrete sequence; 'after the 27:30 clash, 4 buildings fell in 80s'.")
def T5(r):
    m = core[r["match_id"]]; end = m["durationSeconds"]
    conv = [c for c in r["turn"].get("clash_conversions", []) if c[0]["end"] < end - END_EXCL]
    if not conv: return dict(eligible=True, raw=False, tuned=False, strong=False, shape=None, mag=0, text="")
    c, loser_is_us, n, dt = max(conv, key=lambda x: (x[2], -x[3]))
    shape = "WE_LOST_STRUCTURES" if loser_is_us else "WE_TOOK_STRUCTURES"
    return dict(eligible=True, raw=n >= 3, tuned=n >= 4, strong=n >= 6, shape=shape, mag=n,
                text=f"[{shape}] clash {fmt(c['start'])}–{fmt(c['end'])} deaths R{c['radiant_deaths']}/D{c['dire_deaths']} → {n} structures within {dt}s")
F["T5_CLASH_TO_STRUCTURES"] = T5

reg("T6_STRUCTURES_WHILE_DEAD", "turning", "Structures lost during one of your deaths", "What did my team lose while I was dead?", "viewpoint", redundancy="turn_dead",
    why="Personal; players rarely realise how much fell during one death timer.")
def T6(r):
    m = core[r["match_id"]]; end = m["durationSeconds"]; p = next(x for x in m["players"] if x["playerSlot"] == r["slot"])
    S = [s for s in structures(m) if s["time"] < end - END_EXCL and s["kind"] in ("tower", "barracks") and s["owner_radiant"] == p["isRadiant"]]
    best = (0, None)
    for d in p["stats"]["deathEvents"] or []:
        n = sum(1 for s in S if d["time"] <= s["time"] <= d["time"] + (d.get("timeDead") or 0))
        if n > best[0]: best = (n, d)
    n, d = best
    return dict(eligible=True, raw=n >= 3, tuned=n >= 4, strong=n >= 6, shape="STRUCTURES_WHILE_DEAD", mag=n,
                text=f"[STRUCTURES_WHILE_DEAD] died {fmt(d['time'])}, dead {d.get('timeDead')}s, {n} towers/barracks lost meanwhile" if d else "")
F["T6_STRUCTURES_WHILE_DEAD"] = T6

reg("T7_OBJECTIVE_HEAVY_TURN", "turning", "Turn window with many structures", "Did the turning window also include buildings falling?", "team", redundancy="turn", why="Combination: swing + buildings.")
def T7(r):
    x = T1(r)
    if not x: return None
    s = x["extra"]["structs"]
    return dict(eligible=True, raw=x["raw"] and s >= 2, tuned=x["tuned"] and s >= 3, strong=x["strong"] and s >= 4, shape=x["shape"], mag=s, text=x["text"])
F["T7_OBJECTIVE_HEAVY_TURN"] = T7

reg("T8_DEATH_HEAVY_TURN", "turning", "Turn window with lopsided deaths", "Was the turn a string of deaths on one side?", "team", redundancy="turn", why="Combination: swing + death margin.")
def T8(r):
    x = T1(r)
    if not x: return None
    dm = x["extra"]["dm"]
    return dict(eligible=True, raw=x["raw"] and dm >= 4, tuned=x["tuned"] and dm >= 6, strong=x["strong"] and dm >= 8, shape=x["shape"], mag=dm, text=x["text"])
F["T8_DEATH_HEAVY_TURN"] = T8

reg("T9_TORMENTOR_IN_TURN", "turning", "Tormentor fell inside the turn window", "Did a Tormentor fall during the turn?", "team", redundancy="turn", why="Adds a boss event to the turn.")
def T9(r):
    x = T1(r); h = r["hidden"]
    if not x or "tormentor_chat_times" not in h: return None
    W = CHECK[r["bucket"]]["swing_w"]; t0 = x["extra"]["t0"]
    inside = [t for t, _ in h["tormentor_chat_times"] if t0 * 60 <= t <= (t0 + W) * 60]
    return dict(eligible=True, raw=bool(inside), tuned=bool(inside) and x["tuned"], strong=bool(inside) and x["strong"], shape=x["shape"], mag=len(inside), text=x["text"] + f" | tormentor at {[fmt(t) for t in inside]}")
F["T9_TORMENTOR_IN_TURN"] = T9

# ================= Family 3: Hidden Enemy Activity =================
reg("H1_ENEMY_STACKING", "hidden", "Enemy stacking edge", "Did the enemy do stacking work we didn't?", "team", history="bucket", redundancy="hidden_jungle", why="Invisible jungle investment.")
def H1(r):
    h = r["hidden"]; b = r["bucket"]; T = TH[b]
    if "enemy_stacks" not in h: return None
    e, o = h["enemy_stacks"], h["own_stacks"]
    return dict(eligible=True, raw=e >= T["stacks75"], tuned=e >= T["stacks90"] and e - o >= T["stackdiff90"], strong=e >= T["stacks95"] and e - o >= T["stackdiff90"], shape="ENEMY_STACKED_MORE", mag=e, hist_val=e,
                text=f"[ENEMY_STACKED_MORE] enemy {e} vs your team {o} camps stacked by {CHECK[b]['stack']}:00")
F["H1_ENEMY_STACKING"] = H1

reg("H2_ENEMY_VISION", "hidden", "Enemy ward volume / our wards cleared", "Was the enemy's warding or dewarding unusual?", "team", history="bucket", redundancy="hidden_vision", why="Vision war volume is invisible in-game.")
def H2(r):
    h = r["hidden"]; b = r["bucket"]; T = TH[b]
    heavy = h["enemy_obs"] >= T["obs90"]; cleared = h["own_obs"] >= 8 and h["enemy_obs_killed_our"] >= T["obs_killed90"] and (h["our_obs_destroyed_share"] or 0) >= T["obs_share75"]
    shape = "+".join(s for s, f in (("HEAVY_ENEMY_VISION", heavy), ("OUR_VISION_CLEARED", cleared)) if f) or None
    return dict(eligible=True, raw=h["enemy_obs"] >= T["obs90"] or h["enemy_obs_killed_our"] >= T["obs_killed90"], tuned=heavy or cleared, strong=(heavy and cleared) or h["enemy_obs"] >= T["obs95"], shape=shape, mag=h["enemy_obs"], hist_val=h["enemy_obs"],
                text=f"[{shape}] enemy placed {h['enemy_obs']} observers (yours {h['own_obs']}); destroyed {h['enemy_obs_killed_our']} of yours ({(h['our_obs_destroyed_share'] or 0):.0%}); you destroyed {h['own_obs_killed_their']}")
F["H2_ENEMY_VISION"] = H2

reg("H3_ENEMY_SMOKES", "hidden", "Enemy smoke volume", "How often did the enemy move invisibly under Smoke?", "team", history="bucket", redundancy="hidden_smoke", why="Smoke is invisible by design.")
def H3(r):
    h = r["hidden"]; b = r["bucket"]; T = TH[b]
    return dict(eligible=True, raw=h["enemy_smokes"] >= T["smokes75"], tuned=h["enemy_smokes"] >= T["smokes90"] and h["enemy_smokes"] >= h["own_smokes"] + 2, strong=h["enemy_smokes"] >= T["smokes95"] and h["enemy_smokes"] >= h["own_smokes"] + 3,
                shape="ENEMY_SMOKE_HEAVY", mag=h["enemy_smokes"], hist_val=h["enemy_smokes"], text=f"[ENEMY_SMOKE_HEAVY] enemy used Smoke {h['enemy_smokes']} times (your team {h['own_smokes']})")
F["H3_ENEMY_SMOKES"] = H3

reg("H4_SMOKE_TO_KILLS", "hidden", "Enemy smokes followed by kills", "Did their smokes turn into kills?", "team", playback=True, redundancy="hidden_smoke", why="Connects invisible movement to felt deaths (sequence only).")
def H4(r):
    h = r["hidden"]
    if "pb_enemy_smokes" not in h: return None
    s, k = h["pb_enemy_smokes"], h["pb_enemy_smoke_kills"]
    return dict(eligible=True, raw=k >= 2, tuned=k >= 3 and s and k / s >= 0.5, strong=k >= 5, shape="SMOKES_INTO_KILLS", mag=k, text=f"[SMOKES_INTO_KILLS] {k} of {s} enemy smokes were followed by an enemy kill within 60s")
F["H4_SMOKE_TO_KILLS"] = H4

reg("H5_ENEMY_BOSS_CONTROL", "hidden", "Enemy took every Roshan/Tormentor", "Did the enemy take bosses we never contested?", "team", history="bucket", redundancy="hidden_objectives", why="Roshan kills are often unseen by the other team.")
def H5(r):
    h = r["hidden"]; er, orr, et, ot = h["enemy_roshan"], h["own_roshan"], h["enemy_tormentor"], h["own_tormentor"]
    shape = []
    if er >= 1 and orr == 0: shape.append(f"ROSHAN_{er}_0")
    if et >= 1 and ot == 0: shape.append(f"TORMENTOR_{et}_0")
    return dict(eligible=True, raw=bool(shape), tuned=(er >= 2 and orr == 0) or (er + et >= 3 and orr + ot == 0), strong=er >= 3 and orr == 0, shape="+".join(shape) or None, mag=er + et,
                text=f"[BOSSES] enemy Roshan {er} vs yours {orr}; Tormentor {et} vs {ot}")
F["H5_ENEMY_BOSS_CONTROL"] = H5

reg("H6_ENEMY_FAST_CORE", "hidden", "Enemy hero reached NW goal unusually early", "Did an enemy get rich unusually fast?", "team", history="bucket", redundancy="hidden_economy", why="Explains why the enemy suddenly felt unkillable.")
def H6(r):
    h = r["hidden"]; b = r["bucket"]; T = TH[b]
    if not h.get("enemy_fastest_goal"): return None
    mnt, hero, pos = h["enemy_fastest_goal"]; own = h.get("own_fastest_goal")
    return dict(eligible=True, raw=mnt <= T["fast10"], tuned=mnt <= T["fast10"] and (own is None or own - mnt >= 3), strong=mnt <= T["fast5"] and (own is None or own - mnt >= 4), shape="ENEMY_EARLY_RICH", mag=-mnt, hist_val=mnt,
                text=f"[ENEMY_EARLY_RICH] {hero} (P{pos}) reached {CHECK[b]['nw_goal']} NW at {mnt}:00; your team's first at {own}:00")
F["H6_ENEMY_FAST_CORE"] = H6

reg("H7_ENEMY_ECONOMY_CONCENTRATION", "hidden", "Enemy economy concentrated in one hero", "Was the enemy's gold funnelled into one hero?", "team", redundancy="hidden_economy", why="Resource allocation is not visible in-game.")
def H7(r):
    h = r["hidden"]; b = r["bucket"]; T = TH[b]
    if h.get("enemy_top_share") is None: return None
    s = h["enemy_top_share"]
    return dict(eligible=True, raw=s >= T["topshare90"], tuned=s >= T["topshare90"] and s - (h.get("own_top_share") or 0) >= 0.05, strong=s >= T["topshare95"] and s - (h.get("own_top_share") or 0) >= 0.07, shape="ENEMY_ONE_HERO_ECONOMY", mag=s,
                text=f"[ENEMY_ONE_HERO_ECONOMY] {h['enemy_top_hero']} held {s:.0%} of enemy NW at {CHECK[b]['econ']}:00 (your top hero {h.get('own_top_share', 0):.0%})")
F["H7_ENEMY_ECONOMY_CONCENTRATION"] = H7

reg("H8_ENEMY_JUNGLE_RELIANCE", "hidden", "Enemy richest core farmed mostly jungle", "Did their richest core farm away from lanes?", "team", redundancy="hidden_jungle", why="Where enemy gold came from is invisible.")
def H8(r):
    h = r["hidden"]; b = r["bucket"]; T = TH[b]
    if h.get("enemy_top_core_jungle_share") is None: return None
    s = h["enemy_top_core_jungle_share"]
    return dict(eligible=True, raw=s >= T["jungle90"], tuned=s >= T["jungle90"] and s >= 0.45, strong=s >= T["jungle95"] and s >= 0.5, shape="ENEMY_CORE_JUNGLE", mag=s,
                text=f"[ENEMY_CORE_JUNGLE] {h['enemy_top_core_hero']}: {s:.0%} of creep gold from neutral/ancient camps (partial farm report)")
F["H8_ENEMY_JUNGLE_RELIANCE"] = H8

reg("H9_SHORT_LIVED_OBSERVERS", "hidden", "Our observers destroyed within 90s", "Were our wards found almost immediately?", "team", playback=True, redundancy="hidden_vision", why="Ward-level fate is invisible to the placer.")
def H9(r):
    h = r["hidden"]
    if "pb_own_obs" not in h or not h["pb_own_obs"]: return None
    k, n = h["pb_own_obs_killed_90s"], h["pb_own_obs"]
    return dict(eligible=True, raw=k >= 3, tuned=k >= 4 and k / n >= 0.25, strong=k >= 6, shape="OBSERVERS_KILLED_FAST", mag=k, text=f"[OBSERVERS_KILLED_FAST] {k} of {n} observers destroyed within 90s")
F["H9_SHORT_LIVED_OBSERVERS"] = H9

reg("H10_HIDDEN_ACTIVITY_STACK", "hidden", "Several hidden enemy activities in one match", "Was the enemy doing several unseen things?", "team", redundancy="hidden_combo", why="Combination headline.")
def H10(r):
    parts = [n for n, f in (("stacks", H1), ("vision", H2), ("smokes", H3), ("bosses", H5), ("jungle", H8)) if (f(r) or {}).get("tuned")]
    return dict(eligible=True, raw=len(parts) >= 2, tuned=len(parts) >= 2, strong=len(parts) >= 3, shape="+".join(parts) or None, mag=len(parts), text=f"[HIDDEN_STACK] {parts}")
F["H10_HIDDEN_ACTIVITY_STACK"] = H10

# ================= Family 4: Item Execution & Power Spikes =================
reg("I1_UNUSED_ACTIVE_ITEM", "items", "Active item held to the end, never activated", "Did I use the tools I bought?", "viewpoint", redundancy="item_use", why="Direct execution fact.")
def I1(r):
    it = r["items"]; b = r["bucket"]; H = TH[b]["hold_min"]; items = it.get("active_items", [])
    if not items: return None
    raw = [x for x in items if x["uses"] == 0]
    tuned = [x for x in raw if x["final_main"] and x["remaining_min"] >= H]
    strong = [x for x in tuned if x["item"] != "item_mjollnir"]
    top = max(tuned, key=lambda x: x["remaining_min"]) if tuned else None
    return dict(eligible=True, raw=bool(raw), tuned=bool(tuned), strong=bool(strong), shape="NEVER_ACTIVATED" if tuned else None, mag=top["remaining_min"] if top else 0,
                text=f"[NEVER_ACTIVATED] {top['item']} bought {fmt(top['bought'])}, in inventory at end ({top['remaining_min']} min), uses 0" if top else "")
F["I1_UNUSED_ACTIVE_ITEM"] = I1

reg("I2_ACTIVATION_RATE_EXTREME", "items", "Unusually low/high activation rate of a held active item", "Did I use my key active item unusually rarely or often?", "viewpoint", redundancy="item_use",
    why="'Held BKB 27 min, activated once' vs 'activated Glimmer 14 times'.")
def I2(r):
    b = r["bucket"]; RT = TH[b]["rate"]; items = [x for x in r["items"].get("active_items", []) if x["item"] in RT and x["final_main"] and x["remaining_min"] >= 15]
    if not items: return None
    hits = []
    for x in items:
        lo, hi, n = RT[x["item"]]; rate = x["uses"] / x["remaining_min"] * 10
        if rate <= lo and x["uses"] <= 2: hits.append(("LOW", x, rate))
        elif rate >= hi: hits.append(("HIGH", x, rate))
    if not hits: return dict(eligible=True, raw=False, tuned=False, strong=False, shape=None, mag=0, text="")
    shape, x, rate = max(hits, key=lambda h: x["remaining_min"])
    return dict(eligible=True, raw=True, tuned=True, strong=shape == "LOW" and x["uses"] <= 1 and x["remaining_min"] >= 20, shape=shape, mag=rate,
                text=f"[{shape}_USE] {x['item']} held {x['remaining_min']} min (bought {fmt(x['bought'])}), activated {x['uses']}x ({rate:.2f}/10min)")
F["I2_ACTIVATION_RATE_EXTREME"] = I2

reg("I3_ENEMY_EARLY_SPIKE_ITEM", "items", "Enemy core key item unusually early", "Did an enemy core hit a key item unusually early?", "team", history="bucket", redundancy="item_enemy_spike",
    why="Early BKB/Blink/Radiance changes fights; players feel it but don't know it was unusual.")
def I3(r):
    b = r["bucket"]; T = TH[b]["enemy_item"]; ek = r["items"]["enemy_key_first"]
    cands = [(t - T[n][1], n, t, h, pos) for n, (t, h, pos) in ek.items() if n in T and pos in (1, 2, 3)]
    if not cands: return None
    raw = [c for c in cands if c[2] <= T[c[1]][0]]; tuned = [c for c in cands if c[2] <= T[c[1]][1]]
    best = min(tuned or raw) if (tuned or raw) else None
    return dict(eligible=True, raw=bool(raw), tuned=bool(tuned), strong=bool([c for c in tuned if c[1] in ("item_black_king_bar", "item_blink", "item_radiance", "item_bfury", "item_manta")]), shape=("EARLY_" + best[1].replace("item_", "").upper()) if best else None,
                mag=-best[0] if best else 0, hist_val=min((c[2] for c in cands if c[1] == "item_black_king_bar"), default=None),
                text=f"[ENEMY_EARLY_ITEM] {best[3]} (P{best[4]}) {best[1].replace('item_','')} at {fmt(best[2])} (core p5 {fmt(T[best[1]][1])}, p10 {fmt(T[best[1]][0])})" if best else "")
F["I3_ENEMY_EARLY_SPIKE_ITEM"] = I3

reg("I4_LANE_ITEM_RACE", "items", "Same key item race vs lane counterpart", "Did my lane opponent get the same key item much earlier/later?", "viewpoint", roles="core", redundancy="item_race", why="Directly comparable timing between two lane rivals.")
def I4(r):
    L = r["lane"]; b = r["bucket"]
    if rg(r) != "core" or L.get("lane_status") != "ok" or not L.get("same_item_race"): return None
    name, a, o = L["same_item_race"]; gap = a - o
    return dict(eligible=True, raw=abs(gap) >= TH[b]["race75"], tuned=abs(gap) >= TH[b]["race90"], strong=abs(gap) >= TH[b]["race90"] * 1.4, shape="OPP_FIRST" if gap > 0 else "USER_FIRST", mag=abs(gap),
                text=f"[ITEM_RACE] {name.replace('item_','')}: you {fmt(a)} vs {L['opp_hero']} {fmt(o)} (Δ{fmt(abs(gap))})")
F["I4_LANE_ITEM_RACE"] = I4

reg("I5_ENEMY_SPIKE_CLUSTER", "items", "Enemy cores' big items clustered early", "Did several enemy cores complete big items at nearly the same time, unusually early?", "team", redundancy="item_enemy_spike", why="A coordinated power spike window.")
def I5(r):
    b = r["bucket"]; big = r["items"]["enemy_big_items"]; first = None
    for t, h, n in big:
        win = [x for x in big if t <= x[0] <= t + 240]
        if len({x[1] for x in win}) >= 2 and len(win) >= 3: first = (t, win); break
    if not first: return dict(eligible=True, raw=False, tuned=False, strong=False, shape=None, mag=0, text="")
    t, win = first
    return dict(eligible=True, raw=True, tuned=t <= TH[b]["cluster10"], strong=t <= TH[b]["cluster10"] and len({x[1] for x in win}) >= 3, shape="EARLY_SPIKE_CLUSTER", mag=-t,
                text=f"[SPIKE_CLUSTER] from {fmt(t)}: " + "; ".join(f"{h} {n.replace('item_','')} {fmt(tt)}" for tt, h, n in win))
F["I5_ENEMY_SPIKE_CLUSTER"] = I5

reg("I6_SPIKE_BEFORE_TURN", "items", "Enemy big item shortly before adverse turn window", "Did an enemy spike land right before the game turned against us?", "team", redundancy="item_enemy_spike", why="Temporal combination: item + turn.")
def I6(r):
    x = T1(r)
    if not x or not x["extra"]["against"] or not x["tuned"]: return None
    t0 = x["extra"]["t0"] * 60; big = r["items"]["enemy_big_items"]
    hit = [bb for bb in big if t0 - 180 <= bb[0] <= t0 + 60]; ctrl = [bb for bb in big if t0 - 780 <= bb[0] <= t0 - 540]
    return dict(eligible=True, raw=bool(hit), tuned=bool(hit), strong=len(hit) >= 2, shape="SPIKE_THEN_TURN", mag=len(hit), text=x["text"] + f" | enemy items {[(h, n.replace('item_',''), fmt(t)) for t, h, n in hit]}", extra=dict(control=bool(ctrl)))
F["I6_SPIKE_BEFORE_TURN"] = I6

reg("I7_FIRST_ACTIVATION_DELAY", "items", "Long delay before first activation", "How long did I hold a key active item before first using it?", "viewpoint", playback=True, redundancy="item_use", why="Timing of first use is invisible.")
def I7(r):
    d = r["items"].get("pb_first_use")
    if not d: return None
    delays = [(fu - t, n, t, fu) for n, t, fu in d if fu is not None]
    if not delays: return None
    best = max(delays)
    return dict(eligible=True, raw=best[0] >= 180, tuned=best[0] >= 420, strong=best[0] >= 600, shape="DELAYED_FIRST_USE", mag=best[0], text=f"[DELAYED_FIRST_USE] {best[1]} bought {fmt(best[2])}, first used {fmt(best[3])}")
F["I7_FIRST_ACTIVATION_DELAY"] = I7

reg("I8_OWN_ITEM_TIMING_VS_HISTORY", "items", "Own key item timing vs your usual", "Was my key item unusually early or late for me?", "viewpoint", history="bucket+item", redundancy="item_own_timing", why="Personal timing context.")
def I8(r):
    kf = {n: t for n, t in r["items"]["key_first"].items() if n in SPIKE_ITEMS}
    if not kf: return None
    return dict(eligible=True, raw=False, tuned=False, strong=False, shape=None, mag=0, hist_items=kf, text="")
F["I8_OWN_ITEM_TIMING_VS_HISTORY"] = I8

# ---------------- evaluation ----------------
EV = defaultdict(list)
for r in rows:
    for cid, f in F.items():
        try: res = f(r)
        except Exception as e: res = {"error": repr(e)}
        EV[cid].append((r, res))
errs = {cid: sum(1 for _, x in v if x and "error" in x) for cid, v in EV.items()}
print("errors", {k: v for k, v in errs.items() if v})
if any(errs.values()):
    for cid, v in EV.items():
        for _, x in v:
            if x and "error" in x: print(cid, x["error"]); break

def rate(cid, subset):
    items = subset
    if CANDS[cid]["unit"] == "team":
        seen = {}
        for r, x in items: seen.setdefault((r["match_id"], r["side_radiant"]), (r, x))
        items = list(seen.values())
    el = [(r, x) for r, x in items if x and "error" not in x and x.get("eligible")]
    return len(items), len(el), sum(1 for _, x in el if x["raw"]), sum(1 for _, x in el if x["tuned"]), sum(1 for _, x in el if x["tuned"] and x.get("strong"))
RES = []
for cid in F:
    allv = EV[cid]; n, el, raw, tuned, strong = rate(cid, allv); meta = CANDS[cid]
    rec = dict(candidate_id=cid, family=meta["family"], unit=meta["unit"], units=n, eligible=el, eligible_pct=round(100 * el / n, 1) if n else 0,
               raw_fire_pct=round(100 * raw / el, 1) if el else 0, tuned_fire_pct=round(100 * tuned / el, 1) if el else 0, strong_pct=round(100 * strong / el, 1) if el else 0,
               tuned_fires=tuned, playback_required=meta["playback_required"], history_scope=meta["history_scope"])
    for b in BUCKETS:
        n2, el2, r2, t2, s2 = rate(cid, [(r, x) for r, x in allv if r["bucket"] == b])
        rec[f"{b.lower()}_eligible_pct"] = round(100 * el2 / n2, 1) if n2 else 0; rec[f"{b.lower()}_tuned_pct"] = round(100 * t2 / el2, 1) if el2 else 0
    if meta["unit"] == "viewpoint":
        for role in ("carry", "mid", "offlane", "support"):
            n2, el2, r2, t2, s2 = rate(cid, [(r, x) for r, x in allv if r["role"] == role])
            rec[f"{role}_tuned_pct"] = round(100 * t2 / el2, 1) if el2 else None
    for w, lab in ((True, "win"), (False, "loss")):
        n2, el2, r2, t2, s2 = rate(cid, [(r, x) for r, x in allv if r["win"] == w])
        rec[f"{lab}_tuned_pct"] = round(100 * t2 / el2, 1) if el2 else None
    mags = [x["mag"] for _, x in allv if x and x.get("tuned") and isinstance(x.get("mag"), (int, float))]
    for q in (.5, .75, .9, .95): rec[f"mag_p{int(q*100)}"] = round(P(mags, q), 3) if mags else None
    rec["mag_max"] = round(max(mags), 3) if mags else None
    shapes = Counter(x["shape"] for _, x in (allv if meta["unit"] == "viewpoint" else list({(r["match_id"], r["side_radiant"]): (r, x) for r, x in allv}.values())) if x and x.get("tuned"))
    rec["tuned_shapes"] = dict(shapes.most_common(10))
    RES.append(rec)

# ---------------- history ----------------
T = json.load(open("tracked_histories.json"))
hs = json.load(open("../deep-research-2026-09-14/history_self.json"))["self"]
T["acct8"] = [{"id": h["id"], "slot": h["slot"], "start": h["start"]} for h in hs]
idx = {(r["match_id"], r["slot"]): r for r in rows}
HIST = {a: [idx[(m["id"], m["slot"])] for m in sorted(ms, key=lambda x: x["start"]) if (m["id"], m["slot"]) in idx] for a, ms in T.items()}
HSPEC = {"L5_COUNTERPART_EXTREME_START": ("bucket+role", "max"), "L6_OWN_LANE_VS_USUAL": ("bucket+role", "both"), "H1_ENEMY_STACKING": ("bucket", "max"),
         "H2_ENEMY_VISION": ("bucket", "max"), "H3_ENEMY_SMOKES": ("bucket", "max"), "H6_ENEMY_FAST_CORE": ("bucket", "min"), "I3_ENEMY_EARLY_SPIKE_ITEM": ("bucket", "min")}
HSTATS = {}; HEX = defaultdict(list)
for cid, (scope, direction) in HSPEC.items():
    tot = a10 = a20 = fire = fire_pop = st_tot = st_a10 = 0
    for acct, seq in HIST.items():
        prior = defaultdict(list)
        for i, r in enumerate(seq):
            x = F[cid](r)
            if not x or not x.get("eligible") or x.get("hist_val") is None: continue
            key = (r["bucket"], r["role"]) if scope == "bucket+role" else (r["bucket"],)
            pr = prior[key]; tot += 1; steady = i >= 0.6 * len(seq); st_tot += steady
            if len(pr) >= 10:
                a10 += 1; st_a10 += steady; v = x["hist_val"]
                hi, lo = v > max(pr), v < min(pr)
                ok = hi if direction == "max" else (lo if direction == "min" else (hi or lo))
                if ok:
                    fire += 1; fire_pop += bool(x.get("tuned")) or direction == "both"
                    if len(HEX[cid]) < 8: HEX[cid].append(f"{acct} {r['bucket'][:3]} {r['role']} {r['hero']}: {v} vs prior n={len(pr)} median {st.median(pr)} range [{min(pr)},{max(pr)}] :: {x['text']}")
            if len(pr) >= 20: a20 += 1
            pr.append(x["hist_val"])
    HSTATS[cid] = dict(scope=scope, evaluated=tot, avail10_pct=round(100 * a10 / tot, 1) if tot else 0, avail20_pct=round(100 * a20 / tot, 1) if tot else 0,
                       steady_avail10_pct=round(100 * st_a10 / st_tot, 1) if st_tot else 0, record_fire_pct_of_available=round(100 * fire / a10, 1) if a10 else 0,
                       record_and_population_pct_of_available=round(100 * fire_pop / a10, 1) if a10 else 0)
# I8 own item timing vs history (per item, bucket)
tot = a5 = a10 = fire_e = fire_l = 0
for acct, seq in HIST.items():
    prior = defaultdict(list)
    for r in seq:
        for n, t in r["items"]["key_first"].items():
            if n not in SPIKE_ITEMS: continue
            key = (r["bucket"], n); pr = prior[key]; tot += 1
            if len(pr) >= 5: a5 += 1
            if len(pr) >= 10:
                a10 += 1
                if t < min(pr): fire_e += 1; HEX["I8_OWN_ITEM_TIMING_VS_HISTORY"].append(f"{acct} {r['bucket'][:3]} {r['hero']} {n}: {fmt(t)} vs prior n={len(pr)} best {fmt(min(pr))} median {fmt(st.median(pr))}") if len(HEX["I8_OWN_ITEM_TIMING_VS_HISTORY"]) < 8 else None
                if t > max(pr): fire_l += 1
            pr.append(t)
HSTATS["I8_OWN_ITEM_TIMING_VS_HISTORY"] = dict(scope="bucket+item", evaluated_item_purchases=tot, avail5_pct=round(100 * a5 / tot, 1) if tot else 0, avail10_pct=round(100 * a10 / tot, 1) if tot else 0,
                                               record_early_pct_of_available=round(100 * fire_e / a10, 1) if a10 else 0, record_late_pct_of_available=round(100 * fire_l / a10, 1) if a10 else 0)
for rec in RES:
    if rec["candidate_id"] in HSTATS: rec.update({f"hist_{k}": v for k, v in HSTATS[rec["candidate_id"]].items() if k != "scope"})

# ---------------- co-fire (viewpoint, tuned) ----------------
fires = defaultdict(set)
for cid, v in EV.items():
    for r, x in v:
        if x and x.get("tuned"): fires[cid].add((r["match_id"], r["slot"]))
N = len(rows); cids = list(F); CO = {}
for i, a in enumerate(cids):
    for bcid in cids[i + 1:]:
        A, B = fires[a], fires[bcid]
        if not A or not B: continue
        inter = len(A & B); lift = (inter / N) / ((len(A) / N) * (len(B) / N))
        CO[(a, bcid)] = dict(both=inter, p_both_given_smaller=round(inter / min(len(A), len(B)), 2), lift=round(lift, 2))
fam = {c: CANDS[c]["family"] for c in cids}
per_vp = defaultdict(Counter)
for cid, s in fires.items():
    for key in s: per_vp[key][fam[cid]] += 1
FAMDIST = {f: dict(sorted(Counter(min(per_vp[(r["match_id"], r["slot"])][f], 4) for r in rows).items())) for f in ("lane", "turning", "hidden", "items")}
FAMANY = dict(sorted(Counter(sum(1 for f in ("lane", "turning", "hidden", "items") if per_vp[(r["match_id"], r["slot"])][f]) for r in rows).items()))

# ---------------- examples ----------------
EX = {}
def lab(r, x): return f"{r['bucket'][:3]} {r['role']} {r['hero']} ({'W' if r['win'] else 'L'}, {r['duration']//60}m) :: {x['text']}"
for cid, v in EV.items():
    if CANDS[cid]["unit"] == "team": v = list({(r["match_id"], r["side_radiant"]): (r, x) for r, x in v}.values())
    tuned = [(r, x) for r, x in v if x and x.get("tuned")]; raw_only = [(r, x) for r, x in v if x and x.get("raw") and not x.get("tuned")]
    e = {}
    if tuned:
        srt = sorted(tuned, key=lambda rx: rx[1]["mag"] if isinstance(rx[1]["mag"], (int, float)) else 0)
        e["extreme"] = [lab(r, x) for r, x in srt[-4:]]; e["borderline"] = [lab(r, x) for r, x in srt[:4]]
        e["random_standard"] = [lab(r, x) for r, x in random.sample([t for t in tuned if t[0]["bucket"] == "STANDARD"], min(4, sum(1 for t in tuned if t[0]["bucket"] == "STANDARD")))]
        e["random_turbo"] = [lab(r, x) for r, x in random.sample([t for t in tuned if t[0]["bucket"] == "TURBO"], min(4, sum(1 for t in tuned if t[0]["bucket"] == "TURBO")))]
    if raw_only: e["raw_not_tuned"] = [lab(r, x) for r, x in random.sample(raw_only, min(3, len(raw_only)))]
    EX[cid] = e
# special diagnostics
diag = {}
seen = {}
for r, x in EV["I6_SPIKE_BEFORE_TURN"]:
    if x and x.get("eligible"): seen[(r["match_id"], r["side_radiant"])] = x
diag["I6_hit_vs_control"] = (sum(1 for x in seen.values() if x["tuned"]), sum(1 for x in seen.values() if x["extra"]["control"]), len(seen))
seen = {}
for r, x in EV["T5_CLASH_TO_STRUCTURES"]:
    if x: seen[(r["match_id"], r["side_radiant"])] = x
diag["T1_shapes_all_windows"] = {}
for b in BUCKETS:
    s = {}
    for r, x in EV["T1_TURN_WINDOW"]:
        if x and r["bucket"] == b: s[(r["match_id"], r["side_radiant"])] = x
    diag["T1_shapes_all_windows"][b] = dict(Counter(x["shape"] for x in s.values() if x["tuned"]).most_common())
    diag.setdefault("T1_tuned_start_minute_p50", {})[b] = P([x["extra"]["t0"] for x in s.values() if x["tuned"]], .5)
for b in BUCKETS:
    for g in ("core", "support"):
        c = Counter(x["shape"] for r, x in EV["L1_LANE_LEAD_PATH"] if x and r["bucket"] == b and rg(r) == g); tot = sum(c.values())
        diag.setdefault("L1_shapes", {})[f"{b}_{g}"] = {k: round(100 * v / tot, 1) for k, v in c.most_common()}

json.dump({"thresholds": TH, "candidates": CANDS, "history": HSTATS, "primitives_version": PRIMITIVES_VERSION, "clash_version": CLASH_VERSION, "checkpoints": CHECK,
           "curated_items": {"key": KEY_ITEMS, "active": ACTIVE_ITEMS, "spike": SPIKE_ITEMS, "rate": RATE_ITEMS},
           "corpus": {"eligible_matches": len({r['match_id'] for r in rows}), "viewpoints": len(rows), "team_units": len(U), "excluded": dict(Counter(excluded.values())),
                      "standard_matches": len({r['match_id'] for r in rows if r['bucket']=='STANDARD'}), "turbo_matches": len({r['match_id'] for r in rows if r['bucket']=='TURBO'}),
                      "with_reports": len({r['match_id'] for r in rows if r['has_reports']}), "with_playback": len({r['match_id'] for r in rows if r['has_playback']}),
                      "history_sequences": {a: len(v) for a, v in HIST.items()}}},
          open("candidate-definitions.json", "w"), indent=1, default=str)
with open("candidate-results.csv", "w", newline="") as fh:
    keys = sorted({k for rec in RES for k in rec}, key=lambda k: (k != "candidate_id", k != "family", k))
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader()
    for rec in RES: w.writerow({k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in rec.items()})
json.dump({"examples": EX, "history_examples": HEX, "diagnostics": diag, "family_distribution": FAMDIST, "families_with_any": FAMANY,
           "cofire": {f"{a}|{b}": v for (a, b), v in CO.items()}}, open("candidate-examples.json", "w"), indent=1, default=str)
print("corpus", json.load(open("candidate-definitions.json"))["corpus"])
for rec in RES:
    print(f"{rec['candidate_id']:34s} elig {rec['eligible_pct']:5.1f} raw {rec['raw_fire_pct']:5.1f} tuned {rec['tuned_fire_pct']:5.1f} strong {rec['strong_pct']:5.1f} | std {rec['standard_tuned_pct']:5.1f} tur {rec['turbo_tuned_pct']:5.1f} | roles {[rec.get(k) for k in ('carry_tuned_pct','mid_tuned_pct','offlane_tuned_pct','support_tuned_pct')]} | W/L {rec['win_tuned_pct']}/{rec['loss_tuned_pct']} | n {rec['tuned_fires']}")
print("HIST", json.dumps(HSTATS, indent=0))
print("DIAG", json.dumps(diag, indent=0))
print("FAMDIST", FAMDIST, "ANY", FAMANY)
top = sorted(((k, v) for k, v in CO.items() if v["both"] >= 25), key=lambda kv: -kv[1]["p_both_given_smaller"])[:40]
print("TOP COFIRE"); [print(" ", k, v) for k, v in top]

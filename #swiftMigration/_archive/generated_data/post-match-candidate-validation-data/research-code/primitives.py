"""Deterministic primitives for post-match candidate validation (research, v1).

All inputs are STRATZ payload fields validated in post-match-intelligence-deep-research-v2.md.
Index conventions (verified): networthPerMinute[t] = net worth at t:00 (index 0 = start);
lastHitsPerMinute / experiencePerMinute / campStack index i covers minute i+1, so the value
"by t:00" is sum(arr[:t]) for per-minute deltas and arr[t-1] for cumulative campStack.
"""
from __future__ import annotations
import glob, json, math, statistics as st
from collections import defaultdict

RAW = "../deep-research-2026-09-14/raw"
PRIMITIVES_VERSION = "pmi-primitives-1.0.0"
CONST = json.load(open(f"{RAW}/constants.json"))["data"]["constants"]
ITEMS = {i["id"]: i["name"] for i in CONST["items"]}
ITEM_COST = {i["id"]: ((i.get("stat") or {}).get("cost") or 0) for i in CONST["items"]}
ITEM_ID = {v: k for k, v in ITEMS.items()}
NPCS = {n["id"]: n["name"] for n in CONST["npcs"]}
HEROES = {h["id"]: h["displayName"] for h in CONST["heroes"]}
ROSHAN_NPC, TORMENTOR_NPC = 133, 861
BAD_LEAVER = {"ABANDONED", "AFK", "DISCONNECTED_TOO_LONG", "NEVER_CONNECTED", "NEVER_CONNECTED_TOO_LONG", "FAILED_TO_READY_UP", "DECLINED_READY_UP"}

# Curated item sets (explicit domain lists; names verified against constants at load).
KEY_ITEMS = ["item_black_king_bar", "item_blink", "item_ultimate_scepter", "item_manta", "item_desolator", "item_maelstrom", "item_mjollnir",
             "item_bfury", "item_radiance", "item_hand_of_midas", "item_force_staff", "item_glimmer_cape", "item_sphere", "item_cyclone",
             "item_orchid", "item_bloodthorn", "item_diffusal_blade", "item_echo_sabre", "item_armlet", "item_invis_sword", "item_silver_edge",
             "item_butterfly", "item_greater_crit", "item_satanic", "item_skadi", "item_heart", "item_assault", "item_refresher", "item_sheepstick",
             "item_shivas_guard", "item_pipe", "item_crimson_guard", "item_lotus_orb", "item_aether_lens", "item_mekansm", "item_guardian_greaves",
             "item_vladmir", "item_sange_and_yasha", "item_kaya_and_sange", "item_yasha_and_kaya", "item_harpoon", "item_nullifier",
             "item_abyssal_blade", "item_octarine_core", "item_mask_of_madness", "item_basher", "item_monkey_king_bar", "item_hurricane_pike",
             "item_wind_waker", "item_gungir", "item_disperser", "item_heavens_halberd", "item_rod_of_atos", "item_blade_mail", "item_spirit_vessel",
             "item_solar_crest", "item_ethereal_blade", "item_bloodstone", "item_aeon_disk", "item_overwhelming_blink", "item_swift_blink", "item_arcane_blink"]
ACTIVE_ITEMS = ["item_black_king_bar", "item_blink", "item_overwhelming_blink", "item_swift_blink", "item_arcane_blink", "item_force_staff",
                "item_hurricane_pike", "item_glimmer_cape", "item_lotus_orb", "item_satanic", "item_manta", "item_cyclone", "item_wind_waker",
                "item_shivas_guard", "item_pipe", "item_crimson_guard", "item_solar_crest", "item_mekansm", "item_guardian_greaves",
                "item_invis_sword", "item_silver_edge", "item_nullifier", "item_orchid", "item_bloodthorn", "item_sheepstick", "item_abyssal_blade",
                "item_refresher", "item_mjollnir", "item_diffusal_blade", "item_harpoon", "item_heavens_halberd", "item_rod_of_atos", "item_gungir",
                "item_disperser", "item_ethereal_blade", "item_blade_mail", "item_spirit_vessel", "item_hand_of_midas", "item_mask_of_madness",
                "item_bloodstone", "item_ghost", "item_medallion_of_courage", "item_veil_of_discord", "item_holy_locket", "item_boots_of_bearing",
                "item_meteor_hammer", "item_helm_of_the_overlord", "item_helm_of_the_dominator"]
KEY_ITEM_IDS = {ITEM_ID[n] for n in KEY_ITEMS if n in ITEM_ID}
ACTIVE_ITEM_IDS = {ITEM_ID[n] for n in ACTIVE_ITEMS if n in ITEM_ID}
MISSING_ITEM_NAMES = [n for n in set(KEY_ITEMS + ACTIVE_ITEMS) if n not in ITEM_ID]

MAIN_SLOTS = ("item0", "item1", "item2", "item3", "item4", "item5")

def load_matches():
    core, rep, pb = {}, {}, {}
    for pat in ("corpusA_*", "historyA_*", "pbstatsA_*", "cvA_*"):
        for f in sorted(glob.glob(f"{RAW}/{pat}.json")):
            for m in (json.load(open(f)).get("data") or {}).values():
                if m and m.get("players"): core[m["id"]] = m
    for pat in ("corpusB_*", "pbstatsB_*", "cvB_*"):
        for f in sorted(glob.glob(f"{RAW}/{pat}.json")):
            for m in (json.load(open(f)).get("data") or {}).values():
                if m: rep[m["id"]] = m
    for pat in ("playback_std_*", "playback_full_fresh_*", "pbwin_*", "cvP_*"):
        for f in sorted(glob.glob(f"{RAW}/{pat}.json")):
            m = ((json.load(open(f)).get("data") or {}).get("match")) or None
            if m and m.get("players"):
                prev = pb.get(m["id"])
                if not prev or len(json.dumps(m)) > len(json.dumps(prev)): pb[m["id"]] = m
    return core, rep, pb

def bucket(m):
    if m.get("gameMode") == "TURBO": return "TURBO"
    if m.get("gameMode") in ("ALL_PICK", "ALL_PICK_RANKED") and m.get("lobbyType") in ("RANKED", "UNRANKED"): return "STANDARD"
    return None

def eligible_match(m):
    """Returns (ok, reason). Fail closed on missing stats, abandons, bots, non-product modes, <10 min."""
    if bucket(m) is None: return False, "mode"
    if m.get("numHumanPlayers") != 10: return False, "humans"
    if (m.get("durationSeconds") or 0) < 600: return False, "short"
    ps = m["players"]
    if len(ps) != 10 or any(not (p.get("stats") or {}).get("networthPerMinute") for p in ps): return False, "no_stats"
    if any(p.get("leaverStatus") in BAD_LEAVER for p in ps): return False, "leaver"
    if sorted(p.get("position") or "" for p in ps) != sorted(["POSITION_1","POSITION_2","POSITION_3","POSITION_4","POSITION_5"] * 2): return False, "positions"
    return True, None

def pos_num(p): return int(p["position"][-1])
def role(p): return {1: "carry", 2: "mid", 3: "offlane", 4: "support", 5: "support"}[pos_num(p)]
def map_lane(p):
    return {"MID_LANE": "mid", "SAFE_LANE": "bot" if p["isRadiant"] else "top", "OFF_LANE": "top" if p["isRadiant"] else "bot"}.get(p.get("lane"))
COUNTER = {1: 3, 2: 2, 3: 1, 4: 5, 5: 4}

def counterpart(m, p):
    opp = [q for q in m["players"] if q["isRadiant"] != p["isRadiant"] and pos_num(q) == COUNTER[pos_num(p)]]
    if len(opp) != 1: return None, "no_unique_counterpart"
    q = opp[0]
    if map_lane(p) is None or map_lane(p) != map_lane(q): return None, "lane_mismatch"
    return q, None

def team(m, side): return [p for p in m["players"] if p["isRadiant"] == side]
def nw(p, t):
    a = p["stats"]["networthPerMinute"]; return a[t] if 0 <= t < len(a) and a[t] is not None else None
def cs(p, t):
    a = p["stats"]["lastHitsPerMinute"] or []; return sum(x or 0 for x in a[:t]) if len(a) >= t else None
def xp(p, t):
    a = p["stats"]["experiencePerMinute"] or []; return sum(x or 0 for x in a[:t]) if len(a) >= t else None
def level_time(p, level):
    a = p["stats"].get("level") or []; return a[level - 1] if len(a) >= level else None
def stacks_by(p, t):
    a = p["stats"].get("campStack") or []; return a[t - 1] if len(a) >= t else None
def team_nw(m, side, t):
    vals = [nw(p, t) for p in team(m, side)]; return None if any(v is None for v in vals) else sum(vals)
def lead_curve(m, side):
    out = []
    t = 0
    while True:
        a, b = team_nw(m, side, t), team_nw(m, not side, t)
        if a is None or b is None: break
        out.append(a - b); t += 1
    return out

def gold_from_kills_before(p, t_sec):
    s = p["stats"]
    return sum((k.get("gold") or 0) for k in s["killEvents"] or [] if k["time"] < t_sec) + sum((a.get("gold") or 0) for a in s["assistEvents"] or [] if a["time"] < t_sec)
def deaths_before(p, t_sec): return sum(1 for d in p["stats"]["deathEvents"] or [] if d["time"] < t_sec)

def structures(m):
    """towerDeaths classified; owner side = isRadiant (verified ownership semantics)."""
    out = []
    for t in m.get("towerDeaths") or []:
        if t.get("time") is None: continue
        name = NPCS.get(t["npcId"], "")
        kind = "tower" if "tower" in name else ("barracks" if "rax" in name else ("ancient" if "fort" in name else ("shrine" if "filler" in name else "other")))
        out.append({"time": t["time"], "owner_radiant": t["isRadiant"], "kind": kind, "tier": name.split("_")[3] if kind == "tower" else None})
    return sorted(out, key=lambda x: x["time"])

def all_deaths(m):
    out = []
    for p in m["players"]:
        for d in p["stats"]["deathEvents"] or []:
            out.append({"time": d["time"], "x": d.get("positionX"), "y": d.get("positionY"), "victim_radiant": p["isRadiant"], "victim": p["heroId"],
                        "attacker": d.get("attacker"), "assist": d.get("assist") or [], "timeDead": d.get("timeDead") or 0})
    return sorted(out, key=lambda d: d["time"])

CLASH_VERSION = "clash-heuristic-1.0.0 (chain<=20s, centroid<=30 units, >=3 deaths)"
def clashes(m, chain_s=20, radius=30, min_deaths=3):
    cl = []
    for d in all_deaths(m):
        if d["x"] is None: continue
        if cl:
            c = cl[-1]; cx = st.mean(x["x"] for x in c); cy = st.mean(x["y"] for x in c)
            if d["time"] - c[-1]["time"] <= chain_s and math.dist((d["x"], d["y"]), (cx, cy)) <= radius:
                c.append(d); continue
        cl.append([d])
    out = []
    for c in cl:
        if len(c) < min_deaths: continue
        rd = sum(1 for x in c if x["victim_radiant"]); dd = len(c) - rd
        out.append({"start": c[0]["time"], "end": c[-1]["time"], "deaths": len(c), "radiant_deaths": rd, "dire_deaths": dd})
    return out

def observers_placed(m, side): return sum(1 for p in team(m, side) for w in p["stats"]["wards"] or [] if w["type"] == 0)
def sentries_placed(m, side): return sum(1 for p in team(m, side) for w in p["stats"]["wards"] or [] if w["type"] == 1)
def observers_destroyed_by(m, side): return sum(1 for p in team(m, side) for w in p["stats"]["wardDestruction"] or [] if w.get("isWard"))
def item_uses(p, item_name):
    iid = ITEM_ID.get(item_name); return sum((u.get("count") or 0) for u in p["stats"]["itemUsed"] or [] if u["itemId"] == iid)
def farm_other_count(p, npc):
    return sum((o.get("count") or 0) for o in ((p["stats"].get("farmDistributionReport") or {}).get("other") or []) if o["id"] == npc)
def jungle_share(p):
    f = p["stats"].get("farmDistributionReport") or {}
    g = lambda k: sum((o.get("gold") or 0) for o in (f.get(k) or []))
    lane, neu, anc = g("creepLocation"), g("neutralLocation"), g("ancientLocation")
    tot = lane + neu + anc
    return (neu + anc) / tot if tot >= 1000 else None

def first_purchase(p, item_ids, after=-999):
    ev = [(e["time"], e["itemId"]) for e in p["stats"]["itemPurchases"] or [] if e["itemId"] in item_ids and e["time"] > after]
    return min(ev) if ev else None
def purchases(p): return sorted((e["time"], e["itemId"]) for e in p["stats"]["itemPurchases"] or [])

def held_minutes(rep_player, item_id):
    inv = ((rep_player or {}).get("stats") or {}).get("inventoryReport") or []
    return sum(1 for snap in inv if any(((snap.get(s) or {}).get("itemId")) == item_id for s in MAIN_SLOTS)) if inv else None

def pct(vals, q):
    v = sorted(x for x in vals if x is not None)
    if not v: return None
    return v[min(len(v) - 1, max(0, int(round(q * (len(v) - 1)))))]

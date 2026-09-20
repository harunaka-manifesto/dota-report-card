"""Build every locked V1 role metric for the tracked player, from the v7 Pass-2 canonical corpus."""
import json, glob, pickle, collections, os

SRC = "/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/corpora/stratz/v7-pass2-2026-09-04/canonical"
OUT = os.path.dirname(os.path.abspath(__file__))

def physical_lane(lane, rad):
    if lane == "MID_LANE": return "MID"
    if lane == "SAFE_LANE": return "BOT" if rad else "TOP"
    if lane == "OFF_LANE": return "TOP" if rad else "BOT"
    return None

ROLE = {'POSITION_1':'Carry','POSITION_2':'Mid','POSITION_3':'Offlane',
        'POSITION_4':'Support','POSITION_5':'Support'}
BUCKET = {'ALL_PICK_RANKED':'STANDARD','ALL_PICK':'STANDARD','TURBO':'TURBO'}

rows, seen, skip = [], set(), collections.Counter()

for f in sorted(glob.glob(f"{SRC}/*.json")):
    d = json.load(open(f))
    acct = d["account_pseudonym"]
    for r in d["rows"]:
        mid = r.get("match_id")
        if mid in seen: skip["dup"] += 1; continue
        seen.add(mid)
        bucket = BUCKET.get(r.get("game_mode_native"))
        if not bucket: skip["mode"] += 1; continue
        dur = r.get("duration_seconds") or 0
        if dur < 600: skip["short"] += 1; continue
        s = r.get("self") or {}
        if s.get("leaver_status_native") not in (None, "NONE"): skip["leaver"] += 1; continue
        aps = r.get("all_players") or []
        if len(aps) != 10: skip["not10"] += 1; continue
        pos = s.get("position_native"); lane_n = s.get("lane_native")
        if not pos or pos not in ROLE: skip["no_pos"] += 1; continue
        rad = bool(s.get("is_radiant"))
        t = s.get("trajectories") or {}
        ev = s.get("events") or {}
        lh = t.get("last_hits_per_minute") or []
        nw = t.get("networth_per_minute") or []
        lvl = t.get("level") or []
        cs = t.get("camp_stack") or []
        dmin = dur / 60.0

        team  = [p for p in aps if bool(p.get("is_radiant")) == rad]
        tk    = sum(p.get("kills") or 0 for p in team)
        thd   = sum(p.get("hero_damage") or 0 for p in team)
        ttd   = sum(p.get("tower_damage") or 0 for p in team)

        pl = physical_lane(lane_n, rad)
        allies = [p["hero_id"] for p in aps if bool(p.get("is_radiant")) == rad
                  and p.get("player_slot") != s.get("player_slot")
                  and physical_lane(p.get("lane"), bool(p.get("is_radiant"))) == pl] if pl else []
        opps   = [p["hero_id"] for p in aps if bool(p.get("is_radiant")) != rad
                  and physical_lane(p.get("lane"), bool(p.get("is_radiant"))) == pl] if pl else []

        deaths = ev.get("death_events") or []
        towers = r.get("tower_deaths") or []
        enemy_towers = [x for x in towers if bool(x.get("is_radiant")) != rad]   # is_radiant = tower owner
        kt = [e.get("time") for e in (ev.get("kill_events") or []) if e.get("time") is not None]
        at = [e.get("time") for e in (ev.get("assist_events") or []) if e.get("time") is not None]
        credit = sorted(kt + at)
        obj_num = sum(1 for x in enemy_towers
                      if any(0 <= (x.get("time") or 0) - c <= 60 for c in credit))
        wards = ev.get("wards") or []

        m = {}
        # --- Carry ---
        m['last_hits_at_10']  = sum(lh[:10]) if len(lh) >= 10 else None
        m['cs_10_to_20']      = sum(lh[10:20]) if len(lh) >= 20 else None
        m['net_worth_at_20']  = nw[20] if len(nw) >= 21 else None
        m['net_worth_at_10']  = nw[10] if len(nw) >= 11 else None
        # canonical death_events carry only {time}; timeDead is absent, so the SSOT's
        # dead-time metric is genuinely uncomputable here. Use death count as the closest proxy.
        m['deaths_total'] = len(deaths)
        m['death_rate_per10'] = len(deaths) / dmin * 10
        m['hero_damage_share']  = ((s.get("hero_damage") or 0) / thd) if thd > 0 else None
        m['tower_damage_share'] = ((s.get("tower_damage") or 0) / ttd) if ttd > 0 else None
        # --- Mid ---
        m['level_6_time'] = lvl[5] if len(lvl) >= 6 else None
        m['early_fight_presence'] = None   # needs ten-player kill events; probe corpus only
        # --- Offlane / Support shared ---
        m['fight_presence'] = (((s.get("kills") or 0) + (s.get("assists") or 0)) / tk) if tk > 0 else None
        m['objective_involvement'] = (obj_num / len(enemy_towers)) if enemy_towers else None
        # --- Support ---
        m['observer_wards_per10'] = (sum(1 for w in wards if w.get("type") == 0) / dmin * 10) if wards is not None else None
        m['sentry_wards_per10']   = (sum(1 for w in wards if w.get("type") == 1) / dmin * 10) if wards is not None else None
        m['dewards_per10'] = (len(ev.get("ward_destruction") or []) / dmin * 10)
        m['camps_stacked_at_20'] = cs[20] if len(cs) >= 21 else None
        m['healing_per10'] = ((s.get("hero_healing") or 0) / dmin * 10)
        # --- supporting context ---
        m['deaths_before_10'] = sum(1 for e in deaths if (e.get("time") or 0) < 600)

        rows.append(dict(match_id=mid, account=acct, bucket=bucket,
                         mode=r.get("game_mode_native"), patch=r.get("game_version_id"),
                         started=r.get("started_at"), dur=dur,
                         hero=s.get("hero_id"), pos=pos, role=ROLE[pos], lane=lane_n,
                         phys=pl, radiant=rad, win=bool(s.get("is_victory")),
                         allies=tuple(sorted(allies)), opps=tuple(sorted(opps)),
                         n_allies=len(allies), n_opps=len(opps),
                         shape=f"{len(allies)+1}v{len(opps)}",
                         **m))

print("rows:", len(rows), "skipped:", dict(skip))
cov = collections.Counter()
for r in rows:
    for k, v in r.items():
        if k in ('match_id','account','bucket','mode','patch','started','dur','hero','pos','role',
                 'lane','phys','radiant','win','allies','opps','n_allies','n_opps','shape'): continue
        if v is not None: cov[k] += 1
print("\nmetric coverage (of %d rows):" % len(rows))
for k, v in cov.most_common():
    print(f"  {k:<26} {v:6d}  {100*v/len(rows):5.1f}%")
pickle.dump(rows, open(f"{OUT}/metrics.pkl", "wb"))

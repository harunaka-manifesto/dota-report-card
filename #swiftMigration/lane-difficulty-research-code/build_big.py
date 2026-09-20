"""Build the large lane dataset from the v7 Pass-2 canonical corpus (278 accounts)."""
import json, glob, pickle, collections, os

SRC = "/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/corpora/stratz/v7-pass2-2026-09-04/canonical"
OUT = os.path.dirname(os.path.abspath(__file__))

def physical_lane(lane, is_radiant):
    if lane == "MID_LANE": return "MID"
    if lane == "SAFE_LANE": return "BOT" if is_radiant else "TOP"
    if lane == "OFF_LANE": return "TOP" if is_radiant else "BOT"
    return None

rows, seen = [], set()
skip = collections.Counter()

for f in sorted(glob.glob(f"{SRC}/*.json")):
    d = json.load(open(f))
    for r in d["rows"]:
        mid = r.get("match_id")
        if mid in seen: skip["dup"] += 1; continue
        seen.add(mid)
        s = r.get("self") or {}
        aps = r.get("all_players") or []
        if len(aps) != 10: skip["not10"] += 1; continue
        dur = r.get("duration_seconds") or 0
        if dur < 660: skip["short"] += 1; continue
        if s.get("leaver_status_native") not in (None, "NONE"): skip["leaver"] += 1; continue
        lane_n, pos_n = s.get("lane_native"), s.get("position_native")
        if not lane_n or not pos_n: skip["no_lane"] += 1; continue
        t = s.get("trajectories") or {}
        lh, nw, xp = t.get("last_hits_per_minute"), t.get("networth_per_minute"), t.get("experience_per_minute")
        if not (isinstance(lh, list) and len(lh) >= 10 and isinstance(nw, list) and len(nw) >= 11):
            skip["no_traj"] += 1; continue
        rad = bool(s.get("is_radiant"))
        pl = physical_lane(lane_n, rad)
        if pl is None: skip["odd_lane"] += 1; continue
        me_slot = s.get("player_slot")
        allies = [p["hero_id"] for p in aps
                  if bool(p.get("is_radiant")) == rad and p.get("player_slot") != me_slot
                  and physical_lane(p.get("lane"), bool(p.get("is_radiant"))) == pl]
        opps = [p["hero_id"] for p in aps
                if bool(p.get("is_radiant")) != rad
                and physical_lane(p.get("lane"), bool(p.get("is_radiant"))) == pl]
        deaths = (s.get("events") or {}).get("death_events") or []
        d10 = sum(1 for e in deaths if isinstance(e, dict) and (e.get("time") or 0) < 600)
        lvl = t.get("level") or []
        rows.append(dict(
            match_id=mid, patch=r.get("game_version_id"), mode=r.get("game_mode_native"),
            lobby=r.get("lobby_type_native"), dur=dur, started=r.get("started_at"),
            hero=s.get("hero_id"), pos=pos_n, lane=lane_n, phys=pl, radiant=rad,
            win=bool(s.get("is_victory")),
            cs10=sum(lh[:10]), cs8=sum(lh[:8]), cs12=(sum(lh[:12]) if len(lh) >= 12 else None),
            nw10=nw[10], nw8=nw[8], nw12=(nw[12] if len(nw) >= 13 else None),
            xp10=(sum(xp[:10]) if isinstance(xp, list) and len(xp) >= 10 else None),
            lvl6=(lvl[5] if len(lvl) >= 6 else None),
            deaths10=d10, denies10=sum((t.get("denies_per_minute") or [0]*10)[:10]),
            allies=tuple(sorted(allies)), opps=tuple(sorted(opps)),
            n_allies=len(allies), n_opps=len(opps),
            account=d["account_pseudonym"],
        ))

print("rows:", len(rows), "skipped:", dict(skip))
print("modes:", collections.Counter(r['mode'] for r in rows).most_common(6))
print("patches:", collections.Counter(r['patch'] for r in rows).most_common(6))
print("positions:", collections.Counter(r['pos'] for r in rows).most_common())
pickle.dump(rows, open(f"{OUT}/big.pkl", "wb"))

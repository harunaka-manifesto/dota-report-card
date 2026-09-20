"""Build a lane-context dataset from the cached STRATZ probe corpus."""
import json, glob, pickle, collections, os

ROOT = "/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/stratz-probe"
OUT = os.path.dirname(os.path.abspath(__file__))

def physical_lane(lane, is_radiant):
    """Map faction-relative lane to a shared physical lane id."""
    if lane == "MID_LANE":
        return "MID"
    if lane == "SAFE_LANE":
        return "BOT" if is_radiant else "TOP"
    if lane == "OFF_LANE":
        return "TOP" if is_radiant else "BOT"
    return None

rows = []
seen = set()
skipped = collections.Counter()

for f in sorted(glob.glob(f"{ROOT}/*/raw/*.json")):
    try:
        d = json.load(open(f))
    except Exception:
        continue
    for _, m in (d.get("data") or {}).items():
        if not isinstance(m, dict):
            continue
        mid = m.get("id")
        ps = m.get("players")
        if not mid or mid in seen or not isinstance(ps, list) or len(ps) != 10:
            continue
        if not isinstance(ps[0], dict) or "lane" not in ps[0] or "position" not in ps[0]:
            continue
        dur = m.get("durationSeconds")
        if not dur or dur < 660:
            skipped["short_or_no_duration"] += 1
            continue
        if any(p.get("lane") is None or p.get("position") is None for p in ps):
            skipped["null_lane_or_pos"] += 1
            continue
        if any(not isinstance(p.get("stats"), dict) for p in ps):
            skipped["no_stats"] += 1
            continue
        seen.add(mid)

        # index players by physical lane and faction
        by_lane = collections.defaultdict(lambda: {True: [], False: []})
        for p in ps:
            pl = physical_lane(p.get("lane"), bool(p.get("isRadiant")))
            if pl:
                by_lane[pl][bool(p.get("isRadiant"))].append(p)

        for p in ps:
            st = p["stats"]
            lh = st.get("lastHitsPerMinute")
            nw = st.get("networthPerMinute")
            if not isinstance(lh, list) or not isinstance(nw, list):
                continue
            if len(lh) < 10 or len(nw) < 11:
                continue
            rad = bool(p.get("isRadiant"))
            pl = physical_lane(p.get("lane"), rad)
            allies = [q["heroId"] for q in by_lane[pl][rad] if q is not p] if pl else []
            opps = [q["heroId"] for q in by_lane[pl][not rad]] if pl else []

            deaths = st.get("deathEvents") or []
            d10 = sum(1 for e in deaths if isinstance(e, dict) and (e.get("time") or 0) < 600)

            rows.append(dict(
                match_id=mid,
                patch=m.get("gameVersionId"),
                mode=m.get("gameMode"),
                lobby=m.get("lobbyType"),
                dur=dur,
                hero=p.get("heroId"),
                pos=p.get("position"),
                lane=p.get("lane"),
                phys=pl,
                radiant=rad,
                win=p.get("isVictory"),
                cs10=sum(lh[:10]),
                cs8=sum(lh[:8]),
                cs12=sum(lh[:12]) if len(lh) >= 12 else None,
                nw10=nw[10],
                nw8=nw[8],
                xp10=sum((st.get("experiencePerMinute") or [0] * 10)[:10]) or None,
                deaths10=d10,
                allies=tuple(sorted(allies)),
                opps=tuple(sorted(opps)),
                n_allies=len(allies),
                n_opps=len(opps),
            ))

print("matches:", len(seen), "player rows:", len(rows), "skipped:", dict(skipped))
pickle.dump(rows, open(f"{OUT}/rows.pkl", "wb"))

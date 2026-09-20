"""Fresh playback holdout (2026-09-16 evening; playback available again):
(1) vision stats-only ward-identity reconstruction vs playback truth; QUICK/SWEEP agreement,
(2) Smoke->Kills modified rule on fresh units.
Only matches not used by earlier vision/smoke work. Ids stay local."""
import os, sys, json, time, math, pickle, statistics as st
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); VI = os.path.join(HERE, "../vision-2026-09-16")
from sc import call
H = json.load(open("long_histories.json"))
N_TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 60
now = time.time()
cand = {}
for v in H.values():
    for m in v:
        if now - m["start"] < 20 * 86400 and m["humans"] == 10 and m["mode"] in ("ALL_PICK_RANKED", "ALL_PICK", "TURBO"):
            cand[m["id"]] = m
old_pb = set()
for f in os.listdir("../deep-research-2026-09-14/raw"):
    for p in ("playback_", "pbwin", "cvP_", "vis_pb", "pbstats"):
        if f.startswith(p): old_pb.add(f)
std = sorted([c for c in cand.values() if c["mode"] != "TURBO"], key=lambda c: -c["start"])
tur = sorted([c for c in cand.values() if c["mode"] == "TURBO"], key=lambda c: -c["start"])
pick = [c["id"] for c in std[:N_TARGET // 2]] + [c["id"] for c in tur[:N_TARGET // 2]]
STATS = """id durationSeconds gameMode lobbyType numHumanPlayers didRadiantWin startDateTime
 towerDeaths { time npcId isRadiant }
 players { playerSlot isRadiant heroId position lane leaverStatus isVictory
   stats { networthPerMinute campStack wards { time type positionX positionY } wardDestruction { time isWard }
           deathEvents { time attacker target timeDead positionX positionY } killEvents { time target isSmoke } itemUsed { itemId count } } }"""
PB = """query P { match(id: %d) { id playbackData { wardEvents { indexId time positionX positionY fromPlayer wardType action playerDestroyed } }
  players { playerSlot playbackData { itemUsedEvents { time itemId attacker target } } } } }"""
core, pbd = {}, {}
for i in range(0, len(pick), 8):
    chunk = pick[i:i + 8]
    r = call(f"hold_stats_{chunk[0]}_{len(chunk)}", "query S {\n" + "\n".join(f"m{j}: match(id: {m}) {{ {STATS} }}" for j, m in enumerate(chunk)) + "\n}")
    if r.get("errors"): print("stats err", [e["message"][:120] for e in r["errors"]][:1])
    for m in (r.get("data") or {}).values():
        if m: core[m["id"]] = m
for mid in pick:
    r = call(f"hold_pb_{mid}", PB % mid)
    m = (r.get("data") or {}).get("match")
    if m: pbd[mid] = m
calls_note = dict(picked=len(pick), stats=len(core), playback_nonnull=sum(1 for m in pbd.values() if m.get("playbackData")),
                  playback_ward_events=sum(1 for m in pbd.values() if (m.get("playbackData") or {}).get("wardEvents")))
print(calls_note)
pickle.dump(dict(core=core, pb=pbd, pick=pick, note=calls_note), open("pb_holdout_raw.pkl", "wb"))

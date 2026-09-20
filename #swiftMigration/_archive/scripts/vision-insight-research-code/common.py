"""Shared loaders for the vision research (reuses candidate-validation primitives)."""
import sys, os, json, glob, collections
CV = os.path.abspath(os.path.join(os.path.dirname(__file__), "../candidate-validation-2026-09-15"))
RAWD = os.path.abspath(os.path.join(os.path.dirname(__file__), "../deep-research-2026-09-14/raw"))
_cwd = os.getcwd(); os.chdir(CV); sys.path.insert(0, CV)
from primitives import *          # noqa  (RAW path is relative to CV)
from metrics import CHECK         # noqa
os.chdir(_cwd)
def load_all():
    os.chdir(CV)
    try:
        core, rep, pb = load_matches()
    finally:
        os.chdir(_cwd)
    for f in glob.glob(f"{RAWD}/pbwin_old_*.json") + glob.glob(f"{RAWD}/pbstatsA_*.json"):
        d = json.load(open(f)).get("data") or {}
        if "match" in d:
            m = d["match"]
            if m and (m.get("playbackData") or {}).get("wardEvents"): pb.setdefault(m["id"], m)
        else:
            for m in d.values():
                if m and m.get("players"): core.setdefault(m["id"], m)
    pb = {k: v for k, v in pb.items() if (v.get("playbackData") or {}).get("wardEvents")}
    return core, rep, pb
def ward_life(pm, dur):
    """Exact observer/sentry lifecycles from playback wardEvents."""
    byi = collections.defaultdict(list)
    for w in pm["playbackData"]["wardEvents"] or []: byi[w["indexId"]].append(w)
    out = []
    for v in byi.values():
        sp = [w for w in v if w["action"] == "SPAWN"]; dp = [w for w in v if w["action"] == "DESPAWN"]
        if not sp: continue
        s0 = sp[0]; d0 = dp[0] if dp else None
        out.append(dict(t0=s0["time"], t1=d0["time"] if d0 else dur, type=s0["wardType"], owner=s0["fromPlayer"], killer=(d0 or {}).get("playerDestroyed"),
                        x=s0["positionX"], y=s0["positionY"], ended=d0 is not None))
    return out

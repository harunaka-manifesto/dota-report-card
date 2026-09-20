"""Map geometry heuristics (cells = STRATZ coordinate units, 1 cell = 64 world units)."""
import json, glob, collections, math
from common import RAWD
_lab = collections.defaultdict(collections.Counter)
for f in glob.glob(f"{RAWD}/playback_std_*.json") + glob.glob(f"{RAWD}/playback_full_fresh_*.json"):
    for p in json.load(open(f))["data"]["match"]["players"]:
        for e in (p.get("playbackData") or {}).get("csEvents") or []:
            if e.get("mapLocation") and e.get("positionX") is not None:
                _lab[(e["positionX"] // 8, e["positionY"] // 8)][e["mapLocation"]] += 1
LABEL = {k: v.most_common(1)[0][0] for k, v in _lab.items()}
RIVER_SUM, RIVER_HALF = 252, 10          # river diagonal x+y ~ 252 cells (fitted from RIVER/ROSHAN labels)
ROSH_PITS = [(104, 141), (152, 115)]     # labelled pit + point mirror (heuristic, not validated for the current patch)
VISION_R = 25                            # 1600 world units / 64
def label(x, y): return LABEL.get((x // 8, y // 8))
def region(x, y, team_radiant):
    """Coarse region relative to the ward owner's team."""
    lab = label(x, y) or ""
    if lab.endswith("BASE") or lab.endswith("FOUNTAIN"):
        return "OWN_BASE" if lab.startswith("RADIANT") == team_radiant else "ENEMY_BASE"
    s = x + y
    if abs(s - RIVER_SUM) <= RIVER_HALF or lab in ("RIVER", "ROSHAN"): return "RIVER"
    radiant_half = s < RIVER_SUM
    return "OWN_HALF" if radiant_half == team_radiant else "ENEMY_HALF"
def near_rosh(x, y, r=12): return any(math.dist((x, y), p) <= r for p in ROSH_PITS)
GRID = [(x, y) for x in range(64, 193, 4) for y in range(64, 193, 4)]
def coverage(points, r=VISION_R):
    if not points: return 0.0
    r2 = r * r
    return sum(1 for gx, gy in GRID if any((gx - x) ** 2 + (gy - y) ** 2 <= r2 for x, y in points)) / len(GRID)

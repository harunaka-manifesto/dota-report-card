"""Build de-identified hero item shards from the authorized local STRATZ corpus.

Future lettered patch: add its dates to item_references.py, then run this script
with --source pointing at new normalized evidence and --patch set to that patch.
Only that shard is scanned; composition reads the five newest saved shards.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from app.tracker.item_references import (  # noqa: E402
    CURRENT_PATCH,
    KEY_ITEMS,
    PATCH_START,
    STRATZ_VERSION_IDS,
    subpatch,
    suspended,
)

OUT = ROOT / "services/api/app/tracker"
SHARDS = OUT / "item_shards"
ROLES = {"POSITION_1": "CARRY", "POSITION_2": "MID", "POSITION_3": "OFFLANE"}


def scan(source: Path, wanted: set[str]) -> dict[str, dict[str, dict[str, int]]]:
    totals: dict[str, Counter] = defaultdict(Counter)
    ordered_totals: dict[str, Counter] = defaultdict(Counter)
    seen: set[tuple[int, int]] = set()
    for file in source.rglob("*.json"):
        try:
            rows = json.loads(file.read_text()).get("rows", [])
        except (OSError, ValueError):
            continue
        for row in rows:
            if not isinstance(row, dict) or row.get("game_version_id") not in STRATZ_VERSION_IDS:
                continue
            patch = subpatch(row.get("started_at"), major="7.41")
            if patch not in wanted:
                continue
            player = row.get("self")
            if not isinstance(player, dict):
                continue
            native_position = player.get("position_native")
            role = ROLES.get(native_position) if isinstance(native_position, str) else None
            mode = "TURBO" if row.get("game_mode_native") == "TURBO" else (
                "STANDARD" if row.get("game_mode_native") in {"ALL_PICK_RANKED", "ALL_PICK"} else None
            )
            hero = player.get("hero_id")
            match_id, slot = row.get("match_id"), player.get("player_slot")
            if not role or not mode or type(hero) is not int or type(match_id) is not int or type(slot) is not int:
                continue
            identity = (match_id, slot)
            if identity in seen:
                continue
            seen.add(identity)  # identifiers never leave memory or appear in a shard
            base = f"{mode}:{hero}:{role}"
            totals[patch][f"{base}:games"] += 1
            purchases = (player.get("events") or {}).get("item_purchases")
            if not isinstance(purchases, list):
                continue
            key_first: dict[int, int] = {}
            duration = row.get("duration_seconds", row.get("duration"))
            for event in purchases:
                if not isinstance(event, dict):
                    continue
                item, second = event.get("item_id"), event.get("time")
                if (
                    type(item) is int and item in KEY_ITEMS and type(second) is int
                    and type(duration) is int and 0 <= second <= duration
                ):
                    key_first[item] = min(key_first.get(item, second), second)
            for order, (item, second) in enumerate(
                sorted(key_first.items(), key=lambda purchase: (purchase[1], purchase[0])), 1,
            ):
                totals[patch][f"{base}:{item}:{second // 30}"] += 1
                # Build order is descriptive research input only; it never keys a reference.
                ordered_totals[patch][f"{base}:{item}:{order}"] += 1
    return {
        patch: {
            "counts": dict(totals[patch]),
            "ordered_counts": dict(ordered_totals[patch]),
        }
        for patch in wanted
    }


def _percentile(bins: list[tuple[int, int]], purchased: int, frac: float) -> int:
    target = math.ceil(frac * purchased)
    so_far = 0
    for bin_number, count in bins:
        so_far += count
        if so_far >= target:
            return bin_number * 30 + 15
    raise AssertionError("empty item histogram")


def compose(shards: list[dict]) -> dict:
    combined: Counter = Counter()
    for shard in shards:
        combined.update(shard["counts"])
    games: dict[str, int] = {}
    hists: dict[tuple[str, int], Counter] = defaultdict(Counter)
    for key, count in combined.items():
        if key.endswith(":games"):
            games[key[:-6]] = count
        else:
            base, item, bin_number = key.rsplit(":", 2)
            hists[(base, int(item))][int(bin_number)] += count
    references: dict[str, dict] = {}
    coverage: dict[str, dict] = {}
    for base, total in sorted(games.items()):
        hero = int(base.split(":")[1])
        qualified: list[str] = []
        pending = False
        for (group, item), hist in sorted(hists.items()):
            if group != base or item not in KEY_ITEMS:
                continue
            purchased = sum(hist.values())
            if purchased < 50 or purchased / total < 0.20:
                continue
            key, label = KEY_ITEMS[item]
            if suspended(hero, key):
                pending = True
                continue
            bins = sorted(hist.items())
            references[f"{base}:{key}"] = {
                "item_name": label,
                "p10": _percentile(bins, purchased, .10),
                "p25": _percentile(bins, purchased, .25),
                "median": _percentile(bins, purchased, .50),
                "purchase_count": purchased,
                "cohort_games": total,
                "purchase_rate": round(purchased / total, 3),
            }
            qualified.append(key)
        coverage[base] = {
            "games": total,
            "items": qualified,
            "reason": None if qualified else (
                "patch_change_pending" if pending or suspended(hero, "") else
                "sparse" if total < 50 else "no_qualified_item"
            ),
        }
    heroes = {int(base.split(":")[1]) for base in games}
    for hero in heroes:
        for mode in ("STANDARD", "TURBO"):
            for role in ROLES.values():
                coverage.setdefault(f"{mode}:{hero}:{role}", {
                    "games": 0, "items": [], "reason": "sparse",
                })
    return {"schema": 3, "major_patch": "7.41", "applies_to": CURRENT_PATCH,
            "patches": [s["patch"] for s in shards], "references": references,
            "coverage": coverage}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--patch", choices=tuple(PATCH_START), action="append")
    args = parser.parse_args()
    if args.source and args.patch:
        wanted = set(args.patch)
        counts_by_patch = scan(args.source, wanted)
        SHARDS.mkdir(exist_ok=True)
        for patch in wanted:
            result = counts_by_patch[patch]
            (SHARDS / f"{patch}.json").write_text(json.dumps({
                "patch": patch, **result,
            }, sort_keys=True, separators=(",", ":")) + "\n")
    elif args.source or args.patch:
        parser.error("--source and --patch must be supplied together")
    all_paths = sorted(SHARDS.glob("7.41*.json"))
    for old in all_paths[:-5]:
        old.unlink()
    paths = all_paths[-5:]
    shards = [json.loads(path.read_text()) for path in paths]
    result = compose(shards)
    (OUT / "item_references.json").write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"shards": result["patches"], "hero_role_mode": len(result["coverage"]),
                      "references": len(result["references"])}, sort_keys=True))


if __name__ == "__main__":
    main()

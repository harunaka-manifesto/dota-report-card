from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts.hero_knowledge.opendota.normalize import normalize_opendota_snapshot
from scripts.hero_knowledge.validate import validate_opendota_snapshot
from scripts.hero_knowledge.valve.normalize import normalize_hero_list, normalize_valve_snapshot

ROOT = Path(__file__).parents[2]
VALVE = ROOT / "tests" / "fixtures" / "hero_knowledge" / "valve"
OPENDOTA = ROOT / "tests" / "fixtures" / "hero_knowledge" / "opendota"


def _raw_valve(tmp_path: Path) -> dict:
    root = tmp_path / "valve"
    (root / "heroes").mkdir(parents=True)
    for source, destination in (
        (VALVE / "herolist.json", root / "herolist.json"),
        (VALVE / "axe.json", root / "heroes" / "2.json"),
        (VALVE / "puck.json", root / "heroes" / "13.json"),
    ):
        shutil.copy(source, destination)
    (root / "metadata.json").write_text(
        json.dumps({"snapshot_id": "valve-test", "hero_ids": [2, 13], "patch": "7.41e"}),
        encoding="utf-8",
    )
    return normalize_valve_snapshot(root)


def test_opendota_normalization_preserves_observed_context_and_unknowns(tmp_path: Path) -> None:
    root = tmp_path / "opendota"
    shutil.copytree(OPENDOTA, root)
    (root / "metadata.json").write_text(
        json.dumps(
            {
                "snapshot_id": "opendota-test",
                "source_urls": {
                    "heroStats": "https://api.opendota.com/api/heroStats",
                },
                "fetched_at": "2026-08-22T00:00:00Z",
                "raw_sha256": {"heroStats": "fixture"},
                "hero_sources": {"2": {}, "13": {}, "50": {}},
                "status": "available",
            }
        ),
        encoding="utf-8",
    )
    identities = normalize_hero_list(
        json.loads((VALVE / "herolist.json").read_text(encoding="utf-8"))
    )

    normalized = normalize_opendota_snapshot(root, identities)
    hero = normalized["heroes"][0]

    assert hero["hero_id"] == 2
    assert hero["bracket_performance"][0]["picks"] == 10
    assert hero["bracket_performance"][0]["win_rate"] == 0.5
    assert hero["item_profile"][0]["count"] == 20
    assert hero["matchup_profile"][0]["opponent_hero_id"] == 13
    assert hero["provenance"]["endpoint_sources"]["heroStats"]["source_url"] == (
        "https://api.opendota.com/api/heroStats"
    )
    assert validate_opendota_snapshot(normalized, {2, 13, 50}) == ()

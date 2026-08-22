from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

from scripts.hero_knowledge.diff import diff_knowledge_snapshots
from scripts.hero_knowledge.manifest import build_knowledge_snapshot
from scripts.hero_knowledge.opendota.normalize import normalize_opendota_snapshot
from scripts.hero_knowledge.validate import validate_knowledge_snapshot
from scripts.hero_knowledge.valve.normalize import normalize_hero_list, normalize_valve_snapshot

ROOT = Path(__file__).parents[2]
VALVE = ROOT / "tests" / "fixtures" / "hero_knowledge" / "valve"
OPENDOTA = ROOT / "tests" / "fixtures" / "hero_knowledge" / "opendota"


def _snapshots(tmp_path: Path) -> tuple[dict, dict]:
    valve_root = tmp_path / "valve"
    (valve_root / "heroes").mkdir(parents=True)
    for source, destination in (
        (VALVE / "herolist.json", valve_root / "herolist.json"),
        (VALVE / "axe.json", valve_root / "heroes" / "2.json"),
        (VALVE / "puck.json", valve_root / "heroes" / "13.json"),
    ):
        shutil.copy(source, destination)
    (valve_root / "metadata.json").write_text(
        json.dumps({"snapshot_id": "valve-test", "hero_ids": [2, 13], "patch": "7.41e"}),
        encoding="utf-8",
    )
    valve = normalize_valve_snapshot(valve_root)
    opendota_root = tmp_path / "opendota"
    shutil.copytree(OPENDOTA, opendota_root)
    (opendota_root / "metadata.json").write_text(
        json.dumps(
            {
                "snapshot_id": "opendota-test",
                "source_urls": {
                    "heroStats": "https://api.opendota.com/api/heroStats",
                },
                "fetched_at": "2026-08-22T00:00:00Z",
                "raw_sha256": {"heroStats": "fixture"},
                "hero_sources": {
                    "2": {
                        "durations": {},
                        "itemPopularity": {},
                        "matchups": {},
                    },
                    "50": {
                        "durations": {},
                        "itemPopularity": {},
                        "matchups": {},
                    },
                    "13": {
                        "durations": {},
                        "itemPopularity": {},
                        "matchups": {},
                    },
                },
                "status": "available",
            }
        ),
        encoding="utf-8",
    )
    identities = normalize_hero_list(
        json.loads((VALVE / "herolist.json").read_text(encoding="utf-8"))
    )
    opendota = normalize_opendota_snapshot(opendota_root, identities)
    return valve, opendota


def test_knowledge_snapshot_has_provenance_and_preserves_provider_status(tmp_path: Path) -> None:
    valve, opendota = _snapshots(tmp_path)
    knowledge = build_knowledge_snapshot(
        valve,
        opendota,
        repo_root=Path(__file__).parents[2],
        generated_at="2026-08-22T00:00:00Z",
        knowledge_version="hero-knowledge-test",
    )

    assert validate_knowledge_snapshot(knowledge) == ()
    puck = next(row for row in knowledge["heroes"] if row["identity"]["hero_id"] == 13)
    assert puck["empirical"]["status"] == "observed"
    assert puck["provenance"]["field_sources"]["empirical"] == "opendota.aggregate"
    assert puck["provenance"]["field_sources"]["mechanics"] == "valve.herodata"
    assert puck["editorial"]["review_status"] == "unreviewed"


def test_diff_flags_mechanical_change_for_approved_editorial(tmp_path: Path) -> None:
    valve, opendota = _snapshots(tmp_path)
    old = build_knowledge_snapshot(valve, opendota, repo_root=ROOT, knowledge_version="old")
    new = copy.deepcopy(old)
    axe = next(row for row in new["heroes"] if row["identity"]["hero_id"] == 2)
    axe["editorial"]["review_status"] = "approved"
    axe["mechanics"]["abilities"][0]["description"] = "Changed mechanic"
    new["knowledge_version"] = "new"

    result = diff_knowledge_snapshots(old, new)

    assert result["changed_hero_count"] == 1
    assert result["hero_changes"][0]["editorial_review_required"] is True
    assert {item["change"] for item in result["hero_changes"][0]["changes"]} == {
        "mechanics_changed"
    }

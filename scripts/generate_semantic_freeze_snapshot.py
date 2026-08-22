#!/usr/bin/env python3
"""Generate the checked-in v5.2 semantic-freeze pilot snapshot.

The live CLI builds the same record shape from normalized Valve/OpenDota
inputs.  This offline generator keeps the committed pilot reproducible from
the frozen factual identity snapshot plus the reviewed semantic layer, so the
API never needs source payloads or network access at runtime.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.hero_knowledge.manifest import build_knowledge_snapshot, build_manifest, write_json
from scripts.hero_knowledge.validate import assert_valid, validate_semantic_layer

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "services/api/app/heroes/data"
FACTUAL_PATH = DATA_ROOT / "factual/2026-08-16.json"
SEMANTICS_PATH = DATA_ROOT / "semantics/pilot-v1.json"
KNOWLEDGE_PATH = DATA_ROOT / "knowledge/hero-knowledge-semantic-freeze-pilot-v1.json"
MANIFEST_PATH = DATA_ROOT / "hero-knowledge-manifest.json"
KNOWLEDGE_VERSION = "hero-knowledge-semantic-freeze-pilot-v1"
GENERATED_AT = "2026-08-22T00:00:00Z"


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def _source_snapshots(factual: dict, semantics: dict) -> tuple[dict, dict, set[int]]:
    factual_rows = {int(row["hero_id"]): row for row in factual.get("heroes", [])}
    selected = {
        int(row["hero_id"])
        for row in semantics.get("heroes", [])
        if isinstance(row, dict) and row.get("hero_id") is not None
    }
    valve_roster: list[dict] = []
    valve_heroes: list[dict] = []
    opendota_heroes: list[dict] = []
    for hero_id in sorted(selected):
        factual_row = factual_rows[hero_id]
        identity = {
            "hero_id": hero_id,
            "key": str(factual_row["key"]),
            "internal_name": str(factual_row["key"]),
            "display_name": str(factual_row["name"]),
            "primary_attribute": "unknown",
            "complexity": None,
            "portrait_ref": factual_row.get("portrait_ref"),
            "available": bool(factual_row.get("available", True)),
            "aliases": [str(factual_row["name"])],
            "roles": list(factual_row.get("roles", [])),
        }
        valve_roster.append(identity)
        valve_heroes.append(
            {
                "hero_id": hero_id,
                "identity": identity,
                "abilities": [],
                "facets": [],
                "talents": [],
                "base_stats": {},
                "facet_abilities": [],
            }
        )
        opendota_heroes.append(
            {
                "hero_id": hero_id,
                "bracket_performance": [],
                "duration_profile": [],
                "item_profile": [],
                "matchup_profile": [],
                "provenance": {
                    "source": "OpenDota aggregate snapshot",
                    "source_window": "semantic-freeze-pilot",
                },
            }
        )
    valve = {
        "snapshot_id": "valve-semantic-freeze-pilot-7.41e",
        "patch": "7.41e",
        "roster": valve_roster,
        "heroes": valve_heroes,
    }
    opendota = {
        "snapshot_id": "opendota-semantic-freeze-pilot-2026-08-22",
        "status": "partial",
        "heroes": opendota_heroes,
        "endpoint_semantics": {"population": "public_aggregate", "role_distribution": "unknown"},
    }
    return valve, opendota, selected


def main() -> int:
    factual = _read(FACTUAL_PATH)
    semantics = _read(SEMANTICS_PATH)
    assert_valid(validate_semantic_layer(semantics), "semantic layer")
    valve, opendota, selected = _source_snapshots(factual, semantics)
    knowledge = build_knowledge_snapshot(
        valve,
        opendota,
        repo_root=ROOT,
        generated_at=GENERATED_AT,
        hero_ids=selected,
        knowledge_version=KNOWLEDGE_VERSION,
        reviewed_semantics=semantics,
    )
    knowledge["freeze"] = {
        "status": "pilot-reviewed",
        "pilot_hero_ids": sorted(selected),
        "semantic_vocabulary_version": semantics["version"],
        "copy_authoring_status": "not_started",
    }
    write_json(KNOWLEDGE_PATH, knowledge)
    manifest = build_manifest(knowledge, knowledge_path=KNOWLEDGE_PATH, generated_at=GENERATED_AT)
    manifest.update(
        {
            "knowledge_path": str(KNOWLEDGE_PATH.relative_to(DATA_ROOT)),
            "semantic_layer_path": str(SEMANTICS_PATH.relative_to(DATA_ROOT)),
            "semantic_vocabulary_version": semantics["version"],
            "freeze_status": "pilot-reviewed",
            "pilot_hero_ids": sorted(selected),
        }
    )
    write_json(MANIFEST_PATH, manifest)
    print(
        json.dumps(
            {
                "knowledge": str(KNOWLEDGE_PATH),
                "manifest": str(MANIFEST_PATH),
                "heroes": len(selected),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

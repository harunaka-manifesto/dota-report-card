"""Snapshot assembly, manifest versioning, and provenance helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION
from .config import isoformat
from .derive.behavior import derive_behavior
from .derive.confidence import source_confidence
from .derive.mechanics import derive_mechanics
from .errors import SourceSchemaError
from .schemas import HeroKnowledgeRecord, empty_empirical_context


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def read_json(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise SourceSchemaError(f"Unable to read JSON object: {target}") from exc
    if not isinstance(value, dict):
        raise SourceSchemaError(f"Expected JSON object: {target}")
    return value


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def editorial_provenance(repo_root: Path, identity: dict[str, Any]) -> dict[str, Any]:
    metadata_root = repo_root / "heroes_metadata"
    key = str(identity.get("key", ""))
    hero_id = int(identity.get("hero_id", 0))
    path = metadata_root / f"{hero_id:03d}-{key}.md"
    if not path.exists():
        aliases = {
            key,
            str(identity.get("display_name", "")).casefold().replace(" ", "-"),
            str(identity.get("display_name", "")).casefold().replace("'", "").replace(" ", "-"),
        }
        matches = sorted(path for alias in aliases for path in metadata_root.glob(f"*-{alias}.md"))
        path = matches[0] if matches else path
    relative = str(path.relative_to(repo_root)) if path.exists() else None
    return {
        "strengths": [],
        "weaknesses": [],
        "teamfight_jobs": [],
        "notes": [],
        "review_status": "unreviewed",
        "source_file": relative,
        "policy": "Existing research corpus remains build-time evidence; scraper does not generate prose.",
    }


def _hero_map(snapshot: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not snapshot:
        return {}
    return {
        int(row["hero_id"]): row
        for row in snapshot.get("heroes", [])
        if isinstance(row, dict) and row.get("hero_id") is not None
    }


def build_knowledge_snapshot(
    valve: dict[str, Any],
    opendota: dict[str, Any],
    *,
    repo_root: str | Path,
    valve_plus: dict[str, Any] | None = None,
    generated_at: str | None = None,
    hero_ids: set[int] | None = None,
    knowledge_version: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or isoformat()
    valve_heroes = _hero_map(valve)
    opendota_heroes = _hero_map(opendota)
    valve_plus_heroes = _hero_map(valve_plus)
    selected = sorted(hero_ids or valve_heroes)
    if not selected:
        raise SourceSchemaError("Cannot build a knowledge snapshot without Valve heroes")
    records: list[dict[str, Any]] = []
    root = Path(repo_root)
    for hero_id in selected:
        hero = valve_heroes.get(hero_id)
        if hero is None:
            raise SourceSchemaError(
                f"Requested hero {hero_id} is absent from Valve normalized snapshot"
            )
        if hero_id not in opendota_heroes:
            raise SourceSchemaError(
                f"Required OpenDota normalized snapshot is missing hero {hero_id}"
            )
        identity = dict(hero.get("identity", {}))
        mechanics_source = {
            "abilities": hero.get("abilities", []),
            "facets": hero.get("facets", []),
            "talents": hero.get("talents", []),
            "base_stats": hero.get("base_stats", {}),
            "facet_abilities": hero.get("facet_abilities", []),
        }
        mechanic_result = derive_mechanics({**hero, "identity": identity})
        empirical = dict(opendota_heroes[hero_id])
        if not empirical:
            empirical = empty_empirical_context()
        optional = valve_plus_heroes.get(hero_id)
        empirical["optional_valve_plus"] = dict(optional) if optional else {}
        behavior_result = derive_behavior(empirical)
        provenance = {
            "schema_version": SCHEMA_VERSION,
            "field_sources": {
                "identity": "valve.roster",
                "mechanics": "valve.herodata",
                "functions": "derive.mechanics",
                "demands": "derive.mechanics + derive.behavior",
                "capabilities": "derive.mechanics",
                "empirical": "opendota.aggregate",
                "optional_valve_plus": "valve_plus.optional" if optional else "unknown",
                "editorial": "heroes_metadata/*.md",
            },
            "source_versions": {
                "valve_snapshot": valve.get("snapshot_id"),
                "valve_patch": valve.get("patch"),
                "opendota_snapshot": opendota.get("snapshot_id") if opendota else None,
                "valve_plus_snapshot": valve_plus.get("snapshot_id") if valve_plus else None,
                "mechanic_rules": mechanic_result["provenance"]["rule_version"],
                "behavior_rules": behavior_result["provenance"]["rule_version"],
            },
            "generated_at": generated,
            "confidence": source_confidence(
                valve=hero,
                opendota=opendota_heroes.get(hero_id),
                valve_plus=valve_plus,
            ),
        }
        record = HeroKnowledgeRecord(
            identity=identity,
            mechanics=mechanics_source,
            functions=mechanic_result["functions"],
            demands={
                **mechanic_result["demands"],
                **{"behavior": behavior_result.get("role_flexibility")},
            },
            capabilities=mechanic_result["capabilities"],
            empirical=empirical,
            editorial=editorial_provenance(root, identity),
            provenance=provenance,
            derived_characteristics={
                "behavior": behavior_result,
            },
        )
        records.append(record.as_dict())
    version = knowledge_version or f"hero-knowledge-{generated[:10]}"
    return {
        "schema_version": SCHEMA_VERSION,
        "knowledge_version": version,
        "generated_at": generated,
        "sources": {
            "valve": {
                "snapshot": valve.get("snapshot_id"),
                "patch": valve.get("patch"),
                "roster_count": len(valve.get("roster", [])),
            },
            "opendota": {
                "snapshot": opendota.get("snapshot_id"),
                "status": opendota.get("status", "available"),
                "required": True,
                "hero_count": len(opendota.get("heroes", [])),
                "endpoint_semantics": opendota.get("endpoint_semantics", {}),
            },
            "valve_plus": {
                "snapshot": valve_plus.get("snapshot_id") if valve_plus else None,
                "status": valve_plus.get("status", "unavailable") if valve_plus else "unavailable",
                "required": False,
                "reason": (
                    valve_plus.get("reason")
                    if valve_plus
                    else "optional_provider_not_configured"
                ),
            },
            "dotacoach_editorial": {"snapshot": "existing-heroes-metadata"},
        },
        "hero_count": len(records),
        "heroes": records,
    }


def build_manifest(
    knowledge: dict[str, Any],
    *,
    knowledge_path: str | Path,
    valve_path: str | Path | None = None,
    opendota_path: str | Path | None = None,
    valve_plus_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    value = {
        "schema_version": knowledge.get("schema_version", SCHEMA_VERSION),
        "knowledge_version": knowledge.get("knowledge_version"),
        "generated_at": generated_at or knowledge.get("generated_at") or isoformat(),
        "knowledge_path": str(Path(knowledge_path)),
        "knowledge_sha256": sha256_file(knowledge_path),
        "hero_count": knowledge.get("hero_count", len(knowledge.get("heroes", []))),
        "sources": knowledge.get("sources", {}),
    }
    if valve_path is not None:
        value["valve_normalized_sha256"] = sha256_file(valve_path)
    if opendota_path is not None and Path(opendota_path).exists():
        value["opendota_normalized_sha256"] = sha256_file(opendota_path)
    if valve_plus_path is not None and Path(valve_plus_path).exists():
        value["valve_plus_normalized_sha256"] = sha256_file(valve_plus_path)
    return value

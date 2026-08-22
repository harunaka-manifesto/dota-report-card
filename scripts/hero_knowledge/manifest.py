"""Snapshot assembly, manifest versioning, and provenance helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
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
    reviewed_semantics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    generated = generated_at or isoformat()
    valve_heroes = _hero_map(valve)
    opendota_heroes = _hero_map(opendota)
    valve_plus_heroes = _hero_map(valve_plus)
    semantic_heroes = _semantic_map(reviewed_semantics)
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
                "semantic": "reviewed_semantics" if hero_id in semantic_heroes else "unknown",
            },
            "source_versions": {
                "valve_snapshot": valve.get("snapshot_id"),
                "valve_patch": valve.get("patch"),
                "opendota_snapshot": opendota.get("snapshot_id") if opendota else None,
                "valve_plus_snapshot": valve_plus.get("snapshot_id") if valve_plus else None,
                "mechanic_rules": mechanic_result["provenance"]["rule_version"],
                "behavior_rules": behavior_result["provenance"]["rule_version"],
                "semantic_snapshot": (
                    reviewed_semantics.get("version") if reviewed_semantics else None
                ),
            },
            "generated_at": generated,
            "confidence": source_confidence(
                valve=hero,
                opendota=opendota_heroes.get(hero_id),
                valve_plus=valve_plus,
            ),
        }
        semantic = semantic_heroes.get(hero_id)
        functions = mechanic_result["functions"]
        demands = {
            **mechanic_result["demands"],
            **{"behavior": behavior_result.get("role_flexibility")},
        }
        capabilities = mechanic_result["capabilities"]
        editorial = editorial_provenance(root, identity)
        if semantic is not None:
            reviewed_functions = semantic.get("functions", {})
            if isinstance(reviewed_functions, Mapping):
                functions = {
                    "primary": list(reviewed_functions.get("primary", [])),
                    "secondary": list(reviewed_functions.get("secondary", [])),
                }
            demands.update(_semantic_evidence_map(semantic.get("demands"), semantic))
            capabilities.update(_semantic_function_capabilities(functions, semantic))
            editorial.update(
                {
                    "strengths": list(semantic.get("strengths", [])),
                    "weaknesses": list(semantic.get("weaknesses", [])),
                    "teamfight_jobs": list(semantic.get("teamfight_profile", [])),
                    "review_status": semantic.get("review_status", "approved"),
                    "review": dict(semantic.get("review", {})),
                }
            )
        record = HeroKnowledgeRecord(
            identity=identity,
            mechanics=mechanics_source,
            functions=functions,
            demands=demands,
            capabilities=capabilities,
            empirical=empirical,
            editorial=editorial,
            provenance=provenance,
            derived_characteristics={
                "behavior": behavior_result,
            },
        )
        record_data = record.as_dict()
        if semantic is not None:
            record_data["semantic_version"] = str(
                reviewed_semantics.get("version", "hero-semantics-unknown")
                if reviewed_semantics
                else "hero-semantics-unknown"
            )
            record_data["semantic_confidence"] = str(semantic.get("confidence", "low"))
            record_data["empirical_support"] = str(semantic.get("empirical_support", "unknown"))
            record_data["reviewed_evidence_refs"] = _semantic_evidence_refs(semantic)
        records.append(record_data)
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
            "semantic_review": (
                {
                    "snapshot": reviewed_semantics.get("version"),
                    "status": reviewed_semantics.get("review_status", "unknown"),
                    "hero_count": len(semantic_heroes),
                }
                if reviewed_semantics
                else {"snapshot": None, "status": "unavailable", "hero_count": 0}
            ),
        },
        "hero_count": len(records),
        "heroes": records,
    }


def _semantic_map(snapshot: Mapping[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not snapshot:
        return {}
    heroes = snapshot.get("heroes", [])
    if not isinstance(heroes, list):
        return {}
    return {
        int(row["hero_id"]): row
        for row in heroes
        if isinstance(row, Mapping) and row.get("hero_id") is not None
    }


def _semantic_evidence_map(
    value: Any, semantic: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key): {
            "characteristic": str(key),
            "band": str(band) if str(band) in {"low", "medium", "high", "unknown"} else "unknown",
            "derived_from": _semantic_evidence_refs(semantic, key=str(key)),
            "rule_version": str(semantic.get("version", "hero-semantics-unknown")),
        }
        for key, band in value.items()
    }


def _semantic_function_capabilities(
    functions: Mapping[str, Any], semantic: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    values: list[str] = []
    for field_name in ("primary", "secondary"):
        field = functions.get(field_name, [])
        if isinstance(field, list):
            values.extend(str(item) for item in field)
    return {
        key: {
            "characteristic": key,
            "band": "high" if key in set(str(item) for item in functions.get("primary", [])) else "medium",
            "derived_from": _semantic_evidence_refs(semantic, key=key),
            "rule_version": str(semantic.get("version", "hero-semantics-unknown")),
        }
        for key in dict.fromkeys(values)
    }


def _semantic_evidence_refs(semantic: Mapping[str, Any], *, key: str | None = None) -> list[str]:
    refs: list[str] = []
    fields = ("strengths", "weaknesses") if key is not None else ("strengths", "weaknesses", "teamfight_profile")
    for field_name in fields:
        values = semantic.get(field_name, [])
        if not isinstance(values, list):
            continue
        for value in values:
            if not isinstance(value, Mapping):
                continue
            if key is not None and value.get("semantic_key") != key:
                continue
            evidence = value.get("evidence_refs", [])
            if isinstance(evidence, list):
                refs.extend(str(item) for item in evidence)
    return list(dict.fromkeys(refs))


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

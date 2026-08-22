"""Command-line entry point for Valve/OpenDota hero-knowledge ingestion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .client import SourceHttpClient
from .config import Settings, isoformat
from .diff import diff_knowledge_snapshots
from .errors import HeroKnowledgeError
from .manifest import build_knowledge_snapshot, build_manifest, read_json, write_json
from .opendota.client import OpenDotaClient
from .opendota.fetch import fetch_opendota_snapshot
from .opendota.normalize import normalize_opendota_snapshot
from .schemas import HeroIdentity, canonical_key
from .validate import (
    assert_valid,
    validate_knowledge_snapshot,
    validate_opendota_snapshot,
    validate_semantic_layer,
    validate_valve_snapshot,
)
from .valve.client import ValveDatafeedClient
from .valve.fetch import fetch_valve_snapshot
from .valve.normalize import normalize_valve_snapshot
from .valve_plus.fetch import fetch_valve_plus_snapshot
from .valve_plus.normalize import normalize_valve_plus_snapshot

PILOT_HEROES = (
    "axe",
    "centaur warrunner",
    "puck",
    "dazzle",
    "nature's prophet",
    "phantom assassin",
    "beastmaster",
    "oracle",
    "meepo",
    "invoker",
)


def _settings(args: argparse.Namespace) -> Settings:
    return Settings.from_root(args.root)


def _latest_directory(root: Path) -> Path:
    candidates = sorted(path for path in root.iterdir() if path.is_dir()) if root.exists() else []
    if not candidates:
        raise HeroKnowledgeError(f"No snapshots found under {root}")
    return candidates[-1]


def _latest_file(root: Path, pattern: str) -> Path:
    candidates = sorted(root.glob(pattern)) if root.exists() else []
    if not candidates:
        raise HeroKnowledgeError(f"No snapshot files found under {root}")
    return candidates[-1]


def _snapshot_dir(settings: Settings, source: str, snapshot_id: str | None) -> Path:
    return (
        settings.raw_source_root(source) / snapshot_id
        if snapshot_id
        else _latest_directory(settings.raw_source_root(source))
    )


def _normalized_path(settings: Settings, source: str, snapshot_id: str | None) -> Path:
    if snapshot_id:
        candidate = Path(snapshot_id)
        if candidate.exists():
            return candidate
        if candidate.suffix == ".json":
            return settings.normalized_source_root(source) / candidate.name
        return settings.normalized_source_root(source) / f"{snapshot_id}.json"
    return _latest_file(settings.normalized_source_root(source), "*.json")


def _identities_from_valve(normalized: dict[str, Any]) -> list[HeroIdentity]:
    roster = normalized.get("roster")
    if isinstance(roster, list) and roster:
        return [
            HeroIdentity(
                hero_id=int(row["hero_id"]),
                key=str(row["key"]),
                internal_name=str(row.get("internal_name", row["key"])),
                display_name=str(row.get("display_name", row.get("name", row["key"]))),
                primary_attribute=str(row.get("primary_attribute", "unknown")),
                complexity=int(row["complexity"]) if row.get("complexity") is not None else None,
                portrait_ref=row.get("portrait_ref"),
                available=bool(row.get("available", True)),
                aliases=tuple(str(alias) for alias in row.get("aliases", [])),
            )
            for row in roster
            if isinstance(row, dict)
        ]
    raise HeroKnowledgeError("Valve normalized snapshot has no canonical roster")


def _resolve_identity(value: str, identities: list[HeroIdentity]) -> HeroIdentity:
    wanted = canonical_key(value)
    for identity in identities:
        if wanted == canonical_key(str(identity.hero_id)) or wanted in {
            canonical_key(alias) for alias in identity.aliases
        }:
            return identity
    raise HeroKnowledgeError(f"Unknown canonical hero: {value}")


def _fetch_valve(args: argparse.Namespace) -> int:
    settings = _settings(args)
    with SourceHttpClient(settings) as http:
        summary = fetch_valve_snapshot(
            settings,
            ValveDatafeedClient(http, settings),
            hero=args.hero,
            limit=args.limit,
            snapshot_id=args.snapshot_id,
            force_refresh=args.force_refresh,
        )
    print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))
    return 0 if not summary.failed else 1


def _fetch_opendota(args: argparse.Namespace) -> int:
    settings = _settings(args)
    identities: list[HeroIdentity] = []
    if args.hero:
        identities = _identities_from_valve(
            read_json(_normalized_path(settings, "valve", args.valve_snapshot_id))
        )
    hero_ids = {_resolve_identity(args.hero, identities).hero_id} if args.hero else None
    if args.fixture_dir is not None:
        summary = fetch_opendota_snapshot(
            settings,
            fixture_dir=args.fixture_dir,
            hero_ids=hero_ids,
            snapshot_id=args.snapshot_id,
            force_refresh=args.force_refresh,
        )
    else:
        extra_headers = (
            {"Authorization": f"Bearer {settings.opendota_api_key}"}
            if settings.opendota_api_key
            else {}
        )
        with SourceHttpClient(settings, extra_headers=extra_headers) as http:
            summary = fetch_opendota_snapshot(
                settings,
                OpenDotaClient(http, settings),
                hero_ids=hero_ids,
                snapshot_id=args.snapshot_id,
                force_refresh=args.force_refresh,
            )
    print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))
    return 0 if not summary.failed else 1


def _fetch_valve_plus(args: argparse.Namespace) -> int:
    settings = _settings(args)
    summary = fetch_valve_plus_snapshot(
        settings,
        fixture_dir=args.fixture_dir,
        snapshot_id=args.snapshot_id,
    )
    print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))
    return 0


def _normalize_valve(args: argparse.Namespace) -> int:
    settings = _settings(args)
    snapshot = normalize_valve_snapshot(_snapshot_dir(settings, "valve", args.snapshot_id))
    assert_valid(validate_valve_snapshot(snapshot, require_complete=args.all), "Valve normalized")
    output = settings.normalized_source_root("valve") / f"{snapshot['snapshot_id']}.json"
    write_json(output, snapshot)
    print(json.dumps({"source": "valve", "output_path": str(output)}, indent=2, sort_keys=True))
    return 0


def _normalize_opendota(args: argparse.Namespace) -> int:
    settings = _settings(args)
    raw_path = _snapshot_dir(settings, "opendota", args.snapshot_id)
    identities = _identities_from_valve(
        read_json(_normalized_path(settings, "valve", args.valve_snapshot_id))
    )
    snapshot = normalize_opendota_snapshot(raw_path, identities)
    canonical_ids = {identity.hero_id for identity in identities}
    assert_valid(
        validate_opendota_snapshot(
            snapshot, canonical_ids, require_complete=args.all
        ),
        "OpenDota normalized",
    )
    output = settings.normalized_source_root("opendota") / f"{snapshot['snapshot_id']}.json"
    write_json(output, snapshot)
    print(json.dumps({"source": "opendota", "output_path": str(output)}, indent=2, sort_keys=True))
    return 0


def _normalize_valve_plus(args: argparse.Namespace) -> int:
    settings = _settings(args)
    canonical_ids: set[int] | None = None
    try:
        valve = read_json(_normalized_path(settings, "valve", args.valve_snapshot_id))
        canonical_ids = {identity.hero_id for identity in _identities_from_valve(valve)}
    except HeroKnowledgeError:
        pass
    snapshot = normalize_valve_plus_snapshot(
        _snapshot_dir(settings, "valve_plus", args.snapshot_id), canonical_ids
    )
    output = settings.normalized_source_root("valve_plus") / f"{snapshot['snapshot_id']}.json"
    write_json(output, snapshot)
    print(json.dumps({"source": "valve_plus", "output_path": str(output)}, indent=2, sort_keys=True))
    return 0


def _required_opendota(
    settings: Settings,
    snapshot_id: str | None,
    canonical_ids: set[int],
    *,
    require_complete: bool,
) -> tuple[dict[str, Any], Path]:
    path = _normalized_path(settings, "opendota", snapshot_id)
    snapshot = read_json(path)
    assert_valid(
        validate_opendota_snapshot(
            snapshot, canonical_ids, require_complete=require_complete
        ),
        "OpenDota normalized",
    )
    return snapshot, path


def _reviewed_semantics(settings: Settings, value: Path | None) -> dict[str, Any] | None:
    path = value or (settings.root / "services/api/app/heroes/data/semantics/pilot-v1.json")
    if not path.exists():
        return None
    snapshot = read_json(path)
    assert_valid(validate_semantic_layer(snapshot), "semantic layer")
    return snapshot


def _optional_valve_plus(
    settings: Settings, snapshot_id: str | None
) -> tuple[dict[str, Any] | None, Path | None]:
    if not snapshot_id and not settings.normalized_source_root("valve_plus").exists():
        return None, None
    try:
        path = _normalized_path(settings, "valve_plus", snapshot_id)
    except HeroKnowledgeError:
        if snapshot_id:
            raise
        return None, None
    return read_json(path), path


def _build(args: argparse.Namespace) -> int:
    settings = _settings(args)
    valve_path = _normalized_path(settings, "valve", args.valve_snapshot_id)
    valve = read_json(valve_path)
    identities = _identities_from_valve(valve)
    selected_ids: set[int] | None = None
    label = ""
    if args.hero:
        selected_ids = {_resolve_identity(args.hero, identities).hero_id}
        label = "-pilot"
    elif args.pilot:
        selected_ids = {_resolve_identity(value, identities).hero_id for value in PILOT_HEROES}
        label = "-pilot"
    require_complete = args.all or selected_ids is None
    canonical_ids = {identity.hero_id for identity in identities}
    assert_valid(
        validate_valve_snapshot(valve, require_complete=require_complete), "Valve normalized"
    )
    opendota, opendota_path = _required_opendota(
        settings,
        args.opendota_snapshot_id,
        canonical_ids,
        require_complete=require_complete,
    )
    valve_plus, valve_plus_path = _optional_valve_plus(settings, args.valve_plus_snapshot_id)
    reviewed_semantics = _reviewed_semantics(settings, args.semantic_layer)
    generated_at = isoformat()
    version = args.knowledge_version or f"hero-knowledge-{generated_at[:10]}{label}"
    knowledge = build_knowledge_snapshot(
        valve,
        opendota,
        repo_root=settings.root,
        valve_plus=valve_plus,
        generated_at=generated_at,
        hero_ids=selected_ids,
        knowledge_version=version,
        reviewed_semantics=reviewed_semantics,
    )
    assert_valid(validate_knowledge_snapshot(knowledge), "knowledge")
    output = settings.knowledge_root / f"{version}.json"
    write_json(output, knowledge)
    manifest = build_manifest(
        knowledge,
        knowledge_path=output,
        valve_path=valve_path,
        opendota_path=opendota_path,
        valve_plus_path=valve_plus_path,
    )
    manifest["knowledge_path"] = str(output.relative_to(settings.data_root))
    write_json(settings.data_root / "hero-knowledge-manifest.json", manifest)
    print(json.dumps({"knowledge_version": version, "output_path": str(output)}, indent=2, sort_keys=True))
    return 0


def _refresh(args: argparse.Namespace) -> int:
    settings = _settings(args)
    extra_headers = (
        {"Authorization": f"Bearer {settings.opendota_api_key}"}
        if settings.opendota_api_key
        else {}
    )
    with SourceHttpClient(settings) as http:
        valve_summary = fetch_valve_snapshot(
            settings,
            ValveDatafeedClient(http, settings),
            hero=args.hero,
            force_refresh=args.force_refresh,
        )
    if valve_summary.failed:
        raise HeroKnowledgeError(f"Valve refresh failed: {list(valve_summary.failed)}")
    valve = normalize_valve_snapshot(Path(valve_summary.output_path))
    assert_valid(validate_valve_snapshot(valve, require_complete=args.hero is None), "Valve normalized")
    valve_path = settings.normalized_source_root("valve") / f"{valve['snapshot_id']}.json"
    write_json(valve_path, valve)
    identities = _identities_from_valve(valve)
    hero_ids = {_resolve_identity(args.hero, identities).hero_id} if args.hero else None
    if args.opendota_fixture_dir is not None:
        opendota_summary = fetch_opendota_snapshot(
            settings,
            fixture_dir=args.opendota_fixture_dir,
            hero_ids=hero_ids,
            force_refresh=args.force_refresh,
        )
    else:
        with SourceHttpClient(settings, extra_headers=extra_headers) as http:
            opendota_summary = fetch_opendota_snapshot(
                settings,
                OpenDotaClient(http, settings),
                hero_ids=hero_ids,
                force_refresh=args.force_refresh,
            )
    if opendota_summary.failed:
        raise HeroKnowledgeError(
            "Required OpenDota refresh failed; raw snapshot preserved at "
            f"{opendota_summary.output_path}: {list(opendota_summary.failed)}"
        )
    opendota = normalize_opendota_snapshot(Path(opendota_summary.output_path), identities)
    assert_valid(
        validate_opendota_snapshot(
            opendota,
            {identity.hero_id for identity in identities},
            require_complete=args.hero is None,
        ),
        "OpenDota normalized",
    )
    opendota_path = settings.normalized_source_root("opendota") / f"{opendota['snapshot_id']}.json"
    write_json(opendota_path, opendota)
    valve_plus: dict[str, Any] | None = None
    valve_plus_path: Path | None = None
    plus_summary = fetch_valve_plus_snapshot(
        settings,
        fixture_dir=args.valve_plus_fixture_dir,
        snapshot_id=args.valve_plus_snapshot_id,
    )
    valve_plus = normalize_valve_plus_snapshot(
        Path(plus_summary.output_path), {identity.hero_id for identity in identities}
    )
    valve_plus_path = settings.normalized_source_root("valve_plus") / (
        f"{valve_plus['snapshot_id']}.json"
    )
    write_json(valve_plus_path, valve_plus)
    generated_at = isoformat()
    version = args.knowledge_version or f"hero-knowledge-{generated_at[:10]}"
    reviewed_semantics = _reviewed_semantics(settings, args.semantic_layer)
    knowledge = build_knowledge_snapshot(
        valve,
        opendota,
        repo_root=settings.root,
        valve_plus=valve_plus,
        generated_at=generated_at,
        hero_ids=hero_ids,
        knowledge_version=version,
        reviewed_semantics=reviewed_semantics,
    )
    assert_valid(validate_knowledge_snapshot(knowledge), "knowledge")
    output = settings.knowledge_root / f"{version}.json"
    write_json(output, knowledge)
    manifest = build_manifest(
        knowledge,
        knowledge_path=output,
        valve_path=valve_path,
        opendota_path=opendota_path,
        valve_plus_path=valve_plus_path,
    )
    manifest["knowledge_path"] = str(output.relative_to(settings.data_root))
    manifest_path = settings.data_root / "hero-knowledge-manifest.json"
    write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "valve": valve_summary.as_dict(),
                "opendota": opendota_summary.as_dict(),
                "valve_plus": plus_summary.as_dict(),
                "knowledge_version": version,
                "manifest_path": str(manifest_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _validate(args: argparse.Namespace) -> int:
    settings = _settings(args)
    results: dict[str, Any] = {}
    if args.source in {"valve", "all"}:
        path = _normalized_path(settings, "valve", args.snapshot_id)
        snapshot = read_json(path)
        results["valve"] = {
            "path": str(path),
            "errors": list(validate_valve_snapshot(snapshot, require_complete=args.all)),
        }
    if args.source in {"opendota", "all"}:
        path = _normalized_path(settings, "opendota", args.opendota_snapshot_id)
        snapshot = read_json(path)
        valve_path = _normalized_path(settings, "valve", args.valve_snapshot_id)
        identities = _identities_from_valve(read_json(valve_path))
        results["opendota"] = {
            "path": str(path),
            "errors": list(
                validate_opendota_snapshot(
                    snapshot,
                    {identity.hero_id for identity in identities},
                    require_complete=args.all or args.source == "all",
                )
            ),
        }
    if args.source in {"valve-plus", "all"}:
        try:
            path = _normalized_path(settings, "valve_plus", args.valve_plus_snapshot_id)
        except HeroKnowledgeError:
            results["valve_plus"] = {"status": "unavailable", "errors": []}
        else:
            snapshot = read_json(path)
            results["valve_plus"] = {
                "path": str(path),
                "status": snapshot.get("status", "unknown"),
                "errors": [],
            }
    if args.source in {"knowledge", "all"}:
        path = _latest_file(settings.knowledge_root, "*.json")
        snapshot = read_json(path)
        results["knowledge"] = {"path": str(path), "errors": list(validate_knowledge_snapshot(snapshot))}
    print(json.dumps(results, indent=2, sort_keys=True))
    return 1 if any(value["errors"] for value in results.values()) else 0


def _diff(args: argparse.Namespace) -> int:
    print(json.dumps(diff_knowledge_snapshots(read_json(args.old), read_json(args.new)), indent=2, sort_keys=True))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build versioned Valve/OpenDota hero knowledge snapshots")
    parser.add_argument("--root", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch")
    fetch_source = fetch.add_subparsers(dest="source", required=True)
    valve = fetch_source.add_parser("valve")
    valve.add_argument("--hero")
    valve.add_argument("--limit", type=int)
    valve.add_argument("--snapshot-id")
    valve.add_argument("--force-refresh", action="store_true")
    valve.add_argument("--all", action="store_true")
    opendota = fetch_source.add_parser("opendota")
    opendota.add_argument("--hero")
    opendota.add_argument("--snapshot-id")
    opendota.add_argument("--force-refresh", action="store_true")
    opendota.add_argument("--fixture-dir", type=Path)
    opendota.add_argument("--valve-snapshot-id")
    opendota.add_argument("--all", action="store_true")
    valve_plus = fetch_source.add_parser("valve-plus")
    valve_plus.add_argument("--fixture-dir", type=Path)
    valve_plus.add_argument("--snapshot-id")

    normalize = subparsers.add_parser("normalize")
    normalize_source = normalize.add_subparsers(dest="source", required=True)
    valve_normalize = normalize_source.add_parser("valve")
    valve_normalize.add_argument("--snapshot-id")
    valve_normalize.add_argument("--all", action="store_true")
    opendota_normalize = normalize_source.add_parser("opendota")
    opendota_normalize.add_argument("--snapshot-id")
    opendota_normalize.add_argument("--valve-snapshot-id")
    opendota_normalize.add_argument("--all", action="store_true")
    plus_normalize = normalize_source.add_parser("valve-plus")
    plus_normalize.add_argument("--snapshot-id")
    plus_normalize.add_argument("--valve-snapshot-id")

    build = subparsers.add_parser("build")
    build.add_argument("--hero")
    build.add_argument("--pilot", action="store_true")
    build.add_argument("--all", action="store_true")
    build.add_argument("--valve-snapshot-id")
    build.add_argument("--opendota-snapshot-id")
    build.add_argument("--valve-plus-snapshot-id")
    build.add_argument("--knowledge-version")
    build.add_argument("--semantic-layer", type=Path)

    refresh = subparsers.add_parser("refresh", help="fetch, normalize, validate, and build one snapshot")
    refresh.add_argument("--hero")
    refresh.add_argument("--opendota-fixture-dir", type=Path)
    refresh.add_argument("--valve-plus-fixture-dir", type=Path)
    refresh.add_argument("--valve-plus-snapshot-id")
    refresh.add_argument("--force-refresh", action="store_true")
    refresh.add_argument("--knowledge-version")
    refresh.add_argument("--semantic-layer", type=Path)

    validate = subparsers.add_parser("validate")
    validate.add_argument("source", choices=("valve", "opendota", "valve-plus", "knowledge", "all"))
    validate.add_argument("--all", action="store_true")
    validate.add_argument("--snapshot-id")
    validate.add_argument("--opendota-snapshot-id")
    validate.add_argument("--valve-snapshot-id")
    validate.add_argument("--valve-plus-snapshot-id")

    diff = subparsers.add_parser("diff")
    diff.add_argument("--old", required=True)
    diff.add_argument("--new", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "fetch" and args.source == "valve":
            return _fetch_valve(args)
        if args.command == "fetch" and args.source == "opendota":
            return _fetch_opendota(args)
        if args.command == "fetch" and args.source == "valve-plus":
            return _fetch_valve_plus(args)
        if args.command == "normalize" and args.source == "valve":
            return _normalize_valve(args)
        if args.command == "normalize" and args.source == "opendota":
            return _normalize_opendota(args)
        if args.command == "normalize" and args.source == "valve-plus":
            return _normalize_valve_plus(args)
        if args.command == "build":
            return _build(args)
        if args.command == "refresh":
            return _refresh(args)
        if args.command == "validate":
            return _validate(args)
        if args.command == "diff":
            return _diff(args)
        raise HeroKnowledgeError("Unsupported command")
    except (HeroKnowledgeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"hero-knowledge: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

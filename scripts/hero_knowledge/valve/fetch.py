"""Fetch and persist a Valve hero snapshot."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import Settings, isoformat, source_snapshot_id
from ..errors import FetchError, SourceSchemaError
from ..schemas import canonical_key
from .client import ValveDatafeedClient
from .normalize import normalize_hero_list


@dataclass(frozen=True, slots=True)
class ValveFetchSummary:
    source: str
    snapshot_id: str
    attempted: int
    succeeded: int
    failed: tuple[dict[str, Any], ...]
    cache_hits: int
    output_path: str
    patch: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "snapshot_id": self.snapshot_id,
            "heroes_attempted": self.attempted,
            "heroes_succeeded": self.succeeded,
            "heroes_failed": list(self.failed),
            "cache_hits": self.cache_hits,
            "output_path": self.output_path,
            "patch": self.patch,
        }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def _resolve_hero(value: str, identities: list[Any]) -> int:
    try:
        numeric = int(value)
    except ValueError:
        numeric = -1
    if numeric > 0 and any(item.hero_id == numeric for item in identities):
        return numeric
    wanted = canonical_key(value)
    for identity in identities:
        if wanted in {canonical_key(alias) for alias in identity.aliases}:
            return identity.hero_id
    raise SourceSchemaError(f"Unknown Valve hero: {value}")


def fetch_valve_snapshot(
    settings: Settings,
    client: ValveDatafeedClient,
    *,
    hero: str | None = None,
    limit: int | None = None,
    snapshot_id: str | None = None,
    force_refresh: bool = False,
) -> ValveFetchSummary:
    snapshot = snapshot_id or source_snapshot_id("valve", "hero-snapshot")
    output = settings.raw_source_root("valve") / snapshot
    output.mkdir(parents=True, exist_ok=True)
    list_response = client.fetch_hero_list(force_refresh=force_refresh)
    list_payload = list_response.json()
    identities = normalize_hero_list(list_payload)
    _write_json(output / "herolist.json", list_payload)

    selected_ids = (
        [_resolve_hero(hero, identities)] if hero else [item.hero_id for item in identities]
    )
    if limit is not None:
        if limit <= 0:
            raise ValueError("--limit must be positive")
        selected_ids = selected_ids[:limit]

    patch = None
    cache_hits = int(list_response.cache_hit)
    try:
        patch_response = client.fetch_patch_list(force_refresh=force_refresh)
        _write_json(output / "patchnoteslist.json", patch_response.json())
        cache_hits += int(patch_response.cache_hit)
        patches = patch_response.json().get("patches", [])
        if isinstance(patches, list) and patches:
            patch = str(patches[-1].get("patch_number")) if isinstance(patches[-1], dict) else None
    except (FetchError, SourceSchemaError):
        # Patch metadata is useful but not required to normalize the hero
        # payload; record the omission rather than failing a valid hero run.
        patch = None

    succeeded = 0
    failures: list[dict[str, Any]] = []
    hero_hashes: dict[str, str] = {}
    source_urls: dict[str, str] = {
        "herolist": list_response.url,
        "patchnoteslist": f"{settings.valve_base_url}/datafeed/patchnoteslist?language={settings.language}",
    }

    def fetch_one(hero_id: int) -> tuple[int, Any]:
        return hero_id, client.fetch_hero(hero_id, force_refresh=force_refresh)

    with ThreadPoolExecutor(max_workers=settings.concurrency) as pool:
        futures = {pool.submit(fetch_one, hero_id): hero_id for hero_id in selected_ids}
        for future in as_completed(futures):
            hero_id = futures[future]
            try:
                returned_id, response = future.result()
                _write_json(output / "heroes" / f"{returned_id}.json", response.json())
                hero_hashes[str(returned_id)] = response.raw_sha256
                source_urls[str(returned_id)] = response.url
                cache_hits += int(response.cache_hit)
                succeeded += 1
            except Exception as exc:  # noqa: BLE001 - preserve per-hero failure details
                failures.append({"hero_id": hero_id, "error": str(exc)})

    metadata = {
        "snapshot_id": snapshot,
        "source": "valve",
        "fetched_at": isoformat(),
        "patch": patch,
        "language": settings.language,
        "hero_ids": sorted(selected_ids),
        "heroes_attempted": len(selected_ids),
        "heroes_succeeded": succeeded,
        "heroes_failed": sorted(failures, key=lambda item: item["hero_id"]),
        "cache_hits": cache_hits,
        "source_urls": source_urls,
        "hero_hashes": hero_hashes,
        "user_agent": settings.user_agent,
    }
    _write_json(output / "metadata.json", metadata)
    return ValveFetchSummary(
        source="valve",
        snapshot_id=snapshot,
        attempted=len(selected_ids),
        succeeded=succeeded,
        failed=tuple(failures),
        cache_hits=cache_hits,
        output_path=str(output),
        patch=patch,
    )

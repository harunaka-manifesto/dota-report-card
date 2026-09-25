"""Fetch and persist the required OpenDota aggregate hero snapshot."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..client import ResponsePayload
from ..config import Settings, isoformat, source_snapshot_id
from ..errors import HeroKnowledgeError, SourceSchemaError
from .client import OpenDotaClient

ENDPOINTS = {
    "durations": "durations.json",
    "itemPopularity": "itemPopularity.json",
    "matchups": "matchups.json",
}


@dataclass(frozen=True, slots=True)
class OpenDotaFetchSummary:
    source: str
    snapshot_id: str
    attempted: int
    succeeded: int
    failed: tuple[dict[str, Any], ...]
    cache_hits: int
    output_path: str
    source_url: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "snapshot_id": self.snapshot_id,
            "heroes_attempted": self.attempted,
            "heroes_succeeded": self.succeeded,
            "heroes_failed": list(self.failed),
            "cache_hits": self.cache_hits,
            "output_path": self.output_path,
            "source_url": self.source_url,
        }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def _fixture_root(value: Path) -> tuple[Path, Path]:
    root = value if value.is_dir() else value.parent
    stats = value if value.is_file() else root / "heroStats.json"
    return root, stats


def _read_fixture(root: Path, relative: str) -> tuple[Any, str]:
    path = root / relative
    try:
        raw = path.read_bytes()
        return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SourceSchemaError(f"OpenDota fixture is not valid JSON: {path}") from exc


def _hero_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or not payload:
        raise SourceSchemaError("OpenDota heroStats payload must be a non-empty list")
    rows = [row for row in payload if isinstance(row, dict)]
    if len(rows) != len(payload):
        raise SourceSchemaError("OpenDota heroStats payload contains a non-object row")
    if any(row.get("id") is None for row in rows):
        raise SourceSchemaError("OpenDota heroStats payload contains a hero without an id")
    ids = [int(row["id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise SourceSchemaError("OpenDota heroStats payload contains duplicate hero ids")
    return rows


def _validate_endpoint(endpoint: str, payload: Any, hero_id: int) -> None:
    if endpoint in {"durations", "matchups"}:
        if not isinstance(payload, list):
            raise SourceSchemaError(
                f"OpenDota {endpoint} payload for hero {hero_id} must be a list"
            )
        return
    if endpoint == "itemPopularity" and not isinstance(payload, dict):
        raise SourceSchemaError(
            f"OpenDota itemPopularity payload for hero {hero_id} must be an object"
        )


def _response_metadata(response: ResponsePayload) -> dict[str, Any]:
    return {
        "source_url": response.url,
        "fetched_at": response.fetched_at,
        "raw_sha256": response.raw_sha256,
        "cache_hit": response.cache_hit,
    }


def fetch_opendota_snapshot(
    settings: Settings,
    client: OpenDotaClient | None = None,
    *,
    fixture_dir: Path | None = None,
    hero_ids: set[int] | None = None,
    snapshot_id: str | None = None,
    force_refresh: bool = False,
) -> OpenDotaFetchSummary:
    """Fetch heroStats plus per-hero empirical endpoints.

    A partial result is written for inspection, but the required OpenDota
    provider remains a failed run when any selected hero lacks an endpoint.
    """

    snapshot = snapshot_id or source_snapshot_id("opendota", "hero-context")
    output = settings.raw_source_root("opendota") / snapshot
    output.mkdir(parents=True, exist_ok=True)

    fixture_root: Path | None = None
    stats_metadata: dict[str, Any]
    if fixture_dir is not None:
        fixture_root, stats_path = _fixture_root(fixture_dir)
        raw = stats_path.read_bytes()
        try:
            stats_payload = json.loads(raw.decode("utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SourceSchemaError(f"OpenDota fixture is not valid JSON: {stats_path}") from exc
        stats_metadata = {
            "source_url": "fixture://opendota/api/heroStats",
            "fetched_at": isoformat(),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "cache_hit": False,
        }
    else:
        if client is None:
            raise SourceSchemaError("An OpenDota client is required for live retrieval")
        response = client.fetch_hero_stats(force_refresh=force_refresh)
        stats_payload = response.json()
        stats_metadata = _response_metadata(response)

    rows = _hero_rows(stats_payload)
    available_ids = {int(row["id"]) for row in rows}
    selected_ids = sorted(hero_ids if hero_ids is not None else available_ids)
    missing_stats = sorted(set(selected_ids) - available_ids)
    if missing_stats:
        raise SourceSchemaError(
            f"OpenDota heroStats is missing requested hero ids: {missing_stats}"
        )

    _write_json(output / "heroStats.json", stats_payload)
    endpoint_metadata: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    completed = 0
    cache_hits = int(stats_metadata["cache_hit"])

    def fetch_one(hero_id: int) -> tuple[int, dict[str, Any], int]:
        values: dict[str, Any] = {}
        hero_cache_hits = 0
        for endpoint, filename in ENDPOINTS.items():
            if fixture_root is not None:
                payload, raw_sha256 = _read_fixture(
                    fixture_root, f"heroes/{hero_id}/{filename}"
                )
                _validate_endpoint(endpoint, payload, hero_id)
                values[endpoint] = {
                    "payload": payload,
                    "metadata": {
                        "source_url": f"fixture://opendota/heroes/{hero_id}/{endpoint}",
                        "fetched_at": stats_metadata["fetched_at"],
                        "raw_sha256": raw_sha256,
                        "cache_hit": False,
                    },
                }
            else:
                assert client is not None
                fetcher = {
                    "durations": client.fetch_durations,
                    "itemPopularity": client.fetch_item_popularity,
                    "matchups": client.fetch_matchups,
                }[endpoint]
                response = fetcher(hero_id, force_refresh=force_refresh)
                payload = response.json()
                _validate_endpoint(endpoint, payload, hero_id)
                values[endpoint] = {
                    "payload": payload,
                    "metadata": _response_metadata(response),
                }
                hero_cache_hits += int(response.cache_hit)
        return hero_id, values, hero_cache_hits

    if fixture_root is not None or len(selected_ids) <= 1:
        results = []
        for hero_id in selected_ids:
            try:
                results.append(fetch_one(hero_id))
            except (HeroKnowledgeError, OSError, ValueError) as exc:
                failures.append({"hero_id": hero_id, "error": str(exc)})
    else:
        results = []
        with ThreadPoolExecutor(max_workers=settings.concurrency) as executor:
            pending = {executor.submit(fetch_one, hero_id): hero_id for hero_id in selected_ids}
            for future in as_completed(pending):
                hero_id = pending[future]
                try:
                    results.append(future.result())
                except (HeroKnowledgeError, OSError, ValueError) as exc:
                    failures.append({"hero_id": hero_id, "error": str(exc)})

    for hero_id, values, hero_hits in sorted(results):
        hero_root = output / "heroes" / str(hero_id)
        hero_root.mkdir(parents=True, exist_ok=True)
        hero_sources: dict[str, Any] = {}
        for endpoint, filename in ENDPOINTS.items():
            value = values[endpoint]
            _write_json(hero_root / filename, value["payload"])
            hero_sources[endpoint] = value["metadata"]
        endpoint_metadata[str(hero_id)] = hero_sources
        completed += 1
        cache_hits += hero_hits

    status = "available" if not failures else "partial"
    metadata = {
        "snapshot_id": snapshot,
        "source": "opendota",
        "status": status,
        "required": True,
        "fetched_at": stats_metadata["fetched_at"],
        "hero_ids": selected_ids,
        "hero_count": completed,
        "requested_hero_count": len(selected_ids),
        "source_urls": {"heroStats": stats_metadata["source_url"]},
        "raw_sha256": {"heroStats": stats_metadata["raw_sha256"]},
        "hero_sources": endpoint_metadata,
        "failed": failures,
        "cache_hits": cache_hits,
        "endpoint_semantics": {
            "heroStats": "aggregate hero performance by rank_tier/public/pro fields",
            "durations": "aggregate duration bins for the hero",
            "itemPopularity": "aggregate item counts grouped by purchase phase",
            "matchups": "aggregate hero-vs-hero observations; population is not narrowed in payload",
        },
    }
    _write_json(output / "metadata.json", metadata)
    return OpenDotaFetchSummary(
        source="opendota",
        snapshot_id=snapshot,
        attempted=len(selected_ids),
        succeeded=completed,
        failed=tuple(sorted(failures, key=lambda item: int(item["hero_id"]))),
        cache_hits=cache_hits,
        output_path=str(output),
        source_url=str(stats_metadata["source_url"]),
    )

from __future__ import annotations

import json
import shutil
from pathlib import Path

import httpx

from scripts.hero_knowledge.client import SourceHttpClient
from scripts.hero_knowledge.config import Settings
from scripts.hero_knowledge.validate import validate_valve_snapshot
from scripts.hero_knowledge.valve.normalize import normalize_hero_list, normalize_valve_snapshot

FIXTURES = Path(__file__).parents[1] / "fixtures" / "hero_knowledge" / "valve"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _raw_snapshot(tmp_path: Path) -> Path:
    root = tmp_path / "raw" / "valve" / "valve-hero-snapshot-test"
    (root / "heroes").mkdir(parents=True)
    shutil.copy(FIXTURES / "herolist.json", root / "herolist.json")
    shutil.copy(FIXTURES / "axe.json", root / "heroes" / "2.json")
    shutil.copy(FIXTURES / "puck.json", root / "heroes" / "13.json")
    (root / "metadata.json").write_text(
        json.dumps(
            {
                "snapshot_id": "valve-hero-snapshot-test",
                "hero_ids": [2, 13],
                "patch": "7.41e",
                "fetched_at": "2026-08-22T00:00:00Z",
                "hero_hashes": {},
                "source_urls": {},
            }
        ),
        encoding="utf-8",
    )
    return root


def test_canonical_valve_identity_uses_id_and_aliases() -> None:
    identities = normalize_hero_list(_json(FIXTURES / "herolist.json"))

    axe = next(item for item in identities if item.hero_id == 2)

    assert axe.key == "axe"
    assert axe.display_name == "Axe"
    assert "axe" in axe.aliases
    assert axe.primary_attribute == "strength"


def test_partial_development_snapshot_normalizes_without_faking_missing_heroes(
    tmp_path: Path,
) -> None:
    normalized = normalize_valve_snapshot(_raw_snapshot(tmp_path))

    assert normalized["snapshot_id"] == "valve-hero-snapshot-test"
    assert [row["hero_id"] for row in normalized["heroes"]] == [2, 13]
    assert len(normalized["roster"]) == 3
    assert normalized["heroes"][0]["talents"][0]["level"] is None
    assert validate_valve_snapshot(normalized) == ()
    assert validate_valve_snapshot(normalized, require_complete=True) == (
        "valve.incomplete_roster_details",
    )


def test_complete_roster_gate_accepts_every_canonical_id() -> None:
    roster = [{"hero_id": hero_id} for hero_id in range(1, 128)]
    heroes = [
        {"hero_id": hero_id, "identity": {"hero_id": hero_id}, "abilities": []}
        for hero_id in range(1, 128)
    ]

    assert (
        validate_valve_snapshot({"roster": roster, "heroes": heroes}, require_complete=True) == ()
    )


def test_source_client_retries_transient_failure_and_caches_success(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, request=_request)
        return httpx.Response(200, json={"ok": True}, request=_request)

    settings = Settings.from_root(tmp_path)
    settings = Settings(
        root=settings.root,
        data_root=tmp_path / "data",
        max_retries=1,
        min_delay_seconds=0,
    )
    with SourceHttpClient(
        settings, transport=httpx.MockTransport(handler), sleeper=lambda _delay: None
    ) as client:
        first = client.get_json("https://example.test/hero", {"id": 2})
        second = client.get_json("https://example.test/hero", {"id": 2})

    assert first.json() == {"ok": True}
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert calls == 2

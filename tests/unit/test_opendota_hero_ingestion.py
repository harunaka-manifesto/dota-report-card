from __future__ import annotations

import json
import shutil
from pathlib import Path

import httpx

from scripts.hero_knowledge.client import SourceHttpClient
from scripts.hero_knowledge.config import Settings
from scripts.hero_knowledge.opendota.client import OpenDotaClient
from scripts.hero_knowledge.opendota.fetch import fetch_opendota_snapshot
from scripts.hero_knowledge.opendota.normalize import normalize_opendota_snapshot
from scripts.hero_knowledge.validate import validate_opendota_snapshot
from scripts.hero_knowledge.valve.normalize import normalize_hero_list
from scripts.hero_knowledge.valve_plus.fetch import fetch_valve_plus_snapshot
from scripts.hero_knowledge.valve_plus.normalize import normalize_valve_plus_snapshot

ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "hero_knowledge"


def test_opendota_normalization_keeps_aggregate_rates_and_unknown_dimensions(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw" / "opendota" / "opendota-test"
    shutil.copytree(FIXTURES / "opendota", raw)
    (raw / "metadata.json").write_text(
        json.dumps(
            {
                "snapshot_id": "opendota-test",
                "source_urls": {
                    "heroStats": "https://api.opendota.com/api/heroStats",
                },
                "fetched_at": "2026-08-22T00:00:00Z",
                "raw_sha256": {"heroStats": "fixture"},
                "hero_sources": {"2": {}, "50": {}},
                "status": "available",
            }
        ),
        encoding="utf-8",
    )
    identities = normalize_hero_list(
        json.loads((FIXTURES / "valve" / "herolist.json").read_text(encoding="utf-8"))
    )

    normalized = normalize_opendota_snapshot(raw, identities)
    axe = next(row for row in normalized["heroes"] if row["hero_id"] == 2)

    assert axe["bracket_performance"][0]["picks"] == 10
    assert axe["bracket_performance"][0]["win_rate"] == 0.5
    assert axe["item_profile"][0]["count"] == 20
    assert axe["matchup_profile"][0]["opponent_hero_id"] == 13
    assert axe["provenance"]["source"] == "OpenDota public aggregate endpoints"
    assert validate_opendota_snapshot(normalized, {2, 13, 50}) == ()


def test_opendota_client_uses_one_cached_aggregate_request(tmp_path: Path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=[{"id": 2}], request=request)

    settings = Settings.from_root(tmp_path)
    settings = Settings(
        root=settings.root,
        data_root=tmp_path / "data",
        min_delay_seconds=0,
    )
    with SourceHttpClient(
        settings, transport=httpx.MockTransport(handler), sleeper=lambda _delay: None
    ) as http:
        client = OpenDotaClient(http, settings)
        first = client.fetch_hero_stats()
        second = client.fetch_hero_stats()

    assert first.json() == [{"id": 2}]
    assert second.cache_hit is True
    assert calls == 1


def test_opendota_fixture_fetch_persists_a_versioned_raw_snapshot(tmp_path: Path) -> None:
    settings = Settings.from_root(tmp_path)
    settings = Settings(
        root=settings.root,
        data_root=tmp_path / "data",
    )

    summary = fetch_opendota_snapshot(
        settings,
        fixture_dir=FIXTURES / "opendota",
        snapshot_id="opendota-fixture",
    )

    assert summary.source == "opendota"
    assert Path(summary.output_path, "heroStats.json").exists()
    assert Path(summary.output_path, "heroes", "2", "matchups.json").exists()
    assert Path(summary.output_path, "metadata.json").exists()


def test_required_opendota_fetch_reports_missing_endpoint_without_succeeding(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture"
    shutil.copytree(FIXTURES / "opendota", fixture)
    (fixture / "heroes" / "2" / "matchups.json").unlink()
    settings = Settings.from_root(tmp_path / "repo")
    settings = Settings(root=settings.root, data_root=tmp_path / "data")

    summary = fetch_opendota_snapshot(
        settings,
        fixture_dir=fixture,
        hero_ids={2},
        snapshot_id="opendota-missing-endpoint",
    )

    assert summary.succeeded == 0
    assert summary.failed[0]["hero_id"] == 2
    metadata = json.loads(
        Path(summary.output_path, "metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["status"] == "partial"


def test_opendota_validation_rejects_impossible_win_count() -> None:
    snapshot = {
        "heroes": [
            {
                "hero_id": 2,
                "bracket_performance": [
                    {"picks": 2, "wins": 3, "win_rate": 1.5}
                ],
                "duration_profile": [],
                "item_profile": [],
                "matchup_profile": [],
            }
        ]
    }

    errors = validate_opendota_snapshot(snapshot, {2})

    assert "opendota.2.bracket_performance.0.wins_exceed_count" in errors
    assert "opendota.2.bracket_performance.0.win_rate: expected a number in [0, 1]" in errors


def test_optional_valve_plus_unavailable_does_not_fail_the_provider(tmp_path: Path) -> None:
    settings = Settings(root=tmp_path / "repo", data_root=tmp_path / "data")

    summary = fetch_valve_plus_snapshot(settings)
    normalized = normalize_valve_plus_snapshot(summary.output_path)

    assert summary.status == "unavailable"
    assert normalized["status"] == "unavailable"
    assert normalized["heroes"] == []

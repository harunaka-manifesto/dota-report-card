from __future__ import annotations

import asyncio
import copy
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from app.analysis.service import AnalysisService
from app.analysis.source import MappingSource
from app.api.report_schemas import validate_free_dna_report
from app.core.config import Settings
from app.core.security import parse_player_identifier
from app.identity.steam import SteamWebResolver
from app.main import create_app
from app.share.service import build_share_svg
from app.storage.repository import InMemoryRepository
from fastapi.testclient import TestClient

_TEST_WINDOW_END = int(datetime.now(UTC).timestamp())


def _summary(match_id: int, index: int) -> dict[str, int | bool]:
    return {
        "match_id": match_id,
        "start_time": _TEST_WINDOW_END - index * 7_200,
        "duration": 1_800,
        "hero_id": 25 + index % 5,
        "player_slot": 0,
        "radiant_win": index % 2 == 0,
        "game_mode": 1,
        "lobby_type": 0,
        "kills": 8 + index % 4,
        "deaths": 4,
        "assists": 10,
        "lane_role": 2 if index % 2 else 1,
    }


def _run_report(count: int = 35, *, profile: dict[str, object] | None = None):
    source = MappingSource(
        player={"profile": profile or {"account_id": 42, "personaname": "Fixture player"}},
        matches=[_summary(900_100_000 + index, index) for index in range(count)],
        details={},
    )
    repository = InMemoryRepository()
    service = AnalysisService(source, repository=repository, settings=Settings())
    job, _ = asyncio.run(service.create_analysis("42", enqueue=False))
    asyncio.run(service.run_job(job))
    return source, repository, service, job


def test_steam64_and_numeric_profile_url_convert_to_same_account() -> None:
    numeric = parse_player_identifier("76561198154040957")
    profile = parse_player_identifier("https://steamcommunity.com/profiles/76561198154040957/")
    assert numeric.account_id == 193775229
    assert numeric == profile


def test_vanity_resolver_caches_successful_lookup() -> None:
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"response": {"success": 1, "steamid": "76561198154040957"}})

    async def run() -> tuple[int, int]:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        resolver = SteamWebResolver("secret", http_client=client)
        first = await resolver.resolve("Example_Player")
        second = await resolver.resolve("example_player")
        await client.aclose()
        return first, second

    assert asyncio.run(run()) == (193775229, 193775229)
    assert calls == 1


def test_free_report_is_v5_summary_only_versioned_and_expiring() -> None:
    source, repository, _service, job = _run_report()
    assert job.status == "completed"
    assert {"behavior_elements", "behavior_patterns", "hero_portfolio", "rendering_report"} <= set(job.completed_stages)
    assert source.requests == [("player", 42), ("matches", 42)]
    report = repository.get_report(job.report_id or "")
    assert report is not None
    assert report["schema_version"] == "free-dna-report-5.1.0"
    assert report["report_variant"] == "free_dna_report"
    assert report["noindex"] is True
    assert "account_id" not in report
    assert report["cost"]["detail_requests"] == 0
    assert report["cost"]["parse_requests"] == 0
    assert report["cost"]["parse_status_requests"] == 0
    assert len(report["elements"]) == 18
    assert len(report["patterns"]) == 11
    assert report["metadata"]["history_limit"] is None
    assert report["reproducibility"]["model_version"] == "free-dna-model-5.1.0"
    assert report["reproducibility"]["recency_weighting_version"] == "recency-weighting-5.0.0"
    assert report["story"]["ordered_pages"] == [page["id"] for page in report["pages"]]
    assert {page["kind"] for page in report["pages"]} >= {"element_scan", "pattern_highlight", "hero_mirror_reveal", "deep_dive"}
    validate_free_dna_report(report)

    svg, _ = build_share_svg(report, card_type="final", show_name=False, show_avatar=False)
    assert str(42) not in svg
    assert "<svg" in svg
    for heading in ("TOP SIGNALS", "PATTERNS", "HERO PORTFOLIO", "HERO MIRROR"):
        assert heading in svg
    assert "new_heroes_same_toolkit" not in svg

    now = datetime.now(UTC)
    assert repository.purge_expired(now=now + timedelta(days=31)) == 1
    assert repository.get_report(job.report_id or "") is None


def test_public_report_route_sets_noindex_and_returns_strict_v5_contract() -> None:
    source, _repository, _service, job = _run_report()
    app = create_app(Settings(), source=source)
    # The app owns a fresh service, so build one report through that service.
    service = app.state.analysis_service
    created, _ = asyncio.run(service.create_analysis("42", enqueue=False))
    asyncio.run(service.run_job(created))
    response = TestClient(app).get(f"/v1/reports/{created.report_id}")
    assert response.status_code == 200
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    body = response.json()
    assert body["schema_version"] == "free-dna-report-5.1.0"
    assert body["report_variant"] == "free_dna_report"
    validate_free_dna_report(body)
    assert job.status == "completed"


def test_current_report_has_alignment_metadata_and_historical_v50_payload_still_reads() -> None:
    _source, repository, _service, job = _run_report()
    report = repository.get_report(job.report_id or "")
    assert report is not None
    assert report["versions"]["context_baseline"] == "context-baseline-1.0.0"
    assert report["reproducibility"]["context_baseline_version"] == "context-baseline-1.0.0"
    assert all(
        pattern["qualification_element_keys"]
        or pattern["status"] in {"unavailable", "suppressed"}
        for pattern in report["patterns"]
    )
    for pattern in report["patterns"]:
        if pattern["action"] is not None:
            assert pattern["action"]["evidence_summary"] is not None

    historical = copy.deepcopy(report)
    historical["schema_version"] = "free-dna-report-5.0.0"
    historical["versions"].pop("context_baseline", None)
    historical["reproducibility"].pop("context_baseline_version", None)
    for pattern in historical["patterns"]:
        pattern.pop("qualification_element_keys", None)
        pattern.pop("qualification_clause_index", None)
        action = pattern.get("action")
        if action is not None:
            action.pop("evidence_summary", None)
            for difference in action.get("summary_differences", []):
                difference.pop("coverage", None)
    validate_free_dna_report(historical)


def test_free_cache_miss_never_calls_match_details_or_parse_requests() -> None:
    class NoDetailSource(MappingSource):
        async def get_match(self, match_id: int) -> dict[str, object]:
            raise AssertionError(f"Free DNA requested detail match {match_id}")

    source = NoDetailSource(
        player={"profile": {"account_id": 42, "personaname": "Fixture player"}},
        matches=[_summary(900_110_000 + index, index) for index in range(35)],
        details={},
    )
    service = AnalysisService(source, settings=Settings())
    job, _ = asyncio.run(service.create_analysis("42", enqueue=False))
    asyncio.run(service.run_job(job))
    assert job.status == "completed"
    assert source.requests == [("player", 42), ("matches", 42)]
    report = service.repository.get_report(job.report_id or "")
    assert report is not None
    assert report["cost"]["detail_requests"] == 0
    assert report["cost"]["parse_requests"] == 0


def test_public_v5_schema_rejects_internal_and_unknown_fields() -> None:
    _source, repository, _service, job = _run_report()
    report = repository.get_report(job.report_id or "")
    assert report is not None
    for field in ("raw_matches", "source_match_ids", "raw_metrics", "effect_metrics"):
        invalid = copy.deepcopy(report)
        invalid[field] = {}
        with pytest.raises(ValueError):
            validate_free_dna_report(invalid)
    invalid_element = copy.deepcopy(report)
    invalid_element["elements"][0]["raw_metrics"] = {}
    with pytest.raises(ValueError):
        validate_free_dna_report(invalid_element)


def test_public_free_report_sanitizes_identifier_shaped_identity_fields() -> None:
    _source, repository, _service, job = _run_report(
        profile={
            "account_id": 42,
            "personaname": "42",
            "avatarfull": "https://steamcommunity.com/profiles/42/avatar",
        }
    )
    report = repository.get_report(job.report_id or "")
    assert report is not None
    assert report["identity"] == {"display_name": "Anonymous player", "avatar_url": None, "rank_tier": None}


def test_free_history_boundaries_are_29_fail_30_limited_and_60_normal() -> None:
    def report_for(count: int):
        _source, repository, _service, job = _run_report(count)
        return repository.get_report(job.report_id or "") if job.report_id else None

    assert report_for(29) is None
    limited = report_for(30)
    normal = report_for(60)
    assert limited is not None and limited["metadata"]["history_tier"] == "limited"
    assert normal is not None and normal["metadata"]["history_tier"] == "normal"
    assert limited["quality"]["partial"] is True
    assert normal["quality"]["history_tier"] == "normal"

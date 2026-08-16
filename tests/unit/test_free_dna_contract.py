from __future__ import annotations

import asyncio
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

_PRIVATE_KEYS = {
    "account_id",
    "steam_id",
    "steamid",
    "steam64",
    "account_id_masked",
    "source_match_ids",
    "normalized_match_refs",
    "derived_feature_refs",
    "raw_payload_refs",
    "match_ids",
    "legacy_summary",
    "deep_scan_legacy",
    "player_dna",
}


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in _keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in _keys(child)}
    return set()


def test_steam64_and_numeric_profile_url_convert_to_same_account() -> None:
    numeric = parse_player_identifier("76561198154040957")
    profile = parse_player_identifier(
        "https://steamcommunity.com/profiles/76561198154040957/"
    )
    assert numeric.account_id == 193775229
    assert numeric == profile


def test_steam_vanity_is_parsed_without_spending_history_budget() -> None:
    identifier = parse_player_identifier("https://steamcommunity.com/id/Example_Player")
    assert identifier.account_id == 0
    assert identifier.vanity == "example_player"


def test_vanity_resolver_caches_successful_lookup() -> None:
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={"response": {"success": 1, "steamid": "76561198154040957"}},
        )

    async def run() -> tuple[int, int]:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        resolver = SteamWebResolver("secret", http_client=client)
        first = await resolver.resolve("Example_Player")
        second = await resolver.resolve("example_player")
        await client.aclose()
        return first, second

    first, second = asyncio.run(run())
    assert first == second == 193775229
    assert calls == 1


def _summary(match_id: int, index: int) -> dict[str, int | bool]:
    return {
        "match_id": match_id,
        "start_time": 1_700_000_000 + index * 7_200,
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


def test_free_report_is_summary_only_versioned_and_expiring() -> None:
    history = [_summary(900_100_000 + index, index) for index in range(35)]
    source = MappingSource(
        player={"profile": {"account_id": 42, "personaname": "Fixture player"}},
        matches=history,
        details={},
    )
    repository = InMemoryRepository()
    service = AnalysisService(source, repository=repository, settings=Settings())
    job, _ = asyncio.run(service.create_analysis("42", enqueue=False))
    asyncio.run(service.run_job(job))

    assert job.status == "completed"
    assert job.completed_stages
    assert source.requests == [("player", 42), ("matches", 42)]
    report = repository.get_report(job.report_id or "")
    assert report is not None
    assert report["schema_version"] == "free-dna-report-1.0.0"
    assert report["report_variant"] == "free_dna_report"
    assert report["noindex"] is True
    assert "account_id" not in report
    assert "dna" not in report
    assert "legacy_summary" not in report
    assert report["cost"]["history_requests"] == 1
    assert report["cost"]["detail_requests"] == 0
    assert len(report["dimensions"]) == 8
    assert len(report["pages"]) == 23
    assert {page["id"] for page in report["pages"]} >= {
        "breadth", "role", "adaptability", "activity",
        "orientation", "resilience", "endurance", "rhythm",
    }
    assert report["metadata"]["history_tier"] == "limited"
    assert all(
        key not in report
        for key in ("account_id", "account_id_masked", "source_match_ids", "raw_payload_refs")
    )
    assert not (_keys(report) & _PRIVATE_KEYS)
    assert "account_id" not in str(report["shares"])
    assert "account_id" not in str(report["pages"])

    for card_type in ("dna", "heroes", "final"):
        svg, _ = build_share_svg(report, card_type=card_type, show_name=False, show_avatar=False)
        assert str(42) not in svg
        assert "<svg" in svg

    now = datetime.now(UTC)
    assert repository.purge_expired(now=now + timedelta(days=31)) == 1
    assert repository.get_report(job.report_id or "") is None


def test_public_report_route_sets_noindex_and_returns_strict_free_contract() -> None:
    history = [_summary(900_105_000 + index, index) for index in range(35)]
    source = MappingSource(
        player={"profile": {"account_id": 42, "personaname": "Fixture player"}},
        matches=history,
        details={},
    )
    app = create_app(Settings(), source=source)
    service = app.state.analysis_service
    job, _ = asyncio.run(service.create_analysis("42", enqueue=False))
    asyncio.run(service.run_job(job))

    response = TestClient(app).get(f"/v1/reports/{job.report_id}")

    assert response.status_code == 200
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    body = response.json()
    assert body["schema_version"] == "free-dna-report-1.0.0"
    assert body["report_variant"] == "free_dna_report"
    validate_free_dna_report(body)


def test_free_cache_miss_never_calls_match_details_or_deep_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    history = [_summary(900_110_000 + index, index) for index in range(35)]

    class NoDetailSource(MappingSource):
        async def get_match(self, match_id: int) -> dict[str, object]:
            raise AssertionError(f"Free DNA requested detail match {match_id}")

    source = NoDetailSource(
        player={"profile": {"account_id": 42, "personaname": "Fixture player"}},
        matches=history,
        details={},
    )
    monkeypatch.setattr(
        "app.analysis.service.detect_patterns",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Free DNA invoked Deep Scan pattern detection")
        ),
    )
    service = AnalysisService(source, settings=Settings())
    job, _ = asyncio.run(service.create_analysis("42", enqueue=False))
    asyncio.run(service.run_job(job))

    assert job.status == "completed"
    assert source.requests == [("player", 42), ("matches", 42)]


def test_public_free_report_rejects_internal_and_legacy_fields() -> None:
    history = [_summary(900_120_000 + index, index) for index in range(35)]
    source = MappingSource(
        player={"profile": {"account_id": 42, "personaname": "Fixture player"}},
        matches=history,
        details={},
    )
    repository = InMemoryRepository()
    service = AnalysisService(source, repository=repository, settings=Settings())
    job, _ = asyncio.run(service.create_analysis("42", enqueue=False))
    asyncio.run(service.run_job(job))
    report = repository.get_report(job.report_id or "")
    assert report is not None

    for field in ("dna", "legacy_summary", "player_dna", "raw_matches"):
        invalid = {**report, field: {}}
        with pytest.raises(ValueError):
            validate_free_dna_report(invalid)
    with pytest.raises(ValueError):
        validate_free_dna_report({
            **report,
            "identity": {**report["identity"], "account_id": 42},
        })


def test_public_free_report_sanitizes_identifier_shaped_identity_fields() -> None:
    history = [_summary(900_130_000 + index, index) for index in range(35)]
    source = MappingSource(
        player={
            "profile": {
                "account_id": 42,
                "personaname": "42",
                "avatarfull": "https://steamcommunity.com/profiles/42/avatar",
            }
        },
        matches=history,
        details={},
    )
    repository = InMemoryRepository()
    service = AnalysisService(source, repository=repository, settings=Settings())
    job, _ = asyncio.run(service.create_analysis("42", enqueue=False))
    asyncio.run(service.run_job(job))

    report = repository.get_report(job.report_id or "")
    assert report is not None
    assert report["identity"] == {
        "display_name": "Anonymous player",
        "avatar_url": None,
        "rank_tier": None,
    }


def test_free_history_boundaries_are_29_fail_30_limited_and_60_normal() -> None:
    def run(count: int) -> dict[str, object] | None:
        source = MappingSource(
            player={"profile": {"account_id": 42, "personaname": "Fixture player"}},
            matches=[_summary(901_000_000 + index, index) for index in range(count)],
            details={},
        )
        repository = InMemoryRepository()
        service = AnalysisService(source, repository=repository, settings=Settings())
        job, _ = asyncio.run(service.create_analysis("42", enqueue=False))
        asyncio.run(service.run_job(job))
        return repository.get_report(job.report_id or "") if job.report_id else None

    assert run(29) is None
    limited = run(30)
    normal = run(60)
    assert limited is not None and limited["metadata"]["history_tier"] == "limited"  # type: ignore[index]
    assert normal is not None and normal["metadata"]["history_tier"] == "normal"  # type: ignore[index]
    assert limited["quality"]["partial"] is True  # type: ignore[index]
    assert normal["quality"]["history_tier"] == "normal"  # type: ignore[index]

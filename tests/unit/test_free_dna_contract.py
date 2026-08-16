from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
from app.analysis.service import AnalysisService
from app.analysis.source import MappingSource
from app.core.config import Settings
from app.core.security import parse_player_identifier
from app.identity.steam import SteamWebResolver
from app.share.service import build_share_svg
from app.storage.repository import InMemoryRepository


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
    assert report["dna_report_variant"] == "free_dna_report"
    assert report["cost"]["history_requests"] == 1
    assert report["cost"]["detail_requests"] == 0
    assert len(report["dimensions"]) == 8
    assert len(report["pages"]) == 23
    assert str(42) not in str(report["shares"])
    assert str(42) not in str(report["pages"])

    svg, _ = build_share_svg(report, card_type="final", show_name=False, show_avatar=False)
    assert str(42) not in svg
    assert "<svg" in svg

    now = datetime.now(UTC)
    assert repository.purge_expired(now=now + timedelta(days=31)) == 1
    assert repository.get_report(job.report_id or "") is None

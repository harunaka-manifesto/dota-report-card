import asyncio

import httpx
import pytest
from app.core.config import Settings
from app.core.errors import OpenDotaUnavailable
from app.opendota.client import OpenDotaClient
from app.opendota.parse_client import OpenDotaParseClient


async def test_api_key_is_sent_only_as_a_bearer_header() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"match_id": 1})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenDotaClient(
            Settings(opendota_api_key="fixture-secret"),
            http_client=http_client,
        )
        assert await client.get_match(1) == {"match_id": 1}

    assert len(seen) == 1
    assert "api_key" not in str(seen[0].url)
    assert seen[0].headers["Authorization"] == "Bearer fixture-secret"


async def test_match_history_transport_supports_two_hundred_summary_rows() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[{"match_id": index} for index in range(300)])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenDotaClient(Settings(), http_client=http_client)
        matches = await client.get_matches(42, limit=200)

    assert len(matches) == 200
    assert seen[0].url.params["limit"] == "200"


async def test_default_match_history_request_uses_year_window_without_hidden_limit() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[{"match_id": index} for index in range(1_001)])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenDotaClient(Settings(), http_client=http_client)
        matches = await client.get_matches(42)

    assert len(matches) == 1_001
    assert seen[0].url.params["date"] == "365"
    assert seen[0].url.params["limit"] == "200"


async def test_unbounded_match_history_paginates_past_opendota_page_ceiling() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        offset = int(request.url.params.get("offset", "0"))
        count = 200 if offset == 0 else 2
        return httpx.Response(
            200,
            json=[{"match_id": offset + index + 1} for index in range(count)],
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenDotaClient(Settings(), http_client=http_client)
        matches = await client.get_matches(42)

    assert len(matches) == 202
    assert [request.url.params.get("offset", "0") for request in seen] == ["0", "200"]


async def test_match_history_supports_repeated_projection_parameters() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenDotaClient(Settings(), http_client=http_client)
        await client.get_matches(
            42,
            project=("cluster", "lane", "lane_role", "is_roaming"),
        )

    assert seen[0].url.params.get_list("project") == [
        "cluster",
        "lane",
        "lane_role",
        "is_roaming",
    ]


async def test_v61_summary_history_is_one_physical_projected_request() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[{"match_id": index} for index in range(900)])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenDotaClient(Settings(), http_client=http_client)
        rows = await client.get_summary_history_once(
            42,
            days=365,
            project=("match_id", "hero_id", "duration"),
            provider_limit=10_000,
        )

    assert len(rows) == 900
    assert len(seen) == 1
    assert seen[0].url.params["date"] == "365"
    assert seen[0].url.params["limit"] == "10000"
    assert seen[0].url.params.get_list("project") == ["match_id", "hero_id", "duration"]
    assert "offset" not in seen[0].url.params


async def test_v61_summary_history_does_not_retry_the_physical_request() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"error": "temporary"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenDotaClient(
            Settings(opendota_max_retries=4),
            http_client=http_client,
        )
        with pytest.raises(OpenDotaUnavailable):
            await client.get_summary_history_once(
                42,
                days=365,
                project=("match_id",),
                provider_limit=10_000,
            )

    assert calls == 1


async def test_concurrent_cache_misses_share_one_transport_request() -> None:
    class FakeHttpClient:
        calls = 0

        async def get(self, *_args: object, **_kwargs: object) -> httpx.Response:
            self.calls += 1
            await asyncio.sleep(0)
            return httpx.Response(200, json={"match_id": 1})

    http_client = FakeHttpClient()
    client = OpenDotaClient(Settings(), http_client=http_client)  # type: ignore[arg-type]
    values = await asyncio.gather(client.get_match(1), client.get_match(1))

    assert values == [{"match_id": 1}, {"match_id": 1}]
    assert http_client.calls == 1


def test_transport_has_no_replay_parse_method() -> None:
    assert not hasattr(OpenDotaClient, "request_parse")


async def test_parse_transport_is_explicit_and_separate() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        return httpx.Response(200, json={"job": "ok"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenDotaParseClient(Settings(), http_client=http_client)
        assert await client.request_parse(123) == {"job": "ok"}
        assert await client.get_parse_request("job_1") == {"job": "ok"}

    assert seen == [("POST", "/api/request/123"), ("GET", "/api/request/job_1")]

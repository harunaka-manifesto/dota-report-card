import asyncio

import httpx
from app.core.config import Settings
from app.opendota.client import OpenDotaClient


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


async def test_match_history_transport_caps_limit_at_fifty() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[{"match_id": index} for index in range(100)])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenDotaClient(Settings(), http_client=http_client)
        matches = await client.get_matches(42, limit=200)

    assert len(matches) == 50
    assert seen[0].url.params["limit"] == "50"


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

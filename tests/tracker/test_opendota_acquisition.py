"""Tracker acquisition must not inherit frozen report caching or history filters."""
import httpx
import pytest
from app.core.cache import MemoryCache
from app.core.config import Settings
from app.core.errors import OpenDotaUnavailable
from app.opendota.client import OpenDotaClient


async def test_history_includes_turbo_independent_of_provider_default_and_legacy_cache():
    seen = []
    cache = MemoryCache()
    cache.set("matches:42:365:200:0:", [{"match_id": 999}])

    def handler(request):
        seen.append(request)
        # Simulate the provider changing its default: only explicit inclusion works.
        rows = [{"match_id": 2, "game_mode": 23}, {"match_id": 1, "game_mode": 22}]
        return httpx.Response(200, json=rows if request.url.params.get("significant") == "0" else rows[1:])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenDotaClient(Settings(free_history_limit=1), http_client=http, cache=cache)
        assert len(await client.get_history_page(42, days=90)) == 2
        await client.get_history_page(42, offset=200, limit=50)
    assert len(seen) == 2
    assert dict(seen[0].url.params) == {"significant": "0", "limit": "200", "offset": "0", "date": "90"}
    assert dict(seen[1].url.params) == {"significant": "0", "limit": "50", "offset": "200"}


async def test_refresh_observes_replay_without_changing_legacy_snapshot():
    responses = [{"match_id": 8, "version": None}, {"match_id": 8, "version": 21}]
    cache = MemoryCache()
    cache.set("match:8", responses[0], immutable=True)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=responses[len(calls) - 1])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenDotaClient(Settings(), http_client=http, cache=cache)
        assert (await client.refresh_match(8))["version"] is None
        assert (await client.refresh_match(8))["version"] == 21
        assert (await client.get_match(8))["version"] is None
    assert len(calls) == 2


@pytest.mark.parametrize("payload", [None, {}, [None], [{"match_id": True}], [{"match_id": 0}]])
async def test_malformed_history_is_failure_not_empty_coverage(payload):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))) as http:
        client = OpenDotaClient(Settings(), http_client=http)
        with pytest.raises(OpenDotaUnavailable):
            await client.get_history_page(42)


async def test_job_owned_retry_is_one_physical_attempt_and_wrong_match_is_rejected():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503) if "players" in request.url.path else httpx.Response(200, json={"match_id": 9})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenDotaClient(Settings(opendota_max_retries=4), http_client=http)
        with pytest.raises(OpenDotaUnavailable):
            await client.get_history_page(42)
        with pytest.raises(OpenDotaUnavailable):
            await client.refresh_match(8)
        for kwargs in ({"offset": -1}, {"limit": 201}, {"days": 0}):
            with pytest.raises(ValueError):
                await client.get_history_page(42, **kwargs)
        with pytest.raises(ValueError):
            await client.refresh_match(True)
    assert len(calls) == 2

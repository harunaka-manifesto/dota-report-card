import json

import httpx
import pytest
from app.core.config import Settings
from app.core.errors import ProfileUnavailable, StratzSchemaDrift, StratzUnavailable
from app.stratz.client import StratzClient
from app.stratz.queries import GET_TRACKER_MATCH_BATCH


async def test_explicit_take_all_players_stats_and_coverage_ceiling():
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(200, json={"data": {"player": {"matches": [{"id": i} for i in body["variables"]["matchIds"]]}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = StratzClient(Settings(stratz_api_token="test-only"), http_client=http)
        assert len((await client.get_tracker_match_batch(42, list(range(1, 51))))["player"]["matches"]) == 50
        assert len((await client.get_tracker_match_batch(42, list(range(1, 101)), mixed_coverage=True))["player"]["matches"]) == 100
        for rows, mixed in (([], False), (list(range(1, 52)), False), (list(range(1, 102)), True), ([True], False)):
            with pytest.raises(ValueError):
                await client.get_tracker_match_batch(42, rows, mixed_coverage=mixed)
    assert [r["variables"]["take"] for r in requests] == [50, 100]
    assert all(r["operationName"] == GET_TRACKER_MATCH_BATCH.name for r in requests)
    assert "take: $take" in requests[0]["query"]
    assert "players(steamAccountId" not in requests[0]["query"]
    assert "networthPerMinute" in requests[0]["query"]
    assert "statsDateTime" in requests[0]["query"]
    assert "position\n" not in requests[0]["query"]


@pytest.mark.parametrize("player", [{"matches": [{"id": 99}]}, {"matches": [{"id": 1}, {"id": 1}]}, {"matches": None}])
async def test_invalid_history_cannot_be_mistaken_for_coverage(player):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"data": {"player": player}}))) as http:
        client = StratzClient(Settings(stratz_api_token="test-only"), http_client=http)
        with pytest.raises(StratzSchemaDrift):
            await client.get_tracker_match_batch(42, [1, 2])


async def test_single_attempt_unavailable_distinct_from_empty_source_page():
    results = [httpx.Response(503), httpx.Response(200, json={"data": {"player": None}}), httpx.Response(200, json={"data": {"player": {"matches": []}}})]
    calls = []

    def handler(request):
        calls.append(request)
        return results[len(calls) - 1]

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = StratzClient(Settings(stratz_api_token="test-only", stratz_max_retries=4), http_client=http)
        with pytest.raises(StratzUnavailable):
            await client.get_tracker_match_batch(42, [1])
        with pytest.raises(ProfileUnavailable):
            await client.get_tracker_match_batch(42, [1])
        assert (await client.get_tracker_match_batch(42, [1]))["player"]["matches"] == []
    assert len(calls) == 3

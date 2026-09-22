import asyncio

import httpx
import pytest
from app.core.config import Settings
from app.opendota.client import OpenDotaClient
from app.opendota.parse_client import OpenDotaParseClient
from app.stratz.client import StratzClient
from app.tracker.provider_control import ProviderDeferred, ProviderGate
from app.tracker.provider_transport import ControlledTransport
from app.tracker.schema import provider_calls, snapshots
from sqlalchemy import select


def gate_for(redis_client, provider):
    redis, namespace = redis_client
    gate = ProviderGate(redis, namespace=namespace, provider=provider)
    gate.observe({"x-ratelimit-limit-minute": "100", "x-ratelimit-remaining-minute": "100"}, status=200)
    return gate


async def test_existing_clients_use_shared_admission_persist_raw_and_accounting(database, redis_client):
    gate = gate_for(redis_client, "opendota")
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"match_id": 8, "version": None} if request.method == "GET" else {"job": {"jobId": 15}}, headers={"x-ratelimit-remaining-minute": "70"})

    transport = ControlledTransport(gate, database, transport=httpx.MockTransport(handler))
    async with httpx.AsyncClient(transport=transport) as http:
        read = OpenDotaClient(Settings(), http_client=http)
        parse = OpenDotaParseClient(Settings(), http_client=http)
        assert (await read.refresh_match(8))["version"] is None
        assert (await parse.request_parse(8))["job"]["jobId"] == 15
    with database.connect() as connection:
        calls = connection.execute(select(provider_calls).order_by(provider_calls.c.id)).mappings().all()
        assert [(r["rate_units"], r["billed_units"]) for r in calls] == [(1, 1), (10, 1)]
        evidence = connection.execute(select(snapshots)).mappings().all()
        assert len(evidence) == 2
        assert {r["operation"] for r in evidence} == {"match", "request_replay"}
        assert all(r["subject"] == "match:8" for r in evidence)
    assert len(seen) == 2
    assert all(request.headers["accept-encoding"] == "identity" for request in seen)


async def test_global_stratz_singleflight_and_ip_blocked_response(database, redis_client):
    gate = gate_for(redis_client, "stratz")
    entered, release = asyncio.Event(), asyncio.Event()

    async def handler(_):
        entered.set()
        await release.wait()
        return httpx.Response(403, json={"error": "token bound to a different IP"})

    async with httpx.AsyncClient(transport=ControlledTransport(gate, database, transport=httpx.MockTransport(handler))) as http:
        client = StratzClient(Settings(stratz_api_token="test-only"), http_client=http)
        first = asyncio.create_task(client.get_tracker_match_batch(42, [8]))
        await asyncio.wait_for(entered.wait(), 2)
        with pytest.raises(ProviderDeferred, match="SINGLEFLIGHT_BUSY"):
            await client.get_tracker_match_batch(42, [9])
        release.set()
        result = await asyncio.gather(first, return_exceptions=True)
        assert isinstance(result[0], Exception)
        with pytest.raises(ProviderDeferred, match="CREDENTIAL_OR_IP_BLOCKED"):
            await client.get_tracker_match_batch(42, [10])
    with database.connect() as connection:
        calls = connection.execute(select(provider_calls)).mappings().all()
        assert len(calls) == 1 and calls[0]["failure_code"] == "IP_BINDING"


@pytest.mark.parametrize("kind", ["oversize", "timeout"])
async def test_response_bounds_are_logged_without_snapshot(database, redis_client, kind):
    gate = gate_for(redis_client, "opendota")

    async def handler(_):
        if kind == "timeout":
            await asyncio.sleep(1)
        return httpx.Response(200, content=b"x" * 101)

    transport = ControlledTransport(gate, database, transport=httpx.MockTransport(handler), deadline_seconds=0.1, max_response_bytes=100)
    async with httpx.AsyncClient(transport=transport) as http:
        with pytest.raises(httpx.TransportError):
            await http.get("https://example.invalid/api/matches/8")
    with database.connect() as connection:
        row = connection.execute(select(provider_calls)).mappings().one()
        assert row["failure_code"] == ("DEADLINE_EXCEEDED" if kind == "timeout" else "RESPONSE_TOO_LARGE")
        assert connection.execute(select(snapshots)).first() is None

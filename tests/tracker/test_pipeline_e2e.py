"""Stored-source fresh lifecycle checks, including the isolated mobile projection."""

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from app.core.config import Settings
from app.tracker.authentication import VerifiedIdentity, create_user_session
from app.tracker.mobile_api import create_mobile_app
from app.tracker.schema import (
    account_matches,
    identities,
    ingest_jobs,
    matches,
    profiles,
    provider_calls,
)
from app.tracker.worker import WorkerPolicy, run_one
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from .test_provider_transport import gate_for
from .test_replay_acquisition import due, payload, prepare, run


@pytest.mark.parametrize("parsed", [True, False])
async def test_stage_one_to_terminal_replay_and_mobile_ready(database, redis_client, parsed):
    replay_job = prepare(database)
    with database.begin() as connection:
        link = connection.execute(select(account_matches)).mappings().one()
        profile = connection.execute(select(profiles).where(
            profiles.c.id == link["profile_id"],
        )).mappings().one()
        connection.execute(profiles.update().where(profiles.c.id == profile["id"]).values(
            original_linked_at=link["provider_started_at"],
        ))
        connection.execute(identities.insert().values(
            id=str(uuid4()), user_id=profile["user_id"], issuer="https://accounts.google.com",
            subject="pipeline-owner", verified_at=datetime.now(UTC),
        ))
        ref = link["public_ref"]
    user_id, tokens = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", "pipeline-owner", None,
    ))
    assert user_id == profile["user_id"]
    client = TestClient(create_mobile_app(Settings(), database=database))
    headers = {"Authorization": f"Bearer {tokens.access_token}"}
    stage_one = client.get(f"/matches/{ref}", headers=headers)
    assert stage_one.status_code == 200
    assert stage_one.json()["facts"] == "AVAILABLE"
    assert stage_one.json()["performance"] == "PENDING"
    assert stage_one.json()["item_timings"] == {
        "state": "PENDING", "contract_version": None, "reason": None,
        "reference_digest": None, "items": [],
    }
    assert stage_one.json()["role"] in {"CARRY", "MID", "OFFLANE", "SUPPORT"}
    assert stage_one.json()["metrics"] == []

    gate = gate_for(redis_client, "opendota")
    requests = []

    def response(request):
        requests.append(request.method)
        return httpx.Response(200, json={"job": {"jobId": 15}} if request.method == "POST"
                              else payload(parsed))

    assert await run(database, gate, replay_job, response) == "DEFERRED"
    assert await run(database, gate, due(database), response) == ("COMPLETE" if parsed else "DEFERRED")
    if not parsed:
        assert await run(database, gate, due(database), response) == "COMPLETE"
    redis, namespace = redis_client
    policy = WorkerPolicy(namespace=namespace)
    for _ in range(5):
        if await run_one(database, redis, Settings(), priority=0, policy=policy) == "IDLE":
            break
    with database.connect() as connection:
        assert connection.scalar(select(account_matches.c.lifecycle)) == "READY"
        assert connection.scalar(select(func.count()).select_from(ingest_jobs).where(
            ingest_jobs.c.job_type == "FINALIZE", ingest_jobs.c.state == "COMPLETE",
        )) == 1
        assert connection.scalar(select(matches.c.evidence_state)) == (
            "REPLAY_READY" if parsed else "REPLAY_UNAVAILABLE"
        )
        assert connection.scalar(select(func.count()).select_from(provider_calls)) == len(requests)
    ready = client.get(f"/matches/{ref}", headers=headers)
    assert ready.status_code == 200
    assert ready.json()["lifecycle"] == "READY"
    assert ready.json()["performance"] == "AVAILABLE"
    assert ready.json()["progression"] == "STANDARD"
    assert ready.json()["metrics"]
    timings = ready.json()["item_timings"]
    assert timings["state"] == "AVAILABLE"
    assert timings["contract_version"] == "item-timings-v1"
    assert timings["items"] == sorted(
        timings["items"], key=lambda item: (item["purchase_time_seconds"], item["item_id"]),
    )
    assert all(item["comparison"] is None for item in timings["items"])
    if not parsed:
        assert any(metric["state"] == "NOT_AVAILABLE" for metric in ready.json()["metrics"])
    assert requests == (["POST", "GET"] if parsed else ["POST", "GET", "GET"])

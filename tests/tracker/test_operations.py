import json
from datetime import UTC, datetime

from app.core.config import Settings
from app.tracker.mobile_api import create_mobile_app
from app.tracker.operations import create_operations_app
from app.tracker.schema import provider_calls
from fastapi.testclient import TestClient


def test_operations_requires_separate_secret_and_stays_out_of_mobile_schema(database):
    unavailable = TestClient(create_operations_app(Settings(), database=database))
    assert unavailable.get("/summary").status_code == 503
    app = create_operations_app(Settings(), database=database, token="local-operations-test-token")
    client = TestClient(app)
    assert client.get("/summary").status_code == 401
    with database.begin() as connection:
        connection.execute(provider_calls.insert().values(
            id=1, provider="opendota", operation="match", operation_version="1",
            match_id=101, status=429, latency_ms=25, billed_units=0, rate_units=1,
            called_at=datetime.now(UTC), failure_code="RATE_LIMITED",
        ))
    result = client.get("/summary", headers={
        "X-Tracker-Operations-Token": "local-operations-test-token",
    })
    assert result.status_code == 200
    body = result.json()
    assert len(body["queues"]) == 4
    assert body["providers"] == [{
        "name": "opendota", "operation": "match", "calls": 1, "unique_matches": 1,
        "errors": 1, "rate_limited": 1, "billed_units": 0, "rate_units": 1,
    }]
    assert len(body["latency"]) == 3
    assert "summary" not in create_mobile_app(Settings(), database=database).openapi()["paths"]


def test_operations_reads_shared_circuit_and_pause_state(database, redis_client, monkeypatch):
    redis, namespace = redis_client
    monkeypatch.setenv("TRACKER_NAMESPACE", namespace)
    seconds, micros = redis.time()
    now = seconds + micros / 1_000_000
    redis.set(f"{namespace}:pause:p3", "1")
    redis.set(f"{namespace}:provider:opendota", json.dumps({
        "buckets": {}, "disabled": True, "failure_code": "CREDENTIAL_REJECTED",
    }))
    redis.set(f"{namespace}:provider:stratz", json.dumps({
        "buckets": {}, "open_until": now + 30,
    }))
    client = TestClient(create_operations_app(Settings(), database=database,
                                              redis=redis, token="local-operations-test-token"))
    response = client.get("/summary", headers={"X-Tracker-Operations-Token": "local-operations-test-token"})
    assert response.status_code == 200
    body = response.json()
    assert body["p3_paused"] is True
    assert body["provider_control"][0] == {
        "name": "opendota", "state": "DISABLED", "open_seconds": 0,
        "failure_code": "CREDENTIAL_REJECTED",
    }
    assert body["provider_control"][1]["name"] == "stratz"
    assert body["provider_control"][1]["state"] == "OPEN"
    assert 0 < body["provider_control"][1]["open_seconds"] <= 30

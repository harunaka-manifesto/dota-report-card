import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from app.tracker.provider_control import ProviderDeferred, ProviderGate, call_units


def learn(gate, remaining=100, window="hour"):
    gate.observe({f"x-ratelimit-limit-{window}": "100", f"x-ratelimit-remaining-{window}": str(remaining)}, status=200)


def test_unknown_limits_allow_one_global_probe_and_no_processing(redis_client):
    redis, namespace = redis_client
    gates = [ProviderGate(redis, namespace=namespace, provider="opendota") for _ in range(12)]

    def attempt(gate):
        try:
            gate.acquire()
            return True
        except ProviderDeferred:
            return False

    with ThreadPoolExecutor(12) as pool:
        assert sum(pool.map(attempt, gates)) == 1
    with pytest.raises(ProviderDeferred, match="QUOTA_UNKNOWN"):
        gates[0].acquire(processing=True)


def test_concurrent_reads_cannot_spend_processing_share(redis_client):
    redis, namespace = redis_client
    gate = ProviderGate(redis, namespace=namespace, provider="opendota")
    learn(gate)

    def attempt(_):
        try:
            ProviderGate(redis, namespace=namespace, provider="opendota").acquire()
            return 1
        except ProviderDeferred:
            return 0

    with ThreadPoolExecutor(8) as pool:
        count = sum(pool.map(attempt, range(65)))
    assert count <= 50
    # Fill any reservations deferred by contention; totals must still stop at 50.
    while True:
        try:
            gate.acquire()
            count += 1
        except ProviderDeferred:
            break
    assert count == 50
    for _ in range(4):
        # Fixture moves the pacing deadline past while keeping quota exhausted.
        state = json.loads(redis.get(gate.key))
        state["processing_after"] = 0
        redis.set(gate.key, json.dumps(state))
        gate.acquire(processing=True)
    with pytest.raises(ProviderDeferred, match="PROCESSING_PACED"):
        gate.acquire(processing=True)
    state = json.loads(redis.get(gate.key))
    state["processing_after"] = 0
    redis.set(gate.key, json.dumps(state))
    with pytest.raises(ProviderDeferred, match="QUOTA_EXHAUSTED"):
        gate.acquire(processing=True)
    gate.acquire(processing=True, recovery=True)
    assert json.loads(redis.get(gate.key))["buckets"]["hour"]["total"] < 1


def test_remaining_only_header_tightens_budget_and_failures_open_shared_circuit(redis_client):
    redis, namespace = redis_client
    gate = ProviderGate(redis, namespace=namespace, provider="stratz")
    learn(gate)
    gate.observe({"x-ratelimit-remaining-hour": "0"}, status=200)
    with pytest.raises(ProviderDeferred, match="QUOTA_EXHAUSTED"):
        gate.acquire(recovery=True)
    for _ in range(3):
        gate.observe({}, status=503)
    with pytest.raises(ProviderDeferred, match="CIRCUIT_OPEN"):
        ProviderGate(redis, namespace=namespace, provider="stratz").acquire()
    gate.observe({}, status=403, ip_blocked=True)
    with pytest.raises(ProviderDeferred, match="CREDENTIAL_OR_IP_BLOCKED"):
        gate.acquire()
    assert json.loads(redis.get(gate.key))["failure_code"] == "IP_BINDING"


def test_accounting_distinguishes_rate_from_known_billing():
    assert call_units("opendota", processing=True, status=200) == (10, 1)
    assert call_units("opendota", processing=False, status=200) == (1, 1)
    for status in (404, 429, 500, None):
        assert call_units("opendota", processing=True, status=status) == (10, 0)
    assert call_units("stratz", processing=False, status=200) == (1, 0)


def test_live_remaining_only_header_bootstraps_conservative_capacity(redis_client):
    redis, namespace = redis_client
    gate = ProviderGate(redis, namespace=namespace, provider="opendota")
    gate.acquire()
    # Exact header shape observed in the bounded live check; no limit header.
    gate.observe({"x-rate-limit-remaining-minute": "2999"}, status=200)
    gate.acquire(processing=True)
    state = json.loads(redis.get(gate.key))
    assert state["buckets"]["minute"]["limit"] == 2999
    assert state["buckets"]["minute"]["total"] < 2990

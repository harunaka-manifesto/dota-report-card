"""Goal §11.2 / §17 end-to-end matrix on real PostgreSQL and Redis.

The fresh chain runs through the production worker entry point (`run_one`)
with only the provider HTTP replaced by a deterministic mock: foreground sync →
shared summary → private links → one shared replay path → ordered private
finalization → mobile read.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import httpx
from app.core.config import Settings
from app.tracker.authentication import VerifiedIdentity, create_user_session
from app.tracker.finalization import complete_finalization_job, enqueue_finalization
from app.tracker.jobs import claim
from app.tracker.materialization import materialize_snapshot
from app.tracker.mobile_api import create_mobile_app
from app.tracker.provider_control import ProviderGate
from app.tracker.rebuild import (
    complete_readmit_job,
    complete_scope_rebuild_job,
    enqueue_readmissions,
)
from app.tracker.schema import (
    account_matches,
    acquisitions,
    analyses,
    bootstrap,
    dota_accounts,
    events,
    ingest_jobs,
    match_players,
    matches,
    metric_observations,
    notification_outbox,
    profiles,
    provider_calls,
    sync_state,
)
from app.tracker.sync import request_account_sync
from app.tracker.worker import WorkerPolicy, run_one
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select, update

from .builders import add_match, finalize, history
from .test_entitlement import NOW, ready_bootstrap, transaction
from .test_materialization import raw, save
from .test_schema import identity

HEADERS = {"x-rate-limit-remaining-minute": "3000", "x-rate-limit-limit-minute": "3000"}
LINKED = datetime(2026, 9, 1, tzinfo=UTC)


class FakeOpenDota:
    """Unparsed until a processing request is accepted; parsed afterwards."""

    def __init__(self, history: dict[int, list[dict]], matches: dict[int, dict]):
        self.history, self.matches, self.requested = history, matches, set()
        self.calls: list[tuple[str, str]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append((request.method, path))
        if path.startswith("/api/players/"):
            account = int(path.split("/")[3])
            rows = self.history.get(account, []) if int(request.url.params.get("offset", 0)) == 0 else []
            return httpx.Response(200, json=rows, headers=HEADERS)
        match_id = int(path.rsplit("/", 1)[1])
        if request.method == "POST":
            self.requested.add(match_id)
            return httpx.Response(200, json={"job": {"jobId": match_id % 1000}}, headers=HEADERS)
        body = json.loads(json.dumps(self.matches[match_id]))
        if match_id not in self.requested:
            body["version"] = None
        return httpx.Response(200, json=body, headers=HEADERS)


def _owner(database, subject: str, account_id: int) -> tuple[str, str]:
    user_id, tokens = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", subject, None))
    profile_id = f"e2e-{subject}"
    with database.begin() as connection:
        connection.execute(insert(dota_accounts).values(account_id=account_id))
        connection.execute(profiles.insert().values(id=profile_id, user_id=user_id, account_id=account_id,
                                                    active=True, original_linked_at=LINKED))
    ready_bootstrap(database, profile_id)
    return profile_id, tokens.access_token


def _due(database) -> None:
    with database.begin() as connection:
        now = connection.execute(select(func.clock_timestamp())).scalar_one()
        for row in connection.execute(select(ingest_jobs).where(ingest_jobs.c.state == "PENDING")).mappings().all():
            cursor = dict(row["cursor"] or {})
            if "next_poll_at" in cursor:
                cursor["next_poll_at"] = (now - timedelta(seconds=1)).isoformat()
            connection.execute(update(ingest_jobs).where(ingest_jobs.c.id == row["id"])
                               .values(run_after=now - timedelta(seconds=1), cursor=cursor))


async def _drain(database, redis_client, transport, rounds: int = 12) -> None:
    redis, namespace = redis_client
    policy = WorkerPolicy(namespace=namespace)
    for gate_provider in ("opendota", "stratz"):
        ProviderGate(redis, namespace=namespace, provider=gate_provider).observe(HEADERS, status=200)
    for _ in range(rounds):
        _due(database)
        progressed = False
        for priority in range(4):
            for _step in range(20):
                outcome = await run_one(database, redis, Settings(), priority=priority, policy=policy,
                                        transport=transport)
                if outcome == "IDLE" or outcome in {"OPERATOR_PAUSED", "PROVIDER_BUDGET", "P1_DEPTH", "P1_AGE",
                                                    "P2_REDUCED_SHARE"}:
                    break
                progressed = True
        if not progressed:
            return


async def test_fresh_chain_two_owners_one_match_turbo_and_stage_one(database, redis_client):
    first, first_token = _owner(database, "first", 1001)
    second, second_token = _owner(database, "second", 1002)
    standard, turbo = raw(), raw()
    standard["match_id"], turbo["match_id"] = 9_300_000_001, 9_300_000_002
    turbo["game_mode"], turbo["start_time"] = 23, standard["start_time"] + 7200
    for payload in (standard, turbo):
        payload["players"][0]["account_id"] = 1001
        payload["players"][1]["account_id"] = 1002
    rows = [{"match_id": m["match_id"], "start_time": m["start_time"], "game_mode": m["game_mode"]}
            for m in (turbo, standard)]
    fake = FakeOpenDota({1001: rows, 1002: rows}, {m["match_id"]: m for m in (standard, turbo)})
    transport = httpx.MockTransport(fake)

    with database.begin() as connection:
        request_account_sync(connection, 1001, scope_days=40)
        request_account_sync(connection, 1002, scope_days=40)
        assert request_account_sync(connection, 1001, scope_days=40) is not None  # merged, not duplicated
    # Stage 1 only: run discovery, summary and link lanes, not replay/finalization.
    redis, namespace = redis_client
    ProviderGate(redis, namespace=namespace, provider="opendota").observe(HEADERS, status=200)
    policy = WorkerPolicy(namespace=namespace)
    for _ in range(30):
        _due(database)
        if await run_one(database, redis, Settings(), priority=0, policy=policy, transport=transport) == "IDLE":
            break
    client = TestClient(create_mobile_app(Settings(), database=database))
    auth = {"Authorization": f"Bearer {first_token}"}
    rows = client.get("/history?mode=STANDARD", headers=auth).json()["matches"]
    assert len(rows) == 1 and rows[0]["lifecycle"] == "WAITING_FOR_DATA"
    stage_one = client.get(f"/matches/{rows[0]['ref']}", headers=auth).json()
    assert stage_one["facts"] == "AVAILABLE" and len(stage_one["players"]) == 10
    assert stage_one["performance"] == "PENDING" and stage_one["role"] in {"CARRY", "MID", "OFFLANE", "SUPPORT"}
    assert stage_one["metrics"] == []
    assert stage_one["item_timings"]["state"] == "PENDING"

    await _drain(database, redis_client, transport)
    with database.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(matches)) == 2
        assert connection.scalar(select(func.count()).select_from(match_players)) == 20
        assert connection.scalar(select(func.count()).select_from(account_matches)) == 4
        assert set(connection.scalars(select(account_matches.c.lifecycle))) == {"READY"}
        assert set(connection.scalars(select(matches.c.evidence_state))) == {"REPLAY_READY"}
        replay_jobs = connection.scalar(select(func.count()).select_from(ingest_jobs).where(
            ingest_jobs.c.job_type == "REPLAY"))
        assert replay_jobs == 2  # one shared path per match, never per owner or per tier
        assert connection.scalar(select(func.count()).select_from(provider_calls)) == len(fake.calls)
        modes = dict(connection.execute(select(account_matches.c.match_id, account_matches.c.progression).where(
            account_matches.c.profile_id == first)).all())
        assert modes == {standard["match_id"]: "STANDARD", turbo["match_id"]: "TURBO"}
    posts = [path for method, path in fake.calls if method == "POST"]
    assert sorted(posts) == sorted({path for path in posts}) and len(posts) == 2
    summary_reads = [path for method, path in fake.calls if method == "GET" and "/matches/" in path]
    # One unparsed Stage-1 read per match plus at least one parsed read; never per owner.
    assert len(summary_reads) <= 2 * 3

    for token in (first_token, second_token):
        headers = {"Authorization": f"Bearer {token}"}
        for mode in ("STANDARD", "TURBO"):
            [match] = client.get(f"/history?mode={mode}", headers=headers).json()["matches"]
            detail = client.get(f"/matches/{match['ref']}", headers=headers).json()
            assert detail["lifecycle"] == "READY" and detail["performance"] == "AVAILABLE"
            assert detail["progression"] == mode and detail["metrics"]
            assert detail["item_timings"]["state"] == "AVAILABLE"
            assert detail["item_timings"]["contract_version"] == "item-timings-v1"
    # Duplicate foreground syncs after READY only re-read history; nothing else repeats.
    before = len(fake.calls)
    with database.begin() as connection:
        connection.execute(update(sync_state).values(retry_after=None))
        request_account_sync(connection, 1001, scope_days=40)
    await _drain(database, redis_client, transport)
    assert all("/players/" in path for _, path in fake.calls[before:])
    with database.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(analyses)) == 4
        assert connection.scalar(select(func.count()).select_from(events).where(events.c.kind == "MATCH_READY")) == 4


def test_live_match_during_unsettled_bootstrap_defers_only_its_mode(database):
    _, profile_id = identity(database)
    ready_bootstrap(database, profile_id)
    with database.begin() as connection:
        connection.execute(update(bootstrap).where(bootstrap.c.mode == "STANDARD").values(
            completed_at=None, outcome=None, settled_count=0, search_finished=False))
    standard = add_match(database, profile_id, index=1)
    turbo = add_match(database, profile_id, index=2, turbo=True)
    assert finalize(database, profile_id, standard) == "WAITING_FOR_PRIOR_MATCH"
    assert finalize(database, profile_id, turbo) == "READY"
    with database.connect() as connection:
        link = connection.execute(select(account_matches).where(account_matches.c.match_id == standard)).mappings().one()
    assert link["lifecycle"] == "WAITING_FOR_PRIOR_MATCH" and link["active_analysis_id"] is None


def test_stale_unparsed_response_never_regresses_replay_evidence(database):
    _, profile_id = identity(database)
    match_id = add_match(database, profile_id, index=3)
    stale = raw()
    stale["match_id"], stale["version"] = match_id, None
    stale["players"][0]["account_id"] = 1001
    with database.connect() as connection:
        stale["start_time"] = int(connection.scalar(select(matches.c.started_at).where(
            matches.c.match_id == match_id)).timestamp())
    with database.begin() as connection:
        # A stale unparsed observation arrives after the parsed one was retained.
        snapshot_id = save(connection, stale)
        materialize_snapshot(connection, snapshot_id=snapshot_id, match_id=match_id)
    assert finalize(database, profile_id, match_id) == "READY"
    with database.connect() as connection:
        assert connection.scalar(select(matches.c.evidence_state).where(matches.c.match_id == match_id)) == "REPLAY_READY"
        measured = connection.scalar(select(func.count()).select_from(metric_observations).where(
            metric_observations.c.raw_value.is_not(None)))
    assert measured >= 3  # replay-class metrics came from the parsed projection


def test_late_replay_recovery_readmits_silently_without_celebration(database):
    _, profile_id = identity(database)
    ids = history(database, profile_id, [0, 1, 2, 3, 4, 5])
    late = add_match(database, profile_id, index=20)
    with database.begin() as connection:
        connection.execute(update(matches).where(matches.c.match_id == late).values(
            evidence_state="REPLAY_UNAVAILABLE", terminal_reason="REPLAY_CHECKS_EXHAUSTED",
            replay_role_assignment=None))
        # Replay evidence was never obtained on the fresh path.
        connection.execute(update(acquisitions).where(acquisitions.c.match_id == late).values(
            state="REPLAY_UNAVAILABLE"))
    assert finalize(database, profile_id, late) == "READY"
    with database.connect() as connection:
        before = connection.execute(select(metric_observations.c.metric_id, metric_observations.c.raw_value).join(
            account_matches, account_matches.c.active_analysis_id == metric_observations.c.analysis_id).where(
            account_matches.c.match_id == late)).all()
        events_before = connection.scalar(select(func.count()).select_from(events))
        outbox_before = connection.scalar(select(func.count()).select_from(notification_outbox))
    assert any(value is None for _, value in before)
    # Historical re-admission: the one allowed backward evidence transition.
    with database.begin() as connection:
        connection.execute(update(matches).where(matches.c.match_id == late).values(
            evidence_state="REPLAY_READY", terminal_reason=None))
        connection.execute(update(acquisitions).where(acquisitions.c.match_id == late).values(
            state="REPLAY_READY"))
        [job_id] = enqueue_readmissions(connection, late)
        job = claim(connection, priority=3)
    assert job["id"] == job_id
    assert complete_readmit_job(database, job_id=job["id"], lease_token=job["lease_token"]) == "READMITTED"
    with database.connect() as connection:
        after = dict(connection.execute(select(metric_observations.c.metric_id, metric_observations.c.raw_value).join(
            account_matches, account_matches.c.active_analysis_id == metric_observations.c.analysis_id).where(
            account_matches.c.match_id == late)).all())
        assert sum(value is not None for value in after.values()) > sum(value is not None for _, value in before)
        assert connection.scalar(select(func.count()).select_from(events)) == events_before
        assert connection.scalar(select(func.count()).select_from(notification_outbox)) == outbox_before
        assert connection.scalar(select(account_matches.c.lifecycle).where(account_matches.c.match_id == late)) == "READY"
    assert ids


def test_provider_outage_leaves_stored_product_data_readable(database, redis_client):
    from app.tracker.authentication import VerifiedIdentity as Identity

    user_id, tokens = create_user_session(database, Identity("google", "https://accounts.google.com", "outage", None))
    with database.begin() as connection:
        connection.execute(insert(dota_accounts).values(account_id=1001))
        connection.execute(profiles.insert().values(id="outage-profile", user_id=user_id, account_id=1001,
                                                    active=True, original_linked_at=LINKED))
    ready_bootstrap(database, "outage-profile")
    history(database, "outage-profile", [0, 1])
    redis, namespace = redis_client
    gate = ProviderGate(redis, namespace=namespace, provider="opendota")
    for _ in range(10):
        gate.observe({}, status=503)
    client = TestClient(create_mobile_app(Settings(), database=database))
    headers = {"Authorization": f"Bearer {tokens.access_token}"}
    listed = client.get("/history?mode=STANDARD", headers=headers)
    assert listed.status_code == 200 and len(listed.json()["matches"]) == 2
    for match in listed.json()["matches"]:
        assert client.get(f"/matches/{match['ref']}", headers=headers).json()["lifecycle"] == "READY"
    assert client.get("/profile?mode=STANDARD", headers=headers).status_code == 200


def test_scope_rebuild_during_in_flight_enrichment_publishes_one_coherent_timeline(database):
    from app.tracker.entitlement import (
        FakeAppStoreVerifier,
        reconcile_entitlement_scope,
        submit_transaction,
    )

    user_id, profile_id = identity(database)
    ready_bootstrap(database, profile_id)
    history(database, profile_id, [0, 1, 2], origin="HISTORICAL", offset_days=[-9, -8, -7])
    settled = history(database, profile_id, [0], start=10)
    in_flight = add_match(database, profile_id, index=11, offset_days=12)
    with database.begin() as connection:
        connection.execute(update(matches).where(matches.c.match_id == in_flight).values(
            evidence_state="REPLAY_PENDING", replay_role_assignment=None))
        connection.execute(update(account_matches).where(account_matches.c.match_id == in_flight).values(
            lifecycle="WAITING_FOR_PROVIDER"))
    verifier = FakeAppStoreVerifier({"transaction:pro": transaction(user_id, token="pro")})
    submit_transaction(database, user_id=user_id, signed_transaction="pro", verifier=verifier, now=NOW)
    reconcile_entitlement_scope(database, user_id=user_id, now=NOW)
    with database.begin() as connection:
        connection.execute(update(ingest_jobs).where(ingest_jobs.c.job_type == "SCOPE_REBUILD")
                           .values(run_after=func.clock_timestamp() - timedelta(days=1)))
        job = claim(connection, priority=3)
    assert complete_scope_rebuild_job(database, job_id=job["id"], lease_token=job["lease_token"]) == "COMPLETE"
    with database.begin() as connection:
        connection.execute(update(matches).where(matches.c.match_id == in_flight).values(
            evidence_state="REPLAY_READY", replay_terminal_at=func.clock_timestamp()))
        enqueue_finalization(connection, profile_id=profile_id, match_id=in_flight)
        job = claim(connection, priority=0)
    assert complete_finalization_job(database, job_id=job["id"], lease_token=job["lease_token"]) == "READY"
    with database.connect() as connection:
        snapshots_by_match = dict(connection.execute(select(
            account_matches.c.match_id, metric_observations.c.baseline_snapshot).join(
            metric_observations, metric_observations.c.analysis_id == account_matches.c.active_analysis_id).where(
            metric_observations.c.metric_id == "support.camps_stacked.v1",
            account_matches.c.match_id.in_([settled[0], in_flight]))).all())
    # Both post-link matches now see the pre-link history: one Pro timeline, no mixture.
    assert snapshots_by_match[settled[0]]["prior_count"] == 3
    assert snapshots_by_match[in_flight]["prior_count"] == 4

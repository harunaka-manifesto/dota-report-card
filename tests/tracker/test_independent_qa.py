"""Independent QA regressions (2026-09-25).

Each test reproduces a defect found by adversarial review and drives the real
entry points (mobile HTTP, `worker.run_one`, job handlers) with only provider
HTTP replaced by deterministic fakes. No live provider call is reachable.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import httpx
from app.core.config import Settings
from app.tracker.authentication import VerifiedIdentity, create_user_session
from app.tracker.mobile_api import create_mobile_app
from app.tracker.schema import (
    account_discoveries,
    account_matches,
    dota_accounts,
    events,
    profiles,
    sync_state,
)
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select, update

from .test_e2e_matrix import HEADERS, _drain
from .test_entitlement import ready_bootstrap
from .test_materialization import raw


class WindowedOpenDota:
    """History honours the `date` window like OpenDota; matches are parsed on first read."""

    def __init__(self, account_id: int, payloads: list[dict]):
        self.account_id = account_id
        self.matches = {payload["match_id"]: payload for payload in payloads}
        self.history_days: list[int] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.startswith("/api/players/"):
            days = int(request.url.params["date"])
            self.history_days.append(days)
            floor = datetime.now(UTC).timestamp() - days * 86400
            rows = [] if int(request.url.params.get("offset", 0)) else [
                {"match_id": m["match_id"], "start_time": m["start_time"], "game_mode": m["game_mode"]}
                for m in sorted(self.matches.values(), key=lambda m: -m["start_time"])
                if m["start_time"] > floor]
            return httpx.Response(200, json=rows, headers=HEADERS)
        if request.method == "POST":
            return httpx.Response(200, json={"job": {"jobId": 1}}, headers=HEADERS)
        match_id = int(path.rsplit("/", 1)[1])
        return httpx.Response(200, json=json.loads(json.dumps(self.matches[match_id])), headers=HEADERS)


def _match(match_id: int, started: datetime, account_id: int) -> dict:
    payload = raw()
    payload["match_id"], payload["start_time"] = match_id, int(started.timestamp())
    payload["players"][0]["account_id"] = account_id
    return payload


def _linked_owner(database, subject: str, account_id: int, linked_at: datetime) -> tuple[str, str]:
    user_id, tokens = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", subject, None))
    profile_id = f"qa-{subject}"
    with database.begin() as connection:
        connection.execute(insert(dota_accounts).values(account_id=account_id))
        connection.execute(profiles.insert().values(id=profile_id, user_id=user_id, account_id=account_id,
                                                    active=True, original_linked_at=linked_at))
    ready_bootstrap(database, profile_id)
    return profile_id, tokens.access_token


def _sync(client: TestClient, token: str, key: str) -> None:
    response = client.post("/sync", headers={"Authorization": f"Bearer {token}", "Idempotency-Key": key})
    assert response.status_code == 200 and response.json()["accepted"] is True


async def test_foreground_sync_never_links_pre_link_matches_as_live(database, redis_client):
    """QA-1: the 7-day foreground window reached before the link date and created LIVE links.

    A pre-link match is bootstrap/historical territory. Linked as LIVE it was
    hidden from Free History (scope admits BOOTSTRAP or post-link only), still
    produced a READY event/push, and pre-empted the bootstrap link.
    """
    now = datetime.now(UTC)
    linked_at = now - timedelta(days=1)
    profile_id, token = _linked_owner(database, "pre-link", 1001, linked_at)
    before = _match(9_400_000_001, now - timedelta(days=3), 1001)
    after = _match(9_400_000_002, now - timedelta(hours=6), 1001)
    transport = httpx.MockTransport(WindowedOpenDota(1001, [before, after]))
    client = TestClient(create_mobile_app(Settings(), database=database))
    _sync(client, token, "sync-pre-link-1")
    await _drain(database, redis_client, transport)
    with database.connect() as connection:
        links = dict(connection.execute(select(account_matches.c.match_id, account_matches.c.origin).where(
            account_matches.c.profile_id == profile_id)).all())
        ready = set(connection.scalars(select(events.c.payload["match_id"].astext).where(
            events.c.profile_id == profile_id, events.c.kind == "MATCH_READY")))
    assert links == {after["match_id"]: "LIVE"}
    assert ready == {str(after["match_id"])}


async def test_foreground_sync_discovers_everything_since_the_last_authoritative_boundary(database, redis_client):
    """QA-2: discovery used a fixed 7-day window, so a player away longer lost matches forever.

    App foundation §4.1: discovery MUST find all missed source items in scope,
    and the cursor advances only after the durable boundary.
    """
    now = datetime.now(UTC)
    profile_id, token = _linked_owner(database, "away", 1001, now - timedelta(days=30))
    missed = _match(9_400_000_011, now - timedelta(days=12), 1001)
    fake = WindowedOpenDota(1001, [missed])
    client = TestClient(create_mobile_app(Settings(), database=database))
    _sync(client, token, "sync-away-1")
    await _drain(database, redis_client, httpx.MockTransport(fake))
    with database.connect() as connection:
        linked = set(connection.scalars(select(account_matches.c.match_id).where(
            account_matches.c.profile_id == profile_id)))
        rejected = connection.scalar(select(func.count()).select_from(account_discoveries).where(
            account_discoveries.c.reason == "OUTSIDE_SYNC_WINDOW"))
        through = connection.scalar(select(sync_state.c.cursor)).get("complete_through")
    assert linked == {missed["match_id"]} and rejected == 0 and through is not None

    # The next window starts from the recorded boundary, not from "7 days ago".
    later = _match(9_400_000_012, now - timedelta(days=9), 1001)
    fake.matches[later["match_id"]] = later
    with database.begin() as connection:
        connection.execute(update(sync_state).values(
            retry_after=None, cursor={"complete_through": (now - timedelta(days=10)).isoformat()}))
    _sync(client, token, "sync-away-2")
    await _drain(database, redis_client, httpx.MockTransport(fake))
    with database.connect() as connection:
        linked = set(connection.scalars(select(account_matches.c.match_id).where(
            account_matches.c.profile_id == profile_id)))
    assert later["match_id"] in linked
    assert min(fake.history_days[-1:]) >= 11


def _steam_owner(database, subject: str, account_id: int, linked_at: datetime) -> tuple[str, str]:
    from app.tracker.steam_identity import attach_verified_steam_profile

    user_id, tokens = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", subject, None))
    profile_id = attach_verified_steam_profile(database, user_id=user_id, account_id=account_id, now=linked_at)
    return profile_id, tokens.access_token


async def test_terminal_historical_batch_failure_settles_bootstrap_through_summary_fallback(database, redis_client):
    """QA-3: a bootstrap batch that failed terminally left its candidates unsettled forever.

    Here STRATZ is unusable (no token, as in the current deployment gate): every
    batch attempt raised an uncaught provider error until the job FAILED. The
    mode never settled, so every live match of that mode waited forever. The
    retained-evidence route must fall back to the per-match summary source.
    """
    from app.tracker.schema import bootstrap, ingest_jobs

    now = datetime.now(UTC)
    linked_at = now - timedelta(days=1)
    profile_id, token = _steam_owner(database, "batch-failure", 1001, linked_at)
    imported = _match(9_400_000_021, linked_at - timedelta(days=2), 1001)
    live = _match(9_400_000_022, now - timedelta(hours=6), 1001)
    fake = WindowedOpenDota(1001, [imported, live])
    client = TestClient(create_mobile_app(Settings(), database=database))
    _sync(client, token, "sync-batch-failure")
    await _drain(database, redis_client, httpx.MockTransport(fake), rounds=40)
    with database.connect() as connection:
        batch = connection.execute(select(ingest_jobs.c.state, ingest_jobs.c.last_error).where(
            ingest_jobs.c.job_type == "HISTORICAL_BATCH")).all()
        outcome = dict(connection.execute(select(bootstrap.c.mode, bootstrap.c.outcome)).all())
        links = {row.match_id: (row.origin, row.lifecycle) for row in connection.execute(select(
            account_matches.c.match_id, account_matches.c.origin, account_matches.c.lifecycle).where(
            account_matches.c.profile_id == profile_id))}
    assert [state for state, _ in batch] == ["FAILED"]
    assert outcome["STANDARD"] in {"READY", "READY_WITH_GAPS"} and outcome["TURBO"] == "NO_MATCHES_FOUND"
    assert links == {imported["match_id"]: ("BOOTSTRAP", "READY"), live["match_id"]: ("LIVE", "READY")}


async def _fail_bootstrap_search(database, redis_client, attempts: int = 5) -> None:
    from app.tracker.bootstrap import search_bootstrap_page
    from app.tracker.jobs import claim
    from app.tracker.provider_control import ProviderGate
    from app.tracker.schema import ingest_jobs

    redis, namespace = redis_client
    gate = ProviderGate(redis, namespace=namespace, provider="opendota")
    outage = httpx.MockTransport(lambda request: httpx.Response(502, json={}, headers=HEADERS))
    for _ in range(attempts):
        gate.observe(HEADERS, status=200)  # keep the breaker closed: count real attempts only
        with database.begin() as connection:
            connection.execute(update(ingest_jobs).where(ingest_jobs.c.job_type == "BOOTSTRAP_SEARCH").values(
                run_after=func.clock_timestamp() - timedelta(seconds=1)))
            job = claim(connection, priority=3)
        assert job is not None and job["job_type"] == "BOOTSTRAP_SEARCH"
        await search_bootstrap_page(database, gate, Settings(), job_id=job["id"], lease_token=job["lease_token"],
                                    transport=outage)


async def test_failed_bootstrap_search_resumes_on_the_next_foreground_trigger(database, redis_client):
    """QA-4: a bootstrap search that exhausted its retries stayed FAILED forever.

    Onboarding §5.3: temporary retries keep bootstrap non-terminal; live work of
    each mode waits for it (§15). With no path back, every live match waited in
    WAITING_FOR_PRIOR_MATCH permanently. The next app open must resume it.
    """
    from app.tracker.schema import bootstrap, ingest_jobs

    now = datetime.now(UTC)
    linked_at = now - timedelta(days=1)
    profile_id, token = _steam_owner(database, "search-failure", 1001, linked_at)
    await _fail_bootstrap_search(database, redis_client)
    with database.connect() as connection:
        assert connection.scalar(select(ingest_jobs.c.state).where(
            ingest_jobs.c.job_type == "BOOTSTRAP_SEARCH")) == "FAILED"
    live = _match(9_400_000_031, now - timedelta(hours=6), 1001)
    client = TestClient(create_mobile_app(Settings(), database=database))
    _sync(client, token, "sync-after-outage")
    await _drain(database, redis_client, httpx.MockTransport(WindowedOpenDota(1001, [live])), rounds=20)
    with database.connect() as connection:
        outcome = dict(connection.execute(select(bootstrap.c.mode, bootstrap.c.outcome)).all())
        lifecycle = connection.scalar(select(account_matches.c.lifecycle).where(
            account_matches.c.profile_id == profile_id))
    assert outcome == {"STANDARD": "NO_MATCHES_FOUND", "TURBO": "NO_MATCHES_FOUND"}
    assert lifecycle == "READY"


async def test_rediscovery_resumes_an_exhausted_fresh_summary(database, redis_client):
    """QA-5: a SUMMARY job that exhausted its retries was never retried again.

    The match stayed DISCOVERED with no link, and every later discovery merged
    into the FAILED job (dedup key `summary:<match_id>`), so the match was lost
    for every owner. Re-discovery on the next foreground sync must resume it.
    """
    from app.tracker.acquisition import acquire_fresh_summary
    from app.tracker.jobs import claim
    from app.tracker.provider_control import ProviderGate
    from app.tracker.schema import ingest_jobs

    now = datetime.now(UTC)
    profile_id, token = _linked_owner(database, "summary-outage", 1001, now - timedelta(days=2))
    live = _match(9_400_000_041, now - timedelta(hours=6), 1001)
    good = httpx.MockTransport(WindowedOpenDota(1001, [live]))
    client = TestClient(create_mobile_app(Settings(), database=database))
    _sync(client, token, "sync-summary-1")
    redis, namespace = redis_client
    gate = ProviderGate(redis, namespace=namespace, provider="opendota")
    gate.observe(HEADERS, status=200)
    from app.tracker.worker import WorkerPolicy, run_one
    # The first history page journals the match and queues its shared summary.
    assert await run_one(database, redis, Settings(), priority=0, policy=WorkerPolicy(namespace=namespace),
                         transport=good) == "DEFERRED"
    outage = httpx.MockTransport(lambda request: httpx.Response(502, json={}, headers=HEADERS))
    for _ in range(5):
        gate.observe(HEADERS, status=200)
        with database.begin() as connection:
            connection.execute(update(ingest_jobs).where(ingest_jobs.c.job_type == "SUMMARY").values(
                run_after=func.clock_timestamp() - timedelta(seconds=1)))
            job = claim(connection, priority=connection.scalar(select(ingest_jobs.c.priority).where(
                ingest_jobs.c.job_type == "SUMMARY")))
        await acquire_fresh_summary(database, gate, Settings(), job_id=job["id"], lease_token=job["lease_token"],
                                    transport=outage)
    await _drain(database, redis_client, good, rounds=5)  # the first discovery completes
    with database.begin() as connection:
        assert connection.scalar(select(ingest_jobs.c.state).where(ingest_jobs.c.job_type == "SUMMARY")) == "FAILED"
        assert connection.scalar(select(sync_state.c.state)) == "UP_TO_DATE"
        connection.execute(update(sync_state).values(retry_after=None))
    _sync(client, token, "sync-summary-2")
    await _drain(database, redis_client, good, rounds=20)
    with database.connect() as connection:
        lifecycle = connection.scalar(select(account_matches.c.lifecycle).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == live["match_id"]))
    assert lifecycle == "READY"


def test_changes_cursor_never_skips_a_change_committed_after_the_read(database):
    """QA-6: `/changes` returned `clock_timestamp()` as its cursor.

    `updated_at` is stamped when a row is written, not when the transaction
    commits. A finalization that wrote before the read but committed after it
    fell behind the returned cursor and was never reported (no full refresh).
    """
    from .builders import add_match

    now = datetime.now(UTC)
    profile_id, token = _linked_owner(database, "changes", 1001, now - timedelta(days=5))
    match_id = add_match(database, profile_id, index=1, offset_days=1)
    client = TestClient(create_mobile_app(Settings(), database=database))
    auth = {"Authorization": f"Bearer {token}"}
    first = client.get("/changes", headers=auth).json()
    assert first["full_refresh"] is True
    with database.connect() as writer:
        transaction = writer.begin()
        writer.execute(update(account_matches).where(account_matches.c.match_id == match_id).values(
            lifecycle="WAITING_FOR_PRIOR_MATCH"))
        during = client.get("/changes", headers=auth, params={"after": first["cursor"]}).json()
        assert during["changed_refs"] == []  # not committed yet
        transaction.commit()
    after = client.get("/changes", headers=auth, params={"after": during["cursor"]}).json()
    ref = TestClient(create_mobile_app(Settings(), database=database)).get(
        "/history", headers=auth).json()["matches"][0]["ref"]
    assert after["full_refresh"] is False and after["changed_refs"] == [ref]


def test_out_of_order_store_notification_cannot_bypass_the_free_foundation_gate(database):
    """QA-7: a stale (older-signed) store update requested PRO while bootstrap was unsettled.

    The current-update path withholds PRO until both Free modes settle; the
    stale-update path skipped that gate and queued an ENTITLEMENT_REBUILD to PRO.
    """
    from app.tracker.entitlement import FakeAppStoreVerifier, apply_notification, submit_transaction
    from app.tracker.schema import history_operations

    from .test_entitlement import NOW, transaction
    from .test_schema import identity

    user_id, profile_id = identity(database)
    newer = transaction(user_id, token="renewal", signed=NOW + timedelta(hours=1))
    older = transaction(user_id, token="purchase", signed=NOW)
    verifier = FakeAppStoreVerifier({"transaction:renewal": newer, "notification:purchase": older})
    first = submit_transaction(database, user_id=user_id, signed_transaction="renewal", verifier=verifier, now=NOW)
    assert first["desired_scope"] == "FREE" and first["operation_id"] is None
    late = apply_notification(database, signed_notification="purchase", verifier=verifier, now=NOW)
    with database.connect() as connection:
        operations = connection.execute(select(history_operations.c.target_scope).where(
            history_operations.c.profile_id == profile_id)).scalars().all()
    assert late["stale"] is True and late["operation_id"] is None and operations == []


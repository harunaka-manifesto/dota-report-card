"""Owner decisions on the independent QA doubts (2026-09-25).

Each test drives the real job handlers with only provider HTTP replaced by
deterministic fakes; nothing here reaches a provider.
"""
from __future__ import annotations

from datetime import timedelta

from app.core.config import Settings
from app.tracker.jobs import claim
from app.tracker.rebuild import complete_readmit_job, enqueue_readmissions
from app.tracker.schema import (
    account_matches,
    acquisitions,
    events,
    ingest_jobs,
    matches,
    metric_observations,
    notification_outbox,
)
from sqlalchemy import func, select, update

from .builders import add_match, finalize, history
from .test_schema import identity


def _observations(connection, match_id: int) -> tuple[str, dict]:
    analysis_id = connection.scalar(select(account_matches.c.active_analysis_id).where(
        account_matches.c.match_id == match_id))
    rows = connection.execute(select(metric_observations.c.metric_id, metric_observations.c.baseline_snapshot).where(
        metric_observations.c.analysis_id == analysis_id)).all()
    return analysis_id, dict(rows)


def test_late_replay_readmission_rebuilds_later_comparisons(database):
    """A late replay moves the late match's values into every later match's baseline."""
    _, profile_id = identity(database)
    history(database, profile_id, [0, 1, 2, 3, 4, 5])
    late = add_match(database, profile_id, index=20)
    with database.begin() as connection:
        connection.execute(update(matches).where(matches.c.match_id == late).values(
            evidence_state="REPLAY_UNAVAILABLE", terminal_reason="REPLAY_CHECKS_EXHAUSTED",
            replay_role_assignment=None))
        connection.execute(update(acquisitions).where(acquisitions.c.match_id == late).values(
            state="REPLAY_UNAVAILABLE"))
    assert finalize(database, profile_id, late) == "READY"
    later = add_match(database, profile_id, index=21)
    assert finalize(database, profile_id, later) == "READY"
    with database.connect() as connection:
        later_before, baselines_before = _observations(connection, later)
        events_before = connection.scalar(select(func.count()).select_from(events))
        outbox_before = connection.scalar(select(func.count()).select_from(notification_outbox))

    with database.begin() as connection:
        connection.execute(update(matches).where(matches.c.match_id == late).values(
            evidence_state="REPLAY_READY", terminal_reason=None))
        connection.execute(update(acquisitions).where(acquisitions.c.match_id == late).values(state="REPLAY_READY"))
        [job_id] = enqueue_readmissions(connection, late)
        job = claim(connection, priority=3)
    assert job["id"] == job_id
    assert complete_readmit_job(database, job_id=job["id"], lease_token=job["lease_token"]) == "READMITTED"

    with database.connect() as connection:
        later_after, baselines_after = _observations(connection, later)
        assert later_after != later_before
        # At least one replay-class baseline now counts the late match's value.
        assert any(baselines_after[metric] != baselines_before[metric] for metric in baselines_before)
        # Retroactive, never celebrated or notified.
        assert connection.scalar(select(func.count()).select_from(events)) == events_before
        assert connection.scalar(select(func.count()).select_from(notification_outbox)) == outbox_before


def _failed_backfill(database, user_id: str, profile_id: str, *, failed_at, error: str = "BACKFILL_PAGE_FAILED",
                     retries: int = 0) -> str:
    from app.tracker.backfill import request_pro_backfill

    with database.begin() as connection:
        job_id = request_pro_backfill(connection, profile_id, ceiling_days=365)
        connection.execute(update(ingest_jobs).where(ingest_jobs.c.id == job_id).values(
            state="FAILED", attempts=5, last_error=error, run_after=failed_at,
            cursor={"offset": 200, "pages": 1, "request_days": 366, "daily_retries": retries}))
    return job_id


def _job(database, job_id: str) -> dict:
    with database.connect() as connection:
        return dict(connection.execute(select(ingest_jobs).where(ingest_jobs.c.id == job_id)).mappings().one())


def test_failed_pro_backfill_is_retried_daily_while_pro_is_live(database):
    from app.tracker.backfill import DAILY_BACKFILL_RETRIES, retry_failed_pro_backfills
    from app.tracker.entitlement import FakeAppStoreVerifier, submit_transaction

    from .test_entitlement import NOW, ready_bootstrap, transaction

    user_id, profile_id = identity(database)
    ready_bootstrap(database, profile_id)
    verifier = FakeAppStoreVerifier({"transaction:pro": transaction(user_id, token="pro")})
    submit_transaction(database, user_id=user_id, signed_transaction="pro", verifier=verifier, now=NOW)
    job_id = _failed_backfill(database, user_id, profile_id, failed_at=NOW - timedelta(hours=2))

    # Not yet a day since the failure: nothing to do.
    with database.begin() as connection:
        assert retry_failed_pro_backfills(connection, now=NOW) == 0
    assert _job(database, job_id)["state"] == "FAILED"

    with database.begin() as connection:
        assert retry_failed_pro_backfills(connection, now=NOW + timedelta(days=1)) == 1
    job = _job(database, job_id)
    assert job["state"] == "PENDING" and job["attempts"] == 0 and job["priority"] == 3
    # The scan resumes at its committed page instead of refetching earlier ones.
    assert job["cursor"]["offset"] == 200 and job["cursor"]["daily_retries"] == 1

    # Hitting the page ceiling is deterministic: retrying would fail the same way.
    with database.begin() as connection:
        connection.execute(update(ingest_jobs).where(ingest_jobs.c.id == job_id).values(
            state="FAILED", run_after=NOW, last_error="PAGINATION_LIMIT"))
        assert retry_failed_pro_backfills(connection, now=NOW + timedelta(days=5)) == 0

    # The daily ladder is bounded.
    with database.begin() as connection:
        connection.execute(update(ingest_jobs).where(ingest_jobs.c.id == job_id).values(
            state="FAILED", run_after=NOW, last_error="BACKFILL_PAGE_FAILED",
            cursor={**job["cursor"], "daily_retries": DAILY_BACKFILL_RETRIES}))
        assert retry_failed_pro_backfills(connection, now=NOW + timedelta(days=5)) == 0
    assert _job(database, job_id)["state"] == "FAILED"


def test_failed_pro_backfill_is_not_retried_without_pro(database):
    from app.tracker.backfill import retry_failed_pro_backfills

    from .test_entitlement import NOW, ready_bootstrap

    _, profile_id = identity(database)
    ready_bootstrap(database, profile_id)
    # No live subscription: a Free user never spends provider budget on Pro history.
    job_id = _failed_backfill(database, "", profile_id, failed_at=NOW - timedelta(days=2))
    with database.begin() as connection:
        assert retry_failed_pro_backfills(connection, now=NOW) == 0
    assert _job(database, job_id)["state"] == "FAILED"


def test_worker_beat_schedules_the_daily_backfill_retry():
    from app.tracker.worker import create_worker_app

    app = create_worker_app(Settings())
    assert app.conf.beat_schedule["tracker-backfill-retry"]["task"] == "tracker.retry_backfills"
    assert "tracker.retry_backfills" in app.tasks


async def test_out_of_order_import_rebuilds_later_comparisons_through_the_worker(database, redis_client):
    """A recovered match finalized after later READY matches is folded into their comparisons."""
    from app.tracker.provider_control import ProviderGate
    from app.tracker.worker import WorkerPolicy, run_one

    from .test_e2e_matrix import HEADERS

    _, profile_id = identity(database)
    history(database, profile_id, [0, 1, 2, 3, 4, 5])
    later = add_match(database, profile_id, index=21)
    assert finalize(database, profile_id, later) == "READY"
    with database.connect() as connection:
        later_before, baselines_before = _observations(connection, later)

    recovered = add_match(database, profile_id, index=20, origin="RECOVERY", stack_bonus=9)
    assert finalize(database, profile_id, recovered) == "READY"
    with database.begin() as connection:
        events_before = connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind != "PROFILE_CHANGE"))
        [job] = connection.execute(select(ingest_jobs).where(ingest_jobs.c.job_type == "CLOSURE_REBUILD")).mappings().all()
        assert job["priority"] == 3 and job["profile_id"] == profile_id
        connection.execute(update(ingest_jobs).where(ingest_jobs.c.id == job["id"]).values(
            run_after=func.clock_timestamp() - timedelta(seconds=1)))
    redis, namespace = redis_client
    for provider in ("opendota", "stratz"):
        ProviderGate(redis, namespace=namespace, provider=provider).observe(HEADERS, status=200)
    assert await run_one(database, redis, Settings(), priority=3, policy=WorkerPolicy(namespace=namespace)) == "COMPLETE"

    with database.connect() as connection:
        later_after, baselines_after = _observations(connection, later)
        assert later_after != later_before
        assert any(baselines_after[metric] != baselines_before[metric] for metric in baselines_before)
        # A rebuild never celebrates or writes per-match events.
        assert connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind != "PROFILE_CHANGE")) == events_before


def test_in_order_finalization_queues_no_closure_rebuild(database):
    _, profile_id = identity(database)
    history(database, profile_id, [0, 1, 2])
    with database.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(ingest_jobs).where(
            ingest_jobs.c.job_type == "CLOSURE_REBUILD")) == 0


def _signed(key: bytes, message: str) -> str:
    import hashlib
    import hmac

    return hmac.new(key, message.encode("ascii"), hashlib.sha256).hexdigest()[:24]


def test_history_and_changes_cursors_are_keyed_by_a_server_secret(database, monkeypatch):
    """Knowing the profile id is not enough to mint a cursor the server accepts."""
    from app.tracker.mobile_api import create_mobile_app
    from fastapi.testclient import TestClient

    from .test_contract_rules import _client

    monkeypatch.setenv("TRACKER_CURSOR_SECRET", "s" * 32)
    _, headers, profile_id, _ = _client(database, "cursor-owner")
    history(database, profile_id, [0, 1, 2])
    client = TestClient(create_mobile_app(Settings(), database=database))
    paged = client.get("/history?mode=STANDARD&limit=1", headers=headers).json()
    ref = paged["next_cursor"].split(".")[0]
    assert client.get("/history", params={"mode": "STANDARD", "limit": 1, "cursor": paged["next_cursor"]},
                      headers=headers).status_code == 200
    # The former scheme keyed the MAC by the (internal) profile id.
    forged = f"{ref}.{_signed(profile_id.encode('ascii'), f'{ref}:STANDARD::0')}"
    assert client.get("/history", params={"mode": "STANDARD", "cursor": forged}, headers=headers).status_code == 400
    changes = client.get("/changes", headers=headers).json()["cursor"]
    micros, revision, _ = changes.split(".")
    forged_changes = f"{micros}.{revision}.{_signed(profile_id.encode('ascii'), f'{micros}|{revision}')}"
    assert client.get("/changes", params={"after": forged_changes}, headers=headers).json()["full_refresh"] is True
    assert client.get("/changes", params={"after": changes}, headers=headers).json()["full_refresh"] is False

    # A rotated secret invalidates outstanding cursors instead of honouring them.
    monkeypatch.setenv("TRACKER_CURSOR_SECRET", "r" * 32)
    rotated = TestClient(create_mobile_app(Settings(), database=database))
    assert rotated.get("/history", params={"mode": "STANDARD", "cursor": paged["next_cursor"]},
                       headers=headers).status_code == 400


def test_production_cursor_endpoints_fail_closed_without_a_secret_but_the_app_starts(database, monkeypatch):
    """The mobile app is mounted in the live legacy API: startup must survive, cursors must not."""
    from app.tracker.mobile_api import create_mobile_app
    from fastapi.testclient import TestClient

    from .test_contract_rules import _client

    _, headers, profile_id, _ = _client(database, "cursor-prod")
    history(database, profile_id, [0])
    for value in (None, "short"):
        if value is None:
            monkeypatch.delenv("TRACKER_CURSOR_SECRET", raising=False)
        else:
            monkeypatch.setenv("TRACKER_CURSOR_SECRET", value)
        client = TestClient(create_mobile_app(Settings(app_env="production"), database=database))
        assert client.get("/history", headers=headers).status_code == 503
        assert client.get("/changes", headers=headers).status_code == 503
        assert client.get("/account", headers=headers).status_code == 200


# -- live smoke findings --------------------------------------------------------------

async def _drain_production_like(database, redis_client, transport, *, settings=None, rounds: int = 40) -> None:
    """Like the e2e drain, but only OpenDota's window is ever observed, as in production."""
    from app.tracker.provider_control import ProviderGate
    from app.tracker.worker import WorkerPolicy, run_one

    from .test_e2e_matrix import HEADERS, _due

    redis, namespace = redis_client
    policy = WorkerPolicy(namespace=namespace)
    ProviderGate(redis, namespace=namespace, provider="opendota").observe(HEADERS, status=200)
    for _ in range(rounds):
        _due(database)
        progressed = False
        for priority in range(4):
            for _step in range(20):
                outcome = await run_one(database, redis, settings or Settings(), priority=priority, policy=policy,
                                        transport=transport)
                if outcome in {"IDLE", "OPERATOR_PAUSED", "PROVIDER_BUDGET", "P1_DEPTH", "P1_AGE", "P2_REDUCED_SHARE"}:
                    break
                progressed = True
        if not progressed:
            return


def _bootstrap_scenario(database, subject: str):
    from datetime import UTC, datetime

    from .test_independent_qa import WindowedOpenDota, _match, _steam_owner

    now = datetime.now(UTC)
    linked_at = now - timedelta(days=1)
    profile_id, token = _steam_owner(database, subject, 1001, linked_at)
    imported = _match(9_400_000_031, linked_at - timedelta(days=2), 1001)
    live = _match(9_400_000_032, now - timedelta(hours=6), 1001)
    return profile_id, token, imported, live, WindowedOpenDota(1001, [imported, live])


def _settled(database, profile_id: str) -> tuple[dict, dict]:
    from app.tracker.schema import bootstrap

    with database.connect() as connection:
        outcome = dict(connection.execute(select(bootstrap.c.mode, bootstrap.c.outcome).where(
            bootstrap.c.profile_id == profile_id)).all())
        links = {row.match_id: (row.origin, row.lifecycle) for row in connection.execute(select(
            account_matches.c.match_id, account_matches.c.origin, account_matches.c.lifecycle).where(
            account_matches.c.profile_id == profile_id))}
    return outcome, links


async def test_p3_work_runs_before_any_stratz_window_is_observed(database, redis_client):
    """Only P3 work calls STRATZ, so requiring a known STRATZ window to admit P3 deadlocked it."""
    import httpx
    from app.tracker.mobile_api import create_mobile_app
    from fastapi.testclient import TestClient

    from .test_independent_qa import _sync

    profile_id, token, imported, live, fake = _bootstrap_scenario(database, "unobserved-stratz")
    _sync(TestClient(create_mobile_app(Settings(), database=database)), token, "sync-unobserved-stratz")
    await _drain_production_like(database, redis_client, httpx.MockTransport(fake))
    outcome, links = _settled(database, profile_id)
    assert outcome["STANDARD"] in {"READY", "READY_WITH_GAPS"} and outcome["TURBO"] == "NO_MATCHES_FOUND"
    assert links == {imported["match_id"]: ("BOOTSTRAP", "READY"), live["match_id"]: ("LIVE", "READY")}


async def test_disabled_stratz_hands_batches_to_the_summary_route(database, redis_client):
    """A credential/IP-binding disable lasts until an operator reset; bootstrap must not wait on it."""
    import httpx
    from app.tracker.mobile_api import create_mobile_app
    from app.tracker.provider_control import ProviderGate
    from fastapi.testclient import TestClient

    from .test_independent_qa import _sync

    profile_id, token, imported, live, fake = _bootstrap_scenario(database, "disabled-stratz")
    redis, namespace = redis_client
    ProviderGate(redis, namespace=namespace, provider="stratz").observe({}, status=403)
    stratz_requests = []

    def transport(request: httpx.Request) -> httpx.Response:
        if request.url.host.endswith("stratz.com"):
            stratz_requests.append(request)
            return httpx.Response(500)
        return fake(request)

    settings = Settings(stratz_api_token="dev-token")
    _sync(TestClient(create_mobile_app(settings, database=database)), token, "sync-disabled-stratz")
    await _drain_production_like(database, redis_client, httpx.MockTransport(transport), settings=settings)
    outcome, links = _settled(database, profile_id)
    assert stratz_requests == []
    assert outcome["STANDARD"] in {"READY", "READY_WITH_GAPS"}
    assert links == {imported["match_id"]: ("BOOTSTRAP", "READY"), live["match_id"]: ("LIVE", "READY")}

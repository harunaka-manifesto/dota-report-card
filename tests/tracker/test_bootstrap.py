from datetime import timedelta
from uuid import uuid4

import httpx
from app.core.config import Settings
from app.tracker import bootstrap as search
from app.tracker.jobs import claim
from app.tracker.schema import (
    account_matches,
    bootstrap,
    bootstrap_search_items,
    coverage,
    events,
    ingest_jobs,
    match_players,
    matches,
    provider_calls,
)
from sqlalchemy import func, select

from .test_provider_transport import gate_for
from .test_schema import NOW, identity


def setup(database):
    _, profile_id = identity(database)
    with database.begin() as c:
        job_id = search.request_bootstrap_search(c, profile_id)
        assert search.request_bootstrap_search(c, profile_id) == job_id
    return profile_id, job_id


def claim_page(database, job_id):
    with database.begin() as c:
        c.execute(ingest_jobs.update().where(ingest_jobs.c.id == job_id).values(run_after=func.clock_timestamp()))
        return claim(c, priority=3)


async def test_bootstrap_search_journals_both_modes_and_original_window(database, redis_client):
    profile_id, job_id = setup(database)
    gate = gate_for(redis_client, "opendota")
    def stamp(days):
        return int((NOW + timedelta(days=days)).timestamp())
    page = [
        {"match_id": 1, "start_time": stamp(1), "game_mode": 23},
        {"match_id": 2, "start_time": stamp(-1), "game_mode": 22},
        {"match_id": 3, "start_time": stamp(-2), "game_mode": 23},
        {"match_id": 4, "start_time": stamp(-3), "game_mode": 2},
        {"match_id": 5, "start_time": stamp(-91), "game_mode": 22},
    ]
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.params["significant"] == "0"
        return httpx.Response(200, json=page)

    job = claim_page(database, job_id)
    assert await search.search_bootstrap_page(database, gate, Settings(), job_id=job_id, lease_token=job["lease_token"], transport=httpx.MockTransport(handler)) == "COMPLETE"
    assert len(calls) == 1
    with database.connect() as c:
        states = c.execute(select(bootstrap).where(bootstrap.c.profile_id == profile_id).order_by(bootstrap.c.mode)).mappings().all()
        assert [row["mode"] for row in states] == ["STANDARD", "TURBO"]
        assert all(row["search_finished"] and row["completed_at"] is None and row["discovered_count"] == 1 for row in states)
        items = c.execute(select(bootstrap_search_items).order_by(bootstrap_search_items.c.source_item_id)).mappings().all()
        assert [(row["source_item_id"], row["mode"], row["reason"]) for row in items] == [
            ("1", None, "AFTER_LINK"), ("2", "STANDARD", None), ("3", "TURBO", None),
            ("4", None, "UNSUPPORTED_MODE"), ("5", None, "BEFORE_WINDOW"),
        ]
        assert [row["selected_at"] is not None for row in items] == [False, True, True, False, False]
        assert c.scalar(select(ingest_jobs.c.state).where(ingest_jobs.c.id == job_id)) == "COMPLETE"
        batches = c.execute(select(ingest_jobs.c.payload).where(ingest_jobs.c.job_type == "HISTORICAL_BATCH")).scalars().all()
        assert {tuple(batch["match_ids"]) for batch in batches} == {(2,), (3,)}
        assert set(c.scalars(select(matches.c.match_id))) == {2, 3}
        assert c.scalar(select(func.count()).select_from(provider_calls)) == 1


async def test_bootstrap_page_reuses_recorded_evidence_after_rollback(database, redis_client, monkeypatch):
    profile_id, job_id = setup(database)
    gate = gate_for(redis_client, "opendota")
    calls = []
    payload = [{"match_id": 10, "start_time": int((NOW - timedelta(days=1)).timestamp()), "game_mode": 23}]

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=payload if len(calls) == 1 else [])

    original = search._publish_page

    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("publication rollback")

    monkeypatch.setattr(search, "_publish_page", fail)
    job = claim_page(database, job_id)
    assert await search.search_bootstrap_page(database, gate, Settings(), job_id=job_id, lease_token=job["lease_token"], transport=httpx.MockTransport(handler)) == "DEFERRED"
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(bootstrap_search_items)) == 0
        assert c.scalar(select(bootstrap.c.cursor).where(bootstrap.c.profile_id == profile_id, bootstrap.c.mode == "TURBO")) is None
    monkeypatch.setattr(search, "_publish_page", original)
    job = claim_page(database, job_id)
    assert await search.search_bootstrap_page(database, gate, Settings(), job_id=job_id, lease_token=job["lease_token"], transport=httpx.MockTransport(handler)) == "DEFERRED"
    assert len(calls) == 1
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(bootstrap_search_items)) == 1
        assert c.scalar(select(ingest_jobs.c.cursor).where(ingest_jobs.c.id == job_id))["offset"] == 1


async def test_undated_page_cannot_create_false_coverage(database, redis_client):
    profile_id, job_id = setup(database)
    gate = gate_for(redis_client, "opendota")
    job = claim_page(database, job_id)
    result = await search.search_bootstrap_page(database, gate, Settings(), job_id=job_id, lease_token=job["lease_token"],
                                                transport=httpx.MockTransport(lambda _: httpx.Response(200, json=[{"match_id": 10}])), max_attempts=1)
    assert result == "FAILED"
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(bootstrap_search_items)) == 0
        assert not c.scalar(select(bootstrap.c.search_finished).where(bootstrap.c.profile_id == profile_id, bootstrap.c.mode == "STANDARD"))


async def test_shifted_offset_page_does_not_advance_coverage(database, redis_client):
    profile_id, job_id = setup(database)
    gate = gate_for(redis_client, "opendota")
    stamp = int((NOW - timedelta(days=1)).timestamp())
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=[{"match_id": 10, "start_time": stamp, "game_mode": 23}])

    for expected in ("DEFERRED", "FAILED"):
        job = claim_page(database, job_id)
        assert await search.search_bootstrap_page(database, gate, Settings(), job_id=job_id, lease_token=job["lease_token"],
                                                  transport=httpx.MockTransport(handler), max_attempts=1) == expected
    assert calls == 2
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(bootstrap_search_items)) == 1
        assert c.scalar(select(bootstrap.c.cursor).where(bootstrap.c.profile_id == profile_id, bootstrap.c.mode == "TURBO"))["offset"] == 1
        assert not c.scalar(select(bootstrap.c.search_finished).where(bootstrap.c.profile_id == profile_id, bootstrap.c.mode == "TURBO"))


async def test_initial_selection_caps_each_mode_independently(database, redis_client):
    profile_id, job_id = setup(database)
    gate = gate_for(redis_client, "opendota")
    page = [
        {"match_id": i, "start_time": int((NOW - timedelta(days=i)).timestamp()), "game_mode": 22 if i <= 35 else 23}
        for i in range(1, 43)
    ]
    page.append({"match_id": 43, "start_time": int((NOW - timedelta(days=91)).timestamp()), "game_mode": 22})
    job = claim_page(database, job_id)
    assert await search.search_bootstrap_page(database, gate, Settings(), job_id=job_id, lease_token=job["lease_token"],
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=page))) == "COMPLETE"
    with database.connect() as c:
        counts = dict(c.execute(select(bootstrap.c.mode, bootstrap.c.discovered_count).where(bootstrap.c.profile_id == profile_id)).all())
        assert counts == {"STANDARD": 30, "TURBO": 7}
        selected = set(c.scalars(select(bootstrap_search_items.c.match_id).where(bootstrap_search_items.c.selected_at.is_not(None))))
        assert selected == set(range(1, 31)) | set(range(36, 43))
        assert set(c.scalars(select(matches.c.match_id))) == selected
        batches = c.execute(select(ingest_jobs.c.payload).where(ingest_jobs.c.job_type == "HISTORICAL_BATCH")).scalars().all()
        assert {tuple(batch["match_ids"]) for batch in batches} == {tuple(range(1, 31)), tuple(range(36, 43))}
        assert all(batch["origin"] == "BOOTSTRAP" for batch in batches)


async def test_ineligible_candidate_refills_only_its_mode_until_eligible_target(database, redis_client):
    profile_id, job_id = setup(database)
    gate = gate_for(redis_client, "opendota")
    page = [
        {"match_id": i, "start_time": int((NOW - timedelta(days=i)).timestamp()), "game_mode": 22}
        for i in range(1, 33)
    ] + [
        {"match_id": 100 + i, "start_time": int((NOW - timedelta(days=32 + i)).timestamp()), "game_mode": 23}
        for i in range(1, 4)
    ] + [{"match_id": 999, "start_time": int((NOW - timedelta(days=91)).timestamp()), "game_mode": 22}]
    job = claim_page(database, job_id)
    assert await search.search_bootstrap_page(database, gate, Settings(), job_id=job_id,
        lease_token=job["lease_token"], transport=httpx.MockTransport(lambda _: httpx.Response(200, json=page))) == "COMPLETE"

    with database.begin() as c:
        assert search.settle_candidate(c, profile_id=profile_id, match_id=1,
            eligible=False, reason="INELIGIBLE:INTEGRITY_INVALID") == 1
        assert search.settle_candidate(c, profile_id=profile_id, match_id=2,
            eligible=True, reason="ELIGIBLE") == 0
    with database.connect() as c:
        counts = {row["mode"]: (row["discovered_count"], row["eligible_count"], row["settled_count"])
                  for row in c.execute(select(bootstrap).where(bootstrap.c.profile_id == profile_id)).mappings()}
        assert counts == {"STANDARD": (31, 1, 2), "TURBO": (3, 0, 0)}
        standard_selected = set(c.scalars(select(bootstrap_search_items.c.match_id).where(
            bootstrap_search_items.c.profile_id == profile_id,
            bootstrap_search_items.c.mode == "STANDARD",
            bootstrap_search_items.c.selected_at.is_not(None),
        )))
        assert standard_selected == set(range(1, 32))
        assert set(c.scalars(select(bootstrap_search_items.c.match_id).where(
            bootstrap_search_items.c.profile_id == profile_id,
            bootstrap_search_items.c.mode == "TURBO",
            bootstrap_search_items.c.selected_at.is_not(None),
        ))) == {101, 102, 103}
        batches = c.scalars(select(ingest_jobs.c.payload).where(ingest_jobs.c.job_type == "HISTORICAL_BATCH")).all()
        assert any(batch["match_ids"] == [31] for batch in batches)


async def test_bootstrap_completion_waits_for_analyses_and_coverage_then_emits_once(database, redis_client):
    profile_id, job_id = setup(database)
    gate = gate_for(redis_client, "opendota")
    stamp = int((NOW - timedelta(days=2)).timestamp())
    page = [
        {"match_id": 77, "start_time": stamp, "game_mode": 22},
        {"match_id": 78, "start_time": int((NOW - timedelta(days=91)).timestamp()), "game_mode": 22},
    ]
    job = claim_page(database, job_id)
    assert await search.search_bootstrap_page(database, gate, Settings(), job_id=job_id,
        lease_token=job["lease_token"], transport=httpx.MockTransport(lambda _: httpx.Response(200, json=page))) == "COMPLETE"

    with database.begin() as c:
        c.execute(match_players.insert(), [dict(match_id=77, player_slot=slot, hero_id=slot + 1,
            account_id=1001 if slot == 0 else None, team="RADIANT" if slot < 5 else "DIRE", summary={})
            for slot in range(10)])
        c.execute(account_matches.insert().values(profile_id=profile_id, match_id=77, account_id=1001,
            player_slot=0, lifecycle="ANALYZING", mode="STANDARD", progression="STANDARD",
            provider_started_at=NOW - timedelta(days=2), provider_source_match_id=77,
            origin="BOOTSTRAP", effective_role="CARRY"))
        assert search.settle_candidate(c, profile_id=profile_id, match_id=77,
            eligible=True, reason="ELIGIBLE") == 0
        assert not search.settle_bootstrap(c, profile_id)
        c.execute(account_matches.update().where(account_matches.c.profile_id == profile_id,
            account_matches.c.match_id == 77).values(lifecycle="UNAVAILABLE"))
        c.execute(coverage.insert().values(id=str(uuid4()), profile_id=profile_id, mode="STANDARD",
            evidence_class="REPLAY", start_at=NOW - timedelta(days=90), end_at=NOW,
            state="PENDING", reason="REPLAY_PENDING"))
        assert not search.settle_bootstrap(c, profile_id)
        c.execute(coverage.update().where(coverage.c.profile_id == profile_id).values(state="GAP", reason="REPLAY_UNAVAILABLE"))
        assert search.settle_bootstrap(c, profile_id)
        assert search.settle_bootstrap(c, profile_id)

    with database.connect() as c:
        outcomes = dict(c.execute(select(bootstrap.c.mode, bootstrap.c.outcome).where(
            bootstrap.c.profile_id == profile_id)).all())
        assert outcomes == {"STANDARD": "READY_WITH_GAPS", "TURBO": "NO_MATCHES_FOUND"}
        assert c.scalar(select(func.count()).select_from(events).where(
            events.c.profile_id == profile_id, events.c.kind == "BOOTSTRAP_COMPLETED")) == 1


async def test_empty_bootstrap_scope_completes_both_modes(database, redis_client):
    profile_id, job_id = setup(database)
    job = claim_page(database, job_id)
    assert await search.search_bootstrap_page(database, gate_for(redis_client, "opendota"), Settings(),
        job_id=job_id, lease_token=job["lease_token"],
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=[]))) == "COMPLETE"
    with database.connect() as c:
        rows = c.execute(select(bootstrap).where(bootstrap.c.profile_id == profile_id)).mappings().all()
        assert {row["outcome"] for row in rows} == {"NO_MATCHES_FOUND"}
        assert all(row["completed_at"] is not None for row in rows)
        assert c.scalar(select(func.count()).select_from(events).where(
            events.c.profile_id == profile_id, events.c.kind == "BOOTSTRAP_COMPLETED")) == 1

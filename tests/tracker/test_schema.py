from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.analysis.source import FixtureOpenDotaSource
from app.core.config import Settings
from app.main import create_app
from app.storage.database import check_database_revision
from app.storage.models import RawPayloadRecord, ReportRecord
from app.storage.repository import SqlAlchemyRepository
from app.tracker import schema as s
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, func, insert, inspect, select, text, update
from sqlalchemy.exc import IntegrityError

from .conftest import ROOT, migrate

NOW = datetime(2026, 9, 21, tzinfo=UTC)
MATCH_ID = 9_000_000_001


def identity(database: Engine, account_id: int = 1001) -> tuple[str, str]:
    user_id, profile_id = str(uuid4()), str(uuid4())
    with database.begin() as c:
        c.execute(insert(s.users).values(id=user_id, created_at=NOW))
        c.execute(insert(s.dota_accounts).values(account_id=account_id))
        c.execute(insert(s.profiles).values(
            id=profile_id, user_id=user_id, account_id=account_id, original_linked_at=NOW,
        ))
    return user_id, profile_id


def summary(database: Engine, match_id: int = MATCH_ID) -> None:
    with database.begin() as c:
        c.execute(insert(s.matches).values(
            match_id=match_id, started_at=NOW, duration_seconds=1800, mode="STANDARD",
            radiant_win=True, header={}, evidence_state="SUMMARY_READY",
            discovered_at=NOW, summary_ready_at=NOW,
        ))
        c.execute(insert(s.match_players), [
            dict(match_id=match_id, player_slot=i, hero_id=i + 1,
                 account_id=1001 if i == 0 else None,
                 team="RADIANT" if i < 5 else "DIRE", summary={})
            for i in range(10)
        ])


def snapshot(database: Engine, provider: str, payload: dict, digest: str) -> str:
    ref = str(uuid4())
    with database.begin() as c:
        c.execute(insert(s.snapshots).values(
            id=ref, provider=provider, operation="match_detail", operation_version="v1",
            schema_version="v1", subject=str(MATCH_ID), digest=digest,
            byte_size=len(json.dumps(payload)), fetched_at=NOW, payload=payload, provenance={},
        ))
    return ref


def test_upgrade_preserves_current_and_historical_report_reads(postgres: Engine) -> None:
    url = postgres.url.render_as_string(hide_password=False)
    migrate(url, "0005_v6_interactions_deep")
    assert not any(name.startswith("tracker_") for name in inspect(postgres).get_table_names())
    report_ids: list[tuple[str, dict]] = []
    for path in (
        ROOT / "apps/web/tests/fixtures/persisted-reports/v61-historical-production.json",
        ROOT / "tests/fixtures/v61/current-story-payload.json",
    ):
        report_id = str(uuid4())
        document = json.loads(path.read_text())
        report_ids.append((report_id, document))
        with postgres.begin() as c:
            c.execute(insert(ReportRecord).values(
                report_id=report_id, account_id=1001, data_cutoff=1,
                model_version="retained-fixture", template_version="retained-fixture",
                report_json=document, created_at=datetime.now(UTC),
            ))
    settings = Settings(database_url=url, opendota_source="fixture", storage_backend="database")
    source = FixtureOpenDotaSource("tests/fixtures/opendota")
    repository = SqlAlchemyRepository(settings)
    try:
        client = TestClient(create_app(settings, source=source, repository=repository))
        before = {ref: client.get(f"/v1/reports/{ref}").json() for ref, _ in report_ids}
        for _ in range(2):
            migrate(url, "head")
        check_database_revision(postgres)
        for ref, document in report_ids:
            response = client.get(f"/v1/reports/{ref}")
            assert response.status_code == 200
            assert response.json() == before[ref] == {**document, "report_id": ref}
        assert source.requests == []
        migrate(url, "0005_v6_interactions_deep", "downgrade")
        assert not any(name.startswith("tracker_") for name in inspect(postgres).get_table_names())
        for ref, _ in report_ids:
            assert client.get(f"/v1/reports/{ref}").json() == before[ref]
        migrate(url, "head")
    finally:
        repository.engine.dispose()


def test_metadata_matches_migrated_schema(database: Engine) -> None:
    with database.connect() as c:
        context = MigrationContext.configure(c, opts={
            "include_object": lambda obj, name, kind, reflected, compare_to:
                kind != "table" or name.startswith("tracker_"),
        })
        assert compare_metadata(context, s.metadata) == []


def test_summary_requires_complete_ten_player_roster_at_commit(database: Engine) -> None:
    with pytest.raises(IntegrityError, match="ten canonical players"):
        with database.begin() as c:
            c.execute(insert(s.matches).values(
                match_id=MATCH_ID, started_at=NOW, duration_seconds=1800, mode="STANDARD",
                radiant_win=True, header={}, evidence_state="SUMMARY_READY",
                discovered_at=NOW, summary_ready_at=NOW,
            ))
    summary(database)
    with pytest.raises(IntegrityError, match="ten canonical players"):
        with database.begin() as c:
            c.execute(delete(s.match_players).where(s.match_players.c.player_slot == 9))
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(s.match_players)) == 10


@pytest.mark.parametrize("collision", ["account", "user"])
def test_steam_ownership_is_unique_under_concurrent_writers(database: Engine, collision: str) -> None:
    users = [str(uuid4()), str(uuid4())]
    with database.begin() as c:
        c.execute(insert(s.users), [dict(id=ref, created_at=NOW) for ref in users])
        c.execute(insert(s.dota_accounts), [dict(account_id=account) for account in (1001, 1002)])
    barrier = Barrier(2)

    def claim(i: int) -> bool:
        barrier.wait(timeout=5)
        try:
            with database.begin() as c:
                c.execute(insert(s.profiles).values(
                    id=str(uuid4()), user_id=users[0 if collision == "user" else i],
                    account_id=1001 if collision == "account" else 1001 + i,
                    original_linked_at=NOW,
                ))
            return True
        except IntegrityError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(claim, (0, 1))) == [False, True]


def test_job_identity_is_unique_without_a_redis_lock(database: Engine) -> None:
    barrier = Barrier(2)

    def enqueue(_: int) -> bool:
        barrier.wait(timeout=5)
        try:
            with database.begin() as c:
                c.execute(insert(s.ingest_jobs).values(
                    id=str(uuid4()), dedup_key="parse:opendota:fixture", job_type="enrich",
                    priority=1, run_after=NOW, created_at=NOW, payload={},
                ))
            return True
        except IntegrityError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(enqueue, (0, 1))) == [False, True]
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(s.ingest_jobs)) == 1


def test_snapshots_coexist_are_immutable_and_survive_legacy_purge(database: Engine) -> None:
    snapshot(database, "opendota", {"version": None}, "a" * 64)
    raw = snapshot(database, "opendota", {"version": 22}, "b" * 64)
    snapshot(database, "stratz", {"statsDateTime": 123}, "c" * 64)
    with pytest.raises(IntegrityError, match="immutable tracker"):
        with database.begin() as c:
            c.execute(update(s.snapshots).where(s.snapshots.c.id == raw).values(payload={}))
    with database.begin() as c:
        c.execute(insert(RawPayloadRecord).values(
            endpoint="legacy-fixture", source_id="fixture", payload_hash="d" * 64,
            payload_json={}, metadata_json={}, fetched_at=NOW - timedelta(days=365),
        ))
    repository = SqlAlchemyRepository(Settings(database_url=database.url.render_as_string(hide_password=False)))
    try:
        repository.purge_expired(now=NOW)
    finally:
        repository.engine.dispose()
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(s.snapshots)) == 3
        assert c.scalar(select(func.count()).select_from(RawPayloadRecord)) == 0


def test_analysis_retention_role_assertions_and_readiness_axes(database: Engine) -> None:
    _, profile_id = identity(database)
    summary(database)
    source_id = snapshot(database, "opendota", {"version": None}, "e" * 64)
    with database.begin() as c:
        c.execute(insert(s.account_matches).values(
            profile_id=profile_id, match_id=MATCH_ID, account_id=1001, player_slot=0,
            mode="STANDARD", provider_started_at=NOW, provider_source_match_id=MATCH_ID,
            origin="LIVE", lifecycle="ANALYZING",
        ))
        for ref in ("first", "recomputed"):
            c.execute(insert(s.analyses).values(
                id=ref, profile_id=profile_id, match_id=MATCH_ID,
                feature_version="feature-v1", analysis_version="analysis-v1",
                baseline_version="baseline-v1", inputs_digest=ref.ljust(64, "0"),
                result={}, provenance={}, created_at=NOW,
            ))
        c.execute(insert(s.analysis_inputs).values(analysis_id="first", snapshot_id=source_id))
        c.execute(insert(s.role_assertions).values(
            id=str(uuid4()), profile_id=profile_id, match_id=MATCH_ID, revision=1,
            role="SUPPORT", asserted_at=NOW, provenance={}, dedup_key="correction-1",
        ))
    with pytest.raises(IntegrityError):
        with database.begin() as c:
            c.execute(delete(s.snapshots).where(s.snapshots.c.id == source_id))
    with pytest.raises(IntegrityError, match="immutable tracker"):
        with database.begin() as c:
            c.execute(update(s.role_assertions).values(role="CARRY"))
    with pytest.raises(IntegrityError, match="ck_tracker_lifecycle"):
        with database.begin() as c:
            c.execute(update(s.account_matches).values(lifecycle="RETRYING"))
    with pytest.raises(IntegrityError, match="ck_tracker_finalized"):
        with database.begin() as c:
            c.execute(update(s.account_matches).values(lifecycle="READY"))
    with pytest.raises(IntegrityError, match="terminal evidence"):
        with database.begin() as c:
            c.execute(update(s.account_matches).values(
                lifecycle="READY", finalized_at=NOW, progression="STANDARD",
                active_analysis_id="first",
            ))
    with database.connect() as c:
        assert c.scalar(select(s.matches.c.evidence_state)) == "SUMMARY_READY"
        assert c.scalar(select(s.account_matches.c.lifecycle)) == "ANALYZING"
        assert c.scalar(select(func.count()).select_from(s.analyses)) == 2
        assert c.scalar(select(s.role_assertions.c.role)) == "SUPPORT"
    with database.begin() as c:
        c.execute(update(s.matches).values(
            evidence_state="REPLAY_UNAVAILABLE", terminal_reason="NOT_RETAINED",
            replay_terminal_at=NOW,
        ))
        c.execute(update(s.account_matches).values(
            lifecycle="READY", finalized_at=NOW, progression="STANDARD",
            active_analysis_id="first",
        ))
        c.execute(insert(s.metric_observations), [
            dict(analysis_id="first", metric_id=key, metric_version="v1", raw_value=value,
                 comparison_value=value, unavailable_reason=reason, baseline_snapshot={})
            for key, value, reason in (("measured_zero", 0, None), ("missing", None, "NOT_RETAINED"))
        ])
    with database.connect() as c:
        values = dict(c.execute(select(s.metric_observations.c.metric_id, s.metric_observations.c.raw_value)).all())
        assert values == {"measured_zero": 0.0, "missing": None}
        assert c.scalar(select(s.account_matches.c.lifecycle)) == "READY"
    with pytest.raises(IntegrityError, match="finite"):
        with database.begin() as c:
            c.execute(insert(s.metric_observations).values(
                analysis_id="first", metric_id="invalid", metric_version="v1",
                raw_value=float("nan"), comparison_value=float("inf"), baseline_snapshot={},
            ))


def test_worker_claims_do_not_block_behind_another_locked_job(database: Engine) -> None:
    with database.begin() as c:
        c.execute(insert(s.ingest_jobs), [dict(
            id=str(i), dedup_key=str(i), job_type="fixture", priority=1,
            run_after=NOW, created_at=NOW, payload={},
        ) for i in range(2)])
    due = select(s.ingest_jobs.c.id).order_by(s.ingest_jobs.c.id).limit(1).with_for_update(skip_locked=True)
    with database.begin() as first, database.begin() as second:
        first.execute(text("SET LOCAL statement_timeout = '1s'"))
        second.execute(text("SET LOCAL statement_timeout = '1s'"))
        assert first.scalar(due) == "0"
        assert second.scalar(due) == "1"


def test_discovery_upgrade_retains_existing_call_ledger(postgres: Engine) -> None:
    url = postgres.url.render_as_string(hide_password=False)
    migrate(url, "0006_tracker_foundation")
    with postgres.begin() as c:
        c.execute(text("INSERT INTO tracker_provider_calls (provider, operation, operation_version, latency_ms, billed_units, rate_units, called_at) VALUES ('opendota', 'history', '1', 1, 1, 1, now())"))
    migrate(url, "head")
    with postgres.connect() as c:
        row = c.execute(select(s.provider_calls)).mappings().one()
        assert row['billed_units'] == row['rate_units'] == 1
        assert all(row[key] is None for key in ('account_id', 'job_id', 'snapshot_id', 'request_subject'))
    migrate(url, "0006_tracker_foundation", "downgrade")
    with postgres.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM tracker_provider_calls")) == 1
    migrate(url, "head")

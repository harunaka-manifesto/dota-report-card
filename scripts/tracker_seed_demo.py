"""Fixture-backed local seed for the Dota Tracker mobile API (goal §14.5).

Creates one app account per product state from the sanitized, versioned
specimen under tests/fixtures/tracker/paired-replay-v1. Every match is stored
evidence materialized locally; nothing here can reach a provider. States that
the pipeline reaches only through failures (ACTION_REQUIRED, a waiting match)
are written directly within the same database constraints the pipeline obeys.

Usage (after `make db-migrate` against a local database):

    DATABASE_URL=postgresql+psycopg://... uv run python -m scripts.tracker_seed_demo

It prints one bearer token per persona for local exploration.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import Engine, create_engine, func, insert, select, update

ROOT = Path(__file__).resolve().parents[1]
SPECIMEN = ROOT / "tests/fixtures/tracker/paired-replay-v1/opendota.json"
SEED_MATCH_BASE = 9_200_000_000
LINKED_AT = datetime(2026, 9, 1, tzinfo=UTC)

sys.path.insert(0, str(ROOT / "services/api"))

from app.tracker.account_lifecycle import (  # noqa: E402
    request_account_deletion,
    switch_steam_profile,
)
from app.tracker.authentication import VerifiedIdentity, create_user_session  # noqa: E402
from app.tracker.entitlement import (  # noqa: E402
    FakeAppStoreVerifier,
    StoreTransaction,
    apply_notification,
    fake_digest,
    reconcile_entitlement_scope,
    submit_transaction,
)
from app.tracker.evidence import save_snapshot  # noqa: E402
from app.tracker.finalization import complete_finalization_job, enqueue_finalization  # noqa: E402
from app.tracker.jobs import claim  # noqa: E402
from app.tracker.materialization import materialize_snapshot  # noqa: E402
from app.tracker.rebuild import complete_scope_rebuild_job  # noqa: E402
from app.tracker.role_correction import correct_role  # noqa: E402
from app.tracker.schema import (  # noqa: E402
    account_matches,
    bootstrap,
    coverage,
    dota_accounts,
    ingest_jobs,
    matches,
    profiles,
    sync_state,
    users,
)


class Seeder:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.next_match = SEED_MATCH_BASE
        self.next_account = 70_000_001
        self.personas: dict[str, dict[str, Any]] = {}

    # -- identities --------------------------------------------------------------
    def user(self, name: str, *, linked: bool = True) -> dict[str, Any]:
        user_id, tokens = create_user_session(self.engine, VerifiedIdentity(
            "google", "https://accounts.google.com", f"seed-{name}", None))
        persona: dict[str, Any] = {"user_id": user_id, "access_token": tokens.access_token}
        if linked:
            account_id = self.next_account
            self.next_account += 1
            profile_id = str(uuid4())
            with self.engine.begin() as connection:
                connection.execute(insert(dota_accounts).values(account_id=account_id, visibility="ACCESSIBLE"))
                connection.execute(insert(profiles).values(
                    id=profile_id, user_id=user_id, account_id=account_id, active=True,
                    original_linked_at=LINKED_AT))
            persona.update(profile_id=profile_id, account_id=account_id)
        self.personas[name] = persona
        return persona

    def bootstrap(self, persona: dict[str, Any], outcomes: dict[str, str | None]) -> None:
        with self.engine.begin() as connection:
            for mode, outcome in outcomes.items():
                terminal = outcome is not None
                counts = {"READY": (3, 3), "READY_WITH_GAPS": (3, 2), "NO_ELIGIBLE_MATCHES": (2, 0)}.get(outcome or "", (0, 0))
                connection.execute(insert(bootstrap).values(
                    profile_id=persona["profile_id"], mode=mode, search_finished=terminal,
                    discovered_count=counts[0], eligible_count=counts[1],
                    settled_count=counts[0] if terminal else 0, outcome=outcome,
                    completed_at=LINKED_AT if terminal else None))

    # -- matches ---------------------------------------------------------------
    def match(self, persona: dict[str, Any], *, days: float, origin: str = "LIVE", finalize: bool = True,
              parsed: bool = True, turbo: bool = False, stack_bonus: int = 0, duration: int | None = None,
              role: str | None = "SUPPORT", healing: int | None = None) -> int:
        match_id = self.next_match
        self.next_match += 1
        payload = json.loads(SPECIMEN.read_text())
        payload["match_id"] = match_id
        payload["start_time"] = int((LINKED_AT + timedelta(days=days)).timestamp())
        payload["players"][0]["account_id"] = persona["account_id"]
        if turbo:
            payload["game_mode"] = 23
        if duration is not None:
            payload["duration"] = duration
        if healing is not None:
            payload["players"][0]["hero_healing"] = healing
        if not parsed:
            payload["version"] = None
        if stack_bonus:
            payload["players"][0]["camps_stacked_t"] = [
                value + (stack_bonus if minute >= 20 else 0)
                for minute, value in enumerate(payload["players"][0]["camps_stacked_t"])]
        with self.engine.begin() as connection:
            snapshot_id = save_snapshot(
                connection, provider="opendota", operation="match", operation_version="1",
                schema_version="raw-1", subject=f"match:{match_id}", fetched_at=LINKED_AT, payload=payload)
            projection = materialize_snapshot(connection, snapshot_id=snapshot_id, match_id=match_id)
            row = connection.execute(select(matches).where(matches.c.match_id == match_id)).mappings().one()
            connection.execute(update(matches).where(matches.c.match_id == match_id).values(
                evidence_state="REPLAY_READY" if parsed else "REPLAY_UNAVAILABLE",
                replay_role_assignment=projection["role_assignment"] if parsed else None,
                terminal_reason=None if parsed else "REPLAY_CHECKS_EXHAUSTED",
                replay_terminal_at=func.clock_timestamp(),
            ) if finalize else update(matches).where(matches.c.match_id == match_id).values(
                evidence_state="REPLAY_PENDING", replay_requested_at=func.clock_timestamp()))
            connection.execute(insert(account_matches).values(
                profile_id=persona["profile_id"], match_id=match_id, account_id=persona["account_id"],
                player_slot=0, lifecycle="ANALYZING" if finalize else "WAITING_FOR_PROVIDER",
                mode=row["mode"], effective_role=role, provider_started_at=row["started_at"],
                provider_source_match_id=match_id, origin=origin))
        if finalize:
            with self.engine.begin() as connection:
                enqueue_finalization(connection, profile_id=persona["profile_id"], match_id=match_id)
                job = claim(connection, priority=0 if origin == "LIVE" else 3)
            assert job is not None and job["match_id"] == match_id, "seed expects an otherwise idle queue"
            complete_finalization_job(self.engine, job_id=job["id"], lease_token=job["lease_token"])
        return match_id

    def set_link(self, persona: dict[str, Any], match_id: int, **values: Any) -> None:
        with self.engine.begin() as connection:
            connection.execute(update(account_matches).where(
                account_matches.c.profile_id == persona["profile_id"], account_matches.c.match_id == match_id,
            ).values(**values))

    def run_p3(self, job_type: str) -> str:
        with self.engine.begin() as connection:
            connection.execute(update(ingest_jobs).where(ingest_jobs.c.job_type == job_type,
                                                         ingest_jobs.c.state == "PENDING")
                               .values(run_after=func.clock_timestamp() - timedelta(days=1)))
            job = claim(connection, priority=3)
        assert job is not None and job["job_type"] == job_type
        return complete_scope_rebuild_job(self.engine, job_id=job["id"], lease_token=job["lease_token"])


def seed_demo(engine: Engine) -> dict[str, dict[str, Any]]:
    seed = Seeder(engine)
    ready = {"STANDARD": "READY", "TURBO": "READY"}

    seed.user("no_steam_linked", linked=False)

    new = seed.user("new_user_importing")
    seed.bootstrap(new, {"STANDARD": None, "TURBO": None})

    seed.bootstrap(seed.user("cold_start_ready_and_empty"), {"STANDARD": "READY", "TURBO": "NO_MATCHES_FOUND"})
    seed.bootstrap(seed.user("cold_start_gaps_and_ineligible"),
                   {"STANDARD": "READY_WITH_GAPS", "TURBO": "NO_ELIGIBLE_MATCHES"})
    blocked = seed.user("data_access_blocked")
    seed.bootstrap(blocked, {"STANDARD": "DATA_ACCESS_BLOCKED", "TURBO": "DATA_ACCESS_BLOCKED"})
    with engine.begin() as connection:
        connection.execute(update(dota_accounts).where(dota_accounts.c.account_id == blocked["account_id"])
                           .values(visibility="BLOCKED"))

    common = seed.user("ready_common")
    seed.bootstrap(common, ready)
    # 16 matches: a complete 10-point trend window (uncalibrated) and one live PB.
    ids = [seed.match(common, days=1 + index * 0.5, stack_bonus=index % 4 if index < 15 else 6)
           for index in range(16)]
    seed.match(common, days=14, turbo=True)
    with engine.begin() as connection:
        connection.execute(insert(coverage).values(
            id=str(uuid4()), profile_id=common["profile_id"], mode="STANDARD", evidence_class="SUMMARY",
            start_at=LINKED_AT - timedelta(days=90), end_at=LINKED_AT, state="KNOWN"))
        connection.execute(insert(coverage).values(
            id=str(uuid4()), profile_id=common["profile_id"], mode="STANDARD", evidence_class="REPLAY",
            start_at=LINKED_AT - timedelta(days=90), end_at=LINKED_AT - timedelta(days=60), state="GAP",
            reason="REPLAY_UNAVAILABLE"))
        # A correction on the newest match: the user's assertion wins and stays.
        correct_role(connection, profile_id=common["profile_id"], match_id=ids[-1], role="SUPPORT",
                     expected_role_revision=0)
        # A real role change rebuilds the same-bucket old/new-role closure.
        correct_role(connection, profile_id=common["profile_id"], match_id=ids[3], role="OFFLANE",
                     expected_role_revision=0)
    common["match_ids"] = ids

    states = seed.user("match_states")
    seed.bootstrap(states, ready)
    states["match_ids"] = {
        # Legitimate measured zero beside reasoned N/A replay metrics.
        "ready_replay_unavailable": seed.match(states, days=1, parsed=False, healing=0),
        "ready_not_eligible_short": seed.match(states, days=2, duration=599),
        "unavailable_role": seed.match(states, days=3, parsed=False, role=None),
        "summary_ready_replay_pending": seed.match(states, days=4, finalize=False),
    }
    waiting = seed.match(states, days=5, finalize=False)
    seed.set_link(states, waiting, lifecycle="WAITING_FOR_PRIOR_MATCH")
    failed = seed.match(states, days=6, finalize=False)
    seed.set_link(states, failed, lifecycle="ACTION_REQUIRED", failure_stage="FINALIZATION",
                  failure_reason="INTERNAL_FAILURE")
    states["match_ids"].update(waiting_for_prior=waiting, action_required=failed)

    verifier = FakeAppStoreVerifier({})
    for name, final in (("pro_active", "PRO"), ("pro_expired", "FREE")):
        persona = seed.user(name)
        seed.bootstrap(persona, ready)
        for offset in (-20, -19, -18, -17, -16, -15):
            seed.match(persona, days=offset, origin="HISTORICAL")
        seed.match(persona, days=2)
        now = datetime.now(UTC)
        verifier.transactions["transaction:" + name] = StoreTransaction(
            original_transaction_id=f"seed-{name}", user_id=persona["user_id"], product_id="tracker.pro.monthly",
            environment="Sandbox", signed_at=now - timedelta(days=2), expires_at=now + timedelta(days=28),
            revoked_at=None, auto_renew=True, digest=fake_digest(name))
        submit_transaction(engine, user_id=persona["user_id"], signed_transaction=name, verifier=verifier)
        reconcile_entitlement_scope(engine, user_id=persona["user_id"])
        seed.run_p3("SCOPE_REBUILD")
        if final == "FREE":
            verifier.transactions["notification:" + name] = StoreTransaction(
                original_transaction_id=f"seed-{name}", user_id=None, product_id="tracker.pro.monthly",
                environment="Sandbox", signed_at=now - timedelta(days=1), expires_at=now - timedelta(hours=1),
                revoked_at=None, auto_renew=False, digest=fake_digest(name + "-expired"))
            apply_notification(engine, signed_notification=name, verifier=verifier)
            seed.run_p3("SCOPE_REBUILD")

    importing = seed.user("pro_importing")
    seed.bootstrap(importing, ready)
    seed.match(importing, days=1)
    with engine.begin() as connection:
        connection.execute(insert(ingest_jobs).values(
            id=str(uuid4()), dedup_key=f"seed-backfill:{importing['profile_id']}", job_type="PRO_BACKFILL",
            priority=3, account_id=importing["account_id"], user_id=importing["user_id"], user_generation=1,
            profile_id=importing["profile_id"], profile_generation=1, state="PENDING",
            run_after=func.clock_timestamp() + timedelta(days=365), created_at=func.clock_timestamp(),
            payload={"ceiling_days": 365}))
    now = datetime.now(UTC)
    verifier.transactions["transaction:pro_importing"] = StoreTransaction(
        original_transaction_id="seed-pro-importing", user_id=importing["user_id"],
        product_id="tracker.pro.monthly", environment="Sandbox", signed_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=29), revoked_at=None, auto_renew=True, digest=fake_digest("importing"))
    submit_transaction(engine, user_id=importing["user_id"], signed_transaction="pro_importing", verifier=verifier)

    switcher = seed.user("switch_blocked_by_cooldown")
    seed.bootstrap(switcher, ready)
    switch_steam_profile(engine, user_id=switcher["user_id"], verified_target_account_id=seed.next_account)
    seed.next_account += 1

    stale = seed.user("sync_error_with_cached_data")
    seed.bootstrap(stale, ready)
    seed.match(stale, days=1)
    with engine.begin() as connection:
        connection.execute(insert(sync_state).values(
            account_id=stale["account_id"], provider="opendota", state="SYNC_ERROR",
            last_checked_at=func.clock_timestamp(), failure_count=3, blocked_reason="SYNC_PAGE_FAILED"))

    deleted = seed.user("deletion_pending")
    request_account_deletion(engine, user_id=deleted["user_id"])
    with engine.connect() as connection:
        assert connection.scalar(select(users.c.state).where(users.c.id == deleted["user_id"])) == "DELETION_PENDING"
    return seed.personas


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url or not url.startswith("postgresql"):
        raise SystemExit("DATABASE_URL must point at a migrated local PostgreSQL database")
    personas = seed_demo(create_engine(url))
    print(json.dumps({name: {"access_token": persona["access_token"]} for name, persona in personas.items()},
                     indent=2))


if __name__ == "__main__":
    main()

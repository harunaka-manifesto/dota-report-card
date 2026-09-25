"""Profile-owned, resumable search of the original pre-link history window."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import Connection, Engine, func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import Settings
from app.core.errors import OpenDotaRateLimited, OpenDotaUnavailable
from app.opendota.client import OpenDotaClient
from app.tracker.historical import enqueue_historical_batch
from app.tracker.jobs import StaleJob, authorized_job, enqueue, finish, reschedule
from app.tracker.provider_control import ProviderDeferred, ProviderGate
from app.tracker.provider_transport import ControlledTransport
from app.tracker.schema import (
    account_matches,
    bootstrap,
    bootstrap_search_items,
    coverage,
    events,
    ingest_jobs,
    profiles,
    users,
)
from app.tracker.sync import _saved_page


def request_bootstrap_search(connection: Connection, profile_id: str, *, attempt: str | None = None) -> str:
    """Start one P3 scan for both independent mode ledgers, once per profile generation."""
    owner = connection.execute(select(profiles, users.c.generation.label("user_generation"), users.c.state).join(
        users, users.c.id == profiles.c.user_id,
    ).where(profiles.c.id == profile_id)).mappings().one()
    if not owner["active"] or owner["state"] != "ACTIVE":
        raise StaleJob("Inactive bootstrap owner")
    for mode in ("STANDARD", "TURBO"):
        connection.execute(insert(bootstrap).values(profile_id=profile_id, mode=mode).on_conflict_do_nothing())
    return enqueue(
        connection, dedup_key=f"bootstrap-search:{profile_id}:{owner['generation']}:{owner['user_generation']}"
        + (f":{attempt}" if attempt else ""),
        job_type="BOOTSTRAP_SEARCH", priority=3, profile_id=profile_id, payload={},
    )


def _select_initial_candidates(connection: Connection, profile_id: str) -> None:
    """Acquire the first 30 per mode; later eligibility may require replacements."""
    for mode in ("STANDARD", "TURBO"):
        ids = list(connection.scalars(select(bootstrap_search_items.c.match_id).where(
            bootstrap_search_items.c.profile_id == profile_id,
            bootstrap_search_items.c.mode == mode,
            bootstrap_search_items.c.outcome == "CANDIDATE",
            bootstrap_search_items.c.selected_at.is_(None),
        ).order_by(bootstrap_search_items.c.started_at.desc(), bootstrap_search_items.c.match_id.desc()).limit(30)))
        if not ids:
            continue
        connection.execute(bootstrap_search_items.update().where(
            bootstrap_search_items.c.profile_id == profile_id,
            bootstrap_search_items.c.match_id.in_(ids),
        ).values(selected_at=func.clock_timestamp()))
        connection.execute(bootstrap.update().where(
            bootstrap.c.profile_id == profile_id, bootstrap.c.mode == mode,
        ).values(discovered_count=bootstrap.c.discovered_count + len(ids)))
        enqueue_historical_batch(connection, profile_id=profile_id, match_ids=ids, origin="BOOTSTRAP")


def settle_candidate(connection: Connection, *, profile_id: str, match_id: int,
                     eligible: bool, reason: str) -> int:
    """Settle one selected candidate and fill its mode's remaining Free slots."""
    connection.execute(select(profiles.c.id).where(profiles.c.id == profile_id).with_for_update()).scalar_one()
    item = connection.execute(bootstrap_search_items.update().where(
        bootstrap_search_items.c.profile_id == profile_id,
        bootstrap_search_items.c.match_id == match_id,
        bootstrap_search_items.c.selected_at.is_not(None),
        bootstrap_search_items.c.reason.is_(None),
    ).values(reason=reason).returning(bootstrap_search_items.c.mode)).scalar_one_or_none()
    if item is None:
        return 0
    mode = item
    bucket = connection.execute(select(bootstrap).where(
        bootstrap.c.profile_id == profile_id, bootstrap.c.mode == mode,
    ).with_for_update()).mappings().one()
    connection.execute(bootstrap.update().where(
        bootstrap.c.profile_id == profile_id, bootstrap.c.mode == mode,
    ).values(
        settled_count=bootstrap.c.settled_count + 1,
        eligible_count=bootstrap.c.eligible_count + int(eligible),
    ))
    pending = connection.scalar(select(func.count()).select_from(bootstrap_search_items).where(
        bootstrap_search_items.c.profile_id == profile_id,
        bootstrap_search_items.c.mode == mode,
        bootstrap_search_items.c.selected_at.is_not(None),
        bootstrap_search_items.c.reason.is_(None),
    ))
    vacancies = max(0, 30 - bucket["eligible_count"] - int(eligible) - pending)
    if not vacancies or bucket["search_finished"] is False:
        settle_bootstrap(connection, profile_id)
        return 0
    ids = list(connection.scalars(select(bootstrap_search_items.c.match_id).where(
        bootstrap_search_items.c.profile_id == profile_id,
        bootstrap_search_items.c.mode == mode,
        bootstrap_search_items.c.outcome == "CANDIDATE",
        bootstrap_search_items.c.selected_at.is_(None),
    ).order_by(bootstrap_search_items.c.started_at.desc(), bootstrap_search_items.c.match_id.desc()).limit(vacancies)))
    if not ids:
        settle_bootstrap(connection, profile_id)
        return 0
    connection.execute(bootstrap_search_items.update().where(
        bootstrap_search_items.c.profile_id == profile_id,
        bootstrap_search_items.c.match_id.in_(ids),
        bootstrap_search_items.c.selected_at.is_(None),
    ).values(selected_at=func.clock_timestamp()))
    connection.execute(bootstrap.update().where(
        bootstrap.c.profile_id == profile_id, bootstrap.c.mode == mode,
    ).values(discovered_count=bootstrap.c.discovered_count + len(ids)))
    enqueue_historical_batch(connection, profile_id=profile_id, match_ids=ids, origin="BOOTSTRAP")
    settle_bootstrap(connection, profile_id)
    return len(ids)


def settle_bootstrap(connection: Connection, profile_id: str) -> bool:
    """Persist mode outcomes only after acquisition, analyses and coverage settle."""
    linked_at = connection.execute(select(profiles.c.original_linked_at).where(
        profiles.c.id == profile_id,
    ).with_for_update()).scalar_one_or_none()
    if linked_at is None:
        return False
    floor = linked_at - timedelta(days=90)
    buckets = connection.execute(select(bootstrap).where(
        bootstrap.c.profile_id == profile_id,
    ).order_by(bootstrap.c.mode).with_for_update()).mappings().all()
    if len(buckets) != 2:
        return False

    now = connection.execute(select(func.clock_timestamp())).scalar_one()
    for bucket in buckets:
        if bucket["completed_at"] is not None or not bucket["search_finished"]:
            continue
        selected = connection.execute(select(
            bootstrap_search_items.c.match_id,
            bootstrap_search_items.c.reason,
            account_matches.c.lifecycle,
        ).select_from(bootstrap_search_items.outerjoin(
            account_matches,
            (account_matches.c.profile_id == bootstrap_search_items.c.profile_id)
            & (account_matches.c.match_id == bootstrap_search_items.c.match_id),
        )).where(
            bootstrap_search_items.c.profile_id == profile_id,
            bootstrap_search_items.c.mode == bucket["mode"],
            bootstrap_search_items.c.selected_at.is_not(None),
        )).mappings().all()
        if len(selected) != bucket["discovered_count"] or bucket["settled_count"] != bucket["discovered_count"]:
            continue
        if any(row["reason"] is None or
               (row["lifecycle"] not in {"READY", "UNAVAILABLE"} and
                not (row["lifecycle"] is None and row["reason"].startswith("UNAVAILABLE:")))
               for row in selected):
            continue
        pending = connection.scalar(select(func.count()).select_from(coverage).where(
            coverage.c.profile_id == profile_id,
            coverage.c.mode == bucket["mode"],
            coverage.c.end_at >= floor,
            coverage.c.start_at <= linked_at,
            coverage.c.state == "PENDING",
        ))
        if pending:
            continue
        gaps = connection.scalar(select(func.count()).select_from(coverage).where(
            coverage.c.profile_id == profile_id,
            coverage.c.mode == bucket["mode"],
            coverage.c.end_at >= floor,
            coverage.c.start_at <= linked_at,
            coverage.c.state == "GAP",
        ))
        if bucket["discovered_count"] == 0:
            from app.tracker.data_access import data_access_state

            account_id = connection.scalar(select(profiles.c.account_id).where(profiles.c.id == profile_id))
            outcome = ("DATA_ACCESS_BLOCKED" if data_access_state(connection, account_id) == "BLOCKED"
                       else "NO_MATCHES_FOUND")
        elif bucket["eligible_count"] == 0:
            outcome = "NO_ELIGIBLE_MATCHES"
        else:
            outcome = "READY_WITH_GAPS" if gaps else "READY"
        connection.execute(bootstrap.update().where(
            bootstrap.c.profile_id == profile_id,
            bootstrap.c.mode == bucket["mode"],
            bootstrap.c.completed_at.is_(None),
        ).values(outcome=outcome, completed_at=now))

    from app.tracker.profile import publish_profile_checkpoint

    # Settled modes publish their first coherent Profile; importing modes keep waiting.
    publish_profile_checkpoint(connection, profile_id=profile_id, cause="IMPORT")
    terminal = connection.execute(select(bootstrap).where(
        bootstrap.c.profile_id == profile_id,
    ).order_by(bootstrap.c.mode)).mappings().all()
    if len(terminal) != 2 or any(row["completed_at"] is None for row in terminal):
        return False
    payload = {row["mode"].lower(): row["outcome"] for row in terminal}
    connection.execute(insert(events).values(
        id=str(uuid4()), profile_id=profile_id, kind="BOOTSTRAP_COMPLETED",
        dedup_key=f"bootstrap-completed:{profile_id}", payload={"outcomes": payload},
        created_at=now,
    ).on_conflict_do_nothing(index_elements=[events.c.dedup_key]))
    from app.tracker.entitlement import reconcile_bootstrap_entitlement

    reconcile_bootstrap_entitlement(connection, profile_id=profile_id, now=now)
    return True


def _publish_page(connection: Connection, job: dict[str, Any], snapshot: dict[str, Any], *, max_pages: int) -> str:
    rows = snapshot["payload"]
    if not isinstance(rows, list) or len(rows) > 200:
        raise ValueError("Invalid bootstrap history page")
    connection.execute(select(profiles.c.id).where(
        profiles.c.id == job["profile_id"],
    ).with_for_update()).scalar_one()
    profile = connection.execute(select(profiles.c.original_linked_at).where(profiles.c.id == job["profile_id"])).mappings().one()
    linked_at = profile["original_linked_at"]
    floor = linked_at - timedelta(days=90)
    cursor = dict(job["cursor"] or {})
    previous = cursor.get("last_start")
    seen: set[int] = set()
    crossed_floor = False
    for raw in rows:
        if not isinstance(raw, dict) or type(raw.get("match_id")) is not int or not 0 < raw["match_id"] < 2**63:
            raise ValueError("Invalid bootstrap history item")
        match_id = raw["match_id"]
        timestamp = raw.get("start_time")
        if type(timestamp) is not int or not 0 < timestamp <= 253402300799 or match_id in seen or previous is not None and timestamp > previous:
            raise ValueError("Unordered or undated bootstrap history")
        seen.add(match_id)
        previous = timestamp
        started_at = datetime.fromtimestamp(timestamp, UTC)
        game_mode = raw.get("game_mode")
        mode = "STANDARD" if type(game_mode) is int and game_mode in (1, 22) else "TURBO" if type(game_mode) is int and game_mode == 23 else None
        reason = "AFTER_LINK" if started_at > linked_at else "BEFORE_WINDOW" if started_at < floor else "UNSUPPORTED_MODE" if mode is None else None
        if reason == "BEFORE_WINDOW":
            crossed_floor = True
        saved = connection.execute(insert(bootstrap_search_items).values(
            profile_id=job["profile_id"], source_item_id=str(match_id), snapshot_id=snapshot["id"],
            match_id=match_id if reason is None else None, started_at=started_at,
            mode=mode if reason is None else None,
            outcome="CANDIDATE" if reason is None else "REJECTED", reason=reason,
        ).on_conflict_do_nothing().returning(bootstrap_search_items.c.source_item_id)).scalar_one_or_none()
        if saved is None:
            # Offset pagination shifted under us. Do not claim complete coverage.
            raise ValueError("Bootstrap history page overlaps an earlier page")
    pages = cursor.get("pages", 0) + 1
    offset = cursor.get("offset", 0) + len(rows)
    finished = not rows or crossed_floor
    next_cursor = {"offset": offset, "pages": pages, "request_days": cursor["request_days"], "last_start": previous}
    for mode in ("STANDARD", "TURBO"):
        connection.execute(bootstrap.update().where(bootstrap.c.profile_id == job["profile_id"], bootstrap.c.mode == mode).values(
            search_finished=finished,
            cursor=next_cursor,
        ))
    if finished:
        _select_initial_candidates(connection, job["profile_id"])
        settle_bootstrap(connection, job["profile_id"])
        finish(connection, job)
        return "COMPLETE"
    if pages >= max_pages:
        reschedule(connection, job, delay_seconds=0, error="PAGINATION_LIMIT", cursor=next_cursor, max_attempts=1)
        return "FAILED"
    reschedule(connection, job, delay_seconds=0, error="NEXT_PAGE", cursor=next_cursor, failure=False)
    return "DEFERRED"


async def search_bootstrap_page(database: Engine, gate: ProviderGate, settings: Settings, *, job_id: str, lease_token: str,
                                transport: httpx.AsyncBaseTransport | None = None, max_pages: int = 100, max_attempts: int = 5) -> str:
    if gate.provider != "opendota" or type(max_pages) is not int or max_pages < 1 or type(max_attempts) is not int or max_attempts < 1:
        raise ValueError("Invalid bootstrap search policy")
    with authorized_job(database, job_id, lease_token) as (connection, job):
        if job["job_type"] != "BOOTSTRAP_SEARCH" or job["profile_id"] is None:
            raise ValueError("Expected private bootstrap search")
        cursor = dict(job["cursor"] or {})
        linked_at = connection.scalar(select(profiles.c.original_linked_at).where(profiles.c.id == job["profile_id"]))
        if linked_at is None:
            raise StaleJob("Bootstrap profile vanished")
        now = connection.execute(select(func.clock_timestamp())).scalar_one()
        days = cursor.get("request_days", max(1, int((now - (linked_at - timedelta(days=90))).total_seconds() // 86400) + 1))
        offset = cursor.get("offset", 0)
        request = httpx.Request("GET", f"{settings.opendota_base_url.rstrip('/')}/players/{job['account_id']}/matches",
                                params={"significant": 0, "limit": 200, "offset": offset, "date": days})
        subject = hashlib.sha256(request.url.raw_path + request.content).hexdigest()
        snapshot = _saved_page(connection, job_id, subject)
        if snapshot is None and cursor.get("request_lease_token") == lease_token:
            return "RUNNING"
    try:
        if snapshot is None:
            def before_send() -> None:
                with authorized_job(database, job_id, lease_token) as (connection, current):
                    if dict(current["cursor"] or {}) != cursor:
                        raise ProviderDeferred("BOOTSTRAP_STEP_ALREADY_CLAIMED", 0.1)
                    connection.execute(ingest_jobs.update().where(ingest_jobs.c.id == job_id).values(
                        cursor={**cursor, "request_days": days, "request_lease_token": lease_token},
                    ))

            controlled = ControlledTransport(gate, database, transport=transport, before_send=before_send, job_id=job_id)
            try:
                async with httpx.AsyncClient(transport=controlled) as http:
                    await OpenDotaClient(settings, http_client=http).get_history_page(job["account_id"], offset=offset, days=days)
            except OpenDotaUnavailable:
                with database.connect() as connection:
                    if _saved_page(connection, job_id, subject) is None:
                        raise
            with database.connect() as connection:
                snapshot = _saved_page(connection, job_id, subject)
            if snapshot is None:
                raise RuntimeError("Missing bootstrap history evidence")
        with authorized_job(database, job_id, lease_token) as (connection, current):
            return _publish_page(connection, current, snapshot, max_pages=max_pages)
    except StaleJob:
        raise
    except Exception as exc:
        if isinstance(exc, ProviderDeferred) and exc.reason == "BOOTSTRAP_STEP_ALREADY_CLAIMED":
            return "RUNNING"
        deferred = isinstance(exc, (ProviderDeferred, OpenDotaRateLimited))
        reason = exc.reason if isinstance(exc, ProviderDeferred) else "RATE_LIMITED" if isinstance(exc, OpenDotaRateLimited) else "BOOTSTRAP_PAGE_FAILED"
        delay = exc.delay if isinstance(exc, ProviderDeferred) else 30
        with authorized_job(database, job_id, lease_token) as (connection, current):
            reschedule(connection, current, delay_seconds=delay, error=reason, failure=not deferred, max_attempts=max_attempts)
        return "DEFERRED" if deferred or current["attempts"] < max_attempts else "FAILED"

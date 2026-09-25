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

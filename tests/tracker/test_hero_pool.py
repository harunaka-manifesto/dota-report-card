"""Hero pool: pure ranking rules and the /hero-pool contract."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.tracker import activity, hero_pool
from app.tracker.authentication import VerifiedIdentity, create_user_session
from app.tracker.mobile_api import create_mobile_app
from app.tracker.schema import account_matches, dota_accounts, profiles
from fastapi.testclient import TestClient
from sqlalchemy import update

from .builders import add_match, finalize

LINKED = datetime(2026, 3, 1, 12, tzinfo=UTC)
TOKYO = ZoneInfo("Asia/Tokyo")


def _at(day: date, hour: int = 12, zone: ZoneInfo = TOKYO) -> datetime:
    return datetime(day.year, day.month, day.day, hour, tzinfo=zone).astimezone(UTC)


def _today() -> date:
    return datetime.now(TOKYO).date()


def test_window_starts_are_inclusive_trailing_days():
    assert hero_pool.window_starts(date(2026, 9, 29)) == [date(2026, 9, 23), date(2026, 8, 31), date(2025, 9, 30)]
    assert hero_pool.CONTRACT == "hero-pool-v1" and hero_pool.TOP_N == 10


def test_build_roles_orders_by_matches_recency_then_hero_id():
    today = date(2026, 9, 29)
    early, late = datetime(2026, 9, 1, tzinfo=UTC), datetime(2026, 9, 2, tzinfo=UTC)
    rows = [("CARRY", 9, 1, 3, 3, early), ("CARRY", 5, 1, 3, 3, late), ("CARRY", 2, 1, 3, 3, late),
            ("CARRY", 7, 0, 4, 4, early), ("CARRY", 8, 0, 0, 1, early), ("MID", 1, 0, 0, 0, early),
            ("SUPPORT", 4, 2, 2, 2, early), (None, 3, 5, 5, 5, early)]
    roles = {entry["role"]: entry for entry in hero_pool.build_roles(rows, today)}
    assert list(roles) == ["CARRY", "MID", "OFFLANE", "SUPPORT"]
    assert [w["window"] for w in roles["CARRY"]["windows"]] == ["LAST_7_DAYS", "LAST_30_DAYS", "LAST_365_DAYS"]
    week, month, year = roles["CARRY"]["windows"]
    assert [h["hero_id"] for h in week["heroes"]] == [2, 5, 9]  # equal matches: latest play, then hero id
    assert [(h["hero_id"], h["matches"]) for h in month["heroes"]] == [(7, 4), (2, 3), (5, 3), (9, 3)]
    assert year["total_matches"] == 14 and week["start_date"] == date(2026, 9, 23) and week["end_date"] == today
    assert roles["MID"]["windows"][2] == {"window": "LAST_365_DAYS", "start_date": date(2025, 9, 30),
                                           "end_date": today, "total_matches": 0, "heroes": []}
    assert roles["SUPPORT"]["windows"][0]["heroes"] == [{"hero_id": 4, "matches": 2}]


def test_build_roles_cuts_to_top_ten_but_totals_all_heroes():
    now = datetime(2026, 9, 1, tzinfo=UTC)
    rows = [("MID", hero, 0, 0, 1, now) for hero in range(1, 12)]
    year = hero_pool.build_roles(rows, date(2026, 9, 29))[1]["windows"][2]
    assert year["total_matches"] == 11 and [h["hero_id"] for h in year["heroes"]] == list(range(1, 11))


def _client(database, subject: str, *, scope: str = "FREE", linked: datetime = LINKED):
    user_id, tokens = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", subject, None))
    profile_id = f"profile-{subject}"
    with database.begin() as connection:
        connection.execute(dota_accounts.insert().values(account_id=1001))
        connection.execute(profiles.insert().values(
            id=profile_id, user_id=user_id, account_id=1001, active=True,
            original_linked_at=linked, active_scope=scope))
    return (TestClient(create_mobile_app(Settings(), database=database)),
            {"Authorization": f"Bearer {tokens.access_token}"}, profile_id)


def _link(database, profile_id, index, at, *, hero_id=1, role="CARRY", lifecycle="READY", mode=None,
          origin="LIVE"):
    """A stored match played by `hero_id`, finalized when READY, then re-timed to `at` (fixtures only).

    Non-READY rows must take the highest indexes so they never block chronological finalization.
    """
    match_id = add_match(database, profile_id, index=index, origin=origin, role=role,
                         edit=lambda payload: payload["players"][0].__setitem__("hero_id", hero_id))
    values = {"provider_started_at": at, "effective_role": role}
    if lifecycle == "READY":
        assert finalize(database, profile_id, match_id) == "READY"
    else:
        values["lifecycle"] = lifecycle
    if mode is not None:
        values["mode"] = mode
    with database.begin() as connection:
        connection.execute(update(account_matches).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == match_id,
        ).values(**values))
    return match_id


def _get(client, headers, zone="Asia/Tokyo"):
    return client.get("/hero-pool", params={"time_zone": zone}, headers=headers)


def _window(body, role, window):
    role_view = next(r for r in body["roles"] if r["role"] == role)
    return next(w for w in role_view["windows"] if w["window"] == window)


def _heroes(body, role, window):
    return [(h["hero_id"], h["matches"]) for h in _window(body, role, window)["heroes"]]


def test_hero_pool_counts_ready_standard_and_turbo_only(database):
    client, headers, profile_id = _client(database, "pool-owner")
    now = datetime.now(UTC) - timedelta(hours=1)
    _link(database, profile_id, 0, now, hero_id=11)
    _link(database, profile_id, 1, now, hero_id=11, mode="TURBO")
    _link(database, profile_id, 2, now - timedelta(minutes=5), hero_id=22)
    _link(database, profile_id, 3, now, hero_id=33, mode="UNSUPPORTED")
    _link(database, profile_id, 4, now, hero_id=44, lifecycle="ANALYZING")
    _link(database, profile_id, 5, now, hero_id=55, lifecycle="UNAVAILABLE")

    response = _get(client, headers)
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "hero-pool-v1" and body["time_zone"] == "Asia/Tokyo"
    assert [r["role"] for r in body["roles"]] == ["CARRY", "MID", "OFFLANE", "SUPPORT"]
    assert _heroes(body, "CARRY", "LAST_7_DAYS") == [(11, 2), (22, 1)]
    assert _window(body, "CARRY", "LAST_365_DAYS")["total_matches"] == 3
    assert body["partial_ranges"] == []

    # Role correction moves the hero to the new role.
    with database.begin() as connection:
        connection.execute(update(account_matches).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == 9_100_000_002,
        ).values(effective_role="SUPPORT"))
    moved = _get(client, headers).json()
    assert _heroes(moved, "CARRY", "LAST_7_DAYS") == [(11, 2)]
    assert _heroes(moved, "SUPPORT", "LAST_7_DAYS") == [(22, 1)]

    etag = _get(client, headers).headers["ETag"]
    again = client.get("/hero-pool", params={"time_zone": "Asia/Tokyo"},
                       headers={**headers, "If-None-Match": etag})
    assert again.status_code == 304


def test_hero_pool_window_boundaries_in_local_time(database):
    client, headers, profile_id = _client(database, "pool-bounds", linked=datetime(2020, 1, 1, tzinfo=UTC))
    today = _today()
    starts = hero_pool.window_starts(today)
    # Local 00:00 of a window's first day is inside; one minute earlier is the previous local day.
    for index, (start, hero) in enumerate(zip(starts, (1, 2, 3), strict=True)):
        first = datetime.combine(start, datetime.min.time(), TOKYO)
        _link(database, profile_id, 2 * index, first.astimezone(UTC), hero_id=hero)
        _link(database, profile_id, 2 * index + 1, (first - timedelta(minutes=1)).astimezone(UTC),
              hero_id=hero + 10)
    body = _get(client, headers).json()
    assert body["today"] == today.isoformat()
    week, month, year = (_window(body, "CARRY", name) for name in ("LAST_7_DAYS", "LAST_30_DAYS", "LAST_365_DAYS"))
    assert [w["start_date"] for w in (week, month, year)] == [d.isoformat() for d in starts]
    assert [h["hero_id"] for h in week["heroes"]] == [1]
    assert sorted(h["hero_id"] for h in month["heroes"]) == [1, 2, 11]
    assert sorted(h["hero_id"] for h in year["heroes"]) == [1, 2, 3, 11, 12]
    assert (week["total_matches"], month["total_matches"], year["total_matches"]) == (1, 3, 5)


def test_hero_pool_returns_ten_heroes_but_totals_every_match(database):
    client, headers, profile_id = _client(database, "pool-cut")
    now = datetime.now(UTC) - timedelta(hours=1)
    for index in range(11):
        _link(database, profile_id, index, now - timedelta(minutes=index), hero_id=index + 1, role="MID")
    body = _get(client, headers).json()
    week = _window(body, "MID", "LAST_7_DAYS")
    assert week["total_matches"] == 11 and len(week["heroes"]) == 10
    assert [h["hero_id"] for h in week["heroes"]] == list(range(1, 11))  # equal counts: most recent first


def test_hero_pool_empty_shape_without_matches_or_profile(database):
    client, headers, _ = _client(database, "pool-empty")
    body = _get(client, headers).json()
    assert body["partial_ranges"] == [] and len(body["roles"]) == 4
    for role in body["roles"]:
        assert [w["window"] for w in role["windows"]] == ["LAST_7_DAYS", "LAST_30_DAYS", "LAST_365_DAYS"]
        assert all(w["total_matches"] == 0 and w["heroes"] == [] for w in role["windows"])
    with database.begin() as connection:
        connection.execute(profiles.update().where(profiles.c.id == "profile-pool-empty").values(active=False))
    assert _get(client, headers).json()["roles"] == body["roles"]


def test_hero_pool_scope_and_bootstrap_partial_range(database):
    linked = datetime.now(UTC) - timedelta(days=5)
    client, headers, profile_id = _client(database, "pool-scope", linked=linked)
    _link(database, profile_id, 0, linked - timedelta(days=10), hero_id=7, origin="BOOTSTRAP")
    _link(database, profile_id, 1, linked - timedelta(days=20), hero_id=8, origin="HISTORICAL")
    _link(database, profile_id, 2, linked + timedelta(days=1), hero_id=9)

    free = _get(client, headers, "UTC").json()
    assert _heroes(free, "CARRY", "LAST_365_DAYS") == [(9, 1), (7, 1)]
    first = (linked - timedelta(days=10)).date().isoformat()
    assert free["partial_ranges"] == [
        {"start_date": first, "end_date": linked.date().isoformat(), "reason": "BOOTSTRAP_SAMPLE"}]

    with database.begin() as connection:
        connection.execute(profiles.update().where(profiles.c.id == profile_id).values(active_scope="PRO"))
    pro = _get(client, headers, "UTC").json()
    assert _heroes(pro, "CARRY", "LAST_365_DAYS") == [(9, 1), (7, 1), (8, 1)]
    assert pro["partial_ranges"] == []  # backfill covers the pre-link span


def test_hero_pool_total_matches_the_activity_heatmap(database):
    client, headers, profile_id = _client(database, "pool-consistency")
    now = datetime.now(UTC) - timedelta(hours=1)
    for index, role in enumerate(("CARRY", "CARRY", "MID", "SUPPORT", "OFFLANE")):
        _link(database, profile_id, index, now - timedelta(days=index * 40), hero_id=index + 1, role=role)
    pool = _get(client, headers).json()
    heat = client.get("/activity", params={"time_zone": "Asia/Tokyo"}, headers=headers).json()
    for series in heat["series"]:
        if series["role"] != "ALL":
            assert _window(pool, series["role"], "LAST_365_DAYS")["total_matches"] == series["total_matches"]
    assert activity.ROLES == tuple(r["role"] for r in pool["roles"])


def test_hero_pool_rejects_bad_zone(database):
    client, headers, _ = _client(database, "pool-zone")
    response = _get(client, headers, "Not/AZone")
    assert response.status_code == 400 and response.json()["code"] == "TIME_ZONE_INVALID"

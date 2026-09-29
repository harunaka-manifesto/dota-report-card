"""Activity heatmap: pure day/level rules and the /activity + /history drill-in contract."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from app.core.config import Settings
from app.tracker import activity
from app.tracker.authentication import VerifiedIdentity, create_user_session
from app.tracker.mobile_api import DEVELOPMENT_CURSOR_SECRET, _cursor, create_mobile_app
from app.tracker.schema import account_matches, dota_accounts, profiles
from fastapi.testclient import TestClient
from sqlalchemy import update

from .builders import add_match, finalize

LINKED = datetime(2026, 3, 1, 12, tzinfo=UTC)


def test_levels_follow_heatmap_levels_v1():
    assert [activity.level_for_count(n) for n in (0, 1, 2, 3, 4, 5, 6, 20)] == [0, 1, 2, 2, 3, 3, 4, 4]
    assert activity.LEVELS_VERSION == "heatmap-levels-v1"


def test_windows_trailing_year_calendar_year_and_bounds():
    today = date(2026, 9, 29)
    assert activity.resolve_window(today, None) == (date(2025, 9, 30), today)
    assert activity.resolve_window(today, 2025) == (date(2025, 1, 1), date(2025, 12, 31))
    assert activity.resolve_window(today, 2026) == (date(2026, 1, 1), today)
    assert activity.resolve_window(date(2024, 12, 31), None)[0] == date(2024, 1, 2)  # leap year
    for bad in (2010, 2027):
        with pytest.raises(ValueError):
            activity.resolve_window(today, bad)


def test_utc_bounds_respect_dst_days():
    ny = ZoneInfo("America/New_York")
    start, end = activity.utc_bounds(date(2026, 3, 8), date(2026, 3, 8), ny)  # spring forward
    assert end - start == timedelta(hours=23)
    start, end = activity.utc_bounds(date(2026, 10, 25), date(2026, 10, 25), ZoneInfo("Europe/Berlin"))
    assert end - start == timedelta(hours=25)  # fall back
    assert start == datetime(2026, 10, 24, 22, tzinfo=UTC)


def test_build_series_sums_all_and_skips_unknown_roles():
    rows = [(date(2026, 1, 2), "CARRY", 2), (date(2026, 1, 1), "SUPPORT", 6), (date(2026, 1, 2), None, 3)]
    series = {entry["role"]: entry for entry in activity.build_series(rows)}
    assert list(series) == ["ALL", "CARRY", "MID", "OFFLANE", "SUPPORT"]
    assert series["ALL"]["total_matches"] == 8
    assert [(d["date"], d["count"], d["level"]) for d in series["ALL"]["days"]] == [
        (date(2026, 1, 1), 6, 4), (date(2026, 1, 2), 2, 2)]
    assert series["MID"] == {"role": "MID", "total_matches": 0, "days": []}


def _client(database, subject: str, *, scope: str = "FREE"):
    user_id, tokens = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", subject, None))
    profile_id = f"profile-{subject}"
    with database.begin() as connection:
        connection.execute(dota_accounts.insert().values(account_id=1001))
        connection.execute(profiles.insert().values(
            id=profile_id, user_id=user_id, account_id=1001, active=True,
            original_linked_at=LINKED, active_scope=scope))
    return (TestClient(create_mobile_app(Settings(), database=database)),
            {"Authorization": f"Bearer {tokens.access_token}"}, profile_id)


def _link(database, profile_id, index, at, *, role="CARRY", lifecycle="READY", mode=None,
          origin="LIVE"):
    """A stored match, finalized when READY, then re-timed to `at` (fixtures only).

    Non-READY rows must take the highest indexes so they never block chronological finalization.
    """
    match_id = add_match(database, profile_id, index=index, origin=origin, role=role)
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


def _series(body, role):
    return {d["date"]: d["count"] for d in next(s for s in body["series"] if s["role"] == role)["days"]}


def test_activity_counts_ready_matches_by_local_day_and_role(database):
    client, headers, profile_id = _client(database, "activity-owner")
    # 2026-03-10 23:30 in Tokyo is 14:30 UTC; 2026-03-10 16:00 UTC is 03-11 in Tokyo.
    _link(database, profile_id, 0, datetime(2026, 3, 10, 14, 30, tzinfo=UTC), role="CARRY")
    _link(database, profile_id, 1, datetime(2026, 3, 10, 16, 0, tzinfo=UTC), role="CARRY", mode="TURBO")
    _link(database, profile_id, 2, datetime(2026, 3, 10, 16, 5, tzinfo=UTC), role="OFFLANE")
    _link(database, profile_id, 3, datetime(2026, 3, 10, 18, tzinfo=UTC), mode="UNSUPPORTED")
    _link(database, profile_id, 4, datetime(2026, 3, 10, 17, tzinfo=UTC), lifecycle="ANALYZING")
    _link(database, profile_id, 5, datetime(2026, 3, 10, 19, tzinfo=UTC), lifecycle="UNAVAILABLE")

    response = client.get("/activity", params={"time_zone": "Asia/Tokyo", "year": 2026}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "activity-heatmap-v1" and body["levels_version"] == "heatmap-levels-v1"
    assert _series(body, "CARRY") == {"2026-03-10": 1, "2026-03-11": 1}
    assert _series(body, "OFFLANE") == {"2026-03-11": 1}
    assert _series(body, "ALL") == {"2026-03-10": 1, "2026-03-11": 2}
    assert next(s for s in body["series"] if s["role"] == "ALL")["total_matches"] == 3
    assert body["window"]["start_date"] == "2026-03-10"  # cropped to the first visible match day
    assert body["available_years"] == [2026] and body["partial_ranges"] == []

    utc = client.get("/activity", params={"time_zone": "UTC", "year": 2026}, headers=headers).json()
    assert _series(utc, "ALL") == {"2026-03-10": 3}

    etag = response.headers["ETag"]
    again = client.get("/activity", params={"time_zone": "Asia/Tokyo", "year": 2026},
                       headers={**headers, "If-None-Match": etag})
    assert again.status_code == 304

    # A role correction moves the cell to the new role.
    with database.begin() as connection:
        connection.execute(update(account_matches).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == 9_100_000_002,
        ).values(effective_role="SUPPORT"))
    moved = client.get("/activity", params={"time_zone": "Asia/Tokyo", "year": 2026}, headers=headers).json()
    assert _series(moved, "OFFLANE") == {} and _series(moved, "SUPPORT") == {"2026-03-11": 1}

    assert client.get("/activity", params={"time_zone": "Not/AZone"}, headers=headers).status_code == 400
    assert client.get("/activity", params={"time_zone": "UTC", "year": 2010}, headers=headers).status_code == 400
    assert client.get("/activity", params={"time_zone": "UTC", "year": 2099}, headers=headers).status_code == 400
    assert client.get("/activity", params={"time_zone": "UTC", "year": 2025},
                      headers=headers).json()["window"] is None


def test_activity_scope_years_and_bootstrap_sample(database):
    client, headers, profile_id = _client(database, "activity-scope")
    _link(database, profile_id, 0, datetime(2026, 2, 20, 12, tzinfo=UTC), origin="BOOTSTRAP")
    _link(database, profile_id, 1, datetime(2025, 6, 1, 12, tzinfo=UTC), origin="HISTORICAL")
    _link(database, profile_id, 2, datetime(2026, 3, 5, 12, tzinfo=UTC))

    free = client.get("/activity", params={"time_zone": "UTC", "year": 2026}, headers=headers).json()
    assert free["available_years"] == [2026]
    assert free["window"]["start_date"] == "2026-02-20"
    assert free["partial_ranges"] == [
        {"start_date": "2026-02-20", "end_date": "2026-03-01", "reason": "BOOTSTRAP_SAMPLE"}]
    assert client.get("/activity", params={"time_zone": "UTC", "year": 2025},
                      headers=headers).json()["window"] is None

    with database.begin() as connection:
        connection.execute(profiles.update().where(profiles.c.id == profile_id).values(active_scope="PRO"))
    pro = client.get("/activity", params={"time_zone": "UTC", "year": 2025}, headers=headers).json()
    assert pro["available_years"] == [2026, 2025]
    assert pro["window"] == {"start_date": "2025-06-01", "end_date": "2025-12-31"}
    assert _series(pro, "ALL") == {"2025-06-01": 1}
    # Backfill covers the pre-link span, so the bootstrap sample is no longer partial.
    assert client.get("/activity", params={"time_zone": "UTC", "year": 2026},
                      headers=headers).json()["partial_ranges"] == []


def test_history_local_day_drill_in_matches_the_cell(database):
    client, headers, profile_id = _client(database, "activity-history")
    for index in range(3):
        _link(database, profile_id, index, datetime(2026, 3, 10, 14 + index, tzinfo=UTC))
    _link(database, profile_id, 3, datetime(2026, 3, 11, 18, tzinfo=UTC))
    _link(database, profile_id, 4, datetime(2026, 3, 10, 18, tzinfo=UTC), lifecycle="ANALYZING")
    params = {"local_date": "2026-03-10", "time_zone": "UTC", "ready_only": "true", "limit": 2}

    first = client.get("/history", params=params, headers=headers).json()
    assert len(first["matches"]) == 2 and first["next_cursor"]
    second = client.get("/history", params={**params, "cursor": first["next_cursor"]}, headers=headers).json()
    assert len(second["matches"]) == 1 and second["next_cursor"] is None
    everything = client.get("/history", params={"local_date": "2026-03-10", "time_zone": "UTC"},
                            headers=headers).json()
    assert len(everything["matches"]) == 4  # all lifecycles without ready_only

    # The cursor is bound to the day filter.
    moved = {**params, "local_date": "2026-03-11", "cursor": first["next_cursor"]}
    assert client.get("/history", params=moved, headers=headers).status_code == 400
    ref = first["next_cursor"].split(".")[0]
    assert client.get("/history", params={"cursor": first["next_cursor"]}, headers=headers).status_code == 400
    unfiltered = _cursor(DEVELOPMENT_CURSOR_SECRET, profile_id, ref, "ALL", None, 0)
    assert client.get("/history", params={**params, "cursor": unfiltered}, headers=headers).status_code == 400

    assert client.get("/history", params={"local_date": "2026-03-10"}, headers=headers).status_code == 400
    assert client.get("/history", params={"time_zone": "UTC"}, headers=headers).status_code == 200


def test_zone_names_postgres_reads_as_abbreviations_bucket_like_the_drill_in(database):
    client, headers, profile_id = _client(database, "activity-cet")
    # 22:30Z on 10 July is 00:30 on 11 July in CET summer time; PostgreSQL alone reads CET as +01.
    _link(database, profile_id, 0, datetime(2026, 7, 10, 22, 30, tzinfo=UTC))
    body = client.get("/activity", params={"time_zone": "CET", "year": 2026}, headers=headers).json()
    assert _series(body, "ALL") == {"2026-07-11": 1}
    drill = client.get("/history", params={"local_date": "2026-07-11", "time_zone": "CET",
                                           "ready_only": "true"}, headers=headers).json()
    assert len(drill["matches"]) == 1


def test_available_years_never_advertise_unrequestable_years(database):
    client, headers, profile_id = _client(database, "activity-years")
    _link(database, profile_id, 0, datetime(2010, 6, 1, tzinfo=UTC))
    _link(database, profile_id, 1, datetime(2026, 3, 5, 12, tzinfo=UTC))
    _link(database, profile_id, 2, datetime.now(UTC) + timedelta(days=400))
    body = client.get("/activity", params={"time_zone": "UTC"}, headers=headers).json()
    assert body["available_years"] == [2026]
    for year in body["available_years"]:
        assert client.get("/activity", params={"time_zone": "UTC", "year": year},
                          headers=headers).status_code == 200


def test_time_zone_validation_is_shared_by_every_route(database):
    client, headers, _ = _client(database, "activity-zones")
    for zone in ("posixrules", "", "../etc", "Not/AZone"):
        assert client.get("/activity", params={"time_zone": zone}, headers=headers).status_code == 400
        assert client.get("/hero-pool", params={"time_zone": zone}, headers=headers).status_code == 400
        assert client.get("/home", params={"time_zone": zone, "mode": "STANDARD"},
                          headers=headers).status_code == 400
        assert client.get("/history", params={"local_date": "2026-03-10", "time_zone": zone},
                          headers=headers).status_code == 400

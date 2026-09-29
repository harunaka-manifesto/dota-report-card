"""Matches list: sessions, placeholder names, search and the /matches contract."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from app.tracker import hero_references, match_list
from app.tracker.match_list import Fact
from app.tracker.schema import matches
from sqlalchemy import update

from .test_hero_pool import _client, _link

TOKYO = ZoneInfo("Asia/Tokyo")
T0 = datetime(2026, 9, 29, 10, tzinfo=UTC)  # Tuesday 19:00 in Tokyo


def _fact(ref: str, start: datetime, *, duration: int | None = 1800, hero_id: int = 2, role: str | None = "OFFLANE",
          mode: str = "STANDARD", won: bool | None = True, source_id: int = 1) -> Fact:
    return Fact(ref=ref, started_at=start, source_id=source_id, duration_seconds=duration, hero_id=hero_id,
                role=role, mode=mode, won=won)


def _refs(groups):
    return [[fact.ref for fact in group] for group in groups]


def test_gap_is_measured_from_the_previous_end_and_three_hours_splits():
    first = _fact("a", T0, duration=3600)
    joined = _fact("b", T0 + timedelta(hours=3, minutes=59), source_id=2)  # 2h59m after a ended
    split = _fact("c", joined.ended_at + timedelta(hours=3), source_id=3)  # exactly 3h
    assert _refs(match_list.sessions([split, first, joined])) == [["a", "b"], ["c"]]


def test_missing_duration_counts_as_ending_at_start_and_ties_use_source_id():
    waiting = _fact("w", T0, duration=None)
    later = _fact("x", T0 + timedelta(hours=2, minutes=59), source_id=5)
    tied = _fact("y", T0, source_id=0)
    assert _refs(match_list.sessions([later, waiting, tied])) == [["y", "w", "x"]]
    assert _refs(match_list.sessions([waiting, _fact("z", T0 + timedelta(hours=3), source_id=9)])) == [["w"], ["z"]]


def test_placeholder_names_follow_day_part_and_dominant_focus():
    axe, mars = 2, 129
    run = [_fact("a", T0, hero_id=axe), _fact("b", T0 + timedelta(hours=1), hero_id=mars),
           _fact("c", T0 + timedelta(hours=2), hero_id=axe)]
    assert match_list.placeholder_name(run, TOKYO) == "Tuesday evening Axe run"
    mixed = [_fact(str(i), T0 + timedelta(hours=i), hero_id=hero, role="OFFLANE")
             for i, hero in enumerate((axe, mars, 7))]
    assert match_list.placeholder_name(mixed, TOKYO) == "Tuesday evening Offlane grind"
    turbo = [_fact(str(i), T0 + timedelta(hours=i), hero_id=hero, role=role, mode="TURBO")
             for i, (hero, role) in enumerate(((axe, "CARRY"), (mars, "MID"), (7, "SUPPORT")))]
    assert match_list.placeholder_name(turbo, TOKYO) == "Tuesday evening Turbo session"
    assert match_list.placeholder_name([_fact("a", T0, hero_id=axe)], TOKYO) == "Tuesday evening Axe game"
    # 01:00 local keeps its own calendar weekday; unknown heroes fall back to the role.
    night = datetime(2026, 9, 30, 1, tzinfo=TOKYO)
    assert match_list.placeholder_name([_fact("a", night, hero_id=999)], TOKYO) == "Wednesday late-night game"
    two = [_fact("a", T0, hero_id=axe), _fact("b", T0 + timedelta(hours=1), hero_id=mars)]
    assert match_list.placeholder_name(two, TOKYO) == "Tuesday evening Mars run"  # 50% tie: latest played
    assert match_list.placeholder_name(run, ZoneInfo("Europe/London")) == "Tuesday morning Axe run"


def test_header_counts_known_results_and_the_played_span():
    members = [_fact("a", T0, duration=1200, won=True), _fact("b", T0 + timedelta(hours=1), duration=3000, won=False),
               _fact("c", T0 + timedelta(hours=2), duration=None, won=None)]
    assert match_list.header(members) == {"started_at": T0, "ended_at": T0 + timedelta(hours=2),
                                          "wins": 1, "losses": 1, "match_count": 3}


def test_hero_search_uses_aliases_words_and_prefixes():
    assert hero_references.match_heroes("AM") == {1}
    assert hero_references.match_heroes("shadow") == {11, 27, 79}
    assert hero_references.match_heroes("Nature's") == hero_references.match_heroes("natures") == {53}
    assert hero_references.match_heroes("antimage") == {1}
    assert hero_references.match_heroes("a") == set()  # prefixes need two letters
    assert hero_references.match_heroes("win", prefix=False) == set()
    assert len(hero_references.HEROES) == 127 and hero_references.name(2) == "Axe"


def test_query_terms_are_anded_and_match_hero_role_mode_result_or_session_name():
    axe_win = _fact("a", T0, hero_id=2, role="OFFLANE", won=True)
    wr_loss = _fact("b", T0, hero_id=21, role="SUPPORT", mode="TURBO", won=False)
    name = "Tuesday evening grind with friends"

    def hits(query):
        terms = match_list.parse_query(query)
        return [fact.ref for fact in (axe_win, wr_loss) if match_list.matches_query(terms, fact, name)]

    assert hits("axe") == ["a"]
    assert hits("wr") == ["b"]
    assert hits("win") == ["a"]  # a result word, not every hero named Win…
    assert hits("pos3") == hits("offlane") == ["a"]
    assert hits("turbo loss") == ["b"]
    assert hits("axe turbo") == []
    assert hits("FRIENDS") == ["a", "b"]
    assert hits("  ") == ["a", "b"]


# --- /matches contract --------------------------------------------------------------------------

BASE = datetime(2026, 9, 1, 10, tzinfo=UTC)


def _duration(database, match_id: int, seconds: int) -> None:
    with database.begin() as connection:
        connection.execute(update(matches).where(matches.c.match_id == match_id).values(duration_seconds=seconds))


def _get(client, headers, **params):
    response = client.get("/matches", params={"time_zone": "Asia/Tokyo", **params}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _layout(body):
    return [(session["session_ref"], [row["hero_id"] for row in session["matches"]]) for session in body["sessions"]]


def _seed(database, profile_id):
    """Two sessions: heroes 2, 2, 21 in the evening, and 21 plus a Turbo 7 the next day."""
    ids = [
        _link(database, profile_id, 0, BASE, hero_id=2, role="OFFLANE"),
        _link(database, profile_id, 1, BASE + timedelta(hours=1), hero_id=2, role="OFFLANE"),
        _link(database, profile_id, 2, BASE + timedelta(hours=2), hero_id=21, role="SUPPORT"),
        _link(database, profile_id, 3, BASE + timedelta(days=1), hero_id=21, role="SUPPORT"),
        _link(database, profile_id, 4, BASE + timedelta(days=1, hours=1), hero_id=7, role="CARRY", mode="TURBO"),
    ]
    for match_id in ids:
        _duration(database, match_id, 1800)
    return ids


def test_matches_groups_sessions_with_facts_and_hides_unsupported_modes(database):
    client, headers, profile_id = _client(database, "list-owner", scope="PRO")
    _seed(database, profile_id)
    # Unsupported mode between the two sessions: never listed, never a bridge.
    _link(database, profile_id, 5, BASE + timedelta(hours=12), hero_id=99, mode="UNSUPPORTED")

    body = _get(client, headers)
    assert body["contract_version"] == "matches-list-v1" and body["has_matches"] is True
    assert [heroes for _, heroes in _layout(body)] == [[7, 21], [21, 2, 2]]
    newest, oldest = body["sessions"]
    assert oldest["name"] == "Tuesday evening Axe run" and oldest["name_is_custom"] is False
    assert oldest["local_date"] == "2026-09-01" and oldest["match_count"] == 3
    assert datetime.fromisoformat(oldest["started_at"]) == BASE
    assert datetime.fromisoformat(oldest["ended_at"]) == BASE + timedelta(hours=2, minutes=30)
    assert oldest["wins"] + oldest["losses"] == 3
    row = oldest["matches"][0]
    assert {"kills", "deaths", "assists", "won", "role", "mode", "lifecycle"} <= set(row)
    assert all(isinstance(row[key], int) for key in ("kills", "deaths", "assists"))
    assert row["lifecycle"] == "READY" and row["role"] == "SUPPORT"
    assert not {"metrics", "performance_state", "state", "verdict", "score"} & set(row)


def test_filters_and_search_narrow_rows_but_never_change_sessions(database):
    client, headers, profile_id = _client(database, "filter-owner", scope="PRO")
    _seed(database, profile_id)
    full = {s["session_ref"]: s for s in _get(client, headers)["sessions"]}

    for params, expected in (
        ({"hero": [2]}, [[2, 2]]),
        ({"hero": [2, 7]}, [[7], [2, 2]]),
        ({"role": "SUPPORT"}, [[21], [21]]),
        ({"mode": "TURBO"}, [[7]]),
        ({"from": "2026-09-02", "to": "2026-09-02"}, [[7, 21]]),
        ({"q": "wr"}, [[21], [21]]),
        ({"q": "axe offlane"}, [[2, 2]]),
        ({"q": "tuesday"}, [[21, 2, 2]]),
    ):
        body = _get(client, headers, **params)
        assert [heroes for _, heroes in _layout(body)] == expected, params
        for session in body["sessions"]:
            head = {k: v for k, v in session.items() if k != "matches"}
            assert head == {k: v for k, v in full[session["session_ref"]].items() if k != "matches"}

    empty = _get(client, headers, hero=[50])
    assert empty["sessions"] == [] and empty["has_matches"] is True


def test_pagination_splits_a_session_and_binds_the_cursor_to_filters(database):
    client, headers, profile_id = _client(database, "page-owner", scope="PRO")
    _seed(database, profile_id)
    first = _get(client, headers, limit=3)
    assert [heroes for _, heroes in _layout(first)] == [[7, 21], [21]]
    second = _get(client, headers, limit=3, cursor=first["next_cursor"])
    assert [heroes for _, heroes in _layout(second)] == [[2, 2]] and second["next_cursor"] is None
    assert first["sessions"][1]["session_ref"] == second["sessions"][0]["session_ref"]

    changed = client.get("/matches", params={"time_zone": "Asia/Tokyo", "limit": 3, "role": "SUPPORT",
                                             "cursor": first["next_cursor"]}, headers=headers)
    assert changed.status_code == 400 and changed.json()["code"] == "CURSOR_INVALID"
    forged = client.get("/matches", params={"time_zone": "Asia/Tokyo", "cursor": "nope.abc"}, headers=headers)
    assert forged.json()["code"] == "CURSOR_INVALID"


def test_request_validation(database):
    client, headers, _ = _client(database, "validate-owner")
    for params, code in (({"time_zone": "Mars/Base"}, "TIME_ZONE_INVALID"),
                         ({"time_zone": "UTC", "from": "2026-09-02", "to": "2026-09-01"}, "DATE_RANGE_INVALID"),
                         ({"time_zone": "UTC", "hero": 0}, "HERO_INVALID")):
        response = client.get("/matches", params=params, headers=headers)
        assert response.status_code == 400 and response.json()["code"] == code
    assert client.get("/matches", params={"time_zone": "UTC", "hero": list(range(1, 12))},
                      headers=headers).status_code == 422
    assert client.get("/matches", params={"time_zone": "UTC"}).status_code == 401


def test_free_scope_builds_sessions_from_entitled_matches_only(database):
    linked = BASE + timedelta(hours=1, minutes=30)
    client, headers, profile_id = _client(database, "free-owner", linked=linked)
    _seed(database, profile_id)
    body = _get(client, headers)
    # The two pre-link LIVE matches are outside Free scope, so the evening session starts at 21.
    assert [heroes for _, heroes in _layout(body)] == [[7, 21], [21]]
    assert body["sessions"][1]["match_count"] == 1


def _rename(client, headers, ref, name, key="rename-key-1"):
    return client.post(f"/matches/sessions/{ref}/name", params={"time_zone": "Asia/Tokyo"},
                       json={"name": name}, headers={**headers, "Idempotency-Key": key})


def test_rename_reset_idempotency_and_ownership(database):
    client, headers, profile_id = _client(database, "rename-owner", scope="PRO")
    _seed(database, profile_id)
    oldest = _get(client, headers)["sessions"][1]

    renamed = _rename(client, headers, oldest["session_ref"], "  Stack   with   Ken  ")
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "Stack with Ken" and renamed.json()["name_is_custom"] is True
    assert _get(client, headers, q="ken")["sessions"][0]["session_ref"] == oldest["session_ref"]
    replay = _rename(client, headers, oldest["session_ref"], "  Stack   with   Ken  ")
    assert replay.json() == renamed.json()
    assert _rename(client, headers, oldest["session_ref"], "Other").json()["code"] == "IDEMPOTENCY_CONFLICT"

    reset = _rename(client, headers, oldest["session_ref"], None, key="rename-key-2")
    assert reset.json()["name"] == "Tuesday evening Axe run" and reset.json()["name_is_custom"] is False

    member = oldest["matches"][0]["ref"]  # a member that is not the session's first match
    assert _rename(client, headers, member, "x", key="rename-key-3").status_code == 404
    for bad in ("", "   ", "x" * 41, "tab\u0007bell"):
        assert _rename(client, headers, oldest["session_ref"], bad, key="rename-key-4").status_code == 422


def test_a_bridging_match_merges_sessions_and_keeps_the_latest_name(database):
    client, headers, profile_id = _client(database, "merge-owner", scope="PRO")
    ids = _seed(database, profile_id)
    newest, oldest = _get(client, headers)["sessions"]
    assert _rename(client, headers, oldest["session_ref"], "Evening", key="merge-key-1").status_code == 200
    assert _rename(client, headers, newest["session_ref"], "Morning", key="merge-key-2").status_code == 200
    # Stretch the last evening match until the next session is less than three hours away.
    _duration(database, ids[2], 20 * 3600)
    merged = _get(client, headers)["sessions"]
    assert len(merged) == 1 and merged[0]["session_ref"] == oldest["session_ref"]
    assert merged[0]["name"] == "Morning" and merged[0]["match_count"] == 5


def test_matches_without_profile_is_empty(database):
    from app.tracker.schema import profiles

    client, headers, profile_id = _client(database, "no-profile")
    with database.begin() as connection:
        connection.execute(update(profiles).where(profiles.c.id == profile_id).values(active=False))
    assert _get(client, headers) == {"contract_version": "matches-list-v1", "time_zone": "Asia/Tokyo",
                                     "has_matches": False, "sessions": [], "next_cursor": None}


@pytest.mark.parametrize("lifecycle", ["ANALYZING", "UNAVAILABLE"])
def test_non_ready_matches_are_listed_with_their_lifecycle(database, lifecycle):
    client, headers, profile_id = _client(database, f"life-{lifecycle}", scope="PRO")
    _link(database, profile_id, 0, BASE, hero_id=2)
    _link(database, profile_id, 1, BASE + timedelta(hours=1), hero_id=2, lifecycle=lifecycle)
    body = _get(client, headers)
    assert [row["lifecycle"] for row in body["sessions"][0]["matches"]] == [lifecycle, "READY"]

"""Finalizer-backed achievement flow: retained source in, awards out, no provider I/O."""
from datetime import UTC, datetime

from app.tracker import finalization, rebuild
from app.tracker.finalization import complete_finalization_job
from app.tracker.jobs import claim, enqueue
from app.tracker.rebuild import run_methodology_rebuild
from app.tracker.role_correction import correct_role
from app.tracker.schema import account_matches, analyses, events, profiles, provider_calls
from sqlalchemy import func, select

from .builders import add_match, finalize, history
from .test_schema import identity

HERO_A, HERO_B = 123, 99


def _hero(hero_id, *, flawless=False):
    def edit(payload):
        payload["players"][0]["hero_id"] = hero_id
        if flawless:
            payload["players"][0]["deaths"], payload["players"][0]["deaths_log"] = 0, []
    return edit


def _awards(database, profile_id):
    with database.connect() as c:
        rows = c.execute(select(account_matches.c.match_id, analyses.c.result).join(
            analyses, analyses.c.id == account_matches.c.active_analysis_id,
        ).where(account_matches.c.profile_id == profile_id).order_by(
            account_matches.c.provider_started_at)).all()
    return {row.match_id: {a["id"] for a in row.result["achievements"]["awards"]} for row in rows}


def _pb_history(database, profile_id):
    """Five priors on one hero, then a PB on the same hero, then the same PB on a new hero."""
    ids = history(database, profile_id, [0, 0, 0, 0, 0])
    for offset, (bonus, hero) in enumerate([(2, HERO_A), (4, HERO_B), (6, HERO_B)], start=5):
        match_id = add_match(database, profile_id, index=offset, stack_bonus=bonus, edit=_hero(hero))
        assert finalize(database, profile_id, match_id) == "READY"
        ids.append(match_id)
    return ids


def test_record_on_new_hero_repeats_once_per_new_hero_and_retry_is_idempotent(database):
    _, profile_id = identity(database)
    with database.begin() as c:
        c.execute(profiles.update().where(profiles.c.id == profile_id).values(
            original_linked_at=datetime(2020, 1, 1, tzinfo=UTC)))
    ids = _pb_history(database, profile_id)
    awards = _awards(database, profile_id)
    # Same-hero PB is not #4; the first PB on another hero is; a repeat on that hero is not.
    assert 4 not in awards[ids[5]] and 4 in awards[ids[6]] and 4 not in awards[ids[7]]
    with database.begin() as c:
        enqueue(c, dedup_key="duplicate-finalize-attempt", job_type="FINALIZE", priority=0,
                profile_id=profile_id, match_id=ids[6], payload={})
        retry = claim(c, priority=0)
    assert complete_finalization_job(
        database, job_id=retry["id"], lease_token=retry["lease_token"]) == "ALREADY_READY"
    assert _awards(database, profile_id) == awards


def test_role_correction_recomputes_later_awards_across_roles(database):
    _, profile_id = identity(database)
    with database.begin() as c:
        c.execute(profiles.update().where(profiles.c.id == profile_id).values(
            original_linked_at=datetime(2020, 1, 1, tzinfo=UTC)))
    ids = _pb_history(database, profile_id)
    before = _awards(database, profile_id)
    with database.begin() as c:
        result = correct_role(c, profile_id=profile_id, match_id=ids[0], role="CARRY",
                              expected_role_revision=0)
    # Standard closure spans every later Standard match regardless of role (#30 crosses roles).
    assert result["rebuilt"] and result["rebuilt_match_count"] == len(ids)
    after = _awards(database, profile_id)
    assert set(after) == set(before)
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(provider_calls)) == 0


def test_quiet_backfill_keeps_awards_and_never_replays_notifications(database, monkeypatch):
    _, profile_id = identity(database)
    with database.begin() as c:
        c.execute(profiles.update().where(profiles.c.id == profile_id).values(
            original_linked_at=datetime(2020, 1, 1, tzinfo=UTC)))
    match_id = add_match(database, profile_id, index=1, role="CARRY", offset_days=1, edit=_hero(HERO_A, flawless=True))
    assert finalize(database, profile_id, match_id) == "READY"
    before = _awards(database, profile_id)
    assert {14, 15} <= before[match_id]
    with database.connect() as c:
        ready_events = c.scalar(select(func.count()).select_from(events).where(events.c.kind == "MATCH_READY"))
        payload = c.scalar(select(events.c.payload).where(events.c.kind == "MATCH_READY"))
    assert ready_events == 1 and {14, 15} <= set(payload["achievement_ids"])
    monkeypatch.setattr(finalization, "ANALYSIS_VERSION", "tracker-analysis-test-bump")
    monkeypatch.setattr(rebuild, "ANALYSIS_VERSION", "tracker-analysis-test-bump")
    with database.begin() as c:
        assert run_methodology_rebuild(c, profile_id=profile_id) == 1
    with database.begin() as c:
        assert run_methodology_rebuild(c, profile_id=profile_id) == 0
    assert _awards(database, profile_id) == before
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(events).where(events.c.kind == "MATCH_READY")) == 1
        assert c.scalar(select(func.count()).select_from(provider_calls)) == 0


def test_historical_import_is_quiet(database):
    _, profile_id = identity(database)
    with database.begin() as c:
        c.execute(profiles.update().where(profiles.c.id == profile_id).values(
            original_linked_at=datetime(2020, 1, 1, tzinfo=UTC)))
    match_id = add_match(database, profile_id, index=1, role="CARRY", origin="HISTORICAL",
                         offset_days=-30, edit=_hero(HERO_A, flawless=True))
    assert finalize(database, profile_id, match_id) == "READY"
    assert {14, 15} <= _awards(database, profile_id)[match_id]
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(events).where(events.c.kind == "MATCH_READY")) == 0

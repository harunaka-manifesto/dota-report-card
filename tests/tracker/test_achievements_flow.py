"""Finalizer-backed achievement flow: retained source in, awards out, no provider I/O."""
from datetime import UTC, datetime

from app.tracker import finalization, rebuild
from app.tracker.finalization import complete_finalization_job
from app.tracker.jobs import claim, enqueue
from app.tracker.rebuild import run_methodology_rebuild
from app.tracker.role_correction import correct_role
from app.tracker.schema import (
    account_matches,
    analyses,
    events,
    personal_bests,
    profiles,
    provider_calls,
)
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
    # Moving the first match out of the Support bucket leaves the later Support matches one
    # prior short of the five-prior gate: the new-hero record is no longer current truth,
    # while feats that do not depend on the bucket (#18, #30, #41) are untouched.
    assert 4 in before[ids[6]] and 4 not in after[ids[6]]
    assert {k: v - {4} for k, v in before.items()} == after
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(provider_calls)) == 0
        # Every personal-best pointer follows an active analysis, in every role.
        active = select(account_matches.c.active_analysis_id).where(
            account_matches.c.profile_id == profile_id)
        stale = c.scalar(select(func.count()).select_from(personal_bests).where(
            personal_bests.c.profile_id == profile_id, personal_bests.c.analysis_id.not_in(active)))
        assert stale == 0


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


def test_match_in_flight_at_a_feature_version_bump_still_finalizes(database, monkeypatch):
    from app.tracker import materialization
    from app.tracker.schema import derived_features

    _, profile_id = identity(database)
    monkeypatch.setattr(materialization, "FEATURE_VERSION", "tracker-features-old")
    match_id = add_match(database, profile_id, index=1, role="CARRY", offset_days=1)
    monkeypatch.undo()  # deploy: the current feature version no longer matches the projection
    assert finalize(database, profile_id, match_id) == "READY"
    with database.connect() as c:
        versions = set(c.scalars(select(derived_features.c.feature_version).where(
            derived_features.c.match_id == match_id)))
        assert len(versions) == 2  # re-projected from the stored snapshot, nothing fetched
        assert c.scalar(select(func.count()).select_from(provider_calls)) == 0


def test_rule_or_tier_change_makes_analyses_stale_and_rebuilds_quietly(database, monkeypatch):
    from app.tracker import achievements

    _, profile_id = identity(database)
    with database.begin() as c:
        c.execute(profiles.update().where(profiles.c.id == profile_id).values(
            original_linked_at=datetime(2020, 1, 1, tzinfo=UTC)))
    match_id = add_match(database, profile_id, index=1, role="CARRY", offset_days=1, edit=_hero(HERO_A, flawless=True))
    assert finalize(database, profile_id, match_id) == "READY"
    with database.begin() as c:
        assert run_methodology_rebuild(c, profile_id=profile_id) == 0  # same rules: settled
    monkeypatch.setattr(achievements, "rules_digest", lambda: "changed-rules")
    monkeypatch.setattr(rebuild, "rules_digest", lambda: "changed-rules")
    with database.begin() as c:
        assert run_methodology_rebuild(c, profile_id=profile_id) == 1
    with database.begin() as c:
        assert run_methodology_rebuild(c, profile_id=profile_id) == 0
    with database.connect() as c:
        stored = c.scalar(select(analyses.c.result).join(
            account_matches, account_matches.c.active_analysis_id == analyses.c.id))
        assert stored["achievements"]["rules_digest"] == "changed-rules"
        assert c.scalar(select(func.count()).select_from(events).where(events.c.kind == "MATCH_READY")) == 1


def test_collection_progress_is_computed_from_all_visible_history_not_the_latest_match(database):
    from app.tracker.mobile_api import _achievement_collection

    _, profile_id = identity(database)
    with database.begin() as c:
        c.execute(profiles.update().where(profiles.c.id == profile_id).values(
            original_linked_at=datetime(2020, 1, 1, tzinfo=UTC)))
    for index, (hero, flawless) in enumerate([(HERO_A, True), (HERO_A, True), (HERO_B, False)], start=1):
        match_id = add_match(database, profile_id, index=index, role="CARRY", offset_days=index,
                             edit=_hero(hero, flawless=flawless))
        assert finalize(database, profile_id, match_id) == "READY"
    with database.connect() as c:
        profile = c.execute(select(profiles).where(profiles.c.id == profile_id)).mappings().one()
        entries = {e.id: e for e in _achievement_collection(c, profile, "en").entries}
    # Two same-hero matches with #14/#15, then a match without them on another hero: 2 of 3.
    assert entries[30].earned_count == 0
    assert (entries[30].progress.current, entries[30].progress.target) == (2, 3)
    assert entries[14].earned_count == 2

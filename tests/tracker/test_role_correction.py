from uuid import uuid4

import pytest
from app.tracker.finalization import ANALYSIS_VERSION
from app.tracker.history import BASELINE_VERSION
from app.tracker.materialization import materialize_snapshot
from app.tracker.metrics import metric_ids
from app.tracker.role_correction import (
    RoleCorrectionConflict,
    RoleCorrectionUnavailable,
    correct_role,
    correction_available,
)
from app.tracker.schema import (
    account_matches,
    analyses,
    analysis_inputs,
    baselines,
    events,
    insight_results,
    matches,
    metric_observations,
    personal_bests,
    profiles,
    role_assertions,
)
from sqlalchemy import func, select

from .test_finalization import MATCH_ID, _ready_link, _run
from .test_materialization import raw, save


def test_correction_remeasures_retained_source_and_is_idempotent(database):
    profile_id = _ready_link(database)
    assert _run(database, profile_id) == "READY"
    with database.connect() as connection:
        before = connection.execute(select(account_matches)).mappings().one()
        old_analysis_id = before["active_analysis_id"]
        previous_role = before["effective_role"]
        corrected_role = "MID" if before["effective_role"] != "MID" else "CARRY"
        event_count = connection.scalar(select(func.count()).select_from(events))

    later_match_id = MATCH_ID + 10
    payload = raw()
    payload["match_id"] = later_match_id
    payload["start_time"] += 7200
    payload["players"][0]["account_id"] = 1001
    with database.begin() as connection:
        snapshot_id = save(connection, payload)
        projection = materialize_snapshot(connection, snapshot_id=snapshot_id, match_id=later_match_id)
        later = connection.execute(select(matches).where(matches.c.match_id == later_match_id)).mappings().one()
        connection.execute(matches.update().where(matches.c.match_id == later_match_id).values(
            evidence_state="REPLAY_READY", replay_role_assignment=projection["role_assignment"],
            replay_terminal_at=func.clock_timestamp(),
        ))
        connection.execute(account_matches.insert().values(
            profile_id=profile_id, match_id=later_match_id, account_id=1001, player_slot=0,
            lifecycle="ANALYZING", mode=later["mode"], effective_role=previous_role,
            provider_started_at=later["started_at"], provider_source_match_id=later_match_id,
            origin="LIVE",
        ))
    assert _run(database, profile_id, later_match_id) == "READY"
    with database.connect() as connection:
        old_later_analysis_id = connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == later_match_id,
        ))
        event_count = connection.scalar(select(func.count()).select_from(events))

    with database.begin() as connection:
        result = correct_role(connection, profile_id=profile_id, match_id=MATCH_ID,
                              role=corrected_role, expected_role_revision=0)
    assert result == {"effective_role": corrected_role, "role_revision": 1,
                      "rebuilt": True, "rebuilt_match_count": 2}

    with database.connect() as connection:
        link = connection.execute(select(account_matches).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == MATCH_ID,
        )).mappings().one()
        assert link["effective_role"] == corrected_role
        assert link["role_revision"] == 1
        assert link["active_analysis_id"] != old_analysis_id
        later_link = connection.execute(select(account_matches).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == later_match_id,
        )).mappings().one()
        assert later_link["active_analysis_id"] == old_later_analysis_id
        metric_rows = connection.execute(select(metric_observations).where(
            metric_observations.c.analysis_id == link["active_analysis_id"],
        )).mappings().all()
        assert {row["metric_id"] for row in metric_rows} == set(metric_ids(corrected_role))
        # A replay may reuse an identical immutable analysis when this fixture's
        # old-role measurements are all N/A and therefore no baseline changed.
        assert later_link["active_analysis_id"] is not None
        assert connection.scalar(select(func.count()).select_from(analysis_inputs).where(
            analysis_inputs.c.analysis_id == link["active_analysis_id"],
        )) == 1
        assert connection.scalar(select(func.count()).select_from(insight_results).where(
            insight_results.c.analysis_id == link["active_analysis_id"],
        )) == 1
        assert connection.scalar(select(func.count()).select_from(events)) == event_count
        assert connection.scalar(select(func.count()).select_from(role_assertions)) == 1
        active = connection.execute(select(analyses).where(
            analyses.c.id == link["active_analysis_id"],
        )).mappings().one()
        assert active["analysis_version"] == ANALYSIS_VERSION
        assert active["baseline_version"] == BASELINE_VERSION

    with database.begin() as connection:
        repeated = correct_role(connection, profile_id=profile_id, match_id=MATCH_ID,
                                role=corrected_role, expected_role_revision=1)
    assert repeated == {"effective_role": corrected_role, "role_revision": 1, "rebuilt": False}
    with database.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(role_assertions)) == 1
        assert connection.scalar(select(func.count()).select_from(events)) == event_count


def test_correction_stale_revision_and_missing_source_fail_closed(database):
    profile_id = _ready_link(database)
    assert _run(database, profile_id) == "READY"
    with database.connect() as connection:
        link = connection.execute(select(account_matches)).mappings().one()
        previous_role = link["effective_role"]
        corrected_role = "MID" if link["effective_role"] != "MID" else "CARRY"
        assert correction_available(connection, profile_id=profile_id, match_id=MATCH_ID)
    with database.begin() as connection:
        with pytest.raises(RoleCorrectionConflict, match="stale"):
            correct_role(connection, profile_id=profile_id, match_id=MATCH_ID,
                         role=corrected_role, expected_role_revision=4)
    with database.begin() as connection:
        connection.execute(analysis_inputs.delete())
    with database.begin() as connection:
        with pytest.raises(RoleCorrectionUnavailable, match="lineage"):
            correct_role(connection, profile_id=profile_id, match_id=MATCH_ID,
                         role=corrected_role, expected_role_revision=0)
    with database.connect() as connection:
        link = connection.execute(select(account_matches)).mappings().one()
        assert link["effective_role"] == previous_role
        assert link["role_revision"] == 0
        assert connection.scalar(select(func.count()).select_from(role_assertions)) == 0
        assert not correction_available(connection, profile_id=profile_id, match_id=MATCH_ID)


def test_same_role_confirmation_is_append_only_and_repeat_safe(database):
    profile_id = _ready_link(database)
    assert _run(database, profile_id) == "READY"
    with database.connect() as connection:
        link = connection.execute(select(account_matches)).mappings().one()
        current_role = link["effective_role"]
        analysis_id = link["active_analysis_id"]
    with database.begin() as connection:
        first = correct_role(connection, profile_id=profile_id, match_id=MATCH_ID,
                             role=current_role, expected_role_revision=0)
    assert first == {"effective_role": current_role, "role_revision": 1, "rebuilt": False}
    with database.begin() as connection:
        repeated = correct_role(connection, profile_id=profile_id, match_id=MATCH_ID,
                                role=current_role, expected_role_revision=1)
    assert repeated == {"effective_role": current_role, "role_revision": 1, "rebuilt": False}
    with database.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(role_assertions)) == 1
        assert connection.scalar(select(account_matches.c.active_analysis_id)) == analysis_id


def test_retained_non_progression_match_can_be_corrected_without_history_writes(database):
    profile_id = _ready_link(database)
    with database.begin() as connection:
        connection.execute(matches.update().where(matches.c.match_id == MATCH_ID).values(mode="UNSUPPORTED"))
        connection.execute(account_matches.update().where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == MATCH_ID,
        ).values(mode="UNSUPPORTED"))
    assert _run(database, profile_id) == "READY"
    with database.connect() as connection:
        link = connection.execute(select(account_matches).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == MATCH_ID,
        )).mappings().one()
        role = "MID" if link["effective_role"] != "MID" else "CARRY"
        assert link["progression"] == "NONE"
        assert correction_available(connection, profile_id=profile_id, match_id=MATCH_ID, role=role)
    with database.begin() as connection:
        result = correct_role(connection, profile_id=profile_id, match_id=MATCH_ID,
                              role=role, expected_role_revision=0)
    assert result["effective_role"] == role and result["rebuilt"]
    with database.connect() as connection:
        link = connection.execute(select(account_matches).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == MATCH_ID,
        )).mappings().one()
        assert link["progression"] == "NONE"
        assert connection.scalar(select(func.count()).select_from(baselines)) == 0
        assert connection.scalar(select(func.count()).select_from(personal_bests)) == 0


def test_rebuild_replays_five_prior_history_and_keeps_other_series(database):
    profile_id = _ready_link(database)
    with database.begin() as connection:
        connection.execute(profiles.update().where(profiles.c.id == profile_id).values(active_scope="PRO"))
    assert _run(database, profile_id) == "READY"
    with database.connect() as connection:
        target = connection.execute(select(account_matches).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == MATCH_ID,
        )).mappings().one()
        target_start = int(target["provider_started_at"].timestamp())
        old_role = target["effective_role"]
    new_role = "MID" if old_role != "MID" else "CARRY"

    def add_finalized(match_id: int, start_time: int, role: str, *, turbo: bool = False) -> None:
        payload = raw()
        payload["match_id"] = match_id
        payload["start_time"] = start_time
        payload["players"][0]["account_id"] = 1001
        if turbo:
            payload["game_mode"] = 23
        with database.begin() as connection:
            snapshot_id = save(connection, payload)
            projection = materialize_snapshot(connection, snapshot_id=snapshot_id, match_id=match_id)
            match = connection.execute(select(matches).where(matches.c.match_id == match_id)).mappings().one()
            connection.execute(matches.update().where(matches.c.match_id == match_id).values(
                evidence_state="REPLAY_READY", replay_role_assignment=projection["role_assignment"],
                replay_terminal_at=func.clock_timestamp(),
            ))
            connection.execute(account_matches.insert().values(
                profile_id=profile_id, match_id=match_id, account_id=1001, player_slot=0,
                lifecycle="ANALYZING", mode=match["mode"], effective_role=role,
                provider_started_at=match["started_at"], provider_source_match_id=match_id,
                role_revision=1, origin="LIVE",
            ))
            connection.execute(role_assertions.insert().values(
                id=str(uuid4()), profile_id=profile_id, match_id=match_id, revision=1,
                role=role, asserted_at=func.now(), provenance={"source": "test_fixture"},
                dedup_key=f"test-role:{profile_id}:{match_id}",
            ))
        assert _run(database, profile_id, match_id) == "READY"

    prior_ids = [MATCH_ID + 100 + i for i in range(6)]
    for index, match_id in enumerate(prior_ids):
        add_finalized(match_id, target_start - (6 - index) * 3600, new_role)
    unaffected_role = next(role for role in ("CARRY", "MID", "OFFLANE", "SUPPORT")
                            if role not in {old_role, new_role})
    same_bucket_id = MATCH_ID + 200
    turbo_id = MATCH_ID + 201
    add_finalized(same_bucket_id, target_start + 3600, unaffected_role)
    add_finalized(turbo_id, target_start + 7200, new_role, turbo=True)

    with database.connect() as connection:
        before_events = connection.scalar(select(func.count()).select_from(events))
        unaffected_pointer = connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == same_bucket_id,
        ))
        turbo_pointer = connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == turbo_id,
        ))
    with database.begin() as connection:
        result = correct_role(connection, profile_id=profile_id, match_id=MATCH_ID,
                              role=new_role, expected_role_revision=0)
    assert result["rebuilt"] is True
    with database.connect() as connection:
        target = connection.execute(select(account_matches).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == MATCH_ID,
        )).mappings().one()
        metric = f"{new_role.lower()}.net_worth_at_20.v1"
        observation = connection.execute(select(metric_observations).where(
            metric_observations.c.analysis_id == target["active_analysis_id"],
            metric_observations.c.metric_id == metric,
        )).mappings().one()
        assert observation["baseline_snapshot"]["prior_count"] == 6
        assert observation["baseline_snapshot"]["state"] == "BASELINE_READY"
        pb = connection.execute(select(personal_bests).where(
            personal_bests.c.profile_id == profile_id,
            personal_bests.c.revision == 0, personal_bests.c.mode == "STANDARD",
            personal_bests.c.role == new_role, personal_bests.c.metric_id == metric,
        )).mappings().one()
        pb_source = connection.scalar(select(account_matches.c.match_id).where(
            account_matches.c.profile_id == profile_id,
            account_matches.c.active_analysis_id == pb["analysis_id"],
        ))
        assert pb_source == prior_ids[0]  # Equal values keep the earliest observation.
        assert connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == same_bucket_id,
        )) == unaffected_pointer
        assert connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == turbo_id,
        )) == turbo_pointer
        assert connection.scalar(select(func.count()).select_from(events)) == before_events

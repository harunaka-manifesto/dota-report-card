from copy import deepcopy
from uuid import uuid4

import pytest
from app.tracker.jobs import StaleJob, claim
from app.tracker.linking import (
    complete_link_job,
    complete_role_job,
    enqueue_role_refinements,
    enqueue_roster_links,
)
from app.tracker.materialization import materialize_snapshot
from app.tracker.normalization import opendota_summary, stratz_summary
from app.tracker.role_evidence import replay_role_inputs
from app.tracker.schema import account_matches, ingest_jobs, positions, role_assertions, users
from sqlalchemy import func, select

from .test_linking import prepare
from .test_materialization import MATCH_ID, raw, save


def test_paired_ward_counts_match_without_inventing_stratz_lanes():
    od, sz = raw(), raw('stratz')
    left = replay_role_inputs(od, 'opendota', opendota_summary(od))
    right = replay_role_inputs(sz, 'stratz', stratz_summary(sz))
    assert [p['wards_placed'] for p in left] == [p['wards_placed'] for p in right]
    assert all(p['lane'] is None for p in right)
    assert left[0]['lane'] == 'SAFE' and left[4]['lane'] == 'MID'
    od['players'][0]['is_roaming'] = True
    assert replay_role_inputs(od, 'opendota', opendota_summary(od))[0]['lane'] is None
    od['version'] = None
    assert all(p['lane'] is None and p['wards_placed'] is None for p in replay_role_inputs(od, 'opendota', opendota_summary(od)))


@pytest.mark.parametrize('events, expected', [(None, None), ([], 0), ([{'type': 99, 'time': 2}], None)])
def test_absent_empty_and_invalid_ward_lists_are_distinct(events, expected):
    payload = raw('stratz')
    payload['players'][0]['stats']['wards'] = events
    assert replay_role_inputs(payload, 'stratz', stratz_summary(payload))[0]['wards_placed'] == expected


def prepare_refinement(database):
    owners = prepare(database)
    with database.begin() as c:
        enqueue_roster_links(c, match_id=MATCH_ID, origin='HISTORICAL')
        jobs = [claim(c, priority=3), claim(c, priority=3)]
    for job in jobs:
        complete_link_job(database, job_id=job['id'], lease_token=job['lease_token'], replay_delay_seconds=360)
    with database.begin() as c:
        snapshot = save(c, raw())
        projected = materialize_snapshot(c, snapshot_id=snapshot, match_id=MATCH_ID)
        enqueue_role_refinements(c, MATCH_ID, projected['role_assignment'])
        enqueue_role_refinements(c, MATCH_ID, projected['role_assignment'])
        jobs = [claim(c, priority=1), claim(c, priority=1)]
        assert c.scalar(select(func.count()).select_from(ingest_jobs).where(ingest_jobs.c.job_type == 'ROLE_REFRESH')) == 2
    return owners, jobs


def test_replay_refinement_preserves_latest_assertion_and_exact_assignment(database):
    _, jobs = prepare_refinement(database)
    with database.begin() as c:
        first = jobs[0]
        c.execute(role_assertions.insert().values(id=str(uuid4()), profile_id=first['profile_id'], match_id=MATCH_ID, revision=1,
            role='MID', asserted_at=func.now(), provenance={'source': 'user'}, dedup_key=str(uuid4())))
    for job in jobs:
        assert complete_role_job(database, job_id=job['id'], lease_token=job['lease_token']) == 'COMPLETE'
    with database.connect() as c:
        link = c.execute(select(account_matches).where(account_matches.c.profile_id == first['profile_id'])).mappings().one()
        assert link['effective_role'] == 'MID' and link['role_revision'] == 1
        assert link['role_assignment'] == first['payload']
        assert link['finalized_at'] is None and link['active_analysis_id'] is None
        assert c.scalar(select(func.count()).select_from(positions).where(positions.c.evidence_profile == 'REPLAY')) == 10


def test_finalization_and_generation_fences_prevent_late_refinement(database):
    owners, jobs = prepare_refinement(database)
    with database.begin() as c:
        first = jobs[0]
        c.execute(account_matches.update().where(account_matches.c.profile_id == first['profile_id']).values(finalized_at=func.now()))
        before = dict(c.execute(select(account_matches).where(account_matches.c.profile_id == first['profile_id'])).mappings().one())
        other_user = next(user for user, profile in owners if profile == jobs[1]['profile_id'])
        c.execute(users.update().where(users.c.id == other_user).values(generation=users.c.generation + 1))
    assert complete_role_job(database, job_id=first['id'], lease_token=first['lease_token']) == 'FINALIZED_UNCHANGED'
    with pytest.raises(StaleJob):
        complete_role_job(database, job_id=jobs[1]['id'], lease_token=jobs[1]['lease_token'])
    with database.connect() as c:
        assert dict(c.execute(select(account_matches).where(account_matches.c.profile_id == first['profile_id'])).mappings().one()) == before


def test_role_adapters_do_not_mutate_retained_source():
    payload = raw()
    before = deepcopy(payload)
    replay_role_inputs(payload, 'opendota', opendota_summary(payload))
    assert payload == before


def test_link_created_after_replay_terminal_gets_selected_refinement(database):
    from app.tracker.schema import matches
    owners = prepare(database)
    with database.begin() as c:
        projected = materialize_snapshot(c, snapshot_id=save(c, raw()), match_id=MATCH_ID)
        c.execute(matches.update().where(matches.c.match_id == MATCH_ID).values(
            evidence_state='REPLAY_READY', replay_terminal_at=func.now(), replay_role_assignment=projected['role_assignment']))
        enqueue_roster_links(c, match_id=MATCH_ID, origin='LIVE')
        jobs = [claim(c, priority=0), claim(c, priority=0)]
    for job in jobs:
        complete_link_job(database, job_id=job['id'], lease_token=job['lease_token'], replay_delay_seconds=360)
    with database.begin() as c:
        assert c.scalar(select(func.count()).select_from(ingest_jobs).where(ingest_jobs.c.job_type == 'ROLE_REFRESH')) == len(owners)
        jobs = [claim(c, priority=1), claim(c, priority=1)]
    for job in jobs:
        assert complete_role_job(database, job_id=job['id'], lease_token=job['lease_token']) == 'COMPLETE'
    with database.connect() as c:
        assert all(r == projected['role_assignment'] for r in c.scalars(select(account_matches.c.role_assignment)))


def test_role_assignment_migration_preserves_existing_private_role(postgres):
    from .conftest import migrate
    from .test_schema import MATCH_ID as old_match
    from .test_schema import identity, summary
    url = postgres.url.render_as_string(hide_password=False)
    migrate(url, '0007_tracker_discovery_journal')
    _, profile = identity(postgres)
    summary(postgres)
    with postgres.begin() as c:
        c.execute(account_matches.insert().values(profile_id=profile, match_id=old_match, account_id=1001, player_slot=0,
            lifecycle='ANALYZING', mode='STANDARD', effective_role='MID', role_revision=3,
            provider_started_at=func.now(), provider_source_match_id=old_match, origin='LIVE'))
    migrate(url, 'head')
    with postgres.connect() as c:
        row = c.execute(select(account_matches)).mappings().one()
        assert row['effective_role'] == 'MID' and row['role_revision'] == 3 and row['role_assignment'] is None
    migrate(url, '0007_tracker_discovery_journal', 'downgrade')
    migrate(url, 'head')
    with postgres.connect() as c:
        assert c.scalar(select(account_matches.c.effective_role)) == 'MID'


def test_disagreement_arriving_after_enqueue_blocks_dependent_refinement(database):
    from app.tracker.schema import matches
    _, jobs = prepare_refinement(database)
    job = jobs[0]
    with database.begin() as c:
        before = dict(c.execute(select(account_matches).where(account_matches.c.profile_id == job['profile_id'])).mappings().one())
        teammate = 0 if before['player_slot'] < 5 else 5
        c.execute(matches.update().where(matches.c.match_id == MATCH_ID).values(quarantined_fields=[f'players.{teammate}.values.net_worth']))
    assert complete_role_job(database, job_id=job['id'], lease_token=job['lease_token']) == 'ROLE_INPUT_QUARANTINED'
    with database.connect() as c:
        assert dict(c.execute(select(account_matches).where(account_matches.c.profile_id == job['profile_id'])).mappings().one()) == before

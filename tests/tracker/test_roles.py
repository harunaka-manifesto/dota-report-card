from copy import deepcopy
from uuid import uuid4

import pytest
from app.tracker.roles import RolePolicy, assign_positions, persist_summary_positions
from app.tracker.schema import account_matches, matches, parameter_sets, positions, role_assertions
from sqlalchemy import func, select

from .test_linking import prepare
from .test_schema import MATCH_ID, summary


def roster():
    return [dict(player_slot=i, team='RADIANT' if i < 5 else 'DIRE', values={
        'net_worth': (5-i%5)*1000, 'gold_per_min': (5-i%5)*100,
        'last_hits': (5-i%5)*50, 'gold_spent': (5-i%5)*1000,
    }) for i in range(10)]


def test_summary_classifies_both_teams_without_replay_or_native_position():
    players = roster()
    output = assign_positions(players)
    assert [p['position'] for p in output['players']] == [1, 2, 3, 4, 5]*2
    assert [p['role'] for p in output['players'][:5]] == ['CARRY', 'MID', 'OFFLANE', 'SUPPORT', 'SUPPORT']
    assert {p['confidence_bucket'] for p in output['players']} == {'low'}
    for p in players:
        p.update(kills=999, deaths=999, assists=999, radiant_win=False, position=5, role='SUPPORT', hero_id=999, lane='MID', wards_placed=100)
        p['values'].update(kills=999, xp_per_min=99999)
    assert assign_positions(players) == output
    assert assign_positions(list(reversed(players))) == output
    for p in players[5:]:
        p['values'] = {key: value * 100 for key, value in p['values'].items()}
    assert assign_positions(players)['players'][:5] == output['players'][:5]


def test_missing_farm_is_failure_zero_is_evidence_and_ties_are_low_confidence():
    players = roster()
    for p in players[:5]:
        p['values'] = {}
    output = assign_positions(players)
    assert all(p['position'] is None and p['reason'] == 'MISSING_FARM_PRIORITY' for p in output['players'][:5])
    assert all(p['role'] for p in output['players'][5:])
    for p in players[:5]:
        p['values'] = {'last_hits': 0}
    output = assign_positions(players)
    assert [p['position'] for p in output['players'][:5]] == [1, 2, 3, 4, 5]
    assert all(p['confidence'] == 0 and p['confidence_bucket'] == 'low' for p in output['players'][:5])


def test_replay_lane_is_pairing_evidence_not_position_label():
    players = roster()
    # Safelane support belongs beside a safelane carry, not automatically position 1.
    for team in (players[:5], players[5:]):
        for p, lane, wards in zip(team, ['MID', 'SAFE', 'OFF', 'OFF', 'SAFE'], [0, 0, 0, 5, 10], strict=True):
            p.update(lane=lane, wards_placed=wards)
    output = assign_positions(players, evidence_profile='REPLAY')
    assert [p['position'] for p in output['players'][:5]] == [2, 1, 3, 4, 5]
    assert output['inputs_digest'] != assign_positions(players)['inputs_digest']
    before = deepcopy(players)
    assign_positions(players)
    assert players == before


def test_summary_positions_persist_with_provisional_policy_and_idempotent_identity(database):
    prepare(database)
    from .test_materialization import MATCH_ID as materialized_match
    with database.begin() as c:
        first = persist_summary_positions(c, materialized_match)
        assert persist_summary_positions(c, materialized_match) == first
        assert c.scalar(select(func.count()).select_from(positions)) == 10
        policy = c.execute(select(parameter_sets)).mappings().one()
        assert policy['status'] == 'PROVISIONAL'
        assert policy['parameters']['confidence_threshold'] == 0.6
    with pytest.raises(ValueError, match='version reused'):
        with database.begin() as c:
            persist_summary_positions(c, materialized_match, policy=RolePolicy(farm_weight=2))


def test_link_has_effective_role_before_replay_and_keeps_user_correction(database):
    from app.tracker.jobs import claim
    from app.tracker.linking import complete_link_job, enqueue_roster_links

    prepare(database)
    from .test_materialization import MATCH_ID as materialized_match
    with database.begin() as c:
        enqueue_roster_links(c, match_id=materialized_match, origin='HISTORICAL')
        jobs = [claim(c, priority=3), claim(c, priority=3)]
    for job in jobs:
        complete_link_job(database, job_id=job['id'], lease_token=job['lease_token'], replay_delay_seconds=360)
    with database.begin() as c:
        assert all(c.scalars(select(account_matches.c.effective_role)))
        for link in c.execute(select(account_matches)).mappings():
            c.execute(role_assertions.insert().values(id=str(uuid4()), profile_id=link['profile_id'], match_id=link['match_id'],
                revision=1, role='MID', asserted_at=func.now(), provenance={'source': 'user_confirmation'}, dedup_key=str(uuid4())))
        c.execute(account_matches.update().values(effective_role='MID', role_revision=1))
        enqueue_roster_links(c, match_id=materialized_match, origin='LIVE')
        jobs = [claim(c, priority=0), claim(c, priority=0)]
    for job in jobs:
        complete_link_job(database, job_id=job['id'], lease_token=job['lease_token'], replay_delay_seconds=360)
    with database.connect() as c:
        assert set(c.scalars(select(account_matches.c.effective_role))) == {'MID'}


def test_old_rows_without_farm_do_not_fabricate_assignment(database):
    summary(database)
    with database.begin() as c:
        output = persist_summary_positions(c, MATCH_ID)
        assert all(p['role'] is None for p in output['players'])


def test_disputed_farm_inputs_are_withheld_from_assignment(database):
    prepare(database)
    from app.tracker.roles import FARM_FIELDS

    from .test_materialization import MATCH_ID as materialized_match
    with database.begin() as c:
        original = persist_summary_positions(c, materialized_match)
        c.execute(matches.update().where(matches.c.match_id == materialized_match).values(
            quarantined_fields=[f'players.0.values.{key}' for key in FARM_FIELDS]))
        quarantined = persist_summary_positions(c, materialized_match)
        assert quarantined['inputs_digest'] != original['inputs_digest']
        assert all(p['role'] is None for p in quarantined['players'][:5])
        assert quarantined['players'][5:] == original['players'][5:]
        assert c.scalar(select(func.count()).select_from(positions)) == 20

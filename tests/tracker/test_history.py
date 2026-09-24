from datetime import UTC, datetime, timedelta

import pytest
from app.tracker.history import Observation, baseline, personal_best

START = datetime(2026, 1, 1, tzinfo=UTC)


def row(i, value, *, mode='STANDARD', role='CARRY', metric='carry.hero_damage_share.v1', eligible=True, start=None):
    return Observation(i, start or START + timedelta(hours=i), mode, role, metric, value, eligible)


def test_five_prior_gate_exact_chronology_and_identity_isolation():
    current = row(6, .9)
    rows = [row(i, i / 10) for i in range(1, 6)]
    rows += [row(100, 2.0, mode='TURBO', start=START), row(101, 3.0, eligible=False, start=START),
             row(102, None, start=START), row(103, 9.0, start=current.started_at),
             row(104, 9.0, start=current.started_at + timedelta(seconds=1)),
             row(105, 9.0, role='SUPPORT', metric='support.fight_presence.v1', start=START)]
    result = baseline(current, rows)
    assert result == {'version': 'rolling-median-20-v1', 'state': 'BASELINE_READY',
                      'prior_count': 5, 'value': .3, 'source_match_ids': [1, 2, 3, 4, 5]}
    assert baseline(row(5, .5), rows)['state'] == 'BASELINE_BUILDING'
    assert baseline(current, [*rows, row(6, 99, start=START) ])['source_match_ids'] == [1, 2, 3, 4, 5]
    assert personal_best(current, rows, celebrate=True) == {'state': 'READY', 'source_match_id': 6, 'value': .9, 'new_pb': True}


def test_last_twenty_median_but_pb_uses_entire_entitled_history():
    rows = [row(1, 100)] + [row(i, i) for i in range(2, 27)]
    current = row(27, 25)
    result = baseline(current, rows)
    assert result['source_match_ids'] == list(range(7, 27))
    assert result['value'] == 16.5
    assert personal_best(current, rows, celebrate=True) == {'state': 'READY', 'source_match_id': 1, 'value': 100, 'new_pb': False}


def test_lower_direction_strict_tie_earliest_owner_and_silent_rebuild():
    metric = 'carry.dead_time.v1'
    rows = [row(i, 1 / i, metric=metric) for i in range(1, 6)]
    tied = row(6, .2, metric=metric)
    assert personal_best(tied, rows, celebrate=True)['source_match_id'] == 5
    assert personal_best(tied, rows, celebrate=True)['new_pb'] is False
    improved = row(7, .1, metric=metric)
    assert personal_best(improved, [*rows, tied], celebrate=True)['new_pb'] is True
    assert personal_best(improved, [*rows, tied], celebrate=False)['new_pb'] is False
    assert baseline(improved, [*rows, tied])['prior_count'] == 6


def test_missing_current_metric_does_not_erase_existing_record():
    rows = [row(i, i / 10) for i in range(1, 7)]
    current = row(7, None)
    assert personal_best(current, rows)['source_match_id'] == 6
    assert baseline(current, rows)['value'] == .35
    assert personal_best(row(5, .5), rows)['state'] == 'BUILDING'


def test_history_rejects_duplicates_and_nonfinite_values():
    with pytest.raises(ValueError):
        baseline(row(3, .3), [row(1, .1), row(1, .1)])
    with pytest.raises(ValueError):
        row(3, float('nan'))
    with pytest.raises(ValueError):
        row(3, 1.0, role='MID')


def test_database_prior_selection_respects_entitlement_and_active_finalization(database):
    from uuid import uuid4

    from app.tracker.history import load_prior_observations
    from app.tracker.schema import (
        account_matches,
        analyses,
        match_players,
        matches,
        metric_observations,
        profiles,
    )

    from .test_schema import MATCH_ID, NOW, identity

    _, profile_id = identity(database)
    with database.begin() as c:
        for i in range(1, 9):
            match_id = MATCH_ID + i
            started = NOW - timedelta(days=30-i) if i <= 6 else NOW + timedelta(days=i-6)
            origin = 'BOOTSTRAP' if i <= 5 else 'HISTORICAL' if i == 6 else 'LIVE'
            c.execute(matches.insert().values(match_id=match_id, started_at=started, duration_seconds=1800,
                mode='STANDARD', radiant_win=True, header={}, evidence_state='REPLAY_UNAVAILABLE',
                terminal_reason='TEST_REPLAY_UNAVAILABLE', discovered_at=NOW, summary_ready_at=NOW))
            c.execute(match_players.insert(), [dict(match_id=match_id, player_slot=slot, hero_id=slot+1,
                account_id=1001 if slot == 0 else None, team='RADIANT' if slot < 5 else 'DIRE', summary={})
                for slot in range(10)])
            c.execute(account_matches.insert().values(profile_id=profile_id, match_id=match_id, account_id=1001,
                player_slot=0, lifecycle='ANALYZING', mode='STANDARD', provider_started_at=started,
                provider_source_match_id=match_id, origin=origin, effective_role='CARRY'))
            if i == 8:
                continue
            analysis_id = str(uuid4())
            c.execute(analyses.insert().values(id=analysis_id, profile_id=profile_id, match_id=match_id,
                feature_version='test', analysis_version='metrics-1', baseline_version='rolling-median-20-v1',
                inputs_digest=f'{i:064x}', result={}, provenance={}, created_at=NOW))
            c.execute(metric_observations.insert().values(analysis_id=analysis_id,
                metric_id='carry.hero_damage_share.v1', metric_version='v1', raw_value=i,
                comparison_value=i / 10, baseline_snapshot={}))
            c.execute(account_matches.update().where(account_matches.c.profile_id == profile_id,
                account_matches.c.match_id == match_id).values(lifecycle='READY', progression='STANDARD',
                finalized_at=NOW, active_analysis_id=analysis_id))
        current = Observation(MATCH_ID+8, NOW+timedelta(days=2), 'STANDARD', 'CARRY',
                              'carry.hero_damage_share.v1', .8, True)
        kwargs = dict(profile_id=profile_id, current=current, analysis_version='metrics-1',
                      baseline_version='rolling-median-20-v1')
        free = load_prior_observations(c, **kwargs)
        assert [r.match_id for r in free] == [MATCH_ID+i for i in (1, 2, 3, 4, 5, 7)]
        assert baseline(current, free)['value'] == .35
        c.execute(profiles.update().where(profiles.c.id == profile_id).values(active_scope='PRO'))
        pro = load_prior_observations(c, **kwargs)
        assert [r.match_id for r in pro] == [MATCH_ID+i for i in range(1, 8)]
        assert personal_best(current, pro)['source_match_id'] == MATCH_ID+8
        assert load_prior_observations(c, **{**kwargs, 'analysis_version': 'metrics-2'}) == []
        replacement_id = str(uuid4())
        c.execute(analyses.insert().values(id=replacement_id, profile_id=profile_id, match_id=MATCH_ID+7,
            feature_version='test', analysis_version='metrics-2', baseline_version='rolling-median-20-v1',
            inputs_digest='f'*64, result={}, provenance={}, created_at=NOW))
        c.execute(metric_observations.insert().values(analysis_id=replacement_id,
            metric_id='carry.hero_damage_share.v1', metric_version='v1', raw_value=7,
            comparison_value=.7, baseline_snapshot={}))
        c.execute(account_matches.update().where(account_matches.c.profile_id == profile_id,
            account_matches.c.match_id == MATCH_ID+7).values(active_analysis_id=replacement_id))
        assert [r.match_id for r in load_prior_observations(c, **kwargs)] == [MATCH_ID+i for i in range(1, 7)]
        assert [r.match_id for r in load_prior_observations(c, **{**kwargs, 'analysis_version': 'metrics-2'})] == [MATCH_ID+7]

from copy import deepcopy

from app.tracker.events import replay_events
from app.tracker.metrics import EVENT_METRICS, measure
from app.tracker.normalization import opendota_summary, stratz_summary

from .test_materialization import raw


def projection(payload, provider):
    summary = (opendota_summary if provider == 'opendota' else stratz_summary)(payload)
    events = replay_events(payload, provider)
    return [{**e, 'summary': p} for p, e in zip(summary['players'], events['players'], strict=True)]


def result(metric, rows, slot=0):
    return measure(metric, players=rows, player_slot=slot, duration_seconds=3589, replay_ready=True)


def test_retained_replay_events_are_measured_without_mutating_sources():
    od, sz = raw(), raw('stratz')
    before = deepcopy((od, sz))
    a, b = projection(od, 'opendota'), projection(sz, 'stratz')
    for slot in range(10):
        for metric in ['support.observer_wards_placed.v1']:
            assert result(metric, a, slot) == result(metric, b, slot)
            assert result(metric, a, slot).reason is None
        for rows, deaths, key in [(a, od['players'][slot]['deaths_log'], 'time_dead'), (b, sz['players'][slot]['stats']['deathEvents'], 'timeDead')]:
            if all(type(e.get(key)) is int and e['time'] >= 0 for e in deaths):
                assert result('carry.dead_time.v1', rows, slot).raw_value == sum(e[key] for e in deaths)
            else:
                assert result('carry.dead_time.v1', rows, slot).comparison_value is None
        assert result('mid.level_6_time.v1', b, slot).raw_value == sz['players'][slot]['stats']['level'][5]
        assert result('support.vision_denial.v1', b, slot).raw_value == len(sz['players'][slot]['stats']['wardDestruction'])
        assert result('mid.early_fight_presence.v1', b, slot).reason is None
        assert result('offlane.objective_involvement.v1', b, slot).reason is None
    assert (od, sz) == before
    assert result('mid.level_6_time.v1', a).comparison_value is None
    assert result('support.vision_denial.v1', a).comparison_value is None
    assert result('mid.early_fight_presence.v1', a).comparison_value is None


def test_unparsed_and_missing_streams_are_not_zero():
    payload = raw('stratz')
    payload['isStats'] = False
    payload['statsDateTime'] = None
    rows = projection(payload, 'stratz')
    assert all(result(metric, rows).comparison_value is None for metric in EVENT_METRICS)
    payload = raw('stratz')
    payload['players'][0]['stats']['wards'] = []
    assert result('support.observer_wards_placed.v1', projection(payload, 'stratz')).raw_value == 0
    for value in [None, [{'time': True, 'type': 0}], [{'time': 10, 'type': True}], [{'time': 10, 'type': 5}]]:
        payload['players'][0]['stats']['wards'] = value
        assert result('support.observer_wards_placed.v1', projection(payload, 'stratz')).comparison_value is None


def test_selected_operation_missing_death_duration_or_tower_report_stays_unavailable():
    payload = raw('stratz')
    for e in payload['players'][0]['stats']['deathEvents']:
        e.pop('timeDead', None)
    del payload['players'][0]['stats']['towerDamageReport']
    rows = projection(payload, 'stratz')
    assert result('carry.dead_time.v1', rows).reason == 'INCOMPLETE_DEAD_INTERVALS'
    assert result('offlane.objective_involvement.v1', rows).reason == 'MISSING_OR_MALFORMED_TOWER_DAMAGE'
    assert result('mid.level_6_time.v1', rows).raw_value == 512
    payload['players'][0]['stats']['level'][5] = -1
    assert result('mid.level_6_time.v1', projection(payload, 'stratz')).comparison_value is None

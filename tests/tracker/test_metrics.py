from copy import deepcopy

import pytest
from app.tracker.metrics import CHECKPOINT_METRICS, SUMMARY_METRICS, measure


def players():
    return [dict(summary=dict(player_slot=i, team='RADIANT' if i < 5 else 'DIRE', values={
        'kills': 2, 'assists': 3, 'hero_damage': 100, 'tower_damage': 50, 'hero_healing': 300,
    }), checkpoints={'last_hits': {'600': 50, '1200': 120}, 'net_worth': {'600': 5000+i*100, '1200': 10000},
                     'camps_stacked': {'600': 1, '1200': 3, '1800': 6}}) for i in range(10)]


def run(metric, rows=None, **kwargs):
    return measure(metric, players=players() if rows is None else rows, player_slot=kwargs.pop('player_slot', 0),
                   duration_seconds=kwargs.pop('duration_seconds', 1800), replay_ready=kwargs.pop('replay_ready', True),
                   positions=kwargs.pop('positions', {i: i % 5 + 1 for i in range(10)}), **kwargs)


@pytest.mark.parametrize('metric, raw, comparison', [
    ('carry.hero_damage_share.v1', 100, .2), ('carry.tower_damage_share.v1', 50, .2),
    ('mid.tower_damage_share.v1', 50, .2), ('offlane.fight_presence.v1', .5, .5),
    ('support.fight_presence.v1', .5, .5), ('support.healing.v1', 300, 100),
    ('carry.last_hits_at_10.v1', 50, 50), ('carry.cs_10_to_20.v1', 70, 70),
    ('carry.net_worth_at_20.v1', 10000, 10000), ('mid.net_worth_at_20.v1', 10000, 10000),
    ('mid.lane_net_worth_advantage_at_10.v1', -600, -600),
    ('offlane.lane_net_worth_advantage_at_10.v1', -500, -500),
    ('offlane.net_worth_at_10.v1', 5000, 5000), ('support.camps_stacked.v1', 3, 3),
])
def test_exact_formulas_and_raw_comparison_separation(metric, raw, comparison):
    value = run(metric)
    assert value.reason is None
    assert value.raw_value == raw and value.comparison_value == pytest.approx(comparison)


def test_summary_metrics_survive_missing_replay_and_use_credited_team_scoreboard():
    rows = players()
    for p in rows[5:]:
        p['summary']['values']['hero_damage'] = 99999
    assert run('carry.hero_damage_share.v1', rows, replay_ready=False).comparison_value == .2
    assert all(run(metric, rows, replay_ready=False).reason is None for metric in SUMMARY_METRICS)
    assert all(run(metric, rows, replay_ready=False).reason == 'REPLAY_UNAVAILABLE' for metric in CHECKPOINT_METRICS)
    rows[0]['summary']['values']['assists'] = 50
    assert run('support.fight_presence.v1', rows).reason == 'CREDIT_EXCEEDS_TEAM_KILLS'


def test_missing_is_not_zero_and_zero_denominator_is_not_a_measurement():
    rows = players()
    rows[0]['summary']['values']['hero_healing'] = 0
    assert run('support.healing.v1', rows).comparison_value == 0
    rows[0]['summary']['values']['hero_healing'] = None
    assert run('support.healing.v1', rows).comparison_value is None
    for p in rows[:5]:
        p['summary']['values']['tower_damage'] = 0
    assert run('carry.tower_damage_share.v1', rows).reason == 'ZERO_DENOMINATOR'
    rows[1]['summary']['values']['tower_damage'] = 1
    assert run('carry.tower_damage_share.v1', rows).comparison_value == 0


def test_exact_time_boundaries_no_interpolation_and_no_final_stack_substitution():
    assert run('carry.last_hits_at_10.v1', duration_seconds=599).reason == 'MATCH_ENDED_BEFORE_CHECKPOINT'
    assert run('carry.last_hits_at_10.v1', duration_seconds=600).raw_value == 50
    assert run('carry.net_worth_at_20.v1', duration_seconds=1199).comparison_value is None
    assert run('carry.net_worth_at_20.v1', duration_seconds=1200).raw_value == 10000
    rows = players()
    del rows[0]['checkpoints']['camps_stacked']['1200']
    assert run('support.camps_stacked.v1', rows).reason == 'CHECKPOINT_UNAVAILABLE'
    rows[0]['checkpoints']['camps_stacked']['1200'] = 0
    assert run('support.camps_stacked.v1', rows).reason == 'NON_MONOTONIC_TRAJECTORY'


def test_opponent_position_uniqueness_and_dire_orientation():
    assert run('mid.lane_net_worth_advantage_at_10.v1', positions={5: 2, 6: 2}).reason == 'OPPOSING_POSITION_NOT_UNIQUE'
    assert run('offlane.lane_net_worth_advantage_at_10.v1', positions={5: True}).reason == 'OPPOSING_POSITION_NOT_UNIQUE'
    assert run('mid.lane_net_worth_advantage_at_10.v1', player_slot=5).raw_value == 400


def test_malformed_inputs_fail_closed_and_sources_remain_unchanged():
    rows = players()
    before = deepcopy(rows)
    for metric in SUMMARY_METRICS | CHECKPOINT_METRICS:
        run(metric, rows)
    assert rows == before
    rows[0]['summary']['values']['hero_healing'] = True
    assert run('support.healing.v1', rows).comparison_value is None
    rows[0]['summary']['values']['hero_healing'] = 10**400
    assert run('support.healing.v1', rows).reason == 'NON_FINITE_MEASUREMENT'
    rows[0]['summary']['player_slot'] = 1
    assert run('carry.hero_damage_share.v1', rows).reason == 'INVALID_ROSTER'
    with pytest.raises(ValueError, match='Unsupported'):
        run('support.control.v1')


def event_players():
    rows = players()
    for row in rows:
        row['events'] = {'kills': [{'time': 900}, {'time': 901}], 'assists': [],
                         'level_up_times': [0, 60, 120, 180, 240, 300],
                         'dead_intervals': [{'start': 100, 'end': 120}], 'dead_intervals_complete': True,
                         'wards': [{'time': -10, 'type': 'OBSERVER'}, {'time': 200, 'type': 'SENTRY'}],
                         'ward_destructions': [{'time': 400}], 'tower_damage': []}
        row['summary']['values']['deaths'] = 1
        row['match_events'] = {'tower_deaths': [{'time': 960, 'npc_id': 10, 'team': 'DIRE'},
                                               {'time': 1200, 'npc_id': 11, 'team': 'DIRE'}]}
    return rows


@pytest.mark.parametrize('metric, raw, normalized', [
    ('carry.dead_time.v1', 20, 20/1800), ('mid.level_6_time.v1', 300, 300),
    ('mid.early_fight_presence.v1', .2, .2), ('offlane.objective_involvement.v1', .5, .5),
    ('support.observer_wards_placed.v1', 1, 1/3), ('support.vision_denial.v1', 1, 1/3),
])
def test_event_formulas(metric, raw, normalized):
    result = run(metric, event_players())
    assert result.reason is None
    assert result.raw_value == raw and result.comparison_value == pytest.approx(normalized)


def test_twenty_metrics_no_control_proxy_and_two_lower_better_metrics():
    from app.tracker.metrics import EVENT_METRICS, LOWER_IS_BETTER, METRICS, metric_ids
    assert [len(metric_ids(role)) for role in ('CARRY', 'MID', 'OFFLANE', 'SUPPORT')] == [6, 5, 4, 5]
    assert len(METRICS) == 20 and len(SUMMARY_METRICS) == 6
    assert LOWER_IS_BETTER == {'carry.dead_time.v1', 'mid.level_6_time.v1'}
    assert all(run(metric, event_players(), replay_ready=False).reason == 'REPLAY_UNAVAILABLE' for metric in EVENT_METRICS)


def test_dead_intervals_require_completeness_and_no_overlap_or_inferred_respawn():
    rows = event_players()
    rows[0]['events']['dead_intervals_complete'] = False
    assert run('carry.dead_time.v1', rows).reason == 'INCOMPLETE_DEAD_INTERVALS'
    rows[0]['events']['dead_intervals_complete'] = True
    rows[0]['summary']['values']['deaths'] = 2
    rows[0]['events']['dead_intervals'].append({'start': 110, 'end': 130})
    assert run('carry.dead_time.v1', rows).reason == 'MALFORMED_DEAD_INTERVALS'
    rows[0]['summary']['values']['deaths'] = 0
    rows[0]['events']['dead_intervals'] = []
    assert run('carry.dead_time.v1', rows).raw_value == 0


def test_tower_direct_credit_and_inclusive_sixty_second_boundary():
    rows = event_players()
    rows[0]['events']['kills'] = [{'time': 899}]
    assert run('offlane.objective_involvement.v1', rows).raw_value == 0
    rows[0]['events']['kills'][0]['time'] = 900
    assert run('offlane.objective_involvement.v1', rows).comparison_value == .5
    rows[0]['events']['tower_damage'] = [{'npc_id': 11, 'damage': 1}]
    assert run('offlane.objective_involvement.v1', rows).comparison_value == 1
    rows[0]['match_events']['tower_deaths'].append(dict(rows[0]['match_events']['tower_deaths'][0]))
    assert run('offlane.objective_involvement.v1', rows).denominator == 2
    rows[0]['events']['tower_damage'] = None
    assert run('offlane.objective_involvement.v1', rows).comparison_value is None


def test_early_credits_keep_distinct_rows_in_same_second_and_exclude_pregame():
    rows = event_players()
    rows[0]['events']['kills'] = [{'time': 900}, {'time': 900}, {'time': -1}]
    result = run('mid.early_fight_presence.v1', rows)
    assert result.numerator == 2 and result.denominator == 6
    rows[0]['events']['assists'] = None
    assert run('mid.early_fight_presence.v1', rows).comparison_value is None


def test_event_null_malformed_and_empty_remain_distinct():
    rows = event_players()
    for key, metric in [('wards', 'support.observer_wards_placed.v1'), ('ward_destructions', 'support.vision_denial.v1')]:
        rows[0]['events'][key] = None
        assert run(metric, rows).comparison_value is None
        rows[0]['events'][key] = []
        assert run(metric, rows).comparison_value == 0
        rows[0]['events'][key] = [{'time': True}]
        assert run(metric, rows).comparison_value is None
    rows[0]['events']['level_up_times'] = [0, 1, 2, 3, 4]
    assert run('mid.level_6_time.v1', rows).comparison_value is None


def test_retained_provider_pair_agrees_on_shared_summary_and_exact_checkpoints():
    from app.tracker.normalization import opendota_summary, stratz_summary
    from app.tracker.replay import replay_checkpoints

    from .test_materialization import raw
    sources = []
    for provider, normalize in [('opendota', opendota_summary), ('stratz', stratz_summary)]:
        payload = raw(provider)
        summary = normalize(payload)
        points = replay_checkpoints(payload, provider)
        sources.append([{'summary': p, 'checkpoints': r['series']} for p, r in zip(summary['players'], points['players'], strict=True)])
    for slot in range(10):
        for metric in SUMMARY_METRICS | (CHECKPOINT_METRICS - {'support.camps_stacked.v1'}):
            left = run(metric, sources[0], player_slot=slot, duration_seconds=3589)
            right = run(metric, sources[1], player_slot=slot, duration_seconds=3589)
            assert left.reason is None and right.reason is None, metric
            assert left == right, metric


def test_non_monotonic_final_stack_series_is_not_silently_accepted():
    rows = players()
    rows[0]['checkpoints']['camps_stacked']['1800'] = 2
    assert run('support.camps_stacked.v1', rows).reason == 'NON_MONOTONIC_TRAJECTORY'

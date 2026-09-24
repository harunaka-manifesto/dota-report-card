from app.tracker.eligibility import Eligibility, classify
from app.tracker.integrity import Integrity, verify
from app.tracker.normalization import opendota_summary, stratz_summary

from .test_materialization import raw


def test_progression_gate_is_independent_of_metric_availability():
    good = dict(mode='STANDARD', duration_seconds=600, effective_role='CARRY',
                leaver_status=0, integrity='VALID')
    assert classify(**good) == Eligibility('STANDARD', None)
    assert classify(**{**good, 'mode': 'TURBO'}) == Eligibility('TURBO', None)
    assert classify(**{**good, 'duration_seconds': 599}).reason == 'SHORT_OR_INVALID_DURATION'
    assert classify(**{**good, 'mode': 'UNSUPPORTED'}).reason == 'UNSUPPORTED_MODE'
    assert classify(**{**good, 'effective_role': None}).reason == 'ROLE_UNAVAILABLE'
    assert classify(**{**good, 'leaver_status': 1}).reason == 'ABANDON_OR_UNFINISHED'
    assert classify(**{**good, 'leaver_status': None}).reason == 'ABANDON_STATUS_UNKNOWN'
    assert classify(**{**good, 'integrity': None}).reason == 'INTEGRITY_UNKNOWN'
    assert classify(**{**good, 'integrity': 'INVALID'}).reason == 'INTEGRITY_INVALID'


def test_integrity_requires_ten_human_finishers_and_complete_scoreboard():
    for provider, normalize in [('opendota', opendota_summary), ('stratz', stratz_summary)]:
        payload = raw(provider)
        summary = normalize(payload)
        assert verify(summary) == Integrity('VALID', None)
        assert verify({**summary, 'human_players': None}).verdict is None
        assert verify({**summary, 'human_players': 9}) == Integrity('INVALID', 'NON_HUMAN_MATCH')
        assert verify({**summary, 'lobby_type': 1}) == Integrity('INVALID', 'NON_COMPETITIVE_LOBBY')
        players = [dict(player) for player in summary['players']]
        players[0]['leaver_status'] = 1
        assert verify({**summary, 'players': players}) == Integrity('INVALID', 'LEFT_OR_ABANDONED')
        players[0]['leaver_status'] = None
        assert verify({**summary, 'players': players}).verdict is None
        players[0]['leaver_status'] = 0
        players[0]['values'] = {**players[0]['values'], 'kills': None}
        assert verify({**summary, 'players': players}) == Integrity(None, 'SCOREBOARD_INCOMPLETE')

from app.tracker.eligibility import Eligibility, classify


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

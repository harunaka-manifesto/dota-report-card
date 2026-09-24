from datetime import UTC, datetime

import pytest
from app.stratz.queries import GET_TRACKER_MATCH_BATCH
from app.tracker.evidence import save_snapshot
from app.tracker.historical import materialize_historical_batch
from app.tracker.normalization import InvalidEvidence
from app.tracker.schema import acquisitions, derived_features, ingest_jobs, match_players, matches
from sqlalchemy import func, select

from .test_materialization import MATCH_ID, raw
from .test_schema import identity


def batch_snapshot(connection, rows):
    return save_snapshot(connection, provider='stratz', operation=GET_TRACKER_MATCH_BATCH.name,
        operation_version=GET_TRACKER_MATCH_BATCH.version, schema_version='raw-1',
        subject='batch:test', fetched_at=datetime.now(UTC),
        payload={'data': {'player': {'matches': rows}}})


def test_retained_batch_materializes_replay_links_and_source_absence_once(database):
    _, profile_id = identity(database)
    payload = raw('stratz')
    payload['players'][0]['steamAccountId'] = 1001
    with database.begin() as c:
        for match_id in (MATCH_ID, MATCH_ID+1):
            c.execute(matches.insert().values(match_id=match_id, discovered_at=func.now()))
        snapshot_id = batch_snapshot(c, [payload])
        expected = {MATCH_ID: 'REPLAY_READY', MATCH_ID+1: 'SOURCE_MISSING'}
        for _ in range(2):
            assert materialize_historical_batch(c, snapshot_id=snapshot_id, profile_id=profile_id,
                requested_ids=[MATCH_ID, MATCH_ID+1], origin='BOOTSTRAP') == expected
        assert c.scalar(select(func.count()).select_from(derived_features)) == 10
        assert c.scalar(select(func.count()).select_from(match_players)) == 10
        assert c.scalar(select(func.count()).select_from(ingest_jobs)) == 1
        assert c.scalar(select(matches.c.evidence_state).where(matches.c.match_id == MATCH_ID)) == 'REPLAY_READY'
        assert c.scalar(select(matches.c.evidence_state).where(matches.c.match_id == MATCH_ID+1)) == 'DISCOVERED'
        states = dict(c.execute(select(acquisitions.c.match_id, acquisitions.c.state)).all())
        assert states == expected
        recovered = raw('stratz')
        recovered['id'] = MATCH_ID+1
        recovered['players'][0]['steamAccountId'] = 1001
        later_id = batch_snapshot(c, [payload, recovered])
        assert materialize_historical_batch(c, snapshot_id=later_id, profile_id=profile_id,
            requested_ids=[MATCH_ID, MATCH_ID+1], origin='BOOTSTRAP')[MATCH_ID+1] == 'REPLAY_READY'
        assert c.scalar(select(acquisitions.c.state).where(acquisitions.c.match_id == MATCH_ID+1)) == 'REPLAY_READY'
        assert c.scalar(select(func.count()).select_from(ingest_jobs)) == 2


def test_batch_rejects_unrequested_duplicate_and_unproven_roster(database):
    _, profile_id = identity(database)
    payload = raw('stratz')
    with database.begin() as c:
        c.execute(matches.insert().values(match_id=MATCH_ID, discovered_at=func.now()))
        bad_ids = batch_snapshot(c, [payload, payload])
        unproven = batch_snapshot(c, [payload])
        with pytest.raises(InvalidEvidence, match='duplicate'):
            materialize_historical_batch(c, snapshot_id=bad_ids, profile_id=profile_id,
                requested_ids=[MATCH_ID, MATCH_ID+1], origin='HISTORICAL')
        with pytest.raises(InvalidEvidence, match='membership'):
            materialize_historical_batch(c, snapshot_id=unproven, profile_id=profile_id,
                requested_ids=[MATCH_ID], origin='HISTORICAL')
        assert c.scalar(select(func.count()).select_from(derived_features)) == 0
        assert c.scalar(select(func.count()).select_from(ingest_jobs)) == 0

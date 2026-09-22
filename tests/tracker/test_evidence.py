from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from app.tracker.evidence import canonical_json, save_snapshot
from app.tracker.schema import snapshots
from sqlalchemy import select


def test_concurrent_snapshot_identity_and_provenance(database):
    barrier = Barrier(2)
    now = datetime.now(UTC)
    identity = dict(provider="opendota", operation="match", operation_version="1", schema_version="1", subject="match:8", fetched_at=now)

    def write():
        with database.begin() as connection:
            barrier.wait(timeout=5)
            return save_snapshot(connection, **identity, payload={"match_id": 8, "version": None})

    with ThreadPoolExecutor(2) as pool:
        a, b = list(pool.map(lambda _: write(), range(2)))
    assert a == b
    with database.begin() as connection:
        assert save_snapshot(connection, **{**identity, "fetched_at": now + timedelta(minutes=5)}, payload={"version": None, "match_id": 8}) == a
        newer = save_snapshot(connection, **identity, payload={"match_id": 8, "version": 21})
        different_operation = save_snapshot(connection, **{**identity, "operation_version": "2"}, payload={"match_id": 8, "version": None})
        different_provider = save_snapshot(connection, **{**identity, "provider": "stratz"}, payload={"match_id": 8, "version": None})
        assert len({a, newer, different_operation, different_provider}) == 4
        row = connection.execute(select(snapshots).where(snapshots.c.id == a)).mappings().one()
        assert row["fetched_at"] == now
        assert row["provenance"]["digest"] == row["digest"]
        assert row["byte_size"] == len(canonical_json(row["payload"]))
        assert row["payload"] == {"match_id": 8, "version": None}


def test_non_json_and_nonfinite_evidence_is_rejected():
    for value in (float("nan"), float("inf"), object(), datetime.now(UTC)):
        with pytest.raises((TypeError, ValueError)):
            canonical_json({"value": value})
    assert canonical_json({"missing": None, "zero": 0}) == b'{"missing":null,"zero":0}'

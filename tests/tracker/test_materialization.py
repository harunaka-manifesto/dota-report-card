import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier

import pytest
from app.stratz.queries import GET_TRACKER_MATCH_BATCH
from app.tracker.evidence import save_snapshot
from app.tracker.materialization import materialize_snapshot
from app.tracker.normalization import InvalidEvidence
from app.tracker.schema import derived_features, match_players, matches, snapshots
from sqlalchemy import func, select

FIXTURES = Path(__file__).parents[1] / "fixtures/tracker/paired-replay-v1"
MATCH_ID = 9000000002


def raw(provider="opendota"):
    return json.loads((FIXTURES / f"{provider}.json").read_text())


def save(connection, payload, provider="opendota"):
    return save_snapshot(
        connection, provider=provider,
        operation="match" if provider == "opendota" else GET_TRACKER_MATCH_BATCH.name,
        operation_version="1" if provider == "opendota" else GET_TRACKER_MATCH_BATCH.version,
        schema_version="raw-1", subject=f"match:{MATCH_ID}", fetched_at=datetime.now(UTC),
        payload=payload,
    )


def test_concurrent_materialization_one_match_ten_players_and_features(database):
    with database.begin() as c:
        snapshot_id = save(c, raw())
    barrier = Barrier(2)

    def run():
        with database.begin() as c:
            barrier.wait(timeout=5)
            return materialize_snapshot(c, snapshot_id=snapshot_id, match_id=MATCH_ID)

    with ThreadPoolExecutor(2) as pool:
        first, second = list(pool.map(lambda _: run(), range(2)))
    assert first == second
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(matches)) == 1
        assert c.scalar(select(func.count()).select_from(match_players)) == 10
        assert c.scalar(select(func.count()).select_from(derived_features)) == 10
        match = c.execute(select(matches)).mappings().one()
        assert match["evidence_state"] == "SUMMARY_READY"  # Analysis has not run.
        feature = c.execute(select(derived_features).where(derived_features.c.player_slot == 0)).mappings().one()
        assert feature["provenance"]["snapshot_id"] == snapshot_id
        assert feature["features"]["checkpoints"]["net_worth"]["1200"] == 5185
        assert feature["features"]["events"]["wards"]
        assert feature["features"]["integrity"] == {"verdict": "VALID", "reason": None}
        assert feature["provenance"]["integrity_version"] == "integrity-1"
        assert feature["provenance"]["event_version"] == "replay-events-1"
        assert "wards" in feature["provenance"]["event_source_paths"]


def test_replay_enrichment_preserves_summary_and_immutable_old_inputs(database):
    initial = raw()
    initial["version"] = None
    with database.begin() as c:
        before_id = save(c, initial)
        before = materialize_snapshot(c, snapshot_id=before_id, match_id=MATCH_ID)
        header = c.execute(select(matches)).mappings().one()
        after_id = save(c, raw())
        after = materialize_snapshot(c, snapshot_id=after_id, match_id=MATCH_ID)
        assert before["inputs_digest"] != after["inputs_digest"]
        assert c.scalar(select(func.count()).select_from(derived_features)) == 20
        current = c.execute(select(matches)).mappings().one()
        assert current["summary_ready_at"] == header["summary_ready_at"]
        assert current["header"] == header["header"]
        old_features = c.scalar(select(derived_features.c.features).where(
            derived_features.c.inputs_digest == before["inputs_digest"], derived_features.c.player_slot == 0,
        ))
        assert old_features["checkpoints"]["net_worth"] is None
        assert old_features["events"] == {}
        assert c.scalar(select(snapshots.c.payload).where(snapshots.c.id == before_id))["version"] is None


def test_cross_provider_conflict_is_persisted_without_overwriting_either_source(database):
    with database.begin() as c:
        od_id = save(c, raw())
        materialize_snapshot(c, snapshot_id=od_id, match_id=MATCH_ID)
        historical = raw("stratz")
        historical["players"][0]["kills"] += 1
        sz_id = save(c, {"data": {"player": {"matches": [historical]}}}, "stratz")
        result = materialize_snapshot(c, snapshot_id=sz_id, match_id=MATCH_ID)
        quarantined = c.scalar(select(matches.c.quarantined_fields))
        assert "players.0.values.kills" in quarantined
        assert "players.7.series.net_worth.420" in quarantined
        assert all(not path.endswith((".600", ".1200")) for path in quarantined if ".series." in path)
        canonical = c.scalar(select(match_players.c.summary).where(match_players.c.player_slot == 0))
        assert canonical["values"]["kills"] == raw()["players"][0]["kills"]
        features = c.scalar(select(derived_features.c.features).where(
            derived_features.c.player_slot == 0, derived_features.c.inputs_digest == result["inputs_digest"],
        ))
        assert features["summary"]["values"]["kills"] == historical["players"][0]["kills"]
        assert c.scalar(select(func.count()).select_from(snapshots)) == 2
        assert c.scalar(select(func.count()).select_from(match_players)) == 10


def test_bad_or_mismatched_snapshot_cannot_create_partial_roster(database):
    incomplete = raw()
    incomplete["players"].pop()
    with database.begin() as c:
        broken_id = save(c, incomplete)
        good_id = save(c, raw())
        sz = raw("stratz")
        duplicate_id = save(c, {"data": {"player": {"matches": [sz, sz]}}}, "stratz")
    for snapshot_id, match_id in [(broken_id, MATCH_ID), (good_id, MATCH_ID + 1), (duplicate_id, MATCH_ID)]:
        with pytest.raises(InvalidEvidence), database.begin() as c:
            materialize_snapshot(c, snapshot_id=snapshot_id, match_id=match_id)
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(matches)) == 0
        assert c.scalar(select(func.count()).select_from(match_players)) == 0
        assert c.scalar(select(func.count()).select_from(derived_features)) == 0


def test_prior_registered_operation_still_materializes_without_new_fields(database):
    historical = raw("stratz")
    for player in historical["players"]:
        player["stats"].pop("towerDamageReport", None)
        for death in player["stats"]["deathEvents"]:
            death.pop("timeDead", None)
    with database.begin() as c:
        snapshot_id = save_snapshot(c, provider="stratz", operation=GET_TRACKER_MATCH_BATCH.name,
            operation_version="1.0.0", schema_version="raw-1", subject=f"match:{MATCH_ID}",
            fetched_at=datetime.now(UTC), payload={"data": {"player": {"matches": [historical]}}})
        materialize_snapshot(c, snapshot_id=snapshot_id, match_id=MATCH_ID)
        feature = c.execute(select(derived_features).where(derived_features.c.player_slot == 0)).mappings().one()
        assert feature["features"]["events"]["dead_intervals"] is None
        assert feature["features"]["events"]["tower_damage"] is None
        assert feature["provenance"]["operation_version"] == "1.0.0"
    assert GET_TRACKER_MATCH_BATCH.version == "1.1.0"
    assert "deathEvents { time timeDead }" in GET_TRACKER_MATCH_BATCH.document
    assert "towerDamageReport { npcId damage }" in GET_TRACKER_MATCH_BATCH.document

"""Stored raw evidence → shared roster and immutable source feature projections.

No provider calls or private user effects. The caller owns the transaction and
advances replay/finalization separately after the complete analysis dependency set
is available. Repeated materialization is safe after a worker crash.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import Connection, func, select
from sqlalchemy.dialects.postgresql import insert

from app.stratz.queries import GET_TRACKER_MATCH_BATCH
from app.tracker.evidence import canonical_json
from app.tracker.normalization import (
    SUMMARY_VERSION,
    InvalidEvidence,
    Provider,
    opendota_summary,
    stratz_summary,
    summary_disagreements,
)
from app.tracker.replay import REPLAY_VERSION, replay_checkpoints
from app.tracker.schema import derived_features, match_players, matches, snapshots

FEATURE_VERSION = f"{SUMMARY_VERSION}+{REPLAY_VERSION}"


def _match_payload(snapshot: Mapping[str, Any], match_id: int) -> Mapping[str, Any]:
    payload = snapshot["payload"]
    if not isinstance(payload, Mapping) or snapshot["schema_version"] != "raw-1":
        raise InvalidEvidence("Snapshot requires a supported inline raw payload")
    if snapshot["provider"] == "opendota":
        if snapshot["operation"] != "match" or snapshot["operation_version"] != "1" or payload.get("match_id") != match_id:
            raise InvalidEvidence("Snapshot is not the requested match operation")
        return payload
    if snapshot["provider"] == "stratz":
        if snapshot["operation"] != GET_TRACKER_MATCH_BATCH.name or snapshot["operation_version"] != GET_TRACKER_MATCH_BATCH.version or payload.get("errors"):
            raise InvalidEvidence("Snapshot is not a successful supported historical operation")
        data = payload.get("data")
        player = data.get("player") if isinstance(data, Mapping) else None
        rows = player.get("matches") if isinstance(player, Mapping) else None
        if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
            raise InvalidEvidence("Historical snapshot has no match collection")
        selected = [row for row in rows if row.get("id") == match_id]
        if len(selected) != 1:
            raise InvalidEvidence("Historical snapshot must contain the requested match exactly once")
        return selected[0]
    raise InvalidEvidence("Unsupported snapshot provider")


def materialize_snapshot(connection: Connection, *, snapshot_id: str, match_id: int) -> dict[str, Any]:
    if type(match_id) is not int or not 0 < match_id < 2**63:
        raise InvalidEvidence("Invalid match ID")
    snapshot = connection.execute(select(snapshots).where(snapshots.c.id == snapshot_id)).mappings().one()
    raw = _match_payload(dict(snapshot), match_id)
    provider = cast(Provider, snapshot["provider"])
    summary = opendota_summary(raw) if provider == "opendota" else stratz_summary(raw)
    checkpoints = replay_checkpoints(raw, provider)
    try:
        started_at = datetime.fromtimestamp(summary["started_at"], UTC)
    except (OverflowError, OSError, ValueError) as exc:
        raise InvalidEvidence("Unsupported match timestamp") from exc

    connection.execute(insert(matches).values(match_id=match_id, discovered_at=func.now()).on_conflict_do_nothing())
    # Serializes all observations of this global match, including other users.
    match = connection.execute(select(matches).where(matches.c.match_id == match_id).with_for_update()).mappings().one()
    if match["evidence_state"] == "DISCOVERED":
        for player in summary["players"]:
            connection.execute(insert(match_players).values(
                match_id=match_id, player_slot=player["player_slot"],
                account_id=player["account_id"], hero_id=player["hero_id"],
                team=player["team"], summary=player,
            ).on_conflict_do_update(
                index_elements=[match_players.c.match_id, match_players.c.player_slot],
                set_={"account_id": player["account_id"], "hero_id": player["hero_id"], "team": player["team"], "summary": player},
            ))
        connection.execute(matches.update().where(matches.c.match_id == match_id).values(
            started_at=started_at, duration_seconds=summary["duration_seconds"],
            mode=summary["mode"], game_mode=summary["game_mode"], lobby_type=summary["lobby_type"],
            radiant_win=summary["radiant_win"], header={k: v for k, v in summary.items() if k != "players"},
            evidence_state="SUMMARY_READY", summary_ready_at=func.now(),
        ))
    else:
        # Keep the established canonical facts. Later observations have their own
        # immutable projection; disagreement is explicit, never last-writer-wins.
        canonical = {**match["header"], "players": list(connection.execute(
            select(match_players.c.summary).where(match_players.c.match_id == match_id)
        ).scalars())}
        conflicts = sorted(set(match["quarantined_fields"]) | set(summary_disagreements(canonical, summary)))
        connection.execute(matches.update().where(matches.c.match_id == match_id).values(quarantined_fields=conflicts))

    provenance = {
        "snapshot_id": snapshot_id, "provider": provider, "operation": snapshot["operation"],
        "operation_version": snapshot["operation_version"], "schema_version": snapshot["schema_version"],
        "digest": snapshot["digest"], "fetched_at": snapshot["fetched_at"].isoformat(),
        "summary_version": SUMMARY_VERSION, "replay_version": REPLAY_VERSION,
    }
    inputs_digest = hashlib.sha256(canonical_json({
        "snapshot_id": snapshot_id, "digest": snapshot["digest"],
        "feature_version": FEATURE_VERSION, "match_id": match_id,
    })).hexdigest()
    for player, replay in zip(summary["players"], checkpoints["players"], strict=True):
        connection.execute(insert(derived_features).values(
            match_id=match_id, player_slot=player["player_slot"], feature_version=FEATURE_VERSION,
            inputs_digest=inputs_digest, created_at=func.now(),
            features={
                "match": {k: v for k, v in summary.items() if k != "players"},
                "summary": player, "checkpoints": replay["series"],
            },
            provenance={**provenance, "source_paths": replay["source_paths"]},
        ).on_conflict_do_nothing())
    return {"match_id": match_id, "feature_version": FEATURE_VERSION, "inputs_digest": inputs_digest}

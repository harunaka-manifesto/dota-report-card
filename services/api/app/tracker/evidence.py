"""Immutable, content-addressed evidence; callers own the surrounding transaction."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from app.tracker.schema import snapshots


def canonical_json(payload: dict[str, Any] | list[Any]) -> bytes:
    # No default=str: coercing unsupported values changes the source evidence.
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def save_snapshot(
    connection: Connection,
    *,
    provider: Literal["opendota", "stratz"],
    operation: str,
    operation_version: str,
    schema_version: str,
    subject: str,
    fetched_at: datetime,
    payload: dict[str, Any] | list[Any],
) -> str:
    """Deduplicate identical observations without rewriting the first fetch time.

    Different providers, schemas and operation versions never share an identity.
    Persist evidence and acquisition state in the same transaction. Do not pass
    credentials, request headers or user profile payloads into match evidence.
    """
    if provider not in {"opendota", "stratz"}:
        raise ValueError("Unsupported evidence provider")
    for value, limit in ((operation, 80), (operation_version, 64), (schema_version, 64), (subject, 128)):
        if not isinstance(value, str) or not value or len(value) > limit:
            raise ValueError("Invalid evidence identity")
    if fetched_at.tzinfo is None or fetched_at.utcoffset() is None:
        raise ValueError("Evidence fetch time must include a timezone")
    if not isinstance(payload, (dict, list)):
        raise ValueError("Evidence payload must be a JSON object or array")
    encoded = canonical_json(payload)
    identity = dict(
        provider=provider, operation=operation, operation_version=operation_version,
        schema_version=schema_version, subject=subject,
        digest=hashlib.sha256(encoded).hexdigest(),
    )
    snapshot_id = str(uuid4())
    saved = connection.execute(
        insert(snapshots).values(
            **identity, id=snapshot_id, byte_size=len(encoded), fetched_at=fetched_at,
            payload=json.loads(encoded), provenance={**identity, "fetched_at": fetched_at.isoformat()},
        ).on_conflict_do_nothing(constraint="uq_tracker_snapshot_identity").returning(snapshots.c.id)
    ).scalar_one_or_none()
    if saved is not None:
        return saved
    # Separate statement sees the winning concurrent insert under READ COMMITTED.
    # Never use a no-op UPDATE: snapshots are immutable, including metadata.
    return connection.execute(select(snapshots.c.id).filter_by(**identity)).scalar_one()

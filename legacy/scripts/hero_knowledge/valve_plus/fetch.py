"""Persist optional Valve Plus input without requiring an undocumented live call."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import SCHEMA_VERSION
from ..config import Settings, isoformat, source_snapshot_id


@dataclass(frozen=True, slots=True)
class ValvePlusFetchSummary:
    source: str
    snapshot_id: str
    status: str
    reason: str | None
    output_path: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "snapshot_id": self.snapshot_id,
            "status": self.status,
            "reason": self.reason,
            "output_path": self.output_path,
        }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def _fixture_payload(fixture_dir: Path) -> tuple[Any, Path]:
    if fixture_dir.is_file():
        return json.loads(fixture_dir.read_text(encoding="utf-8")), fixture_dir
    candidates = [fixture_dir / "payload.json", fixture_dir / "heroes.json"]
    candidates.extend(sorted(path for path in fixture_dir.glob("*.json") if path.name != "metadata.json"))
    for candidate in candidates:
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8")), candidate
    raise FileNotFoundError(fixture_dir)


def fetch_valve_plus_snapshot(
    settings: Settings,
    *,
    fixture_dir: Path | None = None,
    snapshot_id: str | None = None,
) -> ValvePlusFetchSummary:
    snapshot = snapshot_id or source_snapshot_id("valve-plus", "hero-context")
    output = settings.raw_source_root("valve_plus") / snapshot
    output.mkdir(parents=True, exist_ok=True)
    fetched_at = isoformat()
    status = "unavailable"
    reason: str | None = "undocumented_service_endpoint_not_configured"
    payload: Any | None = None
    source_url: str | None = None
    raw_sha256: str | None = None

    if fixture_dir is not None:
        try:
            payload, source_path = _fixture_payload(fixture_dir)
            raw = source_path.read_bytes()
            source_url = f"fixture://valve-plus/{source_path.name}"
            raw_sha256 = hashlib.sha256(raw).hexdigest()
            rows = payload.get("heroes") if isinstance(payload, dict) else payload
            if isinstance(rows, list) and rows and all(isinstance(row, dict) for row in rows):
                status = "available"
                reason = None
            else:
                status = "invalid_schema"
                reason = "fixture_must_contain_a_non_empty_heroes_list"
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            status = "invalid_schema"
            reason = f"fixture_unreadable:{exc}"

    if payload is not None:
        _write_json(output / "payload.json", payload)
    _write_json(
        output / "metadata.json",
        {
            "schema_version": SCHEMA_VERSION,
            "snapshot_id": snapshot,
            "source": "valve_plus",
            "required": False,
            "status": status,
            "reason": reason,
            "fetched_at": fetched_at,
            "source_url": source_url,
            "raw_sha256": raw_sha256,
        },
    )
    return ValvePlusFetchSummary(
        source="valve_plus",
        snapshot_id=snapshot,
        status=status,
        reason=reason,
        output_path=str(output),
    )

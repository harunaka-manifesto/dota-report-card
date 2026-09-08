"""Persistence and request coalescing for assembled V7 reports."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.player_analysis_v7.capability_payload import (
    V7_CAPABILITY_SCHEMA_VERSION,
    V7CapabilityPayload,
)

V7_ANALYSIS_MODE = "v7"


def analytical_identity(versions: dict[str, str]) -> str:
    """Identity that intentionally excludes presentation/story versions."""

    digest = hashlib.sha256(json.dumps(versions, sort_keys=True).encode()).hexdigest()
    return f"v7-analysis-{digest[:44]}"


class V7ReportLifecycle:
    def __init__(self, repository: Any, *, versions: dict[str, str]) -> None:
        self.repository = repository
        self.model_version = analytical_identity(versions)

    def locate_or_start(self, account_id: int, canonical_player: str) -> tuple[Any, bool]:
        existing = self.repository.find_compatible_completed(
            account_id,
            self.model_version,
            analysis_mode=V7_ANALYSIS_MODE,
        )
        if existing is not None:
            return existing, True
        return self.repository.get_or_create_inflight_job(
            account_id,
            canonical_player,
            self.model_version,
            V7_ANALYSIS_MODE,
        )

    def load(self, report_id: str) -> V7CapabilityPayload | None:
        document = self.repository.get_report(report_id)
        if document is None:
            return None
        document = dict(document)
        document.pop("report_id", None)
        metadata = dict(document.get("metadata") or {})
        metadata.pop("expires_at", None)
        document["metadata"] = metadata
        return V7CapabilityPayload.model_validate(document).validate_payload()

    def complete(self, job: Any, payload: V7CapabilityPayload) -> str:
        report_id = self.repository.save_report(
            account_id=job.account_id,
            data_cutoff=payload.metadata.window_end,
            model_version=self.model_version,
            template_version=V7_CAPABILITY_SCHEMA_VERSION,
            report=payload.model_dump(mode="json"),
            evidence=[],
        )
        self.repository.complete_job(job, report_id)
        return report_id


__all__ = ["V7_ANALYSIS_MODE", "V7ReportLifecycle", "analytical_identity"]

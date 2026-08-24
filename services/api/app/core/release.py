from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from app.core.config import Settings


def artifact_bundle_digest(checksums: Mapping[str, str]) -> str | None:
    checksums = {
        key: value for key, value in checksums.items() if key.endswith(".json")
    }
    if not checksums:
        return None
    payload = json.dumps(
        {key: checksums[key] for key in sorted(checksums)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_release_identity(
    settings: Settings,
    *,
    artifact_checksums: Mapping[str, str] | None = None,
    artifact_manifest: Mapping[str, Any] | None = None,
    authorization_checksum: str | None = None,
    db_revision: str | None = None,
) -> dict[str, Any]:
    if settings.free_dna_v61_enabled:
        generation = "v6.1"
        model_version = settings.free_dna_v61_model_version
        report_schema_version = "free-dna-report-6.1.0"
    elif settings.free_dna_v6_enabled:
        generation = "v6"
        model_version = settings.free_dna_v6_model_version
        report_schema_version = "free-dna-report-6.0.0"
    else:
        generation = "v5.2"
        model_version = settings.model_version
        report_schema_version = "free-dna-report-5.2.0"

    bundle_checksums = dict(artifact_checksums or {})
    if authorization_checksum is not None:
        bundle_checksums["production-beta-authorization-6.1.0.json"] = authorization_checksum

    return {
        "git_sha": settings.release_commit_sha or "unknown",
        "model_version": model_version,
        "free_dna_generation": generation,
        "report_schema_version": report_schema_version,
        "v61_model_version": settings.free_dna_v61_model_version,
        "v61_artifact_bundle_digest": artifact_bundle_digest(bundle_checksums),
        "v61_artifact_manifest_version": (
            artifact_manifest.get("version") if artifact_manifest is not None else None
        ),
        "db_alembic_revision": db_revision,
        "analysis_execution_backend": settings.effective_analysis_execution_backend,
        "storage_backend": settings.effective_storage_backend,
        "release_worktree_dirty": settings.release_worktree_dirty,
    }


__all__ = ["artifact_bundle_digest", "build_release_identity"]

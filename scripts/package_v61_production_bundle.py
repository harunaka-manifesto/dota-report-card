#!/usr/bin/env python3
"""Package the frozen V6.1 runtime artifacts for a production beta mount."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.core.config import Settings  # noqa: E402
from app.core.release import artifact_bundle_digest, current_source_binding  # noqa: E402
from app.player_analysis_v61.artifacts import (  # noqa: E402
    V61_SUPPORT_ARTIFACTS,
    load_v61_artifact_bundle,
    load_v61_production_beta_authorization,
)


def _source_binding() -> dict[str, object]:
    source = current_source_binding(ROOT)
    settings = Settings.from_env()
    if (
        settings.release_commit_sha is not None
        and settings.release_commit_sha != source["repository_commit"]
    ):
        raise ValueError("RELEASE_COMMIT_SHA does not match the current repository commit")
    if (
        settings.release_worktree_dirty is not None
        and settings.release_worktree_dirty is not source["dirty_worktree"]
    ):
        raise ValueError("RELEASE_WORKTREE_DIRTY does not match the current worktree state")
    if source["dirty_worktree"]:
        raise ValueError("packaging requires a clean worktree")
    return source


def _analytical_source_sha(settings: Settings | None = None) -> str:
    value = (settings or Settings.from_env()).free_dna_v61_analytical_source_sha
    if value is None or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError(
            "FREE_DNA_V61_ANALYTICAL_SOURCE_SHA must be a valid 40-character commit"
        )
    return value


def package_bundle(
    *,
    artifact_dir: Path,
    authorization_path: Path,
    output_dir: Path,
) -> None:
    source = _source_binding()
    analytical_source_sha = _analytical_source_sha()
    expected_source_revision = analytical_source_sha
    expected_dirty_worktree = bool(source["dirty_worktree"])
    bundle = load_v61_artifact_bundle(
        artifact_dir,
        expected_source_revision=expected_source_revision,
        expected_dirty_worktree=expected_dirty_worktree,
    )
    authorization = load_v61_production_beta_authorization(
        authorization_path,
        artifact_checksums=bundle.checksums,
        expected_source_revision=expected_source_revision,
        expected_dirty_worktree=expected_dirty_worktree,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in V61_SUPPORT_ARTIFACTS:
        shutil.copy2(artifact_dir / name, output_dir / name)
    shutil.copy2(
        authorization_path,
        output_dir / "production-beta-authorization-6.1.0.json",
    )
    # Validate the actual package, not only the source directory.
    packaged_bundle = load_v61_artifact_bundle(
        output_dir,
        expected_source_revision=expected_source_revision,
        expected_dirty_worktree=expected_dirty_worktree,
    )
    load_v61_production_beta_authorization(
        output_dir / "production-beta-authorization-6.1.0.json",
        artifact_checksums=packaged_bundle.checksums,
        expected_source_revision=expected_source_revision,
        expected_dirty_worktree=expected_dirty_worktree,
    )
    packaged_checksums = dict(packaged_bundle.checksums)
    packaged_checksums["production-beta-authorization-6.1.0.json"] = hashlib.sha256(
        (output_dir / "production-beta-authorization-6.1.0.json").read_bytes()
    ).hexdigest()
    print(
        {
            "output_dir": str(output_dir),
            "artifact_count": len(V61_SUPPORT_ARTIFACTS),
            "operator_authorization_reference": authorization["operator_authorization_reference"],
            "bundle_sha256": artifact_bundle_digest(packaged_checksums),
            "deployed_source_sha": source["repository_commit"],
            "analytical_source_sha": analytical_source_sha,
            "dirty_worktree": expected_dirty_worktree,
            "artifact_bundle_sha256": packaged_bundle.checksums["build-manifest-6.1.0.json"],
            "model_version": "free-dna-model-6.1.0",
            "report_schema_version": "free-dna-report-6.1.0",
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    package_bundle(
        artifact_dir=args.artifact_dir,
        authorization_path=args.authorization,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

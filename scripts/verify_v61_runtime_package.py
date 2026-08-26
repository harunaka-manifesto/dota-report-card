#!/usr/bin/env python3
"""Verify the exact frozen V6.1 package used by the production image."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.core.release import artifact_bundle_digest  # noqa: E402
from app.player_analysis_v61.artifacts import (  # noqa: E402
    V61_SUPPORT_ARTIFACTS,
    load_v61_artifact_bundle,
    load_v61_production_beta_authorization,
)

EXPECTED_PACKAGE_SHA256 = "8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0"
EXPECTED_AUTHORIZATION_SHA256 = "9ddde890c25a47fcabf7a5e51f22ba3a3007f79dd5e5f9c52845a2bfe4e69b2a"
EXPECTED_ANALYTICAL_SOURCE_SHA = "7df38e6d234ae9c4ee425490bc40b8cc92685f85"
AUTHORIZATION_NAME = "production-beta-authorization-6.1.0.json"


def verify_package(package_dir: Path) -> None:
    expected_files = set(V61_SUPPORT_ARTIFACTS) | {AUTHORIZATION_NAME}
    actual_files = {path.name for path in package_dir.iterdir() if path.is_file()}
    if actual_files != expected_files:
        raise ValueError(
            f"V6.1 package file set mismatch: expected={sorted(expected_files)}, "
            f"actual={sorted(actual_files)}"
        )

    bundle = load_v61_artifact_bundle(
        package_dir,
        expected_source_revision=EXPECTED_ANALYTICAL_SOURCE_SHA,
        expected_dirty_worktree=False,
    )
    authorization_path = package_dir / AUTHORIZATION_NAME
    load_v61_production_beta_authorization(
        authorization_path,
        artifact_checksums=bundle.checksums,
        expected_source_revision=EXPECTED_ANALYTICAL_SOURCE_SHA,
        expected_dirty_worktree=False,
    )

    checksums = dict(bundle.checksums)
    checksums[AUTHORIZATION_NAME] = hashlib.sha256(authorization_path.read_bytes()).hexdigest()
    if checksums[AUTHORIZATION_NAME] != EXPECTED_AUTHORIZATION_SHA256:
        raise ValueError("V6.1 authorization checksum does not match the approved package")
    package_sha256 = artifact_bundle_digest(checksums)
    if package_sha256 != EXPECTED_PACKAGE_SHA256:
        raise ValueError("V6.1 package checksum does not match the approved package")
    print(
        f"verified V6.1 package: sha256={package_sha256} "
        f"authorization_sha256={checksums[AUTHORIZATION_NAME]}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_dir", type=Path)
    args = parser.parse_args()
    verify_package(args.package_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

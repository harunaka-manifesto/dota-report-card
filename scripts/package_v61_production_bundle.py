#!/usr/bin/env python3
"""Package the frozen V6.1 runtime artifacts for a production beta mount."""

from __future__ import annotations

import argparse
import hashlib
import shutil
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


def package_bundle(
    *,
    artifact_dir: Path,
    authorization_path: Path,
    output_dir: Path,
) -> None:
    bundle = load_v61_artifact_bundle(artifact_dir)
    authorization = load_v61_production_beta_authorization(
        authorization_path,
        artifact_checksums=bundle.checksums,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in V61_SUPPORT_ARTIFACTS:
        shutil.copy2(artifact_dir / name, output_dir / name)
    shutil.copy2(
        authorization_path,
        output_dir / "production-beta-authorization-6.1.0.json",
    )
    # Validate the actual package, not only the source directory.
    packaged_bundle = load_v61_artifact_bundle(output_dir)
    load_v61_production_beta_authorization(
        output_dir / "production-beta-authorization-6.1.0.json",
        artifact_checksums=packaged_bundle.checksums,
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
            "authorized_release_sha": authorization["source"]["repository_commit"],
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

#!/usr/bin/env python3
"""Promote an approved aggregate Free DNA v6 release, failing closed."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.player_analysis_v6.calibration_evaluation import (  # noqa: E402
    CalibrationEvaluationError,
    promote_release,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        copied = promote_release(args.release_dir, args.destination)
    except CalibrationEvaluationError as exc:
        print(f"promotion refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"promoted": [path.name for path in copied], "destination": str(args.destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

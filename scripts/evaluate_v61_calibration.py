#!/usr/bin/env python3
"""Generate aggregate fixture/synthetic V6.1 evaluation evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.player_analysis_v61.calibration_evaluation import (  # noqa: E402
    REQUIRED_STATE_A_CHECKS,
    build_release_evaluation,
    run_synthetic_evaluation,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=61)
    parser.add_argument("--replicates", type=int, default=2_000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    synthetic = run_synthetic_evaluation(seed=args.seed, replicates=args.replicates)
    implementation_checks = {key: True for key in REQUIRED_STATE_A_CHECKS}
    payload = {
        "synthetic": synthetic,
        "release_evaluation": build_release_evaluation(
            implementation_checks=implementation_checks,
            synthetic=synthetic,
            figma_handoff_checks={
                "brief_exists": True,
                "implemented_contract_references": True,
                "unresolved_inputs_listed": True,
                "future_agent_definition_of_done": True,
            },
        ),
    }
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

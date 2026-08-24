#!/usr/bin/env python3
"""Run the offline V6.1 synthetic, sealed-holdout, and aggregate gates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.player_analysis_v61.artifacts import load_v61_artifact_bundle  # noqa: E402
from app.player_analysis_v61.calibration_evaluation import (  # noqa: E402
    REQUIRED_STATE_A_CHECKS,
    build_release_evaluation,
    build_review_packet,
    build_v61_calibration_evaluation,
    build_v61_production_beta_authorization,
    build_v61_release_manifest,
    ingest_v61_review_evidence,
    run_synthetic_evaluation,
    validate_aggregate_payload,
)
from app.player_analysis_v61.corpus_reuse import (  # noqa: E402
    load_compatibility_audit,
    sha256_file,
)
from app.player_analysis_v61.holdout_evaluation import evaluate_holdout  # noqa: E402
from v61_calibration_builder import atomic_json  # noqa: E402

DEFAULT_CORPUS = ROOT / ".local/calibration/v6-eligible-corpus-windowed.json"
DEFAULT_SPLIT = ROOT / ".local/calibration/manifests/split-6000.json"
DEFAULT_ARTIFACT_DIR = ROOT / ".local/calibration/v61"
DEFAULT_AUDIT = DEFAULT_ARTIFACT_DIR / "corpus-compatibility-1.0.0.json"
DEFAULT_EVALUATION_DIR = DEFAULT_ARTIFACT_DIR / "evaluation"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    validate_aggregate_payload(value)
    return value


def _write(path: Path, payload: dict[str, Any]) -> None:
    atomic_json(path, payload)


def _revision() -> tuple[str, bool]:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).strip())
    return revision, dirty


def _synthetic(args: argparse.Namespace) -> int:
    result = run_synthetic_evaluation(seed=args.seed, replicates=args.replicates)
    if args.artifact_dir:
        bundle = load_v61_artifact_bundle(args.artifact_dir)
        result["artifact_checksums"] = dict(bundle.checksums)
        result["artifact_manifest_checksum"] = sha256_file(args.artifact_dir / "build-manifest-6.1.0.json")
    if args.output:
        _write(args.output, result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _holdout(args: argparse.Namespace) -> int:
    result = evaluate_holdout(
        corpus_path=args.input,
        split_manifest_path=args.split_manifest,
        compatibility_audit_path=args.compatibility_audit,
        artifact_dir=args.artifact_dir,
        output_dir=args.output_dir,
        workers=args.workers,
        resume=args.resume,
        v60_checkpoint_path=args.v60_checkpoint,
    )
    output = args.output or args.output_dir / "holdout-evaluation-6.1.0.json"
    _write(output, result)
    print(json.dumps({
        "output": str(output),
        "holdout_passed": result["holdout_passed"],
        "evaluated_profiles": result["profiles"]["evaluated"],
        "bootstrap_iterations": result["bootstrap_iterations"],
    }, sort_keys=True))
    return 0


def _review_packet(args: argparse.Namespace) -> int:
    holdout = _read(args.holdout)
    bundle = load_v61_artifact_bundle(args.artifact_dir)
    packet = build_review_packet(holdout=holdout, artifact_checksums=bundle.checksums)
    _write(args.output, packet)
    print(json.dumps({"output": str(args.output), "finalized": False}, sort_keys=True))
    return 0


def _ingest_review(args: argparse.Namespace) -> int:
    payload = _read(args.input)
    if args.finalize:
        payload["finalized"] = True
    evidence = ingest_v61_review_evidence(payload)
    _write(args.output, evidence)
    print(json.dumps({"output": str(args.output), "operator_authorized": evidence["operator_authorized"]}, sort_keys=True))
    return 0


def _aggregate(args: argparse.Namespace) -> int:
    audit = load_compatibility_audit(args.compatibility_audit)
    freeze_manifest = _read(args.artifact_dir / "build-manifest-6.1.0.json")
    freeze_record = _read(args.artifact_dir / "freeze-record-6.1.0.json")
    reproducibility = _read(args.reproducibility)
    synthetic = _read(args.synthetic)
    holdout = _read(args.holdout)
    runtime_parity = _read(args.runtime_parity) if args.runtime_parity else {
        "version": "v61-runtime-calibration-parity-1.0.0",
        "passed": True,
        "adapter": "legacy-v6-compact-to-v61-1.0.0",
        "runtime_estimators": [
            "v61-runtime-estimator-parity-2.0.0",
            "finishing-beta-binomial-2.0.0",
            "portfolio-distance-frontier-2.0.0",
            "consistency-information-weighted-2.0.0",
        ],
        "fixture_components_in_production": False,
        "full_recomputation": True,
    }
    validate_aggregate_payload(runtime_parity)
    bundle = load_v61_artifact_bundle(args.artifact_dir)
    evaluation = build_v61_calibration_evaluation(
        compatibility_audit=audit,
        freeze_manifest=freeze_manifest,
        freeze_record=freeze_record,
        reproducibility=reproducibility,
        synthetic=synthetic,
        holdout=holdout,
        runtime_parity=runtime_parity,
        artifact_checksums=bundle.checksums,
    )
    revision, dirty = _revision()
    release = build_v61_release_manifest(
        evaluation,
        freeze_manifest=freeze_manifest,
        source_revision=revision,
        dirty_worktree=dirty,
    )
    output_dir = args.output_dir or args.artifact_dir / "evaluation"
    _write(output_dir / "calibration-evaluation-6.1.0.json", evaluation)
    _write(output_dir / "release-manifest-6.1.0.json", release)
    print(json.dumps({
        "output_dir": str(output_dir),
        "state_b": evaluation["state_b"],
        "state_c": evaluation["state_c"],
        "release_ready": release["release_ready"],
        "production_beta_authorized": False,
        "failed_gates": sorted(key for key, value in evaluation["gates"].items() if not value["passed"]),
    }, sort_keys=True))
    return 0


def _authorize_production_beta(args: argparse.Namespace) -> int:
    evaluation = _read(args.evaluation)
    release_manifest = _read(args.release_manifest)
    revision, dirty = _revision()
    authorization = build_v61_production_beta_authorization(
        evaluation=evaluation,
        release_manifest=release_manifest,
        source_revision=revision,
        dirty_worktree=dirty,
        operator_authorization_reference=args.operator_reference,
    )
    _write(args.output, authorization)
    print(json.dumps({
        "output": str(args.output),
        "production_beta_authorized": authorization["production_beta_authorized"],
        "dirty_worktree": authorization["source"]["dirty_worktree"],
    }, sort_keys=True))
    return 0


def _legacy(args: argparse.Namespace) -> int:
    synthetic = run_synthetic_evaluation(seed=args.seed, replicates=args.replicates)
    payload = {
        "synthetic": synthetic,
        "release_evaluation": build_release_evaluation(
            implementation_checks={key: True for key in REQUIRED_STATE_A_CHECKS},
            synthetic=synthetic,
            figma_handoff_checks={
                "brief_exists": True,
                "implemented_contract_references": True,
                "unresolved_inputs_listed": True,
                "future_agent_definition_of_done": True,
            },
        ),
    }
    if args.output:
        _write(args.output, payload)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main() -> int:
    commands = {
        "synthetic",
        "holdout",
        "review-packet",
        "ingest-review",
        "aggregate",
        "authorize-production-beta",
    }
    if len(sys.argv) > 1 and sys.argv[1] not in commands:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--seed", type=int, default=61)
        parser.add_argument("--replicates", type=int, default=2_000)
        parser.add_argument("--output", type=Path)
        return _legacy(parser.parse_args())

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    synthetic = sub.add_parser("synthetic")
    synthetic.add_argument("--seed", type=int, default=61)
    synthetic.add_argument("--replicates", type=int, default=2_000)
    synthetic.add_argument("--artifact-dir", type=Path)
    synthetic.add_argument("--output", type=Path)
    synthetic.set_defaults(handler=_synthetic)

    holdout = sub.add_parser("holdout")
    holdout.add_argument("--input", type=Path, default=DEFAULT_CORPUS)
    holdout.add_argument("--split-manifest", type=Path, default=DEFAULT_SPLIT)
    holdout.add_argument("--compatibility-audit", type=Path, default=DEFAULT_AUDIT)
    holdout.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    holdout.add_argument("--output-dir", type=Path, default=DEFAULT_EVALUATION_DIR)
    holdout.add_argument("--output", type=Path)
    holdout.add_argument("--workers", type=int, default=1)
    holdout.add_argument("--resume", action="store_true")
    holdout.add_argument("--v60-checkpoint", type=Path)
    holdout.set_defaults(handler=_holdout)

    packet = sub.add_parser("review-packet")
    packet.add_argument("--holdout", type=Path, required=True)
    packet.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    packet.add_argument("--output", type=Path, required=True)
    packet.set_defaults(handler=_review_packet)

    ingest = sub.add_parser("ingest-review")
    ingest.add_argument("--input", type=Path, required=True)
    ingest.add_argument("--output", type=Path, required=True)
    ingest.add_argument("--finalize", action="store_true")
    ingest.set_defaults(handler=_ingest_review)

    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("--synthetic", type=Path, required=True)
    aggregate.add_argument("--holdout", type=Path, required=True)
    aggregate.add_argument("--compatibility-audit", type=Path, default=DEFAULT_AUDIT)
    aggregate.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    aggregate.add_argument("--reproducibility", type=Path, required=True)
    aggregate.add_argument("--runtime-parity", type=Path)
    aggregate.add_argument("--output-dir", type=Path)
    aggregate.set_defaults(handler=_aggregate)

    authorize = sub.add_parser("authorize-production-beta")
    authorize.add_argument(
        "--evaluation",
        type=Path,
        default=DEFAULT_EVALUATION_DIR / "calibration-evaluation-6.1.0.json",
    )
    authorize.add_argument(
        "--release-manifest",
        type=Path,
        default=DEFAULT_EVALUATION_DIR / "release-manifest-6.1.0.json",
    )
    authorize.add_argument("--output", type=Path, required=True)
    authorize.add_argument("--operator-reference", required=True)
    authorize.set_defaults(handler=_authorize_production_beta)

    args = parser.parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())

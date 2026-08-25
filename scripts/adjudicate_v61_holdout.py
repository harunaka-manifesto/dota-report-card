"""Adjudicate one consumed V6.1 holdout from immutable evidence only."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.player_analysis_v61.holdout_evaluation import _one_finding_per_family  # noqa: E402

ADJUDICATION_TOOL_VERSION = "v61-holdout-adjudication-1.0.0"
CLASSIFICATION = "post_hoc_verifier_adjudication_from_immutable_consumed_holdout"
EXPECTED_HASHES = {
    "aggregate": "9a6162685b07760684a026f10d7e7857fa3d0d3c01d980162dcf51b45f61dd00",
    "checkpoint": "c7e6e4071a10787d9087cab084214bfa07433c38f33f63136a49873abddd0ed4",
    "access": "ef0b2b04373b6f5a17aa258bc115a69849414993f16c33985aeb85165ac08772",
}
EXPECTED_FAMILIES = {
    "pool_shape",
    "transfer",
    "post_loss_response",
    "combat_expression",
    "session_drift",
}
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class AdjudicationError(ValueError):
    """Raised when immutable holdout evidence cannot be adjudicated safely."""


def _sha256(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def _json(file: Path) -> dict[str, Any]:
    value = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AdjudicationError(f"{file} must contain a JSON object")
    return value


def _checkpoint(file: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise AdjudicationError(f"checkpoint line {line_no} is not an object")
        records.append(value)
    return records


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AdjudicationError(message)


def adjudicate(
    *,
    aggregate_path: Path,
    checkpoint_path: Path,
    access_path: Path,
    frozen_manifest_path: Path,
    blocked_marker_path: Path,
    holdout_execution_source_sha: str,
    adjudication_verifier_source_sha: str,
    tests_run: list[str],
) -> dict[str, Any]:
    inputs = {
        "aggregate": aggregate_path,
        "checkpoint": checkpoint_path,
        "access": access_path,
    }
    for name, file in inputs.items():
        _require(file.is_file(), f"missing {name}: {file}")
        actual = _sha256(file)
        _require(actual == EXPECTED_HASHES[name], f"{name} SHA-256 mismatch")
    _require(frozen_manifest_path.is_file(), "missing frozen manifest")
    _require(blocked_marker_path.is_file(), "missing blocked marker")
    _require(
        SHA_PATTERN.fullmatch(holdout_execution_source_sha) is not None,
        "invalid holdout execution source SHA",
    )
    _require(
        SHA_PATTERN.fullmatch(adjudication_verifier_source_sha) is not None,
        "invalid adjudication verifier source SHA",
    )

    aggregate = _json(aggregate_path)
    access = _json(access_path)
    frozen_manifest = _json(frozen_manifest_path)
    blocked = _json(blocked_marker_path)
    records = _checkpoint(checkpoint_path)
    evaluated = [record for record in records if record.get("status") == "evaluated"]

    manifest_sha = _sha256(frozen_manifest_path)
    _require(
        aggregate.get("artifact_manifest_checksum") == manifest_sha,
        "aggregate is not bound to the frozen manifest",
    )
    _require(
        access.get("artifact_manifest_checksum") == manifest_sha,
        "access record is not bound to the frozen manifest",
    )
    _require(
        frozen_manifest.get("source", {}).get("repository_commit")
        == holdout_execution_source_sha,
        "frozen manifest source does not match holdout execution source",
    )
    _require(blocked.get("holdout_output_sha256") == EXPECTED_HASHES["aggregate"], "blocked marker aggregate binding mismatch")
    _require(blocked.get("status") == "BLOCKED_HOLDOUT_GATE", "original holdout is not blocked as expected")
    _require(blocked.get("execution_count") == 1, "original holdout execution count is not one")
    _require(blocked.get("holdout_consumed") is True, "original holdout is not marked consumed")
    _require(blocked.get("failed_gate") == "one_finding_per_family", "unexpected original failed gate")
    _require(blocked.get("opendota_calls") == 0, "original holdout recorded OpenDota calls")

    _require(len(records) == 339, "checkpoint does not contain 339 records")
    digests = [record.get("profile_digest") for record in records]
    _require(len(set(digests)) == 339, "checkpoint profile digests are not unique")
    _require(len(evaluated) == 339, "checkpoint contains evaluation errors")
    _require(
        aggregate.get("profiles") == {"checkpointed": 339, "errors": 0, "evaluated": 339},
        "aggregate profile counts changed",
    )
    _require(access.get("profile_count") == 339 and access.get("completed") is True, "access record binding changed")

    max_family_count = 0
    per_profile_violation_count = 0
    for record in evaluated:
        counts = record.get("family_counts") or {}
        _require(isinstance(counts, Mapping), "checkpoint family_counts is malformed")
        _require(set(counts) <= EXPECTED_FAMILIES, "checkpoint contains an unknown family")
        _require(
            all(
                isinstance(value, int)
                and not isinstance(value, bool)
                and value >= 0
                for value in counts.values()
            ),
            "checkpoint contains a malformed family count",
        )
        _require(sum(counts.values()) == record.get("finding_count"), "checkpoint family count sum mismatch")
        profile_max = max(counts.values(), default=0)
        max_family_count = max(max_family_count, profile_max)
        per_profile_violation_count += int(profile_max > 1)

    original_gates = aggregate.get("gate_measurements")
    _require(isinstance(original_gates, dict), "aggregate gate measurements are missing")
    _require(all(isinstance(value, bool) for value in original_gates.values()), "aggregate gates are not boolean")
    _require(original_gates.get("one_finding_per_family") is False, "original one-family gate was not false")
    _require(aggregate.get("holdout_passed") is False, "original holdout status changed")

    corrected_one_per_family = _one_finding_per_family(evaluated)
    corrected_gates = dict(original_gates)
    corrected_gates["one_finding_per_family"] = corrected_one_per_family
    adjudicated_passed = (
        len(records) == 339
        and len(set(digests)) == 339
        and len(evaluated) == 339
        and all(corrected_gates.values())
    )
    status = "HOLDOUT_ADJUDICATION_PASS" if adjudicated_passed else "HOLDOUT_ADJUDICATION_BLOCKED"

    return {
        "status": status,
        "classification": CLASSIFICATION,
        "reason": (
            "The original verifier applied the per-family limit to cohort-wide family_coverage. "
            "Immutable checkpoint family_counts show two distinct profiles with transfer=1 and "
            "no per-profile family duplicate."
        ),
        "original_holdout_status": blocked["status"],
        "original_holdout_execution_count": blocked["execution_count"],
        "holdout_execution_source_sha": holdout_execution_source_sha,
        "adjudication_verifier_source_sha": adjudication_verifier_source_sha,
        "original_aggregate_sha256": EXPECTED_HASHES["aggregate"],
        "checkpoint_sha256": EXPECTED_HASHES["checkpoint"],
        "access_record_sha256": EXPECTED_HASHES["access"],
        "profile_count": len(records),
        "unique_profile_count": len(set(digests)),
        "error_count": len(records) - len(evaluated),
        "original_one_finding_per_family": original_gates["one_finding_per_family"],
        "corrected_one_finding_per_family": corrected_one_per_family,
        "per_profile_violation_count": per_profile_violation_count,
        "max_family_count_per_profile": max_family_count,
        "cohort_family_totals": aggregate["family_coverage"],
        "original_holdout_passed": aggregate["holdout_passed"],
        "adjudicated_holdout_passed": adjudicated_passed,
        "open_dota_calls": blocked["opendota_calls"],
        "runtime_or_model_changed": False,
        "calibration_changed": False,
        "thresholds_changed": False,
        "holdout_analysis_rerun": False,
        "adjudication_timestamp": datetime.now(UTC).isoformat(),
        "adjudication_tool_version": ADJUDICATION_TOOL_VERSION,
        "tests_run": tests_run,
        "gate_measurements_original": dict(original_gates),
        "gate_measurements_adjudicated": corrected_gates,
        "other_holdout_gates": {
            key: value for key, value in corrected_gates.items() if key != "one_finding_per_family"
        },
        "source_provenance": {
            "aggregate": {"filename": aggregate_path.name, "sha256": EXPECTED_HASHES["aggregate"]},
            "checkpoint": {"filename": checkpoint_path.name, "sha256": EXPECTED_HASHES["checkpoint"]},
            "access_record": {"filename": access_path.name, "sha256": EXPECTED_HASHES["access"]},
            "frozen_manifest": {"filename": frozen_manifest_path.name, "sha256": manifest_sha},
            "blocked_marker": {"filename": blocked_marker_path.name, "sha256": _sha256(blocked_marker_path)},
            "copied_metrics": "All metrics except corrected one_finding_per_family and directly derived status are copied from the immutable aggregate or marker.",
        },
        "notes": [
            "Original consumed holdout evidence was not modified.",
            "No player analysis, OpenDota request, bootstrap, retraining, recalibration, or runtime change was performed.",
            "This is not a new sealed holdout and must not be labeled as a sealed holdout PASS.",
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--access", type=Path, required=True)
    parser.add_argument("--frozen-manifest", type=Path, required=True)
    parser.add_argument("--blocked-marker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--holdout-execution-source-sha", required=True)
    parser.add_argument("--adjudication-verifier-source-sha", required=True)
    parser.add_argument("--tests-run", action="append", default=[])
    return parser


def main() -> int:
    args = _parser().parse_args()
    input_files = {
        args.aggregate.resolve(),
        args.checkpoint.resolve(),
        args.access.resolve(),
        args.frozen_manifest.resolve(),
        args.blocked_marker.resolve(),
    }
    if args.output.resolve() in input_files:
        raise SystemExit("output must be a new artifact, not an immutable input")
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing artifact: {args.output}")
    try:
        artifact = adjudicate(
            aggregate_path=args.aggregate,
            checkpoint_path=args.checkpoint,
            access_path=args.access,
            frozen_manifest_path=args.frozen_manifest,
            blocked_marker_path=args.blocked_marker,
            holdout_execution_source_sha=args.holdout_execution_source_sha,
            adjudication_verifier_source_sha=args.adjudication_verifier_source_sha,
            tests_run=args.tests_run,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (AdjudicationError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"adjudication stopped: {exc}") from exc
    print(json.dumps({key: artifact[key] for key in ("status", "classification", "adjudicated_holdout_passed")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

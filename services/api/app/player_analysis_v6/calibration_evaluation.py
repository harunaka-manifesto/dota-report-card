"""Aggregate calibration evidence, release manifests, and safe promotion.

Only aggregate values cross this module.  Private profile-level checkpoints
remain under ``.local/calibration`` and are never accepted as release inputs.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .artifacts import load_context_baseline_artifact
from .calibration import load_threshold_artifact
from .constants import REPORT_VERSION, STATS_BOOTSTRAP_METHOD

EVALUATION_VERSION = "calibration-evaluation-6.0.0"
RELEASE_MANIFEST_VERSION = "free-dna-v6-release-manifest-6.0.0"
SYNTHETIC_VERSION = "v6-synthetic-evaluation-1.0.0"
HOLDOUT_VERSION = "v6-holdout-evaluation-1.0.0"
REVIEW_VERSION = "v6-review-evidence-1.0.0"
REVIEW_PACKET_VERSION = "v6-private-review-packet-1.0.0"
PRODUCTION_FILES = (
    "context-baseline-2.0.0.json",
    "metric-thresholds-6.0.0.json",
    "calibration-evaluation-6.0.0.json",
    "release-manifest-6.0.0.json",
)


class CalibrationEvaluationError(ValueError):
    """Raised when release evidence is incomplete, unsafe, or inconsistent."""


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _finite_walk(value: Any, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            folded = str(key).casefold()
            if folded in {"profile_id", "profile_ids", "match_id", "match_ids", "account_id", "account_ids"}:
                raise CalibrationEvaluationError(f"identifier field is forbidden at {path}.{key}")
            if "mmr" in folded or folded.startswith("rank") or folded in {"skill_bracket", "medal"}:
                if folded == "mmr_used" and item is False:
                    continue
                raise CalibrationEvaluationError(f"rank/MMR field is forbidden at {path}.{key}")
            _finite_walk(item, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _finite_walk(item, f"{path}[{index}]")
    elif isinstance(value, float) and not math.isfinite(value):
        raise CalibrationEvaluationError(f"non-finite value at {path}")
    elif isinstance(value, str):
        if re.search(r"(?:/Users/|/home/|[A-Za-z]:\\Users\\)", value):
            raise CalibrationEvaluationError(f"private filesystem path at {path}")


def validate_aggregate_payload(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise CalibrationEvaluationError("aggregate artifact must be an object")
    _finite_walk(payload)


def gate(
    *,
    required: Any,
    observed: Any,
    denominator: int | None,
    passed: bool,
    source: str,
) -> dict[str, Any]:
    return {
        "required": required,
        "observed": observed,
        "denominator": denominator,
        "passed": bool(passed),
        "evidence_source": source,
    }


def _required_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise CalibrationEvaluationError(f"{key} evidence must be an object")
    return value


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def build_evaluation_artifact(
    synthetic: Mapping[str, Any],
    holdout: Mapping[str, Any],
    review: Mapping[str, Any] | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Combine measured evidence and derive every release gate fail-closed."""

    if synthetic.get("version") != SYNTHETIC_VERSION:
        raise CalibrationEvaluationError("unsupported synthetic evidence version")
    if holdout.get("version") != HOLDOUT_VERSION:
        raise CalibrationEvaluationError("unsupported holdout evidence version")
    if synthetic.get("smoke") is True or holdout.get("smoke") is True:
        raise CalibrationEvaluationError("smoke evidence cannot satisfy release gates")
    validate_aggregate_payload(synthetic)
    validate_aggregate_payload(holdout)
    if review is not None:
        if review.get("version") != REVIEW_VERSION:
            raise CalibrationEvaluationError("unsupported review evidence version")
        validate_aggregate_payload(review)

    synthetic_coverage = _required_mapping(synthetic, "interval_empirical_coverage")
    synthetic_fdr = _required_mapping(synthetic, "family_fdr")
    nonblank = _required_mapping(holdout, "nonblank_identity")
    agreement = _required_mapping(holdout, "split_half_agreement")
    copy_safety = _required_mapping(holdout, "copy_safety")
    free_cost = _required_mapping(holdout, "free_cost")
    corpus = _required_mapping(holdout, "corpus")
    profile_count = int(corpus.get("profile_count", 0))
    interval_value = synthetic_coverage.get("observed")
    fdr_value = synthetic_fdr.get("observed")
    nonblank_value = nonblank.get("observed")
    agreement_value = agreement.get("observed")
    copy_violations = copy_safety.get("violations")
    cost_violations = free_cost.get("violations")
    mmr_used = bool(corpus.get("mmr_used", True))

    review_payload = dict(review or {})
    reviewer = _mapping_or_empty(review_payload.get("dota_reviewer"))
    statistical = _mapping_or_empty(review_payload.get("statistical_review"))
    data_basis = _mapping_or_empty(review_payload.get("data_basis"))
    reviewer_precision = reviewer.get("precision")
    reviewer_total = reviewer.get("reviewed_count")

    gates = {
        "minimum_profiles": gate(required=">=1000", observed=profile_count, denominator=profile_count, passed=profile_count >= 1000, source="holdout.corpus"),
        "interval_empirical_coverage": gate(required="0.93..0.97", observed=interval_value, denominator=synthetic_coverage.get("total"), passed=isinstance(interval_value, (int, float)) and 0.93 <= float(interval_value) <= 0.97, source="synthetic.interval_empirical_coverage"),
        "family_fdr": gate(required="<=0.05", observed=fdr_value, denominator=synthetic_fdr.get("null_replicates"), passed=isinstance(fdr_value, (int, float)) and float(fdr_value) <= 0.05, source="synthetic.family_fdr"),
        "nonblank_identity": gate(required=">=0.80", observed=nonblank_value, denominator=nonblank.get("eligible_profiles"), passed=isinstance(nonblank_value, (int, float)) and float(nonblank_value) >= 0.80, source="holdout.nonblank_identity"),
        "split_half_agreement": gate(required=">=0.80", observed=agreement_value, denominator=agreement.get("comparable_zones"), passed=isinstance(agreement_value, (int, float)) and float(agreement_value) >= 0.80, source="holdout.split_half_agreement"),
        "forbidden_copy_violations": gate(required=0, observed=copy_violations, denominator=copy_safety.get("strings_scanned"), passed=copy_violations == 0, source="holdout.copy_safety"),
        "free_cost_violations": gate(required=0, observed=cost_violations, denominator=free_cost.get("reports_checked"), passed=cost_violations == 0, source="holdout.free_cost"),
        "forbidden_dimension_absence": gate(required=False, observed=mmr_used, denominator=profile_count, passed=mmr_used is False, source="holdout.corpus"),
        "dota_reviewer_precision": gate(required=">=0.90", observed=reviewer_precision, denominator=reviewer_total if isinstance(reviewer_total, int) else None, passed=isinstance(reviewer_precision, (int, float)) and float(reviewer_precision) >= 0.90 and bool(reviewer.get("approved")), source="external_review.dota_reviewer"),
        "statistical_review": gate(required=True, observed=statistical.get("approved"), denominator=None, passed=statistical.get("approved") is True, source="external_review.statistical_review"),
        "data_basis_approval": gate(required=True, observed=data_basis.get("approved"), denominator=None, passed=data_basis.get("approved") is True, source="external_review.data_basis"),
    }
    automated_keys = tuple(key for key in gates if key not in {"dota_reviewer_precision", "statistical_review", "data_basis_approval"})
    automated_passed = all(gates[key]["passed"] for key in automated_keys)
    release_ready = all(item["passed"] for item in gates.values())
    status = "release-ready" if release_ready else "external-review-required" if automated_passed else "automated-gates-failed"
    artifact_checksums = dict(synthetic.get("artifact_checksums") or {})
    if artifact_checksums != dict(holdout.get("artifact_checksums") or {}):
        raise CalibrationEvaluationError("synthetic and holdout artifact checksums do not match")
    result = {
        "version": EVALUATION_VERSION,
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "release_ready": release_ready,
        "status": status,
        "artifact_checksums": artifact_checksums,
        "corpus": dict(corpus),
        "synthetic": {
            "interval_empirical_coverage": dict(synthetic_coverage),
            "family_fdr": dict(synthetic_fdr),
            "scenario_counts": dict(synthetic.get("scenario_counts") or {}),
            "seed": synthetic.get("seed"),
            "bootstrap_iterations": synthetic.get("bootstrap_iterations"),
        },
        "holdout": {
            "nonblank_identity": dict(nonblank),
            "split_half_agreement": dict(agreement),
            "abstention": dict(holdout.get("abstention") or {}),
            "per_metric_coverage": dict(holdout.get("per_metric_coverage") or {}),
            "baseline_fallback": dict(holdout.get("baseline_fallback") or {}),
            "free_cost": dict(free_cost),
        },
        "copy_safety": dict(copy_safety),
        "external_review": review_payload,
        "gates": gates,
    }
    validate_evaluation_artifact(result)
    return result


def validate_evaluation_artifact(payload: Mapping[str, Any]) -> None:
    validate_aggregate_payload(payload)
    if payload.get("version") != EVALUATION_VERSION:
        raise CalibrationEvaluationError("unsupported evaluation artifact version")
    gates = payload.get("gates")
    if not isinstance(gates, Mapping) or not gates:
        raise CalibrationEvaluationError("evaluation gates are missing")
    for name, raw in gates.items():
        if not isinstance(raw, Mapping) or set(raw) != {"required", "observed", "denominator", "passed", "evidence_source"}:
            raise CalibrationEvaluationError(f"gate {name} has an invalid schema")
        if raw.get("passed") is not True and raw.get("passed") is not False:
            raise CalibrationEvaluationError(f"gate {name}.passed must be boolean")
    derived_ready = all(bool(raw["passed"]) for raw in gates.values())
    if payload.get("release_ready") is not derived_ready:
        raise CalibrationEvaluationError("release_ready is inconsistent with required gates")
    expected_status = "release-ready" if derived_ready else (
        "external-review-required"
        if all(bool(raw["passed"]) for key, raw in gates.items() if key not in {"dota_reviewer_precision", "statistical_review", "data_basis_approval"})
        else "automated-gates-failed"
    )
    if payload.get("status") != expected_status:
        raise CalibrationEvaluationError("evaluation status is inconsistent with gates")


def ingest_review_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate human results and compute precision without self-approval."""

    version = payload.get("version")
    if version not in {REVIEW_VERSION, REVIEW_PACKET_VERSION}:
        raise CalibrationEvaluationError("unsupported review evidence version")
    judgments = payload.get("items") if version == REVIEW_PACKET_VERSION else payload.get("judgments")
    if not isinstance(judgments, list) or not judgments:
        raise CalibrationEvaluationError("review evidence needs non-empty judgments")
    supported = 0
    for item in judgments:
        if not isinstance(item, Mapping) or not isinstance(item.get("supported"), bool) or not isinstance(item.get("believable"), bool):
            raise CalibrationEvaluationError("each judgment needs boolean supported and believable values")
        supported += bool(item["supported"] and item["believable"])
    result = {
        "version": REVIEW_VERSION,
        "generated_at": str(payload.get("generated_at") or datetime.now(UTC).isoformat()),
        "dota_reviewer": {
            "reviewed_count": len(judgments),
            "supported_and_believable_count": supported,
            "precision": supported / len(judgments),
            "approved": supported / len(judgments) >= 0.90 and bool(payload.get("dota_reviewer_approved")),
            "reviewer_reference": payload.get("dota_reviewer_reference"),
        },
        "statistical_review": {
            "approved": payload.get("statistical_review_approved") is True,
            "reviewer_reference": payload.get("statistical_reviewer_reference"),
        },
        "data_basis": {
            "approved": payload.get("data_basis_approved") is True,
            "approver_reference": payload.get("data_basis_approver_reference"),
        },
    }
    validate_aggregate_payload(result)
    return result


def build_release_manifest(
    release_dir: str | Path,
    evaluation: Mapping[str, Any],
    *,
    source_revision: str,
    dirty_worktree: bool,
    generated_at: str | None = None,
) -> dict[str, Any]:
    directory = Path(release_dir)
    baseline = directory / PRODUCTION_FILES[0]
    thresholds = directory / PRODUCTION_FILES[1]
    load_context_baseline_artifact(baseline)
    load_threshold_artifact(thresholds)
    validate_evaluation_artifact(evaluation)
    artifacts = {
        baseline.name: {"sha256": sha256_file(baseline), "bytes": baseline.stat().st_size},
        thresholds.name: {"sha256": sha256_file(thresholds), "bytes": thresholds.stat().st_size},
        PRODUCTION_FILES[2]: {
            "sha256": hashlib.sha256((json.dumps(evaluation, indent=2, sort_keys=True) + "\n").encode("utf-8")).hexdigest(),
            "bytes": len((json.dumps(evaluation, indent=2, sort_keys=True) + "\n").encode("utf-8")),
        },
    }
    expected = evaluation.get("artifact_checksums")
    if not isinstance(expected, Mapping) or expected.get("baseline_sha256") != artifacts[baseline.name]["sha256"] or expected.get("threshold_sha256") != artifacts[thresholds.name]["sha256"]:
        raise CalibrationEvaluationError("evaluation checksums do not match release artifacts")
    result = {
        "version": RELEASE_MANIFEST_VERSION,
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "release_ready": evaluation.get("release_ready") is True,
        "approval_state": "approved" if evaluation.get("release_ready") is True else "candidate",
        "source": {"repository_commit": source_revision, "dirty_worktree": bool(dirty_worktree)},
        "corpus": dict(evaluation.get("corpus") or {}),
        "versions": {
            "baseline": "context-baseline-2.0.0",
            "thresholds": "metric-thresholds-6.0.0",
            "evaluation": EVALUATION_VERSION,
            "report": REPORT_VERSION,
            "statistics": STATS_BOOTSTRAP_METHOD,
        },
        "artifacts": artifacts,
        "automated_gates": {key: bool(value["passed"]) for key, value in evaluation["gates"].items()},
        "external_review_checksum": hashlib.sha256(json.dumps(evaluation.get("external_review") or {}, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "mmr_used": False,
        "commands": [
            "build_v6_calibration_artifacts.py validate|baseline|thresholds",
            "evaluate_v6_calibration.py synthetic|holdout|aggregate",
            "promote_v6_calibration_release.py",
        ],
    }
    validate_release_manifest(result)
    return result


def validate_release_manifest(payload: Mapping[str, Any]) -> None:
    validate_aggregate_payload(payload)
    if payload.get("version") != RELEASE_MANIFEST_VERSION:
        raise CalibrationEvaluationError("unsupported release manifest version")
    if payload.get("mmr_used") is not False:
        raise CalibrationEvaluationError("release manifest must declare mmr_used=false")
    gates = payload.get("automated_gates")
    if not isinstance(gates, Mapping) or not gates:
        raise CalibrationEvaluationError("release manifest gate summary is missing")
    ready = all(value is True for value in gates.values())
    if payload.get("release_ready") is not ready:
        raise CalibrationEvaluationError("release manifest readiness is inconsistent")


def atomic_json(path: str | Path, payload: Mapping[str, Any], *, mode: int = 0o600) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700 if mode == 0o600 else 0o755)
    if mode == 0o600:
        output.parent.chmod(0o700)
    temporary = output.with_name(f".{output.name}.tmp")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, mode)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    temporary.replace(output)


def promote_release(release_dir: str | Path, destination: str | Path) -> tuple[Path, ...]:
    """Copy only an approved, checksum-linked aggregate release."""

    source = Path(release_dir)
    evaluation = json.loads((source / PRODUCTION_FILES[2]).read_text(encoding="utf-8"))
    manifest = json.loads((source / PRODUCTION_FILES[3]).read_text(encoding="utf-8"))
    validate_evaluation_artifact(evaluation)
    validate_release_manifest(manifest)
    if evaluation.get("release_ready") is not True or manifest.get("release_ready") is not True:
        raise CalibrationEvaluationError("promotion requires every automated and human gate to pass")
    for name in PRODUCTION_FILES[:3]:
        expected = manifest["artifacts"].get(name)
        if not isinstance(expected, Mapping) or expected.get("sha256") != sha256_file(source / name):
            raise CalibrationEvaluationError(f"release checksum mismatch for {name}")
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for name in PRODUCTION_FILES:
        payload = json.loads((source / name).read_text(encoding="utf-8"))
        validate_aggregate_payload(payload)
        temporary = target / f".{name}.tmp"
        shutil.copyfile(source / name, temporary)
        temporary.replace(target / name)
        copied.append(target / name)
    return tuple(copied)


__all__ = [
    "CalibrationEvaluationError",
    "EVALUATION_VERSION",
    "HOLDOUT_VERSION",
    "RELEASE_MANIFEST_VERSION",
    "REVIEW_PACKET_VERSION",
    "REVIEW_VERSION",
    "SYNTHETIC_VERSION",
    "atomic_json",
    "build_evaluation_artifact",
    "build_release_manifest",
    "ingest_review_evidence",
    "promote_release",
    "sha256_file",
    "validate_aggregate_payload",
    "validate_evaluation_artifact",
    "validate_release_manifest",
]

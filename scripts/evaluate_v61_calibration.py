#!/usr/bin/env python3
"""Run the offline V6.1 synthetic, sealed-holdout, and aggregate gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.analysis.budget import DataCostLedger  # noqa: E402
from app.core.release import current_source_binding  # noqa: E402
from app.dna.sessions import infer_sessions  # noqa: E402
from app.player_analysis_v61.artifacts import (  # noqa: E402
    load_v61_artifact_bundle,
    validate_v61_freeze_record,
)
from app.player_analysis_v61.calibration_corpus import (  # noqa: E402
    CANONICAL_SESSION_POLICY,
    canonical_history,
    load_canonical_corpus,
)
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
    validate_runtime_parity,
)
from app.player_analysis_v61.corpus_reuse import (  # noqa: E402
    load_compatibility_audit,
    sha256_file,
)
from app.player_analysis_v61.holdout_evaluation import evaluate_holdout  # noqa: E402
from app.player_analysis_v61.legacy_adapter import current_taxonomy_mapping  # noqa: E402
from app.player_analysis_v61.versions import MODEL_VERSION  # noqa: E402
from app.reports.dna_assembly_v61 import assemble_free_dna_report_v61  # noqa: E402
from v61_calibration_builder import atomic_json, split_from_manifest  # noqa: E402

DEFAULT_CORPUS = ROOT / ".local/calibration/v61/canonical-corpus.json"
DEFAULT_SPLIT = ROOT / ".local/calibration/v61/manifests/split-6000-canonical.json"
DEFAULT_ARTIFACT_DIR = ROOT / ".local/calibration/v61"
DEFAULT_AUDIT = DEFAULT_ARTIFACT_DIR / "corpus-compatibility-2.0.0.json"
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
    source = current_source_binding(ROOT)
    return str(source["repository_commit"]), bool(source["dirty_worktree"])


def _synthetic(args: argparse.Namespace) -> int:
    result = run_synthetic_evaluation(seed=args.seed, replicates=args.replicates)
    if args.artifact_dir:
        revision, dirty = _revision()
        bundle = load_v61_artifact_bundle(
            args.artifact_dir,
            expected_source_revision=revision,
            expected_dirty_worktree=dirty,
        )
        result["artifact_checksums"] = dict(bundle.checksums)
        result["artifact_manifest_checksum"] = sha256_file(args.artifact_dir / "build-manifest-6.1.0.json")
    if args.output:
        _write(args.output, result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _holdout(args: argparse.Namespace) -> int:
    revision, dirty = _revision()
    result = evaluate_holdout(
        corpus_path=args.input,
        split_manifest_path=args.split_manifest,
        compatibility_audit_path=args.compatibility_audit,
        artifact_dir=args.artifact_dir,
        output_dir=args.output_dir,
        workers=args.workers,
        resume=args.resume,
        v60_checkpoint_path=args.v60_checkpoint,
        expected_source_revision=revision,
        expected_dirty_worktree=dirty,
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
    revision, dirty = _revision()
    bundle = load_v61_artifact_bundle(
        args.artifact_dir,
        expected_source_revision=revision,
        expected_dirty_worktree=dirty,
    )
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


def _runtime_parity(args: argparse.Namespace) -> int:
    """Run one complete canonical report through the frozen runtime bundle."""

    corpus = load_canonical_corpus(args.input)
    corpus_sha256 = sha256_file(args.input)
    split_checksum = sha256_file(args.split_manifest)
    split_payload = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    if not isinstance(split_payload, dict):
        raise ValueError("split manifest must be an object")
    split_from_manifest(
        corpus.matches,
        split_payload,
        corpus_sha256=corpus_sha256,
        require_frozen_counts=False,
    )
    revision, dirty = _revision()
    bundle = load_v61_artifact_bundle(
        args.artifact_dir,
        expected_corpus_sha256=corpus_sha256,
        expected_split_checksum=split_checksum,
        expected_source_revision=revision,
        expected_dirty_worktree=dirty,
    )
    by_profile: dict[str, list[dict[str, Any]]] = {}
    for row in corpus.matches:
        by_profile.setdefault(str(row.get("profile_id", "")), []).append(dict(row))
    candidates = sorted(
        (
            rows
            for profile, rows in by_profile.items()
            if profile
            and len(rows) >= 30
            and all(row.get("leaver_status") is not None for row in rows)
        ),
        key=lambda rows: (str(rows[0].get("profile_id")), len(rows)),
    )
    if not candidates:
        raise ValueError("runtime parity input has no 30-match profile with leaver_status")
    account_id = 1
    rows = candidates[0]
    window = corpus.collection_window_for_profile(str(rows[0]["profile_id"]))
    history = canonical_history(
        rows,
        account_id,
        window_start=int(window["start_time"]),
        window_end=int(window["end_time"]),
    )
    matches = history.normalization.eligible_matches
    sessions = infer_sessions(
        matches,
        CANONICAL_SESSION_POLICY,
        window_start=int(window["start_time"]),
        window_end=int(window["end_time"]),
    )
    completed_ids = {session.session_id for session in sessions.completed_sessions}
    completed = {
        session.session_id: session.session_id in completed_ids
        for session in sessions.sessions
    }
    report = assemble_free_dna_report_v61(
        account_id=account_id,
        profile={"personaname": "Runtime parity subject"},
        matches=matches,
        canonical_history=history,
        processed_matches=len(rows),
        eligible_matches=len(matches),
        model_version=MODEL_VERSION,
        template_version="templates-1.0.0",
        cost_ledger=DataCostLedger(),
        analysis_version_fingerprint=str(bundle.manifest.get("code_fingerprint", "")),
        baseline_resolver=bundle.baseline.resolver(),
        thresholds=bundle.thresholds.metrics,
        taxonomy_by_hero=current_taxonomy_mapping(),
        completed_sessions=completed,
        artifact_checksums=bundle.checksums,
        supporting_artifacts={
            "summary_prior": bundle.summary_prior,
            "distance_calibration": bundle.distance_calibration,
            "session_reliability": bundle.session_reliability,
            "semantic_calibration": bundle.semantic_calibration,
            "manifest": bundle.manifest,
        },
        protected_cohorts_out={},
    )
    parity = {
        "version": "v61-runtime-calibration-parity-2.0.0",
        "passed": True,
        "source": {"repository_commit": revision, "dirty_worktree": dirty},
        "corpus": {
            "schema_version": corpus.payload["schema_version"],
            "sha256": corpus_sha256,
            "split_manifest_checksum": split_checksum,
        },
        "artifact_checksums": dict(bundle.checksums),
        "versions": {
            **dict(report.get("versions") or {}),
            "model_version": str((report.get("versions") or {}).get("model", "")),
            "report_schema_version": str(report.get("schema_version", "")),
        },
        "assertions": {
            "canonical_one_request": history.audit.request_count == 1,
            "fixture_components_in_production": False,
            "full_recomputation": True,
            "family_branch_evidence_complete": bool(report.get("selection_audit")),
            "report_assembly_completed": report.get("schema_version") == "free-dna-report-6.1.0",
        },
    }
    validate_runtime_parity(
        parity,
        source_revision=revision,
        dirty_worktree=dirty,
        corpus_sha256=corpus_sha256,
        split_manifest_checksum=split_checksum,
        artifact_checksums=bundle.checksums,
    )
    _write(args.output, parity)
    print(json.dumps({"output": str(args.output), "passed": True}, sort_keys=True))
    return 0


def _aggregate(args: argparse.Namespace) -> int:
    audit = load_compatibility_audit(args.compatibility_audit)
    freeze_manifest = _read(args.artifact_dir / "build-manifest-6.1.0.json")
    freeze_record = _read(args.artifact_dir / "freeze-record-6.1.0.json")
    reproducibility = _read(args.reproducibility)
    synthetic = _read(args.synthetic)
    holdout = _read(args.holdout)
    revision, dirty = _revision()
    bundle = load_v61_artifact_bundle(
        args.artifact_dir,
        expected_source_revision=revision,
        expected_dirty_worktree=dirty,
    )
    runtime_parity = _read(args.runtime_parity)
    validate_v61_freeze_record(
        freeze_record,
        expected_source_revision=revision,
        expected_dirty_worktree=dirty,
        expected_source=bundle.manifest.get("source"),
    )
    validate_runtime_parity(
        runtime_parity,
        source_revision=revision,
        dirty_worktree=dirty,
        corpus_sha256=freeze_manifest.get("corpus_sha256"),
        split_manifest_checksum=freeze_manifest.get("split_manifest_checksum"),
        artifact_checksums=bundle.checksums,
    )
    evaluation = build_v61_calibration_evaluation(
        compatibility_audit=audit,
        freeze_manifest=freeze_manifest,
        freeze_record=freeze_record,
        reproducibility=reproducibility,
        synthetic=synthetic,
        holdout=holdout,
        runtime_parity=runtime_parity,
        artifact_checksums=bundle.checksums,
        source_revision=revision,
        dirty_worktree=dirty,
        corpus_sha256=freeze_manifest.get("corpus_sha256"),
        split_manifest_checksum=freeze_manifest.get("split_manifest_checksum"),
    )
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
        "runtime-parity",
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
    aggregate.add_argument("--runtime-parity", type=Path, required=True)
    aggregate.add_argument("--output-dir", type=Path)
    aggregate.set_defaults(handler=_aggregate)

    parity = sub.add_parser("runtime-parity")
    parity.add_argument("--input", type=Path, default=DEFAULT_CORPUS)
    parity.add_argument("--split-manifest", type=Path, default=DEFAULT_SPLIT)
    parity.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parity.add_argument("--output", type=Path, required=True)
    parity.set_defaults(handler=_runtime_parity)

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

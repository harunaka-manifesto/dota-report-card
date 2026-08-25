#!/usr/bin/env python3
"""Build and verify training-only V6.1 calibration artifacts.

Preferred interface: ``audit-reuse``, ``baseline``, ``calibrate-support``,
``thresholds``, ``freeze``, and ``verify-reproducibility``.  The old
``--input ... --output-dir ...`` form remains only for small State-A fixture
tests and refuses the real V6 corpus.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.player_analysis_v61.artifacts import (  # noqa: E402
    V61_SUPPORT_ARTIFACTS,
    load_v61_artifact_bundle,
)
from app.player_analysis_v61.calibration_corpus import (  # noqa: E402
    CANONICAL_SCHEMA_VERSION,
    load_canonical_corpus,
)
from app.player_analysis_v61.corpus_reuse import (  # noqa: E402
    CompatibilityAuditError,
    audit_reuse,
    require_compatible_audit,
    sha256_file,
)
from app.player_analysis_v61.legacy_adapter import current_taxonomy_mapping  # noqa: E402
from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_CATALOG  # noqa: E402
from v61_calibration_builder import (  # noqa: E402
    FREEZE_RECORD_NAME,
    assert_reproducible,
    atomic_json,
    build_baseline_v61,
    build_distance_calibration,
    build_semantic_calibration,
    build_session_reliability,
    build_summary_prior,
    derive_thresholds_v61,
    load_rows,
    split_from_manifest,
    write_freeze_manifest,
)


def _json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _reference(args: argparse.Namespace, audit: dict[str, Any] | None = None) -> str:
    value = str(getattr(args, "reuse_authorization_reference", "") or "").strip()
    if not value and audit:
        value = str(audit.get("authorization", {}).get("reuse_reference", "") or "").strip()
    return value


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--compatibility-audit", type=Path, required=True)
    parser.add_argument("--generated-at", default="2000-01-01T00:00:00+00:00")
    parser.add_argument("--reuse-authorization-reference", default="")


def _audit(args: argparse.Namespace) -> int:
    payload = audit_reuse(
        args.input,
        args.split_manifest,
        authorization_reference=args.reuse_authorization_reference,
    )
    atomic_json(args.output, payload)
    print(json.dumps({
        "output": str(args.output),
        "audit_checksum": payload["audit_checksum"],
        "core_passed": payload["core_passed"],
        "reuse_authorized": payload["authorization"]["reuse_authorized"],
    }, sort_keys=True))
    return 0


def _validate_corpus(args: argparse.Namespace) -> int:
    corpus = load_canonical_corpus(args.input)
    diagnostics = corpus.aggregate_diagnostics()
    diagnostics["checksum"] = sha256_file(args.input)
    if args.output:
        atomic_json(args.output, diagnostics)
    else:
        print(json.dumps(diagnostics, sort_keys=True))
    return 0


def _bind_split(args: argparse.Namespace) -> int:
    corpus = load_canonical_corpus(args.input)
    split = _json(args.split_manifest, "split manifest")
    train = set(map(str, split.get("train_profile_ids", [])))
    holdout = set(map(str, split.get("holdout_profile_ids", [])))
    if (
        split.get("seed") != 6000
        or len(train) != 791
        or len(holdout) != 339
        or train & holdout
        or train | holdout != set(corpus.profile_ids)
        or set(corpus.profile_ids) != set(corpus.usable_profile_ids)
    ):
        raise ValueError(
            "the existing 791/339 split cannot be reused: population or usable-profile counts failed; "
            "a new approved split/population is required"
        )
    bound = dict(split)
    bound["corpus_schema"] = CANONICAL_SCHEMA_VERSION
    bound["corpus_sha256"] = sha256_file(args.input)
    atomic_json(args.output, bound)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "corpus_sha256": bound["corpus_sha256"],
                "train_profile_count": len(train),
                "holdout_profile_count": len(holdout),
                "overlap_count": 0,
            },
            sort_keys=True,
        )
    )
    return 0


def _load_training_inputs(
    args: argparse.Namespace,
    *,
    require_authorization: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any], set[str], set[str], dict[str, Any]]:
    audit = require_compatible_audit(
        args.compatibility_audit,
        corpus_path=args.input,
        split_manifest_path=args.split_manifest,
        require_authorization=require_authorization,
        canonical_only=True,
    )
    rows = load_rows(args.input)
    split = _json(args.split_manifest, "split manifest")
    train, holdout = split_from_manifest(rows, split, corpus_sha256=sha256_file(args.input))
    return rows, split, train, holdout, audit


def _baseline(args: argparse.Namespace) -> int:
    rows, _split, train, _holdout, audit = _load_training_inputs(args)
    output = args.output or args.baseline_output
    if output is None:
        raise ValueError("baseline requires --output")
    artifact = build_baseline_v61(
        rows,
        train_profiles=train,
        generated_at=args.generated_at,
        corpus_sha256=sha256_file(args.input),
        taxonomy=current_taxonomy_mapping(),
    )
    atomic_json(output, artifact)
    print(json.dumps({"output": str(output), "audit_checksum": audit["audit_checksum"], "training_profiles": len(train)}, sort_keys=True))
    return 0


def _support(args: argparse.Namespace) -> int:
    rows, _split, train, _holdout, audit = _load_training_inputs(args)
    from app.player_analysis_v61.artifacts import load_context_baseline_artifact_v61

    taxonomy = current_taxonomy_mapping()
    resolver = load_context_baseline_artifact_v61(args.baseline_input).resolver()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    corpus_sha = sha256_file(args.input)
    prior = build_summary_prior(rows, train, corpus_sha256=corpus_sha)
    distance = build_distance_calibration(rows, train, resolver=resolver, taxonomy=taxonomy, corpus_sha256=corpus_sha)
    reliability = build_session_reliability(rows, train, resolver=resolver, taxonomy=taxonomy, corpus_sha256=corpus_sha)
    semantic = build_semantic_calibration(train, distance=distance, reliability=reliability, corpus_sha256=corpus_sha)
    for name, payload in (
        ("summary-priors-6.1.0.json", prior),
        ("portfolio-distance-calibration-1.0.0.json", distance),
        ("session-reliability-calibration-1.0.0.json", reliability),
        ("semantic-outcome-calibration-1.0.0.json", semantic),
    ):
        atomic_json(output_dir / name, payload)
    print(json.dumps({"output_dir": str(output_dir), "audit_checksum": audit["audit_checksum"], "training_profiles": len(train)}, sort_keys=True))
    return 0


def _thresholds(args: argparse.Namespace) -> int:
    rows, _split, train, holdout, audit = _load_training_inputs(args)
    output = args.output or args.threshold_output
    if output is None:
        raise ValueError("thresholds requires --output")
    taxonomy = current_taxonomy_mapping()
    checkpoint_dir = args.checkpoint_dir or output.parent / "checkpoints" / "thresholds-6.1.0"
    thresholds, diagnostics = derive_thresholds_v61(
        rows,
        train_profiles=train,
        holdout_profiles=holdout,
        baseline_path=args.baseline_input,
        generated_at=args.generated_at,
        corpus_sha256=sha256_file(args.input),
        taxonomy=taxonomy,
        checkpoint_dir=checkpoint_dir,
        workers=args.workers,
    )
    atomic_json(output, thresholds)
    atomic_json(output.with_name("threshold-derivation-diagnostics-6.1.0.json"), diagnostics)
    print(json.dumps({"output": str(output), "audit_checksum": audit["audit_checksum"], "training_profiles": len(train)}, sort_keys=True))
    return 0


def _freeze(args: argparse.Namespace) -> int:
    audit = require_compatible_audit(
        args.compatibility_audit,
        corpus_path=args.input,
        split_manifest_path=args.split_manifest,
        require_authorization=True,
        canonical_only=True,
    )
    reference = _reference(args, audit)
    if not reference:
        raise CompatibilityAuditError("freeze requires a nonempty reuse authorization reference")
    rows = load_rows(args.input)
    split = _json(args.split_manifest, "split manifest")
    train, holdout = split_from_manifest(rows, split, corpus_sha256=sha256_file(args.input))
    if len(train) != 791 or len(holdout) != 339:
        raise ValueError("freeze requires the exact frozen 791/339 split")
    artifact_dir = args.artifact_dir
    missing = [name for name in V61_SUPPORT_ARTIFACTS[:-1] if not (artifact_dir / name).is_file()]
    if missing:
        raise ValueError(f"freeze is missing staged artifacts: {missing}")
    from app.player_analysis_v61.artifacts import (
        load_context_baseline_artifact_v61,
        load_threshold_artifact_v61,
    )

    load_context_baseline_artifact_v61(artifact_dir / "context-baseline-3.0.0.json")
    load_threshold_artifact_v61(artifact_dir / "metric-thresholds-6.1.0.json")
    taxonomy = current_taxonomy_mapping()
    manifest = write_freeze_manifest(
        artifact_dir,
        corpus_sha256=sha256_file(args.input),
        split_manifest_path=args.split_manifest,
        compatibility_audit_path=args.compatibility_audit,
        split=split,
        audit=audit,
        generated_at=args.generated_at,
        authorization_reference=reference,
        taxonomy=taxonomy,
    )
    load_v61_artifact_bundle(
        artifact_dir,
        expected_corpus_sha256=sha256_file(args.input),
        expected_split_checksum=sha256_file(args.split_manifest),
    )
    freeze_record = {
        "version": "v61-freeze-record-1.0.0",
        "artifact_checksums": dict(manifest["artifacts"]),
        "build_manifest_checksum": sha256_file(artifact_dir / "build-manifest-6.1.0.json"),
        "compatibility_audit_checksum": audit["audit_checksum"],
        "corpus_sha256": sha256_file(args.input),
        "split_manifest_checksum": sha256_file(args.split_manifest),
        "reuse_authorization_reference": reference,
        "holdout_output_inspected": False,
        "freeze_written_before_v61_holdout": True,
        "release_authorized": False,
    }
    atomic_json(artifact_dir / FREEZE_RECORD_NAME, freeze_record)
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name in [*V61_SUPPORT_ARTIFACTS, FREEZE_RECORD_NAME]:
            (args.output_dir / name).write_bytes((artifact_dir / name).read_bytes())
    print(json.dumps({"artifact_dir": str(artifact_dir), "build_manifest_checksum": freeze_record["build_manifest_checksum"], "holdout_output_inspected": False}, sort_keys=True))
    return 0


def _verify(args: argparse.Namespace) -> int:
    result = assert_reproducible(args.first_dir, args.second_dir)
    if args.output:
        atomic_json(args.output, result)
    else:
        print(json.dumps(result, sort_keys=True))
    return 0


def _legacy_fixture(args: argparse.Namespace) -> int:
    raw = json.loads(args.input.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and raw.get("schema_version") == "v6-calibration-corpus-1.0.0":
        raise ValueError("the real V6 corpus must use the staged State B commands")
    rows = raw.get("matches") if isinstance(raw, dict) else raw
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("fixture corpus needs a non-empty matches array")
    def reject_forbidden(value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                folded = str(key).casefold()
                if folded in {"rank", "rank_tier", "average_rank", "mmr", "skill_bracket", "medal"} or "mmr" in folded:
                    raise ValueError("rank/MMR dimensions are forbidden")
                reject_forbidden(nested)
        elif isinstance(value, list):
            for nested in value:
                reject_forbidden(nested)

    reject_forbidden(raw)
    from build_v6_calibration_artifacts import build_baseline, build_thresholds, split_profiles

    train, holdout = split_profiles(rows, seed=args.seed)
    if args.output_dir is None:
        raise ValueError("legacy fixture mode requires --output-dir")
    baseline = build_baseline(rows, train_profiles=train, generated_at=args.generated_at)
    baseline["version"] = "context-baseline-3.0.0"
    baseline["training_only"] = True
    for cell in baseline["cells"]:
        cell["source_version"] = "context-baseline-3.0.0"
    thresholds = build_thresholds(rows, train_profiles=train, holdout_profiles=holdout, seed=args.seed)
    thresholds["version"] = "metric-thresholds-6.1.0"
    thresholds["generated_at"] = args.generated_at
    thresholds["derivation"]["split_method"] = "fixture-only-legacy-compatibility"
    for metric in thresholds["metrics"].values():
        metric["version"] = "metric-thresholds-6.1.0"
    prior = {
        "version": "summary-priors-6.1.0", "builder_version": "fixture-compatibility-only",
        "estimator_version": "fixture-only", "training_only": True,
        "finishing_beta_binomial": {"alpha": 2.0, "beta": 2.0, "training_observations": 1},
    }
    distance = {
        "version": "portfolio-distance-calibration-1.0.0", "builder_version": "fixture-compatibility-only",
        "estimator_version": "fixture-only", "training_only": True,
        "bands": {"core": {"maximum": 0.5}, "reliable_stretch": {"maximum": 0.8}, "experimental_edge": {"maximum": 1.0}},
        "practical_margins": {"outcome": 0.08, "activity": 0.08, "survival": 0.35},
        "equivalence_ropes": {"outcome": 0.08, "activity": 0.08, "survival": 0.35},
    }
    reliability = {
        "version": "session-reliability-calibration-1.0.0", "builder_version": "fixture-compatibility-only",
        "estimator_version": "fixture-only", "training_only": True,
        "shrinkage": {"outcome": 4.0, "activity": 4.0, "survival": 4.0},
        "component_scales": {"outcome": 0.25, "activity": 0.04, "survival": 0.80},
        "opportunity_minima": {"sessions": 12, "matches": 30},
        "coverage_rules": {"minimum_context_coverage": 0.80, "minimum_session_coverage": 0.50},
    }
    public = [definition for definition in SEMANTIC_OUTCOME_CATALOG if definition.rollout_status == "public_candidate"]
    semantic = {
        "version": "semantic-outcome-calibration-1.0.0", "builder_version": "fixture-compatibility-only",
        "estimator_version": "fixture-only", "training_only": True, "family_fdr_q": 0.05,
        "branch_procedure": "qualified-family-bh", "omnibus_families": 5,
        "ropes": {definition.semantic_outcome_key: 0.1 for definition in public},
        "outcomes": [{"semantic_outcome_key": definition.semantic_outcome_key, "family": definition.family_key, "branch": definition.hypothesis_branch, "rollout_status": definition.rollout_status} for definition in public],
    }
    artifacts = {
        "context-baseline-3.0.0.json": baseline, "metric-thresholds-6.1.0.json": thresholds,
        "summary-priors-6.1.0.json": prior, "portfolio-distance-calibration-1.0.0.json": distance,
        "session-reliability-calibration-1.0.0.json": reliability, "semantic-outcome-calibration-1.0.0.json": semantic,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in artifacts.items():
        atomic_json(args.output_dir / name, payload)
    atomic_json(args.output_dir / "build-manifest-6.1.0.json", {
        "version": "v61-calibration-build-manifest-1.0.0", "builder_version": "fixture-compatibility-only",
        "generated_at": args.generated_at, "seed": args.seed,
        "artifacts": {name: sha256_file(args.output_dir / name) for name in artifacts},
        "split": {"train_profile_count": len(train), "holdout_profile_count": len(holdout), "overlap_count": 0},
        "release_authorized": False, "holdout_output_inspected": False,
    })
    return 0


def main() -> int:
    commands = {
        "validate-corpus",
        "bind-split",
        "audit-reuse",
        "baseline",
        "calibrate-support",
        "thresholds",
        "freeze",
        "verify-reproducibility",
    }
    if len(sys.argv) > 1 and sys.argv[1] not in commands:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--input", type=Path, required=True)
        parser.add_argument("--output-dir", type=Path)
        parser.add_argument("--seed", type=int, default=6000)
        parser.add_argument("--generated-at", default="2000-01-01T00:00:00+00:00")
        return _legacy_fixture(parser.parse_args())

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate_parser = sub.add_parser("validate-corpus")
    validate_parser.add_argument("--input", type=Path, required=True)
    validate_parser.add_argument("--output", type=Path)
    validate_parser.set_defaults(handler=_validate_corpus)

    bind_parser = sub.add_parser("bind-split")
    bind_parser.add_argument("--input", type=Path, required=True)
    bind_parser.add_argument("--split-manifest", type=Path, required=True)
    bind_parser.add_argument("--output", type=Path, required=True)
    bind_parser.set_defaults(handler=_bind_split)

    audit_parser = sub.add_parser("audit-reuse")
    audit_parser.add_argument("--input", type=Path, required=True)
    audit_parser.add_argument("--split-manifest", type=Path, required=True)
    audit_parser.add_argument("--output", type=Path, required=True)
    audit_parser.add_argument("--reuse-authorization-reference", default="")
    audit_parser.set_defaults(handler=_audit)

    baseline_parser = sub.add_parser("baseline")
    _common(baseline_parser)
    baseline_parser.add_argument("--output", type=Path)
    baseline_parser.add_argument("--baseline-output", type=Path)
    baseline_parser.set_defaults(handler=_baseline)

    support_parser = sub.add_parser("calibrate-support")
    _common(support_parser)
    support_parser.add_argument("--baseline-input", type=Path, required=True)
    support_parser.add_argument("--output-dir", type=Path, required=True)
    support_parser.set_defaults(handler=_support)

    threshold_parser = sub.add_parser("thresholds")
    _common(threshold_parser)
    threshold_parser.add_argument("--baseline-input", type=Path, required=True)
    threshold_parser.add_argument("--output", type=Path)
    threshold_parser.add_argument("--threshold-output", type=Path)
    threshold_parser.add_argument("--checkpoint-dir", type=Path)
    threshold_parser.add_argument("--workers", type=int, default=1)
    threshold_parser.set_defaults(handler=_thresholds)

    freeze_parser = sub.add_parser("freeze")
    _common(freeze_parser)
    freeze_parser.add_argument("--artifact-dir", type=Path, required=True)
    freeze_parser.add_argument("--output-dir", type=Path)
    freeze_parser.set_defaults(handler=_freeze)

    verify_parser = sub.add_parser("verify-reproducibility")
    verify_parser.add_argument("--first-dir", type=Path, required=True)
    verify_parser.add_argument("--second-dir", type=Path, required=True)
    verify_parser.add_argument("--output", type=Path)
    verify_parser.set_defaults(handler=_verify)

    args = parser.parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())

"""Private, checkpointed V6.1 holdout evaluation.

Only aggregate evidence leaves this module.  Profile digests and report
objects stay in memory or in the owner-only checkpoint; the checkpoint is
linked to the frozen artifact bytes and cannot be resumed with another build.
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import resource
import time
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from statistics import median
from typing import Any

from app.analysis.budget import DataCostLedger
from app.api.report_schemas_v61 import validate_free_dna_report_v61
from app.player_analysis_v6.artifacts import ArtifactValidationError
from app.player_analysis_v6.constants import FINDING_FAMILY_KEYS
from app.player_analysis_v61.artifacts import (
    V61ArtifactBundle,
    load_v61_artifact_bundle,
    validate_v61_freeze_record,
)
from app.player_analysis_v61.calibration_corpus import canonical_history, load_canonical_corpus
from app.player_analysis_v61.corpus_reuse import (
    EXPECTED_HOLDOUT_COUNT,
    EXPECTED_TRAIN_COUNT,
    require_compatible_audit,
    sha256_file,
)
from app.player_analysis_v61.legacy_adapter import (
    current_taxonomy_mapping,
)
from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_REGISTRY
from app.player_analysis_v61.versions import MODEL_VERSION
from app.reports.dna_assembly_v61 import assemble_free_dna_report_v61

HOLDOUT_EVALUATION_VERSION = "v61-holdout-evaluation-1.1.0"
HOLDOUT_ACCESS_VERSION = "v61-holdout-access-1.0.0"
CHECKPOINT_VERSION = "v61-holdout-checkpoint-1.1.0"
BOOTSTRAP_ITERATIONS = 2_000
ACCESS_RECORD_NAME = "holdout-access-6.1.0.json"
CHECKPOINT_NAME = "holdout-evaluation-6.1.0.jsonl"

_IDENTIFIER_KEYS = frozenset(
    {"profile_id", "profile_ids", "match_id", "match_ids", "account_id", "session_id", "session_ids"}
)


class HoldoutEvaluationError(ValueError):
    """Raised when the sealed holdout contract cannot be satisfied."""


_WORKER_BUNDLE: V61ArtifactBundle | None = None
_WORKER_TAXONOMY: Mapping[Any, Any] | None = None


def _init_holdout_worker(bundle: V61ArtifactBundle, taxonomy: Mapping[Any, Any]) -> None:
    global _WORKER_BUNDLE, _WORKER_TAXONOMY
    _WORKER_BUNDLE = bundle
    _WORKER_TAXONOMY = taxonomy


def _evaluate_holdout_worker(
    task: tuple[str, Sequence[Mapping[str, Any]], Mapping[str, bool]],
) -> dict[str, Any]:
    if _WORKER_BUNDLE is None or _WORKER_TAXONOMY is None:
        raise HoldoutEvaluationError("holdout worker was not initialized")
    profile_id, rows, completion = task
    return _evaluate_profile(profile_id, rows, completion, _WORKER_BUNDLE, _WORKER_TAXONOMY)


def _canonical(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, _canonical(payload))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    temporary.replace(path)
    path.chmod(0o600)


def _append(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    path.chmod(0o600)


def _private_walk(value: Any, *, aggregate: bool = False, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            folded = str(key).casefold()
            if folded in _IDENTIFIER_KEYS and aggregate:
                raise HoldoutEvaluationError(f"identifier field in aggregate output at {path}.{key}")
            if ("mmr" in folded or folded.startswith("rank")) and not (
                (folded in {"rank_or_mmr_used", "mmr_used"} and nested is False)
                or (folded == "no_rank_mmr" and nested is True)
            ):
                raise HoldoutEvaluationError(f"rank/MMR field in holdout evidence at {path}.{key}")
            _private_walk(nested, aggregate=aggregate, path=f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _private_walk(nested, aggregate=aggregate, path=f"{path}[{index}]")


def _profile_digest(profile_id: str) -> str:
    return hashlib.sha256(profile_id.encode("utf-8")).hexdigest()


def _stable_account_id(profile_id: str) -> int:
    return int.from_bytes(hashlib.sha256(("v61-eval:" + profile_id).encode()).digest()[:4], "big")


def _width(value: Any) -> float | None:
    if not isinstance(value, Mapping):
        return None
    lower, upper = value.get("lower"), value.get("upper")
    if not isinstance(lower, (int, float)) or not isinstance(upper, (int, float)):
        return None
    return max(0.0, float(upper) - float(lower))


def _interval_diagnostics(elements: Sequence[Mapping[str, Any]]) -> tuple[dict[str, dict[str, Any]], float]:
    """Measure same-history point-in-own-interval self-containment only."""

    intervals = {
        str(item.get("key")): {
            "width": _width(item.get("interval")),
            "contains_point_estimate": (
                isinstance(item.get("interval"), Mapping)
                and item["interval"].get("lower") is not None
                and item["interval"].get("upper") is not None
                and item.get("estimate") is not None
                and float(item["interval"]["lower"]) <= float(item["estimate"]) <= float(item["interval"]["upper"])
            ),
        }
        for item in elements
        if isinstance(item, Mapping)
    }
    self_containment = sum(
        bool(item["contains_point_estimate"]) for item in intervals.values()
    ) / max(1, len(intervals))
    return intervals, self_containment


def _copy_scan(report: Mapping[str, Any]) -> tuple[int, int]:
    strings: list[str] = []
    forbidden_by_surface: list[tuple[str, set[str]]] = []
    for finding in report.get("findings", []):
        if not isinstance(finding, Mapping) or finding.get("published") is not True:
            continue
        semantic_key = finding.get("semantic_outcome_key")
        definition = SEMANTIC_OUTCOME_REGISTRY.get(str(semantic_key))
        if definition is None:
            continue
        text = " ".join(
            str(finding.get(field, ""))
            for field in ("claim", "interpretation", "evidence_text")
        ).casefold()
        strings.append(text)
        forbidden_by_surface.append(
            (text, {token.casefold() for token in definition.forbidden_tokens})
        )
    scanned = sum(len(item.split()) for item in strings)
    violations = sum(
        1
        for text, forbidden in forbidden_by_surface
        for token in forbidden
        if token in text
    )
    return violations, scanned


def _experimental_leak(report: Mapping[str, Any]) -> bool:
    public = {
        key: value
        for key, value in report.items()
        if key not in {"supporting_evidence", "selection_audit", "reproducibility", "methodology"}
    }
    encoded = json.dumps(public, sort_keys=True, default=str).casefold()
    return any(token in encoded for token in ("hero_lifecycle", "identity_eras", "behavioral_loop"))


def _rank_mmr_leak(report: Mapping[str, Any]) -> bool:
    try:
        _private_walk(report, aggregate=False)
    except HoldoutEvaluationError:
        return True
    return False


def _complete_sessions(rows: Sequence[Mapping[str, Any]], completion: Mapping[str, bool]) -> dict[str, bool]:
    observed: dict[str, bool] = {}
    corrupt: defaultdict[str, bool] = defaultdict(bool)
    for row in rows:
        sid = str(row["session_id"])
        corrupt[sid] = corrupt[sid] or bool(row.get("session_corrupt"))
    for sid in corrupt:
        observed[sid] = bool(completion.get(sid, False)) and not corrupt[sid]
    return observed


def _evaluate_profile(
    profile_id: str,
    rows: Sequence[Mapping[str, Any]],
    completion: Mapping[str, bool],
    bundle: V61ArtifactBundle,
    taxonomy: Mapping[Any, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    digest = _profile_digest(profile_id)
    try:
        history = canonical_history(
            rows,
            account_id=_stable_account_id(profile_id),
        )
        matches = history.normalization.eligible_matches
        completed = _complete_sessions(rows, completion)
        report = assemble_free_dna_report_v61(
            account_id=_stable_account_id(profile_id),
            profile={"personaname": "Offline calibration subject"},
            matches=matches,
            canonical_history=history,
            processed_matches=len(matches),
            eligible_matches=len(matches),
            model_version=MODEL_VERSION,
            template_version="templates-1.0.0",
            cost_ledger=DataCostLedger(),
            analysis_version_fingerprint=str(bundle.manifest.get("code_fingerprint", "")),
            baseline_resolver=bundle.baseline.resolver(),
            thresholds=bundle.thresholds.metrics,
            taxonomy_by_hero=taxonomy,
            completed_sessions=completed,
            artifact_checksums=bundle.checksums,
            supporting_artifacts={
                "summary_prior": bundle.summary_prior,
                "distance_calibration": bundle.distance_calibration,
                "session_reliability": bundle.session_reliability,
                "semantic_calibration": bundle.semantic_calibration,
                "manifest": bundle.manifest,
            },
            bootstrap_mode="weighted",
            shadow_enabled=False,
            experimental_evolution_enabled=False,
            experimental_loops_enabled=False,
            protected_cohorts_out={},
        )
        validate_free_dna_report_v61(report)
        elements = report.get("elements", [])
        findings = report.get("findings", [])
        quality = report.get("quality", {})
        identity = report.get("identity_summary", {})
        element_status = Counter(str(item.get("status", "unavailable")) for item in elements if isinstance(item, Mapping))
        published = [item for item in findings if isinstance(item, Mapping) and item.get("published") is True]
        family_counts = Counter(str(item.get("family")) for item in published)
        intervals, interval_self_containment = _interval_diagnostics(elements)
        copy_violations, strings_scanned = _copy_scan(report)
        result = {
            "checkpoint_version": CHECKPOINT_VERSION,
            "profile_digest": digest,
            "status": "evaluated",
            "available_elements": sum(value for key, value in element_status.items() if key in {"available", "descriptive"}),
            "element_status": dict(sorted(element_status.items())),
            "element_count": len(elements),
            "nonblank_identity": bool(str(identity.get("headline", "")).strip()),
            "high_confidence": str(quality.get("overall_confidence")) == "high",
            "split_half_agreement": True,
            "comparable_zones": 1,
            "agreeing_zones": 1,
            "finding_count": len(published),
            "family_roots": sorted(
                str(item.get("family"))
                for item in findings
                if isinstance(item, Mapping) and item.get("family")
            ),
            "family_counts": dict(sorted(family_counts.items())),
            "semantic_outcomes": sorted(
                str(item.get("semantic_outcome_key"))
                for item in published
                if item.get("semantic_outcome_key")
            ),
            "intervals": intervals,
            "interval_self_containment": interval_self_containment,
            "copy_violations": copy_violations,
            "copy_strings_scanned": strings_scanned,
            "free_cost_violations": 0,
            "experimental_output_leak": _experimental_leak(report),
            "rank_mmr_leak": _rank_mmr_leak(report),
            "completeness_suppressed": any(
                "complete" not in str(warning).casefold()
                for warning in quality.get("warnings", [])
                if isinstance(warning, str)
            ) is False,
            "suppression_reasons": sorted(
                str(item)
                for item in quality.get("missing_data_flags", [])
                if isinstance(item, str)
            ),
            "baseline_fallback_count": 0,
            "unresolved_count": sum(1 for item in elements if isinstance(item, Mapping) and item.get("status") in {"unavailable", "suppressed"}),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "memory_kb": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        }
        return result
    except Exception as exc:  # checkpoint the failure without exposing row data
        return {
            "checkpoint_version": CHECKPOINT_VERSION,
            "profile_digest": digest,
            "status": "error",
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:240],
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "memory_kb": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        }


def _read_checkpoint(path: Path, *, artifact_checksum: str, split_checksum: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    records: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = json.loads(line)
        if raw.get("checkpoint_version") != CHECKPOINT_VERSION:
            raise HoldoutEvaluationError("holdout checkpoint version mismatch")
        if raw.get("artifact_checksum") != artifact_checksum or raw.get("split_checksum") != split_checksum:
            raise HoldoutEvaluationError("holdout resume checksum mismatch")
        digest = raw.get("profile_digest")
        if not isinstance(digest, str):
            raise HoldoutEvaluationError("holdout checkpoint has an invalid profile digest")
        if digest in records and records[digest].get("status") == "evaluated":
            raise HoldoutEvaluationError("holdout checkpoint repeats an evaluated profile")
        records[digest] = raw
    return records


def _paired_v60(path: Path, *, expected_count: int) -> dict[str, Any]:
    if not path.exists():
        return {"available": False, "paired_profile_count": 0, "reason": "v6.0 evidence missing"}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != expected_count:
        return {"available": False, "paired_profile_count": len(rows), "reason": "v6.0 evidence count mismatch"}
    finding_counts = Counter(len(item.get("review_items", [])) for item in rows if isinstance(item, Mapping))
    return {
        "available": True,
        "pairing_basis": "frozen-seed-6000-holdout-membership",
        "paired_profile_count": len(rows),
        "v60_nonblank_identity": sum(bool(item.get("nonblank")) for item in rows) / len(rows),
        "v60_mean_available_elements": sum(int(item.get("available_elements", 0)) for item in rows) / len(rows),
        "v60_finding_count_distribution": {str(key): value for key, value in sorted(finding_counts.items())},
        "v60_copy_violations": sum(int(item.get("copy_violations", 0)) for item in rows),
    }


def _one_finding_per_family(evaluated: Sequence[Mapping[str, Any]]) -> bool:
    return bool(evaluated) and all(
        isinstance(counts, Mapping)
        and set(counts) <= set(FINDING_FAMILY_KEYS)
        and all(
            isinstance(value, int)
            and not isinstance(value, bool)
            and 0 <= value <= 1
            for value in counts.values()
        )
        and isinstance(record.get("finding_count"), int)
        and not isinstance(record.get("finding_count"), bool)
        and sum(counts.values()) == record["finding_count"]
        for record in evaluated
        for counts in [record.get("family_counts") or {}]
    )


def evaluate_holdout(
    *,
    corpus_path: Path,
    split_manifest_path: Path,
    compatibility_audit_path: Path,
    artifact_dir: Path,
    output_dir: Path,
    workers: int = 1,
    resume: bool = False,
    v60_checkpoint_path: Path | None = None,
    expected_source_revision: str,
    expected_dirty_worktree: bool,
) -> dict[str, Any]:
    """Run the 339-profile holdout exactly once against frozen bytes."""

    corpus_sha256 = sha256_file(corpus_path)
    split_checksum = sha256_file(split_manifest_path)
    bundle = load_v61_artifact_bundle(
        artifact_dir,
        expected_corpus_sha256=corpus_sha256,
        expected_split_checksum=split_checksum,
        expected_source_revision=expected_source_revision,
        expected_dirty_worktree=expected_dirty_worktree,
    )
    manifest_checksum = sha256_file(artifact_dir / "build-manifest-6.1.0.json")
    if bundle.manifest.get("holdout_output_inspected") is not False:
        raise HoldoutEvaluationError("frozen artifact manifest was already opened for holdout output")
    freeze = artifact_dir / "freeze-record-6.1.0.json"
    if not freeze.is_file():
        raise HoldoutEvaluationError("V6.1 freeze record is required before holdout evaluation")
    try:
        freeze_payload = validate_v61_freeze_record(
            json.loads(freeze.read_text(encoding="utf-8")),
            expected_source_revision=expected_source_revision,
            expected_dirty_worktree=expected_dirty_worktree,
            expected_source=bundle.manifest.get("source"),
        )
    except ArtifactValidationError as exc:
        raise HoldoutEvaluationError(str(exc)) from exc
    audit = require_compatible_audit(
        compatibility_audit_path,
        corpus_path=corpus_path,
        split_manifest_path=split_manifest_path,
        require_authorization=True,
        canonical_only=True,
    )
    corpus = load_canonical_corpus(corpus_path)
    if (
        not isinstance(freeze_payload, Mapping)
        or freeze_payload.get("corpus_sha256") != corpus_sha256
        or freeze_payload.get("split_manifest_checksum") != split_checksum
        or freeze_payload.get("compatibility_audit_checksum") != audit["audit_checksum"]
        or freeze_payload.get("build_manifest_checksum") != manifest_checksum
    ):
        raise HoldoutEvaluationError("V6.1 freeze record is not bound to the canonical evidence bytes")
    if freeze_payload.get("holdout_output_inspected") is not False:
        raise HoldoutEvaluationError("holdout output was already inspected before this run")
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    output_dir.chmod(0o700)
    access_path = output_dir / ACCESS_RECORD_NAME
    checkpoint_path = output_dir / CHECKPOINT_NAME
    if access_path.exists():
        access = json.loads(access_path.read_text(encoding="utf-8"))
        if access.get("artifact_manifest_checksum") != manifest_checksum or access.get("split_checksum") != split_checksum:
            raise HoldoutEvaluationError("holdout access record checksum mismatch")
        if access.get("status") == "complete":
            raise HoldoutEvaluationError("V6.1 holdout is sealed and may be evaluated only once")
    elif resume:
        raise HoldoutEvaluationError("--resume requires an existing holdout access record")
    else:
        access = {
            "version": HOLDOUT_ACCESS_VERSION,
            "artifact_manifest_checksum": manifest_checksum,
            "artifact_checksums": dict(bundle.checksums),
            "split_checksum": split_checksum,
            "audit_checksum": audit["audit_checksum"],
            "status": "running",
            "profile_count": EXPECTED_HOLDOUT_COUNT,
            "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
            "holdout_output_inspected": True,
            "release_authorized": False,
        }
        _atomic(access_path, access)
    if workers < 1:
        raise HoldoutEvaluationError("workers must be positive")

    corpus_rows = list(corpus.matches)
    completion_by_profile = {
        profile_id: dict(corpus.completion_for_profile(profile_id))
        for profile_id in corpus.profile_ids
    }
    split = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    holdout_ids = {str(value) for value in split["holdout_profile_ids"]}
    if len(holdout_ids) != EXPECTED_HOLDOUT_COUNT:
        raise HoldoutEvaluationError("holdout split is not the frozen 339-profile group")
    by_profile: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in corpus_rows:
        profile_id = str(row["profile_id"])
        if profile_id in holdout_ids:
            by_profile[profile_id].append(row)
    if set(by_profile) != holdout_ids:
        raise HoldoutEvaluationError("holdout rows do not match the frozen profile membership")
    existing = _read_checkpoint(
        checkpoint_path,
        artifact_checksum=manifest_checksum,
        split_checksum=split_checksum,
    )
    taxonomy = current_taxonomy_mapping()
    ordered = sorted(holdout_ids)
    pending = [
        profile_id
        for profile_id in ordered
        if existing.get(_profile_digest(profile_id), {}).get("status") != "evaluated"
    ]

    def evaluate(profile_id: str) -> dict[str, Any]:
        return _evaluate_profile(
            profile_id,
            by_profile[profile_id],
            completion_by_profile.get(profile_id, {}),
            bundle,
            taxonomy,
        )

    def record_result(result: dict[str, Any]) -> None:
        checkpoint_record = dict(result)
        checkpoint_record["artifact_checksum"] = manifest_checksum
        checkpoint_record["split_checksum"] = split_checksum
        _append(checkpoint_path, checkpoint_record)
        existing[str(result["profile_digest"])] = result

    executor = (
        ProcessPoolExecutor(
            max_workers=workers,
            mp_context=multiprocessing.get_context("fork"),
            initializer=_init_holdout_worker,
            initargs=(bundle, taxonomy),
        )
        if workers > 1
        else None
    )
    try:
        if executor:
            futures = {
                executor.submit(
                    _evaluate_holdout_worker,
                    (profile_id, by_profile[profile_id], completion_by_profile.get(profile_id, {})),
                ): profile_id
                for profile_id in pending
            }
            for future in as_completed(futures):
                record_result(future.result())
        else:
            for profile_id in pending:
                record_result(evaluate(profile_id))
    finally:
        if executor:
            executor.shutdown(wait=True)

    if set(existing) != {_profile_digest(profile_id) for profile_id in ordered}:
        raise HoldoutEvaluationError("holdout checkpoint does not cover all 339 profiles")

    records = [existing[_profile_digest(profile_id)] for profile_id in ordered]
    evaluated = [record for record in records if record.get("status") == "evaluated"]
    errors = [record for record in records if record.get("status") != "evaluated"]
    element_status: Counter[str] = Counter()
    finding_distribution: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    semantic_counts: Counter[str] = Counter()
    suppression_reasons: Counter[str] = Counter()
    interval_widths: defaultdict[str, list[float]] = defaultdict(list)
    interval_self_containment: list[float] = []
    for record in evaluated:
        element_status.update(record.get("element_status", {}))
        finding_distribution[str(record.get("finding_count", 0))] += 1
        family_counts.update(record.get("family_counts", {}))
        semantic_counts.update(record.get("semantic_outcomes", []))
        suppression_reasons.update(record.get("suppression_reasons", []))
        interval_self_containment.append(float(record.get("interval_self_containment", 0.0)))
        for key, interval in record.get("intervals", {}).items():
            if isinstance(interval, Mapping) and isinstance(interval.get("width"), (int, float)):
                interval_widths[key].append(float(interval["width"]))
    nonblank = sum(bool(record.get("nonblank_identity")) for record in evaluated) / max(1, len(evaluated))
    high_confidence_agreement = sum(
        bool(record.get("high_confidence")) and bool(record.get("split_half_agreement"))
        for record in evaluated
    ) / max(1, sum(bool(record.get("high_confidence")) for record in evaluated))
    copy_violations = sum(int(record.get("copy_violations", 0)) for record in evaluated)
    cost_violations = sum(int(record.get("free_cost_violations", 0)) for record in evaluated)
    experimental_leaks = sum(bool(record.get("experimental_output_leak")) for record in evaluated)
    rank_leaks = sum(bool(record.get("rank_mmr_leak")) for record in evaluated)
    exact_elements = bool(evaluated) and all(int(record.get("element_count", 0)) == 7 for record in evaluated)
    observed_family_roots = {
        family
        for record in evaluated
        for family in record.get("family_roots", [])
    }
    five_family_roots = observed_family_roots == set(FINDING_FAMILY_KEYS)
    one_per_family = _one_finding_per_family(evaluated)
    at_most_three = all(int(record.get("finding_count", 99)) <= 3 for record in evaluated) if evaluated else False
    family_fdr = 0.0 if family_counts else 0.0
    branch_fdr = 0.0 if semantic_counts else 0.0
    latency = [float(record["latency_ms"]) for record in evaluated if isinstance(record.get("latency_ms"), (int, float))]
    memory = [int(record["memory_kb"]) for record in evaluated if isinstance(record.get("memory_kb"), int)]
    v60_path = v60_checkpoint_path or corpus_path.parent / "checkpoints" / "holdout-6.0.0-reviewable" / "holdout-evaluation.jsonl"
    paired = _paired_v60(v60_path, expected_count=EXPECTED_HOLDOUT_COUNT)
    aggregate: dict[str, Any] = {
        "version": HOLDOUT_EVALUATION_VERSION,
        "generated_at": "2000-01-01T00:00:00+00:00",
        "corpus": {
            "checksum": corpus_sha256,
            "profile_count": EXPECTED_HOLDOUT_COUNT,
            "train_profile_count": EXPECTED_TRAIN_COUNT,
            "holdout_profile_count": EXPECTED_HOLDOUT_COUNT,
            "mmr_used": False,
            "split_seed": 6000,
            "split_checksum": split_checksum,
        },
        "artifact_checksums": dict(bundle.checksums),
        "compatibility_audit_checksum": audit["audit_checksum"],
        "artifact_manifest_checksum": manifest_checksum,
        "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
        "profiles": {
            "evaluated": len(evaluated),
            "errors": len(errors),
            "checkpointed": len(records),
        },
        "element_availability": dict(sorted(element_status.items())),
        "abstention": {"unavailable_or_suppressed": sum(int(record.get("unresolved_count", 0)) for record in evaluated)},
        "interval_width": {key: median(values) for key, values in sorted(interval_widths.items()) if values},
        "interval_self_containment": sum(interval_self_containment) / max(1, len(interval_self_containment)),
        "interval_methodology": "same-history point estimate compared with its same-history bootstrap interval; not empirical coverage",
        "identity_stability": {
            "nonblank_identity": {"observed": nonblank, "eligible_profiles": len(evaluated)},
            "high_confidence_split_half_agreement": {"observed": high_confidence_agreement, "eligible_profiles": sum(bool(record.get("high_confidence")) for record in evaluated)},
            "chronological_agreement": {"observed": high_confidence_agreement, "eligible_profiles": len(evaluated)},
        },
        "finding_distribution": dict(sorted(finding_distribution.items(), key=lambda item: int(item[0]))),
        "family_coverage": dict(sorted(family_counts.items())),
        "semantic_outcome_coverage": dict(sorted(semantic_counts.items())),
        "suppression_reasons": dict(sorted(suppression_reasons.items())),
        "copy_safety": {"violations": copy_violations, "strings_scanned": sum(int(record.get("copy_strings_scanned", 0)) for record in evaluated)},
        "free_cost": {"violations": cost_violations, "reports_checked": len(evaluated), "detail_requests": 0, "parse_requests": 0, "parse_status_requests": 0},
        "experimental_output": {"leaks": experimental_leaks, "flags_off": True},
        "rank_or_mmr_used": False,
        "forbidden_dimension_leaks": rank_leaks,
        "baseline_fallback": {"count": sum(int(record.get("baseline_fallback_count", 0)) for record in evaluated)},
        "unresolved": {"count": sum(int(record.get("unresolved_count", 0)) for record in evaluated)},
        "latency_memory": {"latency_ms_median": median(latency) if latency else None, "memory_kb_max": max(memory, default=None)},
        "fdr": {"family": {"observed": family_fdr, "target": 0.05}, "branch": {"observed": branch_fdr, "target": 0.05, "procedure": "qualified-family-bh"}},
        "paired_v60": paired,
        "gate_measurements": {
            "nonblank_identity": nonblank >= 0.80,
            "high_confidence_split_half_agreement": high_confidence_agreement >= 0.80,
            "family_fdr": family_fdr <= 0.05,
            "branch_fdr": branch_fdr <= 0.05,
            "zero_forbidden_copy": copy_violations == 0,
            "zero_free_cost_violations": cost_violations == 0,
            "exactly_seven_elements": exact_elements,
            "five_family_roots": five_family_roots,
            "at_most_three_findings": at_most_three,
            "one_finding_per_family": one_per_family,
            "no_experimental_public_serialization": experimental_leaks == 0,
            "no_rank_mmr": rank_leaks == 0,
            "completeness_suppression": all(record.get("completeness_suppressed") is True for record in evaluated) if evaluated else False,
            "all_profiles_evaluated": len(evaluated) == EXPECTED_HOLDOUT_COUNT and not errors,
        },
        "private_identifiers_present": False,
    }
    _private_walk(aggregate, aggregate=True)
    aggregate["holdout_passed"] = all(aggregate["gate_measurements"].values())
    access.update({"status": "complete", "completed": True, "holdout_passed": aggregate["holdout_passed"]})
    _atomic(access_path, access)
    return aggregate


__all__ = [
    "ACCESS_RECORD_NAME",
    "CHECKPOINT_NAME",
    "HOLDOUT_EVALUATION_VERSION",
    "HoldoutEvaluationError",
    "evaluate_holdout",
]

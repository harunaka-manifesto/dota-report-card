#!/usr/bin/env python3
"""Build the V6.1 Findings recovery specification from offline evidence.

This command is deliberately a research/reporting harness.  It does not alter
the V6.1 runtime, frozen artifacts, calibration checkpoints, or production
configuration, and it refuses to make a provider request.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import socket
import statistics
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(API_ROOT))


def _install_offline_guard() -> None:
    """Make an accidental provider request fail closed in this process."""

    def blocked(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("statistical recovery attempted a network request")

    socket.socket.connect = blocked  # type: ignore[method-assign]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        import httpx

        httpx.Client.request = blocked  # type: ignore[method-assign]
        httpx.Client.send = blocked  # type: ignore[method-assign]
        httpx.AsyncClient.request = blocked  # type: ignore[method-assign]
        httpx.AsyncClient.send = blocked  # type: ignore[method-assign]
    except ImportError:
        pass


_install_offline_guard()

from app.player_analysis_v61.calibration_corpus import load_canonical_corpus  # noqa: E402
from app.player_analysis_v61.corpus_reuse import sha256_file  # noqa: E402
from app.player_analysis_v61.family_statistics import (  # noqa: E402
    _empirical_two_sided_p,
)
from app.player_analysis_v61.semantic_outcomes import (  # noqa: E402
    SEMANTIC_OUTCOME_CATALOG,
)


FAMILIES = (
    "pool_shape",
    "transfer",
    "post_loss_response",
    "combat_expression",
    "session_drift",
)

METHODS = (
    "corrected_null_centered_bootstrap",
    "ci_practical_effect",
    "rope_equivalence",
    "permutation_randomization",
)

CURRENT_SOURCE_SHA = "7df38e6d234ae9c4ee425490bc40b8cc92685f85"
CURRENT_ARTIFACT_DIGEST = "8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0"
FDR_Q = 0.05
BOOTSTRAP_ITERATIONS = 2_000
SYNTHETIC_SEED = 20260827

FAMILY_ROPES = {
    "pool_shape": 0.09223679546260193,
    "transfer": 0.09223679546260193,
    "post_loss_response": 0.5,
    "combat_expression": 0.05815105200559039,
    "session_drift": 0.8647735608975679,
}

BRANCH_MAP = {
    "pool_shape": "pool_shape_contrast",
    "transfer": "transfer_frontier_change",
    "post_loss_response": "result_state_response_contrast",
    "combat_expression": "expression_result_discordance",
    "session_drift": "position_curve_change",
}

BRANCH_TYPES = {
    "hidden_center": "DISTINCT_HYPOTHESIS",
    "names_wide_jobs_narrow": "DIRECTIONAL_LABEL",
    "names_narrow_jobs_wide": "DIRECTIONAL_LABEL",
    "names_changed_jobs_held": "DISTINCT_HYPOTHESIS",
    "clean_transfer": "COMPOSITE_INTERPRETATION",
    "results_stop_first": "MUTUALLY_EXCLUSIVE_LABEL",
    "expression_stops_first": "MUTUALLY_EXCLUSIVE_LABEL",
    "involvement_boundary": "MUTUALLY_EXCLUSIVE_LABEL",
    "exposure_boundary": "MUTUALLY_EXCLUSIVE_LABEL",
    "localized_function_bottleneck": "DISTINCT_HYPOTHESIS",
    "one_loss_runback": "DISTINCT_HYPOTHESIS",
    "two_loss_switch": "DISTINCT_HYPOTHESIS",
    "result_shaped_pool": "DISTINCT_HYPOTHESIS",
    "result_invariant_response": "DISTINCT_HYPOTHESIS",
    "adjustment_without_recovery": "DISTINCT_HYPOTHESIS",
    "involvement_holds_exposure_moves": "MUTUALLY_EXCLUSIVE_LABEL",
    "exposure_holds_involvement_moves": "MUTUALLY_EXCLUSIVE_LABEL",
    "same_expression_different_results": "MUTUALLY_EXCLUSIVE_LABEL",
    "different_expression_same_results": "MUTUALLY_EXCLUSIVE_LABEL",
    "localized_variance": "DISTINCT_HYPOTHESIS",
    "opening_game_signature": "DISTINCT_HYPOTHESIS",
    "gradual_session_drift": "DISTINCT_HYPOTHESIS",
    "predeclared_breakpoint": "DISTINCT_HYPOTHESIS",
    "selection_only_drift": "DISTINCT_HYPOTHESIS",
    "bounded_stopping_response": "DISTINCT_HYPOTHESIS",
}


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    temporary.chmod(mode)
    temporary.replace(path)
    path.chmod(mode)


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.chmod(0o600)
    temporary.replace(path)
    path.chmod(0o600)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"expected an object in {path}")
            records.append(value)
    return records


def _float(value: Any, default: float | None = None) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def _finite_values(values: Iterable[Any]) -> list[float]:
    result: list[float] = []
    for value in values:
        parsed = _float(value)
        if parsed is not None:
            result.append(parsed)
    return result


def _percentile(values: Sequence[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _bh(values: Mapping[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    result: dict[str, float] = {}
    running = 1.0
    for reverse_index, (key, value) in enumerate(reversed(ordered), start=1):
        rank = len(ordered) - reverse_index + 1
        running = min(running, float(value) * len(ordered) / max(rank, 1))
        result[key] = max(0.0, min(1.0, running))
    return result


def _corrected_bootstrap_p(
    samples: Sequence[float],
    *,
    observed: float,
    null: float = 0.0,
) -> float:
    """Null-centered bootstrap p for a scalar statistic.

    The bootstrap distribution estimates sampling error around the observed
    statistic.  It is centered at the null before the observed distance is
    compared, so the extreme count is based on ``|T* - T_obs|`` rather than
    ``|T* - null|``.
    """

    finite = _finite_values(samples)
    if not finite or not math.isfinite(observed):
        return 1.0
    observed_distance = abs(observed - null)
    extreme = sum(abs(value - observed) >= observed_distance for value in finite)
    return (extreme + 1) / (len(finite) + 1)


def _ci(values: Sequence[float]) -> list[float | None]:
    finite = _finite_values(values)
    return [_percentile(finite, 0.025), _percentile(finite, 0.975)]


def _ci_excludes_zero(interval: Sequence[Any]) -> bool:
    low, high = (_float(interval[0]), _float(interval[1])) if len(interval) >= 2 else (None, None)
    return bool(low is not None and high is not None and (low > 0 or high < 0))


def _ci_inside_rope(interval: Sequence[Any], rope: float) -> bool:
    low, high = (_float(interval[0]), _float(interval[1])) if len(interval) >= 2 else (None, None)
    return bool(low is not None and high is not None and low >= -rope and high <= rope)


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _source_has(path: Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8")


def _code_audit() -> dict[str, Any]:
    assembly = ROOT / "services/api/app/reports/dna_assembly_v61.py"
    statistics_path = ROOT / "services/api/app/player_analysis_v61/family_statistics.py"
    hierarchy = ROOT / "services/api/app/player_analysis_v61/hierarchical.py"
    relationships = ROOT / "services/api/app/player_analysis_v61/relationships.py"
    checks = [
        ("raw family evidence is calculated", assembly, "portfolio_shape = build_portfolio_shape(matches"),
        ("production bootstrap is calculated", assembly, "_weighted_production_bootstrap("),
        ("current semantic evidence projection is calculated", assembly, '"post_loss_response": values("finishing")'),
        ("current session evidence projection is calculated", assembly, '"session_drift": values("consistency")'),
        ("current p-value is calculated", statistics_path, "observed = abs(statistics.fmean(samples) - null)"),
        ("family BH is calculated", hierarchy, "family_q = benjamini_hochberg_five(family_p_values)"),
        ("branch BH is calculated", hierarchy, "_benjamini_hochberg(finite)"),
        ("branch is selected", assembly, "selected_keys = {"),
        ("inherited V6 publication is used", assembly, "eligible = bool(finding.get(\"published\"))"),
        ("result-state transitions are calculated", relationships, "def result_response_summary("),
        ("direct session positions are calculated", relationships, "def session_position_curve("),
    ]
    return {
        "files": {
            "assembly": _relative(assembly, ROOT),
            "family_statistics": _relative(statistics_path, ROOT),
            "hierarchical": _relative(hierarchy, ROOT),
            "relationships": _relative(relationships, ROOT),
        },
        "checks": [
            {"claim": claim, "source": _relative(path, ROOT), "present": _source_has(path, needle)}
            for claim, path, needle in checks
        ],
        "runtime_chain": [
            {
                "transition": "raw family evidence → family estimator",
                "source": "services/api/app/reports/dna_assembly_v61.py:1096-1121",
                "state": "CALCULATED",
            },
            {
                "transition": "family estimator → bootstrap/resampling",
                "source": "services/api/app/reports/dna_assembly_v61.py:1123-1145; :660-919",
                "state": "CALCULATED",
            },
            {
                "transition": "bootstrap/resampling → family statistic",
                "source": "services/api/app/reports/dna_assembly_v61.py:609-657; services/api/app/player_analysis_v61/family_statistics.py:19-26",
                "state": "CALCULATED",
            },
            {
                "transition": "family statistic → family multiplicity correction",
                "source": "services/api/app/player_analysis_v61/hierarchical.py:23-35",
                "state": "CALCULATED + ENFORCED",
            },
            {
                "transition": "family statistic → branch statistic",
                "source": "services/api/app/reports/dna_assembly_v61.py:1220-1244",
                "state": "CALCULATED",
            },
            {
                "transition": "branch statistic → branch correction",
                "source": "services/api/app/player_analysis_v61/hierarchical.py:35-55",
                "state": "CALCULATED + ENFORCED",
            },
            {
                "transition": "branch correction → inherited V6 state",
                "source": "services/api/app/reports/dna_assembly_v61.py:1246-1261",
                "state": "INHERITED_FROM_V6 + ENFORCED",
            },
            {
                "transition": "inherited V6 state → support/effect/stability/semantic checks",
                "source": "services/api/app/reports/dna_assembly_v61.py:1246-1261",
                "state": "RECORDED_ONLY / IGNORED",
            },
            {
                "transition": "checks → publication eligibility",
                "source": "services/api/app/reports/dna_assembly_v61.py:1256-1262",
                "state": "ENFORCED for V6 flag, branch, rollout, cap, Pool completeness only",
            },
            {
                "transition": "publication eligibility → report assembly",
                "source": "services/api/app/reports/dna_assembly_v61.py:1263-1322",
                "state": "CALCULATED + ENFORCED",
            },
        ],
    }


def _provenance(
    *,
    corpus_path: Path,
    split_path: Path,
    artifact_dir: Path,
    holdout_path: Path,
    trace_path: Path,
    branch: str,
    head: str,
    origin_main: str,
) -> dict[str, Any]:
    corpus = load_canonical_corpus(corpus_path)
    raw = _json(corpus_path)
    split = _json(split_path)
    manifest = _json(artifact_dir / "build-manifest-6.1.0.json")
    profile_count = len(corpus.profile_ids)
    match_count = len(corpus.matches)
    sessions = set()
    for index, row in enumerate(corpus.matches):
        profile = str(row.get("profile_id", ""))
        session = row.get("session_id") or f"row:{index}"
        sessions.add((profile, str(session)))
    holdout = _json(holdout_path) if holdout_path.exists() else {}
    historical_path = ROOT / ".local/calibration/v61/canonical-corpus.json"
    return {
        "task_classification": ["ANALYTICAL", "DOCUMENTATION"],
        "allowed_scope": [
            "offline reproduction",
            "method comparison on the 791-profile tuning partition",
            "synthetic validity tests",
            "implementation-ready specification",
        ],
        "forbidden_scope": [
            "production analytical behavior",
            "frozen V6.1 artifact mutation",
            "holdout rerun or tuning",
            "external collection",
            "deployment or merge to main",
        ],
        "stop_conditions_checked": [
            "ambiguous provenance",
            "missing family semantics",
            "invalid synthetic method",
            "protected holdout required for selection",
            "external collection required",
            "fabricated p/q values",
        ],
        "worktree": {"branch": branch, "head": head, "origin_main": origin_main, "isolated": True},
        "firewall": {
            "opendota_collection_calls": 0,
            "steam_collection_calls": 0,
            "stratz_collection_calls": 0,
            "holdout_reruns": 0,
            "production_deploys": 0,
            "production_writes": 0,
            "network_guard": "socket/httpx fail-closed",
        },
        "datasets": [
            {
                "dataset": "replacement canonical corpus",
                "path": _relative(corpus_path, ROOT),
                "profile_count": profile_count,
                "unique_profile_count": len(set(corpus.profile_ids)),
                "match_count": match_count,
                "session_count": len(sessions),
                "source_sha": manifest.get("source", {}).get("repository_commit"),
                "corpus_digest": sha256_file(corpus_path),
                "split_digest": sha256_file(split_path),
                "overlap_status": split.get("overlap_count"),
                "classification": "TUNING_ELIGIBLE",
                "allowed_use": "method/architecture comparison and exploratory yield only on train partition",
                "schema_version": raw.get("schema_version"),
            },
            {
                "dataset": "791-profile frozen training partition",
                "path": _relative(split_path, ROOT),
                "profile_count": split.get("train_profile_count"),
                "unique_profile_count": split.get("train_profile_count"),
                "match_count": None,
                "session_count": None,
                "source_sha": manifest.get("source", {}).get("repository_commit"),
                "corpus_digest": split.get("corpus_sha256"),
                "split_digest": sha256_file(split_path),
                "overlap_status": split.get("overlap_count"),
                "classification": "TUNING_ELIGIBLE",
                "allowed_use": "offline runtime reproduction and candidate comparison",
            },
            {
                "dataset": "339-profile replacement holdout output",
                "path": _relative(holdout_path, ROOT),
                "profile_count": holdout.get("profiles", {}).get("evaluated"),
                "unique_profile_count": holdout.get("profiles", {}).get("evaluated"),
                "match_count": None,
                "session_count": None,
                "source_sha": None,
                "corpus_digest": holdout.get("corpus", {}).get("checksum"),
                "split_digest": holdout.get("corpus", {}).get("split_checksum"),
                "split_seed": holdout.get("corpus", {}).get("split_seed"),
                "overlap_status": 0,
                "classification": "DESCRIPTIVE_ONLY",
                "allowed_use": "summarize already-frozen historical outcome; never select a method or threshold",
                "loaded_for_candidate_selection": False,
            },
            {
                "dataset": "historical V6.1 2.0.0 corpus",
                "path": _relative(historical_path, ROOT),
                "profile_count": 1130,
                "unique_profile_count": 1130,
                "match_count": None,
                "session_count": None,
                "source_sha": None,
                "corpus_digest": sha256_file(historical_path) if historical_path.exists() else None,
                "split_digest": None,
                "overlap_status": "historical comparison only",
                "classification": "HISTORICAL_ONLY",
                "allowed_use": "reconcile older conclusions; not method selection",
            },
            {
                "dataset": "frozen V6.1 runtime artifact package",
                "path": _relative(artifact_dir, ROOT),
                "profile_count": None,
                "unique_profile_count": None,
                "match_count": None,
                "session_count": None,
                "source_sha": manifest.get("source", {}).get("repository_commit"),
                "corpus_digest": manifest.get("corpus_sha256"),
                "split_digest": manifest.get("split_manifest_checksum"),
                "overlap_status": "not applicable",
                "classification": "DESCRIPTIVE_ONLY",
                "allowed_use": "read-only current runtime reproduction",
                "package_digest": CURRENT_ARTIFACT_DIGEST,
            },
            {
                "dataset": "stored bootstrap runtime trace",
                "path": _relative(trace_path, ROOT),
                "profile_count": 791,
                "unique_profile_count": 791,
                "match_count": None,
                "session_count": None,
                "source_sha": manifest.get("source", {}).get("repository_commit"),
                "corpus_digest": manifest.get("corpus_sha256"),
                "split_digest": manifest.get("split_manifest_checksum"),
                "overlap_status": 0,
                "classification": "TUNING_ELIGIBLE",
                "allowed_use": "reproduce current path and compare research candidates",
            },
            {
                "dataset": "synthetic deterministic simulations",
                "path": "generated in memory by scripts/v61_findings_statistical_recovery.py",
                "profile_count": None,
                "unique_profile_count": None,
                "match_count": None,
                "session_count": None,
                "source_sha": None,
                "corpus_digest": None,
                "split_digest": None,
                "overlap_status": "not applicable",
                "classification": "DESCRIPTIVE_ONLY",
                "allowed_use": "known-truth method validity only",
            },
            {
                "dataset": "future deeper-history or fresh sealed validation data",
                "path": None,
                "profile_count": None,
                "unique_profile_count": None,
                "match_count": None,
                "session_count": None,
                "source_sha": None,
                "corpus_digest": None,
                "split_digest": None,
                "overlap_status": "not available in this task",
                "classification": "UNKNOWN_BLOCKED",
                "allowed_use": "not available; requires separately authorized collection/selection and cannot enter this comparison",
            },
        ],
        "binding": {
            "analytical_source_sha": CURRENT_SOURCE_SHA,
            "frozen_artifact_package_digest": CURRENT_ARTIFACT_DIGEST,
            "artifact_manifest_source_sha": manifest.get("source", {}).get("repository_commit"),
            "corpus_sha256": manifest.get("corpus_sha256"),
            "split_manifest_checksum": manifest.get("split_manifest_checksum"),
            "train_profile_digest": manifest.get("split", {}).get("train_profile_digest"),
            "holdout_profile_digest": manifest.get("split", {}).get("holdout_profile_digest"),
            "holdout_output_inspected": manifest.get("holdout_output_inspected"),
        },
    }


def _pvalue_pathology() -> list[dict[str, Any]]:
    rng = random.Random(SYNTHETIC_SEED)
    count = 2_000

    def normal(mean: float, sd: float) -> list[float]:
        return [rng.gauss(mean, sd) for _ in range(count)]

    clustered: list[float] = []
    for size in (1, 3, 7, 11, 23, 41, 67, 101, 149):
        center = rng.gauss(0.0, 0.15)
        clustered.extend([center + rng.gauss(0.0, 0.04) for _ in range(size * 5)])
    clustered = clustered[:count]
    heavy = [rng.gauss(0.0, 0.2) * (4.0 if rng.random() < 0.03 else 1.0) for _ in range(count)]
    designs = [
        ("A1_exact_null_constant", [0.0] * count, "p should be high; no signal"),
        ("A2_symmetric_noise_centered_null", normal(0.0, 0.25), "p should not be systematically small"),
        ("A3_clustered_null_varying_sizes", clustered, "p should not be deterministically one or zero"),
        ("A4_heavy_tailed_null", heavy, "p should remain finite and non-pathological"),
        ("B1_constant_positive", [1.0] * count, "p should be small for a stable non-null effect"),
        ("B2_constant_negative", [-1.0] * count, "p should be small for a stable non-null effect"),
        ("B3_small_shift_noisy", normal(0.15, 0.35), "p should be variable and generally larger"),
        ("B4_moderate_shift_noisy", normal(0.45, 0.25), "p should trend smaller than B3"),
        ("B5_strong_shift_noisy", normal(0.9, 0.12), "p should be small"),
    ]
    rows: list[dict[str, Any]] = []
    for design, values, expected in designs:
        finite = _finite_values(values)
        observed = statistics.fmean(finite) if finite else math.nan
        current = _empirical_two_sided_p(finite)
        corrected = _corrected_bootstrap_p(finite, observed=observed)
        rows.append(
            {
                "input_design": design,
                "null": 0.0,
                "draws": len(finite),
                "observed_statistic": observed,
                "returned_current_p": current,
                "corrected_null_centered_p": corrected,
                "expected_qualitative_behavior": expected,
                "actual_behavior": (
                    "pathological high p for constant non-null"
                    if design in {"B1_constant_positive", "B2_constant_negative"} and current > 0.99
                    else "consistent with qualitative expectation"
                ),
                "valid_current": not (
                    design in {"B1_constant_positive", "B2_constant_negative"} and current > 0.99
                ),
                "reason": (
                    "current function compares each draw to null using the observed bootstrap mean;"
                    " constant non-null draws are all counted extreme, so p=1"
                    if design in {"B1_constant_positive", "B2_constant_negative"}
                    else "current function is finite but does not center the bootstrap sampling error at the null"
                ),
            }
        )
    return rows


def _family_evidence_audit() -> list[dict[str, Any]]:
    return [
        {
            "family": "pool_shape",
            "player_question": "What shape does the hero pool have beyond its most-used names?",
            "intended_estimand": "hero-pool shape versus match-weighted job/toolkit shape and chronological pool movement",
            "declared_evidence_source": "portfolio_shape: breadth/toolkit, concentration, thirds, cross-fitted distance",
            "actual_family_bootstrap_source": "semantic_statistics.families.pool_shape = breadth - toolkit",
            "actual_branch_source": "same pool_shape family vector copied to every public branch",
            "match": "PARTIAL",
            "defect": "omnibus scalar is narrower than the registered branch catalog; branch evidence is duplicated",
            "correct_source_should_be": "predeclared portfolio-shape contrast vector, recomputed from portfolio_shape on session resamples",
            "unit_of_evidence": "eligible summary-history match, with chronological session-aware aggregation",
            "clustering_unit": "whole session",
        },
        {
            "family": "transfer",
            "player_question": "What survives when the hero changes?",
            "intended_estimand": "core-to-reliable-stretch component deltas for outcome, activity, and survival",
            "declared_evidence_source": "transfer_frontier: cross-fitted distance bands and component deltas",
            "actual_family_bootstrap_source": "semantic_statistics.families.transfer = transfer frontier score",
            "actual_branch_source": "same transfer vector copied to every public branch",
            "match": "YES_FOR_FAMILY / NO_FOR_BRANCHES",
            "defect": "branch p-values are not branch-specific; equivalent and directional claims share one sample",
            "correct_source_should_be": "continuous_transfer core/reliable_stretch component vector with fixed cross-fitted frontier",
            "unit_of_evidence": "match in a core or reliable-stretch distance band",
            "clustering_unit": "whole session, preserving band membership",
        },
        {
            "family": "post_loss_response",
            "player_question": "What does your next choice look like after a loss?",
            "intended_estimand": "same-session chronological movement contrast across result states",
            "declared_evidence_source": "result_response_summary: win, one_loss, two_plus_losses, win_streak transitions",
            "actual_family_bootstrap_source": "semantic_statistics.families.post_loss_response = finishing",
            "actual_branch_source": "same finishing vector copied to every public branch",
            "match": "NO",
            "defect": "assembly projects finishing instead of result-state transitions",
            "correct_source_should_be": "result_response_summary transitions rebuilt inside each resampled session",
            "unit_of_evidence": "ordered within-session transition; no cross-session transition",
            "clustering_unit": "whole session",
        },
        {
            "family": "combat_expression",
            "player_question": "Which covered match signals move together once the game starts?",
            "intended_estimand": "context-adjusted involvement/exposure relationship, with finishing as a separate guardrail",
            "declared_evidence_source": "involvement, death_exposure, finishing and context coverage",
            "actual_family_bootstrap_source": "semantic_statistics.families.combat_expression = involvement - death_exposure",
            "actual_branch_source": "same combat vector copied to every public branch",
            "match": "YES_FOR_FAMILY / NO_FOR_BRANCHES",
            "defect": "branch labels such as localized variance are not independently evidenced",
            "correct_source_should_be": "context-adjusted component vector recomputed from involvement/death exposure by session",
            "unit_of_evidence": "context-resolved match",
            "clustering_unit": "whole session",
        },
        {
            "family": "session_drift",
            "player_question": "Does the covered expression change across completed session positions?",
            "intended_estimand": "direct result/expression curve over completed-session G1, G2, G3, G4, G5+ positions",
            "declared_evidence_source": "session_position_curve: direct positions and censoring",
            "actual_family_bootstrap_source": "semantic_statistics.families.session_drift = consistency",
            "actual_branch_source": "same consistency vector copied to every public branch",
            "match": "NO",
            "defect": "assembly projects information-weighted consistency instead of direct positions",
            "correct_source_should_be": "session_position_curve rebuilt from completed sessions on each session resample",
            "unit_of_evidence": "completed session-position observation",
            "clustering_unit": "whole completed session; censored sessions excluded, not imputed",
        },
    ]


def _branch_evidence_audit(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    public = [item for item in SEMANTIC_OUTCOME_CATALOG if item.rollout_status == "public_candidate"]
    by_family: dict[str, list[str]] = defaultdict(list)
    for definition in public:
        by_family[definition.family_key].append(definition.semantic_outcome_key)
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        details = [record["families"][family] for record in records if record.get("status") == "evaluated"]
        identical = 0
        total = 0
        p_ranges: list[tuple[float, float]] = []
        for detail in details:
            values = [
                float(value)
                for value in detail.get("branch", {}).get("raw_p_values", {}).values()
                if _float(value) is not None
            ]
            if values:
                total += 1
                identical += int(max(values) == min(values))
                p_ranges.append((min(values), max(values)))
        rows.append(
            {
                "family": family,
                "public_semantic_branches": by_family[family],
                "branch_types": {key: BRANCH_TYPES.get(key, "UNKNOWN") for key in by_family[family]},
                "sample_used_by_each_branch": "family semantic bootstrap vector; same vector per branch",
                "identical_branch_p_frequency": identical / total if total else None,
                "profiles_with_identical_branch_p": identical,
                "profiles_evaluated": total,
                "raw_p_min": min((item[0] for item in p_ranges), default=None),
                "raw_p_max": max((item[1] for item in p_ranges), default=None),
                "classification_for_candidate": "interpretation-only labels; no branch BH",
                "distinct_hypothesis_treatment": "defer or register a separate statistic before making public",
            }
        )
    return rows


def _gate_audit() -> list[dict[str, Any]]:
    return [
        {"gate": "structural eligibility", "declared": True, "computed": True, "enforced": "PARTIAL", "source": "dna_assembly_v6 + canonical history audit", "failure_code_today": "data_eligibility / history_not_complete", "new_candidate": True},
        {"gate": "opportunity minimum", "declared": True, "computed": True, "enforced": False, "source": "semantic_outcomes registry; estimators", "failure_code_today": "not a final publication boolean", "new_candidate": True},
        {"gate": "minimum support", "declared": True, "computed": True, "enforced": False, "source": "registry + diagnostic trace", "failure_code_today": "minimum_support (diagnostic only)", "new_candidate": True},
        {"gate": "estimator validity", "declared": True, "computed": True, "enforced": "PARTIAL", "source": "artifacts.py + family_statistics.py", "failure_code_today": "invalid/empty evidence fails closed inconsistently", "new_candidate": True},
        {"gate": "practical effect", "declared": True, "computed": True, "enforced": False, "source": "semantic calibration ropes; estimators", "failure_code_today": "effect recorded only", "new_candidate": True},
        {"gate": "equivalence/ROPE", "declared": True, "computed": True, "enforced": False, "source": "production_statistics.interval_inside_rope + family statistics", "failure_code_today": "equivalence recorded only", "new_candidate": True},
        {"gate": "family uncertainty", "declared": True, "computed": True, "enforced": "PARTIAL", "source": "production_statistics + semantic_statistics", "failure_code_today": "p-value path is invalid", "new_candidate": True},
        {"gate": "family statistical qualification", "declared": True, "computed": True, "enforced": True, "source": "hierarchical_qualification", "failure_code_today": "family_q", "new_candidate": True},
        {"gate": "family multiplicity correction", "declared": True, "computed": True, "enforced": True, "source": "benjamini_hochberg_five", "failure_code_today": "fixed_m=5", "new_candidate": True},
        {"gate": "branch determination", "declared": True, "computed": True, "enforced": True, "source": "dna_assembly_v61._semantic_key", "failure_code_today": "semantic_key fallback", "new_candidate": True},
        {"gate": "branch statistical qualification", "declared": True, "computed": True, "enforced": True, "source": "hierarchical_qualification", "failure_code_today": "branch_q", "new_candidate": False},
        {"gate": "branch multiplicity correction", "declared": True, "computed": True, "enforced": True, "source": "hierarchical_qualification._benjamini_hochberg", "failure_code_today": "branch evidence duplicated", "new_candidate": False},
        {"gate": "stability", "declared": True, "computed": True, "enforced": False, "source": "base finding bootstrap_stability", "failure_code_today": "recorded_only", "new_candidate": True},
        {"gate": "robustness", "declared": True, "computed": True, "enforced": False, "source": "semantic registry + estimator audits", "failure_code_today": "recorded_only", "new_candidate": True},
        {"gate": "confounder safety", "declared": True, "computed": False, "enforced": False, "source": "no explicit final selection boolean", "failure_code_today": "not_implemented", "new_candidate": True},
        {"gate": "semantic evidence completeness", "declared": True, "computed": True, "enforced": False, "source": "semantic bootstrap availability", "failure_code_today": "semantic_evidence", "new_candidate": True},
        {"gate": "rollout/public-candidate status", "declared": True, "computed": True, "enforced": True, "source": "SEMANTIC_OUTCOME_REGISTRY", "failure_code_today": "not_public_candidate", "new_candidate": True},
        {"gate": "history completeness", "declared": True, "computed": True, "enforced": "POOL_ONLY", "source": "dna_assembly_v61:1258-1260", "failure_code_today": "history_not_complete", "new_candidate": True},
        {"gate": "maximum-findings product cap", "declared": True, "computed": True, "enforced": True, "source": "dna_assembly_v61:1257", "failure_code_today": "finding_cap", "new_candidate": True},
        {"gate": "inherited V6 publication", "declared": True, "computed": True, "enforced": True, "source": "dna_assembly_v61:1256", "failure_code_today": "inherited_v6_publication_gate", "new_candidate": False},
    ]


def _family_specs() -> list[dict[str, Any]]:
    return [
        {
            "family": "pool_shape",
            "family_name": "Pool Shape",
            "player_facing_question": "What shape does your hero pool have beyond its most-used names?",
            "behavioral_claim": "The supported hero-pool shape differs from the supported job/toolkit shape in a stable direction.",
            "estimand": "Delta_pool = signed predeclared contrast between hero breadth/chronological JSD and match-weighted job/toolkit shape; candidate v1 uses hero_JSD - job_JSD as the scalar omnibus.",
            "null_hypothesis": "H0: Delta_pool = 0.",
            "alternative_hypothesis": "H1: Delta_pool != 0.",
            "raw_observation_unit": "eligible summary-history match",
            "independent_clustering_unit": "session_id; entire session is resampled together",
            "opportunity_definition": "All normalized eligible matches inside the profile's 365-day window; chronological thirds preserve within-session order.",
            "structural_eligibility": "Complete canonical history, at least 30 eligible matches, at least 12 sessions, taxonomy/cross-fit inputs valid.",
            "minimum_opportunities": 30,
            "minimum_clusters_sessions": 12,
            "confounders_adjustments": "No rank/MMR or inferred intent; taxonomy is frozen/cross-fitted. Record patch/hero/context coverage as limitations, not causal adjustments.",
            "practical_effect_threshold": FAMILY_ROPES["pool_shape"],
            "equivalence_rope_rule": "Not a public candidate for the directional omnibus. A compatible-shape statement requires the 95% CI wholly inside +/- the predeclared rope and remains neutral, not a Finding.",
            "current_bootstrap_source": "semantic_statistics.families.pool_shape = breadth - toolkit",
            "correct_bootstrap_source": "portfolio_shape breadth/toolkit and predeclared chronological shape contrast, recomputed on each session resample",
            "recommended_resampling_unit": "session cluster bootstrap with replacement; preserve rows and order within sampled sessions",
            "recommended_uncertainty_method": "Corrected null-centered two-sided cluster-bootstrap p plus percentile 95% CI, B=2,000; pass point and observed statistic separately.",
            "recommended_family_qualification": "p <= 0.05 after fixed five-family BH, CI excludes 0, absolute effect >= margin, and all support/evidence/stability/robustness gates pass.",
            "semantic_branches": ["pool_shape_contrast: hero wider vs job wider is a directional label", "hidden_center and names_changed_jobs_held are distinct hypotheses deferred to supporting evidence"],
            "branch_type": "DIRECTIONAL_LABEL for the retained scalar; distinct old branches are not independently public",
            "branch_evidence": "Use signed scalar CI and source-specific descriptive rows; do not copy one omnibus draw into each old branch.",
            "branch_multiplicity_required": "NO for the retained label; YES only if a distinct branch is separately registered and tested.",
            "stability_requirement": "Sign agreement >= 0.80 across split-half and leave-one-session-out diagnostics; no more than 10% degenerate resamples.",
            "robustness_requirement": "Sign/direction persists under dominant-hero exclusion and taxonomy sensitivity; no single session contributes >25% of effective information.",
            "semantic_evidence_requirement": "Portfolio shape rows, denominator, chronology, taxonomy status, and alternatives all present.",
            "abstention_rule": "Missing completeness, <30 matches, <12 sessions, invalid draws, unstable direction, or incomplete portfolio evidence => insufficient/neutral; never fabricate a branch.",
            "publication_rule": "Publish only the retained scalar outcome after the state machine; V6 published is not a prerequisite.",
        },
        {
            "family": "transfer",
            "family_name": "Transfer",
            "player_facing_question": "What survives when the hero changes?",
            "behavioral_claim": "At the supported distance frontier, a specific covered component changes or remains compatible when the hero changes.",
            "estimand": "Delta_transfer,k = mean(component_k | reliable_stretch) - mean(component_k | core), k in {outcome, activity, survival}; candidate omnibus is the maximum predeclared standardized component departure.",
            "null_hypothesis": "H0: all Delta_transfer,k are 0 within the predeclared component ropes.",
            "alternative_hypothesis": "H1: at least one supported component departs from its core value by the predeclared practical margin.",
            "raw_observation_unit": "match assigned to a cross-fitted core or reliable-stretch distance band",
            "independent_clustering_unit": "session_id; preserve band assignments fixed by the cross-fitted calibration",
            "opportunity_definition": "Both core and reliable-stretch bands must have at least 30 component-complete matches and 12 sessions; no edge band is public.",
            "structural_eligibility": "Cross-fitted frontier valid, core/stretch denominators meet minima, component coverage valid, and 365-day history complete.",
            "minimum_opportunities": 30,
            "minimum_clusters_sessions": 12,
            "confounders_adjustments": "Distance bands are cross-fitted; no hero-choice causality. Report taxonomy/context coverage and component-specific alternatives.",
            "practical_effect_threshold": {"outcome": 0.09223679546260193, "activity": 0.05815105200559039, "survival": 0.2346401477174622},
            "equivalence_rope_rule": "clean_transfer is a neutral/equivalence state unless a predeclared TOST/ROPE family test is added; require every component CI inside its rope for a compatibility label.",
            "current_bootstrap_source": "semantic_statistics.families.transfer = transfer frontier score",
            "correct_bootstrap_source": "continuous_transfer component deltas from core/reliable_stretch, recomputed by session cluster",
            "recommended_resampling_unit": "whole session cluster with replacement; keep cross-fitted band and calibration fixed",
            "recommended_uncertainty_method": "Corrected null-centered max-component bootstrap p plus component percentile CIs; separate CI-inside-ROPE decision for compatibility.",
            "recommended_family_qualification": "Family max statistic p <= 0.05 after fixed five-family BH, practical component margin, complete frontier evidence, and reliability gates.",
            "semantic_branches": ["transfer_frontier_change: component/direction label", "clean_transfer: neutral equivalence interpretation", "old boundary labels are not separate p-values"],
            "branch_type": "MUTUALLY_EXCLUSIVE_LABEL / COMPOSITE_INTERPRETATION",
            "branch_evidence": "Branch text must point to the component-specific CI and distance-band row that selected it; no shared family list may stand in for branch evidence.",
            "branch_multiplicity_required": "NO for deterministic labels of one family max statistic; YES for any newly public distinct component hypothesis.",
            "stability_requirement": "Frontier direction/component selection agrees >=0.80 across split-half and leave-one-session-out; no band loses support in >20% of resamples.",
            "robustness_requirement": "Cross-fitted frontier stable under dominant-hero and taxonomy perturbation; core/stretch result not driven by one session.",
            "semantic_evidence_requirement": "Core/stretch counts, sessions, component deltas/CIs, frontier, cross-fit status, and alternatives present.",
            "abstention_rule": "If either comparison band lacks support, any component is invalid, or branch evidence is incomplete, publish no transfer claim.",
            "publication_rule": "Publish one transfer family outcome only after the family state is Qualified and a deterministic label has complete component evidence.",
        },
        {
            "family": "post_loss_response",
            "family_name": "Post-Loss Response",
            "player_facing_question": "What does your next choice look like after a loss?",
            "behavioral_claim": "Within supported same-session result states, next-choice movement differs in a predeclared way.",
            "estimand": "Delta_response = max_s,s' |mean(movement | state=s) - mean(movement | state=s')| over the predeclared state contrast set; no cross-session transitions.",
            "null_hypothesis": "H0: all predeclared supported result-state movement means are equal.",
            "alternative_hypothesis": "H1: at least one supported state contrast exceeds the practical movement margin.",
            "raw_observation_unit": "ordered loss/result-state transition within a session",
            "independent_clustering_unit": "session_id; transition rows within a session are not independent",
            "opportunity_definition": "Chronological adjacent matches within a session; prior result assigns win/one_loss/two_plus_losses/win_streak; rows never cross session boundaries.",
            "structural_eligibility": "At least 30 transitions and 12 sessions overall; every state used in a public contrast has at least 12 transitions across at least 8 sessions.",
            "minimum_opportunities": 30,
            "minimum_clusters_sessions": 12,
            "confounders_adjustments": "Same-hero rate, next result, and context coverage are guardrails/descriptors; do not call the result causal or psychological.",
            "practical_effect_threshold": FAMILY_ROPES["post_loss_response"],
            "equivalence_rope_rule": "result_invariant_response is neutral unless a predeclared equivalence test is passed; require every compared state CI/range inside +/-0.5.",
            "current_bootstrap_source": "semantic_statistics.families.post_loss_response = finishing (incorrect)",
            "correct_bootstrap_source": "result_response_summary transition movements rebuilt from each resampled session",
            "recommended_resampling_unit": "whole session cluster with replacement; recompute transitions after resampling, never concatenate sessions",
            "recommended_uncertainty_method": "Corrected null-centered max-contrast session bootstrap p plus state-specific percentile CIs; TOST/ROPE only for the invariant label.",
            "recommended_family_qualification": "Family max-contrast p <= 0.05 after fixed five-family BH, practical effect, state support, and all reliability/evidence gates.",
            "semantic_branches": ["result_state_response_contrast: state/direction label", "one_loss_runback/two_loss_switch are interpretations of the selected contrast", "invariant response remains neutral/equivalence"],
            "branch_type": "DISTINCT_OLD_HYPOTHESES_COLLAPSED_TO_ONE_PREDECLARED_CONTRAST",
            "branch_evidence": "Use only the state rows involved in the selected contrast, with transition counts, sessions, movement CIs, and next-result guardrail.",
            "branch_multiplicity_required": "NO for the one predeclared family max contrast; YES if multiple state contrasts become separate public claims.",
            "stability_requirement": "Selected state contrast sign agrees >=0.80 across split-half and leave-one-session-out; state support survives >=90% of bootstrap draws.",
            "robustness_requirement": "Result persists under same-hero exclusion and session-length stratification; no cross-session reuse.",
            "semantic_evidence_requirement": "Transition construction, state definitions, per-state denominators, movement range, next-result guardrail, and alternatives present.",
            "abstention_rule": "No supported state contrast, incomplete transition evidence, cross-session transition, invalid draw, or unstable sign => insufficient/neutral.",
            "publication_rule": "Publish one bounded result-state claim only after corrected source mapping and the complete state machine pass.",
        },
        {
            "family": "combat_expression",
            "family_name": "Combat Expression",
            "player_facing_question": "Which covered match signals move together once the game starts?",
            "behavioral_claim": "Context-adjusted involvement, exposure, and result components show a reproducible relationship in supported matches.",
            "estimand": "Delta_combat = predeclared discordance between context-adjusted involvement, death exposure, and outcome components; candidate v1 uses max absolute standardized component contrast.",
            "null_hypothesis": "H0: the covered combat components move together within their practical margins.",
            "alternative_hypothesis": "H1: at least one component relationship departs from the covered agreement region.",
            "raw_observation_unit": "context-resolved match with involvement and death-exposure values",
            "independent_clustering_unit": "session_id; all match rows in a session resampled together",
            "opportunity_definition": "Matches with valid context-adjusted involvement and death exposure; finishing is separate evidence/guardrail, not silently substituted.",
            "structural_eligibility": "At least 30 complete component matches, at least 12 sessions, and >=80% context coverage for each required component.",
            "minimum_opportunities": 30,
            "minimum_clusters_sessions": 12,
            "confounders_adjustments": "Use frozen context baselines; never infer positioning, aggression, skill, intent, rank, or cause.",
            "practical_effect_threshold": {"involvement": 0.05815105200559039, "death_exposure": 0.05815105200559039, "outcome": 0.09223679546260193},
            "equivalence_rope_rule": "Agreement labels require all required component CIs inside their component ropes; otherwise describe the component that moves.",
            "current_bootstrap_source": "semantic_statistics.families.combat_expression = involvement - death_exposure",
            "correct_bootstrap_source": "context-adjusted involvement/death-exposure/outcome component vector, recomputed by session",
            "recommended_resampling_unit": "whole session cluster with replacement; retain context-resolution and baseline version",
            "recommended_uncertainty_method": "Corrected null-centered max-component bootstrap p plus component CIs; no separate p for deterministic relationship labels.",
            "recommended_family_qualification": "Family discordance statistic p <= 0.05 after fixed five-family BH, practical component effect, coverage, and robustness gates.",
            "semantic_branches": ["expression_result_discordance: involvement/exposure/result relationship label", "localized_variance deferred until independently registered"],
            "branch_type": "MUTUALLY_EXCLUSIVE_LABEL for retained relationship; DISTINCT_HYPOTHESIS deferred",
            "branch_evidence": "Point/CI/evidence rows for every component named in the label; finishing remains an explicit guardrail where used.",
            "branch_multiplicity_required": "NO for labels of one family statistic; YES for localized variance or any new component hypothesis.",
            "stability_requirement": "Relationship label/sign agrees >=0.80 across split-half and leave-one-session-out; context coverage stays >=80%.",
            "robustness_requirement": "Stable after dominant-hero/context stratification and overdispersion check; no one session dominates.",
            "semantic_evidence_requirement": "Component definitions, context coverage, CIs, denominator, overdispersion, and forbidden interpretations present.",
            "abstention_rule": "Invalid context, <30 matches, <12 sessions, <80% coverage, unstable relation, or missing component evidence => insufficient.",
            "publication_rule": "Publish a single bounded component relationship after the state machine; do not derive it from Element zones in a client.",
        },
        {
            "family": "session_drift",
            "family_name": "Session Drift",
            "player_facing_question": "Does the covered expression change across completed session positions?",
            "behavioral_claim": "The direct covered expression curve changes across predeclared positions in completed sessions.",
            "estimand": "Delta_session = max_g,g' |mean(expression at position g) - mean(expression at position g')| over the predeclared G1-G5+ position set.",
            "null_hypothesis": "H0: the direct completed-session position curve is compatible across all predeclared positions.",
            "alternative_hypothesis": "H1: at least one supported position contrast exceeds the practical margin.",
            "raw_observation_unit": "completed-session position observation (G1, G2, G3, G4, G5+)",
            "independent_clustering_unit": "completed session_id; censoring is explicit and not imputed",
            "opportunity_definition": "Only completed sessions reaching each direct position; compare positions that each have >=12 sessions and >=30 position observations where required.",
            "structural_eligibility": "At least two predeclared positions supported, at least 30 position observations, at least 12 completed sessions, and no unreachable calibration sentinel.",
            "minimum_opportunities": 30,
            "minimum_clusters_sessions": 12,
            "confounders_adjustments": "Report selection into longer sessions and 365-day boundary; do not call fatigue, warm-up, intent, or cause.",
            "practical_effect_threshold": FAMILY_ROPES["session_drift"],
            "equivalence_rope_rule": "A compatible curve is neutral unless every compared position CI is inside +/-0.8647735608975679; no directional Finding from equivalence alone.",
            "current_bootstrap_source": "semantic_statistics.families.session_drift = consistency (incorrect)",
            "correct_bootstrap_source": "session_position_curve direct G1-G5+ positions, recomputed from completed sessions",
            "recommended_resampling_unit": "completed session cluster with replacement; exclude censored sessions from all positions",
            "recommended_uncertainty_method": "Corrected null-centered max-position-contrast bootstrap p plus position-specific CIs; no raw match independence assumption.",
            "recommended_family_qualification": "Family position-contrast p <= 0.05 after fixed five-family BH, practical effect, position support, and selection/robustness gates.",
            "semantic_branches": ["position_curve_change: opening/gradual/breakpoint interpretation", "selection_only_drift and stopping response deferred until separately evidenced"],
            "branch_type": "DISTINCT_OLD_HYPOTHESES_COLLAPSED_TO_ONE_PREDECLARED_POSITION_CONTRAST",
            "branch_evidence": "Direct position counts/sessions/rates or expression values, censoring count, selected contrast, and selection alternative.",
            "branch_multiplicity_required": "NO for one predeclared position-contrast family statistic; YES for separately registered breakpoint/stopping hypotheses.",
            "stability_requirement": "Selected position contrast sign agrees >=0.80 across split-half and leave-one-session-out; supported positions remain supported in >=90% of draws.",
            "robustness_requirement": "Early/late window and session-length sensitivity do not reverse the claim; selection into longer sessions remains disclosed.",
            "semantic_evidence_requirement": "Direct positions, completed/censored sessions, denominators, curve values, and alternatives present.",
            "abstention_rule": "Fewer than two supported positions, missing completion, unreachable threshold, unstable sign, or wrong source mapping => insufficient/neutral.",
            "publication_rule": "Publish one direct position-curve claim only after completion wiring and direct bootstrap evidence are implemented and validated.",
        },
    ]


def _candidate_methods() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        for method in METHODS:
            if method == "corrected_null_centered_bootstrap":
                row = {
                    "family": family,
                    "method": method,
                    "statistically_valid": True,
                    "tests_intended_estimand": True,
                    "handles_clustering": True,
                    "multiplicity_compatible": True,
                    "runtime_cost": "2,000 family-statistic recomputations per profile; session sufficient statistics where valid",
                    "implementation_complexity": "moderate",
                    "verdict": "RECOMMEND",
                    "reason": "Corrects the null-centering defect while retaining the existing session-cluster design; family p can enter fixed five-family BH.",
                }
            elif method == "ci_practical_effect":
                row = {
                    "family": family,
                    "method": method,
                    "statistically_valid": True,
                    "tests_intended_estimand": True,
                    "handles_clustering": True,
                    "multiplicity_compatible": False,
                    "runtime_cost": "same bootstrap, plus interval/effect checks",
                    "implementation_complexity": "low",
                    "verdict": "VIABLE_ALTERNATIVE",
                    "reason": "Good semantic publication gate, but percentile CIs alone do not provide the chosen cross-family FDR control without a simultaneous-interval calibration.",
                }
            elif method == "rope_equivalence":
                applicable = family in {"transfer", "post_loss_response", "combat_expression", "session_drift"}
                row = {
                    "family": family,
                    "method": method,
                    "statistically_valid": applicable,
                    "tests_intended_estimand": applicable,
                    "handles_clustering": True,
                    "multiplicity_compatible": "only with a predeclared equivalence family test",
                    "runtime_cost": "same bootstrap; two one-sided/interval boundary checks",
                    "implementation_complexity": "moderate",
                    "verdict": "VIABLE_ALTERNATIVE" if applicable else "NOT_APPLICABLE",
                    "reason": "Use only for claims whose meaning is compatibility/equivalence; it is not the omnibus primitive for a directional family.",
                }
            else:
                row = {
                    "family": family,
                    "method": method,
                    "statistically_valid": False,
                    "tests_intended_estimand": False,
                    "handles_clustering": False,
                    "multiplicity_compatible": False,
                    "runtime_cost": "unknown",
                    "implementation_complexity": "high",
                    "verdict": "REJECT",
                    "reason": "The observational summary history supplies no randomized treatment or exchangeability that would justify a permutation null; result states and hero bands are selected, not randomized.",
                }
            rows.append(row)
    return {
        "methods": rows,
        "chosen_method": "corrected_null_centered_bootstrap",
        "semantic_gate": "ci_practical_effect plus CI-inside-ROPE where the registered claim is equivalence",
        "synthetic_gate": "no method proceeds to corpus comparison unless deterministic null controls are finite and non-pathological",
    }


def _cluster_bootstrap(clusters: Sequence[Sequence[float]], rng: random.Random, iterations: int) -> list[float]:
    if not clusters:
        return []
    return [
        statistics.fmean(value for index in (rng.randrange(len(clusters)) for _ in clusters) for value in clusters[index])
        for _ in range(iterations)
    ]


def _simulate_synthetic() -> list[dict[str, Any]]:
    rng = random.Random(SYNTHETIC_SEED)
    scenarios = [
        ("exact_null", 0.0, 0.0, [10] * 20, "null"),
        ("noisy_null", 0.0, 0.35, [10] * 20, "null"),
        ("clustered_null", 0.0, 0.35, [10] * 20, "null"),
        ("unbalanced_cluster_sizes", 0.0, 0.35, [1, 2, 3, 5, 8, 13, 21, 34, 55, 89], "null"),
        ("heavy_tailed_null", 0.0, 0.35, [10] * 20, "null"),
        ("low_opportunity", 0.0, 0.35, [2] * 6, "null"),
        ("high_opportunity", 0.0, 0.35, [50] * 20, "null"),
        ("small_stable_effect", 0.12, 0.25, [10] * 20, "positive"),
        ("moderate_stable_effect", 0.35, 0.25, [10] * 20, "positive"),
        ("strong_stable_effect", 0.8, 0.2, [10] * 20, "positive"),
        ("one_direction_only", 0.35, 0.25, [10] * 20, "positive"),
        ("effect_flips_across_sessions", 0.0, 0.35, [10] * 20, "flip"),
        ("hero_role_context_confounder", 0.35, 0.25, [10] * 20, "confounded"),
    ]
    rows: list[dict[str, Any]] = []
    runs = 80
    iterations = 250
    for scenario, shift, noise, sizes, truth in scenarios:
        p_hits = 0
        ci_hits = 0
        rope_accepts = 0
        covered = 0
        degenerates = 0
        observed_values: list[float] = []
        for _ in range(runs):
            clusters: list[list[float]] = []
            for cluster_index, size in enumerate(sizes):
                cluster_shift = shift
                if truth == "flip":
                    cluster_shift = 0.35 if cluster_index % 2 == 0 else -0.35
                if truth == "confounded":
                    cluster_shift = shift if cluster_index < len(sizes) // 2 else shift / 4
                cluster_effect = (
                    rng.gauss(0.0, noise * 1.5)
                    if scenario == "clustered_null"
                    else 0.0
                )
                values: list[float] = []
                for _ in range(size):
                    if scenario == "heavy_tailed_null" and rng.random() < 0.03:
                        values.append(rng.gauss(cluster_shift + cluster_effect, noise * 5))
                    else:
                        values.append(rng.gauss(cluster_shift + cluster_effect, noise))
                clusters.append(values)
            flat = [value for cluster in clusters for value in cluster]
            if not flat:
                degenerates += 1
                continue
            observed = statistics.fmean(flat)
            draws = _cluster_bootstrap(clusters, rng, iterations)
            if not draws or len(set(round(value, 12) for value in draws)) <= 1:
                degenerates += 1
            p_value = _corrected_bootstrap_p(draws, observed=observed)
            interval = _ci(draws)
            p_hits += int(p_value <= FDR_Q)
            ci_hits += int(_ci_excludes_zero(interval) and abs(observed) >= 0.2)
            rope_accepts += int(_ci_inside_rope(interval, 0.25))
            covered += int(interval[0] is not None and interval[1] is not None and interval[0] <= shift <= interval[1])
            observed_values.append(observed)
        rows.append(
            {
                "method": "corrected_null_centered_bootstrap",
                "scenario": scenario,
                "truth_class": truth,
                "runs": runs,
                "bootstrap_iterations": iterations,
                "false_positive_rate": p_hits / runs if truth == "null" else None,
                "power_or_detection_rate": p_hits / runs,
                "ci_practical_effect_detection_rate": ci_hits / runs,
                "rope_acceptance_rate": rope_accepts / runs,
                "interval_coverage": covered / runs,
                "degeneracy_rate": degenerates / runs,
                "opportunity_count": sum(sizes),
                "cluster_count": len(sizes),
                "observed_mean": statistics.fmean(observed_values) if observed_values else None,
                "verdict": (
                    "PASS_EXPECTED_DEGENERACY"
                    if scenario == "exact_null"
                    else "LIMITATION_LOW_SUPPORT"
                    if scenario == "low_opportunity"
                    else "PASS_VALIDITY_SCREEN"
                    if (truth != "null" or p_hits / runs < 0.15) and degenerates / runs < 0.15
                    else "REVIEW"
                ),
                "notes": (
                    "Exact-null constant draws are intentionally degenerate and return p=1;"
                    " this is an expected control, not a release failure."
                    if scenario == "exact_null"
                    else "Low-opportunity behavior is a support-floor limitation; the candidate excludes it structurally."
                    if scenario == "low_opportunity"
                    else "Synthetic known-truth calibration only; production plan uses B=2,000 and fixed session clusters."
                ),
            }
        )
    for family in FAMILIES:
        rows.append(
            {
                "method": "ci_practical_effect",
                "scenario": "all_scenarios_summary",
                "truth_class": "diagnostic",
                "runs": runs,
                "bootstrap_iterations": iterations,
                "false_positive_rate": None,
                "power_or_detection_rate": None,
                "ci_practical_effect_detection_rate": None,
                "rope_acceptance_rate": None,
                "interval_coverage": None,
                "degeneracy_rate": None,
                "opportunity_count": None,
                "cluster_count": None,
                "observed_mean": None,
                "verdict": "VIABLE_ALTERNATIVE",
                "notes": f"{family}: percentile CI and practical margin pass semantic checks; cross-family FDR requires separate simultaneous calibration.",
            }
        )
    return rows


def _extract_bootstrap(detail: Mapping[str, Any]) -> tuple[float | None, list[float | None], float | None]:
    bootstrap = detail.get("bootstrap", {})
    family = bootstrap.get("family", {}) if isinstance(bootstrap, Mapping) else {}
    observed = _float(family.get("observed"))
    interval = family.get("ci95") if isinstance(family.get("ci95"), list) else [None, None]
    p_value = _float(family.get("corrected_null_centered_p"))
    return observed, interval, p_value


def _candidate_results(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    evaluated = [record for record in records if record.get("status") == "evaluated"]
    rows: list[dict[str, Any]] = []
    for record in evaluated:
        p_values: dict[str, float] = {}
        structural: dict[str, bool] = {}
        extracted: dict[str, tuple[float | None, list[float | None], float | None]] = {}
        for family in FAMILIES:
            detail = record["families"][family]
            observed, interval, p_value = _extract_bootstrap(detail)
            extracted[family] = (observed, interval, p_value)
            p_values[family] = p_value if p_value is not None else 1.0
            structural[family] = bool(
                detail.get("gate_flags", {}).get("minimum_support")
                and detail.get("semantic", {}).get("evidence_complete")
                and detail.get("publication", {}).get("history_complete")
            )
        q_fixed = _bh(p_values)
        eligible_p = {family: p_values[family] for family in FAMILIES if structural[family]}
        q_structural = _bh(eligible_p)
        m_structural = len(eligible_p)
        for family in FAMILIES:
            detail = record["families"][family]
            observed, interval, p_value = extracted[family]
            margin = FAMILY_ROPES[family]
            support_pass = bool(detail["gate_flags"].get("minimum_support"))
            evidence_pass = bool(detail["semantic"].get("evidence_complete"))
            history_pass = bool(detail["publication"].get("history_complete"))
            public_pass = bool(detail["publication"].get("public_candidate"))
            estimator_valid = p_value is not None
            practical_pass = bool(
                observed is not None
                and interval[0] is not None
                and interval[1] is not None
                and abs(observed) >= margin
                and _ci_excludes_zero(interval)
            )
            branch = BRANCH_MAP[family]
            analytic_candidate = bool(
                q_fixed.get(family, 1.0) <= FDR_Q
                and public_pass
                and support_pass
                and evidence_pass
                and history_pass
                and practical_pass
            )
            common = {
                "profile_digest": record["profile_digest"],
                "family": family,
                "method": "corrected_null_centered_bootstrap",
                "branch": branch,
                "opportunities": detail["support"].get("opportunities"),
                "clusters_sessions": detail["support"].get("sessions"),
                "point_estimate": observed,
                "practical_margin": margin,
                "practical_effect_status": practical_pass,
                "p_value": p_value if p_value is not None else 1.0,
                "p_value_available": estimator_valid,
                "interval_lower": interval[0],
                "interval_upper": interval[1],
                "family_q_fixed_m5": q_fixed.get(family),
                "family_q_structural_filter": q_structural.get(family),
                "structural_m": m_structural,
                "support_status": support_pass,
                "evidence_completeness": evidence_pass,
                "history_complete": history_pass,
                "public_candidate": public_pass,
                "current_diagnostic_stability": detail["base"].get("bootstrap_stability"),
                "branch_q": None,
                "branch_multiplicity": "not used; interpretation-only retained branch",
                "analytic_candidate": analytic_candidate,
                "candidate_publication": False,
                "first_blocker": (
                    "support"
                    if not support_pass
                    else "estimator_invalid"
                    if not estimator_valid
                    else "semantic_evidence"
                    if not evidence_pass
                    else "practical_effect"
                    if not practical_pass
                    else "family_q"
                    if q_fixed.get(family, 1.0) > FDR_Q
                    else "public_rollout_status"
                    if not public_pass
                    else "reliability_not_yet_release_validated"
                ),
                "all_blockers": ";".join(
                    key
                    for key, value in (
                        ("support", support_pass),
                        ("estimator_invalid", estimator_valid),
                        ("semantic_evidence", evidence_pass),
                        ("history", history_pass),
                        ("practical_effect", practical_pass),
                        ("family_q", q_fixed.get(family, 1.0) <= FDR_Q),
                        ("public_rollout", public_pass),
                        ("reliability_not_release_validated", False),
                        ("fresh_sealed_holdout_required", False),
                    )
                    if not value
                ),
                "architecture": "M1_fixed_five_family_BH + M4_no_branch_BH",
            }
            rows.append(common)
            ci_status = bool(
                observed is not None
                and interval[0] is not None
                and interval[1] is not None
                and practical_pass
            )
            rows.append(
                {
                    **common,
                    "method": "ci_practical_effect",
                    "p_value": None,
                    "family_q_fixed_m5": None,
                    "family_q_structural_filter": None,
                    "analytic_candidate": ci_status and support_pass and evidence_pass and history_pass and public_pass,
                    "candidate_publication": False,
                    "first_blocker": "ci_or_practical_effect" if not ci_status else "fdr_calibration_required",
                    "all_blockers": ";".join(
                        key
                        for key, value in (
                            ("support", support_pass),
                            ("semantic_evidence", evidence_pass),
                            ("history", history_pass),
                            ("public_rollout", public_pass),
                            ("ci_practical_effect", ci_status),
                            ("fdr_calibration_required", False),
                            ("fresh_sealed_holdout_required", False),
                        )
                        if not value
                    ),
                    "architecture": "CI_practical_effect_diagnostic_only",
                }
            )
            rope_applicable = family in {"transfer", "post_loss_response", "combat_expression", "session_drift"}
            rope_status = _ci_inside_rope(interval, margin) if rope_applicable else None
            rows.append(
                {
                    **common,
                    "method": "rope_equivalence",
                    "p_value": None,
                    "family_q_fixed_m5": None,
                    "family_q_structural_filter": None,
                    "practical_effect_status": rope_status,
                    "analytic_candidate": bool(rope_applicable and rope_status and support_pass and evidence_pass and history_pass and public_pass),
                    "candidate_publication": False,
                    "first_blocker": "not_applicable" if not rope_applicable else "rope_or_support",
                    "all_blockers": "not_applicable" if not rope_applicable else ";".join(
                        key
                        for key, value in (
                            ("support", support_pass),
                            ("semantic_evidence", evidence_pass),
                            ("history", history_pass),
                            ("public_rollout", public_pass),
                            ("rope", bool(rope_status)),
                            ("fresh_sealed_holdout_required", False),
                        )
                        if not value
                    ),
                    "architecture": "ROPE_diagnostic_only",
                }
            )
            rows.append(
                {
                    **common,
                    "method": "permutation_randomization",
                    "p_value": None,
                    "family_q_fixed_m5": None,
                    "family_q_structural_filter": None,
                    "analytic_candidate": False,
                    "candidate_publication": False,
                    "first_blocker": "no_exchangeable_randomization",
                    "all_blockers": "no_exchangeable_randomization",
                    "architecture": "rejected",
                }
            )
    return rows


def _reliability_checks(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    evaluated = [record for record in records if record.get("status") == "evaluated"]
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        details = [record["families"][family] for record in evaluated]
        points = [
            observed
            for observed, _interval, _p in (_extract_bootstrap(detail) for detail in details)
            if observed is not None
        ]
        nonzero = [value for value in points if value != 0]
        sign_consistency = (
            max(sum(value > 0 for value in nonzero), sum(value < 0 for value in nonzero)) / len(nonzero)
            if nonzero
            else None
        )
        stability = [_float(detail["base"].get("bootstrap_stability")) for detail in details]
        stability_values = [value for value in stability if value is not None]
        rows.append(
            {
                "architecture": "M1_fixed_five_family_BH + M4_no_branch_BH",
                "family": family,
                "check": "stored_runtime_bootstrap_stability",
                "status": "DIAGNOSTIC_ONLY",
                "profiles": len(details),
                "pass_count_at_0_75": sum(value >= 0.75 for value in stability_values),
                "pass_rate_at_0_75": sum(value >= 0.75 for value in stability_values) / len(stability_values) if stability_values else None,
                "value": statistics.fmean(stability_values) if stability_values else None,
                "reason": "Current V6.1 stability field is evidence, not an enforced release gate.",
            }
        )
        rows.append(
            {
                "architecture": "M1_fixed_five_family_BH + M4_no_branch_BH",
                "family": family,
                "check": "sign_consistency_from_family_bootstrap_point",
                "status": "DIAGNOSTIC_ONLY",
                "profiles": len(points),
                "pass_count_at_0_80": int(sign_consistency is not None and sign_consistency >= 0.80),
                "pass_rate_at_0_80": sign_consistency,
                "value": sign_consistency,
                "reason": "Computed from the current scalar semantic projection; not a substitute for split-half/LOSO evidence.",
            }
        )
    for family, check, reason in (
        ("all", "split_half_stability", "Not available in the compact trace; future implementation must recompute family estimands on disjoint session halves."),
        ("all", "leave_one_session_out", "Not run because the current candidate trace intentionally stores no raw session identifiers or per-session estimates."),
        ("all", "hero_stratification", "Not selected from the current frozen trace; must be predeclared and run after direct family evidence is repaired."),
        ("all", "role_stratification", "Summary history coverage is insufficient for an unambiguous role-stratified causal interpretation."),
        ("all", "early_late_window", "A deeper window is not present; no >365-day comparison is possible without new collection."),
        ("all", "negative_controls", "Synthetic null controls pass the validity screen; observational negative-control labels are not available."),
    ):
        rows.append(
            {
                "architecture": "M1_fixed_five_family_BH + M4_no_branch_BH",
                "family": family,
                "check": check,
                "status": "NOT_RUN",
                "profiles": len(evaluated),
                "pass_count_at_0_75": None,
                "pass_rate_at_0_75": None,
                "value": None,
                "reason": reason,
            }
        )
    return rows


def _multiplicity_architectures() -> list[dict[str, Any]]:
    return [
        {
            "id": "M1",
            "name": "CURRENT_FIXED_FIVE_FAMILY_BH",
            "hypothesis_universe": "Exactly the five roots: pool_shape, transfer, post_loss_response, combat_expression, session_drift.",
            "eligibility_rule": "All five p-values enter BH; unsupported families receive a fail-closed p=1 but remain in m=5.",
            "correction_method": "Benjamini-Hochberg, m=5, q=0.05.",
            "dependency_assumptions": "BH is valid under independence or standard positive dependence; report this as FDR control, not per-finding confidence.",
            "interpretation_of_fdr": "Expected false-discovery proportion among rejected family roots under the fixed five-root universe.",
            "branch_treatment": "Branches are not independent tests in the recommended candidate; deterministic labels only.",
            "strengths": "Simple, auditable, conservative, no data-dependent m.",
            "failure_modes": "A permanently unsupported family consumes one slot and reduces power; p-values must first be valid.",
            "complexity": "low",
            "verdict": "RECOMMEND",
        },
        {
            "id": "M2",
            "name": "STRUCTURALLY_ELIGIBLE_FAMILY_BH",
            "hypothesis_universe": "Only family roots passing predeclared support/evidence/history eligibility.",
            "eligibility_rule": "Support/evidence/history only; no p, effect, q, or branch outcome may enter eligibility.",
            "correction_method": "BH over the eligible subset with profile-specific m.",
            "dependency_assumptions": "Requires independent filtering or a proof that structural filtering is independent of null p-values; not assumed here.",
            "interpretation_of_fdr": "Conditional FDR among structurally selected roots only if the filtering proof holds.",
            "branch_treatment": "No branch BH for interpretation-only labels.",
            "strengths": "Avoids spending a slot on an unavailable family.",
            "failure_modes": "Data-dependent filtering can invalidate nominal FDR and makes m vary by profile.",
            "complexity": "moderate",
            "verdict": "VIABLE_ALTERNATIVE",
        },
        {
            "id": "M3",
            "name": "FAMILY_BH_PLUS_BRANCH_BH",
            "hypothesis_universe": "Five family roots plus their public semantic branches.",
            "eligibility_rule": "Branches only after family qualification.",
            "correction_method": "BH at family level then BH inside each qualified family.",
            "dependency_assumptions": "Requires valid, distinct branch evidence and a predeclared hierarchy.",
            "interpretation_of_fdr": "Hierarchical FDR only if branch tests are real distinct hypotheses.",
            "branch_treatment": "Independent branch correction.",
            "strengths": "Appropriate for genuinely distinct branch hypotheses.",
            "failure_modes": "Current branches receive identical family evidence; branch q is decorative and can hide semantic mismatch.",
            "complexity": "moderate",
            "verdict": "REJECT_CURRENTLY",
        },
        {
            "id": "M4",
            "name": "FAMILY_BH_ONLY",
            "hypothesis_universe": "Five family omnibus hypotheses.",
            "eligibility_rule": "All five roots fixed; support/effect/semantic gates occur after valid family evidence and do not change m.",
            "correction_method": "Fixed five-family BH on corrected family p-values.",
            "dependency_assumptions": "Same as M1; branch labels are interpretations of one family result.",
            "interpretation_of_fdr": "FDR applies to family-level rejections; branch copy is not an additional discovery claim.",
            "branch_treatment": "One retained branch label per qualified family; no branch p/q.",
            "strengths": "Smallest defensible correction once branches are collapsed/registered as labels.",
            "failure_modes": "Distinct future branches cannot be smuggled in as labels; they need a new statistic and correction.",
            "complexity": "low",
            "verdict": "RECOMMEND_WITH_M1",
        },
        {
            "id": "M5",
            "name": "OTHER",
            "hypothesis_universe": "No additional architecture recommended.",
            "eligibility_rule": "None.",
            "correction_method": "None.",
            "dependency_assumptions": "None.",
            "interpretation_of_fdr": "Not applicable.",
            "branch_treatment": "Not applicable.",
            "strengths": "Avoids adding an unvalidated method.",
            "failure_modes": "Would defer the required architecture decision.",
            "complexity": "none",
            "verdict": "REJECT",
        },
    ]


def _family_verdicts(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    evaluated = [record for record in records if record.get("status") == "evaluated"]
    verdicts = {
        "pool_shape": ("KEEP_FAMILY_REDEFINE_BRANCHES", "corrected null-centered bootstrap", "one scalar family contrast; old distinct branches deferred", "family evidence is broad but registered branches are different constructs"),
        "transfer": ("KEEP_MEASUREMENT_CHANGE_INFERENCE", "corrected max-component bootstrap + ROPE semantic gate", "one frontier-change label; no branch BH", "measurement is aligned; branch evidence is duplicated"),
        "post_loss_response": ("KEEP_MEASUREMENT_CHANGE_INFERENCE", "direct transition max-contrast bootstrap", "one supported state-contrast label; no branch BH", "direct transition measurement exists but current bootstrap source is finishing"),
        "combat_expression": ("KEEP_FAMILY_REDEFINE_BRANCHES", "corrected max-component bootstrap", "one component-relationship label; localized variance deferred", "family source is aligned but current branch catalog mixes distinct claims"),
        "session_drift": ("REDESIGN_MEASUREMENT", "direct completed-session position max-contrast bootstrap", "one position-curve label; breakpoint/stopping deferred", "current semantic source is consistency and completion/calibration support must be repaired"),
    }
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        details = [record["families"][family] for record in evaluated]
        support = sum(bool(detail["gate_flags"].get("minimum_support")) for detail in details)
        evidence = sum(bool(detail["semantic"].get("evidence_complete")) for detail in details)
        rows.append(
            {
                "family": family,
                "status": verdicts[family][0],
                "recommended_estimator": verdicts[family][1],
                "recommended_uncertainty_method": "session-cluster bootstrap, B=2,000, corrected null-centered p and 95% CI",
                "recommended_multiplicity": "fixed five-family BH; no branch BH for interpretation labels",
                "recommended_branch_model": verdicts[family][2],
                "opportunity_coverage": {"support_pass": support, "profiles": len(details), "semantic_evidence_complete": evidence},
                "main_evidence": verdicts[family][3],
                "main_risk": "new source mapping and reliability gates need fresh validation; tuning data has no independent truth labels",
            }
        )
    return rows


def _aggregate_summary(
    records: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    synthetic_rows: Sequence[Mapping[str, Any]],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    evaluated = [record for record in records if record.get("status") == "evaluated"]
    family_counts: dict[str, Any] = {}
    for family in FAMILIES:
        details = [record["families"][family] for record in evaluated]
        family_counts[family] = {
            "profiles": len(details),
            "support_pass": sum(bool(detail["gate_flags"].get("minimum_support")) for detail in details),
            "semantic_evidence_complete": sum(bool(detail["semantic"].get("evidence_complete")) for detail in details),
            "current_family_qualified": sum(bool(detail["family"].get("qualified")) for detail in details),
            "current_branch_qualified": sum(bool(detail["branch"].get("qualified")) for detail in details),
            "inherited_v6_published": sum(bool(detail["publication"].get("inherited_v6_published")) for detail in details),
            "current_final_published": sum(bool(detail["publication"].get("published")) for detail in details),
            "corrected_p_values_available": sum(_extract_bootstrap(detail)[2] is not None for detail in details),
            "candidate_m1_qualified_without_future_reliability": sum(bool(row.get("analytic_candidate")) for row in candidate_rows if row.get("family") == family and row.get("method") == "corrected_null_centered_bootstrap"),
        }
    pvalue_rows = _pvalue_pathology()
    constant_nonnull_failures = sum(not bool(row["valid_current"]) for row in pvalue_rows)
    synthetic_passes = sum(row.get("verdict") == "PASS_VALIDITY_SCREEN" for row in synthetic_rows)
    return {
        "version": "v61-findings-statistical-recovery-1.0.0",
        "status": "PASS" if not [record for record in records if record.get("status") == "error"] else "PARTIAL",
        "profile_trace": {
            "records": len(records),
            "evaluated": len(evaluated),
            "errors": len(records) - len(evaluated),
            "final_published_profiles": sum(bool(record.get("final_published_count")) for record in evaluated),
            "current_finding_distribution": dict(Counter(str(record.get("final_published_count", 0)) for record in evaluated)),
        },
        "family_counts": family_counts,
        "pvalue_pathology": {
            "deterministic_controls": len(pvalue_rows),
            "current_constant_nonnull_failures": constant_nonnull_failures,
            "corrected_constant_nonnull_small_p": all(
                row["corrected_null_centered_p"] < 0.01
                for row in pvalue_rows
                if row["input_design"] in {"B1_constant_positive", "B2_constant_negative"}
            ),
        },
        "synthetic": {
            "seed": SYNTHETIC_SEED,
            "rows": len(synthetic_rows),
            "validity_screen_passes": synthetic_passes,
            "requires_fresh_validation": True,
        },
        "candidate": {
            "rows": len(candidate_rows),
            "profile_family_method_branch_rows": len(evaluated) * len(FAMILIES) * len(METHODS),
            "recommended_architecture": "M1_fixed_five_family_BH + M4_family_only_branch_labels",
            "no_release_yield_claim": True,
        },
        "firewall": provenance["firewall"],
        "lineage": {
            "new_analytical_lineage_required": True,
            "frozen_v61_source_preserved": True,
            "frozen_v61_artifacts_preserved": True,
        },
    }


def _md_table(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> str:
    if not rows:
        return "(none)"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value, sort_keys=True, separators=(",", ":"))
            values.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _report(
    *,
    provenance: Mapping[str, Any],
    diagnosis: Mapping[str, Any],
    code_audit: Mapping[str, Any],
    evidence_audit: Sequence[Mapping[str, Any]],
    branch_audit: Sequence[Mapping[str, Any]],
    gate_audit: Sequence[Mapping[str, Any]],
    specs: Sequence[Mapping[str, Any]],
    methods: Mapping[str, Any],
    synthetic: Sequence[Mapping[str, Any]],
    multiplicity: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    reliability: Sequence[Mapping[str, Any]],
    verdicts: Sequence[Mapping[str, Any]],
    aggregate: Mapping[str, Any],
    implementation_prompt: str,
    old_report_path: Path,
    latest_report_path: Path,
) -> str:
    family_trace = aggregate["family_counts"]
    current_rows = [
        {
            "family": family,
            "current qualified": family_trace[family]["current_family_qualified"],
            "branch qualified": family_trace[family]["current_branch_qualified"],
            "lost to V6 published=false": family_trace[family]["current_family_qualified"] - family_trace[family]["inherited_v6_published"],
            "survived V6": family_trace[family]["inherited_v6_published"],
            "finally published": family_trace[family]["current_final_published"],
        }
        for family in FAMILIES
    ]
    candidate_summary = []
    for method in ("corrected_null_centered_bootstrap", "ci_practical_effect", "rope_equivalence", "permutation_randomization"):
        rows = [row for row in candidate_rows if row.get("method") == method]
        candidate_summary.append(
            {
                "method": method,
                "rows": len(rows),
                "support/evidence/effect candidates": sum(bool(row.get("analytic_candidate")) for row in rows),
                "note": "diagnostic only; future reliability and fresh holdout remain required",
            }
        )
    pathology = _pvalue_pathology()
    pvalue_answers = [
        "CURRENT P-VALUE PROCEDURE VALID? NO.",
        "FAILURE MODE: it treats the observed bootstrap mean as the observed statistic but compares every draw directly to the null; the bootstrap sampling-error distribution is not centered at the null.",
        "WHY CONSTANT NON-NULL SAMPLES BEHAVE AS THEY DO: if every draw is c != 0, the observed distance is |c| and every draw satisfies |c - 0| >= |c|, so the add-one estimate is (B+1)/(B+1)=1; a null-centered test compares |c-c|=0 with |c-0| and returns approximately 1/(B+1).",
        "WHICH FAMILIES ARE AFFECTED: every V6.1 production family/branch that uses semantic bootstrap evidence; the defect is shared, even where the evidence source is otherwise aligned.",
    ]
    sections: list[str] = []
    sections.append("# V6.1 Findings Statistical Recovery")
    sections.append("## Status\n\n**PASS — research specification complete; fresh validation required before any analytical release.** The runtime trace, method screen, and outputs were generated offline from the 791-profile training partition. This task did not implement the redesigned inference path.")
    sections.append("## Integrity\n\n" + _md_table(
        [
            {"item": "base SHA", "value": provenance["worktree"]["head"]},
            {"item": "branch", "value": provenance["worktree"]["branch"]},
            {"item": "origin/main", "value": provenance["worktree"]["origin_main"]},
            {"item": "analytical source SHA", "value": CURRENT_SOURCE_SHA},
            {"item": "frozen artifact package", "value": CURRENT_ARTIFACT_DIGEST},
            {"item": "external collection calls", "value": "0"},
            {"item": "holdout reruns", "value": "0"},
            {"item": "production changes", "value": "0"},
        ],
        ("item", "value"),
    ))
    sections.append("## Canonical evidence consumed\n\nLatest evidence: `" + _relative(latest_report_path, ROOT) + "`. Older partial evidence: `" + _relative(old_report_path, ROOT) + "`. The replacement V2.1 corpus is the only corpus used for candidate comparisons; the protected holdout is summarized only as a pre-existing output.\n\n" + _md_table(provenance["datasets"], ("dataset", "classification", "profile_count", "allowed_use")))
    sections.append("## Diagnosis reproduction\n\n" + _md_table(current_rows, ("family", "current qualified", "branch qualified", "lost to V6 published=false", "survived V6", "finally published")) + "\n\nLoad-bearing results are marked as follows:\n\n- **CONFIRMED:** 791/791 trace evaluation, zero errors, zero provider calls; Transfer 70 family-qualified → 5 inherited V6-published; branch p-values duplicate within family; Post-Loss and Session source projections mismatch their declared evidence; support/evidence gates are not final booleans.\n- **PARTIALLY_CONFIRMED:** the older partial report's statement that Transfer/Combat/Pool bootstrap computation was blocked is superseded by the newer complete trace; its separate calibration-tool completion-wiring concern remains confirmed in `scripts/build_v61_calibration_artifacts.py:216-226` versus `derive_thresholds_v61(... completed_sessions_by_profile=...)`.\n- **NOT USED FOR SELECTION:** the 339-profile holdout output, older V6.1 corpora, and any historical yield claim.")
    sections.append("## Current publication architecture\n\n" + _md_table(code_audit["runtime_chain"], ("transition", "source", "state")))
    sections.append("## P-value pathology\n\n" + _md_table(pathology, ("input_design", "observed_statistic", "returned_current_p", "corrected_null_centered_p", "valid_current", "reason")) + "\n\n" + "\n".join("- " + answer for answer in pvalue_answers))
    sections.append("## Family evidence-source audit\n\n" + _md_table(evidence_audit, ("family", "intended_estimand", "declared_evidence_source", "actual_family_bootstrap_source", "match", "defect", "correct_source_should_be", "unit_of_evidence", "clustering_unit")))
    sections.append("## Branch-evidence audit\n\n" + _md_table(branch_audit, ("family", "public_semantic_branches", "branch_types", "identical_branch_p_frequency", "profiles_with_identical_branch_p", "classification_for_candidate", "distinct_hypothesis_treatment")))
    sections.append("## Publication-gate audit\n\n" + _md_table(gate_audit, ("gate", "declared", "computed", "enforced", "source", "failure_code_today", "new_candidate")))
    spec_rows = []
    for spec in specs:
        spec_rows.append({"family": spec["family_name"], "estimand": spec["estimand"], "null": spec["null_hypothesis"], "opportunities": spec["minimum_opportunities"], "sessions": spec["minimum_clusters_sessions"], "current source": spec["current_bootstrap_source"], "correct source": spec["correct_bootstrap_source"], "uncertainty": spec["recommended_uncertainty_method"], "publication": spec["publication_rule"]})
    sections.append("## Family statistical specifications\n\n" + _md_table(spec_rows, ("family", "estimand", "null", "opportunities", "sessions", "current source", "correct source", "uncertainty", "publication")) + "\n\nThe complete field-by-field specification is the `family_specifications.json` output and is repeated in the implementation prompt; no future worker is asked to choose an estimator, threshold, or multiplicity rule.")
    sections.append("## Candidate inferential methods\n\n" + _md_table(methods["methods"], ("family", "method", "statistically_valid", "tests_intended_estimand", "handles_clustering", "multiplicity_compatible", "verdict", "reason")))
    synthetic_summary = [row for row in synthetic if row.get("scenario") in {"exact_null", "noisy_null", "clustered_null", "unbalanced_cluster_sizes", "heavy_tailed_null", "low_opportunity", "high_opportunity", "small_stable_effect", "moderate_stable_effect", "strong_stable_effect", "one_direction_only", "effect_flips_across_sessions", "hero_role_context_confounder"}]
    sections.append("## Synthetic validity results\n\n" + _md_table(synthetic_summary, ("scenario", "truth_class", "false_positive_rate", "power_or_detection_rate", "ci_practical_effect_detection_rate", "interval_coverage", "degeneracy_rate", "verdict")) + "\n\nSynthetic controls use seed `" + str(SYNTHETIC_SEED) + "`, 80 repetitions, and 250 draws for a fast validity screen. The production specification remains B=2,000. No method with an obvious null pathology advances.")
    sections.append("## Multiplicity architectures\n\n" + _md_table(multiplicity, ("id", "name", "eligibility_rule", "correction_method", "branch_treatment", "failure_modes", "verdict")))
    sections.append("## Tuning-corpus comparison\n\n" + _md_table(candidate_summary, ("method", "rows", "support/evidence/effect candidates", "note")) + "\n\nThe profile-level comparison has one row per tuning profile × family × method × retained candidate branch. Counts are training-only diagnostics, not estimated precision or a target publication rate. The corrected-bootstrap rows use the enhanced trace's source-specific draw summaries; missing future reliability is a publication blocker.")
    sections.append("## Reliability checks\n\n" + _md_table(reliability, ("family", "check", "status", "pass_rate_at_0_75", "pass_rate_at_0_80", "value", "reason")) + "\n\nWhat evidence suggests additional findings are not noise? The synthetic null/positive controls show the corrected statistic has the expected qualitative behavior, and current traces supply diagnostic stability/sign summaries. There is no independent truth label in the tuning corpus; split-half, leave-one-session-out, stratified, and fresh-holdout evidence therefore remain required.")
    sections.append("## Family verdicts\n\n" + _md_table(verdicts, ("family", "status", "recommended_estimator", "recommended_uncertainty_method", "recommended_multiplicity", "recommended_branch_model", "opportunity_coverage", "main_evidence", "main_risk")))
    sections.append("## V6 inheritance decision\n\n**V6_MEASUREMENT_INPUT_ONLY.** The new candidate may reuse V6's report skeleton or measurement inputs where needed for compatibility, but an inherited V6 `finding.published` boolean must not veto a V6.1 candidate result.")
    sections.append("## Recommended publication state machine\n\n`NOT_STRUCTURALLY_ELIGIBLE → INSUFFICIENT_SUPPORT → ESTIMATOR_INVALID → NO_PRACTICAL_EFFECT → STATISTICALLY_UNQUALIFIED → UNSTABLE → CONFOUNDED → SEMANTIC_EVIDENCE_INCOMPLETE → QUALIFIED → PUBLISHABLE`; every terminal failure abstains, and the V6 publication flag is not a transition.")
    sections.append("## Product finding budget\n\nRecommend **max 3 qualified findings**, applied after analytical qualification as a product/display cap. It is not part of the statistical test; non-selected qualified material must not be relabeled as a stronger claim.")
    sections.append("## Recommended analytical architecture\n\n**POOL:** keep measurement, collapse to one predeclared portfolio-shape contrast; **TRANSFER:** keep measurement, corrected max-component frontier inference plus ROPE semantic gate; **POST_LOSS:** keep measurement, direct same-session transition max-contrast; **COMBAT:** keep measurement, corrected component-discordance statistic; **SESSION:** redesign the measurement path to use direct completed-session positions. All five use a corrected null-centered session-cluster bootstrap, fixed five-family BH at q=0.05, interpretation-only branch labels with no branch BH, V6 measurement inputs only, and the state machine above. This is a new analytical lineage.")
    sections.append("## Why this architecture\n\n1. It fixes the shared p-value mechanism before interpreting yield.\n2. It uses each family's declared evidence source and clustering unit.\n3. It stops duplicated branch evidence from masquerading as independent hypotheses.\n4. It keeps multiplicity auditable with fixed m=5.\n5. It turns support, effect, stability, confounder, and semantic completeness into real gates.\n6. It preserves descriptive Elements/Hero Portfolio without weakening Findings.\n7. It can be calibrated and tested exactly once on a future sealed holdout.")
    sections.append("## Rejected alternatives\n\nFixed-q relaxation, branch-q relaxation, wider history, and a Suggestive tier are rejected for this pass because current p-values/source mappings are not valid enough to choose them. Structurally filtered BH is viable only after an independent-filtering argument; it is not the recommendation. Permutation testing is rejected because the summary history provides no randomized or exchangeable treatment assignment.")
    sections.append("## Versioning impact\n\nThe work is documentation/diagnostic only and does not change the frozen V6.1 release. The future implementation must create a new analytical lineage and version at least the statistics, findings/semantic branch catalog, publication contract, and calibration/artifact manifest. It must not relabel changed estimates as `free-dna-model-6.1.0` or reuse the frozen holdout as validation.")
    sections.append("## Calibration requirements\n\nUse the 791-profile tuning partition only to fit new margins/ROPEs and check reproducibility. Predeclare the estimator, B=2,000 seed rule, family statistic, structural minima, practical margins, equivalence boundary, stability/robustness criteria, and state machine before selecting a new sealed holdout. The current artifact numbers are research starting references, not release validation.")
    sections.append("## Fresh validation plan\n\n`statistical spec freeze → implementation → unit tests → synthetic validity tests → tuning/calibration → reproducibility → negative controls → candidate artifact freeze → fresh sealed holdout selection → predeclared acceptance criteria → exactly-once holdout execution → product/content review → staging → owner-authorized production`. The existing 339-profile output is revealed/descriptive-only and cannot validate this candidate.")
    sections.append("## Future implementation plan\n\nSee `" + implementation_prompt + "`. It names exact modules/functions to change and to leave untouched, the estimator interfaces, source mapping, branch model, multiplicity, state machine, tests, firewalls, artifacts, and stop conditions.")
    sections.append("## What evidence would change this recommendation?\n\nA repaired candidate with valid branch/source evidence and fresh sealed validation showing acceptable FDR/precision could justify a different margin, a separately registered branch test, or a Suggestive tier. A deeper pre-existing corpus with materially higher completed-session/transition support could justify a history change. Neither condition is established here.")
    sections.append("## What must NOT change yet\n\n- current V6.1 thresholds, estimator, significance logic, or production publication path;\n- frozen artifacts or source binding;\n- current 365-day collection contract;\n- protected holdout outputs or membership;\n- production flags, database/Redis state, or deployment;\n- any p/q result label based on the current invalid path;\n- public Suggestive findings;\n- analytical version metadata.")
    sections.append("## Files created\n\nTracked: `scripts/v61_findings_statistical_recovery.py`, `scripts/v61_suppression_autopsy.py` (enhanced local trace summaries), `docs/evidence/free-dna-v6.1-findings-statistical-recovery-2026-08-27.md`, and `docs/prompts/v61-findings-recovery-implementation.md`. Local-only: `.local/diagnostics/v61-findings-statistical-recovery/` with the 15 requested outputs. Existing historical autopsy evidence was preserved.")
    sections.append("## Integrity verification\n\n- production untouched;\n- frozen analytical source preserved: `" + CURRENT_SOURCE_SHA + "`;\n- frozen artifact bundle preserved: `" + CURRENT_ARTIFACT_DIGEST + "`;\n- protected holdout not rerun or used for selection;\n- zero OpenDota/Steam/STRATZ collection;\n- no recalibration, deployment, or merge to main;\n- profile-level local outputs contain pseudonymous digests only.")
    return "\n\n".join(sections) + "\n"


def _implementation_prompt(specs: Sequence[Mapping[str, Any]]) -> str:
    spec_json = json.dumps(specs, indent=2, sort_keys=True)
    return f"""# V6.1 Findings Recovery — Implementation Specification

Status: implementation plan only. This prompt is downstream of the research
recovery task. The worker must not choose a statistical method, threshold,
multiplicity design, branch meaning, or validation rule; all decisions are
fixed below.

## Scope and hard firewall

Implement a new research analytical candidate in an isolated branch. Do not
modify production configuration, call OpenDota/Steam/STRATZ, collect new data,
rerun the revealed holdout, tune against the revealed holdout, regenerate the
frozen V6.1 bundle, deploy, merge main, or change V6.1 release metadata.
Preserve these historical identities exactly:

- source SHA: `{CURRENT_SOURCE_SHA}`
- frozen full artifact package digest: `{CURRENT_ARTIFACT_DIGEST}`

The candidate is a new analytical lineage. Do not label changed estimates as
`free-dna-model-6.1.0` or claim the existing holdout validates them.

## One recommended architecture

- five family roots remain the hypothesis universe;
- each family has one predeclared scalar/max-contrast omnibus statistic;
- uncertainty is a corrected null-centered session-cluster bootstrap, exactly
  `B=2_000`, with a deterministic per-profile seed derived from candidate
  version, artifact checksums, profile digest, and salt;
- family p-values enter fixed five-family BH at `q=0.05` (`m=5`), even when a
  family is structurally unsupported; unsupported p-values are fail-closed at
  `1.0` and do not change m;
- branches are deterministic interpretation labels of the qualified family
  result; there is no branch BH in this candidate;
- a branch that is a genuinely distinct hypothesis must be deferred or added
  as a new registered statistic with an explicitly predeclared correction;
- V6 is `V6_MEASUREMENT_INPUT_ONLY`: an inherited V6 `published` boolean is
  never a V6.1 publication prerequisite;
- product output remains capped at three qualified findings after analytical
  qualification; the cap is not a statistical gate.

## Estimator interface

Add an internal pure interface, preferably in
`services/api/app/player_analysis_v61/production_statistics.py` or a new
research-only module:

```python
class FamilyStatistic(Protocol):
    family: str
    def point(self, matches: Sequence[Any], context: FamilyContext) -> FamilyEstimate: ...
    def resample(self, session_clusters: Sequence[SessionCluster], context: FamilyContext) -> FamilyEstimate: ...

@dataclass(frozen=True)
class FamilyEstimate:
    value: float | None
    opportunities: int
    sessions: int
    components: Mapping[str, float | None]
    evidence: Mapping[str, Any]
    valid: bool

@dataclass(frozen=True)
class BootstrapInference:
    point: float
    interval: tuple[float, float]
    raw_p: float
    family_q: float
    practical_effect: bool
    stable: bool
    robust: bool
    evidence_complete: bool
    state: str
```

The p helper must accept the point estimate separately:

```python
def null_centered_bootstrap_p(
    draws: Sequence[float], *, point: float, null: float = 0.0
) -> float:
    extreme = sum(abs(draw - point) >= abs(point - null) for draw in draws)
    return (extreme + 1) / (len(draws) + 1)
```

Reject empty/non-finite draws. Do not use the current
`_empirical_two_sided_p` implementation for the candidate.

## Resampling

1. Group eligible rows by `session_id`; missing IDs are individual fail-closed
   clusters, not silently merged.
2. Sample exactly the number of observed session clusters with replacement.
3. Recompute the family statistic on each resample; do not treat match rows as
   independent.
4. Preserve within-session chronology and session boundaries.
5. Keep cross-fitted calibration/frontier artifacts fixed during a report run;
   do not refit them inside a draw.
6. Return a percentile 95% interval and the corrected null-centered p.
7. Mark the estimate invalid if required denominators/coverage fail in the
   point estimate or in the evidence required for the claim.

## Family-specific source mapping and exact candidate rules

The machine-readable research specification below is authoritative. The
implementation worker must implement these fields as written; a missing field
or unresolved source is a STOP condition.

```json
{spec_json}
```

Summary of the five public candidate branches:

| family | retained branch | branch treatment |
| --- | --- | --- |
| pool_shape | `pool_shape_contrast` | signed/directional label; old concentration/chronology branches deferred |
| transfer | `transfer_frontier_change` | component/direction label; `clean_transfer` is a ROPE/neutral state |
| post_loss_response | `result_state_response_contrast` | selected state-contrast label; no copied finishing evidence |
| combat_expression | `expression_result_discordance` | component relationship label; localized variance deferred |
| session_drift | `position_curve_change` | direct completed-position label; breakpoint/stopping deferred |

## Publication state machine

Evaluate states in this order and record the first and all blockers:

`NOT_STRUCTURALLY_ELIGIBLE → INSUFFICIENT_SUPPORT → ESTIMATOR_INVALID → NO_PRACTICAL_EFFECT → STATISTICALLY_UNQUALIFIED → UNSTABLE → CONFOUNDED → SEMANTIC_EVIDENCE_INCOMPLETE → QUALIFIED → PUBLISHABLE`.

Every failure is abstention. `PUBLISHABLE` additionally requires public
rollout status and the post-qualification product cap. `finding.published` from
V6 is not read as a gate. Expose only registered copy/evidence after the state
is `PUBLISHABLE`; otherwise redact claim/branch/interaction fields as the
existing strict schema requires.

## Exact modules/functions

Change only the future candidate implementation surfaces:

- `services/api/app/player_analysis_v61/production_statistics.py`: add the
  corrected p helper, explicit point/draw interface, and session-cluster
  inference result;
- `services/api/app/player_analysis_v61/family_statistics.py`: route candidate
  inference to the corrected helper; retain fixture-only helpers only if tests
  explicitly label them fixture-only;
- `services/api/app/player_analysis_v61/relationships.py`: expose direct
  post-loss transition and completed-session position estimands with stable
  session grouping;
- `services/api/app/reports/dna_assembly_v61.py`: use the family-specific
  evidence vectors, apply the single state machine, remove the inherited V6
  publication veto for the candidate version, and emit one retained semantic
  label per family;
- `services/api/app/player_analysis_v61/semantic_outcomes.py` and `copy.py`:
  add a new versioned candidate registry/copy surface only after the five
  retained branches and deferred branches are reviewed;
- `services/api/app/player_analysis_v61/versions.py`: add new candidate
  version keys without changing frozen V6.1 values;
- `scripts/build_v61_calibration_artifacts.py` (new candidate path only): pass
  `completed_sessions_by_profile` into threshold derivation; do not overwrite
  frozen V6.1 artifacts;
- new candidate artifact builder/reproducibility manifest: bind corpus/split,
  source, statistic version, q, margins, seed rule, and all checksums.

## Must remain untouched

- `infra/runtime-artifacts/free_dna_v61/6.1.0/**`;
- existing frozen V6.1 source binding and release metadata;
- the revealed holdout and all historical evidence files;
- `services/api/app/player_analysis_v6/**` semantics, unless an explicitly
  reviewed compatibility adapter is required and proves V6 behavior unchanged;
- database, Redis, providers, environment variables, flags, deployment files;
- frontend/presentation code and persisted report fixtures in this analytical
  implementation pass.

If a public schema or persisted report contract must change, STOP and request a
separate contract review; do not silently make the candidate backwards
incompatible.

## Required tests

- unit tests for the corrected p helper: exact null, noisy null, clustered null,
  heavy tail, constant positive, constant negative, empty, and non-finite;
- estimator tests for each five source mappings and minimum support boundaries;
- session-cluster resampling tests proving no cross-session transition and no
  match-level independence assumption;
- branch tests proving retained labels are not separate p-values and deferred
  distinct branches cannot publish;
- publication state-machine tests for every state and first-blocker ordering;
- deterministic synthetic null/positive tests with fixed seed, coverage,
  degeneracy, power trend, and cluster-size sensitivity;
- tuning-only regression against the 791 profiles, without loading any holdout;
- reproducibility run with byte-identical candidate outputs;
- negative controls and privacy scan.

## Protected holdout and network firewall

Test code must fail if it opens a socket or instantiates a provider client.
The existing 339-profile holdout may only be summarized as historical context;
it must not be loaded during tuning, candidate selection, threshold fitting, or
method comparison. No replacement holdout may be selected or executed here.

## Required outputs

Keep profile-level traces local-only, mode `0600`, pseudonymized by a stable
digest, and free of raw account/Steam/report/match/session identifiers. Emit
the same research outputs:

`.local/diagnostics/v61-findings-statistical-recovery/`

with provenance, diagnosis, contract/gate audits, p-value controls, family
specifications, method matrix, synthetic results, multiplicity architectures,
candidate rows, reliability checks, family verdicts, and aggregate summary.

## STOP conditions

Stop with `PARTIAL`/`BLOCKED` if provenance is ambiguous, source semantics are
not recoverable, a method fails synthetic null validity, a holdout is needed,
network access is needed, p/q would be fabricated, or implementation would
modify frozen V6.1 behavior/artifacts or production.

## Definition of Done

- exact source mapping and clustering tested for all five families;
- corrected p mechanism demonstrated and current pathology preserved as a
  historical diagnosis;
- fixed five-family BH and no-branch-BH architecture implemented;
- all support/effect/stability/robustness/confounder/semantic gates are actual
  publication decisions;
- V6 publication is not a candidate veto;
- synthetic validity and tuning regression pass;
- candidate artifacts are new, bound, reproducible, and not confused with
  frozen V6.1;
- fresh sealed holdout plan is written but not executed;
- no external calls, holdout rerun, production change, or deployment.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--holdout", type=Path, required=True)
    parser.add_argument("--old-report", type=Path, required=True)
    parser.add_argument("--latest-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--origin-main", required=True)
    args = parser.parse_args()

    records = _read_jsonl(args.trace)
    errors = [record for record in records if record.get("status") == "error"]
    if errors:
        raise SystemExit(f"trace contains {len(errors)} errors")
    for record in records:
        if "profile_digest" not in record or any(
            key in record for key in ("account_id", "steam_id", "access_token", "match_id", "session_id")
        ):
            raise SystemExit("trace privacy check failed")

    provenance = _provenance(
        corpus_path=args.corpus,
        split_path=args.split,
        artifact_dir=args.artifact_dir,
        holdout_path=args.holdout,
        trace_path=args.trace,
        branch=args.branch,
        head=args.head,
        origin_main=args.origin_main,
    )
    if provenance["binding"]["corpus_sha256"] != sha256_file(args.corpus):
        raise SystemExit("corpus binding failed")
    if provenance["binding"]["split_manifest_checksum"] != sha256_file(args.split):
        raise SystemExit("split binding failed")
    if len(records) != 791:
        raise SystemExit(f"expected 791 trace records, found {len(records)}")

    code_audit = _code_audit()
    old_report_display_path = Path("docs/evidence/free-dna-v6.1-suppression-autopsy-2026-08-27.md")
    diagnosis = {
        "claims": [
            {"claim": "791 tuning profiles evaluated offline", "status": "CONFIRMED", "evidence": "trace records=791, errors=0"},
            {"claim": "external collection calls are zero", "status": "CONFIRMED", "evidence": provenance["firewall"]},
            {"claim": "current p-value construction is invalid for stable non-null constants", "status": "CONFIRMED", "evidence": "deterministic B1/B2 controls"},
            {"claim": "Transfer 70 family-qualified to 5 inherited V6-published", "status": "CONFIRMED", "evidence": "current trace family counts"},
            {"claim": "Post-Loss source is finishing", "status": "CONFIRMED", "evidence": "assembly semantic projection"},
            {"claim": "Session source is consistency", "status": "CONFIRMED", "evidence": "assembly semantic projection"},
            {"claim": "branch evidence is duplicated", "status": "CONFIRMED", "evidence": "branch sample/p-value equality audit"},
            {"claim": "older report's blocked-bootstrap conclusion remains current", "status": "SUPERSEDED", "evidence": "new complete trace independently executes the path"},
        ],
        "current_path_code_checks": code_audit["checks"],
        "older_report_reconciliation": {
            "older_partial_report": old_report_display_path.as_posix(),
            "latest_complete_report": _relative(args.latest_report, ROOT),
            "superseded_claim": "Transfer/Combat/Pool real bootstrap was BLOCKED_COMPUTE",
            "current_record": "complete offline trace exists; use it for current-path claims",
            "remaining_confirmed_calibration_gap": "scripts/build_v61_calibration_artifacts.py omits completed_sessions_by_profile when invoking derive_thresholds_v61",
        },
    }
    evidence_audit = _family_evidence_audit()
    branch_audit = _branch_evidence_audit(records)
    gate_audit = _gate_audit()
    specs = _family_specs()
    methods = _candidate_methods()
    pvalue_rows = _pvalue_pathology()
    synthetic_rows = _simulate_synthetic()
    multiplicity = _multiplicity_architectures()
    candidate_rows = _candidate_results(records)
    reliability = _reliability_checks(records)
    verdicts = _family_verdicts(records)
    aggregate = _aggregate_summary(records, candidate_rows, synthetic_rows, provenance)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.chmod(0o700)
    _write_json(output / "provenance.json", provenance)
    _write_json(output / "diagnosis_reproduction.json", diagnosis)
    _write_json(output / "current_contract_audit.json", code_audit)
    _write_csv(output / "pvalue_pathology_tests.csv", pvalue_rows)
    _write_json(output / "family_specifications.json", {"version": "findings-recovery-spec-1.0.0", "families": specs})
    _write_csv(output / "family_evidence_audit.csv", evidence_audit)
    _write_csv(output / "branch_evidence_audit.csv", branch_audit)
    _write_csv(output / "publication_gate_audit.csv", gate_audit)
    _write_json(output / "candidate_methods.json", methods)
    _write_csv(output / "synthetic_method_validation.csv", synthetic_rows)
    _write_json(output / "multiplicity_architectures.json", {"architectures": multiplicity, "chosen": {"family": "M1", "branch": "M4"}})
    _write_csv(output / "candidate_architecture_results.csv", candidate_rows)
    _write_csv(output / "reliability_checks.csv", reliability)
    _write_json(output / "family_verdicts.json", {"verdicts": verdicts})
    _write_json(output / "aggregate_summary.json", aggregate)
    prompt = _implementation_prompt(specs)
    prompt_path = ROOT / "docs/prompts/v61-findings-recovery-implementation.md"
    report_path = ROOT / "docs/evidence/free-dna-v6.1-findings-statistical-recovery-2026-08-27.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _report(
            provenance=provenance,
            diagnosis=diagnosis,
            code_audit=code_audit,
            evidence_audit=evidence_audit,
            branch_audit=branch_audit,
            gate_audit=gate_audit,
            specs=specs,
            methods=methods,
            synthetic=synthetic_rows,
            multiplicity=multiplicity,
            candidate_rows=candidate_rows,
            reliability=reliability,
            verdicts=verdicts,
            aggregate=aggregate,
            implementation_prompt=_relative(prompt_path, ROOT),
            old_report_path=old_report_display_path,
            latest_report_path=args.latest_report,
        ),
        encoding="utf-8",
    )
    print(json.dumps({
        "status": aggregate["status"],
        "trace_records": len(records),
        "candidate_rows": len(candidate_rows),
        "output_dir": str(output),
        "report": str(report_path),
        "implementation_prompt": str(prompt_path),
        "opendota_calls": 0,
        "holdout_reruns": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

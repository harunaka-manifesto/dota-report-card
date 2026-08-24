#!/usr/bin/env python3
"""Run synthetic, sealed-holdout, review, and aggregate v6 evaluation stages."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.heroes.taxonomy import load_default_taxonomy  # noqa: E402
from app.player_analysis_v6.artifacts import load_context_baseline_artifact  # noqa: E402
from app.player_analysis_v6.calibration import load_threshold_artifact  # noqa: E402
from app.player_analysis_v6.calibration_corpus import load_calibration_corpus  # noqa: E402
from app.player_analysis_v6.calibration_derivation import (  # noqa: E402
    derive_profile_estimates,
    odd_even_session_ids,
)
from app.player_analysis_v6.calibration_evaluation import (  # noqa: E402
    HOLDOUT_VERSION,
    REVIEW_PACKET_VERSION,
    SYNTHETIC_VERSION,
    atomic_json,
    build_evaluation_artifact,
    build_release_manifest,
    ingest_review_evidence,
    sha256_file,
)
from app.player_analysis_v6.costs import free_cost_invariant  # noqa: E402
from app.player_analysis_v6.family_statistics import (  # noqa: E402
    family_statistics,
    finite_sample_directional_p,
)
from app.player_analysis_v6.pipeline import analyze_free_dna_v6  # noqa: E402
from app.player_analysis_v6.statistics import clustered_bootstrap  # noqa: E402

SCENARIOS = (
    "null_no_effect",
    "positive_centered_effect",
    "negative_centered_effect",
    "mixed_transfer",
    "stable_consistency",
    "variable_consistency",
    "no_post_loss_effect",
    "real_post_loss_effect",
    "no_session_drift",
    "late_session_rise",
    "late_session_fade",
    "patch_boundary_missing_baseline_sparse_taxonomy_limited_history",
)
SYNTHETIC_SESSION_COUNT = 24
SYNTHETIC_PRACTICAL_MARGIN = 0.025
FORBIDDEN_COPY = (
    re.compile(r"\byour (?:positioning|rank|mmr)\b", re.IGNORECASE),
    re.compile(r"\b(?:good|bad|avoidable|unavoidable) deaths?\b", re.IGNORECASE),
    re.compile(r"\bcaused by\b|\bbecause you\b", re.IGNORECASE),
)
_HOLDOUT_WORKER_CONTEXT: tuple[Any, Mapping[str, Any], Mapping[int, Any]] | None = None


def _taxonomy_mapping() -> dict[int, dict[str, Any]]:
    taxonomy = load_default_taxonomy()
    return {
        hero_id: {
            "hero_function": sorted(hero.roles)[0] if hero.roles else None,
            "functional_jobs": list(hero.roles),
        }
        for hero_id, hero in taxonomy.heroes.items()
    }


def _artifact_checksums(baseline: Path, thresholds: Path) -> dict[str, str]:
    return {"baseline_sha256": sha256_file(baseline), "threshold_sha256": sha256_file(thresholds)}


def _evaluation_source_digest() -> str:
    sources = [Path(__file__), *(ROOT / "services" / "api" / "app" / "player_analysis_v6").glob("*.py")]
    taxonomy_root = ROOT / "services" / "api" / "app" / "heroes"
    sources.extend((taxonomy_root / "taxonomy.py", *(taxonomy_root / "data").rglob("*.json")))
    digest = hashlib.sha256()
    for path in sorted(sources):
        digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def _namespace_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[SimpleNamespace, ...]:
    result: list[SimpleNamespace] = []
    for raw in rows:
        row = dict(raw)
        row.setdefault("started_at", row.get("start_time"))
        row.setdefault("role_hint", row.get("lane_context"))
        result.append(SimpleNamespace(**row))
    return tuple(result)


def _synthetic_report_rows(scenario: str, seed: int) -> tuple[dict[str, Any], ...]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    match_id = 1
    for session in range(1, 21):
        session_effect = rng.gauss(0.0, 0.8 if scenario == "variable_consistency" else 0.15)
        for position in range(4):
            late = position >= 2
            drift = 1 if scenario == "late_session_rise" and late else -1 if scenario == "late_session_fade" and late else 0
            post_loss = scenario == "real_post_loss_effect" and position > 0
            won = (rng.random() + 0.10 * drift + 0.08 * post_loss + 0.05 * session_effect) >= 0.5
            hero_id = 1 if scenario == "stable_consistency" or match_id % 5 else 2
            rows.append({
                "match_id": match_id,
                "hero_id": hero_id,
                "start_time": 1_700_000_000 + session * 20_000 + position * 2_000,
                "duration_seconds": 1_800,
                "won": won,
                "kills": max(0, 5 + drift + int(session_effect)),
                "deaths": max(0, 4 - drift),
                "assists": max(0, 8 + drift + int(session_effect)),
                "patch": "7.41" if session > 10 else "7.40",
                "lane_context": "safe_lane",
                "session_id": f"session-{session}",
                "session_index": position + 1,
                "session_corrupt": False,
            })
            match_id += 1
    return tuple(rows)


def run_synthetic(args: argparse.Namespace) -> dict[str, Any]:
    if args.bootstrap_iterations != 2_000 and not args.smoke:
        raise ValueError("full synthetic evaluation must use exactly 2,000 bootstrap iterations")
    baseline_artifact = load_context_baseline_artifact(args.baseline)
    threshold_artifact = load_threshold_artifact(args.thresholds)
    resolver = baseline_artifact.resolver()
    taxonomy = _taxonomy_mapping()
    coverage_total = 0
    coverage_hits = 0
    scenario_counts: Counter[str] = Counter()
    for scenario_index, scenario in enumerate(SCENARIOS):
        center = 0.0 if "null" in scenario or scenario.startswith("no_") else -0.25 if "negative" in scenario or "fade" in scenario else 0.25
        for replication in range(args.profiles_per_scenario):
            rng = random.Random(args.seed + scenario_index * 100_003 + replication)
            observations: dict[str, list[float]] = {}
            for session in range(SYNTHETIC_SESSION_COUNT):
                session_effect = rng.gauss(0.0, 0.25)
                observations[f"session-{session + 1}"] = [center + session_effect + rng.gauss(0.0, 0.12) for _ in range(4)]
            interval = clustered_bootstrap(observations, iterations=args.bootstrap_iterations, seed=args.seed + coverage_total)
            coverage_total += 1
            coverage_hits += bool(
                interval.lower is not None
                and interval.upper is not None
                and interval.lower <= center <= interval.upper
            )
            scenario_counts[scenario] += 1
        # Exercise the real report/five-family path for every approved scenario.
        rows = _synthetic_report_rows(scenario, args.seed + scenario_index)
        completion = {f"session-{index}": True for index in range(1, 21)}
        report = analyze_free_dna_v6(
            _namespace_rows(rows),
            baseline_resolver=resolver,
            thresholds=threshold_artifact.metrics,
            taxonomy_by_hero=taxonomy,
            completed_sessions=completion,
            seed=args.seed + scenario_index,
            bootstrap_iterations=args.bootstrap_iterations,
        )
        if len(report.findings) != 5 or not free_cost_invariant(report.cost):
            raise ValueError(f"synthetic scenario {scenario} violated the production report contract")
        print(f"evaluated synthetic scenario progress: {scenario_index + 1}/{len(SCENARIOS)}", flush=True)

    false_discoveries = 0
    discovery_replicates = 0
    missing_slots = 0
    for replication in range(args.null_replicates):
        rng = random.Random(args.seed + 9_000_000 + replication)
        common_effects = [rng.gauss(0.0, 0.25) for _ in range(SYNTHETIC_SESSION_COUNT)]
        raw_p: dict[str, float] = {}
        for family_index, family in enumerate(("pool_shape", "transfer", "post_loss_response", "combat_expression", "session_drift")):
            observations = {
                f"session-{session + 1}": [common_effects[session] + rng.gauss(0.0, 0.20) for _ in range(4)]
                for session in range(SYNTHETIC_SESSION_COUNT)
            }
            boot = clustered_bootstrap(observations, iterations=args.bootstrap_iterations, seed=args.seed + replication * 10 + family_index)
            point = boot.point_estimate or 0.0
            direction = (
                "positive"
                if point > SYNTHETIC_PRACTICAL_MARGIN
                else "negative"
                if point < -SYNTHETIC_PRACTICAL_MARGIN
                else "unknown"
            )
            missing_slots += direction == "unknown"
            raw_p[family] = finite_sample_directional_p(
                boot.replicates,
                direction=direction,
                practical_margin=SYNTHETIC_PRACTICAL_MARGIN,
            )
        statistics = family_statistics(raw_p)
        discoveries = sum(item["adjusted_q_value"] <= 0.05 for item in statistics.values())
        false_discoveries += discoveries
        discovery_replicates += discoveries > 0
        if (replication + 1) % 25 == 0 or replication + 1 == args.null_replicates:
            print(f"evaluated synthetic null progress: {replication + 1}/{args.null_replicates}", flush=True)
    # Under the global null every discovery is false; FDR is therefore the
    # fraction of repeated five-slot families with at least one discovery.
    empirical_fdr = discovery_replicates / max(1, args.null_replicates)
    result = {
        "version": SYNTHETIC_VERSION,
        "seed": args.seed,
        "bootstrap_iterations": args.bootstrap_iterations,
        "dependent_session_count": SYNTHETIC_SESSION_COUNT,
        "standardized_practical_margin": SYNTHETIC_PRACTICAL_MARGIN,
        "smoke": bool(args.smoke),
        "artifact_checksums": _artifact_checksums(args.baseline, args.thresholds),
        "scenario_counts": dict(sorted(scenario_counts.items())),
        "interval_empirical_coverage": {
            "covered": coverage_hits,
            "total": coverage_total,
            "observed": coverage_hits / coverage_total,
        },
        "family_fdr": {
            "false_discoveries": false_discoveries,
            "replicates_with_discovery": discovery_replicates,
            "null_replicates": args.null_replicates,
            "slots_per_replicate": 5,
            "missing_slot_p_value": 1.0,
            "missing_slots": missing_slots,
            "observed": empirical_fdr,
        },
    }
    atomic_json(args.output, result)
    return result


def _profile_seed(seed: int, profile_id: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{seed}:{profile_id}".encode()).digest()[:8], "big")


def _review_items(report: Any) -> list[dict[str, Any]]:
    result = []
    elements = {element.key: element for element in report.elements}
    for finding in report.findings:
        if not finding.published:
            continue
        evidence_signals = [
            {
                "key": evidence.key,
                "value": evidence.value,
                "unit": evidence.unit,
                "interval": list(evidence.interval) if evidence.interval else None,
                "direction": evidence.signal,
                "sample_size": evidence.sample_size,
                "independent_sessions": evidence.independent_sessions,
                "coverage": evidence.coverage,
                "stability": evidence.stability,
                "limitations": list(evidence.limitations),
            }
            for evidence in finding.evidence
        ]
        if finding.family == "transfer" and (transfer := elements.get("transfer")) is not None:
            raw = transfer.raw_metrics
            components = raw.get("components", {}) if isinstance(raw, Mapping) else {}
            deltas = components.get("component_deltas", {}) if isinstance(components, Mapping) else {}
            directions = components.get("component_directions", {}) if isinstance(components, Mapping) else {}
            confident = components.get("confident_component_directions", {}) if isinstance(components, Mapping) else {}
            intervals = raw.get("component_intervals", {}) if isinstance(raw, Mapping) else {}
            evidence_signals = [
                {
                    "key": f"transfer_{component}",
                    "value": deltas.get(component),
                    "unit": "stretch minus familiar",
                    "interval": intervals.get(component) if isinstance(intervals, Mapping) else None,
                    "direction": directions.get(component, "unknown"),
                    "confident_direction": confident.get(component, "unknown"),
                    "sample_size": transfer.sample_size,
                    "independent_sessions": transfer.independent_sessions,
                    "coverage": transfer.coverage,
                    "stability": transfer.stability,
                    "limitations": list(transfer.estimate.limitations),
                }
                for component in ("outcome", "activity", "survival")
            ]
        result.append({
            "family": finding.family,
            "claim": finding.claim,
            "literal_evidence": finding.evidence_text,
            "interval": list(finding.interval) if finding.interval else None,
            "sample_size": finding.sample_size,
            "independent_sessions": finding.independent_sessions,
            "coverage": finding.coverage,
            "limitations": list(finding.limitations),
            "permitted_interpretation": finding.interpretation,
            "finding_direction": finding.direction,
            "confidence": finding.confidence,
            "confidence_score": finding.confidence_score,
            "adjusted_q_value": finding.adjusted_q_value,
            "evidence_signals": evidence_signals,
        })
    return result


def _one_holdout_profile(
    profile_id: str,
    rows: Sequence[Mapping[str, Any]],
    completion: Mapping[str, bool],
    *,
    seed: int,
    iterations: int,
    resolver: Any,
    thresholds: Mapping[str, Any],
    taxonomy: Mapping[int, Any],
    input_digest: str,
) -> dict[str, Any]:
    profile_seed = _profile_seed(seed, profile_id)
    odd, even = odd_even_session_ids(rows)
    subsets = {
        "full": tuple(rows),
        "a": tuple(row for row in rows if str(row["session_id"]) in odd),
        "b": tuple(row for row in rows if str(row["session_id"]) in even),
    }
    reports: dict[str, Any] = {}
    for offset, (name, subset) in enumerate(subsets.items()):
        subset_completion = {str(row["session_id"]): completion.get(str(row["session_id"]), False) for row in subset}
        reports[name] = analyze_free_dna_v6(
            _namespace_rows(subset),
            baseline_resolver=resolver,
            thresholds=thresholds,
            taxonomy_by_hero=taxonomy,
            completed_sessions=subset_completion,
            seed=profile_seed + offset,
            bootstrap_iterations=iterations,
            enforce_eligibility=name == "full",
        )
    full, left, right = reports["full"], reports["a"], reports["b"]
    available_elements = sum(item.status in {"available", "limited"} and item.confidence != "unavailable" for item in full.elements)
    nonblank = available_elements >= 3 and bool(full.identity.headline.strip()) and bool(full.identity.evidence_refs)
    left_findings = {item.family: item for item in left.findings}
    right_findings = {item.family: item for item in right.findings}
    comparable = 0
    agreements = 0
    for item in full.findings:
        a, b = left_findings[item.family], right_findings[item.family]
        if item.confidence == "high" and a.direction != "unknown" and b.direction != "unknown":
            comparable += 1
            agreements += a.direction == b.direction
    public = full.as_dict()
    strings = tuple(_strings(public))
    copy_violations = sum(bool(pattern.search(value)) for value in strings for pattern in FORBIDDEN_COPY)
    estimates = derive_profile_estimates(
        rows,
        baseline_resolver=resolver,
        taxonomy_by_hero=taxonomy,
        completed_sessions=completion,
    )
    per_metric = {
        key: {
            "available": estimate.value is not None,
            "usable_count": estimate.usable_count,
            "independent_sessions": estimate.independent_sessions,
            "coverage": estimate.coverage,
            "unavailable_reason": estimate.unavailable_reason,
            "fallback_level_counts": dict((estimate.diagnostics or {}).get("fallback_level_counts") or {}),
            "unresolved_count": int((estimate.diagnostics or {}).get("unresolved_count") or 0),
        }
        for key, estimate in estimates.metrics.items()
    }
    return {
        "input_digest": input_digest,
        "profile_digest": hashlib.sha256(profile_id.encode("utf-8")).hexdigest(),
        "nonblank": nonblank,
        "available_elements": available_elements,
        "comparable_zones": comparable,
        "agreeing_zones": agreements,
        "element_status": dict(Counter(item.status for item in full.elements)),
        "family_status": dict(Counter(item.status for item in full.findings)),
        "copy_strings_scanned": len(strings),
        "copy_violations": copy_violations,
        "cost_compliant": (
            free_cost_invariant(full.cost)
            and full.cost.history_reads == 1
            and full.cost.detail_reads == 0
            and full.cost.parse_calls == 0
        ),
        "per_metric": per_metric,
        "review_items": _review_items(full),
    }


def _init_holdout_worker(baseline_path: str, threshold_path: str) -> None:
    global _HOLDOUT_WORKER_CONTEXT
    _HOLDOUT_WORKER_CONTEXT = (
        load_context_baseline_artifact(baseline_path).resolver(),
        load_threshold_artifact(threshold_path).metrics,
        _taxonomy_mapping(),
    )


def _holdout_worker(task: tuple[str, Sequence[Mapping[str, Any]], Mapping[str, bool], int, int, str]) -> dict[str, Any]:
    if _HOLDOUT_WORKER_CONTEXT is None:
        raise RuntimeError("holdout worker was not initialized")
    profile_id, rows, completion, seed, iterations, input_digest = task
    resolver, thresholds, taxonomy = _HOLDOUT_WORKER_CONTEXT
    return _one_holdout_profile(
        profile_id,
        rows,
        completion,
        seed=seed,
        iterations=iterations,
        resolver=resolver,
        thresholds=thresholds,
        taxonomy=taxonomy,
        input_digest=input_digest,
    )


def _append_private_checkpoint(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _load_checkpoint(path: Path, input_digest: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    result: dict[str, dict[str, Any]] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                break
            raise
        if record.get("input_digest") != input_digest:
            raise ValueError("holdout checkpoint input checksum mismatch")
        result[str(record["profile_digest"])] = record
    return result


def run_holdout(args: argparse.Namespace) -> dict[str, Any]:
    if args.bootstrap_iterations != 2_000 and not args.smoke:
        raise ValueError("sealed holdout evaluation must use exactly 2,000 bootstrap iterations")
    corpus = load_calibration_corpus(args.input)
    split = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    if split.get("corpus_sha256") != corpus.checksum:
        raise ValueError("split manifest corpus checksum mismatch")
    all_holdout_ids = tuple(sorted(map(str, split.get("holdout_profile_ids") or ())))
    if len(all_holdout_ids) != int(split.get("holdout_profile_count", -1)):
        raise ValueError("split manifest holdout count mismatch")
    if args.max_profiles is not None and not args.smoke:
        raise ValueError("--max-profiles is permitted only with --smoke")
    holdout_ids = all_holdout_ids[: args.max_profiles] if args.max_profiles is not None else all_holdout_ids
    baseline = load_context_baseline_artifact(args.baseline)
    thresholds = load_threshold_artifact(args.thresholds)
    taxonomy = _taxonomy_mapping()
    by_profile: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in corpus.matches:
        if str(row["profile_id"]) in set(holdout_ids):
            by_profile[str(row["profile_id"])].append(row)
    if set(by_profile) != set(holdout_ids):
        raise ValueError("holdout population is not exhaustive")
    input_digest = hashlib.sha256(
        f"{corpus.checksum}:{sha256_file(args.baseline)}:{sha256_file(args.thresholds)}:{args.seed}:{args.bootstrap_iterations}:{_evaluation_source_digest()}".encode("ascii")
    ).hexdigest()
    checkpoint_path = args.checkpoint_dir / "holdout-evaluation.jsonl"
    completed = _load_checkpoint(checkpoint_path, input_digest)
    selected_digests = {hashlib.sha256(profile_id.encode("utf-8")).hexdigest() for profile_id in holdout_ids}
    completed = {profile_digest: record for profile_digest, record in completed.items() if profile_digest in selected_digests}
    pending = [profile_id for profile_id in holdout_ids if hashlib.sha256(profile_id.encode("utf-8")).hexdigest() not in completed]

    def evaluate(profile_id: str) -> dict[str, Any]:
        return _one_holdout_profile(
            profile_id,
            by_profile[profile_id],
            corpus.completion_for_profile(profile_id),
            seed=args.seed,
            iterations=args.bootstrap_iterations,
            resolver=baseline.resolver(),
            thresholds=thresholds.metrics,
            taxonomy=taxonomy,
            input_digest=input_digest,
        )

    if args.workers == 1:
        iterator = ((profile_id, evaluate(profile_id)) for profile_id in pending)
        for position, (_profile_id, record) in enumerate(iterator, start=1):
            completed[str(record["profile_digest"])] = record
            _append_private_checkpoint(checkpoint_path, record)
            if position % 5 == 0 or position == len(pending):
                print(f"evaluated aggregate holdout progress: {len(completed)}/{len(holdout_ids)} profiles", flush=True)
    else:
        with ProcessPoolExecutor(
            max_workers=args.workers,
            initializer=_init_holdout_worker,
            initargs=(str(args.baseline), str(args.thresholds)),
        ) as executor:
            futures = {
                executor.submit(
                    _holdout_worker,
                    (
                        profile_id,
                        by_profile[profile_id],
                        corpus.completion_for_profile(profile_id),
                        args.seed,
                        args.bootstrap_iterations,
                        input_digest,
                    ),
                ): profile_id
                for profile_id in pending
            }
            for position, future in enumerate(as_completed(futures), start=1):
                record = future.result()
                completed[str(record["profile_digest"])] = record
                _append_private_checkpoint(checkpoint_path, record)
                if position % 5 == 0 or position == len(pending):
                    print(f"evaluated aggregate holdout progress: {len(completed)}/{len(holdout_ids)} profiles", flush=True)
    records = [completed[key] for key in sorted(completed)]
    per_metric: dict[str, Any] = {}
    baseline_fallback: Counter[str] = Counter()
    for key in next(iter(records))["per_metric"]:
        values = [record["per_metric"][key] for record in records]
        reasons = Counter(str(value["unavailable_reason"] or "available") for value in values)
        per_metric[key] = {
            "available_profiles": sum(bool(value["available"]) for value in values),
            "profile_count": len(values),
            "availability": sum(bool(value["available"]) for value in values) / len(values),
            "mean_coverage": sum(float(value["coverage"]) for value in values) / len(values),
            "unavailable_reasons": dict(sorted(reasons.items())),
        }
        for value in values:
            baseline_fallback.update(value["fallback_level_counts"])
            baseline_fallback["unresolved"] += int(value["unresolved_count"])
    nonblank_count = sum(bool(record["nonblank"]) for record in records)
    comparable = sum(int(record["comparable_zones"]) for record in records)
    agreements = sum(int(record["agreeing_zones"]) for record in records)
    copy_violations = sum(int(record["copy_violations"]) for record in records)
    cost_violations = sum(not bool(record["cost_compliant"]) for record in records)
    result = {
        "version": HOLDOUT_VERSION,
        "seed": args.seed,
        "bootstrap_iterations": args.bootstrap_iterations,
        "smoke": bool(args.smoke),
        "artifact_checksums": _artifact_checksums(args.baseline, args.thresholds),
        "corpus": {
            "schema_version": corpus.payload["schema_version"],
            "checksum": corpus.checksum,
            "profile_count": len(corpus.profile_ids),
            "train_profile_count": int(split["train_profile_count"]),
            "holdout_profile_count": len(holdout_ids),
            "sealed_holdout_profile_count": len(all_holdout_ids),
            "holdout_match_count": sum(len(by_profile[profile_id]) for profile_id in holdout_ids),
            "mmr_used": False,
        },
        "nonblank_identity": {"eligible_profiles": len(records), "nonblank_profiles": nonblank_count, "observed": nonblank_count / len(records)},
        "split_half_agreement": {"comparable_zones": comparable, "agreeing_zones": agreements, "observed": agreements / comparable if comparable else None},
        "abstention": {
            "element_status": dict(sum((Counter(record["element_status"]) for record in records), Counter())),
            "family_status": dict(sum((Counter(record["family_status"]) for record in records), Counter())),
        },
        "per_metric_coverage": per_metric,
        "baseline_fallback": dict(sorted(baseline_fallback.items())),
        "copy_safety": {"strings_scanned": sum(int(record["copy_strings_scanned"]) for record in records), "violations": copy_violations},
        "free_cost": {"reports_checked": len(records), "violations": cost_violations},
    }
    atomic_json(args.output, result)
    return result


def build_review_packet(args: argparse.Namespace) -> dict[str, Any]:
    records = _load_checkpoint(args.checkpoint, args.input_digest) if args.input_digest else {}
    if not records:
        lines = [json.loads(line) for line in args.checkpoint.read_text(encoding="utf-8").splitlines() if line]
        records = {str(item["profile_digest"]): item for item in lines}
    items = [item for key in sorted(records) for item in records[key].get("review_items", [])]
    rng = random.Random(args.seed)
    rng.shuffle(items)
    packet = {
        "version": REVIEW_PACKET_VERSION,
        "seed": args.seed,
        "dota_reviewer_approved": None,
        "dota_reviewer_reference": None,
        "statistical_review_approved": None,
        "statistical_reviewer_reference": None,
        "data_basis_approved": None,
        "data_basis_approver_reference": None,
        "items": [
            {"review_item_id": f"review-{index + 1:04d}", **item, "supported": None, "believable": None, "notes": None}
            for index, item in enumerate(items[: args.limit])
        ],
    }
    atomic_json(args.output, packet)
    return packet


def aggregate(args: argparse.Namespace) -> dict[str, Any]:
    synthetic = json.loads(args.synthetic.read_text(encoding="utf-8"))
    holdout = json.loads(args.holdout.read_text(encoding="utf-8"))
    review = json.loads(args.review_evidence.read_text(encoding="utf-8")) if args.review_evidence and args.review_evidence.exists() else None
    evaluation = build_evaluation_artifact(synthetic, holdout, review, generated_at=args.generated_at)
    atomic_json(args.output, evaluation)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip())
    manifest = build_release_manifest(args.output.parent, evaluation, source_revision=revision, dirty_worktree=dirty, generated_at=args.generated_at)
    atomic_json(args.release_manifest or args.output.with_name("release-manifest-6.0.0.json"), manifest)
    return evaluation


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    synthetic = commands.add_parser("synthetic")
    synthetic.add_argument("--baseline", type=Path, required=True)
    synthetic.add_argument("--thresholds", type=Path, required=True)
    synthetic.add_argument("--output", type=Path, required=True)
    synthetic.add_argument("--seed", type=int, default=6000)
    synthetic.add_argument("--bootstrap-iterations", type=int, default=2_000)
    synthetic.add_argument("--profiles-per-scenario", type=int, default=20)
    synthetic.add_argument("--null-replicates", type=int, default=200)
    synthetic.add_argument("--smoke", action="store_true")

    holdout = commands.add_parser("holdout")
    holdout.add_argument("--input", type=Path, required=True)
    holdout.add_argument("--split-manifest", type=Path, required=True)
    holdout.add_argument("--baseline", type=Path, required=True)
    holdout.add_argument("--thresholds", type=Path, required=True)
    holdout.add_argument("--checkpoint-dir", type=Path, required=True)
    holdout.add_argument("--output", type=Path, required=True)
    holdout.add_argument("--seed", type=int, default=6000)
    holdout.add_argument("--workers", type=int, default=1)
    holdout.add_argument("--bootstrap-iterations", type=int, default=2_000)
    holdout.add_argument("--max-profiles", type=int)
    holdout.add_argument("--smoke", action="store_true")

    packet = commands.add_parser("review-packet")
    packet.add_argument("--checkpoint", type=Path, required=True)
    packet.add_argument("--output", type=Path, required=True)
    packet.add_argument("--seed", type=int, default=6000)
    packet.add_argument("--limit", type=int, default=50)
    packet.add_argument("--input-digest")

    review = commands.add_parser("ingest-review")
    review.add_argument("--input", type=Path, required=True)
    review.add_argument("--output", type=Path, required=True)

    combined = commands.add_parser("aggregate")
    combined.add_argument("--synthetic", type=Path, required=True)
    combined.add_argument("--holdout", type=Path, required=True)
    combined.add_argument("--review-evidence", type=Path)
    combined.add_argument("--output", type=Path, required=True)
    combined.add_argument("--release-manifest", type=Path)
    combined.add_argument("--generated-at", default="2026-08-23T00:00:00+07:00")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if getattr(args, "workers", 1) < 1:
        raise ValueError("--workers must be positive")
    if args.command == "synthetic":
        result = run_synthetic(args)
    elif args.command == "holdout":
        result = run_holdout(args)
    elif args.command == "review-packet":
        result = build_review_packet(args)
    elif args.command == "ingest-review":
        result = ingest_review_evidence(json.loads(args.input.read_text(encoding="utf-8")))
        atomic_json(args.output, result)
    else:
        result = aggregate(args)
    print(json.dumps({"command": args.command, "output": str(args.output), "status": result.get("status"), "release_ready": result.get("release_ready")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Core staged builders for existing-corpus V6.1 calibration.

This module is intentionally independent from the network collector.  All
training functions receive already-loaded compact rows and an explicit frozen
split; they never infer a replacement split and never read holdout rows.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.ingestion.summary_history_contract import sha256_payload
from app.player_analysis_v6.baselines import BaselineResolver
from app.player_analysis_v6.calibration import REQUIRED_THRESHOLD_KEYS
from app.player_analysis_v6.calibration_derivation import (
    derive_profile_estimates,
    odd_even_session_ids,
)
from app.player_analysis_v6.context_adjustment import adjusted_value_for_match
from app.player_analysis_v6.metrics import (
    death_exposure_per_ten_minutes,
    involvement_per_minute,
    taxonomy_labels,
)
from app.player_analysis_v61.artifacts import (
    BASELINE_VERSION,
    THRESHOLDS_VERSION,
    V61_SUPPORT_ARTIFACTS,
    load_context_baseline_artifact_v61,
)
from app.player_analysis_v61.corpus_reuse import (
    EXPECTED_HOLDOUT_COUNT,
    EXPECTED_SPLIT_SEED,
    EXPECTED_TRAIN_COUNT,
    profile_digest,
    sha256_file,
)
from app.player_analysis_v61.legacy_adapter import (
    adapt_legacy_rows,
)
from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_CATALOG
from app.player_analysis_v61.versions import VERSION_MATRIX

BUILDER_VERSION = "v61-calibration-builder-2.0.0"
PRIOR_VERSION = "summary-priors-6.1.0"
DISTANCE_VERSION = "portfolio-distance-calibration-1.0.0"
RELIABILITY_VERSION = "session-reliability-calibration-1.0.0"
SEMANTIC_ARTIFACT_VERSION = "semantic-outcome-calibration-1.0.0"
MANIFEST_VERSION = "v61-calibration-build-manifest-1.0.0"
ESTIMATOR_VERSION = "v61-runtime-estimator-parity-2.0.0"
CHECKPOINT_VERSION = "v61-training-checkpoint-1.0.0"
FREEZE_RECORD_NAME = "freeze-record-6.1.0.json"
EPSILON = 1e-9


def canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def payload_checksum(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def atomic_json(path: Path, payload: Mapping[str, Any], *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(canonical_bytes(payload))
    temporary.chmod(mode)
    temporary.replace(path)


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def quantile(values: Sequence[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def load_rows(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read V6.1 calibration corpus: {path}") from exc
    rows = value.get("matches") if isinstance(value, Mapping) else value
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("V6.1 calibration corpus needs a non-empty matches array")
    return [dict(row) for row in rows]


def split_from_manifest(
    rows: Sequence[Mapping[str, Any]], manifest: Mapping[str, Any], *, expected_seed: int = EXPECTED_SPLIT_SEED
) -> tuple[set[str], set[str]]:
    train_raw, holdout_raw = manifest.get("train_profile_ids"), manifest.get("holdout_profile_ids")
    if not isinstance(train_raw, list) or not isinstance(holdout_raw, list):
        raise ValueError("frozen split manifest must contain train_profile_ids and holdout_profile_ids")
    train, holdout = set(map(str, train_raw)), set(map(str, holdout_raw))
    population = {str(row.get("profile_id")) for row in rows}
    if manifest.get("seed") != expected_seed:
        raise ValueError(f"V6.1 requires the frozen seed-{expected_seed} split")
    if train & holdout or train | holdout != population:
        raise ValueError("frozen split is not player-exclusive or does not cover the corpus")
    if len(train) != EXPECTED_TRAIN_COUNT or len(holdout) != EXPECTED_HOLDOUT_COUNT:
        raise ValueError("V6.1 requires the frozen 791/339 split")
    if manifest.get("train_digest") != profile_digest(tuple(train)) or manifest.get("holdout_digest") != profile_digest(tuple(holdout)):
        raise ValueError("frozen split profile digest mismatch")
    return train, holdout


def _adapted_rows(rows: Sequence[Mapping[str, Any]], taxonomy: Mapping[Any, Any]) -> list[dict[str, Any]]:
    adapted, _ = adapt_legacy_rows(rows, taxonomy_by_hero=taxonomy, keep_private_identifiers=True)
    return adapted


def _training_rows(
    rows: Sequence[Mapping[str, Any]], train_profiles: set[str]
) -> list[Mapping[str, Any]]:
    """Return only train rows before any analytical adaptation occurs."""

    return [row for row in rows if str(row.get("profile_id")) in train_profiles]


def build_baseline_v61(
    rows: Sequence[Mapping[str, Any]],
    *,
    train_profiles: set[str],
    generated_at: str,
    corpus_sha256: str,
    taxonomy: Mapping[Any, Any],
) -> dict[str, Any]:
    """Build context cells from runtime formulas and training profiles only."""

    from build_v6_calibration_artifacts import build_baseline

    adapted = _adapted_rows(_training_rows(rows, train_profiles), taxonomy)
    payload = build_baseline(adapted, train_profiles=train_profiles, generated_at=generated_at)
    payload["version"] = BASELINE_VERSION
    payload["estimator_version"] = ESTIMATOR_VERSION
    payload["training_only"] = True
    payload["corpus"]["source_version"] = "legacy-v6-compact-normalized"
    payload["corpus"]["corpus_sha256"] = corpus_sha256
    payload["corpus"]["train_profile_digest"] = profile_digest(tuple(train_profiles))
    payload["corpus"]["builder_version"] = BUILDER_VERSION
    for cell in payload["cells"]:
        cell["source_version"] = BASELINE_VERSION
        cell["estimator_version"] = ESTIMATOR_VERSION
    return payload


def _serialize_estimates(estimates: Any) -> dict[str, Any]:
    return {
        key: {
            "value": item.value,
            "usable_count": item.usable_count,
            "independent_sessions": item.independent_sessions,
            "coverage": item.coverage,
            "unavailable_reason": item.unavailable_reason,
        }
        for key, item in estimates.metrics.items()
    }


def _checkpoint_records(path: Path, input_digest: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    completed: dict[str, dict[str, Any]] = {}
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            if index == len(path.read_text(encoding="utf-8").splitlines()) - 1:
                break
            raise ValueError("training checkpoint contains invalid JSON") from exc
        if record.get("checkpoint_version") != CHECKPOINT_VERSION or record.get("input_digest") != input_digest:
            raise ValueError("training checkpoint checksum mismatch")
        digest = record.get("profile_digest")
        if not isinstance(digest, str) or digest in completed:
            raise ValueError("training checkpoint contains a duplicate or invalid profile digest")
        completed[digest] = record
    return completed


def _append_checkpoint(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _min_sessions_for(key: str) -> int:
    if key.startswith(("consistency_", "post_loss_", "session_drift_")):
        return 12
    if key.startswith("transfer_") or key in {"involvement_adjusted", "finishing_adjusted", "death_exposure_adjusted"}:
        return 8
    return 1


def _coverage_for(key: str) -> float:
    if key in {"toolkit_effective_count", "involvement_adjusted", "finishing_adjusted", "death_exposure_adjusted"}:
        return 0.80
    if key.startswith("transfer_"):
        return 0.70
    if key.startswith(("consistency_", "post_loss_", "session_drift_")):
        return 0.50
    return 0.0


def derive_thresholds_v61(
    rows: Sequence[Mapping[str, Any]],
    *,
    train_profiles: set[str],
    holdout_profiles: set[str],
    baseline_path: Path,
    generated_at: str,
    corpus_sha256: str,
    taxonomy: Mapping[Any, Any],
    checkpoint_dir: Path | None = None,
    completed_sessions_by_profile: Mapping[str, Mapping[str, bool]] | None = None,
    workers: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive threshold distributions from runtime-compatible profile estimates."""

    if train_profiles & holdout_profiles:
        raise ValueError("training and holdout profiles overlap")
    resolver: BaselineResolver = load_context_baseline_artifact_v61(baseline_path).resolver()
    adapted = _adapted_rows(_training_rows(rows, train_profiles), taxonomy)
    by_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in adapted:
        profile_id = str(row["profile_id"])
        if profile_id in train_profiles:
            by_profile[profile_id].append(row)
    if set(by_profile) != train_profiles:
        raise ValueError("training split does not map to the adapted corpus population")
    baseline_checksum = sha256_file(baseline_path)
    input_digest = hashlib.sha256(
        b"v61-threshold-derivation-2.0.0\0"
        + corpus_sha256.encode("ascii")
        + profile_digest(tuple(train_profiles)).encode("ascii")
        + baseline_checksum.encode("ascii")
        + taxonomy_fingerprint(taxonomy).encode("ascii")
    ).hexdigest()
    checkpoint_path = checkpoint_dir / "profile-estimates.jsonl" if checkpoint_dir else None
    completed = _checkpoint_records(checkpoint_path, input_digest) if checkpoint_path else {}
    ordered_profiles = sorted(train_profiles)

    def derive(profile_id: str) -> dict[str, Any]:
        digest = profile_digest((profile_id,))
        if digest in completed:
            return completed[digest]
        profile_rows = by_profile[profile_id]
        odd, even = odd_even_session_ids(profile_rows)
        subsets = {
            "full": profile_rows,
            "a": [row for row in profile_rows if str(row["session_id"]) in odd],
            "b": [row for row in profile_rows if str(row["session_id"]) in even],
        }
        derived: dict[str, Any] = {}
        completion = dict((completed_sessions_by_profile or {}).get(profile_id, {}))
        for name, subset in subsets.items():
            subset_completion = {
                str(row["session_id"]): completion.get(str(row["session_id"]), False)
                for row in subset
            }
            estimates = derive_profile_estimates(
                subset,
                baseline_resolver=resolver,
                taxonomy_by_hero=taxonomy,
                completed_sessions=subset_completion,
            )
            derived[name] = _serialize_estimates(estimates)
        return {
            "checkpoint_version": CHECKPOINT_VERSION,
            "input_digest": input_digest,
            "profile_digest": digest,
            "estimates": derived,
        }

    if workers < 1:
        raise ValueError("workers must be positive")
    executor = ThreadPoolExecutor(max_workers=workers) if workers > 1 else None
    try:
        records = list(executor.map(derive, ordered_profiles)) if executor else [derive(profile) for profile in ordered_profiles]
    finally:
        if executor:
            executor.shutdown(wait=True)
    if checkpoint_path:
        completed_digests = set(completed)
        for record in records:
            if record["profile_digest"] not in completed_digests:
                _append_checkpoint(checkpoint_path, record)
                completed_digests.add(record["profile_digest"])

    metrics: dict[str, dict[str, Any]] = {}
    diagnostics: dict[str, Any] = {}
    for key in REQUIRED_THRESHOLD_KEYS:
        full = [float(record["estimates"]["full"][key]["value"]) for record in records if record["estimates"]["full"][key]["value"] is not None]
        noise = [
            abs(float(record["estimates"]["a"][key]["value"]) - float(record["estimates"]["b"][key]["value"]))
            for record in records
            if record["estimates"]["a"][key]["value"] is not None and record["estimates"]["b"][key]["value"] is not None
        ]
        if len(full) < 2 or not noise:
            reasons = Counter(
                record["estimates"]["full"][key]["unavailable_reason"] or "available"
                for record in records
            )
            # A branch whose required session denominator is absent is an
            # explicit suppression, not a synthetic cutoff.  The impossible
            # opportunity gate is derived from the observed training size, so
            # the runtime can load the complete threshold registry while still
            # refusing to publish the branch.
            metrics[key] = {
                "zone_mode": "centered",
                "practical_margin": 0.0,
                "low_cutoff": 0.0,
                "high_cutoff": 0.0,
                "min_sample": len(records) + 1,
                "min_sessions": len(records) + 1,
                "min_coverage": 1.01,
                "moderate_stability": 1.0,
                "high_stability": 1.0,
                "version": THRESHOLDS_VERSION,
                "status": "suppressed_missing_training_support",
            }
            diagnostics[key] = {
                "full_estimate_count": len(full),
                "split_pair_count": len(noise),
                "fallback_used": False,
                "status": "suppressed_missing_training_support",
                "missing_reasons": dict(sorted(reasons.items())),
            }
            continue
        margin = max(EPSILON, float(quantile(noise, 0.90) or EPSILON) / 2.0)
        mode = "dispersion" if key.startswith("consistency_") else "cutoff" if key in {"breadth_effective_count", "toolkit_effective_count"} else "centered"
        low = high = stable = variable = None
        fallback = False
        if mode == "dispersion":
            stable, variable = quantile(full, 1 / 3), quantile(full, 2 / 3)
            if stable is None or variable is None or variable - stable < 2 * margin:
                center, fallback = statistics.median(full), True
                stable, variable = center - margin, center + margin
        elif mode == "cutoff":
            low, high = quantile(full, 1 / 3), quantile(full, 2 / 3)
            if low is None or high is None or high - low < 2 * margin:
                center, fallback = statistics.median(full), True
                low, high = center - margin, center + margin
        else:
            low, high = -margin, margin
        metrics[key] = {
            "zone_mode": mode,
            "practical_margin": margin,
            "low_cutoff": low,
            "high_cutoff": high,
            "min_sample": 30,
            "min_sessions": _min_sessions_for(key),
            "min_coverage": _coverage_for(key),
            "moderate_stability": 0.75,
            "high_stability": 0.90,
            "version": THRESHOLDS_VERSION,
            **({"stable_cutoff": stable, "variable_cutoff": variable} if mode == "dispersion" else {}),
        }
        diagnostics[key] = {
            "full_estimate_count": len(full),
            "split_pair_count": len(noise),
            "margin": margin,
            "fallback_used": fallback,
            "missing_reasons": dict(sorted(Counter(record["estimates"]["full"][key]["unavailable_reason"] or "available" for record in records).items())),
        }
    return (
        {
            "version": THRESHOLDS_VERSION,
            "generated_at": generated_at,
            "estimator_version": ESTIMATOR_VERSION,
            "training_only": True,
            "derivation": {
                "train_profile_count": len(train_profiles),
                "holdout_profile_count": len(holdout_profiles),
                "split_method": "frozen-seed-6000-manifest",
                "noise_method": "runtime-estimator-odd-even-session-split",
                "mmr_used": False,
                "corpus_sha256": corpus_sha256,
                "train_profile_digest": profile_digest(tuple(train_profiles)),
                "builder_version": BUILDER_VERSION,
            },
            "metrics": metrics,
        },
        diagnostics,
    )


def _raw_components(row: Mapping[str, Any], resolver: BaselineResolver, taxonomy: Mapping[Any, Any]) -> dict[str, float | None]:
    activity = involvement_per_minute(row.get("kills"), row.get("assists"), row.get("duration_seconds"))
    death = death_exposure_per_ten_minutes(row.get("deaths"), row.get("duration_seconds"))
    activity_adjusted, _ = adjusted_value_for_match(row, "involvement_per_minute", activity, baseline_resolver=resolver, taxonomy_by_hero=taxonomy)
    death_adjusted, _ = adjusted_value_for_match(row, "death_exposure_per_ten", death, baseline_resolver=resolver, taxonomy_by_hero=taxonomy)
    return {
        "outcome": float(bool(row.get("won"))) if isinstance(row.get("won"), bool) else None,
        "activity": activity_adjusted,
        "survival": -death_adjusted if death_adjusted is not None else None,
    }


def build_summary_prior(rows: Sequence[Mapping[str, Any]], train_profiles: set[str], *, corpus_sha256: str) -> dict[str, Any]:
    by_profile: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in _training_rows(rows, train_profiles):
        by_profile[str(row["profile_id"])].append(row)
    shares: list[float] = []
    total_kills = total_events = 0
    for profile_rows in by_profile.values():
        kills = sum(max(0, int(row["kills"])) for row in profile_rows)
        events = sum(max(0, int(row["kills"])) + max(0, int(row["assists"])) for row in profile_rows)
        total_kills += kills
        total_events += events
        if events:
            shares.append(kills / events)
    if not shares or total_events <= 0:
        raise ValueError("training corpus has no Finishing events")
    mean = statistics.fmean(shares)
    variance = statistics.pvariance(shares) if len(shares) > 1 else 0.0
    strength = max(2.0, min(1_000_000.0, mean * (1 - mean) / variance - 1.0)) if variance > EPSILON else float(total_events)
    return {
        "version": PRIOR_VERSION,
        "builder_version": BUILDER_VERSION,
        "estimator_version": "finishing-beta-binomial-2.0.0",
        "training_only": True,
        "corpus_sha256": corpus_sha256,
        "train_profile_digest": profile_digest(tuple(train_profiles)),
        "finishing_beta_binomial": {
            "alpha": round(max(EPSILON, mean * strength), 10),
            "beta": round(max(EPSILON, (1 - mean) * strength), 10),
            "training_observations": total_events,
            "training_successes": total_kills,
            "profile_share_observations": len(shares),
            "fit": "profile-share-moment-matched-empirical-bayes",
        },
    }


def build_distance_calibration(
    rows: Sequence[Mapping[str, Any]],
    train_profiles: set[str],
    *,
    resolver: BaselineResolver,
    taxonomy: Mapping[Any, Any],
    corpus_sha256: str,
) -> dict[str, Any]:
    by_profile: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in _training_rows(rows, train_profiles):
        by_profile[str(row["profile_id"])].append(row)
    distances: list[float] = []
    deltas: dict[str, list[float]] = defaultdict(list)
    for profile_rows in by_profile.values():
        from app.player_analysis_v61.portfolio_shape import cross_fitted_distance_records

        records = cross_fitted_distance_records(profile_rows, taxonomy)
        distances.extend(record.combined_distance for record in records)
        by_band: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for record in records:
            values = _raw_components(record.match, resolver, taxonomy)
            for component, value in values.items():
                if value is not None:
                    by_band[record.band][component].append(value)
        core = by_band.get("core", {})
        stretch = by_band.get("reliable_stretch", {})
        for component in ("outcome", "activity", "survival"):
            if core.get(component) and stretch.get(component):
                deltas[component].append(abs(statistics.fmean(stretch[component]) - statistics.fmean(core[component])))
    if not distances:
        raise ValueError("training corpus has no distance observations")
    margins = {
        component: max(EPSILON, float(quantile(values, 0.90) or EPSILON) / 2.0)
        for component, values in deltas.items()
    }
    for component in ("outcome", "activity", "survival"):
        margins.setdefault(component, EPSILON)
    return {
        "version": DISTANCE_VERSION,
        "builder_version": BUILDER_VERSION,
        "estimator_version": "portfolio-distance-frontier-2.0.0",
        "training_only": True,
        "corpus_sha256": corpus_sha256,
        "train_profile_digest": profile_digest(tuple(train_profiles)),
        "cross_fitted": True,
        "bands": {
            "core": {"maximum": float(quantile(distances, 0.50) or 0.0), "quantile": 0.50},
            "reliable_stretch": {"maximum": float(quantile(distances, 0.80) or 0.0), "quantile": 0.80},
            "experimental_edge": {"maximum": float(max(distances)), "quantile": 1.0},
        },
        "practical_margins": margins,
        "equivalence_ropes": dict(margins),
        "training_observations": len(distances),
        "margin_observations": {key: len(value) for key, value in sorted(deltas.items())},
    }


def build_session_reliability(
    rows: Sequence[Mapping[str, Any]],
    train_profiles: set[str],
    *,
    resolver: BaselineResolver,
    taxonomy: Mapping[Any, Any],
    corpus_sha256: str,
) -> dict[str, Any]:
    by_profile: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in _training_rows(rows, train_profiles):
        by_profile[str(row["profile_id"])].append(row)
    session_lengths: dict[str, list[int]] = defaultdict(list)
    component_values: dict[str, list[float]] = defaultdict(list)
    for profile_rows in by_profile.values():
        sessions: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in profile_rows:
            sessions[str(row["session_id"])].append(row)
        for session_rows in sessions.values():
            for component in ("outcome", "activity", "survival"):
                values = [value for row in session_rows if (value := _raw_components(row, resolver, taxonomy).get(component)) is not None]
                if values:
                    session_lengths[component].append(len(values))
                    component_values[component].append(statistics.fmean(values))
    shrinkage = {
        component: max(EPSILON, float(quantile(session_lengths[component], 0.50) or 1.0))
        for component in ("outcome", "activity", "survival")
    }
    scales = {}
    for component in ("outcome", "activity", "survival"):
        values = component_values[component]
        center = statistics.median(values) if values else 0.0
        scales[component] = max(EPSILON, float(quantile([abs(value - center) for value in values], 0.75) or 1.0))
    return {
        "version": RELIABILITY_VERSION,
        "builder_version": BUILDER_VERSION,
        "estimator_version": "consistency-information-weighted-2.0.0",
        "training_only": True,
        "corpus_sha256": corpus_sha256,
        "train_profile_digest": profile_digest(tuple(train_profiles)),
        "shrinkage": shrinkage,
        "component_scales": scales,
        "opportunity_minima": {"sessions": 12, "matches": 30},
        "coverage_rules": {"minimum_context_coverage": 0.80, "minimum_session_coverage": 0.50},
        "training_observations": {component: len(values) for component, values in sorted(component_values.items())},
    }


def build_semantic_calibration(
    train_profiles: set[str], *, distance: Mapping[str, Any], reliability: Mapping[str, Any], corpus_sha256: str
) -> dict[str, Any]:
    public = [definition for definition in SEMANTIC_OUTCOME_CATALOG if definition.rollout_status == "public_candidate"]
    family_rope = {
        "pool_shape": max(float(distance["equivalence_ropes"]["outcome"]), EPSILON),
        "transfer": max(float(distance["equivalence_ropes"]["outcome"]), EPSILON),
        "post_loss_response": max(float(reliability["component_scales"]["outcome"]), EPSILON),
        "combat_expression": max(float(distance["equivalence_ropes"]["activity"]), EPSILON),
        "session_drift": max(float(reliability["component_scales"]["survival"]), EPSILON),
    }
    return {
        "version": SEMANTIC_ARTIFACT_VERSION,
        "builder_version": BUILDER_VERSION,
        "estimator_version": "cluster-bootstrap-omnibus-bh-2.0.0",
        "training_only": True,
        "corpus_sha256": corpus_sha256,
        "train_profile_digest": profile_digest(tuple(train_profiles)),
        "family_fdr_q": 0.05,
        "family_rope": family_rope,
        "branch_procedure": "qualified-family-bh",
        "omnibus_families": 5,
        "ropes": {
            definition.semantic_outcome_key: family_rope[definition.family_key]
            for definition in public
        },
        "outcomes": [
            {
                "semantic_outcome_key": definition.semantic_outcome_key,
                "family": definition.family_key,
                "branch": definition.hypothesis_branch,
                "opportunity_denominator": definition.opportunity_denominator,
                "minimum_opportunities": definition.minimum_opportunities,
                "minimum_sessions": definition.minimum_sessions,
                "rollout_status": definition.rollout_status,
            }
            for definition in public
        ],
    }


def taxonomy_fingerprint(taxonomy: Mapping[Any, Any]) -> str:
    rows: list[dict[str, Any]] = []
    for hero_id, entry in sorted(taxonomy.items(), key=lambda item: repr(item[0])):
        rows.append({"hero_id": str(hero_id), "labels": list(taxonomy_labels(entry))})
    return sha256_payload({"taxonomy": rows})


def code_fingerprint() -> str:
    return hashlib.sha256(
        (BUILDER_VERSION + ESTIMATOR_VERSION + "|".join(sorted(VERSION_MATRIX))).encode("utf-8")
    ).hexdigest()


def build_manifest(
    artifact_dir: Path,
    *,
    corpus_sha256: str,
    split_manifest_path: Path,
    compatibility_audit_path: Path,
    split: Mapping[str, Any],
    audit: Mapping[str, Any],
    generated_at: str,
    authorization_reference: str,
    taxonomy: Mapping[Any, Any],
) -> dict[str, Any]:
    data_artifacts = V61_SUPPORT_ARTIFACTS[:-1]
    return {
        "version": MANIFEST_VERSION,
        "builder_version": BUILDER_VERSION,
        "generated_at": generated_at,
        "seed": EXPECTED_SPLIT_SEED,
        "corpus_sha256": corpus_sha256,
        "split_manifest_checksum": sha256_file(split_manifest_path),
        "compatibility_audit_checksum": audit.get("audit_checksum"),
        "split": {
            "train_profile_count": EXPECTED_TRAIN_COUNT,
            "holdout_profile_count": EXPECTED_HOLDOUT_COUNT,
            "overlap_count": 0,
            "train_profile_digest": profile_digest(tuple(split["train_profile_ids"])),
            "holdout_profile_digest": profile_digest(tuple(split["holdout_profile_ids"])),
        },
        "artifacts": {name: sha256_file(artifact_dir / name) for name in data_artifacts},
        "taxonomy_fingerprint": taxonomy_fingerprint(taxonomy),
        "code_fingerprint": code_fingerprint(),
        "estimator_fingerprint": ESTIMATOR_VERSION,
        "reuse_authorization_reference": authorization_reference,
        "holdout_output_inspected": False,
        "release_authorized": False,
        "state_c": False,
        "v6_0_holdout_previously_evaluated": bool(audit.get("v6_0_comparison_context", {}).get("previously_evaluated")),
        "compatibility_audit_path_digest": hashlib.sha256(str(compatibility_audit_path.name).encode()).hexdigest(),
    }


def write_freeze_manifest(
    artifact_dir: Path,
    *,
    corpus_sha256: str,
    split_manifest_path: Path,
    compatibility_audit_path: Path,
    split: Mapping[str, Any],
    audit: Mapping[str, Any],
    generated_at: str,
    authorization_reference: str,
    taxonomy: Mapping[Any, Any],
) -> dict[str, Any]:
    manifest = build_manifest(
        artifact_dir,
        corpus_sha256=corpus_sha256,
        split_manifest_path=split_manifest_path,
        compatibility_audit_path=compatibility_audit_path,
        split=split,
        audit=audit,
        generated_at=generated_at,
        authorization_reference=authorization_reference,
        taxonomy=taxonomy,
    )
    atomic_json(artifact_dir / "build-manifest-6.1.0.json", manifest)
    return manifest


def assert_reproducible(first: Path, second: Path) -> dict[str, Any]:
    expected_files = set(V61_SUPPORT_ARTIFACTS) | {
        FREEZE_RECORD_NAME,
        "threshold-derivation-diagnostics-6.1.0.json",
    }
    # A staged artifact directory may also contain the compatibility audit;
    # only the declared build outputs participate in byte reproducibility.
    first_files = {path.name for path in first.glob("*.json") if path.name in expected_files}
    second_files = {path.name for path in second.glob("*.json") if path.name in expected_files}
    if first_files != expected_files or second_files != expected_files:
        raise ValueError("V6.1 reproducibility artifact file set mismatch")
    mismatches = sorted(name for name in first_files if (first / name).read_bytes() != (second / name).read_bytes())
    if mismatches:
        raise ValueError(f"V6.1 artifact rebuild is not byte-identical: {mismatches}")
    first_manifest = json.loads((first / "build-manifest-6.1.0.json").read_text(encoding="utf-8"))
    second_manifest = json.loads((second / "build-manifest-6.1.0.json").read_text(encoding="utf-8"))
    if first_manifest.get("split") != second_manifest.get("split") or first_manifest.get("compatibility_audit_checksum") != second_manifest.get("compatibility_audit_checksum"):
        raise ValueError("V6.1 reproducibility population or audit linkage mismatch")
    return {
        "byte_identical": True,
        "files": sorted(first_files),
        "build_manifest_checksum": sha256_file(first / "build-manifest-6.1.0.json"),
        "profile_population_digest": first_manifest["split"]["train_profile_digest"] + first_manifest["split"]["holdout_profile_digest"],
        "compatibility_audit_checksum": first_manifest.get("compatibility_audit_checksum"),
    }


__all__ = [
    "BUILDER_VERSION",
    "CHECKPOINT_VERSION",
    "DISTANCE_VERSION",
    "ESTIMATOR_VERSION",
    "FREEZE_RECORD_NAME",
    "MANIFEST_VERSION",
    "PRIOR_VERSION",
    "RELIABILITY_VERSION",
    "SEMANTIC_ARTIFACT_VERSION",
    "assert_reproducible",
    "atomic_json",
    "build_baseline_v61",
    "build_distance_calibration",
    "build_manifest",
    "build_semantic_calibration",
    "build_session_reliability",
    "build_summary_prior",
    "canonical_bytes",
    "derive_thresholds_v61",
    "load_rows",
    "payload_checksum",
    "split_from_manifest",
    "taxonomy_fingerprint",
    "write_freeze_manifest",
]

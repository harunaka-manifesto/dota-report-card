"""Fail-closed V6.1 analytical artifact loading.

The wire schemas intentionally reject V6.0 version labels even though the
initial fixture cells share a compatible shape.  This prevents a V6.0 artifact
from being silently reinterpreted under changed V6.1 estimator semantics.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.player_analysis_v6.artifacts import ArtifactValidationError
from app.player_analysis_v6.baselines import BASELINE_HIERARCHY, BaselineCell, BaselineResolver
from app.player_analysis_v6.calibration import REQUIRED_THRESHOLD_KEYS
from app.player_analysis_v6.thresholds import MetricThreshold

from .versions import version

BASELINE_VERSION = version("context_baseline")
THRESHOLDS_VERSION = version("thresholds")

V61_SUPPORT_ARTIFACTS = (
    "context-baseline-3.0.0.json",
    "metric-thresholds-6.1.0.json",
    "summary-priors-6.1.0.json",
    "portfolio-distance-calibration-1.0.0.json",
    "session-reliability-calibration-1.0.0.json",
    "semantic-outcome-calibration-1.0.0.json",
    "build-manifest-6.1.0.json",
)
PRODUCTION_BETA_AUTHORIZATION_VERSION = "v61-production-beta-authorization-1.0.0"


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArtifactValidationError(f"duplicate artifact key: {key}")
        result[key] = value
    return result


def _read(path: str | Path, label: str) -> Mapping[str, Any]:
    artifact_path = Path(path)
    try:
        value = json.loads(
            artifact_path.read_text(encoding="utf-8"),
            object_pairs_hook=_no_duplicate_pairs,
        )
    except FileNotFoundError as exc:
        raise ArtifactValidationError(f"{label} artifact is missing: {artifact_path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError(f"{label} artifact cannot be read: {artifact_path}") from exc
    if not isinstance(value, Mapping):
        raise ArtifactValidationError(f"{label} artifact must be an object")
    return value


def _forbid_rank_dimensions(value: Any) -> None:
    forbidden = {"rank", "rank_tier", "mmr", "mmr_bucket", "skill_bracket", "medal"}
    if isinstance(value, Mapping):
        if any(str(key).casefold() in forbidden for key in value):
            raise ArtifactValidationError("rank/MMR dimensions are forbidden in V6.1 artifacts")
        for item in value.values():
            _forbid_rank_dimensions(item)
    elif isinstance(value, list):
        for item in value:
            _forbid_rank_dimensions(item)


def _finite_number(value: Any, label: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ArtifactValidationError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ArtifactValidationError(f"{label} must be finite")
    if minimum is not None and number < minimum:
        raise ArtifactValidationError(f"{label} must be >= {minimum}")
    return number


def _file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class ContextBaselineArtifactV61:
    resolver_value: BaselineResolver
    checksum: str

    def resolver(self) -> BaselineResolver:
        return self.resolver_value


def load_context_baseline_artifact_v61(path: str | Path) -> ContextBaselineArtifactV61:
    payload = _read(path, "V6.1 context baseline")
    if payload.get("version") != BASELINE_VERSION:
        raise ArtifactValidationError(
            f"unsupported V6.1 context baseline version: {payload.get('version')!r}"
        )
    corpus = payload.get("corpus")
    if not isinstance(corpus, Mapping) or corpus.get("mmr_used") is not False:
        raise ArtifactValidationError("V6.1 context baseline must declare mmr_used=false")
    _forbid_rank_dimensions({"cells": payload.get("cells")})
    cells_raw = payload.get("cells")
    if not isinstance(cells_raw, list) or not cells_raw:
        raise ArtifactValidationError("V6.1 context baseline needs non-empty cells")
    cells: list[BaselineCell] = []
    for index, raw in enumerate(cells_raw):
        if not isinstance(raw, Mapping) or raw.get("level") not in BASELINE_HIERARCHY:
            raise ArtifactValidationError(f"V6.1 baseline cell {index} is invalid")
        metrics = raw.get("metrics")
        if not isinstance(metrics, Mapping) or not metrics:
            raise ArtifactValidationError(f"V6.1 baseline cell {index} needs metrics")
        try:
            cells.append(
                BaselineCell(
                    level=str(raw["level"]),
                    patch=raw.get("patch"),
                    hero_id=raw.get("hero_id"),
                    hero_function=raw.get("hero_function"),
                    lane_context=raw.get("lane_context"),
                    metrics={str(key): float(value) for key, value in metrics.items()},
                    match_count=int(raw["match_count"]),
                    distinct_players=int(raw["distinct_players"]),
                    source_version=str(raw["source_version"]),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ArtifactValidationError(f"V6.1 baseline cell {index} is malformed") from exc
    from app.ingestion.summary_history_contract import sha256_payload

    return ContextBaselineArtifactV61(
        BaselineResolver(cells, version=BASELINE_VERSION),
        sha256_payload(payload),
    )


@dataclass(frozen=True, slots=True)
class ThresholdArtifactV61:
    metrics: Mapping[str, MetricThreshold]
    checksum: str


def load_threshold_artifact_v61(path: str | Path) -> ThresholdArtifactV61:
    payload = _read(path, "V6.1 threshold")
    if payload.get("version") != THRESHOLDS_VERSION:
        raise ArtifactValidationError(
            f"unsupported V6.1 threshold version: {payload.get('version')!r}"
        )
    derivation = payload.get("derivation")
    if not isinstance(derivation, Mapping) or derivation.get("mmr_used") is not False:
        raise ArtifactValidationError("V6.1 threshold artifact must declare mmr_used=false")
    _forbid_rank_dimensions({"metrics": payload.get("metrics")})
    metrics_raw = payload.get("metrics")
    if not isinstance(metrics_raw, Mapping) or set(metrics_raw) != set(REQUIRED_THRESHOLD_KEYS):
        missing = sorted(set(REQUIRED_THRESHOLD_KEYS) - set(metrics_raw or {}))
        extra = sorted(set(metrics_raw or {}) - set(REQUIRED_THRESHOLD_KEYS))
        raise ArtifactValidationError(
            f"V6.1 threshold registry manifest mismatch; missing={missing}, extra={extra}"
        )
    metrics: dict[str, MetricThreshold] = {}
    for key in REQUIRED_THRESHOLD_KEYS:
        raw = metrics_raw[key]
        if not isinstance(raw, Mapping) or raw.get("version") != THRESHOLDS_VERSION:
            raise ArtifactValidationError(f"V6.1 threshold {key} has the wrong version")
        low = raw.get("low_cutoff", raw.get("stable_cutoff"))
        high = raw.get("high_cutoff", raw.get("variable_cutoff"))
        try:
            metrics[key] = MetricThreshold(
                key=key,
                practical_margin=float(raw["practical_margin"]),
                low_cutoff=float(low) if low is not None else None,
                high_cutoff=float(high) if high is not None else None,
                min_sample=int(raw["min_sample"]),
                min_sessions=int(raw["min_sessions"]),
                min_coverage=float(raw["min_coverage"]),
                moderate_stability=float(raw["moderate_stability"]),
                high_stability=float(raw["high_stability"]),
                version=str(raw["version"]),
                zone_mode=str(raw["zone_mode"]),
                stable_cutoff=(float(raw["stable_cutoff"]) if raw.get("stable_cutoff") is not None else None),
                variable_cutoff=(float(raw["variable_cutoff"]) if raw.get("variable_cutoff") is not None else None),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ArtifactValidationError(f"V6.1 threshold {key} is malformed") from exc
    from app.ingestion.summary_history_contract import sha256_payload

    return ThresholdArtifactV61(metrics, sha256_payload(payload))


def _load_training_support(
    path: Path,
    label: str,
    expected_version: str,
    *,
    expected_keys: set[str],
) -> Mapping[str, Any]:
    payload = _read(path, label)
    if set(payload) != expected_keys:
        raise ArtifactValidationError(
            f"{label} schema drift; missing={sorted(expected_keys - set(payload))}, "
            f"extra={sorted(set(payload) - expected_keys)}"
        )
    if payload.get("version") != expected_version:
        raise ArtifactValidationError(
            f"unsupported {label} version: {payload.get('version')!r}"
        )
    if payload.get("training_only") is not True:
        raise ArtifactValidationError(f"{label} must declare training_only=true")
    _forbid_rank_dimensions(payload)
    return payload


def _validate_prior(payload: Mapping[str, Any]) -> None:
    raw = payload.get("finishing_beta_binomial")
    if not isinstance(raw, Mapping):
        raise ArtifactValidationError("V6.1 summary prior is missing finishing_beta_binomial")
    _finite_number(raw.get("alpha"), "summary prior alpha", minimum=0.001)
    _finite_number(raw.get("beta"), "summary prior beta", minimum=0.001)
    observations = raw.get("training_observations")
    if isinstance(observations, bool) or not isinstance(observations, int) or observations < 1:
        raise ArtifactValidationError("summary prior training_observations must be positive")


def _validate_distance(payload: Mapping[str, Any]) -> None:
    bands = payload.get("bands")
    if not isinstance(bands, Mapping) or set(bands) != {"core", "reliable_stretch", "experimental_edge"}:
        raise ArtifactValidationError("V6.1 distance artifact has an invalid band registry")
    values: list[float] = []
    for name in ("core", "reliable_stretch", "experimental_edge"):
        cell = bands.get(name)
        if not isinstance(cell, Mapping):
            raise ArtifactValidationError(f"V6.1 distance band {name} is malformed")
        values.append(_finite_number(cell.get("maximum"), f"distance band {name}.maximum", minimum=0.0))
    if values != sorted(values):
        raise ArtifactValidationError("V6.1 distance bands must be ordered")
    margins = payload.get("practical_margins")
    ropes = payload.get("equivalence_ropes")
    if not isinstance(margins, Mapping) or not isinstance(ropes, Mapping):
        raise ArtifactValidationError("V6.1 distance artifact needs margins and equivalence ropes")
    if set(margins) != {"outcome", "activity", "survival"} or set(ropes) != set(margins):
        raise ArtifactValidationError("V6.1 distance margin registry drift")
    for key in margins:
        _finite_number(margins[key], f"distance practical margin {key}", minimum=0.0)
        _finite_number(ropes[key], f"distance equivalence rope {key}", minimum=0.0)


def _validate_reliability(payload: Mapping[str, Any]) -> None:
    shrinkage = payload.get("shrinkage")
    scales = payload.get("component_scales")
    minima = payload.get("opportunity_minima")
    coverage = payload.get("coverage_rules")
    if not isinstance(shrinkage, Mapping) or not isinstance(scales, Mapping):
        raise ArtifactValidationError("V6.1 session reliability calibration is incomplete")
    if set(shrinkage) != {"outcome", "activity", "survival"} or set(scales) != set(shrinkage):
        raise ArtifactValidationError("V6.1 session reliability component registry drift")
    if not isinstance(minima, Mapping) or not isinstance(coverage, Mapping):
        raise ArtifactValidationError("V6.1 session reliability gates are missing")
    for key in shrinkage:
        _finite_number(shrinkage[key], f"session shrinkage {key}", minimum=0.0)
        _finite_number(scales[key], f"session component scale {key}", minimum=0.0)
    for key, value in minima.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ArtifactValidationError(f"session opportunity minimum {key} is invalid")
    for key, value in coverage.items():
        _finite_number(value, f"session coverage rule {key}", minimum=0.0)


def _validate_semantic(payload: Mapping[str, Any]) -> None:
    from .semantic_outcomes import SEMANTIC_OUTCOME_CATALOG

    expected = {
        definition.semantic_outcome_key
        for definition in SEMANTIC_OUTCOME_CATALOG
        if definition.rollout_status == "public_candidate"
    }
    outcomes = payload.get("outcomes")
    if not isinstance(outcomes, list):
        raise ArtifactValidationError("V6.1 semantic artifact outcomes must be a list")
    keys = [item.get("semantic_outcome_key") for item in outcomes if isinstance(item, Mapping)]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ArtifactValidationError("V6.1 semantic artifact registry drift")
    if payload.get("family_fdr_q") != 0.05 or payload.get("branch_procedure") != "qualified-family-bh":
        raise ArtifactValidationError("V6.1 semantic artifact must declare the frozen five-family procedure")
    ropes = payload.get("ropes")
    if not isinstance(ropes, Mapping) or set(ropes) != expected:
        raise ArtifactValidationError("V6.1 semantic artifact must predeclare every public branch rope")
    for key, value in ropes.items():
        _finite_number(value, f"semantic rope {key}", minimum=0.0)


@dataclass(frozen=True, slots=True)
class V61ArtifactBundle:
    """All runtime V6.1 calibration artifacts loaded from one frozen directory."""

    baseline: ContextBaselineArtifactV61
    thresholds: ThresholdArtifactV61
    summary_prior: Mapping[str, Any]
    distance_calibration: Mapping[str, Any]
    session_reliability: Mapping[str, Any]
    semantic_calibration: Mapping[str, Any]
    manifest: Mapping[str, Any]
    checksums: Mapping[str, str]


def load_v61_artifact_bundle(
    artifact_dir: str | Path,
    *,
    expected_corpus_sha256: str | None = None,
    expected_split_checksum: str | None = None,
) -> V61ArtifactBundle:
    """Load every required V6.1 artifact and verify manifest byte linkage."""

    directory = Path(artifact_dir)
    missing = [name for name in V61_SUPPORT_ARTIFACTS if not (directory / name).is_file()]
    if missing:
        raise ArtifactValidationError(f"V6.1 artifact bundle is missing: {missing}")
    baseline = load_context_baseline_artifact_v61(directory / V61_SUPPORT_ARTIFACTS[0])
    thresholds = load_threshold_artifact_v61(directory / V61_SUPPORT_ARTIFACTS[1])
    prior = _load_training_support(
        directory / V61_SUPPORT_ARTIFACTS[2],
        "V6.1 summary prior",
        "summary-priors-6.1.0",
        expected_keys={
            "version", "builder_version", "estimator_version", "training_only",
            "corpus_sha256", "train_profile_digest", "finishing_beta_binomial",
        },
    )
    distance = _load_training_support(
        directory / V61_SUPPORT_ARTIFACTS[3],
        "V6.1 distance calibration",
        "portfolio-distance-calibration-1.0.0",
        expected_keys={
            "version", "builder_version", "estimator_version", "training_only",
            "corpus_sha256", "train_profile_digest", "cross_fitted", "bands",
            "practical_margins", "equivalence_ropes", "training_observations",
            "margin_observations",
        },
    )
    reliability = _load_training_support(
        directory / V61_SUPPORT_ARTIFACTS[4],
        "V6.1 session reliability",
        "session-reliability-calibration-1.0.0",
        expected_keys={
            "version", "builder_version", "estimator_version", "training_only",
            "corpus_sha256", "train_profile_digest", "shrinkage", "component_scales",
            "opportunity_minima", "coverage_rules", "training_observations",
        },
    )
    semantic = _load_training_support(
        directory / V61_SUPPORT_ARTIFACTS[5],
        "V6.1 semantic calibration",
        "semantic-outcome-calibration-1.0.0",
        expected_keys={
            "version", "builder_version", "estimator_version", "training_only",
            "corpus_sha256", "train_profile_digest", "family_fdr_q", "family_rope",
            "branch_procedure", "omnibus_families", "ropes", "outcomes",
        },
    )
    _validate_prior(prior)
    _validate_distance(distance)
    _validate_reliability(reliability)
    _validate_semantic(semantic)
    manifest = _read(directory / V61_SUPPORT_ARTIFACTS[6], "V6.1 build manifest")
    if manifest.get("version") != "v61-calibration-build-manifest-1.0.0":
        raise ArtifactValidationError("unsupported V6.1 build manifest version")
    if manifest.get("release_authorized") is not False:
        raise ArtifactValidationError("V6.1 build manifest cannot authorize release")
    if manifest.get("holdout_output_inspected") is not False:
        raise ArtifactValidationError("V6.1 build manifest must freeze before holdout inspection")
    manifest_artifacts = manifest.get("artifacts")
    data_artifacts = set(V61_SUPPORT_ARTIFACTS[:-1])
    if not isinstance(manifest_artifacts, Mapping) or set(manifest_artifacts) != data_artifacts:
        raise ArtifactValidationError("V6.1 build manifest artifact registry drift")
    checksums = {name: _file_checksum(directory / name) for name in V61_SUPPORT_ARTIFACTS}
    if dict(manifest_artifacts) != {name: checksums[name] for name in data_artifacts}:
        raise ArtifactValidationError("V6.1 artifact checksum mismatch")
    if expected_corpus_sha256 is not None and manifest.get("corpus_sha256") != expected_corpus_sha256:
        raise ArtifactValidationError("V6.1 artifact corpus checksum mismatch")
    if expected_split_checksum is not None and manifest.get("split_manifest_checksum") != expected_split_checksum:
        raise ArtifactValidationError("V6.1 artifact split checksum mismatch")
    _forbid_rank_dimensions(manifest)
    return V61ArtifactBundle(
        baseline=baseline,
        thresholds=thresholds,
        summary_prior=prior,
        distance_calibration=distance,
        session_reliability=reliability,
        semantic_calibration=semantic,
        manifest=manifest,
        checksums=checksums,
    )


def load_v61_production_beta_authorization(
    path: str | Path,
    *,
    artifact_checksums: Mapping[str, str],
) -> Mapping[str, Any]:
    """Load the separate owner authorization required for production beta."""

    payload = _read(path, "V6.1 production-beta authorization")
    if payload.get("version") != PRODUCTION_BETA_AUTHORIZATION_VERSION:
        raise ArtifactValidationError("unsupported V6.1 production-beta authorization version")
    if payload.get("release_mode") != "production-beta":
        raise ArtifactValidationError("V6.1 authorization is not a production-beta decision")
    if payload.get("production_beta_authorized") is not True:
        raise ArtifactValidationError("V6.1 production beta is not authorized")
    if payload.get("release_authorized") is not True:
        raise ArtifactValidationError("V6.1 production-beta release authorization is missing")
    if payload.get("state_b") is not True:
        raise ArtifactValidationError("V6.1 production beta requires State B")
    if payload.get("public_flags_must_remain_off") is not False:
        raise ArtifactValidationError("V6.1 production-beta authorization keeps public traffic disabled")
    if not str(payload.get("operator_authorization_reference", "")).strip():
        raise ArtifactValidationError("V6.1 production-beta authorization lacks operator reference")
    automated_gates = payload.get("automated_gates")
    if not isinstance(automated_gates, Mapping) or not automated_gates:
        raise ArtifactValidationError("V6.1 production-beta authorization lacks automated gates")
    if not all(value is True for value in automated_gates.values()):
        raise ArtifactValidationError("V6.1 production-beta automated gates are incomplete")
    declared_checksums = payload.get("artifact_checksums")
    if not isinstance(declared_checksums, Mapping):
        raise ArtifactValidationError("V6.1 production-beta authorization lacks artifact checksums")
    if dict(declared_checksums) != dict(artifact_checksums):
        raise ArtifactValidationError("V6.1 production-beta authorization checksum mismatch")
    return payload


__all__ = [
    "BASELINE_VERSION",
    "ContextBaselineArtifactV61",
    "THRESHOLDS_VERSION",
    "ThresholdArtifactV61",
    "V61ArtifactBundle",
    "V61_SUPPORT_ARTIFACTS",
    "PRODUCTION_BETA_AUTHORIZATION_VERSION",
    "load_context_baseline_artifact_v61",
    "load_threshold_artifact_v61",
    "load_v61_artifact_bundle",
    "load_v61_production_beta_authorization",
]

"""Fail-closed V6.1 analytical artifact loading.

The wire schemas intentionally reject V6.0 version labels even though the
initial fixture cells share a compatible shape.  This prevents a V6.0 artifact
from being silently reinterpreted under changed V6.1 estimator semantics.
"""

from __future__ import annotations

import json
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


def _read(path: str | Path, label: str) -> Mapping[str, Any]:
    artifact_path = Path(path)
    try:
        value = json.loads(artifact_path.read_text(encoding="utf-8"))
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


__all__ = [
    "BASELINE_VERSION",
    "ContextBaselineArtifactV61",
    "THRESHOLDS_VERSION",
    "ThresholdArtifactV61",
    "load_context_baseline_artifact_v61",
    "load_threshold_artifact_v61",
]

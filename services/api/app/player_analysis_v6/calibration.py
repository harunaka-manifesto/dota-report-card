"""Threshold artifact validation and calibration loading for v6."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifacts import ArtifactValidationError
from .constants import THRESHOLDS_VERSION
from .thresholds import MetricThreshold

REQUIRED_THRESHOLD_KEYS = (
    "breadth_effective_count",
    "toolkit_effective_count",
    "involvement_adjusted",
    "finishing_adjusted",
    "death_exposure_adjusted",
    "transfer_outcome_delta",
    "transfer_activity_delta",
    "transfer_survival_delta",
    "consistency_outcome_dispersion",
    "consistency_activity_dispersion",
    "consistency_death_dispersion",
    "post_loss_outcome_delta",
    "post_loss_activity_delta",
    "post_loss_survival_delta",
    "post_loss_familiarity_delta",
    "post_loss_tempo_delta",
    "session_drift_outcome_delta",
    "session_drift_activity_delta",
    "session_drift_survival_delta",
)

_TOP_LEVEL = {"version", "generated_at", "derivation", "metrics"}
_DERIVATION = {"train_profile_count", "holdout_profile_count", "split_method", "noise_method", "mmr_used"}
_METRIC_FIELDS = {
    "zone_mode",
    "practical_margin",
    "low_cutoff",
    "high_cutoff",
    "min_sample",
    "min_sessions",
    "min_coverage",
    "moderate_stability",
    "high_stability",
    "version",
    "stable_cutoff",
    "variable_cutoff",
}
_FORBIDDEN = {"rank", "rank_tier", "mmr", "mmr_bucket", "skill_bracket", "medal"}


def _keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        result = {str(key).casefold() for key in value}
        for item in value.values():
            result.update(_keys(item))
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        nested_keys: set[str] = set()
        for item in value:
            nested_keys.update(_keys(item))
        return nested_keys
    return set()


def _exact(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    actual = set(map(str, value))
    missing, extra = expected - actual, actual - expected
    if missing or extra:
        detail = []
        if missing:
            detail.append(f"missing {sorted(missing)}")
        if extra:
            detail.append(f"unsupported {sorted(extra)}")
        raise ArtifactValidationError(f"{name} has invalid fields: {', '.join(detail)}")


def _number(value: Any, name: str, *, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ArtifactValidationError(f"{name} must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ArtifactValidationError(f"{name} must be finite")
    if minimum is not None and numeric < minimum:
        raise ArtifactValidationError(f"{name} must be >= {minimum}")
    if maximum is not None and numeric > maximum:
        raise ArtifactValidationError(f"{name} must be <= {maximum}")
    return numeric


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ArtifactValidationError(f"{name} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class ThresholdArtifact:
    version: str
    generated_at: str
    derivation: Mapping[str, Any]
    metrics: Mapping[str, MetricThreshold]

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "derivation": dict(self.derivation),
            "metrics": {
                key: {
                    "zone_mode": threshold.zone_mode,
                    "practical_margin": threshold.practical_margin,
                    "low_cutoff": threshold.low_cutoff,
                    "high_cutoff": threshold.high_cutoff,
                    "min_sample": threshold.min_sample,
                    "min_sessions": threshold.min_sessions,
                    "min_coverage": threshold.min_coverage,
                    "moderate_stability": threshold.moderate_stability,
                    "high_stability": threshold.high_stability,
                    "version": threshold.version,
                    **({
                        "stable_cutoff": threshold.stable_cutoff,
                        "variable_cutoff": threshold.variable_cutoff,
                    } if threshold.zone_mode == "dispersion" else {}),
                }
                for key, threshold in self.metrics.items()
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ThresholdArtifact:
        validate_threshold_artifact(payload)
        metrics: dict[str, MetricThreshold] = {}
        for key, raw in payload["metrics"].items():
            low = raw.get("low_cutoff", raw.get("stable_cutoff"))
            high = raw.get("high_cutoff", raw.get("variable_cutoff"))
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
                stable_cutoff=(
                    float(raw["stable_cutoff"])
                    if raw.get("stable_cutoff") is not None
                    else None
                ),
                variable_cutoff=(
                    float(raw["variable_cutoff"])
                    if raw.get("variable_cutoff") is not None
                    else None
                ),
            )
        return cls(str(payload["version"]), str(payload["generated_at"]), dict(payload["derivation"]), metrics)

    def threshold(self, key: str) -> MetricThreshold:
        try:
            return self.metrics[key]
        except KeyError as exc:
            raise ArtifactValidationError(f"threshold artifact has no metric {key!r}") from exc


def validate_threshold_artifact(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise ArtifactValidationError("threshold artifact must be an object")
    _exact(payload, _TOP_LEVEL, "threshold artifact")
    if payload["version"] != THRESHOLDS_VERSION:
        raise ArtifactValidationError(f"unsupported threshold artifact version: {payload['version']!r}")
    if not isinstance(payload["generated_at"], str) or not payload["generated_at"].strip():
        raise ArtifactValidationError("generated_at must be a non-empty string")
    derivation = payload["derivation"]
    if not isinstance(derivation, Mapping):
        raise ArtifactValidationError("derivation must be an object")
    _exact(derivation, _DERIVATION, "threshold derivation")
    _integer(derivation["train_profile_count"], "derivation.train_profile_count")
    _integer(derivation["holdout_profile_count"], "derivation.holdout_profile_count")
    if derivation["mmr_used"] is not False:
        raise ArtifactValidationError("threshold artifacts must declare mmr_used=false")
    if derivation["split_method"] != "player-level-70-30" or derivation["noise_method"] != "session-odd-even-split":
        raise ArtifactValidationError("threshold derivation method does not match v6 calibration")
    keys = _keys(payload)
    if any(key in keys for key in _FORBIDDEN):
        raise ArtifactValidationError("rank/MMR dimensions are forbidden in threshold artifacts")
    metrics = payload["metrics"]
    if not isinstance(metrics, Mapping) or set(metrics) != set(REQUIRED_THRESHOLD_KEYS):
        missing = sorted(set(REQUIRED_THRESHOLD_KEYS) - set(metrics or {}))
        extra = sorted(set(metrics or {}) - set(REQUIRED_THRESHOLD_KEYS))
        raise ArtifactValidationError(f"threshold metrics mismatch; missing={missing}, extra={extra}")
    for key, raw in metrics.items():
        if not isinstance(raw, Mapping):
            raise ArtifactValidationError(f"metrics.{key} must be an object")
        if not set(raw).issubset(_METRIC_FIELDS) or not {"zone_mode", "practical_margin", "min_sample", "min_sessions", "min_coverage", "moderate_stability", "high_stability", "version"}.issubset(raw):
            raise ArtifactValidationError(f"metrics.{key} has invalid or missing fields")
        if raw["zone_mode"] not in {"centered", "cutoff", "dispersion"}:
            raise ArtifactValidationError(f"metrics.{key}.zone_mode is unsupported")
        _number(raw["practical_margin"], f"metrics.{key}.practical_margin", minimum=0.0)
        _integer(raw["min_sample"], f"metrics.{key}.min_sample")
        _integer(raw["min_sessions"], f"metrics.{key}.min_sessions")
        _number(raw["min_coverage"], f"metrics.{key}.min_coverage", minimum=0.0, maximum=1.0)
        _number(raw["moderate_stability"], f"metrics.{key}.moderate_stability", minimum=0.0, maximum=1.0)
        _number(raw["high_stability"], f"metrics.{key}.high_stability", minimum=0.0, maximum=1.0)
        if raw["moderate_stability"] != 0.75 or raw["high_stability"] != 0.90:
            raise ArtifactValidationError(f"metrics.{key} must use v6 stability gates")
        for cutoff in ("low_cutoff", "high_cutoff", "stable_cutoff", "variable_cutoff"):
            if cutoff in raw and raw[cutoff] is not None:
                _number(raw[cutoff], f"metrics.{key}.{cutoff}")
        if raw["zone_mode"] == "dispersion":
            if raw.get("stable_cutoff") is None or raw.get("variable_cutoff") is None:
                raise ArtifactValidationError(f"metrics.{key} dispersion thresholds require stable_cutoff and variable_cutoff")
            if float(raw["stable_cutoff"]) > float(raw["variable_cutoff"]):
                raise ArtifactValidationError(f"metrics.{key} dispersion cutoffs must be ordered")
        elif raw.get("low_cutoff") is None or raw.get("high_cutoff") is None:
            raise ArtifactValidationError(f"metrics.{key} {raw['zone_mode']} thresholds require low_cutoff and high_cutoff")


def load_threshold_artifact(path: str | Path) -> ThresholdArtifact:
    artifact_path = Path(path)
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ArtifactValidationError(f"threshold artifact is missing: {artifact_path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError(f"threshold artifact cannot be read: {artifact_path}") from exc
    return ThresholdArtifact.from_dict(payload)


def build_thresholds(path: str | Path) -> Mapping[str, MetricThreshold]:
    return load_threshold_artifact(path).metrics


__all__ = [
    "REQUIRED_THRESHOLD_KEYS",
    "ThresholdArtifact",
    "validate_threshold_artifact",
    "load_threshold_artifact",
    "build_thresholds",
]

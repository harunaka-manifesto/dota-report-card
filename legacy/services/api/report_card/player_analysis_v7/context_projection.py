"""Fail-closed application of a frozen V7 categorical context projection.

This module cannot fit coefficients. Research fitting lives in ``research``;
runtime receives one signed artifact and may only validate and apply it.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

CONTEXT_PROJECTION_SCHEMA_VERSION = "v7-context-projection-2.0.0"
COMPATIBLE_POPULATION_SCHEMA_VERSION = "v7-population-parameters-2.0.0"
CONTEXT_PROJECTION_PATH = (
    Path(__file__).resolve().parent / "data" / "context-projection-2.0.0.json"
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_SOURCE_DIGEST_KEYS = frozenset(
    {
        "pass1_complete_manifest_sha256",
        "pass1_state_sha256",
        "pass1_canonical_tree_sha256",
        "pass1_parsed_overlay_manifest_sha256",
        "pass2_run_manifest_sha256",
        "source_tree_sha256",
    }
)

BASE = ("mode", "patch", "hero", "duration", "side", "lobby")
PASS2 = BASE + ("position", "lane")
PARSED_PASS1 = BASE + ("position", "role", "lane")

# Frozen feature schemas from the shipping observation builders. This is a
# validation boundary: an artifact cannot silently omit or reorder a factor.
FINDING_FACTOR_ORDER: dict[str, tuple[str, ...]] = {
    "vision_coverage": PASS2,
    "duration_tempo": ("mode", "patch", "hero", "lobby", "result"),
    "death_clustering": PASS2,
    "lane_vs_jungle_share": PASS2,
    "purchase_tempo": PARSED_PASS1,
    "deaths_alone_share": PASS2,
    "spike_usage": PASS2,
    "position_flexibility": BASE + ("prev_position",),
    "fight_timing_centroid": PARSED_PASS1,
    "hero_novelty": ("mode", "patch", "lobby"),
    "closer_vs_comeback": PASS2 + ("__arm__",),
    "post_loss_session_continuation": BASE + ("hour", "__arm__"),
    "lead_retention": PARSED_PASS1 + ("__arm__",),
    "post_loss_hero_switch": BASE + ("__arm__",),
    "post_loss_requeue_latency": BASE + ("__arm__",),
    "fight_conversion": PASS2,
}
SHIPPING_FINDING_IDS = frozenset(FINDING_FACTOR_ORDER)
RECOMMENDATION_FACTOR_ORDER = ("mode", "patch", "hero", "position", "role", "lane")
RECOMMENDATION_IDS = frozenset(
    {
        "death_clustering",
        "deaths_alone_share",
        "fight_conversion",
        "first_real_item_time",
        "first_ward_time",
        "lane_vs_jungle_share",
        "last_hits_at_ten",
        "spike_usage",
        "vision_coverage",
    }
)


class ContextProjectionError(RuntimeError):
    """The projection is absent, malformed, incompatible, or unsupported."""


class UnsupportedContextLevel(ContextProjectionError):
    """A valid player observation has a level not fitted by the artifact.

    This is a per-observation/per-dimension refusal.  Structural artifact
    failures continue to use ``ContextProjectionError`` and remain fatal.
    """


@dataclass(frozen=True)
class FactorProjection:
    name: str
    vocabulary: tuple[str, ...]
    coefficients: Mapping[str, float]
    unseen_strategy: str
    unseen_level: str | None

    def coefficient_for(self, level: str) -> float:
        if level in self.coefficients:
            return self.coefficients[level]
        if self.unseen_strategy == "map_to_level" and self.unseen_level is not None:
            return self.coefficients[self.unseen_level]
        raise UnsupportedContextLevel(
            f"unsupported level {level!r} for context factor {self.name!r}"
        )


@dataclass(frozen=True)
class FindingProjection:
    finding_id: str
    source_pass: str
    context_feature_schema: str
    intercept: float
    factors: tuple[FactorProjection, ...]

    def residual(self, value: float, context: Mapping[str, str], arm: str | None = None) -> float:
        if not math.isfinite(value):
            raise ContextProjectionError(f"{self.finding_id}: observation must be finite")
        supplied = dict(context)
        expected = {factor.name for factor in self.factors}
        if "__arm__" in expected:
            if arm is None:
                raise ContextProjectionError(f"{self.finding_id}: arm is required")
            supplied["__arm__"] = arm
        unexpected = set(supplied) - expected
        if unexpected:
            raise ContextProjectionError(
                f"{self.finding_id}: unsupported context factor(s) {sorted(unexpected)!r}"
            )
        effect = self.intercept
        for factor in self.factors:
            level = supplied.get(factor.name, "__missing__")
            effect += factor.coefficient_for(level)
        return value - effect


@dataclass(frozen=True)
class ContextProjectionArtifact:
    schema_version: str
    artifact_version: str
    artifact_sha256: str
    analytical_lineage_id: str
    population_compatibility_id: str
    feature_schema_version: str
    estimator_version: str
    source_digests: Mapping[str, str]
    dimensions: Mapping[str, FindingProjection]
    recommendation_dimensions: Mapping[str, FindingProjection]

    def finding(self, finding_id: str) -> FindingProjection:
        try:
            return self.dimensions[finding_id]
        except KeyError:
            raise ContextProjectionError(
                f"no frozen context projection for Finding {finding_id!r}"
            ) from None

    def provenance(self) -> dict[str, str]:
        return {
            "analytical_lineage_id": self.analytical_lineage_id,
            "context_projection_version": self.artifact_version,
            "context_projection_sha256": self.artifact_sha256,
            "population_compatibility_id": self.population_compatibility_id,
        }

    def recommendation(self, recommendation_id: str) -> FindingProjection:
        try:
            return self.recommendation_dimensions[recommendation_id]
        except KeyError:
            raise ContextProjectionError(
                f"no frozen context projection for Recommendation {recommendation_id!r}"
            ) from None


def artifact_digest(document: Mapping[str, Any]) -> str:
    """Digest canonical JSON with its self-digest field omitted."""

    unsigned = dict(document)
    unsigned.pop("artifact_sha256", None)
    try:
        payload = json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    except (TypeError, ValueError) as exc:
        raise ContextProjectionError(f"projection is not canonical JSON: {exc}") from exc
    return hashlib.sha256(payload).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContextProjectionError(f"{field} must be a non-empty string")
    return value


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ContextProjectionError(f"{field} must be a finite number")
    return float(value)


def _parse_factor(raw: Any, *, finding_id: str, expected_name: str) -> FactorProjection:
    if not isinstance(raw, Mapping):
        raise ContextProjectionError(f"{finding_id}.{expected_name} must be an object")
    name = _text(raw.get("name"), f"{finding_id}.factor.name")
    if name != expected_name:
        raise ContextProjectionError(
            f"{finding_id}: factor {name!r} does not match required order {expected_name!r}"
        )
    vocabulary_raw = raw.get("categorical_vocabulary")
    if not isinstance(vocabulary_raw, list) or not vocabulary_raw:
        raise ContextProjectionError(f"{finding_id}.{name}: vocabulary must be non-empty")
    vocabulary = tuple(_text(level, f"{finding_id}.{name}.level") for level in vocabulary_raw)
    if len(set(vocabulary)) != len(vocabulary):
        raise ContextProjectionError(f"{finding_id}.{name}: vocabulary contains duplicates")
    if raw.get("reference_level", "not-null") is not None:
        raise ContextProjectionError(
            f"{finding_id}.{name}: finite-sweep projection has no reference level"
        )
    coefficients_raw = raw.get("coefficients")
    if not isinstance(coefficients_raw, Mapping) or set(coefficients_raw) != set(vocabulary):
        raise ContextProjectionError(
            f"{finding_id}.{name}: coefficients must match the categorical vocabulary"
        )
    coefficients = {
        level: _finite(coefficients_raw[level], f"{finding_id}.{name}.{level}")
        for level in vocabulary
    }
    unseen = raw.get("unseen_level_behavior")
    if not isinstance(unseen, Mapping):
        raise ContextProjectionError(f"{finding_id}.{name}: unseen-level behavior is required")
    strategy = unseen.get("strategy")
    fallback = unseen.get("level")
    if strategy == "refuse":
        if fallback is not None:
            raise ContextProjectionError(f"{finding_id}.{name}: refuse cannot name a fallback")
    elif strategy == "map_to_level":
        if fallback not in vocabulary:
            raise ContextProjectionError(
                f"{finding_id}.{name}: fallback level must be in the fitted vocabulary"
            )
    else:
        raise ContextProjectionError(f"{finding_id}.{name}: unknown unseen-level strategy")
    return FactorProjection(name, vocabulary, coefficients, str(strategy), fallback)


def _parse_dimension(
    finding_id: str,
    raw: Any,
    *,
    expected: tuple[str, ...] | None = None,
    id_field: str = "finding_id",
) -> FindingProjection:
    if not isinstance(raw, Mapping) or raw.get(id_field) != finding_id:
        raise ContextProjectionError(f"{finding_id}: malformed context projection")
    expected = expected or FINDING_FACTOR_ORDER[finding_id]
    factor_order = raw.get("factor_order")
    if factor_order != list(expected):
        raise ContextProjectionError(
            f"{finding_id}: factor_order {factor_order!r} does not match {list(expected)!r}"
        )
    factors_raw = raw.get("factors")
    if not isinstance(factors_raw, list) or len(factors_raw) != len(expected):
        raise ContextProjectionError(f"{finding_id}: factors do not match factor_order")
    factors = tuple(
        _parse_factor(row, finding_id=finding_id, expected_name=name)
        for row, name in zip(factors_raw, expected, strict=True)
    )
    expected_order = [
        {"factor": factor.name, "level": level}
        for factor in factors
        for level in factor.vocabulary
    ]
    if raw.get("coefficient_order") != expected_order:
        raise ContextProjectionError(f"{finding_id}: coefficient_order is not canonical")
    return FindingProjection(
        finding_id=finding_id,
        source_pass=_text(raw.get("source_pass"), f"{finding_id}.source_pass"),
        context_feature_schema=_text(
            raw.get("context_feature_schema"), f"{finding_id}.context_feature_schema"
        ),
        intercept=_finite(raw.get("intercept"), f"{finding_id}.intercept"),
        factors=factors,
    )


def parse_context_projection(document: Mapping[str, Any]) -> ContextProjectionArtifact:
    if document.get("schema_version") != CONTEXT_PROJECTION_SCHEMA_VERSION:
        raise ContextProjectionError(
            f"projection schema {document.get('schema_version')!r} is not "
            f"{CONTEXT_PROJECTION_SCHEMA_VERSION!r}"
        )
    declared_digest = _text(document.get("artifact_sha256"), "artifact_sha256")
    if not SHA256.fullmatch(declared_digest) or declared_digest != artifact_digest(document):
        raise ContextProjectionError("context projection artifact digest mismatch")
    estimator = document.get("estimator")
    if not isinstance(estimator, Mapping):
        raise ContextProjectionError("estimator identity is required")
    if estimator.get("algorithm") != "finite-sweep-additive-categorical-gauss-seidel":
        raise ContextProjectionError("unsupported context projection algorithm")
    if estimator.get("sweeps") != 10 or estimator.get("weighting") != "equal_per_opportunity":
        raise ContextProjectionError("unsupported projection sweeps or weighting")
    if estimator.get("interactions") != [] or estimator.get("player_factor") is not False:
        raise ContextProjectionError("projection interactions/player factor are incompatible")
    if estimator.get("reference_policy") != "none_finite_sweep_parameterization":
        raise ContextProjectionError("unsupported projection reference policy")
    source_digests = document.get("source_digests")
    if not isinstance(source_digests, Mapping) or not REQUIRED_SOURCE_DIGEST_KEYS.issubset(
        source_digests
    ):
        raise ContextProjectionError(
            f"source_digests must include {sorted(REQUIRED_SOURCE_DIGEST_KEYS)!r}"
        )
    for name, digest in source_digests.items():
        if not isinstance(name, str) or not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise ContextProjectionError(f"invalid source digest {name!r}")
    dimensions_raw = document.get("dimensions")
    if not isinstance(dimensions_raw, Mapping) or set(dimensions_raw) != SHIPPING_FINDING_IDS:
        raise ContextProjectionError("artifact must contain exactly the 16 shipping Findings")
    dimensions = {
        finding_id: _parse_dimension(finding_id, dimensions_raw[finding_id])
        for finding_id in FINDING_FACTOR_ORDER
    }
    recommendations_raw = document.get("recommendation_dimensions")
    if not isinstance(recommendations_raw, Mapping) or set(recommendations_raw) != RECOMMENDATION_IDS:
        raise ContextProjectionError("artifact must contain exactly the 9 Recommendation projections")
    recommendations = {
        key: _parse_dimension(
            key,
            recommendations_raw[key],
            expected=RECOMMENDATION_FACTOR_ORDER,
            id_field="recommendation_id",
        )
        for key in sorted(RECOMMENDATION_IDS)
    }
    return ContextProjectionArtifact(
        schema_version=CONTEXT_PROJECTION_SCHEMA_VERSION,
        artifact_version=_text(document.get("artifact_version"), "artifact_version"),
        artifact_sha256=declared_digest,
        analytical_lineage_id=_text(
            document.get("analytical_lineage_id"), "analytical_lineage_id"
        ),
        population_compatibility_id=_text(
            document.get("population_compatibility_id"), "population_compatibility_id"
        ),
        feature_schema_version=_text(
            document.get("feature_schema_version"), "feature_schema_version"
        ),
        estimator_version=_text(estimator.get("version"), "estimator.version"),
        source_digests=dict(source_digests),
        dimensions=dimensions,
        recommendation_dimensions=recommendations,
    )


@lru_cache(maxsize=1)
def load_context_projection(path: Path | None = None) -> ContextProjectionArtifact:
    target = path or CONTEXT_PROJECTION_PATH
    if not target.is_file():
        raise ContextProjectionError(f"frozen context projection missing at {target}")
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContextProjectionError(f"cannot read context projection {target}: {exc}") from exc
    if not isinstance(document, Mapping):
        raise ContextProjectionError("context projection root must be an object")
    return parse_context_projection(document)


def assert_population_compatible(
    projection: ContextProjectionArtifact, population_document: Mapping[str, Any]
) -> None:
    expected = {
        "schema_version": COMPATIBLE_POPULATION_SCHEMA_VERSION,
        "analytical_lineage_id": projection.analytical_lineage_id,
        "context_projection_sha256": projection.artifact_sha256,
        "population_compatibility_id": projection.population_compatibility_id,
    }
    mismatches = {
        key: (population_document.get(key), value)
        for key, value in expected.items()
        if population_document.get(key) != value
    }
    if mismatches:
        raise ContextProjectionError(f"incompatible population artifact: {mismatches!r}")


def project_series(
    projection: ContextProjectionArtifact,
    finding_id: str,
    observations: Sequence[tuple[float, Mapping[str, str], str | None]],
) -> list[float]:
    finding = projection.finding(finding_id)
    return [finding.residual(value, context, arm) for value, context, arm in observations]


__all__ = [
    "CONTEXT_PROJECTION_PATH",
    "CONTEXT_PROJECTION_SCHEMA_VERSION",
    "COMPATIBLE_POPULATION_SCHEMA_VERSION",
    "FINDING_FACTOR_ORDER",
    "RECOMMENDATION_FACTOR_ORDER",
    "RECOMMENDATION_IDS",
    "SHIPPING_FINDING_IDS",
    "ContextProjectionArtifact",
    "ContextProjectionError",
    "UnsupportedContextLevel",
    "artifact_digest",
    "assert_population_compatible",
    "load_context_projection",
    "parse_context_projection",
    "project_series",
]

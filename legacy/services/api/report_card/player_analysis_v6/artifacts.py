"""Validated, immutable calibration artifacts used by Free DNA v6.

The public v6 switch is intentionally fail-closed.  This module keeps the
wire format small and strict so a report can never silently use an unreviewed
or rank/MMR-conditioned calibration snapshot.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .baselines import BASELINE_HIERARCHY, BaselineCell, BaselineResolver
from .constants import BASELINE_VERSION


class ArtifactValidationError(ValueError):
    """Raised when a v6 calibration artifact cannot be trusted."""


_BASELINE_TOP_LEVEL = {"version", "generated_at", "corpus", "cells"}
_CORPUS_KEYS = {"profile_count", "match_count", "regions", "lobby_mix", "mmr_used"}
_CELL_KEYS = {
    "level",
    "patch",
    "hero_id",
    "hero_function",
    "lane_context",
    "metrics",
    "match_count",
    "distinct_players",
    "source_version",
}
_FORBIDDEN_DIMENSION_KEYS = {
    "mmr",
    "mmr_bucket",
    "rank",
    "rank_tier",
    "skill_bracket",
    "medal",
}


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            keys.add(str(key).casefold())
            keys.update(_walk_keys(item))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            keys.update(_walk_keys(item))
    return keys


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    actual = {str(key) for key in value}
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing {sorted(missing)}")
        if extra:
            parts.append(f"unsupported {sorted(extra)}")
        raise ArtifactValidationError(f"{name} has invalid fields: {', '.join(parts)}")


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ArtifactValidationError(f"{name} must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ArtifactValidationError(f"{name} must be finite")
    return numeric


def _count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ArtifactValidationError(f"{name} must be a non-negative integer")
    return value


def _logical_cell_key(cell: Mapping[str, Any]) -> tuple[Any, ...]:
    level = str(cell["level"])
    return (
        level,
        cell.get("patch"),
        cell.get("hero_id"),
        cell.get("hero_function"),
        cell.get("lane_context"),
    )


@dataclass(frozen=True, slots=True)
class ContextBaselineArtifact:
    version: str
    generated_at: str
    corpus: Mapping[str, Any]
    cells: tuple[BaselineCell, ...]

    def resolver(self) -> BaselineResolver:
        return BaselineResolver(self.cells, version=self.version)

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "corpus": dict(self.corpus),
            "cells": [
                {
                    "level": cell.level,
                    "patch": cell.patch,
                    "hero_id": cell.hero_id,
                    "hero_function": cell.hero_function,
                    "lane_context": cell.lane_context,
                    "metrics": dict(cell.metrics),
                    "match_count": cell.match_count,
                    "distinct_players": cell.distinct_players,
                    "source_version": cell.source_version,
                }
                for cell in self.cells
            ],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ContextBaselineArtifact:
        validate_context_baseline_artifact(payload)
        cells = tuple(
            BaselineCell(
                level=str(raw["level"]),
                patch=raw.get("patch"),
                hero_id=raw.get("hero_id"),
                hero_function=raw.get("hero_function"),
                lane_context=raw.get("lane_context"),
                metrics={key: float(value) for key, value in raw["metrics"].items()},
                match_count=int(raw["match_count"]),
                distinct_players=int(raw["distinct_players"]),
                source_version=str(raw["source_version"]),
            )
            for raw in payload["cells"]
        )
        return cls(str(payload["version"]), str(payload["generated_at"]), dict(payload["corpus"]), cells)


def validate_context_baseline_artifact(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise ArtifactValidationError("Context baseline artifact must be an object")
    _require_exact_keys(payload, _BASELINE_TOP_LEVEL, "context baseline artifact")
    if payload["version"] != BASELINE_VERSION:
        raise ArtifactValidationError(f"unsupported context baseline version: {payload['version']!r}")
    if not isinstance(payload["generated_at"], str) or not payload["generated_at"].strip():
        raise ArtifactValidationError("generated_at must be a non-empty string")
    corpus = payload["corpus"]
    if not isinstance(corpus, Mapping):
        raise ArtifactValidationError("corpus must be an object")
    _require_exact_keys(corpus, _CORPUS_KEYS, "context baseline corpus")
    if corpus["mmr_used"] is not False:
        raise ArtifactValidationError("context baseline artifacts must declare mmr_used=false")
    _count(corpus["profile_count"], "corpus.profile_count")
    _count(corpus["match_count"], "corpus.match_count")
    if not isinstance(corpus["regions"], list) or not isinstance(corpus["lobby_mix"], Mapping):
        raise ArtifactValidationError("corpus.regions and corpus.lobby_mix have invalid types")
    keys = _walk_keys(payload)
    forbidden = sorted(key for key in keys if key in _FORBIDDEN_DIMENSION_KEYS)
    if forbidden:
        raise ArtifactValidationError(f"rank/MMR dimensions are forbidden: {forbidden}")
    # mmr_used is handled explicitly above; it is allowed only as the corpus
    # declaration and must never occur in a cell or nested metric payload.
    if "cells" not in payload or not isinstance(payload["cells"], list):
        raise ArtifactValidationError("cells must be an array")
    seen: set[tuple[Any, ...]] = set()
    for index, raw in enumerate(payload["cells"]):
        if not isinstance(raw, Mapping):
            raise ArtifactValidationError(f"cells[{index}] must be an object")
        _require_exact_keys(raw, _CELL_KEYS, f"cells[{index}]")
        level = str(raw["level"])
        if level not in BASELINE_HIERARCHY:
            raise ArtifactValidationError(f"cells[{index}] has unsupported level {level!r}")
        required_dimensions = {
            "patch+hero+lane": {"patch", "hero_id", "lane_context"},
            "patch+hero_function+lane": {"patch", "hero_function", "lane_context"},
            "patch+hero": {"patch", "hero_id"},
            "patch+lane": {"patch", "lane_context"},
            "patch": {"patch"},
            "overall": set(),
        }[level]
        dimension_fields = {"patch", "hero_id", "hero_function", "lane_context"}
        missing_dimensions = sorted(name for name in required_dimensions if raw.get(name) in (None, ""))
        unexpected_dimensions = sorted(name for name in dimension_fields - required_dimensions if raw.get(name) not in (None, ""))
        if missing_dimensions or unexpected_dimensions:
            raise ArtifactValidationError(
                f"cells[{index}] dimensions do not match {level}; "
                f"missing={missing_dimensions}, unexpected={unexpected_dimensions}"
            )
        key = _logical_cell_key(raw)
        if key in seen:
            raise ArtifactValidationError(f"duplicate logical baseline cell: {key!r}")
        seen.add(key)
        _count(raw["match_count"], f"cells[{index}].match_count")
        _count(raw["distinct_players"], f"cells[{index}].distinct_players")
        if not isinstance(raw["metrics"], Mapping) or not raw["metrics"]:
            raise ArtifactValidationError(f"cells[{index}].metrics must be a non-empty object")
        for metric, value in raw["metrics"].items():
            _finite_number(value, f"cells[{index}].metrics.{metric}")


def load_context_baseline_artifact(path: str | Path) -> ContextBaselineArtifact:
    artifact_path = Path(path)
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ArtifactValidationError(f"context baseline artifact is missing: {artifact_path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError(f"context baseline artifact cannot be read: {artifact_path}") from exc
    return ContextBaselineArtifact.from_dict(payload)


def build_baseline_resolver(path: str | Path) -> BaselineResolver:
    return load_context_baseline_artifact(path).resolver()


__all__ = [
    "ArtifactValidationError",
    "ContextBaselineArtifact",
    "validate_context_baseline_artifact",
    "load_context_baseline_artifact",
    "build_baseline_resolver",
]

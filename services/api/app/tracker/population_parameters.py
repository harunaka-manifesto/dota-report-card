"""Offline builder and immutable publisher for V1 context parameters.

Provider transport and scheduling stay outside this module. Inputs are validated,
normalized STRATZ aggregates plus an independent calibration sample; no endpoint
response is trusted merely because its shape parsed.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import cast

from sqlalchemy import Connection, func, select
from sqlalchemy.dialects.postgresql import insert

from .context import METRIC_CLASS, HeroLevel, MetricParameters, ParameterSet
from .metrics import METRICS
from .schema import parameter_sets

ROLE_POSITION = {"CARRY": 1, "MID": 2, "OFFLANE": 3}
ROLE_NAMES = {"CARRY": "Carry", "MID": "Mid", "OFFLANE": "Offlane"}
LANE_THRESHOLDS = {
    "Carry": (-2.05, 1.52),
    "Mid": (-2.01, 2.04),
    "Offlane": (-1.91, 1.32),
}
MIN_HERO_MATCHES = 300
MIN_BASE_MATCHES = 3_000
MIN_PAIR_MATCHES = 20
MIN_OPPONENT_MATCHES = 500
MIN_COVERAGE = 0.97


@dataclass(frozen=True)
class HeroStatRow:
    hero_id: int
    position: int
    metric_id: str
    value: float
    match_count: int


@dataclass(frozen=True)
class LaneOutcomeRow:
    position: int
    hero_id: int
    opponent_hero_id: int
    cs_count: float
    match_count: int


@dataclass(frozen=True)
class CalibrationMatch:
    role: str
    opponent_hero_ids: tuple[int, ...]
    observed_cs_advantage: float
    weight: int = 1


@dataclass(frozen=True)
class BuildInput:
    version: str
    pool_start: date
    pool_end: date
    hero_stats: tuple[HeroStatRow, ...]
    lane_outcomes: tuple[LaneOutcomeRow, ...]
    calibration_matches: tuple[CalibrationMatch, ...]
    # Locked estimates from the independent research calibration. The job checks
    # drift against these rather than silently treating a new fit as validated.
    reference_role_slopes: Mapping[str, float]
    maximum_slope_drift: float
    metric_parameters: Mapping[str, MetricParameters]
    model_version: str = "context-adjustment-v1"


def _number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_input(data: BuildInput) -> None:
    if not data.version or "/" in data.version or "\\" in data.version or data.version in {".", ".."}:
        raise ValueError("invalid artifact version")
    weeks = (data.pool_end - data.pool_start).days / 7
    if weeks < 4 or weeks > 8 or data.pool_end < data.pool_start:
        raise ValueError("source pool must span 4–8 weeks")
    if not _number(data.maximum_slope_drift) or data.maximum_slope_drift < 0:
        raise ValueError("invalid maximum slope drift")
    if set(data.reference_role_slopes) != set(ROLE_NAMES):
        raise ValueError("reference slopes must cover Carry, Mid and Offlane")
    if set(data.metric_parameters) != set(METRICS):
        raise ValueError("metric parameters must cover the complete tracker registry")
    if set(METRIC_CLASS) != set(METRICS):
        raise ValueError("context metric matrix does not match the tracker metric registry")
    for value in data.reference_role_slopes.values():
        if not _number(value):
            raise ValueError("reference slopes must be finite")
    for param in data.metric_parameters.values():
        if not all(_number(value) for value in asdict(param).values()):
            raise ValueError("metric parameters must be finite")
        if param.sigma_pop <= 0 or param.tau <= 0 or param.floor_tolerance < 0:
            raise ValueError("metric parameters are outside valid bounds")

    seen_hero: set[tuple[int, int, str]] = set()
    for row in data.hero_stats:
        hero_key = (row.hero_id, row.position, row.metric_id)
        if (type(row.hero_id) is not int or row.hero_id <= 0 or row.position not in range(1, 6)
                or row.metric_id not in METRICS or not _number(row.value)
                or type(row.match_count) is not int or row.match_count < 0 or hero_key in seen_hero):
            raise ValueError("invalid or duplicate heroStats.stats row")
        seen_hero.add(hero_key)

    seen_lane: set[tuple[int, int, int]] = set()
    for lane_row in data.lane_outcomes:
        lane_key = (lane_row.position, lane_row.hero_id, lane_row.opponent_hero_id)
        if (lane_row.position not in ROLE_POSITION.values() or type(lane_row.hero_id) is not int or lane_row.hero_id <= 0
                or type(lane_row.opponent_hero_id) is not int or lane_row.opponent_hero_id <= 0
                or not _number(lane_row.cs_count) or lane_row.cs_count < 0
                or type(lane_row.match_count) is not int or lane_row.match_count < 0
                or lane_row.match_count == 0 and lane_row.cs_count != 0 or lane_key in seen_lane):
            raise ValueError("invalid heroStats.laneOutcome row")
        seen_lane.add(lane_key)
    if not data.lane_outcomes:
        raise ValueError("laneOutcome rows are required")
    for sample in data.calibration_matches:
        if (sample.role not in ROLE_POSITION or not sample.opponent_hero_ids
                or any(type(hero_id) is not int or hero_id <= 0 for hero_id in sample.opponent_hero_ids)
                or not _number(sample.observed_cs_advantage)
                or type(sample.weight) is not int or sample.weight <= 0):
            raise ValueError("invalid independent CS slope calibration row")


def _derive_opponent_effects(rows: tuple[LaneOutcomeRow, ...]) -> tuple[dict[tuple[int, int], float], dict[tuple[int, int], int]]:
    grouped: dict[tuple[int, int], list[LaneOutcomeRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.position, row.hero_id)].append(row)
    effects: dict[tuple[int, int], float] = {}
    effective_counts: dict[tuple[int, int], int] = {}
    for (position, _hero_id), pairs in grouped.items():
        total = sum(row.match_count for row in pairs)
        if total < MIN_BASE_MATCHES:
            continue
        base = sum(row.cs_count for row in pairs) / total
        for row in pairs:
            if row.match_count < MIN_PAIR_MATCHES:
                continue
            key = (position, row.opponent_hero_id)
            effects.setdefault(key, 0.0)
            effective_counts.setdefault(key, 0)
            effects[key] += (row.cs_count / row.match_count - base) * row.match_count
            effective_counts[key] += row.match_count
    for key, count in tuple(effective_counts.items()):
        if count < MIN_OPPONENT_MATCHES:
            del effective_counts[key]
            del effects[key]
        else:
            effects[key] /= count
    return effects, effective_counts


def _fit_role_slopes(data: BuildInput, effects: Mapping[tuple[int, int], float]) -> dict[str, float]:
    accum: dict[str, tuple[float, float]] = {role: (0.0, 0.0) for role in ROLE_NAMES}
    for sample in data.calibration_matches:
        position = ROLE_POSITION[sample.role]
        keys = [(position, hero_id) for hero_id in sample.opponent_hero_ids]
        if any(key not in effects for key in keys):
            continue
        score = sum(effects[key] for key in keys)
        if score == 0:
            continue
        numerator, denominator = accum[sample.role]
        accum[sample.role] = (numerator + sample.weight * score * sample.observed_cs_advantage,
                              denominator + sample.weight * score * score)
    if any(denominator == 0 for _, denominator in accum.values()):
        raise ValueError("insufficient covered observations to estimate every role slope")
    return {role: numerator / denominator for role, (numerator, denominator) in accum.items()}


def _coverage(data: BuildInput, effects: Mapping[tuple[int, int], float]) -> dict[str, float]:
    totals = {role: (0, 0) for role in ROLE_NAMES}
    for sample in data.calibration_matches:
        total, covered = totals[sample.role]
        totals[sample.role] = (total + sample.weight,
                               covered + sample.weight * all(
                                   (ROLE_POSITION[sample.role], hero_id) in effects
                                   for hero_id in sample.opponent_hero_ids))
    if any(total == 0 for total, _ in totals.values()):
        raise ValueError("coverage sample must contain all three roles")
    return {role: covered / total for role, (total, covered) in totals.items()}


def build_artifact(data: BuildInput) -> dict[str, object]:
    """Validate provider aggregates and return a JSON-ready immutable artifact."""
    _validate_input(data)
    opponent_effects, opponent_counts = _derive_opponent_effects(data.lane_outcomes)
    coverage = _coverage(data, opponent_effects)
    if min(coverage.values()) < MIN_COVERAGE:
        raise ValueError(f"opponent coverage below {MIN_COVERAGE:.0%}: {coverage}")
    role_slopes = _fit_role_slopes(data, opponent_effects)
    drift = {role: abs(role_slopes[role] - data.reference_role_slopes[role]) for role in ROLE_NAMES}
    if max(drift.values()) > data.maximum_slope_drift:
        raise ValueError(f"csCount role-slope drift exceeds approved bound: {drift}")

    hero_levels = {
        f"{row.hero_id}:{row.position}:{row.metric_id}": {
            "value": row.value if row.match_count >= MIN_HERO_MATCHES else None,
            "match_count": row.match_count,
        }
        for row in data.hero_stats
    }
    input_json = json.dumps({
        "hero_stats": [asdict(row) for row in data.hero_stats],
        "lane_outcomes": [asdict(row) for row in data.lane_outcomes],
        "calibration_matches": [asdict(row) for row in data.calibration_matches],
        "pool_start": data.pool_start.isoformat(),
        "pool_end": data.pool_end.isoformat(),
    }, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    artifact = {
        "schema_version": "tracker-context-parameters-v1",
        "version": data.version,
        "model_version": data.model_version,
        "pool": {"start": data.pool_start.isoformat(), "end": data.pool_end.isoformat(),
                 "weeks": (data.pool_end - data.pool_start).days / 7},
        "source": "stratz.heroStats.stats+laneOutcome",
        "input_sha256": hashlib.sha256(input_json).hexdigest(),
        "hero_levels": hero_levels,
        "opponent_effects": {f"{position}:{hero_id}": effect
                             for (position, hero_id), effect in sorted(opponent_effects.items())},
        "opponent_match_counts": {f"{position}:{hero_id}": count
                                  for (position, hero_id), count in sorted(opponent_counts.items())},
        "opponent_coverage": coverage,
        "role_slopes": role_slopes,
        "reference_role_slopes": dict(data.reference_role_slopes),
        "maximum_slope_drift": data.maximum_slope_drift,
        "slope_drift": drift,
        "lane_thresholds": {role: list(values) for role, values in LANE_THRESHOLDS.items()},
        "metrics": {metric_id: asdict(param) for metric_id, param in sorted(data.metric_parameters.items())},
        "validation": {"passed": True, "minimum_opponent_coverage": MIN_COVERAGE,
                       "maximum_role_slope_drift": max(drift.values())},
    }
    encoded = json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    artifact["sha256"] = hashlib.sha256(encoded).hexdigest()
    return artifact


def _verified_artifact(artifact: Mapping[str, object]) -> bool:
    digest = artifact.get("sha256")
    if not isinstance(digest, str):
        return False
    unsigned = dict(artifact)
    del unsigned["sha256"]
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest() == digest


def load_parameter_set(path: Path) -> ParameterSet:
    """Load a verified published artifact into the context evaluator's contract."""
    return parameter_set_from_artifact(json.loads(path.read_text()))


def parameter_set_from_artifact(artifact: object) -> ParameterSet:
    """Verify an artifact's integrity and validation record, then map it."""
    if (not isinstance(artifact, Mapping) or artifact.get("schema_version") != "tracker-context-parameters-v1"
            or not _verified_artifact(artifact)):
        raise ValueError("population parameter artifact failed integrity validation")
    validation = artifact.get("validation")
    if not isinstance(validation, Mapping) or validation.get("passed") is not True:
        raise ValueError("population parameter artifact is not validated")
    hero_levels: dict[tuple[int, int, str], HeroLevel] = {}
    for key, row in artifact["hero_levels"].items():
        hero_id, position, metric_id = key.split(":", 2)
        value = row["value"]
        if value is None:
            continue
        hero_levels[(int(hero_id), int(position), metric_id)] = HeroLevel(value, row["match_count"])
    opponent_effects: dict[tuple[int, int], float] = {}
    for key, value in artifact["opponent_effects"].items():
        position, hero_id = map(int, key.split(":"))
        opponent_effects[(position, hero_id)] = cast(float, value)
    metrics = {key: MetricParameters(**value) for key, value in artifact["metrics"].items()}
    coverage = min(artifact["opponent_coverage"].values())
    return ParameterSet(
        version=artifact["version"], validated=True, opponent_coverage=coverage,
        cs_slope_regression_passed=True, hero_levels=hero_levels,
        opponent_effects=opponent_effects, role_slopes=artifact["role_slopes"],
        lane_thresholds={key: tuple(value) for key, value in artifact["lane_thresholds"].items()},
        metrics=metrics,
    )


def publish_artifact(artifact: Mapping[str, object], directory: Path) -> Path:
    """Atomically create a versioned artifact; an existing version is immutable."""
    version = artifact.get("version")
    validation = artifact.get("validation")
    if (not isinstance(version, str) or not version or "/" in version or "\\" in version
            or version in {".", ".."} or not isinstance(validation, Mapping)
            or validation.get("passed") is not True or not _verified_artifact(artifact)):
        raise ValueError("only validated versioned artifacts may be published")
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{version}.json"
    payload = json.dumps(artifact, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    fd, temporary_name = tempfile.mkstemp(prefix=".population-parameters-", dir=directory)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # link is atomic and fails if the version already exists, preserving immutability.
        os.link(temporary, destination)
    except FileExistsError as exc:
        raise FileExistsError(f"parameter artifact already exists: {destination.name}") from exc
    finally:
        temporary.unlink(missing_ok=True)
    return destination


CONTEXT_PARAMETER_KIND = "CONTEXT_POPULATION"
# Production analysis reads only owner-approved artifacts. Tests may widen this
# to clearly labelled TEST_ONLY fixtures; PROVISIONAL is never consumed.
ACTIVE_PARAMETER_STATUSES: tuple[str, ...] = ("APPROVED",)


def register_parameter_artifact(connection: Connection, artifact: Mapping[str, object], *,
                                status: str) -> str:
    """Store a validated artifact as an immutable parameter-set row.

    Registering does not trigger rebuilds by itself; the methodology rebuild
    sweep compares each analysis's stamped version with the current one.
    """
    if status not in {"APPROVED", "TEST_ONLY", "PROVISIONAL"}:
        raise ValueError("Unsupported parameter-set status")
    parameter_set_from_artifact(artifact)
    version = cast(str, artifact["version"])
    digest = cast(str, artifact["sha256"])
    connection.execute(insert(parameter_sets).values(
        version=version, kind=CONTEXT_PARAMETER_KIND, digest=digest, status=status,
        parameters=dict(artifact), provenance={"source": artifact.get("source"),
                                               "input_sha256": artifact.get("input_sha256")},
        created_at=func.clock_timestamp(),
    ).on_conflict_do_nothing())
    existing = connection.execute(select(parameter_sets).where(
        parameter_sets.c.version == version,
    )).mappings().one()
    if existing["kind"] != CONTEXT_PARAMETER_KIND or existing["digest"] != digest or existing["status"] != status:
        raise ValueError("Parameter-set version is immutable")
    return version


def current_context_parameters(connection: Connection) -> ParameterSet | None:
    """The newest active artifact, or None: adjustment then degrades to zero."""
    row = connection.execute(select(parameter_sets.c.parameters).where(
        parameter_sets.c.kind == CONTEXT_PARAMETER_KIND,
        parameter_sets.c.status.in_(ACTIVE_PARAMETER_STATUSES),
    ).order_by(parameter_sets.c.created_at.desc(), parameter_sets.c.version.desc()).limit(1)).scalar_one_or_none()
    if row is None:
        return None
    try:
        return parameter_set_from_artifact(row)
    except (KeyError, TypeError, ValueError):
        return None

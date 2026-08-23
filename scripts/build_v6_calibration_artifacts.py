#!/usr/bin/env python3
"""Build v6 calibration artifacts from an operator-supplied real corpus.

The command is deliberately fail-closed. It requires a real, already-derived
corpus and never creates fixture data or writes into the repository fixture
directory. The input is either a JSON array of match rows or an object with a
``matches`` array. Rows must identify a player and, for threshold calibration,
an independent session.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import statistics
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.heroes.taxonomy import load_default_taxonomy  # noqa: E402
from app.player_analysis_v6.artifacts import load_context_baseline_artifact  # noqa: E402
from app.player_analysis_v6.calibration import REQUIRED_THRESHOLD_KEYS  # noqa: E402
from app.player_analysis_v6.calibration_corpus import (  # noqa: E402
    load_calibration_corpus,
    migrate_calibration_corpus,
)
from app.player_analysis_v6.calibration_derivation import (  # noqa: E402
    derive_profile_estimates,
    odd_even_session_ids,
)
from app.player_analysis_v6.constants import BASELINE_VERSION, THRESHOLDS_VERSION  # noqa: E402

BASELINE_METRICS = (
    "outcome",
    "involvement_adjusted",
    "finishing_adjusted",
    "death_exposure_adjusted",
)
BASELINE_ALIASES = {
    "involvement_adjusted": "involvement_per_minute",
    "finishing_adjusted": "finishing_share",
    "death_exposure_adjusted": "death_exposure_per_ten",
}
EPSILON = 1e-9


def _atomic_json(path: Path, payload: Mapping[str, Any], *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700 if mode == 0o600 else 0o755)
    if mode == 0o600:
        path.parent.chmod(0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if mode is not None:
        temporary.chmod(mode)
    temporary.replace(path)


def _taxonomy_mapping() -> dict[int, dict[str, Any]]:
    taxonomy = load_default_taxonomy()
    return {hero_id: {"functional_jobs": list(hero.roles)} for hero_id, hero in taxonomy.heroes.items()}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _profile_id(row: Mapping[str, Any]) -> Any:
    return row.get("profile_id", row.get("account_id"))


def _session_id(row: Mapping[str, Any], index: int) -> str:
    value = row.get("session_id", row.get("session"))
    return str(value) if value not in (None, "") else f"row-session-{index}"


def _row_metric(row: Mapping[str, Any], key: str) -> float | None:
    metrics = row.get("metrics")
    if isinstance(metrics, Mapping):
        direct = _number(metrics.get(key))
        if direct is not None:
            return direct
        alias = BASELINE_ALIASES.get(key)
        if alias is not None:
            aliased = _number(metrics.get(alias))
            if aliased is not None:
                return aliased
    direct = _number(row.get(key))
    if direct is not None:
        return direct
    alias = BASELINE_ALIASES.get(key)
    if alias is not None:
        return _number(row.get(alias))
    return None


def _quantile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot calibrate a metric with no finite observations")
    position = (len(ordered) - 1) * p
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _rows(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read calibration corpus: {path}") from exc
    values = payload.get("matches") if isinstance(payload, Mapping) else payload
    if not isinstance(values, list) or not values or not all(isinstance(item, dict) for item in values):
        raise ValueError("calibration corpus must contain a non-empty matches array")
    if not all(_profile_id(item) is not None for item in values):
        raise ValueError("every calibration row must include profile_id or account_id")
    if len({_profile_id(item) for item in values}) < 2:
        raise ValueError("calibration corpus must contain at least two distinct profiles")
    return values


def _stable_int(value: Any) -> int:
    return int.from_bytes(hashlib.sha256(repr(value).encode("utf-8")).digest()[:8], "big")


def _hero_concentration(rows: list[Mapping[str, Any]]) -> str:
    heroes = [row.get("hero_id") for row in rows if row.get("hero_id") is not None]
    if not heroes:
        return "unknown"
    share = max(Counter(heroes).values()) / len(heroes)
    return "high" if share >= 0.60 else "medium" if share >= 0.35 else "low"


def _stratum(rows: list[Mapping[str, Any]]) -> tuple[str, str, str, str]:
    regions = Counter(str(row.get("region")) for row in rows if row.get("region") is not None)
    lobbies = Counter(str(row.get("lobby_type", row.get("lobby"))) for row in rows if row.get("lobby_type", row.get("lobby")) is not None)
    return (
        "high" if len(rows) >= 200 else "medium" if len(rows) >= 80 else "low",
        _hero_concentration(rows),
        regions.most_common(1)[0][0] if regions else "unknown",
        lobbies.most_common(1)[0][0] if lobbies else "unknown",
    )


def split_profiles(rows: list[dict[str, Any]], *, seed: int) -> tuple[set[Any], set[Any]]:
    """Return a deterministic, player-exclusive stratified 70/30 split."""

    by_profile: dict[Any, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_profile[_profile_id(row)].append(row)
    profiles = sorted(by_profile, key=repr)
    if len(profiles) < 2:
        raise ValueError("calibration split requires at least two profiles")
    groups: dict[tuple[str, str, str, str], list[Any]] = defaultdict(list)
    for profile in profiles:
        groups[_stratum(by_profile[profile])].append(profile)
    for key, members in groups.items():
        random.Random(seed ^ _stable_int(key)).shuffle(members)

    target_train = max(1, min(len(profiles) - 1, round(len(profiles) * 0.70)))
    train: set[Any] = set()
    for members in groups.values():
        count = int(math.floor(len(members) * 0.70))
        if len(members) >= 2:
            count = max(1, min(len(members) - 1, count))
        train.update(members[:count])
    remaining = [profile for profile in profiles if profile not in train]
    while len(train) < target_train and remaining:
        train.add(remaining.pop(0))
    while len(train) > target_train:
        candidates = sorted(train, key=lambda item: (_stratum(by_profile[item]), repr(item)), reverse=True)
        for profile in candidates:
            group = groups[_stratum(by_profile[profile])]
            if sum(member in train for member in group) > (1 if len(group) >= 2 else 0):
                train.remove(profile)
                break
        else:
            break
    return train, set(profiles).difference(train)


def _cell_key(row: Mapping[str, Any], level: str) -> tuple[Any, ...]:
    dimensions = {
        "patch+hero+lane": ("patch", "hero_id", "lane_context"),
        "patch+hero_function+lane": ("patch", "hero_function", "lane_context"),
        "patch+hero": ("patch", "hero_id"),
        "patch+lane": ("patch", "lane_context"),
        "patch": ("patch",),
        "overall": (),
    }[level]
    return tuple(row.get(key) for key in dimensions)


def build_baseline(rows: list[dict[str, Any]], *, train_profiles: set[Any] | None = None, generated_at: str | None = None) -> dict[str, Any]:
    source_rows = [row for row in rows if train_profiles is None or _profile_id(row) in train_profiles]
    grouped: dict[tuple[str, tuple[Any, ...]], list[dict[str, Any]]] = defaultdict(list)
    for row in source_rows:
        for level in ("patch+hero+lane", "patch+hero_function+lane", "patch+hero", "patch+lane", "patch", "overall"):
            dimensions = _cell_key(row, level)
            if level != "overall" and any(value is None for value in dimensions):
                continue
            grouped[(level, dimensions)].append(row)
    cells: list[dict[str, Any]] = []
    for (level, dimensions), group in sorted(grouped.items(), key=lambda item: repr(item[0])):
        metrics: dict[str, float] = {}
        for metric in BASELINE_METRICS:
            values = [value for row in group if (value := _row_metric(row, metric)) is not None]
            if values:
                metrics[metric] = statistics.fmean(values)
                alias = BASELINE_ALIASES.get(metric)
                if alias:
                    metrics[alias] = metrics[metric]
        if not metrics:
            continue
        patch = dimensions[0] if level != "overall" else None
        hero_id = dimensions[1] if level in {"patch+hero+lane", "patch+hero"} else None
        hero_function = dimensions[1] if level == "patch+hero_function+lane" else None
        lane_context = dimensions[-1] if level in {"patch+hero+lane", "patch+hero_function+lane", "patch+lane"} else None
        cells.append({
            "level": level,
            "patch": patch,
            "hero_id": hero_id,
            "hero_function": hero_function,
            "lane_context": lane_context,
            "metrics": metrics,
            "match_count": len(group),
            "distinct_players": len({_profile_id(row) for row in group}),
            "source_version": "context-baseline-2.0.0",
        })
    if not cells:
        raise ValueError("the training corpus did not contain any finite baseline metrics")
    regions = sorted({str(row["region"]) for row in source_rows if row.get("region") is not None})
    lobby_values = [str(row.get("lobby_type", row.get("lobby"))) for row in source_rows if row.get("lobby_type", row.get("lobby")) is not None]
    lobby_counts = Counter(lobby_values)
    total = sum(lobby_counts.values()) or 1
    return {
        "version": BASELINE_VERSION,
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "corpus": {
            "profile_count": len({_profile_id(row) for row in source_rows}),
            "match_count": len(source_rows),
            "regions": regions,
            "lobby_mix": {key: count / total for key, count in sorted(lobby_counts.items())},
            "mmr_used": False,
        },
        "cells": cells,
    }


def _session_id_for_row(row: Mapping[str, Any], index: int) -> str:
    return _session_id(row, index)


def _session_noise(rows: list[dict[str, Any]], key: str) -> list[float]:
    by_profile: dict[Any, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for index, row in enumerate(rows):
        value = _row_metric(row, key)
        if value is not None:
            by_profile[_profile_id(row)][_session_id_for_row(row, index)].append(value)
    noise: list[float] = []
    for sessions in by_profile.values():
        ordered = sorted(sessions, key=repr)
        odd = [statistics.fmean(sessions[session]) for position, session in enumerate(ordered, start=1) if position % 2 == 1 and sessions[session]]
        even = [statistics.fmean(sessions[session]) for position, session in enumerate(ordered, start=1) if position % 2 == 0 and sessions[session]]
        if odd and even:
            noise.append(abs(statistics.fmean(odd) - statistics.fmean(even)))
    return noise


def _player_estimates(rows: list[dict[str, Any]], key: str) -> list[float]:
    grouped: dict[Any, list[float]] = defaultdict(list)
    for row in rows:
        value = _row_metric(row, key)
        if value is not None:
            grouped[_profile_id(row)].append(value)
    return [statistics.fmean(values) for values in grouped.values() if values]


def _player_dispersion(rows: list[dict[str, Any]], key: str) -> list[float]:
    grouped: dict[Any, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for index, row in enumerate(rows):
        value = _row_metric(row, key)
        if value is not None:
            grouped[_profile_id(row)][_session_id_for_row(row, index)].append(value)
    values: list[float] = []
    for sessions in grouped.values():
        session_means = [statistics.fmean(items) for items in sessions.values() if items]
        if len(session_means) < 2:
            continue
        median = statistics.median(session_means)
        deviations = [abs(value - median) for value in session_means]
        values.append(statistics.median(deviations) / abs(median) if abs(median) > EPSILON else statistics.median(deviations))
    return values


def _coverage_for(key: str) -> float:
    if key == "toolkit_effective_count" or key in {"involvement_adjusted", "finishing_adjusted", "death_exposure_adjusted"}:
        return 0.80
    if key.startswith("transfer_"):
        return 0.70
    if key.startswith(("consistency_", "post_loss_", "session_drift_")):
        return 0.50
    return 0.0


def _min_sessions_for(key: str) -> int:
    if key.startswith(("consistency_", "post_loss_", "session_drift_")):
        return 12
    if key.startswith("transfer_") or key in {
        "involvement_adjusted",
        "finishing_adjusted",
        "death_exposure_adjusted",
    }:
        return 8
    return 1


def build_thresholds(
    rows: list[dict[str, Any]],
    *,
    train_profiles: set[Any] | None = None,
    holdout_profiles: set[Any] | None = None,
    seed: int = 0,
) -> dict[str, Any]:
    if train_profiles is None:
        train_profiles, holdout_profiles = split_profiles(rows, seed=seed)
    holdout_profiles = holdout_profiles or set()
    train = [row for row in rows if _profile_id(row) in train_profiles]
    if not train_profiles or not holdout_profiles:
        raise ValueError("threshold calibration requires non-empty training and holdout profiles")
    metrics: dict[str, dict[str, Any]] = {}
    for key in REQUIRED_THRESHOLD_KEYS:
        values = _player_dispersion(train, key) if key.startswith("consistency_") else _player_estimates(train, key)
        finite_rows = [value for row in train if (value := _row_metric(row, key)) is not None]
        if len(finite_rows) < 20 or len(values) < 2:
            raise ValueError(f"metric {key!r} needs at least 20 rows and two player estimates")
        noise = _session_noise(train, key)
        if not noise:
            raise ValueError(f"metric {key!r} has no usable odd/even session noise sample")
        margin = max(EPSILON, _quantile(noise, 0.90) / 2.0)
        zone_mode = "dispersion" if key.startswith("consistency_") else "cutoff" if key in {"breadth_effective_count", "toolkit_effective_count"} else "centered"
        low_cutoff: float | None = None
        high_cutoff: float | None = None
        stable_cutoff: float | None = None
        variable_cutoff: float | None = None
        if zone_mode == "dispersion":
            stable_cutoff = _quantile(values, 1 / 3)
            variable_cutoff = _quantile(values, 2 / 3)
            if variable_cutoff <= stable_cutoff:
                center = statistics.median(values)
                stable_cutoff, variable_cutoff = center - margin, center + margin
        elif zone_mode == "cutoff":
            low_cutoff, high_cutoff = _quantile(values, 1 / 3), _quantile(values, 2 / 3)
            if high_cutoff - low_cutoff < 2 * margin:
                center = statistics.median(values)
                low_cutoff, high_cutoff = center - margin, center + margin
        else:
            low_cutoff, high_cutoff = -margin, margin
        metrics[key] = {
            "zone_mode": zone_mode,
            "practical_margin": margin,
            "low_cutoff": low_cutoff,
            "high_cutoff": high_cutoff,
            "min_sample": 30,
            "min_sessions": _min_sessions_for(key),
            "min_coverage": _coverage_for(key),
            "moderate_stability": 0.75,
            "high_stability": 0.90,
            "version": THRESHOLDS_VERSION,
            **({"stable_cutoff": stable_cutoff, "variable_cutoff": variable_cutoff} if zone_mode == "dispersion" else {}),
        }
    return {
        "version": THRESHOLDS_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "derivation": {
            "train_profile_count": len(train_profiles),
            "holdout_profile_count": len(holdout_profiles),
            "split_method": "player-level-70-30",
            "noise_method": "session-odd-even-split",
            "mmr_used": False,
        },
        "metrics": metrics,
    }


def build_thresholds_from_raw_corpus(
    rows: list[dict[str, Any]],
    *,
    train_profiles: set[Any],
    holdout_profiles: set[Any],
    baseline_path: Path,
    generated_at: str,
    checkpoint_dir: Path | None = None,
    completed_sessions_by_profile: Mapping[str, Mapping[str, bool]] | None = None,
    corpus_checksum: str = "",
    workers: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive full/A/B player estimates from raw rows, never holdout outcomes."""

    resolver = load_context_baseline_artifact(baseline_path).resolver()
    taxonomy = _taxonomy_mapping()
    by_profile: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if _profile_id(row) in train_profiles:
            by_profile[_profile_id(row)].append(row)
    checkpoint_path = checkpoint_dir / "player-estimates.jsonl" if checkpoint_dir else None
    completed: dict[str, dict[str, Any]] = {}
    input_digest = hashlib.sha256(
        b"v6-calibration-derivation-1.0.0\0"
        + corpus_checksum.encode("ascii")
        + json.dumps(sorted(map(str, train_profiles)), separators=(",", ":")).encode("utf-8")
        + baseline_path.read_bytes()
    ).hexdigest()
    if checkpoint_path and checkpoint_path.exists():
        lines = checkpoint_path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                if index == len(lines) - 1:
                    break
                raise
            if record.get("input_digest") != input_digest:
                raise ValueError("threshold checkpoint input checksum mismatch")
            completed[str(record["profile_digest"])] = record
    ordered_profiles = sorted(train_profiles, key=repr)

    def derive_record(profile_id: Any) -> dict[str, Any]:
        profile_digest = hashlib.sha256(str(profile_id).encode("utf-8")).hexdigest()
        if profile_digest in completed:
            return completed[profile_digest]
        profile_rows = by_profile[profile_id]
        odd_ids, even_ids = odd_even_session_ids(profile_rows)
        subsets = {
            "full": profile_rows,
            "a": [row for row in profile_rows if str(row["session_id"]) in odd_ids],
            "b": [row for row in profile_rows if str(row["session_id"]) in even_ids],
        }
        derived: dict[str, Any] = {}
        completion = dict((completed_sessions_by_profile or {}).get(str(profile_id), {}))
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
            derived[name] = {
                key: {
                    "value": estimate.value,
                    "usable_count": estimate.usable_count,
                    "independent_sessions": estimate.independent_sessions,
                    "coverage": estimate.coverage,
                    "unavailable_reason": estimate.unavailable_reason,
                }
                for key, estimate in estimates.metrics.items()
            }
        record = {"input_digest": input_digest, "profile_digest": profile_digest, "estimates": derived}
        return record

    executor: ThreadPoolExecutor | None = None
    try:
        if workers > 1:
            executor = ThreadPoolExecutor(max_workers=workers)
            derived_records = executor.map(derive_record, ordered_profiles)
        else:
            derived_records = map(derive_record, ordered_profiles)
        records: list[dict[str, Any]] = []
        for position, record in enumerate(derived_records, start=1):
            records.append(record)
            profile_digest = str(record["profile_digest"])
            if checkpoint_path and profile_digest not in completed:
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                checkpoint_path.parent.chmod(0o700)
                descriptor = os.open(checkpoint_path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
                try:
                    os.write(descriptor, (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                checkpoint_path.chmod(0o600)
            if position % 25 == 0 or position == len(train_profiles):
                print(f"derived aggregate training progress: {position}/{len(train_profiles)} profiles", flush=True)
    finally:
        if executor is not None:
            executor.shutdown(wait=True)
    metrics: dict[str, dict[str, Any]] = {}
    diagnostics: dict[str, Any] = {}
    for key in REQUIRED_THRESHOLD_KEYS:
        full = [float(record["estimates"]["full"][key]["value"]) for record in records if record["estimates"]["full"][key]["value"] is not None]
        noise = [
            abs(float(record["estimates"]["a"][key]["value"]) - float(record["estimates"]["b"][key]["value"]))
            for record in records
            if record["estimates"]["a"][key]["value"] is not None and record["estimates"]["b"][key]["value"] is not None
        ]
        if not full or not noise:
            reasons = Counter(
                record["estimates"]["full"][key]["unavailable_reason"] or "available"
                for record in records
            )
            raise ValueError(f"metric {key!r} has no defensible training distribution/noise sample; aggregate_reasons={dict(reasons)}")
        margin = max(EPSILON, _quantile(noise, 0.90) / 2.0)
        mode = "dispersion" if key.startswith("consistency_") else "cutoff" if key in {"breadth_effective_count", "toolkit_effective_count"} else "centered"
        low = high = stable = variable = None
        fallback = False
        if mode == "dispersion":
            stable, variable = _quantile(full, 1 / 3), _quantile(full, 2 / 3)
            if variable - stable < 2 * margin:
                center, fallback = statistics.median(full), True
                stable, variable = center - margin, center + margin
        elif mode == "cutoff":
            low, high = _quantile(full, 1 / 3), _quantile(full, 2 / 3)
            if high - low < 2 * margin:
                center, fallback = statistics.median(full), True
                low, high = center - margin, center + margin
        else:
            low, high = -margin, margin
        metrics[key] = {
            "zone_mode": mode, "practical_margin": margin, "low_cutoff": low, "high_cutoff": high,
            "min_sample": 30, "min_sessions": _min_sessions_for(key),
            "min_coverage": _coverage_for(key), "moderate_stability": 0.75, "high_stability": 0.90,
            "version": THRESHOLDS_VERSION,
            **({"stable_cutoff": stable, "variable_cutoff": variable} if mode == "dispersion" else {}),
        }
        reasons = Counter(record["estimates"]["full"][key]["unavailable_reason"] or "available" for record in records)
        diagnostics[key] = {"full_estimate_count": len(full), "split_pair_count": len(noise), "margin": margin, "fallback_used": fallback, "missing_reasons": dict(sorted(reasons.items()))}
    return ({
        "version": THRESHOLDS_VERSION, "generated_at": generated_at,
        "derivation": {"train_profile_count": len(train_profiles), "holdout_profile_count": len(holdout_profiles), "split_method": "player-level-70-30", "noise_method": "session-odd-even-split", "mmr_used": False},
        "metrics": metrics,
    }, diagnostics)


def build_evaluation(rows: list[dict[str, Any]], train: set[Any], holdout: set[Any], thresholds: Mapping[str, Any]) -> dict[str, Any]:
    holdout_rows = [row for row in rows if _profile_id(row) in holdout]
    return {
        "version": "calibration-evaluation-6.0.0",
        "release_ready": False,
        "status": "external-review-required",
        "corpus": {"profile_count": len(train | holdout), "train_profile_count": len(train), "holdout_profile_count": len(holdout), "holdout_match_count": len(holdout_rows)},
        "gates": {
            "minimum_profiles": {"required": 1000, "observed": len(train | holdout), "passed": len(train | holdout) >= 1000},
            "interval_empirical_coverage_93_97": {"observed": None, "passed": False},
            "family_fdr_at_most_5_percent": {"observed": None, "passed": False},
            "nonblank_identity_at_least_80_percent": {"observed": None, "passed": False},
            "split_half_agreement_at_least_80_percent": {"observed": None, "passed": False},
            "forbidden_copy_violations": {"observed": 0, "passed": True},
            "mmr_used": {"observed": False, "passed": True},
        },
        "per_metric_coverage": {
            key: {
                "holdout_rows": sum(_row_metric(row, key) is not None for row in holdout_rows),
                "holdout_profiles": len({_profile_id(row) for row in holdout_rows if _row_metric(row, key) is not None}),
            }
            for key in thresholds
        },
    }


def _staged_main(command: str, argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=f"{Path(__file__).name} {command}")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=6000)
    parser.add_argument("--generated-at", default="2000-01-01T00:00:00+00:00")
    if command == "migrate":
        parser.add_argument("--output", type=Path, required=True)
        args = parser.parse_args(argv)
        diagnostics = migrate_calibration_corpus(args.input, args.output)
        print(json.dumps(diagnostics, sort_keys=True))
        return 0
    if command == "validate":
        parser.add_argument("--split-manifest", type=Path)
        parser.add_argument(
            "--split-source",
            type=Path,
            help="validated legacy source used only to preserve an already-established split across migration",
        )
        args = parser.parse_args(argv)
        corpus = load_calibration_corpus(args.input)
        split_rows: list[dict[str, Any]] = _rows(args.split_source) if args.split_source else [dict(row) for row in corpus.matches]
        if {_profile_id(row) for row in split_rows} != set(corpus.profile_ids):
            raise ValueError("split source and validated corpus have different profile populations")
        train, holdout = split_profiles(split_rows, seed=args.seed)
        manifest_path = args.split_manifest or args.input.parent / "manifests" / f"split-{args.seed}.json"
        manifest = {
            "version": "v6-player-split-1.0.0", "seed": args.seed, "algorithm": "player-level-stratified-70-30",
            "corpus_sha256": corpus.checksum,
            "split_source_sha256": hashlib.sha256(args.split_source.read_bytes()).hexdigest() if args.split_source else corpus.checksum,
            "train_profile_ids": sorted(map(str, train)), "holdout_profile_ids": sorted(map(str, holdout)),
            "train_digest": hashlib.sha256("\n".join(sorted(map(str, train))).encode()).hexdigest(),
            "holdout_digest": hashlib.sha256("\n".join(sorted(map(str, holdout))).encode()).hexdigest(),
            "train_profile_count": len(train), "holdout_profile_count": len(holdout),
        }
        _atomic_json(manifest_path, manifest, mode=0o600)
        print(json.dumps({**corpus.aggregate_diagnostics(), "train_profile_count": len(train), "holdout_profile_count": len(holdout), "split_manifest": str(manifest_path)}, sort_keys=True))
        return 0
    parser.add_argument("--split-manifest", type=Path, required=True)
    if command == "baseline":
        parser.add_argument("--baseline-output", type=Path, required=True)
        args = parser.parse_args(argv)
        corpus = load_calibration_corpus(args.input)
        split = json.loads(args.split_manifest.read_text(encoding="utf-8"))
        if split.get("corpus_sha256") != corpus.checksum:
            raise ValueError("split manifest corpus checksum mismatch")
        baseline = build_baseline([dict(row) for row in corpus.matches], train_profiles=set(split["train_profile_ids"]), generated_at=args.generated_at)
        _atomic_json(args.baseline_output, baseline, mode=0o600)
        print(f"wrote candidate v6 baseline: {args.baseline_output}")
        return 0
    if command == "thresholds":
        parser.add_argument("--baseline-input", type=Path, required=True)
        parser.add_argument("--threshold-output", type=Path, required=True)
        parser.add_argument("--checkpoint-dir", type=Path)
        parser.add_argument("--workers", type=int, default=1)
        args = parser.parse_args(argv)
        if args.workers < 1:
            parser.error("--workers must be positive")
        corpus = load_calibration_corpus(args.input)
        split = json.loads(args.split_manifest.read_text(encoding="utf-8"))
        if split.get("corpus_sha256") != corpus.checksum:
            raise ValueError("split manifest corpus checksum mismatch")
        thresholds, diagnostics = build_thresholds_from_raw_corpus(
            [dict(row) for row in corpus.matches], train_profiles=set(split["train_profile_ids"]), holdout_profiles=set(split["holdout_profile_ids"]),
            baseline_path=args.baseline_input, generated_at=args.generated_at, checkpoint_dir=args.checkpoint_dir,
            completed_sessions_by_profile=corpus.completed_sessions_by_profile,
            corpus_checksum=corpus.checksum,
            workers=args.workers,
        )
        _atomic_json(args.threshold_output, thresholds, mode=0o600)
        diagnostics_path = args.threshold_output.with_name("threshold-derivation-diagnostics-6.0.0.json")
        _atomic_json(diagnostics_path, diagnostics, mode=0o600)
        print(f"wrote candidate v6 thresholds: {args.threshold_output}")
        return 0
    parser.error(f"unsupported command {command}")


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"migrate", "validate", "baseline", "thresholds"}:
        return _staged_main(sys.argv[1], sys.argv[2:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="real calibration corpus JSON")
    parser.add_argument("--output-dir", type=Path, help="legacy convenience directory for three outputs")
    parser.add_argument("--baseline-output", type=Path, help="context-baseline-2.0.0.json output path")
    parser.add_argument("--threshold-output", type=Path, help="metric-thresholds-6.0.0.json output path")
    parser.add_argument("--evaluation-output", type=Path, help="machine-readable holdout evaluation output path")
    parser.add_argument("--seed", type=int, default=6000, help="deterministic player split seed")
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="write the training-only context baseline without deriving thresholds",
    )
    args = parser.parse_args()
    output_dir = args.output_dir
    baseline_path = args.baseline_output or (output_dir / "context-baseline-2.0.0.json" if output_dir else None)
    threshold_path = args.threshold_output or (output_dir / "metric-thresholds-6.0.0.json" if output_dir else None)
    if baseline_path is None or (threshold_path is None and not args.baseline_only):
        parser.error("provide --output-dir or the required explicit output paths")
    rows = _rows(args.input)
    train, holdout = split_profiles(rows, seed=args.seed)
    baseline = build_baseline(rows, train_profiles=train)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote v6 baseline: {baseline_path}")
    if args.baseline_only:
        return 0
    assert threshold_path is not None
    thresholds = build_thresholds(rows, train_profiles=train, holdout_profiles=holdout, seed=args.seed)
    evaluation = build_evaluation(rows, train, holdout, thresholds["metrics"])
    threshold_path.parent.mkdir(parents=True, exist_ok=True)
    threshold_path.write_text(json.dumps(thresholds, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    evaluation_path = args.evaluation_output or threshold_path.parent / "calibration-evaluation-6.0.0.json"
    evaluation_path.parent.mkdir(parents=True, exist_ok=True)
    evaluation_path.write_text(json.dumps(evaluation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote v6 thresholds: {threshold_path}")
    print(f"wrote calibration evaluation: {evaluation_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

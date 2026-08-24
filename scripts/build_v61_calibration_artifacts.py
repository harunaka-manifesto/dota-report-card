#!/usr/bin/env python3
"""Build deterministic training-only V6.1 candidate artifacts.

This command is fixture-capable for State A and real-corpus-capable for the
future State B workflow. It never authorizes release and never derives bytes
from holdout rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.player_analysis_v61.artifacts import (  # noqa: E402
    load_context_baseline_artifact_v61,
    load_threshold_artifact_v61,
)
from app.player_analysis_v61.semantic_outcomes import (  # noqa: E402
    SEMANTIC_OUTCOME_CATALOG,
)
from app.player_analysis_v61.versions import version  # noqa: E402
from build_v6_calibration_artifacts import (  # noqa: E402
    _profile_id,
    build_baseline,
    build_thresholds,
    split_profiles,
)

BUILDER_VERSION = "v61-calibration-builder-1.0.0"
PRIOR_VERSION = "summary-priors-6.1.0"
DISTANCE_VERSION = "portfolio-distance-calibration-1.0.0"
SEMANTIC_ARTIFACT_VERSION = "semantic-outcome-calibration-1.0.0"
SPLIT_VERSION = "v61-player-split-1.0.0"


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _checksum(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(_canonical_bytes(payload))
    temporary.chmod(0o600)
    temporary.replace(path)


def _load_rows(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read V6.1 calibration corpus: {path}") from exc
    rows = payload.get("matches") if isinstance(payload, Mapping) else payload
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("V6.1 calibration corpus needs a non-empty matches array")
    forbidden = {"rank", "rank_tier", "average_rank", "mmr", "skill_bracket", "medal"}

    def inspect(value: Any) -> None:
        if isinstance(value, Mapping):
            leaked = forbidden.intersection(str(key).casefold() for key in value)
            if leaked:
                raise ValueError(f"rank/MMR dimensions are forbidden: {sorted(leaked)}")
            for nested in value.values():
                inspect(nested)
        elif isinstance(value, list):
            for nested in value:
                inspect(nested)

    inspect(rows)
    if any(_profile_id(row) is None for row in rows):
        raise ValueError("every V6.1 calibration row needs profile_id")
    return [dict(row) for row in rows]


def _profile_digest(values: Sequence[Any]) -> str:
    encoded = "\n".join(sorted(map(str, values))).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _numbers(rows: Sequence[Mapping[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        metrics = row.get("metrics")
        value = metrics.get(key) if isinstance(metrics, Mapping) else row.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            values.append(float(value))
    return values


def _quantile(values: Sequence[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _v61_baseline(
    rows: list[dict[str, Any]], train: set[Any], generated_at: str
) -> dict[str, Any]:
    payload = build_baseline(rows, train_profiles=train, generated_at=generated_at)
    payload["version"] = version("context_baseline")
    for cell in payload["cells"]:
        cell["source_version"] = version("context_baseline")
    payload["corpus"].update(
        {
            "builder_version": BUILDER_VERSION,
            "train_profile_digest": _profile_digest(list(train)),
            "training_only": True,
        }
    )
    return payload


def _v61_thresholds(
    rows: list[dict[str, Any]],
    train: set[Any],
    holdout: set[Any],
    seed: int,
    generated_at: str,
) -> dict[str, Any]:
    payload = build_thresholds(
        rows,
        train_profiles=train,
        holdout_profiles=holdout,
        seed=seed,
    )
    payload["version"] = version("thresholds")
    payload["generated_at"] = generated_at
    payload["derivation"].update(
        {
            "builder_version": BUILDER_VERSION,
            "train_profile_digest": _profile_digest(list(train)),
            "training_only": True,
        }
    )
    for metric in payload["metrics"].values():
        metric["version"] = version("thresholds")
    return payload


def _prior_artifact(train_rows: Sequence[Mapping[str, Any]], train: set[Any]) -> dict[str, Any]:
    shares = _numbers(train_rows, "finishing_share")
    center = statistics.fmean(shares) if shares else 0.5
    strength = max(2.0, min(50.0, math.sqrt(max(1, len(shares)))))
    return {
        "version": PRIOR_VERSION,
        "builder_version": BUILDER_VERSION,
        "training_only": True,
        "train_profile_digest": _profile_digest(list(train)),
        "finishing_beta_binomial": {
            "alpha": round(max(0.001, center * strength), 8),
            "beta": round(max(0.001, (1 - center) * strength), 8),
            "training_observations": len(shares),
        },
    }


def _distance_artifact(train_rows: Sequence[Mapping[str, Any]], train: set[Any]) -> dict[str, Any]:
    values = _numbers(train_rows, "transfer_distance")
    return {
        "version": DISTANCE_VERSION,
        "builder_version": BUILDER_VERSION,
        "training_only": True,
        "train_profile_digest": _profile_digest(list(train)),
        "bands": {
            "core": {"maximum": _quantile(values, 1 / 3)},
            "reliable_stretch": {"maximum": _quantile(values, 2 / 3)},
            "experimental_edge": {"maximum": _quantile(values, 1.0)},
        },
        "training_observations": len(values),
        "calibrated": bool(values),
    }


def _semantic_artifact(train: set[Any]) -> dict[str, Any]:
    return {
        "version": SEMANTIC_ARTIFACT_VERSION,
        "builder_version": BUILDER_VERSION,
        "training_only": True,
        "train_profile_digest": _profile_digest(list(train)),
        "family_fdr_q": 0.05,
        "branch_procedure": "qualified-family-bh",
        "outcomes": [
            {
                "semantic_outcome_key": item.semantic_outcome_key,
                "family": item.family_key,
                "branch": item.hypothesis_branch,
                "rollout_status": item.rollout_status,
            }
            for item in SEMANTIC_OUTCOME_CATALOG
        ],
    }


def build_candidate_artifacts(
    rows: list[dict[str, Any]], *, seed: int, generated_at: str
) -> dict[str, dict[str, Any]]:
    train, holdout = split_profiles(rows, seed=seed)
    train_rows = [row for row in rows if _profile_id(row) in train]
    artifacts = {
        "context-baseline-3.0.0.json": _v61_baseline(rows, train, generated_at),
        "metric-thresholds-6.1.0.json": _v61_thresholds(
            rows, train, holdout, seed, generated_at
        ),
        "summary-priors-6.1.0.json": _prior_artifact(train_rows, train),
        "portfolio-distance-calibration-1.0.0.json": _distance_artifact(train_rows, train),
        "semantic-outcome-calibration-1.0.0.json": _semantic_artifact(train),
    }
    artifacts["build-manifest-6.1.0.json"] = {
        "version": "v61-calibration-build-manifest-1.0.0",
        "builder_version": BUILDER_VERSION,
        "generated_at": generated_at,
        "seed": seed,
        "split": {
            "version": SPLIT_VERSION,
            "algorithm": "player-exclusive-stratified-70-30",
            "train_profile_count": len(train),
            "holdout_profile_count": len(holdout),
            "train_profile_digest": _profile_digest(list(train)),
            "holdout_profile_digest": _profile_digest(list(holdout)),
            "overlap_count": len(train & holdout),
        },
        "artifacts": {name: _checksum(payload) for name, payload in artifacts.items()},
        "release_authorized": False,
    }
    return artifacts


def _validate_auxiliary(artifacts: Mapping[str, Mapping[str, Any]]) -> None:
    manifest = artifacts["build-manifest-6.1.0.json"]
    if manifest["split"]["overlap_count"] != 0 or manifest["release_authorized"] is not False:
        raise ValueError("V6.1 build manifest must be leak-free and non-authorizing")
    semantic = artifacts["semantic-outcome-calibration-1.0.0.json"]
    expected = {item.semantic_outcome_key for item in SEMANTIC_OUTCOME_CATALOG}
    observed = {item["semantic_outcome_key"] for item in semantic["outcomes"]}
    if observed != expected:
        raise ValueError("V6.1 semantic artifact registry drift")
    for name in (
        "summary-priors-6.1.0.json",
        "portfolio-distance-calibration-1.0.0.json",
        "semantic-outcome-calibration-1.0.0.json",
    ):
        if artifacts[name].get("training_only") is not True:
            raise ValueError(f"{name} must be training-only")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=6100)
    parser.add_argument("--generated-at", default="2000-01-01T00:00:00+00:00")
    args = parser.parse_args()
    rows = _load_rows(args.input)
    artifacts = build_candidate_artifacts(
        rows,
        seed=args.seed,
        generated_at=args.generated_at,
    )
    _validate_auxiliary(artifacts)
    for name, payload in artifacts.items():
        _atomic_json(args.output_dir / name, payload)
    load_context_baseline_artifact_v61(args.output_dir / "context-baseline-3.0.0.json")
    load_threshold_artifact_v61(args.output_dir / "metric-thresholds-6.1.0.json")
    print(json.dumps({"output_dir": str(args.output_dir), "files": sorted(artifacts)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

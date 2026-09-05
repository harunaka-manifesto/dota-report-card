#!/usr/bin/env python3
"""Aggregate-only measurement run over ``pass2_features``' eight dimensions.

For every Pass-2 DISCOVERY account, computes all eight Finding dimensions
from ``scripts.v7_research.pass2_features`` and writes an **aggregate-only**
summary: per dimension, how many players got a value, the median
observation count behind those values, and the p5/p25/p50/p75/p95 of the
value itself (of ``primary`` for a plain dimension; of both ``primary`` and
``secondary`` for a contrast). No per-player row, account, match, or session
identifier is ever written to the output file — this reports population
shape only.

Read-only on the corpus; makes no network call; does not modify
``pass2_tables.py``, ``tables.py``, the contract, the runner, or any Pass-1
artifact.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.v7_research.pass2_features import (  # noqa: E402
    FEATURE_REGISTRY,
    FEATURE_VERSION,
    FeatureResult,
    group_rows_by_account,
)
from scripts.v7_research.pass2_tables import (  # noqa: E402
    is_pass2_product_context,
    iter_pass2_players,
)

DEFAULT_CORPUS_ROOT = ROOT / ".local" / "corpora" / "stratz" / "v7-pass2-2026-09-04" / "canonical"

QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)


def _quantile(ordered: list[float], quantile: float) -> float:
    index = min(len(ordered) - 1, int(quantile * (len(ordered) - 1) + 0.5))
    return ordered[index]


def _describe(values: list[float]) -> dict[str, Any]:
    """Aggregate-only summary of a list of numbers: no raw values kept
    beyond what the summary itself exposes (min/max are themselves single
    real observations by construction, same as ``v7_capability_atlas``'s
    convention)."""

    if not values:
        return {"n": 0}
    ordered = sorted(values)
    summary: dict[str, Any] = {
        "n": len(ordered),
        "mean": round(statistics.fmean(ordered), 4),
        "min": round(ordered[0], 4),
        "max": round(ordered[-1], 4),
    }
    for q in QUANTILES:
        summary[f"p{int(q * 100)}"] = round(_quantile(ordered, q), 4)
    return summary


def _summarize_dimension(
    values: list[float], observation_counts: list[int]
) -> dict[str, Any]:
    return {
        "players_with_a_value": len(values),
        "median_observation_count": (
            statistics.median(observation_counts) if observation_counts else None
        ),
        "value_quantiles": _describe(values),
    }


def build_census(corpus_root: Path) -> dict[str, Any]:
    rows = (
        row
        for row in iter_pass2_players(corpus_root)
        if is_pass2_product_context(row)
    )
    by_account = group_rows_by_account(rows)

    # dimension key -> ("primary" values/obs, "secondary" values/obs or None)
    primary_values: dict[str, list[float]] = {key: [] for key in FEATURE_REGISTRY}
    primary_obs: dict[str, list[int]] = {key: [] for key in FEATURE_REGISTRY}
    secondary_values: dict[str, list[float]] = {key: [] for key in FEATURE_REGISTRY}
    secondary_obs: dict[str, list[int]] = {key: [] for key in FEATURE_REGISTRY}

    players_considered = 0
    for account_rows in by_account.values():
        players_considered += 1
        for key, spec in FEATURE_REGISTRY.items():
            result: FeatureResult | None = spec.fn(account_rows)
            if result is None:
                continue
            primary_values[key].append(result.primary.value)
            primary_obs[key].append(result.primary.observations)
            if result.secondary is not None:
                secondary_values[key].append(result.secondary.value)
                secondary_obs[key].append(result.secondary.observations)

    dimensions: dict[str, Any] = {}
    for key, spec in FEATURE_REGISTRY.items():
        entry: dict[str, Any] = {
            "description": spec.description,
            "report_section": spec.report_section,
            "is_contrast": spec.is_contrast,
            "is_actionable": spec.is_actionable,
            "primary": _summarize_dimension(primary_values[key], primary_obs[key]),
        }
        if spec.is_contrast:
            entry["secondary"] = _summarize_dimension(
                secondary_values[key], secondary_obs[key]
            )
        dimensions[key] = entry

    return {
        "feature_version": FEATURE_VERSION,
        "players_considered": players_considered,
        "dimensions": dimensions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", default=str(DEFAULT_CORPUS_ROOT))
    parser.add_argument(
        "--out",
        default=str(
            ROOT / "docs" / "evidence" / "v7-pass2-feature-census-2026-09-05.json"
        ),
    )
    args = parser.parse_args()

    census = build_census(Path(args.corpus_root))
    out_path = Path(args.out)
    out_path.write_text(json.dumps(census, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    print(f"players_considered: {census['players_considered']}")
    for key, entry in census["dimensions"].items():
        primary = entry["primary"]
        print(
            f"  {key}: n={primary['players_with_a_value']} "
            f"median_obs={primary['median_observation_count']} "
            f"p50={primary['value_quantiles'].get('p50')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

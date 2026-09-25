from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import median
from typing import Any


@dataclass(frozen=True, slots=True)
class CohortAggregate:
    dimensions: dict[str, Any]
    sample_size: int
    distinct_players: int
    estimates: dict[str, float]
    intervals: dict[str, tuple[float, float]]


def aggregate_by_dimensions(
    rows: Iterable[dict[str, Any]],
    dimensions: tuple[str, ...],
    metric_keys: tuple[str, ...],
) -> list[CohortAggregate]:
    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[tuple(row.get(key) for key in dimensions)].append(row)
    result: list[CohortAggregate] = []
    for values, bucket in buckets.items():
        estimates = {
            key: float(median(float(row.get(key) or 0) for row in bucket)) for key in metric_keys
        }
        result.append(
            CohortAggregate(
                dimensions=dict(zip(dimensions, values, strict=True)),
                sample_size=len(bucket),
                distinct_players=len({row.get("account_id") for row in bucket}),
                estimates=estimates,
                intervals={},
            )
        )
    return result

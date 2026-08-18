"""Shared summary-only units for Hero Mirror behavior vectors.

The player reference and every candidate hero use these same observables:
events per minute, kill share inside involvement, deaths per ten minutes, and
one role distribution.  Keeping the units here prevents display labels from
quietly drifting away from the similarity calculation.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from app.ingestion.summary_normalize import NormalizedSummaryMatch

ROLE_KEYS = ("carry", "mid", "offlane", "soft_support", "hard_support", "roamer", "jungle")
INVOLVEMENT_ZONE_CUTOFFS = (0.25, 0.45, 0.70, 0.95)
FINISHING_ZONE_CUTOFFS = (0.25, 0.40, 0.60, 0.75)
DEATH_ZONE_CUTOFFS = (0.50, 0.75, 1.00, 1.35)
INVOLVEMENT_ZONE_LABELS = ("Quiet", "Selective", "Present", "Active", "Everywhere")
FINISHING_ZONE_LABELS = ("Setup", "Support", "Split", "Closer", "Cleanup")
DEATH_ZONE_LABELS = ("Elusive", "Safe", "Mixed", "Exposed", "Frequent")


def row_has_metrics(item: NormalizedSummaryMatch) -> bool:
    return (
        item.duration_seconds is not None
        and item.duration_seconds >= 600
        and item.kills is not None
        and item.deaths is not None
        and item.assists is not None
    )


def events_per_minute(rows: Sequence[NormalizedSummaryMatch]) -> float:
    valid = [item for item in rows if row_has_metrics(item)]
    minutes = sum(float(item.duration_seconds or 0) / 60.0 for item in valid)
    return sum((item.kills or 0) + (item.assists or 0) for item in valid) / max(minutes, 1e-9)


def finishing_kill_share(rows: Sequence[NormalizedSummaryMatch]) -> float:
    valid = [item for item in rows if row_has_metrics(item)]
    kills = sum(item.kills or 0 for item in valid)
    assists = sum(item.assists or 0 for item in valid)
    return kills / max(kills + assists, 1)


def deaths_per_ten_minutes(rows: Sequence[NormalizedSummaryMatch]) -> float:
    valid = [item for item in rows if row_has_metrics(item)]
    minutes = sum(float(item.duration_seconds or 0) / 60.0 for item in valid)
    return sum(item.deaths or 0 for item in valid) / max(minutes / 10.0, 1e-9)


def role_distribution(rows: Sequence[NormalizedSummaryMatch]) -> dict[str, float]:
    counts = Counter(item.role_hint for item in rows if item.role_hint in ROLE_KEYS)
    total = sum(counts.values())
    if not total:
        return {}
    return {role: counts[role] / total for role in ROLE_KEYS}


def aggregate_behavior(rows: Sequence[NormalizedSummaryMatch]) -> dict[str, float]:
    valid = [item for item in rows if row_has_metrics(item)]
    if not valid:
        return {}
    vector = {
        "involvement": events_per_minute(valid),
        "finishing": finishing_kill_share(valid),
        "deaths": deaths_per_ten_minutes(valid),
    }
    vector.update({f"role:{role}": value for role, value in role_distribution(valid).items()})
    return vector


def involvement_label(value: float) -> str:
    return _five_zone(value, INVOLVEMENT_ZONE_CUTOFFS, INVOLVEMENT_ZONE_LABELS)


def finishing_label(value: float) -> str:
    return _five_zone(value, FINISHING_ZONE_CUTOFFS, FINISHING_ZONE_LABELS)


def death_label(value: float) -> str:
    return _five_zone(value, DEATH_ZONE_CUTOFFS, DEATH_ZONE_LABELS)


def role_label(role: str | None) -> str:
    return {
        "carry": "Carry-heavy",
        "mid": "Mid-heavy",
        "offlane": "Offlane-heavy",
        "soft_support": "Support-heavy",
        "hard_support": "Support-heavy",
        "roamer": "Roam-heavy",
        "jungle": "Jungle-heavy",
    }.get(role or "", "Role context mixed")


def behavior_labels(vector: dict[str, float]) -> dict[str, str]:
    role_values = {
        key.removeprefix("role:"): value
        for key, value in vector.items()
        if key.startswith("role:")
    }
    dominant_role = max(role_values.items(), key=lambda item: item[1])[0] if role_values else None
    return {
        "involvement": involvement_label(vector.get("involvement", 0.0)),
        "finishing": finishing_label(vector.get("finishing", 0.5)),
        "deaths": death_label(vector.get("deaths", 1.0)),
        "role_context": role_label(dominant_role),
    }


def _five_zone(value: float, cutoffs: tuple[float, ...], labels: tuple[str, ...]) -> str:
    for index, cutoff in enumerate(cutoffs):
        if value < cutoff:
            return labels[index]
    return labels[-1]


__all__ = [
    "DEATH_ZONE_CUTOFFS",
    "FINISHING_ZONE_CUTOFFS",
    "INVOLVEMENT_ZONE_CUTOFFS",
    "ROLE_KEYS",
    "aggregate_behavior",
    "behavior_labels",
    "deaths_per_ten_minutes",
    "events_per_minute",
    "finishing_kill_share",
    "role_distribution",
    "row_has_metrics",
]

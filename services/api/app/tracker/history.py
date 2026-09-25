"""Previous-only progression reference and current Personal Best ownership."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import cast

from sqlalchemy import Connection

from .metrics import LOWER_IS_BETTER, METRICS

BASELINE_VERSION = "rolling-median-20-v1"


@dataclass(frozen=True)
class Observation:
    match_id: int
    started_at: datetime
    mode: str
    role: str
    metric_id: str
    comparison_value: float | None
    eligible: bool

    def __post_init__(self) -> None:
        if type(self.match_id) is not int or self.match_id <= 0 or self.started_at.tzinfo is None:
            raise ValueError("Observation needs a positive match identity and aware timestamp")
        if self.mode not in {"STANDARD", "TURBO"} or self.role not in {"CARRY", "MID", "OFFLANE", "SUPPORT"}:
            raise ValueError("Invalid progression identity")
        if self.metric_id not in METRICS or not self.metric_id.startswith(self.role.lower() + "."):
            raise ValueError("Metric does not belong to the effective role")
        if self.comparison_value is not None and (type(self.comparison_value) not in {int, float} or not math.isfinite(self.comparison_value)):
            raise ValueError("Nonfinite metric observation")

    @property
    def chronology(self) -> tuple[datetime, int]:
        return self.started_at, self.match_id


def _matching(current: Observation, rows: list[Observation]) -> list[Observation]:
    matching = [row for row in rows if row.eligible and row.comparison_value is not None
                and row.mode == current.mode and row.role == current.role
                and row.metric_id == current.metric_id and row.match_id != current.match_id
                and row.chronology < current.chronology]
    if len({row.match_id for row in matching}) != len(matching):
        raise ValueError("Duplicate historical metric observation")
    return sorted(matching, key=lambda row: row.chronology)


def baseline(current: Observation, rows: list[Observation]) -> dict[str, object]:
    """The finalized match's reference snapshot; never includes its own value."""
    prior = _matching(current, rows)[-20:]
    return {
        "version": BASELINE_VERSION,
        "state": "BASELINE_READY" if len(prior) >= 5 else "BASELINE_BUILDING",
        "prior_count": len(prior),
        "value": median(cast(float, row.comparison_value) for row in prior) if len(prior) >= 5 else None,
        "source_match_ids": [row.match_id for row in prior],
    }


def personal_best(current: Observation, rows: list[Observation], *, celebrate: bool = False) -> dict[str, object]:
    """All-history record; equal values keep the earliest source match."""
    prior = _matching(current, rows)
    if len(prior) < 5:
        return {"state": "BUILDING", "source_match_id": None, "value": None, "new_pb": False}
    candidates = [*prior, current] if current.eligible and current.comparison_value is not None else prior
    if not candidates:
        return {"state": "UNAVAILABLE", "source_match_id": None, "value": None, "new_pb": False}
    ordered = sorted(candidates, key=lambda row: row.chronology)
    best = min(ordered, key=lambda row: cast(float, row.comparison_value)) if current.metric_id in LOWER_IS_BETTER else max(ordered, key=lambda row: cast(float, row.comparison_value))
    previous_best = min(prior, key=lambda row: cast(float, row.comparison_value)) if current.metric_id in LOWER_IS_BETTER else max(prior, key=lambda row: cast(float, row.comparison_value))
    return {
        "state": "READY", "source_match_id": best.match_id,
        "value": best.comparison_value,
        "new_pb": bool(celebrate and current.eligible and best.match_id == current.match_id
                       and best.comparison_value != previous_best.comparison_value),
    }


def load_prior_observations(connection: Connection, *, profile_id: str, current: Observation,
                            analysis_version: str, baseline_version: str) -> list[Observation]:
    """Read current-methodology, finalized, entitled observations from active pointers.

    Call inside the profile-locked ordered finalization transaction. Historical
    acquisitions stay stored when a Pro profile returns to Free scope.
    """
    from sqlalchemy import select, tuple_

    from .schema import account_matches, analyses, metric_observations, profiles
    from .scope import entitled as entitled_history

    profile = connection.execute(select(profiles).where(
        profiles.c.id == profile_id, profiles.c.active.is_(True),
    )).mappings().one()
    prior = account_matches.alias("prior")
    entitled = entitled_history(profile, prior)
    rows = connection.execute(select(
        prior.c.provider_source_match_id, prior.c.provider_started_at, metric_observations.c.comparison_value,
    ).join(analyses, analyses.c.id == prior.c.active_analysis_id).join(
        metric_observations, metric_observations.c.analysis_id == analyses.c.id,
    ).where(
        prior.c.profile_id == profile_id, prior.c.lifecycle == "READY", prior.c.progression == current.mode,
        prior.c.effective_role == current.role, prior.c.match_id != current.match_id,
        tuple_(prior.c.provider_started_at, prior.c.provider_source_match_id) < current.chronology,
        entitled, analyses.c.analysis_version == analysis_version,
        analyses.c.baseline_version == baseline_version,
        metric_observations.c.metric_id == current.metric_id,
        metric_observations.c.metric_version == current.metric_id.rsplit(".", 1)[-1],
        metric_observations.c.comparison_value.is_not(None),
    ).order_by(prior.c.provider_started_at, prior.c.provider_source_match_id)).all()
    return [Observation(match_id, started_at, current.mode, current.role, current.metric_id, value, True)
            for match_id, started_at, value in rows]

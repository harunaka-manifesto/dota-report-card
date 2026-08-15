from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.ingestion.normalize import NormalizedParticipant

ROLE_LABELS = {
    1: "position 1",
    2: "position 2",
    3: "position 3",
    4: "position 4",
    5: "position 5",
}


@dataclass(frozen=True, slots=True)
class RoleInference:
    role: int | None
    probability: float
    method: str
    signals: dict[str, float]

    @property
    def label(self) -> str | None:
        return ROLE_LABELS.get(self.role) if self.role is not None else None


def infer_role(
    participants: Iterable[NormalizedParticipant],
    target_account_id: int,
    *,
    hero_priors: dict[int, dict[int, float]] | None = None,
) -> RoleInference:
    rows = list(participants)
    target = next((row for row in rows if row.account_id == target_account_id), None)
    if target is None:
        return RoleInference(None, 0.0, "unavailable", {})

    lane_role = target.lane_role
    if lane_role in {1, 2, 3}:
        return RoleInference(
            lane_role,
            0.86,
            "parsed_lane_role",
            {"lane_role": 1.0, "economy_rank": _economy_rank(rows, target)},
        )

    economy_order = sorted(rows, key=_economy_score, reverse=True)
    economy_rank = economy_order.index(target) if target in economy_order else len(rows)
    wards = float(target.obs_placed + target.sen_placed)
    support_order = sorted(
        rows, key=lambda row: (row.obs_placed + row.sen_placed, -_economy_score(row)), reverse=True
    )
    support_rank = support_order.index(target) if target in support_order else len(rows)
    signals = {
        "economy_rank": float(economy_rank),
        "support_rank": float(support_rank),
        "ward_events": wards,
        "farm_score": _economy_score(target),
    }

    if lane_role == 4:
        role = 4 if wards >= 2 or economy_rank >= 3 else 3
        return RoleInference(
            role, 0.70 if role == 4 else 0.58, "parsed_lane_role_plus_signals", signals
        )
    if wards >= 4 or support_rank == 0:
        role = 5 if support_rank == 0 and economy_rank >= 3 else 4
        return RoleInference(role, 0.68, "support_signals", signals)

    role = {0: 1, 1: 2, 2: 3}.get(economy_rank, 4 if economy_rank == 3 else 5)
    confidence = 0.64 if len(rows) >= 5 else 0.52
    if hero_priors and target.hero_id is not None and target.hero_id in hero_priors:
        prior = hero_priors[target.hero_id].get(role, 0.0)
        confidence = min(0.84, confidence + prior * 0.12)
        signals["hero_role_prior"] = prior
    return RoleInference(role, confidence, "team_relative_economy_and_support", signals)


def _economy_score(row: NormalizedParticipant) -> float:
    return row.net_worth + row.gold_per_min * 15 + row.last_hits * 4 + row.gold_spent * 0.15


def _economy_rank(rows: list[NormalizedParticipant], target: NormalizedParticipant) -> float:
    ordered = sorted(rows, key=_economy_score, reverse=True)
    return float(ordered.index(target) + 1) if target in ordered else float(len(rows))

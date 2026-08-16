from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ExclusionReason(StrEnum):
    UNSUPPORTED_MODE = "non_standard_mode"
    NON_RANKED = "non_ranked"
    NON_STANDARD_MODE = "non_standard_mode"
    ABANDONED = "abandoned"
    PRO_OR_LEAGUE = "pro_or_league"
    INVALID_DURATION = "invalid_duration"
    MISSING_OUTCOME = "missing_outcome"
    PLAYER_NOT_FOUND = "player_not_found"
    MALFORMED = "malformed"


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    match_id: int | None
    eligible: bool
    reasons: tuple[ExclusionReason, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "eligible": self.eligible,
            "reasons": [reason.value for reason in self.reasons],
        }


ALL_PICK_MODE = 1
RANKED_ALL_PICK_MODE = 22
SUPPORTED_ALL_PICK_MODES = frozenset({ALL_PICK_MODE, RANKED_ALL_PICK_MODE})


def assess_match(
    match: dict[str, Any],
    *,
    detail: dict[str, Any] | None = None,
    account_id: int | None = None,
) -> EligibilityResult:
    detail = detail or {}
    merged = {**match, **{key: value for key, value in detail.items() if value is not None}}
    match_id = _as_int(merged.get("match_id"))
    reasons: list[ExclusionReason] = []

    if match_id is None:
        reasons.append(ExclusionReason.MALFORMED)
    if _as_int(merged.get("game_mode")) not in SUPPORTED_ALL_PICK_MODES:
        reasons.append(ExclusionReason.NON_STANDARD_MODE)
    if merged.get("leagueid") or merged.get("league_id"):
        reasons.append(ExclusionReason.PRO_OR_LEAGUE)

    duration = _as_int(merged.get("duration"))
    if duration is None or duration < 300:
        reasons.append(ExclusionReason.INVALID_DURATION)
    if merged.get("radiant_win") is None and merged.get("won") is None:
        reasons.append(ExclusionReason.MISSING_OUTCOME)

    if account_id is not None and detail:
        players = detail.get("players") or []
        if not any(
            _as_int(row.get("account_id")) == account_id for row in players if isinstance(row, dict)
        ):
            reasons.append(ExclusionReason.PLAYER_NOT_FOUND)

    target = _target_player(detail, account_id)
    if target and _as_int(target.get("leaver_status")) not in (None, 0, 1):
        reasons.append(ExclusionReason.ABANDONED)
    if match.get("leaver_status") not in (None, 0, 1):
        reasons.append(ExclusionReason.ABANDONED)

    return EligibilityResult(match_id, not reasons, tuple(dict.fromkeys(reasons)))


def _target_player(detail: dict[str, Any], account_id: int | None) -> dict[str, Any] | None:
    if account_id is None:
        return None
    return next(
        (
            row
            for row in detail.get("players") or []
            if isinstance(row, dict) and _as_int(row.get("account_id")) == account_id
        ),
        None,
    )


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None

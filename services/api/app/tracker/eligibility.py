"""Match-level progression gate; metric availability is evaluated separately."""
from __future__ import annotations

from dataclasses import dataclass

from .roles import ROLES


@dataclass(frozen=True)
class Eligibility:
    progression: str
    reason: str | None


def classify(*, mode: str, duration_seconds: int, effective_role: str | None,
             leaver_status: int | None, integrity: str | None) -> Eligibility:
    """Require positive competitive-integrity evidence from a separate verifier.

    A scorecard can still be measured when progression is NONE. Unknown source
    status is never treated as a normal competitive match.
    """
    if mode not in {"STANDARD", "TURBO"}:
        return Eligibility("NONE", "UNSUPPORTED_MODE")
    if type(duration_seconds) is not int or duration_seconds < 600:
        return Eligibility("NONE", "SHORT_OR_INVALID_DURATION")
    if leaver_status is None:
        return Eligibility("NONE", "ABANDON_STATUS_UNKNOWN")
    if type(leaver_status) is not int or leaver_status != 0:
        return Eligibility("NONE", "ABANDON_OR_UNFINISHED")
    if effective_role not in set(ROLES.values()):
        return Eligibility("NONE", "ROLE_UNAVAILABLE")
    if integrity != "VALID":
        return Eligibility("NONE", "INTEGRITY_UNKNOWN" if integrity is None else "INTEGRITY_INVALID")
    return Eligibility(mode, None)

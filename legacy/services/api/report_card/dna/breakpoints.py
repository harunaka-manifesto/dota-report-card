"""Breakpoint detection for Session Fade and Session Rise."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

BREAKPOINT_VERSION = "session-breakpoints-5.0.0"
SESSION_BUCKETS = ("G1", "G2", "G3", "G4", "G5+")


@dataclass(frozen=True, slots=True)
class BreakpointResult:
    state: str
    direction: str
    bucket: str | None
    effect: float | None
    supported_buckets: tuple[str, ...]
    version: str = BREAKPOINT_VERSION

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "direction": self.direction,
            "bucket": self.bucket,
            "effect": round(self.effect, 6) if self.effect is not None else None,
            "supported_buckets": list(self.supported_buckets),
            "version": self.version,
        }


def detect_breakpoint(
    curve: Mapping[str, float],
    *,
    direction: str,
    counts: Mapping[str, int] | None = None,
    minimum_effect: float = 0.08,
    minimum_count: int = 8,
    persistence_buckets: Sequence[str] = SESSION_BUCKETS,
) -> BreakpointResult:
    """Find the earliest supported bucket with a persistent directional effect.

    ``curve`` is already relative to the player's context-adjusted baseline.
    The detector never searches for the largest isolated bucket: a candidate
    must have enough coverage and retain the same sign in all later supported
    buckets.
    """

    sign = 1.0 if direction == "rise" else -1.0
    supported = tuple(
        bucket
        for bucket in persistence_buckets
        if bucket in curve and (counts is None or counts.get(bucket, 0) >= minimum_count)
    )
    if len(supported) < 2:
        return BreakpointResult("unresolved", direction, None, None, supported)

    for index, bucket in enumerate(supported):
        effect = float(curve[bucket])
        if sign * effect < minimum_effect:
            continue
        later = [float(curve[item]) for item in supported[index:]]
        if all(sign * value >= minimum_effect for value in later):
            return BreakpointResult("stable_breakpoint", direction, bucket, effect, supported)

    if all(sign * float(curve[item]) >= 0 for item in supported) and any(
        sign * float(curve[item]) >= minimum_effect for item in supported
    ):
        return BreakpointResult("gradual", direction, None, None, supported)
    return BreakpointResult("unresolved", direction, None, None, supported)


__all__ = ["BREAKPOINT_VERSION", "SESSION_BUCKETS", "BreakpointResult", "detect_breakpoint"]

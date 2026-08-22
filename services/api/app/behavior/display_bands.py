"""Deterministic human-readable display bands for Free DNA stories.

The scoring layer keeps its numeric measurements and the presentation layer
owns the translation into a small, reviewed vocabulary.  Keeping the cutoffs
here prevents the API and web app from inventing slightly different meanings
for the same evidence.
"""

from __future__ import annotations

from typing import Literal

RelativePerformanceBand = Literal[
    "very_strong", "strong", "normal", "weak", "very_weak", "unavailable"
]
PresenceBand = Literal["high", "normal", "low", "unavailable"]
DeathExposureBand = Literal["high", "normal", "low", "unavailable"]
SessionCurveBand = Literal[
    "above_usual",
    "about_usual",
    "below_usual",
    "lowest_point",
    "slow_start",
    "warming_up",
    "strongest",
    "unavailable",
]

# Boundaries are inclusive at the outside bands and inclusive for the
# neutral interval.  They are deliberately simple enough to audit in a
# catalog review and stable across reports.
RELATIVE_PERFORMANCE_CUTOFFS = {
    "very_weak": -0.30,
    "weak": -0.10,
    "normal_low": 0.10,
    "strong": 0.30,
}
PRESENCE_CUTOFFS = {"low": 0.40, "high": 0.60}
DEATH_EXPOSURE_CUTOFFS = {"low": 0.40, "high": 0.60}

RELATIVE_PERFORMANCE_LABELS: dict[str, str] = {
    "very_strong": "Much stronger than usual",
    "strong": "Stronger than usual",
    "normal": "About usual",
    "weak": "Weaker than usual",
    "very_weak": "Much weaker than usual",
    "unavailable": "Not enough evidence",
}
PRESENCE_LABELS: dict[str, str] = {
    "high": "Shows up often",
    "normal": "About usual",
    "low": "Shows up less",
    "unavailable": "Not enough evidence",
}
DEATH_EXPOSURE_LABELS: dict[str, str] = {
    "high": "High cost",
    "normal": "Typical cost",
    "low": "Low cost",
    "unavailable": "Not enough evidence",
}
SESSION_CURVE_LABELS: dict[str, str] = {
    "above_usual": "Above usual",
    "about_usual": "About usual",
    "below_usual": "Below usual",
    "lowest_point": "Lowest point",
    "slow_start": "Slow start",
    "warming_up": "Warming up",
    "strongest": "Strongest",
    "unavailable": "Not enough evidence",
}
SESSION_BUCKET_LABELS = {
    "G1": "Game 1",
    "G2": "Game 2",
    "G3": "Game 3",
    "G4": "Game 4",
    "G5+": "Game 5+",
}


def relative_performance_band(value: float | int | None) -> RelativePerformanceBand:
    """Classify a relative performance delta without exposing the delta."""

    if value is None:
        return "unavailable"
    numeric = float(value)
    if numeric <= RELATIVE_PERFORMANCE_CUTOFFS["very_weak"]:
        return "very_weak"
    if numeric < RELATIVE_PERFORMANCE_CUTOFFS["weak"]:
        return "weak"
    if numeric <= RELATIVE_PERFORMANCE_CUTOFFS["normal_low"]:
        return "normal"
    if numeric < RELATIVE_PERFORMANCE_CUTOFFS["strong"]:
        return "strong"
    return "very_strong"


def relative_performance_label(value: float | int | None) -> str:
    return RELATIVE_PERFORMANCE_LABELS[relative_performance_band(value)]


def presence_band(value: float | int | None) -> PresenceBand:
    """Classify involvement, where the input is normalized to ``[0, 1]``."""

    if value is None:
        return "unavailable"
    numeric = float(value)
    if numeric >= PRESENCE_CUTOFFS["high"]:
        return "high"
    if numeric < PRESENCE_CUTOFFS["low"]:
        return "low"
    return "normal"


def presence_label(value: float | int | None) -> str:
    return PRESENCE_LABELS[presence_band(value)]


def death_exposure_band(value: float | int | None) -> DeathExposureBand:
    """Classify normalized death exposure for the presence map."""

    if value is None:
        return "unavailable"
    numeric = float(value)
    if numeric >= DEATH_EXPOSURE_CUTOFFS["high"]:
        return "high"
    if numeric < DEATH_EXPOSURE_CUTOFFS["low"]:
        return "low"
    return "normal"


def death_exposure_label(value: float | int | None) -> str:
    return DEATH_EXPOSURE_LABELS[death_exposure_band(value)]


def session_curve_band(
    value: float | int | None, *, direction: Literal["fade", "rise"]
) -> SessionCurveBand:
    """Translate a session delta into the reviewed curve vocabulary."""

    if value is None:
        return "unavailable"
    numeric = float(value)
    if direction == "fade":
        if numeric <= -0.20:
            return "lowest_point"
        if numeric < -0.05:
            return "below_usual"
        if numeric <= 0.05:
            return "about_usual"
        return "above_usual"
    if numeric <= -0.10:
        return "slow_start"
    if numeric < -0.03:
        return "warming_up"
    if numeric <= 0.05:
        return "about_usual"
    if numeric < 0.20:
        return "above_usual"
    return "strongest"


def session_curve_label(
    value: float | int | None, *, direction: Literal["fade", "rise"]
) -> str:
    return SESSION_CURVE_LABELS[session_curve_band(value, direction=direction)]


def session_bucket_label(bucket: str) -> str:
    return SESSION_BUCKET_LABELS.get(bucket, "Session position unavailable")


def job_display_label(value: str) -> str:
    """Convert a taxonomy key to a stable readable label when needed."""

    labels = {
        "global_presence": "Global presence",
        "micro_intensity": "Micro intensity",
        "farm_dependency": "Farm dependence",
        "sustained_damage": "Sustained damage",
        "wave_clear": "Wave clear",
        "frontline": "Frontline",
        "teamfight": "Teamfight",
        "repositioning": "Repositioning",
        "initiation": "Initiation",
        "pickoff": "Pickoff",
        "mobility": "Mobility",
        "save": "Save",
        "sustain": "Sustain",
        "burst": "Burst",
        "push": "Push",
        "scaling": "Scaling",
    }
    return labels.get(value, value.replace("_", " ").capitalize())


__all__ = [
    "DEATH_EXPOSURE_CUTOFFS",
    "DEATH_EXPOSURE_LABELS",
    "PRESENCE_CUTOFFS",
    "PRESENCE_LABELS",
    "RELATIVE_PERFORMANCE_CUTOFFS",
    "RELATIVE_PERFORMANCE_LABELS",
    "SESSION_BUCKET_LABELS",
    "SESSION_CURVE_LABELS",
    "death_exposure_band",
    "death_exposure_label",
    "job_display_label",
    "presence_band",
    "presence_label",
    "relative_performance_band",
    "relative_performance_label",
    "session_bucket_label",
    "session_curve_band",
    "session_curve_label",
]

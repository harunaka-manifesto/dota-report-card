"""Versioned, replaceable V1 baseline cells for summary-only dimensions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

BASELINE_VERSION = "activity-v1.1.0"


@dataclass(frozen=True, slots=True)
class BaselineSnapshot:
    version: str
    activity_by_role: dict[str, float]
    kill_share_by_role: dict[str, float]
    limitations: tuple[str, ...]
    source_cohort: str = "provisional-summary-cohort"
    collection_window: str = "unknown"
    patch_range: str = "7.41e"
    filters: tuple[str, ...] = ()
    sample_size: int = 0
    generation_code_version: str = "baseline-generator-1.1.0"
    review_date: str = "2026-08-16"
    provisional: bool = True

    def activity(self, role: str | None) -> float:
        return self.activity_by_role.get(role or "", self.activity_by_role["default"])

    def kill_share(self, role: str | None) -> float:
        return self.kill_share_by_role.get(role or "", self.kill_share_by_role["default"])


def load_baseline(path: str | Path | None = None) -> BaselineSnapshot:
    source = Path(path) if path else Path(__file__).with_name("baselines") / "activity-v1.json"
    value = json.loads(source.read_text(encoding="utf-8"))
    return BaselineSnapshot(
        version=str(value.get("version", BASELINE_VERSION)),
        activity_by_role={key: float(item) for key, item in value.get("activity_by_role", {}).items()},
        kill_share_by_role={key: float(item) for key, item in value.get("kill_share_by_role", {}).items()},
        limitations=tuple(str(item) for item in value.get("limitations", [])),
        source_cohort=str(value.get("source_cohort", "provisional-summary-cohort")),
        collection_window=str(value.get("collection_window", "unknown")),
        patch_range=str(value.get("patch_range", "7.41e")),
        filters=tuple(str(item) for item in value.get("filters", [])),
        sample_size=int(value.get("sample_size", 0) or 0),
        generation_code_version=str(value.get("generation_code_version", "baseline-generator-1.1.0")),
        review_date=str(value.get("review_date", "2026-08-16")),
        provisional=bool(value.get("provisional", True)),
    )


DEFAULT_BASELINE = load_baseline()

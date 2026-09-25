"""Pure AP/CM story-population selection over retained normalized rows."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.ingestion.summary_normalize import EligibilityFlag, NormalizedSummaryMatch

from .versions import STORY_MODE_MAP_VERSION


class StoryModeMapError(ValueError):
    """Raised when the pinned story mode-map artifact cannot be trusted."""


# This is a deliberately small, reviewed subset of OpenDota's game-mode and
# lobby constants.  The selector must not silently broaden the story universe
# when the upstream constants change.
MODE_MAP_VERSION = STORY_MODE_MAP_VERSION
MODE_MAP_UPSTREAM_COMMIT = "e7705ee975ebec2a88a59a7b455d4cae5dc69ca1"
MODE_MAP_FILENAME = "opendota-mode-map-e7705ee.json"
MODE_MAP_PATH = Path(__file__).with_name("data") / MODE_MAP_FILENAME
MODE_MAP_CATEGORIES: dict[str, tuple[int, int]] = {
    "unranked_all_pick": (1, 0),
    "ranked_all_pick": (22, 7),
    "unranked_captains_mode": (2, 0),
    "ranked_captains_mode": (2, 7),
}
# Bound after the checked-in artifact is written.  This is a byte checksum,
# so formatting or an unexpected edit is treated as artifact drift.
MODE_MAP_SHA256 = "ce78848ca0511309422e560f2db9bd67080b32a165069ca747370c94176e135a"


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StoryModeMapError(f"duplicate mode-map key: {key}")
        result[key] = value
    return result


def validate_mode_map_artifact(payload: Any) -> None:
    """Validate the exact OpenDota mode/lobby subset used by story selection."""

    if not isinstance(payload, Mapping):
        raise StoryModeMapError("OpenDota mode map artifact must be an object")
    expected_keys = {"version", "upstream_commit", "categories"}
    actual_keys = {str(key) for key in payload}
    if actual_keys != expected_keys:
        raise StoryModeMapError(
            "OpenDota mode map artifact fields do not match the pinned schema"
        )
    if payload.get("version") != MODE_MAP_VERSION:
        raise StoryModeMapError(
            f"unsupported OpenDota mode map version: {payload.get('version')!r}"
        )
    if payload.get("upstream_commit") != MODE_MAP_UPSTREAM_COMMIT:
        raise StoryModeMapError("OpenDota mode map upstream commit mismatch")
    categories = payload.get("categories")
    if not isinstance(categories, Mapping):
        raise StoryModeMapError("OpenDota mode map categories must be an object")
    if set(categories) != set(MODE_MAP_CATEGORIES):
        raise StoryModeMapError("OpenDota mode map category registry drift")
    for category, expected_pair in MODE_MAP_CATEGORIES.items():
        value = categories.get(category)
        if not isinstance(value, Mapping) or set(value) != {"game_mode", "lobby_type"}:
            raise StoryModeMapError(f"OpenDota mode map category {category} is malformed")
        game_mode = value.get("game_mode")
        lobby_type = value.get("lobby_type")
        if (
            isinstance(game_mode, bool)
            or not isinstance(game_mode, int)
            or isinstance(lobby_type, bool)
            or not isinstance(lobby_type, int)
            or (game_mode, lobby_type) != expected_pair
        ):
            raise StoryModeMapError(
                f"OpenDota mode map category {category} has an unexpected tuple"
            )


@dataclass(frozen=True, slots=True)
class ModeMapArtifact:
    """The checksum-linked, fail-closed mode map used by story selection."""

    version: str
    upstream_commit: str
    categories: Mapping[str, tuple[int, int]]
    checksum: str

    def category_for(self, game_mode: int | None, lobby_type: int | None) -> str | None:
        if (
            game_mode is None
            or lobby_type is None
            or isinstance(game_mode, bool)
            or isinstance(lobby_type, bool)
        ):
            return None
        pair = (game_mode, lobby_type)
        return next(
            (category for category, category_pair in self.categories.items() if category_pair == pair),
            None,
        )


def load_mode_map_artifact(
    path: str | Path = MODE_MAP_PATH,
    *,
    expected_checksum: str | None = MODE_MAP_SHA256,
) -> ModeMapArtifact:
    """Load and checksum-validate the checked-in OpenDota mode map."""

    artifact_path = Path(path)
    try:
        raw = artifact_path.read_bytes()
    except OSError as exc:
        raise StoryModeMapError(
            f"OpenDota mode map artifact cannot be read: {artifact_path}"
        ) from exc
    checksum = hashlib.sha256(raw).hexdigest()
    if expected_checksum is not None and checksum != expected_checksum:
        raise StoryModeMapError("OpenDota mode map artifact checksum mismatch")
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_duplicate_pairs,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StoryModeMapError(
            f"OpenDota mode map artifact cannot be parsed: {artifact_path}"
        ) from exc
    validate_mode_map_artifact(payload)
    categories = payload["categories"]
    return ModeMapArtifact(
        version=str(payload["version"]),
        upstream_commit=str(payload["upstream_commit"]),
        categories={
            category: (
                int(value["game_mode"]),
                int(value["lobby_type"]),
            )
            for category, value in categories.items()
        },
        checksum=checksum,
    )


@dataclass(frozen=True, slots=True)
class StorySelection:
    """Selected rows plus safe, identifier-free selection diagnostics."""

    matches: tuple[NormalizedSummaryMatch, ...]
    mode_counts: Mapping[str, int]
    excluded_or_unknown_count: int
    exclusion_reasons: Mapping[str, int]
    mode_map_version: str
    mode_map_checksum: str

    @property
    def match_count(self) -> int:
        return len(self.matches)


def select_story_matches(
    matches: Iterable[NormalizedSummaryMatch],
    *,
    mode_map: ModeMapArtifact | None = None,
) -> StorySelection:
    """Select exact AP/CM tuples without changing inferential eligibility.

    The input must be the retained normalized snapshot, not
    ``NormalizationResult.eligible_matches``: Captain's Mode rows are retained
    there with only ``unsupported_game_mode`` on their common flag.  AP rows
    require no common failure; for CM rows that one mode failure is the only
    tolerated reason.  All other normalized failures remain disqualifying.
    """

    artifact = mode_map or load_mode_map_artifact()
    if mode_map is not None:
        validate_mode_map_artifact(
            {
                "version": artifact.version,
                "upstream_commit": artifact.upstream_commit,
                "categories": {
                    category: {"game_mode": pair[0], "lobby_type": pair[1]}
                    for category, pair in artifact.categories.items()
                },
            }
        )
    mode_counts = {category: 0 for category in artifact.categories}
    exclusions: Counter[str] = Counter()
    selected: list[NormalizedSummaryMatch] = []
    excluded_count = 0

    for item in matches:
        category = artifact.category_for(item.game_mode, item.lobby_type)
        if category is None:
            excluded_count += 1
            exclusions["unsupported_mode_lobby_tuple"] += 1
            continue

        eligibility = item.eligibility
        common_flag = eligibility.get("overall") if isinstance(eligibility, Mapping) else None
        if not isinstance(common_flag, EligibilityFlag):
            excluded_count += 1
            exclusions["missing_common_eligibility"] += 1
            continue

        reasons = tuple(str(reason) for reason in common_flag.reasons)
        remaining_reasons = set(reasons)
        is_captains_mode = category in {
            "unranked_captains_mode",
            "ranked_captains_mode",
        }
        if is_captains_mode:
            remaining_reasons.discard("unsupported_game_mode")

        if not common_flag.included and not (is_captains_mode and not remaining_reasons):
            excluded_count += 1
            if not remaining_reasons:
                exclusions["common_ineligible"] += 1
            else:
                exclusions.update(remaining_reasons)
            continue
        if remaining_reasons:
            excluded_count += 1
            exclusions.update(remaining_reasons)
            continue

        selected.append(item)
        mode_counts[category] += 1

    return StorySelection(
        matches=tuple(selected),
        mode_counts=mode_counts,
        excluded_or_unknown_count=excluded_count,
        exclusion_reasons=dict(sorted(exclusions.items())),
        mode_map_version=artifact.version,
        mode_map_checksum=artifact.checksum,
    )


__all__ = [
    "MODE_MAP_CATEGORIES",
    "MODE_MAP_FILENAME",
    "MODE_MAP_PATH",
    "MODE_MAP_SHA256",
    "MODE_MAP_UPSTREAM_COMMIT",
    "MODE_MAP_VERSION",
    "ModeMapArtifact",
    "StoryModeMapError",
    "StorySelection",
    "load_mode_map_artifact",
    "select_story_matches",
    "validate_mode_map_artifact",
]

"""Versioned aggregate hero evidence seams for P02.

The report-time code reads checked-in artifacts only.  The initial repository
ships the schema and a conservative empty snapshot because examples must not
be invented from one player's bounded history.  An offline refresh can add
records without changing the action contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.hero_portfolio.version import (
    HERO_MATCHUPS_VERSION,
    HERO_SITUATIONS_VERSION,
    HERO_SYNERGIES_VERSION,
)

_DATA_ROOT = Path(__file__).with_name("data")
_MATCHUPS_PATH = _DATA_ROOT / "aggregate_matchups.v1.json"
_SYNERGIES_PATH = _DATA_ROOT / "aggregate_synergies.v1.json"


@dataclass(frozen=True, slots=True)
class HeroEvidenceRelationship:
    hero_id: int
    related_hero_id: int
    sample_size: int
    adjusted_score: float
    confidence_score: float
    patch_scope: str
    reason_tags: tuple[str, ...] = ()
    version: str = ""


@lru_cache(maxsize=1)
def load_matchup_artifact() -> tuple[HeroEvidenceRelationship, ...]:
    return _load_artifact(_MATCHUPS_PATH, HERO_MATCHUPS_VERSION)


@lru_cache(maxsize=1)
def load_synergy_artifact() -> tuple[HeroEvidenceRelationship, ...]:
    return _load_artifact(_SYNERGIES_PATH, HERO_SYNERGIES_VERSION)


def representative_matchups(
    hero_id: int,
    *,
    minimum_confidence: float = 0.65,
    limit: int = 3,
) -> tuple[HeroEvidenceRelationship, ...]:
    return _representative(load_matchup_artifact(), hero_id, minimum_confidence, limit)


def representative_synergies(
    hero_id: int,
    *,
    minimum_confidence: float = 0.65,
    limit: int = 3,
) -> tuple[HeroEvidenceRelationship, ...]:
    return _representative(load_synergy_artifact(), hero_id, minimum_confidence, limit)


def situations_for_traits(traits: tuple[str, ...]) -> tuple[str, ...]:
    situations: list[str] = []
    for trait in traits:
        situations.extend(_TRAIT_SITUATIONS.get(trait, ()))
    return tuple(dict.fromkeys(situations))[:3]


def _representative(
    records: tuple[HeroEvidenceRelationship, ...],
    hero_id: int,
    minimum_confidence: float,
    limit: int,
) -> tuple[HeroEvidenceRelationship, ...]:
    return tuple(
        sorted(
            (
                item
                for item in records
                if item.hero_id == hero_id and item.confidence_score >= minimum_confidence
            ),
            key=lambda item: (-item.confidence_score, -item.adjusted_score, -item.sample_size, item.related_hero_id),
        )[: max(0, limit)]
    )


def _load_artifact(path: Path, version: str) -> tuple[HeroEvidenceRelationship, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    if not isinstance(payload, dict) or payload.get("version") != version:
        return ()
    records: list[HeroEvidenceRelationship] = []
    for item in payload.get("records", []):
        if not isinstance(item, dict):
            continue
        try:
            records.append(
                HeroEvidenceRelationship(
                    hero_id=int(item["hero_id"]),
                    related_hero_id=int(item["related_hero_id"]),
                    sample_size=max(0, int(item.get("sample_size", 0))),
                    adjusted_score=float(item.get("adjusted_score", 0.0)),
                    confidence_score=float(item.get("confidence_score", 0.0)),
                    patch_scope=str(item.get("patch_scope", "unknown")),
                    reason_tags=tuple(str(tag) for tag in item.get("reason_tags", [])),
                    version=str(item.get("version", version)),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return tuple(records)


_TRAIT_SITUATIONS: dict[str, tuple[str, ...]] = {
    "initiation": ("the team lacks reliable initiation",),
    "mobility": ("the enemy lineup is highly mobile",),
    "save": ("the team needs save / reset options",),
    "sustain": ("the team needs sustained frontline presence",),
    "wave_clear": ("the team needs wave clear",),
    "push": ("the team needs global pressure or push",),
    "global_presence": ("the team needs global pressure",),
    "burst": ("the enemy backline is difficult to reach",),
    "frontline": ("the team needs stronger frontline presence",),
    "repositioning": ("the team needs stronger disengage",),
    "pickoff": ("the enemy draft is vulnerable to isolated pickoffs",),
}


__all__ = [
    "HERO_MATCHUPS_VERSION",
    "HERO_SITUATIONS_VERSION",
    "HERO_SYNERGIES_VERSION",
    "HeroEvidenceRelationship",
    "load_matchup_artifact",
    "load_synergy_artifact",
    "representative_matchups",
    "representative_synergies",
    "situations_for_traits",
]

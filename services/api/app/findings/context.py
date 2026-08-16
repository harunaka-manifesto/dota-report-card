"""Build the pure input context used by Free finding synthesis."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.dna.pipeline import DnaAnalysisResult
from app.features.summary_calculators import calculate_summary_features
from app.features.summary_models import SummaryFeatureSet
from app.heroes.taxonomy import load_default_taxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch
from app.patterns.models import PatternCandidate


@dataclass(frozen=True, slots=True)
class FreeFindingContext:
    """All summary-safe inputs required to evaluate a Free finding."""

    dna: DnaAnalysisResult
    summary_features: SummaryFeatureSet
    patterns: tuple[PatternCandidate, ...]
    eligible_matches: int
    processed_matches: int
    history_limit: int
    hero_name_by_id: Mapping[int, str]

    def __post_init__(self) -> None:
        if self.eligible_matches != len(self.dna.matches):
            raise ValueError(
                "Finding context eligible count must match the DNA analysis population"
            )
        if len(self.summary_features.matches) != self.eligible_matches:
            raise ValueError(
                "Finding context summary features must use the same eligible population"
            )


def summary_features_for_free(
    matches: tuple[NormalizedSummaryMatch, ...] | list[NormalizedSummaryMatch],
    *,
    session_gap_minutes: int,
) -> SummaryFeatureSet:
    """Adapt canonical normalized rows to the legacy summary detector contract.

    This adapter is intentionally CPU-only.  It fills only fields already
    proven by common eligibility; it never invents a missing behavioral value.
    """

    rows: list[dict[str, object]] = []
    for item in matches:
        if not item.is_common_eligible:
            continue
        if item.side is None or item.won is None or item.duration_seconds is None:
            continue
        player_slot = 0 if item.side == "radiant" else 128
        radiant_win = item.won if item.side == "radiant" else not item.won
        row = item.as_dict()
        row.update(
            {
                "duration": item.duration_seconds,
                "player_slot": player_slot,
                "radiant_win": radiant_win,
                "won": item.won,
            }
        )
        rows.append(row)
    result = calculate_summary_features(rows, session_gap_minutes=session_gap_minutes)
    if len(result.matches) != len(tuple(item for item in matches if item.is_common_eligible)):
        raise ValueError("Summary adapter dropped an eligible Free DNA row")
    return result


def build_free_finding_context(
    *,
    dna: DnaAnalysisResult,
    summary_features: SummaryFeatureSet,
    patterns: tuple[PatternCandidate, ...] | list[PatternCandidate],
    processed_matches: int,
    eligible_matches: int,
    history_limit: int,
) -> FreeFindingContext:
    return FreeFindingContext(
        dna=dna,
        summary_features=summary_features,
        patterns=tuple(patterns),
        eligible_matches=eligible_matches,
        processed_matches=processed_matches,
        history_limit=history_limit,
        hero_name_by_id=_hero_names(dna),
    )


def _hero_names(dna: DnaAnalysisResult) -> dict[int, str]:
    names: dict[int, str] = {}
    cards = [dna.heroes.signature, *dna.heroes.comfort_picks]
    for card in cards:
        if card is not None:
            names[card.hero_id] = card.name
    for recommendation in dna.heroes.recommendations:
        hero_id = recommendation.get("hero_id")
        name = recommendation.get("name")
        if isinstance(hero_id, int) and isinstance(name, str):
            names.setdefault(hero_id, name)
    try:
        taxonomy = load_default_taxonomy()
        for hero_id in dna.features.hero_counts:
            hero = taxonomy.get(hero_id)
            if hero is not None:
                names.setdefault(hero_id, hero.name)
    except (OSError, TypeError, ValueError):
        pass
    return names

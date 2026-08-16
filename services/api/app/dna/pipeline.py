from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from app.dna.archetypes.classifier import ArchetypeResult, classify
from app.dna.archetypes.descriptors import choose_descriptors
from app.dna.dimensions.models import DimensionResult
from app.dna.dimensions.service import score_dimensions
from app.dna.features.extractor import extract_dna_features
from app.dna.features.models import DnaFeatureSet
from app.dna.sessions import SessionPolicy, SessionResult, infer_sessions
from app.heroes.identity import HeroIdentityResult, select_hero_identity
from app.heroes.taxonomy import HeroTaxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch

DNA_SCORING_VERSION = "dna-scoring-1.1.0"


@dataclass(frozen=True, slots=True)
class DnaAnalysisResult:
    matches: tuple[NormalizedSummaryMatch, ...]
    sessions: SessionResult
    features: DnaFeatureSet
    dimensions: tuple[DimensionResult, ...]
    archetype: ArchetypeResult
    heroes: HeroIdentityResult
    history_tier: str = "normal"

    @property
    def overall_confidence(self) -> str:
        values = [item.confidence_score for item in self.dimensions if item.score is not None]
        if not values:
            return "low"
        average = sum(values) / len(values)
        if self.history_tier == "limited":
            return "moderate" if average >= 0.35 else "low"
        return "high" if average >= 0.75 else "moderate" if average >= 0.50 else "low"

    @property
    def warnings(self) -> tuple[str, ...]:
        warnings: list[str] = []
        unavailable = [item.key for item in self.dimensions if item.status == "unavailable"]
        if unavailable:
            warnings.append("Signals with missing fields remain visible as limited or unavailable: " + ", ".join(unavailable))
        if 30 <= self.features.sample_size < 60 or self.history_tier == "limited":
            warnings.append("This is a limited-history report; more matches will make the pattern steadier.")
        warnings.extend(self.heroes.limitations)
        return tuple(dict.fromkeys(warnings))

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature_version": self.features.feature_version,
            "session_version": self.sessions.policy.version,
            "scoring_version": DNA_SCORING_VERSION,
            "features": self.features.as_dict(),
            "sessions": self.sessions.as_dict(),
            "dimensions": [item.as_dict() for item in self.dimensions],
            "archetype": self.archetype.as_dict(),
            "heroes": self.heroes.as_dict(),
            "overall_confidence": self.overall_confidence,
            "warnings": list(self.warnings),
        }


def analyze_dna(
    matches: tuple[NormalizedSummaryMatch, ...] | list[NormalizedSummaryMatch],
    *,
    session_gap_minutes: int = 90,
    taxonomy: HeroTaxonomy | None = None,
    history_tier: str | None = None,
) -> DnaAnalysisResult:
    policy = SessionPolicy(gap_minutes=max(1, session_gap_minutes))
    sessions = infer_sessions(matches, policy)
    features = extract_dna_features(sessions.matches, sessions)
    dimensions = score_dimensions(features)
    archetype = classify(dimensions)
    archetype = replace(archetype, descriptors=choose_descriptors(dimensions, archetype_key=archetype.key))
    heroes = select_hero_identity(features, taxonomy)
    return DnaAnalysisResult(
        matches=sessions.matches,
        sessions=sessions,
        features=features,
        dimensions=dimensions,
        archetype=archetype,
        heroes=heroes,
        history_tier=history_tier or ("limited" if 30 <= features.sample_size < 60 else "normal"),
    )

"""Checked-in version matrix for the additive Free DNA V6.1 path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

VersionDisposition = Literal["changed", "compatible", "unchanged", "new"]

# The story extension is versioned independently from the legacy nine-beat
# ``story`` surface above.  Keep these values here, alongside the V6.1
# compatibility matrix, so changing any story contract surface invalidates a
# cached report without changing the frozen analytical identities.
StoryPayloadVersion: TypeAlias = Literal["free-story-payload-1.0.0"]
StoryRulesVersion: TypeAlias = Literal["free-story-rules-1.0.0"]
StoryCopyVersion: TypeAlias = Literal["free-story-copy-1.0.0"]
StoryModeMapVersion: TypeAlias = Literal["opendota-mode-map-e7705ee"]
StoryHeroTaxonomyVersion: TypeAlias = Literal["hero-taxonomy-2026-08-16"]
StoryHeroMetadataVersion: TypeAlias = Literal["hero-knowledge-semantic-freeze-full-roster-v1"]
StoryArchetypeContractVersion: TypeAlias = Literal["free-archetype-interface-1.0.0"]

STORY_PAYLOAD_VERSION: Final[StoryPayloadVersion] = "free-story-payload-1.0.0"
STORY_RULES_VERSION: Final[StoryRulesVersion] = "free-story-rules-1.0.0"
STORY_COPY_VERSION: Final[StoryCopyVersion] = "free-story-copy-1.0.0"
STORY_MODE_MAP_VERSION: Final[StoryModeMapVersion] = "opendota-mode-map-e7705ee"
STORY_HERO_TAXONOMY_VERSION: Final[StoryHeroTaxonomyVersion] = "hero-taxonomy-2026-08-16"
STORY_HERO_METADATA_VERSION: Final[StoryHeroMetadataVersion] = "hero-knowledge-semantic-freeze-full-roster-v1"
STORY_ARCHETYPE_CONTRACT_VERSION: Final[StoryArchetypeContractVersion] = "free-archetype-interface-1.0.0"


@dataclass(frozen=True, slots=True)
class VersionSurface:
    key: str
    version: str
    disposition: VersionDisposition
    compatibility: str


VERSION_SURFACES = (
    VersionSurface("report", "free-dna-report-6.1.0", "changed", "V6.0 remains validator-routed and immutable"),
    VersionSurface("model", "free-dna-model-6.1.0", "changed", "new generation selector only"),
    VersionSurface("elements", "free-elements-6.1.0", "changed", "same seven ordered public keys"),
    VersionSurface("findings", "free-findings-6.1.0", "changed", "same five roots; nested outcomes"),
    VersionSurface("supporting_signals", "supporting-signals-1.0.0", "new", "private graph; selected evidence only"),
    VersionSurface("semantic_outcomes", "semantic-outcomes-1.0.0", "new", "frozen hierarchical registry"),
    VersionSurface("expression", "summary-expression-multisignal-2.0.0", "changed", "V6.1 estimators only"),
    VersionSurface("statistics", "stats-cluster-bootstrap-2.0.0", "changed", "recomputed/cross-fitted estimators"),
    VersionSurface("context_baseline", "context-baseline-3.0.0", "changed", "V6.1 artifact schema"),
    VersionSurface("thresholds", "metric-thresholds-6.1.0", "changed", "registry-key manifest"),
    VersionSurface("claims", "claim-contract-2.0.0", "changed", "alternatives and verification added"),
    VersionSurface("story", "free-story-6.1.0", "changed", "same nine beats; interaction-aware payload"),
    VersionSurface("story_payload", STORY_PAYLOAD_VERSION, "new", "additive descriptive module payload"),
    VersionSurface("story_rules", STORY_RULES_VERSION, "new", "frozen story aggregation and omission rules"),
    VersionSurface("story_copy", STORY_COPY_VERSION, "new", "deterministic story copy variants"),
    VersionSurface("game_mode_map", STORY_MODE_MAP_VERSION, "new", "pinned AP/CM mode and lobby tuples"),
    VersionSurface("hero_taxonomy", STORY_HERO_TAXONOMY_VERSION, "new", "frozen public hero taxonomy"),
    VersionSurface("hero_metadata", STORY_HERO_METADATA_VERSION, "new", "frozen public hero metadata roster"),
    VersionSurface("archetype_contract", STORY_ARCHETYPE_CONTRACT_VERSION, "new", "not-ready archetype interface"),
    VersionSurface("copy", "free-dna-semantic-copy-6.1.0", "changed", "outcome-owned deterministic copy"),
    VersionSurface("recommendations", "free-dna-recommendations-6.1.0", "changed", "five-game verification contract"),
    VersionSurface("deep_diagnostics", "deep-diagnostics-2.1.0", "changed", "protected qualifying cohort references"),
    VersionSurface("share_renderer", "share-svg-6.1.0", "changed", "semantic cards gated separately"),
    VersionSurface("interactions", "report-interactions-1.1.0", "changed", "additive kinds; old sessions readable"),
    VersionSurface("summary_history", "summary-history-schema-3.0.0", "new", "one physical request contract"),
)

VERSION_MATRIX = {surface.key: surface for surface in VERSION_SURFACES}


def version(key: str) -> str:
    try:
        return VERSION_MATRIX[key].version
    except KeyError as exc:
        raise ValueError(f"unknown V6.1 version surface: {key}") from exc


def default_versions_v61() -> dict[str, str]:
    return {surface.key: surface.version for surface in VERSION_SURFACES}


REPORT_VERSION = version("report")
MODEL_VERSION = version("model")
ELEMENTS_VERSION = version("elements")
FINDINGS_VERSION = version("findings")
SUPPORTING_SIGNALS_VERSION = version("supporting_signals")
SEMANTIC_OUTCOMES_VERSION = version("semantic_outcomes")

__all__ = [
    "ELEMENTS_VERSION",
    "FINDINGS_VERSION",
    "MODEL_VERSION",
    "REPORT_VERSION",
    "SEMANTIC_OUTCOMES_VERSION",
    "STORY_ARCHETYPE_CONTRACT_VERSION",
    "STORY_COPY_VERSION",
    "STORY_HERO_METADATA_VERSION",
    "STORY_HERO_TAXONOMY_VERSION",
    "STORY_MODE_MAP_VERSION",
    "STORY_PAYLOAD_VERSION",
    "STORY_RULES_VERSION",
    "StoryArchetypeContractVersion",
    "StoryCopyVersion",
    "StoryHeroMetadataVersion",
    "StoryHeroTaxonomyVersion",
    "StoryModeMapVersion",
    "StoryPayloadVersion",
    "StoryRulesVersion",
    "SUPPORTING_SIGNALS_VERSION",
    "VERSION_MATRIX",
    "VERSION_SURFACES",
    "VersionSurface",
    "default_versions_v61",
    "version",
]

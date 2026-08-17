"""Strict public schema for the immutable Free DNA v4 report."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class IdentitySchema(PublicModel):
    display_name: str
    avatar_url: str | None = None
    rank_tier: int | None = None


class MetadataSchema(PublicModel):
    created_at: str
    expires_at: str | None = None
    data_from: str | None = None
    data_to: str | None = None
    processed_matches: int = Field(ge=0)
    eligible_matches: int = Field(ge=0)
    history_limit: int = Field(ge=1, le=500)
    raw_history_hash: str
    history_tier: Literal["limited", "normal"]


class VersionMapV4Schema(PublicModel):
    eligibility: str
    sessions: str
    features: str
    behavior_model: str
    element_registry: str
    pattern_registry: str
    pattern_ranking: str
    hero_taxonomy: str
    hero_portfolio: str
    hero_mirror: str
    story: str
    copy_: str = Field(alias="copy")
    model: str
    template: str
    share_renderer: str
    analysis_version_fingerprint: str


class QualitySchema(PublicModel):
    overall_confidence: Literal["low", "moderate", "high", "unavailable"]
    history_tier: Literal["limited", "normal"]
    missing_data_flags: list[str]
    partial: bool
    warnings: list[str]
    available_elements: int = Field(ge=0)
    limited_elements: int = Field(ge=0)
    unavailable_elements: int = Field(ge=0)
    qualified_patterns: int = Field(ge=0)


class BehaviorReceiptSchema(PublicModel):
    key: str
    value: float | int | str | bool | None
    unit: str
    denominator: int = Field(ge=0)
    coverage: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    comparison: str | None = None


BehaviorConfidence = Literal["low", "moderate", "high", "unavailable"]


class BehaviorElementSchema(PublicModel):
    key: str
    label: str
    dimension_key: str
    status: Literal["available", "limited", "unavailable"]
    score: float | None = Field(default=None, ge=0, le=1)
    centered_score: float | None = Field(default=None, ge=-1, le=1)
    axis: dict[str, str | None]
    zone: str | None = None
    confidence: BehaviorConfidence
    confidence_score: float = Field(ge=0, le=1)
    sample_size: int = Field(ge=0)
    effective_sample_size: float = Field(ge=0)
    coverage: float = Field(ge=0, le=1)
    receipts: list[BehaviorReceiptSchema] = Field(default_factory=list)
    confounders: list[str] = Field(default_factory=list)
    missing_reasons: list[str] = Field(default_factory=list)
    methodology_version: str


class BehaviorPatternSchema(PublicModel):
    key: str
    label: str
    kind: Literal["identity", "contradiction", "edge", "leak", "trajectory", "style"]
    status: Literal["qualified", "suppressed", "unavailable"]
    direction: str | None = None
    strength: float = Field(ge=0, le=1)
    relationship_strength: float = Field(ge=0, le=1)
    confidence: BehaviorConfidence
    confidence_score: float = Field(ge=0, le=1)
    evidence_coverage: float = Field(ge=0, le=1)
    qualification_quality: float = Field(ge=0, le=1)
    element_keys: list[str] = Field(min_length=2)
    modifier_element_keys: list[str] = Field(default_factory=list)
    family: str
    tier: Literal["A", "B"]
    receipts: list[BehaviorReceiptSchema] = Field(default_factory=list)
    confounders: list[str] = Field(default_factory=list)
    suppression_reasons: list[str] = Field(default_factory=list)
    methodology_version: str


class HighlightsSchema(PublicModel):
    element_keys: list[str] = Field(max_length=3)
    pattern_keys: list[str] = Field(max_length=3)


class ChoiceOptionSchema(PublicModel):
    key: str
    label: str
    hero_id: int | None = Field(default=None, gt=0)


class CommonThreadSchema(PublicModel):
    status: Literal["available", "unavailable"]
    trait_key: str | None = None
    trait_label: str | None = None
    weighted_coverage: float = Field(ge=0, le=1)
    hero_count: int = Field(ge=0)
    denominator: int = Field(ge=0)
    secondary_traits: list[str]
    options: list[ChoiceOptionSchema]
    correct_option_key: str | None = None
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]


class ExceptionSchema(PublicModel):
    status: Literal["available", "no_clear_exception", "unavailable"]
    hero_id: int | None = Field(default=None, gt=0)
    hero_name: str | None = None
    pool_traits: list[str]
    exception_traits: list[str]
    options: list[ChoiceOptionSchema]
    correct_option_key: str | None = None
    distance: float | None = Field(default=None, ge=0)
    margin: float | None = None
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]


class EvolutionSchema(PublicModel):
    status: Literal["available", "unavailable"]
    variant: Literal[
        "new_heroes_new_toolkit", "new_heroes_same_toolkit", "stable_core_new_branch", "broadly_stable"
    ] | None = None
    earlier_hero_ids: list[int]
    recent_hero_ids: list[int]
    earlier_traits: list[str]
    recent_traits: list[str]
    hero_distribution_shift: float | None = Field(default=None, ge=0, le=1)
    toolkit_distribution_shift: float | None = Field(default=None, ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]


class HeroMirrorSchema(PublicModel):
    status: Literal["available", "no_clear_mirror", "unavailable"]
    hero_id: int | None = Field(default=None, gt=0)
    hero_name: str | None = None
    similarity_score: float | None = Field(default=None, ge=0, le=1)
    runner_up_hero_id: int | None = Field(default=None, gt=0)
    margin: float | None = None
    player_behavior: dict[str, str]
    hero_behavior: dict[str, str]
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]


class HeroPortfolioSchema(PublicModel):
    common_thread: CommonThreadSchema
    exception: ExceptionSchema
    evolution: EvolutionSchema
    hero_mirror: HeroMirrorSchema
    version: str


class StorySchema(PublicModel):
    version: str
    ordered_pages: list[str]


StoryPageKindV4 = Literal[
    "element_scan",
    "element_highlight",
    "pattern_highlight",
    "hero_common_thread_question",
    "hero_exception_question",
    "pool_evolution_question",
    "pool_evolution_reveal",
    "hero_mirror_reveal",
    "final_card",
    "deep_dive",
]


class StoryPageV4Schema(PublicModel):
    id: str
    kind: StoryPageKindV4
    section: Literal["elements", "patterns", "hero_portfolio", "finale"]
    title: str
    body: str | None = None
    evidence_keys: list[str] = Field(default_factory=list)
    element_key: str | None = None
    pattern_key: str | None = None
    portfolio_key: str | None = None
    options: list[ChoiceOptionSchema] = Field(default_factory=list)


class ShareElementSchema(PublicModel):
    key: str
    label: str
    zone: str | None = None


class SharePatternSchema(PublicModel):
    key: str
    label: str


class SharePortfolioSchema(PublicModel):
    common_thread: str | None = None
    exception_hero: str | None = None
    pool_direction: str | None = None


class ShareMirrorSchema(PublicModel):
    hero_id: int = Field(gt=0)
    hero_name: str


class ShareV4Schema(PublicModel):
    display_name: str | None = None
    strongest_elements: list[ShareElementSchema]
    strongest_patterns: list[SharePatternSchema]
    hero_portfolio: SharePortfolioSchema
    hero_mirror: ShareMirrorSchema | None = None


class PrivacyDefaultsSchema(PublicModel):
    show_name: bool
    show_avatar: bool
    show_raw_id: Literal[False]


class SharesV4Schema(PublicModel):
    final: ShareV4Schema
    privacy_defaults: PrivacyDefaultsSchema


class DeepDiveSchema(PublicModel):
    available: bool
    cta_label: str
    href: str
    copy_: str = Field(alias="copy")


class MethodologySchema(PublicModel):
    free_summary_only: Literal[True]
    session_gap_minutes: int = Field(ge=1)
    session_policy_version: str
    notes: list[str]


class CostSchema(PublicModel):
    history_requests: int = Field(ge=0)
    detail_requests: Literal[0]
    parse_requests: Literal[0]
    parse_status_requests: int = Field(ge=0)
    cache_hits: int = Field(ge=0)
    estimated_cost_units: float = Field(ge=0)


class FreeDnaReportV4Schema(PublicModel):
    report_id: str | None = None
    schema_version: Literal["free-dna-report-4.0.0"]
    report_variant: Literal["free_dna_report"]
    noindex: Literal[True]
    identity: IdentitySchema
    metadata: MetadataSchema
    versions: VersionMapV4Schema
    quality: QualitySchema
    elements: list[BehaviorElementSchema] = Field(min_length=17, max_length=17)
    patterns: list[BehaviorPatternSchema] = Field(min_length=14, max_length=14)
    highlights: HighlightsSchema
    hero_portfolio: HeroPortfolioSchema
    story: StorySchema
    pages: list[StoryPageV4Schema]
    shares: SharesV4Schema
    deep_dive: DeepDiveSchema
    methodology: MethodologySchema
    cost: CostSchema

    @model_validator(mode="after")
    def validate_v4_contract(self) -> FreeDnaReportV4Schema:
        from app.behavior.elements.registry import ELEMENT_REGISTRY
        from app.behavior.patterns.registry import PATTERN_REGISTRY

        element_keys = [item.key for item in self.elements]
        if set(element_keys) != set(ELEMENT_REGISTRY) or len(element_keys) != len(set(element_keys)):
            raise ValueError("Free DNA v4 must contain each of the 17 registered Elements once")
        pattern_keys = [item.key for item in self.patterns]
        if set(pattern_keys) != set(PATTERN_REGISTRY) or len(pattern_keys) != len(set(pattern_keys)):
            raise ValueError("Free DNA v4 must contain each of the 14 registered Patterns once")
        if len(self.highlights.element_keys) != len(set(self.highlights.element_keys)):
            raise ValueError("Element highlights must be unique")
        if len(self.highlights.pattern_keys) != len(set(self.highlights.pattern_keys)):
            raise ValueError("Pattern highlights must be unique")
        if not set(self.highlights.element_keys).issubset(element_keys):
            raise ValueError("Element highlight references an unknown Element")
        if not set(self.highlights.pattern_keys).issubset(pattern_keys):
            raise ValueError("Pattern highlight references an unknown Pattern")
        for pattern in self.patterns:
            if not set(pattern.element_keys).issubset(element_keys):
                raise ValueError(f"Pattern {pattern.key} references an unknown required Element")
            if not set(pattern.modifier_element_keys).issubset(element_keys):
                raise ValueError(f"Pattern {pattern.key} references an unknown modifier Element")
            if set(pattern.element_keys) & set(pattern.modifier_element_keys):
                raise ValueError(f"Pattern {pattern.key} overlaps required and modifier Elements")
        page_ids = [item.id for item in self.pages]
        if page_ids != self.story.ordered_pages or len(page_ids) != len(set(page_ids)):
            raise ValueError("Free DNA v4 story ordering must match unique public pages")
        for page in self.pages:
            if page.element_key is not None and page.element_key not in element_keys:
                raise ValueError(f"Story page references unknown Element: {page.element_key}")
            if page.pattern_key is not None and page.pattern_key not in pattern_keys:
                raise ValueError(f"Story page references unknown Pattern: {page.pattern_key}")
            if not set(page.evidence_keys).issubset(element_keys):
                raise ValueError(f"Story page {page.id} references an unknown Element")
        if self.shares.privacy_defaults.show_raw_id is not False:
            raise ValueError("Free DNA share cards cannot enable raw IDs")
        if self.cost.detail_requests != 0 or self.cost.parse_requests != 0:
            raise ValueError("Free DNA v4 cannot require match-detail or replay-parse requests")
        return self


def validate_free_dna_report(report: dict[str, Any]) -> dict[str, Any]:
    """Validate a new immutable v4 snapshot at the public API boundary."""

    return FreeDnaReportV4Schema.model_validate(report).model_dump(mode="json", by_alias=True)


__all__ = ["FreeDnaReportV4Schema", "validate_free_dna_report"]

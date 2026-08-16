"""Strict public schemas for immutable Free DNA reports.

Internal analysis snapshots intentionally have different Python types and are
never serialized through this module.  Keeping this boundary strict prevents
raw match rows and compatibility payloads from reaching the web client.
"""

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


class VersionMapSchema(PublicModel):
    eligibility: str
    sessions: str
    features: str
    dna_scoring: str
    baselines: str
    archetype: str
    hero_identity: str
    hero_taxonomy: str
    recommendations: str
    copy_: str = Field(alias="copy")
    model: str
    template: str
    share_renderer: str
    analysis_version_fingerprint: str


class QualitySchema(PublicModel):
    overall_confidence: Literal["low", "moderate", "high"]
    history_tier: Literal["limited", "normal"]
    missing_data_flags: list[str]
    partial: bool
    warnings: list[str]


class EvidenceSchema(PublicModel):
    key: str
    value: float | int | str | None
    unit: str
    denominator: int = Field(ge=0)


class CopySchema(PublicModel):
    headline_key: str
    receipt_key: str
    receipt_params: dict[str, str | int | float | bool] = Field(default_factory=dict)
    left_label: str | None = None
    right_label: str | None = None


DimensionKey = Literal[
    "breadth", "role", "adaptability", "activity", "orientation",
    "resilience", "endurance", "rhythm",
]


class DimensionResultSchema(PublicModel):
    key: DimensionKey
    status: Literal["available", "limited", "unavailable"]
    score: float | None = None
    centered_score: float | None = None
    label: str | None = None
    confidence: Literal["low", "moderate", "high", "unavailable"]
    confidence_score: float = Field(ge=0, le=1)
    sample_size: int = Field(ge=0)
    effective_sample_size: float = Field(ge=0)
    coverage: float = Field(ge=0, le=1)
    evidence: list[EvidenceSchema] = Field(default_factory=list)
    confounders: list[str] = Field(default_factory=list)
    missing_reasons: list[str] = Field(default_factory=list)
    copy_: CopySchema | None = Field(default=None, alias="copy")
    methodology_version: str
    descriptor_eligible: bool = True


class DescriptorSchema(PublicModel):
    key: str
    label: str
    dimension: str


class RunnerUpSchema(PublicModel):
    key: str
    fit: float = Field(ge=0, le=1)


class ContributionSchema(PublicModel):
    key: str
    weight: float = Field(ge=0)
    contribution: float = Field(ge=0)


class ArchetypeSchema(PublicModel):
    key: str
    label: str
    fit: float = Field(ge=0, le=1)
    runner_up: RunnerUpSchema | None = None
    descriptors: list[DescriptorSchema] = Field(min_length=3, max_length=3)
    contributing_dimensions: list[ContributionSchema]
    confidence: Literal["low", "moderate", "high"]
    explanation_evidence: list[str]
    classifier_version: str

    @model_validator(mode="after")
    def validate_descriptors(self) -> ArchetypeSchema:
        keys = [item.key for item in self.descriptors]
        if len(keys) != len(set(keys)):
            raise ValueError("Archetype descriptors must be unique")
        return self


class HeroCardSchema(PublicModel):
    hero_id: int = Field(gt=0)
    name: str
    portrait_url: str | None = None
    score: float = Field(ge=0, le=1)
    component_scores: dict[str, float]
    matches: int = Field(ge=0)
    roles: list[str]
    traits: list[str]
    receipts: list[str]
    reason_key: str
    confidence: Literal["low", "moderate", "high"]
    portrait_asset_version: str


class HeroPatternSchema(PublicModel):
    key: str
    label: str
    copy_key: str
    traits: list[str]
    role_traits: list[str] = Field(default_factory=list)
    contributors: list[str]
    scores: dict[str, float] = Field(default_factory=dict)


class HeroRecommendationSchema(PublicModel):
    hero_id: int = Field(gt=0)
    name: str
    portrait_url: str | None = None
    portrait_asset_version: str
    fit_band: Literal["strong", "good", "exploratory"]
    score: float = Field(ge=0, le=1)
    familiar_traits: list[str]
    new_traits: list[str]
    plausible_roles: list[str]
    role_change: bool
    reason_key: str
    recommendation_version: str


class HeroesSchema(PublicModel):
    signature: HeroCardSchema | None
    comfort_picks: list[HeroCardSchema]
    patterns: list[HeroPatternSchema]
    recommendations: list[HeroRecommendationSchema]
    taxonomy_version: str | None
    limitations: list[str]
    identity_version: str


PageKind = Literal[
    "input", "player_found", "analysis", "reveal", "section_intro", "dimension",
    "archetype", "summary", "signature_hero", "comfort", "hero_pattern",
    "recommendations", "final_card", "deep_dive",
]


class PageSchema(PublicModel):
    id: str
    kind: PageKind
    section: Literal["intro", "dna", "heroes", "finale"]
    title: str
    body: str | None = None
    evidence_keys: list[str] = Field(default_factory=list)


class ShareDimensionSchema(PublicModel):
    key: DimensionKey
    label: str | None
    score: float | None
    centered_score: float | None
    confidence: Literal["low", "moderate", "high", "unavailable"]


class ShareCommonSchema(PublicModel):
    archetype: str
    descriptors: list[DescriptorSchema]
    match_count: int = Field(ge=0)


class ShareDnaSchema(ShareCommonSchema):
    spectra: list[ShareDimensionSchema]


class ShareHeroesSchema(PublicModel):
    signature: HeroCardSchema | None
    comfort: list[HeroCardSchema]
    pattern: HeroPatternSchema | None
    recommendations: list[HeroRecommendationSchema]


class ShareFinalSchema(ShareCommonSchema):
    display_name: str
    signature: str | None
    pattern: str | None
    rhythm: str | None


class PrivacyDefaultsSchema(PublicModel):
    show_name: bool
    show_avatar: bool
    show_raw_id: Literal[False]


class SharesSchema(PublicModel):
    dna: ShareDnaSchema
    heroes: ShareHeroesSchema
    final: ShareFinalSchema
    privacy_defaults: PrivacyDefaultsSchema


class DeepDiveSchema(PublicModel):
    available: bool
    cta_label: str
    href: str
    copy_: str = Field(alias="copy")


class MethodologySchema(PublicModel):
    free_summary_only: Literal[True]
    session_gap_minutes: int
    session_policy_version: str
    notes: list[str]


class CostSchema(PublicModel):
    history_requests: int = Field(ge=0)
    detail_requests: Literal[0]
    parse_requests: Literal[0]
    parse_status_requests: int = Field(ge=0)
    cache_hits: int = Field(ge=0)
    estimated_cost_units: float = Field(ge=0)


class FreeDnaReportSchema(PublicModel):
    report_id: str | None = None
    schema_version: Literal["free-dna-report-1.0.0"]
    report_variant: Literal["free_dna_report"]
    noindex: Literal[True]
    identity: IdentitySchema
    metadata: MetadataSchema
    versions: VersionMapSchema
    quality: QualitySchema
    dimensions: list[DimensionResultSchema] = Field(min_length=8, max_length=8)
    archetype: ArchetypeSchema
    heroes: HeroesSchema
    pages: list[PageSchema] = Field(min_length=23, max_length=23)
    shares: SharesSchema
    deep_dive: DeepDiveSchema
    methodology: MethodologySchema
    cost: CostSchema

    @model_validator(mode="after")
    def validate_free_contract(self) -> FreeDnaReportSchema:
        keys = [item.key for item in self.dimensions]
        expected = {
            "breadth", "role", "adaptability", "activity",
            "orientation", "resilience", "endurance", "rhythm",
        }
        if set(keys) != expected or len(keys) != len(set(keys)):
            raise ValueError("Free DNA reports must contain each of the eight dimensions once")
        page_ids = [item.id for item in self.pages]
        if len(page_ids) != 23 or len(page_ids) != len(set(page_ids)):
            raise ValueError("Free DNA reports must contain exactly 23 unique story pages")
        if self.shares.privacy_defaults.show_raw_id is not False:
            raise ValueError("Free DNA share cards cannot enable raw IDs")
        return self

# ---------------------------------------------------------------------------
# Free DNA report v2
# ---------------------------------------------------------------------------

FindingKind = Literal[
    "thesis", "strength", "contradiction", "edge", "leak", "trajectory", "identity"
]
FindingConfidence = Literal["limited", "moderate", "high"]


class FindingReceiptSchema(PublicModel):
    key: str
    label: str
    value: str
    context: str | None = None
    confidence: FindingConfidence


class FindingExperimentSchema(PublicModel):
    key: str
    title: str
    instruction: str
    hypothesis: str
    measurement: str
    window: str


class PublicFindingSchema(PublicModel):
    key: str
    kind: FindingKind
    headline: str
    body: str
    interpretation: str | None = None
    confidence: FindingConfidence
    receipts: list[FindingReceiptSchema] = Field(min_length=2, max_length=4)
    related_dimensions: list[DimensionKey] = Field(default_factory=list)
    related_heroes: list[int] = Field(default_factory=list)
    experiment: FindingExperimentSchema | None = None
    share_copy: str | None = None


class StoryDefinitionSchema(PublicModel):
    version: str
    thesis_key: str | None = None
    strength_key: str | None = None
    contradiction_key: str | None = None
    edge_key: str | None = None
    leak_key: str | None = None
    experiment_key: str | None = None
    ordered_pages: list[str] = Field(min_length=7, max_length=14)


V2PageKind = Literal[
    "input", "player_found", "analysis", "reveal", "finding", "experiment",
    "identity_card", "dna_xray", "deep_dive",
]


class V2PageSchema(PublicModel):
    id: str
    kind: V2PageKind
    section: Literal["intro", "findings", "dna", "finale"]
    title: str
    body: str | None = None
    evidence_keys: list[str] = Field(default_factory=list)
    finding_key: str | None = None
    experiment_key: str | None = None


class FindingShareSchema(PublicModel):
    finding_key: str | None = None
    headline: str
    archetype: str | None = None
    receipts: list[str] = Field(default_factory=list, max_length=4)


class SharesV2Schema(PublicModel):
    identity: FindingShareSchema
    exposed: FindingShareSchema
    strength: FindingShareSchema
    # Backward-compatible aliases are retained in the immutable snapshot for
    # old share URLs; v2 UI copy uses the three finding-oriented cards above.
    dna: ShareDnaSchema
    heroes: ShareHeroesSchema
    final: ShareFinalSchema
    privacy_defaults: PrivacyDefaultsSchema


class VersionMapV2Schema(VersionMapSchema):
    findings: str
    finding_ranking: str
    story: str


class FreeDnaReportV2Schema(PublicModel):
    report_id: str | None = None
    schema_version: Literal["free-dna-report-2.0.0"]
    report_variant: Literal["free_dna_report"]
    noindex: Literal[True]
    identity: IdentitySchema
    metadata: MetadataSchema
    versions: VersionMapV2Schema
    quality: QualitySchema
    dimensions: list[DimensionResultSchema] = Field(min_length=8, max_length=8)
    archetype: ArchetypeSchema
    heroes: HeroesSchema
    findings: list[PublicFindingSchema] = Field(max_length=12)
    story: StoryDefinitionSchema
    pages: list[V2PageSchema] = Field(min_length=7, max_length=14)
    shares: SharesV2Schema
    deep_dive: DeepDiveSchema
    methodology: MethodologySchema
    cost: CostSchema

    @model_validator(mode="after")
    def validate_v2_contract(self) -> FreeDnaReportV2Schema:
        dimension_keys = [item.key for item in self.dimensions]
        expected_dimensions = {
            "breadth", "role", "adaptability", "activity",
            "orientation", "resilience", "endurance", "rhythm",
        }
        if set(dimension_keys) != expected_dimensions or len(dimension_keys) != len(set(dimension_keys)):
            raise ValueError("Free DNA reports must contain each of the eight dimensions once")
        finding_keys = [item.key for item in self.findings]
        if len(finding_keys) != len(set(finding_keys)):
            raise ValueError("Free DNA finding keys must be unique")
        page_ids = [item.id for item in self.pages]
        if len(page_ids) != len(set(page_ids)):
            raise ValueError("Free DNA v2 story page IDs must be unique")
        if page_ids != self.story.ordered_pages:
            raise ValueError("Story ordering must match the public page sequence")
        finding_map = {item.key: item for item in self.findings}
        for page in self.pages:
            if page.finding_key is not None and page.finding_key not in finding_map:
                raise ValueError(f"Story page references unknown finding: {page.finding_key}")
            if page.kind == "finding" and page.finding_key is None:
                raise ValueError("Finding pages must reference a finding")
            if page.kind == "experiment":
                if page.finding_key is None or page.experiment_key is None:
                    raise ValueError("Experiment pages must reference a finding and experiment")
                finding = finding_map.get(page.finding_key)
                if finding is None or finding.experiment is None or finding.experiment.key != page.experiment_key:
                    raise ValueError("Experiment page does not resolve to its finding experiment")
        if not any(page.kind == "identity_card" for page in self.pages):
            raise ValueError("Free DNA v2 story must include an identity card")
        if not any(page.kind == "dna_xray" for page in self.pages):
            raise ValueError("Free DNA v2 story must include the DNA X-ray")
        if not any(page.kind == "deep_dive" for page in self.pages):
            raise ValueError("Free DNA v2 story must include a Deep Dive CTA")
        for key in (
            self.story.thesis_key,
            self.story.strength_key,
            self.story.contradiction_key,
            self.story.edge_key,
            self.story.leak_key,
        ):
            if key is not None and key not in finding_map:
                raise ValueError(f"Story slot references unknown finding: {key}")
        if self.story.experiment_key is not None and not any(
            page.experiment_key == self.story.experiment_key for page in self.pages
        ):
            raise ValueError("Story experiment slot does not resolve to a page")
        if self.shares.privacy_defaults.show_raw_id is not False:
            raise ValueError("Free DNA share cards cannot enable raw IDs")
        return self


def validate_free_dna_report(report: dict[str, Any]) -> dict[str, Any]:
    """Validate either immutable Free DNA v1 or v2 snapshots.

    Existing v1 links remain immutable and continue through their original
    strict contract; new analysis snapshots use the finding-led v2 contract.
    """

    if report.get("schema_version") == "free-dna-report-2.0.0":
        return FreeDnaReportV2Schema.model_validate(report).model_dump(mode="json", by_alias=True)
    return FreeDnaReportSchema.model_validate(report).model_dump(mode="json", by_alias=True)

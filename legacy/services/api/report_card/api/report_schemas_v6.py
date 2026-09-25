"""Strict public contract for immutable Free DNA v6 snapshots."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ELEMENT_KEYS = {
    "breadth",
    "toolkit",
    "involvement",
    "finishing",
    "death_exposure",
    "transfer",
    "consistency",
}
FINDING_FAMILIES = {
    "pool_shape",
    "transfer",
    "post_loss_response",
    "combat_expression",
    "session_drift",
}
STORY_BEATS = (
    "self-estimate",
    "identity-reveal",
    "pool-evolution",
    "combat-expression",
    "strongest-finding",
    "secondary-finding",
    "recommendation",
    "hero-mirror",
    "deep-diagnostic",
)

ConfidenceTier = Literal["unavailable", "descriptive", "moderate", "high"]


class PublicV6Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class IdentityV6Schema(PublicV6Model):
    display_name: str
    avatar_url: str | None = None


class MetadataV6Schema(PublicV6Model):
    created_at: str
    expires_at: str | None = None
    data_from: str | None = None
    data_to: str | None = None
    processed_matches: int = Field(ge=0)
    eligible_matches: int = Field(ge=30)
    history_limit: int | None = Field(default=None, ge=1)
    raw_history_hash: str
    history_tier: Literal["limited", "normal"]


class VersionsV6Schema(PublicV6Model):
    elements: Literal["free-elements-6.0.0"]
    findings: Literal["free-findings-6.0.0"]
    expression: Literal["summary-expression-multisignal-1.0.0"]
    statistics: Literal["stats-cluster-bootstrap-1.0.0"]
    context_baseline: Literal["context-baseline-2.0.0"]
    thresholds: Literal["metric-thresholds-6.0.0"]
    claims: Literal["claim-contract-1.0.0"]
    story: Literal["free-story-6.0.0"]
    copy_: Literal["free-dna-semantic-copy-6.0.0"] = Field(alias="copy")
    deep_diagnostics: Literal["deep-diagnostics-2.0.0"]
    share_renderer: Literal["share-svg-6.0.0"]
    interactions: Literal["report-interactions-1.0.0"]
    model: str
    template: str
    analysis_version_fingerprint: str


class ReproducibilityV6Schema(PublicV6Model):
    generated_at: str
    input_snapshot_hash: str
    window_start: str | None = None
    window_end: str | None = None
    raw_match_count: int = Field(ge=0)
    usable_match_count: int = Field(ge=30)
    independent_session_count: int = Field(ge=0)
    bootstrap_iterations: int = Field(ge=1)
    bootstrap_seed: str
    session_gap_minutes: int = Field(ge=1)
    baseline_artifact: str
    threshold_artifact: str


class QualityV6Schema(PublicV6Model):
    overall_confidence: ConfidenceTier
    history_tier: Literal["limited", "normal"]
    partial: bool
    warnings: list[str] = Field(default_factory=list)
    missing_data_flags: list[str] = Field(default_factory=list)
    available_elements: int = Field(ge=0, le=7)
    published_findings: int = Field(ge=0, le=3)


class IntervalV6Schema(PublicV6Model):
    lower: float
    upper: float
    level: float = Field(default=0.95, ge=0.95, le=0.95)

    @model_validator(mode="after")
    def ordered(self) -> IntervalV6Schema:
        if self.lower > self.upper:
            raise ValueError("interval lower bound must not exceed upper bound")
        return self


class ClaimContractV6Schema(PublicV6Model):
    claim: str | None = None
    evidence: str | None = None
    interpretation: str | None = None
    recommendation: dict[str, Any] | None = None
    copy_version: str | None = None


class MeasurementV6Schema(PublicV6Model):
    key: str
    label: str
    status: Literal["available", "descriptive", "suppressed", "unavailable"]
    estimate: float | None = None
    unit: str
    interval: IntervalV6Schema | None = None
    zone: str | None = None
    direction: str | None = None
    bootstrap_stability: float = Field(ge=0, le=1)
    sample_size: int = Field(ge=0)
    independent_session_count: int = Field(ge=0)
    coverage: float = Field(ge=0, le=1)
    confidence: ConfidenceTier
    evidence_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    supported_claims: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)


class ElementV6Schema(MeasurementV6Schema):
    pass


class FindingV6Schema(MeasurementV6Schema):
    family: str
    published: bool = False
    signal_keys: list[str] = Field(default_factory=list)
    outcome_key: str | None = None
    raw_p_value: float = Field(default=1.0, ge=0, le=1)
    adjusted_q_value: float = Field(default=1.0, ge=0, le=1)
    claim_contract: ClaimContractV6Schema


class IdentitySummaryV6Schema(PublicV6Model):
    headline: str
    supporting_lines: list[str] = Field(max_length=2)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: ConfidenceTier


class DiagnosticQuestionV6Schema(PublicV6Model):
    id: str
    version: Literal["deep-diagnostics-2.0.0"]
    prompt: str
    finding_family: str
    evidence_refs: list[str] = Field(min_length=1)
    confidence: Literal["moderate", "high"]
    diagnostic_question_id: str | None = None
    statement: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    primary_hypothesis: dict[str, Any] = Field(default_factory=dict)
    secondary_hypothesis: dict[str, Any] | None = None
    required_summary_metrics: list[str] = Field(default_factory=list)
    required_detail_metrics: list[str] = Field(default_factory=list)
    required_parse_metrics: list[str] = Field(default_factory=list)
    question_spec: dict[str, Any] = Field(default_factory=dict)
    secondary_reuse_fraction: float = Field(default=0.0, ge=0, le=1)
    options: list[dict[str, Any]] = Field(default_factory=list)
    observed: dict[str, Any] = Field(default_factory=dict)
    available: bool = True
    skippable: bool = True


class StoryV6Schema(PublicV6Model):
    version: Literal["free-story-6.0.0"]
    ordered_beats: list[str] = Field(min_length=9, max_length=9)


class StoryPageV6Schema(PublicV6Model):
    id: str
    kind: str
    observed: dict[str, Any] = Field(default_factory=dict)
    content: dict[str, Any] = Field(default_factory=dict)
    title: str | None = None
    prompt: str | None = None
    body: str | None = None
    options: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    available: bool = True
    skippable: Literal[True] = True


class ShareCandidateV6Schema(PublicV6Model):
    id: str
    kind: Literal["dynamic_identity", "strongest_finding", "hero_mirror"]
    eligible: bool
    confidence: ConfidenceTier
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_confounders: list[str] = Field(default_factory=list)
    contains_recommendation: Literal[False] = False
    early_signal: Literal[False] = False
    payload: dict[str, Any] = Field(default_factory=dict)


class MethodologyV6Schema(PublicV6Model):
    free_summary_only: Literal[True]
    population_window_days: Literal[365]
    weighting: Literal["equal"]
    lane_context: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class FreeCostV6Schema(PublicV6Model):
    history_requests: Literal[1]
    detail_requests: Literal[0]
    parse_requests: Literal[0]
    parse_status_requests: Literal[0]
    cache_hits: int = Field(ge=0)
    estimated_cost_units: float = Field(ge=0)


class FreeDnaReportV6Schema(PublicV6Model):
    report_id: str | None = None
    schema_version: Literal["free-dna-report-6.0.0"]
    report_variant: Literal["free_dna_report"]
    noindex: Literal[True]
    identity: IdentityV6Schema
    metadata: MetadataV6Schema
    versions: VersionsV6Schema
    reproducibility: ReproducibilityV6Schema
    quality: QualityV6Schema
    elements: list[ElementV6Schema] = Field(min_length=7, max_length=7)
    findings: list[FindingV6Schema] = Field(min_length=5, max_length=5)
    identity_summary: IdentitySummaryV6Schema
    hero_portfolio: dict[str, Any]
    diagnostic_questions: list[DiagnosticQuestionV6Schema] = Field(max_length=3)
    story: StoryV6Schema
    pages: list[StoryPageV6Schema] = Field(min_length=9, max_length=9)
    share_candidates: list[ShareCandidateV6Schema] = Field(max_length=3)
    methodology: MethodologyV6Schema
    cost: FreeCostV6Schema

    @model_validator(mode="after")
    def validate_v6_contract(self) -> FreeDnaReportV6Schema:
        element_keys = [item.key for item in self.elements]
        if set(element_keys) != ELEMENT_KEYS or len(element_keys) != len(set(element_keys)):
            raise ValueError("Free DNA v6 must contain each of the seven Elements once")
        finding_families = [item.family for item in self.findings]
        if set(finding_families) != FINDING_FAMILIES or len(finding_families) != len(
            set(finding_families)
        ):
            raise ValueError("Free DNA v6 must contain each of the five finding families once")
        published = [item for item in self.findings if item.published]
        if len(published) > 3:
            raise ValueError("Free DNA v6 can publish at most three findings")
        if any(len(item.signal_keys) < 2 for item in published):
            raise ValueError("Published v6 findings require two independent signals")
        if self.metadata.history_tier == "limited" and any(
            item.published and item.claim_contract.recommendation for item in self.findings
        ):
            raise ValueError("Limited reports cannot publish finding-based recommendations")
        if tuple(self.story.ordered_beats) != STORY_BEATS:
            raise ValueError("Free DNA v6 story must contain the reviewed nine-beat order")
        page_ids = [item.id for item in self.pages]
        if page_ids != self.story.ordered_beats or len(page_ids) != len(set(page_ids)):
            raise ValueError("Free DNA v6 pages must match the unique nine-beat story order")
        available_refs = {
            ref for item in [*self.elements, *self.findings] for ref in item.evidence_refs
        }
        if not set(self.identity_summary.evidence_refs).issubset(available_refs):
            raise ValueError("Identity summary references unknown evidence")
        if any(
            question.finding_family not in FINDING_FAMILIES
            for question in self.diagnostic_questions
        ):
            raise ValueError("Diagnostic question references an unknown finding family")
        if any(
            not set(question.evidence_refs).issubset(available_refs)
            for question in self.diagnostic_questions
        ):
            raise ValueError("Diagnostic question references unknown evidence")
        for candidate in self.share_candidates:
            if candidate.eligible and (
                candidate.confidence != "high"
                or candidate.blocking_confounders
                or not candidate.evidence_refs
            ):
                raise ValueError(
                    "Eligible v6 share candidates must be high-confidence and standalone"
                )
        forbidden_lane_labels = {
            "position 1",
            "position 2",
            "position 3",
            "position 4",
            "position 5",
            "pos 1",
            "pos 2",
            "pos 3",
            "pos 4",
            "pos 5",
            "hard support",
            "soft support",
        }
        if any(
            label.strip().lower() in forbidden_lane_labels
            for label in self.methodology.lane_context
        ):
            raise ValueError("Free v6 lane context cannot expose inferred position labels")
        return self


def validate_free_dna_report_v6(report: dict[str, Any]) -> dict[str, Any]:
    return FreeDnaReportV6Schema.model_validate(report).model_dump(mode="json", by_alias=True)


__all__ = [
    "ELEMENT_KEYS",
    "FINDING_FAMILIES",
    "STORY_BEATS",
    "FreeDnaReportV6Schema",
    "validate_free_dna_report_v6",
]

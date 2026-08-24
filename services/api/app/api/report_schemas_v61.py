"""Strict public schema for immutable Free DNA V6.1 snapshots."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from app.api.report_schemas_v6 import (
    ELEMENT_KEYS,
    FINDING_FAMILIES,
    STORY_BEATS,
    ClaimContractV6Schema,
    FreeCostV6Schema,
    IdentityV6Schema,
    IntervalV6Schema,
    MetadataV6Schema,
    PublicV6Model,
    ShareCandidateV6Schema,
    StoryPageV6Schema,
)
from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_REGISTRY

ConfidenceTier = Literal["unavailable", "descriptive", "moderate", "high"]


class VersionsV61Schema(PublicV6Model):
    elements: Literal["free-elements-6.1.0"]
    findings: Literal["free-findings-6.1.0"]
    supporting_signals: Literal["supporting-signals-1.0.0"]
    semantic_outcomes: Literal["semantic-outcomes-1.0.0"]
    expression: Literal["summary-expression-multisignal-2.0.0"]
    statistics: Literal["stats-cluster-bootstrap-2.0.0"]
    context_baseline: Literal["context-baseline-3.0.0"]
    thresholds: Literal["metric-thresholds-6.1.0"]
    claims: Literal["claim-contract-2.0.0"]
    story: Literal["free-story-6.1.0"]
    copy_: Literal["free-dna-semantic-copy-6.1.0"] = Field(alias="copy")
    recommendations: Literal["free-dna-recommendations-6.1.0"]
    deep_diagnostics: Literal["deep-diagnostics-2.1.0"]
    share_renderer: Literal["share-svg-6.1.0"]
    interactions: Literal["report-interactions-1.1.0"]
    summary_history: Literal["summary-history-schema-3.0.0"]
    model: Literal["free-dna-model-6.1.0"]
    template: str
    analysis_version_fingerprint: str


class ReproducibilityV61Schema(PublicV6Model):
    generated_at: str
    input_snapshot_hash: str
    window_start: str | None = None
    window_end: str | None = None
    raw_match_count: int = Field(ge=0)
    usable_match_count: int = Field(ge=30)
    independent_session_count: int = Field(ge=0)
    bootstrap_iterations: Literal[2000]
    bootstrap_seed: str
    session_gap_minutes: int = Field(ge=1)
    baseline_artifact: Literal["context-baseline-3.0.0"]
    threshold_artifact: Literal["metric-thresholds-6.1.0"]
    history_contract: dict[str, Any]
    request_manifest: dict[str, Any]
    artifact_checksums: dict[str, str]

    @model_validator(mode="after")
    def validate_history_contract(self) -> ReproducibilityV61Schema:
        if self.history_contract.get("request_count") != 1:
            raise ValueError("V6.1 needs exactly one physical summary-history request")
        if self.history_contract.get("rank_or_mmr_used") is not False:
            raise ValueError("V6.1 cannot use rank or MMR")
        if self.request_manifest.get("projection_version") != "summary-projection-3.0.0":
            raise ValueError("V6.1 request manifest projection drift")
        return self


class QualityV61Schema(PublicV6Model):
    overall_confidence: ConfidenceTier
    history_tier: Literal["limited", "normal"]
    partial: bool
    warnings: list[str] = Field(default_factory=list)
    missing_data_flags: list[str] = Field(default_factory=list)
    available_elements: int = Field(ge=0, le=7)
    published_findings: int = Field(ge=0, le=3)


class VerificationV61Schema(PublicV6Model):
    eligibility_games: Literal[5]
    primary_metric: str
    guardrail_metric: str
    causal: Literal[False]
    abstention: Literal["too early to tell"]


class DeepHandoffV61Schema(PublicV6Model):
    cohort_reference: str
    unanswered_alternatives: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def opaque_reference(self) -> DeepHandoffV61Schema:
        if not self.cohort_reference.startswith("cohort:v61:"):
            raise ValueError("V6.1 public Deep handoff must use an opaque cohort reference")
        return self


class ClaimContractV61Schema(ClaimContractV6Schema):
    alternatives: list[str] = Field(min_length=1)
    verification: VerificationV61Schema | None = None
    interaction: str | None = None
    deep_handoff: DeepHandoffV61Schema
    copy_version: Literal["free-dna-semantic-copy-6.1.0"]


class MeasurementV61Schema(PublicV6Model):
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
    estimator_version: str


class ElementV61Schema(MeasurementV61Schema):
    pass


class FindingV61Schema(MeasurementV61Schema):
    family: str
    published: bool = False
    signal_keys: list[str] = Field(default_factory=list)
    outcome_key: str | None = None
    semantic_outcome_key: str | None = None
    hypothesis_branch: str | None = None
    raw_p_value: float = Field(default=1.0, ge=0, le=1)
    adjusted_q_value: float = Field(default=1.0, ge=0, le=1)
    branch_adjusted_q_value: float = Field(default=1.0, ge=0, le=1)
    interaction: dict[str, Any] = Field(default_factory=dict)
    claim_contract: ClaimContractV61Schema | None = None
    claim: str | None = None
    evidence_text: str | None = None
    interpretation: str | None = None


class IdentitySlotV61Schema(PublicV6Model):
    kind: Literal["PRIMARY", "TWIST", "ANCHOR"]
    scope: str = Field(min_length=1)
    text: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    family: str | None = None
    semantic_outcome_key: str | None = None
    stability: dict[str, Any] | None = None


class IdentitySlotsV61Schema(PublicV6Model):
    version: Literal["identity-slots-1.0.0"]
    primary: IdentitySlotV61Schema | None = None
    twist: IdentitySlotV61Schema | None = None
    anchor: IdentitySlotV61Schema | None = None
    compatibility: Literal["identity-slot-compatibility-1.0.0"]
    compatibility_checks: dict[str, bool]

    @model_validator(mode="after")
    def validate_slot_kinds(self) -> IdentitySlotsV61Schema:
        for name, expected in (
            ("primary", "PRIMARY"),
            ("twist", "TWIST"),
            ("anchor", "ANCHOR"),
        ):
            slot = getattr(self, name)
            if slot is not None and slot.kind != expected:
                raise ValueError(f"V6.1 {name} slot has the wrong kind")
        if not self.compatibility_checks or not all(self.compatibility_checks.values()):
            raise ValueError("V6.1 identity compatibility checks must all pass")
        return self


class IdentitySummaryV61Schema(PublicV6Model):
    headline: str
    supporting_lines: list[str] = Field(max_length=2)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: ConfidenceTier
    slots: IdentitySlotsV61Schema


class DiagnosticQuestionV61Schema(PublicV6Model):
    id: str
    version: Literal["deep-diagnostics-2.1.0"]
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
    protected_cohort_reference: str | None = None

    @model_validator(mode="after")
    def validate_protected_reference(self) -> DiagnosticQuestionV61Schema:
        if (
            self.protected_cohort_reference is not None
            and not self.protected_cohort_reference.startswith("cohort:v61:")
        ):
            raise ValueError("V6.1 Deep questions require an opaque cohort reference")
        return self


class StoryV61Schema(PublicV6Model):
    version: Literal["free-story-6.1.0"]
    ordered_beats: list[str] = Field(min_length=9, max_length=9)


class MethodologyV61Schema(PublicV6Model):
    free_summary_only: Literal[True]
    population_window_days: Literal[365]
    weighting: Literal["estimator_specific"]
    sessions_are_independence_unit: Literal[True]
    bootstrap_iterations: Literal[2000]
    family_roots: Literal[5]
    public_elements: Literal[7]
    hierarchical_error_control: Literal[True]
    calibration_status: Literal["fixture_synthetic_only", "automated_complete", "release_approved"]
    rank_or_mmr_used: Literal[False]
    shadow_enabled: bool
    experimental_evolution_enabled: bool
    experimental_loops_enabled: bool
    notes: list[str] = Field(default_factory=list)


class FreeDnaReportV61Schema(PublicV6Model):
    report_id: str | None = None
    schema_version: Literal["free-dna-report-6.1.0"]
    report_variant: Literal["free_dna_report"]
    noindex: Literal[True]
    identity: IdentityV6Schema
    metadata: MetadataV6Schema
    versions: VersionsV61Schema
    reproducibility: ReproducibilityV61Schema
    quality: QualityV61Schema
    elements: list[ElementV61Schema] = Field(min_length=7, max_length=7)
    findings: list[FindingV61Schema] = Field(min_length=5, max_length=5)
    identity_summary: IdentitySummaryV61Schema
    hero_portfolio: dict[str, Any]
    supporting_evidence: dict[str, Any]
    selection_audit: dict[str, Any]
    diagnostic_questions: list[DiagnosticQuestionV61Schema] = Field(max_length=3)
    story: StoryV61Schema
    pages: list[StoryPageV6Schema] = Field(min_length=9, max_length=9)
    share_candidates: list[ShareCandidateV6Schema] = Field(max_length=3)
    methodology: MethodologyV61Schema
    cost: FreeCostV6Schema

    @model_validator(mode="after")
    def validate_v61_contract(self) -> FreeDnaReportV61Schema:
        element_keys = [item.key for item in self.elements]
        if set(element_keys) != ELEMENT_KEYS or len(element_keys) != len(set(element_keys)):
            raise ValueError("Free DNA V6.1 must contain each of the seven Elements once")
        families = [item.family for item in self.findings]
        if set(families) != FINDING_FAMILIES or len(families) != len(set(families)):
            raise ValueError("Free DNA V6.1 must contain each of the five families once")
        if sum(item.published for item in self.findings) > 3:
            raise ValueError("Free DNA V6.1 can publish at most three findings")
        for item in self.findings:
            if item.published:
                semantic_key = item.semantic_outcome_key
                if (
                    semantic_key is None
                    or semantic_key not in SEMANTIC_OUTCOME_REGISTRY
                    or SEMANTIC_OUTCOME_REGISTRY[semantic_key].family_key != item.family
                    or item.claim_contract is None
                ):
                    raise ValueError("published V6.1 finding needs a registered outcome")
            elif any(
                (
                    item.semantic_outcome_key is not None,
                    item.hypothesis_branch is not None,
                    item.claim is not None,
                    item.interpretation is not None,
                    item.claim_contract is not None,
                    bool(item.interaction.get("enabled")),
                )
            ):
                raise ValueError("unpublished V6.1 family records must redact branch claims")
        if tuple(self.story.ordered_beats) != STORY_BEATS:
            raise ValueError("Free DNA V6.1 must preserve the nine-beat story")
        if [page.id for page in self.pages] != self.story.ordered_beats:
            raise ValueError("V6.1 pages must match the nine-beat story")
        if set(self.selection_audit) != FINDING_FAMILIES:
            raise ValueError("V6.1 selection audit must cover exactly five families")
        public = self.model_dump(mode="json", by_alias=True)
        forbidden_private_keys = {"match_ids", "account_id", "rank_tier", "average_rank", "mmr"}

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                leaked = forbidden_private_keys.intersection(value)
                if leaked:
                    raise ValueError(
                        f"V6.1 public report contains private cohort keys: {sorted(leaked)}"
                    )
                for nested in value.values():
                    walk(nested)
            elif isinstance(value, list):
                for nested in value:
                    walk(nested)

        walk(public)
        return self


def validate_free_dna_report_v61(report: dict[str, Any]) -> dict[str, Any]:
    return FreeDnaReportV61Schema.model_validate(report).model_dump(mode="json", by_alias=True)


__all__ = ["FreeDnaReportV61Schema", "validate_free_dna_report_v61"]

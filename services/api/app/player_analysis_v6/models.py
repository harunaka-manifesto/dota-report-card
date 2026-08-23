"""Immutable internal and public-facing contracts for Free DNA v6.

The report assembly layer can serialise these models without knowing how an
estimate was produced.  Public serialisation intentionally omits raw match
identifiers; evidence references are stable semantic keys, not a new source
of player-identifying analytics.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Literal

from .constants import (
    BASELINE_VERSION,
    BOOTSTRAP_VERSION,
    CLAIM_VERSION,
    DIAGNOSTICS_VERSION,
    ELEMENTS_VERSION,
    FINDING_FAMILY_KEYS,
    FINDINGS_VERSION,
    INTERACTION_VERSION,
    PUBLIC_ELEMENT_KEYS,
    REPORT_VERSION,
    SEMANTIC_COPY_VERSION,
    SHARE_VERSION,
    STORY_BEAT_KEYS,
    STORY_VERSION,
)

EstimateStatus = Literal["available", "limited", "unavailable"]
ConfidenceTier = Literal["high", "moderate", "descriptive", "unavailable"]
Direction = Literal["positive", "negative", "neutral", "mixed", "unknown"]
FindingStatus = Literal["qualified", "suppressed", "unavailable"]


def _freeze(value: Any) -> Any:
    """Recursively freeze JSON-like values used in public contracts."""

    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value: Any) -> Any:
    """Convert frozen values to JSON-compatible mutable values."""

    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, frozenset)):
        return [_plain(item) for item in value]
    return value


def _finite(value: float | int | None, name: str) -> None:
    if value is not None and not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class Estimate:
    """A bounded estimate shared by Elements and family evidence."""

    value: float | None
    unit: str
    interval: tuple[float, float] | None = None
    zone: str | None = None
    direction: Direction = "unknown"
    stability: float = 0.0
    sample_size: int = 0
    independent_sessions: int = 0
    coverage: float = 0.0
    confidence: ConfidenceTier = "unavailable"
    status: EstimateStatus = "unavailable"
    evidence_refs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    supported_claims: tuple[str, ...] = ()
    forbidden_claims: tuple[str, ...] = ()
    bootstrap_method: str = ""

    def __post_init__(self) -> None:
        _finite(self.value, "estimate.value")
        _finite(self.stability, "estimate.stability")
        _finite(self.coverage, "estimate.coverage")
        if not 0.0 <= float(self.stability) <= 1.0:
            raise ValueError("estimate.stability must be within [0, 1]")
        if not 0.0 <= float(self.coverage) <= 1.0:
            raise ValueError("estimate.coverage must be within [0, 1]")
        if self.sample_size < 0 or self.independent_sessions < 0:
            raise ValueError("estimate sample sizes must be non-negative")
        if self.interval is not None:
            if len(self.interval) != 2:
                raise ValueError("estimate.interval must contain lower and upper bounds")
            lower, upper = map(float, self.interval)
            if not math.isfinite(lower) or not math.isfinite(upper) or lower > upper:
                raise ValueError("estimate.interval must be finite and ordered")
        object.__setattr__(self, "evidence_refs", tuple(str(item) for item in self.evidence_refs))
        object.__setattr__(self, "limitations", tuple(str(item) for item in self.limitations))
        object.__setattr__(self, "supported_claims", tuple(str(item) for item in self.supported_claims))
        object.__setattr__(self, "forbidden_claims", tuple(str(item) for item in self.forbidden_claims))

    @property
    def lower(self) -> float | None:
        return self.interval[0] if self.interval else None

    @property
    def upper(self) -> float | None:
        return self.interval[1] if self.interval else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "interval": list(self.interval) if self.interval else None,
            "zone": self.zone,
            "direction": self.direction,
            "stability": round(self.stability, 6),
            "sample_size": self.sample_size,
            "independent_sessions": self.independent_sessions,
            "coverage": round(self.coverage, 6),
            "confidence": self.confidence,
            "status": self.status,
            "evidence_refs": list(self.evidence_refs),
            "limitations": list(self.limitations),
            "supported_claims": list(self.supported_claims),
            "forbidden_claims": list(self.forbidden_claims),
            "bootstrap_method": self.bootstrap_method or None,
        }


@dataclass(frozen=True, slots=True)
class ElementDefinition:
    key: str
    label: str
    description: str
    unit: str
    metric_key: str
    minimum_sample: int = 30
    minimum_sessions: int = 1
    minimum_coverage: float = 0.0
    axis_left: str | None = None
    axis_right: str | None = None
    version: str = ELEMENTS_VERSION
    forbidden_claims: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "unit": self.unit,
            "metric_key": self.metric_key,
            "minimum_sample": self.minimum_sample,
            "minimum_sessions": self.minimum_sessions,
            "minimum_coverage": self.minimum_coverage,
            "axis": {"left": self.axis_left, "right": self.axis_right},
            "version": self.version,
            "forbidden_claims": list(self.forbidden_claims),
        }


@dataclass(frozen=True, slots=True)
class ElementResultV6:
    key: str
    label: str
    estimate: Estimate
    definition_version: str = ELEMENTS_VERSION
    raw_metrics: Mapping[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    source_match_ids: tuple[int, ...] = ()
    internal_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.key not in PUBLIC_ELEMENT_KEYS:
            raise ValueError(f"Unknown v6 public Element: {self.key}")
        object.__setattr__(self, "raw_metrics", _freeze(self.raw_metrics))
        object.__setattr__(self, "evidence_refs", tuple(str(item) for item in self.evidence_refs))
        object.__setattr__(self, "source_match_ids", tuple(int(item) for item in self.source_match_ids))
        object.__setattr__(self, "internal_notes", tuple(str(item) for item in self.internal_notes))

    @property
    def status(self) -> EstimateStatus:
        return self.estimate.status

    @property
    def confidence(self) -> ConfidenceTier:
        return self.estimate.confidence

    @property
    def value(self) -> float | None:
        return self.estimate.value

    @property
    def interval(self) -> tuple[float, float] | None:
        return self.estimate.interval

    @property
    def zone(self) -> str | None:
        return self.estimate.zone

    @property
    def stability(self) -> float:
        return self.estimate.stability

    @property
    def sample_size(self) -> int:
        return self.estimate.sample_size

    @property
    def independent_sessions(self) -> int:
        return self.estimate.independent_sessions

    @property
    def coverage(self) -> float:
        return self.estimate.coverage

    def as_dict(self, *, public: bool = True) -> dict[str, Any]:
        value: dict[str, Any] = {
            "key": self.key,
            "label": self.label,
            "estimate": self.estimate.as_dict(),
            "definition_version": self.definition_version,
            "evidence_refs": list(self.evidence_refs or self.estimate.evidence_refs),
        }
        if not public:
            value.update(
                {
                    "raw_metrics": _plain(self.raw_metrics),
                    "source_match_ids": list(self.source_match_ids),
                    "internal_notes": list(self.internal_notes),
                }
            )
        return value


# Friendly aliases used by assembly code and callers migrating from the v5
# ElementResult name.
ElementResult = ElementResultV6
PublicElement = ElementResultV6


@dataclass(frozen=True, slots=True)
class FamilyEvidence:
    key: str
    value: float | None = None
    unit: str = ""
    interval: tuple[float, float] | None = None
    signal: Direction = "unknown"
    sample_size: int = 0
    independent_sessions: int = 0
    coverage: float = 0.0
    evidence_refs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _finite(self.value, "family evidence value")
        if not 0 <= self.coverage <= 1:
            raise ValueError("family evidence coverage must be within [0, 1]")
        object.__setattr__(self, "evidence_refs", tuple(str(item) for item in self.evidence_refs))
        object.__setattr__(self, "limitations", tuple(str(item) for item in self.limitations))

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "unit": self.unit,
            "interval": list(self.interval) if self.interval else None,
            "signal": self.signal,
            "sample_size": self.sample_size,
            "independent_sessions": self.independent_sessions,
            "coverage": self.coverage,
            "evidence_refs": list(self.evidence_refs),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class FindingFamilyResult:
    family: str
    status: FindingStatus
    direction: Direction = "unknown"
    confidence: ConfidenceTier = "unavailable"
    confidence_score: float = 0.0
    identity_value: float = 0.0
    actionability: float = 0.0
    diversity_score: float = 0.0
    p_value: float | None = None
    q_value: float | None = None
    published: bool = False
    estimate: Estimate | None = None
    evidence: tuple[FamilyEvidence, ...] = ()
    claim: str | None = None
    evidence_text: str | None = None
    interpretation: str | None = None
    recommendation: str | None = None
    qualification_reason: str | None = None
    limitations: tuple[str, ...] = ()
    diagnostic_question_ids: tuple[str, ...] = ()
    blocking_confounders: tuple[str, ...] = ()
    version: str = FINDINGS_VERSION

    def __post_init__(self) -> None:
        if self.family not in FINDING_FAMILY_KEYS:
            raise ValueError(f"Unknown v6 finding family: {self.family}")
        for name in ("confidence_score", "identity_value", "actionability", "diversity_score"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")
        if self.p_value is not None and not 0.0 <= self.p_value <= 1.0:
            raise ValueError("p_value must be within [0, 1]")
        if self.q_value is not None and not 0.0 <= self.q_value <= 1.0:
            raise ValueError("q_value must be within [0, 1]")
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "limitations", tuple(str(item) for item in self.limitations))
        object.__setattr__(self, "diagnostic_question_ids", tuple(str(item) for item in self.diagnostic_question_ids))
        object.__setattr__(self, "blocking_confounders", tuple(str(item) for item in self.blocking_confounders))

    @property
    def evidence_refs(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(ref for item in self.evidence for ref in item.evidence_refs))

    @property
    def sample_size(self) -> int:
        if self.estimate is not None:
            return self.estimate.sample_size
        return max((item.sample_size for item in self.evidence), default=0)

    @property
    def independent_sessions(self) -> int:
        if self.estimate is not None:
            return self.estimate.independent_sessions
        return max((item.independent_sessions for item in self.evidence), default=0)

    @property
    def coverage(self) -> float:
        if self.estimate is not None:
            return self.estimate.coverage
        return max((item.coverage for item in self.evidence), default=0.0)

    @property
    def interval(self) -> tuple[float, float] | None:
        return self.estimate.interval if self.estimate else None

    @property
    def stability(self) -> float:
        return self.estimate.stability if self.estimate else self.confidence_score

    @property
    def zone(self) -> str | None:
        return self.estimate.zone if self.estimate else self.direction

    def as_dict(self, *, public: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "family": self.family,
            "status": self.status,
            "direction": self.direction,
            "confidence": self.confidence,
            "confidence_score": round(self.confidence_score, 6),
            "identity_value": round(self.identity_value, 6),
            "actionability": round(self.actionability, 6),
            "diversity_score": round(self.diversity_score, 6),
            "p_value": self.p_value,
            "q_value": self.q_value,
            "published": self.published,
            "estimate": self.estimate.as_dict() if self.estimate else None,
            "evidence": [item.as_dict() for item in self.evidence],
            "claim": self.claim,
            "evidence_text": self.evidence_text,
            "interpretation": self.interpretation,
            "recommendation": self.recommendation,
            "qualification_reason": self.qualification_reason,
            "limitations": list(self.limitations),
            "diagnostic_question_ids": list(self.diagnostic_question_ids),
            "blocking_confounders": list(self.blocking_confounders),
            "version": self.version,
        }
        if not public:
            result["evidence_refs"] = list(self.evidence_refs)
        # A public result's claims must be explicit even when a family is
        # suppressed or unavailable; this makes abstention machine-readable.
        return result


FindingResult = FindingFamilyResult


@dataclass(frozen=True, slots=True)
class IdentitySummary:
    headline: str
    supporting_lines: tuple[str, ...] = ()
    confidence: ConfidenceTier = "unavailable"
    evidence_refs: tuple[str, ...] = ()
    anchor: str | None = None
    finding_families: tuple[str, ...] = ()
    version: str = REPORT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "supporting_lines", tuple(str(item) for item in self.supporting_lines))
        object.__setattr__(self, "evidence_refs", tuple(str(item) for item in self.evidence_refs))
        object.__setattr__(self, "finding_families", tuple(str(item) for item in self.finding_families))

    def as_dict(self) -> dict[str, Any]:
        return {
            "headline": self.headline,
            "supporting_lines": list(self.supporting_lines),
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "anchor": self.anchor,
            "finding_families": list(self.finding_families),
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class DiagnosticQuestion:
    question_id: str
    prompt: str
    family: str
    evidence_refs: tuple[str, ...] = ()
    confidence: ConfidenceTier = "moderate"
    offered: bool = True
    order: int = 0
    version: str = DIAGNOSTICS_VERSION

    def __post_init__(self) -> None:
        if self.family not in FINDING_FAMILY_KEYS:
            raise ValueError(f"Unknown diagnostic family: {self.family}")
        object.__setattr__(self, "evidence_refs", tuple(str(item) for item in self.evidence_refs))

    def as_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "prompt": self.prompt,
            "family": self.family,
            "evidence_refs": list(self.evidence_refs),
            "confidence": self.confidence,
            "offered": self.offered,
            "order": self.order,
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class StoryBeat:
    key: str
    order: int
    title: str
    prompt: str
    interaction: str
    skippable: bool = True
    keyboard_accessible: bool = True
    reduced_motion_safe: bool = True
    available: bool = True
    payload_refs: tuple[str, ...] = ()
    version: str = STORY_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "order": self.order,
            "title": self.title,
            "prompt": self.prompt,
            "interaction": self.interaction,
            "skippable": self.skippable,
            "keyboard_accessible": self.keyboard_accessible,
            "reduced_motion_safe": self.reduced_motion_safe,
            "available": self.available,
            "payload_refs": list(self.payload_refs),
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class ShareCandidate:
    candidate_id: str
    kind: Literal["identity", "finding", "hero_mirror"]
    title: str
    eligible: bool
    reason: str
    evidence_refs: tuple[str, ...] = ()
    confidence: ConfidenceTier = "unavailable"
    blocking_reasons: tuple[str, ...] = ()
    version: str = SHARE_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(str(item) for item in self.evidence_refs))
        object.__setattr__(self, "blocking_reasons", tuple(str(item) for item in self.blocking_reasons))

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "kind": self.kind,
            "title": self.title,
            "eligible": self.eligible,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
            "confidence": self.confidence,
            "blocking_reasons": list(self.blocking_reasons),
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class FreeCostLedger:
    """Hard boundary for Free v6 source costs.

    Free's only upstream history operation is one summary-history read.  The
    ledger is intentionally stricter than the general analysis budget: detail
    and parse calls are always rejected, even if a caller has spare capacity.
    """

    history_reads: int = 0
    detail_reads: int = 0
    parse_calls: int = 0
    history_limit: int = 1
    detail_limit: int = 0
    parse_limit: int = 0
    version: str = REPORT_VERSION

    def __post_init__(self) -> None:
        for name in ("history_reads", "detail_reads", "parse_calls", "history_limit", "detail_limit", "parse_limit"):
            if int(getattr(self, name)) < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.history_reads > self.history_limit:
            raise ValueError("Free history-read invariant exceeded")
        if self.detail_reads != 0 or self.parse_calls != 0:
            raise ValueError("Free v6 cannot perform detail or parse calls")
        if self.detail_limit != 0 or self.parse_limit != 0:
            raise ValueError("Free v6 detail and parse limits must remain zero")

    @property
    def compliant(self) -> bool:
        return (
            self.history_reads <= 1
            and self.detail_reads == 0
            and self.parse_calls == 0
            and self.detail_limit == 0
            and self.parse_limit == 0
        )

    @property
    def history_requests(self) -> int:
        return self.history_reads

    @property
    def detail_requests(self) -> int:
        return self.detail_reads

    @property
    def parse_requests(self) -> int:
        return self.parse_calls

    def record_history(self) -> FreeCostLedger:
        if self.history_reads >= self.history_limit:
            raise ValueError("Free history-read limit exceeded")
        return replace(self, history_reads=self.history_reads + 1)

    def record_detail(self, count: int = 1) -> FreeCostLedger:
        if count:
            raise ValueError("Free v6 cannot record detail reads")
        return self

    def record_parse(self, count: int = 1) -> FreeCostLedger:
        if count:
            raise ValueError("Free v6 cannot record parse calls")
        return self

    def as_dict(self) -> dict[str, Any]:
        return {
            "history_reads": self.history_reads,
            "detail_reads": self.detail_reads,
            "parse_calls": self.parse_calls,
            "limits": {
                "history_reads": self.history_limit,
                "detail_reads": self.detail_limit,
                "parse_calls": self.parse_limit,
            },
            "compliant": self.compliant,
            "version": self.version,
        }


CostLedger = FreeCostLedger


def default_versions() -> dict[str, str]:
    return {
        "report": REPORT_VERSION,
        "elements": ELEMENTS_VERSION,
        "findings": FINDINGS_VERSION,
        "expression": "summary-expression-multisignal-1.0.0",
        "bootstrap": BOOTSTRAP_VERSION,
        "baseline": BASELINE_VERSION,
        "thresholds": "metric-thresholds-6.0.0",
        "claims": CLAIM_VERSION,
        "story": STORY_VERSION,
        "semantic_copy": SEMANTIC_COPY_VERSION,
        "diagnostics": DIAGNOSTICS_VERSION,
        "share": SHARE_VERSION,
        "interactions": INTERACTION_VERSION,
    }


@dataclass(frozen=True, slots=True)
class FreeDnaReportV6:
    """Complete summary-only v6 result consumed by the API assembly layer."""

    identity: IdentitySummary
    elements: tuple[ElementResultV6, ...]
    findings: tuple[FindingFamilyResult, ...]
    story: tuple[StoryBeat, ...]
    diagnostic_questions: tuple[DiagnosticQuestion, ...] = ()
    share_candidates: tuple[ShareCandidate, ...] = ()
    hero_portfolio: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    reproducibility: Mapping[str, Any] = field(default_factory=dict)
    quality: Mapping[str, Any] = field(default_factory=dict)
    pages: tuple[Mapping[str, Any], ...] = ()
    methodology: Mapping[str, Any] = field(default_factory=dict)
    cost: FreeCostLedger = field(default_factory=FreeCostLedger)
    versions: Mapping[str, str] = field(default_factory=default_versions)
    report_version: str = REPORT_VERSION

    def __post_init__(self) -> None:
        if len(self.elements) != len(PUBLIC_ELEMENT_KEYS):
            raise ValueError("Free v6 reports must expose exactly seven Elements")
        keys = tuple(item.key for item in self.elements)
        if keys != PUBLIC_ELEMENT_KEYS:
            raise ValueError(f"Free v6 Elements must be ordered as {PUBLIC_ELEMENT_KEYS}")
        if len(self.findings) != len(FINDING_FAMILY_KEYS):
            raise ValueError("Free v6 reports must expose exactly five finding families")
        families = tuple(item.family for item in self.findings)
        if families != FINDING_FAMILY_KEYS:
            raise ValueError(f"Free v6 findings must be ordered as {FINDING_FAMILY_KEYS}")
        beat_keys = tuple(item.key for item in self.story)
        if beat_keys != STORY_BEAT_KEYS:
            raise ValueError(f"Free v6 story must contain nine ordered beats: {STORY_BEAT_KEYS}")
        if len(self.diagnostic_questions) > 3:
            raise ValueError("Free v6 offers at most three diagnostic questions")
        if not self.cost.compliant:
            raise ValueError("Free v6 cost ledger is not compliant")
        object.__setattr__(self, "elements", tuple(self.elements))
        object.__setattr__(self, "findings", tuple(self.findings))
        object.__setattr__(self, "story", tuple(self.story))
        object.__setattr__(self, "diagnostic_questions", tuple(self.diagnostic_questions))
        object.__setattr__(self, "share_candidates", tuple(self.share_candidates))
        object.__setattr__(self, "hero_portfolio", _freeze(self.hero_portfolio))
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        object.__setattr__(self, "reproducibility", _freeze(self.reproducibility))
        object.__setattr__(self, "quality", _freeze(self.quality))
        object.__setattr__(self, "pages", tuple(_freeze(item) for item in self.pages))
        object.__setattr__(self, "methodology", _freeze(self.methodology))
        object.__setattr__(self, "versions", _freeze(self.versions))

    @property
    def published_findings(self) -> tuple[FindingFamilyResult, ...]:
        return tuple(item for item in self.findings if item.published)

    def as_dict(self, *, public: bool = True) -> dict[str, Any]:
        return {
            "identity": self.identity.as_dict(),
            "metadata": _plain(self.metadata),
            "versions": _plain(self.versions),
            "reproducibility": _plain(self.reproducibility),
            "quality": _plain(self.quality),
            "elements": [item.as_dict(public=public) for item in self.elements],
            "findings": [item.as_dict(public=public) for item in self.findings],
            "identity_summary": self.identity.as_dict(),
            "hero_portfolio": _plain(self.hero_portfolio),
            "diagnostic_questions": [item.as_dict() for item in self.diagnostic_questions],
            "story": [item.as_dict() for item in self.story],
            "pages": [_plain(item) for item in self.pages],
            "share_candidates": [item.as_dict() for item in self.share_candidates],
            "methodology": _plain(self.methodology),
            "cost": self.cost.as_dict(),
            "report_version": self.report_version,
        }


ReportV6 = FreeDnaReportV6


__all__ = [
    "Estimate",
    "ElementDefinition",
    "ElementResultV6",
    "ElementResult",
    "PublicElement",
    "FamilyEvidence",
    "FindingFamilyResult",
    "FindingResult",
    "IdentitySummary",
    "DiagnosticQuestion",
    "StoryBeat",
    "ShareCandidate",
    "FreeCostLedger",
    "CostLedger",
    "FreeDnaReportV6",
    "ReportV6",
    "default_versions",
]

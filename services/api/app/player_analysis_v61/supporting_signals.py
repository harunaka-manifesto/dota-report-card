"""Typed private signal graph and complete 128-feature classification catalog."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal

from app.player_analysis_v6.constants import FINDING_FAMILY_KEYS, PUBLIC_ELEMENT_KEYS

from .versions import SUPPORTING_SIGNALS_VERSION

SignalClassification = Literal[
    "PUBLIC_ELEMENT_SUPPORT",
    "SUPPORTING",
    "CONDITIONAL",
    "LONGITUDINAL",
    "FINDING_ONLY",
    "RESEARCH_ONLY",
    "REJECTED",
]
SignalStatus = Literal[
    "available",
    "mixed",
    "insufficient",
    "unavailable",
    "suppressed",
    "experimental",
]
PublicExposure = Literal["never", "evidence_only", "named_when_qualified"]


@dataclass(frozen=True, slots=True)
class OpportunityContract:
    denominator: str
    minimum_matches: int = 0
    minimum_sessions: int = 0
    minimum_events: int = 0
    minimum_coverage: float = 0.0

    def __post_init__(self) -> None:
        if not self.denominator:
            raise ValueError("supporting signals need an opportunity denominator")
        if min(self.minimum_matches, self.minimum_sessions, self.minimum_events) < 0:
            raise ValueError("opportunity minimums must be non-negative")
        if not 0 <= self.minimum_coverage <= 1:
            raise ValueError("opportunity coverage must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class SupportingSignalDefinition:
    key: str
    classification: SignalClassification
    source_fields: tuple[str, ...]
    opportunity_contract: OpportunityContract
    estimator_version: str
    normalization_version: str
    coverage_contract: str
    public_exposure: PublicExposure
    allowed_consumers: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    rejected_reason: str | None = None
    version: str = SUPPORTING_SIGNALS_VERSION

    def __post_init__(self) -> None:
        if not self.key or not self.estimator_version or not self.normalization_version:
            raise ValueError("supporting signals need key and versioned estimators")
        if not self.source_fields:
            raise ValueError(f"{self.key} needs source fields")
        if self.classification in {"RESEARCH_ONLY", "REJECTED"} and self.public_exposure != "never":
            raise ValueError(f"{self.key} cannot have public exposure")
        if self.classification == "REJECTED" and not self.rejected_reason:
            raise ValueError(f"{self.key} needs a rejected reason")
        allowed = set(PUBLIC_ELEMENT_KEYS) | set(FINDING_FAMILY_KEYS) | {"identity", "deep", "calibration"}
        unknown = set(self.allowed_consumers) - allowed
        if unknown:
            raise ValueError(f"{self.key} has unknown consumers: {sorted(unknown)}")


@dataclass(frozen=True, slots=True)
class SupportingSignalResult:
    key: str
    status: SignalStatus
    estimate: float | None = None
    components: Mapping[str, Any] = field(default_factory=dict)
    interval: tuple[float, float] | None = None
    opportunities: int = 0
    sessions: int = 0
    coverage: float = 0.0
    robustness: Mapping[str, Any] = field(default_factory=dict)
    limitations: tuple[str, ...] = ()
    provenance: Mapping[str, str] = field(default_factory=dict)

    def as_public_evidence(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "status": self.status,
            "estimate": self.estimate,
            "components": dict(self.components),
            "interval": list(self.interval) if self.interval else None,
            "opportunities": self.opportunities,
            "sessions": self.sessions,
            "coverage": self.coverage,
            "robustness": dict(self.robustness),
            "limitations": list(self.limitations),
            "provenance": dict(self.provenance),
        }


_GROUPS: Mapping[str, tuple[str, SignalClassification, tuple[str, ...], tuple[str, ...]]] = {
    "A": ("atomic", "PUBLIC_ELEMENT_SUPPORT", ("match_id", "start_time", "duration", "hero_id", "kills", "deaths", "assists", "radiant_win", "player_slot"), tuple(PUBLIC_ELEMENT_KEYS)),
    "X": ("contextual", "SUPPORTING", ("duration", "hero_id", "lane", "lane_role", "is_roaming"), ("involvement", "death_exposure", "combat_expression")),
    "L": ("longitudinal", "LONGITUDINAL", ("start_time", "hero_id", "kills", "deaths", "assists"), ("pool_shape", "identity")),
    "T": ("transitional", "CONDITIONAL", ("start_time", "radiant_win", "player_slot", "hero_id"), ("post_loss_response", "transfer")),
    "Q": ("sequential", "RESEARCH_ONLY", ("start_time", "radiant_win", "player_slot", "hero_id"), ("calibration",)),
    "P": ("portfolio", "SUPPORTING", ("hero_id", "start_time"), ("breadth", "toolkit", "pool_shape", "transfer")),
    "C": ("conditional", "FINDING_ONLY", ("hero_id", "duration", "kills", "deaths", "assists", "radiant_win", "player_slot"), ("combat_expression", "session_drift")),
    "M": ("meta", "RESEARCH_ONLY", ("match_id", "start_time", "version", "hero_variant", "party_size", "cluster"), ("calibration",)),
}

# Research features whose inference is outside the one-call public boundary.
_REJECTED = {
    "X13": "actual role cannot be inferred from sparse summary lane fields",
    "X14": "positioning is unavailable in summary history",
    "X15": "aggression or intent is not observable",
    "X16": "death quality is not observable",
    "M09": "rank/MMR conditioning is forbidden",
    "M10": "local time cannot be inferred from UTC and cluster",
    "M11": "patch causality is not identifiable",
    "M12": "final inventory is not item-build identity",
}


def _catalog() -> tuple[SupportingSignalDefinition, ...]:
    definitions: list[SupportingSignalDefinition] = []
    for prefix, (name, classification, fields, consumers) in _GROUPS.items():
        for index in range(1, 17):
            code = f"{prefix}{index:02d}"
            rejected_reason = _REJECTED.get(code)
            effective_classification: SignalClassification = (
                "REJECTED" if rejected_reason else classification
            )
            exposure: PublicExposure
            if effective_classification in {"RESEARCH_ONLY", "REJECTED"}:
                exposure = "never"
            elif effective_classification in {"CONDITIONAL", "FINDING_ONLY", "LONGITUDINAL"}:
                exposure = "named_when_qualified"
            else:
                exposure = "evidence_only"
            definitions.append(
                SupportingSignalDefinition(
                    key=code,
                    classification=effective_classification,
                    source_fields=fields,
                    opportunity_contract=OpportunityContract(
                        denominator=(
                            "sessions" if prefix in {"L", "Q"} else
                            "transitions" if prefix == "T" else
                            "matches"
                        ),
                        minimum_matches=30,
                        minimum_sessions=8 if prefix in {"L", "T", "Q", "C"} else 1,
                        minimum_coverage=0.80 if prefix in {"X", "M"} else 0.0,
                    ),
                    estimator_version=f"{name}-features-1.0.0",
                    normalization_version="summary-normalization-2.0.0",
                    coverage_contract="availability-before-effect-1.0.0",
                    public_exposure=exposure,
                    allowed_consumers=("calibration",) if rejected_reason else consumers,
                    rejected_reason=rejected_reason,
                )
            )
    return tuple(definitions)


SUPPORTING_SIGNAL_CATALOG = _catalog()
SUPPORTING_SIGNAL_REGISTRY = MappingProxyType(
    {definition.key: definition for definition in SUPPORTING_SIGNAL_CATALOG}
)


def validate_supporting_signal_registry(
    definitions: Iterable[SupportingSignalDefinition] = SUPPORTING_SIGNAL_CATALOG,
) -> tuple[SupportingSignalDefinition, ...]:
    ordered = tuple(definitions)
    keys = [definition.key for definition in ordered]
    if len(keys) != 128 or len(set(keys)) != 128:
        raise ValueError("V6.1 must classify exactly 128 unique research features")
    known = set(keys)
    for definition in ordered:
        missing = set(definition.dependencies) - known
        if missing:
            raise ValueError(f"{definition.key} has unknown dependencies: {sorted(missing)}")
    # Deterministic DFS cycle check even though the initial catalog is flat.
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(key: str) -> None:
        if key in visiting:
            raise ValueError(f"supporting signal dependency cycle at {key}")
        if key in visited:
            return
        visiting.add(key)
        for dependency in SUPPORTING_SIGNAL_REGISTRY[key].dependencies:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)

    for key in keys:
        visit(key)
    return ordered


validate_supporting_signal_registry()

__all__ = [
    "OpportunityContract",
    "SUPPORTING_SIGNAL_CATALOG",
    "SUPPORTING_SIGNAL_REGISTRY",
    "SupportingSignalDefinition",
    "SupportingSignalResult",
    "validate_supporting_signal_registry",
]

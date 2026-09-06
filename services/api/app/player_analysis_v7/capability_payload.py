"""The frontend-facing V7 capability payload.

Implements `docs/architecture/v7-runtime-capability-payload.md`.

**Capability-oriented, not screen-oriented.** The payload says what is true
about a player; it never says what to show first. Sequence, hierarchy and
emphasis belong to the frontend, and nothing here encodes them — the one
ordering the payload carries is the analytical ranking, which is a property of
the measurement rather than a display decision.

The models a Finding, Recommendation and Archetype are made of already exist in
``report_contract`` and are reused verbatim. This module adds the envelope: the
metadata, the availability and refusal machinery, the provenance block, and the
invariants that make a malformed payload impossible to construct rather than
merely discouraged.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any, Literal

from pydantic import Field, model_validator

from app.player_analysis_v7.acquisition_policy import ACQUISITION_POLICY_VERSION
from app.player_analysis_v7.report_contract import (
    ArchetypeSection,
    Finding,
    PublicV7Model,
    RankDisplay,
    Recommendation,
)
from app.player_analysis_v7.research.corpus import FORBIDDEN_FIELD_TOKENS
from app.player_analysis_v7.research.ranking import (
    FINDING_FLOOR,
    FINDING_SECTIONS,
    REPORT_SLOTS,
    SCORE_LINE,
)

V7_CAPABILITY_SCHEMA_VERSION = "v7-capability-payload-1.0.0"

CapabilityKey = Literal[
    "findings",
    "recommendation",
    "archetype",
    "dominant_mode",
    "rank_display",
]
"""Every capability the payload can carry. ``availability`` covers all of them,
always, so a frontend never has to infer absence from a missing key."""

CAPABILITY_KEYS: tuple[str, ...] = (
    "findings",
    "recommendation",
    "archetype",
    "dominant_mode",
    "rank_display",
)

#: Capabilities whose payload field is nullable and must agree with
#: ``availability``. ``findings`` is handled separately because its "absent"
#: form is an empty list rather than ``None``.
NULLABLE_CAPABILITIES: tuple[str, ...] = ("recommendation", "archetype")

RefusalCode = Literal[
    "profile_private",
    "insufficient_history",
    "insufficient_parsed_support",
    "no_dominant_mode_stratum",
    "insufficient_event_support",
    "insufficient_sessions",
    "insufficient_wins_or_losses_per_arm",
    "no_valid_opportunities",
    "fewer_than_floor_dimensions",
    "acquisition_failed",
    "not_collected",
]

#: What each refusal means for a caller deciding whether to offer a retry:
#: ``(retry_may_change, more_matches_may_change, permanently_unsupported)``.
#:
#: These are documented semantics, not free-form booleans, so ``Refusal``
#: validates its own fields against this table. A caller cannot ship a refusal
#: that promises "play more games and this appears" for a reason more games
#: cannot fix.
REFUSAL_SEMANTICS: dict[str, tuple[bool, bool, bool]] = {
    "profile_private": (True, False, False),
    "insufficient_history": (True, True, False),
    "insufficient_parsed_support": (True, True, False),
    "no_dominant_mode_stratum": (True, True, False),
    "insufficient_event_support": (True, True, False),
    "insufficient_sessions": (True, True, False),
    "insufficient_wins_or_losses_per_arm": (True, True, False),
    "no_valid_opportunities": (True, True, False),
    "fewer_than_floor_dimensions": (True, True, False),
    "acquisition_failed": (True, False, False),
    "not_collected": (True, False, False),
}

#: Dimensions that estimate zero between-player spread and therefore produce no
#: Finding at all. A payload carrying one is a defect in the assembler, not a
#: display choice, so the contract fails closed on it.
#:
#: ``side_sensitivity`` is the negative control: a deliberate placebo whose
#: silence is the evidence that the estimator does not manufacture Findings out
#: of noise. It must never reach a reader under any circumstance.
WITHHELD_DIMENSIONS: frozenset[str] = frozenset(
    {
        "transfer_risk",
        "transfer_activity",
        "lane_to_map",
        "lane_recovery_participation",
        "side_sensitivity",
    }
)


def _reject_non_finite(value: float, field: str) -> float:
    """``json.dumps`` happily emits ``NaN`` and ``Infinity``, neither of which
    is valid JSON, so a frontend parser rejects the whole document. Catch it
    where the number enters rather than where the response fails."""

    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite, got {value!r}")
    return value


class ReportMetadata(PublicV7Model):
    """When the report was made and what span of play it rests on."""

    generated_at: str = Field(min_length=1, description="ISO-8601 UTC")
    window_days: int = Field(ge=1)
    window_start: int = Field(ge=0, description="epoch seconds")
    window_end: int = Field(ge=0, description="epoch seconds")
    matches_total: int = Field(ge=0)
    matches_analysed: int = Field(ge=0)
    matches_with_event_detail: int = Field(ge=0)
    acquisition_depth: int = Field(ge=0)

    @model_validator(mode="after")
    def counts_are_coherent(self) -> ReportMetadata:
        if self.window_end < self.window_start:
            raise ValueError("window_end precedes window_start")
        if self.matches_analysed > self.matches_total:
            raise ValueError("matches_analysed exceeds matches_total")
        if self.matches_with_event_detail > self.matches_analysed:
            raise ValueError("matches_with_event_detail exceeds matches_analysed")
        return self


class PlayerContext(PublicV7Model):
    """The frame the archetype output is expressed in, plus display-only rank.

    ``dominant_mode`` is not decoration: every archetype axis is cut inside it,
    so "mid tempo" means mid *among players who mostly queue this mode*.

    ``rank_display`` is display-only and fenced from the analysis at the code
    level (``research.rank_fence``). It appears here so a frontend can show it
    as history; nothing analytical may read it.
    """

    dominant_mode: Literal["STANDARD", "TURBO"] | None = None
    rank_display: RankDisplay | None = None


class CapabilityAvailability(PublicV7Model):
    """Whether one capability is present, and if not, the machine-readable why.

    ``detail`` is factual backend state for logs and debugging. It is never
    user-facing copy: the frontend owns presentation, the backend states fact.
    """

    status: Literal["available", "refused"]
    refusal_code: RefusalCode | None = None
    detail: str | None = None

    @model_validator(mode="after")
    def refusal_code_matches_status(self) -> CapabilityAvailability:
        if self.status == "refused" and self.refusal_code is None:
            raise ValueError("a refused capability must carry a refusal_code")
        if self.status == "available" and self.refusal_code is not None:
            raise ValueError("an available capability must not carry a refusal_code")
        return self


class Refusal(PublicV7Model):
    """One refusal, with what a caller can honestly say about changing it."""

    capability: CapabilityKey
    code: RefusalCode
    retry_may_change: bool
    more_matches_may_change: bool
    permanently_unsupported: bool

    @model_validator(mode="after")
    def semantics_match_the_documented_code(self) -> Refusal:
        expected = REFUSAL_SEMANTICS[self.code]
        actual = (
            self.retry_may_change,
            self.more_matches_may_change,
            self.permanently_unsupported,
        )
        if actual != expected:
            raise ValueError(
                f"refusal {self.code!r} carries {actual!r} but its documented "
                f"semantics are {expected!r}; the code and its meaning must agree"
            )
        return self

    @classmethod
    def of(cls, capability: str, code: str) -> Refusal:
        """Build a refusal with the documented semantics for ``code``."""

        retry, more_matches, permanent = REFUSAL_SEMANTICS[code]
        return cls(
            capability=capability,  # type: ignore[arg-type]
            code=code,  # type: ignore[arg-type]
            retry_may_change=retry,
            more_matches_may_change=more_matches,
            permanently_unsupported=permanent,
        )


class V7Provenance(PublicV7Model):
    """Everything needed to interpret a cached payload later.

    A payload computed against different population parameters is not
    comparable to one computed against these, so the version is carried rather
    than assumed.
    """

    schema_version: str = Field(min_length=1)
    population_parameters_version: str = Field(min_length=1)
    ranking_model_version: str = Field(min_length=1)
    recommendation_model_version: str = Field(min_length=1)
    archetype_model_version: str = Field(min_length=1)
    feature_version: str = Field(min_length=1)
    inference_version: str = Field(min_length=1)
    acquisition_policy_version: str = Field(default=ACQUISITION_POLICY_VERSION, min_length=1)
    owner_decisions_version: str = Field(min_length=1)
    validation_status: Literal["development", "sealed_validated"] = "development"


class V7CapabilityPayload(PublicV7Model):
    """The complete V7 response.

    ``supporting_facts`` is deliberately absent in this schema version. Nothing
    in the backend computes history statistics, hero contrasts, death profiles
    or telling-sign minutes today, and an empty bag would invite a design agent
    to fill it. Adding one when a producer exists is an additive change.
    """

    schema_version: Literal["v7-capability-payload-1.0.0"] = "v7-capability-payload-1.0.0"
    metadata: ReportMetadata
    player_context: PlayerContext
    findings: list[Finding] = Field(default_factory=list, max_length=REPORT_SLOTS)
    recommendation: Recommendation | None = None
    archetype: ArchetypeSection | None = None
    availability: dict[str, CapabilityAvailability]
    refusals: list[Refusal] = Field(default_factory=list)
    provenance: V7Provenance

    # -- individual invariants ------------------------------------------------

    @model_validator(mode="after")
    def findings_are_ranked(self) -> V7CapabilityPayload:
        """Descending score, ties broken by key -- the ranking model's own
        deterministic order. This is analytical, not a display choice."""

        keys = [(-f.score, f.dimension_key) for f in self.findings]
        if keys != sorted(keys):
            raise ValueError(
                "findings must arrive ordered by (-score, dimension_key); "
                f"got {[f.dimension_key for f in self.findings]!r}"
            )
        return self

    @model_validator(mode="after")
    def no_withheld_dimension_ships(self) -> V7CapabilityPayload:
        leaked = sorted(
            {f.dimension_key for f in self.findings} & WITHHELD_DIMENSIONS
        )
        if leaked:
            raise ValueError(
                f"withheld dimension(s) {leaked} reached the payload. These estimate "
                "zero between-player spread and produce no Finding; "
                "'side_sensitivity' is the negative control and must never be shown"
            )
        return self

    @model_validator(mode="after")
    def scores_and_estimates_are_finite(self) -> V7CapabilityPayload:
        for finding in self.findings:
            _reject_non_finite(finding.score, f"{finding.dimension_key}.score")
            _reject_non_finite(finding.z, f"{finding.dimension_key}.z")
            _reject_non_finite(finding.reliability, f"{finding.dimension_key}.reliability")
            _reject_non_finite(finding.estimate.point, f"{finding.dimension_key}.estimate")
        if self.recommendation is not None:
            _reject_non_finite(self.recommendation.observation.gap, "recommendation.gap")
            _reject_non_finite(self.recommendation.priority_score, "recommendation.priority")
        return self

    @model_validator(mode="after")
    def availability_covers_every_capability(self) -> V7CapabilityPayload:
        present = set(self.availability)
        expected = set(CAPABILITY_KEYS)
        if present != expected:
            missing = sorted(expected - present)
            extra = sorted(present - expected)
            raise ValueError(
                f"availability must cover every capability exactly once; "
                f"missing={missing!r} unexpected={extra!r}"
            )
        return self

    @model_validator(mode="after")
    def refusals_agree_with_availability(self) -> V7CapabilityPayload:
        refused = {
            key for key, entry in self.availability.items() if entry.status == "refused"
        }
        listed = {refusal.capability for refusal in self.refusals}
        if refused != listed:
            raise ValueError(
                f"refusals must match the refused capabilities exactly; "
                f"availability says {sorted(refused)!r}, refusals list {sorted(listed)!r}"
            )
        for refusal in self.refusals:
            entry = self.availability[refusal.capability]
            if entry.refusal_code != refusal.code:
                raise ValueError(
                    f"capability {refusal.capability!r} is refused with code "
                    f"{entry.refusal_code!r} in availability but {refusal.code!r} "
                    "in refusals"
                )
        if len(listed) != len(self.refusals):
            raise ValueError("a capability appears more than once in refusals")
        return self

    @model_validator(mode="after")
    def payload_fields_agree_with_availability(self) -> V7CapabilityPayload:
        """A null capability and a refused capability are the same statement.

        Checked in both directions: a frontend must be able to branch on either
        one and get the same answer.
        """

        for key, value in (
            ("recommendation", self.recommendation),
            ("archetype", self.archetype),
        ):
            refused = self.availability[key].status == "refused"
            if refused and value is not None:
                raise ValueError(f"{key} is marked refused but carries a value")
            if not refused and value is None:
                raise ValueError(f"{key} is marked available but is null")

        findings_refused = self.availability["findings"].status == "refused"
        if findings_refused and self.findings:
            raise ValueError("findings are marked refused but the list is not empty")
        if not findings_refused and not self.findings:
            raise ValueError("findings are marked available but the list is empty")

        mode_refused = self.availability["dominant_mode"].status == "refused"
        if mode_refused and self.player_context.dominant_mode is not None:
            raise ValueError("dominant_mode is marked refused but carries a value")
        if not mode_refused and self.player_context.dominant_mode is None:
            raise ValueError("dominant_mode is marked available but is null")

        rank_refused = self.availability["rank_display"].status == "refused"
        if rank_refused and self.player_context.rank_display is not None:
            raise ValueError("rank_display is marked refused but carries a value")
        if not rank_refused and self.player_context.rank_display is None:
            raise ValueError("rank_display is marked available but is null")
        return self

    @model_validator(mode="after")
    def the_d1_gate_is_respected(self) -> V7CapabilityPayload:
        """Owner decision D1, restated as an invariant.

        Beyond the floor, a Finding earns its slot by clearing the score line
        *or* by being the only representative of its report section. The second
        clause is the one that matters: selection promotes a section's best
        Finding first so no section renders empty, and gating on score alone
        would delete exactly those promotions.
        """

        if len(self.findings) <= FINDING_FLOOR:
            return self
        sections = [f.section for f in self.findings]
        for finding in self.findings[FINDING_FLOOR:]:
            if finding.score > SCORE_LINE:
                continue
            if sections.count(finding.section) == 1:
                continue
            raise ValueError(
                f"finding {finding.dimension_key!r} scores {finding.score} at or "
                f"below the {SCORE_LINE} line, sits beyond the floor of "
                f"{FINDING_FLOOR}, and is not the only representative of section "
                f"{finding.section!r}; the D1 gate would have removed it"
            )
        return self

    @model_validator(mode="after")
    def findings_sit_in_finding_sections(self) -> V7CapabilityPayload:
        for finding in self.findings:
            if finding.section not in FINDING_SECTIONS:
                raise ValueError(
                    f"finding {finding.dimension_key!r} claims section "
                    f"{finding.section!r}, which does not carry Findings"
                )
        return self

    # -- payload-level check --------------------------------------------------

    def validate_payload(self) -> V7CapabilityPayload:
        """Serialisation-level checks that need the finished document.

        Everything above is structural and runs on construction. This runs the
        two checks that can only be made against the serialised form: that no
        internal identifier leaks, and that no forbidden analytical surface
        appears as a key anywhere in the tree.
        """

        document = self.model_dump(mode="json")
        _assert_no_internal_identifiers(document)
        _assert_no_forbidden_field(document)
        return self


def _assert_no_internal_identifiers(document: Any) -> None:
    import json

    serialized = json.dumps(document, sort_keys=True)
    if "v7p_" in serialized:
        raise ValueError(
            "an internal research pseudonym ('v7p_...') reached the payload; "
            "these identify corpus accounts and must never leave the backend"
        )


def _assert_no_forbidden_field(node: Any, path: str = "") -> None:
    """No key may name a fenced surface -- rank, MMR, behaviour score and the
    rest. ``rank_display`` is the one sanctioned exception: it is display-only
    metadata, it lives under ``player_context``, and the fence that matters is
    enforced upstream where the analysis reads its inputs."""

    if isinstance(node, dict):
        for key, value in node.items():
            lowered = key.lower().replace("_", "")
            if key not in _SANCTIONED_KEYS:
                for token in FORBIDDEN_FIELD_TOKENS:
                    if token in lowered:
                        raise ValueError(
                            f"payload key {path + key!r} names the forbidden surface "
                            f"{token!r}"
                        )
            _assert_no_forbidden_field(value, f"{path}{key}.")
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _assert_no_forbidden_field(item, f"{path}{index}.")


#: Keys that legitimately contain a forbidden token, each for a stated reason.
#: An explicit list rather than a loosened pattern: every entry is a decision
#: someone made, and a new key that happens to contain "rank" has to be added
#: here deliberately instead of slipping past a widened rule.
#:
#: * ``rank_display`` and its two labels are display-only rank metadata,
#:   sanctioned by owner decision 5.1. The fence that matters is enforced
#:   upstream, where the analysis reads its inputs.
#: * ``ranking_model_version`` names the model that *ranks a player's own
#:   Findings*. It has nothing to do with the player's medal.
_SANCTIONED_KEYS: frozenset[str] = frozenset(
    {
        "rank_display",
        "start_rank_label",
        "end_rank_label",
        "ranking_model_version",
    }
)


def availability_map(
    available: Iterable[str] = (), refused: dict[str, str] | None = None
) -> dict[str, CapabilityAvailability]:
    """Build a complete availability map from the two halves.

    Every capability must appear, so this is the safe way to build one: pass
    what is available and what is refused, and it fails loudly if the two
    together do not cover the set.
    """

    refused = refused or {}
    entries: dict[str, CapabilityAvailability] = {}
    for key in available:
        entries[key] = CapabilityAvailability(status="available")
    for key, code in refused.items():
        entries[key] = CapabilityAvailability(
            status="refused",
            refusal_code=code,  # type: ignore[arg-type]
        )
    missing = set(CAPABILITY_KEYS) - set(entries)
    if missing:
        raise ValueError(f"availability_map is missing {sorted(missing)!r}")
    return entries


__all__ = [
    "CAPABILITY_KEYS",
    "REFUSAL_SEMANTICS",
    "V7_CAPABILITY_SCHEMA_VERSION",
    "WITHHELD_DIMENSIONS",
    "CapabilityAvailability",
    "CapabilityKey",
    "PlayerContext",
    "Refusal",
    "RefusalCode",
    "ReportMetadata",
    "V7CapabilityPayload",
    "V7Provenance",
    "availability_map",
]

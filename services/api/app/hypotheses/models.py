from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.features.summary_models import SummaryMatchFeature


@dataclass(frozen=True, slots=True)
class MatchPredicate:
    """Serializable candidate definition used by the diagnostic selector."""

    name: str
    params: dict[str, Any]

    def matches(self, match: SummaryMatchFeature) -> bool:
        if self.name == "hero_set":
            hero_ids = self.params.get("hero_ids", ())
            return bool(hero_ids) and match.hero_id in set(hero_ids)
        if self.name == "outside_hero_set":
            hero_ids = self.params.get("hero_ids", ())
            return bool(hero_ids) and match.hero_id not in set(hero_ids)
        if self.name == "hero_set_lane":
            hero_ids = self.params.get("hero_ids", ())
            lane = self.params.get("lane_context")
            return bool(hero_ids) and match.hero_id in set(hero_ids) and (lane is None or match.role_hint == lane)
        if self.name == "match_id_set":
            match_ids = self.params.get("match_ids", ())
            return bool(match_ids) and match.match_id in set(match_ids)
        if self.name == "outside_match_id_set":
            match_ids = self.params.get("match_ids", ())
            return bool(match_ids) and match.match_id not in set(match_ids)
        if self.name == "session_position_range":
            position = match.session_index or 0
            minimum = int(self.params.get("min", 0))
            maximum = self.params.get("max")
            return position >= minimum and (maximum is None or position <= int(maximum))
        if self.name == "expression_quadrant":
            duration = match.duration_minutes
            if duration <= 0 or match.kills is None or match.assists is None or match.deaths is None:
                return False
            involvement = (match.kills + match.assists) / duration
            exposure = match.deaths / duration * 10.0
            involvement_zone = self.params.get("involvement_zone")
            exposure_zone = self.params.get("exposure_zone")
            involvement_cutoff = float(self.params.get("involvement_cutoff", 0.0))
            exposure_cutoff = float(self.params.get("exposure_cutoff", 0.0))
            typical_band = max(0.0, float(self.params.get("typical_band", 0.0)))
            involvement_band = max(
                0.0,
                float(self.params.get("involvement_typical_band", typical_band)),
            )
            exposure_band = max(
                0.0,
                float(self.params.get("exposure_typical_band", typical_band)),
            )
            observed_involvement = (
                "typical"
                if involvement_band and abs(involvement - involvement_cutoff) <= involvement_band
                else "high" if involvement > involvement_cutoff else "low"
            )
            observed_exposure = (
                "typical"
                if exposure_band and abs(exposure - exposure_cutoff) <= exposure_band
                else "high" if exposure > exposure_cutoff else "low"
            )
            return observed_involvement == involvement_zone and observed_exposure == exposure_zone
        if self.name == "post_loss_transition":
            match_ids = self.params.get("match_ids", ())
            return bool(match_ids) and match.match_id in set(match_ids)
        if self.name == "hero_and_outcome":
            return match.hero_id == self.params.get("hero_id") and match.won == self.params.get("won")
        if self.name == "hero":
            return match.hero_id == self.params.get("hero_id")
        if self.name == "non_hero_same_role":
            role = self.params.get("lane_role")
            return (
                match.hero_id != self.params.get("hero_id")
                and (role is None or match.lane_role == role)
                and (
                    self.params.get("won") is None
                    or match.won == self.params.get("won")
                )
            )
        if self.name == "duration_bucket":
            return match.duration_bucket == self.params.get("bucket")
        if self.name == "duration_and_outcome":
            return (
                match.duration_bucket == self.params.get("bucket")
                and match.won == self.params.get("won")
            )
        if self.name == "session_position":
            operator = self.params.get("operator", ">=")
            value = match.session_index or 0
            threshold = int(self.params.get("value", 0))
            return value >= threshold if operator == ">=" else value <= threshold
        if self.name == "session_position_and_outcome":
            operator = self.params.get("operator", ">=")
            value = match.session_index or 0
            threshold = int(self.params.get("value", 0))
            position_matches = value >= threshold if operator == ">=" else value <= threshold
            return position_matches and match.won == self.params.get("won")
        if self.name == "outcome":
            return match.won == self.params.get("won")
        if self.name == "recent_window":
            start = int(self.params.get("start", 0))
            end = int(self.params.get("end", 0))
            ordered_index = int(self.params.get("ordered_index", -1))
            return start <= ordered_index < end
        return False

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "params": dict(self.params)}


@dataclass(frozen=True, slots=True)
class Hypothesis:
    hypothesis_id: str
    source_pattern_id: str
    statement: str
    explanation_type: str
    priority: float
    pattern_strength: float
    actionability: float
    required_data_families: tuple[str, ...]
    positive_definition: MatchPredicate
    negative_definition: MatchPredicate
    control_definition: MatchPredicate
    min_positive: int
    min_negative: int
    min_control: int
    target_positive: int
    target_negative: int
    target_control: int
    confounders_to_control: tuple[str, ...]
    expected_cost: float | None = None
    # v6 diagnostic questions may name one primary hypothesis and one
    # secondary whose evidence is shared with the primary.  Keeping these as
    # metadata preserves the v5 PatternCandidate constructor contract.
    diagnostic_question_id: str | None = None
    primary: bool = True
    evidence_reuse_fraction: float = 1.0

    @property
    def evidence_targets(self) -> dict[str, int]:
        return {
            "positive": self.target_positive,
            "negative": self.target_negative,
            "control": self.target_control,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "source_pattern_id": self.source_pattern_id,
            "statement": self.statement,
            "explanation_type": self.explanation_type,
            "priority": round(self.priority, 4),
            "pattern_strength": round(self.pattern_strength, 4),
            "actionability": round(self.actionability, 4),
            "required_data_families": list(self.required_data_families),
            "positive_definition": self.positive_definition.as_dict(),
            "negative_definition": self.negative_definition.as_dict(),
            "control_definition": self.control_definition.as_dict(),
            "min_positive": self.min_positive,
            "min_negative": self.min_negative,
            "min_control": self.min_control,
            "target_positive": self.target_positive,
            "target_negative": self.target_negative,
            "target_control": self.target_control,
            "confounders_to_control": list(self.confounders_to_control),
            "expected_cost": self.expected_cost,
            "diagnostic_question_id": self.diagnostic_question_id,
            "primary": self.primary,
            "evidence_reuse_fraction": round(self.evidence_reuse_fraction, 4),
        }


@dataclass(frozen=True, slots=True)
class DiagnosticQuestion:
    """Serializable question offered by a Free v6 report.

    Report payloads are intentionally allowed to carry richer copy and
    evidence metadata than this selector needs.  ``from_mapping`` extracts a
    stable identifier and the optional hypothesis definitions while ignoring
    presentation-only keys.
    """

    diagnostic_question_id: str
    statement: str = ""
    primary_hypothesis: dict[str, Any] | None = None
    secondary_hypothesis: dict[str, Any] | None = None
    secondary_reuse_fraction: float = 0.0
    required_data_families: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | str) -> DiagnosticQuestion:
        if isinstance(value, str):
            return cls(value)
        identifier = (
            value.get("diagnostic_question_id")
            or value.get("question_id")
            or value.get("id")
            or value.get("key")
        )
        if not identifier:
            raise ValueError("Diagnostic question requires an id")
        primary = value.get("primary_hypothesis")
        if primary is None and value.get("primary_hypothesis_id"):
            primary = {"hypothesis_id": value["primary_hypothesis_id"]}
        if primary is None and any(key in value for key in ("hypothesis_id", "statement", "explanation_type")):
            primary = value
        secondary = value.get("secondary_hypothesis")
        if secondary is None and value.get("secondary_hypothesis_id"):
            secondary = {"hypothesis_id": value["secondary_hypothesis_id"]}
        reuse = value.get(
            "secondary_reuse_fraction",
            value.get("reuse_fraction", value.get("evidence_reuse", value.get("reuse", 0.0))),
        )
        try:
            reuse_value = max(0.0, min(1.0, float(reuse)))
        except (TypeError, ValueError):
            reuse_value = 0.0
        required = value.get("required_data_families") or value.get("evidence_families") or ()
        return cls(
            diagnostic_question_id=str(identifier),
            statement=str(value.get("statement") or value.get("question") or value.get("prompt") or ""),
            primary_hypothesis=dict(primary) if isinstance(primary, dict) else None,
            secondary_hypothesis=dict(secondary) if isinstance(secondary, dict) else None,
            secondary_reuse_fraction=reuse_value,
            required_data_families=tuple(str(item) for item in required),
            metadata=dict(value),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "diagnostic_question_id": self.diagnostic_question_id,
            "statement": self.statement,
            "primary_hypothesis": dict(self.primary_hypothesis or {}),
            "secondary_hypothesis": dict(self.secondary_hypothesis or {})
            if self.secondary_hypothesis is not None
            else None,
            "secondary_reuse_fraction": round(self.secondary_reuse_fraction, 4),
            "required_data_families": list(self.required_data_families),
            "metadata": dict(self.metadata or {}),
        }

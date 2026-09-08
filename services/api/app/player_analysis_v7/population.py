"""Load the frozen population parameters the V7 runtime ranks against.

A runtime request has one player. Every V7 analytical output is
population-relative, so the parameters that place a player on the population
spread cannot be fitted per request -- they are frozen once from DISCOVERY and
shipped with the app. See ``docs/architecture/v7-runtime-capability-payload.md``
section 1.

Everything here **fails closed**. An unknown dimension raises rather than
returning a default, because a default would silently place the player at the
population mean and produce a confident-looking Finding out of nothing.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.player_analysis_v7.context_projection import SHIPPING_FINDING_IDS, artifact_digest

DATA_DIR = Path(__file__).resolve().parent / "data"
POPULATION_PARAMETERS_VERSION = "v7-population-parameters-2.0.0"
POPULATION_PARAMETERS_PATH = DATA_DIR / f"population-parameters-{POPULATION_PARAMETERS_VERSION.rsplit('-', 1)[-1]}.json"
WITHHELD_ANALYTICAL_IDS = frozenset(
    {
        "lane_recovery_participation",
        "lane_to_map",
        "side_sensitivity",
        "transfer_activity",
        "transfer_risk",
    }
)

#: The six cuts every archetype stratum must supply.
ARCHETYPE_CUT_KEYS = (
    "tempo_low",
    "tempo_high",
    "participation_low",
    "deaths_median",
    "lighthouse_cut",
    "closer_cut",
)


class PopulationParametersError(RuntimeError):
    """The frozen parameters are missing, malformed, or were asked for
    something they do not describe."""


@dataclass(frozen=True)
class FindingParameters:
    """One dimension's population fit.

    ``ships`` is false for a dimension whose ``tau`` collapsed to zero. Such a
    dimension produces no Finding at all, and ``reliability_is_upper_bound``
    marks the ones whose dependence curve had not plateaued -- their
    reliability is optimistic, which callers weighing dimensions should know.
    """

    key: str
    mu: float
    tau: float
    dependence_inflation: float
    section: str
    source_pass: str
    players_fitted: int
    ships: bool
    negative_control: bool
    reliability_is_upper_bound: bool
    status: str
    derivation_method: str
    source_evidence_document: str
    source_evidence_sha256: str
    source_analytical_version: str
    source_reproducible: bool
    source_reproducibility_note: str
    withheld_reason: str | None = None


@dataclass(frozen=True)
class RecommendationParameters:
    """One recommendation dimension's scale and eligibility.

    ``dimension_scale`` is the dimension's own pooled match-to-match spread --
    a unit conversion identical for every player. It is deliberately not the
    between-player spread of gaps, which is exactly zero everywhere.
    """

    key: str
    dimension_scale: float
    dependence_inflation: float
    modal_sign_share: float
    eligible: bool
    outcome_contaminated: bool
    status: str
    derivation_method: str
    source_evidence_document: str
    source_evidence_sha256: str
    source_analytical_version: str


@dataclass(frozen=True)
class PopulationParameters:
    schema_version: str
    artifact_version: str
    artifact_sha256: str
    analytical_lineage_id: str
    population_compatibility_id: str
    context_projection_version: str
    context_projection_sha256: str
    fitted_on_split: str
    derivation_method: str
    refit_from_source_corpus: bool
    validation_status: str
    source_code_sha: str
    source_evidence: dict[str, Any]
    model_versions: dict[str, str]
    denominators: dict[str, int]
    findings: dict[str, FindingParameters]
    recommendations: dict[str, RecommendationParameters]
    archetype_cuts: dict[str, dict[str, float]]

    @property
    def shipping_dimensions(self) -> tuple[str, ...]:
        return tuple(sorted(k for k, v in self.findings.items() if v.ships))

    @property
    def withheld_dimensions(self) -> tuple[str, ...]:
        return tuple(sorted(k for k, v in self.findings.items() if not v.ships))

    def finding(self, key: str) -> FindingParameters:
        """The fit for one dimension. Raises for anything unknown."""

        try:
            return self.findings[key]
        except KeyError:
            raise PopulationParametersError(
                f"no frozen population fit for dimension {key!r}; the runtime "
                "will not invent one"
            ) from None

    def recommendation(self, key: str) -> RecommendationParameters:
        try:
            return self.recommendations[key]
        except KeyError:
            raise PopulationParametersError(
                f"no frozen scale for recommendation dimension {key!r}"
            ) from None

    def cuts_for(self, stratum: str) -> dict[str, float]:
        """Archetype cuts for one mode stratum.

        Raises for an unknown stratum, including ``"UNKNOWN"`` -- that is the
        fail-closed bucket from ``tables.mode_stratum`` and never a population
        a player can be compared against.
        """

        try:
            return self.archetype_cuts[stratum]
        except KeyError:
            raise PopulationParametersError(
                f"no archetype cuts for mode stratum {stratum!r}"
            ) from None


def _parse(document: dict[str, Any]) -> PopulationParameters:
    expected = SHIPPING_FINDING_IDS | WITHHELD_ANALYTICAL_IDS
    if set(document.get("finding_dimensions", {})) != expected:
        raise PopulationParametersError("population artifact must contain 16 shipping and 5 withheld dimensions")
    if document.get("artifact_sha256") != artifact_digest(document):
        raise PopulationParametersError("population artifact digest mismatch")
    findings = {
        key: FindingParameters(
            key=key,
            mu=row["mu"],
            tau=row["tau"],
            dependence_inflation=row["dependence_inflation"],
            section=row["section"],
            source_pass=row["source_pass"],
            players_fitted=row["players_fitted"],
            ships=row["ships"],
            negative_control=row["negative_control"],
            reliability_is_upper_bound=row["reliability_is_upper_bound"],
            status=row["status"],
            derivation_method=row["derivation_method"],
            source_evidence_document=row["source_evidence_document"],
            source_evidence_sha256=row["source_evidence_sha256"],
            source_analytical_version=row["source_analytical_version"],
            source_reproducible=row["source_reproducible"],
            source_reproducibility_note=row["source_reproducibility_note"],
            withheld_reason=row.get("withheld_reason"),
        )
        for key, row in document["finding_dimensions"].items()
    }
    recommendations = {
        key: RecommendationParameters(
            key=key,
            dimension_scale=row["dimension_scale"],
            dependence_inflation=row["dependence_inflation"],
            modal_sign_share=row["modal_sign_share"],
            eligible=row["eligible"],
            outcome_contaminated=row["outcome_contaminated"],
            status=row["status"],
            derivation_method=row["derivation_method"],
            source_evidence_document=row["source_evidence_document"],
            source_evidence_sha256=row["source_evidence_sha256"],
            source_analytical_version=row["source_analytical_version"],
        )
        for key, row in document["recommendation_dimensions"].items()
    }
    cuts = document["archetype_cuts"]
    for stratum, row in cuts.items():
        missing = [name for name in ARCHETYPE_CUT_KEYS if name not in row]
        if missing:
            raise PopulationParametersError(
                f"archetype stratum {stratum!r} is missing cuts {missing!r}"
            )
    for key, row in findings.items():
        if not all(
            math.isfinite(value)
            for value in (row.mu, row.tau, row.dependence_inflation)
        ) or (row.ships and row.tau <= 0) or row.tau < 0 or row.dependence_inflation < 1:
            raise PopulationParametersError(f"{key}: invalid fitted population parameters")
    return PopulationParameters(
        schema_version=document["schema_version"],
        artifact_version=document["artifact_version"],
        artifact_sha256=document["artifact_sha256"],
        analytical_lineage_id=document["analytical_lineage_id"],
        population_compatibility_id=document["population_compatibility_id"],
        context_projection_version=document["context_projection_version"],
        context_projection_sha256=document["context_projection_sha256"],
        fitted_on_split=document["fitted_on_split"],
        derivation_method=document["derivation_method"],
        refit_from_source_corpus=document["refit_from_source_corpus"],
        validation_status=document["validation_status"],
        source_code_sha=document["source_code_sha"],
        source_evidence=document["source_evidence"],
        model_versions=document["model_versions"],
        denominators=document["denominators"],
        findings=findings,
        recommendations=recommendations,
        archetype_cuts=cuts,
    )


@lru_cache(maxsize=1)
def load_population_parameters(path: Path | None = None) -> PopulationParameters:
    """Parse and cache the frozen parameters.

    Cached because the file never changes within a process, and because a
    runtime that re-read and re-parsed it per request would make a cheap
    constant look like a cost worth trimming.
    """

    target = path or POPULATION_PARAMETERS_PATH
    if not target.is_file():
        raise PopulationParametersError(
            f"frozen population parameters missing at {target}; the V7 runtime "
            "cannot rank a player without them"
        )
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PopulationParametersError(f"{target} is not valid JSON: {exc}") from exc
    parsed = _parse(document)
    if parsed.schema_version != POPULATION_PARAMETERS_VERSION:
        raise PopulationParametersError(
            f"{target} declares schema {parsed.schema_version!r}, expected "
            f"{POPULATION_PARAMETERS_VERSION!r}"
        )
    return parsed


__all__ = [
    "ARCHETYPE_CUT_KEYS",
    "POPULATION_PARAMETERS_PATH",
    "POPULATION_PARAMETERS_VERSION",
    "FindingParameters",
    "PopulationParameters",
    "PopulationParametersError",
    "RecommendationParameters",
    "load_population_parameters",
]

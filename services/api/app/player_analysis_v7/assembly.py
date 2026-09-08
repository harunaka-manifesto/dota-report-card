"""Non-analytical assembly boundary for a persisted V7 capability payload."""

from __future__ import annotations

from collections.abc import Mapping

from app.player_analysis_v7.capability_payload import (
    V7_CAPABILITY_SCHEMA_VERSION,
    PlayerContext,
    Refusal,
    ReportMetadata,
    V7CapabilityPayload,
    V7Provenance,
    availability_map,
)
from app.player_analysis_v7.context_projection import (
    assert_population_compatible,
    load_context_projection,
)
from app.player_analysis_v7.descriptive import (
    DESCRIPTIVE_PRODUCER_VERSION,
    derive_descriptive_facts,
)
from app.player_analysis_v7.display_semantics import (
    DISPLAY_SEMANTICS_VERSION,
    build_display_semantics,
)
from app.player_analysis_v7.population import (
    POPULATION_PARAMETERS_VERSION,
    load_population_parameters,
)
from app.player_analysis_v7.public_projection import (
    PUBLIC_PROJECTION_VERSION,
    build_public_projection,
)
from app.player_analysis_v7.report_contract import (
    ArchetypeSection,
    Finding,
    RankDisplay,
    Recommendation,
)
from app.providers.base import V7CanonicalHistory


def assemble_v7_capability(
    *,
    history: V7CanonicalHistory,
    hero_metadata: Mapping[int, Mapping[str, object]],
    generated_at: str,
    findings: list[Finding],
    recommendation: Recommendation | None,
    archetype: ArchetypeSection | None,
    dominant_mode: str | None,
    rank_display: RankDisplay | None,
    refused: dict[str, str],
    feature_version: str,
    inference_version: str,
    reuse_status: str = "generated",
) -> V7CapabilityPayload:
    """Assemble already-computed analytics with deterministic history facts.

    Analytical selection is intentionally an input.  This function cannot fit,
    rank, recommend, or synthesize an archetype.
    """

    facts = derive_descriptive_facts(
        history,
        hero_metadata,
        generated_at=generated_at,
    )
    semantics = build_display_semantics()
    available = [
        key
        for key, present in (
            ("findings", bool(findings)),
            ("recommendation", recommendation is not None),
            ("archetype", archetype is not None),
            ("dominant_mode", dominant_mode is not None),
            ("rank_display", rank_display is not None),
        )
        if present
    ]
    availability = availability_map(available=available, refused=refused)
    population = load_population_parameters()
    context_projection = load_context_projection()
    assert_population_compatible(
        context_projection,
        {
            "schema_version": population.schema_version,
            "analytical_lineage_id": population.analytical_lineage_id,
            "context_projection_sha256": population.context_projection_sha256,
            "population_compatibility_id": population.population_compatibility_id,
        },
    )
    projection = build_public_projection(
        facts=facts,
        semantics=semantics,
        findings=findings,
        archetype=archetype,
        dominant_mode=dominant_mode,  # type: ignore[arg-type]
    )
    payload = V7CapabilityPayload(
        metadata=ReportMetadata(
            generated_at=generated_at,
            window_days=history.window.days,
            window_start=history.window.start_timestamp,
            window_end=history.window.end_timestamp,
            matches_total=len(history.matches),
            matches_analysed=facts.scope.eligible_match_count,
            matches_with_event_detail=facts.scope.parsed_match_count,
            acquisition_depth=facts.scope.acquisition_depth_limit,
        ),
        descriptive_facts=facts,
        display_semantics=semantics,
        player_context=PlayerContext(
            dominant_mode=dominant_mode,  # type: ignore[arg-type]
            rank_display=rank_display,
        ),
        findings=findings,
        recommendation=recommendation,
        archetype=archetype,
        availability=availability,
        refusals=[Refusal.of(key, code) for key, code in sorted(refused.items())],
        public_projection=projection,
        provenance=V7Provenance(
            schema_version=V7_CAPABILITY_SCHEMA_VERSION,
            population_parameters_version=POPULATION_PARAMETERS_VERSION,
            population_parameters_sha256=population.artifact_sha256,
            analytical_lineage_id=population.analytical_lineage_id,
            population_compatibility_id=population.population_compatibility_id,
            context_projection_version=context_projection.artifact_version,
            context_projection_sha256=context_projection.artifact_sha256,
            ranking_model_version=population.model_versions["ranking"],
            recommendation_model_version=population.model_versions["recommendation"],
            archetype_model_version=population.model_versions["archetype"],
            feature_version=feature_version,
            inference_version=inference_version,
            owner_decisions_version=population.model_versions["owner_decisions"],
            descriptive_producer_version=DESCRIPTIVE_PRODUCER_VERSION,
            display_semantics_version=DISPLAY_SEMANTICS_VERSION,
            public_projection_version=PUBLIC_PROJECTION_VERSION,
            reuse_status=reuse_status,  # type: ignore[arg-type]
        ),
    )
    return payload.validate_payload()


__all__ = ["assemble_v7_capability"]

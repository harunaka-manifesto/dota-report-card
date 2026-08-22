from __future__ import annotations

from app.behavior.display_bands import (
    death_exposure_band,
    presence_band,
    relative_performance_band,
    session_bucket_label,
    session_curve_band,
)
from app.behavior.models import PatternResult
from app.behavior.presentation import (
    PATTERN_PRESENTATION_CONTRACT,
    PATTERN_PRESENTATION_VERSION,
    build_pattern_presentation,
)
from app.content.renderer import resolve_pattern_presentation_copy
from app.heroes.knowledge import TaxonomyHeroKnowledgeProvider
from app.heroes.taxonomy import HeroTaxonomy, HeroTaxonomyEntry


def _pattern(key: str, *, status: str = "suppressed", confidence: str = "unavailable") -> PatternResult:
    supported = status == "qualified" and confidence in {"moderate", "high"}
    return PatternResult(
        key=key,
        label=key,
        kind="style",
        status=status,  # type: ignore[arg-type]
        direction=None,
        strength=0.0,
        confidence=confidence,  # type: ignore[arg-type]
        confidence_score=0.9 if supported else 0.0,
        element_keys=(),
        evidence_coverage=1.0 if supported else 0.0,
    )


def test_every_registered_pattern_has_a_deterministic_visual_contract() -> None:
    assert len(PATTERN_PRESENTATION_CONTRACT) == 11
    for key, contract in PATTERN_PRESENTATION_CONTRACT.items():
        payload = build_pattern_presentation(_pattern(key), {})
        assert payload.pattern_id == key
        assert payload.outcome_id == contract["outcome_id"]
        assert payload.visual_variant == contract["visual_variant"]
        assert payload.presentation_version == PATTERN_PRESENTATION_VERSION
        assert payload.recommendation_id is None
        assert payload.deep_dive_id is None


def test_qualified_patterns_get_reviewed_copy_and_low_confidence_gets_fallback() -> None:
    for key, contract in PATTERN_PRESENTATION_CONTRACT.items():
        payload = build_pattern_presentation(
            _pattern(key, status="qualified", confidence="high"),
            {},
        )
        params = {"hero_name": "Example bridge hero"} if key in {"same_playbook", "versatile_core"} else {}
        copy = resolve_pattern_presentation_copy(
            key,
            contract["outcome_id"],
            recommendation_id=contract["recommendation_id"],
            deep_dive_id=contract["deep_dive_id"],
            params=params,
        )
        assert payload.recommendation_id == contract["recommendation_id"]
        assert payload.deep_dive_id == contract["deep_dive_id"]
        assert copy["headline"] and copy["interpretation"]["body"]

    weak = build_pattern_presentation(
        _pattern("same_playbook", status="qualified", confidence="low"),
        {},
    )
    assert weak.recommendation_id is None
    assert weak.deep_dive_id is None


def test_display_bands_are_human_readable_and_stable_at_boundaries() -> None:
    assert relative_performance_band(-0.30) == "very_weak"
    assert relative_performance_band(-0.10) == "normal"
    assert relative_performance_band(0.10) == "normal"
    assert relative_performance_band(0.30) == "very_strong"
    assert presence_band(0.40) == "normal"
    assert presence_band(0.60) == "high"
    assert death_exposure_band(0.40) == "normal"
    assert death_exposure_band(0.60) == "high"
    assert session_curve_band(-0.20, direction="fade") == "lowest_point"
    assert session_curve_band(-0.05, direction="rise") == "warming_up"
    assert session_curve_band(0.20, direction="rise") == "strongest"
    assert session_bucket_label("G5+") == "Game 5+"
    assert session_bucket_label("Game N") == "Session position unavailable"


def test_normalized_hero_knowledge_resolves_canonical_display_names() -> None:
    taxonomy = HeroTaxonomy(
        "hero-taxonomy-fixture",
        {
            7: HeroTaxonomyEntry(
                hero_id=7,
                key="fixture_hero",
                name="Fixture Hero",
                roles=("support",),
                traits={"save": 0.80, "teamfight": 0.70},
                portrait_url="https://example.test/hero.png",
                available=True,
                provenance={"source": "fixture"},
            )
        },
        {},
    )
    provider = TaxonomyHeroKnowledgeProvider(taxonomy)
    hero = provider.get(7)
    assert provider.version == "hero-knowledge-fixture"
    assert hero is not None
    assert hero.display_name == "Fixture Hero"
    assert "Save" in hero.functional_jobs
    assert hero.provenance_versions["hero_knowledge_schema"] == "hero-knowledge-schema-1.0.0"


def test_primary_copy_does_not_expose_internal_metric_shorthand() -> None:
    for key, contract in PATTERN_PRESENTATION_CONTRACT.items():
        params = {"hero_name": "Example bridge hero"} if key in {"same_playbook", "versatile_core"} else {}
        copy = resolve_pattern_presentation_copy(
            key,
            contract["outcome_id"],
            recommendation_id=contract["recommendation_id"],
            deep_dive_id=contract["deep_dive_id"],
            params=params,
        )
        text = str(copy["headline"]) + str(copy["subheadline"]) + str(copy["interpretation"])
        assert "z_score" not in text
        assert "delta =" not in text
        assert "Game N" not in text

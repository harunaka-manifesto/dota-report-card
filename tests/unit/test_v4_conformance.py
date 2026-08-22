from __future__ import annotations

from dataclasses import replace

import pytest
from app.analysis.budget import DataCostLedger
from app.behavior.elements.registry import ELEMENT_REGISTRY, zone_for_score
from app.behavior.evidence import BehaviorEvidence
from app.behavior.models import ElementResult, PatternResult
from app.behavior.patterns.service import _qualification, evaluate_patterns
from app.behavior.ranking import pattern_ranking_breakdown, rank_pattern_highlights
from app.hero_portfolio.behavior import (
    deaths_per_ten_minutes,
    events_per_minute,
    finishing_kill_share,
)
from app.hero_portfolio.common_thread import compute_common_thread
from app.hero_portfolio.eligibility import build_hero_eligibility
from app.hero_portfolio.evolution import compute_pool_evolution
from app.hero_portfolio.exception import compute_hero_exception
from app.hero_portfolio.mirror import _behavior_labels, _shrink, _similarity, compute_hero_mirror
from app.heroes.taxonomy import TRAITS, HeroTaxonomy, HeroTaxonomyEntry
from app.ingestion.summary_normalize import normalize_summary_rows
from app.reports.dna_assembly import _free_cost


def _element(
    key: str,
    score: float = 0.5,
    *,
    blocking_confounders: tuple[str, ...] = (),
) -> ElementResult:
    definition = ELEMENT_REGISTRY[key]
    return ElementResult(
        key=key,
        label=definition.label,
        dimension_key=definition.dimension_key,
        status="available",
        score=score,
        centered_score=2 * score - 1,
        confidence="high",
        confidence_score=0.9,
        sample_size=60,
        effective_sample_size=60,
        coverage=1.0,
        stability=0.9,
        quality=0.9,
        evidence=(BehaviorEvidence("fixture", score, "score", 60),),
        methodology_version=definition.version,
        axis_left=definition.axis_left,
        axis_right=definition.axis_right,
        zone=zone_for_score(key, score),
        blocking_confounders=blocking_confounders,
    )


def _score_for_zone(key: str, zone: str) -> float:
    labels = ELEMENT_REGISTRY[key].zone_labels
    return (labels.index(zone) + 0.1) / len(labels)


def _elements_for_zones(zones: dict[str, str]) -> dict[str, ElementResult]:
    values = {key: _element(key) for key in ELEMENT_REGISTRY}
    for key, zone in zones.items():
        values[key] = _element(key, _score_for_zone(key, zone))
    return values


def _pattern(key: str, *, strength: float, confidence: float, coverage: float) -> PatternResult:
    return PatternResult(
        key=key,
        label=key,
        kind="style",
        status="qualified",
        direction="fixture",
        strength=strength,
        confidence="high",
        confidence_score=confidence,
        element_keys=("hero_pool_breadth", "toolkit_breadth"),
        family=key,
        relationship_strength=strength,
        evidence_coverage=coverage,
        qualification_quality=1.0,
    )


def _taxonomy(*, available: bool = True) -> HeroTaxonomy:
    heroes = {}
    for hero_id in range(1, 5):
        heroes[hero_id] = HeroTaxonomyEntry(
            hero_id=hero_id,
            key=f"hero_{hero_id}",
            name=f"Hero {hero_id}",
            roles=("carry",),
            traits={trait: 0.5 for trait in TRAITS},
            portrait_url=f"https://example.test/{hero_id}.png",
            available=available,
            provenance={"source": "fixture", "research_file": "fixture", "editorial": "fixture", "review_status": "reviewed"},
        )
    return HeroTaxonomy("fixture", heroes, {})


def _common_taxonomy() -> HeroTaxonomy:
    base = _taxonomy()
    heroes = {
        hero_id: replace(
            entry,
            traits={trait: (0.90 if trait == "mobility" and hero_id < 4 else 0.10) for trait in TRAITS},
        )
        for hero_id, entry in base.heroes.items()
    }
    return HeroTaxonomy("common-thread-fixture", heroes, {})


def _summary_rows(count: int = 32) -> tuple:
    rows = [
        {
            "match_id": 700_000 + index,
            "start_time": 1_700_000_000 + index * 3_600,
            "duration": 1_800,
            "hero_id": 1 + index % 4,
            "player_slot": 0,
            "radiant_win": index % 2 == 0,
            "game_mode": 1,
            "lobby_type": 0,
            "kills": 8,
            "deaths": 4,
            "assists": 10,
            "lane_role": 1,
        }
        for index in range(count)
    ]
    return normalize_summary_rows(rows, account_id=42).matches


def _evolution_taxonomy(mode: str) -> HeroTaxonomy:
    heroes: dict[int, HeroTaxonomyEntry] = {}
    for hero_id in range(1, 5):
        traits = {trait: 0.01 for trait in TRAITS}
        if mode == "new_new":
            if hero_id <= 2:
                traits.update(mobility=0.9, frontline=0.9)
            else:
                traits.update(global_presence=0.9, push=0.9)
        elif mode == "same_toolkit":
            traits = {trait: 0.5 for trait in TRAITS}
        elif mode == "stable_branch":
            if hero_id <= 2:
                traits["mobility"] = 0.25
                traits["frontline"] = 0.25
            elif hero_id == 3:
                traits.update(global_presence=1.0, push=1.0)
        else:
            traits = {trait: 0.5 for trait in TRAITS}
        heroes[hero_id] = HeroTaxonomyEntry(
            hero_id=hero_id,
            key=f"hero_{hero_id}",
            name=f"Hero {hero_id}",
            roles=("carry",),
            traits=traits,
            portrait_url=f"https://example.test/{hero_id}.png",
            provenance={"source": "fixture", "research_file": "fixture", "editorial": "fixture", "review_status": "reviewed"},
        )
    return HeroTaxonomy(f"evolution-{mode}", heroes, {})


def _evolution_matches(earlier: tuple[int, ...], recent: tuple[int, ...]) -> tuple:
    rows = []
    for index, hero_id in enumerate((*earlier, *recent)):
        rows.append(
            {
                "match_id": 900_000 + index,
                "start_time": 1_700_000_000 + index * 3_600,
                "duration": 1_800,
                "hero_id": hero_id,
                "player_slot": 0,
                "radiant_win": index % 2 == 0,
                "game_mode": 1,
                "lobby_type": 0,
                "kills": 8,
                "deaths": 4,
                "assists": 10,
                "lane_role": 1,
            }
        )
    return normalize_summary_rows(rows, account_id=42).matches


def test_pattern_qualification_uses_reviewed_zones_at_boundaries() -> None:
    values = {key: _element(key) for key in ELEMENT_REGISTRY}
    values["hero_pool_breadth"] = _element("hero_pool_breadth", 0.61)  # Varied
    values["toolkit_breadth"] = _element("toolkit_breadth", 0.40)  # Mixed, not Compact/Focused
    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == "same_playbook")
    assert result.status == "suppressed"


@pytest.mark.parametrize("key", tuple(ELEMENT_REGISTRY))
def test_every_element_uses_the_same_half_open_zone_boundaries(key: str) -> None:
    labels = ELEMENT_REGISTRY[key].zone_labels
    assert zone_for_score(key, 0.0) == labels[0]
    assert zone_for_score(key, 0.199999) == labels[0]
    assert zone_for_score(key, 0.20) == labels[1]
    assert zone_for_score(key, 0.399999) == labels[1]
    assert zone_for_score(key, 0.40) == labels[2]
    assert zone_for_score(key, 0.599999) == labels[2]
    assert zone_for_score(key, 0.60) == labels[3]
    assert zone_for_score(key, 0.799999) == labels[3]
    assert zone_for_score(key, 0.80) == labels[4]
    assert zone_for_score(key, 1.0) == labels[4]


def test_pattern_qualification_does_not_trust_a_stale_serialized_zone() -> None:
    values = {key: _element(key) for key in ELEMENT_REGISTRY}
    values["hero_pool_breadth"] = _element("hero_pool_breadth", 0.61)
    values["toolkit_breadth"] = replace(_element("toolkit_breadth", 0.41), zone="Focused")

    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == "same_playbook")

    assert result.status == "suppressed"


PATTERN_ZONE_FIXTURES = (
    ("same_playbook", {"hero_pool_breadth": "Varied", "toolkit_breadth": "Focused"}, {"toolkit_breadth": "Mixed"}),
    ("comfort_edge", {"hero_pool_breadth": "Wide", "off_pool_performance": "Slips"}, {"off_pool_performance": "Holds"}),
    ("partial_transfer", {"off_pool_activity_stability": "Holds", "off_pool_performance": "Slips"}, {"off_pool_activity_stability": "Similar"}),
    ("versatile_core", {"hero_pool_breadth": "Focused", "toolkit_breadth": "Versatile"}, {"toolkit_breadth": "Mixed"}),
    ("proven_flexibility", {"hero_pool_breadth": "Wide", "off_pool_performance": "Travels"}, {"off_pool_performance": "Holds"}),
    ("bounceback", {"post_loss_performance_response": "Recovers", "post_loss_familiarity_shift": "Returns", "post_loss_activity_shift": "Same"}, {"post_loss_performance_response": "Holds"}),
    ("performance_slide", {"post_loss_performance_response": "Slips", "post_loss_familiarity_shift": "Unchanged", "post_loss_activity_shift": "Speeds up"}, {"post_loss_performance_response": "Holds"}),
    ("controlled_presence", {"combat_involvement": "Active", "death_exposure": "Safe"}, {"death_exposure": "Mixed"}),
    ("presence_tax", {"combat_involvement": "Active", "death_exposure": "Exposed"}, {"death_exposure": "Safe"}),
    ("session_fade", {"session_length_tendency": "Long", "late_session_performance": "Fades"}, {"late_session_performance": "Holds"}),
    ("session_rise", {"session_length_tendency": "Medium", "late_session_performance": "Warms up"}, {"session_length_tendency": "Short"}),
)


@pytest.mark.parametrize("key, positive, negative", PATTERN_ZONE_FIXTURES)
def test_every_pattern_uses_exact_positive_and_negative_zone_membership(
    key: str,
    positive: dict[str, str],
    negative: dict[str, str],
) -> None:
    positive_result, direction, _ = _qualification(key, _elements_for_zones(positive))
    negative_result, negative_direction, _ = _qualification(key, _elements_for_zones(positive | negative))

    assert positive_result is True
    assert direction is not None
    assert negative_result is False
    assert negative_direction is None


def test_pattern_modifier_missing_does_not_turn_into_a_hidden_gate() -> None:
    values = _elements_for_zones({"hero_pool_breadth": "Wide", "off_pool_performance": "Travels"})
    values.pop("hero_exploration_rate")
    values.pop("post_loss_familiarity_shift")

    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == "proven_flexibility")
    assert result.status == "qualified"
    comfort_values = _elements_for_zones({"hero_pool_breadth": "Wide", "off_pool_performance": "Slips"})
    comfort_values.pop("hero_exploration_rate")
    comfort_values.pop("post_loss_familiarity_shift")
    comfort_edge = next(item for item in evaluate_patterns(tuple(comfort_values.values())) if item.key == "comfort_edge")
    assert comfort_edge.status == "qualified"


def test_pattern_low_confidence_and_low_coverage_are_suppressed() -> None:
    low_confidence = _elements_for_zones({"hero_pool_breadth": "Wide", "toolkit_breadth": "Focused"})
    low_confidence["toolkit_breadth"] = replace(low_confidence["toolkit_breadth"], confidence_score=0.20)
    result = next(item for item in evaluate_patterns(tuple(low_confidence.values())) if item.key == "same_playbook")
    assert result.status == "suppressed"
    assert "confidence_below_gate" in result.suppression_reasons[0]

    low_coverage = _elements_for_zones({"hero_pool_breadth": "Wide", "toolkit_breadth": "Focused"})
    low_coverage["toolkit_breadth"] = replace(low_coverage["toolkit_breadth"], coverage=0.20)
    result = next(item for item in evaluate_patterns(tuple(low_coverage.values())) if item.key == "same_playbook")
    assert result.status == "suppressed"
    assert result.suppression_reasons == ("required_element_coverage_below_gate:toolkit_breadth",)


def test_pattern_coverage_uses_the_element_registry_gate_and_preserves_actual_coverage() -> None:
    values = _elements_for_zones({"hero_pool_breadth": "Focused", "toolkit_breadth": "Versatile"})
    values["toolkit_breadth"] = replace(values["toolkit_breadth"], coverage=0.80)
    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == "versatile_core")
    assert result.status == "qualified"

    values["toolkit_breadth"] = replace(values["toolkit_breadth"], coverage=0.799999)
    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == "versatile_core")
    assert result.status == "suppressed"
    assert result.suppression_reasons == ("required_element_coverage_below_gate:toolkit_breadth",)

    values = _elements_for_zones({"hero_pool_breadth": "Wide", "toolkit_breadth": "Focused"})
    values["hero_pool_breadth"] = replace(values["hero_pool_breadth"], coverage=0.20)
    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == "same_playbook")
    assert result.status == "qualified"
    assert result.evidence_coverage == 0.20


def test_pattern_gate_does_not_invent_a_floor_for_zero_coverage_elements() -> None:
    values = _elements_for_zones({"hero_pool_breadth": "Wide", "toolkit_breadth": "Focused"})
    values["hero_pool_breadth"] = replace(values["hero_pool_breadth"], coverage=0.0)
    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == "same_playbook")
    assert result.status == "qualified"
    assert result.evidence_coverage == 0.0


def test_pattern_confidence_gate_accepts_exact_boundary_and_rejects_just_below() -> None:
    values = _elements_for_zones({"hero_pool_breadth": "Wide", "toolkit_breadth": "Focused"})
    values["toolkit_breadth"] = replace(values["toolkit_breadth"], confidence_score=0.45)
    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == "same_playbook")
    assert result.status == "qualified"

    values["toolkit_breadth"] = replace(values["toolkit_breadth"], confidence_score=0.449999)
    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == "same_playbook")
    assert result.status == "suppressed"
    assert result.suppression_reasons == ("required_element_confidence_below_gate:toolkit_breadth",)


@pytest.mark.parametrize(
    ("key", "recovery_zone", "familiarity_zone", "tempo_zone", "expected_keys", "expected_direction"),
    (
        (
            "bounceback",
            "Surges",
            "Returns",
            "Same",
            ("post_loss_performance_response", "post_loss_familiarity_shift"),
            "positive_recovery_with_familiarity",
        ),
        (
            "bounceback",
            "Surges",
            "Unchanged",
            "Speeds up",
            ("post_loss_performance_response", "post_loss_activity_shift"),
            "positive_recovery_with_tempo",
        ),
        (
            "performance_slide",
            "Slips",
            "Returns",
            "Same",
            ("post_loss_performance_response", "post_loss_familiarity_shift"),
            "negative_recovery_with_familiarity",
        ),
        (
            "performance_slide",
            "Slips",
            "Unchanged",
            "Speeds up",
            ("post_loss_performance_response", "post_loss_activity_shift"),
            "negative_recovery_with_tempo",
        ),
    ),
)
def test_recovery_patterns_record_the_winning_or_clause(
    key: str,
    recovery_zone: str,
    familiarity_zone: str,
    tempo_zone: str,
    expected_keys: tuple[str, ...],
    expected_direction: str,
) -> None:
    values = _elements_for_zones(
        {
            "post_loss_performance_response": recovery_zone,
            "post_loss_familiarity_shift": familiarity_zone,
            "post_loss_activity_shift": tempo_zone,
        }
    )
    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == key)
    assert result.status == "qualified"
    assert result.direction == expected_direction
    assert result.qualification_element_keys == expected_keys
    assert result.qualification_clause_index == (0 if expected_keys[-1] == "post_loss_familiarity_shift" else 1)
    assert len(result.evidence) == 2


@pytest.mark.parametrize("key,recovery_zone", (("bounceback", "Surges"), ("performance_slide", "Slips")))
def test_recovery_or_pattern_suppresses_when_neither_alternative_moves(key: str, recovery_zone: str) -> None:
    values = _elements_for_zones(
        {
            "post_loss_performance_response": recovery_zone,
            "post_loss_familiarity_shift": "Unchanged",
            "post_loss_activity_shift": "Same",
        }
    )
    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == key)
    assert result.status == "suppressed"
    assert result.suppression_reasons == ("relationship_zone_not_met",)


@pytest.mark.parametrize("key,recovery_zone", (("bounceback", "Surges"), ("performance_slide", "Slips")))
def test_recovery_or_pattern_ignores_weak_or_blocked_unused_branch(key: str, recovery_zone: str) -> None:
    baseline = _elements_for_zones(
        {
            "post_loss_performance_response": recovery_zone,
            "post_loss_familiarity_shift": "Returns",
            "post_loss_activity_shift": "Same",
        }
    )
    baseline_result = next(item for item in evaluate_patterns(tuple(baseline.values())) if item.key == key)

    weak_unused = dict(baseline)
    weak_unused["post_loss_activity_shift"] = replace(
        weak_unused["post_loss_activity_shift"], confidence_score=0.20, coverage=0.01
    )
    weak_result = next(item for item in evaluate_patterns(tuple(weak_unused.values())) if item.key == key)
    assert weak_result.status == "qualified"
    assert weak_result.qualification_element_keys == baseline_result.qualification_element_keys
    assert weak_result.confidence_score == baseline_result.confidence_score
    assert weak_result.evidence_coverage == baseline_result.evidence_coverage
    assert weak_result.qualification_quality == baseline_result.qualification_quality
    assert weak_result.strength == baseline_result.strength
    assert weak_result.blocking_confounders == ()

    blocked_unused = dict(baseline)
    blocked_unused["post_loss_activity_shift"] = replace(
        blocked_unused["post_loss_activity_shift"], blocking_confounders=("fixture_block",)
    )
    blocked_result = next(item for item in evaluate_patterns(tuple(blocked_unused.values())) if item.key == key)
    assert blocked_result.status == "qualified"
    assert blocked_result.blocking_confounders == ()


def test_recovery_or_pattern_prefers_the_stronger_qualifying_branch() -> None:
    values = _elements_for_zones(
        {
            "post_loss_performance_response": "Surges",
            "post_loss_familiarity_shift": "Returns",
            "post_loss_activity_shift": "Speeds up",
        }
    )
    values["post_loss_familiarity_shift"] = replace(values["post_loss_familiarity_shift"], confidence_score=0.46)
    values["post_loss_activity_shift"] = replace(values["post_loss_activity_shift"], confidence_score=0.90)
    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == "bounceback")
    assert result.status == "qualified"
    assert result.qualification_element_keys == (
        "post_loss_performance_response",
        "post_loss_activity_shift",
    )
    assert result.direction == "positive_recovery_with_tempo"


def test_recovery_or_pattern_reports_confidence_failure_for_a_zone_matching_weak_branch() -> None:
    values = _elements_for_zones(
        {
            "post_loss_performance_response": "Surges",
            "post_loss_familiarity_shift": "Returns",
            "post_loss_activity_shift": "Same",
        }
    )
    values["post_loss_familiarity_shift"] = replace(values["post_loss_familiarity_shift"], confidence_score=0.449999)
    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == "bounceback")
    assert result.status == "suppressed"
    assert result.suppression_reasons == ("required_element_confidence_below_gate:post_loss_familiarity_shift",)


def test_pattern_ranking_does_not_double_count_confidence_or_coverage() -> None:
    low_evidence_high_strength = _pattern("low", strength=0.80, confidence=0.50, coverage=0.50)
    lower_strength_high_evidence = _pattern("high", strength=0.70, confidence=0.95, coverage=0.95)
    ranked = rank_pattern_highlights((low_evidence_high_strength, lower_strength_high_evidence), limit=2)
    assert [item.key for item in ranked] == ["low", "high"]


def test_pattern_ranking_has_three_slot_limit_family_penalty_and_gates() -> None:
    first = replace(_pattern("first", strength=0.80, confidence=0.90, coverage=0.90), family="same", tier="B")
    second = replace(_pattern("second", strength=0.79, confidence=0.90, coverage=0.90), family="same", tier="B")
    third = replace(_pattern("third", strength=0.78, confidence=0.90, coverage=0.90), family="different", tier="A")
    weak = replace(_pattern("weak", strength=0.99, confidence=0.20, coverage=0.90), family="weak", tier="A")
    blocked = replace(_pattern("blocked", strength=0.99, confidence=0.90, coverage=0.90), status="suppressed", family="blocked", tier="A")

    ranked = rank_pattern_highlights((first, second, third, weak, blocked), limit=3)
    assert len(ranked) == 3
    assert "weak" not in {item.key for item in ranked}
    assert "blocked" not in {item.key for item in ranked}
    assert pattern_ranking_breakdown(second, {"same"}).family_redundancy_penalty > 0
    assert pattern_ranking_breakdown(third, {"same"}).family_redundancy_penalty == 0


def test_pattern_ranking_defaults_to_five_story_slots_and_excludes_blocked_results() -> None:
    patterns = tuple(
        replace(
            _pattern(f"pattern-{index}", strength=0.80 - index * 0.01, confidence=0.90, coverage=0.90),
            family=f"family-{index}",
        )
        for index in range(6)
    )
    blocked = replace(patterns[-1], story_eligibility="blocked", story_blockers=("window_invalid",))

    ranked = rank_pattern_highlights((*patterns[:-1], blocked))

    assert len(ranked) == 5
    assert all(item.story_eligibility == "eligible" for item in ranked)


def test_public_element_and_pattern_serialization_excludes_private_metrics() -> None:
    element = _element("hero_pool_breadth")
    pattern = _pattern("same_playbook", strength=0.8, confidence=0.9, coverage=0.9)
    assert "source_match_ids" not in element.as_dict()
    assert "source_match_ids" in element.as_dict(public=False)
    assert "effect_metrics" not in pattern.as_dict()
    assert "effect_metrics" in pattern.as_dict(public=False)


def test_blocking_confounder_suppresses_a_pattern_but_information_does_not() -> None:
    values = {key: _element(key) for key in ELEMENT_REGISTRY}
    values["hero_pool_breadth"] = _element("hero_pool_breadth", 0.82, blocking_confounders=("window_invalid",))
    values["toolkit_breadth"] = _element("toolkit_breadth", 0.18)
    result = next(item for item in evaluate_patterns(tuple(values.values())) if item.key == "same_playbook")
    assert result.status == "suppressed"
    assert "window_invalid" in result.blocking_confounders
    assert result.story_eligibility == "blocked"
    assert result.story_blockers == ("window_invalid",)


def test_mirror_labels_use_realistic_events_per_minute_zones() -> None:
    labels = {
        _behavior_labels({"involvement": value, "finishing": 0.5, "deaths": 1.0})["involvement"]
        for value in (0.18, 0.42, 0.68, 0.95, 1.30)
    }
    assert len(labels) >= 3


def test_mirror_behavior_units_are_explicit_and_shared() -> None:
    matches = _summary_rows(2)
    assert events_per_minute(matches) == pytest.approx(0.6)
    assert finishing_kill_share(matches) == pytest.approx(8 / 18)
    assert deaths_per_ten_minutes(matches) == pytest.approx(4 / 3)


def test_mirror_role_distribution_is_one_component_and_missing_roles_reduce_coverage() -> None:
    combat = {"involvement": 0.60, "finishing": 0.50, "deaths": 1.0}
    with_roles = {**combat, "role:carry": 1.0}
    without_roles = dict(combat)
    _, with_role_coverage = _similarity(with_roles, with_roles)
    _, without_role_coverage = _similarity(without_roles, without_roles)
    assert with_role_coverage == 1.0
    assert without_role_coverage == 0.75


def test_mirror_shrinkage_caps_small_samples_and_taxonomy_traits_do_not_change_score() -> None:
    reference = {"involvement": 0.6, "finishing": 0.5, "deaths": 1.0}
    observed = {"involvement": 1.0, "finishing": 1.0, "deaths": 2.0}
    assert _shrink(observed, reference, 10)["involvement"] == pytest.approx(0.8)
    assert _shrink(observed, reference, 100) == observed

    matches = _summary_rows(60)
    normal = compute_hero_mirror(matches, _taxonomy())
    altered_entries = {
        hero_id: replace(entry, traits={trait: (0.99 if hero_id == 1 else 0.01) for trait in TRAITS})
        for hero_id, entry in _taxonomy().heroes.items()
    }
    altered = compute_hero_mirror(matches, HeroTaxonomy("altered", altered_entries, {}))
    assert altered.hero_id == normal.hero_id
    assert altered.similarity_score == normal.similarity_score


def test_mirror_eligibility_does_not_require_taxonomy_coverage() -> None:
    matches = _summary_rows()
    eligibility = build_hero_eligibility(matches, _taxonomy(available=False))
    assert all(item.eligible_for_mirror for item in eligibility)
    assert all(not item.eligible_for_common_thread for item in eligibility)


def test_common_thread_has_deterministic_feedback_and_unavailable_ambiguity() -> None:
    matches = _summary_rows()
    taxonomy = _common_taxonomy()
    result = compute_common_thread(matches, taxonomy)
    repeated = compute_common_thread(tuple(reversed(matches)), taxonomy)

    assert result.status == "available"
    assert result.trait_key == "mobility"
    assert len(result.options) == 4
    assert result.options == repeated.options
    assert result.correct_option_key in {option.key for option in result.options}
    assert all(option.feedback for option in result.options)

    ambiguous = compute_common_thread(matches, _taxonomy())
    assert ambiguous.status == "no_clear_thread"
    assert ambiguous.options == ()


def test_exception_does_not_use_win_rate_and_keeps_option_order_deterministic() -> None:
    matches = _summary_rows()
    flipped = tuple(replace(item, won=not item.won) for item in matches)
    taxonomy = _common_taxonomy()
    result = compute_hero_exception(matches, taxonomy)
    changed_outcomes = compute_hero_exception(flipped, taxonomy)

    assert result.options == changed_outcomes.options
    assert result.hero_id == changed_outcomes.hero_id
    assert len(result.options) == (4 if result.status == "available" else 0)


def test_evolution_uses_equal_sized_windows_and_semantic_coverage_check() -> None:
    result = compute_pool_evolution(_summary_rows(60), _taxonomy())
    assert result.status == "available"
    assert result.earlier_sample_size == result.recent_sample_size
    assert result.earlier_sample_size <= 24

    unavailable = compute_pool_evolution(_summary_rows(60), _taxonomy(available=False))
    assert unavailable.status == "unavailable"
    assert "readable hero information" in " ".join(unavailable.limitations).lower()

    patch_changed = tuple(replace(item, patch="7.35" if index < 30 else "7.36") for index, item in enumerate(_summary_rows(60)))
    warned = compute_pool_evolution(patch_changed, _taxonomy())
    assert warned.status == "available"
    assert any("Patch or time context" in item for item in warned.limitations)

    too_short = compute_pool_evolution(_summary_rows(23), _taxonomy())
    assert too_short.status == "unavailable"


@pytest.mark.parametrize(
    "mode, earlier, recent, expected",
    (
        ("new_new", (1, 2) * 12, (3, 4) * 12, "new_heroes_new_toolkit"),
        ("same_toolkit", (1, 2) * 12, (3, 4) * 12, "new_heroes_same_toolkit"),
        ("stable_branch", (1, 2) * 12, (1, 2) * 11 + (3, 4), "stable_core_new_branch"),
        ("stable", (1, 2) * 12, (1, 2) * 12, "broadly_stable"),
    ),
)
def test_evolution_classifies_all_four_reviewed_variants(
    mode: str,
    earlier: tuple[int, ...],
    recent: tuple[int, ...],
    expected: str,
) -> None:
    result = compute_pool_evolution(_evolution_matches(earlier, recent), _evolution_taxonomy(mode))
    assert result.status == "available"
    assert result.variant == expected
    assert result.earlier_sample_size == result.recent_sample_size == 24


def test_exception_has_four_options_only_when_an_outlier_exists() -> None:
    result = compute_hero_exception(_summary_rows(), _taxonomy())
    if result.status == "available":
        assert len(result.options) == 4
        assert result.correct_option_key in {option.key for option in result.options}
    else:
        assert result.status == "no_clear_exception"
        assert result.options == ()
        assert result.correct_option_key == "no_clear_exception"


def test_free_cost_rejects_contaminated_ledger() -> None:
    ledger = DataCostLedger(detail_requests=1)
    with pytest.raises(ValueError, match="summary-only"):
        _free_cost(ledger)


def test_free_cost_requires_and_preserves_the_actual_ledger() -> None:
    with pytest.raises(ValueError, match="actual cost ledger"):
        _free_cost(None)
    ledger = DataCostLedger(history_requests=1, cache_hits=2, estimated_cost_units=1.0)
    assert _free_cost(ledger) == {
        "history_requests": 1,
        "detail_requests": 0,
        "parse_requests": 0,
        "parse_status_requests": 0,
        "cache_hits": 2,
        "estimated_cost_units": 1.0,
    }

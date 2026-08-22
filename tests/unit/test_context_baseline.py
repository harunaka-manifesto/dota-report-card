from __future__ import annotations

from dataclasses import replace

from app.behavior.context_baseline import resolve_leave_group_out_baseline
from app.heroes.taxonomy import TRAITS, HeroTaxonomy, HeroTaxonomyEntry
from app.ingestion.summary_normalize import NormalizedSummaryMatch, normalize_summary_rows


def _taxonomy() -> HeroTaxonomy:
    heroes: dict[int, HeroTaxonomyEntry] = {}
    for hero_id in range(1, 6):
        traits = {trait: 0.10 for trait in TRAITS}
        if hero_id in {1, 2, 3}:
            traits["initiation"] = 0.90
        else:
            traits["burst"] = 0.90
        heroes[hero_id] = HeroTaxonomyEntry(
            hero_id=hero_id,
            key=f"hero_{hero_id}",
            name=f"Hero {hero_id}",
            roles=("carry",),
            traits=traits,
            portrait_url=f"https://example.test/{hero_id}.png",
            provenance={"source": "fixture", "research_file": "fixture", "editorial": "fixture", "review_status": "reviewed"},
        )
    return HeroTaxonomy("baseline-fixture", heroes, {})


def _rows(specs: list[tuple[int, int, int, int, str]]) -> tuple[NormalizedSummaryMatch, ...]:
    normalized = normalize_summary_rows(
        [
            {
                "match_id": match_id,
                "start_time": 1_700_000_000 + match_id,
                "duration": 1_800,
                "hero_id": hero_id,
                "player_slot": 0,
                "radiant_win": True,
                "game_mode": 1,
                "lobby_type": 0,
                "kills": 8,
                "deaths": 4,
                "assists": 10,
                "lane_role": lane_role,
            }
            for match_id, hero_id, lane_role, _value, _session_id in specs
        ],
        account_id=42,
    )
    by_id = {item.match_id: item for item in normalized.matches}
    return tuple(
        replace(by_id[match_id], session_id=session_id, session_index=index)
        for index, (match_id, _hero_id, _lane_role, _value, session_id) in enumerate(specs, start=1)
    )


def _resolve(
    target: NormalizedSummaryMatch,
    candidates: tuple[NormalizedSummaryMatch, ...],
    values: dict[int, float],
    *,
    taxonomy: HeroTaxonomy | None = None,
    weights: dict[int, float] | None = None,
    exclusion_group_id: str | None = "target-session",
    use_taxonomy: bool = True,
):
    return resolve_leave_group_out_baseline(
        target=target,
        candidate_rows=candidates,
        performance_by_match=values,
        taxonomy=_taxonomy() if use_taxonomy and taxonomy is None else taxonomy,
        weights_by_match=weights or {match_id: 1.0 for match_id in values},
        exclusion_group_id=exclusion_group_id,
    )


def test_resolver_uses_the_narrowest_supported_context_then_falls_back_deterministically() -> None:
    target, *candidate_rows = _rows(
        [
            (1, 1, 1, 0, "target-session"),
            (2, 1, 1, 0, "s2"),
            (3, 1, 1, 0, "s3"),
            (4, 1, 1, 0, "s4"),
            (5, 1, 2, 0, "s5"),
            (6, 1, 2, 0, "s6"),
            (7, 1, 2, 0, "s7"),
            (8, 2, 1, 0, "s8"),
            (9, 2, 1, 0, "s9"),
            (10, 2, 1, 0, "s10"),
            (11, 4, 1, 0, "s11"),
            (12, 4, 1, 0, "s12"),
            (13, 4, 1, 0, "s13"),
            (14, 4, 2, 0, "s14"),
            (15, 4, 2, 0, "s15"),
            (16, 4, 2, 0, "s16"),
        ]
    )
    candidates = tuple(candidate_rows)
    values = {item.match_id: float(item.match_id) / 100.0 for item in candidates}

    narrow = _resolve(target, candidates, values)
    assert narrow is not None
    assert narrow.level == "hero_role_function"
    assert narrow.reference_match_ids == (2, 3, 4)

    hero_function = _resolve(target, tuple(item for item in candidates if item.match_id not in {2, 3, 4}), values)
    assert hero_function is not None
    assert hero_function.level == "hero_function"
    assert hero_function.reference_match_ids == (5, 6, 7)

    function = _resolve(
        target,
        tuple(item for item in candidates if item.match_id not in {2, 3, 4, 5, 6, 7}),
        values,
    )
    assert function is not None
    assert function.level == "function"
    assert function.reference_match_ids == (8, 9, 10)

    role = _resolve(
        target,
        tuple(item for item in candidates if item.match_id not in {2, 3, 4, 5, 6, 7, 8, 9, 10}),
        values,
    )
    assert role is not None
    assert role.level == "role"
    assert role.reference_match_ids == (11, 12, 13)

    overall = _resolve(
        target,
        tuple(item for item in candidates if item.match_id in {14, 15, 16}),
        values,
    )
    assert overall is not None
    assert overall.level == "overall"
    assert overall.reference_match_ids == (14, 15, 16)


def test_resolver_excludes_target_group_and_returns_none_when_no_cell_has_three_references() -> None:
    target, *candidate_rows = _rows(
        [
            (1, 1, 1, 0, "target-session"),
            (2, 1, 1, 0, "target-session"),
            (3, 1, 1, 0, "target-session"),
            (4, 1, 1, 0, "outside"),
            (5, 1, 1, 0, "outside"),
        ]
    )
    candidates = tuple(candidate_rows)
    values = {item.match_id: 0.5 for item in candidates}

    resolution = _resolve(target, candidates, values)
    assert resolution is None


def test_resolver_falls_back_to_role_or_overall_without_taxonomy_or_role_context() -> None:
    target, *candidate_rows = _rows(
        [
            (1, 1, 1, 0, "target-session"),
            (2, 4, 1, 0, "s2"),
            (3, 4, 1, 0, "s3"),
            (4, 4, 1, 0, "s4"),
        ]
    )
    candidates = tuple(candidate_rows)
    values = {item.match_id: 0.5 for item in candidates}

    role = _resolve(target, candidates, values, taxonomy=None, use_taxonomy=False)
    assert role is not None
    assert role.level == "role"

    no_role_target = replace(target, role_hint=None)
    overall = _resolve(no_role_target, candidates, values, taxonomy=None, use_taxonomy=False)
    assert overall is not None
    assert overall.level == "overall"


def test_resolver_uses_weighted_median_and_exposes_effective_sample_and_ids() -> None:
    target, *candidate_rows = _rows(
        [
            (1, 1, 1, 0, "target-session"),
            (2, 1, 1, 0, "s2"),
            (3, 1, 1, 0, "s3"),
            (4, 1, 1, 0, "s4"),
        ]
    )
    candidates = tuple(candidate_rows)
    values = {2: 0.10, 3: 0.20, 4: 0.90}
    resolution = _resolve(
        target,
        candidates,
        values,
        weights={2: 1.0, 3: 1.0, 4: 5.0},
    )
    assert resolution is not None
    assert resolution.value == 0.90
    assert resolution.reference_sample_size == 3
    assert resolution.effective_sample_size > 1.0
    assert resolution.reference_match_ids == (2, 3, 4)

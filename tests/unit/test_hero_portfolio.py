from __future__ import annotations

from app.hero_portfolio.common_thread import compute_common_thread
from app.hero_portfolio.eligibility import build_hero_eligibility
from app.hero_portfolio.exception import compute_hero_exception
from app.heroes.taxonomy import TRAITS, HeroTaxonomy, HeroTaxonomyEntry
from app.ingestion.summary_normalize import normalize_summary_rows


def _taxonomy(*, outlier: bool = False) -> HeroTaxonomy:
    heroes: dict[int, HeroTaxonomyEntry] = {}
    for hero_id in range(1, 6):
        traits = {trait: 0.10 for trait in TRAITS}
        if hero_id < 5:
            traits["mobility"] = 0.80
        if outlier and hero_id == 4:
            traits["mobility"] = 0.10
            traits["global_presence"] = 0.95
            traits["push"] = 0.90
        if hero_id == 5:
            traits["mobility"] = 1.0
            traits["global_presence"] = 1.0
        heroes[hero_id] = HeroTaxonomyEntry(
            hero_id=hero_id,
            key=f"hero_{hero_id}",
            name=f"Hero {hero_id}",
            roles=("carry",),
            traits=traits,
            portrait_url=f"https://example.test/{hero_id}.png",
            provenance={"source": "fixture", "research_file": "fixture", "editorial": "fixture", "review_status": "reviewed"},
        )
    return HeroTaxonomy("fixture-taxonomy", heroes, {})


def _matches() -> tuple:
    rows = [
        {
            "match_id": 800_000 + index,
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
        for index in range(48)
    ]
    rows.append({**rows[-1], "match_id": 800_999, "start_time": 1_700_200_000, "hero_id": 5})
    return normalize_summary_rows(rows, account_id=42).matches


def test_one_game_hero_cannot_enter_established_portfolio_candidates() -> None:
    matches = _matches()
    eligibility = build_hero_eligibility(matches, _taxonomy())
    one_game = next(item for item in eligibility if item.hero_id == 5)

    assert not one_game.eligible_for_common_thread
    assert not one_game.eligible_for_exception
    assert not one_game.eligible_for_mirror
    assert "too_few_matches" in one_game.exclusion_reasons
    assert "too_small_history_share" in one_game.exclusion_reasons


def test_common_thread_caps_dominant_hero_and_ignores_one_game_luck() -> None:
    matches = _matches()
    taxonomy = _taxonomy()
    result = compute_common_thread(matches, taxonomy)

    assert result.status == "available"
    assert result.trait_key == "mobility"
    assert result.denominator == 4
    assert all(option.hero_id is None for option in result.options)


def test_exception_can_return_a_clear_functional_outlier() -> None:
    matches = _matches()
    result = compute_hero_exception(matches, _taxonomy(outlier=True))

    assert result.status == "available"
    assert result.hero_id == 4
    assert result.correct_option_key == "hero:4"


def test_exception_preserves_no_clear_state_when_pool_shapes_match() -> None:
    matches = _matches()
    result = compute_hero_exception(matches, _taxonomy())

    assert result.status == "no_clear_exception"
    assert result.hero_id is None
    assert result.correct_option_key == "no_clear_exception"

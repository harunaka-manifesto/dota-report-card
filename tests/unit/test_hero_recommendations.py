from app.dna.features.models import DnaFeatureSet
from app.heroes.identity import HeroCard
from app.heroes.recommendations import recommend_heroes
from app.heroes.taxonomy import TRAITS, HeroTaxonomy, HeroTaxonomyEntry


def _entry(hero_id: int, name: str, roles: tuple[str, ...], active: set[str]) -> HeroTaxonomyEntry:
    return HeroTaxonomyEntry(
        hero_id=hero_id,
        key=name.lower().replace(" ", "_"),
        name=name,
        roles=roles,
        traits={trait: 0.9 if trait in active else 0.1 for trait in TRAITS},
        portrait_url=f"https://example.test/{hero_id}.png",
        provenance={"source": "test"},
    )


def _card(hero_id: int, name: str, score: float) -> HeroCard:
    return HeroCard(
        hero_id=hero_id,
        name=name,
        portrait_url=f"https://example.test/{hero_id}.png",
        score=score,
        component_scores={},
        matches=8,
        roles=("carry",),
        traits=("initiation", "mobility"),
        receipts=(),
        reason_key="comfort_pick",
    )


def test_recommendations_return_a_diverse_three_item_set_and_allow_one_role_change() -> None:
    heroes = {
        1: _entry(1, "Comfort One", ("carry",), {"initiation", "mobility", "burst"}),
        2: _entry(2, "Comfort Two", ("carry",), {"initiation", "mobility", "burst"}),
        3: _entry(3, "Adjacent One", ("carry",), {"initiation", "wave_clear"}),
        4: _entry(4, "Adjacent Two", ("carry",), {"mobility", "push"}),
        5: _entry(5, "Adjacent Three", ("offlane",), {"initiation", "burst", "save"}),
        6: _entry(6, "Played Too Much", ("carry",), {"initiation", "wave_clear"}),
    }
    taxonomy = HeroTaxonomy("test", heroes, {})
    features = DnaFeatureSet(
        matches=(),
        sessions=(),
        hero_counts={1: 8, 2: 7, 6: 5},
        role_counts={"carry": 20},
        sample_size=35,
    )

    recommendations = recommend_heroes(
        (_card(1, "Comfort One", 0.9), _card(2, "Comfort Two", 0.8)),
        features,
        taxonomy,
    )

    assert [item["hero_id"] for item in recommendations] == [3, 4, 5]
    assert sum(bool(item["role_change"]) for item in recommendations) <= 1
    assert all(item["recommendation_version"] == "hero-recommendations-1.1.0" for item in recommendations)

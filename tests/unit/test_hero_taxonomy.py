from app.heroes.taxonomy import TRAITS, load_default_taxonomy


def test_checked_in_taxonomy_uses_stable_ids_and_complete_editorial_rows() -> None:
    taxonomy = load_default_taxonomy()

    assert taxonomy.validate() == ()
    assert len(taxonomy.heroes) == 127
    assert taxonomy.get(1).name == "Anti-Mage"  # type: ignore[union-attr]
    assert taxonomy.get(22).name == "Zeus"  # type: ignore[union-attr]
    assert taxonomy.get(155).name == "Largo"  # type: ignore[union-attr]
    assert all(set(hero.traits) == set(TRAITS) for hero in taxonomy.heroes.values())
    assert all(hero.provenance and hero.portrait_url for hero in taxonomy.heroes.values())

__all__ = [
    "HeroIdentityResult",
    "HeroTaxonomy",
    "HeroTaxonomyEntry",
    "load_default_taxonomy",
    "select_hero_identity",
]


def __getattr__(name: str):
    if name in {"HeroTaxonomy", "HeroTaxonomyEntry", "load_default_taxonomy"}:
        from app.heroes.taxonomy import HeroTaxonomy, HeroTaxonomyEntry, load_default_taxonomy

        return {
            "HeroTaxonomy": HeroTaxonomy,
            "HeroTaxonomyEntry": HeroTaxonomyEntry,
            "load_default_taxonomy": load_default_taxonomy,
        }[name]
    if name in {"HeroIdentityResult", "select_hero_identity"}:
        from app.heroes.identity import HeroIdentityResult, select_hero_identity

        return {
            "HeroIdentityResult": HeroIdentityResult,
            "select_hero_identity": select_hero_identity,
        }[name]
    raise AttributeError(name)

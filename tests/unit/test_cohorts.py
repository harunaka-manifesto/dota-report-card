from app.cohorts.selector import select_narrowest_cohort


def test_cohort_backoff_chooses_narrowest_valid_level() -> None:
    target = {"account_id": 1, "hero_id": 25, "role": 2, "rank_tier": 45, "patch": "7.36c"}
    population = [
        {
            "account_id": index + 2,
            "hero_id": 25,
            "role": 2,
            "rank_tier": 45,
            "patch": "7.36b" if index < 22 else "7.36c",
            "won": index % 2 == 0,
            "gold_per_min": 500 + index,
            "xp_per_min": 500,
            "last_hits": 200,
            "tower_damage": 1000,
            "duration_seconds": 1800,
            "kills": 5,
            "assists": 10,
        }
        for index in range(25)
    ]
    cohort = select_narrowest_cohort(target, population, minimum_rows=5, minimum_distinct_players=5)
    assert cohort.valid
    assert cohort.level == "hero_role_rank"
    assert cohort.sample_size == 25


def test_sparse_cohort_fails_closed() -> None:
    target = {"account_id": 1, "hero_id": 25, "role": 2, "rank_tier": 45, "patch": "7.36c"}
    cohort = select_narrowest_cohort(target, [target], minimum_rows=5, minimum_distinct_players=2)
    assert not cohort.valid
    assert cohort.suppression_reason == "NO_VALID_COHORT"

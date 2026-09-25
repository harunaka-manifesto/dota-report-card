from scripts.tracker_traceability import STATUSES, verify


def test_every_acceptance_rule_is_classified_and_cited_tests_exist():
    counts, problems = verify()
    assert problems == []
    assert set(counts) <= STATUSES and sum(counts.values()) == 305

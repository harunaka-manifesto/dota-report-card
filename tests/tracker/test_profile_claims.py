import pytest
from app.tracker.profile_claims import (
    ClaimEvaluation,
    ClaimPolicy,
    evaluate,
    load_checkpoint,
    record_checkpoint,
)
from sqlalchemy import text


def evaluation(seq: int, *, enter: bool = True, exit: bool = False, covered: bool = True, n: int = 2):
    match_ids = list(range(1, n + 1))
    return ClaimEvaluation(
        claim_id="role-shape", claim_version="1", mode="STANDARD", scope="ACCOUNT",
        checkpoint_seq=seq, match_id=1000 + seq, eligible=True, coverage_complete=covered,
        enter_met=enter, exit_met=exit,
        evidence={
            "window": {"definition": "last 200 eligible matches / 24 months", "start_at": "2026-01-01", "end_at": "2026-09-01"},
            "n": n, "aggregate_values": {"carry_share": 0.7}, "thresholds_crossed": ["SPECIALIST"],
            "sample_match_ids": match_ids, "representative_match_ids": match_ids[:1],
            "coverage": {"complete": covered, "from_at": "2026-01-01", "more_arriving": False},
        },
    )


def test_claim_confirmation_and_exit_require_gap_between_observations():
    policy = ClaimPolicy("profile-v1-provisional", persistence_gap=3)
    candidate = evaluate(evaluation(1), None, policy)
    assert candidate and candidate.state == "CANDIDATE"
    assert evaluate(evaluation(3), candidate.__dict__, policy).state == "CANDIDATE"
    confirmed = evaluate(evaluation(4), candidate.__dict__, policy)
    assert confirmed and confirmed.state == "CONFIRMED"
    pending_exit = evaluate(evaluation(5, exit=True), confirmed.__dict__, policy)
    assert pending_exit and pending_exit.state == "CONFIRMED"
    fading = evaluate(evaluation(8, exit=True), pending_exit.__dict__, policy)
    assert fading and fading.state == "FADING"


def test_incomplete_coverage_and_failed_candidate_are_withheld_silently():
    policy = ClaimPolicy("profile-v1-provisional", persistence_gap=3)
    assert evaluate(evaluation(1, covered=False), None, policy) is None
    candidate = evaluate(evaluation(1), None, policy)
    assert candidate is not None
    assert evaluate(evaluation(2, enter=False), candidate.__dict__, policy) is None


def test_evidence_window_is_bounded_and_sample_truthful():
    policy = ClaimPolicy("profile-v1-provisional", persistence_gap=1)
    too_many = evaluation(1, n=201)
    with pytest.raises(ValueError, match="bounded"):
        evaluate(too_many, None, policy)
    inconsistent = evaluation(1)
    object.__setattr__(inconsistent, "evidence", {**inconsistent.evidence, "n": 3})
    with pytest.raises(ValueError, match="sample count"):
        evaluate(inconsistent, None, policy)


def test_same_checkpoint_is_idempotent_and_changed_input_is_rejected():
    policy = ClaimPolicy("profile-v1-provisional", persistence_gap=5)
    first = evaluation(1)
    candidate = evaluate(first, None, policy)
    assert candidate
    assert evaluate(first, candidate.__dict__, policy).state == "CANDIDATE"
    with pytest.raises(ValueError, match="monotonically"):
        evaluate(evaluation(1, enter=False), candidate.__dict__, policy)


def test_postgres_claim_checkpoint_is_generation_fenced_and_keeps_previous_evidence(database):
    from .test_schema import identity

    _, profile_id = identity(database)
    policy = ClaimPolicy("profile-v1-provisional", persistence_gap=3)
    first = evaluation(1)
    candidate = evaluate(first, None, policy)
    assert candidate
    with database.begin() as connection:
        assert record_checkpoint(connection, profile_id=profile_id, profile_generation=1,
                                current=first, result=candidate)
        assert not record_checkpoint(connection, profile_id=profile_id, profile_generation=1,
                                    current=first, result=candidate)
        previous = load_checkpoint(connection, profile_id=profile_id, mode="STANDARD",
                                   scope="ACCOUNT", claim_id="role-shape", claim_version="1")
        assert previous
        second = evaluation(4)
        confirmed = evaluate(second, previous, policy)
        assert confirmed and confirmed.state == "CONFIRMED"
        assert record_checkpoint(connection, profile_id=profile_id, profile_generation=1,
                                current=second, result=confirmed)
    with database.connect() as connection:
        row = connection.execute(text("""SELECT state, previous_evidence
            FROM tracker_profile_claim_checkpoints WHERE profile_id=:id"""), {"id": profile_id}).mappings().one()
        assert row["state"] == "CONFIRMED"
        assert row["previous_evidence"]["n"] == candidate.evidence["n"]
    next_input = evaluation(5)
    next_result = evaluate(next_input, confirmed.__dict__, policy)
    assert next_result
    with database.begin() as connection, pytest.raises(ValueError, match="stale or inactive"):
        record_checkpoint(connection, profile_id=profile_id, profile_generation=2,
                          current=next_input, result=next_result)
    with database.begin() as connection, pytest.raises(ValueError, match="matching eligible"):
        record_checkpoint(connection, profile_id=profile_id, profile_generation=1,
                          current=next_input, result=confirmed)

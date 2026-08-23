from datetime import UTC, datetime, timedelta

import pytest
from app.storage.repository import (
    InMemoryRepository,
    InteractionRevisionConflict,
)


def _repository() -> tuple[InMemoryRepository, str]:
    repository = InMemoryRepository()
    report_id = repository.save_report(
        account_id=42,
        data_cutoff=100,
        model_version="free-dna-model-6.0.0",
        template_version="templates-6.0.0",
        report={"identity": {"account_id": 42}},
        evidence=[],
    )
    return repository, report_id


def test_interaction_token_is_returned_once_and_only_digest_is_stored() -> None:
    repository, report_id = _repository()
    session, token = repository.create_interaction_session(
        report_id,
        state={"user_reported": {"estimate": "steady"}},
        recommendation_baseline={"metric": "win_rate", "value": 0.5},
    )

    assert len(token) >= 40
    assert token not in repr(repository.interaction_sessions)
    assert session.token_hash != token
    assert repository.authenticate_interaction_session(session.session_id, token).revision == 1


def test_interaction_revision_conflict_and_expiry_fail_closed() -> None:
    repository, report_id = _repository()
    now = datetime.now(UTC)
    session, token = repository.create_interaction_session(report_id, now=now)
    updated = repository.update_interaction_session(
        session.session_id,
        token,
        expected_revision=1,
        state={"user_reported": {"answer": "a"}},
    )
    assert updated.revision == 2
    with pytest.raises(InteractionRevisionConflict):
        repository.update_interaction_session(
            session.session_id,
            token,
            expected_revision=1,
            state={"user_reported": {"answer": "stale"}},
        )
    assert repository.get_interaction_session(
        session.session_id,
        now=now + timedelta(days=91),
    ) is None


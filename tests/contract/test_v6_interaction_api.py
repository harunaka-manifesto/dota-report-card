from app.analysis.source import MappingSource
from app.core.config import Settings
from app.main import create_app
from app.storage.repository import InMemoryRepository
from fastapi.testclient import TestClient


def _client() -> tuple[TestClient, str]:
    repository = InMemoryRepository()
    report_id = repository.save_report(
        account_id=42,
        data_cutoff=100,
        model_version="free-dna-model-6.0.0",
        template_version="templates-6.0.0",
        report={
            "identity": {"account_id": 42},
            "diagnostic_questions": [
                {"id": "q-transfer", "primary_hypothesis_id": "h-transfer"}
            ],
        },
        evidence=[],
    )
    source = MappingSource(
        player={"profile": {"account_id": 42}},
        matches=[],
        details={},
    )
    return TestClient(create_app(Settings(), source=source, repository=repository)), report_id


def test_interaction_api_requires_bearer_and_if_match_and_deletes() -> None:
    client, report_id = _client()
    created = client.post(
        f"/v1/reports/{report_id}/interaction-sessions",
        json={"state": {"user_reported": {"estimate": "steady"}}},
    )
    assert created.status_code == 201
    body = created.json()
    session_id = body["session_id"]
    token = body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get(f"/v1/report-interactions/{session_id}").status_code == 401
    assert client.patch(
        f"/v1/report-interactions/{session_id}",
        headers=headers,
        json={"state": {"user_reported": {"estimate": "different"}}},
    ).status_code == 428
    updated = client.patch(
        f"/v1/report-interactions/{session_id}",
        headers={**headers, "If-Match": '"1"'},
        json={"state": {"user_reported": {"estimate": "different"}}},
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert client.patch(
        f"/v1/report-interactions/{session_id}",
        headers={**headers, "If-Match": '"1"'},
        json={"state": {}},
    ).status_code == 409
    assert client.delete(f"/v1/report-interactions/{session_id}", headers=headers).status_code == 204
    assert client.get(f"/v1/report-interactions/{session_id}", headers=headers).status_code == 404


def test_deep_api_rejects_unoffered_question_and_persists_selection_metadata() -> None:
    client, report_id = _client()
    rejected = client.post(
        f"/v1/reports/{report_id}/deep-analyses",
        json={"diagnostic_question_id": "q-not-offered"},
    )
    assert rejected.status_code == 422
    accepted = client.post(
        f"/v1/reports/{report_id}/deep-analyses",
        json={"diagnostic_question_id": "q-transfer"},
    )
    assert accepted.status_code == 202
    body = accepted.json()
    assert body["parent_report_id"] == report_id
    assert body["selection_plan"]["limits"]["max_detail_requests"] == 25
    assert body["selection_plan"]["limits"]["max_parse_requests"] == 25
    assert body["selection_plan"]["limits"]["max_data_cost"] == 160


def test_deep_api_authenticates_an_attached_interaction_session() -> None:
    client, report_id = _client()
    created = client.post(
        f"/v1/reports/{report_id}/interaction-sessions",
        json={"state": {"user_reported": {"estimate": "steady"}}},
    )
    assert created.status_code == 201
    session_id = created.json()["session_id"]
    token = created.json()["access_token"]
    payload = {
        "diagnostic_question_id": "q-transfer",
        "interaction_session_id": session_id,
    }

    assert client.post(
        f"/v1/reports/{report_id}/deep-analyses",
        json=payload,
    ).status_code == 401
    accepted = client.post(
        f"/v1/reports/{report_id}/deep-analyses",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert accepted.status_code == 202
    assert accepted.json()["diagnostic_question_id"] == "q-transfer"

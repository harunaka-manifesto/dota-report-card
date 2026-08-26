import asyncio

from app.analysis.source import FixtureOpenDotaSource, MappingSource
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_health_contract() -> None:
    app = create_app(Settings(), source=FixtureOpenDotaSource("tests/fixtures/opendota"))
    client = TestClient(app)
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert set(response.json()) == {
        "status",
        "api",
        "postgres",
        "redis",
        "worker",
        "artifacts",
        "auth",
        "source",
    }

    ready = client.get("/v1/health/ready")
    assert ready.status_code == 200
    assert ready.json()["release"]["free_dna_generation"] == "v5.2"
    assert ready.json()["release_parity"] == "not_required"
    release = client.get("/v1/health/release").json()["release"]
    assert release["git_sha"] == "unknown"
    assert release["deployed_source_sha"] == "unknown"
    assert release["analytical_source_sha"] is None


def test_malformed_identifier_is_rejected_before_source_request() -> None:
    source = FixtureOpenDotaSource("tests/fixtures/opendota")
    app = create_app(Settings(), source=source)
    response = TestClient(app).post(
        "/v1/analyses",
        json={"player": "https://example.com/players/193875165"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_PLAYER_IDENTIFIER"
    assert source.requests == []


def test_create_analysis_returns_job_contract() -> None:
    source = FixtureOpenDotaSource("tests/fixtures/opendota")
    app = create_app(Settings(), source=source)
    response = TestClient(app).post("/v1/analyses", json={"player": "193875165"})
    assert response.status_code == 202
    body = response.json()
    assert {"job_id", "status", "reused", "events_url"} <= set(body)


def test_private_profile_returns_stable_empty_state() -> None:
    source = MappingSource(player={"profile": None}, matches=[], details={})
    app = create_app(Settings(), source=source)
    service = app.state.analysis_service
    job, _ = asyncio.run(service.create_analysis("193875165", enqueue=False))
    asyncio.run(service.run_job(job))
    assert job.status == "failed"
    assert job.failure_code == "PROFILE_PRIVATE_OR_UNAVAILABLE"
    response = TestClient(app).get(f"/v1/analyses/{job.job_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Public profile is unavailable"

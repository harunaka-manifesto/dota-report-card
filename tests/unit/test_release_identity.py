from __future__ import annotations

from dataclasses import replace

import pytest
from app.core.config import Settings, validate_runtime_configuration
from app.core.release import artifact_bundle_digest, build_release_identity

ANALYTICAL_SOURCE_SHA = "7df38e6d234ae9c4ee425490bc40b8cc92685f85"
DEPLOY_SOURCE_SHA = "a" * 40


def test_release_identity_binds_v61_runtime_metadata() -> None:
    settings = Settings(
        free_dna_v61_enabled=True,
        release_commit_sha=DEPLOY_SOURCE_SHA,
        free_dna_v61_analytical_source_sha=ANALYTICAL_SOURCE_SHA,
        release_worktree_dirty=False,
        analysis_execution_backend="celery",
        storage_backend="database",
    )
    identity = build_release_identity(
        settings,
        artifact_checksums={"b.json": "b", "a.json": "a"},
        artifact_manifest={"version": "manifest-1"},
        db_revision="0005_v6_interactions_deep",
    )

    assert identity["git_sha"] == DEPLOY_SOURCE_SHA
    assert identity["deployed_source_sha"] == DEPLOY_SOURCE_SHA
    assert identity["analytical_source_sha"] == ANALYTICAL_SOURCE_SHA
    assert identity["free_dna_generation"] == "v6.1"
    assert identity["report_schema_version"] == "free-dna-report-6.1.0"
    assert identity["v61_artifact_manifest_version"] == "manifest-1"
    assert identity["v61_artifact_bundle_digest"] == artifact_bundle_digest(
        {"a.json": "a", "b.json": "b"}
    )
    assert identity["db_alembic_revision"] == "0005_v6_interactions_deep"


def test_production_rejects_fixture_source_and_missing_release_binding() -> None:
    with pytest.raises(ValueError, match="OPENDOTA_SOURCE=live"):
        validate_runtime_configuration(Settings(app_env="production"))


def test_production_requires_clean_release_metadata() -> None:
    with pytest.raises(ValueError, match="RELEASE_COMMIT_SHA"):
        validate_runtime_configuration(Settings(app_env="production", opendota_source="live"))


def _production_v61_settings(analytical_source_sha: str | None) -> Settings:
    return Settings(
        app_env="production",
        opendota_source="live",
        storage_backend="database",
        analysis_execution_backend="celery",
        free_dna_v61_enabled=True,
        free_dna_v61_analytical_source_sha=analytical_source_sha,
        release_commit_sha=DEPLOY_SOURCE_SHA,
        release_worktree_dirty=False,
    )


def test_production_requires_explicit_v61_analytical_source_sha() -> None:
    with pytest.raises(ValueError, match="FREE_DNA_V61_ANALYTICAL_SOURCE_SHA"):
        validate_runtime_configuration(_production_v61_settings(None))


def test_production_rejects_malformed_v61_analytical_source_sha() -> None:
    with pytest.raises(ValueError, match="40-character commit"):
        validate_runtime_configuration(_production_v61_settings("not-a-sha"))


def test_release_sha_change_does_not_rebind_analytical_identity() -> None:
    base = _production_v61_settings(ANALYTICAL_SOURCE_SHA)
    first = build_release_identity(
        base,
    )
    second = build_release_identity(replace(base, release_commit_sha="b" * 40))
    assert first["deployed_source_sha"] != second["deployed_source_sha"]
    assert first["analytical_source_sha"] == second["analytical_source_sha"]


def test_api_and_worker_share_the_same_analytical_source_contract() -> None:
    api_identity = build_release_identity(_production_v61_settings(ANALYTICAL_SOURCE_SHA))
    worker_identity = build_release_identity(
        replace(_production_v61_settings(ANALYTICAL_SOURCE_SHA), release_commit_sha="b" * 40)
    )
    assert api_identity["analytical_source_sha"] == worker_identity["analytical_source_sha"]

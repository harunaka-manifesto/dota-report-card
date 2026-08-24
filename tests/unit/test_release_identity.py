from __future__ import annotations

import pytest
from app.core.config import Settings, validate_runtime_configuration
from app.core.release import artifact_bundle_digest, build_release_identity


def test_release_identity_binds_v61_runtime_metadata() -> None:
    settings = Settings(
        free_dna_v61_enabled=True,
        release_commit_sha="release-sha",
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

    assert identity["git_sha"] == "release-sha"
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

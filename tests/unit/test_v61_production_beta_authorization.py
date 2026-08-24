from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.player_analysis_v61.artifacts import (
    ArtifactValidationError,
    load_v61_production_beta_authorization,
)
from app.player_analysis_v61.calibration_evaluation import (
    build_v61_production_beta_authorization,
)


def _evaluation() -> dict[str, object]:
    return {
        "version": "calibration-evaluation-6.1.0",
        "state_b": True,
        "gates": {"automated": {"passed": True}},
    }


def _release_manifest() -> dict[str, object]:
    return {
        "version": "free-dna-v61-release-manifest-6.1.0",
        "automated_gates": {"sealed_holdout_gates": True},
        "artifact_checksums": {"context-baseline-3.0.0.json": "abc123"},
    }


def test_production_beta_authorization_is_separate_from_frozen_release_manifest() -> None:
    result = build_v61_production_beta_authorization(
        evaluation=_evaluation(),
        release_manifest=_release_manifest(),
        source_revision="abc123",
        dirty_worktree=True,
        operator_authorization_reference="user-task:Free DNA V6.1 production beta",
    )

    assert result["production_beta_authorized"] is True
    assert result["release_authorized"] is True
    assert result["state_c"] is False
    assert result["public_flags_must_remain_off"] is False
    assert result["approval_basis"] == (
        "owner-assumed-review-complete-per-explicit-task-instruction"
    )


def test_loader_requires_matching_checksums_and_explicit_beta_authorization(
    tmp_path: Path,
) -> None:
    result = build_v61_production_beta_authorization(
        evaluation=_evaluation(),
        release_manifest=_release_manifest(),
        source_revision="abc123",
        dirty_worktree=False,
        operator_authorization_reference="user-task:Free DNA V6.1 production beta",
    )
    path = tmp_path / "production-beta-authorization-6.1.0.json"
    path.write_text(json.dumps(result), encoding="utf-8")

    loaded = load_v61_production_beta_authorization(
        path,
        artifact_checksums={"context-baseline-3.0.0.json": "abc123"},
    )
    assert loaded["release_mode"] == "production-beta"

    with pytest.raises(ArtifactValidationError, match="checksum mismatch"):
        load_v61_production_beta_authorization(
            path,
            artifact_checksums={"context-baseline-3.0.0.json": "different"},
        )

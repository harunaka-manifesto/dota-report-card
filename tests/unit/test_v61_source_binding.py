from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.player_analysis_v61 import artifacts as artifact_module
from app.player_analysis_v61.artifacts import (
    FREEZE_RECORD_VERSION,
    V61_BUILD_MANIFEST_VERSION,
    V61_SUPPORT_ARTIFACTS,
    ArtifactValidationError,
    validate_v61_freeze_record,
)
from app.player_analysis_v61.calibration_corpus import CANONICAL_SCHEMA_VERSION
from app.player_analysis_v61.calibration_evaluation import build_v61_calibration_evaluation

from scripts import build_v61_calibration_artifacts as builder


def _manifest_bundle(
    directory: Path, *, version: str, source: dict[str, object] | None = None
) -> None:
    directory.mkdir()
    for name in V61_SUPPORT_ARTIFACTS:
        (directory / name).write_text("{}", encoding="utf-8")
    (directory / "build-manifest-6.1.0.json").write_text(
        json.dumps(
            {
                "version": version,
                "corpus_schema": CANONICAL_SCHEMA_VERSION,
                "release_authorized": False,
                "holdout_output_inspected": False,
                **({"source": source} if source is not None else {}),
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("version", "message"),
    [
        ("v61-calibration-build-manifest-1.0.0", "unsupported"),
        (V61_BUILD_MANIFEST_VERSION, "source binding"),
    ],
)
def test_loader_rejects_unbound_manifests(
    tmp_path: Path, version: str, message: str
) -> None:
    artifact_dir = tmp_path / "artifacts"
    _manifest_bundle(artifact_dir, version=version)

    with pytest.raises(ArtifactValidationError, match=message):
        artifact_module.load_v61_artifact_bundle(artifact_dir)


def test_loader_rejects_mismatched_expected_source(tmp_path: Path) -> None:
    source = {"repository_commit": "a" * 40, "dirty_worktree": False}
    artifact_dir = tmp_path / "artifacts"
    _manifest_bundle(artifact_dir, version=V61_BUILD_MANIFEST_VERSION, source=source)

    with pytest.raises(ArtifactValidationError, match="source revision mismatch"):
        artifact_module.load_v61_artifact_bundle(
            artifact_dir,
            expected_source_revision="b" * 40,
            expected_dirty_worktree=False,
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {"version": "v61-freeze-record-1.0.0", "source": {"repository_commit": "a" * 40, "dirty_worktree": False}},
            "unsupported",
        ),
        ({"version": FREEZE_RECORD_VERSION}, "source binding"),
    ],
)
def test_freeze_record_rejects_old_or_unbound_payload(
    payload: dict[str, object], message: str
) -> None:
    with pytest.raises(ArtifactValidationError, match=message):
        validate_v61_freeze_record(payload)


def test_aggregate_rejects_cross_source_mismatch() -> None:
    manifest_source = {"repository_commit": "a" * 40, "dirty_worktree": False}
    runtime_source = {"repository_commit": "b" * 40, "dirty_worktree": False}

    with pytest.raises(ValueError, match="source"):
        build_v61_calibration_evaluation(
            compatibility_audit={},
            freeze_manifest={"source": manifest_source},
            freeze_record={"version": FREEZE_RECORD_VERSION, "source": manifest_source},
            reproducibility={},
            synthetic={},
            holdout={},
            runtime_parity={"source": runtime_source},
            artifact_checksums={},
            source_revision=manifest_source["repository_commit"],
            dirty_worktree=False,
        )


@pytest.mark.parametrize(
    ("revision", "status", "message"),
    [
        ("not-a-commit", "", "40-character"),
        ("a" * 40, " M changed.py\n", "clean worktree"),
    ],
)
def test_freeze_source_binding_fails_closed(
    monkeypatch: pytest.MonkeyPatch, revision: str, status: str, message: str
) -> None:
    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(stdout=revision if command[1] == "rev-parse" else status)

    monkeypatch.setattr(builder.subprocess, "run", fake_run)

    with pytest.raises(ValueError, match=message):
        builder._source_binding()


def test_freeze_writes_exact_source_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = {"repository_commit": "b" * 40, "dirty_worktree": False}
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text("{}", encoding="utf-8")
    split_path = tmp_path / "split.json"
    split_path.write_text(
        json.dumps(
            {
                "train_profile_ids": [str(index) for index in range(791)],
                "holdout_profile_ids": [str(index) for index in range(791, 1130)],
            }
        ),
        encoding="utf-8",
    )
    audit_path = tmp_path / "audit.json"
    audit_path.write_text("{}", encoding="utf-8")
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    for name in V61_SUPPORT_ARTIFACTS[:-1]:
        (artifact_dir / name).write_bytes(name.encode("utf-8"))

    audit = {"audit_checksum": "audit-sha", "v6_0_comparison_context": {}}
    loader_kwargs: dict[str, object] = {}
    monkeypatch.setattr(builder, "_source_binding", lambda: source)
    monkeypatch.setattr(builder, "require_compatible_audit", lambda *_args, **_kwargs: audit)
    monkeypatch.setattr(builder, "load_rows", lambda _path: [])
    monkeypatch.setattr(
        builder,
        "split_from_manifest",
        lambda *_args, **_kwargs: (set(range(791)), set(range(339))),
    )
    monkeypatch.setattr(builder, "current_taxonomy_mapping", lambda: {})
    monkeypatch.setattr(
        builder,
        "load_v61_artifact_bundle",
        lambda _path, **kwargs: loader_kwargs.update(kwargs),
    )
    monkeypatch.setattr(artifact_module, "load_context_baseline_artifact_v61", lambda _path: None)
    monkeypatch.setattr(artifact_module, "load_threshold_artifact_v61", lambda _path: None)

    args = SimpleNamespace(
        input=corpus_path,
        split_manifest=split_path,
        compatibility_audit=audit_path,
        generated_at="2000-01-01T00:00:00+00:00",
        reuse_authorization_reference="fixture-auth",
        artifact_dir=artifact_dir,
        output_dir=None,
    )

    assert builder._freeze(args) == 0

    manifest = json.loads(
        (artifact_dir / "build-manifest-6.1.0.json").read_text(encoding="utf-8")
    )
    freeze_record = json.loads(
        (artifact_dir / "freeze-record-6.1.0.json").read_text(encoding="utf-8")
    )
    assert manifest["source"] == source
    assert freeze_record["version"] == FREEZE_RECORD_VERSION
    assert freeze_record["source"] == source
    assert loader_kwargs["expected_source_revision"] == source["repository_commit"]
    assert loader_kwargs["expected_dirty_worktree"] is False

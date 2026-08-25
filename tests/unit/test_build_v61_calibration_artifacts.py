from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.player_analysis_v6.calibration import REQUIRED_THRESHOLD_KEYS
from app.player_analysis_v61.artifacts import (
    load_context_baseline_artifact_v61,
    load_threshold_artifact_v61,
)
from app.player_analysis_v61.calibration_corpus import (
    CANONICAL_SCHEMA_VERSION,
    LEGACY_CANONICAL_SCHEMA_VERSION,
)

ROOT = Path(__file__).resolve().parents[2]


def _rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for profile in range(10):
        for index in range(12):
            metrics = {
                key: 0.1 * profile + 0.01 * index + position * 0.001
                for position, key in enumerate(REQUIRED_THRESHOLD_KEYS)
            }
            metrics.update(
                {
                    "outcome": float((profile + index) % 2),
                    "involvement_per_minute": 0.3 + profile * 0.01,
                    "finishing_share": 0.2 + (profile + index) % 5 * 0.05,
                    "death_exposure_per_ten": 1.5 + index * 0.05,
                    "transfer_distance": (profile + index) / 25,
                }
            )
            rows.append(
                {
                    "profile_id": f"fixture-{profile}",
                    "match_id": profile * 1_000 + index,
                    "session_id": f"fixture-{profile}:{index // 2}",
                    "patch": "7.39",
                    "hero_id": 1 + index % 4,
                    "hero_function": "catch",
                    "lane_context": "core",
                    "region": 1,
                    "lobby_type": 0,
                    "metrics": metrics,
                }
            )
    return rows


def test_v61_builder_is_deterministic_training_only_and_loadable(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({"matches": _rows()}), encoding="utf-8")
    first, second = tmp_path / "first", tmp_path / "second"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "build_v61_calibration_artifacts.py"),
        "--input",
        str(corpus),
        "--seed",
        "6100",
        "--generated-at",
        "2000-01-01T00:00:00+00:00",
    ]
    subprocess.run([*command, "--output-dir", str(first)], check=True, capture_output=True)
    subprocess.run([*command, "--output-dir", str(second)], check=True, capture_output=True)

    assert {path.name for path in first.iterdir()} == {path.name for path in second.iterdir()}
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()
    load_context_baseline_artifact_v61(first / "context-baseline-3.0.0.json")
    load_threshold_artifact_v61(first / "metric-thresholds-6.1.0.json")
    manifest = json.loads((first / "build-manifest-6.1.0.json").read_text())
    assert manifest["split"]["overlap_count"] == 0
    assert manifest["release_authorized"] is False


def test_v61_builder_rejects_rank_dimensions(tmp_path: Path) -> None:
    rows = _rows()
    rows[0]["rank_tier"] = 80
    corpus = tmp_path / "ranked.json"
    corpus.write_text(json.dumps({"matches": rows}), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_v61_calibration_artifacts.py"),
            "--input",
            str(corpus),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "rank/MMR dimensions are forbidden" in result.stderr


@pytest.mark.parametrize("schema", [LEGACY_CANONICAL_SCHEMA_VERSION, CANONICAL_SCHEMA_VERSION])
def test_bind_split_records_the_corpus_schema_from_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, schema: str
) -> None:
    from scripts import build_v61_calibration_artifacts as builder

    profile_ids = tuple(f"{index:064x}" for index in range(1_130))
    corpus = SimpleNamespace(
        payload={"schema_version": schema},
        profile_ids=profile_ids,
        usable_profile_ids=profile_ids,
    )
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text("{}", encoding="utf-8")
    split_path = tmp_path / "split.json"
    split_path.write_text(
        json.dumps(
            {
                "seed": 6000,
                "train_profile_ids": list(profile_ids[:791]),
                "holdout_profile_ids": list(profile_ids[791:]),
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "bound.json"
    monkeypatch.setattr(builder, "load_canonical_corpus", lambda _path: corpus)

    assert builder._bind_split(
        SimpleNamespace(
            input=corpus_path,
            split_manifest=split_path,
            output=output_path,
        )
    ) == 0

    assert json.loads(output_path.read_text(encoding="utf-8"))["corpus_schema"] == schema

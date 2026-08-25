from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path

import pytest

from scripts import prepare_v61_replacement_holdout as tool

RELEASE_SHA = "a" * 40
SALT = b"replacement-test-salt-0123456789"
HISTORICAL = tuple(range(1, 2_365))
ORIGINAL = tuple(range(1, 1_131))
SCREENED = tuple(range(1_131, 1_141))
UNTOUCHED = tuple(range(1_141, 2_365))


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _inputs(tmp_path: Path) -> dict[str, Path | str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    historical_path = tmp_path / "historical.json"
    original_path = tmp_path / "original.json"
    screened_path = tmp_path / "screened.json"
    salt_path = tmp_path / "salt.bin"
    split_path = tmp_path / "split.json"
    _write(
        historical_path,
        {
            "schema_version": "v6-calibration-candidates-1.0.0",
            "summary": {"unique_candidate_account_ids": len(HISTORICAL)},
            "candidate_account_ids": list(HISTORICAL),
        },
    )
    _write(
        original_path,
        {"candidate_count": len(ORIGINAL), "candidate_account_ids": list(ORIGINAL)},
    )
    _write(
        screened_path,
        {
            "schema_version": "v61-replacement-candidates-1.0.0",
            "batch_index": 1,
            "candidate_count": len(SCREENED),
            "selection_policy": "unused-historical-candidates-sorted-by-profile-id",
            "candidate_account_ids": list(SCREENED),
        },
    )
    salt_path.write_bytes(SALT)
    _write(
        split_path,
        {
            "train_profile_count": 791,
            "holdout_profile_count": 339,
            "train_profile_ids": [f"profile-{index}" for index in range(791)],
            "holdout_profile_ids": [f"profile-{index}" for index in range(791, 1_130)],
        },
    )
    return {
        "historical": historical_path,
        "original": original_path,
        "screened": screened_path,
        "salt": salt_path,
        "split": split_path,
        "split_sha": hashlib.sha256(split_path.read_bytes()).hexdigest(),
    }


def _build_from_paths(paths: dict[str, Path | str]) -> dict[str, object]:
    return tool.build_precommit_manifest(
        historical_candidates=paths["historical"],  # type: ignore[arg-type]
        original_population=paths["original"],  # type: ignore[arg-type]
        screened_reserve=paths["screened"],  # type: ignore[arg-type]
        salt_path=paths["salt"],  # type: ignore[arg-type]
        current_split=paths["split"],  # type: ignore[arg-type]
        expected_current_split_sha256=paths["split_sha"],  # type: ignore[arg-type]
        release_sha=RELEASE_SHA,
    )


def _build(tmp_path: Path) -> dict[str, object]:
    return _build_from_paths(_inputs(tmp_path))


def test_happy_path_freezes_exact_reserve_and_collection_contract(tmp_path: Path) -> None:
    payload = _build(tmp_path)
    ordered = sorted(UNTOUCHED, key=tool.ordering_key)

    assert payload["candidate_count"] == 1_224
    assert payload["candidate_account_ids"] == ordered
    assert payload["candidate_order_sha256"] == tool._order_digest(ordered)
    assert payload["selection_protocol"]["target_holdout_profile_count"] == 339
    assert payload["selection_protocol"]["eligibility_rule"]["minimum_usable_matches"] == 30
    assert payload["collection_contract"] == {
        "summary_requests_per_candidate": 1,
        "planned_summary_requests": 1_224,
        "planned_detail_requests": 0,
        "planned_parse_requests": 0,
        "retry_limit": 0,
        "window_days": 365,
        "provider_limit": 10_000,
        "projection_version": "summary-projection-3.0.0",
        "raw_archive_required": True,
    }
    assert "generated_at" not in payload


def test_identical_inputs_are_byte_deterministic(tmp_path: Path) -> None:
    paths = _inputs(tmp_path)
    first = _build_from_paths(paths)
    second = _build_from_paths(paths)

    assert tool.serialize_manifest(first) == tool.serialize_manifest(second)
    assert first["candidate_order_sha256"] == second["candidate_order_sha256"]


@pytest.mark.parametrize("source", ["historical", "original", "screened"])
def test_duplicate_candidate_ids_are_rejected_without_deduplication(
    tmp_path: Path,
    source: str,
) -> None:
    paths = _inputs(tmp_path)
    path = paths[source]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["candidate_account_ids"].append(payload["candidate_account_ids"][0])
    _write(path, payload)

    with pytest.raises(ValueError, match="duplicate"):
        tool.load_candidate_ids(path, label=source)


@pytest.mark.parametrize("value", [True, 0, -1, "123", None])
def test_invalid_candidate_values_are_rejected(tmp_path: Path, value: object) -> None:
    path = tmp_path / "candidates.json"
    _write(path, {"candidate_account_ids": [value]})

    with pytest.raises(ValueError, match="invalid account ID"):
        tool.load_candidate_ids(path, label="test candidates")


def test_missing_source_fails_without_creating_output(tmp_path: Path) -> None:
    paths = _inputs(tmp_path)
    paths["historical"].unlink()  # type: ignore[union-attr]
    output = tmp_path / "manifest.json"

    with pytest.raises(ValueError, match="historical candidates file is missing"):
        _build_from_paths(paths)
    assert not output.exists()


@pytest.mark.parametrize(
    ("validator", "count"),
    [
        ("historical", 2_363),
        ("original", 1_129),
        ("screened", 9),
    ],
)
def test_population_count_mismatches_fail_closed(
    tmp_path: Path,
    validator: str,
    count: int,
) -> None:
    paths = _inputs(tmp_path)
    path = paths[validator]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["candidate_account_ids"] = payload["candidate_account_ids"][:count]
    if validator == "historical":
        payload["summary"]["unique_candidate_account_ids"] = count
    if validator == "original":
        payload["candidate_count"] = count
    if validator == "screened":
        payload["candidate_count"] = count
    _write(path, payload)

    with pytest.raises(ValueError, match="count"):
        {
            "historical": tool.validate_historical_candidates,
            "original": tool.validate_original_population,
            "screened": tool.validate_screened_reserve,
        }[validator](path)


@pytest.mark.parametrize("relationship", ["original-outside", "screened-outside", "exclusion-overlap"])
def test_exclusion_relationships_fail_closed(tmp_path: Path, relationship: str) -> None:
    paths = _inputs(tmp_path)
    if relationship == "original-outside":
        payload = json.loads(paths["original"].read_text(encoding="utf-8"))
        payload["candidate_account_ids"][0] = 9_999
        _write(paths["original"], payload)
        expected = "original population is outside"
    elif relationship == "screened-outside":
        payload = json.loads(paths["screened"].read_text(encoding="utf-8"))
        payload["candidate_account_ids"][0] = 9_999
        _write(paths["screened"], payload)
        expected = "screened reserve is outside"
    else:
        payload = json.loads(paths["screened"].read_text(encoding="utf-8"))
        payload["candidate_account_ids"][0] = 1
        _write(paths["screened"], payload)
        expected = "exclusions overlap"

    with pytest.raises(ValueError, match=expected):
        _build_from_paths(paths)


def test_current_split_leakage_and_sha_mismatch_fail_closed(tmp_path: Path) -> None:
    paths = _inputs(tmp_path)
    split = json.loads(paths["split"].read_text(encoding="utf-8"))
    split["train_profile_ids"][0] = tool._pseudonym(UNTOUCHED[0], SALT)
    _write(paths["split"], split)
    changed_sha = hashlib.sha256(paths["split"].read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="overlaps the current population"):
        tool.build_precommit_manifest(
            historical_candidates=paths["historical"],  # type: ignore[arg-type]
            original_population=paths["original"],  # type: ignore[arg-type]
            screened_reserve=paths["screened"],  # type: ignore[arg-type]
            salt_path=paths["salt"],  # type: ignore[arg-type]
            current_split=paths["split"],  # type: ignore[arg-type]
            expected_current_split_sha256=changed_sha,
            release_sha=RELEASE_SHA,
        )
    with pytest.raises(ValueError, match="SHA-256"):
        paths = _inputs(tmp_path / "sha")
        tool.build_precommit_manifest(
            historical_candidates=paths["historical"],  # type: ignore[arg-type]
            original_population=paths["original"],  # type: ignore[arg-type]
            screened_reserve=paths["screened"],  # type: ignore[arg-type]
            salt_path=paths["salt"],  # type: ignore[arg-type]
            current_split=paths["split"],  # type: ignore[arg-type]
            expected_current_split_sha256="0" * 64,
            release_sha=RELEASE_SHA,
        )


def test_split_counts_and_short_salt_fail_closed(tmp_path: Path) -> None:
    paths = _inputs(tmp_path)
    split = json.loads(paths["split"].read_text(encoding="utf-8"))
    split["train_profile_ids"] = split["train_profile_ids"][:-1]
    _write(paths["split"], split)
    with pytest.raises(ValueError, match="current split train_profile_ids count"):
        tool.build_precommit_manifest(
            historical_candidates=paths["historical"],  # type: ignore[arg-type]
            original_population=paths["original"],  # type: ignore[arg-type]
            screened_reserve=paths["screened"],  # type: ignore[arg-type]
            salt_path=paths["salt"],  # type: ignore[arg-type]
            current_split=paths["split"],  # type: ignore[arg-type]
            expected_current_split_sha256=hashlib.sha256(paths["split"].read_bytes()).hexdigest(),
            release_sha=RELEASE_SHA,
        )

    paths = _inputs(tmp_path / "salt")
    paths["salt"].write_bytes(b"short")  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="salt is too short"):
        _build_from_paths(paths)


@pytest.mark.parametrize("release_sha", ["a" * 39, "A" * 40, "g" * 40])
def test_release_sha_must_be_lowercase_full_hex(tmp_path: Path, release_sha: str) -> None:
    paths = _inputs(tmp_path)
    with pytest.raises(ValueError, match="release SHA"):
        tool.build_precommit_manifest(
            historical_candidates=paths["historical"],  # type: ignore[arg-type]
            original_population=paths["original"],  # type: ignore[arg-type]
            screened_reserve=paths["screened"],  # type: ignore[arg-type]
            salt_path=paths["salt"],  # type: ignore[arg-type]
            current_split=paths["split"],  # type: ignore[arg-type]
            expected_current_split_sha256=paths["split_sha"],  # type: ignore[arg-type]
            release_sha=release_sha,
        )


def test_write_once_permissions_and_different_content_rejection(tmp_path: Path) -> None:
    payload = _build(tmp_path / "inputs")
    output = tmp_path / "private" / "manifest.json"
    status, digest = tool.write_private_manifest(output, payload)
    original_bytes = output.read_bytes()

    assert status == "created"
    assert digest == hashlib.sha256(original_bytes).hexdigest()
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert stat.S_IMODE(output.parent.stat().st_mode) == 0o700

    assert tool.write_private_manifest(output, payload) == ("verified-existing", digest)
    changed = dict(payload)
    changed["release_sha"] = "b" * 40
    with pytest.raises(ValueError, match="differs"):
        tool.write_private_manifest(output, changed)
    assert output.read_bytes() == original_bytes


def test_cli_prints_only_aggregate_metadata_and_writes_private_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _inputs(tmp_path / "inputs")
    output = tmp_path / "manifest.json"
    rc = tool.main(
        [
            "--historical-candidates",
            str(paths["historical"]),
            "--original-population",
            str(paths["original"]),
            "--screened-reserve",
            str(paths["screened"]),
            "--salt",
            str(paths["salt"]),
            "--current-split",
            str(paths["split"]),
            "--expected-current-split-sha256",
            str(paths["split_sha"]),
            "--release-sha",
            RELEASE_SHA,
            "--output",
            str(output),
        ]
    )
    stdout = capsys.readouterr().out
    result = json.loads(stdout)

    assert rc == 0
    assert result["status"] == "created"
    assert result["candidate_count"] == 1_224
    assert result["planned_summary_requests"] == 1_224
    assert "account_id" not in stdout
    assert "candidate_account_ids" not in stdout
    assert stat.S_IMODE(output.stat().st_mode) == 0o600

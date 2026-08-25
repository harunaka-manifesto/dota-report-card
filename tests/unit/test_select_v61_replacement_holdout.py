from __future__ import annotations

import copy
import hashlib
import json
import re
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from app.ingestion.summary_history_contract import request_manifest
from app.player_analysis_v61.calibration_corpus import (
    CANONICAL_SCHEMA_VERSION,
    LEGACY_CANONICAL_SCHEMA_VERSION,
    validate_canonical_corpus,
)

from scripts import build_v61_calibration_artifacts as builder
from scripts import select_v61_replacement_holdout as selector
from scripts.prepare_v61_replacement_holdout import _order_digest
from tests.unit.test_v61_canonical_corpus import _canonical_profile


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _source() -> dict[str, Any]:
    return {
        "endpoint": "/players/{account_id}/matches",
        "request_count_per_profile": 1,
        "detail_requests": 0,
        "parse_requests": 0,
        "rank_or_mmr_used": False,
        "retry_limit": 0,
    }


def _historical_payload(profiles: list[dict[str, Any]], window_start: int) -> dict[str, Any]:
    return {
        "schema_version": LEGACY_CANONICAL_SCHEMA_VERSION,
        "generated_at": "2000-01-01T00:00:00+00:00",
        "request_manifest": request_manifest(),
        "source": _source(),
        "window": {
            "days": 365,
            "start_time": window_start,
            "end_time": window_start + 365 * 24 * 60 * 60,
        },
        "profile_count": len(profiles),
        "summary": {
            "profile_count": len(profiles),
            "eligible_profile_count": len(profiles),
            "eligible_match_count": 30 * len(profiles),
        },
        "raw_identifiers_present": False,
        "profiles": profiles,
    }


def _ineligible(profile: dict[str, Any]) -> dict[str, Any]:
    profile["status"] = "ineligible"
    profile["matches"].pop()
    profile["eligible_match_count"] = 29
    profile["eligibility_audit"] = {
        "excluded_match_count": 1,
        "exclusion_reasons": {"synthetic": 1},
        "duplicate_conflict_count": 0,
        "minimum_usable_matches": 30,
    }
    return profile


@pytest.fixture(scope="module")
def synthetic_inputs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("replacement-selection")
    historical_window_start = 1_700_000_000
    replacement_window_start = selector.REPLACEMENT_WINDOW["start_time"]
    historical_profiles = [
        _canonical_profile(f"{index + 1:064x}", historical_window_start)
        for index in range(selector.EXPECTED_POPULATION_COUNT)
    ]
    historical_path = root / "historical-corpus.json"
    historical_sha = _write_json(
        historical_path,
        _historical_payload(historical_profiles, historical_window_start),
    )
    train_ids = [profile["profile_id"] for profile in historical_profiles[: selector.EXPECTED_TRAIN_COUNT]]
    revealed_ids = [profile["profile_id"] for profile in historical_profiles[selector.EXPECTED_TRAIN_COUNT :]]
    split_path = root / "historical-split.json"
    split_sha = _write_json(
        split_path,
        {
            "version": "synthetic-current-split",
            "algorithm": "synthetic",
            "seed": selector.EXPECTED_SPLIT_SEED,
            "corpus_schema": LEGACY_CANONICAL_SCHEMA_VERSION,
            "corpus_sha256": historical_sha,
            "train_profile_count": selector.EXPECTED_TRAIN_COUNT,
            "holdout_profile_count": selector.EXPECTED_HOLDOUT_COUNT,
            "train_profile_ids": train_ids,
            "holdout_profile_ids": revealed_ids,
            "train_digest": selector.profile_digest(train_ids),
            "holdout_digest": selector.profile_digest(revealed_ids),
        },
    )
    candidate_ids = list(range(1, selector.EXPECTED_CANDIDATE_COUNT + 1))
    order_sha = _order_digest(candidate_ids)
    precommit_path = root / "precommit.json"
    precommit_sha = _write_json(
        precommit_path,
        {
            "schema_version": selector.PRECOMMIT_SCHEMA_VERSION,
            "release_sha": selector.COLLECTION_RELEASE_SHA,
            "candidate_count": selector.EXPECTED_CANDIDATE_COUNT,
            "candidate_order_digest_format": selector.ORDER_DIGEST_FORMAT,
            "candidate_order_sha256": order_sha,
            "candidate_account_ids": candidate_ids,
            "exclusions": {"current_population_overlap_count": 0},
        },
    )
    eligible_indices = set(range(338)) | set(range(1070, 1111))
    scan_profiles: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    for index in range(selector.EXPECTED_CANDIDATE_COUNT):
        profile = _canonical_profile(
            f"{index + 10_000:064x}",
            replacement_window_start,
        )
        if index not in eligible_indices:
            profile = _ineligible(profile)
        scan_profiles.append(profile)
        statuses.append(
            {
                "candidate_index": index,
                "profile_id": profile["profile_id"],
                "status": "success",
                "eligibility": profile["status"],
                "request_accounting": "network_attempt",
            }
        )
    scan_path = root / "replacement-scan.json"
    scan_sha = _write_json(
        scan_path,
        {
            "schema_version": selector.SCAN_SCHEMA_VERSION,
            "release_sha": selector.COLLECTION_RELEASE_SHA,
            "precommit_manifest_sha256": precommit_sha,
            "candidate_order_sha256": order_sha,
            "candidate_count": selector.EXPECTED_CANDIDATE_COUNT,
            "requested_candidate_count": selector.EXPECTED_CANDIDATE_COUNT,
            "window_start": replacement_window_start,
            "window_end": selector.REPLACEMENT_WINDOW["end_time"],
            "window_days": selector.REPLACEMENT_WINDOW["days"],
            "window": dict(selector.REPLACEMENT_WINDOW),
            "success_count": selector.EXPECTED_CANDIDATE_COUNT,
            "failure_count": 0,
            "indeterminate_count": 0,
            "eligible_count": selector.EXPECTED_SCAN_ELIGIBLE_COUNT,
            "ineligible_count": selector.EXPECTED_CANDIDATE_COUNT - selector.EXPECTED_SCAN_ELIGIBLE_COUNT,
            "request_accounting": {
                "summary_requests_per_candidate": 1,
                "planned_summary_requests": selector.EXPECTED_CANDIDATE_COUNT,
                "attempted_summary_requests": selector.EXPECTED_CANDIDATE_COUNT,
                "known_terminal_summary_requests": selector.EXPECTED_CANDIDATE_COUNT,
                "indeterminate_summary_requests": 0,
                "reused_archive_count": 0,
                "detail_requests": 0,
                "parse_requests": 0,
                "retry_limit": 0,
            },
            "detail_requests": 0,
            "parse_requests": 0,
            "rank_or_mmr_used": False,
            "raw_archive_required": True,
            "raw_identifiers_present": False,
            "candidate_statuses": statuses,
            "profiles": scan_profiles,
        },
    )
    return {
        "root": root,
        "historical_path": historical_path,
        "historical_sha": historical_sha,
        "split_path": split_path,
        "split_sha": split_sha,
        "precommit_path": precommit_path,
        "precommit_sha": precommit_sha,
        "scan_path": scan_path,
        "scan_sha": scan_sha,
        "order_sha": order_sha,
        "train_ids": train_ids,
        "revealed_ids": revealed_ids,
        "scan_profiles": scan_profiles,
        "eligible_indices": eligible_indices,
    }


def _args(inputs: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    values = {
        "precommit_manifest": inputs["precommit_path"],
        "replacement_scan": inputs["scan_path"],
        "current_corpus": inputs["historical_path"],
        "current_split": inputs["split_path"],
        "expected_current_corpus_sha256": inputs["historical_sha"],
        "expected_current_split_sha256": inputs["split_sha"],
        "expected_historical_corpus_sha256": inputs["historical_sha"],
        "expected_historical_split_sha256": inputs["split_sha"],
        "collection_release_sha": selector.COLLECTION_RELEASE_SHA,
        "schema_release_sha": selector.SCHEMA_RELEASE_SHA,
        "selection_release_sha": "3" * 40,
        "expected_precommit_sha256": inputs["precommit_sha"],
        "expected_replacement_scan_sha256": inputs["scan_sha"],
        "expected_candidate_order_sha256": inputs["order_sha"],
    }
    values.update(overrides)
    return values


def _build(inputs: dict[str, Any], **overrides: Any) -> selector.SelectionResult:
    return selector.build_selection(**_args(inputs, **overrides))


def _variant(inputs: dict[str, Any], name: str, payload: dict[str, Any], key: str) -> tuple[Path, str]:
    path = inputs["root"] / f"{name}.json"
    checksum = _write_json(path, payload)
    return path, checksum


def test_first_339_eligible_are_selected_deterministically(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    selected = result.raw_split["holdout_profile_ids"]
    expected = [synthetic_inputs["scan_profiles"][index]["profile_id"] for index in range(338)]
    expected.append(synthetic_inputs["scan_profiles"][1070]["profile_id"])
    assert selected == expected


def test_precommit_order_controls_selection(synthetic_inputs: dict[str, Any]) -> None:
    precommit = json.loads(synthetic_inputs["precommit_path"].read_text())
    precommit["candidate_account_ids"] = precommit["candidate_account_ids"][1:] + precommit["candidate_account_ids"][:1]
    precommit["candidate_order_sha256"] = _order_digest(precommit["candidate_account_ids"])
    precommit_path, precommit_sha = _variant(synthetic_inputs, "rotated-precommit", precommit, "precommit")
    scan = json.loads(synthetic_inputs["scan_path"].read_text())
    old_statuses = scan["candidate_statuses"]
    old_profiles = scan["profiles"]
    scan["candidate_statuses"] = [dict(old_statuses[(index + 1) % len(old_statuses)], candidate_index=index) for index in range(len(old_statuses))]
    scan["profiles"] = [old_profiles[(index + 1) % len(old_profiles)] for index in range(len(old_profiles))]
    scan["precommit_manifest_sha256"] = precommit_sha
    scan["candidate_order_sha256"] = precommit["candidate_order_sha256"]
    scan_path, scan_sha = _variant(synthetic_inputs, "rotated-scan", scan, "scan")
    rotated = _build(
        synthetic_inputs,
        precommit_manifest=precommit_path,
        replacement_scan=scan_path,
        expected_precommit_sha256=precommit_sha,
        expected_replacement_scan_sha256=scan_sha,
        expected_candidate_order_sha256=precommit["candidate_order_sha256"],
    )
    base = _build(synthetic_inputs)
    assert rotated.raw_split["holdout_profile_ids"] != base.raw_split["holdout_profile_ids"]


def test_selected_count_is_exact(synthetic_inputs: dict[str, Any]) -> None:
    assert len(_build(synthetic_inputs).raw_split["holdout_profile_ids"]) == 339


def test_selected_boundary_index_is_zero_based(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    assert result.evidence["selected_339th_candidate_index"] == 1070
    assert result.evidence["index_convention"] == "zero-based"


def test_ineligible_profiles_are_skipped(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    ineligible_ids = {
        profile["profile_id"]
        for index, profile in enumerate(synthetic_inputs["scan_profiles"])
        if index not in synthetic_inputs["eligible_indices"]
    }
    assert not ineligible_ids & set(result.raw_split["holdout_profile_ids"])


@pytest.mark.parametrize("status", ["failed", "indeterminate"])
def test_non_success_scan_status_blocks(synthetic_inputs: dict[str, Any], status: str) -> None:
    scan = json.loads(synthetic_inputs["scan_path"].read_text())
    scan["candidate_statuses"][0]["status"] = status
    path, checksum = _variant(synthetic_inputs, f"{status}-scan", scan, "scan")
    with pytest.raises(selector.SelectionError):
        _build(synthetic_inputs, replacement_scan=path, expected_replacement_scan_sha256=checksum)


def test_fewer_than_339_eligible_blocks(synthetic_inputs: dict[str, Any]) -> None:
    scan = json.loads(synthetic_inputs["scan_path"].read_text())
    index = 0
    scan["candidate_statuses"][index]["eligibility"] = "ineligible"
    scan["profiles"][index] = _ineligible(scan["profiles"][index])
    scan["eligible_count"] = 338
    scan["ineligible_count"] = 886
    path, checksum = _variant(synthetic_inputs, "short-scan", scan, "scan")
    with pytest.raises(selector.SelectionError):
        _build(
            synthetic_inputs,
            replacement_scan=path,
            expected_replacement_scan_sha256=checksum,
            expected_scan_eligible_count=338,
            expected_unused_eligible_count=0,
        )


def test_duplicate_scan_profile_blocks(synthetic_inputs: dict[str, Any]) -> None:
    scan = json.loads(synthetic_inputs["scan_path"].read_text())
    scan["profiles"][1]["profile_id"] = scan["profiles"][0]["profile_id"]
    path, checksum = _variant(synthetic_inputs, "duplicate-scan", scan, "scan")
    with pytest.raises(selector.SelectionError):
        _build(synthetic_inputs, replacement_scan=path, expected_replacement_scan_sha256=checksum)


def test_duplicate_precommit_candidate_blocks(synthetic_inputs: dict[str, Any]) -> None:
    precommit = json.loads(synthetic_inputs["precommit_path"].read_text())
    precommit["candidate_account_ids"][1] = precommit["candidate_account_ids"][0]
    path, checksum = _variant(synthetic_inputs, "duplicate-precommit", precommit, "precommit")
    with pytest.raises(selector.SelectionError):
        _build(synthetic_inputs, precommit_manifest=path, expected_precommit_sha256=checksum)


def test_precommit_sha_mismatch_blocks(synthetic_inputs: dict[str, Any]) -> None:
    with pytest.raises(selector.SelectionError):
        _build(synthetic_inputs, expected_precommit_sha256="0" * 64)


def test_scan_sha_mismatch_blocks(synthetic_inputs: dict[str, Any]) -> None:
    with pytest.raises(selector.SelectionError):
        _build(synthetic_inputs, expected_replacement_scan_sha256="0" * 64)


def test_candidate_order_sha_mismatch_blocks(synthetic_inputs: dict[str, Any]) -> None:
    with pytest.raises(selector.SelectionError):
        _build(synthetic_inputs, expected_candidate_order_sha256="0" * 64)


def test_historical_corpus_sha_mismatch_blocks(synthetic_inputs: dict[str, Any]) -> None:
    with pytest.raises(selector.SelectionError):
        _build(synthetic_inputs, expected_current_corpus_sha256="0" * 64)


def test_historical_split_sha_mismatch_blocks(synthetic_inputs: dict[str, Any]) -> None:
    with pytest.raises(selector.SelectionError):
        _build(synthetic_inputs, expected_current_split_sha256="0" * 64)


def test_historical_split_must_be_exact_791_339(synthetic_inputs: dict[str, Any]) -> None:
    split = json.loads(synthetic_inputs["split_path"].read_text())
    split["holdout_profile_ids"] = split["holdout_profile_ids"][:-1]
    path, checksum = _variant(synthetic_inputs, "short-historical-split", split, "split")
    with pytest.raises(selector.SelectionError):
        _build(synthetic_inputs, current_split=path, expected_current_split_sha256=checksum)


def test_historical_revealed_holdout_is_excluded(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    assert not set(result.raw_split["holdout_profile_ids"]) & set(synthetic_inputs["revealed_ids"])


def test_unused_eligible_reserve_is_excluded(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    unused = {
        synthetic_inputs["scan_profiles"][index]["profile_id"]
        for index in range(1071, 1111)
    }
    output_ids = {profile["profile_id"] for profile in result.corpus["profiles"]}
    assert not unused & output_ids


def test_replacement_has_no_historical_overlap(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    assert not set(result.raw_split["holdout_profile_ids"]) & set(synthetic_inputs["train_ids"] + synthetic_inputs["revealed_ids"])


def test_historical_profiles_inherit_v20_window(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    window = result.corpus["profiles"][0]["collection_window"]
    assert window["start_time"] == 1_700_000_000
    assert window["end_time"] - window["start_time"] == 365 * 24 * 60 * 60


def test_replacement_profiles_inherit_scan_window(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    assert result.corpus["profiles"][selector.EXPECTED_TRAIN_COUNT]["collection_window"] == selector.REPLACEMENT_WINDOW


def test_historical_profile_content_is_preserved(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    source = json.loads(synthetic_inputs["historical_path"].read_text())["profiles"][0]
    materialized = copy.deepcopy(result.corpus["profiles"][0])
    materialized.pop("collection_window")
    assert materialized == source


def test_replacement_profile_content_is_preserved(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    source = synthetic_inputs["scan_profiles"][0]
    materialized = copy.deepcopy(result.corpus["profiles"][selector.EXPECTED_TRAIN_COUNT])
    materialized.pop("collection_window")
    assert materialized == source


def test_materialized_corpus_is_v21_mixed_window(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    corpus = validate_canonical_corpus(result.corpus)
    diagnostics = corpus.aggregate_diagnostics()
    assert result.corpus["schema_version"] == CANONICAL_SCHEMA_VERSION
    assert "window" not in result.corpus
    assert diagnostics["window_mode"] == "per_profile_365_day"
    assert diagnostics["profile_window_count"] == 1130
    assert diagnostics["all_profile_windows_exact_365_days"] is True


def test_materialized_population_is_exactly_1130(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    assert result.corpus["profile_count"] == 1130
    assert len(result.corpus["profiles"]) == 1130


def test_materialized_population_is_entirely_usable(synthetic_inputs: dict[str, Any]) -> None:
    corpus = validate_canonical_corpus(_build(synthetic_inputs).corpus)
    assert len(corpus.usable_profile_ids) == 1130


def test_raw_split_uses_train_order_and_selection_order(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    assert result.raw_split["train_profile_ids"] == synthetic_inputs["train_ids"]
    assert result.raw_split["holdout_profile_ids"][0] == synthetic_inputs["scan_profiles"][0]["profile_id"]
    assert result.raw_split["selection_method"] == "precommitted_first_339_eligible"


def test_split_binder_accepts_generated_raw_split(synthetic_inputs: dict[str, Any], tmp_path: Path) -> None:
    result = _build(synthetic_inputs)
    corpus_path = tmp_path / "corpus.json"
    split_path = tmp_path / "raw-split.json"
    output_path = tmp_path / "bound-split.json"
    corpus_path.write_bytes(selector.serialize_manifest(result.corpus))
    split_path.write_bytes(selector.serialize_manifest(result.raw_split))
    assert builder._bind_split(SimpleNamespace(input=corpus_path, split_manifest=split_path, output=output_path)) == 0
    bound = json.loads(output_path.read_text())
    assert bound["corpus_schema"] == CANONICAL_SCHEMA_VERSION
    assert len(bound["train_profile_ids"]) == 791
    assert len(bound["holdout_profile_ids"]) == 339


def test_generated_split_has_zero_overlap(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    assert set(result.raw_split["train_profile_ids"]).isdisjoint(result.raw_split["holdout_profile_ids"])
    assert result.raw_split["overlap_count"] == 0


def test_rank_dimensions_are_rejected(synthetic_inputs: dict[str, Any]) -> None:
    scan = json.loads(synthetic_inputs["scan_path"].read_text())
    scan["profiles"][0]["rank_tier"] = 80
    path, checksum = _variant(synthetic_inputs, "rank-scan", scan, "scan")
    with pytest.raises(selector.SelectionError):
        _build(synthetic_inputs, replacement_scan=path, expected_replacement_scan_sha256=checksum)


def test_raw_account_identifiers_are_rejected(synthetic_inputs: dict[str, Any]) -> None:
    scan = json.loads(synthetic_inputs["scan_path"].read_text())
    scan["profiles"][0]["account_id"] = 123
    path, checksum = _variant(synthetic_inputs, "raw-id-scan", scan, "scan")
    with pytest.raises(selector.SelectionError):
        _build(synthetic_inputs, replacement_scan=path, expected_replacement_scan_sha256=checksum)


def test_selection_bytes_are_deterministic(synthetic_inputs: dict[str, Any]) -> None:
    first = _build(synthetic_inputs)
    second = _build(synthetic_inputs)
    assert selector.serialize_manifest(first.corpus) == selector.serialize_manifest(second.corpus)
    assert selector.serialize_manifest(first.raw_split) == selector.serialize_manifest(second.raw_split)
    assert selector.serialize_manifest(first.evidence) == selector.serialize_manifest(second.evidence)


def test_write_once_and_permissions(synthetic_inputs: dict[str, Any], tmp_path: Path) -> None:
    result = _build(synthetic_inputs)
    paths = {
        "output_corpus": tmp_path / "private" / "corpus.json",
        "output_split": tmp_path / "private" / "manifests" / "split.json",
        "output_selection_evidence": tmp_path / "private" / "evidence.json",
    }
    assert all(value == "created" for value in selector.write_selection_outputs(result, **paths).values())
    assert all(value == "verified-existing" for value in selector.write_selection_outputs(result, **paths).values())
    assert stat.S_IMODE((tmp_path / "private").stat().st_mode) == 0o700
    assert stat.S_IMODE((tmp_path / "private" / "manifests").stat().st_mode) == 0o700
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in paths.values())
    changed = copy.deepcopy(result.evidence)
    changed["selected_holdout_count"] = 338
    with pytest.raises(selector.SelectionError):
        selector.write_selection_outputs(
            selector.SelectionResult(
                result.corpus,
                result.raw_split,
                changed,
                result.corpus_sha256,
                result.raw_split_sha256,
                result.bound_split_sha256,
            ),
            **paths,
        )


def test_stdout_contains_no_profile_or_match_ids(
    synthetic_inputs: dict[str, Any],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _build(synthetic_inputs)
    monkeypatch.setattr(selector, "EXPECTED_PRECOMMIT_SHA256", synthetic_inputs["precommit_sha"])
    monkeypatch.setattr(selector, "EXPECTED_REPLACEMENT_SCAN_SHA256", synthetic_inputs["scan_sha"])
    monkeypatch.setattr(selector, "EXPECTED_CANDIDATE_ORDER_SHA256", synthetic_inputs["order_sha"])
    monkeypatch.setattr(selector, "EXPECTED_HISTORICAL_CORPUS_SHA256", synthetic_inputs["historical_sha"])
    monkeypatch.setattr(selector, "EXPECTED_HISTORICAL_SPLIT_SHA256", synthetic_inputs["split_sha"])
    args = [
        "--precommit-manifest", str(synthetic_inputs["precommit_path"]),
        "--replacement-scan", str(synthetic_inputs["scan_path"]),
        "--current-corpus", str(synthetic_inputs["historical_path"]),
        "--current-split", str(synthetic_inputs["split_path"]),
        "--expected-current-corpus-sha256", synthetic_inputs["historical_sha"],
        "--expected-current-split-sha256", synthetic_inputs["split_sha"],
        "--collection-release-sha", selector.COLLECTION_RELEASE_SHA,
        "--schema-release-sha", selector.SCHEMA_RELEASE_SHA,
        "--selection-release-sha", "3" * 40,
        "--output-corpus", str(tmp_path / "corpus.json"),
        "--output-split", str(tmp_path / "split.json"),
        "--output-selection-evidence", str(tmp_path / "evidence.json"),
    ]
    assert selector.main(args) == 0
    stdout = capsys.readouterr().out
    assert result.corpus["profiles"][0]["profile_id"] not in stdout
    assert str(result.corpus["profiles"][0]["matches"][0]["match_id"]) not in stdout
    assert "account_id" not in stdout


def test_selector_has_no_network_execution_path() -> None:
    source = Path(selector.__file__).read_text(encoding="utf-8")
    assert "OpenDota" not in source
    assert not re.search(r"(?:^|\n)\s*(?:import|from)\s+(?:httpx|requests|aiohttp|socket)", source)
    assert "urlopen" not in source


def test_evidence_is_aggregate_only(synthetic_inputs: dict[str, Any]) -> None:
    result = _build(synthetic_inputs)
    encoded = selector.serialize_manifest(result.evidence).decode()
    assert "profile_id" not in encoded
    assert "match_id" not in encoded
    assert "account_id" not in encoded

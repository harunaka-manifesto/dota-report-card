from __future__ import annotations

import json
from pathlib import Path

from app.stratz.queries import GET_PARSED_ACQUISITION_BATCH, get_operation

from legacy.scripts.stratz_v7_acquisition_freeze import (
    EXPECTED_FRAME_COUNT,
    PARSED_SUBSET_COUNTS,
    SAMPLE_SIZE,
    SCHEMA_VERSION,
    SPLIT_COUNTS,
    FrameRecord,
    SourceFrame,
    build_public_summary,
    build_split_manifest,
    calculate_economics,
    load_source_frame,
    max_proportion_se,
    pseudonymize_account,
    validate_pack_registry,
    verify_no_split_overlap,
)


def _small_frame() -> SourceFrame:
    records = tuple(
        FrameRecord(account_id=400_000_000 + index, source_position=index)
        for index in range(10)
    )
    return SourceFrame(
        path=Path("fixture-frame.json"),
        digest="frame-digest",
        schema_version="fixture-frame-1.0.0",
        frame_count=len(records),
        positive_public_account_count=len(records),
        records=records,
    )


def _small_counts() -> tuple[dict[str, int], dict[str, int]]:
    split_counts = {
        "DISCOVERY": 4,
        "CANDIDATE_TEST": 3,
        "CALIBRATION_RESERVED": 2,
        "SEALED_VALIDATION": 1,
    }
    parsed_counts = {
        "DISCOVERY": 1,
        "CANDIDATE_TEST": 1,
        "CALIBRATION_RESERVED": 0,
        "SEALED_VALIDATION": 0,
    }
    return split_counts, parsed_counts


def _write_synthetic_source_frame(path: Path) -> Path:
    target = path / "fixed-frame-manifest.json"
    target.write_text(
        json.dumps(
            {
                "adaptive_top_up": False,
                "positive_public_account_count": EXPECTED_FRAME_COUNT,
                "schema_version": "fixture-frame-1.0.0",
                "selection": "12 descending /publicMatches pages plus HMAC rank",
                "ranked_frame": [
                    {"account_id": 1_000_000_000 + index, "position": index}
                    for index in range(EXPECTED_FRAME_COUNT)
                ],
            }
        ),
        encoding="utf-8",
    )
    return target


def test_fixed_source_frame_validates_without_exposing_accounts(tmp_path: Path) -> None:
    frame = load_source_frame(_write_synthetic_source_frame(tmp_path))
    assert frame.frame_count == EXPECTED_FRAME_COUNT
    assert frame.positive_public_account_count == EXPECTED_FRAME_COUNT
    summary = frame.public_summary()
    encoded = json.dumps(summary)
    assert str(frame.records[0].account_id) not in encoded


def test_hmac_manifest_is_deterministic_and_pseudonymous() -> None:
    frame = _small_frame()
    split_counts, parsed_counts = _small_counts()
    salt = b"v7-acquisition-test-salt-00000000"[:32]
    first = build_split_manifest(
        frame,
        salt,
        sample_size=10,
        split_counts=split_counts,
        parsed_subset_counts=parsed_counts,
    )
    second = build_split_manifest(
        frame,
        salt,
        sample_size=10,
        split_counts=split_counts,
        parsed_subset_counts=parsed_counts,
    )
    assert first == second
    assert first["salt_sha256"] == __import__("hashlib").sha256(salt).hexdigest()
    encoded = json.dumps(first, sort_keys=True)
    assert "account_id" not in encoded
    assert all("v7p_" in member["pseudonym"] for member in first["members"])
    assert pseudonymize_account(400_000_000, salt) == pseudonymize_account(400_000_000, salt)


def test_split_manifest_has_no_overlap_and_fixed_parsed_subset() -> None:
    split_counts, parsed_counts = _small_counts()
    manifest = build_split_manifest(
        _small_frame(),
        b"v7-acquisition-test-salt-00000000"[:32],
        sample_size=10,
        split_counts=split_counts,
        parsed_subset_counts=parsed_counts,
    )
    check = verify_no_split_overlap(manifest)
    assert check["passed"] is True
    assert check["overlap_count"] == 0
    assert check["split_counts"] == split_counts
    assert check["parsed_subset_counts"] == parsed_counts


def test_public_summary_is_aggregate_only_and_has_no_raw_ids() -> None:
    split_counts, parsed_counts = _small_counts()
    frame = _small_frame()
    manifest = build_split_manifest(
        frame,
        b"v7-acquisition-test-salt-00000000"[:32],
        sample_size=10,
        split_counts=split_counts,
        parsed_subset_counts=parsed_counts,
    )
    summary = build_public_summary(
        frame,
        manifest,
        split_manifest_digest="split-digest",
        corpus_plan_digest="plan-digest",
    )
    encoded = json.dumps(summary, sort_keys=True)
    assert all(str(record.account_id) not in encoded for record in frame.records)
    assert "members" not in summary
    assert summary["network_calls"] == {"stratz": 0, "opendota": 0}


def test_operation_digests_and_field_packs_are_frozen_and_safe() -> None:
    registry = validate_pack_registry()
    assert registry["passed"] is True
    assert len(registry["packs"]) == 3
    parsed_operation = get_operation(GET_PARSED_ACQUISITION_BATCH.name)
    assert all(
        pack["operation_sha256"] == get_operation(pack["operation"]).document_sha256
        for pack in registry["packs"]
    )
    assert parsed_operation.document_sha256 == registry["packs"][1]["operation_sha256"]
    forbidden = ("rank", "mmr", "chat", "playback", "rolebasic", "behavior", "imp")
    assert not any(token in parsed_operation.document.lower() for token in forbidden)


def test_batch_economics_uses_safe_batch_eight_and_daily_reserve() -> None:
    economics = calculate_economics()
    assert economics["sample_size"] == SAMPLE_SIZE
    assert economics["planning_scenario"]["history_rows_per_player_year"] == 597
    assert economics["planning_scenario"]["parsed_batch_size"] == 8
    assert economics["calls"]["history_pages_per_account"] == 6
    assert economics["calls"]["history_calls"] == 7_200
    assert economics["calls"]["parsed_batches_per_account_upper_bound"] == 37
    assert economics["calls"]["parsed_calls"] == 9_472
    assert economics["calls"]["total_planned_calls"] == 16_672
    assert economics["daily_schedule"]["DAY_1"]["planned_calls"] == 7_200
    assert economics["daily_schedule"]["DAY_1"]["planned_calls"] < 9_000
    assert economics["daily_schedule"]["DAY_2"]["planned_calls"] == 4_736
    assert economics["daily_schedule"]["DAY_3"]["planned_calls"] == 4_736
    assert economics["wall_clock"]["day_1_hours_at_hour_ceiling"] == 7.2
    assert economics["wall_clock"]["day_2_hours_at_hour_ceiling"] == 4.736
    assert economics["wall_clock"]["day_3_hours_at_hour_ceiling"] == 4.736
    assert economics["context_opportunities"]["history_rows"] == 716_400
    assert economics["context_opportunities"]["history_structural_match_rows"] == 351_600
    assert economics["bytes"]["history_raw_bytes_proxy"] == 744_775_200
    assert economics["bytes"]["combined_raw_bytes_upper_bound"] == 1_010_928_928
    parsed_se = max_proportion_se(128, EXPECTED_FRAME_COUNT)
    assert economics["parsed_candidate_test_n"] == 128
    assert economics["parsed_candidate_test_max_standard_error"] == parsed_se
    assert economics["parsed_candidate_test_max_95_percent_margin"] == 1.96 * parsed_se
    assert economics["quotas"]["provider_observed"] == {
        "second": 8,
        "minute": 150,
        "hour": 1_500,
        "day": 15_000,
    }
    assert economics["quotas"]["orchestration_ceiling"] == {
        "second": 5,
        "minute": 100,
        "hour": 1_000,
        "day": 10_000,
    }
    assert tuple(PARSED_SUBSET_COUNTS) == tuple(SPLIT_COUNTS)
    assert economics["max_reach_95_percent_margin"] < 0.025
    assert SCHEMA_VERSION == "stratz-v7-acquisition-freeze-1.0.0"

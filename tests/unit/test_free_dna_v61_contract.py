from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.analysis.service import AnalysisService
from app.analysis.source import MappingSource
from app.api.report_schemas import validate_free_dna_report
from app.core.config import Settings
from app.ingestion.summary_history_contract import (
    SUMMARY_HISTORY_PROJECTION,
    history_completeness,
    normalize_canonical_summary_history,
)
from app.player_analysis_v6.artifacts import ArtifactValidationError
from app.player_analysis_v61.calibration_corpus import normalize_calibration_history
from app.player_analysis_v61.portfolio_shape import chronological_thirds
from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_CATALOG
from app.player_analysis_v61.supporting_signals import SUPPORTING_SIGNAL_CATALOG
from app.storage.repository import InMemoryRepository

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "v6"


def _rows(count: int = 90) -> list[dict[str, object]]:
    window_end = int(datetime.now(UTC).timestamp())
    return [
        {
            "match_id": 961_000_000 + index,
            "start_time": window_end - index * 10_800,
            "duration": 1_800 + index % 8 * 60,
            "hero_id": 1 + index % 12,
            "player_slot": 0,
            "radiant_win": index % 2 == 0,
            "game_mode": 1,
            "lobby_type": 0,
            "kills": 4 + index % 9,
            "deaths": 2 + index % 6,
            "assists": 5 + index % 11,
            "leaver_status": 0,
            "party_size": None,
            "version": None,
            "hero_variant": None,
            "leagueid": None,
            "cluster": 111,
            "lane": None,
            "lane_role": None,
            "is_roaming": None,
        }
        for index in range(count)
    ]


def _generate() -> tuple[dict[str, object], MappingSource]:
    source = MappingSource(
        player={"profile": {"account_id": 42, "personaname": "V6.1 fixture"}},
        matches=_rows(),
        details={},
    )
    repository = InMemoryRepository()
    service = AnalysisService(
        source,
        repository=repository,
        settings=Settings(
            free_dna_v61_enabled=True,
            free_dna_v61_baseline_artifact_path=_FIXTURES / "context-baseline-3.0.0.fixture.json",
            free_dna_v61_threshold_artifact_path=_FIXTURES / "metric-thresholds-6.1.0.fixture.json",
        ),
    )
    job, _ = asyncio.run(service.create_analysis("42", enqueue=False))
    asyncio.run(service.run_job(job))
    assert job.status == "completed", job.failure_detail
    report = repository.get_report(job.report_id or "")
    assert report is not None
    return report, source


def test_v61_generates_new_immutable_contract_with_old_ontology() -> None:
    report, source = _generate()

    assert report["schema_version"] == "free-dna-report-6.1.0"
    assert len(report["elements"]) == 7
    assert len(report["findings"]) == 5
    assert sum(bool(item["published"]) for item in report["findings"]) <= 3
    assert len(report["story"]["ordered_beats"]) == 9
    assert report["reproducibility"]["history_contract"]["request_count"] == 1
    assert report["reproducibility"]["history_contract"]["rank_or_mmr_used"] is False
    assert report["methodology"]["rank_or_mmr_used"] is False
    assert source.requests.count(("summary_history_once", 42)) == 1
    assert not any(request[0] == "match" for request in source.requests)
    validate_free_dna_report(report)


def test_v61_rejects_v60_only_artifacts() -> None:
    with pytest.raises(ArtifactValidationError, match="V6.1 context baseline version"):
        AnalysisService(
            MappingSource(player={}, matches=[], details={}),
            settings=Settings(
                free_dna_v61_enabled=True,
                free_dna_v61_baseline_artifact_path=_FIXTURES / "context-baseline-2.0.0.fixture.json",
                free_dna_v61_threshold_artifact_path=_FIXTURES / "metric-thresholds-6.0.0.fixture.json",
            ),
        )


def test_v60_and_v61_flags_are_mutually_exclusive() -> None:
    with pytest.raises(ArtifactValidationError, match="mutually exclusive"):
        AnalysisService(
            MappingSource(player={}, matches=[], details={}),
            settings=Settings(free_dna_v6_enabled=True, free_dna_v61_enabled=True),
        )


def test_runtime_and_calibration_use_identical_canonical_normalization() -> None:
    rows = _rows()
    runtime = normalize_canonical_summary_history(rows, 42)
    calibration = normalize_calibration_history(rows, 42)

    assert calibration["normalized_payload_sha256"] == runtime.audit.normalized_payload_sha256
    assert calibration["eligibility_audit"]["eligible_count"] == runtime.audit.eligible_count
    assert calibration["coverage"]["optional"] == runtime.audit.optional_field_coverage


def test_canonical_projection_excludes_rank_and_mmr() -> None:
    assert "average_rank" not in SUMMARY_HISTORY_PROJECTION
    assert "rank_tier" not in SUMMARY_HISTORY_PROJECTION
    assert "mmr" not in SUMMARY_HISTORY_PROJECTION


def test_canonical_normalization_drops_unrequested_rank_fields_before_hashing() -> None:
    row = _rows(1)[0]
    with_rank = {**row, "rank_tier": 80, "skill": 3, "account_id": 42}

    canonical = normalize_canonical_summary_history([with_rank], 42)
    without_rank = normalize_canonical_summary_history([row], 42)

    assert canonical.audit.raw_payload_sha256 == without_rank.audit.raw_payload_sha256
    assert canonical.normalization.matches[0].skill_bracket is None
    assert canonical.audit.rank_or_mmr_used is False


def test_provider_ceiling_is_explicitly_possibly_truncated() -> None:
    assert history_completeness(9_999, provider_limit=10_000) == "complete"
    assert history_completeness(10_000, provider_limit=10_000) == "possibly_truncated"
    assert history_completeness(10_001, provider_limit=10_000) == "possibly_truncated"


def test_research_and_semantic_registries_are_finite_and_complete() -> None:
    assert len(SUPPORTING_SIGNAL_CATALOG) == 128
    assert len({item.key for item in SUPPORTING_SIGNAL_CATALOG}) == 128
    assert {item.family_key for item in SEMANTIC_OUTCOME_CATALOG} == {
        "pool_shape",
        "transfer",
        "post_loss_response",
        "combat_expression",
        "session_drift",
    }
    assert all(
        item.public_exposure == "never"
        for item in SUPPORTING_SIGNAL_CATALOG
        if item.classification in {"RESEARCH_ONLY", "REJECTED"}
    )


def test_unpublished_v61_families_cannot_leak_branch_claims_to_story_or_deep() -> None:
    report, _ = _generate()
    unpublished = [finding for finding in report["findings"] if not finding["published"]]

    assert unpublished
    assert all(finding["semantic_outcome_key"] is None for finding in unpublished)
    assert all(finding["claim_contract"] is None for finding in unpublished)
    published_families = {
        finding["family"] for finding in report["findings"] if finding["published"]
    }
    assert all(
        question["finding_family"] in published_families
        for question in report["diagnostic_questions"]
    )
    for page in report["pages"]:
        observed = page.get("observed") or {}
        finding = observed.get("finding") if isinstance(observed, dict) else None
        assert finding is None or finding.get("published") is True


@pytest.mark.parametrize("count", [30, 31, 32, 33])
def test_chronological_timeline_has_exactly_three_non_overlapping_parts(count: int) -> None:
    rows = _rows(count)
    thirds = chronological_thirds(rows)

    assert len(thirds) == 3
    assert sum(map(len, thirds)) == count
    assert len({id(row) for part in thirds for row in part}) == count

from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
from app.player_analysis_v6.constants import FINDING_FAMILY_KEYS
from app.player_analysis_v61.calibration_corpus import normalize_calibration_history
from app.player_analysis_v61.portfolio_shape import chronological_thirds
from app.player_analysis_v61.semantic_outcomes import (
    SEMANTIC_OUTCOME_CATALOG,
    SEMANTIC_OUTCOME_REGISTRY,
)
from app.player_analysis_v61.story_selector import select_story_matches
from app.player_analysis_v61.supporting_signals import SUPPORTING_SIGNAL_CATALOG
from app.reports import dna_assembly_v61 as dna_assembly_v61_module
from app.storage.repository import InMemoryRepository

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "v6"
_ANALYTICAL_SOURCE_SHA = "f85e88a277ffb365e76dd6eeac6f5009c7bd0165"


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


def _generate(
    account_id: int = 42,
    *,
    settings: Settings | None = None,
    rows: list[dict[str, object]] | None = None,
) -> tuple[dict[str, object], MappingSource]:
    source = MappingSource(
        player={"profile": {"account_id": account_id, "personaname": "V6.1 fixture"}},
        matches=rows if rows is not None else _rows(),
        details={},
    )
    repository = InMemoryRepository()
    service = AnalysisService(
        source,
        repository=repository,
        settings=settings
        or Settings(
            free_dna_v61_enabled=True,
            free_dna_v61_baseline_artifact_path=_FIXTURES / "context-baseline-3.0.0.fixture.json",
            free_dna_v61_threshold_artifact_path=_FIXTURES / "metric-thresholds-6.1.0.fixture.json",
        ),
    )
    job, _ = asyncio.run(service.create_analysis(str(account_id), enqueue=False))
    asyncio.run(service.run_job(job))
    assert job.status == "completed", job.failure_detail
    report = repository.get_report(job.report_id or "")
    assert report is not None
    return report, source


def test_source_binding_metadata_does_not_change_v61_output() -> None:
    fixture_settings = Settings(
        free_dna_v61_enabled=True,
        free_dna_v61_baseline_artifact_path=_FIXTURES / "context-baseline-3.0.0.fixture.json",
        free_dna_v61_threshold_artifact_path=_FIXTURES / "metric-thresholds-6.1.0.fixture.json",
    )
    deployed_settings = replace(
        fixture_settings,
        release_commit_sha="a" * 40,
        free_dna_v61_analytical_source_sha=_ANALYTICAL_SOURCE_SHA,
    )
    rows = _rows()
    before, _ = _generate(settings=fixture_settings, rows=rows)
    after, _ = _generate(settings=deployed_settings, rows=rows)

    for key in ("elements", "findings", "methodology"):
        assert before[key] == after[key]
    assert {
        key: value
        for key, value in before["reproducibility"].items()
        if key != "generated_at"
    } == {
        key: value
        for key, value in after["reproducibility"].items()
        if key != "generated_at"
    }


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


def test_v61_publication_cap_keeps_transfer_and_post_loss_before_later_families(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_assemble = dna_assembly_v61_module.assemble_free_dna_report_v6

    def all_candidates(*args: Any, **kwargs: Any) -> dict[str, Any]:
        report = original_assemble(*args, **kwargs)
        for finding in report["findings"]:
            finding["published"] = True
        return report

    def all_qualified(
        family_p: dict[str, float],
        branch_p: dict[str, dict[str, float]],
    ) -> dict[str, dict[str, object]]:
        result: dict[str, dict[str, object]] = {}
        for family in FINDING_FAMILY_KEYS:
            branches = dict(branch_p.get(family, {}))
            for key, definition in SEMANTIC_OUTCOME_REGISTRY.items():
                if definition.family_key == family:
                    branches.setdefault(key, 0.0)
            result[family] = {
                "raw_p_value": family_p.get(family, 0.0),
                "adjusted_q_value": 0.0,
                "qualified": True,
                "branches": {
                    key: {
                        "raw_p_value": value,
                        "adjusted_q_value": 0.0,
                        "qualified": True,
                    }
                    for key, value in branches.items()
                },
            }
        return result

    monkeypatch.setattr(dna_assembly_v61_module, "assemble_free_dna_report_v6", all_candidates)
    monkeypatch.setattr(dna_assembly_v61_module, "hierarchical_qualification", all_qualified)

    report, _ = _generate()

    assert tuple(item["family"] for item in report["findings"]) == FINDING_FAMILY_KEYS
    assert [
        item["family"] for item in report["findings"] if item["published"]
    ] == list(FINDING_FAMILY_KEYS[:3])


def test_story_population_adds_captains_mode_without_widening_inferential_rows() -> None:
    rows = _rows(30)
    rows.extend(
        {
            **row,
            "match_id": 962_000_000 + index,
            "game_mode": 2,
        }
        for index, row in enumerate(_rows(10))
    )

    report, source = _generate(rows=rows)

    assert report["metadata"]["processed_matches"] == 40
    assert report["metadata"]["eligible_matches"] == 30
    story = report["story_payload"]
    assert story["universe"]["match_count"] == 40
    assert story["universe"]["mode_counts"] == {
        "unranked_all_pick": 30,
        "ranked_all_pick": 0,
        "unranked_captains_mode": 10,
        "ranked_captains_mode": 0,
    }
    assert story["provenance"]["physical_history_requests"] == 1
    assert story["provenance"]["detail_requests"] == 0
    assert story["provenance"]["parse_requests"] == 0
    assert source.requests == [("player", 42), ("summary_history_once", 42)]
    validate_free_dna_report(report)


def test_story_activation_omits_cross_product_rows_and_story_versions_below_thirty() -> None:
    rows = _rows(30)
    for row in rows[25:]:
        row["lobby_type"] = 7

    report, _source = _generate(rows=rows)

    assert report["metadata"]["eligible_matches"] == 30
    assert "story_payload" not in report
    assert all(
        key not in report["versions"]
        for key in (
            "story_payload",
            "story_rules",
            "story_copy",
            "game_mode_map",
            "hero_taxonomy",
            "hero_metadata",
            "archetype_contract",
        )
    )
    validate_free_dna_report(report)


def test_story_extension_does_not_change_ap_only_legacy_surfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = _rows()
    original_selector = select_story_matches

    def no_story_selection(matches: Any) -> Any:
        selection = original_selector(matches)
        return replace(selection, matches=selection.matches[:29])

    monkeypatch.setattr("app.analysis.service.select_story_matches", no_story_selection)
    without_story, _ = _generate(rows=rows)
    monkeypatch.undo()
    with_story, _ = _generate(rows=rows)

    def legacy_surface(report: dict[str, object]) -> dict[str, object]:
        value = deepcopy(report)
        value.pop("report_id", None)
        value.pop("story_payload", None)
        versions = value.get("versions")
        if isinstance(versions, dict):
            for key in (
                "story_payload",
                "story_rules",
                "story_copy",
                "game_mode_map",
                "hero_taxonomy",
                "hero_metadata",
                "archetype_contract",
                "analysis_version_fingerprint",
            ):
                versions.pop(key, None)
        metadata = value.get("metadata")
        if isinstance(metadata, dict):
            metadata.pop("created_at", None)
            metadata.pop("expires_at", None)
        reproducibility = value.get("reproducibility")
        if isinstance(reproducibility, dict):
            reproducibility.pop("generated_at", None)
        return value

    assert legacy_surface(without_story) == legacy_surface(with_story)


def test_known_production_regression_player_completes_v61_assembly_and_persistence() -> None:
    report, source = _generate(193875165)

    assert report["schema_version"] == "free-dna-report-6.1.0"
    assert report["reproducibility"]["history_contract"]["request_count"] == 1
    assert source.requests == [("player", 193875165), ("summary_history_once", 193875165)]
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

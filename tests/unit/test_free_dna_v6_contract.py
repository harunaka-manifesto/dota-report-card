from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.analysis.service import AnalysisService
from app.analysis.source import MappingSource
from app.api.report_schemas import validate_free_dna_report
from app.core.config import Settings
from app.player_analysis_v6.artifacts import ArtifactValidationError
from app.storage.repository import InMemoryRepository

_WINDOW_END = int(datetime.now(UTC).timestamp())
_V6_FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "v6"


def _summary(index: int) -> dict[str, int | bool]:
    return {
        "match_id": 906_000_000 + index,
        "start_time": _WINDOW_END - index * 7_200,
        "duration": 1_800 + index % 8 * 60,
        "hero_id": 25 + index % 5,
        "player_slot": 0,
        "radiant_win": index % 2 == 0,
        "game_mode": 1,
        "lobby_type": 0,
        "leaver_status": 0,
        "kills": 7 + index % 5,
        "deaths": 3 + index % 4,
        "assists": 8 + index % 7,
        "lane_role": 1 + index % 3,
    }


def _report(count: int) -> dict[str, object]:
    source = MappingSource(
        player={"profile": {"account_id": 42, "personaname": "V6 fixture"}},
        matches=[_summary(index) for index in range(count)],
        details={},
    )
    repository = InMemoryRepository()
    service = AnalysisService(
        source,
        repository=repository,
        settings=Settings(
            free_dna_v6_enabled=True,
            free_dna_v6_baseline_artifact_path=_V6_FIXTURES / "context-baseline-2.0.0.fixture.json",
            free_dna_v6_threshold_artifact_path=_V6_FIXTURES / "metric-thresholds-6.0.0.fixture.json",
        ),
    )
    job, _ = asyncio.run(service.create_analysis("42", enqueue=False))
    asyncio.run(service.run_job(job))
    assert job.status == "completed", job.failure_detail
    report = repository.get_report(job.report_id or "")
    assert report is not None
    return report


def test_flagged_v6_report_has_strict_summary_only_contract() -> None:
    report = _report(65)

    assert report["schema_version"] == "free-dna-report-6.0.0"
    assert len(report["elements"]) == 7
    assert len(report["findings"]) == 5
    assert sum(item["published"] for item in report["findings"]) <= 3
    assert len(report["story"]["ordered_beats"]) == 9
    assert report["story"]["ordered_beats"] == [item["id"] for item in report["pages"]]
    assert report["cost"]["history_requests"] == 1
    assert report["cost"]["detail_requests"] == 0
    assert report["cost"]["parse_requests"] == 0
    assert report["methodology"]["weighting"] == "equal"
    validate_free_dna_report(report)


def test_limited_v6_report_never_publishes_finding_recommendations() -> None:
    report = _report(35)

    assert report["metadata"]["history_tier"] == "limited"
    assert all(
        item["claim_contract"]["recommendation"] is None for item in report["findings"]
    )
    validate_free_dna_report(report)


def test_disabled_v6_constructs_without_artifacts() -> None:
    AnalysisService(MappingSource(player={}, matches=[], details={}), settings=Settings())


@pytest.mark.parametrize(
    ("baseline", "thresholds", "message"),
    [
        (None, _V6_FIXTURES / "metric-thresholds-6.0.0.fixture.json", "explicit validated"),
        (_V6_FIXTURES / "context-baseline-2.0.0.fixture.json", None, "explicit validated"),
        (_V6_FIXTURES / "missing.json", _V6_FIXTURES / "metric-thresholds-6.0.0.fixture.json", "missing"),
    ],
)
def test_enabled_v6_fails_closed_for_missing_artifacts(
    baseline: Path | None,
    thresholds: Path | None,
    message: str,
) -> None:
    with pytest.raises(ArtifactValidationError, match=message):
        AnalysisService(
            MappingSource(player={}, matches=[], details={}),
            settings=Settings(
                free_dna_v6_enabled=True,
                free_dna_v6_baseline_artifact_path=baseline,
                free_dna_v6_threshold_artifact_path=thresholds,
            ),
        )


def test_enabled_v6_rejects_mismatched_model_version() -> None:
    with pytest.raises(ArtifactValidationError, match="MODEL_VERSION"):
        AnalysisService(
            MappingSource(player={}, matches=[], details={}),
            settings=Settings(
                free_dna_v6_enabled=True,
                free_dna_v6_model_version="free-dna-model-6.0.1",
                free_dna_v6_baseline_artifact_path=_V6_FIXTURES / "context-baseline-2.0.0.fixture.json",
                free_dna_v6_threshold_artifact_path=_V6_FIXTURES / "metric-thresholds-6.0.0.fixture.json",
            ),
        )


def test_compose_uses_identical_unlimited_v6_configuration_for_api_and_worker() -> None:
    compose = (Path(__file__).resolve().parents[2] / "infra" / "compose.yaml").read_text(encoding="utf-8")
    assert "FREE_HISTORY_LIMIT" not in compose
    assert compose.count("/app/services/api/artifacts/free_dna_v6/6.0.0/context-baseline-2.0.0.json") == 2
    assert compose.count("/app/services/api/artifacts/free_dna_v6/6.0.0/metric-thresholds-6.0.0.json") == 2

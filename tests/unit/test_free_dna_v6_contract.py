from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.analysis.service import AnalysisService
from app.analysis.source import MappingSource
from app.api.report_schemas import validate_free_dna_report
from app.core.config import Settings
from app.storage.repository import InMemoryRepository

_WINDOW_END = int(datetime.now(UTC).timestamp())


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
        settings=Settings(free_dna_v6_enabled=True),
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

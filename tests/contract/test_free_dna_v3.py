from __future__ import annotations

import asyncio

from app.analysis.service import AnalysisService
from app.analysis.source import MappingSource
from app.api.report_schemas import validate_free_dna_report
from app.core.config import Settings
from app.storage.repository import InMemoryRepository


def _summary(index: int) -> dict[str, int | bool]:
    return {
        "match_id": 920_000_000 + index,
        "start_time": 1_700_000_000 + index * 7_200,
        "duration": 1_800,
        "hero_id": 25 + index % 8,
        "player_slot": 0,
        "radiant_win": index % 2 == 0,
        "game_mode": 1,
        "lobby_type": 0,
        "kills": 7 + index % 5,
        "deaths": 4 + index % 3,
        "assists": 9 + index % 4,
        "lane_role": 1 + index % 3,
    }


def test_free_v3_public_contract_is_layered_and_summary_only() -> None:
    source = MappingSource(
        player={"profile": {"account_id": 42, "personaname": "Contract player"}},
        matches=[_summary(index) for index in range(60)],
        details={},
    )
    repository = InMemoryRepository()
    service = AnalysisService(source, repository=repository, settings=Settings())
    job, _ = asyncio.run(service.create_analysis("42", enqueue=False))
    asyncio.run(service.run_job(job))

    report = repository.get_report(job.report_id or "")
    assert report is not None
    assert report["schema_version"] == "free-dna-report-3.0.0"
    assert len(report["dimensions"]) == 10
    assert len(report["elements"]) == 23
    assert len(report["archetypes"]) == 3
    assert report["cost"]["history_requests"] == 1
    assert report["cost"]["detail_requests"] == 0
    assert report["cost"]["parse_requests"] == 0
    assert all("raw_metrics" not in element for element in report["elements"])
    assert all("source_match_ids" not in element for element in report["elements"])
    assert report["shares"]["privacy_defaults"]["show_raw_id"] is False
    validate_free_dna_report(report)

from datetime import UTC, datetime

from app.analysis.service import AnalysisService
from app.analysis.source import FixtureOpenDotaSource, MappingSource
from app.core.config import Settings

_TEST_WINDOW_END = int(datetime.now(UTC).timestamp())


def _summary(match_id: int, index: int) -> dict[str, int | bool]:
    return {
        "match_id": match_id,
        "start_time": _TEST_WINDOW_END - index * 7_200,
        "duration": 1_800,
        "hero_id": 25 + index % 5,
        "player_slot": 0,
        "radiant_win": index % 2 == 0,
        "game_mode": 1,
        "lobby_type": 7,
        "kills": 8 + index % 4,
        "deaths": 4,
        "assists": 10,
        "lane_role": 2 if index % 2 else 1,
    }


async def test_free_recorded_example_fails_closed_below_history_floor() -> None:
    source = FixtureOpenDotaSource("tests/fixtures/opendota")
    service = AnalysisService(source, settings=Settings())
    job, _ = await service.create_analysis(
        "https://www.opendota.com/players/193875165", enqueue=False
    )
    await service.run_job(job)

    assert job.status == "failed"
    assert job.failure_code == "INSUFFICIENT_HISTORY"
    assert len(service.repository.raw_payloads) == 2
    assert len(service.repository.normalized_matches) == 0
    assert len(service.repository.derived_features) == 0
    assert source.requests == [("player", 193875165), ("matches", 193875165)]
    assert job.report_id is None


async def test_unchanged_completed_analysis_is_reused() -> None:
    history = [_summary(900_200_000 + index, index) for index in range(35)]
    source = MappingSource(
        player={"profile": {"account_id": 42, "personaname": "Fixture player"}},
        matches=history,
        details={},
    )
    service = AnalysisService(
        source,
        settings=Settings(),
    )
    first, reused = await service.create_analysis("42", enqueue=False)
    assert not reused
    await service.run_job(first)
    second, reused = await service.create_analysis(
        "42", enqueue=False
    )
    assert reused
    assert second.job_id == first.job_id


async def test_free_report_is_not_reused_without_history_identity() -> None:
    history = [_summary(900_300_000 + index, index) for index in range(35)]
    source = MappingSource(
        player={"profile": {"account_id": 42, "personaname": "Fixture player"}},
        matches=history,
        details={},
    )
    service = AnalysisService(source, settings=Settings())
    first, _ = await service.create_analysis("42", enqueue=False)
    await service.run_job(first)
    service.repository.raw_payloads.clear()
    service.repository._raw_payload_index.clear()  # type: ignore[attr-defined]

    second, reused = await service.create_analysis("42", enqueue=False)

    assert not reused
    assert second.job_id != first.job_id

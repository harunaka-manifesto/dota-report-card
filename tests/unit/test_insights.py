from app.analysis.service import AnalysisService
from app.analysis.source import FixtureOpenDotaSource
from app.core.config import Settings


async def test_free_report_fails_closed_without_thirty_eligible_matches() -> None:
    service = AnalysisService(
        FixtureOpenDotaSource("tests/fixtures/opendota"),
        settings=Settings(),
    )
    job, reused = await service.create_analysis("193875165", enqueue=False)
    assert not reused
    await service.run_job(job)
    assert job.status == "failed"
    assert job.failure_code == "INSUFFICIENT_HISTORY"
    assert job.report_id is None

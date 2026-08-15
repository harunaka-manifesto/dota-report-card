from app.analysis.service import AnalysisService
from app.analysis.source import FixtureOpenDotaSource
from app.core.config import Settings


async def test_low_replay_coverage_publishes_summary_and_suppresses_replay() -> None:
    service = AnalysisService(
        FixtureOpenDotaSource("tests/fixtures/opendota"),
        settings=Settings(),
    )
    job, reused = await service.create_analysis("193875165", enqueue=False)
    assert not reused
    await service.run_job(job)
    assert job.status == "completed"
    report = service.repository.get_report(job.report_id or "")
    assert report is not None
    appendix = report["evidence_appendix"]
    assert any(item["publication_status"] == "published" for item in appendix)
    replay = [item for item in appendix if item["insight_id"] == "advantage_conversion"][0]
    assert replay["publication_status"] == "suppressed"
    assert "INSUFFICIENT_PARSE_COVERAGE" in replay["publication_reason"]
    assert report["evidence_scope"]["replay_evidence_status"] == "not_enough_evidence"

from app.analysis.service import AnalysisService
from app.analysis.source import FixtureOpenDotaSource
from app.core.config import Settings


async def test_free_report_publishes_summary_observation_without_replay_reads() -> None:
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
    assert all(item["publication_status"] == "published" for item in appendix)
    assert report["report_variant"] == "free_player_dna"
    assert report["evidence_scope"]["replay_evidence_status"] == "not_requested"

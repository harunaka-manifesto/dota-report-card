from app.analysis.service import AnalysisService
from app.analysis.source import FixtureOpenDotaSource
from app.core.config import Settings


async def test_recorded_example_retains_distinct_provenance_layers() -> None:
    source = FixtureOpenDotaSource("tests/fixtures/opendota")
    service = AnalysisService(source, settings=Settings())
    job, _ = await service.create_analysis(
        "https://www.opendota.com/players/193875165", enqueue=False
    )
    await service.run_job(job)

    assert job.status == "completed"
    assert len(service.repository.raw_payloads) == 8
    assert len(service.repository.normalized_matches) == 6
    assert len(service.repository.derived_features) == 6
    report = service.repository.get_report(job.report_id or "")
    assert report is not None
    assert report["noindex"] is True
    assert report["evidence_scope"]["eligible_matches"] == 6
    published = next(
        item for item in report["evidence_appendix"] if item["publication_status"] == "published"
    )
    assert published["provenance"]["raw_payload_refs"]
    assert published["provenance"]["normalized_match_refs"]
    assert published["provenance"]["derived_feature_refs"]


async def test_unchanged_completed_analysis_is_reused() -> None:
    service = AnalysisService(
        FixtureOpenDotaSource("tests/fixtures/opendota"),
        settings=Settings(),
    )
    first, reused = await service.create_analysis("193875165", enqueue=False)
    assert not reused
    await service.run_job(first)
    second, reused = await service.create_analysis(
        "https://www.opendota.com/players/193875165", enqueue=False
    )
    assert reused
    assert second.job_id == first.job_id

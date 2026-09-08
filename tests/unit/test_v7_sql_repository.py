from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.core.config import Settings
from app.player_analysis_v7.lifecycle import V7ReportLifecycle
from app.storage.models import Base, ReportRecord
from app.storage.repository import SqlAlchemyRepository
from sqlalchemy import update


def _repository(tmp_path) -> SqlAlchemyRepository:
    repository = SqlAlchemyRepository(Settings(database_url=f"sqlite:///{tmp_path / 'reports.db'}"))
    Base.metadata.create_all(repository.engine)
    return repository


def _completed_v7_job(repository: SqlAlchemyRepository) -> tuple[V7ReportLifecycle, str, str]:
    lifecycle = V7ReportLifecycle(repository, versions={"analysis": "fixture-1"})
    job, reused = lifecycle.locate_or_start(7, "fixture-player")
    assert reused is False
    report_id = repository.save_report(
        account_id=job.account_id,
        data_cutoff=None,
        model_version=lifecycle.model_version,
        template_version="fixture-1",
        report={"metadata": {}},
        evidence=[],
    )
    repository.complete_job(job, report_id)
    return lifecycle, job.job_id, report_id


@pytest.mark.parametrize("disposition", ["deleted", "expired"])
def test_v7_sql_reuse_requires_a_readable_report(tmp_path, disposition: str) -> None:
    repository = _repository(tmp_path)
    lifecycle, completed_job_id, report_id = _completed_v7_job(repository)

    with repository._session_factory() as session:
        record = session.get(ReportRecord, report_id)
        assert record is not None
        if disposition == "deleted":
            session.delete(record)
        else:
            data = dict(record.report_json or {})
            data["metadata"] = {
                **dict(data.get("metadata") or {}),
                "expires_at": datetime.now(UTC).isoformat(),
            }
            session.execute(
                update(ReportRecord)
                .where(ReportRecord.report_id == report_id)
                .values(report_json=data)
            )
        session.commit()

    assert repository.get_report(report_id) is None
    replacement, reused = lifecycle.locate_or_start(7, "fixture-player")

    assert reused is False
    assert replacement.report_id is None
    assert replacement.job_id != completed_job_id

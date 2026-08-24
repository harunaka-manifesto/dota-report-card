from __future__ import annotations

import asyncio
import logging

from celery import Celery
from celery.signals import worker_init

from app.analysis.service import AnalysisService
from app.core.config import get_settings
from app.core.metrics import record_metric
from app.core.release import build_release_identity
from app.core.security import PlayerIdentifier

logger = logging.getLogger(__name__)

celery_app = Celery(
    "dota-report-card", broker=get_settings().redis_url, backend=get_settings().redis_url
)
celery_app.conf.beat_schedule = {
    "purge-expired-report-data-hourly": {
        "task": "dota_report_card.purge_expired",
        "schedule": 3600.0,
    }
}
_service: AnalysisService | None = None


def configure_service(service: AnalysisService) -> None:
    global _service
    _service = service


@worker_init.connect
def validate_worker_dependencies(**_kwargs: object) -> None:
    """Fail worker startup before accepting a task against an un-migrated DB."""

    global _service
    from app.main import create_app

    service = create_app().state.analysis_service
    checker = getattr(service.repository, "check_ready", None)
    if checker is not None:
        checker()
    _service = service
    logger.info(
        "worker_release_identity=%s",
        build_release_identity(
            get_settings(),
            artifact_checksums=service.v61_artifact_checksums,
            artifact_manifest=service.v61_supporting_artifacts.get("manifest"),
            authorization_checksum=service.v61_authorization_checksum,
            db_revision=(
                service.repository.current_revision()
                if hasattr(service.repository, "current_revision")
                else None
            ),
        ),
    )


@celery_app.task(name="dota_report_card.release_identity")
def release_identity_task() -> dict[str, object]:
    service = _service
    if service is None:
        from app.main import create_app

        service = create_app().state.analysis_service
    repository = service.repository
    return build_release_identity(
        get_settings(),
        artifact_checksums=service.v61_artifact_checksums,
        artifact_manifest=service.v61_supporting_artifacts.get("manifest"),
        authorization_checksum=service.v61_authorization_checksum,
        db_revision=(
            repository.current_revision()
            if hasattr(repository, "current_revision")
            else None
        ),
    )


@celery_app.task(name="dota_report_card.run_analysis")
def run_analysis_task(job_id: str, account_id: int, canonical_player: str) -> None:
    service = _service
    if service is None:
        # A Celery worker is a separate process. Build its service from the
        # shared settings/database instead of relying on API-process memory.
        from app.main import create_app

        service = create_app().state.analysis_service
    job = service.repository.get_job(job_id)
    if job is None:
        raise RuntimeError("Analysis job does not exist")
    asyncio.run(
        service.run_job(job, PlayerIdentifier(account_id, canonical_player))
    )


@celery_app.task(name="dota_report_card.purge_expired")
def purge_expired_task() -> int:
    service = _service
    if service is None:
        from app.main import create_app

        service = create_app().state.analysis_service
    try:
        deleted = int(service.repository.purge_expired())
        record_metric("retention.purged", value=deleted)
        return deleted
    except Exception:
        record_metric("retention.failed")
        raise

from __future__ import annotations

import threading
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.insights.models import EvidenceObject
from app.opendota.cache import payload_hash
from app.storage.database import create_database_engine
from app.storage.models import (
    AnalysisJobRecord,
    Base,
    DerivedFeatureRecord,
    EvidenceObjectRecord,
    MatchRecord,
    RawPayloadRecord,
    ReportRecord,
)


@dataclass(slots=True)
class AnalysisEvent:
    stage: str
    status: str
    message: str
    processed_matches: int = 0
    eligible_matches: int = 0
    at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "message": self.message,
            "processed_matches": self.processed_matches,
            "eligible_matches": self.eligible_matches,
            "at": self.at,
        }


@dataclass(slots=True)
class AnalysisJob:
    job_id: str
    account_id: int
    canonical_player: str
    analysis_mode: str = "free"
    status: str = "queued"
    stage: str = "validating_player"
    processed_matches: int = 0
    eligible_matches: int = 0
    warnings: list[str] = field(default_factory=list)
    failure_code: str | None = None
    failure_detail: str | None = None
    report_id: str | None = None
    model_version: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    events: list[AnalysisEvent] = field(default_factory=list)
    completed_stages: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "account_id": self.account_id,
            "analysis_mode": self.analysis_mode,
            "status": self.status,
            "stage": self.stage,
            "processed_matches": self.processed_matches,
            "eligible_matches": self.eligible_matches,
            "warnings": list(self.warnings),
            "failure_code": self.failure_code,
            "message": self.failure_detail,
            "report_id": self.report_id,
            "events_url": f"/v1/analyses/{self.job_id}/events",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_stages": list(self.completed_stages),
        }


class InMemoryRepository:
    """Deterministic local store mirroring the production persistence seams."""

    def __init__(self, *, report_retention_days: int = 30) -> None:
        self._lock = threading.RLock()
        self.jobs: dict[str, AnalysisJob] = {}
        self.reports: dict[str, dict[str, Any]] = {}
        self.evidence: dict[str, list[dict[str, Any]]] = {}
        self.raw_payloads: list[dict[str, Any]] = []
        self.normalized_matches: dict[int, dict[str, Any]] = {}
        self.derived_features: dict[int, dict[str, Any]] = {}
        self._completed: dict[tuple[int, str, str], str] = {}
        self._raw_payload_index: set[tuple[str, str, str]] = set()
        self.report_retention = timedelta(days=max(1, report_retention_days))

    def create_job(
        self,
        account_id: int,
        canonical_player: str,
        model_version: str,
        analysis_mode: str = "free",
    ) -> AnalysisJob:
        job = AnalysisJob(
            str(uuid4()),
            account_id,
            canonical_player,
            analysis_mode=analysis_mode,
            model_version=model_version,
        )
        with self._lock:
            self.jobs[job.job_id] = job
        return job

    def get_or_create_inflight_job(
        self,
        account_id: int,
        canonical_player: str,
        model_version: str,
        analysis_mode: str = "free",
    ) -> tuple[AnalysisJob, bool]:
        """Atomically coalesce queued/running work for one account and model."""

        with self._lock:
            candidates = [
                job
                for job in self.jobs.values()
                if job.account_id == account_id
                and job.model_version == model_version
                and job.analysis_mode == analysis_mode
                and job.status in {"queued", "running"}
            ]
            if candidates:
                return max(candidates, key=lambda item: item.created_at), True
            job = AnalysisJob(
                str(uuid4()),
                account_id,
                canonical_player,
                analysis_mode=analysis_mode,
                model_version=model_version,
            )
            self.jobs[job.job_id] = job
            return job, False

    def find_compatible_completed(
        self,
        account_id: int,
        model_version: str,
        *,
        analysis_mode: str = "free",
        max_age_seconds: int | None = None,
    ) -> AnalysisJob | None:
        with self._lock:
            job_id = self._completed.get((account_id, model_version, analysis_mode))
            job = self.jobs.get(job_id) if job_id else None
            if job is not None and job.report_id and self.get_report(job.report_id) is None:
                return None
            if job is None or max_age_seconds is None:
                return job
            age = (datetime.now(UTC) - job.updated_at).total_seconds()
            return job if age <= max_age_seconds else None

    def get_job(self, job_id: str) -> AnalysisJob | None:
        with self._lock:
            return self.jobs.get(job_id)

    def get_events(self, job_id: str, offset: int = 0) -> list[AnalysisEvent]:
        with self._lock:
            job = self.jobs.get(job_id)
            return list(job.events[offset:]) if job else []

    def update_job(
        self,
        job: AnalysisJob,
        *,
        stage: str | None = None,
        status: str | None = None,
        message: str | None = None,
    ) -> None:
        with self._lock:
            if stage and stage != job.stage:
                _mark_stage_complete(job, job.stage)
            job.stage = stage or job.stage
            job.status = status or job.status
            job.updated_at = datetime.now(UTC)
            if message:
                job.events.append(
                    AnalysisEvent(
                        stage=job.stage,
                        status=job.status,
                        message=message,
                        processed_matches=job.processed_matches,
                        eligible_matches=job.eligible_matches,
                    )
                )

    def add_warning(self, job: AnalysisJob, warning: str) -> None:
        with self._lock:
            if warning not in job.warnings:
                job.warnings.append(warning)

    def fail_job(self, job: AnalysisJob, code: str, detail: str) -> None:
        with self._lock:
            _mark_stage_complete(job, job.stage)
            job.status = "failed"
            job.stage = "failed"
            job.failure_code = code
            job.failure_detail = detail
            job.updated_at = datetime.now(UTC)
            job.events.append(AnalysisEvent("failed", "failed", detail))

    def complete_job(self, job: AnalysisJob, report_id: str) -> None:
        with self._lock:
            _mark_stage_complete(job, job.stage)
            job.status = "completed"
            job.stage = "completed"
            job.report_id = report_id
            job.updated_at = datetime.now(UTC)
            job.events.append(
                AnalysisEvent(
                    "completed",
                    "completed",
                    "Report is ready",
                    job.processed_matches,
                    job.eligible_matches,
                )
            )
            self._completed[(job.account_id, job.model_version, job.analysis_mode)] = job.job_id

    def record_event(self, job: AnalysisJob, message: str) -> None:
        with self._lock:
            job.events.append(
                AnalysisEvent(
                    job.stage,
                    job.status,
                    message,
                    job.processed_matches,
                    job.eligible_matches,
                )
            )

    def persist_raw_payload(
        self,
        endpoint: str,
        source_id: str,
        payload: Any,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "endpoint": endpoint,
            "source_id": str(source_id),
            "payload_hash": payload_hash(payload),
            "payload": payload,
            "metadata": dict(metadata or {}),
            "fetched_at": datetime.now(UTC).isoformat(),
        }
        with self._lock:
            key = (endpoint, str(source_id), record["payload_hash"])
            if key not in self._raw_payload_index:
                self.raw_payloads.append(record)
                self._raw_payload_index.add(key)
        return record

    def get_cached_raw_payload(self, endpoint: str, source_id: str) -> Any | None:
        with self._lock:
            for record in reversed(self.raw_payloads):
                if record["endpoint"] == endpoint and record["source_id"] == str(source_id):
                    return record["payload"]
        return None

    def save_normalized_match(self, match_id: int, value: dict[str, Any]) -> None:
        with self._lock:
            self.normalized_matches[match_id] = value

    def save_derived_feature(self, match_id: int, value: dict[str, Any]) -> None:
        with self._lock:
            self.derived_features[match_id] = value

    def save_report(
        self,
        *,
        account_id: int,
        data_cutoff: int | None,
        model_version: str,
        template_version: str,
        report: dict[str, Any],
        evidence: list[EvidenceObject],
    ) -> str:
        report_id = str(uuid4())
        created_at = datetime.now(UTC)
        expires_at = created_at + self.report_retention
        with self._lock:
            self.reports[report_id] = {
                **deepcopy(report),
                "report_id": report_id,
                "account_id": account_id,
                "data_cutoff": data_cutoff,
                "model_version": model_version,
                "template_version": template_version,
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
            }
            self.evidence[report_id] = [item.as_dict() for item in evidence]
        return report_id

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        with self._lock:
            report = self.reports.get(report_id)
            if report is None:
                return None
            if _expired(report.get("expires_at")):
                self.reports.pop(report_id, None)
                self.evidence.pop(report_id, None)
                return None
            return deepcopy(report)

    def purge_expired(self, *, now: datetime | None = None) -> int:
        cutoff = now or datetime.now(UTC)
        with self._lock:
            expired_reports = [
                report_id
                for report_id, report in self.reports.items()
                if _expired(report.get("expires_at"), now=cutoff)
            ]
            for report_id in expired_reports:
                self.reports.pop(report_id, None)
                self.evidence.pop(report_id, None)
            raw_cutoff = cutoff - self.report_retention
            retained_payloads: list[dict[str, Any]] = []
            for item in self.raw_payloads:
                fetched_at = _parse_datetime(item.get("fetched_at"))
                if fetched_at is None or fetched_at >= raw_cutoff:
                    retained_payloads.append(item)
            self.raw_payloads[:] = retained_payloads
            self._raw_payload_index = {
                (item["endpoint"], item["source_id"], item["payload_hash"])
                for item in self.raw_payloads
            }
            return len(expired_reports)

    def get_evidence(self, report_id: str, insight_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            values = list(self.evidence.get(report_id, []))
        if insight_id is None:
            return values
        return [item for item in values if item["insight_id"] == insight_id]


class SqlAlchemyRepository:
    """Persistent repository used by production API and worker processes."""

    def __init__(self, settings: Any) -> None:
        self.engine = create_database_engine(settings)
        Base.metadata.create_all(self.engine)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self._lock = threading.RLock()
        self.report_retention = timedelta(
            days=max(1, int(getattr(settings, "effective_report_retention_days", 30)))
        )

    @staticmethod
    def _active_key(account_id: int, model_version: str, analysis_mode: str = "free") -> str:
        return f"{account_id}:{model_version}:{analysis_mode}"

    def _job_from_record(self, record: AnalysisJobRecord) -> AnalysisJob:
        events = [
            AnalysisEvent(
                stage=item.get("stage", ""),
                status=item.get("status", ""),
                message=item.get("message", ""),
                processed_matches=int(item.get("processed_matches", 0)),
                eligible_matches=int(item.get("eligible_matches", 0)),
                at=item.get("at") or datetime.now(UTC).isoformat(),
            )
            for item in (record.events_json or [])
        ]
        created_at = _as_aware(record.created_at)
        updated_at = _as_aware(record.updated_at)
        return AnalysisJob(
            job_id=record.job_id,
            account_id=record.account_id,
            canonical_player=record.canonical_player,
            analysis_mode=getattr(record, "analysis_mode", "free") or "free",
            status=record.status,
            stage=record.stage,
            processed_matches=record.processed_matches or 0,
            eligible_matches=record.eligible_matches or 0,
            warnings=list(record.warnings_json or []),
            failure_code=record.failure_code,
            failure_detail=record.failure_detail,
            report_id=record.report_id,
            model_version=record.model_version,
            created_at=created_at,
            updated_at=updated_at,
            events=events,
            completed_stages=list(
                dict.fromkeys(
                    event.stage
                    for event in events
                    if event.stage not in {"completed", "failed"}
                )
            ),
        )

    def _write_job(self, session: Session, job: AnalysisJob) -> None:
        record = session.get(AnalysisJobRecord, job.job_id)
        if record is None:
            return
        record.account_id = job.account_id
        record.canonical_player = job.canonical_player
        record.analysis_mode = job.analysis_mode
        record.active_key = (
            self._active_key(job.account_id, job.model_version, job.analysis_mode)
            if job.status in {"queued", "running"}
            else None
        )
        record.status = job.status
        record.stage = job.stage
        record.processed_matches = job.processed_matches
        record.eligible_matches = job.eligible_matches
        record.warnings_json = list(job.warnings)
        record.failure_code = job.failure_code
        record.failure_detail = job.failure_detail
        record.report_id = job.report_id
        record.updated_at = job.updated_at
        record.events_json = [event.as_dict() for event in job.events]

    def create_job(
        self,
        account_id: int,
        canonical_player: str,
        model_version: str,
        analysis_mode: str = "free",
    ) -> AnalysisJob:
        job = AnalysisJob(
            str(uuid4()),
            account_id,
            canonical_player,
            analysis_mode=analysis_mode,
            model_version=model_version,
        )
        with self._session_factory() as session:
            session.add(
                AnalysisJobRecord(
                    job_id=job.job_id,
                    account_id=account_id,
                    canonical_player=canonical_player,
                    analysis_mode=analysis_mode,
                    active_key=self._active_key(account_id, model_version, analysis_mode),
                    status=job.status,
                    stage=job.stage,
                    warnings_json=[],
                    events_json=[],
                    model_version=model_version,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                )
            )
            session.commit()
        return job

    def get_or_create_inflight_job(
        self,
        account_id: int,
        canonical_player: str,
        model_version: str,
        analysis_mode: str = "free",
    ) -> tuple[AnalysisJob, bool]:
        key = self._active_key(account_id, model_version, analysis_mode)
        with self._lock:
            with self._session_factory() as session:
                record = session.scalar(
                    select(AnalysisJobRecord).where(
                        AnalysisJobRecord.active_key == key,
                        AnalysisJobRecord.status.in_(["queued", "running"]),
                    )
                )
                if record is not None:
                    return self._job_from_record(record), True
                job = AnalysisJob(
                    str(uuid4()),
                    account_id,
                    canonical_player,
                    analysis_mode=analysis_mode,
                    model_version=model_version,
                )
                session.add(
                    AnalysisJobRecord(
                        job_id=job.job_id,
                        account_id=account_id,
                        canonical_player=canonical_player,
                        analysis_mode=analysis_mode,
                        active_key=key,
                        status=job.status,
                        stage=job.stage,
                        warnings_json=[],
                        events_json=[],
                        model_version=model_version,
                        created_at=job.created_at,
                        updated_at=job.updated_at,
                    )
                )
                try:
                    session.commit()
                except IntegrityError:
                    session.rollback()
                    record = session.scalar(
                        select(AnalysisJobRecord).where(AnalysisJobRecord.active_key == key)
                    )
                    if record is not None:
                        return self._job_from_record(record), True
                    raise
                return job, False

    def find_compatible_completed(
        self,
        account_id: int,
        model_version: str,
        *,
        analysis_mode: str = "free",
        max_age_seconds: int | None = None,
    ) -> AnalysisJob | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(AnalysisJobRecord)
                .where(
                    AnalysisJobRecord.account_id == account_id,
                    AnalysisJobRecord.model_version == model_version,
                    AnalysisJobRecord.analysis_mode == analysis_mode,
                    AnalysisJobRecord.status == "completed",
                )
                .order_by(AnalysisJobRecord.updated_at.desc())
            )
            if record is None:
                return None
            job = self._job_from_record(record)
            if max_age_seconds is not None:
                age = (datetime.now(UTC) - job.updated_at).total_seconds()
                if age > max_age_seconds:
                    return None
            return job

    def get_job(self, job_id: str) -> AnalysisJob | None:
        with self._session_factory() as session:
            record = session.get(AnalysisJobRecord, job_id)
            return self._job_from_record(record) if record else None

    def get_events(self, job_id: str, offset: int = 0) -> list[AnalysisEvent]:
        job = self.get_job(job_id)
        return job.events[offset:] if job else []

    def update_job(
        self,
        job: AnalysisJob,
        *,
        stage: str | None = None,
        status: str | None = None,
        message: str | None = None,
    ) -> None:
        with self._session_factory() as session:
            record = session.get(AnalysisJobRecord, job.job_id)
            if record is None:
                return
            if stage and stage != job.stage:
                _mark_stage_complete(job, job.stage)
            job.stage = stage or job.stage
            job.status = status or job.status
            job.updated_at = datetime.now(UTC)
            if message:
                job.events.append(
                    AnalysisEvent(
                        job.stage,
                        job.status,
                        message,
                        job.processed_matches,
                        job.eligible_matches,
                    )
                )
            self._write_job(session, job)
            session.commit()

    def add_warning(self, job: AnalysisJob, warning: str) -> None:
        if warning not in job.warnings:
            job.warnings.append(warning)
        job.updated_at = datetime.now(UTC)
        self._save_job(job)

    def fail_job(self, job: AnalysisJob, code: str, detail: str) -> None:
        _mark_stage_complete(job, job.stage)
        job.status = "failed"
        job.stage = "failed"
        job.failure_code = code
        job.failure_detail = detail
        job.updated_at = datetime.now(UTC)
        job.events.append(AnalysisEvent("failed", "failed", detail))
        self._save_job(job)

    def complete_job(self, job: AnalysisJob, report_id: str) -> None:
        _mark_stage_complete(job, job.stage)
        job.status = "completed"
        job.stage = "completed"
        job.report_id = report_id
        job.updated_at = datetime.now(UTC)
        job.events.append(
            AnalysisEvent(
                "completed",
                "completed",
                "Report is ready",
                job.processed_matches,
                job.eligible_matches,
            )
        )
        self._save_job(job)

    def record_event(self, job: AnalysisJob, message: str) -> None:
        job.events.append(
            AnalysisEvent(
                job.stage,
                job.status,
                message,
                job.processed_matches,
                job.eligible_matches,
            )
        )
        job.updated_at = datetime.now(UTC)
        self._save_job(job)

    def _save_job(self, job: AnalysisJob) -> None:
        with self._session_factory() as session:
            self._write_job(session, job)
            session.commit()

    def persist_raw_payload(
        self,
        endpoint: str,
        source_id: str,
        payload: Any,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "endpoint": endpoint,
            "source_id": str(source_id),
            "payload_hash": payload_hash(payload),
            "payload": payload,
            "metadata": dict(metadata or {}),
            "fetched_at": datetime.now(UTC).isoformat(),
        }
        with self._session_factory() as session:
            existing = session.scalar(
                select(RawPayloadRecord).where(
                    RawPayloadRecord.endpoint == endpoint,
                    RawPayloadRecord.source_id == str(source_id),
                    RawPayloadRecord.payload_hash == record["payload_hash"],
                )
            )
            if existing is None:
                session.add(
                    RawPayloadRecord(
                        endpoint=endpoint,
                        source_id=str(source_id),
                        payload_hash=record["payload_hash"],
                        payload_json=payload,
                        metadata_json=dict(metadata or {}),
                        fetched_at=datetime.now(UTC),
                    )
                )
                session.commit()
        return record

    def get_cached_raw_payload(self, endpoint: str, source_id: str) -> Any | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(RawPayloadRecord)
                .where(
                    RawPayloadRecord.endpoint == endpoint,
                    RawPayloadRecord.source_id == str(source_id),
                )
                .order_by(RawPayloadRecord.fetched_at.desc())
            )
            return record.payload_json if record is not None else None

    def save_normalized_match(self, match_id: int, value: dict[str, Any]) -> None:
        with self._session_factory() as session:
            record = session.get(MatchRecord, match_id)
            if record is None:
                record = MatchRecord(
                    match_id=match_id,
                    start_time=value.get("start_time"),
                    duration_seconds=value.get("duration_seconds", 0),
                    game_mode=value.get("game_mode"),
                    lobby_type=value.get("lobby_type"),
                    patch=value.get("patch"),
                    radiant_win=value.get("won"),
                    eligibility_json=value.get("coverage", {}),
                )
                session.add(record)
            else:
                record.start_time = value.get("start_time")
                record.duration_seconds = value.get("duration_seconds", 0)
                record.game_mode = value.get("game_mode")
                record.lobby_type = value.get("lobby_type")
                record.patch = value.get("patch")
                record.radiant_win = value.get("won")
                record.eligibility_json = value.get("coverage", {})
            session.commit()

    def save_derived_feature(self, match_id: int, value: dict[str, Any]) -> None:
        with self._session_factory() as session:
            record = session.scalar(
                select(DerivedFeatureRecord).where(
                    DerivedFeatureRecord.entity_scope == "match",
                    DerivedFeatureRecord.entity_id == str(match_id),
                    DerivedFeatureRecord.feature_id == f"feature:match:{match_id}",
                )
            )
            if record is None:
                session.add(
                    DerivedFeatureRecord(
                        feature_id=f"feature:match:{match_id}",
                        feature_version="features-1.0.0",
                        entity_scope="match",
                        entity_id=str(match_id),
                        value_json=value,
                        denominator=1,
                        provenance_json={"match_id": match_id},
                    )
                )
            else:
                record.value_json = value
            session.commit()

    def save_report(
        self,
        *,
        account_id: int,
        data_cutoff: int | None,
        model_version: str,
        template_version: str,
        report: dict[str, Any],
        evidence: list[EvidenceObject],
    ) -> str:
        report_id = str(uuid4())
        created_at = datetime.now(UTC)
        expires_at = created_at + self.report_retention
        report_json = deepcopy(report)
        report_json["expires_at"] = expires_at.isoformat()
        report_json["metadata"] = {
            **dict(report_json.get("metadata") or {}),
            "expires_at": expires_at.isoformat(),
        }
        with self._session_factory() as session:
            session.add(
                ReportRecord(
                    report_id=report_id,
                    account_id=account_id,
                    data_cutoff=data_cutoff,
                    model_version=model_version,
                    template_version=template_version,
                    report_json=report_json,
                    created_at=created_at,
                )
            )
            session.add_all(
                EvidenceObjectRecord(
                    report_id=report_id,
                    insight_id=item.insight_id,
                    concept_id=item.concept_id,
                    publication_status=item.publication_status,
                    evidence_json=item.as_dict(),
                    source_match_ids=list(item.source_match_ids),
                )
                for item in evidence
            )
            session.commit()
        return report_id

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        with self._session_factory() as session:
            record = session.get(ReportRecord, report_id)
            if record is None:
                return None
            if _expired((record.report_json or {}).get("expires_at")) or (
                _as_aware(record.created_at) + self.report_retention <= datetime.now(UTC)
            ):
                return None
            return {
                **dict(record.report_json or {}),
                "report_id": record.report_id,
                "account_id": record.account_id,
                "data_cutoff": record.data_cutoff,
                "model_version": record.model_version,
                "template_version": record.template_version,
                "created_at": _as_aware(record.created_at).isoformat(),
                "expires_at": (record.report_json or {}).get("expires_at"),
            }

    def purge_expired(self, *, now: datetime | None = None) -> int:
        current = now or datetime.now(UTC)
        cutoff = current - self.report_retention
        with self._session_factory() as session:
            reports = session.scalars(select(ReportRecord)).all()
            expired = [
                record.report_id
                for record in reports
                if _expired((record.report_json or {}).get("expires_at"), now=current)
                or _as_aware(record.created_at) < cutoff
            ]
            if expired:
                session.execute(
                    delete(EvidenceObjectRecord).where(
                        EvidenceObjectRecord.report_id.in_(expired)
                    )
                )
                session.execute(delete(ReportRecord).where(ReportRecord.report_id.in_(expired)))
            session.execute(delete(RawPayloadRecord).where(RawPayloadRecord.fetched_at < cutoff))
            session.commit()
            return len(expired)

    def get_evidence(self, report_id: str, insight_id: str | None = None) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            query = select(EvidenceObjectRecord).where(EvidenceObjectRecord.report_id == report_id)
            if insight_id is not None:
                query = query.where(EvidenceObjectRecord.insight_id == insight_id)
            return [dict(record.evidence_json or {}) for record in session.scalars(query).all()]


def _as_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _mark_stage_complete(job: AnalysisJob, stage: str | None) -> None:
    if stage and stage not in {"queued", "completed", "failed"} and stage not in job.completed_stages:
        job.completed_stages.append(stage)


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return _as_aware(datetime.fromisoformat(value))
    except ValueError:
        return None


def _expired(value: Any, *, now: datetime | None = None) -> bool:
    parsed = _parse_datetime(value)
    return parsed is not None and parsed <= (now or datetime.now(UTC))

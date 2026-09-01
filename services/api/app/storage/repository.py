from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.cache import payload_hash
from app.insights.models import EvidenceObject
from app.storage.database import (
    check_database_revision,
    create_database_engine,
    current_database_revision,
)
from app.storage.models import (
    AnalysisJobRecord,
    DerivedFeatureRecord,
    EvidenceObjectRecord,
    MatchRecord,
    RawPayloadRecord,
    ReportInteractionSessionRecord,
    ReportRecord,
)

INTERACTION_STATE_SCHEMA_VERSION = "report-interactions-1.0.0"
INTERACTION_SESSION_TTL = timedelta(days=90)


class InteractionSessionError(Exception):
    """Base error raised by the repository's interaction-session seam."""


class InteractionSessionNotFound(InteractionSessionError):
    pass


class InteractionSessionUnauthorized(InteractionSessionError):
    pass


class InteractionSessionExpired(InteractionSessionError):
    pass


class InteractionRevisionConflict(InteractionSessionError):
    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(f"Expected revision {expected}, current revision is {actual}")
        self.expected = expected
        self.actual = actual


@dataclass(slots=True)
class ReportInteractionSession:
    session_id: str
    report_id: str
    account_id: int
    state_schema_version: str
    revision: int
    state: dict[str, Any]
    recommendation_baseline: dict[str, Any]
    history_cutoff: int | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    # This is a digest, never the caller's raw bearer token.
    access_token_hash: str = ""

    @property
    def token_hash(self) -> str:
        """Compatibility name used by security/audit callers."""

        return self.access_token_hash

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "report_id": self.report_id,
            "account_id": self.account_id,
            "state_schema_version": self.state_schema_version,
            "revision": self.revision,
            "state": deepcopy(self.state),
            "recommendation_baseline": deepcopy(self.recommendation_baseline),
            "history_cutoff": self.history_cutoff,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


def _new_access_token() -> tuple[str, str]:
    """Create a 256-bit bearer token and its storage-safe SHA-256 digest."""

    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode("ascii")).hexdigest()


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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
    stage: str = "resolving_player"
    processed_matches: int = 0
    eligible_matches: int = 0
    warnings: list[str] = field(default_factory=list)
    failure_code: str | None = None
    failure_detail: str | None = None
    report_id: str | None = None
    parent_report_id: str | None = None
    diagnostic_question_id: str | None = None
    entitlement_decision: dict[str, Any] | None = None
    selection_plan: dict[str, Any] | None = None
    stopping_reason: str | None = None
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
            "parent_report_id": self.parent_report_id,
            "diagnostic_question_id": self.diagnostic_question_id,
            "entitlement_decision": deepcopy(self.entitlement_decision),
            "selection_plan": deepcopy(self.selection_plan),
            "stopping_reason": self.stopping_reason,
            "events_url": f"/v1/analyses/{self.job_id}/events",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_stages": list(self.completed_stages),
        }


class InMemoryRepository:
    """Deterministic local store mirroring the production persistence seams."""

    def __init__(
        self,
        *,
        report_retention_days: int = 30,
        interaction_retention_days: int = 90,
    ) -> None:
        self._lock = threading.RLock()
        self.jobs: dict[str, AnalysisJob] = {}
        self.reports: dict[str, dict[str, Any]] = {}
        self._report_private: dict[str, dict[str, Any]] = {}
        self.evidence: dict[str, list[dict[str, Any]]] = {}
        self.raw_payloads: list[dict[str, Any]] = []
        self.normalized_matches: dict[int, dict[str, Any]] = {}
        self.derived_features: dict[int, dict[str, Any]] = {}
        self.interaction_sessions: dict[str, ReportInteractionSession] = {}
        self._completed: dict[tuple[int, str, str], str] = {}
        self._raw_payload_index: set[tuple[str, str, str]] = set()
        self.report_retention = timedelta(days=max(1, report_retention_days))
        self.interaction_retention = timedelta(days=max(1, interaction_retention_days))

    def create_job(
        self,
        account_id: int,
        canonical_player: str,
        model_version: str,
        analysis_mode: str = "free",
        *,
        parent_report_id: str | None = None,
        diagnostic_question_id: str | None = None,
        entitlement_decision: dict[str, Any] | None = None,
        selection_plan: dict[str, Any] | None = None,
        stopping_reason: str | None = None,
    ) -> AnalysisJob:
        job = AnalysisJob(
            str(uuid4()),
            account_id,
            canonical_player,
            analysis_mode=analysis_mode,
            parent_report_id=parent_report_id,
            diagnostic_question_id=diagnostic_question_id,
            entitlement_decision=deepcopy(entitlement_decision),
            selection_plan=deepcopy(selection_plan),
            stopping_reason=stopping_reason,
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

    def find_active_deep_job(
        self, report_id: str, diagnostic_question_id: str, account_id: int, grant_id: str
    ) -> AnalysisJob | None:
        with self._lock:
            return next(
                (
                    job
                    for job in self.jobs.values()
                    if job.analysis_mode == "deep_scan"
                    and job.parent_report_id == report_id
                    and job.diagnostic_question_id == diagnostic_question_id
                    and job.account_id == account_id
                    and (job.entitlement_decision or {}).get("grant_id") == grant_id
                    and job.status in {"queued", "running"}
                ),
                None,
            )

    def find_compatible_completed(
        self,
        account_id: int,
        model_version: str,
        *,
        analysis_mode: str = "free",
        max_age_seconds: int | None = None,
        raw_history_hash: str | None = None,
        identity_fingerprint: str | None = None,
    ) -> AnalysisJob | None:
        with self._lock:
            job_id = self._completed.get((account_id, model_version, analysis_mode))
            job = self.jobs.get(job_id) if job_id else None
            if job is not None and job.report_id and self.get_report(job.report_id) is None:
                return None
            if raw_history_hash is not None and job is not None and job.report_id:
                report = self.reports.get(job.report_id)
                stored_hash = ((report or {}).get("metadata") or {}).get("raw_history_hash")
                if stored_hash != raw_history_hash:
                    return None
            if identity_fingerprint is not None and job is not None and job.report_id:
                report = self.reports.get(job.report_id) or {}
                if _report_identity_fingerprint(report) != identity_fingerprint:
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

    def get_cached_raw_payload(
        self,
        endpoint: str,
        source_id: str,
        *,
        max_age_seconds: int | None = None,
    ) -> Any | None:
        with self._lock:
            for record in reversed(self.raw_payloads):
                if record["endpoint"] == endpoint and record["source_id"] == str(source_id):
                    if max_age_seconds is not None:
                        fetched_at = _parse_datetime(record.get("fetched_at"))
                        if fetched_at is None or (
                            datetime.now(UTC) - fetched_at
                        ).total_seconds() > max(0, max_age_seconds):
                            continue
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
            }
            self.reports[report_id]["metadata"] = {
                **dict(self.reports[report_id].get("metadata") or {}),
                "expires_at": expires_at.isoformat(),
            }
            self._report_private[report_id] = {
                "account_id": account_id,
                "data_cutoff": data_cutoff,
                "model_version": model_version,
                "template_version": template_version,
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
            }
            self.evidence[report_id] = [item.as_dict() for item in evidence]
        return report_id

    def save_report_with_protected_cohorts(
        self,
        *,
        account_id: int,
        data_cutoff: int | None,
        model_version: str,
        template_version: str,
        report: dict[str, Any],
        evidence: list[EvidenceObject],
        protected_cohorts: dict[str, Any],
    ) -> str:
        with self._lock:
            report_id = self.save_report(
                account_id=account_id,
                data_cutoff=data_cutoff,
                model_version=model_version,
                template_version=template_version,
                report=report,
                evidence=evidence,
            )
            try:
                self.persist_protected_cohorts(report_id, protected_cohorts)
            except Exception:
                self.reports.pop(report_id, None)
                self._report_private.pop(report_id, None)
                self.evidence.pop(report_id, None)
                raise
            return report_id

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        with self._lock:
            report = self.reports.get(report_id)
            if report is None:
                return None
            if _expired((report.get("metadata") or {}).get("expires_at")):
                self.reports.pop(report_id, None)
                self._report_private.pop(report_id, None)
                self.evidence.pop(report_id, None)
                return None
            return deepcopy(report)

    def purge_expired(self, *, now: datetime | None = None) -> int:
        cutoff = now or datetime.now(UTC)
        with self._lock:
            expired_reports = [
                report_id
                for report_id, report in self.reports.items()
                if _expired((report.get("metadata") or {}).get("expires_at"), now=cutoff)
            ]
            for report_id in expired_reports:
                self.reports.pop(report_id, None)
                self._report_private.pop(report_id, None)
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
            self.purge_expired_interaction_sessions(now=cutoff)
            return len(expired_reports)

    def get_evidence(self, report_id: str, insight_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            values = list(self.evidence.get(report_id, []))
        if insight_id is None:
            return values
        return [item for item in values if item["insight_id"] == insight_id]

    # --- v6 report interaction state -------------------------------------

    def get_report_owner(self, report_id: str) -> int | None:
        with self._lock:
            private = self._report_private.get(report_id)
            if private is not None:
                return int(private["account_id"])
            report = self.reports.get(report_id) or {}
            identity = report.get("identity") or {}
            value = identity.get("account_id")
            try:
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                return None

    def get_report_cutoff(self, report_id: str) -> int | None:
        with self._lock:
            private = self._report_private.get(report_id)
            if private is not None:
                value = private.get("data_cutoff")
                try:
                    return int(value) if value is not None else None
                except (TypeError, ValueError):
                    return None
            report = self.reports.get(report_id) or {}
            for source in (report.get("metadata") or {}, report):
                for key in ("history_cutoff", "data_cutoff", "cutoff"):
                    value = source.get(key)
                    try:
                        if value is not None:
                            return int(value)
                    except (TypeError, ValueError):
                        continue
            return None

    def persist_protected_cohorts(
        self, report_id: str, cohorts: dict[str, Any]
    ) -> None:
        with self._lock:
            private = self._report_private.get(report_id)
            if private is None:
                raise InteractionSessionNotFound("Report was not found")
            private["protected_cohorts"] = deepcopy(cohorts)

    def resolve_protected_cohort(
        self, report_id: str, cohort_reference: str
    ) -> dict[str, Any] | None:
        with self._lock:
            private = self._report_private.get(report_id) or {}
            cohorts = private.get("protected_cohorts") or {}
            value = cohorts.get(cohort_reference)
            return deepcopy(value) if isinstance(value, dict) else None

    def create_interaction_session(
        self,
        report_id: str,
        *,
        account_id: int | None = None,
        state: dict[str, Any] | None = None,
        recommendation_baseline: dict[str, Any] | None = None,
        history_cutoff: int | None = None,
        state_schema_version: str = INTERACTION_STATE_SCHEMA_VERSION,
        now: datetime | None = None,
    ) -> tuple[ReportInteractionSession, str]:
        with self._lock:
            if self.get_report(report_id) is None:
                raise InteractionSessionNotFound("Report was not found")
            owner = account_id if account_id is not None else self.get_report_owner(report_id)
            if owner is None:
                raise InteractionSessionNotFound("Report owner was not found")
            token, token_hash = _new_access_token()
            created_at = _as_aware(now) if now is not None else datetime.now(UTC)
            cutoff = history_cutoff if history_cutoff is not None else self.get_report_cutoff(report_id)
            session = ReportInteractionSession(
                session_id=str(uuid4()),
                report_id=report_id,
                account_id=int(owner),
                state_schema_version=state_schema_version,
                revision=1,
                state=deepcopy(state or {}),
                recommendation_baseline=deepcopy(recommendation_baseline or {}),
                history_cutoff=cutoff,
                created_at=created_at,
                updated_at=created_at,
                expires_at=created_at + self.interaction_retention,
                access_token_hash=token_hash,
            )
            self.interaction_sessions[session.session_id] = session
            return deepcopy(session), token

    # Explicit alias keeps the repository seam discoverable to callers that
    # use the public resource name rather than the table name.
    create_report_interaction_session = create_interaction_session

    def get_interaction_session(
        self, session_id: str, *, now: datetime | None = None
    ) -> ReportInteractionSession | None:
        with self._lock:
            session = self.interaction_sessions.get(session_id)
            if session is None:
                return None
            current = _as_aware(now) if now is not None else datetime.now(UTC)
            if session.expires_at <= current:
                self.interaction_sessions.pop(session_id, None)
                return None
            return deepcopy(session)

    def authenticate_interaction_session(
        self,
        session_id: str,
        access_token: str,
        *,
        now: datetime | None = None,
    ) -> ReportInteractionSession:
        with self._lock:
            session = self.interaction_sessions.get(session_id)
            if session is None:
                raise InteractionSessionNotFound("Interaction session was not found")
            current = _as_aware(now) if now is not None else datetime.now(UTC)
            if session.expires_at <= current:
                self.interaction_sessions.pop(session_id, None)
                raise InteractionSessionExpired("Interaction session has expired")
            if not hmac.compare_digest(session.access_token_hash, _token_digest(access_token)):
                raise InteractionSessionUnauthorized("Interaction session token is invalid")
            return deepcopy(session)

    get_interaction_session_for_token = authenticate_interaction_session
    get_report_interaction_session = get_interaction_session

    def update_interaction_session(
        self,
        session_id: str,
        access_token: str,
        *,
        expected_revision: int,
        state: dict[str, Any],
        recommendation_baseline: dict[str, Any] | None = None,
        history_cutoff: int | None = None,
        now: datetime | None = None,
    ) -> ReportInteractionSession:
        with self._lock:
            current = self.authenticate_interaction_session(session_id, access_token, now=now)
            stored = self.interaction_sessions.get(session_id)
            assert stored is not None
            if current.revision != expected_revision:
                raise InteractionRevisionConflict(expected_revision, current.revision)
            if recommendation_baseline is not None:
                if stored.recommendation_baseline and stored.recommendation_baseline != recommendation_baseline:
                    raise ValueError("Recommendation baseline is already locked")
                if not stored.recommendation_baseline:
                    stored.recommendation_baseline = deepcopy(recommendation_baseline)
                    if history_cutoff is not None:
                        stored.history_cutoff = int(history_cutoff)
            stored.state = deepcopy(state)
            stored.revision += 1
            stored.updated_at = _as_aware(now) if now is not None else datetime.now(UTC)
            return deepcopy(stored)

    def record_interaction_follow_up(
        self,
        session_id: str,
        access_token: str,
        *,
        follow_up: dict[str, Any],
        now: datetime | None = None,
    ) -> ReportInteractionSession:
        with self._lock:
            self.authenticate_interaction_session(session_id, access_token, now=now)
            stored = self.interaction_sessions.get(session_id)
            assert stored is not None
            state = deepcopy(stored.state)
            observed = state.get("observed")
            observed_state = deepcopy(observed) if isinstance(observed, dict) else {}
            observed_state["follow_up"] = deepcopy(follow_up)
            state["observed"] = observed_state
            stored.state = state
            stored.revision += 1
            stored.updated_at = _as_aware(now) if now is not None else datetime.now(UTC)
            return deepcopy(stored)

    update_report_interaction_session = update_interaction_session

    def delete_interaction_session(self, session_id: str, access_token: str) -> None:
        with self._lock:
            self.authenticate_interaction_session(session_id, access_token)
            self.interaction_sessions.pop(session_id, None)

    delete_report_interaction_session = delete_interaction_session

    def purge_expired_interaction_sessions(self, *, now: datetime | None = None) -> int:
        current = _as_aware(now) if now is not None else datetime.now(UTC)
        with self._lock:
            expired = [
                session_id
                for session_id, session in self.interaction_sessions.items()
                if session.expires_at <= current
            ]
            for session_id in expired:
                self.interaction_sessions.pop(session_id, None)
            return len(expired)


class SqlAlchemyRepository:
    """Persistent repository used by production API and worker processes."""

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self.engine = create_database_engine(settings)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self._lock = threading.RLock()
        self.report_retention = timedelta(
            days=max(1, int(getattr(settings, "effective_report_retention_days", 30)))
        )
        self.interaction_retention = timedelta(
            days=max(1, int(getattr(settings, "effective_report_interaction_retention_days", 90)))
        )

    def check_ready(self) -> None:
        check_database_revision(self.engine)

    def current_revision(self) -> str | None:
        return current_database_revision(self.engine)

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
            parent_report_id=getattr(record, "parent_report_id", None),
            diagnostic_question_id=getattr(record, "diagnostic_question_id", None),
            entitlement_decision=deepcopy(getattr(record, "entitlement_decision_json", None)),
            selection_plan=deepcopy(getattr(record, "selection_plan_json", None)),
            stopping_reason=getattr(record, "stopping_reason", None),
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
        record.parent_report_id = job.parent_report_id
        record.diagnostic_question_id = job.diagnostic_question_id
        record.entitlement_decision_json = deepcopy(job.entitlement_decision)
        record.selection_plan_json = deepcopy(job.selection_plan)
        record.stopping_reason = job.stopping_reason
        record.updated_at = job.updated_at
        record.events_json = [event.as_dict() for event in job.events]

    def create_job(
        self,
        account_id: int,
        canonical_player: str,
        model_version: str,
        analysis_mode: str = "free",
        *,
        parent_report_id: str | None = None,
        diagnostic_question_id: str | None = None,
        entitlement_decision: dict[str, Any] | None = None,
        selection_plan: dict[str, Any] | None = None,
        stopping_reason: str | None = None,
    ) -> AnalysisJob:
        job = AnalysisJob(
            str(uuid4()),
            account_id,
            canonical_player,
            analysis_mode=analysis_mode,
            parent_report_id=parent_report_id,
            diagnostic_question_id=diagnostic_question_id,
            entitlement_decision=deepcopy(entitlement_decision),
            selection_plan=deepcopy(selection_plan),
            stopping_reason=stopping_reason,
            model_version=model_version,
        )
        with self._session_factory() as session:
            session.add(
                AnalysisJobRecord(
                    job_id=job.job_id,
                    account_id=account_id,
                    canonical_player=canonical_player,
                    analysis_mode=analysis_mode,
                    # Explicit jobs (including a user-selected Deep
                    # continuation) are not an idempotent request key.  The
                    # coalescing path uses ``get_or_create_inflight_job``.
                    active_key=None,
                    status=job.status,
                    stage=job.stage,
                    warnings_json=[],
                    events_json=[],
                    parent_report_id=parent_report_id,
                    diagnostic_question_id=diagnostic_question_id,
                    entitlement_decision_json=deepcopy(entitlement_decision),
                    selection_plan_json=deepcopy(selection_plan),
                    stopping_reason=stopping_reason,
                    model_version=model_version,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                )
            )
            session.commit()
        return job

    def find_active_deep_job(
        self, report_id: str, diagnostic_question_id: str, account_id: int, grant_id: str
    ) -> AnalysisJob | None:
        with self._session_factory() as session:
            records = session.scalars(
                select(AnalysisJobRecord).where(
                    AnalysisJobRecord.parent_report_id == report_id,
                    AnalysisJobRecord.diagnostic_question_id == diagnostic_question_id,
                    AnalysisJobRecord.account_id == account_id,
                    AnalysisJobRecord.analysis_mode == "deep_scan",
                    AnalysisJobRecord.status.in_(("queued", "running")),
                )
            ).all()
            for record in records:
                if (record.entitlement_decision_json or {}).get("grant_id") == grant_id:
                    return self._job_from_record(record)
        return None

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
        raw_history_hash: str | None = None,
        identity_fingerprint: str | None = None,
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
            if raw_history_hash is not None and job.report_id:
                report = self.get_report(job.report_id)
                stored_hash = ((report or {}).get("metadata") or {}).get("raw_history_hash")
                if stored_hash != raw_history_hash:
                    return None
            if identity_fingerprint is not None and job.report_id:
                report = self.get_report(job.report_id) or {}
                if _report_identity_fingerprint(report) != identity_fingerprint:
                    return None
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

    def get_cached_raw_payload(
        self,
        endpoint: str,
        source_id: str,
        *,
        max_age_seconds: int | None = None,
    ) -> Any | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(RawPayloadRecord)
                .where(
                    RawPayloadRecord.endpoint == endpoint,
                    RawPayloadRecord.source_id == str(source_id),
                )
                .order_by(RawPayloadRecord.fetched_at.desc())
            )
            if record is None:
                return None
            if max_age_seconds is not None:
                fetched_at = _as_aware(record.fetched_at)
                if (
                    datetime.now(UTC) - fetched_at
                ).total_seconds() > max(0, max_age_seconds):
                    return None
            return record.payload_json

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

    def save_report_with_protected_cohorts(
        self,
        *,
        account_id: int,
        data_cutoff: int | None,
        model_version: str,
        template_version: str,
        report: dict[str, Any],
        evidence: list[EvidenceObject],
        protected_cohorts: dict[str, Any],
    ) -> str:
        report_id = str(uuid4())
        created_at = datetime.now(UTC)
        expires_at = created_at + self.report_retention
        report_json = deepcopy(report)
        report_json["metadata"] = {
            **dict(report_json.get("metadata") or {}),
            "expires_at": expires_at.isoformat(),
        }
        endpoint = f"internal://reports/{report_id}/protected-deep-cohorts"
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
            session.add(
                RawPayloadRecord(
                    endpoint=endpoint,
                    source_id=report_id,
                    payload_hash=payload_hash(protected_cohorts),
                    payload_json=deepcopy(protected_cohorts),
                    metadata_json={"private": True, "schema_version": "protected-deep-cohort-1.0.0"},
                    fetched_at=created_at,
                )
            )
            session.commit()
        return report_id

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        with self._session_factory() as session:
            record = session.get(ReportRecord, report_id)
            if record is None:
                return None
            if _expired((record.report_json or {}).get("metadata", {}).get("expires_at")) or (
                _as_aware(record.created_at) + self.report_retention <= datetime.now(UTC)
            ):
                return None
            return {
                **dict(record.report_json or {}),
                "report_id": record.report_id,
            }

    def purge_expired(self, *, now: datetime | None = None) -> int:
        current = _as_aware(now) if now is not None else datetime.now(UTC)
        cutoff = current - self.report_retention
        with self._session_factory() as session:
            reports = session.scalars(select(ReportRecord)).all()
            expired = [
                record.report_id
                for record in reports
                if _expired((record.report_json or {}).get("metadata", {}).get("expires_at"), now=current)
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
            session.execute(
                delete(ReportInteractionSessionRecord).where(
                    ReportInteractionSessionRecord.expires_at <= current
                )
            )
            session.commit()
            return len(expired)

    def get_evidence(self, report_id: str, insight_id: str | None = None) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            query = select(EvidenceObjectRecord).where(EvidenceObjectRecord.report_id == report_id)
            if insight_id is not None:
                query = query.where(EvidenceObjectRecord.insight_id == insight_id)
            return [dict(record.evidence_json or {}) for record in session.scalars(query).all()]

    # --- v6 report interaction state -------------------------------------

    def get_report_owner(self, report_id: str) -> int | None:
        with self._session_factory() as session:
            record = session.get(ReportRecord, report_id)
            return int(record.account_id) if record is not None else None

    def get_report_cutoff(self, report_id: str) -> int | None:
        with self._session_factory() as session:
            record = session.get(ReportRecord, report_id)
            if record is None:
                return None
            if record.data_cutoff is not None:
                return int(record.data_cutoff)
            report = record.report_json or {}
            for source in (report.get("metadata") or {}, report):
                for key in ("history_cutoff", "data_cutoff", "cutoff"):
                    value = source.get(key)
                    try:
                        if value is not None:
                            return int(value)
                    except (TypeError, ValueError):
                        continue
            return None

    def persist_protected_cohorts(
        self, report_id: str, cohorts: dict[str, Any]
    ) -> None:
        if self.get_report(report_id) is None:
            raise InteractionSessionNotFound("Report was not found")
        self.persist_raw_payload(
            f"internal://reports/{report_id}/protected-deep-cohorts",
            report_id,
            deepcopy(cohorts),
            metadata={"private": True, "schema_version": "protected-deep-cohort-1.0.0"},
        )

    def resolve_protected_cohort(
        self, report_id: str, cohort_reference: str
    ) -> dict[str, Any] | None:
        cohorts = self.get_cached_raw_payload(
            f"internal://reports/{report_id}/protected-deep-cohorts", report_id
        )
        if not isinstance(cohorts, dict):
            return None
        value = cohorts.get(cohort_reference)
        return deepcopy(value) if isinstance(value, dict) else None

    @staticmethod
    def _interaction_from_record(
        record: ReportInteractionSessionRecord,
    ) -> ReportInteractionSession:
        return ReportInteractionSession(
            session_id=record.session_id,
            report_id=record.report_id,
            account_id=record.account_id,
            state_schema_version=record.state_schema_version,
            revision=record.revision,
            state=deepcopy(record.state_json or {}),
            recommendation_baseline=deepcopy(record.recommendation_baseline_json or {}),
            history_cutoff=record.history_cutoff,
            created_at=_as_aware(record.created_at),
            updated_at=_as_aware(record.updated_at),
            expires_at=_as_aware(record.expires_at),
            access_token_hash=record.access_token_hash,
        )

    def create_interaction_session(
        self,
        report_id: str,
        *,
        account_id: int | None = None,
        state: dict[str, Any] | None = None,
        recommendation_baseline: dict[str, Any] | None = None,
        history_cutoff: int | None = None,
        state_schema_version: str = INTERACTION_STATE_SCHEMA_VERSION,
        now: datetime | None = None,
    ) -> tuple[ReportInteractionSession, str]:
        owner = account_id if account_id is not None else self.get_report_owner(report_id)
        if owner is None or self.get_report(report_id) is None:
            raise InteractionSessionNotFound("Report was not found")
        token, token_hash = _new_access_token()
        created_at = _as_aware(now) if now is not None else datetime.now(UTC)
        cutoff = history_cutoff if history_cutoff is not None else self.get_report_cutoff(report_id)
        session_value = ReportInteractionSession(
            session_id=str(uuid4()),
            report_id=report_id,
            account_id=int(owner),
            state_schema_version=state_schema_version,
            revision=1,
            state=deepcopy(state or {}),
            recommendation_baseline=deepcopy(recommendation_baseline or {}),
            history_cutoff=cutoff,
            created_at=created_at,
            updated_at=created_at,
            expires_at=created_at + self.interaction_retention,
            access_token_hash=token_hash,
        )
        with self._session_factory() as session:
            session.add(
                ReportInteractionSessionRecord(
                    session_id=session_value.session_id,
                    report_id=report_id,
                    account_id=int(owner),
                    access_token_hash=token_hash,
                    state_schema_version=state_schema_version,
                    revision=1,
                    state_json=deepcopy(state or {}),
                    recommendation_baseline_json=deepcopy(recommendation_baseline or {}),
                    history_cutoff=cutoff,
                    created_at=created_at,
                    updated_at=created_at,
                    expires_at=session_value.expires_at,
                )
            )
            session.commit()
        return deepcopy(session_value), token

    create_report_interaction_session = create_interaction_session

    def get_interaction_session(
        self, session_id: str, *, now: datetime | None = None
    ) -> ReportInteractionSession | None:
        current = _as_aware(now) if now is not None else datetime.now(UTC)
        with self._session_factory() as session:
            record = session.get(ReportInteractionSessionRecord, session_id)
            if record is None:
                return None
            if _as_aware(record.expires_at) <= current:
                session.delete(record)
                session.commit()
                return None
            return self._interaction_from_record(record)

    def authenticate_interaction_session(
        self,
        session_id: str,
        access_token: str,
        *,
        now: datetime | None = None,
    ) -> ReportInteractionSession:
        current = _as_aware(now) if now is not None else datetime.now(UTC)
        with self._session_factory() as session:
            record = session.get(ReportInteractionSessionRecord, session_id)
            if record is None:
                raise InteractionSessionNotFound("Interaction session was not found")
            if _as_aware(record.expires_at) <= current:
                session.delete(record)
                session.commit()
                raise InteractionSessionExpired("Interaction session has expired")
            if not hmac.compare_digest(record.access_token_hash, _token_digest(access_token)):
                raise InteractionSessionUnauthorized("Interaction session token is invalid")
            return self._interaction_from_record(record)

    get_interaction_session_for_token = authenticate_interaction_session

    def update_interaction_session(
        self,
        session_id: str,
        access_token: str,
        *,
        expected_revision: int,
        state: dict[str, Any],
        recommendation_baseline: dict[str, Any] | None = None,
        history_cutoff: int | None = None,
        now: datetime | None = None,
    ) -> ReportInteractionSession:
        current = _as_aware(now) if now is not None else datetime.now(UTC)
        with self._session_factory() as session:
            record = session.get(ReportInteractionSessionRecord, session_id)
            if record is None:
                raise InteractionSessionNotFound("Interaction session was not found")
            if _as_aware(record.expires_at) <= current:
                session.delete(record)
                session.commit()
                raise InteractionSessionExpired("Interaction session has expired")
            if not hmac.compare_digest(record.access_token_hash, _token_digest(access_token)):
                raise InteractionSessionUnauthorized("Interaction session token is invalid")
            if record.revision != expected_revision:
                raise InteractionRevisionConflict(expected_revision, record.revision)
            if recommendation_baseline is not None:
                current_baseline = deepcopy(record.recommendation_baseline_json or {})
                if current_baseline and current_baseline != recommendation_baseline:
                    raise ValueError("Recommendation baseline is already locked")
                if not current_baseline:
                    record.recommendation_baseline_json = deepcopy(recommendation_baseline)
                    if history_cutoff is not None:
                        record.history_cutoff = int(history_cutoff)
            record.state_json = deepcopy(state)
            record.revision += 1
            record.updated_at = current
            session.commit()
            return self._interaction_from_record(record)

    def record_interaction_follow_up(
        self,
        session_id: str,
        access_token: str,
        *,
        follow_up: dict[str, Any],
        now: datetime | None = None,
    ) -> ReportInteractionSession:
        current = _as_aware(now) if now is not None else datetime.now(UTC)
        with self._session_factory() as session:
            record = session.get(ReportInteractionSessionRecord, session_id)
            if record is None:
                raise InteractionSessionNotFound("Interaction session was not found")
            if _as_aware(record.expires_at) <= current:
                session.delete(record)
                session.commit()
                raise InteractionSessionExpired("Interaction session has expired")
            if not hmac.compare_digest(record.access_token_hash, _token_digest(access_token)):
                raise InteractionSessionUnauthorized("Interaction session token is invalid")
            state = deepcopy(record.state_json or {})
            observed = state.get("observed")
            observed_state = deepcopy(observed) if isinstance(observed, dict) else {}
            observed_state["follow_up"] = deepcopy(follow_up)
            state["observed"] = observed_state
            record.state_json = state
            record.revision += 1
            record.updated_at = current
            session.commit()
            return self._interaction_from_record(record)

    def delete_interaction_session(self, session_id: str, access_token: str) -> None:
        with self._session_factory() as session:
            record = session.get(ReportInteractionSessionRecord, session_id)
            if record is None:
                raise InteractionSessionNotFound("Interaction session was not found")
            if _as_aware(record.expires_at) <= datetime.now(UTC):
                session.delete(record)
                session.commit()
                raise InteractionSessionExpired("Interaction session has expired")
            if not hmac.compare_digest(record.access_token_hash, _token_digest(access_token)):
                raise InteractionSessionUnauthorized("Interaction session token is invalid")
            session.delete(record)
            session.commit()

    def purge_expired_interaction_sessions(self, *, now: datetime | None = None) -> int:
        current = _as_aware(now) if now is not None else datetime.now(UTC)
        with self._session_factory() as session:
            records = session.scalars(select(ReportInteractionSessionRecord)).all()
            expired = [
                record.session_id
                for record in records
                if _as_aware(record.expires_at) <= current
            ]
            if expired:
                session.execute(
                    delete(ReportInteractionSessionRecord).where(
                        ReportInteractionSessionRecord.session_id.in_(expired)
                    )
                )
                session.commit()
            return len(expired)


def _as_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _mark_stage_complete(job: AnalysisJob, stage: str | None) -> None:
    if stage and stage not in {"queued", "completed", "failed"} and stage not in job.completed_stages:
        job.completed_stages.append(stage)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return _as_aware(value)
    if not isinstance(value, str):
        return None
    try:
        return _as_aware(datetime.fromisoformat(value))
    except ValueError:
        return None


def _expired(value: Any, *, now: datetime | None = None) -> bool:
    parsed = _parse_datetime(value)
    return parsed is not None and parsed <= (now or datetime.now(UTC))


def _report_identity_fingerprint(report: dict[str, Any]) -> str:
    identity = report.get("identity") or {}
    public = {
        "display_name": identity.get("display_name") or identity.get("personaname") or "Anonymous player",
        "avatar_url": identity.get("avatar_url") or identity.get("avatarfull"),
        "rank_tier": identity.get("rank_tier"),
    }
    return hashlib.sha256(
        json.dumps(public, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

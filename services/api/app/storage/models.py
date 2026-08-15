from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class PlayerRecord(Base):
    __tablename__ = "players"
    account_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)
    current_rank_tier: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MatchRecord(Base):
    __tablename__ = "matches"
    match_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_time: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    game_mode: Mapped[int | None] = mapped_column(Integer)
    lobby_type: Mapped[int | None] = mapped_column(Integer)
    patch: Mapped[str | None] = mapped_column(String(32))
    radiant_win: Mapped[bool | None] = mapped_column()
    eligibility_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)


class MatchParticipantRecord(Base):
    __tablename__ = "match_participants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.match_id"), index=True)
    account_id: Mapped[int | None] = mapped_column(Integer, index=True)
    player_slot: Mapped[int | None] = mapped_column(Integer)
    hero_id: Mapped[int | None] = mapped_column(Integer)
    inferred_role: Mapped[int | None] = mapped_column(Integer)
    role_probability: Mapped[float] = mapped_column(Float)
    facts_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)


class MatchTimeSeriesRecord(Base):
    __tablename__ = "match_time_series"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.match_id"), index=True)
    family: Mapped[str] = mapped_column(String(64))
    minute: Mapped[int] = mapped_column(Integer)
    value: Mapped[float] = mapped_column(Float)


class MatchEventRecord(Base):
    __tablename__ = "match_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.match_id"), index=True)
    account_id: Mapped[int | None] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(64))
    time_seconds: Mapped[int | None] = mapped_column(Integer)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)


class TeamfightRecord(Base):
    __tablename__ = "teamfights"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.match_id"), index=True)
    start_seconds: Mapped[int | None] = mapped_column(Integer)
    end_seconds: Mapped[int | None] = mapped_column(Integer)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)


class WardEventRecord(Base):
    __tablename__ = "ward_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.match_id"), index=True)
    account_id: Mapped[int | None] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(32))
    time_seconds: Mapped[int | None] = mapped_column(Integer)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)


class RawPayloadRecord(Base):
    __tablename__ = "raw_payloads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint: Mapped[str] = mapped_column(String(128), index=True)
    source_id: Mapped[str] = mapped_column(String(128), index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("endpoint", "source_id", "payload_hash"),)


class ParseCoverageRecord(Base):
    __tablename__ = "parse_coverage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.match_id"), index=True)
    parser_version: Mapped[int | None] = mapped_column(Integer)
    coverage_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)


class ConstantSnapshotRecord(Base):
    __tablename__ = "constant_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DerivedFeatureRecord(Base):
    __tablename__ = "derived_features"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feature_id: Mapped[str] = mapped_column(String(128), index=True)
    feature_version: Mapped[str] = mapped_column(String(32))
    entity_scope: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(128))
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT)
    denominator: Mapped[int | None] = mapped_column(Integer)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)


class CohortAggregateRecord(Base):
    __tablename__ = "cohort_aggregates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dimensions_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT)
    sample_size: Mapped[int] = mapped_column(Integer)
    distinct_player_count: Mapped[int] = mapped_column(Integer)
    estimates_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT)
    intervals_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict)


class AnalysisJobRecord(Base):
    __tablename__ = "analysis_jobs"
    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, index=True)
    canonical_player: Mapped[str] = mapped_column(String(300))
    analysis_mode: Mapped[str] = mapped_column(String(32), default="free")
    active_key: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32))
    stage: Mapped[str] = mapped_column(String(64))
    processed_matches: Mapped[int] = mapped_column(Integer, default=0)
    eligible_matches: Mapped[int] = mapped_column(Integer, default=0)
    warnings_json: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list)
    failure_code: Mapped[str | None] = mapped_column(String(64))
    failure_detail: Mapped[str | None] = mapped_column(String(500))
    events_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON_DOCUMENT, default=list)
    report_id: Mapped[str | None] = mapped_column(String(36), index=True)
    model_version: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReportRecord(Base):
    __tablename__ = "reports"
    report_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, index=True)
    data_cutoff: Mapped[int | None] = mapped_column(Integer)
    model_version: Mapped[str] = mapped_column(String(64))
    template_version: Mapped[str] = mapped_column(String(64))
    report_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvidenceObjectRecord(Base):
    __tablename__ = "evidence_objects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.report_id"), index=True)
    insight_id: Mapped[str] = mapped_column(String(128), index=True)
    concept_id: Mapped[str] = mapped_column(String(128))
    publication_status: Mapped[str] = mapped_column(String(32))
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT)
    source_match_ids: Mapped[list[int]] = mapped_column(JSON_DOCUMENT, default=list)

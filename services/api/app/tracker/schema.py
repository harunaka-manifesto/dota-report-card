"""Tracker's persisted boundaries. Migrations own DDL; no runtime create_all.

The tracker namespace keeps legacy report retention and initial migrations intact.
One tracker_matches row is the global canonical match for every tracked account.
Legacy matches are report-extraction records, never tracker canonical inputs.
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

users = Table(
    "tracker_users",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("state", String(24), nullable=False, server_default="ACTIVE"),
    Column("generation", BigInteger, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("deletion_requested_at", DateTime(timezone=True)),
    Column("notifications_enabled", Boolean, nullable=False, server_default=text("false")),
    CheckConstraint("state IN ('ACTIVE', 'DELETION_PENDING')", name="ck_tracker_user_state"),
    CheckConstraint("generation > 0", name="ck_tracker_user_generation"),
)
identities = Table(
    "tracker_identities",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", ForeignKey(users.c.id, ondelete="CASCADE"), nullable=False),
    Column("issuer", String(300), nullable=False),
    Column("subject", String(300), nullable=False),
    Column("verified_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("issuer", "subject"),
)
sessions = Table(
    "tracker_sessions",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", ForeignKey(users.c.id, ondelete="CASCADE"), nullable=False, index=True),
    Column("family_id", String(36), nullable=False, index=True),
    Column("refresh_hash", String(64), nullable=False, unique=True),
    Column("access_hash", String(64), nullable=False, unique=True),
    Column("user_generation", BigInteger, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("access_expires_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True)),
    Column("replaced_by", String(36)),
    CheckConstraint("expires_at > created_at", name="ck_tracker_session_expiry"),
)
devices = Table(
    "tracker_devices",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", ForeignKey(users.c.id, ondelete="CASCADE"), nullable=False, index=True),
    Column("push_token", Text),
    Column("permission", String(16), nullable=False),
    Column("last_active_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "permission IN ('UNKNOWN', 'GRANTED', 'DENIED')", name="ck_tracker_device_permission"
    ),
)
dota_accounts = Table(
    "tracker_dota_accounts",
    metadata,
    Column("account_id", BigInteger, primary_key=True, autoincrement=False),
    Column("display_name", String(300)),
    Column("visibility", String(24), nullable=False, server_default="UNKNOWN"),
    Column("tracked", Boolean, nullable=False, server_default=text("false")),
    CheckConstraint("account_id > 0 AND account_id <= 4294967295", name="ck_tracker_account_id"),
    CheckConstraint(
        "visibility IN ('UNKNOWN', 'ACCESSIBLE', 'BLOCKED')", name="ck_tracker_visibility"
    ),
)
profiles = Table(
    "tracker_profiles",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", ForeignKey(users.c.id, ondelete="CASCADE"), nullable=False),
    Column("account_id", ForeignKey(dota_accounts.c.account_id), nullable=False),
    Column("active", Boolean, nullable=False, server_default=text("true")),
    Column("original_linked_at", DateTime(timezone=True), nullable=False),
    Column("archived_at", DateTime(timezone=True)),
    Column("generation", BigInteger, nullable=False, server_default="1"),
    Column("active_revision", BigInteger, nullable=False, server_default="0"),
    Column("active_scope", String(8), nullable=False, server_default="FREE"),
    Column("favourite_hero_id", Integer),
    UniqueConstraint("user_id", "account_id"),
    UniqueConstraint("id", "account_id"),
    UniqueConstraint("id", "user_id", name="uq_tracker_profiles_id_user"),
    CheckConstraint("active_scope IN ('FREE', 'PRO')", name="ck_tracker_scope"),
    CheckConstraint("generation > 0 AND active_revision >= 0", name="ck_tracker_profile_revision"),
    Index("uq_tracker_active_user", "user_id", unique=True, postgresql_where=text("active")),
    Index("uq_tracker_active_account", "account_id", unique=True, postgresql_where=text("active")),
)
switches = Table(
    "tracker_switches",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", ForeignKey(users.c.id, ondelete="CASCADE"), nullable=False, index=True),
    Column("previous_profile_id", ForeignKey(profiles.c.id, ondelete="CASCADE"), nullable=False),
    Column("next_profile_id", ForeignKey(profiles.c.id, ondelete="CASCADE"), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=False),
    Column("dedup_key", String(200), nullable=False, unique=True),
)
follows = Table(
    "tracker_follows",
    metadata,
    Column("user_id", ForeignKey(users.c.id, ondelete="CASCADE"), primary_key=True),
    Column("account_id", ForeignKey(dota_accounts.c.account_id), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

matches = Table(
    "tracker_matches",
    metadata,
    Column("match_id", BigInteger, primary_key=True, autoincrement=False),
    Column("started_at", DateTime(timezone=True)),
    Column("duration_seconds", Integer),
    Column("mode", String(16)),
    Column("game_mode", Integer),
    Column("lobby_type", Integer),
    Column("patch", String(32)),
    Column("radiant_win", Boolean),
    Column("header", JSONB),
    Column("evidence_state", String(24), nullable=False, server_default="DISCOVERED"),
    Column("terminal_reason", String(64)),
    Column("discovered_at", DateTime(timezone=True), nullable=False),
    Column("summary_ready_at", DateTime(timezone=True)),
    Column("replay_requested_at", DateTime(timezone=True)),
    Column("replay_terminal_at", DateTime(timezone=True)),
    Column("quarantined_fields", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    CheckConstraint("match_id > 0", name="ck_tracker_match_id"),
    CheckConstraint("duration_seconds >= 0", name="ck_tracker_match_duration"),
    CheckConstraint("mode IN ('STANDARD', 'TURBO', 'UNSUPPORTED')", name="ck_tracker_match_mode"),
    CheckConstraint(
        "evidence_state IN ('DISCOVERED', 'SUMMARY_READY', 'REPLAY_PENDING', 'REPLAY_READY', 'REPLAY_UNAVAILABLE')",
        name="ck_tracker_evidence",
    ),
    CheckConstraint(
        "evidence_state = 'DISCOVERED' OR (started_at IS NOT NULL AND duration_seconds IS NOT NULL AND mode IS NOT NULL AND radiant_win IS NOT NULL AND header IS NOT NULL AND summary_ready_at IS NOT NULL)",
        name="ck_tracker_summary_header",
    ),
    CheckConstraint(
        "evidence_state != 'REPLAY_UNAVAILABLE' OR terminal_reason IS NOT NULL",
        name="ck_tracker_terminal_reason",
    ),
)
match_players = Table(
    "tracker_match_players",
    metadata,
    Column("match_id", ForeignKey(matches.c.match_id, ondelete="CASCADE"), primary_key=True),
    Column("player_slot", Integer, primary_key=True),
    Column("account_id", BigInteger),
    Column("hero_id", Integer, nullable=False),
    Column("team", String(8), nullable=False),
    Column("summary", JSONB, nullable=False),
    CheckConstraint("player_slot BETWEEN 0 AND 9", name="ck_tracker_player_slot"),
    CheckConstraint("hero_id > 0", name="ck_tracker_player_hero"),
    CheckConstraint(
        "(player_slot BETWEEN 0 AND 4 AND team = 'RADIANT') OR (player_slot BETWEEN 5 AND 9 AND team = 'DIRE')",
        name="ck_tracker_player_team",
    ),
)
account_matches = Table(
    "tracker_account_matches",
    metadata,
    Column("profile_id", String(36), primary_key=True),
    Column("match_id", ForeignKey(matches.c.match_id), primary_key=True),
    Column("account_id", BigInteger, nullable=False),
    Column("player_slot", Integer, nullable=False),
    Column("lifecycle", String(32), nullable=False, server_default="WAITING_FOR_PROVIDER"),
    Column("mode", String(16), nullable=False),
    Column("progression", String(16)),
    Column("progression_reason", String(64)),
    Column("provider_started_at", DateTime(timezone=True), nullable=False),
    Column("provider_source_match_id", BigInteger, nullable=False),
    Column("origin", String(16), nullable=False),
    Column("effective_role", String(16)),
    Column("role_revision", BigInteger, nullable=False, server_default="0"),
    Column("finalized_at", DateTime(timezone=True)),
    Column("active_analysis_id", String(36)),
    Column("attempt_count", Integer, nullable=False, server_default="0"),
    Column("retrying", Boolean, nullable=False, server_default=text("false")),
    Column("failure_stage", String(64)),
    Column("failure_reason", String(64)),
    ForeignKeyConstraint(
        ["profile_id", "account_id"], [profiles.c.id, profiles.c.account_id], ondelete="CASCADE"
    ),
    ForeignKeyConstraint(
        ["match_id", "player_slot"], [match_players.c.match_id, match_players.c.player_slot]
    ),
    CheckConstraint(
        "lifecycle IN ('WAITING_FOR_PROVIDER', 'ANALYZING', 'WAITING_FOR_PRIOR_MATCH', 'ACTION_REQUIRED', 'READY', 'UNAVAILABLE')",
        name="ck_tracker_lifecycle",
    ),
    CheckConstraint("mode IN ('STANDARD', 'TURBO', 'UNSUPPORTED')", name="ck_tracker_link_mode"),
    CheckConstraint("progression IN ('STANDARD', 'TURBO', 'NONE')", name="ck_tracker_progression"),
    CheckConstraint(
        "progression != 'NONE' OR progression_reason IS NOT NULL",
        name="ck_tracker_progression_reason",
    ),
    CheckConstraint(
        "origin IN ('LIVE', 'BOOTSTRAP', 'HISTORICAL', 'RECOVERY')", name="ck_tracker_origin"
    ),
    CheckConstraint(
        "effective_role IN ('CARRY', 'MID', 'OFFLANE', 'SUPPORT')", name="ck_tracker_effective_role"
    ),
    CheckConstraint(
        "lifecycle != 'READY' OR (finalized_at IS NOT NULL AND progression IS NOT NULL AND active_analysis_id IS NOT NULL)",
        name="ck_tracker_finalized",
    ),
    CheckConstraint("provider_source_match_id = match_id", name="ck_tracker_source_identity"),
    Index(
        "ix_tracker_chronology",
        "profile_id",
        "mode",
        "provider_started_at",
        "provider_source_match_id",
    ),
)
snapshots = Table(
    "tracker_provider_snapshots",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("provider", String(32), nullable=False),
    Column("operation", String(80), nullable=False),
    Column("operation_version", String(64), nullable=False),
    Column("schema_version", String(64), nullable=False),
    Column("subject", String(128), nullable=False),
    Column("digest", String(64), nullable=False),
    Column("byte_size", BigInteger, nullable=False),
    Column("fetched_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSONB),
    Column("storage_uri", Text),
    Column("provenance", JSONB, nullable=False),
    UniqueConstraint(
        "provider",
        "operation",
        "operation_version",
        "schema_version",
        "subject",
        "digest",
        name="uq_tracker_snapshot_identity",
    ),
    CheckConstraint("byte_size >= 0 AND length(digest) = 64", name="ck_tracker_snapshot_digest"),
    CheckConstraint(
        "(payload IS NULL) != (storage_uri IS NULL)", name="ck_tracker_snapshot_storage"
    ),
)
acquisitions = Table(
    "tracker_match_acquisition",
    metadata,
    Column("match_id", ForeignKey(matches.c.match_id, ondelete="CASCADE"), primary_key=True),
    Column("provider", String(32), primary_key=True),
    Column("operation", String(80), primary_key=True),
    Column("operation_version", String(64), nullable=False),
    Column("state", String(24), nullable=False),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("requested_at", DateTime(timezone=True)),
    Column("retry_after", DateTime(timezone=True)),
    Column("terminal_reason", String(64)),
    Column("snapshot_id", ForeignKey(snapshots.c.id)),
    CheckConstraint("attempts >= 0", name="ck_tracker_acquisition_attempts"),
)
derived_features = Table(
    "tracker_derived_features",
    metadata,
    Column("match_id", BigInteger, primary_key=True),
    Column("player_slot", Integer, primary_key=True),
    Column("feature_version", String(64), primary_key=True),
    Column("inputs_digest", String(64), primary_key=True),
    Column("features", JSONB, nullable=False),
    Column("provenance", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["match_id", "player_slot"], [match_players.c.match_id, match_players.c.player_slot]
    ),
)
positions = Table(
    "tracker_position_assignments",
    metadata,
    Column("match_id", BigInteger, primary_key=True),
    Column("player_slot", Integer, primary_key=True),
    Column("evidence_profile", String(16), primary_key=True),
    Column("version", String(64), primary_key=True),
    Column("inputs_digest", String(64), primary_key=True),
    Column("team", String(8), nullable=False),
    Column("position", Integer),
    Column("confidence", Float),
    Column("reason", String(64)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["match_id", "player_slot"], [match_players.c.match_id, match_players.c.player_slot]
    ),
    UniqueConstraint(
        "match_id",
        "team",
        "position",
        "evidence_profile",
        "version",
        "inputs_digest",
        name="uq_tracker_team_position",
    ),
    CheckConstraint("position BETWEEN 1 AND 5", name="ck_tracker_position"),
    CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_tracker_role_confidence"),
    CheckConstraint("evidence_profile IN ('SUMMARY', 'REPLAY')", name="ck_tracker_role_profile"),
)
role_assertions = Table(
    "tracker_role_assertions",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("profile_id", String(36), nullable=False),
    Column("match_id", BigInteger, nullable=False),
    Column("revision", BigInteger, nullable=False),
    Column("role", String(16), nullable=False),
    Column("asserted_at", DateTime(timezone=True), nullable=False),
    Column("provenance", JSONB, nullable=False),
    Column("dedup_key", String(200), nullable=False, unique=True),
    ForeignKeyConstraint(
        ["profile_id", "match_id"],
        [account_matches.c.profile_id, account_matches.c.match_id],
        ondelete="CASCADE",
    ),
    UniqueConstraint("profile_id", "match_id", "revision"),
    CheckConstraint(
        "role IN ('CARRY', 'MID', 'OFFLANE', 'SUPPORT')", name="ck_tracker_asserted_role"
    ),
)
parameter_sets = Table(
    "tracker_parameter_sets",
    metadata,
    Column("version", String(64), primary_key=True),
    Column("kind", String(32), nullable=False),
    Column("digest", String(64), nullable=False),
    Column("status", String(16), nullable=False),
    Column("parameters", JSONB, nullable=False),
    Column("provenance", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "status IN ('PROVISIONAL', 'APPROVED', 'TEST_ONLY')", name="ck_tracker_parameter_status"
    ),
)
analyses = Table(
    "tracker_analyses",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("profile_id", String(36), nullable=False),
    Column("match_id", BigInteger, nullable=False),
    Column("feature_version", String(64), nullable=False),
    Column("analysis_version", String(64), nullable=False),
    Column("baseline_version", String(64), nullable=False),
    Column("inputs_digest", String(64), nullable=False),
    Column("result", JSONB, nullable=False),
    Column("provenance", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["profile_id", "match_id"],
        [account_matches.c.profile_id, account_matches.c.match_id],
        ondelete="CASCADE",
    ),
    UniqueConstraint(
        "profile_id",
        "match_id",
        "analysis_version",
        "inputs_digest",
        name="uq_tracker_analysis_identity",
    ),
    UniqueConstraint("id", "profile_id", "match_id"),
    UniqueConstraint("id", "profile_id", name="uq_tracker_analyses_id_profile"),
)
account_matches.append_constraint(
    ForeignKeyConstraint(
        ["active_analysis_id", "profile_id", "match_id"],
        [analyses.c.id, analyses.c.profile_id, analyses.c.match_id],
        name="fk_tracker_active_analysis",
        use_alter=True,
    )
)
analysis_inputs = Table(
    "tracker_analysis_inputs",
    metadata,
    Column("analysis_id", ForeignKey(analyses.c.id, ondelete="CASCADE"), primary_key=True),
    Column("snapshot_id", ForeignKey(snapshots.c.id, ondelete="RESTRICT"), primary_key=True),
)
metric_observations = Table(
    "tracker_metric_observations",
    metadata,
    Column("analysis_id", ForeignKey(analyses.c.id, ondelete="CASCADE"), primary_key=True),
    Column("metric_id", String(100), primary_key=True),
    Column("metric_version", String(64), nullable=False),
    Column("raw_value", Float),
    Column("comparison_value", Float),
    Column("unavailable_reason", String(64)),
    Column("baseline_snapshot", JSONB, nullable=False),
    Column("context_h", Float),
    Column("context_e", Float),
    Column("parameter_set_version", ForeignKey(parameter_sets.c.version)),
    Column("performance_state", String(16)),
    CheckConstraint(
        "performance_state IN ('ABOVE', 'IN_LINE', 'BELOW', 'NOT_READY')",
        name="ck_tracker_performance",
    ),
    CheckConstraint(
        "(raw_value IS NOT NULL AND comparison_value IS NOT NULL AND unavailable_reason IS NULL) OR (raw_value IS NULL AND comparison_value IS NULL AND unavailable_reason IS NOT NULL)",
        name="ck_tracker_metric_absence",
    ),
)
insight_results = Table(
    "tracker_insight_results",
    metadata,
    Column("analysis_id", ForeignKey(analyses.c.id, ondelete="CASCADE"), primary_key=True),
    Column("contract_version", String(64), primary_key=True),
    Column("inputs_digest", String(64), primary_key=True),
    Column("cards", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "jsonb_typeof(cards) = 'array' AND jsonb_array_length(cards) <= 3",
        name="ck_tracker_insight_count",
    ),
)
# Revision-scoped rows allow a rebuild to publish by moving one profile pointer.
baselines = Table(
    "tracker_baselines",
    metadata,
    Column("profile_id", ForeignKey(profiles.c.id, ondelete="CASCADE"), primary_key=True),
    Column("revision", BigInteger, primary_key=True),
    Column("mode", String(16), primary_key=True),
    Column("role", String(16), primary_key=True),
    Column("metric_id", String(100), primary_key=True),
    Column("metric_version", String(64), primary_key=True),
    Column("baseline_version", String(64), nullable=False),
    Column("snapshot", JSONB, nullable=False),
)
personal_bests = Table(
    "tracker_personal_bests",
    metadata,
    Column("profile_id", ForeignKey(profiles.c.id, ondelete="CASCADE"), primary_key=True),
    Column("revision", BigInteger, primary_key=True),
    Column("mode", String(16), primary_key=True),
    Column("role", String(16), primary_key=True),
    Column("metric_id", String(100), primary_key=True),
    Column("metric_version", String(64), primary_key=True),
    Column("analysis_id", ForeignKey(analyses.c.id, ondelete="CASCADE"), nullable=False),
    Column("comparison_value", Float, nullable=False),
)
profile_claims = Table(
    "tracker_profile_claims",
    metadata,
    Column("profile_id", ForeignKey(profiles.c.id, ondelete="CASCADE"), primary_key=True),
    Column("revision", BigInteger, primary_key=True),
    Column("mode", String(16), primary_key=True),
    Column("scope", String(80), primary_key=True),
    Column("claim_id", String(80), primary_key=True),
    Column("claim_version", String(64), primary_key=True),
    Column("state", String(16), nullable=False),
    Column("state_since", DateTime(timezone=True), nullable=False),
    Column("evidence", JSONB, nullable=False),
    Column("persistence", JSONB, nullable=False),
    CheckConstraint(
        "state IN ('CANDIDATE', 'CONFIRMED', 'FADING', 'RETIRED')", name="ck_tracker_claim_state"
    ),
)
events = Table(
    "tracker_events",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("profile_id", ForeignKey(profiles.c.id, ondelete="CASCADE"), nullable=False, index=True),
    Column("kind", String(40), nullable=False),
    Column("dedup_key", String(240), nullable=False, unique=True),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
notification_outbox = Table(
    "tracker_notification_outbox",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", ForeignKey(users.c.id, ondelete="CASCADE"), nullable=False),
    Column("profile_id", ForeignKey(profiles.c.id, ondelete="CASCADE"), nullable=False),
    Column("user_generation", BigInteger, nullable=False),
    Column("dedup_key", String(240), nullable=False, unique=True),
    Column("event_refs", JSONB, nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("state", String(16), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("sent_at", DateTime(timezone=True)),
    CheckConstraint(
        "state IN ('PENDING', 'SENT', 'SUPPRESSED', 'CANCELLED')",
        name="ck_tracker_notification_state",
    ),
)
shares = Table(
    "tracker_shares",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("profile_id", ForeignKey(profiles.c.id, ondelete="CASCADE"), nullable=False, index=True),
    Column("snapshot_version", String(64), nullable=False),
    Column("projection", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

sync_state = Table(
    "tracker_sync_state",
    metadata,
    Column(
        "account_id", ForeignKey(dota_accounts.c.account_id, ondelete="CASCADE"), primary_key=True
    ),
    Column("provider", String(32), primary_key=True),
    Column("state", String(16), nullable=False),
    Column("cursor", JSONB),
    Column("last_checked_at", DateTime(timezone=True)),
    Column("last_complete_at", DateTime(timezone=True)),
    Column("source_updated_at", DateTime(timezone=True)),
    Column("retry_after", DateTime(timezone=True)),
    Column("failure_count", Integer, nullable=False, server_default="0"),
    Column("blocked_reason", String(64)),
    CheckConstraint(
        "state IN ('IDLE', 'CHECKING', 'UP_TO_DATE', 'SYNC_ERROR')", name="ck_tracker_sync_state"
    ),
)
discoveries = Table(
    "tracker_discoveries",
    metadata,
    Column("profile_id", ForeignKey(profiles.c.id, ondelete="CASCADE"), primary_key=True),
    Column("provider", String(32), primary_key=True),
    Column("source_item_id", String(128), primary_key=True),
    Column("outcome", String(16), nullable=False),
    Column("reason", String(64)),
    Column("match_id", ForeignKey(matches.c.match_id)),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "outcome IN ('ACCEPTED', 'REJECTED', 'TERMINAL')", name="ck_tracker_discovery_outcome"
    ),
)
coverage = Table(
    "tracker_coverage",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("profile_id", ForeignKey(profiles.c.id, ondelete="CASCADE"), nullable=False),
    Column("mode", String(16), nullable=False),
    Column("evidence_class", String(16), nullable=False),
    Column("start_at", DateTime(timezone=True), nullable=False),
    Column("end_at", DateTime(timezone=True), nullable=False),
    Column("state", String(16), nullable=False),
    Column("reason", String(64)),
    UniqueConstraint("profile_id", "mode", "evidence_class", "start_at", "end_at"),
    CheckConstraint("end_at >= start_at", name="ck_tracker_coverage_interval"),
    CheckConstraint("mode IN ('STANDARD', 'TURBO')", name="ck_tracker_coverage_mode"),
    CheckConstraint("evidence_class IN ('SUMMARY', 'REPLAY')", name="ck_tracker_coverage_class"),
    CheckConstraint("state IN ('KNOWN', 'GAP', 'PENDING')", name="ck_tracker_coverage_state"),
)
bootstrap = Table(
    "tracker_bootstrap",
    metadata,
    Column("profile_id", ForeignKey(profiles.c.id, ondelete="CASCADE"), primary_key=True),
    Column("mode", String(16), primary_key=True),
    Column("search_finished", Boolean, nullable=False, server_default=text("false")),
    Column("cursor", JSONB),
    Column("discovered_count", Integer, nullable=False, server_default="0"),
    Column("eligible_count", Integer, nullable=False, server_default="0"),
    Column("settled_count", Integer, nullable=False, server_default="0"),
    Column("outcome", String(32)),
    Column("completed_at", DateTime(timezone=True)),
    CheckConstraint("mode IN ('STANDARD', 'TURBO')", name="ck_tracker_bootstrap_mode"),
    CheckConstraint(
        "outcome IN ('NO_STEAM_LINKED', 'DATA_ACCESS_BLOCKED', 'NO_MATCHES_FOUND', 'NO_ELIGIBLE_MATCHES', 'READY', 'READY_WITH_GAPS')",
        name="ck_tracker_bootstrap_outcome",
    ),
    CheckConstraint(
        "discovered_count >= settled_count AND settled_count >= 0 AND eligible_count >= 0 AND eligible_count <= discovered_count",
        name="ck_tracker_bootstrap_counts",
    ),
    CheckConstraint(
        "completed_at IS NULL OR (search_finished AND settled_count = discovered_count AND outcome IS NOT NULL)",
        name="ck_tracker_bootstrap_terminal",
    ),
)
ingest_jobs = Table(
    "tracker_ingest_jobs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("dedup_key", String(240), nullable=False, unique=True),
    Column("job_type", String(64), nullable=False),
    Column("priority", Integer, nullable=False),
    Column("match_id", ForeignKey(matches.c.match_id)),
    Column("account_id", ForeignKey(dota_accounts.c.account_id)),
    Column("user_id", ForeignKey(users.c.id, ondelete="CASCADE")),
    Column("profile_id", ForeignKey(profiles.c.id, ondelete="CASCADE")),
    Column("user_generation", BigInteger),
    Column("profile_generation", BigInteger),
    Column("state", String(16), nullable=False, server_default="PENDING"),
    Column("run_after", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("lease_token", String(36)),
    Column("lease_until", DateTime(timezone=True)),
    Column("cursor", JSONB),
    Column("payload", JSONB, nullable=False),
    Column("last_error", String(64)),
    CheckConstraint("priority BETWEEN 0 AND 3", name="ck_tracker_priority"),
    CheckConstraint(
        "state IN ('PENDING', 'RUNNING', 'COMPLETE', 'FAILED', 'CANCELLED')",
        name="ck_tracker_job_state",
    ),
    CheckConstraint("attempts >= 0", name="ck_tracker_job_attempts"),
    CheckConstraint(
        "(user_id IS NULL) = (user_generation IS NULL)", name="ck_tracker_job_user_fence"
    ),
    CheckConstraint(
        "(profile_id IS NULL) = (profile_generation IS NULL)", name="ck_tracker_job_profile_fence"
    ),
    Index(
        "ix_tracker_due_work", "priority", "run_after", postgresql_where=text("state = 'PENDING'")
    ),
)
provider_calls = Table(
    "tracker_provider_calls",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("provider", String(32), nullable=False),
    Column("operation", String(80), nullable=False),
    Column("operation_version", String(64), nullable=False),
    Column("match_id", BigInteger),
    Column("account_id", BigInteger),
    Column("job_id", ForeignKey(ingest_jobs.c.id, ondelete="SET NULL")),
    Column("snapshot_id", ForeignKey(snapshots.c.id, ondelete="SET NULL")),
    Column("request_subject", String(128)),
    Column("status", Integer),
    Column("latency_ms", Float, nullable=False),
    Column("billed_units", Integer, nullable=False),
    Column("rate_units", Integer, nullable=False),
    Column("called_at", DateTime(timezone=True), nullable=False),
    Column("failure_code", String(64)),
    Index("ix_tracker_call_job_subject", "job_id", "request_subject"),
    CheckConstraint(
        "latency_ms >= 0 AND billed_units >= 0 AND rate_units >= 0",
        name="ck_tracker_call_accounting",
    ),
)
account_discoveries = Table(
    "tracker_account_discoveries",
    metadata,
    Column("account_id", ForeignKey(dota_accounts.c.account_id, ondelete="CASCADE"), primary_key=True),
    Column("provider", String(32), primary_key=True),
    Column("source_item_id", String(128), primary_key=True),
    Column("snapshot_id", ForeignKey(snapshots.c.id), nullable=False),
    Column("match_id", ForeignKey(matches.c.match_id)),
    Column("source_started_at", DateTime(timezone=True)),
    Column("outcome", String(16), nullable=False),
    Column("reason", String(64)),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("outcome IN ('ACCEPTED', 'REJECTED', 'TERMINAL')", name="ck_tracker_account_discovery_outcome"),
    CheckConstraint("outcome = 'ACCEPTED' OR reason IS NOT NULL", name="ck_tracker_account_discovery_reason"),
)
subscriptions = Table(
    "tracker_subscriptions",
    metadata,
    Column("original_transaction_id", String(128), primary_key=True),
    Column("user_id", ForeignKey(users.c.id, ondelete="CASCADE"), nullable=False, index=True),
    Column("product_id", String(128), nullable=False),
    Column("environment", String(16), nullable=False),
    Column("state", String(24), nullable=False),
    Column("signed_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True)),
    Column("auto_renew", Boolean),
    Column("verification_digest", String(64), nullable=False),
)
history_operations = Table(
    "tracker_history_operations",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("profile_id", ForeignKey(profiles.c.id, ondelete="CASCADE"), nullable=False),
    Column("kind", String(32), nullable=False),
    Column("state", String(16), nullable=False),
    Column("target_scope", String(8), nullable=False),
    Column("target_revision", BigInteger, nullable=False),
    Column("cutoff_started_at", DateTime(timezone=True)),
    Column("cutoff_match_id", BigInteger),
    Column("cursor", JSONB),
    Column("dependency_scope", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True)),
    Column("dedup_key", String(240), nullable=False, unique=True),
    CheckConstraint("target_scope IN ('FREE', 'PRO')", name="ck_tracker_operation_scope"),
    CheckConstraint(
        "state IN ('PENDING', 'RUNNING', 'COMPLETE', 'FAILED', 'CANCELLED')",
        name="ck_tracker_operation_state",
    ),
    Index(
        "uq_tracker_active_rebuild",
        "profile_id",
        unique=True,
        postgresql_where=text("state IN ('PENDING', 'RUNNING')"),
    ),
)
idempotency_keys = Table(
    "tracker_idempotency_keys",
    metadata,
    Column("user_id", ForeignKey(users.c.id, ondelete="CASCADE"), primary_key=True),
    Column("operation", String(100), primary_key=True),
    Column("key", String(200), primary_key=True),
    Column("request_digest", String(64), nullable=False),
    Column("response", JSONB, nullable=False),
    Column("status_code", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

for table in (baselines, personal_bests):
    table.append_constraint(
        CheckConstraint(
            "mode IN ('STANDARD', 'TURBO')",
            name=f"ck_{table.name}_mode",
        )
    )
    table.append_constraint(
        CheckConstraint(
            "role IN ('CARRY', 'MID', 'OFFLANE', 'SUPPORT')",
            name=f"ck_{table.name}_role",
        )
    )
profile_claims.append_constraint(
    CheckConstraint(
        "mode IN ('STANDARD', 'TURBO')",
        name="ck_tracker_claim_mode",
    )
)
positions.append_constraint(
    CheckConstraint(
        "(player_slot BETWEEN 0 AND 4 AND team = 'RADIANT') OR "
        "(player_slot BETWEEN 5 AND 9 AND team = 'DIRE')",
        name="ck_tracker_position_team",
    )
)
for table, columns in (
    (metric_observations, ("raw_value", "comparison_value", "context_h", "context_e")),
    (personal_bests, ("comparison_value",)),
    (provider_calls, ("latency_ms",)),
):
    for column in columns:
        table.append_constraint(
            CheckConstraint(
                f"{column} > '-Infinity'::float8 AND {column} < 'Infinity'::float8",
                name=f"ck_{table.name}_{column}_finite",
            )
        )
personal_bests.append_constraint(
    ForeignKeyConstraint(
        ["analysis_id", "profile_id"],
        [analyses.c.id, analyses.c.profile_id],
        ondelete="CASCADE",
        name="fk_tracker_pb_owner",
    )
)
notification_outbox.append_constraint(
    ForeignKeyConstraint(
        ["profile_id", "user_id"],
        [profiles.c.id, profiles.c.user_id],
        ondelete="CASCADE",
        name="fk_tracker_notification_owner",
    )
)

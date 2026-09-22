"""Add independent tracker data boundaries; legacy rows and retention are unchanged."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "0006_tracker_foundation"
down_revision = "0005_v6_interactions_deep"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tracker_dota_accounts",
        sa.Column("account_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("display_name", sa.String(length=300), nullable=True),
        sa.Column("visibility", sa.String(length=24), server_default="UNKNOWN", nullable=False),
        sa.Column("tracked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint(
            "visibility IN ('UNKNOWN', 'ACCESSIBLE', 'BLOCKED')", name="ck_tracker_visibility"
        ),
        sa.CheckConstraint(
            "account_id > 0 AND account_id <= 4294967295", name="ck_tracker_account_id"
        ),
        sa.PrimaryKeyConstraint("account_id", name=op.f("pk_tracker_dota_accounts")),
    )
    op.create_table(
        "tracker_matches",
        sa.Column("match_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=True),
        sa.Column("game_mode", sa.Integer(), nullable=True),
        sa.Column("lobby_type", sa.Integer(), nullable=True),
        sa.Column("patch", sa.String(length=32), nullable=True),
        sa.Column("radiant_win", sa.Boolean(), nullable=True),
        sa.Column("header", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "evidence_state", sa.String(length=24), server_default="DISCOVERED", nullable=False
        ),
        sa.Column("terminal_reason", sa.String(length=64), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary_ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replay_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replay_terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "quarantined_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "evidence_state != 'REPLAY_UNAVAILABLE' OR terminal_reason IS NOT NULL",
            name="ck_tracker_terminal_reason",
        ),
        sa.CheckConstraint(
            "evidence_state = 'DISCOVERED' OR (started_at IS NOT NULL AND duration_seconds IS NOT NULL AND mode IS NOT NULL AND radiant_win IS NOT NULL AND header IS NOT NULL AND summary_ready_at IS NOT NULL)",
            name="ck_tracker_summary_header",
        ),
        sa.CheckConstraint(
            "evidence_state IN ('DISCOVERED', 'SUMMARY_READY', 'REPLAY_PENDING', 'REPLAY_READY', 'REPLAY_UNAVAILABLE')",
            name="ck_tracker_evidence",
        ),
        sa.CheckConstraint(
            "mode IN ('STANDARD', 'TURBO', 'UNSUPPORTED')", name="ck_tracker_match_mode"
        ),
        sa.CheckConstraint("duration_seconds >= 0", name="ck_tracker_match_duration"),
        sa.CheckConstraint("match_id > 0", name="ck_tracker_match_id"),
        sa.PrimaryKeyConstraint("match_id", name=op.f("pk_tracker_matches")),
    )
    op.create_table(
        "tracker_parameter_sets",
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('PROVISIONAL', 'APPROVED', 'TEST_ONLY')", name="ck_tracker_parameter_status"
        ),
        sa.PrimaryKeyConstraint("version", name=op.f("pk_tracker_parameter_sets")),
    )
    op.create_table(
        "tracker_provider_calls",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("operation", sa.String(length=80), nullable=False),
        sa.Column("operation_version", sa.String(length=64), nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("billed_units", sa.Integer(), nullable=False),
        sa.Column("rate_units", sa.Integer(), nullable=False),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "latency_ms >= 0 AND billed_units >= 0 AND rate_units >= 0",
            name="ck_tracker_call_accounting",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_provider_calls")),
    )
    op.create_table(
        "tracker_provider_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("operation", sa.String(length=80), nullable=False),
        sa.Column("operation_version", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=128), nullable=False),
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("storage_uri", sa.Text(), nullable=True),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "(payload IS NULL) != (storage_uri IS NULL)", name="ck_tracker_snapshot_storage"
        ),
        sa.CheckConstraint(
            "byte_size >= 0 AND length(digest) = 64", name="ck_tracker_snapshot_digest"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_provider_snapshots")),
        sa.UniqueConstraint(
            "provider",
            "operation",
            "operation_version",
            "schema_version",
            "subject",
            "digest",
            name="uq_tracker_snapshot_identity",
        ),
    )
    op.create_table(
        "tracker_users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("state", sa.String(length=24), server_default="ACTIVE", nullable=False),
        sa.Column("generation", sa.BigInteger(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "notifications_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.CheckConstraint("state IN ('ACTIVE', 'DELETION_PENDING')", name="ck_tracker_user_state"),
        sa.CheckConstraint("generation > 0", name="ck_tracker_user_generation"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_users")),
    )
    op.create_table(
        "tracker_devices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("push_token", sa.Text(), nullable=True),
        sa.Column("permission", sa.String(length=16), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "permission IN ('UNKNOWN', 'GRANTED', 'DENIED')", name="ck_tracker_device_permission"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["tracker_users.id"],
            name=op.f("fk_tracker_devices_user_id_tracker_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_devices")),
    )
    op.create_index(
        op.f("ix_tracker_devices_user_id"), "tracker_devices", ["user_id"], unique=False
    )
    op.create_table(
        "tracker_follows",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["tracker_dota_accounts.account_id"],
            name=op.f("fk_tracker_follows_account_id_tracker_dota_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["tracker_users.id"],
            name=op.f("fk_tracker_follows_user_id_tracker_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "account_id", name=op.f("pk_tracker_follows")),
    )
    op.create_table(
        "tracker_idempotency_keys",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("response", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["tracker_users.id"],
            name=op.f("fk_tracker_idempotency_keys_user_id_tracker_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "user_id", "operation", "key", name=op.f("pk_tracker_idempotency_keys")
        ),
    )
    op.create_table(
        "tracker_identities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("issuer", sa.String(length=300), nullable=False),
        sa.Column("subject", sa.String(length=300), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["tracker_users.id"],
            name=op.f("fk_tracker_identities_user_id_tracker_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_identities")),
        sa.UniqueConstraint("issuer", "subject", name=op.f("uq_tracker_identities_issuer")),
    )
    op.create_table(
        "tracker_match_acquisition",
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("operation", sa.String(length=80), nullable=False),
        sa.Column("operation_version", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminal_reason", sa.String(length=64), nullable=True),
        sa.Column("snapshot_id", sa.String(length=36), nullable=True),
        sa.CheckConstraint("attempts >= 0", name="ck_tracker_acquisition_attempts"),
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["tracker_matches.match_id"],
            name=op.f("fk_tracker_match_acquisition_match_id_tracker_matches"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["tracker_provider_snapshots.id"],
            name=op.f("fk_tracker_match_acquisition_snapshot_id_tracker_provider_snapshots"),
        ),
        sa.PrimaryKeyConstraint(
            "match_id", "provider", "operation", name=op.f("pk_tracker_match_acquisition")
        ),
    )
    op.create_table(
        "tracker_match_players",
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("player_slot", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=True),
        sa.Column("hero_id", sa.Integer(), nullable=False),
        sa.Column("team", sa.String(length=8), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "(player_slot BETWEEN 0 AND 4 AND team = 'RADIANT') OR (player_slot BETWEEN 5 AND 9 AND team = 'DIRE')",
            name="ck_tracker_player_team",
        ),
        sa.CheckConstraint("hero_id > 0", name="ck_tracker_player_hero"),
        sa.CheckConstraint("player_slot BETWEEN 0 AND 9", name="ck_tracker_player_slot"),
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["tracker_matches.match_id"],
            name=op.f("fk_tracker_match_players_match_id_tracker_matches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("match_id", "player_slot", name=op.f("pk_tracker_match_players")),
    )
    op.create_table(
        "tracker_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("original_linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generation", sa.BigInteger(), server_default="1", nullable=False),
        sa.Column("active_revision", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("active_scope", sa.String(length=8), server_default="FREE", nullable=False),
        sa.Column("favourite_hero_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("active_scope IN ('FREE', 'PRO')", name="ck_tracker_scope"),
        sa.CheckConstraint(
            "generation > 0 AND active_revision >= 0", name="ck_tracker_profile_revision"
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["tracker_dota_accounts.account_id"],
            name=op.f("fk_tracker_profiles_account_id_tracker_dota_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["tracker_users.id"],
            name=op.f("fk_tracker_profiles_user_id_tracker_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_profiles")),
        sa.UniqueConstraint("id", "account_id", name=op.f("uq_tracker_profiles_id")),
        sa.UniqueConstraint("user_id", "account_id", name=op.f("uq_tracker_profiles_user_id")),
    )
    op.create_index(
        "uq_tracker_active_account",
        "tracker_profiles",
        ["account_id"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.create_index(
        "uq_tracker_active_user",
        "tracker_profiles",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.create_table(
        "tracker_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("family_id", sa.String(length=36), nullable=False),
        sa.Column("refresh_hash", sa.String(length=64), nullable=False),
        sa.Column("access_hash", sa.String(length=64), nullable=False),
        sa.Column("user_generation", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", sa.String(length=36), nullable=True),
        sa.CheckConstraint("expires_at > created_at", name="ck_tracker_session_expiry"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["tracker_users.id"],
            name=op.f("fk_tracker_sessions_user_id_tracker_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_sessions")),
        sa.UniqueConstraint("access_hash", name=op.f("uq_tracker_sessions_access_hash")),
        sa.UniqueConstraint("refresh_hash", name=op.f("uq_tracker_sessions_refresh_hash")),
    )
    op.create_index(
        op.f("ix_tracker_sessions_family_id"), "tracker_sessions", ["family_id"], unique=False
    )
    op.create_index(
        op.f("ix_tracker_sessions_user_id"), "tracker_sessions", ["user_id"], unique=False
    )
    op.create_table(
        "tracker_subscriptions",
        sa.Column("original_transaction_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=128), nullable=False),
        sa.Column("environment", sa.String(length=16), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=True),
        sa.Column("verification_digest", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["tracker_users.id"],
            name=op.f("fk_tracker_subscriptions_user_id_tracker_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("original_transaction_id", name=op.f("pk_tracker_subscriptions")),
    )
    op.create_index(
        op.f("ix_tracker_subscriptions_user_id"), "tracker_subscriptions", ["user_id"], unique=False
    )
    op.create_table(
        "tracker_sync_state",
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("cursor", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_complete_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("blocked_reason", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "state IN ('IDLE', 'CHECKING', 'UP_TO_DATE', 'SYNC_ERROR')",
            name="ck_tracker_sync_state",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["tracker_dota_accounts.account_id"],
            name=op.f("fk_tracker_sync_state_account_id_tracker_dota_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("account_id", "provider", name=op.f("pk_tracker_sync_state")),
    )
    op.create_table(
        "tracker_account_matches",
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("player_slot", sa.Integer(), nullable=False),
        sa.Column(
            "lifecycle", sa.String(length=32), server_default="WAITING_FOR_PROVIDER", nullable=False
        ),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("progression", sa.String(length=16), nullable=True),
        sa.Column("progression_reason", sa.String(length=64), nullable=True),
        sa.Column("provider_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_source_match_id", sa.BigInteger(), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("effective_role", sa.String(length=16), nullable=True),
        sa.Column("role_revision", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active_analysis_id", sa.String(length=36), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("retrying", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("failure_stage", sa.String(length=64), nullable=True),
        sa.Column("failure_reason", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "effective_role IN ('CARRY', 'MID', 'OFFLANE', 'SUPPORT')",
            name="ck_tracker_effective_role",
        ),
        sa.CheckConstraint(
            "lifecycle != 'READY' OR (finalized_at IS NOT NULL AND progression IS NOT NULL AND active_analysis_id IS NOT NULL)",
            name="ck_tracker_finalized",
        ),
        sa.CheckConstraint(
            "lifecycle IN ('WAITING_FOR_PROVIDER', 'ANALYZING', 'WAITING_FOR_PRIOR_MATCH', 'ACTION_REQUIRED', 'READY', 'UNAVAILABLE')",
            name="ck_tracker_lifecycle",
        ),
        sa.CheckConstraint(
            "mode IN ('STANDARD', 'TURBO', 'UNSUPPORTED')", name="ck_tracker_link_mode"
        ),
        sa.CheckConstraint(
            "origin IN ('LIVE', 'BOOTSTRAP', 'HISTORICAL', 'RECOVERY')", name="ck_tracker_origin"
        ),
        sa.CheckConstraint(
            "progression != 'NONE' OR progression_reason IS NOT NULL",
            name="ck_tracker_progression_reason",
        ),
        sa.CheckConstraint(
            "progression IN ('STANDARD', 'TURBO', 'NONE')", name="ck_tracker_progression"
        ),
        sa.CheckConstraint(
            "provider_source_match_id = match_id", name="ck_tracker_source_identity"
        ),
        sa.ForeignKeyConstraint(
            ["match_id", "player_slot"],
            ["tracker_match_players.match_id", "tracker_match_players.player_slot"],
            name=op.f("fk_tracker_account_matches_match_id_tracker_match_players"),
        ),
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["tracker_matches.match_id"],
            name=op.f("fk_tracker_account_matches_match_id_tracker_matches"),
        ),
        sa.ForeignKeyConstraint(
            ["profile_id", "account_id"],
            ["tracker_profiles.id", "tracker_profiles.account_id"],
            name=op.f("fk_tracker_account_matches_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("profile_id", "match_id", name=op.f("pk_tracker_account_matches")),
    )
    op.create_index(
        "ix_tracker_chronology",
        "tracker_account_matches",
        ["profile_id", "mode", "provider_started_at", "provider_source_match_id"],
        unique=False,
    )
    op.create_table(
        "tracker_baselines",
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("metric_id", sa.String(length=100), nullable=False),
        sa.Column("metric_version", sa.String(length=64), nullable=False),
        sa.Column("baseline_version", sa.String(length=64), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["tracker_profiles.id"],
            name=op.f("fk_tracker_baselines_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "revision",
            "mode",
            "role",
            "metric_id",
            "metric_version",
            name=op.f("pk_tracker_baselines"),
        ),
    )
    op.create_table(
        "tracker_bootstrap",
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("search_finished", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("cursor", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("discovered_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("eligible_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("settled_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("mode IN ('STANDARD', 'TURBO')", name="ck_tracker_bootstrap_mode"),
        sa.CheckConstraint(
            "outcome IN ('NO_STEAM_LINKED', 'DATA_ACCESS_BLOCKED', 'NO_MATCHES_FOUND', 'NO_ELIGIBLE_MATCHES', 'READY', 'READY_WITH_GAPS')",
            name="ck_tracker_bootstrap_outcome",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR (search_finished AND settled_count = discovered_count AND outcome IS NOT NULL)",
            name="ck_tracker_bootstrap_terminal",
        ),
        sa.CheckConstraint(
            "discovered_count >= settled_count AND settled_count >= 0 AND eligible_count >= 0 AND eligible_count <= discovered_count",
            name="ck_tracker_bootstrap_counts",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["tracker_profiles.id"],
            name=op.f("fk_tracker_bootstrap_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("profile_id", "mode", name=op.f("pk_tracker_bootstrap")),
    )
    op.create_table(
        "tracker_coverage",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("evidence_class", sa.String(length=16), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "evidence_class IN ('SUMMARY', 'REPLAY')", name="ck_tracker_coverage_class"
        ),
        sa.CheckConstraint("mode IN ('STANDARD', 'TURBO')", name="ck_tracker_coverage_mode"),
        sa.CheckConstraint(
            "state IN ('KNOWN', 'GAP', 'PENDING')", name="ck_tracker_coverage_state"
        ),
        sa.CheckConstraint("end_at >= start_at", name="ck_tracker_coverage_interval"),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["tracker_profiles.id"],
            name=op.f("fk_tracker_coverage_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_coverage")),
        sa.UniqueConstraint(
            "profile_id",
            "mode",
            "evidence_class",
            "start_at",
            "end_at",
            name=op.f("uq_tracker_coverage_profile_id"),
        ),
    )
    op.create_table(
        "tracker_derived_features",
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("player_slot", sa.Integer(), nullable=False),
        sa.Column("feature_version", sa.String(length=64), nullable=False),
        sa.Column("inputs_digest", sa.String(length=64), nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["match_id", "player_slot"],
            ["tracker_match_players.match_id", "tracker_match_players.player_slot"],
            name=op.f("fk_tracker_derived_features_match_id_tracker_match_players"),
        ),
        sa.PrimaryKeyConstraint(
            "match_id",
            "player_slot",
            "feature_version",
            "inputs_digest",
            name=op.f("pk_tracker_derived_features"),
        ),
    )
    op.create_table(
        "tracker_discoveries",
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("source_item_id", sa.String(length=128), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column("match_id", sa.BigInteger(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('ACCEPTED', 'REJECTED', 'TERMINAL')", name="ck_tracker_discovery_outcome"
        ),
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["tracker_matches.match_id"],
            name=op.f("fk_tracker_discoveries_match_id_tracker_matches"),
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["tracker_profiles.id"],
            name=op.f("fk_tracker_discoveries_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "profile_id", "provider", "source_item_id", name=op.f("pk_tracker_discoveries")
        ),
    )
    op.create_table(
        "tracker_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("dedup_key", sa.String(length=240), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["tracker_profiles.id"],
            name=op.f("fk_tracker_events_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_events")),
        sa.UniqueConstraint("dedup_key", name=op.f("uq_tracker_events_dedup_key")),
    )
    op.create_index(
        op.f("ix_tracker_events_profile_id"), "tracker_events", ["profile_id"], unique=False
    )
    op.create_table(
        "tracker_history_operations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("target_scope", sa.String(length=8), nullable=False),
        sa.Column("target_revision", sa.BigInteger(), nullable=False),
        sa.Column("cutoff_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cutoff_match_id", sa.BigInteger(), nullable=True),
        sa.Column("cursor", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("dependency_scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedup_key", sa.String(length=240), nullable=False),
        sa.CheckConstraint(
            "state IN ('PENDING', 'RUNNING', 'COMPLETE', 'FAILED', 'CANCELLED')",
            name="ck_tracker_operation_state",
        ),
        sa.CheckConstraint("target_scope IN ('FREE', 'PRO')", name="ck_tracker_operation_scope"),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["tracker_profiles.id"],
            name=op.f("fk_tracker_history_operations_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_history_operations")),
        sa.UniqueConstraint("dedup_key", name=op.f("uq_tracker_history_operations_dedup_key")),
    )
    op.create_index(
        "uq_tracker_active_rebuild",
        "tracker_history_operations",
        ["profile_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('PENDING', 'RUNNING')"),
    )
    op.create_table(
        "tracker_ingest_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dedup_key", sa.String(length=240), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=True),
        sa.Column("account_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("profile_id", sa.String(length=36), nullable=True),
        sa.Column("user_generation", sa.BigInteger(), nullable=True),
        sa.Column("profile_generation", sa.BigInteger(), nullable=True),
        sa.Column("state", sa.String(length=16), server_default="PENDING", nullable=False),
        sa.Column("run_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lease_token", sa.String(length=36), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cursor", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("last_error", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "state IN ('PENDING', 'RUNNING', 'COMPLETE', 'FAILED', 'CANCELLED')",
            name="ck_tracker_job_state",
        ),
        sa.CheckConstraint(
            "(profile_id IS NULL) = (profile_generation IS NULL)",
            name="ck_tracker_job_profile_fence",
        ),
        sa.CheckConstraint(
            "(user_id IS NULL) = (user_generation IS NULL)", name="ck_tracker_job_user_fence"
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_tracker_job_attempts"),
        sa.CheckConstraint("priority BETWEEN 0 AND 3", name="ck_tracker_priority"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["tracker_dota_accounts.account_id"],
            name=op.f("fk_tracker_ingest_jobs_account_id_tracker_dota_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["tracker_matches.match_id"],
            name=op.f("fk_tracker_ingest_jobs_match_id_tracker_matches"),
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["tracker_profiles.id"],
            name=op.f("fk_tracker_ingest_jobs_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["tracker_users.id"],
            name=op.f("fk_tracker_ingest_jobs_user_id_tracker_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_ingest_jobs")),
        sa.UniqueConstraint("dedup_key", name=op.f("uq_tracker_ingest_jobs_dedup_key")),
    )
    op.create_index(
        "ix_tracker_due_work",
        "tracker_ingest_jobs",
        ["priority", "run_after"],
        unique=False,
        postgresql_where=sa.text("state = 'PENDING'"),
    )
    op.create_table(
        "tracker_notification_outbox",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("user_generation", sa.BigInteger(), nullable=False),
        sa.Column("dedup_key", sa.String(length=240), nullable=False),
        sa.Column("event_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('PENDING', 'SENT', 'SUPPRESSED', 'CANCELLED')",
            name="ck_tracker_notification_state",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["tracker_profiles.id"],
            name=op.f("fk_tracker_notification_outbox_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["tracker_users.id"],
            name=op.f("fk_tracker_notification_outbox_user_id_tracker_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_notification_outbox")),
        sa.UniqueConstraint("dedup_key", name=op.f("uq_tracker_notification_outbox_dedup_key")),
    )
    op.create_table(
        "tracker_position_assignments",
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("player_slot", sa.Integer(), nullable=False),
        sa.Column("evidence_profile", sa.String(length=16), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("inputs_digest", sa.String(length=64), nullable=False),
        sa.Column("team", sa.String(length=8), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "evidence_profile IN ('SUMMARY', 'REPLAY')", name="ck_tracker_role_profile"
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_tracker_role_confidence"
        ),
        sa.CheckConstraint("position BETWEEN 1 AND 5", name="ck_tracker_position"),
        sa.ForeignKeyConstraint(
            ["match_id", "player_slot"],
            ["tracker_match_players.match_id", "tracker_match_players.player_slot"],
            name=op.f("fk_tracker_position_assignments_match_id_tracker_match_players"),
        ),
        sa.PrimaryKeyConstraint(
            "match_id",
            "player_slot",
            "evidence_profile",
            "version",
            "inputs_digest",
            name=op.f("pk_tracker_position_assignments"),
        ),
        sa.UniqueConstraint(
            "match_id",
            "team",
            "position",
            "evidence_profile",
            "version",
            "inputs_digest",
            name="uq_tracker_team_position",
        ),
    )
    op.create_table(
        "tracker_profile_claims",
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("scope", sa.String(length=80), nullable=False),
        sa.Column("claim_id", sa.String(length=80), nullable=False),
        sa.Column("claim_version", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("state_since", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("persistence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "state IN ('CANDIDATE', 'CONFIRMED', 'FADING', 'RETIRED')",
            name="ck_tracker_claim_state",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["tracker_profiles.id"],
            name=op.f("fk_tracker_profile_claims_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "revision",
            "mode",
            "scope",
            "claim_id",
            "claim_version",
            name=op.f("pk_tracker_profile_claims"),
        ),
    )
    op.create_table(
        "tracker_shares",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_version", sa.String(length=64), nullable=False),
        sa.Column("projection", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["tracker_profiles.id"],
            name=op.f("fk_tracker_shares_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_shares")),
    )
    op.create_index(
        op.f("ix_tracker_shares_profile_id"), "tracker_shares", ["profile_id"], unique=False
    )
    op.create_table(
        "tracker_switches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("previous_profile_id", sa.String(length=36), nullable=False),
        sa.Column("next_profile_id", sa.String(length=36), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dedup_key", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(
            ["next_profile_id"],
            ["tracker_profiles.id"],
            name=op.f("fk_tracker_switches_next_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["previous_profile_id"],
            ["tracker_profiles.id"],
            name=op.f("fk_tracker_switches_previous_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["tracker_users.id"],
            name=op.f("fk_tracker_switches_user_id_tracker_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_switches")),
        sa.UniqueConstraint("dedup_key", name=op.f("uq_tracker_switches_dedup_key")),
    )
    op.create_index(
        op.f("ix_tracker_switches_user_id"), "tracker_switches", ["user_id"], unique=False
    )
    op.create_table(
        "tracker_analyses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("feature_version", sa.String(length=64), nullable=False),
        sa.Column("analysis_version", sa.String(length=64), nullable=False),
        sa.Column("baseline_version", sa.String(length=64), nullable=False),
        sa.Column("inputs_digest", sa.String(length=64), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id", "match_id"],
            ["tracker_account_matches.profile_id", "tracker_account_matches.match_id"],
            name=op.f("fk_tracker_analyses_profile_id_tracker_account_matches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_analyses")),
        sa.UniqueConstraint("id", "profile_id", "match_id", name=op.f("uq_tracker_analyses_id")),
        sa.UniqueConstraint(
            "profile_id",
            "match_id",
            "analysis_version",
            "inputs_digest",
            name="uq_tracker_analysis_identity",
        ),
    )
    op.create_table(
        "tracker_role_assertions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("asserted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dedup_key", sa.String(length=200), nullable=False),
        sa.CheckConstraint(
            "role IN ('CARRY', 'MID', 'OFFLANE', 'SUPPORT')", name="ck_tracker_asserted_role"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id", "match_id"],
            ["tracker_account_matches.profile_id", "tracker_account_matches.match_id"],
            name=op.f("fk_tracker_role_assertions_profile_id_tracker_account_matches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracker_role_assertions")),
        sa.UniqueConstraint("dedup_key", name=op.f("uq_tracker_role_assertions_dedup_key")),
        sa.UniqueConstraint(
            "profile_id", "match_id", "revision", name=op.f("uq_tracker_role_assertions_profile_id")
        ),
    )
    op.create_table(
        "tracker_analysis_inputs",
        sa.Column("analysis_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["tracker_analyses.id"],
            name=op.f("fk_tracker_analysis_inputs_analysis_id_tracker_analyses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["tracker_provider_snapshots.id"],
            name=op.f("fk_tracker_analysis_inputs_snapshot_id_tracker_provider_snapshots"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "analysis_id", "snapshot_id", name=op.f("pk_tracker_analysis_inputs")
        ),
    )
    op.create_table(
        "tracker_insight_results",
        sa.Column("analysis_id", sa.String(length=36), nullable=False),
        sa.Column("contract_version", sa.String(length=64), nullable=False),
        sa.Column("inputs_digest", sa.String(length=64), nullable=False),
        sa.Column("cards", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(cards) = 'array' AND jsonb_array_length(cards) <= 3",
            name="ck_tracker_insight_count",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["tracker_analyses.id"],
            name=op.f("fk_tracker_insight_results_analysis_id_tracker_analyses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "analysis_id",
            "contract_version",
            "inputs_digest",
            name=op.f("pk_tracker_insight_results"),
        ),
    )
    op.create_table(
        "tracker_metric_observations",
        sa.Column("analysis_id", sa.String(length=36), nullable=False),
        sa.Column("metric_id", sa.String(length=100), nullable=False),
        sa.Column("metric_version", sa.String(length=64), nullable=False),
        sa.Column("raw_value", sa.Float(), nullable=True),
        sa.Column("comparison_value", sa.Float(), nullable=True),
        sa.Column("unavailable_reason", sa.String(length=64), nullable=True),
        sa.Column("baseline_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("context_h", sa.Float(), nullable=True),
        sa.Column("context_e", sa.Float(), nullable=True),
        sa.Column("parameter_set_version", sa.String(length=64), nullable=True),
        sa.Column("performance_state", sa.String(length=16), nullable=True),
        sa.CheckConstraint(
            "performance_state IN ('ABOVE', 'IN_LINE', 'BELOW', 'NOT_READY')",
            name="ck_tracker_performance",
        ),
        sa.CheckConstraint(
            "(raw_value IS NOT NULL AND comparison_value IS NOT NULL AND unavailable_reason IS NULL) OR (raw_value IS NULL AND comparison_value IS NULL AND unavailable_reason IS NOT NULL)",
            name="ck_tracker_metric_absence",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["tracker_analyses.id"],
            name=op.f("fk_tracker_metric_observations_analysis_id_tracker_analyses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parameter_set_version"],
            ["tracker_parameter_sets.version"],
            name=op.f(
                "fk_tracker_metric_observations_parameter_set_version_tracker_parameter_sets"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "analysis_id", "metric_id", name=op.f("pk_tracker_metric_observations")
        ),
    )
    op.create_table(
        "tracker_personal_bests",
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("metric_id", sa.String(length=100), nullable=False),
        sa.Column("metric_version", sa.String(length=64), nullable=False),
        sa.Column("analysis_id", sa.String(length=36), nullable=False),
        sa.Column("comparison_value", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["tracker_analyses.id"],
            name=op.f("fk_tracker_personal_bests_analysis_id_tracker_analyses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["tracker_profiles.id"],
            name=op.f("fk_tracker_personal_bests_profile_id_tracker_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "revision",
            "mode",
            "role",
            "metric_id",
            "metric_version",
            name=op.f("pk_tracker_personal_bests"),
        ),
    )
    op.create_unique_constraint(
        "uq_tracker_profiles_id_user", "tracker_profiles", ["id", "user_id"]
    )
    op.create_unique_constraint(
        "uq_tracker_analyses_id_profile", "tracker_analyses", ["id", "profile_id"]
    )
    for table in ("tracker_baselines", "tracker_personal_bests"):
        op.create_check_constraint(f"ck_{table}_mode", table, "mode IN ('STANDARD', 'TURBO')")
        op.create_check_constraint(
            f"ck_{table}_role", table, "role IN ('CARRY', 'MID', 'OFFLANE', 'SUPPORT')"
        )
    op.create_check_constraint(
        "ck_tracker_claim_mode", "tracker_profile_claims", "mode IN ('STANDARD', 'TURBO')"
    )
    op.create_check_constraint(
        "ck_tracker_position_team",
        "tracker_position_assignments",
        "(player_slot BETWEEN 0 AND 4 AND team = 'RADIANT') OR (player_slot BETWEEN 5 AND 9 AND team = 'DIRE')",
    )
    for table, columns in (
        (
            "tracker_metric_observations",
            ("raw_value", "comparison_value", "context_h", "context_e"),
        ),
        ("tracker_personal_bests", ("comparison_value",)),
        ("tracker_provider_calls", ("latency_ms",)),
    ):
        for column in columns:
            op.create_check_constraint(
                f"ck_{table}_{column}_finite",
                table,
                f"{column} > '-Infinity'::float8 AND {column} < 'Infinity'::float8",
            )
    op.create_foreign_key(
        "fk_tracker_pb_owner",
        "tracker_personal_bests",
        "tracker_analyses",
        ["analysis_id", "profile_id"],
        ["id", "profile_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_tracker_notification_owner",
        "tracker_notification_outbox",
        "tracker_profiles",
        ["profile_id", "user_id"],
        ["id", "user_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_tracker_active_analysis",
        "tracker_account_matches",
        "tracker_analyses",
        ["active_analysis_id", "profile_id", "match_id"],
        ["id", "profile_id", "match_id"],
    )
    op.execute("""
        CREATE FUNCTION tracker_require_roster() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE target_id bigint; state text;
        BEGIN
            target_id := COALESCE(NEW.match_id, OLD.match_id);
            SELECT evidence_state INTO state FROM tracker_matches WHERE match_id = target_id;
            IF state IS NOT NULL AND state <> 'DISCOVERED' AND
               (SELECT count(*) FROM tracker_match_players WHERE match_id = target_id) <> 10 THEN
                RAISE EXCEPTION 'summary requires ten canonical players' USING ERRCODE = '23514';
            END IF;
            RETURN NULL;
        END $$
    """)
    for table in ("tracker_matches", "tracker_match_players"):
        op.execute(f"""
            CREATE CONSTRAINT TRIGGER tracker_complete_roster
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
            EXECUTE FUNCTION tracker_require_roster()
        """)
    op.execute("""
        CREATE FUNCTION tracker_require_terminal_analysis() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE current_state text;
        BEGIN
            SELECT lifecycle INTO current_state FROM tracker_account_matches
                WHERE profile_id = NEW.profile_id AND match_id = NEW.match_id;
            IF current_state = 'READY' AND NOT EXISTS (
                SELECT 1 FROM tracker_matches WHERE match_id = NEW.match_id
                    AND evidence_state IN ('REPLAY_READY', 'REPLAY_UNAVAILABLE')
            ) THEN
                RAISE EXCEPTION 'finalization requires terminal evidence' USING ERRCODE = '23514';
            END IF;
            RETURN NULL;
        END $$
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER tracker_finalization_gate
        AFTER INSERT OR UPDATE ON tracker_account_matches
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
        EXECUTE FUNCTION tracker_require_terminal_analysis()
    """)
    op.execute("""
        CREATE FUNCTION tracker_reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'immutable tracker evidence or result' USING ERRCODE = '23514';
        END $$
    """)
    for table in (
        "tracker_provider_snapshots",
        "tracker_derived_features",
        "tracker_analyses",
        "tracker_analysis_inputs",
        "tracker_metric_observations",
        "tracker_insight_results",
        "tracker_role_assertions",
        "tracker_events",
        "tracker_shares",
        "tracker_parameter_sets",
    ):
        op.execute(f"""
            CREATE TRIGGER tracker_immutable_update BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION tracker_reject_mutation()
        """)


def downgrade() -> None:
    op.drop_constraint("fk_tracker_active_analysis", "tracker_account_matches", type_="foreignkey")
    op.drop_table("tracker_personal_bests")
    op.drop_table("tracker_metric_observations")
    op.drop_table("tracker_insight_results")
    op.drop_table("tracker_analysis_inputs")
    op.drop_table("tracker_role_assertions")
    op.drop_table("tracker_analyses")
    op.drop_index(op.f("ix_tracker_switches_user_id"), table_name="tracker_switches")
    op.drop_table("tracker_switches")
    op.drop_index(op.f("ix_tracker_shares_profile_id"), table_name="tracker_shares")
    op.drop_table("tracker_shares")
    op.drop_table("tracker_profile_claims")
    op.drop_table("tracker_position_assignments")
    op.drop_table("tracker_notification_outbox")
    op.drop_index(
        "ix_tracker_due_work",
        table_name="tracker_ingest_jobs",
        postgresql_where=sa.text("state = 'PENDING'"),
    )
    op.drop_table("tracker_ingest_jobs")
    op.drop_index(
        "uq_tracker_active_rebuild",
        table_name="tracker_history_operations",
        postgresql_where=sa.text("state IN ('PENDING', 'RUNNING')"),
    )
    op.drop_table("tracker_history_operations")
    op.drop_index(op.f("ix_tracker_events_profile_id"), table_name="tracker_events")
    op.drop_table("tracker_events")
    op.drop_table("tracker_discoveries")
    op.drop_table("tracker_derived_features")
    op.drop_table("tracker_coverage")
    op.drop_table("tracker_bootstrap")
    op.drop_table("tracker_baselines")
    op.drop_index("ix_tracker_chronology", table_name="tracker_account_matches")
    op.drop_table("tracker_account_matches")
    op.drop_table("tracker_sync_state")
    op.drop_index(op.f("ix_tracker_subscriptions_user_id"), table_name="tracker_subscriptions")
    op.drop_table("tracker_subscriptions")
    op.drop_index(op.f("ix_tracker_sessions_user_id"), table_name="tracker_sessions")
    op.drop_index(op.f("ix_tracker_sessions_family_id"), table_name="tracker_sessions")
    op.drop_table("tracker_sessions")
    op.drop_index(
        "uq_tracker_active_user", table_name="tracker_profiles", postgresql_where=sa.text("active")
    )
    op.drop_index(
        "uq_tracker_active_account",
        table_name="tracker_profiles",
        postgresql_where=sa.text("active"),
    )
    op.drop_table("tracker_profiles")
    op.drop_table("tracker_match_players")
    op.drop_table("tracker_match_acquisition")
    op.drop_table("tracker_identities")
    op.drop_table("tracker_idempotency_keys")
    op.drop_table("tracker_follows")
    op.drop_index(op.f("ix_tracker_devices_user_id"), table_name="tracker_devices")
    op.drop_table("tracker_devices")
    op.drop_table("tracker_users")
    op.drop_table("tracker_provider_snapshots")
    op.drop_table("tracker_provider_calls")
    op.drop_table("tracker_parameter_sets")
    op.drop_table("tracker_matches")
    op.drop_table("tracker_dota_accounts")
    op.execute("DROP FUNCTION tracker_require_roster()")
    op.execute("DROP FUNCTION tracker_reject_mutation()")
    op.execute("DROP FUNCTION tracker_require_terminal_analysis()")

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# The Free population is a time window, not a match-count product cap.  The
# optional limit remains an infrastructure safety valve for a future rollout,
# but the default is deliberately unbounded so a busy account is not silently
# reduced to the old 500-row population.
FREE_HISTORY_WINDOW_DAYS = 365
FREE_HISTORY_LIMIT: int | None = None
MAX_FREE_HISTORY_LIMIT: int | None = None
MATCH_HISTORY_LIMIT = FREE_HISTORY_LIMIT
RECENCY_HALF_LIFE_DAYS = 180.0
DEFAULT_MAX_DEEP_MATCHES = 25
DEFAULT_MAX_PARSE_REQUESTS = 0
DEFAULT_MAX_DATA_COST_PER_REPORT = 50.0
DEFAULT_MIN_MARGINAL_INFORMATION_GAIN = 0.05
DEFAULT_MAX_PRIMARY_HYPOTHESES = 3
DEFAULT_SESSION_GAP_MINUTES = 90
DEFAULT_SUMMARY_HISTORY_CACHE_TTL_SECONDS = 120
DEFAULT_REPORT_RETENTION_DAYS = 30
DEFAULT_STEAM_RESOLVER_BASE_URL = "https://api.steampowered.com"
DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _optional_int(value: str | None, *, default: int | None) -> int | None:
    """Parse an optional infrastructure ceiling without inventing a product cap."""

    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else None


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    log_level: str = "INFO"
    opendota_source: str = "fixture"
    opendota_base_url: str = "https://api.opendota.com/api"
    opendota_api_key: str | None = None
    steam_api_key: str | None = None
    steam_resolver_base_url: str = DEFAULT_STEAM_RESOLVER_BASE_URL
    fixture_dir: Path = Path("tests/fixtures/opendota")
    database_url: str = "postgresql+psycopg://dota:dota@localhost:5432/dota_report_card"
    redis_url: str = "redis://localhost:6379/0"
    model_version: str = "free-dna-model-5.1.0"
    template_version: str = "templates-1.0.0"
    role_confidence_threshold: float = 0.60
    analysis_max_concurrency: int = 4
    opendota_max_retries: int = 3
    opendota_timeout_seconds: float = 15.0
    # Broad summary reads and deep evidence acquisition have independent
    # budgets.  ``history_limit`` is a deprecated constructor alias kept for
    # existing integrations; new code should use ``free_history_limit``.
    free_history_limit: int | None = FREE_HISTORY_LIMIT
    history_limit: int | None = None
    max_deep_matches: int = DEFAULT_MAX_DEEP_MATCHES
    max_parse_requests: int = DEFAULT_MAX_PARSE_REQUESTS
    max_data_cost_per_report: float = DEFAULT_MAX_DATA_COST_PER_REPORT
    min_marginal_information_gain: float = DEFAULT_MIN_MARGINAL_INFORMATION_GAIN
    max_primary_hypotheses: int = DEFAULT_MAX_PRIMARY_HYPOTHESES
    session_gap_minutes: int = DEFAULT_SESSION_GAP_MINUTES
    default_analysis_mode: str = "free"
    compatible_analysis_ttl_seconds: int = 3600
    summary_history_cache_ttl_seconds: int = DEFAULT_SUMMARY_HISTORY_CACHE_TTL_SECONDS
    report_retention_days: int = DEFAULT_REPORT_RETENTION_DAYS
    replay_coverage_threshold: float = 0.60
    summary_coverage_threshold: float = 0.60
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS
    storage_backend: str = "auto"
    analysis_execution_backend: str = "auto"

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        app_env = os.getenv("APP_ENV", "development").lower()
        cors_origins = tuple(
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", ",".join(DEFAULT_CORS_ORIGINS)).split(",")
            if origin.strip()
        )
        api_key = os.getenv("OPENDOTA_API_KEY") or None
        return cls(
            app_env=app_env,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            opendota_source=os.getenv("OPENDOTA_SOURCE", "fixture").lower(),
            opendota_base_url=os.getenv("OPENDOTA_BASE_URL", cls.opendota_base_url),
            opendota_api_key=api_key,
            steam_api_key=os.getenv("STEAM_API_KEY") or None,
            steam_resolver_base_url=os.getenv(
                "STEAM_RESOLVER_BASE_URL", cls.steam_resolver_base_url
            ),
            fixture_dir=Path(os.getenv("OPENDOTA_FIXTURE_DIR", str(cls.fixture_dir))),
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            redis_url=os.getenv("REDIS_URL", cls.redis_url),
            model_version=os.getenv("MODEL_VERSION", cls.model_version),
            template_version=os.getenv("TEMPLATE_VERSION", cls.template_version),
            role_confidence_threshold=float(
                os.getenv("ROLE_CONFIDENCE_THRESHOLD", str(cls.role_confidence_threshold))
            ),
            analysis_max_concurrency=int(
                os.getenv("ANALYSIS_MAX_CONCURRENCY", str(cls.analysis_max_concurrency))
            ),
            opendota_max_retries=int(
                os.getenv("OPENDOTA_MAX_RETRIES", str(cls.opendota_max_retries))
            ),
            opendota_timeout_seconds=float(
                os.getenv("OPENDOTA_TIMEOUT_SECONDS", str(cls.opendota_timeout_seconds))
            ),
            free_history_limit=_optional_int(
                os.getenv("FREE_HISTORY_LIMIT", os.getenv("HISTORY_LIMIT")),
                default=cls.free_history_limit,
            ),
            max_deep_matches=int(
                os.getenv("MAX_DEEP_MATCHES", str(cls.max_deep_matches))
            ),
            max_parse_requests=int(
                os.getenv("MAX_PARSE_REQUESTS", str(cls.max_parse_requests))
            ),
            max_data_cost_per_report=float(
                os.getenv(
                    "MAX_DATA_COST_PER_REPORT",
                    str(cls.max_data_cost_per_report),
                )
            ),
            min_marginal_information_gain=float(
                os.getenv(
                    "MIN_MARGINAL_INFORMATION_GAIN",
                    str(cls.min_marginal_information_gain),
                )
            ),
            max_primary_hypotheses=int(
                os.getenv(
                    "MAX_PRIMARY_HYPOTHESES",
                    str(cls.max_primary_hypotheses),
                )
            ),
            session_gap_minutes=int(
                os.getenv("SESSION_GAP_MINUTES", str(cls.session_gap_minutes))
            ),
            default_analysis_mode=os.getenv(
                "DEFAULT_ANALYSIS_MODE", cls.default_analysis_mode
            ).lower(),
            compatible_analysis_ttl_seconds=int(
                os.getenv(
                    "COMPATIBLE_ANALYSIS_TTL_SECONDS",
                    str(cls.compatible_analysis_ttl_seconds),
                )
            ),
            summary_history_cache_ttl_seconds=int(
                os.getenv(
                    "SUMMARY_HISTORY_CACHE_TTL_SECONDS",
                    str(cls.summary_history_cache_ttl_seconds),
                )
            ),
            report_retention_days=int(
                os.getenv("REPORT_RETENTION_DAYS", str(cls.report_retention_days))
            ),
            replay_coverage_threshold=float(
                os.getenv("REPLAY_COVERAGE_THRESHOLD", str(cls.replay_coverage_threshold))
            ),
            summary_coverage_threshold=float(
                os.getenv("SUMMARY_COVERAGE_THRESHOLD", str(cls.summary_coverage_threshold))
            ),
            cors_origins=cors_origins or DEFAULT_CORS_ORIGINS,
            storage_backend=os.getenv("STORAGE_BACKEND", "auto").lower(),
            analysis_execution_backend=os.getenv(
                "ANALYSIS_EXECUTION_BACKEND", "auto"
            ).lower(),
        )

    @property
    def effective_fixture_dir(self) -> Path:
        return self.fixture_dir if self.fixture_dir.is_absolute() else Path.cwd() / self.fixture_dir

    @property
    def effective_history_limit(self) -> int | None:
        """Backward-compatible alias for the broad summary limit."""

        return self.effective_free_history_limit

    @property
    def effective_free_history_limit(self) -> int | None:
        requested = self.history_limit if self.history_limit is not None else self.free_history_limit
        if requested is None:
            return None
        if requested <= 0:
            return None
        return requested if MAX_FREE_HISTORY_LIMIT is None else min(requested, MAX_FREE_HISTORY_LIMIT)

    @property
    def effective_max_deep_matches(self) -> int:
        return max(0, self.max_deep_matches)

    @property
    def effective_max_parse_requests(self) -> int:
        return max(0, self.max_parse_requests)

    @property
    def effective_max_data_cost_per_report(self) -> float:
        return max(0.0, self.max_data_cost_per_report)

    @property
    def effective_min_marginal_information_gain(self) -> float:
        return max(0.0, self.min_marginal_information_gain)

    @property
    def effective_max_primary_hypotheses(self) -> int:
        return max(1, self.max_primary_hypotheses)

    @property
    def effective_session_gap_minutes(self) -> int:
        return max(1, self.session_gap_minutes)

    @property
    def effective_summary_history_cache_ttl_seconds(self) -> int:
        return max(1, self.summary_history_cache_ttl_seconds)

    @property
    def effective_report_retention_days(self) -> int:
        return max(1, self.report_retention_days)

    @property
    def effective_storage_backend(self) -> str:
        if self.storage_backend != "auto":
            return self.storage_backend
        return "database" if self.app_env == "production" else "memory"

    @property
    def effective_analysis_execution_backend(self) -> str:
        if self.analysis_execution_backend != "auto":
            return self.analysis_execution_backend
        return "celery" if self.app_env == "production" else "in_process"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()

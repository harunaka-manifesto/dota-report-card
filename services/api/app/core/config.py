from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

MATCH_HISTORY_LIMIT = 50
DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    log_level: str = "INFO"
    opendota_source: str = "fixture"
    opendota_base_url: str = "https://api.opendota.com/api"
    opendota_api_key: str | None = None
    fixture_dir: Path = Path("tests/fixtures/opendota")
    database_url: str = "postgresql+psycopg://dota:dota@localhost:5432/dota_report_card"
    redis_url: str = "redis://localhost:6379/0"
    model_version: str = "insight-engine-1.0.0"
    template_version: str = "templates-1.0.0"
    role_confidence_threshold: float = 0.60
    analysis_max_concurrency: int = 4
    opendota_max_retries: int = 3
    opendota_timeout_seconds: float = 15.0
    # Experiment guardrail: keep every source and transport bounded to the
    # latest 50 matches until the larger history policy is validated.
    history_limit: int = MATCH_HISTORY_LIMIT
    compatible_analysis_ttl_seconds: int = 3600
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
            history_limit=int(os.getenv("HISTORY_LIMIT", str(cls.history_limit))),
            compatible_analysis_ttl_seconds=int(
                os.getenv(
                    "COMPATIBLE_ANALYSIS_TTL_SECONDS",
                    str(cls.compatible_analysis_ttl_seconds),
                )
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
    def effective_history_limit(self) -> int:
        return max(1, min(self.history_limit, MATCH_HISTORY_LIMIT))

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

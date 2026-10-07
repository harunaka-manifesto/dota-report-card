from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

# OpenDota match-history reads cover a time window, not a match-count product
# cap. The optional limit is an infrastructure safety valve only.
FREE_HISTORY_WINDOW_DAYS = 365
FREE_HISTORY_LIMIT: int | None = None
MAX_FREE_HISTORY_LIMIT: int | None = None
DEFAULT_STRATZ_BASE_URL = "https://api.stratz.com/graphql"
DEFAULT_STRATZ_USER_AGENT = "STRATZ_API"
DEFAULT_STRATZ_TIMEOUT_SECONDS = 20.0
DEFAULT_STRATZ_MAX_RETRIES = 3
DEFAULT_STRATZ_MAX_HISTORY_PAGES = 25


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
    opendota_base_url: str = "https://api.opendota.com/api"
    opendota_api_key: str | None = None
    database_url: str = "postgresql+psycopg://dota:dota@localhost:5432/dota_report_card"
    redis_url: str = "redis://localhost:6379/0"
    opendota_max_retries: int = 3
    opendota_timeout_seconds: float = 15.0
    stratz_base_url: str = DEFAULT_STRATZ_BASE_URL
    stratz_api_token: str | None = None
    stratz_user_agent: str = DEFAULT_STRATZ_USER_AGENT
    stratz_timeout_seconds: float = DEFAULT_STRATZ_TIMEOUT_SECONDS
    stratz_max_retries: int = DEFAULT_STRATZ_MAX_RETRIES
    stratz_max_history_pages: int = DEFAULT_STRATZ_MAX_HISTORY_PAGES
    free_history_limit: int | None = FREE_HISTORY_LIMIT

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        return cls(
            app_env=os.getenv("APP_ENV", "development").lower(),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            opendota_base_url=os.getenv("OPENDOTA_BASE_URL", cls.opendota_base_url),
            opendota_api_key=os.getenv("OPENDOTA_API_KEY") or None,
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            redis_url=os.getenv("REDIS_URL", cls.redis_url),
            opendota_max_retries=int(
                os.getenv("OPENDOTA_MAX_RETRIES", str(cls.opendota_max_retries))
            ),
            opendota_timeout_seconds=float(
                os.getenv("OPENDOTA_TIMEOUT_SECONDS", str(cls.opendota_timeout_seconds))
            ),
            stratz_base_url=os.getenv("STRATZ_BASE_URL", cls.stratz_base_url),
            # STRATZ_API_TOKEN is canonical; the older local name STRATZ_API_KEY is
            # accepted only as a fallback so existing developer .env files keep working.
            stratz_api_token=os.getenv("STRATZ_API_TOKEN") or os.getenv("STRATZ_API_KEY") or None,
            stratz_user_agent=os.getenv("STRATZ_USER_AGENT", cls.stratz_user_agent),
            stratz_timeout_seconds=float(
                os.getenv("STRATZ_TIMEOUT_SECONDS", str(cls.stratz_timeout_seconds))
            ),
            stratz_max_retries=int(
                os.getenv("STRATZ_MAX_RETRIES", str(cls.stratz_max_retries))
            ),
            stratz_max_history_pages=int(
                os.getenv("STRATZ_MAX_HISTORY_PAGES", str(cls.stratz_max_history_pages))
            ),
            free_history_limit=_optional_int(
                os.getenv("FREE_HISTORY_LIMIT", os.getenv("HISTORY_LIMIT")),
                default=cls.free_history_limit,
            ),
        )

    @property
    def effective_free_history_limit(self) -> int | None:
        requested = self.free_history_limit
        if requested is None or requested <= 0:
            return None
        return (
            requested if MAX_FREE_HISTORY_LIMIT is None else min(requested, MAX_FREE_HISTORY_LIMIT)
        )

    @property
    def effective_stratz_max_history_pages(self) -> int:
        return max(1, self.stratz_max_history_pages)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()

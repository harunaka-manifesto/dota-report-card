"""Configuration for offline and live hero-knowledge runs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def utc_now() -> datetime:
    return datetime.now(UTC)


def isoformat(value: datetime | None = None) -> str:
    current = value or utc_now()
    return current.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings for the scraper CLI.

    Relative paths are resolved against ``root`` so CI and local runs produce
    the same layout regardless of the caller's current directory.
    """

    root: Path
    data_root: Path
    valve_base_url: str = "https://www.dota2.com"
    opendota_base_url: str = "https://api.opendota.com/api"
    opendota_api_key: str | None = None
    language: str = "english"
    user_agent: str = "dota-report-card-hero-knowledge/1.0 (+repository-local)"
    timeout_seconds: float = 20.0
    max_retries: int = 3
    concurrency: int = 4
    min_delay_seconds: float = 1.0
    cache_enabled: bool = True

    @classmethod
    def from_root(cls, root: str | Path | None = None) -> Settings:
        resolved_root = Path(root or Path(__file__).resolve().parents[2]).resolve()
        raw_data_root = Path(os.getenv("HERO_KNOWLEDGE_DATA_ROOT", "services/api/app/heroes/data"))
        data_root = raw_data_root if raw_data_root.is_absolute() else resolved_root / raw_data_root
        return cls(
            root=resolved_root,
            data_root=data_root,
            valve_base_url=os.getenv(
                "HERO_KNOWLEDGE_VALVE_BASE_URL", "https://www.dota2.com"
            ).rstrip("/"),
            opendota_base_url=os.getenv(
                "HERO_KNOWLEDGE_OPENDOTA_BASE_URL",
                os.getenv("OPENDOTA_BASE_URL", "https://api.opendota.com/api"),
            ).rstrip("/"),
            opendota_api_key=(
                os.getenv("HERO_KNOWLEDGE_OPENDOTA_API_KEY")
                or os.getenv("OPENDOTA_API_KEY")
                or None
            ),
            language=os.getenv("HERO_KNOWLEDGE_LANGUAGE", "english"),
            user_agent=os.getenv(
                "HERO_KNOWLEDGE_USER_AGENT",
                "dota-report-card-hero-knowledge/1.0 (+repository-local)",
            ),
            timeout_seconds=float(os.getenv("HERO_KNOWLEDGE_TIMEOUT_SECONDS", "20.0")),
            max_retries=max(0, int(os.getenv("HERO_KNOWLEDGE_MAX_RETRIES", "3"))),
            concurrency=max(1, int(os.getenv("HERO_KNOWLEDGE_CONCURRENCY", "4"))),
            min_delay_seconds=max(
                0.0,
                float(os.getenv("HERO_KNOWLEDGE_MIN_DELAY_SECONDS", "1.0")),
            ),
            cache_enabled=not _env_bool("HERO_KNOWLEDGE_DISABLE_CACHE"),
        )

    @property
    def raw_root(self) -> Path:
        return self.data_root / "raw"

    @property
    def normalized_root(self) -> Path:
        return self.data_root / "normalized"

    @property
    def knowledge_root(self) -> Path:
        return self.data_root / "knowledge"

    @property
    def cache_root(self) -> Path:
        return self.data_root / ".cache" / "hero-knowledge"

    def raw_source_root(self, source: str) -> Path:
        return self.raw_root / source

    def normalized_source_root(self, source: str) -> Path:
        return self.normalized_root / source


def snapshot_date(value: datetime | None = None) -> str:
    return (value or utc_now()).astimezone(UTC).date().isoformat()


def source_snapshot_id(source: str, purpose: str, value: datetime | None = None) -> str:
    return f"{source}-{purpose}-{snapshot_date(value)}"

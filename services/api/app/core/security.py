from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Any
from urllib.parse import urlparse

from app.core.errors import InvalidPlayerIdentifier
from app.identity.steam import steam64_to_account_id

STEAM32_MAX = 2**32 - 1
_STEAM32 = re.compile(r"^[0-9]{1,10}$")
_ALLOWED_HOSTS = {"www.opendota.com", "opendota.com"}
_STEAM_HOSTS = {"steamcommunity.com", "www.steamcommunity.com"}


@dataclass(frozen=True, slots=True)
class PlayerIdentifier:
    account_id: int
    canonical_url: str
    vanity: str | None = None


def parse_player_identifier(raw: str) -> PlayerIdentifier:
    value = (raw or "").strip()
    if _STEAM32.fullmatch(value):
        account_id = int(value)
        if 0 < account_id <= STEAM32_MAX:
            return PlayerIdentifier(account_id, f"https://www.opendota.com/players/{account_id}")
        raise InvalidPlayerIdentifier("Steam32 account ID is out of range")
    if value.isdigit() and len(value) > 10:
        account_id = steam64_to_account_id(value)
        return PlayerIdentifier(account_id, f"https://www.opendota.com/players/{account_id}")

    parsed = urlparse(value)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in _ALLOWED_HOSTS | _STEAM_HOSTS
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise InvalidPlayerIdentifier("Use a Steam32 ID or an OpenDota player URL")

    parts = [part for part in parsed.path.split("/") if part]
    if parsed.hostname in _STEAM_HOSTS:
        if len(parts) != 2:
            raise InvalidPlayerIdentifier("Use a Steam profile or vanity URL")
        kind, value_part = parts[0].lower(), parts[1]
        if kind == "profiles" and value_part.isdigit():
            account_id = steam64_to_account_id(value_part)
            return PlayerIdentifier(account_id, f"https://www.opendota.com/players/{account_id}")
        if kind == "id" and _STEAM_VANITY.fullmatch(value_part):
            return PlayerIdentifier(0, f"https://steamcommunity.com/id/{value_part}", value_part.lower())
        raise InvalidPlayerIdentifier("Use a numeric Steam profile or vanity URL")
    if len(parts) != 2 or parts[0].lower() != "players" or not _STEAM32.fullmatch(parts[1]):
        raise InvalidPlayerIdentifier("Use a Steam32 ID or an OpenDota player URL")

    account_id = int(parts[1])
    if not 0 < account_id <= STEAM32_MAX:
        raise InvalidPlayerIdentifier("Steam32 account ID is out of range")
    return PlayerIdentifier(account_id, f"https://www.opendota.com/players/{account_id}")


_STEAM_VANITY = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def redact(value: Any, secrets: tuple[str | None, ...] = ()) -> Any:
    """Recursively remove known credentials from logs and exception payloads."""

    known = {secret for secret in secrets if secret}
    if isinstance(value, str):
        result = value
        for secret in known:
            result = result.replace(secret, "[REDACTED]")
        result = re.sub(r"(?i)(authorization\s*[:=]\s*)([^,\s]+)", r"\1[REDACTED]", result)
        result = re.sub(r"(?i)(api_key\s*=\s*)([^&\s]+)", r"\1[REDACTED]", result)
        return result
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if str(key).lower() in {"authorization", "api_key"}
            else redact(item, secrets)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item, secrets) for item in value)
    return value


def safe_endpoint(endpoint: str) -> str:
    """Only log an API path, never a query string that could contain credentials."""

    parsed = urlparse(endpoint)
    return parsed.path or endpoint.split("?", 1)[0]


class RateLimiter:
    """Small process-local limiter; production can replace it with Redis counters."""

    def __init__(
        self,
        *,
        max_per_ip: int = 60,
        max_per_account: int = 20,
        window_seconds: int = 3600,
    ) -> None:
        self.max_per_ip = max_per_ip
        self.max_per_account = max_per_account
        self.window = timedelta(seconds=window_seconds)
        self._lock = RLock()
        self._ip_hits: dict[str, list[datetime]] = {}
        self._account_hits: dict[str, list[datetime]] = {}

    def allow(self, ip: str, account_id: int, *, unresolved_key: str | None = None) -> bool:
        now = datetime.now(UTC)
        with self._lock:
            ip_hits = self._prune(self._ip_hits.setdefault(ip, []), now)
            if account_id > 0:
                bucket = f"account:{account_id}"
            else:
                # Vanity URLs are unresolved until after this gate. Hash the
                # safe input so distinct vanity names do not share account 0.
                safe_key = (unresolved_key or "unknown").strip().casefold()
                bucket = "vanity:" + hashlib.sha256(safe_key.encode()).hexdigest()
            account_hits = self._prune(self._account_hits.setdefault(bucket, []), now)
            if len(ip_hits) >= self.max_per_ip or len(account_hits) >= self.max_per_account:
                return False
            ip_hits.append(now)
            account_hits.append(now)
            return True

    def _prune(self, hits: list[datetime], now: datetime) -> list[datetime]:
        cutoff = now - self.window
        hits[:] = [hit for hit in hits if hit > cutoff]
        return hits

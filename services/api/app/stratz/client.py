"""Small, bounded STRATZ GraphQL transport for the V7 foundation."""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, cast

import httpx

from app.core.cache import CacheBackend, MemoryCache, RedisCache
from app.core.config import (
    DEFAULT_STRATZ_USER_AGENT,
    Settings,
    get_settings,
)
from app.core.errors import (
    ProfileUnavailable,
    StratzChallengeError,
    StratzForbidden,
    StratzGraphQLError,
    StratzInvalidResponse,
    StratzPartialResponse,
    StratzRateLimited,
    StratzSchemaDrift,
    StratzUnavailable,
)
from app.core.metrics import record_metric
from app.core.security import redact
from app.providers.base import (
    HistoryWindow,
    RequestLedger,
    canonical_json_sha256,
    provider_cache_key,
)

from .models import (
    StratzHistory,
    StratzHistoryPage,
    StratzMatch,
    StratzModelError,
    StratzPlayerProfile,
)
from .queries import (
    GET_MATCH_CORE,
    GET_PLAYER_HISTORY_PAGE,
    GET_PLAYER_PROFILE,
    GraphQLOperation,
)

logger = logging.getLogger(__name__)
Sleep = Callable[[float], Awaitable[None]]

STRATZ_PAGE_SIZE = 100
STRATZ_RATE_LIMIT_CEILINGS = {
    "second": 6,
    "minute": 120,
    "hour": 1_200,
    "day": 12_000,
}
_WINDOW_SECONDS = {"second": 1.0, "minute": 60.0, "hour": 3_600.0, "day": 86_400.0}
_RATE_HEADER = re.compile(
    r"^(?:x[-_])?rate[-_]?limit[-_](limit|remaining|reset)(?:[-_](second|sec|s|minute|min|m|hour|h|day|d))?$",
    re.IGNORECASE,
)


class RateLimitSnapshot:
    """Rate-limit values reported by a STRATZ response."""

    def __init__(
        self,
        *,
        limits: Mapping[str, int] | None = None,
        remaining: Mapping[str, int] | None = None,
        reset_at: Mapping[str, float] | None = None,
    ) -> None:
        self.limits = dict(limits or {})
        self.remaining = dict(remaining or {})
        self.reset_at = dict(reset_at or {})

    def reset_delay(self, *, now: float | None = None) -> float | None:
        current = time.time() if now is None else now
        delays = [reset - current for reset in self.reset_at.values() if reset > current]
        return min(delays) if delays else None

    def as_dict(self) -> dict[str, dict[str, int | float]]:
        return {
            "limits": dict(self.limits),
            "remaining": dict(self.remaining),
            "reset_at": dict(self.reset_at),
        }


def parse_rate_limit_headers(headers: Mapping[str, str]) -> RateLimitSnapshot:
    """Parse common STRATZ/proxy rate-limit header spellings safely."""

    limits: dict[str, int] = {}
    remaining: dict[str, int] = {}
    reset_at: dict[str, float] = {}
    now = time.time()
    for name, raw_value in headers.items():
        key = name.lower().replace(" ", "")
        if key in {"ratelimit-limit", "x-ratelimit-limit"}:
            _parse_structured_limits(raw_value, limits)
            continue
        if key in {"ratelimit-remaining", "x-ratelimit-remaining"}:
            _put_int(remaining, "default", raw_value)
            continue
        if key in {"ratelimit-reset", "x-ratelimit-reset"}:
            _put_reset(reset_at, "default", raw_value, now)
            continue
        match = _RATE_HEADER.match(key)
        if match is None:
            continue
        kind, raw_bucket = match.groups()
        bucket = _bucket_name(raw_bucket)
        if kind.lower() == "limit":
            _put_int(limits, bucket, raw_value)
        elif kind.lower() == "remaining":
            _put_int(remaining, bucket, raw_value)
        else:
            _put_reset(reset_at, bucket, raw_value, now)
    return RateLimitSnapshot(limits=limits, remaining=remaining, reset_at=reset_at)


def stratz_cache_key(resource: str, *parts: object) -> str:
    return provider_cache_key("stratz", resource, *parts)


class StratzClient:
    """Authenticated STRATZ GraphQL client with bounded retries and paging."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
        cache: CacheBackend | None = None,
        sleep: Sleep = asyncio.sleep,
        rng: Callable[[], float] = random.random,
    ) -> None:
        self.settings = settings or get_settings()
        if self.settings.stratz_user_agent != DEFAULT_STRATZ_USER_AGENT:
            raise ValueError("STRATZ_USER_AGENT must be STRATZ_API")
        self._http = http_client
        self._owns_http = http_client is None
        self.cache = cache or (
            RedisCache(self.settings.redis_url, prefix="dota:stratz")
            if self.settings.app_env == "production"
            else MemoryCache()
        )
        self._sleep = sleep
        self._rng = rng
        self._request_times: list[float] = []
        self._rate_limits = RateLimitSnapshot()
        self.request_ledger = RequestLedger()
        self.request_counts: dict[str, int] = {}
        self.cache_hits = 0

    async def __aenter__(self) -> StratzClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.settings.stratz_timeout_seconds)
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._http is not None and self._owns_http:
            await self._http.aclose()
            self._http = None

    @property
    def request_headers(self) -> dict[str, str]:
        token = self.settings.stratz_api_token
        if not token:
            return {
                "Content-Type": "application/json",
                "User-Agent": DEFAULT_STRATZ_USER_AGENT,
            }
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_STRATZ_USER_AGENT,
        }

    @property
    def auth_headers(self) -> dict[str, str]:
        return self.request_headers

    async def get_player_profile(self, account_id: int) -> StratzPlayerProfile:
        account_id = _positive_id(account_id, "account ID")
        data = await self._graphql(
            GET_PLAYER_PROFILE,
            {"steamAccountId": account_id},
            cache_key=stratz_cache_key("player", account_id),
            cache_ttl=300,
        )
        raw_player = data.get("player")
        if raw_player is None:
            raise ProfileUnavailable("STRATZ profile is private or unavailable")
        profile = self._parse_profile(raw_player)
        _ensure_public_profile(profile)
        if profile.steam_account_id != account_id:
            raise StratzSchemaDrift("STRATZ profile account ID does not match the request")
        return profile

    async def get_profile(self, account_id: int) -> StratzPlayerProfile:
        return await self.get_player_profile(account_id)

    async def get_player_history_page(
        self,
        account_id: int,
        *,
        start_timestamp: int,
        end_timestamp: int,
        take: int = STRATZ_PAGE_SIZE,
        skip: int = 0,
        _ledger: RequestLedger | None = None,
    ) -> StratzHistoryPage:
        account_id = _positive_id(account_id, "account ID")
        start = int(start_timestamp)
        end = int(end_timestamp)
        if start > end:
            raise ValueError("history window start must not be after its end")
        page_size = min(STRATZ_PAGE_SIZE, max(1, int(take)))
        offset = max(0, int(skip))
        data = await self._graphql(
            GET_PLAYER_HISTORY_PAGE,
            {
                "steamAccountId": account_id,
                "startDateTime": start,
                "endDateTime": end,
                "take": page_size,
                "skip": offset,
            },
            cache_key=stratz_cache_key(
                "history",
                account_id,
                f"{start}-{end}",
                GET_PLAYER_HISTORY_PAGE.version,
                "page",
                offset,
                page_size,
            ),
            cache_ttl=120,
            ledger=_ledger,
        )
        raw_player = data.get("player")
        if raw_player is None:
            raise ProfileUnavailable("STRATZ profile is private or unavailable")
        page = self._parse_history_page(data, account_id, offset, page_size)
        _ensure_public_profile(page.profile)
        if page.profile.steam_account_id != account_id:
            raise StratzSchemaDrift("STRATZ history account ID does not match the request")
        return page

    async def get_history_page(self, *args: Any, **kwargs: Any) -> StratzHistoryPage:
        return await self.get_player_history_page(*args, **kwargs)

    async def get_player_history(
        self,
        account_id: int,
        *,
        days: int = 365,
        window_end: int | None = None,
        window: HistoryWindow | None = None,
    ) -> StratzHistory:
        account_id = _positive_id(account_id, "account ID")
        window = window or HistoryWindow.for_days(days, end_timestamp=window_end)
        ledger = RequestLedger()
        pages: list[StratzHistoryPage] = []
        raw_pages: list[Mapping[str, Any]] = []
        matches: list[StratzMatch] = []
        profile: StratzPlayerProfile | None = None
        truncated = False
        for page_number in range(self.settings.effective_stratz_max_history_pages):
            page = await self.get_player_history_page(
                account_id,
                start_timestamp=window.start_timestamp,
                end_timestamp=window.end_timestamp,
                take=STRATZ_PAGE_SIZE,
                skip=page_number * STRATZ_PAGE_SIZE,
                _ledger=ledger,
            )
            ledger.record_page()
            self.request_ledger.record_page()
            pages.append(page)
            raw_pages.append(page.raw_data)
            profile = profile or page.profile
            matches.extend(
                match
                for match in page.matches
                if match.started_at is not None
                and window.start_timestamp <= match.started_at <= window.end_timestamp
            )
            if not page.matches:
                break
            starts = [match.started_at for match in page.matches if match.started_at is not None]
            reached_window_start = bool(starts and min(starts) < window.start_timestamp)
            if len(page.matches) < STRATZ_PAGE_SIZE or reached_window_start:
                break
            if page_number + 1 == self.settings.effective_stratz_max_history_pages:
                truncated = True
                record_metric("stratz.pages_truncated")
                break
        else:
            truncated = True
        if profile is None:
            raise ProfileUnavailable("STRATZ profile is private or unavailable")
        unique_matches, duplicate_count = _deduplicate_matches(tuple(matches))
        return StratzHistory(
            profile=profile,
            matches=unique_matches,
            pages=tuple(pages),
            raw_pages=tuple(raw_pages),
            ledger=ledger,
            window=window,
            fetched_at=datetime.now(UTC).isoformat(),
            operation_name=GET_PLAYER_HISTORY_PAGE.name,
            operation_version=GET_PLAYER_HISTORY_PAGE.version,
            operation_document_sha256=GET_PLAYER_HISTORY_PAGE.document_sha256,
            truncated=truncated,
            duplicate_match_count=duplicate_count,
        )

    async def get_history(self, *args: Any, **kwargs: Any) -> StratzHistory:
        return await self.get_player_history(*args, **kwargs)

    async def get_match_core(
        self,
        match_id: int,
        *,
        account_id: int | None = None,
    ) -> StratzMatch:
        match_id = _positive_id(match_id, "match ID")
        account_id = (
            _positive_id(account_id, "account ID") if account_id is not None else None
        )
        data = await self._graphql(
            GET_MATCH_CORE,
            {"matchId": match_id},
            cache_key=stratz_cache_key(
                "match",
                match_id,
                GET_MATCH_CORE.version,
                *("account", account_id) if account_id is not None else (),
            ),
            cache_ttl=None,
        )
        raw_match = data.get("match")
        if raw_match is None:
            raise StratzUnavailable("STRATZ match is private or unavailable")
        match = self._parse_match(raw_match, path="data.match")
        if match.match_id != match_id:
            raise StratzSchemaDrift("STRATZ match ID does not match the request")
        if account_id is not None and match.player_for(account_id) is None:
            raise StratzUnavailable("STRATZ match does not contain the requested player")
        return match

    async def _graphql(
        self,
        operation: GraphQLOperation,
        variables: Mapping[str, Any],
        *,
        cache_key: str | None = None,
        cache_ttl: int | None = None,
        ledger: RequestLedger | None = None,
    ) -> Mapping[str, Any]:
        if not self.settings.stratz_api_token:
            raise StratzForbidden("STRATZ_API_TOKEN is not configured")
        if cache_key:
            cached = self.cache.get(cache_key)
            if isinstance(cached, Mapping) and isinstance(cached.get("data"), Mapping):
                self.cache_hits += 1
                active_ledger = ledger or self.request_ledger
                active_ledger.record_cache_hit()
                if active_ledger is not self.request_ledger:
                    self.request_ledger.record_cache_hit()
                record_metric("stratz.cache.hit", tags={"resource": cache_key.split(":", 2)[1]})
                return cast(Mapping[str, Any], cached["data"])
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.settings.stratz_timeout_seconds)
        active_ledger = ledger or self.request_ledger
        retries = max(0, int(self.settings.stratz_max_retries))
        body = {
            "operationName": operation.name,
            "variables": dict(variables),
            "query": operation.document,
        }
        for attempt in range(retries + 1):
            await self._throttle()
            try:
                response = await self._http.post(
                    self.settings.stratz_base_url,
                    headers=self.request_headers,
                    json=body,
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                self._record_attempt(active_ledger, operation, None)
                if attempt >= retries:
                    record_metric("stratz.request.error", tags={"kind": type(exc).__name__})
                    raise StratzUnavailable("STRATZ is unavailable") from exc
                self._record_retry(active_ledger)
                await self._backoff(attempt)
                continue

            self._record_attempt(active_ledger, operation, response.status_code)
            self._rate_limits = parse_rate_limit_headers(response.headers)
            if response.status_code == 429:
                record_metric("stratz.response", tags={"status": "429"})
                if attempt >= retries:
                    raise StratzRateLimited("STRATZ rate limit reached")
                self._record_retry(active_ledger)
                await self._backoff(
                    attempt,
                    retry_after=response.headers.get("Retry-After"),
                )
                continue
            if response.status_code >= 500:
                record_metric("stratz.response", tags={"status": str(response.status_code)})
                if attempt >= retries:
                    raise StratzUnavailable("STRATZ is unavailable")
                self._record_retry(active_ledger)
                await self._backoff(attempt)
                continue
            if response.status_code == 403:
                if _is_html_challenge(response):
                    raise StratzChallengeError(
                        "Cloudflare edge challenge — check User-Agent: STRATZ_API"
                    )
                raise StratzForbidden("STRATZ rejected the request credentials")
            if response.status_code == 401:
                raise StratzForbidden("STRATZ rejected the request credentials")
            if response.status_code >= 400:
                raise StratzUnavailable("STRATZ rejected the request")
            try:
                payload = response.json()
            except (TypeError, ValueError) as exc:
                raise StratzInvalidResponse("STRATZ returned invalid JSON") from exc
            if not isinstance(payload, Mapping):
                raise StratzInvalidResponse("STRATZ returned a non-object JSON response")
            errors = payload.get("errors")
            if errors:
                messages = _graphql_error_messages(errors, self.settings.stratz_api_token)
                record_metric("stratz.graphql.error", tags={"operation": operation.name})
                if _is_schema_error(messages):
                    raise StratzSchemaDrift(
                        f"STRATZ GraphQL schema drift in {operation.name}: {messages}"
                    )
                if not isinstance(payload.get("data"), Mapping):
                    raise StratzGraphQLError(
                        f"STRATZ GraphQL operation {operation.name} failed: {messages}"
                    )
                raise StratzPartialResponse(
                    f"STRATZ GraphQL operation {operation.name} failed: {messages}"
                )
            data = payload.get("data")
            if not isinstance(data, Mapping):
                raise StratzInvalidResponse(
                    f"STRATZ operation {operation.name} returned no data"
                )
            self._record_success(active_ledger)
            if cache_key:
                self.cache.set(cache_key, {"data": data}, cache_ttl)
            record_metric("stratz.response", tags={"status": str(response.status_code)})
            logger.info(
                "stratz_request operation=%s version=%s status=%s",
                operation.name,
                operation.version,
                response.status_code,
            )
            return cast(Mapping[str, Any], data)
        raise StratzUnavailable("STRATZ request failed")

    def _record_attempt(
        self,
        ledger: RequestLedger,
        operation: GraphQLOperation,
        status_code: int | None,
    ) -> None:
        ledger.record_attempt(operation.name, status_code)
        if ledger is not self.request_ledger:
            self.request_ledger.record_attempt(operation.name, status_code)
        self.request_counts[operation.name] = self.request_counts.get(operation.name, 0) + 1
        record_metric("stratz.request.attempt", tags={"operation": operation.name})

    def _record_retry(self, ledger: RequestLedger) -> None:
        ledger.record_retry()
        if ledger is not self.request_ledger:
            self.request_ledger.record_retry()

    def _record_success(self, ledger: RequestLedger) -> None:
        ledger.record_success()
        if ledger is not self.request_ledger:
            self.request_ledger.record_success()

    async def _throttle(self) -> None:
        delay = 0.0
        if any(remaining <= 0 for remaining in self._rate_limits.remaining.values()):
            delay = self._rate_limits.reset_delay() or 0.0
        now = time.monotonic()
        self._request_times = [timestamp for timestamp in self._request_times if now - timestamp < 86_400]
        live_limits = {
            bucket: max(1, min(limit, self._rate_limits.limits.get(bucket, limit)))
            for bucket, limit in STRATZ_RATE_LIMIT_CEILINGS.items()
        }
        for bucket, limit in live_limits.items():
            window = _WINDOW_SECONDS[bucket]
            active = [timestamp for timestamp in self._request_times if now - timestamp < window]
            if len(active) >= limit:
                delay = max(delay, active[0] + window - now)
        if delay > 30.0:
            raise StratzRateLimited("STRATZ rate-limit reset exceeds the bounded wait window")
        if delay > 0:
            await self._sleep(delay)
        self._request_times.append(time.monotonic())

    async def _backoff(self, attempt: int, *, retry_after: str | None = None) -> None:
        delay = _retry_after_seconds(retry_after)
        if delay is None:
            delay = self._rate_limits.reset_delay()
        if delay is None:
            delay = min(2**attempt, 30.0)
        delay = min(max(0.0, delay), 30.0) + self._rng() * 0.25
        await self._sleep(delay)

    def _parse_profile(self, raw_player: Any) -> StratzPlayerProfile:
        if isinstance(raw_player, Mapping) and raw_player.get("steamAccount") is None:
            raise ProfileUnavailable("STRATZ profile is private or unavailable")
        try:
            return StratzPlayerProfile.from_graphql(raw_player)
        except StratzModelError as exc:
            raise StratzSchemaDrift(str(exc)) from exc

    def _parse_history_page(
        self,
        data: Mapping[str, Any],
        account_id: int,
        skip: int,
        take: int,
    ) -> StratzHistoryPage:
        try:
            return StratzHistoryPage.from_graphql(
                data,
                account_id=account_id,
                skip=skip,
                take=take,
            )
        except StratzModelError as exc:
            if "data.player is unavailable" in str(exc) or "steamAccount" in str(exc):
                raise ProfileUnavailable("STRATZ profile is private or unavailable") from exc
            raise StratzSchemaDrift(str(exc)) from exc

    def _parse_match(self, raw_match: Any, *, path: str) -> StratzMatch:
        try:
            return StratzMatch.from_graphql(raw_match, path=path)
        except StratzModelError as exc:
            raise StratzSchemaDrift(str(exc)) from exc


def _deduplicate_matches(matches: tuple[StratzMatch, ...]) -> tuple[tuple[StratzMatch, ...], int]:
    chosen: dict[int, StratzMatch] = {}
    duplicates = 0
    for match in matches:
        previous = chosen.get(match.match_id)
        if previous is None:
            chosen[match.match_id] = match
            continue
        duplicates += 1
        if _match_preference(match) > _match_preference(previous):
            chosen[match.match_id] = match
    return (
        tuple(
            sorted(
                chosen.values(),
                key=lambda item: (item.started_at is None, -(item.started_at or 0), item.match_id),
            )
        ),
        duplicates,
    )


def _match_preference(match: StratzMatch) -> tuple[int, str]:
    values: list[Any] = [
        match.did_radiant_win,
        match.duration_seconds,
        match.started_at,
        match.ended_at,
        match.lobby_type,
        match.game_mode,
        match.game_version_id,
        match.parsed_at,
    ]
    for player in match.players:
        values.extend(player.as_dict().values())
    return sum(value is not None for value in values), canonical_json_sha256(match.as_dict())


def _positive_id(value: int, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be positive")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be positive") from exc
    if parsed <= 0:
        raise ValueError(f"{label} must be positive")
    return parsed


def _ensure_public_profile(profile: StratzPlayerProfile) -> None:
    if profile.is_anonymous is True or profile.is_stratz_public is False:
        raise ProfileUnavailable("STRATZ profile is private or unavailable")


def _bucket_name(raw_bucket: str | None) -> str:
    if raw_bucket is None:
        return "default"
    value = raw_bucket.lower()
    if value in {"second", "sec", "s"}:
        return "second"
    if value in {"minute", "min", "m"}:
        return "minute"
    if value in {"hour", "h"}:
        return "hour"
    if value in {"day", "d"}:
        return "day"
    return value


def _put_int(target: dict[str, int], key: str, value: str) -> None:
    try:
        target[key] = int(value.split(";", 1)[0].strip())
    except (TypeError, ValueError):
        return


def _put_reset(target: dict[str, float], key: str, value: str, now: float) -> None:
    try:
        parsed = float(value.split(";", 1)[0].strip())
    except (TypeError, ValueError):
        return
    target[key] = parsed if parsed > now - 60 else now + max(0.0, parsed)


def _parse_structured_limits(value: str, target: dict[str, int]) -> None:
    for item in value.split(","):
        pieces = [piece.strip() for piece in item.split(";")]
        try:
            limit = int(pieces[0])
        except (TypeError, ValueError):
            continue
        bucket = "default"
        for piece in pieces[1:]:
            if piece.lower().startswith("w="):
                try:
                    seconds = float(piece.split("=", 1)[1])
                except ValueError:
                    continue
                bucket = _bucket_name(
                    "second"
                    if seconds <= 1
                    else "minute"
                    if seconds <= 60
                    else "hour"
                    if seconds <= 3_600
                    else "day"
                )
        target[bucket] = limit


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return max(0.0, parsed.timestamp() - time.time())


def _is_html_challenge(response: httpx.Response) -> bool:
    content_type = response.headers.get("Content-Type", "").lower()
    body = response.content[:512].lstrip().lower()
    return "text/html" in content_type or body.startswith(b"<!doctype html") or b"<html" in body


def _graphql_error_messages(errors: Any, secret: str | None) -> str:
    if not isinstance(errors, (list, tuple)):
        errors = [errors]
    messages: list[str] = []
    for error in errors:
        if isinstance(error, Mapping):
            message = error.get("message", "unknown GraphQL error")
        else:
            message = error
        messages.append(str(redact(str(message), (secret,)))[:500])
    return "; ".join(messages) or "unknown GraphQL error"


def _is_schema_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        marker in lowered
        for marker in ("cannot query field", "unknown argument", "unknown type", "does not exist")
    )


__all__ = [
    "RateLimitSnapshot",
    "STRATZ_PAGE_SIZE",
    "STRATZ_RATE_LIMIT_CEILINGS",
    "StratzClient",
    "parse_rate_limit_headers",
    "stratz_cache_key",
]

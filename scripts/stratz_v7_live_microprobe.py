#!/usr/bin/env python3
"""Run the bounded, direct-HTTP STRATZ V7 live microprobe.

The command is intentionally separate from the production provider. It reads
only ``STRATZ_API_TOKEN`` from an explicitly supplied dotenv file, makes at
most eight physical requests, and stores redacted response evidence under the
ignored local corpus tree. Ordinary tests import its pure helpers and never
open a network transport.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import time
import uuid
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.stratz.client import parse_rate_limit_headers  # noqa: E402
from app.stratz.queries import (  # noqa: E402
    FIND_SHORT_PARSED_TRAJECTORY,
    GET_SHORT_PARSED_TRAJECTORY,
    PROBE_PARSED_AVAILABILITY,
    PROBE_PARSED_CORE_BATCH_FALLBACK,
    PROBE_PARSED_EVIDENCE_BATCH,
    V7_PARSED_SUBTYPE_SHAPE_SENTINEL,
    V7_SCHEMA_SENTINEL,
    GraphQLOperation,
)

DEFAULT_ENDPOINT = "https://api.stratz.com/graphql"
DEFAULT_OUTPUT_DIR = ROOT / ".local" / "corpora" / "stratz" / "v7-prep"
MAX_PHYSICAL_CALLS = 8
DEFAULT_MAX_RETRIES = 1
DEFAULT_TIMEOUT_SECONDS = 30.0
SHORT_TRAJECTORY_SECONDS = 1_500
_COMPLEXITY_RE = re.compile(r"\bcomplexity(?:\s+is|\s*:)\s*(\d+)", re.IGNORECASE)
_SCHEMA_MARKERS = (
    "cannot query field",
    "unknown argument",
    "unknown type",
    "does not exist",
    "graphql validation",
    "validation failed",
)
_SENSITIVE_HEADER_MARKERS = (
    "authorization",
    "cookie",
    "set-cookie",
    "api-key",
    "apikey",
    "secret",
    "token",
)
Sleep = Callable[[float], Awaitable[None]]


class MicroprobeError(RuntimeError):
    """A safe, user-facing microprobe setup or transport error."""


class PhysicalBudgetExceeded(MicroprobeError):
    """The hard physical-request budget was reached."""


def load_stratz_token(dotenv_path: Path) -> str:
    """Read only the STRATZ token from an explicitly supplied dotenv file."""

    try:
        values = dotenv_values(dotenv_path, interpolate=False)
    except OSError as exc:
        raise MicroprobeError("cannot read the supplied dotenv file") from exc
    token = values.get("STRATZ_API_TOKEN")
    if not isinstance(token, str) or not token.strip():
        raise MicroprobeError("STRATZ_API_TOKEN is missing from the supplied dotenv file")
    return token.strip()


def redact_text(value: str, secret: str | None) -> str:
    """Redact a token without exposing any token-derived diagnostic."""

    if secret:
        return value.replace(secret, "[REDACTED]")
    return value


def redact_bytes(value: bytes, secret: str | None) -> bytes:
    if not secret:
        return value
    return value.replace(secret.encode("utf-8"), b"[REDACTED]")


def safe_response_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Keep response metadata useful while excluding credential-bearing headers."""

    safe: dict[str, str] = {}
    for name, value in headers.items():
        lowered = name.casefold()
        if any(marker in lowered for marker in _SENSITIVE_HEADER_MARKERS):
            continue
        safe[name] = value
    return safe


def safe_rate_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        name: value
        for name, value in headers.items()
        if name.casefold() == "retry-after"
        or "rate-limit" in name.casefold()
        or "ratelimit" in name.casefold()
    }


def extract_complexity(payload: Mapping[str, Any] | None, headers: Mapping[str, str]) -> int | None:
    """Extract only provider-reported complexity, never estimate it locally."""

    for name, value in headers.items():
        if "complexity" not in name.casefold() and "query-cost" not in name.casefold():
            continue
        match = re.search(r"\d+", str(value))
        if match:
            return int(match.group())
    if not isinstance(payload, Mapping):
        return None
    candidates: list[Any] = []
    extensions = payload.get("extensions")
    if isinstance(extensions, Mapping):
        candidates.extend(
            value
            for key, value in extensions.items()
            if "complexity" in str(key).casefold() or "cost" in str(key).casefold()
        )
    errors = payload.get("errors")
    if isinstance(errors, Sequence) and not isinstance(errors, (str, bytes, bytearray)):
        for error in errors:
            if isinstance(error, Mapping):
                error_extensions = error.get("extensions")
                if isinstance(error_extensions, Mapping):
                    candidates.extend(
                        value
                        for key, value in error_extensions.items()
                        if "complexity" in str(key).casefold() or "cost" in str(key).casefold()
                    )
                candidates.append(error.get("message"))
    for candidate in candidates:
        if isinstance(candidate, bool):
            continue
        if isinstance(candidate, (int, float)):
            return int(candidate)
        match = _COMPLEXITY_RE.search(str(candidate))
        if match:
            return int(match.group(1))
    return None


def graphql_error_text(payload: Mapping[str, Any] | None, secret: str | None) -> str | None:
    if not isinstance(payload, Mapping) or not payload.get("errors"):
        return None
    errors = payload["errors"]
    if not isinstance(errors, Sequence) or isinstance(errors, (str, bytes, bytearray)):
        errors = (errors,)
    messages: list[str] = []
    for error in errors:
        if isinstance(error, Mapping):
            message = error.get("message", "unknown GraphQL error")
        else:
            message = error
        messages.append(redact_text(str(message), secret)[:500])
    return "; ".join(messages) or "unknown GraphQL error"


def is_complexity_failure(payload: Mapping[str, Any] | None, reason: str | None) -> bool:
    text = (reason or "").casefold()
    if "complexity" in text:
        return True
    if not isinstance(payload, Mapping):
        return False
    errors = payload.get("errors")
    if not isinstance(errors, Sequence) or isinstance(errors, (str, bytes, bytearray)):
        errors = (errors,)
    for error in errors:
        if isinstance(error, Mapping):
            extensions = error.get("extensions")
            if isinstance(extensions, Mapping) and str(extensions.get("code", "")).casefold() == "complexity":
                return True
    return False


def is_schema_failure(reason: str | None) -> bool:
    text = (reason or "").casefold()
    return any(marker in text for marker in _SCHEMA_MARKERS)


def _type_ref_is_object(value: Any) -> bool:
    return isinstance(value, Mapping) and isinstance(value.get("name"), str)


def validate_schema_sentinel(payload: Mapping[str, Any] | None) -> tuple[bool, dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, Mapping) else None
    required = (
        "match",
        "matchPlayer",
        "playerStats",
        "playerPlayback",
        "matchPlayback",
        "player",
        "matchesRequest",
    )
    if not isinstance(data, Mapping):
        return False, {"required_types": 0, "missing_types": list(required), "schema_drift": True}
    missing = [name for name in required if not _type_ref_is_object(data.get(name))]
    return not missing, {
        "required_types": len(required) - len(missing),
        "missing_types": missing,
        "schema_drift": bool(missing),
    }


SUBTYPE_ALIASES = (
    "laneReport",
    "towerDeath",
    "pickBan",
    "farmDistribution",
    "locationReport",
    "actionReport",
    "heroDamageReport",
    "abilityCastReport",
    "inventoryReport",
    "killEvent",
    "deathEvent",
    "assistEvent",
    "wardEvent",
    "wardDestruction",
    "itemPurchase",
    "itemUsed",
    "buffEvent",
    "courierKill",
    "runeEvent",
    "eLane",
    "ePosition",
    "eRole",
    "eLaneOut",
    "eLeaver",
    "eLobby",
    "eMode",
    "eRune",
)


def validate_subtype_sentinel(payload: Mapping[str, Any] | None) -> tuple[bool, dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, Mapping) else None
    if not isinstance(data, Mapping):
        return False, {"aliases_present": 0, "aliases_available": 0, "schema_drift": True}
    present = [alias for alias in SUBTYPE_ALIASES if alias in data]
    available = [alias for alias in present if data.get(alias) is not None]
    ok = len(present) == len(SUBTYPE_ALIASES)
    return ok, {
        "aliases_present": len(present),
        "aliases_available": len(available),
        "unavailable_aliases": [alias for alias in SUBTYPE_ALIASES if alias not in available],
        "schema_drift": not ok,
    }


def _rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        return (value,)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def summarize_parsed_batch(
    payload: Mapping[str, Any] | None,
    requested_ids: Sequence[int],
) -> tuple[bool, dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, Mapping) else None
    player = data.get("player") if isinstance(data, Mapping) else None
    matches_value = player.get("matches") if isinstance(player, Mapping) else None
    matches = _rows(matches_value)
    shape_ok = isinstance(player, Mapping) and isinstance(matches_value, (Mapping, Sequence)) and not isinstance(
        matches_value, (str, bytes, bytearray)
    )
    requested = {int(value) for value in requested_ids}
    returned_ids: list[int] = []
    stats_non_null = 0
    stats_null = 0
    missing_player_rows = 0
    structural_failure = False
    for match in matches:
        match_id = match.get("id")
        if isinstance(match_id, bool) or not isinstance(match_id, int):
            shape_ok = False
            structural_failure = True
        else:
            returned_ids.append(match_id)
        player_value = match.get("players")
        if not isinstance(player_value, (Mapping, Sequence)) or isinstance(
            player_value, (str, bytes, bytearray)
        ):
            shape_ok = False
            structural_failure = True
            continue
        selected_players = _rows(player_value)
        if not selected_players:
            missing_player_rows += 1
        for selected_player in selected_players:
            if "stats" not in selected_player:
                shape_ok = False
                structural_failure = True
            elif selected_player.get("stats") is None:
                stats_null += 1
            elif not isinstance(selected_player.get("stats"), Mapping):
                shape_ok = False
                if selected_player.get("stats") is not None:
                    structural_failure = True
            else:
                stats_non_null += 1
    returned_requested_count = sum(match_id in requested for match_id in returned_ids)
    if returned_requested_count != len(requested_ids) or missing_player_rows or stats_null:
        shape_ok = False
    summary = {
        "requested_batch_size": len(requested_ids),
        "returned_match_count": len(matches),
        "returned_requested_match_count": returned_requested_count,
        "stats_non_null_count": stats_non_null,
        "stats_null_count": stats_null,
        "missing_player_rows": missing_player_rows,
        "partial_response": returned_requested_count != len(requested_ids)
        or bool(missing_player_rows)
        or bool(stats_null),
        "schema_drift": structural_failure,
        "shape_failure_reason": (
            "missing_requested_matches"
            if returned_requested_count != len(requested_ids)
            else "missing_player_or_stats"
            if missing_player_rows or stats_null
            else "invalid_response_shape"
            if structural_failure
            else None
        ),
        "shape_ok": shape_ok,
    }
    return bool(shape_ok), summary


def summarize_short_index(payload: Mapping[str, Any] | None) -> tuple[bool, dict[str, Any], int | None]:
    data = payload.get("data") if isinstance(payload, Mapping) else None
    player = data.get("player") if isinstance(data, Mapping) else None
    matches_value = player.get("matches") if isinstance(player, Mapping) else None
    matches = _rows(matches_value)
    shape_ok = isinstance(player, Mapping) and isinstance(matches_value, (Mapping, Sequence)) and not isinstance(
        matches_value, (str, bytes, bytearray)
    )
    candidates: list[tuple[int, int]] = []
    for match in matches:
        match_id = match.get("id")
        duration = match.get("durationSeconds")
        if isinstance(match_id, bool) or not isinstance(match_id, int):
            shape_ok = False
            continue
        if isinstance(duration, bool) or not isinstance(duration, int):
            shape_ok = False
            continue
        player_value = match.get("players")
        if not isinstance(player_value, (Mapping, Sequence)) or isinstance(
            player_value, (str, bytes, bytearray)
        ):
            shape_ok = False
            continue
        for row in _rows(player_value):
            if row.get("heroId") is not None or row.get("level") is not None:
                candidates.append((duration, match_id))
                break
    chosen = min(candidates) if candidates else None
    return bool(shape_ok), {
        "returned_match_count": len(matches),
        "parsed_candidate_count": len(candidates),
        "shortest_duration_seconds": chosen[0] if chosen else None,
        "short_match_found": bool(chosen),
    }, chosen[1] if chosen else None


def summarize_short_trajectory(payload: Mapping[str, Any] | None) -> tuple[bool, dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, Mapping) else None
    match = data.get("match") if isinstance(data, Mapping) else None
    if not isinstance(match, Mapping):
        return False, {"match_present": False}
    players = _rows(match.get("players"))
    shape_ok = (
        isinstance(match.get("id"), int)
        and not isinstance(match.get("id"), bool)
        and isinstance(match.get("durationSeconds"), int)
        and not isinstance(match.get("durationSeconds"), bool)
    )
    stats_rows = 0
    lengths: dict[str, int | None] = {"networth": None, "experience": None, "level": None}
    for player in players:
        stats = player.get("stats")
        if stats is None:
            continue
        if not isinstance(stats, Mapping):
            shape_ok = False
            continue
        stats_rows += 1
        for source, target in (
            ("networthPerMinute", "networth"),
            ("experiencePerMinute", "experience"),
            ("level", "level"),
        ):
            value = stats.get(source)
            if value is not None and not isinstance(value, Sequence):
                shape_ok = False
            elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                lengths[target] = len(value)
    return bool(shape_ok), {
        "match_present": True,
        "duration_seconds": match.get("durationSeconds"),
        "stats_player_count": stats_rows,
        "series_lengths": lengths,
    }


def summarize_availability(payload: Mapping[str, Any] | None) -> tuple[bool, dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, Mapping) else None
    player = data.get("player") if isinstance(data, Mapping) else None
    if not isinstance(player, Mapping):
        return False, {"aliases": {}}
    aliases: dict[str, dict[str, int]] = {}
    shape_ok = True
    for alias in ("allRanked", "parsedRanked", "allTurbo", "parsedTurbo"):
        value = player.get(alias)
        if not isinstance(value, (Mapping, Sequence)) or isinstance(value, (str, bytes, bytearray)):
            shape_ok = False
            aliases[alias] = {"rows": 0, "parsed_rows": 0}
            continue
        rows = _rows(value)
        aliases[alias] = {
            "rows": len(rows),
            "parsed_rows": sum(row.get("parsedDateTime") is not None for row in rows),
        }
    return shape_ok, {"aliases": aliases}


def parse_retry_after(value: str | None) -> float | None:
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


def planned_batch_sizes(match_count: int) -> tuple[int, ...]:
    """Return only the prepared 4→8→16 ladder sizes available locally."""

    count = max(0, int(match_count))
    return tuple(size for size in (4, 8, 16) if count >= size)


class MicroprobeRunner:
    """Small sequential runner with immutable local response archives."""

    def __init__(
        self,
        token: str,
        *,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_physical_calls: int = MAX_PHYSICAL_CALLS,
        http_client: httpx.AsyncClient | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        if not token:
            raise MicroprobeError("STRATZ_API_TOKEN is empty")
        if max_physical_calls < 1 or max_physical_calls > MAX_PHYSICAL_CALLS:
            raise MicroprobeError("physical request budget must be between 1 and 8")
        self._token = token
        self.endpoint = endpoint
        self.max_retries = max(0, int(max_retries))
        self.max_physical_calls = max_physical_calls
        self._http = http_client
        self._owns_http = http_client is None
        self._timeout_seconds = timeout_seconds
        self._sleep = sleep
        self._physical_calls = 0
        self._ordinal = 0
        self._logical_calls = 0
        self._ledger_rows: list[dict[str, Any]] = []
        self._calls: list[dict[str, Any]] = []
        self._started_at = datetime.now(UTC)
        run_id = self._started_at.strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
        self.run_dir = output_dir / "runs" / run_id
        self.responses_dir = self.run_dir / "responses"
        self.headers_dir = self.run_dir / "headers"
        self.ledger_dir = self.run_dir / "ledgers"
        for directory in (self.responses_dir, self.headers_dir, self.ledger_dir):
            directory.mkdir(parents=True, exist_ok=False, mode=0o700)
        self.ledger_path = self.ledger_dir / "request-ledger.jsonl"

    async def __aenter__(self) -> MicroprobeRunner:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self._timeout_seconds)
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._http is not None and self._owns_http:
            await self._http.aclose()
            self._http = None

    @property
    def physical_calls(self) -> int:
        return self._physical_calls

    async def request(
        self,
        operation: GraphQLOperation,
        variables: Mapping[str, Any],
        *,
        batch_size: int | None = None,
    ) -> dict[str, Any]:
        self._logical_calls += 1
        logical_call = self._logical_calls
        started = time.monotonic()
        attempts: list[dict[str, Any]] = []
        payload: Mapping[str, Any] | None = None
        final_reason: str | None = None
        final_kind: str | None = None
        final_status: int | None = None
        final_complexity: int | None = None
        final_shape_payload: Mapping[str, Any] | None = None
        for attempt in range(self.max_retries + 1):
            if self._physical_calls >= self.max_physical_calls:
                final_reason = "physical request budget reached"
                final_kind = "physical_budget"
                break
            self._physical_calls += 1
            self._ordinal += 1
            physical_ordinal = self._ordinal
            attempt_started = time.monotonic()
            headers: dict[str, str] = {}
            status: int | None = None
            response_bytes = 0
            raw_response_sha256: str | None = None
            raw_path: str | None = None
            headers_path: str | None = None
            retryable = False
            retry_after: float | None = None
            try:
                if self._http is None:
                    self._http = httpx.AsyncClient(timeout=self._timeout_seconds)
                response = await self._http.post(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {self._token}",
                        "Content-Type": "application/json",
                        "User-Agent": "STRATZ_API",
                    },
                    json={
                        "operationName": operation.name,
                        "variables": dict(variables),
                        "query": operation.document,
                    },
                )
                status = response.status_code
                response_bytes = len(response.content)
                raw_response_sha256 = hashlib.sha256(response.content).hexdigest()
                headers = {
                    name: redact_text(value, self._token)
                    for name, value in safe_response_headers(response.headers).items()
                }
                raw_path, headers_path = self._archive_response(
                    physical_ordinal,
                    operation,
                    response.content,
                    headers,
                )
                try:
                    candidate = response.json()
                except (TypeError, ValueError):
                    candidate = None
                if isinstance(candidate, Mapping):
                    payload = candidate
                    final_shape_payload = candidate
                else:
                    payload = None
                    final_shape_payload = None
                final_status = status
                final_complexity = extract_complexity(payload, headers)
                reason = graphql_error_text(payload, self._token)
                if status >= 400:
                    reason = reason or f"HTTP {status}"
                    final_kind = "http_error"
                    retryable = status == 429 or status >= 500
                    retry_after = parse_retry_after(response.headers.get("Retry-After"))
                    if status in {401, 403}:
                        final_kind = "authentication_failure"
                elif not isinstance(payload, Mapping):
                    reason = "STRATZ returned invalid JSON"
                    final_kind = "invalid_json"
                elif reason:
                    final_kind = "graphql_error"
                elif not isinstance(payload.get("data"), Mapping):
                    reason = f"STRATZ operation {operation.name} returned no data"
                    final_kind = "missing_data"
                else:
                    reason = None
                    final_kind = None
                final_reason = reason
                attempts.append(
                    self._ledger_row(
                        operation,
                        variables,
                        logical_call=logical_call,
                        physical_ordinal=physical_ordinal,
                        attempt=attempt,
                        status=status,
                        response_bytes=response_bytes,
                        raw_response_sha256=raw_response_sha256,
                        latency=time.monotonic() - attempt_started,
                        complexity=final_complexity,
                        headers=headers,
                        raw_path=raw_path,
                        headers_path=headers_path,
                        retrying=retryable and attempt < self.max_retries,
                        error_kind=final_kind,
                        error=reason,
                    )
                )
                if retryable and attempt < self.max_retries:
                    delay = retry_after
                    if delay is None:
                        delay = 0.25 * (2**attempt)
                    rate = parse_rate_limit_headers(response.headers)
                    reset_delay = rate.reset_delay()
                    if reset_delay is not None:
                        delay = max(delay, reset_delay)
                    if delay > 30:
                        final_reason = "STRATZ rate-limit reset exceeds bounded wait"
                        break
                    await self._sleep(delay)
                    continue
                break
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                final_reason = redact_text(type(exc).__name__, self._token)
                final_kind = "transport_error"
                attempts.append(
                    self._ledger_row(
                        operation,
                        variables,
                        logical_call=logical_call,
                        physical_ordinal=physical_ordinal,
                        attempt=attempt,
                        status=None,
                        response_bytes=0,
                        raw_response_sha256=None,
                        latency=time.monotonic() - attempt_started,
                        complexity=None,
                        headers={},
                        raw_path=None,
                        headers_path=None,
                        retrying=attempt < self.max_retries,
                        error_kind=final_kind,
                        error=final_reason,
                    )
                )
                if attempt < self.max_retries:
                    await self._sleep(0.25 * (2**attempt))
                    continue
                break
        self._ledger_rows.extend(attempts)
        self._append_ledger(attempts)
        safe_rate = attempts[-1].get("safe_rate_headers", {}) if attempts else {}
        parsed_rate = attempts[-1].get("rate_headers", {}) if attempts else {}
        result = {
            "logical_call": logical_call,
            "operation": operation.name,
            "operation_version": operation.version,
            "operation_document_sha256": operation.document_sha256,
            "batch_size": batch_size,
            "status": "success" if final_reason is None and final_status is not None and final_status < 400 else "failed",
            "http_status": final_status,
            "response_bytes": sum(int(row["response_bytes"]) for row in attempts),
            "raw_response_sha256": attempts[-1].get("raw_response_sha256") if attempts else None,
            "latency_seconds": round(time.monotonic() - started, 6),
            "complexity": final_complexity,
            "retries": max(0, len(attempts) - 1),
            "cache_hit": False,
            "cache_miss": True,
            "safe_rate_headers": safe_rate,
            "rate_limits": parsed_rate,
            "reason": final_reason,
            "error_kind": final_kind,
            "raw_response_paths": [row["raw_path"] for row in attempts if row.get("raw_path")],
            "response_header_paths": [row["headers_path"] for row in attempts if row.get("headers_path")],
            "_payload": final_shape_payload,
        }
        result["complexity_failure"] = is_complexity_failure(final_shape_payload, final_reason)
        result["schema_failure"] = is_schema_failure(final_reason)
        result["hard_stop"] = final_kind == "physical_budget" or final_status in {401, 403} or (
            final_status == 429 and result["status"] == "failed"
        )
        return result

    def _archive_response(
        self,
        ordinal: int,
        operation: GraphQLOperation,
        body: bytes,
        headers: Mapping[str, str],
    ) -> tuple[str, str]:
        stem = f"{ordinal:03d}-{operation.name}"
        body_path = self.responses_dir / f"{stem}.body"
        header_path = self.headers_dir / f"{stem}.json"
        with body_path.open("xb") as handle:
            handle.write(redact_bytes(body, self._token))
        with header_path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(headers), indent=2, sort_keys=True) + "\n")
        body_path.chmod(0o600)
        header_path.chmod(0o600)
        relative_body = body_path.relative_to(self.run_dir).as_posix()
        relative_headers = header_path.relative_to(self.run_dir).as_posix()
        return relative_body, relative_headers

    def _ledger_row(
        self,
        operation: GraphQLOperation,
        variables: Mapping[str, Any],
        *,
        logical_call: int,
        physical_ordinal: int,
        attempt: int,
        status: int | None,
        response_bytes: int,
        raw_response_sha256: str | None,
        latency: float,
        complexity: int | None,
        headers: Mapping[str, str],
        raw_path: str | None,
        headers_path: str | None,
        retrying: bool,
        error_kind: str | None,
        error: str | None,
    ) -> dict[str, Any]:
        rate = parse_rate_limit_headers(headers)
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "logical_call": logical_call,
            "physical_ordinal": physical_ordinal,
            "attempt": attempt,
            "operation": operation.name,
            "operation_version": operation.version,
            "operation_document_sha256": operation.document_sha256,
            "variable_keys": sorted(variables),
            "batch_size": len(variables.get("matchIds", ())) if "matchIds" in variables else None,
            "http_status": status,
            "observable_complexity": complexity,
            "response_bytes": response_bytes,
            "raw_response_sha256": raw_response_sha256,
            "latency_seconds": round(latency, 6),
            "safe_rate_headers": safe_rate_headers(headers),
            "rate_headers": rate.as_dict(),
            "retries": attempt,
            "cache_hit": False,
            "cache_miss": True,
            "retrying": retrying,
            "error_kind": error_kind,
            "error": redact_text(error or "", self._token) or None,
            "raw_path": raw_path,
            "headers_path": headers_path,
        }

    def _append_ledger(self, rows: Sequence[Mapping[str, Any]]) -> None:
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(dict(row), sort_keys=True) + "\n")
        self.ledger_path.chmod(0o600)

    async def run(
        self,
        *,
        account_id: int,
        match_ids: Sequence[int],
        start_timestamp: int,
        end_timestamp: int,
        include_short_trajectory: bool = False,
        include_availability: bool = False,
        short_duration_threshold: int = SHORT_TRAJECTORY_SECONDS,
        input_source: str = "explicit",
    ) -> dict[str, Any]:
        unique_ids = tuple(dict.fromkeys(int(value) for value in match_ids))
        if len(unique_ids) < 4:
            raise MicroprobeError("at least four unique parsed match IDs are required")
        if start_timestamp > end_timestamp:
            raise MicroprobeError("start timestamp must not be after end timestamp")
        stop_reason: str | None = None

        async def call(
            operation: GraphQLOperation,
            variables: Mapping[str, Any],
            validator: Callable[[Mapping[str, Any] | None], tuple[bool, dict[str, Any]] | tuple[bool, dict[str, Any], int | None]],
            *,
            batch_size: int | None = None,
        ) -> dict[str, Any]:
            result = await self.request(operation, variables, batch_size=batch_size)
            payload = result.pop("_payload", None)
            validated = validator(payload)
            if len(validated) == 3:
                shape_ok, details, selected = validated
                if selected is not None:
                    result["_selected_match_id"] = selected
            else:
                shape_ok, details = validated
            result.update(details)
            result["shape_ok"] = bool(shape_ok)
            if result["status"] == "success" and not shape_ok:
                result["status"] = "failed"
                result["reason"] = details.get("shape_failure_reason") or "response_shape_failure"
                result["error_kind"] = "schema_shape_failure" if details.get("schema_drift") else "response_shape_failure"
                result["schema_failure"] = bool(details.get("schema_drift"))
            self._calls.append(result)
            return result

        schema = await call(V7_SCHEMA_SENTINEL, {}, validate_schema_sentinel)
        if schema.get("hard_stop") or schema.get("schema_failure"):
            stop_reason = schema.get("reason") or "schema sentinel failed"
        else:
            subtype = await call(V7_PARSED_SUBTYPE_SHAPE_SENTINEL, {}, validate_subtype_sentinel)
            if subtype.get("hard_stop") or subtype.get("schema_failure"):
                stop_reason = subtype.get("reason") or "parsed subtype sentinel failed"
            else:
                for size in planned_batch_sizes(len(unique_ids)):
                    batch = await call(
                        PROBE_PARSED_EVIDENCE_BATCH,
                        {"accountId": account_id, "matchIds": list(unique_ids[:size])},
                        lambda payload, ids=unique_ids[:size]: summarize_parsed_batch(payload, ids),
                        batch_size=size,
                    )
                    if batch.get("hard_stop") or batch.get("schema_failure"):
                        stop_reason = batch.get("reason") or "parsed batch failed"
                        break
                    if batch["status"] != "success":
                        if batch.get("complexity_failure") and size == 4:
                            fallback = await call(
                                PROBE_PARSED_CORE_BATCH_FALLBACK,
                                {"accountId": account_id, "matchIds": list(unique_ids[:2])},
                                lambda payload: summarize_parsed_batch(payload, unique_ids[:2]),
                                batch_size=2,
                            )
                            if fallback.get("hard_stop") or fallback.get("schema_failure"):
                                stop_reason = fallback.get("reason") or "parsed fallback failed"
                            else:
                                stop_reason = "full parsed selection complexity failure"
                        break
                if stop_reason is None and include_short_trajectory:
                    short_index = await call(
                        FIND_SHORT_PARSED_TRAJECTORY,
                        {
                            "accountId": account_id,
                            "startDateTime": start_timestamp,
                            "endDateTime": end_timestamp,
                        },
                        summarize_short_index,
                    )
                    selected_id = short_index.pop("_selected_match_id", None)
                    if (
                        short_index["status"] == "success"
                        and short_index.get("short_match_found")
                        and isinstance(short_index.get("shortest_duration_seconds"), int)
                        and short_index["shortest_duration_seconds"] < short_duration_threshold
                        and selected_id is not None
                    ):
                        await call(
                            GET_SHORT_PARSED_TRAJECTORY,
                            {"accountId": account_id, "matchId": selected_id},
                            summarize_short_trajectory,
                        )
                if stop_reason is None and include_availability:
                    await call(
                        PROBE_PARSED_AVAILABILITY,
                        {
                            "accountId": account_id,
                            "startDateTime": start_timestamp,
                            "endDateTime": end_timestamp,
                        },
                        summarize_availability,
                    )
        if any(call.get("hard_stop") for call in self._calls):
            stop_reason = stop_reason or "provider authentication/rate failure"
        summary = self._summary(
            account_id=account_id,
            requested_match_count=len(unique_ids),
            input_source=input_source,
            include_short_trajectory=include_short_trajectory,
            include_availability=include_availability,
            stop_reason=stop_reason,
        )
        self._write_summary(summary)
        return summary

    def _summary(
        self,
        *,
        account_id: int,
        requested_match_count: int,
        input_source: str,
        include_short_trajectory: bool,
        include_availability: bool,
        stop_reason: str | None,
    ) -> dict[str, Any]:
        batches = [
            call
            for call in self._calls
            if call["operation"] == PROBE_PARSED_EVIDENCE_BATCH.name
        ]
        successful_batches = [
            call for call in batches if call.get("status") == "success" and call.get("shape_ok")
        ]
        public_calls = [
            {key: value for key, value in call.items() if not key.startswith("_")}
            for call in self._calls
        ]
        physical_successes = sum(
            1
            for row in self._ledger_rows
            if isinstance(row.get("http_status"), int)
            and 200 <= row["http_status"] < 300
            and not row.get("error_kind")
        )
        return {
            "schema": "stratz-v7-live-microprobe-1.0.0",
            "started_at": self._started_at.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "input_source": input_source,
            "requested_match_count": requested_match_count,
            "account_id_present": bool(account_id),
            "physical_calls": self._physical_calls,
            "logical_calls": len(self._calls),
            "successful_calls": sum(call.get("status") == "success" for call in self._calls),
            "failed_calls": sum(call.get("status") == "failed" for call in self._calls),
            "physical_successful_responses": physical_successes,
            "physical_failed_responses": self._physical_calls - physical_successes,
            "largest_safe_batch": max((call["batch_size"] for call in successful_batches if call.get("batch_size")), default=None),
            "largest_attempted_batch": max((call["batch_size"] for call in batches if call.get("batch_size")), default=None),
            "fallback_attempted": any(
                call["operation"] == PROBE_PARSED_CORE_BATCH_FALLBACK.name for call in self._calls
            ),
            "complexity_observed": [
                {"operation": call["operation"], "value": call.get("complexity"), "failure": call.get("complexity_failure", False)}
                for call in public_calls
                if call.get("complexity") is not None or call.get("complexity_failure")
            ],
            "schema_drift_observed": any(call.get("schema_failure") for call in self._calls),
            "short_trajectory_requested": include_short_trajectory,
            "availability_requested": include_availability,
            "stop_reason": redact_text(stop_reason, self._token) if stop_reason else None,
            "calls": public_calls,
            "ledger": {
                "path": self.ledger_path.relative_to(self.run_dir).as_posix(),
                "rows": len(self._ledger_rows),
            },
        }

    def _write_summary(self, summary: Mapping[str, Any]) -> None:
        path = self.run_dir / "run-summary.json"
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(summary), indent=2, sort_keys=True) + "\n")
        path.chmod(0o600)


def load_specimen_inputs(path: Path) -> tuple[int, tuple[int, ...]]:
    """Select parsed IDs locally from a recovered history specimen."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        player = payload["data"]["player"]
        account_id = int(player["steamAccountId"])
        matches = player["matches"]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MicroprobeError("supplied specimen does not contain a usable history shape") from exc
    ids = tuple(
        int(match["id"])
        for match in matches
        if isinstance(match, Mapping)
        and match.get("parsedDateTime") is not None
        and isinstance(match.get("id"), int)
    )
    unique = tuple(dict.fromkeys(ids))
    if len(unique) < 4:
        raise MicroprobeError("supplied specimen has fewer than four parsed match IDs")
    return account_id, unique


def parse_match_ids(values: Sequence[str]) -> tuple[int, ...]:
    result: list[int] = []
    for value in values:
        for part in value.split(","):
            try:
                parsed = int(part.strip())
            except ValueError as exc:
                raise MicroprobeError("match IDs must be integers") from exc
            if parsed <= 0:
                raise MicroprobeError("match IDs must be positive")
            result.append(parsed)
    unique = tuple(dict.fromkeys(result))
    if len(unique) < 4:
        raise MicroprobeError("at least four unique parsed match IDs are required")
    return unique


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotenv-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--specimen-path", type=Path)
    parser.add_argument("--account-id", type=int)
    parser.add_argument("--match-ids", nargs="+")
    parser.add_argument("--start-timestamp", type=int)
    parser.add_argument("--end-timestamp", type=int)
    parser.add_argument("--with-short-trajectory", action="store_true")
    parser.add_argument("--with-availability", action="store_true")
    parser.add_argument("--short-duration-threshold", type=int, default=SHORT_TRAJECTORY_SECONDS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    token: str | None = None
    try:
        token = load_stratz_token(args.dotenv_path)
        if args.specimen_path:
            if args.account_id is not None or args.match_ids:
                raise MicroprobeError("use either --specimen-path or explicit account/match inputs")
            account_id, match_ids = load_specimen_inputs(args.specimen_path)
            input_source = "recovered_specimen"
        else:
            if args.account_id is None or not args.match_ids:
                raise MicroprobeError("explicit inputs require --account-id and --match-ids")
            account_id = args.account_id
            match_ids = parse_match_ids(args.match_ids)
            input_source = "explicit"
        end_timestamp = int(args.end_timestamp or datetime.now(UTC).timestamp())
        start_timestamp = int(args.start_timestamp or end_timestamp - 365 * 24 * 60 * 60)
        async def execute() -> dict[str, Any]:
            async with MicroprobeRunner(
                token,
                output_dir=args.output_dir,
                endpoint=args.endpoint,
                timeout_seconds=args.timeout_seconds,
                max_retries=args.max_retries,
            ) as runner:
                return await runner.run(
                    account_id=account_id,
                    match_ids=match_ids,
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp,
                    include_short_trajectory=args.with_short_trajectory,
                    include_availability=args.with_availability,
                    short_duration_threshold=args.short_duration_threshold,
                    input_source=input_source,
                )
        summary = asyncio.run(execute())
    except (MicroprobeError, httpx.HTTPError) as exc:
        print(f"stratz microprobe stopped: {redact_text(str(exc), token)}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "physical_calls": summary["physical_calls"],
                "successful_calls": summary["successful_calls"],
                "failed_calls": summary["failed_calls"],
                "largest_safe_batch": summary["largest_safe_batch"],
                "largest_attempted_batch": summary["largest_attempted_batch"],
                "stop_reason": summary["stop_reason"],
                "run_summary": str(args.output_dir / "runs"),
            },
            sort_keys=True,
        )
    )
    return 2 if summary["stop_reason"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

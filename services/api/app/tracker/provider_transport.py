"""Tracker-only admission and accounting around the existing HTTP clients."""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import Engine

from app.stratz.queries import GET_TRACKER_MATCH_BATCH
from app.tracker.evidence import save_snapshot
from app.tracker.provider_control import ProviderDeferred, ProviderGate, call_units
from app.tracker.schema import provider_calls


def _operation(request: httpx.Request, provider: str) -> tuple[str, str, int | None, bool]:
    if provider == "stratz":
        try:
            body = json.loads(request.content)
        except (ValueError, UnicodeError) as exc:
            raise ValueError("Invalid historical operation") from exc
        if not isinstance(body, dict) or body.get("operationName") != GET_TRACKER_MATCH_BATCH.name:
            raise ValueError("Unregistered historical operation")
        if body.get("query") != GET_TRACKER_MATCH_BATCH.document or request.method != "POST":
            raise ValueError("Historical operation version mismatch")
        return GET_TRACKER_MATCH_BATCH.name, GET_TRACKER_MATCH_BATCH.version, None, False
    path = request.url.path
    match = re.fullmatch(r"(?:/api)?/matches/([1-9][0-9]*)", path)
    if match and request.method == "GET":
        return "match", "1", int(match[1]), False
    if re.fullmatch(r"(?:/api)?/players/[1-9][0-9]*/matches", path) and request.method == "GET":
        if request.url.params.get("significant") != "0":
            raise ValueError("Tracker history must include Turbo")
        return "history", "1", None, False
    match = re.fullmatch(r"(?:/api)?/request/([1-9][0-9]*)", path)
    if match and request.method == "POST":
        return "request_replay", "1", int(match[1]), True
    if re.fullmatch(r"(?:/api)?/request/[A-Za-z0-9_-]{1,128}", path) and request.method == "GET":
        return "request_status", "1", None, False
    raise ValueError("Unregistered tracker provider operation")


class ControlledTransport(httpx.AsyncBaseTransport):
    def __init__(
        self, gate: ProviderGate, database: Engine, *,
        transport: httpx.AsyncBaseTransport | None = None,
        deadline_seconds: float = 30, max_response_bytes: int = 16 * 1024 * 1024,
        before_send: Callable[[], None] | None = None,
        job_id: str | None = None,
    ):
        if not math.isfinite(deadline_seconds) or deadline_seconds <= 0 or max_response_bytes <= 0:
            raise ValueError("Invalid acquisition bounds")
        self.job_id = job_id
        self.before_send = before_send
        self.gate = gate
        self.database = database
        # Pin one IP family. A stable public egress still requires deployment setup.
        self.transport = transport or httpx.AsyncHTTPTransport(local_address="0.0.0.0")
        self.deadline_seconds = deadline_seconds
        self.max_response_bytes = max_response_bytes

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        operation, version, match_id, processing = _operation(request, self.gate.provider)
        lock = None
        if self.gate.provider == "stratz":
            lock = self.gate.redis.lock(
                self.gate.key + ":singleflight", timeout=math.ceil(self.deadline_seconds) + 5,
                blocking=False, thread_local=False,
            )
            if not await asyncio.to_thread(lock.acquire):
                raise ProviderDeferred("SINGLEFLIGHT_BUSY", 1)
        try:
            await asyncio.to_thread(self.gate.acquire, processing=processing)
            if self.before_send is not None:
                await asyncio.to_thread(self.before_send)
            return await self._attempt(request, operation, version, match_id, processing)
        finally:
            if lock is not None:
                await asyncio.to_thread(lock.release)

    async def _attempt(
        self, request: httpx.Request, operation: str, version: str,
        match_id: int | None, processing: bool,
    ) -> httpx.Response:
        started = time.monotonic()
        called_at = datetime.now(UTC)
        status = None
        headers: dict[str, str] = {}
        failure = None
        response = None
        payload = None
        body = bytearray()
        try:
            # Avoid decompression expansion outside the bounded response reader.
            request.headers["Accept-Encoding"] = "identity"
            async with asyncio.timeout(self.deadline_seconds):
                response = await self.transport.handle_async_request(request)
                status = response.status_code
                headers = dict(response.headers)
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    failure = "UNEXPECTED_ENCODING"
                    raise httpx.TransportError("Unexpected provider content encoding")
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > self.max_response_bytes:
                        failure = "RESPONSE_TOO_LARGE"
                        raise httpx.TransportError("Provider response exceeds acquisition bound")
                    body.extend(chunk)
                if 200 <= status < 300:
                    try:
                        payload = json.loads(body)
                    except (ValueError, UnicodeError):
                        failure = "INVALID_JSON"
                        raise httpx.TransportError("Provider returned invalid JSON") from None
                return httpx.Response(status, headers=response.headers, content=bytes(body), request=request)
        except TimeoutError as exc:
            failure = "DEADLINE_EXCEEDED"
            raise httpx.ReadTimeout("Provider acquisition deadline exceeded", request=request) from exc
        except BaseException:
            failure = failure or "TRANSPORT_FAILED"
            raise
        finally:
            if response is not None:
                await response.aclose()
            ip_blocked = status == 403 and self.gate.provider == "stratz" and b"ip" in bytes(body).lower()
            rate, billed = call_units(self.gate.provider, processing=processing, status=status)
            account_id = None
            history_path = re.fullmatch(r"(?:/api)?/players/([1-9][0-9]*)/matches", request.url.path)
            if self.gate.provider == "opendota" and history_path:
                account_id = int(history_path[1])
            elif self.gate.provider == "stratz":
                account_id = json.loads(request.content).get("variables", {}).get("steamAccountId")
            if type(account_id) is not int or not 0 < account_id < 2**32:
                account_id = None
            values = dict(
                account_id=account_id, job_id=self.job_id,
                provider=self.gate.provider, operation=operation, operation_version=version,
                match_id=match_id, status=status, latency_ms=(time.monotonic() - started) * 1000,
                billed_units=billed, rate_units=rate, called_at=called_at,
                failure_code=failure or ("IP_BINDING" if ip_blocked else f"HTTP_{status}" if status and status >= 400 else None),
            )
            subject = f"match:{match_id}" if match_id else hashlib.sha256(request.url.raw_path + request.content).hexdigest()
            try:
                await asyncio.to_thread(self._record, values, payload, subject)
            finally:
                await asyncio.to_thread(self.gate.observe, headers, status=status if not failure else None, ip_blocked=ip_blocked)

    def _record(self, values: dict[str, Any], payload: Any, subject: str) -> None:
        with self.database.begin() as connection:
            snapshot_id = None
            if isinstance(payload, (dict, list)):
                snapshot_id = save_snapshot(
                    connection, provider=self.gate.provider, operation=values["operation"],
                    operation_version=values["operation_version"], schema_version="raw-1",
                    subject=subject, fetched_at=datetime.now(UTC), payload=payload,
                )
            connection.execute(provider_calls.insert().values(**values, snapshot_id=snapshot_id, request_subject=subject))

    async def aclose(self) -> None:
        await self.transport.aclose()

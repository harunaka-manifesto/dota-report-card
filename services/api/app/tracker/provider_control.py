"""Shared header-sized provider buckets and circuit state; no product reads here."""
from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast

from redis import Redis, WatchError

from app.stratz.client import parse_rate_limit_headers

_WINDOWS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


class ProviderDeferred(Exception):
    """Persist the job's next run time instead of sleeping inside a worker."""

    def __init__(self, reason: str, delay: float):
        super().__init__(reason)
        self.reason = reason
        self.delay = max(0.1, delay)


@dataclass(frozen=True)
class RatePolicy:
    reserve_share: float = 0.1
    processing_share: float = 0.5
    failure_threshold: int = 3
    cooldown_seconds: int = 30
    probe_seconds: int = 30

    def __post_init__(self) -> None:
        if not 0 < self.reserve_share < 1 or not 0 < self.processing_share < 1:
            raise ValueError("Invalid provider budget share")
        if min(self.failure_threshold, self.cooldown_seconds, self.probe_seconds) < 1:
            raise ValueError("Invalid circuit policy")


class ProviderGate:
    def __init__(self, redis: Redis, *, namespace: str, provider: str, policy: RatePolicy = RatePolicy()):
        if provider not in {"opendota", "stratz"} or not namespace:
            raise ValueError("Invalid provider gate identity")
        self.redis = redis
        self.provider = cast(Literal["opendota", "stratz"], provider)
        self.key = f"{namespace}:provider:{provider}"
        self.policy = policy

    def _refill(self, bucket: dict[str, Any], now: float) -> None:
        elapsed = max(0, now - bucket["updated_at"])
        process_share = self.policy.processing_share if self.provider == "opendota" else 0
        for part, share in (("total", 1), ("reads", 1 - process_share), ("processing", process_share)):
            capacity = bucket["limit"] * share
            bucket[part] = min(capacity, bucket[part] + elapsed * capacity / bucket["window"])
        bucket["updated_at"] = now

    def _change(self, operation: Callable[[dict[str, Any], float], Any]) -> Any:
        for _ in range(16):
            with self.redis.pipeline() as pipe:
                try:
                    pipe.watch(self.key)
                    seconds, micros = cast(Any, pipe.time())
                    now = seconds + micros / 1_000_000
                    raw = cast(Any, pipe.get(self.key))
                    state = json.loads(raw) if raw else {"buckets": {}, "failures": 0}
                    result = operation(state, now)
                    pipe.multi()
                    pipe.set(self.key, json.dumps(state, allow_nan=False))
                    pipe.execute()
                    return result
                except WatchError:
                    continue
        raise ProviderDeferred("COORDINATION_BUSY", 0.5)

    def acquire(self, *, processing: bool = False, recovery: bool = False) -> None:
        if processing and self.provider != "opendota":
            raise ValueError("Unsupported processing provider")
        units = 10 if processing else 1

        def apply(state: dict[str, Any], now: float) -> None:
            if state.get("disabled"):
                raise ProviderDeferred("CREDENTIAL_OR_IP_BLOCKED", self.policy.cooldown_seconds)
            if state.get("open_until", 0) > now:
                raise ProviderDeferred("CIRCUIT_OPEN", state["open_until"] - now)
            if processing and state.get("processing_after", 0) > now:
                raise ProviderDeferred("PROCESSING_PACED", state["processing_after"] - now)
            buckets = state["buckets"]
            if not buckets:
                # One shared discovery read learns headers; no guessed published quota.
                if processing or state.get("probe_after", 0) > now:
                    raise ProviderDeferred("QUOTA_UNKNOWN", max(1, state.get("probe_after", now) - now))
                state["probe_after"] = now + self.policy.probe_seconds
                return
            lane = "processing" if processing else "reads"
            for bucket in buckets.values():
                if bucket.get("blocked_until", 0) > now:
                    raise ProviderDeferred("QUOTA_EXHAUSTED", bucket["blocked_until"] - now)
                self._refill(bucket, now)
                reserve = 0 if recovery else bucket["limit"] * self.policy.reserve_share
                usable = min(bucket["total"] - reserve, bucket[lane])
                if usable < units:
                    raise ProviderDeferred("QUOTA_EXHAUSTED", bucket["window"] * (units - usable) / max(1, bucket["limit"]))
            for bucket in buckets.values():
                bucket["total"] -= units
                bucket[lane] -= units
            if processing:
                state["processing_after"] = now + max(
                    bucket["window"] * units / (bucket["limit"] * self.policy.processing_share)
                    for bucket in buckets.values()
                )
        self._change(apply)

    def observe(self, headers: Mapping[str, str], *, status: int | None, ip_blocked: bool = False) -> None:
        parsed = parse_rate_limit_headers(headers)
        # Default-window duration is ambiguous; only explicit named windows are used.
        # A proxy with only generic headers stays in conservative discovery-read mode.
        def apply(state: dict[str, Any], now: float) -> None:
            for name in _WINDOWS:
                old = state["buckets"].get(name)
                limit = parsed.limits.get(name, old["limit"] if old else 0)
                remaining = parsed.remaining.get(name)
                if remaining is None or remaining < 0 or limit <= 0:
                    continue
                if old:
                    self._refill(old, now)
                capacity = min(limit, remaining)
                old = state["buckets"].get(name)
                # Headers can lower headroom, never refund an in-flight reservation.
                total = min(capacity, old["total"]) if old else capacity
                process_cap = limit * self.policy.processing_share if self.provider == "opendota" else 0
                read_cap = limit - process_cap
                state["buckets"][name] = {
                    "limit": limit, "window": _WINDOWS[name], "updated_at": now,
                    "total": total,
                    "reads": min(read_cap, old["reads"] if old else total),
                    "processing": min(process_cap, old["processing"] if old else total),
                    "blocked_until": max(now, parsed.reset_at.get(name, now + _WINDOWS[name])) if remaining == 0 else old.get("blocked_until", 0) if old else 0,
                }
            if ip_blocked or status in {401, 403}:
                state["disabled"] = True
                state["failure_code"] = "IP_BINDING" if ip_blocked else "CREDENTIAL_REJECTED"
            elif status is None or status == 429 or status >= 500:
                state["failures"] += 1
                if status == 429 or state["failures"] >= self.policy.failure_threshold:
                    delay = float(self.policy.cooldown_seconds)
                    try:
                        retry_after = float(headers.get("retry-after", headers.get("Retry-After", "0")))
                        if math.isfinite(retry_after):
                            delay = max(delay, retry_after)
                    except ValueError:
                        pass
                    state["open_until"] = now + delay
            else:
                state["failures"] = 0
                state["open_until"] = 0
        self._change(apply)


def call_units(provider: str, *, processing: bool, status: int | None) -> tuple[int, int]:
    """Return (rate units, known billed units). Network uncertainty bills zero known units."""
    if provider not in {"opendota", "stratz"} or processing and provider != "opendota":
        raise ValueError("Invalid provider operation")
    rate = 10 if processing else 1
    billed = int(provider == "opendota" and status is not None and 200 <= status < 400)
    return rate, billed

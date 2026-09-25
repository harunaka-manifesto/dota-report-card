"""Content-addressed disk cache for source requests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class CacheEntry:
    url: str
    params: dict[str, Any]
    status_code: int
    headers: dict[str, str]
    body: str
    fetched_at: str

    @property
    def cache_hit(self) -> bool:
        return True


class DiskCache:
    """A bounded, deterministic cache keyed by URL and query parameters."""

    def __init__(self, root: str | Path, enabled: bool = True) -> None:
        self.root = Path(root)
        self.enabled = enabled

    def _path(self, url: str, params: dict[str, Any]) -> Path:
        key = hashlib.sha256(
            json.dumps(
                {"url": url, "params": params}, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
        return self.root / key[:2] / f"{key}.json"

    def get(self, url: str, params: dict[str, Any]) -> CacheEntry | None:
        if not self.enabled:
            return None
        path = self._path(url, params)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        if not isinstance(value, dict) or value.get("url") != url or value.get("params") != params:
            return None
        return CacheEntry(
            url=url,
            params=dict(params),
            status_code=int(value.get("status_code", 200)),
            headers={str(k): str(v) for k, v in dict(value.get("headers", {})).items()},
            body=str(value.get("body", "")),
            fetched_at=str(value.get("fetched_at", "")),
        )

    def put(
        self,
        url: str,
        params: dict[str, Any],
        *,
        status_code: int,
        headers: dict[str, str],
        body: str,
        fetched_at: str,
    ) -> None:
        if not self.enabled:
            return
        path = self._path(url, params)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "url": url,
            "params": params,
            "status_code": status_code,
            "headers": headers,
            "body": body,
            "fetched_at": fetched_at,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")

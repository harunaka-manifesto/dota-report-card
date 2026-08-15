from __future__ import annotations

import re
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import OpenDotaRateLimited, OpenDotaUnavailable


class OpenDotaParseClient:
    """Explicit transport for parse requests.

    Keeping this capability in a separate client makes it impossible for a
    normal match-detail read to submit a paid/expensive parse accidentally.
    Product policy and budgets belong above this transport boundary.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http = http_client
        self._owns_http = http_client is None

    async def __aenter__(self) -> OpenDotaParseClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.settings.opendota_timeout_seconds)
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._http is not None and self._owns_http:
            await self._http.aclose()
            self._http = None

    async def request_parse(self, match_id: int) -> dict[str, Any]:
        return dict(await self._request("POST", f"/request/{_match_id(match_id)}") or {})

    async def get_parse_request(self, job_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", job_id):
            raise ValueError("Invalid parse job ID")
        return dict(await self._request("GET", f"/request/{job_id}") or {})

    async def _request(self, method: str, endpoint: str) -> Any:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.settings.opendota_timeout_seconds)
        try:
            response = await self._http.request(
                method,
                f"{self.settings.opendota_base_url.rstrip('/')}/{endpoint.lstrip('/')}",
                headers=(
                    {"Authorization": f"Bearer {self.settings.opendota_api_key}"}
                    if self.settings.opendota_api_key
                    else {}
                ),
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise OpenDotaUnavailable("OpenDota is unavailable") from exc
        if response.status_code == 429:
            raise OpenDotaRateLimited("OpenDota rate limit reached")
        if response.status_code >= 400:
            raise OpenDotaUnavailable("OpenDota rejected the parse request")
        try:
            return response.json()
        except ValueError as exc:
            raise OpenDotaUnavailable("OpenDota returned invalid JSON") from exc


def _match_id(value: int) -> int:
    try:
        match_id = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid match ID") from exc
    if match_id <= 0:
        raise ValueError("Invalid match ID")
    return match_id

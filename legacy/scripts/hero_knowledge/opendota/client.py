"""Small client for the bounded OpenDota hero-context endpoints."""

from __future__ import annotations

from ..client import ResponsePayload, SourceHttpClient
from ..config import Settings


class OpenDotaClient:
    """Fetch the public aggregate hero context needed by ingestion.

    The build-time client intentionally exposes only the four endpoints used
    by the knowledge schema. It does not expose replay parsing or player
    history operations.
    """

    def __init__(self, http: SourceHttpClient, settings: Settings) -> None:
        self.http = http
        self.settings = settings
        base = settings.opendota_base_url.rstrip("/")
        self.base_url = base if base.endswith("/api") else f"{base}/api"

    def _get(self, path: str, *, force_refresh: bool = False) -> ResponsePayload:
        return self.http.get_json(
            f"{self.base_url}/{path.lstrip('/')}",
            force_refresh=force_refresh,
        )

    def fetch_hero_stats(self, *, force_refresh: bool = False) -> ResponsePayload:
        return self._get("heroStats", force_refresh=force_refresh)

    def fetch_durations(self, hero_id: int, *, force_refresh: bool = False) -> ResponsePayload:
        return self._get(f"heroes/{hero_id}/durations", force_refresh=force_refresh)

    def fetch_item_popularity(
        self, hero_id: int, *, force_refresh: bool = False
    ) -> ResponsePayload:
        return self._get(f"heroes/{hero_id}/itemPopularity", force_refresh=force_refresh)

    def fetch_matchups(self, hero_id: int, *, force_refresh: bool = False) -> ResponsePayload:
        return self._get(f"heroes/{hero_id}/matchups", force_refresh=force_refresh)

"""Client for Valve's public Dota 2 datafeed."""

from __future__ import annotations

from typing import Any

from ..client import ResponsePayload, SourceHttpClient
from ..config import Settings
from ..errors import SourceSchemaError


class ValveDatafeedClient:
    """Typed access to the public, keyless Dota 2 datafeed endpoints."""

    def __init__(self, http: SourceHttpClient, settings: Settings) -> None:
        self.http = http
        self.settings = settings
        self.base_url = settings.valve_base_url

    def _get(
        self, path: str, params: dict[str, Any], *, force_refresh: bool = False
    ) -> ResponsePayload:
        return self.http.get_json(
            f"{self.base_url}{path}",
            params,
            force_refresh=force_refresh,
        )

    def fetch_hero_list(self, *, force_refresh: bool = False) -> ResponsePayload:
        response = self._get(
            "/datafeed/herolist",
            {"language": self.settings.language},
            force_refresh=force_refresh,
        )
        payload = response.json()
        heroes = (
            payload.get("result", {}).get("data", {}).get("heroes")
            if isinstance(payload, dict)
            else None
        )
        if not isinstance(heroes, list) or not heroes:
            raise SourceSchemaError(
                "Valve herolist response does not contain a non-empty heroes list"
            )
        return response

    def fetch_hero(self, hero_id: int, *, force_refresh: bool = False) -> ResponsePayload:
        response = self._get(
            "/datafeed/herodata",
            {"hero_id": hero_id, "language": self.settings.language},
            force_refresh=force_refresh,
        )
        payload = response.json()
        heroes = (
            payload.get("result", {}).get("data", {}).get("heroes")
            if isinstance(payload, dict)
            else None
        )
        if not isinstance(heroes, list) or len(heroes) != 1 or not isinstance(heroes[0], dict):
            raise SourceSchemaError(f"Valve herodata response for hero {hero_id} is malformed")
        if int(heroes[0].get("id", -1)) != hero_id:
            raise SourceSchemaError(
                f"Valve herodata response returned the wrong hero for {hero_id}"
            )
        return response

    def fetch_patch_list(self, *, force_refresh: bool = False) -> ResponsePayload:
        response = self._get(
            "/datafeed/patchnoteslist",
            {"language": self.settings.language},
            force_refresh=force_refresh,
        )
        payload = response.json()
        patches = payload.get("patches") if isinstance(payload, dict) else None
        if not isinstance(patches, list):
            raise SourceSchemaError("Valve patchnoteslist response does not contain a patches list")
        return response

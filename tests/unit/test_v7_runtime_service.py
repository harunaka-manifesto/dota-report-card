from __future__ import annotations

import dataclasses

from app.analysis.source import MappingSource
from app.core.config import Settings
from app.main import create_app
from app.player_analysis_v7.runtime import history_rows
from app.player_analysis_v7.service import DEEP_CACHE_ENDPOINT, V7RuntimeService
from app.providers.base import (
    CanonicalProfile,
    HistoryWindow,
    ProviderProvenance,
    V7CanonicalHistory,
    V7CanonicalMatch,
)
from app.storage.repository import InMemoryRepository
from fastapi.testclient import TestClient


def _history() -> V7CanonicalHistory:
    return V7CanonicalHistory(
        profile=CanonicalProfile("stratz", "test", 7, "Player", None, False, True),
        window=HistoryWindow(100, 200, 1),
        matches=(
            V7CanonicalMatch(
                "stratz",
                "test",
                9,
                1,
                150,
                30,
                "radiant",
                True,
                1,
                0,
                1,
                180,
                "POSITION_1",
                "CORE",
                "SAFE_LANE",
                "ALL_PICK_RANKED",
                "RANKED",
                "NONE",
                True,
            ),
        ),
        provenance=ProviderProvenance(
            "stratz", "test", "history", "test", "0" * 64, "test", 0, 0,
            "2026-09-08T00:00:00+00:00", "1" * 64, "complete", 1.0,
        ),
    )


def _deep_row() -> dict[str, object]:
    return {
        "match_id": 9,
        "duration_seconds": 30,
        "started_at": 150,
        "ended_at": 180,
        "game_mode_native": "ALL_PICK_RANKED",
        "lobby_type_native": "RANKED",
        "radiant_kills": [0],
        "dire_kills": [0],
        "radiant_networth_leads": [0],
        "tower_deaths": [],
        "self": {
            "hero_id": 1,
            "is_radiant": True,
            "is_victory": True,
            "position_native": "POSITION_1",
            "role_native": "CORE",
            "lane_native": "SAFE_LANE",
            "leaver_status_native": "NONE",
            "trajectories": {},
            "events": {
                "kill_events": [],
                "death_events": [],
                "assist_events": [],
                "item_purchases": [],
                "wards": [],
            },
            "farm_distribution": None,
        },
    }


def test_history_rows_retains_nullable_identity_without_coercion() -> None:
    source = _history()
    unknown = dataclasses.replace(source.matches[0], won=None, side=None, hero_id=None)
    retained = history_rows(dataclasses.replace(source, matches=(unknown,)))

    assert len(retained) == 1
    assert retained[0]["is_victory"] is None
    assert retained[0]["is_radiant"] is None
    assert retained[0]["hero_id"] is None
    assert "did_radiant_win" not in retained[0]


class _Provider:
    provider = "stratz"

    def __init__(self) -> None:
        self.history_calls = 0
        self.deep_calls = 0

    async def fetch_history(self, _account_id: int) -> V7CanonicalHistory:
        self.history_calls += 1
        return _history()

    async def fetch_deep_matches(
        self, _account_id: int, _match_ids: tuple[int, ...]
    ) -> list[dict[str, object]]:
        self.deep_calls += 1
        return [_deep_row()]


async def test_acquisition_to_persistence_and_api_with_frozen_runtime() -> None:
    provider = _Provider()
    repository = InMemoryRepository()
    service = V7RuntimeService(provider, repository, hero_metadata={1: {"display_name": "Anti-Mage"}})

    job, reused = await service.generate(
        7, "https://www.opendota.com/players/7", generated_at="2026-09-08T00:00:00+00:00"
    )
    repeated, repeated_reused = await service.generate(7, job.canonical_player)

    assert reused is False and repeated_reused is True
    assert repeated.report_id == job.report_id
    assert provider.history_calls == provider.deep_calls == 1
    assert repository.get_cached_raw_payload(DEEP_CACHE_ENDPOINT, "7")[0]["match_id"] == 9
    source = MappingSource(player={"profile": {"account_id": 7}}, matches=[], details={})
    response = TestClient(create_app(Settings(), source=source, repository=repository)).get(
        f"/v1/v7/reports/{job.report_id}"
    )
    assert response.status_code == 200
    assert response.json()["version"] == "v7-public-projection-1.0.0"

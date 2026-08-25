from __future__ import annotations

import asyncio

from app.ingestion.summary_history_contract import SUMMARY_HISTORY_PROJECTION

from scripts.collect_v61_calibration_histories import collect_profiles


class _Source:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, tuple[str, ...], int]] = []

    async def get_summary_history_once(
        self,
        account_id: int,
        *,
        days: int,
        project: tuple[str, ...],
        provider_limit: int,
    ) -> list[dict[str, object]]:
        self.calls.append((account_id, days, project, provider_limit))
        return [
            {
                "match_id": account_id * 100,
                "player_slot": 0,
                "radiant_win": True,
                "duration": 1_800,
                "game_mode": 1,
                "lobby_type": 0,
                "hero_id": 1,
                "start_time": 1_780_000_000,
                "kills": 3,
                "deaths": 2,
                "assists": 8,
                "leaver_status": 0,
            }
        ]


def test_v61_collector_uses_canonical_one_request_contract_without_identifiers() -> None:
    source = _Source()
    payload = asyncio.run(collect_profiles(source, [42], salt=b"x" * 32))

    assert source.calls == [(42, 365, SUMMARY_HISTORY_PROJECTION, 10_000)]
    assert payload["request_manifest"]["physical_request_count"] == 1
    assert payload["raw_identifiers_present"] is False
    assert "account_id" not in payload["profiles"][0]
    assert "account_id" not in payload["profiles"][0]["matches"][0]
    assert payload["profiles"][0]["matches"][0]["match_id"] == 4200
    assert payload["profiles"][0]["matches"][0]["leaver_status"] == 0

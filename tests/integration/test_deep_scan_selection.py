from __future__ import annotations

from typing import Any

from app.analysis.service import AnalysisService
from app.core.config import Settings


class TrackingSource:
    def __init__(self, history: list[dict[str, Any]], details: dict[int, dict[str, Any]]) -> None:
        self.history = history
        self.details = details
        self.requests: list[tuple[str, int]] = []

    async def get_player(self, account_id: int) -> dict[str, Any]:
        self.requests.append(("player", account_id))
        return {"profile": {"account_id": account_id, "personaname": "Tracked player"}}

    async def get_matches(self, account_id: int, *, limit: int = 200) -> list[dict[str, Any]]:
        self.requests.append(("matches", account_id))
        return self.history[:limit]

    async def get_match(self, match_id: int) -> dict[str, Any]:
        self.requests.append(("match", match_id))
        return self.details[match_id]


def _summary(match_id: int, hero_id: int, won: bool) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "start_time": 1_700_000_000 + match_id * 3_600,
        "duration": 1_800,
        "game_mode": 1,
        "lobby_type": 7,
        "radiant_win": won,
        "player_slot": 0,
        "hero_id": hero_id,
        "lane_role": 3,
        "rank_tier": 45,
        "leaver_status": 0,
    }


def _detail(summary: dict[str, Any], account_id: int = 42) -> dict[str, Any]:
    return {
        **summary,
        "players": [
            {
                "account_id": account_id,
                "player_slot": summary["player_slot"],
                "hero_id": summary["hero_id"],
                "lane_role": summary["lane_role"],
                "rank_tier": 45,
                "kills": 8 if summary["radiant_win"] else 2,
                "deaths": 2 if summary["radiant_win"] else 8,
                "assists": 12,
                "last_hits": 200,
                "denies": 10,
                "gold_per_min": 500,
                "xp_per_min": 600,
                "net_worth": 15000,
                "gold_spent": 14000,
                "hero_damage": 20000,
                "tower_damage": 1500,
                "hero_healing": 0,
                "obs_placed": 0,
                "sen_placed": 0,
                "party_size": 1,
                "item_0": 1,
                "item_1": 0,
                "item_2": 0,
                "item_3": 0,
                "item_4": 0,
                "item_5": 0,
                "leaver_status": 0,
            }
        ],
    }


async def test_deep_scan_hydrates_only_global_selection() -> None:
    history = [_summary(index, 1 if index <= 10 else 2, index <= 9) for index in range(1, 21)]
    details = {item["match_id"]: _detail(item) for item in history}
    source = TrackingSource(history, details)
    service = AnalysisService(
        source,
        settings=Settings(max_deep_matches=5, max_data_cost_per_report=5),
    )
    job, _ = await service.create_analysis("42", enqueue=False, mode="deep_scan")
    await service.run_job(job)

    deep_reads = [request for request in source.requests if request[0] == "match"]
    report = service.repository.get_report(job.report_id or "")
    assert job.status == "completed"
    assert 0 < len(deep_reads) <= 5
    assert report is not None
    assert report["cost"]["detail_requests"] == len(deep_reads)
    assert report["telemetry"]["candidate_matches"] >= len(deep_reads)

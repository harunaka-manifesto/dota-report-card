from __future__ import annotations

from typing import Any

from scripts.collect_v6_calibration_candidates import collect_candidates, collect_until_target


class FakeOpenDotaClient:
    async def get_public_matches(self, **_kwargs: Any) -> list[dict[str, Any]]:
        return [{"match_id": 20}, {"match_id": 19}]

    async def get_match(self, match_id: int) -> dict[str, Any]:
        players = (
            [{"account_id": 1}, {"account_id": 2}, {"account_id": None}]
            if match_id == 20
            else [{"account_id": 2}, {"account_id": 3}]
        )
        return {"match_id": match_id, "players": players, "cluster": 122}


async def test_collect_candidates_deduplicates_and_counts_anonymous_slots() -> None:
    artifact = await collect_candidates(
        FakeOpenDotaClient(),
        match_count=2,
        requests_per_minute=1_000_000,
    )

    assert artifact["candidate_account_ids"] == [1, 2, 3]
    assert artifact["summary"] == {
        "requested_seed_matches": 2,
        "collected_seed_matches": 2,
        "failed_seed_matches": 0,
        "identified_player_slots": 4,
        "anonymous_player_slots": 1,
        "duplicate_identified_slots": 1,
        "unique_candidate_account_ids": 3,
    }
    assert artifact["source"]["rank_filters_used"] is False


class PagingOpenDotaClient:
    def __init__(self) -> None:
        self.cursors: list[int | None] = []

    async def get_public_matches(self, **kwargs: Any) -> list[dict[str, Any]]:
        cursor = kwargs.get("less_than_match_id")
        self.cursors.append(cursor)
        pages = {
            None: [{"match_id": 20}, {"match_id": 19}],
            19: [{"match_id": 18}, {"match_id": 17}],
        }
        return pages[cursor]

    async def get_match(self, match_id: int) -> dict[str, Any]:
        account_ids = {
            20: [1, 2],
            19: [2, 3],
            18: [4],
            17: [5],
        }
        return {
            "match_id": match_id,
            "players": [{"account_id": value} for value in account_ids[match_id]],
        }


async def test_collect_until_target_pages_and_stops_after_threshold() -> None:
    client = PagingOpenDotaClient()
    checkpoints: list[int] = []

    artifact = await collect_until_target(
        client,
        target_candidates=5,
        batch_size=2,
        requests_per_minute=1_000_000,
        checkpoint=lambda value: checkpoints.append(
            value["summary"]["unique_candidate_account_ids"]
        ),
    )

    assert client.cursors == [None, 19]
    assert checkpoints == [3, 5]
    assert artifact["candidate_account_ids"] == [1, 2, 3, 4, 5]
    assert artifact["summary"]["collected_seed_matches"] == 4
    assert artifact["batches"][-1]["candidate_total"] == 5

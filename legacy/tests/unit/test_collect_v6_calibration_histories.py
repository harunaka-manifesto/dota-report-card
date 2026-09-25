from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.collect_v6_calibration_histories import (
    HISTORY_PROJECTIONS,
    RequestPacer,
    build_reference_data,
    collect_histories,
    process_candidate,
)


class FakeHistoryClient:
    async def get_matches(self, account_id: int, **kwargs: Any) -> list[dict[str, Any]]:
        assert kwargs["project"] == HISTORY_PROJECTIONS
        assert "skill" not in HISTORY_PROJECTIONS
        assert "average_rank" not in HISTORY_PROJECTIONS
        return [
            {
                "match_id": index + 1,
                "account_id": account_id,
                "player_slot": 0,
                "radiant_win": True,
                "duration": 1_800,
                "game_mode": 1,
                "lobby_type": 0,
                "hero_id": 1,
                "start_time": 1_700_000_000 + index * 10_000,
                "kills": 5,
                "deaths": 3,
                "assists": 10,
                "leaver_status": 0,
                "cluster": 111,
                "lane_role": 1,
                "skill": 3,
            }
            for index in range(30)
        ]


async def test_process_candidate_produces_pseudonymous_mmr_free_eligible_rows(
    tmp_path: Path,
) -> None:
    del tmp_path
    references = build_reference_data(
        {"111": 1},
        [{"name": "7.40", "date": "2023-01-01T00:00:00Z"}],
        {1: {"hero_function": "carry"}},
    )
    record = await process_candidate(
        FakeHistoryClient(),
        42,
        salt=b"s" * 32,
        references=references,
        pacer=RequestPacer(1_000_000),
        window_start=1_699_000_000,
        window_end=1_701_000_000,
    )

    assert record["status"] == "eligible"
    assert record["eligible_match_count"] == 30
    assert record["profile_id"] != "42"
    assert len(record["matches"]) == 30
    first = record["matches"][0]
    assert "account_id" not in first
    assert "skill_bracket" not in first
    assert "eligibility" not in first
    assert first["region"] == 1
    assert first["patch"] == "7.40"
    assert first["hero_function"] == "carry"
    assert first["lane_context"] == "carry"
    assert first["metrics"]["outcome"] == 1.0


async def test_collect_histories_stops_at_profile_batch_after_target(tmp_path: Path) -> None:
    client = FakeHistoryClient()
    references = build_reference_data(
        {"111": 1},
        [{"name": "7.40", "date": "2023-01-01T00:00:00Z"}],
        {1: {"hero_function": "carry"}},
    )
    payload = await collect_histories(
        client,
        list(range(1, 41)),
        checkpoint_path=tmp_path / "checkpoint.jsonl",
        output_path=tmp_path / "corpus.json",
        salt=b"s" * 32,
        references=references,
        requests_per_minute=1_000_000,
        concurrency=4,
        progress_batch_size=20,
        target_eligible=1,
        window_end=1_701_000_000,
    )

    assert payload["summary"]["processed_profile_count"] == 20
    assert payload["summary"]["eligible_profile_count"] == 20
    assert payload["summary"]["target_met"] is True

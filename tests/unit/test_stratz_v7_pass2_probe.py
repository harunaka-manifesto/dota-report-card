from __future__ import annotations

import re

import pytest
from app.stratz.queries import (
    GET_DEEP_MATCH_BATCH,
    GET_PLAYER_RANK_HISTORY,
    PROBE_ITEM_VOCABULARY,
    PROBE_LOCATION_REPORT,
    STRATZ_OPERATIONS,
)

from scripts.stratz_v7_pass2_probe import (
    BATCH_LADDER,
    MAX_PHYSICAL_CALLS,
    main,
    projected_cost,
    summarise_deep_batch,
    summarise_item_vocabulary,
    summarise_location_report,
)

# Surfaces the V7 rules exclude. A field that is not requested cannot leak, so
# the guard is on the query document itself rather than on the response.
FORBIDDEN_TOKENS = (
    "imp",
    "award",
    "behavior",
    "intentionalFeeding",
    "streakPrediction",
    "actualRank",
    "averageRank",
    "averageImp",
    "bracket",
    "analysisOutcome",
    "predictedOutcomeWeight",
    "winRates",
    "predictedWinRates",
    "chatEvents",
    "allTalks",
    "chatWheels",
    "playbackData",
    "dotaPlus",
    "steamAccount ",
)


def _words(document: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", document))


@pytest.mark.parametrize(
    "operation",
    [GET_DEEP_MATCH_BATCH, PROBE_LOCATION_REPORT, PROBE_ITEM_VOCABULARY],
)
def test_research_operations_request_no_forbidden_surface(operation) -> None:
    words = _words(operation.document)
    for token in FORBIDDEN_TOKENS:
        assert token.strip() not in words, f"{operation.name} requests {token}"


def test_deep_batch_requests_everything_the_report_needs() -> None:
    words = _words(GET_DEEP_MATCH_BATCH.document)
    required = {
        "deathEvents",
        "killEvents",
        "assistEvents",
        "itemPurchases",
        "wards",
        "runes",
        "networthPerMinute",
        "lastHitsPerMinute",
        "deniesPerMinute",
        "goldPerMinute",
        "experiencePerMinute",
        "heroDamagePerMinute",
        "heroDamageReceivedPerMinute",
        "towerDamagePerMinute",
        "healPerMinute",
        "campStack",
        "radiantNetworthLeads",
        "radiantExperienceLeads",
        "radiantKills",
        "direKills",
        "towerStatusRadiant",
        "barracksStatusRadiant",
        "firstBloodTime",
        "allPlayers",
    }
    assert required <= words, sorted(required - words)


def test_the_ten_player_projection_carries_no_trajectories() -> None:
    # The specimen that asked for trajectories on all ten players was rejected
    # at a complexity of 6,159,595 against a ceiling of 310,000.
    document = GET_DEEP_MATCH_BATCH.document
    block = document[document.index("allPlayers:") : document.index("players(steamAccountId:")]
    # goldPerMinute and experiencePerMinute are scalars on the player type and
    # are wanted here; what must not appear is the stats block that carries the
    # per-minute arrays and the event lists.
    for banned in ("stats", "Events", "itemPurchases", "wards", "runes", "campStack"):
        assert banned not in block, f"allPlayers projection carries {banned}"


def test_the_ten_player_projection_carries_no_identifiers() -> None:
    document = GET_DEEP_MATCH_BATCH.document
    block = document[document.index("allPlayers:") : document.index("players(steamAccountId:")]
    assert "steamAccountId" not in block
    assert "steamAccount" not in block


def test_rank_history_is_registered_but_declares_itself_display_only() -> None:
    assert "DISPLAY ONLY" in GET_PLAYER_RANK_HISTORY.purpose
    assert "never" in GET_PLAYER_RANK_HISTORY.purpose
    assert GET_PLAYER_RANK_HISTORY.name in STRATZ_OPERATIONS


def test_rank_history_is_the_only_new_operation_touching_rank() -> None:
    for operation in (GET_DEEP_MATCH_BATCH, PROBE_LOCATION_REPORT, PROBE_ITEM_VOCABULARY):
        assert "rank" not in operation.document.lower()


def test_operation_digests_are_stable_and_distinct() -> None:
    operations = (
        GET_DEEP_MATCH_BATCH,
        PROBE_LOCATION_REPORT,
        PROBE_ITEM_VOCABULARY,
        GET_PLAYER_RANK_HISTORY,
    )
    digests = {op.document_sha256 for op in operations}
    assert len(digests) == len(operations)
    assert all(len(digest) == 64 for digest in digests)


def test_batch_ladder_descends_and_ends_at_one() -> None:
    assert list(BATCH_LADDER) == sorted(BATCH_LADDER, reverse=True)
    assert BATCH_LADDER[-1] == 1


def test_call_budget_above_the_ceiling_is_refused() -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "--dotenv",
                "/nonexistent",
                "--steam-account-id",
                "1",
                "--match-ids",
                "1",
                "--max-calls",
                str(MAX_PHYSICAL_CALLS + 1),
            ]
        )


def test_projected_cost_rounds_partial_batches_up() -> None:
    row = projected_cost(batch_size=4, accounts=300, matches_per_account=500)
    assert row["calls_per_account"] == 125
    assert row["total_calls"] == 37_500
    assert row["days_at_15000_per_day"] == 2.5
    # A partial final batch still costs a call.
    assert projected_cost(4, 1, 501)["calls_per_account"] == 126


def test_halving_the_batch_size_doubles_the_cost() -> None:
    eight = projected_cost(8, 300, 500)["total_calls"]
    four = projected_cost(4, 300, 500)["total_calls"]
    assert four == pytest.approx(eight * 2, rel=0.02)


def test_deep_batch_summary_is_aggregate_only() -> None:
    payload = {
        "data": {
            "player": {
                "matches": [
                    {
                        "parsedDateTime": 1,
                        "allPlayers": [{"heroId": i} for i in range(10)],
                        "players": [
                            {
                                "stats": {
                                    "networthPerMinute": [1, 2, 3],
                                    "deathEvents": [{"time": 10}],
                                    "wards": [],
                                }
                            }
                        ],
                    }
                ]
            }
        }
    }
    summary = summarise_deep_batch(payload)
    assert summary["matches"] == 1
    assert summary["parsed_matches"] == 1
    assert summary["all_player_row_counts"] == [10]
    assert summary["field_present_in_matches"]["deathEvents"] == 1
    assert summary["field_median_length"]["networthPerMinute"] == 3
    assert summary["usable"] is True
    assert "heroId" not in str(summary)


def test_a_response_without_death_events_is_not_usable() -> None:
    payload = {
        "data": {
            "player": {
                "matches": [{"players": [{"stats": {"networthPerMinute": [1]}}], "allPlayers": []}]
            }
        }
    }
    assert summarise_deep_batch(payload)["usable"] is False


@pytest.mark.parametrize("payload", [None, {}, {"data": None}, {"data": {"player": None}}])
def test_summaries_fail_closed_on_an_empty_response(payload) -> None:
    assert summarise_deep_batch(payload)["usable"] is False
    assert summarise_location_report(payload)["usable"] is False
    assert summarise_item_vocabulary(payload)["usable"] is False


def test_location_report_shape_is_described_not_stored() -> None:
    payload = {
        "data": {
            "player": {
                "matches": [
                    {"players": [{"stats": {"locationReport": [{"x": 1, "y": 2, "time": 3}]}}]}
                ]
            }
        }
    }
    summary = summarise_location_report(payload)
    assert summary["usable"] is True
    assert summary["samples"][0]["element_keys"] == ["time", "x", "y"]
    assert "1" not in str(summary["samples"][0].get("element_keys"))


def test_absent_location_report_is_reported_as_unusable() -> None:
    payload = {"data": {"player": {"matches": [{"players": [{"stats": {"locationReport": None}}]}]}}}
    summary = summarise_location_report(payload)
    assert summary["usable"] is False
    assert summary["samples"] == [{"present": False}]


def test_item_vocabulary_summary_counts_costs() -> None:
    payload = {
        "data": {
            "constants": {
                "items": [
                    {"id": 1, "displayName": "Tango", "stat": {"cost": 90}},
                    {"id": 2, "displayName": "Blink", "stat": {"cost": None}},
                ]
            }
        }
    }
    summary = summarise_item_vocabulary(payload)
    assert summary == {
        "items": 2,
        "with_cost": 1,
        "element_keys": ["displayName", "id", "stat"],
        "usable": True,
    }

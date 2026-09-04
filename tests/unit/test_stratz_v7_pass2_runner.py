from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.stratz.queries import GET_DEEP_MATCH_BATCH

from scripts.stratz_v7_corpus_runner import StopRun
from scripts.stratz_v7_pass2_runner import (
    PASS2_BATCH_SIZE,
    PASS2_CANONICAL_SCHEMA,
    PASS2_MATCH_TARGET,
    PASS2_SPLIT,
    PASS2_TARGET_ACCOUNTS,
    Pass2Error,
    Pass2Runner,
    ReservedSplitRequested,
    batches,
    canonicalize_account,
    normalize_deep_batch,
    pass2_targets,
    planned_match_ids,
    verify,
)

TOKEN = "test-token-do-not-log-abcdef123456"


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _Target:
    def __init__(self, position: int, split: str = PASS2_SPLIT, account_id: int | None = None):
        self.source_position = position
        self.split = split
        self.pseudonym = f"v7p_{position:04d}"
        self.account_id = account_id if account_id is not None else 1000 + position
        self.parsed_subset = True
        self.parsed_order = position


class _Cohort:
    def __init__(self, targets):
        self.targets = tuple(targets)


class _Response:
    def __init__(self, status: int, payload: Any, headers: dict[str, str] | None = None):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}
        self.content = (
            json.dumps(payload).encode() if payload is not None else b"<not json>"
        )

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


#: Scripted entry meaning "return exactly the matches this request asked for".
#: Echoing beats a hand-written payload: the runner rejects any match it did not
#: request, so a fixture that guesses the plan order fails for the wrong reason.
ECHO = "ECHO"


class _Client:
    """Scripted transport. Records requests so we can assert on ordering."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    async def post(self, url, **kwargs):
        self.requests.append(kwargs)
        if not self._responses:
            raise AssertionError("transport exhausted")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        if item == ECHO:
            return _ok(kwargs["json"]["variables"]["matchIds"])
        return item

    async def aclose(self):
        return None


def _match(match_id: int, *, started: int = 1_700_000_000) -> dict[str, Any]:
    return {
        "id": match_id,
        "didRadiantWin": True,
        "durationSeconds": 1800,
        "startDateTime": started,
        "endDateTime": started + 1800,
        "parsedDateTime": started + 1900,
        "statsDateTime": started + 1900,
        "isStats": True,
        "numHumanPlayers": 10,
        "gameMode": "ALL_PICK_RANKED",
        "lobbyType": "RANKED",
        "gameVersionId": 182,
        "regionId": 5,
        "firstBloodTime": 60,
        "towerStatusRadiant": 1828,
        "towerStatusDire": 0,
        "barracksStatusRadiant": 63,
        "barracksStatusDire": 0,
        "radiantKills": [0, 1],
        "direKills": [0, 2],
        "radiantNetworthLeads": [0, 500],
        "radiantExperienceLeads": [0, 300],
        "bottomLaneOutcome": "TIE",
        "midLaneOutcome": "RADIANT_VICTORY",
        "topLaneOutcome": "DIRE_VICTORY",
        "towerDeaths": [{"time": 600, "isRadiant": False, "npcId": 12, "attacker": 41}],
        "pickBans": [
            {
                "isPick": True,
                "isRadiant": True,
                "heroId": 41,
                "bannedHeroId": None,
                "order": 1,
                "playerIndex": 0,
                "isCaptain": False,
                "wasBannedSuccessfully": None,
            }
        ],
        "allPlayers": [
            {
                "playerSlot": slot,
                "isRadiant": slot < 5,
                "isVictory": slot < 5,
                "heroId": 10 + slot,
                "position": "POSITION_1",
                "role": "CORE",
                "lane": "SAFE_LANE",
                "kills": 1,
                "deaths": 2,
                "assists": 3,
                "numLastHits": 100,
                "numDenies": 5,
                "goldPerMinute": 500,
                "experiencePerMinute": 600,
                "networth": 15000,
                "heroDamage": 20000,
                "towerDamage": 1000,
                "heroHealing": 0,
            }
            for slot in range(10)
        ],
        "players": [
            {
                "steamAccountId": 42,
                "playerSlot": 0,
                "isRadiant": True,
                "isVictory": True,
                "heroId": 41,
                "variant": 0,
                "position": "POSITION_1",
                "role": "CORE",
                "lane": "SAFE_LANE",
                "leaverStatus": "NONE",
                "isRandom": False,
                "partyId": 1,
                "invisibleSeconds": 0,
                "kills": 5,
                "deaths": 2,
                "assists": 7,
                "numLastHits": 200,
                "numDenies": 10,
                "goldPerMinute": 600,
                "experiencePerMinute": 700,
                "networth": 20000,
                "level": 25,
                "gold": 500,
                "goldSpent": 19000,
                "heroDamage": 30000,
                "towerDamage": 2000,
                "heroHealing": 100,
                "item0Id": 1,
                "item1Id": 2,
                "item2Id": None,
                "item3Id": None,
                "item4Id": None,
                "item5Id": None,
                "backpack0Id": None,
                "backpack1Id": None,
                "backpack2Id": None,
                "neutral0Id": 2190,
                "abilities": [
                    {
                        "abilityId": 5001,
                        "level": 6,
                        "time": 480,
                        "isTalent": False,
                    }
                ],
                "stats": {
                    "networthPerMinute": [100, 200],
                    "goldPerMinute": [100, 200],
                    "experiencePerMinute": [100, 200],
                    "lastHitsPerMinute": [1, 2],
                    "deniesPerMinute": [0, 1],
                    "heroDamagePerMinute": [0, 500],
                    "heroDamageReceivedPerMinute": [0, 300],
                    "towerDamagePerMinute": [0, 0],
                    "healPerMinute": [0, 0],
                    "campStack": [0, 1],
                    "level": [1, 2],
                    "actionsPerMinute": [300, 320],
                    "tripsFountainPerMinute": [0, 1],
                    "killEvents": [{"time": 400}],
                    "deathEvents": [{"time": 900}],
                    "assistEvents": [{"time": 500}],
                    "itemPurchases": [{"time": -60, "itemId": 44}],
                    "wards": [{"time": 30, "type": 1, "positionX": 120, "positionY": 130}],
                    "runes": [{"time": 240, "rune": "BOUNTY"}],
                    "itemUsed": [{"itemId": 116, "count": 3}],
                    "wardDestruction": [
                        {"time": 700, "isWard": True, "gold": 50, "experience": 100}
                    ],
                    "matchPlayerBuffEvent": [
                        {"time": 1200, "itemId": 609, "abilityId": None, "stackCount": 1}
                    ],
                    "towerDamageReport": [
                        {"npcId": 12, "damage": 900, "damageCreeps": 10, "damageFromAbility": 100}
                    ],
                    "farmDistributionReport": {"buyBackGold": 0, "abandonGold": 0},
                },
            }
        ],
    }


def _payload(match_ids) -> dict[str, Any]:
    return {"data": {"player": {"matches": [_match(mid) for mid in match_ids]}}}


def _ok(match_ids, headers=None) -> _Response:
    return _Response(200, _payload(match_ids), headers)


def _pass1(tmp_path: Path, pseudonym: str, match_ids, *, split: str = PASS2_SPLIT) -> None:
    directory = tmp_path / "canonical/history"
    directory.mkdir(parents=True, exist_ok=True)
    rows = [
        {"match_id": mid, "started_at": 1_700_000_000 + index, "is_parsed": True}
        for index, mid in enumerate(match_ids)
    ]
    (directory / f"{pseudonym}.json").write_text(
        json.dumps({"split": split, "account_pseudonym": pseudonym, "rows": rows}),
        encoding="utf-8",
    )


def _runner(tmp_path: Path, targets, responses, **kwargs) -> Pass2Runner:
    return Pass2Runner(
        _Cohort(targets),
        pass1_dir=tmp_path / "pass1",
        output_dir=tmp_path / "pass2",
        token=TOKEN,
        network=True,
        http_client=_Client(responses),
        max_retries=kwargs.pop("max_retries", 2),
        sleep=kwargs.pop("sleep", _no_sleep),
        **kwargs,
    )


async def _no_sleep(_seconds: float) -> None:
    return None


# ---------------------------------------------------------------------------
# Query contract
# ---------------------------------------------------------------------------


def test_production_query_is_versioned_and_hashed() -> None:
    assert GET_DEEP_MATCH_BATCH.version == "3.0.0"
    assert len(GET_DEEP_MATCH_BATCH.document_sha256) == 64
    assert GET_DEEP_MATCH_BATCH.document_sha256 == GET_DEEP_MATCH_BATCH.digest


def test_production_query_selects_every_resolved_object_we_decided_to_keep() -> None:
    document = GET_DEEP_MATCH_BATCH.document
    for block, fields in {
        "towerDeaths": ("time", "isRadiant", "npcId", "attacker"),
        "pickBans": ("isPick", "heroId", "bannedHeroId", "order", "playerIndex"),
        "abilities": ("abilityId", "level", "time", "isTalent"),
        "itemUsed": ("itemId", "count"),
        "wardDestruction": ("time", "isWard", "gold", "experience"),
        "matchPlayerBuffEvent": ("time", "itemId", "abilityId", "stackCount"),
        "towerDamageReport": ("npcId", "damage", "damageCreeps", "damageFromAbility"),
        "farmDistributionReport": ("buyBackGold", "abandonGold"),
    }.items():
        start = document.index(block + " {")
        body = document[start : document.index("}", start)]
        for field in fields:
            assert field in body, f"{block} is missing {field}"


def test_production_query_excludes_the_objects_we_decided_against() -> None:
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", GET_DEEP_MATCH_BATCH.document))
    # locationReport carries only positionX/positionY with no time, so it cannot
    # be joined to a death or any other event; the rest are either unresolved
    # nested objects or mechanical-intensity counters.
    for excluded in (
        "locationReport",
        "heroDamageReport",
        "inventoryReport",
        "laneReport",
        "abilityCastReport",
        "actionReport",
        "courierKills",
    ):
        assert excluded not in words


def test_production_query_excludes_proprietary_win_rate_fields_from_pickbans() -> None:
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", GET_DEEP_MATCH_BATCH.document))
    assert "adjustedWinRate" not in words
    assert "baseWinRate" not in words


# ---------------------------------------------------------------------------
# Deterministic planning
# ---------------------------------------------------------------------------


def test_targets_are_discovery_only_in_frozen_order() -> None:
    cohort = _Cohort(
        [
            _Target(9),
            _Target(3, split="CANDIDATE_TEST"),
            _Target(1),
            _Target(7, split="CALIBRATION_RESERVED"),
            _Target(5),
        ]
    )
    targets = pass2_targets(cohort, limit=10)
    assert [t.source_position for t in targets] == [1, 5, 9]
    assert {t.split for t in targets} == {PASS2_SPLIT}


def test_targets_never_include_the_confirmation_split() -> None:
    cohort = _Cohort([_Target(i, split="CANDIDATE_TEST") for i in range(5)])
    assert pass2_targets(cohort, limit=5) == ()


def test_target_selection_is_stable_across_calls() -> None:
    cohort = _Cohort([_Target(i) for i in (4, 2, 8, 6)])
    assert [t.pseudonym for t in pass2_targets(cohort, limit=3)] == [
        t.pseudonym for t in pass2_targets(cohort, limit=3)
    ]


def test_default_account_limit_is_the_owner_decision() -> None:
    assert PASS2_TARGET_ACCOUNTS == 300
    assert PASS2_MATCH_TARGET == 500
    assert PASS2_BATCH_SIZE == 8


def test_match_plan_is_most_recent_first_and_capped() -> None:
    document = {
        "rows": [
            {"match_id": 1, "started_at": 100, "is_parsed": True},
            {"match_id": 2, "started_at": 300, "is_parsed": True},
            {"match_id": 3, "started_at": 200, "is_parsed": True},
        ]
    }
    assert planned_match_ids(document) == [2, 3, 1]
    assert planned_match_ids(document, target=2) == [2, 3]


def test_match_plan_breaks_timestamp_ties_deterministically() -> None:
    document = {
        "rows": [
            {"match_id": 5, "started_at": 100, "is_parsed": True},
            {"match_id": 9, "started_at": 100, "is_parsed": True},
        ]
    }
    assert planned_match_ids(document) == [9, 5]


def test_match_plan_skips_unparsed_and_duplicate_rows() -> None:
    document = {
        "rows": [
            {"match_id": 1, "started_at": 100, "is_parsed": False},
            {"match_id": 2, "started_at": 200, "is_parsed": True},
            {"match_id": 2, "started_at": 200, "is_parsed": True},
        ]
    }
    assert planned_match_ids(document) == [2]


def test_batches_use_eight_and_allow_a_short_final_batch() -> None:
    plan = list(range(20))
    result = batches(plan)
    assert [len(b) for b in result] == [8, 8, 4]
    assert [m for b in result for m in b] == plan


def test_a_single_match_is_one_short_batch() -> None:
    assert batches([7]) == [[7]]
    assert batches([]) == []


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


def _normalize(match_ids, **kwargs):
    return normalize_deep_batch(
        _payload(match_ids),
        requested_ids=match_ids,
        pseudonym="v7p_0001",
        split=kwargs.pop("split", PASS2_SPLIT),
        source_position=1,
        batch_index=0,
        **kwargs,
    )


def test_normalisation_keeps_every_resolved_object_selection() -> None:
    document = _normalize([1])
    row = document["rows"][0]
    assert row["tower_deaths"] == [
        {"time": 600, "is_radiant": False, "npc_id": 12, "attacker": 41}
    ]
    assert row["pick_bans"][0]["hero_id"] == 41
    assert row["self"]["abilities"][0] == {
        "ability_id": 5001,
        "level": 6,
        "time": 480,
        "is_talent": False,
    }
    events = row["self"]["events"]
    assert events["item_used"] == [{"item_id": 116, "count": 3}]
    assert events["ward_destruction"][0]["is_ward"] is True
    assert events["buff_events"][0]["item_id"] == 609
    assert events["tower_damage_report"][0]["npc_id"] == 12
    assert row["self"]["farm_distribution"] == {"buy_back_gold": 0, "abandon_gold": 0}
    assert row["self"]["party_id"] == 1
    assert row["radiant_experience_leads"] == [0, 300]


def test_quarantined_trajectories_are_kept_out_of_the_analytical_block() -> None:
    # actionsPerMinute correlates with skill. It is collected, but it must not
    # sit alongside the fields a feature builder reaches for by default.
    row = _normalize([1])["rows"][0]
    assert "actions_per_minute" not in row["self"]["trajectories"]
    assert row["self"]["quarantined_trajectories"]["actions_per_minute"] == [300, 320]


def test_normalisation_records_matches_the_provider_did_not_return() -> None:
    payload = _payload([1, 2])
    document = normalize_deep_batch(
        payload,
        requested_ids=[1, 2, 3],
        pseudonym="v7p_0001",
        split=PASS2_SPLIT,
        source_position=1,
        batch_index=0,
    )
    assert document["missing_match_ids"] == [3]
    assert document["returned_match_ids"] == [1, 2]


def test_normalisation_rejects_a_match_that_was_not_requested() -> None:
    with pytest.raises(StopRun):
        normalize_deep_batch(
            _payload([99]),
            requested_ids=[1],
            pseudonym="v7p_0001",
            split=PASS2_SPLIT,
            source_position=1,
            batch_index=0,
        )


def test_normalisation_refuses_a_non_discovery_split() -> None:
    with pytest.raises(ReservedSplitRequested):
        _normalize([1], split="CANDIDATE_TEST")


def test_normalisation_stamps_the_operation_contract() -> None:
    document = _normalize([1])
    assert document["operation_version"] == GET_DEEP_MATCH_BATCH.version
    assert document["operation_document_sha256"] == GET_DEEP_MATCH_BATCH.document_sha256
    assert document["schema_version"].startswith("stratz-v7-pass2-provider-native")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"data": None},
        {"data": {}},
        {"data": {"player": None}},
        {"data": {"player": {}}},
        {"data": {"player": {"matches": None}}},
    ],
)
def test_normalisation_fails_closed_on_missing_player_or_match_data(payload) -> None:
    with pytest.raises(StopRun):
        normalize_deep_batch(
            payload,
            requested_ids=[1],
            pseudonym="v7p_0001",
            split=PASS2_SPLIT,
            source_position=1,
            batch_index=0,
        )


def test_normalisation_fails_closed_when_the_own_player_row_is_absent() -> None:
    payload = _payload([1])
    payload["data"]["player"]["matches"][0]["players"] = []
    with pytest.raises(StopRun):
        normalize_deep_batch(
            payload,
            requested_ids=[1],
            pseudonym="v7p_0001",
            split=PASS2_SPLIT,
            source_position=1,
            batch_index=0,
        )


def test_normalisation_tolerates_a_null_stats_block() -> None:
    payload = _payload([1])
    payload["data"]["player"]["matches"][0]["players"][0]["stats"] = None
    row = normalize_deep_batch(
        payload,
        requested_ids=[1],
        pseudonym="v7p_0001",
        split=PASS2_SPLIT,
        source_position=1,
        batch_index=0,
    )["rows"][0]
    assert row["self"]["trajectories"]["networth_per_minute"] is None
    assert row["self"]["events"]["death_events"] is None
    assert row["self"]["farm_distribution"] is None


def test_normalisation_tolerates_a_null_farm_distribution() -> None:
    payload = _payload([1])
    payload["data"]["player"]["matches"][0]["players"][0]["stats"][
        "farmDistributionReport"
    ] = None
    row = normalize_deep_batch(
        payload,
        requested_ids=[1],
        pseudonym="v7p_0001",
        split=PASS2_SPLIT,
        source_position=1,
        batch_index=0,
    )["rows"][0]
    assert row["self"]["farm_distribution"] is None


def test_normalisation_rejects_a_forbidden_provider_field() -> None:
    payload = _payload([1])
    payload["data"]["player"]["matches"][0]["players"][0]["imp"] = 12
    with pytest.raises(StopRun):
        normalize_deep_batch(
            payload,
            requested_ids=[1],
            pseudonym="v7p_0001",
            split=PASS2_SPLIT,
            source_position=1,
            batch_index=0,
        )


def test_canonicalisation_deduplicates_and_orders_by_match_id() -> None:
    first = _normalize([2, 1])
    second = _normalize([1, 3])
    canonical = canonicalize_account(
        [first, second],
        pseudonym="v7p_0001",
        split=PASS2_SPLIT,
        source_position=1,
        planned_ids=[1, 2, 3, 4],
    )
    assert [row["match_id"] for row in canonical["rows"]] == [1, 2, 3]
    assert canonical["duplicate_rows_dropped"] == 1
    assert canonical["missing_match_ids"] == [4]
    assert canonical["schema_version"] == PASS2_CANONICAL_SCHEMA


# ---------------------------------------------------------------------------
# Collection, resume, idempotency
# ---------------------------------------------------------------------------


async def test_a_full_account_collects_in_eight_match_batches(tmp_path: Path) -> None:
    plan = list(range(1, 21))
    _pass1(tmp_path / "pass1", "v7p_0001", plan)
    client = _Client([ECHO, ECHO, ECHO])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = client
    state = await runner.run()

    assert state["status"] == "COMPLETE"
    sizes = [len(r["json"]["variables"]["matchIds"]) for r in client.requests]
    assert sizes == [8, 8, 4]
    canonical = json.loads(
        (tmp_path / "pass2/canonical/v7p_0001.json").read_text(encoding="utf-8")
    )
    assert canonical["collected_match_count"] == 20
    assert canonical["missing_match_ids"] == []
    assert [row["match_id"] for row in canonical["rows"]] == sorted(plan)


async def test_requests_go_out_in_the_planned_match_order(tmp_path: Path) -> None:
    plan = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    _pass1(tmp_path / "pass1", "v7p_0001", plan)
    client = _Client([ECHO, ECHO])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = client
    await runner.run()
    sent = [m for r in client.requests for m in r["json"]["variables"]["matchIds"]]
    # Pass-1 rows ascend in started_at, so the plan is reversed most-recent-first.
    assert sent == list(reversed(plan))


async def test_accounts_are_visited_in_frozen_order(tmp_path: Path) -> None:
    for position, plan in ((9, [1]), (1, [2]), (5, [3])):
        _pass1(tmp_path / "pass1", f"v7p_{position:04d}", plan)
    client = _Client([ECHO, ECHO, ECHO])
    runner = _runner(tmp_path, [_Target(9), _Target(1), _Target(5)], [])
    runner._http = client
    await runner.run()
    account_ids = [r["json"]["variables"]["steamAccountId"] for r in client.requests]
    assert account_ids == [1001, 1005, 1009]


async def test_resume_from_a_partial_account_refetches_nothing(tmp_path: Path) -> None:
    plan = list(range(1, 17))
    _pass1(tmp_path / "pass1", "v7p_0001", plan)

    first = _Client([ECHO, httpx.ConnectError("boom")])
    runner = _runner(tmp_path, [_Target(1)], [], max_retries=0)
    runner._http = first
    state = await runner.run()
    assert state["status"] == "STOP"
    assert state["accounts"]["v7p_0001"]["next_batch"] == 1

    second = _Client([ECHO])
    resumed = _runner(tmp_path, [_Target(1)], [])
    resumed._http = second
    state = await resumed.run()
    assert state["status"] == "COMPLETE"
    # Only the outstanding batch was requested on resume.
    assert len(second.requests) == 1
    assert second.requests[0]["json"]["variables"]["matchIds"] == list(reversed(plan))[8:16]


async def test_rerunning_a_completed_account_issues_no_request(tmp_path: Path) -> None:
    plan = [1, 2, 3]
    _pass1(tmp_path / "pass1", "v7p_0001", plan)
    first = _Client([ECHO])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = first
    await runner.run()

    second = _Client([])
    again = _runner(tmp_path, [_Target(1)], [])
    again._http = second
    state = await again.run()
    assert state["status"] == "COMPLETE"
    assert second.requests == []


async def test_a_repeated_batch_is_served_from_the_archive_not_the_network(
    tmp_path: Path,
) -> None:
    plan = [1, 2, 3]
    _pass1(tmp_path / "pass1", "v7p_0001", plan)
    client = _Client([ECHO])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = client
    await runner.run()

    # Same request key, second time: cache hit, no transport call.
    payload, meta = await runner.request(
        GET_DEEP_MATCH_BATCH, {"steamAccountId": 1001, "matchIds": list(reversed(plan))}
    )
    assert meta["cache_hit"] is True
    assert meta["physical_attempts"] == 0
    assert len(client.requests) == 1
    assert payload["data"]["player"]["matches"][0]["id"] == 3


async def test_an_account_with_no_parsed_matches_is_recorded_not_skipped(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "pass1/canonical/history"
    directory.mkdir(parents=True)
    (directory / "v7p_0001.json").write_text(
        json.dumps(
            {
                "split": PASS2_SPLIT,
                "rows": [{"match_id": 1, "started_at": 1, "is_parsed": False}],
            }
        ),
        encoding="utf-8",
    )
    runner = _runner(tmp_path, [_Target(1)], [])
    state = await runner.run()
    assert state["accounts"]["v7p_0001"]["status"] == "no_parsed_opportunities"
    assert state["status"] == "COMPLETE"


async def test_an_account_missing_from_pass_one_is_recorded_not_skipped(
    tmp_path: Path,
) -> None:
    runner = _runner(tmp_path, [_Target(1)], [])
    state = await runner.run()
    assert state["accounts"]["v7p_0001"]["status"] == "no_pass1_history"


async def test_a_pass_one_document_from_another_split_is_refused(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1], split="CANDIDATE_TEST")
    runner = _runner(tmp_path, [_Target(1)], [])
    with pytest.raises(ReservedSplitRequested):
        await runner._acquire_account(runner.targets[0])


# ---------------------------------------------------------------------------
# Transport failure handling
# ---------------------------------------------------------------------------


async def test_a_transient_five_hundred_is_retried_then_succeeds(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    client = _Client([_Response(503, {"errors": [{"message": "upstream"}]}), ECHO])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = client
    state = await runner.run()
    assert state["status"] == "COMPLETE"
    assert len(client.requests) == 2
    statuses = [row["http_status"] for row in runner.ledger_rows]
    assert statuses == [503, 200]


async def test_a_rate_limit_is_retried_and_honours_retry_after(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    slept: list[float] = []

    async def _record(seconds: float) -> None:
        slept.append(seconds)

    client = _Client(
        [_Response(429, {"errors": [{"message": "slow down"}]}, {"Retry-After": "7"}), ECHO]
    )
    runner = _runner(tmp_path, [_Target(1)], [], sleep=_record)
    runner._http = client
    state = await runner.run()
    assert state["status"] == "COMPLETE"
    assert 7.0 in slept


async def test_a_persistent_rate_limit_stops_the_run(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    responses = [_Response(429, {"errors": [{"message": "slow down"}]}) for _ in range(3)]
    runner = _runner(tmp_path, [_Target(1)], [], max_retries=2)
    runner._http = _Client(responses)
    state = await runner.run()
    assert state["status"] == "STOP"
    assert state["stop_kind"] == "rate_limited"


async def test_authentication_failure_stops_immediately_without_retrying(
    tmp_path: Path,
) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    client = _Client([_Response(401, {"errors": [{"message": "bad token"}]})])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = client
    state = await runner.run()
    assert state["status"] == "STOP"
    assert state["stop_kind"] == "authentication_failure"
    assert len(client.requests) == 1


async def test_a_graphql_error_stops_the_run(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = _Client([_Response(200, {"errors": [{"message": "internal failure"}]})])
    state = await runner.run()
    assert state["status"] == "STOP"
    assert state["stop_kind"] == "graphql_error"


async def test_a_schema_error_stops_the_run_and_is_never_retried(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    client = _Client(
        [_Response(200, {"errors": [{"message": "Cannot query field nonsense on type"}]})]
    )
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = client
    state = await runner.run()
    assert state["status"] == "STOP"
    assert state["stop_kind"] == "schema_drift"
    assert len(client.requests) == 1


async def test_a_malformed_body_stops_the_run(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = _Client([_Response(200, None)])
    state = await runner.run()
    assert state["status"] == "STOP"
    assert state["stop_kind"] == "invalid_response"


async def test_the_request_ceiling_pauses_rather_than_overrunning(tmp_path: Path) -> None:
    plan = list(range(1, 25))
    _pass1(tmp_path / "pass1", "v7p_0001", plan)
    client = _Client([ECHO, ECHO, ECHO])
    runner = _runner(tmp_path, [_Target(1)], [], max_requests=2)
    runner._http = client
    state = await runner.run()
    assert state["status"] == "PARTIAL_PAUSED"
    assert len(client.requests) == 2


# ---------------------------------------------------------------------------
# Secrets, durability, and verification
# ---------------------------------------------------------------------------


async def test_the_token_never_reaches_disk(tmp_path: Path) -> None:
    plan = [1, 2]
    _pass1(tmp_path / "pass1", "v7p_0001", plan)
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = _Client([ECHO])
    await runner.run()

    for path in (tmp_path / "pass2").rglob("*"):
        if path.is_file():
            assert TOKEN not in path.read_text(encoding="utf-8", errors="replace"), path
            assert "Authorization" not in path.read_text(encoding="utf-8", errors="replace")


async def test_an_error_message_containing_the_token_is_redacted(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = _Client(
        [_Response(200, {"errors": [{"message": f"bad credential {TOKEN} supplied"}]})]
    )
    state = await runner.run()
    assert state["status"] == "STOP"
    ledger = (tmp_path / "pass2/ledgers/request-ledger.jsonl").read_text(encoding="utf-8")
    assert TOKEN not in ledger
    assert "REDACTED" in ledger


async def test_a_raw_body_is_written_once_and_never_rewritten(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = _Client([ECHO])
    await runner.run()
    bodies = sorted((tmp_path / "pass2/raw").glob("*.body"))
    assert len(bodies) == 1
    assert bodies[0].stat().st_mode & 0o777 == 0o600


async def test_state_and_canonical_writes_leave_no_temporary_files(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1, 2, 3])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = _Client([ECHO])
    await runner.run()
    leftovers = [p.name for p in (tmp_path / "pass2").rglob(".*tmp-*")]
    assert leftovers == []


async def test_an_interrupted_run_leaves_a_resumable_checkpoint(tmp_path: Path) -> None:
    plan = list(range(1, 25))
    _pass1(tmp_path / "pass1", "v7p_0001", plan)

    class _Interrupt(_Client):
        async def post(self, url, **kwargs):
            if len(self.requests) == 2:
                raise KeyboardInterrupt
            return await super().post(url, **kwargs)

    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = _Interrupt([ECHO, ECHO, ECHO])
    with pytest.raises(KeyboardInterrupt):
        await runner.run()

    state = json.loads(
        (tmp_path / "pass2/manifests/state.json").read_text(encoding="utf-8")
    )
    assert state["accounts"]["v7p_0001"]["next_batch"] == 2

    resumed = _runner(tmp_path, [_Target(1)], [])
    resumed._http = _Client([ECHO])
    final = await resumed.run()
    assert final["status"] == "COMPLETE"


async def test_resume_refuses_a_corpus_collected_with_a_different_query(
    tmp_path: Path,
) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = _Client([ECHO])
    await runner.run()

    state_path = tmp_path / "pass2/manifests/state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["operation_document_sha256"] = "0" * 64
    state_path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(Pass2Error, match="different query document"):
        _runner(tmp_path, [_Target(1)], [])


def test_the_batch_size_cannot_be_changed_without_a_new_probe(tmp_path: Path) -> None:
    with pytest.raises(Pass2Error, match="batch size is fixed"):
        Pass2Runner(
            _Cohort([_Target(1)]),
            pass1_dir=tmp_path / "pass1",
            output_dir=tmp_path / "pass2",
            batch_size=4,
        )


def test_network_collection_requires_a_token(tmp_path: Path) -> None:
    with pytest.raises(Pass2Error, match="STRATZ_API_TOKEN"):
        Pass2Runner(
            _Cohort([_Target(1)]),
            pass1_dir=tmp_path / "pass1",
            output_dir=tmp_path / "pass2",
            network=True,
            token=None,
        )


async def test_an_offline_runner_makes_no_request(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    runner = Pass2Runner(
        _Cohort([_Target(1)]),
        pass1_dir=tmp_path / "pass1",
        output_dir=tmp_path / "pass2",
        network=False,
    )
    state = await runner.run()
    assert state["status"] == "STOP"
    assert list((tmp_path / "pass2/raw").glob("*.body")) == []


async def test_verify_reports_a_complete_corpus(tmp_path: Path) -> None:
    for position in (1, 2):
        _pass1(tmp_path / "pass1", f"v7p_{position:04d}", [1, 2, 3])
    cohort = _Cohort([_Target(1), _Target(2)])
    runner = _runner(tmp_path, cohort.targets, [])
    runner._http = _Client([ECHO, ECHO])
    await runner.run()

    report = verify(
        tmp_path / "pass2", pass1_dir=tmp_path / "pass1", cohort=cohort, limit=2
    )
    assert report["critical_findings"] == []
    assert report["complete"] is True
    assert report["canonical_documents"] == 2
    assert report["collected_matches"] == 6
    assert report["orphan_raw_bodies"] == 0
    assert report["operation_document_sha256"] == GET_DEEP_MATCH_BATCH.document_sha256


async def test_verify_flags_an_unfinished_account(tmp_path: Path) -> None:
    plan = list(range(1, 17))
    _pass1(tmp_path / "pass1", "v7p_0001", plan)
    cohort = _Cohort([_Target(1)])
    runner = _runner(tmp_path, cohort.targets, [], max_requests=1)
    runner._http = _Client([ECHO, ECHO])
    await runner.run()
    report = verify(
        tmp_path / "pass2", pass1_dir=tmp_path / "pass1", cohort=cohort, limit=1
    )
    assert report["complete"] is False
    assert report["accounts_not_terminal"] == 1


async def test_verify_detects_a_tampered_raw_body(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    cohort = _Cohort([_Target(1)])
    runner = _runner(tmp_path, cohort.targets, [])
    runner._http = _Client([ECHO])
    await runner.run()

    body = next((tmp_path / "pass2/raw").glob("*.body"))
    body.chmod(0o600)
    body.write_text('{"data": {"player": {"matches": []}}}', encoding="utf-8")
    report = verify(
        tmp_path / "pass2", pass1_dir=tmp_path / "pass1", cohort=cohort, limit=1
    )
    assert any("digest" in finding for finding in report["critical_findings"])
    assert report["complete"] is False


async def test_verify_rejects_a_corpus_from_a_different_query_document(
    tmp_path: Path,
) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    cohort = _Cohort([_Target(1)])
    runner = _runner(tmp_path, cohort.targets, [])
    runner._http = _Client([ECHO])
    await runner.run()

    state_path = tmp_path / "pass2/manifests/state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["operation_document_sha256"] = "0" * 64
    state_path.write_text(json.dumps(state), encoding="utf-8")

    report = verify(
        tmp_path / "pass2", pass1_dir=tmp_path / "pass1", cohort=cohort, limit=1
    )
    assert any("query document" in finding for finding in report["critical_findings"])


async def test_the_manifest_records_the_contract_and_the_untouched_splits(
    tmp_path: Path,
) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = _Client([ECHO])
    await runner.run()
    manifest = json.loads(
        (tmp_path / "pass2/manifests/run-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["split"] == PASS2_SPLIT
    assert manifest["candidate_test_touched"] is False
    assert manifest["reserved_or_sealed_touched"] is False
    assert manifest["batch_size"] == PASS2_BATCH_SIZE
    assert manifest["operation"]["document_sha256"] == GET_DEEP_MATCH_BATCH.document_sha256
    assert manifest["raw_committed"] is False


# ---------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------


def test_supervisor_pause_arithmetic_never_returns_a_negative_delay() -> None:
    from datetime import UTC, datetime, timedelta

    from scripts.stratz_v7_pass2_supervisor import seconds_until

    now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    assert seconds_until((now + timedelta(seconds=90)).isoformat(), now=now) == 90
    assert seconds_until((now - timedelta(seconds=90)).isoformat(), now=now) == 0


def test_supervisor_rejects_a_naive_resume_timestamp() -> None:
    from scripts.stratz_v7_pass2_supervisor import seconds_until

    with pytest.raises(ValueError, match="timezone"):
        seconds_until("2026-09-04T12:00:00")


def test_supervisor_command_always_names_the_discovery_only_collector() -> None:
    import argparse

    from scripts.stratz_v7_pass2_supervisor import collect_command

    args = argparse.Namespace(
        freeze_dir=Path("/f"),
        source_frame=Path("/s"),
        pass1_dir=Path("/p1"),
        output_dir=Path("/o"),
        dotenv=Path(".env"),
        max_accounts=300,
    )
    command = collect_command(args)
    assert command[2] == "collect"
    assert "--acknowledge-network-collection" in command
    assert str(PASS2_TARGET_ACCOUNTS) in command


# ---------------------------------------------------------------------------
# Recovery from a torn write
# ---------------------------------------------------------------------------


async def test_a_body_written_without_its_ledger_row_does_not_abort_the_run(
    tmp_path: Path,
) -> None:
    # The crash window: body archived, process died before the ledger append.
    # On resume the ordinal repeats, and a write-once archive must not take the
    # whole collection down with a FileExistsError.
    _pass1(tmp_path / "pass1", "v7p_0001", [1, 2])
    runner = _runner(tmp_path, [_Target(1)], [])
    orphan = tmp_path / "pass2/raw/000001-GetDeepMatchBatch.body"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("{}", encoding="utf-8")

    runner._http = _Client([ECHO])
    state = await runner.run()
    assert state["status"] == "COMPLETE"
    bodies = sorted(p.name for p in (tmp_path / "pass2/raw").glob("*.body"))
    assert bodies == ["000001-GetDeepMatchBatch-r1.body", "000001-GetDeepMatchBatch.body"]
    ledgered = [row["raw_body_path"] for row in runner.ledger_rows]
    assert ledgered == ["raw/000001-GetDeepMatchBatch-r1.body"]


async def test_a_completed_account_with_a_deleted_canonical_file_is_repaired(
    tmp_path: Path,
) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", [1, 2, 3])
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = _Client([ECHO])
    await runner.run()

    canonical = tmp_path / "pass2/canonical/v7p_0001.json"
    canonical.unlink()

    repair = _runner(tmp_path, [_Target(1)], [])
    repair._http = _Client([])
    state = await repair.run()
    assert state["status"] == "COMPLETE"
    assert canonical.is_file()
    assert repair._http.requests == []


async def test_the_success_index_is_maintained_incrementally(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", list(range(1, 17)))
    runner = _runner(tmp_path, [_Target(1)], [])
    runner._http = _Client([ECHO, ECHO])
    await runner.run()
    assert len(runner._success_index()) == 2

    resumed = _runner(tmp_path, [_Target(1)], [])
    assert len(resumed._success_index()) == 2


async def test_a_paused_run_still_writes_an_inspectable_manifest(tmp_path: Path) -> None:
    _pass1(tmp_path / "pass1", "v7p_0001", list(range(1, 25)))
    runner = _runner(tmp_path, [_Target(1)], [], max_requests=1)
    runner._http = _Client([ECHO, ECHO, ECHO])
    state = await runner.run()
    assert state["status"] == "PARTIAL_PAUSED"
    manifest = json.loads(
        (tmp_path / "pass2/manifests/run-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "PARTIAL_PAUSED"
    assert manifest["physical_attempts"] == 1

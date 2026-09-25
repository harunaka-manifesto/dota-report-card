from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.stratz.queries import GET_PARSED_ACQUISITION_BATCH, GET_PLAYER_HISTORY_PAGE

from legacy.scripts.stratz_v7_corpus_runner import (
    EXPECTED_FRAME_COUNT,
    EXPECTED_PARSED_COUNTS,
    EXPECTED_SPLIT_COUNTS,
    CohortTarget,
    CorpusRunner,
    FrozenCohort,
    PauseRun,
    RateController,
    RunnerError,
    StopRun,
    canonicalize_history,
    dedupe_rows,
    load_frozen_cohort,
    load_stratz_token,
    normalize_history_page,
    normalize_parsed_batch,
    pseudonymize_account,
    safe_response_headers,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "stratz" / "get_player_history_page.json"
ACCOUNT_ID = 123456789


def _fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _cohort(*, parsed_subset: bool = True) -> FrozenCohort:
    target = CohortTarget(
        pseudonym="v7p_fixture",
        source_position=7,
        split="DISCOVERY",
        parsed_subset=parsed_subset,
        parsed_order=0 if parsed_subset else None,
        account_id=ACCOUNT_ID,
    )
    return FrozenCohort(
        freeze_dir=Path("fixture-freeze"),
        source_frame_path=Path("fixture-frame"),
        salt=b"0" * 32,
        split_digest="split-digest",
        plan_digest="plan-digest",
        frame_digest="frame-digest",
        targets=(target,),
    )


def _synthetic_frozen_artifacts(tmp_path: Path) -> tuple[Path, Path]:
    salt = b"synthetic-v7-salt-012345678901234"[:32]
    frame_path = tmp_path / "source-frame.json"
    frame = {
        "schema_version": "synthetic-source-frame",
        "adaptive_top_up": False,
        "selection": "/publicmatches HMAC synthetic fixture",
        "positive_public_account_count": EXPECTED_FRAME_COUNT,
        "ranked_frame": [
            {"account_id": 1_000_000 + position, "position": position}
            for position in range(EXPECTED_FRAME_COUNT)
        ],
    }
    frame_path.write_text(json.dumps(frame), encoding="utf-8")
    freeze_dir = tmp_path / "freeze"
    split_path = freeze_dir / "manifests/split-manifest.json"
    plan_path = freeze_dir / "manifests/corpus-plan.json"
    (freeze_dir / "manifests").mkdir(parents=True)
    (freeze_dir / "salt.bin").write_bytes(salt)
    members: list[dict[str, Any]] = []
    position = 0
    for split, count in EXPECTED_SPLIT_COUNTS.items():
        parsed_count = EXPECTED_PARSED_COUNTS[split]
        for index in range(count):
            members.append(
                {
                    "pseudonym": pseudonymize_account(1_000_000 + position, salt),
                    "source_position": position,
                    "split": split,
                    "parsed_subset": index < parsed_count,
                    "parsed_subset_order": index if index < parsed_count else None,
                }
            )
            position += 1
    split_path.write_text(
        json.dumps(
            {
                "split_counts": EXPECTED_SPLIT_COUNTS,
                "parsed_subset_counts": EXPECTED_PARSED_COUNTS,
                "members": members,
            }
        ),
        encoding="utf-8",
    )
    plan_path.write_text(
        json.dumps(
            {
                "split_manifest_sha256": hashlib.sha256(split_path.read_bytes()).hexdigest(),
                "split_counts": EXPECTED_SPLIT_COUNTS,
                "parsed_subset_counts": EXPECTED_PARSED_COUNTS,
                "pack_registry_check": {
                    "packs": [
                        {
                            "operation": GET_PLAYER_HISTORY_PAGE.name,
                            "operation_sha256": GET_PLAYER_HISTORY_PAGE.document_sha256,
                            "operation_version": GET_PLAYER_HISTORY_PAGE.version,
                        },
                        {
                            "operation": GET_PARSED_ACQUISITION_BATCH.name,
                            "operation_sha256": GET_PARSED_ACQUISITION_BATCH.document_sha256,
                            "operation_version": GET_PARSED_ACQUISITION_BATCH.version,
                        },
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    return freeze_dir, frame_path


def _history_payload() -> dict[str, Any]:
    payload = _fixture()
    payload["data"]["player"]["matches"] = payload["data"]["player"]["matches"][:1]
    return payload


def _parsed_payload() -> dict[str, Any]:
    payload = _fixture()
    match = copy.deepcopy(payload["data"]["player"]["matches"][0])
    match.update(
        {
            "radiantKills": [1],
            "direKills": [2],
            "radiantNetworthLeads": [0, 20],
            "bottomLaneOutcome": "TIE",
            "midLaneOutcome": "RADIANT_VICTORY",
            "topLaneOutcome": "DIRE_VICTORY",
        }
    )
    match["players"][0]["stats"] = {
        "killEvents": [{"time": 10}],
        "assistEvents": [],
        "itemPurchases": [{"time": 20, "itemId": 1}],
    }
    payload["data"]["player"]["matches"] = [match]
    return payload


async def _no_sleep(_delay: float) -> None:
    return None


def test_token_loader_and_safe_headers_do_not_leak_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("STRATZ_API_TOKEN=fixture-token\nUNRELATED=do-not-load\n", encoding="utf-8")
    monkeypatch.delenv("STRATZ_API_TOKEN", raising=False)
    assert load_stratz_token(dotenv) == "fixture-token"
    assert "STRATZ_API_TOKEN" not in __import__("os").environ
    assert safe_response_headers(
        {"Authorization": "Bearer fixture-token", "Set-Cookie": "private", "RateLimit-Limit": "8"}
    ) == {"RateLimit-Limit": "8"}


def test_frozen_cohort_excludes_reserved_and_sealed_members(tmp_path: Path) -> None:
    freeze_dir, frame_path = _synthetic_frozen_artifacts(tmp_path)
    cohort = load_frozen_cohort(freeze_dir, source_frame_path=frame_path, strict=False)
    assert len(cohort.targets) == 900
    assert len(cohort.parsed_targets) == 256
    assert {target.split for target in cohort.targets} == {"DISCOVERY", "CANDIDATE_TEST"}
    assert not any(target.split in {"CALIBRATION_RESERVED", "SEALED_VALIDATION"} for target in cohort.targets)


def test_history_normalization_preserves_native_role_position_lane() -> None:
    normalized = normalize_history_page(
        _history_payload(),
        account_id=ACCOUNT_ID,
        pseudonym="v7p_fixture",
        split="DISCOVERY",
        source_position=7,
        window_start=1_999_900_000,
        window_end=2_000_100_000,
    )
    player = normalized["rows"][0]["player"]
    assert (player["role_native"], player["position_native"], player["lane_native"]) == (
        "HARD_SUPPORT",
        "POSITION_5",
        "SAFE_LANE",
    )
    assert "roleBasic" not in json.dumps(normalized)


def test_parsed_normalization_requires_requested_ids_and_stats() -> None:
    normalized = normalize_parsed_batch(
        _parsed_payload(),
        account_id=ACCOUNT_ID,
        requested_ids=(9_000_000_001,),
        pseudonym="v7p_fixture",
        split="DISCOVERY",
        source_position=7,
    )
    assert normalized["rows"][0]["player"]["stats"]["item_purchases"][0]["item_id"] == 1
    broken = _parsed_payload()
    broken["data"]["player"]["matches"][0]["players"][0]["stats"] = None
    with pytest.raises(RunnerError):
        normalize_parsed_batch(
            broken,
            account_id=ACCOUNT_ID,
            requested_ids=(9_000_000_001,),
            pseudonym="v7p_fixture",
            split="DISCOVERY",
            source_position=7,
        )


def test_dedupe_rows_keeps_one_match_and_counts_duplicates() -> None:
    first = {"match_id": 1, "started_at": 10, "player": {"hero_id": 1}}
    second = {"match_id": 1, "started_at": 10, "duration_seconds": 100, "player": {"hero_id": 1}}
    rows, duplicates = dedupe_rows((first, second))
    assert duplicates == 1
    assert rows == [second]


def test_history_window_keeps_inclusive_boundaries_and_drops_outside_rows() -> None:
    page = normalize_history_page(
        _history_payload(),
        account_id=ACCOUNT_ID,
        pseudonym="v7p_fixture",
        split="DISCOVERY",
        source_position=7,
        window_start=1_999_900_000,
        window_end=2_000_100_000,
    )
    row = copy.deepcopy(page["rows"][0])
    row["started_at"] = 1_999_900_000
    outside = copy.deepcopy(row)
    outside["match_id"] = 2
    outside["started_at"] = 1_999_899_999
    result = canonicalize_history(
        [{"profile": page["profile"], "rows": [row, outside]}],
        pseudonym="v7p_fixture",
        source_position=7,
        split="DISCOVERY",
        window_start=1_999_900_000,
        window_end=2_000_100_000,
        completeness="complete",
    )
    assert [item["match_id"] for item in result["rows"]] == [9_000_000_001]


def test_rate_windows_and_daily_cap_pause_without_network() -> None:
    controller = RateController(sleep=_no_sleep)
    with pytest.raises(PauseRun, match="daily cap"):
        __import__("asyncio").run(controller.before_attempt(9_000))
    controller.observe({"RateLimit-Limit-Second": "3"})
    with pytest.raises(StopRun, match="changed"):
        controller.observe({"RateLimit-Limit-Second": "4"})


@pytest.mark.asyncio
async def test_zero_network_default_writes_no_request_rows(tmp_path: Path) -> None:
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        runner = CorpusRunner(_cohort(), output_dir=tmp_path, http_client=http, sleep=_no_sleep)
        result = await runner.run()
    assert result["status"] == "OFFLINE_VALIDATED"
    assert calls == 0
    assert runner.ledger_rows == []


@pytest.mark.asyncio
async def test_live_run_archives_immutable_responses_and_resume_reuses_them(tmp_path: Path) -> None:
    requests: list[dict[str, Any]] = []
    history_payload = _history_payload()
    history_payload["data"]["player"]["steamAccount"]["isStratzPublic"] = False

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        if body["operationName"] == GET_PLAYER_HISTORY_PAGE.name:
            return httpx.Response(200, json=history_payload)
        return httpx.Response(200, json=_parsed_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        runner = CorpusRunner(
            _cohort(),
            output_dir=tmp_path,
            token="fixture-token",
            network=True,
            http_client=http,
            sleep=_no_sleep,
        )
        runner.state["window"] = {
            "start_timestamp": 1_999_900_000,
            "end_timestamp": 2_000_100_000,
            "days": 365,
        }
        runner._save_state()
        result = await runner.run()
    assert result["status"] == "COMPLETE"
    assert [body["operationName"] for body in requests] == [
        GET_PLAYER_HISTORY_PAGE.name,
        GET_PARSED_ACQUISITION_BATCH.name,
    ]
    assert runner.reconcile()["physical_attempts"] == 2
    assert len(list((tmp_path / "raw").glob("*.json"))) == 2
    manifest = json.loads((tmp_path / "manifests/run-manifest.json").read_text())
    assert manifest["ledger"]["reconciled"] is True
    assert manifest["ledger"]["physical_attempts"] == manifest["ledger"]["successful_immutable_requests"]
    assert "fixture-token" not in (tmp_path / "ledgers/request-ledger.jsonl").read_text()

    async def should_not_call(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("successful immutable request was repeated")

    async with httpx.AsyncClient(transport=httpx.MockTransport(should_not_call)) as http:
        resumed = CorpusRunner(
            _cohort(),
            output_dir=tmp_path,
            token="fixture-token",
            network=True,
            http_client=http,
            sleep=_no_sleep,
        )
        payload, metadata = await resumed.request(
            GET_PLAYER_HISTORY_PAGE,
            {
                "steamAccountId": ACCOUNT_ID,
                "startDateTime": int(runner.state["window"]["start_timestamp"]),
                "endDateTime": int(runner.state["window"]["end_timestamp"]),
                "take": 100,
                "skip": 0,
            },
        )
    assert payload["data"]["player"]["steamAccountId"] == ACCOUNT_ID
    assert metadata["cache_hit"] is True
    assert len(resumed.ledger_rows) == 2
    body_path = tmp_path / str(resumed.ledger_rows[0]["raw_body_path"])
    body_path.write_bytes(body_path.read_bytes() + b" ")
    with pytest.raises(RunnerError, match="hash mismatch"):
        await resumed.request(
            GET_PLAYER_HISTORY_PAGE,
            {
                "steamAccountId": ACCOUNT_ID,
                "startDateTime": int(runner.state["window"]["start_timestamp"]),
                "endDateTime": int(runner.state["window"]["end_timestamp"]),
                "take": 100,
                "skip": 0,
            },
        )


@pytest.mark.asyncio
async def test_parsed_acquisition_advances_by_batch_size(tmp_path: Path) -> None:
    match_ids = list(range(9_000_000_001, 9_000_000_018))
    calls: list[list[int]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requested = json.loads(request.content)["variables"]["matchIds"]
        calls.append(requested)
        template = _parsed_payload()["data"]["player"]["matches"][0]
        matches = []
        for match_id in requested:
            match = copy.deepcopy(template)
            match["id"] = match_id
            matches.append(match)
        payload = _parsed_payload()
        payload["data"]["player"]["matches"] = matches
        return httpx.Response(200, json=payload)

    cohort = _cohort()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        runner = CorpusRunner(
            cohort,
            output_dir=tmp_path,
            token="fixture-token",
            network=True,
            http_client=http,
            sleep=_no_sleep,
        )
        target = cohort.targets[0]
        runner._history_account_state(target)["profile"] = {"is_anonymous": False, "is_public": False}
        parsed_state = runner._parsed_account_state(target)
        parsed_state["match_ids"] = match_ids
        parsed_state["batch_count"] = 3
        await runner._acquire_parsed(target)

    assert [len(batch) for batch in calls] == [8, 8, 1]
    assert parsed_state["next_batch"] == 17
    assert parsed_state["status"] == "complete"


@pytest.mark.asyncio
async def test_auth_failure_is_redacted_and_recorded_as_one_physical_attempt(tmp_path: Path) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, content=b"token=fixture-token", headers={"Authorization": "bad"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        runner = CorpusRunner(
            _cohort(parsed_subset=False),
            output_dir=tmp_path,
            token="fixture-token",
            network=True,
            http_client=http,
            max_retries=3,
            sleep=_no_sleep,
        )
        with pytest.raises(StopRun, match="authentication"):
            await runner.request(GET_PLAYER_HISTORY_PAGE, {"steamAccountId": ACCOUNT_ID})
    assert len(runner.ledger_rows) == 1
    assert "fixture-token" not in (tmp_path / "ledgers/request-ledger.jsonl").read_text()
    assert "fixture-token" not in "".join(path.read_text(errors="ignore") for path in (tmp_path / "raw").glob("*"))


@pytest.mark.asyncio
async def test_graphql_partial_error_fails_closed_after_archival(tmp_path: Path) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": {"player": {"matches": []}},
                "errors": [{"message": "partial response"}],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        runner = CorpusRunner(
            _cohort(parsed_subset=False),
            output_dir=tmp_path,
            token="fixture-token",
            network=True,
            http_client=http,
            sleep=_no_sleep,
        )
        with pytest.raises(StopRun, match="GraphQL error"):
            await runner.request(GET_PLAYER_HISTORY_PAGE, {"steamAccountId": ACCOUNT_ID})
    assert len(runner.ledger_rows) == 1
    assert runner.ledger_rows[0]["error_kind"] == "graphql_error"
    assert runner.ledger_rows[0]["immutable_success"] is False

    calls = 0

    async def recovery_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_history_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(recovery_handler)) as http:
        resumed = CorpusRunner(
            _cohort(parsed_subset=False),
            output_dir=tmp_path,
            token="fixture-token",
            network=True,
            http_client=http,
            sleep=_no_sleep,
        )
        payload, metadata = await resumed.request(
            GET_PLAYER_HISTORY_PAGE,
            {"steamAccountId": ACCOUNT_ID},
        )
    assert calls == 1
    assert metadata["cache_hit"] is False
    assert payload["data"]["player"]["steamAccountId"] == ACCOUNT_ID
    assert len(resumed.ledger_rows) == 2
    assert resumed.ledger_rows[1]["immutable_success"] is True


@pytest.mark.asyncio
async def test_rate_limit_retry_is_counted_as_two_physical_attempts(tmp_path: Path) -> None:
    responses = [
        httpx.Response(429, json={"error": "slow down"}, headers={"Retry-After": "0"}),
        httpx.Response(200, json=_history_payload()),
    ]

    async def handler(_request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        runner = CorpusRunner(
            _cohort(parsed_subset=False),
            output_dir=tmp_path,
            token="fixture-token",
            network=True,
            http_client=http,
            max_retries=1,
            sleep=_no_sleep,
        )
        payload, metadata = await runner.request(GET_PLAYER_HISTORY_PAGE, {"steamAccountId": ACCOUNT_ID})
    assert payload["data"]["player"]["steamAccountId"] == ACCOUNT_ID
    assert metadata["physical_attempts"] == 2
    assert [row["physical_ordinal"] for row in runner.ledger_rows] == [1, 2]
    assert runner.ledger_rows[0]["http_status"] == 429
    assert runner.ledger_rows[0]["retrying"] is True
    assert runner.reconcile()["physical_attempts"] == 2


def test_forbidden_field_fails_closed() -> None:
    payload = _history_payload()
    payload["data"]["player"]["matches"][0]["players"][0]["roleBasic"] = "CORE"
    with pytest.raises(StopRun, match="forbidden"):
        normalize_history_page(
            payload,
            account_id=ACCOUNT_ID,
            pseudonym="v7p_fixture",
            split="DISCOVERY",
            source_position=7,
            window_start=1_999_900_000,
            window_end=2_000_100_000,
        )

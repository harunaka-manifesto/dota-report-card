from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.stratz.queries import (
    FIND_SHORT_PARSED_TRAJECTORY,
    GET_SHORT_PARSED_TRAJECTORY,
    PROBE_PARSED_AVAILABILITY,
    PROBE_PARSED_CORE_BATCH_FALLBACK,
    PROBE_PARSED_EVIDENCE_BATCH,
    STRATZ_OPERATIONS,
    V7_PARSED_SUBTYPE_SHAPE_SENTINEL,
    V7_SCHEMA_SENTINEL,
)

from scripts.stratz_v7_live_microprobe import (
    SUBTYPE_ALIASES,
    MicroprobeRunner,
    extract_complexity,
    is_complexity_failure,
    load_stratz_token,
    planned_batch_sizes,
    redact_bytes,
    safe_response_headers,
    summarize_parsed_batch,
    validate_schema_sentinel,
    validate_subtype_sentinel,
)


def test_dotenv_loader_reads_only_the_requested_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("STRATZ_API_TOKEN=fixture-token\nOTHER_SETTING=should-not-load\n", encoding="utf-8")
    monkeypatch.delenv("STRATZ_API_TOKEN", raising=False)
    monkeypatch.delenv("OTHER_SETTING", raising=False)

    assert load_stratz_token(dotenv) == "fixture-token"
    assert "STRATZ_API_TOKEN" not in os.environ
    assert "OTHER_SETTING" not in os.environ


def test_redaction_and_safe_header_filtering() -> None:
    assert redact_bytes(b"token=fixture-token", "fixture-token") == b"token=[REDACTED]"
    safe = safe_response_headers(
        {
            "Authorization": "Bearer fixture-token",
            "Set-Cookie": "session=private",
            "RateLimit-Limit": "8;w=1",
            "Retry-After": "1",
            "X-Request-ID": "request-id",
        }
    )
    assert safe == {
        "RateLimit-Limit": "8;w=1",
        "Retry-After": "1",
        "X-Request-ID": "request-id",
    }


def test_research_operations_are_registered_and_digest_stable() -> None:
    operations = (
        V7_SCHEMA_SENTINEL,
        V7_PARSED_SUBTYPE_SHAPE_SENTINEL,
        PROBE_PARSED_EVIDENCE_BATCH,
        PROBE_PARSED_CORE_BATCH_FALLBACK,
        FIND_SHORT_PARSED_TRAJECTORY,
        GET_SHORT_PARSED_TRAJECTORY,
        PROBE_PARSED_AVAILABILITY,
    )
    assert all(STRATZ_OPERATIONS[operation.name] is operation for operation in operations)
    assert len({operation.document_sha256 for operation in operations}) == len(operations)
    assert all("Authorization" not in operation.document for operation in operations)


def test_batch_plan_stops_at_locally_available_size() -> None:
    assert planned_batch_sizes(3) == ()
    assert planned_batch_sizes(4) == (4,)
    assert planned_batch_sizes(8) == (4, 8)
    assert planned_batch_sizes(16) == (4, 8, 16)


def test_schema_and_subtype_decisions_are_fail_closed() -> None:
    schema_payload = {
        "data": {
            alias: {"kind": "OBJECT", "name": alias}
            for alias in (
                "match",
                "matchPlayer",
                "playerStats",
                "playerPlayback",
                "matchPlayback",
                "player",
                "matchesRequest",
            )
        }
    }
    ok, details = validate_schema_sentinel(schema_payload)
    assert ok is True
    assert details["required_types"] == 7
    broken = dict(schema_payload)
    broken["data"] = dict(schema_payload["data"])
    broken["data"]["match"] = None
    assert validate_schema_sentinel(broken)[0] is False

    subtype = {
        "data": {
        alias: None
        for alias in (
            "laneReport",
            "towerDeath",
            "pickBan",
            "farmDistribution",
            "locationReport",
            "actionReport",
            "heroDamageReport",
            "abilityCastReport",
            "inventoryReport",
            "killEvent",
            "deathEvent",
            "assistEvent",
            "wardEvent",
            "wardDestruction",
            "itemPurchase",
            "itemUsed",
            "buffEvent",
            "courierKill",
            "runeEvent",
            "eLane",
            "ePosition",
            "eRole",
            "eLaneOut",
            "eLeaver",
            "eLobby",
            "eMode",
            "eRune",
        )
        }
    }
    assert validate_subtype_sentinel(subtype)[0] is True
    del subtype["data"]["eRune"]
    assert validate_subtype_sentinel(subtype)[0] is False


def test_batch_summary_requires_stats_field_and_counts_non_null_stats() -> None:
    payload: dict[str, Any] = {
        "data": {
            "player": {
                "matches": [
                    {"id": 1, "players": [{"stats": {}}]},
                    {"id": 2, "players": [{"stats": None}]},
                ]
            }
        }
    }
    ok, summary = summarize_parsed_batch(payload, (1, 2))
    assert ok is False
    assert summary["stats_non_null_count"] == 1
    assert summary["stats_null_count"] == 1

    payload["data"]["player"]["matches"][1]["players"][0]["stats"] = {}
    ok, _summary = summarize_parsed_batch(payload, (1, 2))
    assert ok is True

    payload["data"]["player"]["matches"][0]["players"][0].pop("stats")
    ok, _summary = summarize_parsed_batch(payload, (1, 2))
    assert ok is False


def test_complexity_is_observed_but_never_estimated() -> None:
    payload = {
        "errors": [{"message": "Query too complex", "extensions": {"code": "COMPLEXITY"}}]
    }
    assert extract_complexity(payload, {}) is None
    assert is_complexity_failure(payload, "Query too complex") is True
    assert extract_complexity({"errors": [{"message": "Complexity is 123"}]}, {}) == 123


@pytest.mark.asyncio
async def test_runner_archives_redacted_response_and_ledger(tmp_path: Path) -> None:
    payload = {
        "data": {"player": None},
        "errors": [{"message": "token=fixture-token"}],
    }

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=payload,
            headers={"RateLimit-Limit": "8;w=1", "Authorization": "should-not-archive"},
        )

    async def no_sleep(_delay: float) -> None:
        return None

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        runner = MicroprobeRunner(
            "fixture-token",
            output_dir=tmp_path,
            http_client=http,
            max_retries=0,
            sleep=no_sleep,
        )
        result = await runner.request(V7_SCHEMA_SENTINEL, {})

    assert result["status"] == "failed"
    body_path = runner.run_dir / result["raw_response_paths"][0]
    header_path = runner.run_dir / result["response_header_paths"][0]
    ledger_path = runner.ledger_path
    assert "fixture-token" not in body_path.read_text(encoding="utf-8")
    assert "Authorization" not in header_path.read_text(encoding="utf-8")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
    assert ledger["operation"] == V7_SCHEMA_SENTINEL.name
    assert ledger["http_status"] == 200
    assert ledger["cache_hit"] is False
    assert ledger["cache_miss"] is True
    assert "fixture-token" not in ledger_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_runner_executes_only_the_prepared_ladder_and_records_economics(tmp_path: Path) -> None:
    schema = {
        "data": {
            alias: {"kind": "OBJECT", "name": alias}
            for alias in (
                "match",
                "matchPlayer",
                "playerStats",
                "playerPlayback",
                "matchPlayback",
                "player",
                "matchesRequest",
            )
        }
    }
    subtype = {"data": {alias: None for alias in SUBTYPE_ALIASES}}

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        operation = body["operationName"]
        if operation == V7_SCHEMA_SENTINEL.name:
            payload = schema
        elif operation == V7_PARSED_SUBTYPE_SHAPE_SENTINEL.name:
            payload = subtype
        else:
            ids = body["variables"]["matchIds"]
            payload = {
                "data": {
                    "player": {
                        "matches": [
                            {"id": match_id, "players": [{"stats": {}}]}
                            for match_id in ids
                        ]
                    }
                }
            }
        return httpx.Response(200, json=payload, headers={"RateLimit-Remaining": "7"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        runner = MicroprobeRunner(
            "fixture-token",
            output_dir=tmp_path,
            http_client=http,
            max_retries=0,
        )
        summary = await runner.run(
            account_id=99,
            match_ids=tuple(range(1, 17)),
            start_timestamp=1,
            end_timestamp=2,
        )

    assert summary["physical_calls"] == 5
    assert summary["successful_calls"] == 5
    assert summary["failed_calls"] == 0
    assert summary["largest_safe_batch"] == 16
    assert summary["largest_attempted_batch"] == 16
    assert summary["account_id_present"] is True
    assert summary["ledger"]["rows"] == 5

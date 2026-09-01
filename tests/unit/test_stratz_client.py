from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.core.config import Settings
from app.core.errors import (
    ProfileUnavailable,
    StratzChallengeError,
    StratzForbidden,
    StratzGraphQLError,
    StratzInvalidResponse,
    StratzPartialResponse,
    StratzSchemaDrift,
)
from app.stratz.client import StratzClient, parse_rate_limit_headers
from app.stratz.queries import GET_PLAYER_PROFILE

FIXTURE = Path(__file__).parents[1] / "fixtures" / "stratz" / "get_player_history_page.json"
ACCOUNT_ID = 123456789


def _payload() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text())


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "data_provider": "stratz",
        "stratz_api_token": "stratz-test-secret",
        "stratz_max_retries": 1,
    }
    values.update(overrides)
    return Settings(**values)


async def _no_sleep(_delay: float) -> None:
    return None


def _json_response(payload: Any, *, status_code: int = 200, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(status_code, json=payload, headers=headers)


@pytest.mark.asyncio
async def test_profile_request_uses_stratz_transport_contract() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _json_response({"data": {"player": _payload()["data"]["player"]}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = StratzClient(_settings(), http_client=http, sleep=_no_sleep)
        profile = await client.get_player_profile(ACCOUNT_ID)

    assert profile.steam_account_id == ACCOUNT_ID
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://api.stratz.com/graphql"
    assert request.headers["user-agent"] == "STRATZ_API"
    assert request.headers["authorization"] == "Bearer stratz-test-secret"
    assert request.headers["content-type"] == "application/json"
    body = json.loads(request.content)
    assert body["operationName"] == GET_PLAYER_PROFILE.name
    assert body["variables"] == {"steamAccountId": ACCOUNT_ID}
    assert body["query"] == GET_PLAYER_PROFILE.document


@pytest.mark.asyncio
async def test_graphql_partial_data_fails_closed_without_secret_leak() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return _json_response(
            {
                "data": {"player": _payload()["data"]["player"]},
                "errors": [{"message": "token=stratz-test-secret"}],
            }
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = StratzClient(_settings(), http_client=http, sleep=_no_sleep)
        with pytest.raises(StratzPartialResponse) as caught:
            await client.get_player_profile(ACCOUNT_ID)

    assert "stratz-test-secret" not in str(caught.value)
    assert "[REDACTED]" in str(caught.value)


@pytest.mark.asyncio
async def test_graphql_without_data_and_schema_errors_have_distinct_failures() -> None:
    async def no_data(_request: httpx.Request) -> httpx.Response:
        return _json_response({"errors": [{"message": "resolver failed"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(no_data)) as http:
        client = StratzClient(_settings(), http_client=http, sleep=_no_sleep)
        with pytest.raises(StratzGraphQLError):
            await client.get_player_profile(ACCOUNT_ID)

    async def schema_drift(_request: httpx.Request) -> httpx.Response:
        return _json_response(
            {"errors": [{"message": "Cannot query field deprecatedField"}]}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(schema_drift)) as http:
        client = StratzClient(_settings(), http_client=http, sleep=_no_sleep)
        with pytest.raises(StratzSchemaDrift):
            await client.get_player_profile(ACCOUNT_ID)


@pytest.mark.asyncio
async def test_invalid_json_and_html_challenge_are_provider_errors() -> None:
    async def invalid_json(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json", headers={"Content-Type": "text/plain"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(invalid_json)) as http:
        client = StratzClient(_settings(), http_client=http, sleep=_no_sleep)
        with pytest.raises(StratzInvalidResponse):
            await client.get_player_profile(ACCOUNT_ID)

    async def challenge(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            content=b"<!doctype html><html>challenge</html>",
            headers={"Content-Type": "text/html"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(challenge)) as http:
        client = StratzClient(_settings(), http_client=http, sleep=_no_sleep)
        with pytest.raises(StratzChallengeError):
            await client.get_player_profile(ACCOUNT_ID)

    async def forbidden(_request: httpx.Request) -> httpx.Response:
        return _json_response({"error": "forbidden"}, status_code=403)

    async with httpx.AsyncClient(transport=httpx.MockTransport(forbidden)) as http:
        client = StratzClient(_settings(), http_client=http, sleep=_no_sleep)
        with pytest.raises(StratzForbidden):
            await client.get_player_profile(ACCOUNT_ID)


@pytest.mark.asyncio
async def test_timeout_and_5xx_are_bounded_retries() -> None:
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("timed out")
        if calls == 2:
            return _json_response(
                {"error": "rate limited"}, status_code=429, headers={"Retry-After": "0"}
            )
        if calls == 3:
            return _json_response({"error": "temporary"}, status_code=503)
        return _json_response({"data": {"player": _payload()["data"]["player"]}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = StratzClient(_settings(stratz_max_retries=3), http_client=http, sleep=_no_sleep)
        profile = await client.get_player_profile(ACCOUNT_ID)

    assert profile.steam_account_id == ACCOUNT_ID
    assert calls == 4
    assert client.request_ledger.request_count == 4
    assert client.request_ledger.retry_count == 3
    assert client.request_ledger.status_counts == {"429": 1, "503": 1, "200": 1}


def test_rate_limit_headers_parse_live_and_structured_forms() -> None:
    snapshot = parse_rate_limit_headers(
        {
            "RateLimit-Limit": "8;w=1, 150;w=60, 1500;w=3600",
            "X-RateLimit-Remaining-Second": "7",
            "X-RateLimit-Reset-Second": "1",
            "X-RateLimit-Limit-Day": "15000",
        }
    )

    assert snapshot.limits == {"second": 8, "minute": 150, "hour": 1500, "day": 15000}
    assert snapshot.remaining == {"second": 7}
    assert 0 < snapshot.reset_delay() <= 1


@pytest.mark.asyncio
async def test_private_profile_is_not_normalized_as_empty_public_data() -> None:
    payload = _payload()
    payload["data"]["player"]["steamAccount"] = None

    async def handler(_request: httpx.Request) -> httpx.Response:
        return _json_response(payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = StratzClient(_settings(), http_client=http, sleep=_no_sleep)
        with pytest.raises(ProfileUnavailable):
            await client.get_player_profile(ACCOUNT_ID)


def _match_template(match_id: int, started_at: int, *, parsed: int | None = 2_000_000_000) -> dict[str, Any]:
    match = copy.deepcopy(_payload()["data"]["player"]["matches"][0])
    match["id"] = match_id
    match["startDateTime"] = started_at
    match["endDateTime"] = started_at + 1_800
    match["parsedDateTime"] = parsed
    return match


@pytest.mark.asyncio
async def test_history_paginates_dedupes_and_enforces_inclusive_window() -> None:
    end = 2_000_000_000
    start = end - 86_400
    first_page = [
        _match_template(
            9_000_000_100 + index,
            end - 60 * index,
            parsed=None if index == 1 else 2_000_000_000,
        )
        for index in range(100)
    ]
    duplicate = _match_template(9_000_000_101, end - 60, parsed=2_000_000_100)
    second_page = [duplicate, _match_template(9_000_000_999, start - 1)]
    skips: list[int] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        skip = body["variables"]["skip"]
        skips.append(skip)
        matches = first_page if skip == 0 else second_page
        page = copy.deepcopy(_payload())
        page["data"]["player"]["matches"] = matches
        return _json_response(page)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = StratzClient(_settings(stratz_max_retries=0), http_client=http, sleep=_no_sleep)
        history = await client.get_player_history(ACCOUNT_ID, days=1, window_end=end)

    assert skips == [0, 100]
    assert len(history.matches) == 100
    assert history.duplicate_match_count == 1
    assert history.matches[0].started_at == end
    assert history.matches[-1].started_at == end - (99 * 60)
    assert history.ledger.request_count == 2
    assert history.ledger.page_count == 2
    assert history.truncated is False


@pytest.mark.asyncio
async def test_history_empty_page_and_page_ceiling_are_explicit() -> None:
    calls = 0

    async def empty_handler(_request: httpx.Request) -> httpx.Response:
        page = copy.deepcopy(_payload())
        page["data"]["player"]["matches"] = []
        return _json_response(page)

    async with httpx.AsyncClient(transport=httpx.MockTransport(empty_handler)) as http:
        client = StratzClient(_settings(stratz_max_retries=0), http_client=http, sleep=_no_sleep)
        history = await client.get_player_history(ACCOUNT_ID, days=1, window_end=2_000_000_000)
    assert history.matches == ()
    assert history.truncated is False
    assert history.ledger.page_count == 1

    async def full_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        page = copy.deepcopy(_payload())
        page["data"]["player"]["matches"] = [
            _match_template(9_000_001_000 + index, 2_000_000_000 - index)
            for index in range(100)
        ]
        return _json_response(page)

    async with httpx.AsyncClient(transport=httpx.MockTransport(full_handler)) as http:
        client = StratzClient(
            _settings(stratz_max_retries=0, stratz_max_history_pages=1),
            http_client=http,
            sleep=_no_sleep,
        )
        history = await client.get_player_history(ACCOUNT_ID, days=1, window_end=2_000_000_000)
    assert calls == 1
    assert history.truncated is True
    assert history.ledger.request_count == 1


@pytest.mark.asyncio
async def test_missing_token_fails_before_network() -> None:
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _json_response({})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = StratzClient(_settings(stratz_api_token=None), http_client=http, sleep=_no_sleep)
        with pytest.raises(StratzForbidden):
            await client.get_player_profile(ACCOUNT_ID)
    assert calls == 0

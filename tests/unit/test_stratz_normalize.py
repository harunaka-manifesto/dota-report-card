from __future__ import annotations

import copy
import json
from pathlib import Path

from app.providers.base import HistoryWindow, RequestLedger
from app.stratz.models import StratzHistory, StratzHistoryPage
from app.stratz.normalize import normalize_stratz_history, normalize_stratz_page

FIXTURE = Path(__file__).parents[1] / "fixtures" / "stratz" / "get_player_history_page.json"
ACCOUNT_ID = 123456789


def _page() -> StratzHistoryPage:
    raw = json.loads(FIXTURE.read_text())
    return StratzHistoryPage.from_graphql(
        raw["data"], account_id=ACCOUNT_ID, skip=0, take=100
    )


def _history(page: StratzHistoryPage) -> StratzHistory:
    ledger = RequestLedger(request_count=1, success_count=1, page_count=1)
    return StratzHistory(
        profile=page.profile,
        matches=page.matches,
        pages=(page,),
        raw_pages=(page.raw_data,),
        ledger=ledger,
        window=HistoryWindow(start_timestamp=1_999_900_000, end_timestamp=2_000_000_000),
        fetched_at="2026-09-01T00:00:00+00:00",
        operation_name="GetPlayerHistoryPage",
        operation_version="1.0.0",
        operation_document_sha256="fixture-document-digest",
    )


def test_normalizer_preserves_native_role_position_and_lane_separately() -> None:
    page = _page()
    result = normalize_stratz_page(page, account_id=ACCOUNT_ID)

    hard_support = result[0]
    light_support = result[1]
    assert (hard_support.role, hard_support.position, hard_support.lane) == (
        "HARD_SUPPORT",
        "POSITION_5",
        "SAFE_LANE",
    )
    assert (light_support.role, light_support.position, light_support.lane) == (
        "LIGHT_SUPPORT",
        "POSITION_4",
        "OFF_LANE",
    )
    assert hard_support.role != "carry"
    assert light_support.role != "offlane"
    assert "role_hint" not in hard_support.as_dict()
    assert "lane_role" not in hard_support.as_dict()


def test_normalizer_keeps_provider_native_metadata_and_parsed_coverage() -> None:
    result = normalize_stratz_history(_history(_page()), account_id=ACCOUNT_ID)

    parsed, unparsed = result.matches
    assert parsed.game_version_id == 182
    assert parsed.game_mode_native == "ALL_PICK_RANKED"
    assert parsed.lobby_native == "RANKED"
    assert parsed.leaver_status_native == "NONE"
    assert parsed.is_parsed is True
    assert unparsed.is_parsed is False
    assert result.provenance.provider == "stratz"
    assert result.provenance.parsed_coverage == 0.5
    assert result.provenance.completeness == "complete"


def test_unknown_native_enum_is_retained_and_never_mapped_to_opendota_integer() -> None:
    raw = json.loads(FIXTURE.read_text())
    raw = copy.deepcopy(raw)
    raw["data"]["player"]["matches"][0]["players"][0]["role"] = "FUTURE_ROLE"
    page = StratzHistoryPage.from_graphql(
        raw["data"], account_id=ACCOUNT_ID, skip=0, take=100
    )
    result = normalize_stratz_page(page, account_id=ACCOUNT_ID)

    assert result[0].role == "FUTURE_ROLE"
    assert not isinstance(result[0].role, int)

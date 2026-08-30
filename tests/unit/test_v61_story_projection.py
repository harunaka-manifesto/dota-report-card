from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

import pytest
from app.api.story_payload_schemas_v61 import StoryPayloadV61Schema
from app.ingestion.summary_normalize import normalize_summary_rows
from app.player_analysis_v61.story_projection import (
    build_story_payload,
    story_input_sha256,
)
from app.player_analysis_v61.story_selector import select_story_matches

TAXONOMY_CHECKSUMS = {
    "factual_checksum": "56b0c0fb2f9f1e75d3649b655780197d12a845edb26ccb0d2645370b42e2cb89",
    "editorial_checksum": "394190d3a4c8b067b9eda04975d8d7c1b19092a9f1c9a39d46266bfec5533e0d",
}


def _timestamp(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp())


def _rows(count: int = 30) -> list[dict[str, object]]:
    return [
        {
            "match_id": index,
            "player_slot": 0,
            "radiant_win": True,
            "duration": 1_800,
            "game_mode": 1 if index % 2 else 2,
            "lobby_type": 0,
            "hero_id": 1,
            "start_time": _timestamp("2025-06-01T12:00:00+00:00"),
            "version": 1,
            "kills": index % 5,
            "deaths": 1,
            "assists": 2,
            "leaver_status": 0,
        }
        for index in range(1, count + 1)
    ]


def _finding(family: str, *, published: bool = True) -> dict[str, object]:
    evidence_refs = [f"{family}:evidence"]
    if family == "post_loss_response":
        evidence_refs.append("post_loss:123456789")
    return {
        "family": family,
        "published": published,
        "claim": f"{family} claim",
        "interpretation": f"{family} interpretation",
        "evidence_refs": evidence_refs,
        "confidence": "high",
        "semantic_outcome_key": "clean_transfer" if family == "transfer" else "one_loss_runback",
        "claim_contract": {
            "claim": f"{family} claim",
            "evidence": f"{family} evidence",
            "interpretation": f"{family} interpretation",
            "recommendation": None,
            "alternatives": ["another explanation"],
            "verification": {
                "eligibility_games": 5,
                "primary_metric": "primary",
                "guardrail_metric": "guardrail",
                "causal": False,
                "abstention": "too early to tell",
            },
            "interaction": "open_deep",
            "copy_version": "free-dna-semantic-copy-6.1.0",
            "deep_handoff": {"cohort_reference": "cohort:v61:private"},
        },
    }


def _build(
    *, post_loss_published: bool = True, transfer_published: bool = True
) -> dict[str, Any]:
    normalized = normalize_summary_rows(_rows(), 123)
    selection = select_story_matches(normalized.matches)
    payload = build_story_payload(
        selection=selection,
        legacy_report={
            "findings": [
                _finding("post_loss_response", published=post_loss_published),
                _finding("transfer", published=transfer_published),
            ],
        },
        profile={"personaname": "Story Player", "account_id": 123},
        canonical_audit={"completeness": "complete"},
        window_start=_timestamp("2025-01-01T00:00:00+00:00"),
        window_end=_timestamp("2025-12-31T23:59:59+00:00"),
        hero_metadata={1: {"display_name": "Anti-Mage"}},
        hero_taxonomy_checksums=TAXONOMY_CHECKSUMS,
        internal_evidence={"post_loss": {"comparable_pair_count": 7}},
    )
    assert payload is not None
    return payload


def test_projection_is_none_below_story_activation_gate() -> None:
    normalized = normalize_summary_rows(_rows(29), 123)
    selection = select_story_matches(normalized.matches)

    payload = build_story_payload(
        selection=selection,
        legacy_report={"findings": []},
        profile=None,
        canonical_audit={"completeness": "complete"},
        window_start=_timestamp("2025-01-01T00:00:00+00:00"),
        window_end=_timestamp("2025-12-31T23:59:59+00:00"),
        hero_metadata={},
        hero_taxonomy_checksums=TAXONOMY_CHECKSUMS,
        internal_evidence={},
    )

    assert payload is None


def test_projection_is_strict_schema_compatible_and_projects_findings() -> None:
    payload = _build()
    assert payload is not None
    validated = StoryPayloadV61Schema.model_validate(payload)

    assert validated.universe.match_count == 30
    assert validated.universe.mode_counts.unranked_all_pick == 15
    assert validated.universe.mode_counts.unranked_captains_mode == 15
    assert validated.provenance.physical_history_requests == 1
    assert validated.provenance.detail_requests == 0
    assert validated.provenance.hero_taxonomy_factual_checksum == TAXONOMY_CHECKSUMS["factual_checksum"]
    assert validated.provenance.hero_taxonomy_editorial_checksum == TAXONOMY_CHECKSUMS["editorial_checksum"]
    assert validated.finding_slots.post_loss.available is True
    assert validated.finding_slots.post_loss.content is not None
    assert validated.finding_slots.post_loss.content.comparable_opportunities == 7
    assert validated.finding_slots.post_loss.content.evidence_refs == [
        "post_loss_response:evidence"
    ]
    assert validated.finding_slots.post_loss.content.claim_contract is not None
    assert "deep_handoff" not in validated.finding_slots.post_loss.content.claim_contract.model_dump()
    assert validated.finding_slots.transfer.available is True

    page_numbers = [
        item["page"] if isinstance(item, dict) else item for item in payload["page_manifest"]
    ]
    assert all(left < right for left, right in zip(page_numbers, page_numbers[1:], strict=False))
    page_by_module = {
        item["module"]: item["page"]
        for item in payload["page_manifest"]
        if isinstance(item, dict) and item.get("module") is not None
    }
    assert page_by_module["transfer"] == 21
    assert page_by_module["hero_era_payoff"] < page_by_module["transfer"] < page_by_module["kills"]
    assert 13 < page_by_module["post_loss"] < page_by_module["hero_pool"]

    cards = payload["modules"]["card_collage"]["data"]["cards"]
    card_modules = [card["module"] for card in cards]
    assert card_modules == [card["module"] for card in payload["card_manifest"]]
    assert all(
        card["page"] < next_card["page"]
        for card, next_card in zip(cards, cards[1:], strict=False)
    )
    assert card_modules == [
        item["module"]
        for item in payload["page_manifest"]
        if isinstance(item, dict) and item.get("module") not in {None, "card_collage"}
    ]
    assert 25 not in page_numbers
    assert page_numbers[page_numbers.index(24) + 1] == 26
    assert "death_context" not in str(payload).casefold()
    assert "account_id" not in str(payload)


@pytest.mark.parametrize(
    ("post_loss_published", "transfer_published"),
    [(False, False), (False, True), (True, False), (True, True)],
)
def test_projection_preserves_all_finding_slot_availability_combinations(
    post_loss_published: bool,
    transfer_published: bool,
) -> None:
    payload = _build(
        post_loss_published=post_loss_published,
        transfer_published=transfer_published,
    )
    assert payload is not None

    expected = {
        "post_loss": (post_loss_published, "post_loss_response", 7),
        "transfer": (transfer_published, "transfer", None),
    }
    slots = payload["finding_slots"]
    assert isinstance(slots, dict)
    for slot_key, (published, family, comparable_opportunities) in expected.items():
        slot = slots[slot_key]
        assert isinstance(slot, dict)
        assert slot["available"] is published
        assert slot["family"] == family
        if not published:
            assert slot["content"] is None
            continue

        content = slot["content"]
        assert isinstance(content, dict)
        assert content["family"] == family
        assert content["claim"] == f"{family} claim"
        assert content["interpretation"] == f"{family} interpretation"
        assert content["comparable_opportunities"] == comparable_opportunities


def test_legacy_anonymous_placeholder_is_not_published_as_a_player_name() -> None:
    normalized = normalize_summary_rows(_rows(), 123)
    selection = select_story_matches(normalized.matches)
    payload = build_story_payload(
        selection=selection,
        legacy_report={"findings": []},
        profile={"personaname": "Anonymous player"},
        canonical_audit={"completeness": "complete"},
        window_start=_timestamp("2025-01-01T00:00:00+00:00"),
        window_end=_timestamp("2025-12-31T23:59:59+00:00"),
        hero_metadata={1: {"display_name": "Anti-Mage"}},
        hero_taxonomy_checksums=TAXONOMY_CHECKSUMS,
        internal_evidence={},
    )

    assert payload is not None
    assert payload["identity"]["display_name"] is None
    assert payload["modules"]["hello"]["copy_variant"].startswith("anonymous_")


def test_story_input_hash_ignores_identifiers_but_changes_story_facts() -> None:
    rows = _rows(2)
    changed_identifier = deepcopy(rows)
    changed_identifier[0]["match_id"] = 999_999
    changed_identifier[0]["account_id"] = 456
    assert story_input_sha256(rows) == story_input_sha256(changed_identifier)

    changed_fact = deepcopy(rows)
    changed_fact[0]["kills"] = 99
    assert story_input_sha256(rows) != story_input_sha256(changed_fact)

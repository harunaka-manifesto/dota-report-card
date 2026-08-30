from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from app.api.report_schemas import validate_free_dna_report
from app.api.story_payload_schemas_v61 import (
    StoryCombatRowV61Schema,
    StoryPayloadV61Schema,
    validate_story_privacy,
)
from app.player_analysis_v61.story_selector import MODE_MAP_SHA256


def _payload() -> dict[str, object]:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "v61" / "current-story-payload.json"
    return copy.deepcopy(json.loads(fixture_path.read_text(encoding="utf-8")))


def test_story_payload_is_strict_and_historical_reports_remain_optional() -> None:
    payload = StoryPayloadV61Schema.model_validate(_payload())
    assert payload.modules.match_count.data is not None

    missing_module = copy.deepcopy(_payload())
    del missing_module["modules"]["hello"]  # type: ignore[index]
    with pytest.raises(ValueError, match="hello"):
        StoryPayloadV61Schema.model_validate(missing_module)


def test_module_state_requires_explicit_null_data_for_omission() -> None:
    invalid = copy.deepcopy(_payload())
    invalid["modules"]["hours_in_matches"]["data"] = {  # type: ignore[index]
        "total_duration_seconds": None,
        "display_value": None,
        "display_unit": None,
        "hours_available": False,
        "coverage_numerator": 0,
        "coverage_denominator": 0,
        "coverage_ratio": 0.0,
    }
    with pytest.raises(ValueError, match="omitted story modules"):
        StoryPayloadV61Schema.model_validate(invalid)


def test_page_25_and_death_context_are_rejected() -> None:
    page_25 = copy.deepcopy(_payload())
    page_25["page_manifest"] = [1, 25]  # type: ignore[assignment]
    with pytest.raises(ValueError, match="Page 25"):
        StoryPayloadV61Schema.model_validate(page_25)

    object_page_25 = copy.deepcopy(_payload())
    object_page_25["page_manifest"] = [{"id": "page-25"}]  # type: ignore[assignment]
    with pytest.raises(ValueError, match="Page 25"):
        StoryPayloadV61Schema.model_validate(object_page_25)

    unavailable_module = copy.deepcopy(_payload())
    unavailable_module["page_manifest"] = [{"id": "hours_in_matches"}]  # type: ignore[assignment]
    with pytest.raises(ValueError, match="available or degraded"):
        StoryPayloadV61Schema.model_validate(unavailable_module)

    archetype_page = copy.deepcopy(_payload())
    archetype_page["page_manifest"] = [30]  # type: ignore[assignment]
    with pytest.raises(ValueError, match="archetype"):
        StoryPayloadV61Schema.model_validate(archetype_page)

    death_context = copy.deepcopy(_payload())
    death_context["modules"]["death_context"] = {}  # type: ignore[index]
    with pytest.raises(ValueError, match="death_context"):
        StoryPayloadV61Schema.model_validate(death_context)


def test_story_privacy_rejects_private_identifier_keys() -> None:
    invalid = copy.deepcopy(_payload())
    invalid["identity"]["account_id"] = 42  # type: ignore[index]
    with pytest.raises(ValueError):
        StoryPayloadV61Schema.model_validate(invalid)

    with pytest.raises(ValueError, match="private reference"):
        validate_story_privacy({"evidence_refs": ["post_loss:123456789"]})


def test_story_provenance_binds_pinned_and_digest_checksums() -> None:
    payload = _payload()
    assert payload["provenance"]["mode_map_checksum"] == MODE_MAP_SHA256  # type: ignore[index]
    assert len(payload["provenance"]["story_input_sha256"]) == 64  # type: ignore[index]

    wrong_mode_map = copy.deepcopy(payload)
    wrong_mode_map["provenance"]["mode_map_checksum"] = "0" * 64  # type: ignore[index]
    with pytest.raises(ValueError, match="mode map checksum"):
        StoryPayloadV61Schema.model_validate(wrong_mode_map)

    for field, label in (
        ("story_input_sha256", "story input"),
        ("hero_taxonomy_factual_checksum", "hero taxonomy factual"),
        ("hero_taxonomy_editorial_checksum", "hero taxonomy editorial"),
    ):
        invalid = copy.deepcopy(payload)
        invalid["provenance"][field] = "A" * 64  # type: ignore[index]
        with pytest.raises(ValueError, match=label):
            StoryPayloadV61Schema.model_validate(invalid)


def test_optional_combat_hero_ids_must_be_positive() -> None:
    with pytest.raises(ValueError, match="greater than or equal to 1"):
        StoryCombatRowV61Schema.model_validate({"rank": 1, "hero_id": 0})


def test_archetype_interface_cannot_be_marked_ready_or_populated() -> None:
    invalid = copy.deepcopy(_payload())
    invalid["modules"]["archetype"]["data"]["production_ready"] = True  # type: ignore[index]
    with pytest.raises(ValueError):
        StoryPayloadV61Schema.model_validate(invalid)


def test_available_finding_slots_require_a_safe_claim_contract_projection() -> None:
    invalid = copy.deepcopy(_payload())
    invalid["finding_slots"]["transfer"] = {  # type: ignore[index]
        "available": True,
        "family": "transfer",
        "content": {
            "family": "transfer",
            "claim": "A published transfer claim.",
            "interpretation": "Its public interpretation.",
        },
    }
    with pytest.raises(ValueError, match="claim, interpretation, and claim contract"):
        StoryPayloadV61Schema.model_validate(invalid)

    private = copy.deepcopy(_payload())
    private["finding_slots"]["transfer"] = {  # type: ignore[index]
        "available": True,
        "family": "transfer",
        "content": {
            "family": "transfer",
            "claim": "A published transfer claim.",
            "interpretation": "Its public interpretation.",
            "claim_contract": {
                "deep_handoff": {"cohort_reference": "cohort:v61:private"}
            },
        },
    }
    with pytest.raises(ValueError, match="deep_handoff|private"):
        StoryPayloadV61Schema.model_validate(private)


def test_card_manifest_mirrors_cards_and_only_ships_available_modules() -> None:
    invalid = copy.deepcopy(_payload())
    invalid["modules"]["card_collage"] = {  # type: ignore[index]
        "state": "available",
        "reason": None,
        "copy_variant": None,
        "data": {
            "version": "free-story-cards-1.0.0",
            "cards": [{"id": "hours", "module": "hours_in_matches"}],
        },
    }
    invalid["card_manifest"] = ["hours"]
    with pytest.raises(ValueError, match="eligible shipped modules|available or degraded"):
        StoryPayloadV61Schema.model_validate(invalid)

    missing_page = copy.deepcopy(_payload())
    missing_page["page_manifest"].remove(8)  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="exactly match shipped modules"):
        StoryPayloadV61Schema.model_validate(missing_page)

    missing_card = copy.deepcopy(_payload())
    missing_card["modules"]["card_collage"]["data"]["cards"].pop()  # type: ignore[index,union-attr]
    missing_card["card_manifest"].pop()  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="exactly match eligible shipped modules"):
        StoryPayloadV61Schema.model_validate(missing_card)


def test_page_24_requires_the_page_26_bridge() -> None:
    invalid = copy.deepcopy(_payload())
    invalid["modules"]["deaths"] = {  # type: ignore[index]
        "state": "available",
        "reason": None,
        "copy_variant": "zero",
        "data": {"total": 0, "leading_hero": None, "individuals": []},
    }
    invalid["page_manifest"] = [1, 2, 5, 8, 9, 24, 32]  # type: ignore[assignment]
    death_card = {"id": "story-card-deaths", "module": "deaths", "page": 24}
    invalid["modules"]["card_collage"]["data"]["cards"].append(death_card)  # type: ignore[index,union-attr]
    invalid["card_manifest"].append(death_card)  # type: ignore[union-attr]

    with pytest.raises(ValueError, match="Page 24 must connect directly to Page 26"):
        StoryPayloadV61Schema.model_validate(invalid)


def test_v61_version_keys_are_all_or_none_and_preserve_historical_absence() -> None:
    # The report fixture is generated by the existing V6.1 tests; this small
    # assertion covers the public validator's absence-preserving return path.
    from test_free_dna_v61_contract import _generate

    report, _source = _generate()
    historical = copy.deepcopy(report)
    historical.pop("story_payload", None)
    for key in (
        "story_payload",
        "story_rules",
        "story_copy",
        "game_mode_map",
        "hero_taxonomy",
        "hero_metadata",
        "archetype_contract",
    ):
        historical["versions"].pop(key, None)
    validated = validate_free_dna_report(historical)
    assert "story_payload" not in validated
    assert all(
        key not in validated["versions"]
        for key in (
            "story_payload",
            "story_rules",
            "story_copy",
            "game_mode_map",
            "hero_taxonomy",
            "hero_metadata",
            "archetype_contract",
        )
    )

    partial = copy.deepcopy(historical)
    partial["versions"]["story_payload"] = "free-story-payload-1.0.0"
    with pytest.raises(ValueError, match="story_payload block"):
        validate_free_dna_report(partial)


def test_current_v61_report_accepts_the_full_additive_story_extension() -> None:
    from test_free_dna_v61_contract import _generate

    report, _source = _generate()
    report["story_payload"] = _payload()
    report["versions"].update(  # type: ignore[union-attr]
        {
            "story_payload": "free-story-payload-1.0.0",
            "story_rules": "free-story-rules-1.0.0",
            "story_copy": "free-story-copy-1.0.0",
            "game_mode_map": "opendota-mode-map-e7705ee",
            "hero_taxonomy": "hero-taxonomy-2026-08-16",
            "hero_metadata": "hero-knowledge-semantic-freeze-full-roster-v1",
            "archetype_contract": "free-archetype-interface-1.0.0",
        }
    )

    validated = validate_free_dna_report(report)
    assert validated["story_payload"]["version"] == "free-story-payload-1.0.0"  # type: ignore[index]

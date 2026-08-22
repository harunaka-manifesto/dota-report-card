from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.hero_knowledge.validate import validate_semantic_layer

ROOT = Path(__file__).parents[2]
DATA_ROOT = ROOT / "services/api/app/heroes/data"
SEMANTICS_PATH = DATA_ROOT / "semantics/full-roster-v1.json"
FACTUAL_PATH = DATA_ROOT / "factual/2026-08-16.json"
KNOWLEDGE_PATH = DATA_ROOT / "knowledge/hero-knowledge-semantic-freeze-full-roster-v1.json"
MANIFEST_PATH = DATA_ROOT / "hero-knowledge-manifest.json"


def _snapshot() -> dict:
    return json.loads(SEMANTICS_PATH.read_text(encoding="utf-8"))


def test_full_roster_semantics_resolve_to_the_canonical_127_ids() -> None:
    snapshot = _snapshot()
    factual = json.loads(FACTUAL_PATH.read_text(encoding="utf-8"))
    canonical_ids = {int(row["hero_id"]) for row in factual["heroes"]}

    assert len(canonical_ids) == 127
    assert (
        validate_semantic_layer(
            snapshot,
            canonical_ids,
            require_complete=True,
            repo_root=ROOT,
            strict_evidence=True,
        )
        == ()
    )
    assert snapshot["version"] == "hero-semantics-full-roster-v1"
    assert snapshot["review_status"] == "reviewed"
    assert len(snapshot["heroes"]) == 127
    assert all(row["review_status"] == "approved" for row in snapshot["heroes"])


def test_full_roster_fields_are_structured_and_keep_local_evidence_namespaces() -> None:
    snapshot = _snapshot()

    for row in snapshot["heroes"]:
        functions = row["functions"]
        assert functions["primary"] or functions["secondary"]
        assert set(row["capabilities"]) == set(functions["primary"] + functions["secondary"])
        assert set(row["demands"]) == set(snapshot["vocabulary"]["demands"])
        assert set(row["position_credibility"]) == {"1", "2", "3", "4", "5"}
        for section in ("capabilities", "demands"):
            for value in row[section].values():
                assert isinstance(value, dict)
                assert value["evidence_refs"]
                assert all(
                    ref.split(":", 1)[0] in {"editorial", "derived"}
                    for ref in value["evidence_refs"]
                )
        for section in ("strengths", "weaknesses", "teamfight_profile"):
            assert row[section]
            assert all(item["evidence_refs"] for item in row[section])
    assert snapshot["evidence_sources"]["valve"]["status"] == "unavailable"
    assert snapshot["evidence_sources"]["opendota"]["status"] == "unavailable"


def test_full_roster_validator_rejects_unknown_ids_and_unresolved_refs() -> None:
    snapshot = _snapshot()
    factual = json.loads(FACTUAL_PATH.read_text(encoding="utf-8"))
    canonical_ids = {int(row["hero_id"]) for row in factual["heroes"]}

    unknown = copy.deepcopy(snapshot)
    unknown["heroes"][0]["hero_id"] = 999999
    errors = validate_semantic_layer(
        unknown,
        canonical_ids,
        require_complete=True,
        repo_root=ROOT,
        strict_evidence=True,
    )
    assert "semantic.unknown_hero:999999" in errors
    assert "semantic.incomplete_canonical_roster" in errors

    malformed = copy.deepcopy(snapshot)
    malformed["heroes"][0]["demands"]["access"]["evidence_refs"] = [
        "editorial:not-a-real-file#strategy"
    ]
    errors = validate_semantic_layer(
        malformed,
        canonical_ids,
        require_complete=True,
        repo_root=ROOT,
        strict_evidence=True,
    )
    assert any("unresolved_ref:editorial:not-a-real-file#strategy" in error for error in errors)


def test_manifest_and_knowledge_snapshot_switch_to_full_roster() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    knowledge = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))

    assert (
        manifest["knowledge_path"] == "knowledge/hero-knowledge-semantic-freeze-full-roster-v1.json"
    )
    assert manifest["semantic_layer_path"] == "semantics/full-roster-v1.json"
    assert len(manifest["semantic_layer_sha256"]) == 64
    assert manifest["knowledge_version"] == "hero-knowledge-semantic-freeze-full-roster-v1"
    assert manifest["hero_count"] == 127
    assert knowledge["hero_count"] == 127
    assert knowledge["freeze"]["pilot_history_path"] == "semantics/pilot-v1.json"
    assert knowledge["sources"]["opendota"]["required"] is False
    assert all(row["editorial"]["review_status"] == "approved" for row in knowledge["heroes"])


def test_conflict_sweep_blocks_generic_keywords_from_core_semantics() -> None:
    factual = json.loads(FACTUAL_PATH.read_text(encoding="utf-8"))
    by_key = {row["key"]: row["hero_id"] for row in factual["heroes"]}
    by_id = {row["hero_id"]: row for row in _snapshot()["heroes"]}

    meepo = by_id[by_key["meepo"]]
    assert {"catch", "sustained_damage", "push"} <= set(
        meepo["functions"]["primary"] + meepo["functions"]["secondary"]
    )
    assert "forced_movement" not in meepo["functions"]["primary"] + meepo["functions"]["secondary"]
    assert "global_presence" not in meepo["functions"]["primary"] + meepo["functions"]["secondary"]

    techies = by_id[by_key["techies"]]
    techies_functions = techies["functions"]["primary"] + techies["functions"]["secondary"]
    assert {"initiation", "burst", "wave_clear"} <= set(techies_functions)
    assert "save" not in techies_functions

    marci = by_id[by_key["marci"]]
    assert "forced_movement" in marci["functions"]["primary"] + marci["functions"]["secondary"]

    chen = by_id[by_key["chen"]]
    chen_functions = chen["functions"]["primary"] + chen["functions"]["secondary"]
    assert {"sustain", "save", "push", "global_presence"} <= set(chen_functions)
    assert not {"mobility", "repositioning", "scaling"} & set(chen_functions)
    assert {"micro_intensive", "high_execution", "multi_unit_control"} <= set(
        chen["specialist_markers"]
    )


def test_truthfulness_sweep_rejects_negated_or_incidental_mechanics() -> None:
    factual = json.loads(FACTUAL_PATH.read_text(encoding="utf-8"))
    by_key = {row["key"]: row["hero_id"] for row in factual["heroes"]}
    by_id = {row["hero_id"]: row for row in _snapshot()["heroes"]}

    def functions(key: str) -> set[str]:
        row = by_id[by_key[key]]
        return set(row["functions"]["primary"] + row["functions"]["secondary"])

    assert not {"frontline", "scaling", "sustain"} & functions("nyx_assassin")
    assert not {"frontline", "wave_clear"} & functions("rubick")
    assert not {"burst", "catch"} & functions("abaddon")
    assert "catch" not in functions("lycan")
    assert "catch" not in functions("ringmaster")

    # These are the reviewer-identified generic displacement matches. The
    # remaining displacement records are explicit enemy/ally movement, not
    # projectile verbs, health swaps, rune pulls, or patch/stat prose.
    forced_movement_false_positives = {
        "phantom_assassin",
        "dazzle",
        "alchemist",
        "troll_warlord",
        "elder_titan",
        "terrorblade",
        "oracle",
        "arc_warden",
    }
    assert all("forced_movement" not in functions(key) for key in forced_movement_false_positives)

    save_false_positives = {
        "pudge",
        "lion",
        "viper",
        "dragon_knight",
        "furion",
        "dark_seer",
        "broodmother",
        "ancient_apparition",
        "visage",
        "medusa",
        "skywrath_mage",
        "ember_spirit",
        "earth_spirit",
        "pangolier",
        "grimstroke",
        "void_spirit",
        "mars",
    }
    assert all("save" not in functions(key) for key in save_false_positives)

    scaling_false_positives = {
        "drow_ranger",
        "tinker",
        "furion",
        "huskar",
        "brewmaster",
        "nyx_assassin",
        "wisp",
        "visage",
        "dark_willow",
        "hoodwink",
    }
    assert all("scaling" not in functions(key) for key in scaling_false_positives)

    # Charge-resource wording must not manufacture initiation, while the two
    # reviewed movement initiators remain explicit exceptions.
    charge_false_positives = {
        "mirana",
        "storm_spirit",
        "sniper",
        "skeleton_king",
        "templar_assassin",
        "clinkz",
        "ursa",
        "invoker",
        "broodmother",
        "treant",
        "visage",
        "ember_spirit",
        "hoodwink",
        "void_spirit",
        "ringmaster",
    }
    assert all("initiation" not in functions(key) for key in charge_false_positives)
    assert {"initiation"} <= functions("batrider")
    assert {"initiation"} <= functions("earth_spirit")

    assert {"global_presence"} <= functions("rattletrap")
    assert {"global_presence"} <= functions("furion")
    assert "multi_unit_control" in by_id[by_key["visage"]]["specialist_markers"]


def test_full_snapshot_provenance_does_not_claim_unavailable_sources() -> None:
    knowledge = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))

    for row in knowledge["heroes"]:
        confidence = row["provenance"]["confidence"]
        assert confidence["band"] == "unknown"
        assert all(
            not ref.startswith(("valve:", "opendota:")) for ref in confidence["derived_from"]
        )
        assert row["provenance"]["field_sources"]["mechanics"] == "unknown:local_factual_mechanics"
        assert row["provenance"]["field_sources"]["empirical"] == "unknown:opendota_unavailable"
        assert set(row["position_credibility"].values()) == {"unknown"}
        assert "patch-specific 1-5" in row["position_credibility_reason"]


def test_strict_semantic_validator_rejects_unavailable_source_refs() -> None:
    snapshot = _snapshot()
    factual = json.loads(FACTUAL_PATH.read_text(encoding="utf-8"))
    canonical_ids = {int(row["hero_id"]) for row in factual["heroes"]}
    mutated = copy.deepcopy(snapshot)
    ref = "valve:unavailable-local#mechanics"
    mutated["evidence_catalog"][ref] = {"namespace": "valve", "status": "unavailable"}
    capability = next(iter(mutated["heroes"][0]["capabilities"]))
    mutated["heroes"][0]["capabilities"][capability]["evidence_refs"] = [ref]
    errors = validate_semantic_layer(
        mutated,
        canonical_ids,
        require_complete=True,
        repo_root=ROOT,
        strict_evidence=True,
    )
    assert any("source_unavailable:valve:unavailable-local#mechanics" in error for error in errors)

from __future__ import annotations

import json
from pathlib import Path

from app.heroes.knowledge import (
    EMPIRICAL_SUPPORT_BANDS,
    FUNCTIONAL_JOBS,
    HERO_DEMAND_FAMILIES,
    JOB_GLOSSARY,
    SEMANTIC_BANDS,
    FullRosterHeroKnowledgeProvider,
    SnapshotHeroKnowledgeProvider,
    canonical_function_key,
)
from app.heroes.taxonomy import load_default_taxonomy


def test_generated_pilot_snapshot_implements_runtime_provider_contract() -> None:
    provider = SnapshotHeroKnowledgeProvider()

    assert provider.available is True
    assert provider.version == "hero-knowledge-semantic-freeze-pilot-v1"
    assert {entry.hero_id for entry in provider.entries} == {
        2,
        13,
        38,
        44,
        50,
        53,
        74,
        82,
        96,
        111,
    }
    assert provider.get(None) is None
    assert provider.get(999999) is None

    for entry in provider.entries:
        assert set(entry.primary_functions + entry.secondary_functions) <= set(FUNCTIONAL_JOBS)
        assert set(entry.demands) <= set(HERO_DEMAND_FAMILIES)
        assert set(entry.demands.values()) <= SEMANTIC_BANDS
        assert entry.empirical_support in EMPIRICAL_SUPPORT_BANDS
        assert entry.confidence in {"high", "medium", "low"}
        assert entry.provenance_versions["hero_knowledge"] == provider.version


def test_unknown_semantics_stay_explicit_in_the_adapter(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps(
            {
                "knowledge_version": "hero-knowledge-test",
                "heroes": [
                    {
                        "identity": {"hero_id": 2, "display_name": "Axe", "roles": ["offlane"]},
                        "functions": {"primary": ["initiation"], "secondary": []},
                        "demands": {"micro": "unknown"},
                        "capabilities": {"initiation": {"band": "high"}},
                        "empirical_support": "unknown",
                        "semantic_confidence": "high",
                        "editorial": {"review_status": "approved"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    hero = SnapshotHeroKnowledgeProvider(snapshot_path=snapshot).get(2)

    assert hero is not None
    assert hero.demands["micro"] == "unknown"
    assert hero.empirical_support == "unknown"
    assert 0.5 not in hero.demands.values()


def test_full_roster_provider_keeps_review_status_and_structural_coverage_explicit() -> None:
    provider = FullRosterHeroKnowledgeProvider(load_default_taxonomy())

    assert len(provider.entries) == 127
    reviewed = provider.get(2)
    structural = provider.get(1)
    assert reviewed is not None and reviewed.review_status in {"approved", "reviewed"}
    assert structural is not None and structural.review_status == "unreviewed"
    assert structural.confidence == "low"
    assert structural.provenance_versions["hero_semantics"] == provider.version


def test_legacy_function_aliases_cannot_leak_into_the_public_glossary() -> None:
    assert "teamfight" not in FUNCTIONAL_JOBS
    assert canonical_function_key("teamfight") == "fight_control"
    assert JOB_GLOSSARY["fight_control"]["public_label"] == "Fight control"

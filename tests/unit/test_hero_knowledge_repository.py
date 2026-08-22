from __future__ import annotations

import json
from pathlib import Path

from app.heroes.knowledge import HeroKnowledgeRepository


def test_runtime_repository_reads_version_and_hero(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    knowledge_path = data_root / "knowledge" / "hero-knowledge-test.json"
    knowledge_path.parent.mkdir(parents=True)
    knowledge_path.write_text(
        json.dumps(
            {
                "knowledge_version": "hero-knowledge-test",
                "heroes": [
                    {
                        "identity": {"hero_id": 2, "display_name": "Axe"},
                        "capabilities": {"initiation": {"band": "high"}},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (data_root / "hero-knowledge-manifest.json").write_text(
        json.dumps({"knowledge_path": "knowledge/hero-knowledge-test.json"}), encoding="utf-8"
    )

    repository = HeroKnowledgeRepository(data_root=data_root)

    assert repository.version() == "hero-knowledge-test"
    assert repository.get(2).name == "Axe"  # type: ignore[union-attr]
    assert repository.get(99) is None

"""Validate the checked-in factual/editorial hero taxonomy snapshot."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))

from app.heroes.taxonomy import load_default_taxonomy  # noqa: E402


def main() -> None:
    taxonomy = load_default_taxonomy()
    research_root = ROOT / "heroes_metadata"
    research_files = {
        path.relative_to(ROOT).as_posix()
        for path in research_root.glob("*.md")
    }
    referenced_files = {
        str((hero.provenance or {}).get("research_file"))
        for hero in taxonomy.heroes.values()
    }
    if len(research_files) != 127 or research_files != referenced_files:
        raise SystemExit("Hero taxonomy research-file coverage does not match the checked-in corpus")
    print(
        f"{taxonomy.version}: {len(taxonomy.heroes)} heroes, "
        f"factual={taxonomy.manifest['factual_version']}, "
        f"editorial={taxonomy.manifest['editorial_version']}"
    )


if __name__ == "__main__":
    main()

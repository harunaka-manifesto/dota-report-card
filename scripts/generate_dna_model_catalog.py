#!/usr/bin/env python3
"""Generate the active Free DNA model catalog from production registries."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.behavior.archetypes.registry import (  # noqa: E402
    ARCHETYPE_GROUP_REGISTRY,
    ARCHETYPE_REGISTRY_VERSION,
)
from app.behavior.dimensions import DIMENSION_DEFINITIONS  # noqa: E402
from app.behavior.elements.registry import (  # noqa: E402
    ELEMENT_REGISTRY,
    ELEMENT_REGISTRY_VERSION,
)
from app.behavior.patterns.registry import (  # noqa: E402
    PATTERN_REGISTRY,
    PATTERN_REGISTRY_VERSION,
)

CATALOG_PATH = ROOT / "docs" / "architecture" / "model-catalog.md"
BEGIN = "<!-- BEGIN GENERATED MODEL CATALOG -->"
END = "<!-- END GENERATED MODEL CATALOG -->"


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _list(values: object) -> str:
    if not values:
        return "—"
    return ", ".join(f"`{_cell(item)}`" for item in values)  # type: ignore[union-attr]


def _table(headers: tuple[str, ...], rows: list[tuple[object, ...]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend(
        "| " + " | ".join(_cell(value) for value in row) + " |"
        for row in rows
    )
    return lines


def render_generated_catalog() -> str:
    lines = [
        BEGIN,
        "## Registry versions",
        "",
        *_table(
            ("Registry", "Version", "Active count"),
            [
                ("Dimensions", "dimensions-1.0.0", len(DIMENSION_DEFINITIONS)),
                ("Free Elements", ELEMENT_REGISTRY_VERSION, len(ELEMENT_REGISTRY)),
                ("Free Patterns", PATTERN_REGISTRY_VERSION, len(PATTERN_REGISTRY)),
                ("Context Archetypes", ARCHETYPE_REGISTRY_VERSION, len(ARCHETYPE_GROUP_REGISTRY)),
            ],
        ),
        "",
        "## Dimensions",
        "",
        *_table(
            ("Key", "Label", "Question the layer answers"),
            [(item.key, item.label, item.description) for item in DIMENSION_DEFINITIONS],
        ),
        "",
        "## Free Elements",
        "",
        *_table(
            ("ID", "Key", "Dimension", "Axis", "Minimum sample", "Coverage", "Required capabilities"),
            [
                (
                    f"E{index:02d}",
                    item.key,
                    item.dimension_key,
                    f"{item.axis_left or '—'} → {item.axis_right or '—'}",
                    item.minimum_sample,
                    f"{item.minimum_coverage:.0%}",
                    _list(item.required_capabilities),
                )
                for index, item in enumerate(ELEMENT_REGISTRY.values(), start=1)
            ],
        ),
        "",
        "## Free Patterns",
        "",
        *_table(
            ("ID", "Key", "Kind", "Required Elements", "Optional Elements", "Deep diagnostic handoff"),
            [
                (
                    f"P{index:02d}",
                    item.key,
                    item.kind,
                    _list(item.required_elements),
                    _list(item.optional_elements),
                    _list(item.required_deep_elements),
                )
                for index, item in enumerate(PATTERN_REGISTRY.values(), start=1)
            ],
        ),
        "",
        "## Context Archetype groups",
        "",
        *_table(
            ("Group", "Required Elements", "Optional Patterns", "Finite labels"),
            [
                (
                    group.key,
                    _list(group.required_elements),
                    _list(group.optional_patterns),
                    _list(tuple(f"{item.key} — {item.label}" for item in group.prototypes)),
                )
                for group in ARCHETYPE_GROUP_REGISTRY.values()
            ],
        ),
        "",
        "## Product tier",
        "",
        *_table(
            ("Tier", "Active model surface", "Evidence boundary"),
            [
                (
                    "Free",
                    f"{len(ELEMENT_REGISTRY)} Elements · {len(PATTERN_REGISTRY)} Patterns · {len(ARCHETYPE_GROUP_REGISTRY)} context groups",
                    "One bounded summary-history read; no match-detail or replay-parse reads",
                ),
                (
                    "Deep Scan",
                    "Selected-match diagnostic families are a separate handoff",
                    "Explicit opt-in, bounded detail reads, and coverage gates",
                ),
            ],
        ),
        END,
    ]
    return "\n".join(lines) + "\n"


def _replace_generated_block(document: str, generated: str) -> str:
    start = document.find(BEGIN)
    end = document.find(END)
    if start < 0 or end < 0 or end < start:
        raise ValueError(f"{CATALOG_PATH} must contain both catalog markers")
    end += len(END)
    return document[:start] + generated.rstrip("\n") + document[end:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the catalog is stale")
    args = parser.parse_args()

    current = CATALOG_PATH.read_text(encoding="utf-8")
    expected = _replace_generated_block(current, render_generated_catalog())
    if args.check:
        if current != expected:
            print(f"{CATALOG_PATH} is stale; run: make dna-catalog")
            return 1
        print("dna-catalog: current")
        return 0
    CATALOG_PATH.write_text(expected, encoding="utf-8")
    print(f"updated {CATALOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

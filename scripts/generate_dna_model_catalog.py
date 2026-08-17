#!/usr/bin/env python3
"""Generate the active Free DNA catalog from production registries."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.behavior.elements.registry import ELEMENT_REGISTRY, ELEMENT_REGISTRY_VERSION  # noqa: E402
from app.behavior.patterns.registry import PATTERN_REGISTRY, PATTERN_REGISTRY_VERSION  # noqa: E402

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
    lines.extend("| " + " | ".join(_cell(value) for value in row) + " |" for row in rows)
    return lines


def render_generated_catalog() -> str:
    lines = [
        BEGIN,
        "## Registry versions",
        "",
        *_table(
            ("Registry", "Version", "Active count"),
            [
                ("Free Elements", ELEMENT_REGISTRY_VERSION, len(ELEMENT_REGISTRY)),
                ("Free Patterns", PATTERN_REGISTRY_VERSION, len(PATTERN_REGISTRY)),
            ],
        ),
        "",
        "## Free Elements",
        "",
        *_table(
            ("ID", "Key", "Label", "Axis", "Minimum sample", "Coverage"),
            [
                (
                    f"E{index:02d}",
                    item.key,
                    item.label,
                    f"{item.axis_left or '—'} → {item.axis_right or '—'}",
                    item.minimum_sample,
                    f"{item.minimum_coverage:.0%}",
                )
                for index, item in enumerate(ELEMENT_REGISTRY.values(), start=1)
            ],
        ),
        "",
        "## Free Patterns",
        "",
        *_table(
            ("ID", "Key", "Family", "Tier", "Required Elements", "Modifier Elements"),
            [
                (
                    f"P{index:02d}",
                    item.key,
                    item.family,
                    item.tier,
                    _list(item.required_elements),
                    _list(item.modifier_elements),
                )
                for index, item in enumerate(PATTERN_REGISTRY.values(), start=1)
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
                    f"{len(ELEMENT_REGISTRY)} Elements · {len(PATTERN_REGISTRY)} Patterns · Hero Portfolio",
                    "One bounded summary-history read; no match-detail or replay-parse reads",
                ),
                (
                    "Deep Scan",
                    "Explicit selected-match analysis",
                    "Separate opt-in budgets and coverage gates",
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

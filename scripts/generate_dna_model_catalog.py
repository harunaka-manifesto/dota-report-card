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
from app.player_analysis_v6.constants import FINDING_FAMILY_KEYS, PUBLIC_ELEMENT_KEYS  # noqa: E402
from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_CATALOG  # noqa: E402
from app.player_analysis_v61.supporting_signals import SUPPORTING_SIGNAL_CATALOG  # noqa: E402
from app.player_analysis_v61.versions import (  # noqa: E402
    SEMANTIC_OUTCOMES_VERSION,
    VERSION_SURFACES,
)

CATALOG_PATH = ROOT / "docs" / "architecture" / "model-catalog.md"
BEGIN = "<!-- BEGIN GENERATED MODEL CATALOG -->"
END = "<!-- END GENERATED MODEL CATALOG -->"


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _list(values: object) -> str:
    if not values:
        return "—"
    if not isinstance(values, (list, tuple, set, frozenset)):
        return f"`{_cell(values)}`"
    return ", ".join(f"`{_cell(item)}`" for item in values)


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
                ("V6.1 public Elements", "free-elements-6.1.0", len(PUBLIC_ELEMENT_KEYS)),
                ("V6.1 family roots", "free-findings-6.1.0", len(FINDING_FAMILY_KEYS)),
                ("V6.1 supporting signals", "supporting-signals-1.0.0", len(SUPPORTING_SIGNAL_CATALOG)),
                ("V6.1 semantic outcomes", SEMANTIC_OUTCOMES_VERSION, len(SEMANTIC_OUTCOME_CATALOG)),
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
        "## Active V6.1 public ontology",
        "",
        "Supporting signals below are evidence and never additional public score cards.",
        "",
        *_table(
            ("Public Elements (7)", "Family roots (5)"),
            [
                (
                    f"`{PUBLIC_ELEMENT_KEYS[index]}`" if index < len(PUBLIC_ELEMENT_KEYS) else "—",
                    f"`{FINDING_FAMILY_KEYS[index]}`" if index < len(FINDING_FAMILY_KEYS) else "—",
                )
                for index in range(max(len(PUBLIC_ELEMENT_KEYS), len(FINDING_FAMILY_KEYS)))
            ],
        ),
        "",
        "## V6.1 version matrix",
        "",
        *_table(
            ("Surface", "Version", "Disposition", "Compatibility"),
            [
                (surface.key, f"`{surface.version}`", surface.disposition, surface.compatibility)
                for surface in VERSION_SURFACES
            ],
        ),
        "",
        "## V6.1 semantic outcomes",
        "",
        *_table(
            ("Family", "Branch", "Outcome key", "Denominator", "Rollout", "Interaction"),
            [
                (
                    item.family_key,
                    item.hypothesis_branch,
                    f"`{item.semantic_outcome_key}`",
                    item.opportunity_denominator,
                    item.rollout_status,
                    item.interaction_key or "—",
                )
                for item in SEMANTIC_OUTCOME_CATALOG
            ],
        ),
        "",
        "## V6.1 supporting-signal catalog",
        "",
        *_table(
            ("Key", "Class", "Exposure", "Denominator", "Consumers", "Rejected reason"),
            [
                (
                    f"`{item.key}`",
                    item.classification,
                    item.public_exposure,
                    item.opportunity_contract.denominator,
                    _list(item.allowed_consumers),
                    item.rejected_reason or "—",
                )
                for item in SUPPORTING_SIGNAL_CATALOG
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
                    f"{len(PUBLIC_ELEMENT_KEYS)} Elements · {len(FINDING_FAMILY_KEYS)} family roots · zero to three Findings",
                    "One physical previous-365-day canonical summary-history read; no detail, parse, status, rank, or MMR dependency",
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

#!/usr/bin/env python3
"""Generate the human review surface for every reachable v5.2 Pattern story."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from string import Formatter

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.behavior.patterns.registry import PATTERN_REGISTRY  # noqa: E402
from app.behavior.presentation import PATTERN_PRESENTATION_CONTRACT  # noqa: E402
from app.content.renderer import (  # noqa: E402
    resolve_pattern_presentation_copy,
    validate_copy_catalog,
)

OUTPUT_PATH = ROOT / "docs" / "generated" / "free-dna-v5.2-copy-review.md"


def _fields(value: object) -> set[str]:
    if isinstance(value, str):
        return {name for _, name, _, _ in Formatter().parse(value) if name}
    if isinstance(value, dict):
        return {field for child in value.values() for field in _fields(child)}
    if isinstance(value, list):
        return {field for child in value for field in _fields(child)}
    return set()


def _example_params(pattern_key: str) -> dict[str, str]:
    if pattern_key in {"same_playbook", "versatile_core"}:
        return {"hero_name": "Example bridge hero"}
    return {}


def _render(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key}: {_render(child)}" for key, child in value.items())
    if isinstance(value, list):
        return "; ".join(_render(child) for child in value)
    return str(value)


def render_catalog() -> str:
    catalog = validate_copy_catalog()
    approval_status = "reviewed for the v5.2 product-closure pass"
    lines = [
        "# Free DNA v5.2 copy review catalog",
        "",
        "Generated from the deterministic presentation contract and the server copy catalog.",
        "Every sentence below is catalog-backed; this is an editorial QA surface, not a runtime source.",
        "",
        f"- Copy version: `{catalog['copy_version']}`",
        f"- Approval status: {approval_status}",
        "- Runtime LLM calls: none",
        "",
    ]
    for index, (pattern_key, contract) in enumerate(PATTERN_PRESENTATION_CONTRACT.items(), start=1):
        definition = PATTERN_REGISTRY[pattern_key]
        params = _example_params(pattern_key)
        copy = resolve_pattern_presentation_copy(
            pattern_key,
            contract["outcome_id"],
            recommendation_id=contract["recommendation_id"],
            deep_dive_id=contract["deep_dive_id"],
            params=params,
        )
        source = catalog["presentation"]["patterns"][pattern_key]
        lines.extend(
            [
                f"## P{index:02d} · {definition.label}",
                "",
                f"- Pattern key: `{pattern_key}`",
                f"- Outcome ID: `{contract['outcome_id']}`",
                f"- Visual variant: `{contract['visual_variant']}`",
                f"- Trigger summary: {definition.description}",
                f"- Evidence requirement: `{', '.join(definition.required_elements)}`",
                f"- Allowed placeholders: `{', '.join(sorted(_fields(source))) or 'none'}`",
                f"- Approval status: {approval_status}",
                "",
                "### Exact resolved copy",
                "",
                f"- Reveal: **{copy['headline']}** — {copy['subheadline']}",
                f"- Interpretation: **{copy['interpretation']['title']}** — {copy['interpretation']['body']}",
                f"- Recommendation: **{copy['recommendation']['eyebrow']} / {copy['recommendation']['title']}** — {copy['recommendation']['body']}",
                f"- Deep Dive: **{copy['deep_dive']['title']}** — {copy['deep_dive']['body']}",
                f"- Fallback: {_render(copy['fallback'])}",
                "",
                "### Guardrails",
                "",
                *[f"- {guardrail}" for guardrail in definition.copy_guardrails],
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the generated catalog is stale")
    args = parser.parse_args()
    expected = render_catalog()
    if args.check:
        if not OUTPUT_PATH.exists() or OUTPUT_PATH.read_text(encoding="utf-8") != expected:
            print(f"{OUTPUT_PATH} is stale; run: python scripts/generate_copy_review_catalog.py")
            return 1
        print("copy-review-catalog: current")
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(expected, encoding="utf-8")
    print(f"updated {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

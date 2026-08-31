#!/usr/bin/env python3
"""Generate the human review surface for every reachable v5.3 Pattern story.

The legacy presentation catalog remains in the output for historical snapshot
compatibility. The active semantic catalog is reviewed separately so every
finite outcome and recommendation branch has an exact, resolved copy record.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from string import Formatter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.behavior.outcomes import (  # noqa: E402
    SEMANTIC_OUTCOME_BRANCHES,
    SEMANTIC_OUTCOME_IDS,
    SEMANTIC_OUTCOME_VERSION,
    SEMANTIC_RECOMMENDATION_BRANCHES,
    SEMANTIC_RECOMMENDATION_IDS,
)
from app.behavior.patterns.registry import PATTERN_REGISTRY  # noqa: E402
from app.behavior.presentation import PATTERN_PRESENTATION_CONTRACT  # noqa: E402
from app.content.catalog import (  # noqa: E402
    copy_version,
    load_free_dna_semantic_copy,
    semantic_copy_version,
)
from app.content.renderer import (  # noqa: E402
    resolve_pattern_presentation_copy,
    validate_copy_catalog,
)
from app.heroes.recommendations import SEMANTIC_RECOMMENDATION_VERSION  # noqa: E402
from app.player_analysis_v61.versions import SEMANTIC_COPY_VERSION  # noqa: E402

OUTPUT_PATH = ROOT / "docs" / "generated" / "free-dna-v5.2-copy-review.md"
V61_OUTPUT_PATH = ROOT / "docs" / "generated" / "free-dna-v6.1-copy-review.md"


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


def _semantic_example_params(value: object) -> dict[str, str]:
    fields = _fields(value)
    params: dict[str, str] = {}
    if "hero_name" in fields:
        params["hero_name"] = "Example bridge hero"
    if "function_name" in fields:
        params["function_name"] = "Map & Objectives"
    if "familiar_anchor" in fields:
        params["familiar_anchor"] = "Fight control"
    if "session_game_label" in fields:
        params["session_game_label"] = "Game 4"
    return params


def _render(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key}: {_render(child)}" for key, child in value.items())
    if isinstance(value, list):
        return "; ".join(_render(child) for child in value)
    return str(value)


def _semantic_outcome_copy(
    pattern_key: str,
    outcome_id: str,
    *,
    semantic_catalog: dict[str, Any],
) -> dict[str, Any]:
    contract = PATTERN_PRESENTATION_CONTRACT[pattern_key]
    outcome = semantic_catalog["outcomes"][outcome_id]
    params = _semantic_example_params(outcome)
    return resolve_pattern_presentation_copy(
        pattern_key,
        contract["outcome_id"],
        semantic_outcome_id=outcome_id,
        params=params,
    )


def _semantic_recommendation_copy(
    pattern_key: str,
    recommendation_id: str,
    *,
    semantic_catalog: dict[str, Any],
) -> dict[str, Any]:
    contract = PATTERN_PRESENTATION_CONTRACT[pattern_key]
    recommendation = semantic_catalog["recommendations"][recommendation_id]
    params = _semantic_example_params(recommendation)
    return resolve_pattern_presentation_copy(
        pattern_key,
        contract["outcome_id"],
        semantic_recommendation_id=recommendation_id,
        params=params,
    )


def render_catalog() -> str:
    catalog = validate_copy_catalog()
    semantic_catalog = load_free_dna_semantic_copy()
    approval_status = "reviewed for the v5.3 identity-copy pass"
    lines = [
        "# Free DNA v5.2 copy review catalog",
        "",
        "Generated from the deterministic presentation contract and the server copy catalogs.",
        "Every sentence below is catalog-backed; this is an editorial QA surface, not a runtime source.",
        "",
        f"- Legacy compatibility copy: `{copy_version()}`",
        f"- Active semantic copy: `{semantic_copy_version()}`",
        f"- Semantic outcomes: `{SEMANTIC_OUTCOME_VERSION}` ({len(SEMANTIC_OUTCOME_IDS)} registered branches)",
        f"- Semantic recommendations: `{SEMANTIC_RECOMMENDATION_VERSION}` ({len(SEMANTIC_RECOMMENDATION_IDS)} registered IDs)",
        f"- Approval status: {approval_status}",
        "- Runtime LLM calls: none",
        "",
        "## Historical compatibility copy",
        "",
        "These 11 presentation records remain readable for historical snapshots.\n"
        "Active story pages use the v5.3 semantic branch records below.",
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
    lines.extend(
        [
            "## Active semantic copy",
            "",
            "The active resolver covers every registered semantic outcome branch and\n"
            "recommendation ID. Outcomes are distinct from recommendations: one\n"
            "outcome can intentionally carry a practice fallback recommendation.",
            "",
        ]
    )
    for index, (pattern_key, contract) in enumerate(PATTERN_PRESENTATION_CONTRACT.items(), start=1):
        definition = PATTERN_REGISTRY[pattern_key]
        outcome_ids = SEMANTIC_OUTCOME_BRANCHES[pattern_key]
        recommendation_ids = SEMANTIC_RECOMMENDATION_BRANCHES[pattern_key]
        lines.extend(
            [
                f"## P{index:02d} · {definition.label} · semantic branches",
                "",
                f"- Pattern key: `{pattern_key}`",
                f"- Visual variant: `{contract['visual_variant']}`",
                f"- Outcome branches: `{', '.join(outcome_ids)}`",
                f"- Recommendation branches: `{', '.join(recommendation_ids)}`",
                f"- Evidence requirement: `{', '.join(definition.required_elements)}`",
                f"- Approval status: {approval_status}",
                "",
                "### Exact semantic outcome copy",
                "",
            ]
        )
        for outcome_id in outcome_ids:
            copy = _semantic_outcome_copy(
                pattern_key,
                outcome_id,
                semantic_catalog=semantic_catalog,
            )
            source = semantic_catalog["outcomes"][outcome_id]
            lines.extend(
                [
                    f"#### `{outcome_id}`",
                    "",
                    f"- Allowed placeholders: `{', '.join(sorted(_fields(source))) or 'none'}`",
                    f"- Reveal: **{copy['headline']}** — {copy['subheadline']}",
                    f"- Interpretation: **{copy['interpretation']['title']}** — {copy['interpretation']['body']}",
                    f"- Fallback: {_render(copy['fallback'])}",
                    "",
                ]
            )
        lines.extend(["### Exact semantic recommendation copy", ""])
        for recommendation_id in recommendation_ids:
            copy = _semantic_recommendation_copy(
                pattern_key,
                recommendation_id,
                semantic_catalog=semantic_catalog,
            )
            source = semantic_catalog["recommendations"][recommendation_id]
            lines.extend(
                [
                    f"#### `{recommendation_id}`",
                    "",
                    f"- Allowed placeholders: `{', '.join(sorted(_fields(source))) or 'none'}`",
                    f"- Recommendation: **{copy['recommendation']['eyebrow']} / {copy['recommendation']['title']}** — {copy['recommendation']['body']}",
                    "",
                ]
            )
        lines.extend(
            [
                "### Guardrails",
                "",
                *[f"- {guardrail}" for guardrail in definition.copy_guardrails],
                "",
            ]
        )
    lines.extend(
        [
            "## Semantic coverage summary",
            "",
            f"- Registered semantic outcomes: `{len(SEMANTIC_OUTCOME_IDS)}`",
            f"- Registered semantic recommendations: `{len(SEMANTIC_RECOMMENDATION_IDS)}`",
            "- Every branch above is resolved from the semantic catalog with deterministic example parameters.",
            "",
        ]
    )
    return "\n".join(lines)


def render_v61_catalog() -> str:
    from app.player_analysis_v61.copy import SEMANTIC_COPY_REGISTRY
    from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_REGISTRY

    lines = [
        "# Free DNA V6.1 copy review catalog",
        "",
        "Generated from the frozen semantic-outcome and deterministic-copy registries.",
        "This is a review surface; runtime copy remains registry-owned and contains no LLM call.",
        "",
        f"- Copy version: `{SEMANTIC_COPY_VERSION}`",
        "- Claim contract: `claim-contract-2.0.0`",
        f"- Registered outcomes: `{len(SEMANTIC_OUTCOME_REGISTRY)}`",
        "- Public ontology: exactly seven Elements and five family roots",
        "- Forbidden inference: aggression, intent, tilt, fatigue, positioning, skill, cause, rank, and MMR",
        "",
    ]
    for key, definition in SEMANTIC_OUTCOME_REGISTRY.items():
        copy = SEMANTIC_COPY_REGISTRY[key]
        lines.extend(
            [
                f"## `{key}`",
                "",
                f"- Family / branch: `{definition.family_key}` / `{definition.hypothesis_branch}`",
                f"- Rollout: `{definition.rollout_status}`",
                f"- Denominator: `{definition.opportunity_denominator}`; minimum `{definition.minimum_opportunities}` opportunities and `{definition.minimum_sessions}` sessions",
                f"- Claim: {copy.claim}",
                f"- Evidence label: {copy.evidence_label}",
                f"- Interpretation: {copy.interpretation}",
                f"- Alternatives: {'; '.join(definition.alternatives)}",
                f"- Interaction / fallback: `{definition.interaction_key or 'text_only'}` / `text_evidence`",
                f"- Recommendation / verification: `{definition.recommendation_key or 'none'}` / `{', '.join(definition.verification_metric_keys) or 'none'}`",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the generated catalog is stale")
    args = parser.parse_args()
    expected = render_catalog()
    expected_v61 = render_v61_catalog()
    if args.check:
        stale = not OUTPUT_PATH.exists() or OUTPUT_PATH.read_text(encoding="utf-8") != expected
        stale_v61 = not V61_OUTPUT_PATH.exists() or V61_OUTPUT_PATH.read_text(encoding="utf-8") != expected_v61
        if stale or stale_v61:
            print(f"{OUTPUT_PATH} is stale; run: python scripts/generate_copy_review_catalog.py")
            return 1
        print("copy-review-catalog: current")
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(expected, encoding="utf-8")
    V61_OUTPUT_PATH.write_text(expected_v61, encoding="utf-8")
    print(f"updated {OUTPUT_PATH}")
    print(f"updated {V61_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

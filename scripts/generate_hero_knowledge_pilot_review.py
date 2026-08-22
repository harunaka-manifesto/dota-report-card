#!/usr/bin/env python3
"""Generate the human gate for the v5.2 semantic-freeze pilot."""

from __future__ import annotations

from pathlib import Path

from app.heroes.knowledge import SnapshotHeroKnowledgeProvider
from app.heroes.recommendations import recommend_semantic_heroes
from app.ingestion.summary_normalize import normalize_summary_rows

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/generated/hero-knowledge-pilot-review.md"


def _matches(hero_ids: list[int]):
    return normalize_summary_rows(
        [
            {
                "match_id": 800_000 + index,
                "start_time": 1_800_000_000 + index * 100,
                "duration": 1_800,
                "hero_id": hero_id,
                "player_slot": 0,
                "radiant_win": True,
                "game_mode": 1,
                "lobby_type": 0,
                "kills": 5,
                "deaths": 2,
                "assists": 5,
                "lane_role": 3,
            }
            for index, hero_id in enumerate(hero_id for hero_id in hero_ids for _repeat in range(3))
        ],
        account_id=42,
    ).matches


def _band_map(values: dict[str, str]) -> str:
    return ", ".join(f"{key}={values.get(key, 'unknown')}" for key in values)


def render() -> str:
    provider = SnapshotHeroKnowledgeProvider()
    lines = [
        "# Hero knowledge semantic-freeze pilot review",
        "",
        "Generated from the checked-in reviewed semantic layer and the generated runtime snapshot.",
        "This is a semantic QA artifact; it contains controlled facts, not production copy.",
        "",
        f"- Knowledge version: `{provider.version}`",
        "- Semantic version: `hero-semantics-pilot-v1`",
        "- Review status: `approved`",
        "- Runtime LLM calls: none",
        "- Empirical support policy: `unknown` stays unknown and lowers recommendation confidence.",
        "",
        "## Pilot facts",
        "",
    ]
    for hero in provider.entries:
        lines.extend(
            [
                f"### {hero.display_name} · `{hero.hero_id}`",
                "",
                f"- Roles: `{', '.join(hero.roles) or 'unknown'}`",
                f"- Primary functions: `{', '.join(hero.primary_functions)}`",
                f"- Secondary functions: `{', '.join(hero.secondary_functions)}`",
                f"- Demands: `{_band_map(dict(hero.demands))}`",
                f"- Empirical support: `{hero.empirical_support}`",
                f"- Confidence: `{hero.confidence}`",
                f"- Review status: `{hero.review_status}`",
                f"- Evidence refs: `{', '.join(hero.evidence_refs) or 'snapshot-level review refs'}`",
                f"- Provenance: `{', '.join(f'{key}={value}' for key, value in hero.provenance_versions.items())}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Representative recommendation comparisons",
            "",
            "The comparisons below exercise the same rationale schema across distinct semantic shapes.",
            "",
        ]
    )
    comparisons = (
        ("Axe + Puck pool → adjacent move", [2, 13], "adjacent_move"),
        ("Dazzle + Oracle pool → adjacent move", [50, 111], "adjacent_move"),
        ("Nature's Prophet + Phantom Assassin pool → fill gap", [53, 44], "fill_gap"),
        ("Beastmaster + Meepo pool → high-demand specialist", [38, 82], "specialist"),
    )
    for label, hero_ids, intent in comparisons:
        rationales = recommend_semantic_heroes(
            _matches(hero_ids),
            provider,
            intent=intent,
            limit=1,  # type: ignore[arg-type]
        )
        lines.append(f"### {label}")
        lines.append("")
        if not rationales:
            lines.append(
                "- Eligible: `no` — no candidate cleared the frozen role, demand, and confidence gates."
            )
            lines.append("")
            continue
        rationale = rationales[0]
        hero = provider.get(rationale.hero_id)
        lines.extend(
            [
                f"- Candidate: `{hero.display_name if hero else rationale.hero_id}`",
                f"- Familiar anchors: `{', '.join(rationale.familiar_anchors) or 'none'}`",
                f"- Adds: `{', '.join(rationale.adds) or 'none'}`",
                f"- New demands: `{', '.join(rationale.new_demands) or 'none'}`",
                f"- Role fit: `{rationale.role_fit}`",
                f"- Learning distance: `{rationale.learning_distance}`",
                f"- Empirical support: `{rationale.empirical_support}`",
                f"- Confidence: `{rationale.confidence}`",
                f"- Eligible: `{'yes' if rationale.eligible else 'no'}`",
                f"- Limitations: `{'; '.join(rationale.limitations) or 'none'}`",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(), encoding="utf-8")
    print(f"updated {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

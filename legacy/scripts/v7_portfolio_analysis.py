#!/usr/bin/env python3
"""Portfolio complementarity and coverage analysis over the graded candidates.

The five Findings are a portfolio, not five isolated tests. This script asks
which combinations cover which players, who is left uncovered, and whether any
five-candidate portfolio approaches the product target honestly.

DISCOVERY only — the confirmation split was spent once by the tournament and is
not read again here. No provider call. No publication threshold is chosen: the
provisional levels are carried through from the frozen inference design purely
as a comparison scale.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "legacy" / "services" / "api"))

from report_card.player_analysis_v7.research.corpus import (  # noqa: E402
    DISCOVERY,
    corpus_paths,
    manifest_digests,
)
from report_card.player_analysis_v7.research.features import (  # noqa: E402
    FEATURE_VERSION,
    load_frames,
)
from report_card.player_analysis_v7.research.inference import INFERENCE_VERSION  # noqa: E402
from report_card.player_analysis_v7.research.registry import (  # noqa: E402
    CANDIDATE_DEFINITION_VERSION,
    FAMILY_BY_NAME,
)
from report_card.player_analysis_v7.research.screen import spearman  # noqa: E402
from report_card.player_analysis_v7.research.tournament import Denominators, evaluate  # noqa: E402

PORTFOLIO_VERSION = "v7-portfolio-analysis-1.0.0"

#: Comparison scale only, matching the tournament's provisional levels.
LEVELS = (0.01, 0.05)


def qualification_matrix(
    corpus_root: str,
    families: tuple[str, ...],
    seed: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], Denominators]:
    paths = corpus_paths(corpus_root)
    frames = load_frames(paths, frozenset({DISCOVERY}), with_parsed=True)
    denominators = Denominators(
        sampled=len(frames),
        product_eligible=sum(1 for frame in frames if frame.rows),
        parsed_eligible=sum(1 for frame in frames if frame.parsed),
    )
    per_family: dict[str, dict[str, Any]] = {}
    summaries: dict[str, dict[str, Any]] = {}
    for name in families:
        family = FAMILY_BY_NAME[name]
        evaluation, results, _ = evaluate(
            name,
            family,
            frames,
            denominators,
            split=DISCOVERY,
            seed=seed,
            type_i_replicates=0,
        )
        per_family[name] = {
            result.pseudonym: {
                "delta": result.delta,
                "se": result.standard_error,
                "p": result.p_value,
            }
            for result in results
            if result.p_value == result.p_value
        }
        summaries[name] = {
            "parsed_dependent": family.parsed,
            "information_eligible": evaluation.information_eligible,
            "reach_of_sampled": evaluation.reach_of_sampled,
            "reach_of_applicable": evaluation.reach_of_applicable,
        }
    return per_family, summaries, denominators


def coverage(
    per_family: dict[str, dict[str, Any]],
    members: tuple[str, ...],
    population: list[str],
    level: float,
) -> dict[str, Any]:
    counts = Counter()
    for pseudonym in population:
        qualified = sum(
            1
            for name in members
            if (row := per_family[name].get(pseudonym)) is not None and row["p"] < level
        )
        counts[qualified] += 1
    total = len(population)
    at_least = {
        str(k): sum(value for size, value in counts.items() if size >= k) / total
        for k in range(1, len(members) + 1)
    }
    return {
        "histogram": {str(k): counts.get(k, 0) for k in range(0, len(members) + 1)},
        "share_at_least": at_least,
        "denominator": total,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", required=True)
    parser.add_argument("--tournament-discovery", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=20260903)
    args = parser.parse_args()

    tournament = json.loads(Path(args.tournament_discovery).read_text(encoding="utf-8"))
    grades = {
        row["family"]: row["grade"]
        for row in json.loads(
            Path(args.tournament_discovery)
            .with_name("v7-statistical-feasibility-tournament-2026-09-03.json")
            .read_text(encoding="utf-8")
        )["decision_rows"]
    }
    families = tuple(name for name in grades)

    per_family, summaries, denominators = qualification_matrix(
        args.corpus_root, families, args.seed
    )

    population = sorted({p for rows in per_family.values() for p in rows})

    # Pairwise qualification overlap: of the players either candidate qualifies,
    # what share do both qualify? A high value means the two Findings tend to
    # land on the same people, which is what makes a portfolio fail to spread.
    overlap: dict[str, dict[str, float]] = {}
    effect_correlation: dict[str, dict[str, float]] = {}
    for left in families:
        overlap[left] = {}
        effect_correlation[left] = {}
        for right in families:
            left_set = {p for p, row in per_family[left].items() if row["p"] < 0.01}
            right_set = {p for p, row in per_family[right].items() if row["p"] < 0.01}
            union = left_set | right_set
            overlap[left][right] = len(left_set & right_set) / len(union) if union else float("nan")
            shared = sorted(set(per_family[left]) & set(per_family[right]))
            if len(shared) >= 20:
                effect_correlation[left][right] = spearman(
                    [per_family[left][p]["delta"] for p in shared],
                    [per_family[right][p]["delta"] for p in shared],
                )
            else:
                effect_correlation[left][right] = float("nan")

    ab_families = tuple(name for name in families if grades[name] in {"A", "B"})
    selectable = tuple(name for name in families if grades[name] in {"A", "B", "C"})

    portfolios: list[dict[str, Any]] = []
    for members in itertools.combinations(selectable, 5):
        result = coverage(per_family, members, population, 0.01)
        result_05 = coverage(per_family, members, population, 0.05)
        portfolios.append(
            {
                "members": list(members),
                "grades": [grades[name] for name in members],
                "parsed_dependent_count": sum(
                    1 for name in members if summaries[name]["parsed_dependent"]
                ),
                "share_at_least_three_01": result["share_at_least"]["3"],
                "share_at_least_three_05": result_05["share_at_least"]["3"],
                "share_at_least_one_01": result["share_at_least"]["1"],
                "share_all_five_01": result["share_at_least"]["5"],
            }
        )
    portfolios.sort(key=lambda row: -row["share_at_least_three_01"])

    # Who is never covered, and is it the same people every time?
    # Across *every* candidate, not only the selectable ones. An earlier version
    # counted over the A/B/C subset and published the result as "all twelve",
    # which understated coverage and silently contradicted the tournament.
    never_qualified = [
        pseudonym
        for pseudonym in population
        if all(
            (row := per_family[name].get(pseudonym)) is None or row["p"] >= 0.01
            for name in families
        )
    ]
    coverage_counts = Counter(
        sum(
            1
            for name in families
            if (row := per_family[name].get(pseudonym)) is not None and row["p"] < 0.01
        )
        for pseudonym in population
    )

    document = {
        "schema_version": PORTFOLIO_VERSION,
        "split": DISCOVERY,
        "seed": args.seed,
        "identities_included": False,
        "new_provider_calls": 0,
        "candidate_test_read": False,
        "publication_thresholds_chosen": False,
        "corpus": manifest_digests(corpus_paths(args.corpus_root).root),
        "source_tournament_code_sha": tournament["code_sha"],
        "design_digest": tournament["design_digest"],
        "feature_version": FEATURE_VERSION,
        "inference_version": INFERENCE_VERSION,
        "candidate_definition_version": CANDIDATE_DEFINITION_VERSION,
        "denominators": {
            "sampled": denominators.sampled,
            "product_eligible": denominators.product_eligible,
            "parsed_eligible": denominators.parsed_eligible,
            "any_information_eligible": len(population),
        },
        "grades": grades,
        "family_summary": summaries,
        "qualification_overlap_jaccard_01": overlap,
        "effect_correlation_spearman": effect_correlation,
        "all_candidate_coverage": {
            "candidates_counted": list(families),
            "histogram": {str(k): v for k, v in sorted(coverage_counts.items())},
            "never_qualified": len(never_qualified),
            "never_qualified_share": len(never_qualified) / len(population),
        },
        "ab_only_coverage": coverage(per_family, ab_families, population, 0.01),
        "ab_only_coverage_05": coverage(per_family, ab_families, population, 0.05),
        "five_candidate_portfolios": portfolios,
    }
    Path(args.out).write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    best = portfolios[0]
    print(f"best five at 0.01: {best['members']} -> P(>=3) = {best['share_at_least_three_01']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the section-5 improvement selection over DISCOVERY.

Answers the question the model cannot answer on paper: does a player's own
win/loss gap actually pick out one improvement, or does the reliability weight
silence every dimension?

Emits an **aggregate-only** document — per dimension, how many players carry a
measurable gap, the population spread, the reliability and priority
distributions, and how often each dimension wins the single slot. No
per-player row, account, or match identifier is written.

Read-only. No provider call. DISCOVERY only.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))

from report_card.player_analysis_v7.research import inference  # noqa: E402
from report_card.player_analysis_v7.research.corpus import DISCOVERY  # noqa: E402
from report_card.player_analysis_v7.research.pass2_features import (  # noqa: E402
    group_rows_by_account,
)
from report_card.player_analysis_v7.research.pass2_observations import chronological  # noqa: E402
from report_card.player_analysis_v7.research.pass2_tables import (  # noqa: E402
    is_pass2_product_context,
    iter_pass2_players,
)
from report_card.player_analysis_v7.research.ranking import (  # noqa: E402
    PopulationObservation,
    population_parameters,
)
from report_card.player_analysis_v7.research.recommendation import (  # noqa: E402
    DOWNSTREAM_EXCLUSIONS,
    MIN_PER_ARM,
    MODAL_SIGN_SHARE_LIMIT,
    OUTCOME_CONTAMINATED_EXCLUSIONS,
    RECOMMENDATION_REGISTRY,
    RECOMMENDATION_VERSION,
    ScoredRecommendation,
    build_personal_contrast_matrix,
    dimension_scale,
    eligible_dimensions,
    gap_reliability,
    has_denominator,
    modal_sign_share,
    opportunities,
    priority,
    select,
    standardized_gap,
)

SELECTION_RUN_VERSION = "v7-recommendation-selection-run-1.0.0"

DEPENDENCE_BATCH_LENGTHS = (1, 5, 10, 25, 50, 100)

QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)


def _quantile(ordered: list[float], q: float) -> float:
    index = min(len(ordered) - 1, int(q * (len(ordered) - 1) + 0.5))
    return ordered[index]


def _describe(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    out: dict[str, Any] = {
        "n": len(ordered),
        "mean": round(statistics.fmean(ordered), 6),
        "min": round(ordered[0], 6),
        "max": round(ordered[-1], 6),
    }
    for q in QUANTILES:
        out[f"p{int(q * 100)}"] = round(_quantile(ordered, q), 6)
    return out


def _dependence(matrix: inference.FamilyMatrix) -> tuple[float, int | None, bool]:
    """``D`` at the longest batch length the data supports, floored at 1.0.

    Same rule as the Finding pipeline, and for the same reason: reading a
    fixed length silently falls back to independence, and a ratio below 1.0
    would hand the dimension free reliability.
    """

    curve = inference.variance_ratio_curve(matrix, batch_lengths=DEPENDENCE_BATCH_LENGTHS)
    usable = [b for b in DEPENDENCE_BATCH_LENGTHS if b > 1 and curve.get(b) == curve.get(b)]
    if not usable:
        return 1.0, None, False
    batch_length = max(usable)
    return max(1.0, curve[batch_length]), batch_length, True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pass2-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows = (row for row in iter_pass2_players(args.pass2_root) if is_pass2_product_context(row))
    by_account = {
        pseudonym: chronological(account_rows)
        for pseudonym, account_rows in group_rows_by_account(rows).items()
    }

    summaries: dict[str, Any] = {}
    scored_by_player: dict[str, list[ScoredRecommendation]] = {}

    # Every dimension is fitted, including the excluded ones: the
    # outcome-contamination screen is a recorded design-time property, and the
    # only way it cannot drift is to re-measure it and fail when the record
    # and the corpus disagree.
    for key, dimension in RECOMMENDATION_REGISTRY.items():
        per_player: list[tuple[str, list[Any]]] = []
        without_denominator = 0
        for pseudonym, account_rows in sorted(by_account.items()):
            series = opportunities(account_rows, dimension)
            if not series:
                continue
            if not has_denominator(series):
                without_denominator += 1
                continue
            per_player.append((pseudonym, series))

        if len(per_player) < 2:
            summaries[key] = {
                "players_with_a_gap": len(per_player),
                "players_without_a_denominator": without_denominator,
                "reason": "fewer than two players support a population fit",
            }
            continue

        matrix = build_personal_contrast_matrix(per_player)
        results = [r for r in inference.infer_all(matrix) if r.p_value == r.p_value]
        dependence, batch_length, measured = _dependence(matrix)
        scale = dimension_scale(matrix)
        # Reported for the record, never used as the denominator: the model as
        # first written standardized by this and it is exactly zero everywhere.
        _, tau = population_parameters(
            [
                PopulationObservation(
                    delta_hat=r.delta, se=r.standard_error, dependence_inflation=dependence
                )
                for r in results
            ]
        )

        gaps = [result.delta for result in results]
        sign_share = modal_sign_share(gaps)
        contaminated = sign_share >= MODAL_SIGN_SHARE_LIMIT
        if contaminated != dimension.outcome_contaminated:
            raise RuntimeError(
                f"{key}: recorded outcome_contaminated="
                f"{dimension.outcome_contaminated} but the corpus measures a "
                f"modal-sign share of {sign_share:.4f} against a limit of "
                f"{MODAL_SIGN_SHARE_LIMIT}. The registry and the data disagree; "
                "fix the registry rather than the check."
            )
        eligible = key in eligible_dimensions()

        reliabilities: list[float] = []
        priorities: list[float] = []
        for result in results:
            standardized = standardized_gap(result.delta, scale)
            r_value = gap_reliability(result.standard_error, scale, dependence)
            p_value = priority(standardized, r_value, dimension.actionability)
            reliabilities.append(r_value)
            priorities.append(p_value)
            if not eligible:
                continue
            scored_by_player.setdefault(result.pseudonym, []).append(
                ScoredRecommendation(
                    key=key,
                    gap=result.delta,
                    standard_error=result.standard_error,
                    standardized_gap=standardized,
                    reliability=r_value,
                    actionability=dimension.actionability,
                    priority=p_value,
                    direction="positive" if result.delta > 0 else "negative",
                    wins=result.n_control,
                    losses=result.n_treated,
                    recommendation=dimension.recommendation,
                    verification=dimension.verification,
                )
            )

        summaries[key] = {
            "actionability": dimension.actionability,
            "upstream": dimension.upstream,
            "upstream_rationale": dimension.upstream_rationale,
            "verification": dimension.verification,
            "eligible": eligible,
            "modal_sign_share": sign_share,
            "outcome_contaminated": contaminated,
            "players_with_a_gap": len(results),
            "players_without_a_denominator": without_denominator,
            "opportunities": len(matrix.residual),
            "dimension_scale": scale,
            "between_player_tau_unused": tau,
            "dependence_inflation": dependence,
            "dependence_batch_length": batch_length,
            "dependence_measured": measured,
            "gap": _describe(gaps),
            "reliability": _describe(reliabilities),
            "priority": _describe(priorities),
            "context_projection": {
                "factor_order": list(matrix.encoded.factors),
                "categorical_vocabularies": {
                    factor: list(levels)
                    for factor, levels in zip(
                        matrix.encoded.factors, matrix.encoded.level_names, strict=True
                    )
                },
                "intercept": matrix.context_fit.intercept,
                "coefficients": {
                    factor: dict(zip(levels, coefficients, strict=True))
                    for factor, levels, coefficients in zip(
                        matrix.encoded.factors,
                        matrix.encoded.level_names,
                        matrix.context_fit.coefficients,
                        strict=True,
                    )
                },
            },
        }
        print(
            f"{key:24s} players={len(results):>4d} scale={scale:.4f} "
            f"sign={sign_share:.4f} {'EXCLUDED' if not eligible else 'eligible'} "
            f"rel_p50={_describe(reliabilities).get('p50')} "
            f"prio_p50={_describe(priorities).get('p50')}",
            flush=True,
        )

    chosen: Counter[str] = Counter()
    runner_up: Counter[str] = Counter()
    chosen_priorities: list[float] = []
    candidate_counts: Counter[int] = Counter()
    players_with_no_recommendation = 0
    for scored in scored_by_player.values():
        candidate_counts[len(scored)] += 1
        top, runners = select(scored)
        if top is None:
            players_with_no_recommendation += 1
            continue
        chosen[top.key] += 1
        chosen_priorities.append(top.priority)
        for runner in runners:
            runner_up[runner.key] += 1

    players = len(scored_by_player)
    document: dict[str, Any] = {
        "schema_version": SELECTION_RUN_VERSION,
        "recommendation_version": RECOMMENDATION_VERSION,
        "split": DISCOVERY,
        "identities_included": False,
        "new_provider_calls": 0,
        "candidate_test_read": False,
        "minimum_matches_per_arm": MIN_PER_ARM,
        "modal_sign_share_limit": MODAL_SIGN_SHARE_LIMIT,
        "causality_claimed": False,
        "population_used_as_comparison": False,
        "denominators": {
            "pass2_discovery_players": len(by_account),
            "players_with_at_least_one_candidate": players,
            "players_with_no_recommendation": players_with_no_recommendation,
        },
        "downstream_exclusions": DOWNSTREAM_EXCLUSIONS,
        "outcome_contaminated_exclusions": OUTCOME_CONTAMINATED_EXCLUSIONS,
        "dimensions": summaries,
        "candidates_per_player_histogram": {str(k): v for k, v in sorted(candidate_counts.items())},
        "chosen_dimension_counts": dict(sorted(chosen.items())),
        "runner_up_dimension_counts": dict(sorted(runner_up.items())),
        "chosen_priority": _describe(chosen_priorities),
        "distinct_dimensions_ever_chosen": len(chosen),
    }

    serialized = json.dumps(document, indent=2, sort_keys=True)
    if "v7p_" in serialized:
        raise RuntimeError("a player pseudonym reached the recommendation output document")
    Path(args.out).write_text(serialized + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(
        f"{players} players carry a candidate; {len(chosen)} distinct dimensions "
        f"win the single slot; {players_with_no_recommendation} get none"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

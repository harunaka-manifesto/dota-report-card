#!/usr/bin/env python3
"""End-to-end Finding pipeline: corpus in, ranked report slate out.

This is the acceptance artifact for the V7 Finding work. Every earlier script
measured one stage; this one runs the whole chain on the real corpus and
reports what a player would actually receive:

    features / observations
      -> inference (context removal, blocked means, dependence-robust SE)
      -> population parameters (mu, tau) per dimension, consistently estimated
      -> ranking (z, reliability, score, shrunk estimate)
      -> stratified selection into the three Finding-carrying report sections

Pass-1 families come from ``v7_research.features`` via the tournament's
``collect``; Pass-2 dimensions come from ``v7_research.pass2_observations``,
which emits the same ``Opportunity`` records so both halves go through one
estimator and land on one comparable reliability scale.

Four assertions decide whether the run succeeded. They are checks on the
result, not on the code path, and any one of them failing means the pipeline
is broken and must not report success:

1. The negative control (``side_sensitivity``) estimates ``tau = 0``, gives
   every player reliability 0, and puts nobody above the 0.25 score line. No
   rule in the pipeline names the control; if the estimator can be talked
   into manufacturing a Finding out of noise, this is where it shows.
2. Every reliability lies in ``[0, 1]``.
3. The output document contains no player pseudonym, from either corpus.
4. CANDIDATE_TEST was never read: DISCOVERY is the only split requested, and
   the candidate-test access ledger is byte-identical before and after.

Read-only on both corpora. Makes no provider call. Chooses no publication
threshold. The output is aggregate-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))

from app.player_analysis_v7.research import inference  # noqa: E402
from app.player_analysis_v7.research.corpus import (  # noqa: E402
    CANDIDATE_TEST_LEDGER,
    DISCOVERY,
    corpus_paths,
    manifest_digests,
)
from app.player_analysis_v7.research.features import (  # noqa: E402
    FEATURE_VERSION,
    Opportunity,
    load_frames,
)
from app.player_analysis_v7.research.pass2_features import (  # noqa: E402
    FEATURE_VERSION as PASS2_FEATURE_VERSION,
)
from app.player_analysis_v7.research.pass2_features import group_rows_by_account  # noqa: E402
from app.player_analysis_v7.research.pass2_observations import (  # noqa: E402
    OBSERVATION_REGISTRY,
    OBSERVATION_VERSION,
    chronological,
)
from app.player_analysis_v7.research.pass2_tables import (  # noqa: E402
    is_pass2_product_context,
    iter_pass2_players,
)
from app.player_analysis_v7.research.ranking import (  # noqa: E402
    FINDING_FLOOR,
    FINDING_SECTIONS,
    RANKING_MODEL_VERSION,
    REPORT_SLOTS,
    SCORE_LINE,
    PlayerDimension,
    PopulationObservation,
    apply_score_gate,
    population_parameters,
    rank_player,
    select_stratified,
)
from app.player_analysis_v7.research.registry import (  # noqa: E402
    CANDIDATE_DEFINITION_VERSION,
    FAMILY_BY_NAME,
)
from app.player_analysis_v7.research.tournament import collect  # noqa: E402

from scripts.v7_discovery_screen import FROZEN_SERIOUS_CANDIDATES  # noqa: E402

PIPELINE_VERSION = "v7-finding-pipeline-1.0.0"

#: The negative control. Measured like any other dimension and excluded from
#: selection; assertion 1 reads its result.
NEGATIVE_CONTROL = "side_sensitivity"

#: Batch lengths at which the variance-ratio curve is measured. ``D`` is read
#: at the longest length the data actually supports, not at a fixed 100:
#: ``inference.variance_ratio_curve`` needs at least five blocks per player,
#: so a dimension whose players have ~470 observations can be measured at 50
#: but silently returns ``nan`` at 100. Reading 100 unconditionally sent four
#: Pass-2 dimensions down the independence fallback, which overstates their
#: reliability - the opposite of what a dependence correction is for.
DEPENDENCE_BATCH_LENGTHS = (1, 5, 10, 25, 50, 100)

#: Which report section each Pass-1 family speaks to. This is a topical
#: placement, not a verdict: direction decides whether a Finding reads as a
#: strength or a cost at render time, so a family sits under the question it
#: answers rather than under an assumed sign.
SECTION_BY_FAMILY: dict[str, str] = {
    "post_loss_session_continuation": "response_to_a_loss",
    "post_loss_hero_switch": "response_to_a_loss",
    "post_loss_requeue_latency": "response_to_a_loss",
    "hero_novelty": "what_is_good",
    "transfer_activity": "what_is_good",
    "duration_tempo": "what_is_good",
    "position_flexibility": "what_is_good",
    "fight_timing_centroid": "what_is_good",
    "purchase_tempo": "what_is_good",
    "transfer_risk": "what_is_costing_you",
    "lead_retention": "what_is_costing_you",
    "lane_recovery_participation": "what_is_costing_you",
}

QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)


class PipelineAssertionError(RuntimeError):
    """A result-level acceptance check failed."""


def _quantile(ordered: list[float], quantile: float) -> float:
    index = min(len(ordered) - 1, int(quantile * (len(ordered) - 1) + 0.5))
    return ordered[index]


def _describe(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    summary: dict[str, Any] = {
        "n": len(ordered),
        "mean": round(statistics.fmean(ordered), 6),
        "min": round(ordered[0], 6),
        "max": round(ordered[-1], 6),
    }
    for q in QUANTILES:
        summary[f"p{int(q * 100)}"] = round(_quantile(ordered, q), 6)
    return summary


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _ledger_digest() -> str:
    """Digest of the candidate-test access ledger, or a marker if absent."""

    if not CANDIDATE_TEST_LEDGER.exists():
        return "absent"
    return hashlib.sha256(CANDIDATE_TEST_LEDGER.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# One dimension, end to end
# ---------------------------------------------------------------------------


def fit_dimension(
    key: str,
    section: str,
    per_player: list[tuple[str, list[Opportunity]]],
    *,
    arm_family: bool,
    treated: str | None,
    control: str | None,
) -> tuple[dict[str, PlayerDimension], dict[str, Any]]:
    """Estimate one dimension for every player who supports it.

    Returns the per-player ``PlayerDimension`` records (keyed by pseudonym,
    kept in memory only) and an aggregate-only summary of the fit.
    """

    if not per_player:
        return {}, {"section": section, "players": 0, "reason": "no player supports it"}

    matrix = inference.build_matrix(
        per_player, arm_family=arm_family, treated=treated, control=control
    )
    results = [r for r in inference.infer_all(matrix) if r.p_value == r.p_value]
    if len(results) < 2:
        return {}, {
            "section": section,
            "players": len(results),
            "reason": "fewer than two estimable players; no population fit",
        }

    curve = inference.variance_ratio_curve(matrix, batch_lengths=DEPENDENCE_BATCH_LENGTHS)
    usable = [
        b for b in DEPENDENCE_BATCH_LENGTHS if b > 1 and curve.get(b, float("nan")) == curve.get(b)
    ]
    dependence_measured = bool(usable)
    batch_length = max(usable) if usable else None
    raw = curve[batch_length] if batch_length is not None else float("nan")
    # Two guards, both in the conservative direction:
    #
    # * Falling back to 1.0 when nothing is measurable assumes independence,
    #   which understates measurement variance and so overstates reliability.
    #   It is the optimistic direction, so it is always reported, never
    #   absorbed silently.
    # * A measured ratio below 1.0 means the batch means vary *less* than
    #   independence predicts. That is sampling noise far more often than it
    #   is real negative serial dependence, and crediting it would inflate
    #   reliability for free, so D is floored at 1.0 and the raw value kept.
    dependence = max(1.0, raw) if dependence_measured else 1.0
    # The curve plateaus once the batch is longer than the dependence range.
    # If the longest measurable length is still rising, D is a lower bound and
    # every reliability computed from it is an upper bound.
    previous = None
    for candidate in DEPENDENCE_BATCH_LENGTHS:
        if (
            batch_length is not None
            and candidate < batch_length
            and curve.get(candidate, float("nan")) == curve.get(candidate)
        ):
            previous = curve[candidate]
    plateaued = (
        previous is not None and previous > 0 and raw == raw and (raw - previous) / previous <= 0.10
    )

    mu, tau = population_parameters(
        [
            PopulationObservation(
                delta_hat=r.delta, se=r.standard_error, dependence_inflation=dependence
            )
            for r in results
        ]
    )

    dimensions = {
        r.pseudonym: PlayerDimension(
            key=key,
            section=section,
            delta_hat=r.delta,
            se=r.standard_error,
            sample_size=r.n,
            mu=mu,
            tau=tau,
            dependence_inflation=dependence,
        )
        for r in results
    }

    ranked = {pseudonym: rank_player([d])[0] for pseudonym, d in dimensions.items()}
    reliabilities = [f.reliability for f in ranked.values()]
    scores = [f.score for f in ranked.values()]
    summary = {
        "section": section,
        "players": len(dimensions),
        "opportunities": len(matrix.residual),
        "projection_drift": round(matrix.projection_drift, 6),
        "mu": round(mu, 6),
        "tau": round(tau, 6),
        "dependence_inflation": round(dependence, 6),
        "dependence_inflation_measured": dependence_measured,
        "dependence_batch_length": batch_length,
        "dependence_inflation_raw": round(raw, 6) if raw == raw else None,
        "dependence_curve": {
            str(b): round(curve[b], 6)
            for b in DEPENDENCE_BATCH_LENGTHS
            if curve.get(b, float("nan")) == curve.get(b)
        },
        "dependence_curve_plateaued": plateaued,
        "reliability": _describe(reliabilities),
        "score": _describe(scores),
        "share_scoring_above_line": round(
            sum(1 for s in scores if s > SCORE_LINE) / len(scores), 6
        ),
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
                factor: {
                    level: coefficient
                    for level, coefficient in zip(levels, coefficients, strict=True)
                }
                for factor, levels, coefficients in zip(
                    matrix.encoded.factors,
                    matrix.encoded.level_names,
                    matrix.context_fit.coefficients,
                    strict=True,
                )
            },
            "sweeps": 10,
            "weighting": "equal_per_opportunity",
            "interactions": [],
            "player_factor": False,
            "reference_policy": "none_finite_sweep_parameterization",
        },
    }
    return dimensions, summary


# ---------------------------------------------------------------------------
# The two corpora
# ---------------------------------------------------------------------------


def fit_pass1(
    corpus_root: str,
    parsed_root: str,
) -> tuple[dict[str, dict[str, PlayerDimension]], dict[str, Any], int]:
    paths = corpus_paths(corpus_root)
    frames = load_frames(
        paths,
        frozenset({DISCOVERY}),
        with_parsed=True,
        parsed_paths=corpus_paths(parsed_root),
    )
    per_dimension: dict[str, dict[str, PlayerDimension]] = {}
    summaries: dict[str, Any] = {}
    for name in (*FROZEN_SERIOUS_CANDIDATES, NEGATIVE_CONTROL):
        family = FAMILY_BY_NAME[name]
        section = SECTION_BY_FAMILY.get(name, "what_is_good")
        dimensions, summary = fit_dimension(
            name,
            section,
            collect(name, frames),
            arm_family=family.arm_family,
            treated=family.treated,
            control=family.control,
        )
        summary["negative_control"] = name == NEGATIVE_CONTROL
        summary["source"] = "pass1"
        per_dimension[name] = dimensions
        summaries[name] = summary
        print(
            f"pass1 {name:32s} players={summary.get('players', 0):>4d} "
            f"tau={summary.get('tau', float('nan')):.4f} "
            f"rel_p50={summary.get('reliability', {}).get('p50', float('nan'))}",
            flush=True,
        )
    return per_dimension, summaries, len(frames)


def fit_pass2(
    pass2_root: str,
) -> tuple[dict[str, dict[str, PlayerDimension]], dict[str, Any], int]:
    rows = (row for row in iter_pass2_players(pass2_root) if is_pass2_product_context(row))
    by_account = {
        pseudonym: chronological(account_rows)
        for pseudonym, account_rows in group_rows_by_account(rows).items()
    }
    per_dimension: dict[str, dict[str, PlayerDimension]] = {}
    summaries: dict[str, Any] = {}
    for key, dimension in OBSERVATION_REGISTRY.items():
        per_player = [
            (pseudonym, series)
            for pseudonym, account_rows in sorted(by_account.items())
            if (series := dimension.fn(account_rows))
        ]
        dimensions, summary = fit_dimension(
            key,
            dimension.section,
            per_player,
            arm_family=dimension.arm_family,
            treated=dimension.treated,
            control=dimension.control,
        )
        summary["negative_control"] = False
        summary["source"] = "pass2"
        summary["estimand"] = dimension.estimand
        per_dimension[key] = dimensions
        summaries[key] = summary
        print(
            f"pass2 {key:32s} players={summary.get('players', 0):>4d} "
            f"tau={summary.get('tau', float('nan')):.4f} "
            f"rel_p50={summary.get('reliability', {}).get('p50', float('nan'))}",
            flush=True,
        )
    return per_dimension, summaries, len(by_account)


# ---------------------------------------------------------------------------
# Assembly and acceptance
# ---------------------------------------------------------------------------


def assemble_slates(
    per_dimension: dict[str, dict[str, PlayerDimension]],
) -> dict[str, list[Any]]:
    """One ranked, stratified slate per player, over every non-control dimension."""

    by_player: dict[str, list[PlayerDimension]] = {}
    for key, dimensions in per_dimension.items():
        if key == NEGATIVE_CONTROL:
            continue
        for pseudonym, dimension in dimensions.items():
            by_player.setdefault(pseudonym, []).append(dimension)
    # Owner decision D1: select first, gate second. Selection decides which
    # Findings matter, including promoting a weak one to keep a section from
    # being empty; the gate then trims only the slots above the floor.
    return {
        pseudonym: apply_score_gate(
            select_stratified(rank_player(dimensions), FINDING_SECTIONS, REPORT_SLOTS)
        )
        for pseudonym, dimensions in by_player.items()
    }


def check_negative_control(summary: dict[str, Any]) -> None:
    tau = summary.get("tau")
    if summary.get("players", 0) < 2:
        raise PipelineAssertionError(
            f"negative control {NEGATIVE_CONTROL!r} was not estimated at all "
            "(no players); the assertion cannot pass vacuously"
        )
    if tau is None or tau != 0.0:
        raise PipelineAssertionError(
            f"negative control {NEGATIVE_CONTROL!r} estimated tau={tau!r}, expected exactly 0"
        )
    reliability_max = summary["reliability"].get("max")
    if reliability_max != 0.0:
        raise PipelineAssertionError(
            f"negative control {NEGATIVE_CONTROL!r} gave a non-zero reliability "
            f"(max {reliability_max!r})"
        )
    score_max = summary["score"].get("max")
    if not (score_max == 0.0 or score_max <= SCORE_LINE):
        raise PipelineAssertionError(
            f"negative control {NEGATIVE_CONTROL!r} put a player above the "
            f"{SCORE_LINE} score line (max {score_max!r})"
        )


def check_reliability_range(per_dimension: dict[str, dict[str, PlayerDimension]]) -> None:
    for key, dimensions in per_dimension.items():
        for dimension in dimensions.values():
            finding = rank_player([dimension])[0]
            r = finding.reliability
            if not (0.0 <= r <= 1.0) or r != r:
                raise PipelineAssertionError(
                    f"dimension {key!r} produced reliability {r!r}, outside [0, 1]"
                )


def check_no_pseudonyms(document: dict[str, Any], pseudonyms: set[str]) -> None:
    serialized = json.dumps(document, sort_keys=True)
    leaked = sorted(p for p in pseudonyms if p and p in serialized)
    if leaked:
        raise PipelineAssertionError(
            f"{len(leaked)} player pseudonym(s) reached the output document, first: {leaked[0]!r}"
        )
    if "v7p_" in serialized:
        raise PipelineAssertionError(
            "the substring 'v7p_' reached the output document; Pass-2 account "
            "identifiers must never be published"
        )


def check_candidate_test_untouched(before: str, after: str) -> None:
    if before != after:
        raise PipelineAssertionError(
            "the candidate-test access ledger changed during the run; this "
            "pipeline reads DISCOVERY only"
        )


# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", required=True, help="Pass-1 corpus root")
    parser.add_argument(
        "--pass1-parsed-root",
        required=True,
        help="DISCOVERY-only canonical parsed overlay for the Pass-1 identities",
    )
    parser.add_argument("--pass2-root", required=True, help="Pass-2 corpus or canonical root")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    ledger_before = _ledger_digest()

    pass1, pass1_summaries, pass1_players = fit_pass1(
        args.corpus_root, args.pass1_parsed_root
    )
    pass2, pass2_summaries, pass2_players = fit_pass2(args.pass2_root)

    ledger_after = _ledger_digest()

    per_dimension = {**pass1, **pass2}
    summaries = {**pass1_summaries, **pass2_summaries}

    # Assertions 1, 2 and 4. Assertion 3 runs on the finished document.
    check_negative_control(summaries[NEGATIVE_CONTROL])
    check_reliability_range(per_dimension)
    check_candidate_test_untouched(ledger_before, ledger_after)

    slates = assemble_slates(per_dimension)

    slate_sizes = Counter(len(slate) for slate in slates.values())
    sections_covered = Counter(
        len({finding.section for finding in slate}) for slate in slates.values()
    )
    above_line = Counter(
        sum(1 for finding in slate if finding.score > SCORE_LINE) for slate in slates.values()
    )
    top_dimension = Counter(slate[0].key for slate in slates.values() if slate)
    top_scores = [slate[0].score for slate in slates.values() if slate]
    players_with_full_slate = sum(1 for slate in slates.values() if len(slate) == REPORT_SLOTS)
    players_at_the_floor = sum(1 for slate in slates.values() if len(slate) == FINDING_FLOOR)
    players_below_the_floor = sum(1 for slate in slates.values() if len(slate) < FINDING_FLOOR)
    players_with_three_above = sum(players for count, players in above_line.items() if count >= 3)

    document: dict[str, Any] = {
        "schema_version": PIPELINE_VERSION,
        "code_sha": git_sha(),
        "split": DISCOVERY,
        "identities_included": False,
        "new_provider_calls": 0,
        "candidate_test_read": False,
        "publication_thresholds_chosen": False,
        "score_line": SCORE_LINE,
        "report_slots": REPORT_SLOTS,
        "finding_floor": FINDING_FLOOR,
        "owner_decisions_applied": ["D1"],
        "finding_sections": list(FINDING_SECTIONS),
        "corpus": manifest_digests(corpus_paths(args.corpus_root).root),
        "feature_version": FEATURE_VERSION,
        "pass2_feature_version": PASS2_FEATURE_VERSION,
        "pass2_observation_version": OBSERVATION_VERSION,
        "inference_version": inference.INFERENCE_VERSION,
        "ranking_model_version": RANKING_MODEL_VERSION,
        "candidate_definition_version": CANDIDATE_DEFINITION_VERSION,
        "denominators": {
            "pass1_discovery_players": pass1_players,
            "pass2_discovery_players": pass2_players,
            "players_with_any_finding": len(slates),
        },
        "dimensions": summaries,
        "slates": {
            "size_histogram": {str(k): v for k, v in sorted(slate_sizes.items())},
            "sections_covered_histogram": {str(k): v for k, v in sorted(sections_covered.items())},
            "findings_above_line_histogram": {str(k): v for k, v in sorted(above_line.items())},
            "players_with_full_slate": players_with_full_slate,
            "players_trimmed_to_the_floor": players_at_the_floor,
            "players_under_the_floor_for_lack_of_dimensions": players_below_the_floor,
            "share_with_full_slate": round(players_with_full_slate / len(slates), 6)
            if slates
            else 0.0,
            "share_with_three_above_line": round(players_with_three_above / len(slates), 6)
            if slates
            else 0.0,
            "top_finding_score": _describe(top_scores),
            "top_dimension_counts": {key: count for key, count in sorted(top_dimension.items())},
        },
        "assertions": {
            "negative_control_is_silent": True,
            "reliability_within_unit_interval": True,
            "candidate_test_ledger_unchanged": True,
            "no_pseudonyms_in_output": None,  # filled in below, after the check
        },
    }

    pseudonyms = {p for dimensions in per_dimension.values() for p in dimensions}
    check_no_pseudonyms(document, pseudonyms)
    document["assertions"]["no_pseudonyms_in_output"] = True

    Path(args.out).write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {args.out}")
    print(
        f"players with a slate: {len(slates)}; full slate of {REPORT_SLOTS}: "
        f"{players_with_full_slate} "
        f"({document['slates']['share_with_full_slate']:.3f}); "
        f"three or more above {SCORE_LINE}: "
        f"{document['slates']['share_with_three_above_line']:.3f}"
    )
    print("all four acceptance assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

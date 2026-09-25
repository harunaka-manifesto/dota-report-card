#!/usr/bin/env python3
"""Fit the D2 strength-band cut points and sweep the D7 support minimum.

Owner decisions D2 and D7 are settled in principle and provisional in value.
This is the machinery that makes them final. It takes a ``--split`` so the
same code fits on DISCOVERY (a dry run, which is what the committed output
is) and later on CALIBRATION_RESERVED without a line changing.

**D2 — absolute cut points on ``|z| * reliability``.** The owner rejected
population terciles, so a cut point is not "where a third of Findings fall".
What makes an absolute cut good is that the band it assigns is *not an
accident of measurement error*: a Finding whose 95% interval straddles the cut
has been given a band the data cannot support. So each candidate cut is scored
by how many Findings it labels ambiguously, subject to every band staying
populated enough to be worth having.

**D7 — minimum matches per arm.** Raising it buys precision and costs
coverage. The sweep reports both at each candidate so the trade is visible
rather than argued.

Aggregate-only output. No per-player row, account or match identifier. Refuses
SEALED_VALIDATION outright: it is not a calibration set and the owner's
approval to open it has not been given.

Read-only on the corpus. No provider call.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "legacy" / "services" / "api"))
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))

from report_card.player_analysis_v7.research import inference  # noqa: E402
from report_card.player_analysis_v7.research.corpus import (  # noqa: E402
    DISCOVERY,
    SEALED_VALIDATION,
    corpus_paths,
)
from report_card.player_analysis_v7.research.features import load_frames  # noqa: E402
from report_card.player_analysis_v7.research.owner_decisions import (  # noqa: E402
    DECISIONS_VERSION,
    SEALED_VALIDATION_APPROVED,
)
from report_card.player_analysis_v7.research.pass2_features import (  # noqa: E402
    group_rows_by_account,
)
from report_card.player_analysis_v7.research.pass2_observations import (  # noqa: E402
    OBSERVATION_REGISTRY,
    chronological,
)
from report_card.player_analysis_v7.research.pass2_tables import (  # noqa: E402
    is_pass2_product_context,
    iter_pass2_players,
)
from report_card.player_analysis_v7.research.ranking import (  # noqa: E402
    INTERVAL_Z,
    rank_player,
)
from report_card.player_analysis_v7.research.recommendation import (  # noqa: E402
    ARM_LOSS,
    ARM_WIN,
    build_personal_contrast_matrix,
    dimension_scale,
    eligible_dimensions,
    gap_reliability,
    opportunities,
    priority,
    standardized_gap,
)
from report_card.player_analysis_v7.research.registry import FAMILY_BY_NAME  # noqa: E402
from report_card.player_analysis_v7.research.tournament import collect  # noqa: E402

from legacy.scripts.v7_discovery_screen import FROZEN_SERIOUS_CANDIDATES  # noqa: E402
from legacy.scripts.v7_finding_pipeline import (  # noqa: E402
    DEPENDENCE_BATCH_LENGTHS,
    NEGATIVE_CONTROL,
    SECTION_BY_FAMILY,
    fit_dimension,
)

CALIBRATION_VERSION = "v7-cut-point-calibration-1.0.0"

#: Candidate cut points swept for the "pronounced" and "moderate" bands.
PRONOUNCED_CANDIDATES = (1.5, 1.75, 2.0, 2.25, 2.5, 3.0)
MODERATE_CANDIDATES = (0.5, 0.75, 1.0, 1.25, 1.5)

#: A band carrying fewer than this share of Findings is not worth a word.
MIN_BAND_SHARE = 0.05

#: Candidate minimums for D7.
SUPPORT_CANDIDATES = (10, 15, 20, 25, 30)


def _quantiles(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    ordered = sorted(values)

    def q(p: float) -> float:
        return ordered[min(len(ordered) - 1, int(p * (len(ordered) - 1) + 0.5))]

    return {
        "n": len(ordered),
        "median": round(statistics.median(ordered), 6),
        "p5": round(q(0.05), 6),
        "p95": round(q(0.95), 6),
    }


def score_interval(z_value: float, reliability_value: float, se_z: float) -> tuple[float, float]:
    """A 95% interval on ``|z| * r``, propagated from the interval on ``z``.

    ``r`` is treated as fixed: it is a variance-ratio estimated across the
    whole population, so its uncertainty is an order of magnitude below the
    per-player uncertainty in ``z`` and folding it in would overstate the
    interval's honesty rather than its width.
    """

    low_z = abs(z_value) - INTERVAL_Z * se_z
    high_z = abs(z_value) + INTERVAL_Z * se_z
    return max(0.0, low_z) * reliability_value, max(0.0, high_z) * reliability_value


def fit_d2(scores: list[tuple[float, float, float]]) -> dict[str, Any]:
    """Choose band cut points that minimise ambiguous band assignments.

    ``scores`` is ``(score, interval_low, interval_high)`` per Finding.
    """

    total = len(scores)
    rows: list[dict[str, Any]] = []
    for pronounced in PRONOUNCED_CANDIDATES:
        for moderate in MODERATE_CANDIDATES:
            if moderate >= pronounced:
                continue
            n_pronounced = sum(1 for s, _, _ in scores if s >= pronounced)
            n_moderate = sum(1 for s, _, _ in scores if moderate <= s < pronounced)
            n_slight = total - n_pronounced - n_moderate
            # A Finding is ambiguous when its interval straddles a cut: the
            # data does not distinguish its band from the neighbouring one.
            ambiguous = sum(
                1
                for _, low, high in scores
                if (low < pronounced <= high) or (low < moderate <= high)
            )
            shares = (n_pronounced / total, n_moderate / total, n_slight / total)
            rows.append(
                {
                    "pronounced_at": pronounced,
                    "moderate_at": moderate,
                    "share_pronounced": round(shares[0], 6),
                    "share_moderate": round(shares[1], 6),
                    "share_slight": round(shares[2], 6),
                    "ambiguous_share": round(ambiguous / total, 6),
                    "all_bands_populated": min(shares) >= MIN_BAND_SHARE,
                }
            )
    viable = [row for row in rows if row["all_bands_populated"]]
    best = min(viable, key=lambda row: (row["ambiguous_share"], -row["moderate_at"])) if viable else None
    return {
        "findings_scored": total,
        "min_band_share": MIN_BAND_SHARE,
        "candidates": rows,
        "proposed": best,
    }


def collect_finding_scores(corpus_root: str, pass2_root: str, split: str) -> list[tuple[float, float, float]]:
    paths = corpus_paths(corpus_root)
    frames = load_frames(paths, frozenset({split}), with_parsed=True)

    scored: list[tuple[float, float, float]] = []

    def absorb(key: str, section: str, per_player: Any, *, arm_family: bool, treated: Any, control: Any) -> None:
        dimensions, summary = fit_dimension(
            key, section, per_player, arm_family=arm_family, treated=treated, control=control
        )
        if not dimensions or summary.get("tau", 0.0) <= 0.0:
            return
        for dimension in dimensions.values():
            finding = rank_player([dimension])[0]
            se_z = dimension.se * (dimension.dependence_inflation**0.5) / dimension.tau
            low, high = score_interval(finding.z, finding.reliability, se_z)
            scored.append((finding.score, low, high))

    for name in FROZEN_SERIOUS_CANDIDATES:
        if name == NEGATIVE_CONTROL:
            continue
        family = FAMILY_BY_NAME[name]
        absorb(
            name,
            SECTION_BY_FAMILY.get(name, "what_is_good"),
            collect(name, frames),
            arm_family=family.arm_family,
            treated=family.treated,
            control=family.control,
        )

    rows = (row for row in iter_pass2_players(pass2_root) if is_pass2_product_context(row))
    by_account = {
        pseudonym: chronological(account_rows)
        for pseudonym, account_rows in group_rows_by_account(rows).items()
    }
    for key, dimension in OBSERVATION_REGISTRY.items():
        per_player = [
            (pseudonym, series)
            for pseudonym, account_rows in sorted(by_account.items())
            if (series := dimension.fn(account_rows))
        ]
        absorb(
            key,
            dimension.section,
            per_player,
            arm_family=dimension.arm_family,
            treated=dimension.treated,
            control=dimension.control,
        )
    return scored


def sweep_d7(pass2_root: str) -> dict[str, Any]:
    """Coverage against precision at each candidate support minimum."""

    rows = (row for row in iter_pass2_players(pass2_root) if is_pass2_product_context(row))
    by_account = {
        pseudonym: chronological(account_rows)
        for pseudonym, account_rows in group_rows_by_account(rows).items()
    }
    eligible = eligible_dimensions()
    out: list[dict[str, Any]] = []

    for minimum in SUPPORT_CANDIDATES:
        players_with_any: set[str] = set()
        reliabilities: list[float] = []
        priorities: list[float] = []
        refused = 0
        for dimension in eligible.values():
            per_player = []
            for pseudonym, account_rows in sorted(by_account.items()):
                series = opportunities(account_rows, dimension)
                if not series:
                    continue
                wins = sum(1 for o in series if o.arm == ARM_WIN)
                losses = sum(1 for o in series if o.arm == ARM_LOSS)
                if wins < minimum or losses < minimum:
                    refused += 1
                    continue
                per_player.append((pseudonym, series))
            if len(per_player) < 2:
                continue
            matrix = build_personal_contrast_matrix(per_player)
            results = [r for r in inference.infer_all(matrix) if r.p_value == r.p_value]
            if not results:
                continue
            curve = inference.variance_ratio_curve(matrix, batch_lengths=DEPENDENCE_BATCH_LENGTHS)
            usable = [b for b in DEPENDENCE_BATCH_LENGTHS if b > 1 and curve.get(b) == curve.get(b)]
            dependence = max(1.0, curve[max(usable)]) if usable else 1.0
            scale = dimension_scale(matrix)
            for result in results:
                players_with_any.add(result.pseudonym)
                r_value = gap_reliability(result.standard_error, scale, dependence)
                reliabilities.append(r_value)
                priorities.append(
                    priority(
                        standardized_gap(result.delta, scale), r_value, dimension.actionability
                    )
                )
        out.append(
            {
                "minimum_per_arm": minimum,
                "players_with_a_recommendation": len(players_with_any),
                "player_dimension_pairs_refused": refused,
                "gap_reliability": _quantiles(reliabilities),
                "priority": _quantiles(priorities),
            }
        )
        print(
            f"D7 min={minimum:>3d} players={len(players_with_any):>4d} "
            f"refused={refused:>5d} rel_median={out[-1]['gap_reliability'].get('median')}",
            flush=True,
        )
    return {"candidates": out}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", required=True)
    parser.add_argument("--pass2-root", required=True)
    parser.add_argument("--split", default=DISCOVERY)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    if args.split == SEALED_VALIDATION and not SEALED_VALIDATION_APPROVED:
        raise SystemExit(
            "refusing to read SEALED_VALIDATION: it is the final untouched exam and "
            "the owner has not approved opening it (owner decision D8)"
        )

    scores = collect_finding_scores(args.corpus_root, args.pass2_root, args.split)
    print(f"scored {len(scores)} player-Findings on {args.split}", flush=True)
    d2 = fit_d2(scores)
    d7 = sweep_d7(args.pass2_root)

    document = {
        "schema_version": CALIBRATION_VERSION,
        "owner_decisions_version": DECISIONS_VERSION,
        "split": args.split,
        "is_dry_run_on_discovery": args.split == DISCOVERY,
        "identities_included": False,
        "new_provider_calls": 0,
        "sealed_validation_read": False,
        "d2_strength_bands": d2,
        "d7_support_minimum": d7,
    }
    serialized = json.dumps(document, indent=2, sort_keys=True)
    if "v7p_" in serialized:
        raise RuntimeError("a pseudonym reached the calibration output")
    Path(args.out).write_text(serialized + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    if d2["proposed"]:
        p = d2["proposed"]
        print(
            f"D2 proposed: pronounced >= {p['pronounced_at']}, moderate >= {p['moderate_at']} "
            f"({p['ambiguous_share']:.1%} ambiguous)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

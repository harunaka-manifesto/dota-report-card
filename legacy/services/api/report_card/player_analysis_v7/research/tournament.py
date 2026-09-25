"""The V7 statistical feasibility tournament.

One evaluation per frozen candidate family, plus the declared robustness probes
that test the judgement calls discovery flagged for a second opinion. Every
number this module produces is reported with its denominator, and every
denominator is one of the five the task packet requires:

``sampled``
    every account drawn into the split.
``product_eligible``
    accounts with at least one ordinary-lobby match they finished.
``structurally_eligible``
    accounts for which the family produces at least one opportunity.
``information_eligible``
    accounts that additionally clear the family's support bar and can supply
    enough valid blocks for the dependence-robust standard error.
``provisionally_qualified``
    information-eligible accounts whose two-sided p-value clears the phase's
    provisional level. This is a comparison scale for candidates, not a
    publication rule and not a multiplicity-corrected level.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from report_card.player_analysis_v7.research import inference
from report_card.player_analysis_v7.research.features import Opportunity, PlayerFrame, extract
from report_card.player_analysis_v7.research.inference import (
    PROVISIONAL_ALPHA,
    block_config,
    build_matrix,
    infer_all,
    measure_type_i,
    minimum_detectable_effect,
    pool,
    split_half_stability,
    variance_ratio_curve,
)
from report_card.player_analysis_v7.research.registry import Family
from report_card.player_analysis_v7.research.screen import (
    _mean,
    _pearson,
    eta_squared,
    quantile,
    spearman,
)

TOURNAMENT_VERSION = "v7-luna-c-tournament-1.0.0"


@dataclass
class Denominators:
    sampled: int
    product_eligible: int
    parsed_eligible: int


def collect(name: str, frames: Sequence[PlayerFrame]) -> list[tuple[str, list[Opportunity]]]:
    out = []
    for frame in frames:
        opportunities = extract(name, frame)
        if opportunities:
            out.append((frame.pseudonym, opportunities))
    return out


def _quantiles(values: Sequence[float]) -> dict[str, float]:
    ordered = sorted(v for v in values if v == v)
    if not ordered:
        return {"p25": float("nan"), "median": float("nan"), "p75": float("nan")}
    return {
        "p25": quantile(ordered, 0.25),
        "median": quantile(ordered, 0.50),
        "p75": quantile(ordered, 0.75),
    }


@dataclass
class Evaluation:
    family: str
    label: str
    split: str
    parsed_dependent: bool
    arm_family: bool
    support_bar: int
    denominator_sampled: int
    denominator_product_eligible: int
    denominator_applicable: int
    structurally_eligible: int
    information_eligible: int
    provisionally_qualified_01: int
    provisionally_qualified_05: int
    reach_of_sampled: float
    reach_of_applicable: float
    qualified_share_of_information_eligible: float
    opportunities: int
    obs_p25: float
    obs_median: float
    obs_p75: float
    delta_median: float
    abs_delta_median: float
    delta_p10: float
    delta_p90: float
    se_p25: float
    se_median: float
    se_p75: float
    mde_p25: float
    mde_median: float
    mde_p75: float
    dependence_inflation_median: float
    variance_ratio: dict[str, float]
    tau: float
    mu: float
    i_squared: float
    shrinkage_p10: float
    shrinkage_median: float
    shrinkage_p90: float
    shrinkage_reach_inflation: float
    split_half_random_r: float
    split_half_random_sb: float
    split_half_chrono_r: float
    split_half_chrono_sb: float
    split_half_players: int
    projection_drift: float
    eta2: dict[str, float] = field(default_factory=dict)
    type_i: list[dict[str, Any]] = field(default_factory=list)
    seconds: float = 0.0
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate(
    name: str,
    family: Family,
    frames: Sequence[PlayerFrame],
    denominators: Denominators,
    *,
    split: str,
    seed: int,
    label: str = "primary",
    drop_factors: Sequence[str] = (),
    type_i_replicates: int = 0,
    per_player: Sequence[tuple[str, Sequence[Opportunity]]] | None = None,
    geometry_override: dict[str, int] | None = None,
    notes: Sequence[str] = (),
) -> tuple[Evaluation, list[inference.PlayerInference], inference.FamilyMatrix | None]:
    """Run the frozen inference design over one family view."""

    started = time.perf_counter()
    collected = list(per_player) if per_player is not None else collect(name, frames)
    applicable = denominators.parsed_eligible if family.parsed else denominators.product_eligible
    if not collected:
        empty = Evaluation(
            family=name,
            label=label,
            split=split,
            parsed_dependent=family.parsed,
            arm_family=family.arm_family,
            support_bar=family.support,
            denominator_sampled=denominators.sampled,
            denominator_product_eligible=denominators.product_eligible,
            denominator_applicable=applicable,
            structurally_eligible=0,
            information_eligible=0,
            provisionally_qualified_01=0,
            provisionally_qualified_05=0,
            reach_of_sampled=0.0,
            reach_of_applicable=0.0,
            qualified_share_of_information_eligible=float("nan"),
            opportunities=0,
            obs_p25=float("nan"),
            obs_median=float("nan"),
            obs_p75=float("nan"),
            delta_median=float("nan"),
            abs_delta_median=float("nan"),
            delta_p10=float("nan"),
            delta_p90=float("nan"),
            se_p25=float("nan"),
            se_median=float("nan"),
            se_p75=float("nan"),
            mde_p25=float("nan"),
            mde_median=float("nan"),
            mde_p75=float("nan"),
            dependence_inflation_median=float("nan"),
            variance_ratio={},
            tau=float("nan"),
            mu=float("nan"),
            i_squared=float("nan"),
            shrinkage_p10=float("nan"),
            shrinkage_median=float("nan"),
            shrinkage_p90=float("nan"),
            shrinkage_reach_inflation=float("nan"),
            split_half_random_r=float("nan"),
            split_half_random_sb=float("nan"),
            split_half_chrono_r=float("nan"),
            split_half_chrono_sb=float("nan"),
            split_half_players=0,
            projection_drift=0.0,
            seconds=time.perf_counter() - started,
            notes=[*notes, "no opportunities produced"],
        )
        return empty, [], None

    matrix = build_matrix(
        collected,
        arm_family=family.arm_family,
        treated=family.treated,
        control=family.control,
        drop_factors=drop_factors,
    )

    # The support bar declared in the frozen registry is an opportunity count;
    # the block machinery adds an information requirement on top of it.
    # ``geometry_override`` exists for descriptive probes only, where two views
    # of the same family are compared as point estimates and no p-value is read.
    # It is always recorded in the probe's notes.
    geometry = geometry_override or block_config(family.arm_family)
    supported = {
        pseudonym for pseudonym, indices in matrix.order.items() if len(indices) >= family.support
    }
    results = [r for r in infer_all(matrix, **geometry) if r.pseudonym in supported]

    counts = [len(indices) for indices in matrix.order.values()]
    deltas = sorted(r.delta for r in results)
    errors = [r.standard_error for r in results]
    inflation = [
        r.standard_error / r.naive_standard_error
        for r in results
        if r.naive_standard_error > 0
    ]
    mdes = [minimum_detectable_effect(r.standard_error, r.df) for r in results]
    curve = variance_ratio_curve(matrix)
    pooled = pool(results, alpha=PROVISIONAL_ALPHA)

    random_r, random_sb, players = split_half_stability(matrix, chronological=False, seed=seed)
    chrono_r, chrono_sb, chrono_players = split_half_stability(matrix, chronological=True, seed=seed)

    eta2 = {
        matrix.encoded.factors[position]: eta_squared(
            matrix.encoded.codes[position], matrix.encoded.levels[position], matrix.encoded.value
        )
        for position in range(len(matrix.encoded.factors))
    }

    type_i: list[dict[str, Any]] = []
    if type_i_replicates:
        # A contrast family's circular-shift null preserves the real dependence
        # exactly, so one construction settles it. A level family has no such
        # null, so it is swept against a range of planted dependence lengths and
        # the whole curve is reported.
        plans: list[tuple[str, int, str]] = (
            [("circular", 0, "circular"), ("iid", 0, "iid")]
            if family.arm_family
            else [
                ("iid", 0, "iid"),
                ("block", 25, "block_L25"),
                ("block", 100, "block_L100"),
                ("block", 200, "block_L200"),
            ]
        )
        for mode, length, label_ in plans:
            measured = measure_type_i(
                matrix,
                replicates=type_i_replicates,
                seed=seed,
                null_mode=mode,
                block_length=length or 25,
                **geometry,
            )
            row = asdict(measured)
            row["null_name"] = label_
            row["verdict"] = measured.verdict()
            type_i.append(row)

    qualified_01 = sum(1 for r in results if r.p_value == r.p_value and r.p_value < 0.01)
    qualified_05 = sum(1 for r in results if r.p_value == r.p_value and r.p_value < 0.05)

    evaluation = Evaluation(
        family=name,
        label=label,
        split=split,
        parsed_dependent=family.parsed,
        arm_family=family.arm_family,
        support_bar=family.support,
        denominator_sampled=denominators.sampled,
        denominator_product_eligible=denominators.product_eligible,
        denominator_applicable=applicable,
        structurally_eligible=len(matrix.order),
        information_eligible=len(results),
        provisionally_qualified_01=qualified_01,
        provisionally_qualified_05=qualified_05,
        reach_of_sampled=len(results) / denominators.sampled,
        reach_of_applicable=len(results) / applicable if applicable else float("nan"),
        qualified_share_of_information_eligible=(
            qualified_01 / len(results) if results else float("nan")
        ),
        opportunities=len(matrix.residual),
        obs_p25=quantile(sorted(counts), 0.25),
        obs_median=quantile(sorted(counts), 0.50),
        obs_p75=quantile(sorted(counts), 0.75),
        delta_median=quantile(deltas, 0.50),
        abs_delta_median=quantile(sorted(abs(d) for d in deltas), 0.50),
        delta_p10=quantile(deltas, 0.10),
        delta_p90=quantile(deltas, 0.90),
        se_p25=_quantiles(errors)["p25"],
        se_median=_quantiles(errors)["median"],
        se_p75=_quantiles(errors)["p75"],
        mde_p25=_quantiles(mdes)["p25"],
        mde_median=_quantiles(mdes)["median"],
        mde_p75=_quantiles(mdes)["p75"],
        dependence_inflation_median=_quantiles(inflation)["median"],
        variance_ratio={str(b): value for b, value in curve.items()},
        tau=pooled.tau,
        mu=pooled.mu,
        i_squared=pooled.i_squared,
        shrinkage_p10=pooled.shrinkage_p10,
        shrinkage_median=pooled.shrinkage_median,
        shrinkage_p90=pooled.shrinkage_p90,
        shrinkage_reach_inflation=pooled.shrinkage_reach_inflation,
        split_half_random_r=random_r,
        split_half_random_sb=random_sb,
        split_half_chrono_r=chrono_r,
        split_half_chrono_sb=chrono_sb,
        split_half_players=min(players, chrono_players),
        projection_drift=matrix.projection_drift,
        eta2=eta2,
        type_i=type_i,
        seconds=time.perf_counter() - started,
        notes=list(notes),
    )
    return evaluation, results, matrix


def agreement(
    left: Sequence[inference.PlayerInference],
    right: Sequence[inference.PlayerInference],
) -> dict[str, Any]:
    """Per-player agreement between two views of the same family."""

    left_map = {r.pseudonym: r.delta for r in left}
    right_map = {r.pseudonym: r.delta for r in right}
    shared = sorted(set(left_map) & set(right_map))
    if len(shared) < 20:
        return {"players": len(shared), "pearson": float("nan"), "spearman": float("nan")}
    a = [left_map[k] for k in shared]
    b = [right_map[k] for k in shared]
    return {
        "players": len(shared),
        "pearson": _pearson(a, b),
        "spearman": spearman(a, b),
        "sd_ratio": (
            math.sqrt(sum((x - _mean(b)) ** 2 for x in b) / max(len(b) - 1, 1))
            / math.sqrt(sum((x - _mean(a)) ** 2 for x in a) / max(len(a) - 1, 1))
            if len(a) > 1
            else float("nan")
        ),
    }


__all__ = [
    "TOURNAMENT_VERSION",
    "Denominators",
    "Evaluation",
    "agreement",
    "collect",
    "evaluate",
]

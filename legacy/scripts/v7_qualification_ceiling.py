#!/usr/bin/env python3
"""How far can a significance-gated Finding reach, at best?

This is a diagnostic, not a threshold choice. It sets no alpha, picks no
publication rule, and reads no data: it takes the variance components the
tournament already measured and asks what share of players *could* qualify
under a rule of the form "this player's effect differs from the population
average", for any candidate with those components.

The answer is a closed form. Under the tournament's own model

    delta_p          ~ N(mu, tau^2)          true player effects
    delta_hat_p | .. ~ N(delta_p, SE_p^2)    what we can measure

the observed deviation ``delta_hat_p - mu`` is marginally
``N(0, tau^2 + SE_p^2)``, so a two-sided test at critical value ``z`` rejects
with probability

    q(z, r) = 2 * Phi( -z / sqrt(1 + r^2) ),      r = tau / SE_p

which depends on the data only through the signal-to-noise ratio ``r``. The
ratio needed for a given reach is therefore also closed form, and it is the
honest ceiling: it assumes a perfectly calibrated test, no multiplicity
correction, no effect-size requirement, and no stability gate. Every one of
those makes the real number smaller.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import NormalDist
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

NORMAL = NormalDist()

#: Reported purely as a comparison scale, matching the tournament's provisional
#: levels. Nothing here selects a publication alpha.
REPORTED_CRITICAL_VALUES = {"0.05": 1.959963984540054, "0.01": 2.5758293035489004}


def qualified_share(critical_value: float, ratio: float) -> float:
    """Share of players a perfectly calibrated two-sided test would reject."""

    return 2.0 * NORMAL.cdf(-critical_value / math.sqrt(1.0 + ratio * ratio))


def required_ratio(critical_value: float, target_share: float) -> float:
    """``tau / SE`` needed to reach ``target_share``, or ``inf`` if impossible."""

    if not 0.0 < target_share < 1.0:
        raise ValueError("target share must be strictly between 0 and 1")
    bound = -NORMAL.inv_cdf(target_share / 2.0)
    # A target at or below the test's own nominal rate needs no signal at all.
    # The comparison is relative because the quantile function and the tabulated
    # critical value can disagree in the last bit at exactly that boundary.
    if bound >= critical_value * (1.0 - 1e-12):
        return 0.0
    # Clamped because a target only just above the nominal rate lands on a
    # quantity that is zero in exact arithmetic and can go slightly negative in
    # floating point.
    return math.sqrt(max(0.0, (critical_value / bound) ** 2 - 1.0))


def portfolio_share_at_least(per_candidate: float, size: int, at_least: int) -> float:
    """Independent-candidate binomial bound on P(at least ``at_least`` of ``size``).

    Independence is not true — the candidates are correlated — but it is the
    convenient case, and a convenient case that already fails is a stronger
    statement than one that fails under a pessimistic assumption.
    """

    total = 0.0
    for wins in range(at_least, size + 1):
        total += (
            math.comb(size, wins)
            * per_candidate**wins
            * (1.0 - per_candidate) ** (size - wins)
        )
    return total


def required_per_candidate(size: int, at_least: int, target: float) -> float:
    low, high = 0.0, 1.0
    for _ in range(200):
        mid = (low + high) / 2.0
        if portfolio_share_at_least(mid, size, at_least) < target:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def build(tournament_discovery: Path) -> dict[str, Any]:
    payload = json.loads(tournament_discovery.read_text(encoding="utf-8"))
    rows = []
    for evaluation in payload["evaluations"]:
        tau = evaluation["tau"]
        rows.append(
            {
                "family": evaluation["family"],
                "tau": tau,
                "se_p25": evaluation["se_p25"],
                "se_median": evaluation["se_median"],
                "se_p75": evaluation["se_p75"],
                "ratio_at_se_median": tau / evaluation["se_median"]
                if evaluation["se_median"]
                else None,
                "ratio_at_se_p25": tau / evaluation["se_p25"] if evaluation["se_p25"] else None,
                "predicted_share": {
                    level: qualified_share(z, tau / evaluation["se_median"])
                    if evaluation["se_median"]
                    else None
                    for level, z in REPORTED_CRITICAL_VALUES.items()
                },
                "observed_share_of_information_eligible_01": evaluation[
                    "qualified_share_of_information_eligible"
                ],
                "information_eligible": evaluation["information_eligible"],
                "parsed_dependent": evaluation["parsed_dependent"],
            }
        )
    rows.sort(key=lambda row: -(row["ratio_at_se_median"] or 0.0))

    targets = (0.60, 0.70, 0.75, 0.80, 0.85, 0.90)
    ratio_table = {
        level: {f"{target:.2f}": required_ratio(z, target) for target in targets}
        for level, z in REPORTED_CRITICAL_VALUES.items()
    }

    portfolio = {
        "five_candidates_at_least_three": {
            f"{target:.2f}": required_per_candidate(5, 3, target)
            for target in (0.60, 0.70, 0.80, 0.85, 0.90)
        },
        "implied_ratio_for_at_least_three_of_five": {
            level: {
                f"{target:.2f}": required_ratio(z, required_per_candidate(5, 3, target))
                for target in (0.60, 0.70, 0.80, 0.85, 0.90)
            }
            for level, z in REPORTED_CRITICAL_VALUES.items()
        },
    }

    return {
        "schema_version": "v7-qualification-ceiling-1.0.0",
        "source": str(tournament_discovery),
        "source_code_sha": payload["code_sha"],
        "source_design_digest": payload["design_digest"],
        "split": payload["split"],
        "is_a_threshold_choice": False,
        "note": (
            "Closed-form ceiling under the tournament's own variance components. "
            "Assumes a perfectly calibrated test, no multiplicity correction, no "
            "effect-size requirement and no stability gate, so it is an upper bound "
            "on what a significance-gated Finding can reach."
        ),
        "families": rows,
        "required_ratio_for_share": ratio_table,
        "portfolio": portfolio,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tournament-discovery", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    document = build(Path(args.tournament_discovery))
    Path(args.out).write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

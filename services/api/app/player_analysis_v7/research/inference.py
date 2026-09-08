"""Provisional per-player inference for V7 candidate families.

This module is the statistical half of the Luna C feasibility tournament. It
answers, for one candidate family and one player, the only question a personal
Finding may ask:

    is *this* player's context-adjusted behaviour credibly different from the
    population's, given this player's own volume and context?

Nothing here chooses a publication threshold, freezes a multiplicity family, or
builds a population percentile. Those are later decisions and are deliberately
out of scope (see the task packet and learning 6).

Design, stated before any p-value is computed
---------------------------------------------

**Unit of observation.** One *opportunity*, as emitted by
``app.player_analysis_v7.research.features``. Every extractor emits opportunities in the
chronological order of the player's own product-context matches; this module
depends on that ordering and ``tests/unit/test_v7_research_inference.py``
asserts it.

**Estimand.** Let ``r_i`` be the opportunity response after additive
categorical context effects have been projected out over the whole split
(``screen.project_out_context``). For a *level* family the estimand for player
``p`` is

    delta_p = E[ r_i | player p ] ,

the player's context-adjusted deviation from the population. For a *contrast*
family, ``arm`` is carried as an ordinary context factor, so the population
average treatment effect is removed by the same projection, and

    delta_p = E[ r_i | p, treated ] - E[ r_i | p, control ]

is the player's *own* departure from the population's shared response. That is
what learning 9 requires: a response everybody shares is not identity.

**The null data-generating process.** It differs by family type, and the
difference is the point.

* *Contrast family.* H0(p): within player ``p``, conditional on that player's
  own sequence of opportunities, the arm label carries no information about the
  response. The null DGP re-labels the arms of ``p``'s own opportunities. The
  primary construction is a **circular shift** of the arm-label sequence, which
  preserves the autocorrelation of both the arm sequence and the response
  sequence exactly, and preserves the player's volume and arm counts exactly.
  An i.i.d. within-player permutation is carried as a secondary construction so
  that the cost of serial dependence is *measured* rather than assumed away.
* *Level family.* A within-player permutation leaves the player's mean
  unchanged, so it is not a null for this estimand — it would test nothing. The
  estimand-matching null is H0(p): ``p``'s opportunities are an exchangeable
  draw from the population's context-matched residual pool at ``p``'s own
  volume. The primary construction reassigns **contiguous blocks** of residuals
  between players inside a mode stratum, preserving each player's volume and
  block count and preserving within-block serial dependence. An i.i.d.
  restricted permutation inside finer context cells is carried as the secondary
  construction.

**Test statistic.** The player's opportunity sequence is cut into ``K``
contiguous equal-length blocks (batched means). The per-block statistic is the
block mean (level) or the block's treated-minus-control difference (contrast).
The estimate is the mean of the valid block statistics and the standard error
is ``sd(block statistics) / sqrt(K_valid)``, referred to Student ``t`` on
``K_valid - 1`` degrees of freedom, two-sided. Batching is what makes the
standard error robust to the serial dependence a 365-day history certainly
has; the ratio of the batched standard error to the naive i.i.d. one is
reported per family as the *dependence inflation factor*.

**Partial pooling.** ``delta_p ~ N(mu, tau^2)`` with ``delta_hat_p |
delta_p ~ N(delta_p, SE_p^2)``. ``tau^2`` is estimated by the Paule-Mandel
iteration, which is a moment estimator that does not assume the ``SE_p`` are
equal. The shrinkage factor ``B_p = tau^2 / (tau^2 + SE_p^2)`` is reported as a
distribution, never as a single number, and the qualification decision is made
on the **unshrunk** statistic. Shrinkage can only move an estimate towards the
population mean, so a qualification rule applied to shrunken estimates would
manufacture reach out of the prior; that failure mode is measured explicitly by
``shrinkage_reach_inflation``.

Everything is pure Python and deterministic given the seed.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.player_analysis_v7.research.screen import (
    ContextProjectionFit,
    Encoded,
    _mean,
    _pearson,
    _variance,
    encode,
    fit_context_projection,
    quantile,
    stable_seed,
)

INFERENCE_VERSION = "v7-luna-c-inference-1.0.0"

#: Target number of batched-means blocks per player. Twenty blocks give a
#: t reference with 19 degrees of freedom, which is enough for the tail to
#: behave while leaving each block long enough to absorb local dependence.
TARGET_BLOCKS = 20

#: A player needs at least this many *valid* blocks to be information-eligible.
MIN_BLOCKS = 8

#: Minimum opportunities per block. Below this the block statistic is too noisy
#: for a contrast family to find both arms inside it.
MIN_PER_BLOCK = 4

# The two family types get different block geometries, and the reason is
# measured rather than assumed. ``variance_ratio_curve`` over DISCOVERY shows
# that within-player residual dependence in this corpus has not plateaued by a
# batch length of 100 opportunities for any behavioural family (ratios of
# 1.7-5.3 at b=100, against 1.06 for the planted negative control). A contrast
# estimand differences that drift out within the player, and the circular-shift
# null - which preserves the real dependence exactly - confirms the contrast
# test is calibrated at 20 short blocks. A level estimand does not difference
# it out, so its blocks must be long enough to contain the dependence; even at
# a block length of 100 the level test remains anticonservative against a null
# with range 200, which is recorded as an open validity risk rather than
# hidden.
CONTRAST_TARGET_BLOCKS = 20
CONTRAST_MIN_BLOCKS = 8
CONTRAST_MIN_PER_BLOCK = 4

LEVEL_TARGET_BLOCKS = 20
LEVEL_MIN_BLOCKS = 4
LEVEL_MIN_PER_BLOCK = 100


def block_config(arm_family: bool) -> dict[str, int]:
    """Frozen block geometry for a family type."""

    if arm_family:
        return {
            "target_blocks": CONTRAST_TARGET_BLOCKS,
            "min_blocks": CONTRAST_MIN_BLOCKS,
            "min_per_block": CONTRAST_MIN_PER_BLOCK,
        }
    return {
        "target_blocks": LEVEL_TARGET_BLOCKS,
        "min_blocks": LEVEL_MIN_BLOCKS,
        "min_per_block": LEVEL_MIN_PER_BLOCK,
    }

#: Block length used by the level-family block-reassignment null. Long enough
#: to carry the within-player dependence that an i.i.d. permutation destroys.
NULL_BLOCK_LENGTH = 25

#: Nominal levels at which realised Type-I behaviour is reported.
ALPHA_PRIMARY = 0.01
ALPHA_SECONDARY = 0.05

#: Provisional per-player qualification level for this phase only. This is a
#: reporting convention so that candidates can be compared on one scale; it is
#: NOT a publication threshold and NOT a multiplicity-corrected level.
PROVISIONAL_ALPHA = ALPHA_PRIMARY


# ---------------------------------------------------------------------------
# distributions (pure Python; no third-party dependency)
# ---------------------------------------------------------------------------


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Lentz)."""

    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-16:
            break
    return h


def regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + b * math.log1p(-x) + a * math.log(x)
    ) * _betacf(b, a, 1.0 - x) / b


def student_t_two_sided_p(t_stat: float, df: int) -> float:
    """Two-sided p-value for Student ``t`` with ``df`` degrees of freedom."""

    if df < 1 or t_stat != t_stat or math.isinf(df):
        return float("nan")
    if math.isinf(t_stat):
        return 0.0
    x = df / (df + t_stat * t_stat)
    return max(0.0, min(1.0, regularized_incomplete_beta(df / 2.0, 0.5, x)))


def student_t_quantile(p: float, df: int) -> float:
    """Upper-tail quantile ``t`` with ``P(T > t) = p``, by bisection."""

    if df < 1:
        return float("nan")
    low, high = 0.0, 200.0
    target = 2.0 * p
    for _ in range(200):
        mid = 0.5 * (low + high)
        if student_t_two_sided_p(mid, df) > target:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


# ---------------------------------------------------------------------------
# blocks and the per-player statistic
# ---------------------------------------------------------------------------


def block_bounds(n: int, target: int = TARGET_BLOCKS, min_per_block: int = MIN_PER_BLOCK) -> list[tuple[int, int]]:
    """Contiguous, near-equal blocks over ``n`` chronologically ordered items."""

    if n <= 0:
        return []
    blocks = min(target, max(1, n // min_per_block))
    if blocks < 1:
        blocks = 1
    bounds = []
    for index in range(blocks):
        start = (index * n) // blocks
        end = ((index + 1) * n) // blocks
        if end > start:
            bounds.append((start, end))
    return bounds


@dataclass(frozen=True)
class PlayerInference:
    pseudonym: str
    delta: float
    standard_error: float
    naive_standard_error: float
    t_stat: float
    df: int
    p_value: float
    n: int
    n_treated: int
    n_control: int
    blocks: int


def player_inference(
    pseudonym: str,
    values: Sequence[float],
    arms: Sequence[int] | None,
    treated_code: int | None,
    control_code: int | None,
    *,
    target_blocks: int = TARGET_BLOCKS,
    min_blocks: int = MIN_BLOCKS,
    min_per_block: int = MIN_PER_BLOCK,
) -> PlayerInference | None:
    """Batched-means estimate, dependence-robust SE and two-sided p-value.

    ``values`` must be in chronological order. Returns ``None`` when the player
    cannot supply ``min_blocks`` valid blocks — that player is structurally
    eligible but not information-eligible, and the caller must count them in
    that denominator rather than dropping them silently.
    """

    n = len(values)
    if n == 0:
        return None
    contrast = arms is not None and treated_code is not None and control_code is not None
    stats: list[float] = []
    n_treated = n_control = 0
    for start, end in block_bounds(n, target_blocks, min_per_block):
        if contrast:
            assert arms is not None
            treated_values = [values[i] for i in range(start, end) if arms[i] == treated_code]
            control_values = [values[i] for i in range(start, end) if arms[i] == control_code]
            if not treated_values or not control_values:
                continue
            n_treated += len(treated_values)
            n_control += len(control_values)
            stats.append(_mean(treated_values) - _mean(control_values))
        else:
            stats.append(_mean(values[start:end]))
    if len(stats) < min_blocks:
        return None
    delta = _mean(stats)
    spread = _variance(stats)
    if spread != spread or spread < 0:
        return None
    standard_error = math.sqrt(spread / len(stats))
    if contrast:
        assert arms is not None
        treated_all = [values[i] for i in range(n) if arms[i] == treated_code]
        control_all = [values[i] for i in range(n) if arms[i] == control_code]
        var_t = _variance(treated_all) if len(treated_all) > 1 else 0.0
        var_c = _variance(control_all) if len(control_all) > 1 else 0.0
        naive = math.sqrt(
            (var_t / len(treated_all) if treated_all else 0.0)
            + (var_c / len(control_all) if control_all else 0.0)
        )
    else:
        naive = math.sqrt(_variance(values) / n) if n > 1 else 0.0
    df = len(stats) - 1
    if standard_error <= 0.0:
        t_stat = 0.0 if delta == 0.0 else math.copysign(float("inf"), delta)
    else:
        t_stat = delta / standard_error
    return PlayerInference(
        pseudonym=pseudonym,
        delta=delta,
        standard_error=standard_error,
        naive_standard_error=naive,
        t_stat=t_stat,
        df=df,
        p_value=student_t_two_sided_p(t_stat, df),
        n=n if not contrast else n_treated + n_control,
        n_treated=n_treated,
        n_control=n_control,
        blocks=len(stats),
    )


# ---------------------------------------------------------------------------
# per-player views over an encoded family
# ---------------------------------------------------------------------------


@dataclass
class FamilyMatrix:
    """Residualised, per-player, chronologically ordered view of one family."""

    encoded: Encoded
    context_fit: ContextProjectionFit
    residual: list[float]
    projection_drift: float
    arm_family: bool
    treated_code: int | None
    control_code: int | None
    order: dict[str, list[int]] = field(default_factory=dict)

    def player_values(self, pseudonym: str) -> list[float]:
        return [self.residual[i] for i in self.order[pseudonym]]

    def player_arms(self, pseudonym: str) -> list[int]:
        return [self.encoded.arm[i] for i in self.order[pseudonym]]


def build_matrix(
    per_player: Sequence[tuple[str, Sequence[Any]]],
    *,
    arm_family: bool,
    treated: str | None,
    control: str | None,
    drop_factors: Sequence[str] = (),
) -> FamilyMatrix:
    """Encode, project out context, and index rows by player in input order.

    ``drop_factors`` removes named context factors from the projection. It
    exists for one declared robustness probe — whether removing ``hero``
    over-removes the Transfer signal — and its use is always reported.
    """

    if drop_factors:
        dropped = set(drop_factors)
        filtered: list[tuple[str, list[Any]]] = []
        for pseudonym, opportunities in per_player:
            kept = [
                type(opportunity)(
                    opportunity.value,
                    tuple(item for item in opportunity.ctx if item[0] not in dropped),
                    opportunity.arm,
                )
                for opportunity in opportunities
            ]
            filtered.append((pseudonym, kept))
        per_player = filtered
    encoded = encode(per_player, include_arm_as_factor=arm_family)
    context_fit = fit_context_projection(encoded)
    residual = list(context_fit.residual)
    order: dict[str, list[int]] = {}
    for index, pid in enumerate(encoded.player):
        order.setdefault(encoded.player_names[pid], []).append(index)
    treated_code = (
        encoded.arm_names.index(treated)
        if arm_family and treated is not None and treated in encoded.arm_names
        else None
    )
    control_code = (
        encoded.arm_names.index(control)
        if arm_family and control is not None and control in encoded.arm_names
        else None
    )
    return FamilyMatrix(
        encoded=encoded,
        context_fit=context_fit,
        residual=residual,
        projection_drift=context_fit.drift,
        arm_family=arm_family,
        treated_code=treated_code,
        control_code=control_code,
        order=order,
    )


def infer_all(matrix: FamilyMatrix, **kwargs: Any) -> list[PlayerInference]:
    results = []
    for pseudonym in sorted(matrix.order):
        values = matrix.player_values(pseudonym)
        arms = matrix.player_arms(pseudonym) if matrix.arm_family else None
        result = player_inference(
            pseudonym,
            values,
            arms,
            matrix.treated_code,
            matrix.control_code,
            **kwargs,
        )
        if result is not None:
            results.append(result)
    return results


# ---------------------------------------------------------------------------
# partial pooling
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PoolingResult:
    tau: float
    tau_squared: float
    mu: float
    players: int
    shrinkage_p10: float
    shrinkage_p25: float
    shrinkage_median: float
    shrinkage_p75: float
    shrinkage_p90: float
    i_squared: float
    shrinkage_reach_inflation: float


def paule_mandel_tau_squared(
    deltas: Sequence[float], errors: Sequence[float], iterations: int = 200
) -> tuple[float, float]:
    """Paule-Mandel moment estimate of ``tau^2`` and the weighted mean.

    Solves ``sum_p (delta_p - mu(tau^2))^2 / (SE_p^2 + tau^2) = P - 1`` by
    bisection. Unlike DerSimonian-Laird it does not assume the standard errors
    are homogeneous, which matters here because opportunity counts range over
    more than an order of magnitude between players.
    """

    p = len(deltas)
    if p < 3 or any(error <= 0 or error != error for error in errors):
        # A zero or missing standard error is degenerate, not infinitely
        # precise: pooling refuses it rather than dividing by zero.
        return float("nan"), _mean(deltas) if deltas else float("nan")

    def statistic(tau2: float) -> tuple[float, float]:
        weights = [1.0 / (error * error + tau2) for error in errors]
        total = sum(weights)
        mu = sum(w * d for w, d in zip(weights, deltas, strict=True)) / total
        q = sum(w * (d - mu) ** 2 for w, d in zip(weights, deltas, strict=True))
        return q, mu

    q0, mu0 = statistic(0.0)
    if q0 <= p - 1:
        return 0.0, mu0
    low, high = 0.0, max(1e-12, _variance(deltas))
    for _ in range(80):
        q, _mu = statistic(high)
        if q <= p - 1:
            break
        high *= 2.0
    for _ in range(iterations):
        mid = 0.5 * (low + high)
        q, _mu = statistic(mid)
        if q > p - 1:
            low = mid
        else:
            high = mid
    tau2 = 0.5 * (low + high)
    _q, mu = statistic(tau2)
    return tau2, mu


def pool(results: Sequence[PlayerInference], alpha: float = PROVISIONAL_ALPHA) -> PoolingResult:
    # Players whose residual series is exactly constant have a zero standard
    # error. They are degenerate rather than infinitely informative and are
    # excluded from the variance-components fit; the count is recoverable from
    # ``players`` against the caller's own information-eligible count.
    results = [r for r in results if r.standard_error > 0 and r.standard_error == r.standard_error]
    if len(results) < 3:
        nan = float("nan")
        return PoolingResult(nan, nan, nan, len(results), nan, nan, nan, nan, nan, nan, nan)
    deltas = [r.delta for r in results]
    errors = [r.standard_error for r in results]
    tau2, mu = paule_mandel_tau_squared(deltas, errors)
    if tau2 != tau2:
        nan = float("nan")
        return PoolingResult(nan, nan, nan, len(results), nan, nan, nan, nan, nan, nan, nan)
    shrink = sorted(
        tau2 / (tau2 + error * error) if (tau2 + error * error) > 0 else 0.0 for error in errors
    )
    mean_error_squared = _mean([error * error for error in errors])
    i_squared = tau2 / (tau2 + mean_error_squared) if (tau2 + mean_error_squared) > 0 else 0.0
    unshrunk = sum(1 for r in results if r.p_value == r.p_value and r.p_value < alpha)
    shrunk = 0
    for r in results:
        b = tau2 / (tau2 + r.standard_error**2) if (tau2 + r.standard_error**2) > 0 else 0.0
        posterior = mu + b * (r.delta - mu)
        posterior_sd = math.sqrt(b) * r.standard_error
        if posterior_sd > 0 and abs(posterior) / posterior_sd > student_t_quantile(alpha / 2.0, 60):
            shrunk += 1
    inflation = (shrunk - unshrunk) / len(results) if results else float("nan")
    return PoolingResult(
        tau=math.sqrt(tau2),
        tau_squared=tau2,
        mu=mu,
        players=len(results),
        shrinkage_p10=quantile(shrink, 0.10),
        shrinkage_p25=quantile(shrink, 0.25),
        shrinkage_median=quantile(shrink, 0.50),
        shrinkage_p75=quantile(shrink, 0.75),
        shrinkage_p90=quantile(shrink, 0.90),
        i_squared=i_squared,
        shrinkage_reach_inflation=inflation,
    )


# ---------------------------------------------------------------------------
# null data-generating processes
# ---------------------------------------------------------------------------


def _circular_shift(sequence: Sequence[int], offset: int) -> list[int]:
    n = len(sequence)
    if n == 0:
        return []
    offset %= n
    return list(sequence[offset:]) + list(sequence[:offset])


def contrast_null_replicate(
    matrix: FamilyMatrix,
    rng: random.Random,
    *,
    mode: str = "circular",
    **kwargs: Any,
) -> list[PlayerInference]:
    """One draw from the contrast-family null: relabel arms within each player.

    ``circular`` shifts the arm sequence, preserving the autocorrelation of both
    series and the exact arm counts. ``iid`` shuffles them, which additionally
    destroys serial dependence and therefore measures how much of the realised
    Type-I behaviour is a dependence artefact.
    """

    results = []
    for pseudonym in sorted(matrix.order):
        values = matrix.player_values(pseudonym)
        arms = matrix.player_arms(pseudonym)
        if mode == "circular":
            offset = rng.randrange(1, len(arms)) if len(arms) > 1 else 0
            permuted = _circular_shift(arms, offset)
        else:
            permuted = list(arms)
            rng.shuffle(permuted)
        result = player_inference(
            pseudonym, values, permuted, matrix.treated_code, matrix.control_code, **kwargs
        )
        if result is not None:
            results.append(result)
    return results


def _mode_stratum_of(matrix: FamilyMatrix) -> list[str]:
    """Coarse stratum label per row: the mode level when the family carries it."""

    if "mode" not in matrix.encoded.factors:
        return ["*"] * len(matrix.residual)
    position = matrix.encoded.factors.index("mode")
    codes = matrix.encoded.codes[position]
    return [f"m{code}" for code in codes]


def level_null_replicate(
    matrix: FamilyMatrix,
    rng: random.Random,
    *,
    mode: str = "block",
    block_length: int = NULL_BLOCK_LENGTH,
    **kwargs: Any,
) -> list[PlayerInference]:
    """One draw from the level-family null: exchange residuals between players.

    ``block`` pools contiguous residual blocks of length ``block_length`` across
    players inside a mode stratum and deals them back out, preserving each
    player's volume, stratum profile and within-block serial dependence while
    destroying player identity. ``iid`` permutes single residuals inside the
    same strata, which additionally destroys serial dependence.
    """

    strata = _mode_stratum_of(matrix)
    per_player_blocks: dict[str, list[tuple[str, list[float]]]] = {}
    pool_by_stratum: dict[str, list[list[float]]] = {}
    for pseudonym in sorted(matrix.order):
        indices = matrix.order[pseudonym]
        blocks: list[tuple[str, list[float]]] = []
        start = 0
        while start < len(indices):
            end = min(start + block_length, len(indices))
            stratum = strata[indices[start]]
            chunk = [matrix.residual[i] for i in indices[start:end]]
            blocks.append((stratum, chunk))
            pool_by_stratum.setdefault(stratum, []).append(chunk)
            start = end
        per_player_blocks[pseudonym] = blocks

    if mode == "iid":
        flat_by_stratum: dict[str, list[float]] = {}
        for stratum, chunks in pool_by_stratum.items():
            flat = [value for chunk in chunks for value in chunk]
            rng.shuffle(flat)
            flat_by_stratum[stratum] = flat
        cursor = dict.fromkeys(flat_by_stratum, 0)
    else:
        for chunks in pool_by_stratum.values():
            rng.shuffle(chunks)
        cursor = dict.fromkeys(pool_by_stratum, 0)

    results = []
    for pseudonym in sorted(matrix.order):
        values: list[float] = []
        for stratum, chunk in per_player_blocks[pseudonym]:
            if mode == "iid":
                flat = flat_by_stratum[stratum]
                start = cursor[stratum]
                values.extend(flat[start : start + len(chunk)])
                cursor[stratum] = start + len(chunk)
            else:
                donor = pool_by_stratum[stratum][cursor[stratum]]
                cursor[stratum] += 1
                # Volume is preserved exactly: a donor block shorter than the
                # slot it fills (only ever a player's final, partial block) is
                # cycled rather than truncated.
                values.extend(donor[index % len(donor)] for index in range(len(chunk)))
        result = player_inference(pseudonym, values, None, None, None, **kwargs)
        if result is not None:
            results.append(result)
    return results


def variance_ratio_curve(
    matrix: FamilyMatrix, batch_lengths: Sequence[int] = (1, 5, 10, 25, 50, 100)
) -> dict[int, float]:
    """Measured serial-dependence range of the real residuals.

    For batch length ``b`` let ``V(b) = b * Var(batch means)`` within a player.
    Under independence ``V(b)`` does not depend on ``b``; under positive serial
    dependence with range ``R`` it rises with ``b`` and plateaus once
    ``b > R``. The curve is reported as ``V(b) / V(1)`` pooled over players, and
    it is the number that decides whether the batched-means standard error is
    long enough for this family: the Type-I sweep is only informative against a
    null whose dependence range matches the one the data actually has.
    """

    out: dict[int, float] = {}
    baseline: list[float] = []
    per_length: dict[int, list[float]] = {b: [] for b in batch_lengths}
    for pseudonym in sorted(matrix.order):
        values = matrix.player_values(pseudonym)
        if len(values) < 200:
            continue
        base = _variance(values)
        if base != base or base <= 0:
            continue
        baseline.append(base)
        for b in batch_lengths:
            blocks = [values[i : i + b] for i in range(0, len(values) - b + 1, b)]
            if len(blocks) < 5:
                per_length[b].append(float("nan"))
                continue
            means = [_mean(block) for block in blocks]
            per_length[b].append(b * _variance(means) / base)
    for b in batch_lengths:
        usable = [v for v in per_length[b] if v == v]
        out[b] = _mean(usable) if usable else float("nan")
    return out


@dataclass(frozen=True)
class TypeIResult:
    null_name: str
    replicates: int
    player_tests: int
    rejection_05: float
    rejection_01: float
    mc_error_05: float
    mc_error_01: float

    def verdict(self, tolerance: float = 2.5) -> str:
        """Whether realised Type-I is within ``tolerance`` MC errors of nominal."""

        checks = []
        for realised, nominal, error in (
            (self.rejection_05, 0.05, self.mc_error_05),
            (self.rejection_01, 0.01, self.mc_error_01),
        ):
            if realised != realised or error != error or error <= 0:
                return "UNKNOWN"
            checks.append(abs(realised - nominal) <= tolerance * error)
        if all(checks):
            return "CALIBRATED"
        return "ANTICONSERVATIVE" if self.rejection_05 > 0.05 else "CONSERVATIVE"


def measure_type_i(
    matrix: FamilyMatrix,
    *,
    replicates: int,
    seed: int,
    null_mode: str,
    block_length: int = NULL_BLOCK_LENGTH,
    **kwargs: Any,
) -> TypeIResult:
    """Realised rejection rate of the primary test under a structural null.

    The Monte-Carlo error is computed **across replicates**, not across the
    (dependent) player tests inside one replicate: all players in a replicate
    share the same permuted residual pool, so treating the individual player
    tests as independent would understate the error.
    """

    rng = random.Random(stable_seed(seed, f"typeI:{null_mode}"))
    per_replicate_05: list[float] = []
    per_replicate_01: list[float] = []
    tests = 0
    for _ in range(replicates):
        if matrix.arm_family:
            results = contrast_null_replicate(matrix, rng, mode=null_mode, **kwargs)
        else:
            results = level_null_replicate(
                matrix, rng, mode=null_mode, block_length=block_length, **kwargs
            )
        usable = [r for r in results if r.p_value == r.p_value]
        if not usable:
            continue
        tests += len(usable)
        per_replicate_05.append(sum(1 for r in usable if r.p_value < 0.05) / len(usable))
        per_replicate_01.append(sum(1 for r in usable if r.p_value < 0.01) / len(usable))
    if not per_replicate_05:
        nan = float("nan")
        return TypeIResult(null_mode, 0, 0, nan, nan, nan, nan)
    r05, r01 = _mean(per_replicate_05), _mean(per_replicate_01)
    n = len(per_replicate_05)
    e05 = math.sqrt(_variance(per_replicate_05) / n) if n > 1 else float("nan")
    e01 = math.sqrt(_variance(per_replicate_01) / n) if n > 1 else float("nan")
    return TypeIResult(null_mode, n, tests, r05, r01, e05, e01)


# ---------------------------------------------------------------------------
# stability
# ---------------------------------------------------------------------------


def _half_statistic(
    values: Sequence[float],
    arms: Sequence[int] | None,
    treated_code: int | None,
    control_code: int | None,
    minimum_per_arm: int,
) -> float | None:
    if arms is None:
        return _mean(values) if len(values) >= 8 else None
    treated = [values[i] for i in range(len(values)) if arms[i] == treated_code]
    control = [values[i] for i in range(len(values)) if arms[i] == control_code]
    if len(treated) < minimum_per_arm or len(control) < minimum_per_arm:
        return None
    return _mean(treated) - _mean(control)


def split_half_stability(
    matrix: FamilyMatrix,
    *,
    chronological: bool,
    seed: int,
    minimum_per_arm: int = 8,
) -> tuple[float, float, int]:
    """Split-half agreement of the per-player estimate.

    ``chronological=True`` splits each player's own timeline at its midpoint,
    which is the only split that can see drift over a 365-day window. The
    random split is retained purely for comparability with the discovery
    screen; it measures internal consistency, not test-retest stability.
    """

    first: list[float] = []
    second: list[float] = []
    for pseudonym in sorted(matrix.order):
        values = matrix.player_values(pseudonym)
        arms = matrix.player_arms(pseudonym) if matrix.arm_family else None
        if not chronological:
            rng = random.Random(stable_seed(seed, pseudonym))
            order = list(range(len(values)))
            rng.shuffle(order)
            values = [values[i] for i in order]
            if arms is not None:
                arms = [arms[i] for i in order]
        cut = len(values) // 2
        if cut < 8:
            continue
        left = _half_statistic(
            values[:cut], arms[:cut] if arms else None, matrix.treated_code, matrix.control_code, minimum_per_arm
        )
        right = _half_statistic(
            values[cut : 2 * cut],
            arms[cut : 2 * cut] if arms else None,
            matrix.treated_code,
            matrix.control_code,
            minimum_per_arm,
        )
        if left is None or right is None:
            continue
        first.append(left)
        second.append(right)
    if len(first) < 20:
        return float("nan"), float("nan"), len(first)
    raw = _pearson(first, second)
    if raw != raw or raw <= -1.0:
        return raw, float("nan"), len(first)
    corrected = 2 * raw / (1 + raw)
    return raw, corrected, len(first)


# ---------------------------------------------------------------------------
# power
# ---------------------------------------------------------------------------


def minimum_detectable_effect(standard_error: float, df: int, power: float = 0.80) -> float:
    """Two-sided 0.05 minimum detectable effect at ``power`` for one player."""

    if standard_error != standard_error or standard_error <= 0 or df < 1:
        return float("nan")
    return (student_t_quantile(0.025, df) + student_t_quantile(1.0 - power, df)) * standard_error


def design_payload() -> dict[str, Any]:
    """The complete frozen inference design, as data.

    Digesting this is what lets a later reader prove the CANDIDATE_TEST
    confirmation used the design that was frozen on DISCOVERY, and not a design
    adjusted after seeing the confirmation.
    """

    return {
        "inference_version": INFERENCE_VERSION,
        "estimand": {
            "level": "E[context-adjusted residual | player]",
            "contrast": (
                "E[residual | player, treated] - E[residual | player, control], "
                "with the arm carried as a context factor so the population "
                "average response is removed before the player is compared"
            ),
            "unit_of_observation": "one opportunity, in chronological order",
        },
        "context_projection": {
            "method": "additive categorical projection by alternating group-mean removal",
            "player_is_a_factor": False,
            "arm_is_a_factor_for_contrast_families": True,
        },
        "test_statistic": {
            "method": "batched means over contiguous chronological blocks",
            "standard_error": "sd(block statistics) / sqrt(valid blocks)",
            "reference": "Student t on (valid blocks - 1) degrees of freedom, two-sided",
            "contrast_blocks": block_config(True),
            "level_blocks": block_config(False),
        },
        "null_dgp": {
            "contrast_primary": "within-player circular shift of the arm-label sequence",
            "contrast_secondary": "within-player i.i.d. permutation of the arm labels",
            "level_primary": (
                "between-player reassignment of contiguous residual blocks inside a "
                "mode stratum, preserving each player's volume and block count"
            ),
            "level_secondary": "i.i.d. restricted permutation inside a mode stratum",
            "level_block_lengths_measured": [5, 25, 100, 200],
            "why_level_differs": (
                "a within-player permutation leaves a level estimand unchanged and is "
                "therefore not a null for it"
            ),
        },
        "partial_pooling": {
            "model": "delta_p ~ N(mu, tau^2); delta_hat_p | delta_p ~ N(delta_p, SE_p^2)",
            "tau_estimator": "Paule-Mandel",
            "qualification_uses_shrunken_estimates": False,
            "degenerate_zero_se_players": "excluded from the variance-components fit",
        },
        "stability": {
            "chronological_split_half": True,
            "random_split_half": "reported only for comparability with the discovery screen",
        },
        "provisional_alpha": PROVISIONAL_ALPHA,
        "reported_alphas": [ALPHA_SECONDARY, ALPHA_PRIMARY],
        "multiplicity": "NOT CHOSEN IN THIS PHASE",
        "publication_thresholds": "NOT CHOSEN IN THIS PHASE",
        "seeded": True,
    }


def design_digest() -> str:
    import hashlib
    import json

    payload = json.dumps(design_payload(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "ALPHA_PRIMARY",
    "ALPHA_SECONDARY",
    "CONTRAST_MIN_BLOCKS",
    "CONTRAST_MIN_PER_BLOCK",
    "CONTRAST_TARGET_BLOCKS",
    "LEVEL_MIN_BLOCKS",
    "LEVEL_MIN_PER_BLOCK",
    "LEVEL_TARGET_BLOCKS",
    "INFERENCE_VERSION",
    "MIN_BLOCKS",
    "MIN_PER_BLOCK",
    "NULL_BLOCK_LENGTH",
    "PROVISIONAL_ALPHA",
    "TARGET_BLOCKS",
    "FamilyMatrix",
    "PlayerInference",
    "PoolingResult",
    "TypeIResult",
    "block_bounds",
    "block_config",
    "design_digest",
    "design_payload",
    "build_matrix",
    "contrast_null_replicate",
    "infer_all",
    "level_null_replicate",
    "measure_type_i",
    "minimum_detectable_effect",
    "paule_mandel_tau_squared",
    "player_inference",
    "pool",
    "regularized_incomplete_beta",
    "split_half_stability",
    "student_t_quantile",
    "student_t_two_sided_p",
    "variance_ratio_curve",
]

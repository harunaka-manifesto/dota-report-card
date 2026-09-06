"""Independent red-team checks over the V7 post-corpus research line.

Every function here is a *check*, not an estimator: it exists so that a claim
another phase made in prose can be recomputed by someone who does not trust the
phase that made it. They are deliberately pure — they take numbers the
tournament already publishes and return the number that decides whether a claim
survives — so that they are cheap to unit-test and impossible to run against a
forbidden split by accident.

The four checks correspond to the four claims that changed a grade or an
owner-facing figure:

``disattenuated_agreement``
    The mode-split probe demoted ``duration_tempo`` to C for agreeing across
    Turbo and standard at only Spearman +0.495. That probe was run on one
    family. Comparing it across families is only fair after dividing out each
    family's own within-mode reliability, because a noisier family cannot agree
    with itself even when it measures one trait.

``expected_qualified_share`` / ``qualified_share_at_ratio``
    The qualification ceiling evaluates its closed form at the *median*
    standard error. Standard errors here span an order of magnitude, so the
    honest quantity is the average of the per-player share, not the share at
    the average player.

``marginal_variance_ratio``
    The pooling model asserts ``Var(delta_hat) = tau^2 + E[SE^2]``. If the
    realised spread does not match, ``tau`` is not measuring between-player
    heterogeneity and every ``tau/SE`` argument downstream is unsound.

``bonferroni_level``
    No phase in this line applies a multiplicity correction, and each says so.
    The correction is one line; reporting the corrected coverage alongside the
    uncorrected coverage is what stops "optimistic" from being load-bearing.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from statistics import NormalDist

REDTEAM_VERSION = "v7-luna-e-redteam-1.0.0"

_NORMAL = NormalDist()


def disattenuated_agreement(observed: float, reliability_a: float, reliability_b: float) -> float:
    """Spearman agreement between two views, corrected for their own noise.

    ``observed`` is the correlation of the same players' estimates computed on
    two disjoint views (here: Turbo-only and standard-only). ``reliability_a``
    and ``reliability_b`` are each view's own split-half reliability. A view
    that cannot reproduce itself cannot agree with the other view either, so
    comparing raw cross-view agreement across families of different reliability
    is not a like-for-like comparison.

    Returns ``nan`` when either reliability is non-positive, because the
    correction is undefined there rather than infinite.
    """

    if reliability_a <= 0.0 or reliability_b <= 0.0:
        return float("nan")
    return observed / math.sqrt(reliability_a * reliability_b)


def qualified_share_at_ratio(critical_value: float, ratio: float) -> float:
    """``2 * Phi(-z / sqrt(1 + r^2))`` — the ceiling's own closed form."""

    if critical_value <= 0.0:
        raise ValueError("critical value must be positive")
    if ratio < 0.0:
        raise ValueError("signal-to-noise ratio cannot be negative")
    return 2.0 * _NORMAL.cdf(-critical_value / math.sqrt(1.0 + ratio * ratio))


def expected_qualified_share(
    critical_value: float, tau: float, standard_errors: Sequence[float]
) -> float:
    """Mean over players of the per-player qualification probability.

    The ceiling diagnostic reports ``q(z, tau / median(SE))``. That is the share
    for the median player, not the mean share, and the two differ whenever the
    standard errors are spread out. This returns the mean.
    """

    usable = [se for se in standard_errors if se == se and se > 0.0]
    if not usable:
        return float("nan")
    return sum(qualified_share_at_ratio(critical_value, tau / se) for se in usable) / len(usable)


def marginal_variance_ratio(
    deltas: Sequence[float], mu: float, tau: float, standard_errors: Sequence[float]
) -> float:
    """Realised spread of the estimates over the spread the model predicts.

    Under ``delta_p ~ N(mu, tau^2)`` and ``delta_hat_p | delta_p ~ N(delta_p,
    SE_p^2)`` the marginal variance of ``delta_hat`` is ``tau^2 + E[SE^2]``. A
    ratio far from 1 means the variance components do not describe the data
    they were fitted to.
    """

    values = [d for d in deltas if d == d]
    errors = [se for se in standard_errors if se == se]
    if len(values) < 2 or not errors:
        return float("nan")
    realised = sum((value - mu) ** 2 for value in values) / (len(values) - 1)
    predicted = tau * tau + sum(se * se for se in errors) / len(errors)
    if predicted <= 0.0:
        return float("nan")
    return realised / predicted


def bonferroni_level(alpha: float, families: int) -> float:
    """Per-family level that holds ``alpha`` across ``families`` simultaneous tests."""

    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly between 0 and 1")
    if families < 1:
        raise ValueError("families must be at least 1")
    return alpha / families


__all__ = [
    "REDTEAM_VERSION",
    "bonferroni_level",
    "disattenuated_agreement",
    "expected_qualified_share",
    "marginal_variance_ratio",
    "qualified_share_at_ratio",
]

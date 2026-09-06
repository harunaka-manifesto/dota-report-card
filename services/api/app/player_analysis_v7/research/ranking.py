"""Per-player Finding ranking for V7.

This module implements ``docs/evidence/v7-finding-ranking-model-2026-09-05.md``.
It answers a different question than ``app.player_analysis_v7.research.inference``: that
module asks whether a player's effect is *distinguishable from the
population*; this module assumes the effect is real for the player and asks
*how strongly it shows up in the player's own data*, on a scale that lets
different dimensions be compared.

    A Finding is something I would not know without looking at my whole year.

The model, restated from the spec:

* ``z`` places a player's raw effect in population standard deviations
  (``tau`` is the ruler; the old model's mistake was using ``SE``, a test,
  for this job).
* ``reliability`` is the classic shrinkage weight — the share of a player's
  measured deviation that is signal rather than noise — corrected for the
  serial dependence in a player's own match history via ``D_f``.
* ``score`` is the shrunk position, ``|z| * reliability``. It is a magnitude;
  direction is carried separately as ``sign(z)``.
* Every dimension a player has support for gets ranked. Nobody is excluded
  for being ordinary; a badly-measured dimension simply cannot reach the top
  of the list, because its ``reliability`` collapses its ``score`` toward
  zero.

This module is pure: plain dataclasses in, plain dataclasses out. It reads no
corpus and does not import the feature module that supplies real values
(``app.player_analysis_v7.research.pass2_features`` is owned by another worker and is
deliberately not imported here).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import sqrt

RANKING_MODEL_VERSION = "v7-luna-f-ranking-1.0.0"

#: The z-score multiplier for a two-sided 95% interval under the (approximate)
#: normal posterior implied by the normal-normal shrinkage model. See
#: ``shrunk_estimate`` for why 95% was chosen.
INTERVAL_Z = 1.959964
INTERVAL_COVERAGE = 0.95

# ---------------------------------------------------------------------------
# Owner-decided display policy (V7 owner selection packet, 2026-09-06)
# ---------------------------------------------------------------------------

#: How many Findings a report slate holds. (Report contract, section 2-4.)
REPORT_SLOTS = 5

#: Owner decision D1: a report always shows at least this many Findings,
#: whatever their score. Below the floor a slate is never trimmed; above it,
#: a slot must clear ``SCORE_LINE`` to be filled.
#:
#: The alternatives were to show five unconditionally, which pads the weakest
#: slates with material that is technically the reader's strongest but not
#: strongly measured, or to gate every slot, which leaves seven of 543
#: DISCOVERY players with fewer than one Finding. The floor keeps a report
#: from ever looking broken without dressing up slots four and five.
FINDING_FLOOR = 3

#: The score a Finding must clear to fill a slot above the floor.
#:
#: Provisional. This is the comparison scale the reliability table reports
#: "share scoring above the line" against, not a threshold fitted to
#: anything, and it is calibration work reserved for a later phase
#: (owner decision D2 and D8).
SCORE_LINE = 0.25

#: The three sections that carry ranked Findings, in narrative order.
FINDING_SECTIONS: tuple[str, ...] = (
    "what_is_good",
    "what_is_costing_you",
    "response_to_a_loss",
)

_DIRECTION_POSITIVE = "positive"
_DIRECTION_NEGATIVE = "negative"
_DIRECTION_NEUTRAL = "neutral"


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Interval:
    """A shrunk-estimate interval, with the coverage it was built for stated
    alongside it so a caller never has to guess what "the interval" means."""

    lower: float
    upper: float
    coverage: float


@dataclass(frozen=True)
class ShrunkEstimate:
    """The posterior mean and interval for one player-dimension pair."""

    point: float
    interval: Interval


@dataclass(frozen=True)
class PlayerDimension:
    """One player's raw measurement on one Finding dimension, plus the
    population parameters for that dimension.

    ``dependence_inflation`` is the ``D_f`` from the spec: the variance-ratio
    correction for serially dependent matches. It is required, not defaulted,
    because omitting it silently overstates reliability (see
    ``reliability``).
    """

    key: str
    section: str
    delta_hat: float
    se: float
    sample_size: int
    mu: float
    tau: float
    dependence_inflation: float


@dataclass(frozen=True)
class RankedFinding:
    """One player-dimension pair, scored and ready to sort into a report."""

    key: str
    section: str
    direction: str
    z: float
    reliability: float
    score: float
    shrunk_estimate: ShrunkEstimate
    sample_size: int


@dataclass(frozen=True)
class PopulationObservation:
    """One player's raw effect and precision for a population fit.

    ``dependence_inflation`` is per-observation rather than a single
    dimension-wide constant so that a caller with per-player ``D`` estimates
    is not forced to average them first; in the common case every
    observation for a dimension carries the same ``D_f``.
    """

    delta_hat: float
    se: float
    dependence_inflation: float


# ---------------------------------------------------------------------------
# 2.1 position
# ---------------------------------------------------------------------------


def z(delta_hat: float, mu: float, tau: float) -> float:
    """The player's position in population standard deviations.

    ``tau`` is a ruler, not a test: dividing by it (rather than by ``SE``) is
    the entire difference from the old, rejected model. A non-positive
    ``tau`` means the dimension has no measured between-player spread to
    place anyone against, so position is undefined rather than infinite or
    sign-flipped; this guard returns ``0.0`` (no measurable position) instead
    of raising or dividing by zero.
    """

    if tau <= 0.0:
        return 0.0
    return (delta_hat - mu) / tau


def direction_of(value: float) -> str:
    """``sign(z)`` as the three labels the report copy switches on."""

    if value > 0.0:
        return _DIRECTION_POSITIVE
    if value < 0.0:
        return _DIRECTION_NEGATIVE
    return _DIRECTION_NEUTRAL


# ---------------------------------------------------------------------------
# 2.2 reliability
# ---------------------------------------------------------------------------


def reliability(se: float, tau: float, dependence_inflation: float) -> float:
    """The classic shrinkage weight, corrected for serial dependence.

        r = tau^2 / (tau^2 + SE^2 * D)

    ``dependence_inflation`` (``D_f``) has no default. It is not an optional
    refinement: a player's matches are serially dependent, so a naive ``SE``
    understates true uncertainty, and skipping the correction inflates every
    reliability figure it touches (the spec's own worked example: naive
    ``r=0.921`` for ``hero_novelty`` becomes a dependence-corrected
    ``r=0.688``). If a caller genuinely wants the naive, uncorrected figure —
    for comparison only, never for a published Finding — they must pass
    ``dependence_inflation=1.0`` explicitly; there is no way to get that
    behaviour by omission.

    The result is clamped to ``[0, 1]``: it is a variance ratio and floating
    point error should never be allowed to carry it outside its own
    definition.
    """

    if tau <= 0.0:
        return 0.0
    tau_sq = tau * tau
    se_term = se * se * dependence_inflation
    if se_term < 0.0:
        se_term = 0.0
    denominator = tau_sq + se_term
    if denominator <= 0.0:
        # tau > 0 and se_term >= 0 with a zero denominator only happens if
        # both are exactly zero, which tau > 0 already rules out; kept as a
        # defensive guard against a future signature change.
        return 1.0
    value = tau_sq / denominator
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


# ---------------------------------------------------------------------------
# 2.3 score
# ---------------------------------------------------------------------------


def score(z_value: float, reliability_value: float) -> float:
    """The shrunk position, in population units: ``|z| * r``.

    A magnitude, not a signed quantity — a strong Finding in either direction
    should rank the same way, and direction is reported separately
    (``direction_of``) rather than folded into the number sorting decides on.
    """

    return abs(z_value) * reliability_value


# ---------------------------------------------------------------------------
# 2.2 shrunk estimate
# ---------------------------------------------------------------------------


def shrunk_estimate(
    delta_hat: float,
    mu: float,
    reliability_value: float,
    tau: float,
    *,
    interval_z: float = INTERVAL_Z,
    coverage: float = INTERVAL_COVERAGE,
) -> ShrunkEstimate:
    """The posterior mean and interval under the normal-normal shrinkage
    model implied by ``reliability``.

        posterior mean     = mu + r * (delta_hat - mu)
        posterior variance = (1 - r) * tau^2

    The variance identity follows directly from the reliability definition:
    with ``r = tau^2 / (tau^2 + SE^2 * D)``, the conjugate normal-normal
    posterior variance ``tau^2 * SE^2 * D / (tau^2 + SE^2 * D)`` is exactly
    ``(1 - r) * tau^2``, so no separate ``SE`` argument is needed here.

    **Interval coverage.** This returns a two-sided 95% interval
    (``point +/- 1.959964 * posterior_sd``), the conventional default for a
    reader-facing interval and the same convention used elsewhere in this
    codebase's inference (``ALPHA_PRIMARY`` two-sided testing). It assumes
    the posterior is approximately normal, which is exact under the
    normal-normal model this module uses and is the documented approximation
    the spec asks for ("an interval from the posterior standard deviation").
    Coverage is a keyword so a caller can ask for a different one, but the
    ``coverage`` value returned on ``Interval`` must always match the
    ``interval_z`` actually used — callers overriding one without the other
    get a mislabeled interval, which is on them.
    """

    point = mu + reliability_value * (delta_hat - mu)
    variance = (1.0 - reliability_value) * tau * tau
    if variance < 0.0:
        variance = 0.0
    posterior_sd = sqrt(variance)
    half_width = interval_z * posterior_sd
    return ShrunkEstimate(
        point=point,
        interval=Interval(lower=point - half_width, upper=point + half_width, coverage=coverage),
    )


# ---------------------------------------------------------------------------
# 5. rank_player
# ---------------------------------------------------------------------------


def rank_player(dimensions: Sequence[PlayerDimension]) -> list[RankedFinding]:
    """A player's dimensions, sorted by descending ``score``.

    Ties are broken by ``key`` ascending, which makes the ordering fully
    deterministic (never dependent on input order or sort stability) and
    reproducible across runs and languages.
    """

    ranked: list[RankedFinding] = []
    for dimension in dimensions:
        z_value = z(dimension.delta_hat, dimension.mu, dimension.tau)
        r_value = reliability(dimension.se, dimension.tau, dimension.dependence_inflation)
        estimate = shrunk_estimate(dimension.delta_hat, dimension.mu, r_value, dimension.tau)
        ranked.append(
            RankedFinding(
                key=dimension.key,
                section=dimension.section,
                direction=direction_of(z_value),
                z=z_value,
                reliability=r_value,
                score=score(z_value, r_value),
                shrunk_estimate=estimate,
                sample_size=dimension.sample_size,
            )
        )
    ranked.sort(key=lambda finding: (-finding.score, finding.key))
    return ranked


# ---------------------------------------------------------------------------
# 6. select_stratified
# ---------------------------------------------------------------------------


def select_stratified(
    ranked: Sequence[RankedFinding], sections: Sequence[str], slots: int
) -> list[RankedFinding]:
    """Section-aware selection: cover every section first, then fill by score.

    Phase 1 walks ``sections`` in the order given and takes the single
    top-scoring Finding from each section that has one, so one strong family
    cannot leave a report section empty. Phase 2 fills any remaining slots
    globally by descending score among everything not already picked.

    Both phases use the same deterministic tie-break as ``rank_player``
    (score descending, then key ascending), and the whole function first
    re-sorts its input by that rule — so the result does not depend on the
    order ``ranked`` arrives in, only on the ``(score, key)`` of each entry.
    A section absent from ``ranked`` is simply skipped in phase 1; it cannot
    manufacture a Finding that was never scored. If ``slots <= 0``, or
    ``ranked`` is empty, the result is ``[]``.
    """

    if slots <= 0 or not ranked:
        return []

    ordered = sorted(ranked, key=lambda finding: (-finding.score, finding.key))

    by_section: dict[str, list[RankedFinding]] = {}
    for finding in ordered:
        by_section.setdefault(finding.section, []).append(finding)

    selected: list[RankedFinding] = []
    selected_keys: set[str] = set()

    for section in sections:
        if len(selected) >= slots:
            break
        candidates = by_section.get(section)
        if not candidates:
            continue
        top = candidates[0]
        if top.key in selected_keys:
            continue
        selected.append(top)
        selected_keys.add(top.key)

    if len(selected) < slots:
        for finding in ordered:
            if len(selected) >= slots:
                break
            if finding.key in selected_keys:
                continue
            selected.append(finding)
            selected_keys.add(finding.key)

    selected.sort(key=lambda finding: (-finding.score, finding.key))
    return selected


# ---------------------------------------------------------------------------
# 7. population_parameters
# ---------------------------------------------------------------------------


def apply_score_gate(
    selected: Sequence[RankedFinding],
    *,
    sections: Sequence[str] = FINDING_SECTIONS,
    floor: int = FINDING_FLOOR,
    line: float = SCORE_LINE,
) -> list[RankedFinding]:
    """Owner decision D1: keep a floor unconditionally, gate the rest.

    Three things are kept, in this order of priority:

    1. **The top-scoring Finding of each section present.** ``select_stratified``
       promotes these first so no report section renders empty, then re-sorts
       everything by score — which means a section's sole representative can
       land in slot four or five. Gating on score alone therefore undoes the
       stratification. Measured on DISCOVERY, doing exactly that dropped the
       players whose report covered all three sections from 520 to 290.
    2. **Enough of the next-highest scores to reach ``floor``**, for a player
       whose Findings do not span three sections.
    3. **Anything above ``line``**, which is what fills slots four and five.

    The result keeps ``selected``'s order, so the caller's ranking survives.
    A slate at or under the floor is returned unchanged, so this can never
    make a report shorter than the floor promises.
    """

    if floor < 0:
        raise ValueError("floor must not be negative")
    if len(selected) <= floor:
        return list(selected)

    protected: set[int] = set()

    # 1. one per section, highest score first (selected is already ranked)
    seen_sections: set[str] = set()
    wanted = set(sections)
    for index, finding in enumerate(selected):
        if finding.section in wanted and finding.section not in seen_sections:
            seen_sections.add(finding.section)
            protected.add(index)

    # 2. top up to the floor by rank
    for index in range(len(selected)):
        if len(protected) >= floor:
            break
        protected.add(index)

    # 3. everything clearing the line
    for index, finding in enumerate(selected):
        if finding.score > line:
            protected.add(index)

    return [finding for index, finding in enumerate(selected) if index in protected]


def population_parameters(observations: Sequence[PopulationObservation]) -> tuple[float, float]:
    """Method-of-moments ``(mu, tau)`` for one dimension, across players.

    ``mu`` is the plain sample mean of ``delta_hat``.

    ``tau`` is the *between-player* spread, so it must have the within-player
    measurement variance removed:

        tau^2 = max(0, var(delta_hat) - mean(SE^2 * D))

    The naive standard deviation of ``delta_hat`` is the wrong estimator for
    this job: ``delta_hat`` is itself a noisy measurement of each player's
    true effect (``delta_hat_p = delta_p + noise_p``, ``noise_p ~ (0,
    SE_p^2 * D_p)``), so ``var(delta_hat)`` is the *sum* of the real
    between-player variance and the average measurement-error variance. Using
    it directly double-counts measurement error as if it were population
    spread, which inflates ``tau`` for every player, which in turn inflates
    every ``reliability`` figure computed against it — exactly the mistake
    the dependence correction in ``reliability`` exists to avoid making a
    second time, one level up.

    Needs at least two observations to form a sample variance; returns
    ``(delta_hat, 0.0)`` for exactly one observation and ``(nan, nan)`` for
    none. When the average measurement-error variance meets or exceeds the
    observed variance, ``tau`` is clamped to ``0.0`` rather than returned as
    a negative number — a variance component estimate.
    """

    n = len(observations)
    if n == 0:
        return float("nan"), float("nan")

    deltas = [obs.delta_hat for obs in observations]
    mu = sum(deltas) / n

    if n == 1:
        return mu, 0.0

    sample_variance = sum((d - mu) ** 2 for d in deltas) / (n - 1)
    mean_measurement_variance = sum(
        obs.se * obs.se * obs.dependence_inflation for obs in observations
    ) / n
    tau_sq = sample_variance - mean_measurement_variance
    if tau_sq < 0.0:
        tau_sq = 0.0
    return mu, sqrt(tau_sq)


__all__ = [
    "FINDING_FLOOR",
    "FINDING_SECTIONS",
    "INTERVAL_COVERAGE",
    "INTERVAL_Z",
    "RANKING_MODEL_VERSION",
    "REPORT_SLOTS",
    "SCORE_LINE",
    "Interval",
    "PlayerDimension",
    "PopulationObservation",
    "RankedFinding",
    "ShrunkEstimate",
    "apply_score_gate",
    "direction_of",
    "population_parameters",
    "rank_player",
    "reliability",
    "score",
    "select_stratified",
    "shrunk_estimate",
    "z",
]

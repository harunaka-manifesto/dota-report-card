"""Discovery-only early screen for V7 candidate families.

This module answers the cheap questions that decide whether a candidate family
is worth a real statistical tournament at all:

* how many players get enough opportunities (**structural reach**);
* how precisely each player's own value can be estimated (**information
  reach**);
* how much of the spread is genuinely between players rather than within
  (**player heterogeneity**) — the make-or-break metric, since a large
  population-wide effect with no individual variation is not a Finding;
* whether the signal is really patch, mode, hero or role rather than the
  player (**context sensitivity**);
* whether a player's value reproduces on their own held-out matches
  (**preliminary stability**).

It is deliberately *not* inference. There is no p-value here, no alpha, no
effect threshold, and nothing is tuned. Everything runs on DISCOVERY only; the
corpus reader fails closed on reserved splits.

Estimation notes
----------------

Context adjustment is an additive categorical projection fitted by alternating
group-mean removal (Gauss–Seidel on the additive fixed-effect model). Player is
deliberately *not* a factor in that projection — removing it would remove the
signal being measured. Because context factors such as hero are themselves
chosen by the player, this adjustment is conservative: it takes player-driven
context choice out of the residual, so the reported heterogeneity is a lower
bound on the raw between-player spread.

Heterogeneity uses a method-of-moments split, not a likelihood:

    Var(observed player values) = sigma_between^2 + mean(SE_player^2)

so ``sigma_between^2 = max(0, Var(d_p) - mean(SE_p^2))`` and the reliability
``sigma_between^2 / (sigma_between^2 + mean SE^2)`` is the share of observed
spread that is real. The James–Stein style shrinkage factor a later estimator
would apply to player ``p`` is ``sigma_b^2 / (sigma_b^2 + SE_p^2)``.

Everything is pure Python: the screen adds no third-party dependency, so it
runs in ordinary credential-free CI.
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from app.player_analysis_v7.research.features import Opportunity, PlayerFrame, extract

SCREEN_VERSION = "v7-luna-b-screen-1.0.0"

#: Fixed everywhere in this phase. Recorded in every emitted artefact.
DEFAULT_SEED = 20260903

#: Sweeps of the alternating categorical projection. Convergence is measured
#: and reported rather than assumed.
PROJECTION_SWEEPS = 10

#: Default opportunity bar for a level family, and per-arm bar for a contrast
#: family. Declared before screening and never tuned against a result.
DEFAULT_SUPPORT = 30
DEFAULT_ARM_SUPPORT = 12


def quantile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        return float("nan")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = q * (len(sorted_values) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return float(sorted_values[low])
    weight = position - low
    return float(sorted_values[low] * (1 - weight) + sorted_values[high] * weight)


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def _variance(values: Sequence[float]) -> float:
    if len(values) < 2:
        return float("nan")
    mu = _mean(values)
    return sum((value - mu) ** 2 for value in values) / (len(values) - 1)


def stable_seed(seed: int, key: str) -> int:
    """Deterministic per-player seed that does not depend on PYTHONHASHSEED."""

    digest = hashlib.sha256(f"{seed}:{key}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


# ---------------------------------------------------------------------------
# context projection
# ---------------------------------------------------------------------------


@dataclass
class Encoded:
    """Opportunities flattened into parallel arrays for the screen."""

    player: list[int]
    value: list[float]
    arm: list[int]
    factors: list[str]
    codes: list[list[int]]
    levels: list[int]
    level_names: list[list[str]]
    player_names: list[str]
    arm_names: list[str]

    def __len__(self) -> int:
        return len(self.value)


def encode(
    per_player: Sequence[tuple[str, Sequence[Opportunity]]],
    include_arm_as_factor: bool = True,
) -> Encoded:
    """Flatten opportunities, keeping factor identity explicit.

    ``arm`` is encoded as an ordinary context factor so that the *population*
    treatment effect is removed by the projection. Each player's value is then
    a deviation from the population effect, which is what learning 9 requires:
    a shared population-wide response is not personal identity.
    """

    factor_names: list[str] = []
    factor_index: dict[str, int] = {}
    for _, opportunities in per_player:
        for opportunity in opportunities:
            for name, _level in opportunity.ctx:
                if name not in factor_index:
                    factor_index[name] = len(factor_names)
                    factor_names.append(name)
    if include_arm_as_factor:
        factor_index["__arm__"] = len(factor_names)
        factor_names.append("__arm__")

    level_maps: list[dict[str, int]] = [{} for _ in factor_names]
    codes: list[list[int]] = [[] for _ in factor_names]
    player_names: list[str] = []
    player_index: dict[str, int] = {}
    arm_names: list[str] = []
    arm_index: dict[str, int] = {}
    players: list[int] = []
    values: list[float] = []
    arms: list[int] = []

    for pseudonym, opportunities in per_player:
        if pseudonym not in player_index:
            player_index[pseudonym] = len(player_names)
            player_names.append(pseudonym)
        pid = player_index[pseudonym]
        for opportunity in opportunities:
            players.append(pid)
            values.append(float(opportunity.value))
            arm_label = opportunity.arm or ""
            if arm_label not in arm_index:
                arm_index[arm_label] = len(arm_names)
                arm_names.append(arm_label)
            arms.append(arm_index[arm_label])
            present = dict(opportunity.ctx)
            if include_arm_as_factor:
                present["__arm__"] = arm_label
            for position, name in enumerate(factor_names):
                level = present.get(name, "__missing__")
                mapping = level_maps[position]
                code = mapping.get(level)
                if code is None:
                    code = len(mapping)
                    mapping[level] = code
                codes[position].append(code)

    return Encoded(
        player=players,
        value=values,
        arm=arms,
        factors=factor_names,
        codes=codes,
        levels=[len(mapping) for mapping in level_maps],
        level_names=[list(mapping) for mapping in level_maps],
        player_names=player_names,
        arm_names=arm_names,
    )


@dataclass(frozen=True)
class ContextProjectionFit:
    """Sufficient runtime representation of the finite-sweep projection."""

    intercept: float
    coefficients: tuple[tuple[float, ...], ...]
    residual: tuple[float, ...]
    drift: float


def fit_context_projection(
    encoded: Encoded, sweeps: int = PROJECTION_SWEEPS
) -> ContextProjectionFit:
    """Fit the existing projection while retaining its applied corrections.

    The coefficient for a level is the sum of the corrections removed from
    that level across the fixed Gauss-Seidel sweeps. Applying ``intercept +
    sum(coefficients)`` therefore reproduces the research residual exactly.
    ``drift`` is the largest absolute group-mean correction applied in the
    last sweep relative to the residual standard deviation.
    """

    if not encoded.value:
        raise ValueError("cannot fit a context projection without observations")
    if sweeps < 1:
        raise ValueError("context projection needs at least one sweep")

    residual = list(encoded.value)
    grand = _mean(residual)
    residual = [value - grand for value in residual]
    coefficients = [[0.0] * level_count for level_count in encoded.levels]
    last_drift = 0.0
    for sweep in range(sweeps):
        last_drift = 0.0
        for position, level_count in enumerate(encoded.levels):
            if level_count < 2:
                continue
            code_column = encoded.codes[position]
            totals = [0.0] * level_count
            counts = [0] * level_count
            for index, code in enumerate(code_column):
                totals[code] += residual[index]
                counts[code] += 1
            means = [
                (totals[level] / counts[level]) if counts[level] else 0.0
                for level in range(level_count)
            ]
            for level, mean in enumerate(means):
                coefficients[position][level] += mean
            for level in range(level_count):
                if counts[level]:
                    last_drift = max(last_drift, abs(means[level]))
            for index, code in enumerate(code_column):
                residual[index] -= means[code]
        del sweep
    spread = math.sqrt(_variance(residual)) if len(residual) > 1 else 0.0
    return ContextProjectionFit(
        intercept=grand,
        coefficients=tuple(tuple(row) for row in coefficients),
        residual=tuple(residual),
        drift=last_drift / spread if spread else 0.0,
    )


def project_out_context(encoded: Encoded, sweeps: int = PROJECTION_SWEEPS) -> tuple[list[float], float]:
    """Remove additive categorical context effects; return residuals and drift."""

    fit = fit_context_projection(encoded, sweeps)
    return list(fit.residual), fit.drift


def eta_squared(codes: Sequence[int], level_count: int, values: Sequence[float]) -> float:
    """Marginal share of variance in ``values`` explained by one factor."""

    if not values or level_count < 2:
        return 0.0
    grand = _mean(values)
    totals = [0.0] * level_count
    counts = [0] * level_count
    for index, code in enumerate(codes):
        totals[code] += values[index]
        counts[code] += 1
    between = 0.0
    for level in range(level_count):
        if counts[level]:
            between += counts[level] * (totals[level] / counts[level] - grand) ** 2
    total = sum((value - grand) ** 2 for value in values)
    return between / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# per-player effects
# ---------------------------------------------------------------------------


@dataclass
class PlayerEffect:
    pseudonym: str
    value: float
    standard_error: float
    n: int
    n_treated: int
    n_control: int


def player_effects(
    encoded: Encoded,
    residual: Sequence[float],
    arm_family: bool,
    treated: str | None,
    control: str | None,
    support: int,
    arm_support: int,
) -> list[PlayerEffect]:
    """Per-player value and its within-player standard error.

    Level family: the player's mean residual, ``SE = sd / sqrt(n)``.
    Contrast family: treated-minus-control residual difference, with the
    two-sample standard error ``sqrt(var_t / n_t + var_c / n_c)``.
    """

    buckets: dict[int, list[tuple[int, float]]] = {}
    for index, pid in enumerate(encoded.player):
        buckets.setdefault(pid, []).append((encoded.arm[index], residual[index]))

    treated_code = encoded.arm_names.index(treated) if arm_family and treated in encoded.arm_names else None
    control_code = encoded.arm_names.index(control) if arm_family and control in encoded.arm_names else None

    effects: list[PlayerEffect] = []
    for pid, rows in buckets.items():
        name = encoded.player_names[pid]
        if not arm_family:
            values = [value for _, value in rows]
            if len(values) < support:
                continue
            spread = _variance(values)
            effects.append(
                PlayerEffect(
                    pseudonym=name,
                    value=_mean(values),
                    standard_error=math.sqrt(spread / len(values)) if spread == spread else float("nan"),
                    n=len(values),
                    n_treated=0,
                    n_control=0,
                )
            )
            continue
        if treated_code is None or control_code is None:
            continue
        treated_values = [value for code, value in rows if code == treated_code]
        control_values = [value for code, value in rows if code == control_code]
        if len(treated_values) < arm_support or len(control_values) < arm_support:
            continue
        if len(treated_values) + len(control_values) < support:
            continue
        var_t = _variance(treated_values)
        var_c = _variance(control_values)
        effects.append(
            PlayerEffect(
                pseudonym=name,
                value=_mean(treated_values) - _mean(control_values),
                standard_error=math.sqrt(var_t / len(treated_values) + var_c / len(control_values)),
                n=len(treated_values) + len(control_values),
                n_treated=len(treated_values),
                n_control=len(control_values),
            )
        )
    effects.sort(key=lambda effect: effect.pseudonym)
    return effects


def split_half(
    encoded: Encoded,
    residual: Sequence[float],
    arm_family: bool,
    treated: str | None,
    control: str | None,
    arm_support: int,
    seed: int,
) -> tuple[float, float, int]:
    """Within-player split-half reliability of the per-player value.

    Each player's opportunities are split into two halves with a per-player
    deterministic RNG seeded from ``seed`` and the pseudonym, stratified by arm
    for contrast families. Returns ``(raw r, Spearman-Brown r, n players)``.
    """

    buckets: dict[int, list[tuple[int, float]]] = {}
    for index, pid in enumerate(encoded.player):
        buckets.setdefault(pid, []).append((encoded.arm[index], residual[index]))

    treated_code = encoded.arm_names.index(treated) if arm_family and treated in encoded.arm_names else None
    control_code = encoded.arm_names.index(control) if arm_family and control in encoded.arm_names else None

    first: list[float] = []
    second: list[float] = []
    for pid, rows in buckets.items():
        rng = random.Random(stable_seed(seed, encoded.player_names[pid]))
        if arm_family:
            if treated_code is None or control_code is None:
                continue
            halves: list[dict[int, list[float]]] = [{}, {}]
            ok = True
            for code in (treated_code, control_code):
                values = [value for arm_code, value in rows if arm_code == code]
                rng.shuffle(values)
                cut = len(values) // 2
                if cut < max(2, arm_support // 2):
                    ok = False
                    break
                halves[0][code] = values[:cut]
                halves[1][code] = values[cut : 2 * cut]
            if not ok:
                continue
            first.append(_mean(halves[0][treated_code]) - _mean(halves[0][control_code]))
            second.append(_mean(halves[1][treated_code]) - _mean(halves[1][control_code]))
        else:
            values = [value for _, value in rows]
            rng.shuffle(values)
            cut = len(values) // 2
            if cut < 8:
                continue
            first.append(_mean(values[:cut]))
            second.append(_mean(values[cut : 2 * cut]))

    if len(first) < 20:
        return float("nan"), float("nan"), len(first)
    raw = _pearson(first, second)
    if raw != raw or raw <= -1.0:
        return raw, float("nan"), len(first)
    corrected = 2 * raw / (1 + raw) if (1 + raw) != 0 else float("nan")
    return raw, corrected, len(first)


def _pearson(left: Sequence[float], right: Sequence[float]) -> float:
    n = len(left)
    if n < 3:
        return float("nan")
    mu_l, mu_r = _mean(left), _mean(right)
    num = sum((left[i] - mu_l) * (right[i] - mu_r) for i in range(n))
    den_l = math.sqrt(sum((left[i] - mu_l) ** 2 for i in range(n)))
    den_r = math.sqrt(sum((right[i] - mu_r) ** 2 for i in range(n)))
    if den_l == 0 or den_r == 0:
        return float("nan")
    return num / (den_l * den_r)


# ---------------------------------------------------------------------------
# the screen itself
# ---------------------------------------------------------------------------


@dataclass
class ScreenResult:
    family: str
    parsed_dependent: bool
    arm_family: bool
    support_bar: int
    arm_support_bar: int
    denominator_sampled: int
    denominator_eligible: int
    players_with_any: int
    players_supported: int
    reach_of_sampled: float
    reach_of_eligible: float
    opportunities: int
    obs_p5: float
    obs_p25: float
    obs_median: float
    obs_p75: float
    obs_p95: float
    sigma_between: float
    mean_within_se: float
    reliability: float
    information_reach_snr1: float
    information_reach_snr2: float
    median_shrinkage: float
    split_half_r: float
    spearman_brown: float
    split_half_players: int
    projection_drift: float
    eta2: dict[str, float] = field(default_factory=dict)
    eta2_player_raw: float = 0.0
    role_opportunity_share: dict[str, float] = field(default_factory=dict)
    role_reach: dict[str, float] = field(default_factory=dict)
    seconds: float = 0.0
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def screen_family(
    name: str,
    frames: Sequence[PlayerFrame],
    *,
    parsed_dependent: bool,
    arm_family: bool,
    treated: str | None = None,
    control: str | None = None,
    support: int = DEFAULT_SUPPORT,
    arm_support: int = DEFAULT_ARM_SUPPORT,
    denominator_sampled: int,
    denominator_eligible: int,
    seed: int = DEFAULT_SEED,
) -> ScreenResult:
    started = time.perf_counter()
    per_player: list[tuple[str, list[Opportunity]]] = []
    for frame in frames:
        opportunities = extract(name, frame)
        if opportunities:
            per_player.append((frame.pseudonym, opportunities))

    notes: list[str] = []
    if not per_player:
        return ScreenResult(
            family=name,
            parsed_dependent=parsed_dependent,
            arm_family=arm_family,
            support_bar=support,
            arm_support_bar=arm_support,
            denominator_sampled=denominator_sampled,
            denominator_eligible=denominator_eligible,
            players_with_any=0,
            players_supported=0,
            reach_of_sampled=0.0,
            reach_of_eligible=0.0,
            opportunities=0,
            obs_p5=0.0,
            obs_p25=0.0,
            obs_median=0.0,
            obs_p75=0.0,
            obs_p95=0.0,
            sigma_between=float("nan"),
            mean_within_se=float("nan"),
            reliability=float("nan"),
            information_reach_snr1=0.0,
            information_reach_snr2=0.0,
            median_shrinkage=float("nan"),
            split_half_r=float("nan"),
            spearman_brown=float("nan"),
            split_half_players=0,
            projection_drift=0.0,
            seconds=time.perf_counter() - started,
            notes=["no opportunities produced"],
        )

    encoded = encode(per_player, include_arm_as_factor=arm_family)
    residual, drift = project_out_context(encoded)

    effects = player_effects(
        encoded,
        residual,
        arm_family=arm_family,
        treated=treated,
        control=control,
        support=support,
        arm_support=arm_support,
        )

    counts = sorted(len(opportunities) for _, opportunities in per_player)
    observed = sorted(effect.value for effect in effects)
    del observed

    values = [effect.value for effect in effects]
    errors = [effect.standard_error for effect in effects if effect.standard_error == effect.standard_error]
    observed_variance = _variance(values) if len(values) > 1 else float("nan")
    mean_error_squared = _mean([error**2 for error in errors]) if errors else float("nan")
    if observed_variance == observed_variance and mean_error_squared == mean_error_squared:
        sigma_between_squared = max(observed_variance - mean_error_squared, 0.0)
    else:
        sigma_between_squared = float("nan")
    sigma_between = math.sqrt(sigma_between_squared) if sigma_between_squared == sigma_between_squared else float("nan")
    reliability = (
        sigma_between_squared / (sigma_between_squared + mean_error_squared)
        if sigma_between_squared == sigma_between_squared
        and mean_error_squared == mean_error_squared
        and (sigma_between_squared + mean_error_squared) > 0
        else float("nan")
    )
    if sigma_between_squared == 0.0:
        notes.append(
            "observed between-player spread does not exceed within-player noise: "
            "no detectable player heterogeneity at this support"
        )

    if errors and sigma_between == sigma_between and sigma_between > 0:
        snr = [sigma_between / error for error in errors if error > 0]
        information_snr1 = sum(1 for ratio in snr if ratio >= 1.0) / len(effects)
        information_snr2 = sum(1 for ratio in snr if ratio >= 2.0) / len(effects)
        shrinkage = sorted(
            sigma_between_squared / (sigma_between_squared + error**2) for error in errors if error > 0
        )
        median_shrinkage = quantile(shrinkage, 0.5)
    else:
        information_snr1 = 0.0
        information_snr2 = 0.0
        median_shrinkage = float("nan")

    raw_r, corrected_r, split_players = split_half(
        encoded, residual, arm_family, treated, control, arm_support, seed
    )

    eta2 = {
        encoded.factors[position]: eta_squared(
            encoded.codes[position], encoded.levels[position], encoded.value
        )
        for position in range(len(encoded.factors))
    }
    player_levels = len(encoded.player_names)
    eta2_player_raw = eta_squared(encoded.player, player_levels, encoded.value)

    role_share: dict[str, float] = {}
    role_reach: dict[str, float] = {}
    if "role" in encoded.factors:
        position = encoded.factors.index("role")
        inverse: dict[int, str] = {}
        # Recover level labels by re-walking the opportunities in order.
        index = 0
        for _, opportunities in per_player:
            for opportunity in opportunities:
                label = dict(opportunity.ctx).get("role", "__missing__")
                inverse[encoded.codes[position][index]] = label
                index += 1
        totals: dict[str, int] = {}
        per_player_role: dict[str, dict[str, int]] = {}
        index = 0
        for pseudonym, opportunities in per_player:
            bucket = per_player_role.setdefault(pseudonym, {})
            for _ in opportunities:
                label = inverse[encoded.codes[position][index]]
                totals[label] = totals.get(label, 0) + 1
                bucket[label] = bucket.get(label, 0) + 1
                index += 1
        grand_total = sum(totals.values())
        role_share = {label: count / grand_total for label, count in sorted(totals.items())}
        for label in sorted(totals):
            qualifying = sum(
                1 for bucket in per_player_role.values() if bucket.get(label, 0) >= support
            )
            role_reach[label] = qualifying / denominator_sampled

    return ScreenResult(
        family=name,
        parsed_dependent=parsed_dependent,
        arm_family=arm_family,
        support_bar=support,
        arm_support_bar=arm_support if arm_family else 0,
        denominator_sampled=denominator_sampled,
        denominator_eligible=denominator_eligible,
        players_with_any=len(per_player),
        players_supported=len(effects),
        reach_of_sampled=len(effects) / denominator_sampled,
        reach_of_eligible=len(effects) / denominator_eligible,
        opportunities=len(encoded),
        obs_p5=quantile(counts, 0.05),
        obs_p25=quantile(counts, 0.25),
        obs_median=quantile(counts, 0.5),
        obs_p75=quantile(counts, 0.75),
        obs_p95=quantile(counts, 0.95),
        sigma_between=sigma_between,
        mean_within_se=math.sqrt(mean_error_squared) if mean_error_squared == mean_error_squared else float("nan"),
        reliability=reliability,
        information_reach_snr1=information_snr1,
        information_reach_snr2=information_snr2,
        median_shrinkage=median_shrinkage,
        split_half_r=raw_r,
        spearman_brown=corrected_r,
        split_half_players=split_players,
        projection_drift=drift,
        eta2=eta2,
        eta2_player_raw=eta2_player_raw,
        role_opportunity_share=role_share,
        role_reach=role_reach,
        seconds=time.perf_counter() - started,
        notes=notes,
    )


def effect_vectors(
    name: str,
    frames: Sequence[PlayerFrame],
    *,
    arm_family: bool,
    treated: str | None,
    control: str | None,
    support: int,
    arm_support: int,
) -> dict[str, float]:
    """Per-player values for one family, for cross-family redundancy checks."""

    per_player = [
        (frame.pseudonym, extract(name, frame))
        for frame in frames
    ]
    per_player = [(name_, ops) for name_, ops in per_player if ops]
    if not per_player:
        return {}
    encoded = encode(per_player, include_arm_as_factor=arm_family)
    residual, _ = project_out_context(encoded)
    effects = player_effects(
        encoded, residual, arm_family, treated, control, support, arm_support
    )
    return {effect.pseudonym: effect.value for effect in effects}


def spearman(left: Sequence[float], right: Sequence[float]) -> float:
    def ranks(values: Sequence[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda index: values[index])
        result = [0.0] * len(values)
        index = 0
        while index < len(order):
            end = index
            while end + 1 < len(order) and values[order[end + 1]] == values[order[index]]:
                end += 1
            average = (index + end) / 2 + 1
            for position in range(index, end + 1):
                result[order[position]] = average
            index = end + 1
        return result

    if len(left) < 3:
        return float("nan")
    return _pearson(ranks(left), ranks(right))


__all__ = [
    "DEFAULT_ARM_SUPPORT",
    "DEFAULT_SEED",
    "DEFAULT_SUPPORT",
    "PROJECTION_SWEEPS",
    "SCREEN_VERSION",
    "Encoded",
    "ContextProjectionFit",
    "PlayerEffect",
    "ScreenResult",
    "effect_vectors",
    "encode",
    "eta_squared",
    "fit_context_projection",
    "player_effects",
    "project_out_context",
    "quantile",
    "screen_family",
    "spearman",
    "split_half",
    "stable_seed",
]

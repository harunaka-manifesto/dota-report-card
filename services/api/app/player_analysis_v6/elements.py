"""Seven public v6 Elements computed from summary history only."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from .baselines import BaselineContext, BaselineResolver
from .constants import DEFAULT_BOOTSTRAP_ITERATIONS, MIN_CONSISTENCY_SESSIONS, PUBLIC_ELEMENT_KEYS
from .metrics import (
    compare_consistency_signals,
    compare_transfer_signals,
    death_exposure_per_ten_minutes,
    finishing_share,
    involvement_per_minute,
    match_weighted_effective_count,
    shannon_effective_count,
)
from .models import ElementDefinition, ElementResultV6, Estimate
from .statistics import BootstrapResult, bootstrap_stability, clustered_bootstrap
from .thresholds import DEFAULT_THRESHOLDS, MetricThreshold, threshold_for

ELEMENT_DEFINITIONS: tuple[ElementDefinition, ...] = (
    ElementDefinition(
        "breadth",
        "Hero Breadth",
        "How widely your matches are distributed across heroes.",
        "effective heroes",
        "breadth_effective_count",
        axis_left="focused pool",
        axis_right="broad pool",
    ),
    ElementDefinition(
        "toolkit",
        "Toolkit Range",
        "How many functional jobs your hero choices cover in the reviewed taxonomy.",
        "effective jobs",
        "toolkit_effective_count",
        minimum_coverage=0.80,
        axis_left="narrow toolkit",
        axis_right="versatile toolkit",
    ),
    ElementDefinition(
        "involvement",
        "Involvement",
        "Context-adjusted kills plus assists per minute.",
        "kills+assists/minute",
        "involvement_per_minute",
        minimum_sessions=8,
        axis_left="quieter participation",
        axis_right="frequent participation",
        forbidden_claims=("aggression", "positioning", "fight entry"),
    ),
    ElementDefinition(
        "finishing",
        "Finishing",
        "Context-adjusted share of known kill-plus-assist events that are kills.",
        "kill share",
        "finishing_share",
        minimum_sessions=8,
        axis_left="shared conversion",
        axis_right="personal conversion",
        forbidden_claims=("intent", "objective conversion"),
    ),
    ElementDefinition(
        "death_exposure",
        "Death Exposure",
        "Context-adjusted deaths per ten minutes.",
        "deaths/10 minutes",
        "death_exposure_per_ten",
        minimum_sessions=8,
        axis_left="lower exposure",
        axis_right="higher exposure",
        forbidden_claims=("death quality", "positioning", "intention"),
    ),
    ElementDefinition(
        "transfer",
        "Transfer",
        "Agreement when a familiar hero context is compared with stretch choices.",
        "multi-signal agreement",
        "transfer_agreement",
        minimum_sessions=8,
        axis_left="does not transfer",
        axis_right="transfers across choices",
        forbidden_claims=("causality", "positioning", "intent"),
    ),
    ElementDefinition(
        "consistency",
        "Consistency",
        "Robust session-to-session agreement across outcome, activity, and death exposure.",
        "session consistency",
        "consistency_dispersion",
        minimum_sessions=MIN_CONSISTENCY_SESSIONS,
        axis_left="variable expression",
        axis_right="consistent expression",
        forbidden_claims=("intent", "tilt", "causality"),
    ),
)


def element_registry() -> tuple[ElementDefinition, ...]:
    return ELEMENT_DEFINITIONS


def _get(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _hero(item: Any) -> Any:
    return _get(item, "hero_id")


def _session_id(item: Any, index: int) -> str:
    value = _get(item, "session_id")
    return str(value) if value not in (None, "") else f"session-{index + 1}"


def _session_groups(matches: Sequence[Any]) -> tuple[tuple[str, tuple[Any, ...]], ...]:
    groups: dict[str, list[Any]] = defaultdict(list)
    for index, item in enumerate(matches):
        groups[_session_id(item, index)].append(item)
    return tuple((key, tuple(groups[key])) for key in sorted(groups))


def _numeric_values(matches: Sequence[Any], getter: Any) -> tuple[list[float], list[str], float]:
    values: list[float] = []
    session_ids: list[str] = []
    denominator = len(matches)
    for index, item in enumerate(matches):
        value = getter(item)
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(numeric):
            continue
        values.append(numeric)
        session_ids.append(_session_id(item, index))
    return values, session_ids, len(values) / denominator if denominator else 0.0


def _bootstrap(
    values: Sequence[float],
    session_ids: Sequence[str],
    *,
    estimator: Any = None,
    iterations: int,
    seed: int,
) -> BootstrapResult:
    return clustered_bootstrap(
        values,
        session_ids,
        estimator=estimator or (lambda sample: sum(sample) / len(sample) if sample else math.nan),
        iterations=iterations,
        seed=seed,
    )


def _confidence(threshold: MetricThreshold, result: BootstrapResult, coverage: float, sample_size: int, sessions: int) -> tuple[str, float]:
    stability = 0.0
    if result.replicates:
        # A scalar metric's practical region is unknown here; confidence is
        # based on repeatability around its point estimate.  Baseline-aware
        # direction stability is applied by the caller where available.
        spread = (result.upper - result.lower) if result.lower is not None and result.upper is not None else math.inf
        scale = abs(result.point_estimate or 0.0) + threshold.practical_margin
        stability = max(0.0, min(1.0, 1.0 - spread / (2.0 * max(scale, 1e-9))))
    tier = threshold.supports_confidence(
        sample_size=sample_size,
        independent_sessions=sessions,
        coverage=coverage,
        stability=stability,
    )
    return tier, stability


def _estimate(
    key: str,
    definition: ElementDefinition,
    values: Sequence[float],
    session_ids: Sequence[str],
    *,
    coverage: float,
    baseline: float | None = None,
    raw_metrics: Mapping[str, Any] | None = None,
    evidence_refs: tuple[str, ...] = (),
    iterations: int,
    seed: int,
    thresholds: Mapping[str, MetricThreshold],
    direction_override: str | None = None,
    value_override: float | None = None,
    status_override: str | None = None,
    limitation: str | None = None,
    sample_size_override: int | None = None,
    sessions_override: int | None = None,
) -> ElementResultV6:
    threshold = threshold_for(definition.metric_key, thresholds)
    sample_size = len(values) if sample_size_override is None else max(0, int(sample_size_override))
    sessions = len(set(session_ids)) if sessions_override is None else max(0, int(sessions_override))
    if sample_size == 0 or status_override == "unavailable":
        estimate = Estimate(
            None,
            definition.unit,
            zone="unknown",
            direction="unknown",
            sample_size=sample_size,
            independent_sessions=sessions,
            coverage=coverage,
            confidence="unavailable",
            status="unavailable",
            evidence_refs=evidence_refs,
            limitations=tuple(item for item in (limitation or "metric unavailable",) if item),
            forbidden_claims=definition.forbidden_claims,
        )
        return ElementResultV6(key, definition.label, estimate, raw_metrics=raw_metrics or {}, evidence_refs=evidence_refs)
    result = _bootstrap(values, session_ids, iterations=iterations, seed=seed)
    point = value_override if value_override is not None else result.point_estimate
    zone = threshold.zone(point, baseline=baseline)
    direction = direction_override or {"low": "negative", "high": "positive", "typical": "neutral", "unknown": "unknown"}[zone]
    tier, stability = _confidence(threshold, result, coverage, sample_size, sessions)
    status = "available" if sample_size >= definition.minimum_sample else "limited"
    if sessions < definition.minimum_sessions or coverage < definition.minimum_coverage:
        status = "limited"
    if status_override in {"available", "limited"}:
        status = status_override
    limitations: list[str] = []
    if sample_size < definition.minimum_sample:
        limitations.append(f"fewer than {definition.minimum_sample} usable matches")
    if sessions < definition.minimum_sessions:
        limitations.append(f"fewer than {definition.minimum_sessions} independent sessions")
    if coverage < definition.minimum_coverage:
        limitations.append(f"coverage below {definition.minimum_coverage:.0%}")
    if limitation:
        limitations.append(limitation)
    if status == "limited" and tier == "high":
        tier = "descriptive"
    estimate = Estimate(
        point,
        definition.unit,
        interval=result.interval,
        zone=zone,
        direction=direction,  # type: ignore[arg-type]
        stability=stability,
        sample_size=sample_size,
        independent_sessions=sessions,
        coverage=coverage,
        confidence=tier,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        evidence_refs=evidence_refs,
        limitations=tuple(dict.fromkeys(limitations)),
        supported_claims=(definition.description,),
        forbidden_claims=definition.forbidden_claims,
        bootstrap_method=result.method,
    )
    return ElementResultV6(key, definition.label, estimate, raw_metrics=raw_metrics or {}, evidence_refs=evidence_refs)


def _unavailable(key: str, definition: ElementDefinition, *, sample_size: int, coverage: float, sessions: int, reason: str) -> ElementResultV6:
    estimate = Estimate(
        None,
        definition.unit,
        zone="unknown",
        direction="unknown",
        sample_size=sample_size,
        independent_sessions=sessions,
        coverage=coverage,
        confidence="unavailable",
        status="unavailable",
        evidence_refs=(f"element:{key}",),
        limitations=(reason,),
        forbidden_claims=definition.forbidden_claims,
    )
    return ElementResultV6(key, definition.label, estimate, evidence_refs=(f"element:{key}",))


def _context_from(metadata: Mapping[str, Any] | None) -> BaselineContext:
    metadata = metadata or {}
    return BaselineContext(
        patch=metadata.get("patch"),
        hero_id=metadata.get("hero_id"),
        hero_function=metadata.get("hero_function"),
        lane_context=metadata.get("lane_context", metadata.get("lane")),
    )


def _core_and_stretch(matches: Sequence[Any]) -> tuple[set[Any], set[Any]]:
    counts = Counter(_hero(item) for item in matches if _hero(item) is not None)
    if len(counts) < 2:
        return set(counts), set()
    ordered = sorted(counts, key=lambda hero: (-counts[hero], repr(hero)))
    target = max(1, math.ceil(sum(counts.values()) * 0.60))
    core: set[Any] = set()
    running = 0
    for hero in ordered:
        core.add(hero)
        running += counts[hero]
        if running >= target:
            break
    return core, set(counts).difference(core)


def _transfer_values(matches: Sequence[Any], baseline_resolver: BaselineResolver | None, metadata: Mapping[str, Any] | None) -> tuple[float | None, Any, tuple[str, ...]]:
    core, stretch = _core_and_stretch(matches)
    if not core or not stretch:
        return None, None, ("familiar and stretch hero contexts both require evidence",)
    groups: dict[str, list[Any]] = defaultdict(list)
    for _index, item in enumerate(matches):
        if _hero(item) in core:
            groups["core"].append(item)
        elif _hero(item) in stretch:
            groups["stretch"].append(item)
    signals: dict[str, float | None] = {}
    for component in ("outcome", "activity", "survival"):
        component_values: dict[str, list[float]] = {"core": [], "stretch": []}
        for label in component_values:
            for item in groups[label]:
                if component == "outcome":
                    value = _get(item, "won")
                    numeric = None if value is None else (1.0 if bool(value) else 0.0)
                elif component == "activity":
                    numeric = involvement_per_minute(_get(item, "kills"), _get(item, "assists"), _get(item, "duration_seconds", _get(item, "duration")))
                else:
                    deaths = death_exposure_per_ten_minutes(_get(item, "deaths"), _get(item, "duration_seconds", _get(item, "duration")))
                    numeric = None if deaths is None else -deaths
                if numeric is not None:
                    component_values[label].append(numeric)
        if component_values["core"] and component_values["stretch"]:
            signals[component] = sum(component_values["stretch"]) / len(component_values["stretch"]) - sum(component_values["core"]) / len(component_values["core"])
    comparison = compare_transfer_signals(signals, practical_margin=0.0)
    value = {"positive": 1.0, "negative": -1.0, "mixed": 0.0, "unknown": None}[comparison.direction]
    return value, comparison, tuple(f"transfer:{component}" for component in signals)


def compute_elements(
    matches: Sequence[Any],
    *,
    metadata: Mapping[str, Any] | None = None,
    taxonomy_by_hero: Mapping[Any, Any] | None = None,
    taxonomy_by_match: Mapping[Any, Any] | None = None,
    baseline_resolver: BaselineResolver | None = None,
    thresholds: Mapping[str, MetricThreshold] | None = None,
    seed: int = 0,
    bootstrap_iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
) -> tuple[ElementResultV6, ...]:
    """Compute exactly seven Elements, preserving unavailable states."""

    items = tuple(matches)
    sample_size = len(items)
    session_count = len({_session_id(item, index) for index, item in enumerate(items)})
    coverage = 1.0 if items else 0.0
    metadata = metadata or {}
    thresholds = thresholds or DEFAULT_THRESHOLDS
    context = _context_from(metadata)

    definitions = {item.key: item for item in ELEMENT_DEFINITIONS}
    result: dict[str, ElementResultV6] = {}
    def evidence(key: str) -> tuple[str, ...]:
        return (f"element:{key}",)

    hero_counts = Counter(_hero(item) for item in items if _hero(item) is not None)
    hero_values = {session: tuple(_hero(item) for item in group if _hero(item) is not None) for session, group in _session_groups(items)}
    if hero_counts:
        def breadth_estimator(values: Sequence[Any]) -> float:
            return shannon_effective_count(Counter(value for value in values if value is not None))
        bread = clustered_bootstrap(hero_values, estimator=breadth_estimator, iterations=bootstrap_iterations, seed=seed)
        threshold = threshold_for("breadth_effective_count", thresholds)
        tier = threshold.supports_confidence(sample_size=sample_size, independent_sessions=session_count, coverage=coverage, stability=bootstrap_stability(bread.replicates, center=bread.point_estimate or 0.0, practical_margin=threshold.practical_margin))
        result["breadth"] = ElementResultV6(
            "breadth",
            definitions["breadth"].label,
            Estimate(
                bread.point_estimate,
                definitions["breadth"].unit,
                interval=bread.interval,
                zone="typical",
                direction="neutral",
                stability=bootstrap_stability(bread.replicates, center=bread.point_estimate or 0.0, practical_margin=threshold.practical_margin),
                sample_size=sample_size,
                independent_sessions=session_count,
                coverage=coverage,
                confidence=tier,  # type: ignore[arg-type]
                status="available" if sample_size >= 30 else "limited",
                evidence_refs=evidence("breadth"),
                supported_claims=(definitions["breadth"].description,),
                forbidden_claims=definitions["breadth"].forbidden_claims,
                bootstrap_method=bread.method,
            ),
            raw_metrics={"hero_counts": dict(hero_counts)},
            evidence_refs=evidence("breadth"),
        )
    else:
        result["breadth"] = _unavailable("breadth", definitions["breadth"], sample_size=sample_size, coverage=coverage, sessions=session_count, reason="no hero identifiers")

    taxonomy = taxonomy_by_match or {getattr(item, "match_id", index): taxonomy_by_hero.get(_hero(item)) if taxonomy_by_hero else None for index, item in enumerate(items)}
    toolkit, taxonomy_coverage = match_weighted_effective_count(taxonomy)
    if toolkit is None:
        result["toolkit"] = _unavailable("toolkit", definitions["toolkit"], sample_size=sample_size, coverage=taxonomy_coverage, sessions=session_count, reason="taxonomy coverage below 80%")
    else:
        # One label per match is sufficient for the bootstrap estimate; the
        # point estimate itself retains the full match-weighted taxonomy.
        labels_by_session: dict[str, list[Any]] = defaultdict(list)
        for index, item in enumerate(items):
            raw = taxonomy.get(_get(item, "match_id", index))
            if raw is None:
                continue
            labels = (raw,) if isinstance(raw, str) else tuple(raw) if not isinstance(raw, Mapping) else tuple(raw)
            labels_by_session[_session_id(item, index)].extend(labels)
        def toolkit_estimator(values: Sequence[Any]) -> float:
            return shannon_effective_count(Counter(value for value in values if value is not None))
        boot = clustered_bootstrap(labels_by_session, estimator=toolkit_estimator, iterations=bootstrap_iterations, seed=seed + 1)
        stability = bootstrap_stability(boot.replicates, center=boot.point_estimate or toolkit, practical_margin=threshold_for("toolkit_effective_count", thresholds).practical_margin)
        result["toolkit"] = ElementResultV6(
            "toolkit",
            definitions["toolkit"].label,
            Estimate(
                toolkit,
                definitions["toolkit"].unit,
                interval=boot.interval,
                zone="typical",
                direction="neutral",
                stability=stability,
                sample_size=sample_size,
                independent_sessions=session_count,
                coverage=taxonomy_coverage,
                confidence=threshold_for("toolkit_effective_count", thresholds).supports_confidence(sample_size=sample_size, independent_sessions=session_count, coverage=taxonomy_coverage, stability=stability),  # type: ignore[arg-type]
                status="available" if sample_size >= 30 and taxonomy_coverage >= 0.80 else "limited",
                evidence_refs=evidence("toolkit"),
                supported_claims=(definitions["toolkit"].description,),
                forbidden_claims=definitions["toolkit"].forbidden_claims,
                bootstrap_method=boot.method,
            ),
            raw_metrics={"taxonomy_coverage": taxonomy_coverage},
            evidence_refs=evidence("toolkit"),
        )

    formulas = {
        "involvement": lambda item: involvement_per_minute(_get(item, "kills"), _get(item, "assists"), _get(item, "duration_seconds", _get(item, "duration"))),
        "finishing": lambda item: finishing_share(_get(item, "kills"), _get(item, "assists")),
        "death_exposure": lambda item: death_exposure_per_ten_minutes(_get(item, "deaths"), _get(item, "duration_seconds", _get(item, "duration"))),
    }
    for key, formula in formulas.items():
        values, session_ids, metric_coverage = _numeric_values(items, formula)
        baseline = None
        baseline_limitation = None
        if baseline_resolver is not None:
            resolution = baseline_resolver.resolve(context, definitions[key].metric_key)
            baseline = resolution.value if resolution.available else None
            baseline_limitation = "; ".join(resolution.limitations) if resolution.limitations else None
        result[key] = _estimate(
            key,
            definitions[key],
            values,
            session_ids,
            coverage=metric_coverage,
            baseline=baseline,
            raw_metrics={"baseline": baseline},
            evidence_refs=evidence(key),
            iterations=bootstrap_iterations,
            seed=seed + len(result),
            thresholds=thresholds,
            limitation=baseline_limitation,
        )

    transfer_value, transfer_comparison, transfer_refs = _transfer_values(items, baseline_resolver, metadata)
    if transfer_value is None or transfer_comparison is None:
        result["transfer"] = _unavailable("transfer", definitions["transfer"], sample_size=sample_size, coverage=coverage, sessions=session_count, reason="familiar/stretch comparison unavailable")
    else:
        direction = {"positive": "positive", "negative": "negative", "mixed": "mixed", "unknown": "unknown"}[transfer_comparison.direction]
        result["transfer"] = _estimate(
            "transfer",
            definitions["transfer"],
            [transfer_value],
            ["transfer"],
            coverage=len(transfer_refs) / 3 if transfer_refs else 0.0,
            value_override=transfer_value,
            direction_override=direction,
            raw_metrics=transfer_comparison.as_dict(),
            evidence_refs=transfer_refs or evidence("transfer"),
            iterations=max(1, min(bootstrap_iterations, 250)),
            seed=seed + 4,
            thresholds=thresholds,
            status_override="available" if session_count >= 8 else "limited",
            sample_size_override=sample_size,
            sessions_override=session_count,
        )

    session_component_values: dict[str, list[float]] = {"outcome": [], "activity": [], "death_exposure": []}
    for _, group in _session_groups(items):
        outcomes = [1.0 if bool(_get(item, "won")) else 0.0 for item in group if _get(item, "won") is not None]
        activity = [value for item in group if (value := involvement_per_minute(_get(item, "kills"), _get(item, "assists"), _get(item, "duration_seconds", _get(item, "duration")))) is not None]
        deaths = [value for item in group if (value := death_exposure_per_ten_minutes(_get(item, "deaths"), _get(item, "duration_seconds", _get(item, "duration")))) is not None]
        if outcomes:
            session_component_values["outcome"].append(sum(outcomes) / len(outcomes))
        if activity:
            session_component_values["activity"].append(sum(activity) / len(activity))
        if deaths:
            session_component_values["death_exposure"].append(sum(deaths) / len(deaths))
    consistency = compare_consistency_signals(session_component_values, usable_sessions=session_count)
    if consistency.direction == "unknown":
        result["consistency"] = _unavailable("consistency", definitions["consistency"], sample_size=sample_size, coverage=coverage, sessions=session_count, reason=f"requires {MIN_CONSISTENCY_SESSIONS} usable sessions and two-of-three agreement")
    else:
        consistency_value = 1.0 if consistency.direction == "stable" else 0.0 if consistency.direction == "variable" else 0.5
        direction = "positive" if consistency.direction == "stable" else "negative" if consistency.direction == "variable" else "mixed"
        result["consistency"] = _estimate(
            "consistency",
            definitions["consistency"],
            [consistency_value],
            ["consistency"],
            coverage=sum(value is not None for value in session_component_values.values()) / 3,
            value_override=consistency_value,
            direction_override=direction,
            raw_metrics=consistency.as_dict(),
            evidence_refs=tuple(f"consistency:{key}" for key in consistency.component_directions),
            iterations=max(1, min(bootstrap_iterations, 250)),
            seed=seed + 5,
            thresholds=thresholds,
            status_override="available" if session_count >= MIN_CONSISTENCY_SESSIONS else "limited",
            sample_size_override=sample_size,
            sessions_override=session_count,
        )

    return tuple(result[key] for key in PUBLIC_ELEMENT_KEYS)


calculate_elements = compute_elements


__all__ = ["ELEMENT_DEFINITIONS", "element_registry", "compute_elements", "calculate_elements"]

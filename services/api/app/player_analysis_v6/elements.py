"""The seven summary-only Free DNA v6 Elements.

Point estimates use match rows; uncertainty resamples complete sessions. Every
context-adjusted metric resolves its baseline per match.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from .baselines import BaselineResolver
from .constants import DEFAULT_BOOTSTRAP_ITERATIONS, MIN_CONSISTENCY_SESSIONS, PUBLIC_ELEMENT_KEYS
from .context_adjustment import adjusted_value_for_match, match_field, match_hero_id
from .metrics import (
    death_exposure_per_ten_minutes,
    finishing_share,
    involvement_per_minute,
    match_weighted_effective_count,
    robust_dispersion,
    shannon_effective_count,
    taxonomy_labels,
)
from .models import ElementDefinition, ElementResultV6, Estimate
from .statistics import BootstrapResult, bootstrap_stability, clustered_bootstrap
from .thresholds import DEFAULT_THRESHOLDS, MetricThreshold, threshold_for

ELEMENT_DEFINITIONS: tuple[ElementDefinition, ...] = (
    ElementDefinition("breadth", "Breadth", "How widely your matches are distributed across heroes.", "effective heroes", "breadth_effective_count", axis_left="focused pool", axis_right="broad pool"),
    ElementDefinition("toolkit", "Toolkit", "How many functional jobs your hero choices cover in the reviewed taxonomy.", "effective jobs", "toolkit_effective_count", minimum_coverage=0.80, axis_left="narrow toolkit", axis_right="versatile toolkit"),
    ElementDefinition("involvement", "Involvement", "Context-adjusted kills plus assists per minute.", "kills+assists/minute", "involvement_adjusted", minimum_sessions=8, axis_left="quieter participation", axis_right="frequent participation", forbidden_claims=("aggression", "positioning", "fight entry")),
    ElementDefinition("finishing", "Finishing", "Context-adjusted share of known kill-plus-assist events that are kills.", "kill share", "finishing_adjusted", minimum_sessions=8, axis_left="shared conversion", axis_right="personal conversion", forbidden_claims=("intent", "objective conversion")),
    ElementDefinition("death_exposure", "Death Exposure", "Context-adjusted deaths per ten minutes.", "deaths/10 minutes", "death_exposure_adjusted", minimum_sessions=8, axis_left="lower exposure", axis_right="higher exposure", forbidden_claims=("death quality", "positioning", "intention")),
    ElementDefinition("transfer", "Transfer", "Agreement when a familiar hero context is compared with stretch choices.", "multi-signal agreement", "transfer_outcome_delta", minimum_sessions=8, axis_left="does not transfer", axis_right="transfers across choices", forbidden_claims=("causality", "positioning", "intent")),
    ElementDefinition("consistency", "Consistency", "Robust session-to-session agreement across outcome, activity, and death exposure.", "session consistency", "consistency_outcome_dispersion", minimum_sessions=MIN_CONSISTENCY_SESSIONS, axis_left="variable expression", axis_right="consistent expression", forbidden_claims=("intent", "tilt", "causality")),
)


def element_registry() -> tuple[ElementDefinition, ...]:
    return ELEMENT_DEFINITIONS


def _get(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _hero(item: Any) -> Any:
    return match_hero_id(item)


def _session_id(item: Any, index: int) -> str:
    value = _get(item, "session_id")
    return str(value) if value not in (None, "") else f"session-{index + 1}"


def _session_groups(matches: Sequence[Any]) -> tuple[tuple[str, tuple[Any, ...]], ...]:
    groups: dict[str, list[Any]] = defaultdict(list)
    for index, item in enumerate(matches):
        groups[_session_id(item, index)].append(item)
    return tuple((key, tuple(groups[key])) for key in sorted(groups))


def _finite(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _threshold(key: str, thresholds: Mapping[str, MetricThreshold]) -> MetricThreshold:
    return threshold_for(key, thresholds)


def _stability(result: BootstrapResult, threshold: MetricThreshold, *, direction: str, zone: str, center: float = 0.0) -> float:
    if not result.replicates:
        return 0.0
    if threshold.zone_mode in {"cutoff", "dispersion"}:
        # Consistency's public bootstrap is an agreement score (+1 stable,
        # -1 variable, 0 mixed), while its calibration artifact stores the
        # underlying dispersion cutoffs. Translate that score back to the
        # low/high dispersion zones before measuring classification stability.
        if threshold.zone_mode == "dispersion" and all(-1.0 <= float(value) <= 1.0 for value in result.replicates):
            return sum(
                ("low" if float(value) > 0.5 else "high" if float(value) < -0.5 else "typical") == zone
                for value in result.replicates
            ) / len(result.replicates)
        return sum(threshold.zone(value) == zone for value in result.replicates) / len(result.replicates)
    if direction in {"positive", "negative"}:
        return bootstrap_stability(result.replicates, direction=direction, center=center, practical_margin=threshold.practical_margin)
    return bootstrap_stability(result.replicates, center=center, practical_margin=threshold.practical_margin)


def _interval_clears_zone(result: BootstrapResult, threshold: MetricThreshold, zone: str) -> bool:
    if result.interval is None or zone == "unknown":
        return False
    lower, upper = result.interval
    if threshold.zone_mode == "dispersion":
        # The consistency Element reports the signed agreement score rather
        # than exposing a synthetic aggregate dispersion as its public value.
        if all(-1.0 <= float(value) <= 1.0 for value in result.replicates):
            if zone == "low":
                return lower > 0.0
            if zone == "high":
                return upper < 0.0
        if zone == "low" and threshold.stable_cutoff is not None:
            return upper < threshold.stable_cutoff
        if zone == "high" and threshold.variable_cutoff is not None:
            return lower > threshold.variable_cutoff
        if zone == "typical" and threshold.stable_cutoff is not None and threshold.variable_cutoff is not None:
            return lower >= threshold.stable_cutoff and upper <= threshold.variable_cutoff
        return False
    if threshold.low_cutoff is None or threshold.high_cutoff is None:
        low = -threshold.practical_margin
        high = threshold.practical_margin
    else:
        low, high = threshold.low_cutoff, threshold.high_cutoff
    if zone == "low":
        return upper < low
    if zone == "high":
        return lower > high
    if zone == "typical":
        return lower >= low and upper <= high
    return False


def _status_and_limitations(
    definition: ElementDefinition,
    *,
    sample_size: int,
    sessions: int,
    coverage: float,
    threshold: MetricThreshold,
    stability: float,
    requested_status: str | None = None,
    extra: Sequence[str] = (),
) -> tuple[str, str, tuple[str, ...]]:
    minimum_sample = max(definition.minimum_sample, threshold.min_sample)
    minimum_sessions = max(definition.minimum_sessions, threshold.min_sessions)
    minimum_coverage = max(definition.minimum_coverage, threshold.min_coverage)
    status = "available" if sample_size >= minimum_sample else "limited"
    if sessions < minimum_sessions or coverage < minimum_coverage:
        status = "limited"
    if requested_status in {"available", "limited", "unavailable"}:
        status = requested_status
    limitations: list[str] = []
    if sample_size < minimum_sample:
        limitations.append(f"fewer than {minimum_sample} usable matches")
    if sessions < minimum_sessions:
        limitations.append(f"fewer than {minimum_sessions} independent sessions")
    if coverage < minimum_coverage:
        limitations.append(f"coverage below {minimum_coverage:.0%}")
    limitations.extend(str(item) for item in extra if item)
    confidence = threshold.supports_confidence(sample_size=sample_size, independent_sessions=sessions, coverage=coverage, stability=stability)
    if status in {"limited", "unavailable"} and confidence == "high":
        confidence = "descriptive"
    if status == "unavailable":
        confidence = "unavailable"
    return status, confidence, tuple(dict.fromkeys(limitations))


def _element(
    definition: ElementDefinition,
    *,
    result: BootstrapResult | None,
    value: float | None,
    direction: str,
    zone: str,
    sample_size: int,
    sessions: int,
    coverage: float,
    thresholds: Mapping[str, MetricThreshold],
    evidence_refs: Sequence[str],
    raw_metrics: Mapping[str, Any] | None = None,
    requested_status: str | None = None,
    extra_limitations: Sequence[str] = (),
) -> ElementResultV6:
    threshold = _threshold(definition.metric_key, thresholds)
    if result is None or value is None:
        estimate = Estimate(None, definition.unit, zone="unknown", direction="unknown", sample_size=sample_size, independent_sessions=sessions, coverage=coverage, confidence="unavailable", status="unavailable", evidence_refs=tuple(evidence_refs), limitations=tuple(extra_limitations) or ("metric unavailable",), forbidden_claims=definition.forbidden_claims)
        return ElementResultV6(definition.key, definition.label, estimate, raw_metrics=raw_metrics or {}, evidence_refs=tuple(evidence_refs))
    stability = _stability(result, threshold, direction=direction, zone=zone)
    status, confidence, limitations = _status_and_limitations(definition, sample_size=sample_size, sessions=sessions, coverage=coverage, threshold=threshold, stability=stability, requested_status=requested_status, extra=extra_limitations)
    if confidence == "high" and not _interval_clears_zone(result, threshold, zone):
        confidence = "moderate"
        limitations = tuple(dict.fromkeys((*limitations, "95% interval does not clear the reported zone boundary")))
    estimate = Estimate(value, definition.unit, interval=result.interval, zone=zone, direction=direction, stability=stability, sample_size=sample_size, independent_sessions=sessions, coverage=coverage, confidence=confidence, status=status, evidence_refs=tuple(evidence_refs), limitations=limitations, supported_claims=(definition.description,), forbidden_claims=definition.forbidden_claims, bootstrap_method=result.method)  # type: ignore[arg-type]
    metrics = dict(raw_metrics or {})
    metrics.setdefault("bootstrap", result.as_dict(include_replicates=False))
    metrics.setdefault("bootstrap_replicates", list(result.replicates))
    return ElementResultV6(definition.key, definition.label, estimate, raw_metrics=metrics, evidence_refs=tuple(evidence_refs))


def _unavailable(definition: ElementDefinition, sample_size: int, sessions: int, coverage: float, reason: str) -> ElementResultV6:
    estimate = Estimate(None, definition.unit, zone="unknown", direction="unknown", sample_size=sample_size, independent_sessions=sessions, coverage=coverage, confidence="unavailable", status="unavailable", evidence_refs=(f"element:{definition.key}",), limitations=(reason,), forbidden_claims=definition.forbidden_claims)
    return ElementResultV6(definition.key, definition.label, estimate, evidence_refs=(f"element:{definition.key}",))


def _metric_raw(item: Any, key: str) -> float | None:
    duration = match_field(item, "duration_seconds", match_field(item, "duration"))
    if key == "involvement_adjusted":
        return involvement_per_minute(match_field(item, "kills"), match_field(item, "assists"), duration)
    if key == "finishing_adjusted":
        return finishing_share(match_field(item, "kills"), match_field(item, "assists"))
    if key == "death_exposure_adjusted":
        return death_exposure_per_ten_minutes(match_field(item, "deaths"), duration)
    return None


def _adjusted_rows(matches: Sequence[Any], metric: str, *, baseline_resolver: BaselineResolver | None, taxonomy_by_hero: Mapping[Any, Any] | None) -> tuple[list[float], list[str], float, list[dict[str, Any]]]:
    values: list[float] = []
    sessions: list[str] = []
    audit: list[dict[str, Any]] = []
    for index, item in enumerate(matches):
        raw = _metric_raw(item, metric)
        adjusted, resolution = adjusted_value_for_match(item, metric, raw, baseline_resolver=baseline_resolver, taxonomy_by_hero=taxonomy_by_hero)
        if adjusted is None:
            continue
        values.append(adjusted)
        sessions.append(_session_id(item, index))
        audit.append({"match_id": _get(item, "match_id", index), "context": resolution.as_dict() if resolution else None})
    return values, sessions, len(values) / len(matches) if matches else 0.0, audit


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


def _outcome(item: Any) -> float | None:
    value = match_field(item, "won")
    return None if value is None else (1.0 if bool(value) else 0.0)


def _adjusted_component(item: Any, component: str, *, baseline_resolver: BaselineResolver | None, taxonomy_by_hero: Mapping[Any, Any] | None) -> float | None:
    if component == "outcome":
        return _outcome(item)
    metric = "involvement_adjusted" if component == "activity" else "death_exposure_adjusted"
    raw = _metric_raw(item, metric)
    value, _ = adjusted_value_for_match(item, metric, raw, baseline_resolver=baseline_resolver, taxonomy_by_hero=taxonomy_by_hero)
    return None if value is None else (-value if component == "survival" else value)


def _transfer_components(records: Sequence[Mapping[str, Any]]) -> dict[str, float | None]:
    grouped: dict[str, dict[str, list[float]]] = {"core": defaultdict(list), "stretch": defaultdict(list)}
    for record in records:
        bucket = str(record.get("bucket", ""))
        if bucket not in grouped:
            continue
        for component in ("outcome", "activity", "survival"):
            value = _finite(record.get(component))
            if value is not None:
                grouped[bucket][component].append(value)
    result: dict[str, float | None] = {}
    for component in ("outcome", "activity", "survival"):
        left, right = grouped["core"][component], grouped["stretch"][component]
        result[component] = sum(right) / len(right) - sum(left) / len(left) if left and right else None
    return result


def _transfer_component_directions(
    components: Mapping[str, float | None],
    thresholds: Mapping[str, MetricThreshold],
) -> dict[str, str]:
    keys = {
        "outcome": "transfer_outcome_delta",
        "activity": "transfer_activity_delta",
        "survival": "transfer_survival_delta",
    }
    directions: dict[str, str] = {}
    for component, threshold_key in keys.items():
        threshold = _threshold(threshold_key, thresholds)
        directions[component] = threshold.direction(components.get(component))
    return directions


def _transfer_direction(
    directions: Mapping[str, str],
    confident_directions: Mapping[str, str] | None = None,
) -> str:
    confident_directions = confident_directions or directions
    usable = sum(value != "unknown" for value in directions.values())
    if usable < 2:
        return "unknown"
    positive = sum(value == "positive" for value in directions.values())
    negative = sum(value == "negative" for value in directions.values())
    confidently_positive = any(value == "positive" for value in confident_directions.values())
    confidently_negative = any(value == "negative" for value in confident_directions.values())
    if positive >= 2 and not confidently_negative:
        return "positive"
    if negative >= 2 and not confidently_positive:
        return "negative"
    return "mixed"


def _transfer_score(
    records: Sequence[Mapping[str, Any]],
    thresholds: Mapping[str, MetricThreshold],
    confident_directions: Mapping[str, str] | None = None,
) -> float:
    components = _transfer_components(records)
    component_directions = _transfer_component_directions(components, thresholds)
    direction = _transfer_direction(component_directions, confident_directions)
    positive = sum(value == "positive" for value in component_directions.values())
    negative = sum(value == "negative" for value in component_directions.values())
    if direction == "positive":
        return 1.0 if positive == 3 else 2.0 / 3.0
    if direction == "negative":
        return -1.0 if negative == 3 else -2.0 / 3.0
    if direction == "mixed":
        return 0.0
    return math.nan


def _consistency_rows(matches: Sequence[Any], *, baseline_resolver: BaselineResolver | None, taxonomy_by_hero: Mapping[Any, Any] | None) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for session_id, group in _session_groups(matches):
        row: dict[str, Any] = {"session_id": session_id}
        for component in ("outcome", "activity", "survival"):
            values = [_adjusted_component(item, component, baseline_resolver=baseline_resolver, taxonomy_by_hero=taxonomy_by_hero) for item in group]
            usable = [value for value in values if value is not None]
            if usable:
                row[component] = sum(usable) / len(usable)
        if len(row) >= 3:
            rows.append(row)
    return tuple(rows)


def _consistency_component_key(component: str) -> str:
    return {
        "outcome": "consistency_outcome_dispersion",
        "activity": "consistency_activity_dispersion",
        "survival": "consistency_death_dispersion",
    }[component]


def _consistency_classification(
    rows: Sequence[Mapping[str, Any]],
    thresholds: Mapping[str, MetricThreshold],
    confident_directions: Mapping[str, str] | None = None,
) -> tuple[str, dict[str, str], dict[str, float | None]]:
    directions: dict[str, str] = {}
    dispersions: dict[str, float | None] = {}
    for component in ("outcome", "activity", "survival"):
        values = [float(row[component]) for row in rows if _finite(row.get(component)) is not None]
        dispersion = robust_dispersion(values)
        dispersions[component] = dispersion
        threshold = _threshold(_consistency_component_key(component), thresholds)
        stable = threshold.stable_cutoff
        variable = threshold.variable_cutoff
        if dispersion is None:
            directions[component] = "unknown"
        elif stable is not None and dispersion < stable:
            directions[component] = "stable"
        elif variable is not None and dispersion > variable:
            directions[component] = "variable"
        elif stable is None and dispersion <= threshold.practical_margin:
            directions[component] = "stable"
        elif variable is None and dispersion > threshold.practical_margin:
            directions[component] = "variable"
        else:
            directions[component] = "neutral"
    confident_directions = confident_directions or directions
    usable_count = sum(value != "unknown" for value in directions.values())
    if usable_count < 2:
        return "unknown", directions, dispersions
    stable_count = sum(value == "stable" for value in directions.values())
    variable_count = sum(value == "variable" for value in directions.values())
    confidently_stable = any(value == "stable" for value in confident_directions.values())
    confidently_variable = any(value == "variable" for value in confident_directions.values())
    if stable_count >= 2 and not confidently_variable:
        direction = "stable"
    elif variable_count >= 2 and not confidently_stable:
        direction = "variable"
    else:
        direction = "mixed"
    return direction, directions, dispersions


def _consistency_score(
    rows: Sequence[Mapping[str, Any]],
    thresholds: Mapping[str, MetricThreshold],
    confident_directions: Mapping[str, str] | None = None,
) -> float:
    direction, _components, _dispersions = _consistency_classification(
        rows,
        thresholds,
        confident_directions,
    )
    return {"stable": 1.0, "variable": -1.0, "mixed": 0.0, "unknown": math.nan}[direction]


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
    """Compute exactly seven Elements with no v5 feature dependency."""

    del metadata
    items = tuple(matches)
    sample_size = len(items)
    session_count = len({_session_id(item, index) for index, item in enumerate(items)})
    thresholds = thresholds or DEFAULT_THRESHOLDS
    definitions = {item.key: item for item in ELEMENT_DEFINITIONS}
    result: dict[str, ElementResultV6] = {}

    hero_counts = Counter(_hero(item) for item in items if _hero(item) is not None)
    if hero_counts:
        groups = {session_id: [_hero(row) for row in group if _hero(row) is not None] for session_id, group in _session_groups(items)}
        breadth_boot = clustered_bootstrap(groups, estimator=lambda values: shannon_effective_count(Counter(value for value in values if value is not None)), iterations=bootstrap_iterations, seed=seed)
        breadth_threshold = _threshold(definitions["breadth"].metric_key, thresholds)
        breadth_zone = breadth_threshold.zone(breadth_boot.point_estimate)
        breadth_direction = breadth_threshold.direction(breadth_boot.point_estimate)
        result["breadth"] = _element(definitions["breadth"], result=breadth_boot, value=breadth_boot.point_estimate, direction=breadth_direction, zone=breadth_zone, sample_size=sum(hero_counts.values()), sessions=session_count, coverage=sum(hero_counts.values()) / len(items) if items else 0.0, thresholds=thresholds, evidence_refs=("element:breadth",), raw_metrics={"hero_counts": dict(hero_counts)})
    else:
        result["breadth"] = _unavailable(definitions["breadth"], sample_size, session_count, 0.0, "no hero identifiers")

    by_match: dict[Any, Any] = {}
    for index, item in enumerate(items):
        match_id = _get(item, "match_id", index)
        # Preserve missing taxonomy rows in the denominator. Omitting them
        # would make any non-empty partial mapping appear to have 100% coverage.
        by_match[match_id] = None
        if taxonomy_by_match and match_id in taxonomy_by_match:
            by_match[match_id] = taxonomy_by_match[match_id]
        elif taxonomy_by_hero and _hero(item) in taxonomy_by_hero:
            by_match[match_id] = taxonomy_by_hero[_hero(item)]
    toolkit, taxonomy_coverage = match_weighted_effective_count(by_match)
    if toolkit is None:
        result["toolkit"] = _unavailable(definitions["toolkit"], sample_size, session_count, taxonomy_coverage, "taxonomy coverage below 80%")
    else:
        label_groups: dict[str, list[tuple[str, ...]]] = defaultdict(list)
        for index, item in enumerate(items):
            raw = by_match.get(_get(item, "match_id", index))
            if raw is None:
                continue
            labels = taxonomy_labels(raw)
            if labels:
                label_groups[_session_id(item, index)].append(tuple(dict.fromkeys(labels)))
        def estimate_toolkit(rows: Sequence[Any]) -> float:
            counts: dict[str, float] = defaultdict(float)
            for labels in rows:
                if isinstance(labels, (tuple, list)) and labels:
                    weight = 1.0 / len(labels)
                    for label in labels:
                        counts[str(label)] += weight
            return shannon_effective_count(counts)
        toolkit_boot = clustered_bootstrap(label_groups, estimator=estimate_toolkit, iterations=bootstrap_iterations, seed=seed + 1)
        toolkit_threshold = _threshold(definitions["toolkit"].metric_key, thresholds)
        toolkit_zone = toolkit_threshold.zone(toolkit)
        covered_matches = sum(bool(taxonomy_labels(raw)) for raw in by_match.values())
        result["toolkit"] = _element(definitions["toolkit"], result=toolkit_boot, value=toolkit, direction=toolkit_threshold.direction(toolkit), zone=toolkit_zone, sample_size=covered_matches, sessions=session_count, coverage=taxonomy_coverage, thresholds=thresholds, evidence_refs=("element:toolkit",), raw_metrics={"taxonomy_coverage": taxonomy_coverage})

    for offset, key in enumerate(("involvement", "finishing", "death_exposure"), start=2):
        metric = definitions[key].metric_key
        values, session_ids, metric_coverage, audit = _adjusted_rows(items, metric, baseline_resolver=baseline_resolver, taxonomy_by_hero=taxonomy_by_hero)
        if not values:
            result[key] = _unavailable(definitions[key], sample_size, session_count, metric_coverage, "no usable context-adjusted summary values")
            continue
        boot = clustered_bootstrap(values, session_ids, iterations=bootstrap_iterations, seed=seed + offset)
        metric_threshold = _threshold(metric, thresholds)
        direction = metric_threshold.direction(boot.point_estimate)
        zone = metric_threshold.zone(boot.point_estimate)
        result[key] = _element(definitions[key], result=boot, value=boot.point_estimate, direction=direction, zone=zone, sample_size=len(values), sessions=len(set(session_ids)), coverage=metric_coverage, thresholds=thresholds, evidence_refs=(f"element:{key}",), raw_metrics={"baseline_audit": audit})

    core, stretch = _core_and_stretch(items)
    records: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        bucket = "core" if _hero(item) in core else "stretch" if _hero(item) in stretch else ""
        if not bucket:
            continue
        record: dict[str, Any] = {"bucket": bucket, "session_id": _session_id(item, index)}
        for component in ("outcome", "activity", "survival"):
            record[component] = _adjusted_component(item, component, baseline_resolver=baseline_resolver, taxonomy_by_hero=taxonomy_by_hero)
        if any(record[component] is not None for component in ("outcome", "activity", "survival")):
            records.append(record)
    usable_core = sum(any(record.get(component) is not None for component in ("outcome", "activity", "survival")) for record in records if record.get("bucket") == "core")
    usable_stretch = sum(any(record.get(component) is not None for component in ("outcome", "activity", "survival")) for record in records if record.get("bucket") == "stretch")
    transfer_sessions = len({str(record["session_id"]) for record in records})
    if not core or not stretch or not records:
        result["transfer"] = _unavailable(definitions["transfer"], sample_size, session_count, 0.0, "familiar and stretch hero contexts both require evidence")
    else:
        ids = [str(record["session_id"]) for record in records]
        point_components = _transfer_components(records)
        component_directions = _transfer_component_directions(point_components, thresholds)
        component_intervals: dict[str, list[float] | None] = {}
        component_replicates: dict[str, tuple[float, ...]] = {}
        confident_component_directions: dict[str, str] = {}
        for component_index, component in enumerate(("outcome", "activity", "survival")):
            def component_estimator(rows: Sequence[Mapping[str, Any]], component: str = component) -> float:
                value = _transfer_components(rows).get(component)
                return float(value) if value is not None else math.nan
            component_boot = clustered_bootstrap(records, ids, estimator=component_estimator, iterations=bootstrap_iterations, seed=seed + 20 + component_index)
            component_intervals[component] = list(component_boot.interval) if component_boot.interval else None
            component_replicates[component] = component_boot.replicates
            threshold = _threshold(f"transfer_{component}_delta", thresholds)
            if component_boot.interval is None:
                confident_component_directions[component] = "unknown"
            elif component_boot.lower is not None and component_boot.lower > threshold.practical_margin:
                confident_component_directions[component] = "positive"
            elif component_boot.upper is not None and component_boot.upper < -threshold.practical_margin:
                confident_component_directions[component] = "negative"
            else:
                confident_component_directions[component] = "neutral"
        direction = _transfer_direction(component_directions, confident_component_directions)
        transfer_boot = clustered_bootstrap(
            records,
            ids,
            estimator=lambda rows: _transfer_score(rows, thresholds, confident_component_directions),
            iterations=bootstrap_iterations,
            seed=seed + 5,
        )
        resolved_baseline_values = sum(record.get(component) is not None for record in records for component in ("activity", "survival"))
        # Every core/stretch match is an opportunity for each adjusted
        # component.  Excluding fully unresolved matches from the denominator
        # would inflate coverage precisely when the baseline is weakest.
        transfer_coverage = resolved_baseline_values / max(1, 2 * len(records))
        transfer_limitations: list[str] = []
        if usable_core < 10:
            transfer_limitations.append("fewer than 10 usable core matches")
        if usable_stretch < 10:
            transfer_limitations.append("fewer than 10 usable stretch matches")
        if transfer_sessions < 8:
            transfer_limitations.append("fewer than 8 independent sessions")
        if transfer_coverage < _threshold("transfer_activity_delta", thresholds).min_coverage:
            transfer_limitations.append("comparable baseline coverage below 70%")
        if transfer_limitations:
            status = "limited"
        else:
            status = None
        result["transfer"] = _element(
            definitions["transfer"],
            result=transfer_boot,
            value=transfer_boot.point_estimate,
            direction=direction,
            # Low dispersion is the stable/right-side public outcome; the
            # direction remains positive for stable and negative for variable.
            zone={"positive": "high", "negative": "low", "mixed": "typical", "unknown": "unknown"}[direction],
            sample_size=len(records),
            sessions=transfer_sessions,
            coverage=transfer_coverage,
            thresholds=thresholds,
            evidence_refs=tuple(f"transfer:{component}" for component in point_components if point_components[component] is not None),
            raw_metrics={
                "core_hero_ids": sorted(core, key=repr),
                "stretch_hero_ids": sorted(stretch, key=repr),
                "usable_core_matches": usable_core,
                "usable_stretch_matches": usable_stretch,
                "components": {"direction": direction, "component_deltas": point_components, "component_directions": component_directions, "confident_component_directions": confident_component_directions},
                "component_intervals": component_intervals,
                "component_bootstrap_replicates": component_replicates,
            },
            requested_status=status,
            extra_limitations=transfer_limitations,
        )

    consistency_rows: list[dict[str, Any]] = []
    for session_id, group in _session_groups(items):
        row: dict[str, Any] = {"session_id": session_id}
        for component in ("outcome", "activity", "survival"):
            component_values = [_adjusted_component(item, component, baseline_resolver=baseline_resolver, taxonomy_by_hero=taxonomy_by_hero) for item in group]
            usable = [value for value in component_values if value is not None]
            if usable:
                row[component] = sum(usable) / len(usable)
        if len(row) >= 3:
            consistency_rows.append(row)
    if len(consistency_rows) < MIN_CONSISTENCY_SESSIONS:
        result["consistency"] = _unavailable(definitions["consistency"], sample_size, session_count, 0.0, f"requires {MIN_CONSISTENCY_SESSIONS} usable sessions and two-of-three agreement")
    else:
        ids = [str(row["session_id"]) for row in consistency_rows]
        consistency_component_replicates: dict[str, tuple[float, ...]] = {}
        consistency_component_intervals: dict[str, list[float] | None] = {}
        consistency_confident_directions: dict[str, str] = {}
        for component_index, component in enumerate(("outcome", "activity", "survival")):
            def component_estimator(rows: Sequence[Mapping[str, Any]], component: str = component) -> float:
                values = [float(row[component]) for row in rows if _finite(row.get(component)) is not None]
                dispersion = robust_dispersion(values)
                return float(dispersion) if dispersion is not None else math.nan
            component_boot = clustered_bootstrap(consistency_rows, ids, estimator=component_estimator, iterations=bootstrap_iterations, seed=seed + 30 + component_index)
            consistency_component_replicates[component] = component_boot.replicates
            consistency_component_intervals[component] = list(component_boot.interval) if component_boot.interval else None
            threshold = _threshold(_consistency_component_key(component), thresholds)
            stable_cutoff = threshold.stable_cutoff if threshold.stable_cutoff is not None else threshold.practical_margin
            variable_cutoff = threshold.variable_cutoff if threshold.variable_cutoff is not None else threshold.practical_margin
            if component_boot.interval is None:
                consistency_confident_directions[component] = "unknown"
            elif component_boot.upper is not None and component_boot.upper < stable_cutoff:
                consistency_confident_directions[component] = "stable"
            elif component_boot.lower is not None and component_boot.lower > variable_cutoff:
                consistency_confident_directions[component] = "variable"
            else:
                consistency_confident_directions[component] = "neutral"
        consistency_direction, component_directions, component_dispersions = _consistency_classification(
            consistency_rows,
            thresholds,
            consistency_confident_directions,
        )
        direction = {"stable": "positive", "variable": "negative", "mixed": "mixed", "unknown": "unknown"}[consistency_direction]
        consistency_boot = clustered_bootstrap(
            consistency_rows,
            ids,
            estimator=lambda rows: _consistency_score(rows, thresholds, consistency_confident_directions),
            iterations=bootstrap_iterations,
            seed=seed + 6,
        )
        consistency_coverage = len(consistency_rows) / session_count if session_count else 0.0
        result["consistency"] = _element(
            definitions["consistency"],
            result=consistency_boot,
            value=consistency_boot.point_estimate,
            direction=direction,
            zone={"positive": "low", "negative": "high", "mixed": "typical", "unknown": "unknown"}[direction],
            sample_size=sample_size,
            sessions=len(consistency_rows),
            coverage=consistency_coverage,
            thresholds=thresholds,
            evidence_refs=tuple(f"consistency:{key}" for key in component_directions),
            raw_metrics={"components": {"direction": consistency_direction, "component_directions": component_directions, "confident_component_directions": consistency_confident_directions, "component_dispersion": component_dispersions}, "component_intervals": consistency_component_intervals, "component_bootstrap_replicates": consistency_component_replicates},
        )

    return tuple(result[key] for key in PUBLIC_ELEMENT_KEYS)


calculate_elements = compute_elements

__all__ = ["ELEMENT_DEFINITIONS", "element_registry", "compute_elements", "calculate_elements"]

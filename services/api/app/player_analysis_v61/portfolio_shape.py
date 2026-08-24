"""Portfolio shape, chronological thirds, and cross-fitted core distance."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.player_analysis_v6.metrics import shannon_effective_count, taxonomy_labels


def _get(value: Any, key: str, default: Any = None) -> Any:
    return value.get(key, default) if isinstance(value, Mapping) else getattr(value, key, default)


def _hero(value: Any) -> int | None:
    hero = _get(value, "hero_id")
    return hero if isinstance(hero, int) and hero > 0 else None


def _session(value: Any, index: int) -> str:
    session_id = _get(value, "session_id")
    return str(session_id) if session_id not in (None, "") else f"match:{index}"


def _hero_counts(matches: Sequence[Any]) -> Counter[int]:
    counts: Counter[int] = Counter()
    for match in matches:
        hero_id = _hero(match)
        if hero_id is not None:
            counts[hero_id] += 1
    return counts


def _labels(hero_id: int, taxonomy_by_hero: Mapping[Any, Any] | None) -> tuple[str, ...]:
    if not taxonomy_by_hero:
        return ()
    return taxonomy_labels(taxonomy_by_hero.get(hero_id, taxonomy_by_hero.get(str(hero_id))))


def _simpson_effective(counts: Mapping[Any, float]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    concentration = sum((count / total) ** 2 for count in counts.values())
    return 1.0 / concentration if concentration else 0.0


def _top_share(counts: Mapping[Any, float], count: int) -> float:
    total = sum(counts.values())
    return sum(sorted(counts.values(), reverse=True)[:count]) / total if total else 0.0


def _mass_core(counts: Mapping[int, int], target: float = 0.50) -> tuple[int, ...]:
    total = sum(counts.values())
    if not total:
        return ()
    selected: list[int] = []
    cumulative = 0
    for hero_id, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        selected.append(hero_id)
        cumulative += count
        if cumulative / total >= target:
            break
    return tuple(selected)


def chronological_thirds(matches: Sequence[Any]) -> tuple[tuple[Any, ...], ...]:
    """Return exactly three ordered, non-overlapping buckets."""

    ordered = sorted(
        matches,
        key=lambda item: (
            _get(item, "started_at", _get(item, "start_time")) is None,
            _get(item, "started_at", _get(item, "start_time")) or 0,
            _get(item, "match_id") or 0,
        ),
    )
    size = len(ordered)
    boundaries = (0, size // 3, (2 * size) // 3, size)
    return tuple(tuple(ordered[boundaries[index] : boundaries[index + 1]]) for index in range(3))


def _fractional_job_mass(
    matches: Sequence[Any], taxonomy_by_hero: Mapping[Any, Any] | None
) -> tuple[dict[str, float], float]:
    mass: dict[str, float] = defaultdict(float)
    covered = 0
    for match in matches:
        hero_id = _hero(match)
        labels = _labels(hero_id, taxonomy_by_hero) if hero_id is not None else ()
        if not labels:
            continue
        covered += 1
        share = 1.0 / len(labels)
        for label in labels:
            mass[label] += share
    return dict(sorted(mass.items())), covered / len(matches) if matches else 0.0


def _taxonomy_sensitivity(
    matches: Sequence[Any],
    taxonomy_by_hero: Mapping[Any, Any] | None,
    reference_effective_count: float,
) -> dict[str, Any]:
    labels = sorted(
        {
            label
            for match in matches
            if (hero_id := _hero(match)) is not None
            for label in _labels(hero_id, taxonomy_by_hero)
        }
    )
    alternatives: list[float] = []
    for removed in labels:
        mass: dict[str, float] = defaultdict(float)
        for match in matches:
            hero_id = _hero(match)
            hero_labels = tuple(
                label
                for label in (_labels(hero_id, taxonomy_by_hero) if hero_id is not None else ())
                if label != removed
            )
            if not hero_labels:
                continue
            for label in hero_labels:
                mass[label] += 1.0 / len(hero_labels)
        alternatives.append(shannon_effective_count(mass))
    deviation = max(
        (abs(value - reference_effective_count) for value in alternatives),
        default=0.0,
    )
    return {
        "version": "taxonomy-leave-one-label-1.0.0",
        "perturbations": len(alternatives),
        "effective_count_min": min(alternatives, default=reference_effective_count),
        "effective_count_max": max(alternatives, default=reference_effective_count),
        "maximum_deviation": deviation,
        "stable": deviation <= 0.50,
    }


def _jensen_shannon(left: Mapping[Any, float], right: Mapping[Any, float]) -> float:
    keys = set(left) | set(right)
    left_total, right_total = sum(left.values()), sum(right.values())
    if not keys or left_total <= 0 or right_total <= 0:
        return 0.0
    p = {key: left.get(key, 0.0) / left_total for key in keys}
    q = {key: right.get(key, 0.0) / right_total for key in keys}
    midpoint = {key: (p[key] + q[key]) / 2.0 for key in keys}

    def divergence(source: Mapping[Any, float]) -> float:
        return sum(
            value * math.log(value / midpoint[key], 2)
            for key, value in source.items()
            if value > 0 and midpoint[key] > 0
        )

    return (divergence(p) + divergence(q)) / 2.0


@dataclass(frozen=True, slots=True)
class DistanceRecord:
    match: Any
    familiarity_distance: float
    function_distance: float
    combined_distance: float
    band: str
    fold: int


def cross_fitted_distance_records(
    matches: Sequence[Any],
    taxonomy_by_hero: Mapping[Any, Any] | None,
    calibration: Mapping[str, Any] | None = None,
) -> tuple[DistanceRecord, ...]:
    indexed = list(enumerate(matches))
    fold_by_session: dict[str, int] = {}
    for index, match in indexed:
        session_id = _session(match, index)
        fold_by_session.setdefault(session_id, len(fold_by_session) % 2)
    records: list[DistanceRecord] = []
    for verification_fold in (0, 1):
        training = [
            match
            for index, match in indexed
            if fold_by_session[_session(match, index)] != verification_fold
        ]
        verification = [
            (index, match)
            for index, match in indexed
            if fold_by_session[_session(match, index)] == verification_fold
        ]
        hero_counts = _hero_counts(training)
        total = sum(hero_counts.values())
        core = set(_mass_core(hero_counts, 0.50))
        core_jobs: dict[str, float] = defaultdict(float)
        for hero_id in core:
            labels = _labels(hero_id, taxonomy_by_hero)
            if not labels:
                continue
            share = hero_counts[hero_id] / max(total, 1) / len(labels)
            for label in labels:
                core_jobs[label] += share
        provisional: list[tuple[int, Any, float, float, float]] = []
        for index, match in verification:
            verification_hero_id = _hero(match)
            frequency = (
                hero_counts.get(verification_hero_id, 0) / max(total, 1)
                if verification_hero_id is not None
                else 0.0
            )
            familiarity = min(1.0, -math.log(max(frequency, 1 / max(total * 4, 1))) / math.log(max(total * 4, 2)))
            hero_labels = (
                set(_labels(verification_hero_id, taxonomy_by_hero))
                if verification_hero_id is not None
                else set()
            )
            core_label_set = set(core_jobs)
            overlap = (
                len(hero_labels & core_label_set) / len(hero_labels | core_label_set)
                if hero_labels and core_label_set
                else 0.0
            )
            function = 1.0 - overlap
            combined = 0.65 * familiarity + 0.35 * function
            provisional.append((index, match, familiarity, function, combined))
        training_distances: list[float] = []
        for match in training:
            training_hero_id = _hero(match)
            frequency = (
                hero_counts.get(training_hero_id, 0) / max(total, 1)
                if training_hero_id is not None
                else 0.0
            )
            familiarity = min(1.0, -math.log(max(frequency, 1 / max(total * 4, 1))) / math.log(max(total * 4, 2)))
            hero_labels = (
                set(_labels(training_hero_id, taxonomy_by_hero))
                if training_hero_id is not None
                else set()
            )
            core_label_set = set(core_jobs)
            overlap = (
                len(hero_labels & core_label_set) / len(hero_labels | core_label_set)
                if hero_labels and core_label_set
                else 0.0
            )
            training_distances.append(0.65 * familiarity + 0.35 * (1.0 - overlap))
        ordered_distances = sorted(training_distances)
        if calibration is None:
            core_cut = ordered_distances[max(0, int(len(ordered_distances) * 0.50) - 1)] if ordered_distances else 0.0
            stretch_cut = ordered_distances[max(0, int(len(ordered_distances) * 0.80) - 1)] if ordered_distances else 0.0
        else:
            bands = calibration.get("bands")
            if not isinstance(bands, Mapping):
                raise ValueError("V6.1 distance calibration is missing bands")
            core_cut = float(bands["core"]["maximum"])
            stretch_cut = float(bands["reliable_stretch"]["maximum"])
        for _index, match, familiarity, function, combined in provisional:
            band = "core" if combined <= core_cut else "reliable_stretch" if combined <= stretch_cut else "experimental_edge"
            records.append(DistanceRecord(match, familiarity, function, combined, band, verification_fold))
    return tuple(records)


def build_portfolio_shape(
    matches: Sequence[Any],
    taxonomy_by_hero: Mapping[Any, Any] | None,
    distance_calibration: Mapping[str, Any] | None = None,
    distance_records: Sequence[DistanceRecord] | None = None,
    include_taxonomy_sensitivity: bool = True,
) -> dict[str, Any]:
    hero_counts = _hero_counts(matches)
    job_mass, taxonomy_coverage = _fractional_job_mass(matches, taxonomy_by_hero)
    thirds = chronological_thirds(matches)
    third_hero_counts = [_hero_counts(part) for part in thirds]
    third_job_mass = [_fractional_job_mass(part, taxonomy_by_hero)[0] for part in thirds]
    distances = tuple(distance_records) if distance_records is not None else cross_fitted_distance_records(
        matches,
        taxonomy_by_hero,
        calibration=distance_calibration,
    )
    band_counts = Counter(record.band for record in distances)
    core = _mass_core(hero_counts, 0.50)
    stretch = tuple(
        hero_id
        for hero_id, _count in sorted(hero_counts.items(), key=lambda item: (-item[1], item[0]))
        if hero_id not in set(core)
    )
    stable_core = tuple(
        sorted(
            set.intersection(
                *(set(_mass_core(counts, 0.60)) for counts in third_hero_counts if counts)
            )
        )
    ) if all(third_hero_counts) else ()
    effective_jobs = shannon_effective_count(job_mass)
    job_hero_sets: dict[str, set[int]] = defaultdict(set)
    for hero_id in hero_counts:
        for label in _labels(hero_id, taxonomy_by_hero):
            job_hero_sets[label].add(hero_id)
    sensitivity = (
        _taxonomy_sensitivity(matches, taxonomy_by_hero, effective_jobs)
        if include_taxonomy_sensitivity
        else {
            "version": "taxonomy-leave-one-label-1.0.0",
            "perturbations": 0,
            "effective_count_min": effective_jobs,
            "effective_count_max": effective_jobs,
            "maximum_deviation": 0.0,
            "stable": True,
            "bootstrap_omitted": True,
        }
    )
    sensitivity["stable"] = bool(sensitivity["stable"] and taxonomy_coverage >= 0.80)
    return {
        "version": "portfolio-shape-1.0.0",
        "match_count": len(matches),
        "shannon_effective_heroes": shannon_effective_count(hero_counts),
        "simpson_effective_heroes": _simpson_effective(hero_counts),
        "top_shares": {
            "top_1": _top_share(hero_counts, 1),
            "top_3": _top_share(hero_counts, 3),
            "top_5": _top_share(hero_counts, 5),
            "top_50_mass_hero_count": len(core),
        },
        "concentration_hhi": sum(
            (count / sum(hero_counts.values())) ** 2 for count in hero_counts.values()
        ) if hero_counts else 0.0,
        "stable_core_hero_ids": list(stable_core),
        "core_hero_ids": list(core),
        "reliable_stretch_hero_ids": list(stretch[: max(1, len(stretch) // 2)]),
        "experimental_tail_hero_ids": list(stretch[max(1, len(stretch) // 2) :]),
        "fractional_job_mass": job_mass,
        "shannon_effective_jobs": effective_jobs,
        "taxonomy_coverage": taxonomy_coverage,
        "taxonomy_version": "hero-taxonomy-v6-fixture-or-runtime-manifest",
        "taxonomy_sensitivity": sensitivity,
        "single_point_jobs": sorted(
            label for label, heroes in job_hero_sets.items() if len(heroes) == 1
        ),
        "job_redundancy": {
            label: len(heroes) for label, heroes in sorted(job_hero_sets.items())
        },
        "chronological_thirds": [
            {
                "index": index + 1,
                "match_count": len(part),
                "hero_effective_count": shannon_effective_count(third_hero_counts[index]),
                "job_effective_count": shannon_effective_count(third_job_mass[index]),
            }
            for index, part in enumerate(thirds)
        ],
        "hero_jsd_first_to_last": _jensen_shannon(third_hero_counts[0], third_hero_counts[2]),
        "job_jsd_first_to_last": _jensen_shannon(third_job_mass[0], third_job_mass[2]),
        "distance_band_counts": dict(sorted(band_counts.items())),
        "distance_cross_fitted": True,
    }


__all__ = [
    "DistanceRecord",
    "build_portfolio_shape",
    "chronological_thirds",
    "cross_fitted_distance_records",
]

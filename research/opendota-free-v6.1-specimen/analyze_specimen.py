#!/usr/bin/env python3
"""Reproducible, local-only forensic analysis of the one-call V6.1 specimen.

This script never performs network I/O. It reads ``raw-history.json`` and the
repository's checked-in hero taxonomy, then writes ``analysis-summary.json``.
It is research instrumentation, not production Free DNA implementation.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.heroes.taxonomy import load_default_taxonomy  # noqa: E402
from app.player_analysis_v6.hero_portfolio import load_v6_hero_taxonomy  # noqa: E402

RAW_PATH = HERE / "raw-history.json"
OUTPUT_PATH = HERE / "analysis-summary.json"
RETRIEVED_AT = datetime(2026, 8, 23, 12, 50, 18, tzinfo=UTC)
WINDOW_SECONDS = 365 * 24 * 60 * 60
SESSION_GAP_SECONDS = 90 * 60
ELIGIBLE_GAME_MODES = {1, 22}
ELIGIBLE_LOBBIES = {0, 7}
BOOTSTRAP_ITERATIONS = 2_000
RANDOMIZATION_ITERATIONS = 500

REQUESTED_FIELDS = (
    "match_id", "player_slot", "radiant_win", "hero_id", "hero_variant",
    "start_time", "duration", "game_mode", "lobby_type", "version",
    "cluster", "leagueid", "kills", "deaths", "assists", "level",
    "last_hits", "denies", "gold_per_min", "xp_per_min", "hero_damage",
    "tower_damage", "hero_healing", "leaver_status", "party_size", "lane",
    "lane_role", "is_roaming", "skill", "average_rank", "item_0", "item_1",
    "item_2", "item_3", "item_4", "item_5", "item_neutral",
)

V6_FIELD_USE = {
    "match_id": "identity/evidence and chronology tie-break",
    "player_slot": "side and player win derivation",
    "radiant_win": "player win derivation",
    "hero_id": "Breadth, Toolkit, pool, Transfer, sequences",
    "hero_variant": "retained but not analytically used",
    "start_time": "window, chronology, sessions, transitions, recent state",
    "duration": "eligibility and per-minute normalization",
    "game_mode": "eligibility/context",
    "lobby_type": "eligibility/context",
    "version": "context baseline source version when present",
    "cluster": "region derivation when static mapping is available",
    "leagueid": "pro/league exclusion when present",
    "kills": "Involvement and Finishing",
    "deaths": "Death Exposure",
    "assists": "Involvement and Finishing",
    "leaver_status": "eligibility",
    "party_size": "supporting context when present",
    "lane": "literal lane context when present",
    "lane_role": "literal lane context when present",
    "is_roaming": "literal roaming context when present",
    "skill": "stored as source context but prohibited from thresholds/copy",
    "average_rank": "prohibited from V6 baselines, thresholds, and copy",
}


def finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def mean(values: Iterable[float | int | None]) -> float | None:
    usable = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return sum(usable) / len(usable) if usable else None


def quantile(values: Iterable[float | int | None], q: float) -> float | None:
    usable = sorted(float(value) for value in values if value is not None and math.isfinite(float(value)))
    if not usable:
        return None
    position = max(0.0, min(1.0, q)) * (len(usable) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return usable[low]
    weight = position - low
    return usable[low] * (1 - weight) + usable[high] * weight


def rounded(value: Any, digits: int = 6) -> Any:
    if isinstance(value, float):
        return round(value, digits) if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): rounded(child, digits) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [rounded(child, digits) for child in value]
    return value


def rate(successes: int, total: int) -> dict[str, Any]:
    if total <= 0:
        return {"successes": successes, "n": total, "rate": None, "wilson_95": None}
    p = successes / total
    z = 1.959963984540054
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return {"successes": successes, "n": total, "rate": p, "wilson_95": [max(0.0, center - half), min(1.0, center + half)]}


def shannon_effective(weights: Mapping[Any, float | int]) -> float:
    total = sum(float(value) for value in weights.values() if float(value) > 0)
    if total <= 0:
        return 0.0
    entropy = -sum((float(value) / total) * math.log(float(value) / total) for value in weights.values() if float(value) > 0)
    return math.exp(entropy)


def simpson_effective(weights: Mapping[Any, float | int]) -> float:
    total = sum(float(value) for value in weights.values() if float(value) > 0)
    if total <= 0:
        return 0.0
    concentration = sum((float(value) / total) ** 2 for value in weights.values() if float(value) > 0)
    return 1 / concentration if concentration > 0 else 0.0


def gini(values: Iterable[int | float]) -> float:
    usable = sorted(float(value) for value in values if float(value) >= 0)
    if not usable or sum(usable) == 0:
        return 0.0
    n = len(usable)
    return (2 * sum((index + 1) * value for index, value in enumerate(usable)) / (n * sum(usable))) - (n + 1) / n


def js_divergence(left: Mapping[Any, float | int], right: Mapping[Any, float | int]) -> float:
    keys = set(left) | set(right)
    left_total = sum(float(left.get(key, 0)) for key in keys)
    right_total = sum(float(right.get(key, 0)) for key in keys)
    if left_total <= 0 or right_total <= 0:
        return 0.0
    result = 0.0
    for key in keys:
        p = float(left.get(key, 0)) / left_total
        q = float(right.get(key, 0)) / right_total
        midpoint = (p + q) / 2
        if p > 0:
            result += 0.5 * p * math.log2(p / midpoint)
        if q > 0:
            result += 0.5 * q * math.log2(q / midpoint)
    return result


def derive(row: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(row)
    player_slot = row.get("player_slot")
    radiant = isinstance(player_slot, int) and player_slot < 128
    radiant_win = row.get("radiant_win")
    result["won"] = bool(radiant_win) == radiant if isinstance(radiant_win, bool) and isinstance(player_slot, int) else None
    duration = finite(row.get("duration"))
    duration_minutes = duration / 60 if duration and duration > 0 else None
    kills = finite(row.get("kills"))
    deaths = finite(row.get("deaths"))
    assists = finite(row.get("assists"))
    result["duration_minutes"] = duration_minutes
    result["involvement_per_minute"] = (kills + assists) / duration_minutes if duration_minutes and kills is not None and assists is not None else None
    result["finishing_share"] = kills / (kills + assists) if kills is not None and assists is not None and kills + assists > 0 else None
    result["death_exposure_per_ten"] = deaths / duration_minutes * 10 if duration_minutes and deaths is not None else None
    for source, target in (
        ("hero_damage", "hero_damage_per_minute"),
        ("tower_damage", "tower_damage_per_minute"),
        ("hero_healing", "hero_healing_per_minute"),
        ("last_hits", "last_hits_per_minute"),
        ("denies", "denies_per_minute"),
    ):
        value = finite(row.get(source))
        result[target] = value / duration_minutes if duration_minutes and value is not None else None
    return result


def eligibility_reasons(row: Mapping[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    if not isinstance(row.get("match_id"), int) or row["match_id"] <= 0:
        reasons.append("invalid_match_id")
    if not isinstance(row.get("hero_id"), int) or row["hero_id"] <= 0:
        reasons.append("missing_hero")
    if row.get("game_mode") not in ELIGIBLE_GAME_MODES:
        reasons.append("unsupported_game_mode")
    if row.get("lobby_type") not in ELIGIBLE_LOBBIES:
        reasons.append("unsupported_lobby_type")
    duration = finite(row.get("duration"))
    if duration is None or duration < 300:
        reasons.append("invalid_duration")
    leaver = row.get("leaver_status")
    if isinstance(leaver, int) and leaver >= 2:
        reasons.append("abandoned")
    if row.get("won") is None:
        reasons.append("missing_outcome")
    if not isinstance(row.get("start_time"), int) or row["start_time"] <= 0:
        reasons.append("missing_start_time")
    return tuple(reasons)


def infer_sessions(rows: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: (row["start_time"], row["match_id"]))
    sessions: list[list[dict[str, Any]]] = []
    for row in ordered:
        if not sessions:
            sessions.append([row])
            continue
        previous = sessions[-1][-1]
        previous_end = previous["start_time"] + previous["duration"]
        if row["start_time"] - previous_end > SESSION_GAP_SECONDS:
            sessions.append([row])
        else:
            sessions[-1].append(row)
    session_records: list[dict[str, Any]] = []
    assigned: list[dict[str, Any]] = []
    for index, group in enumerate(sessions, start=1):
        session_id = f"session-{index}"
        for position, row in enumerate(group, start=1):
            value = dict(row)
            value["session_id"] = session_id
            value["session_index"] = position
            value["session_size"] = len(group)
            assigned.append(value)
        session_records.append({
            "session_id": session_id,
            "start_time": group[0]["start_time"],
            "end_time": group[-1]["start_time"] + group[-1]["duration"],
            "match_count": len(group),
            "left_censored": index == 1,
            "right_censored": index == len(sessions),
        })
    return assigned, session_records


def field_inventory(raw_rows: Sequence[Mapping[str, Any]], eligible_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    returned = sorted({key for row in raw_rows for key in row})
    result: list[dict[str, Any]] = []
    for key in returned:
        values = [row.get(key) for row in raw_rows]
        eligible_values = [row.get(key) for row in eligible_rows]
        nonnull = [value for value in values if value is not None]
        types = Counter(type(value).__name__ for value in nonnull)
        numeric = [float(value) for value in nonnull if isinstance(value, (int, float)) and not isinstance(value, bool)]
        try:
            unique_count = len({json.dumps(value, sort_keys=True) for value in nonnull})
        except TypeError:
            unique_count = None
        result.append({
            "field": key,
            "types": dict(sorted(types.items())),
            "nonnull": len(nonnull),
            "null": len(values) - len(nonnull),
            "coverage": len(nonnull) / len(values) if values else 0.0,
            "eligible_coverage": sum(value is not None for value in eligible_values) / len(eligible_values) if eligible_values else 0.0,
            "unique_count": unique_count,
            "min": min(numeric) if numeric else None,
            "max": max(numeric) if numeric else None,
            "current_v6_use": V6_FIELD_USE.get(key, "ignored by V6 stable identity path"),
        })
    return result


def portfolio_summary(rows: Sequence[Mapping[str, Any]], hero_names: Mapping[int, str], jobs_by_hero: Mapping[int, Mapping[str, Any]]) -> tuple[dict[str, Any], set[int], dict[int, int]]:
    counts = Counter(int(row["hero_id"]) for row in rows)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    total = len(rows)
    cumulative = 0
    core: set[int] = set()
    for hero_id, count in ordered:
        core.add(hero_id)
        cumulative += count
        if cumulative >= math.ceil(total * 0.60):
            break
    effective_jobs: defaultdict[str, float] = defaultdict(float)
    primary_jobs: Counter[str] = Counter()
    taxonomy_matches = 0
    for row in rows:
        taxonomy = jobs_by_hero.get(int(row["hero_id"]))
        labels = tuple(taxonomy.get("functional_jobs", ())) if taxonomy else ()
        if not labels:
            continue
        taxonomy_matches += 1
        for label in labels:
            effective_jobs[str(label)] += 1 / len(labels)
        primary_jobs[str(labels[0])] += 1
    def heroes_to_cover(target: float) -> int:
        running = 0
        for index, (_hero, count) in enumerate(ordered, start=1):
            running += count
            if running / total >= target:
                return index
        return len(ordered)
    top = [
        {
            "hero_id": hero_id,
            "hero_name": hero_names.get(hero_id, f"Hero {hero_id}"),
            "matches": count,
            "share": count / total,
            "core_60": hero_id in core,
            "functional_jobs": list(jobs_by_hero.get(hero_id, {}).get("functional_jobs", ())),
        }
        for hero_id, count in ordered
    ]
    established = sum(count >= 5 for count in counts.values())
    experimental = sum(count < 5 for count in counts.values())
    return ({
        "unique_heroes": len(counts),
        "shannon_effective_heroes": shannon_effective(counts),
        "simpson_effective_heroes": simpson_effective(counts),
        "hhi": sum((count / total) ** 2 for count in counts.values()),
        "gini_across_played_heroes": gini(counts.values()),
        "top_1_share": ordered[0][1] / total if ordered else 0.0,
        "top_3_share": sum(count for _hero, count in ordered[:3]) / total,
        "top_5_share": sum(count for _hero, count in ordered[:5]) / total,
        "heroes_for_50_percent": heroes_to_cover(0.50),
        "heroes_for_60_percent_core": len(core),
        "heroes_for_80_percent": heroes_to_cover(0.80),
        "heroes_for_90_percent": heroes_to_cover(0.90),
        "established_heroes_5_plus": established,
        "experimental_tail_under_5": experimental,
        "long_tail_matches": sum(count for count in counts.values() if count < 5),
        "taxonomy_coverage": taxonomy_matches / total if total else 0.0,
        "fractional_shannon_effective_jobs": shannon_effective(effective_jobs),
        "primary_job_effective_count": shannon_effective(primary_jobs),
        "fractional_job_distribution": dict(sorted(effective_jobs.items(), key=lambda item: (-item[1], item[0]))),
        "primary_job_distribution": dict(primary_jobs.most_common()),
        "heroes": top,
    }, core, dict(counts))


METRIC_KEYS = (
    "won", "involvement_per_minute", "finishing_share", "death_exposure_per_ten",
    "gold_per_min", "xp_per_min", "hero_damage_per_minute", "tower_damage_per_minute",
    "hero_healing_per_minute", "last_hits_per_minute", "denies_per_minute",
)


def metric_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        key: {
            "mean": mean(finite(row.get(key)) for row in rows),
            "median": quantile((finite(row.get(key)) for row in rows), 0.5),
            "q25": quantile((finite(row.get(key)) for row in rows), 0.25),
            "q75": quantile((finite(row.get(key)) for row in rows), 0.75),
            "coverage": sum(finite(row.get(key)) is not None for row in rows) / len(rows) if rows else 0.0,
        }
        for key in METRIC_KEYS
    }


def group_metric_summary(rows: Sequence[Mapping[str, Any]], key: str | Callable[[Mapping[str, Any]], str]) -> dict[str, Any]:
    groups: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        group = key(row) if callable(key) else row.get(key)
        groups[str(group)].append(row)
    return {
        group: {"n": len(values), "metrics": metric_summary(values)}
        for group, values in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
    }


def bootstrap_difference(
    rows: Sequence[Mapping[str, Any]],
    predicate_left: Callable[[Mapping[str, Any]], bool],
    predicate_right: Callable[[Mapping[str, Any]], bool],
    metric: str,
    *,
    seed: int,
) -> dict[str, Any]:
    grouped: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["session_id"])].append(row)
    session_ids = sorted(grouped)
    left = [finite(row.get(metric)) for row in rows if predicate_left(row)]
    right = [finite(row.get(metric)) for row in rows if predicate_right(row)]
    left_values = [value for value in left if value is not None]
    right_values = [value for value in right if value is not None]
    point = mean(left_values)
    right_mean = mean(right_values)
    point = point - right_mean if point is not None and right_mean is not None else None
    rng = random.Random(seed)
    replicates: list[float] = []
    if point is not None and session_ids:
        for _ in range(BOOTSTRAP_ITERATIONS):
            sample_rows = [row for _sid in (rng.choice(session_ids) for _ in session_ids) for row in grouped[_sid]]
            sample_left = [finite(row.get(metric)) for row in sample_rows if predicate_left(row)]
            sample_right = [finite(row.get(metric)) for row in sample_rows if predicate_right(row)]
            a = mean(value for value in sample_left if value is not None)
            b = mean(value for value in sample_right if value is not None)
            if a is not None and b is not None:
                replicates.append(a - b)
    return {
        "metric": metric,
        "definition": "left minus right",
        "n_left": len(left_values),
        "n_right": len(right_values),
        "point": point,
        "cluster_bootstrap_95": [quantile(replicates, 0.025), quantile(replicates, 0.975)] if replicates else None,
        "bootstrap_probability_positive": sum(value > 0 for value in replicates) / len(replicates) if replicates else None,
        "iterations": len(replicates),
    }


def session_analysis(rows: Sequence[Mapping[str, Any]], sessions: Sequence[Mapping[str, Any]], core: set[int]) -> dict[str, Any]:
    sizes = [int(session["match_count"]) for session in sessions]
    completed_ids = {str(session["session_id"]) for session in sessions if not session["left_censored"] and not session["right_censored"]}
    completed_rows = [row for row in rows if row["session_id"] in completed_ids]
    positions = group_metric_summary(
        completed_rows,
        lambda row: "5+" if int(row["session_index"]) >= 5 else str(row["session_index"]),
    )
    for position, value in positions.items():
        position_rows = [row for row in completed_rows if ("5+" if row["session_index"] >= 5 else str(row["session_index"])) == position]
        value["core_pick_rate"] = sum(int(row["hero_id"]) in core for row in position_rows) / len(position_rows)
        value["hero_repeat_from_previous_rate"] = (
            sum(bool(row.get("repeat_hero")) for row in position_rows if row["session_index"] > 1)
            / sum(row["session_index"] > 1 for row in position_rows)
            if any(row["session_index"] > 1 for row in position_rows)
            else None
        )
    stop_rows: list[dict[str, Any]] = []
    by_session: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in completed_rows:
        by_session[str(row["session_id"])].append(row)
    for group in by_session.values():
        ordered = sorted(group, key=lambda row: int(row["session_index"]))
        win_run = loss_run = 0
        for index, row in enumerate(ordered):
            if row["won"]:
                win_run += 1
                loss_run = 0
            else:
                loss_run += 1
                win_run = 0
            stop_rows.append({
                **row,
                "stopped": index == len(ordered) - 1,
                "result_run": win_run if row["won"] else loss_run,
            })
    def stop_rate(predicate: Callable[[Mapping[str, Any]], bool]) -> dict[str, Any]:
        values = [row for row in stop_rows if predicate(row)]
        return rate(sum(bool(row["stopped"]) for row in values), len(values))
    return {
        "session_count": len(sessions),
        "completed_uncensored_sessions": len(completed_ids),
        "match_count_mean": mean(sizes),
        "match_count_median": quantile(sizes, 0.5),
        "match_count_q90": quantile(sizes, 0.9),
        "sessions_4_plus": sum(size >= 4 for size in sizes),
        "sessions_5_plus": sum(size >= 5 for size in sizes),
        "position_profiles": positions,
        "stopping": {
            "after_win": stop_rate(lambda row: bool(row["won"])),
            "after_loss": stop_rate(lambda row: not bool(row["won"])),
            "after_one_loss": stop_rate(lambda row: not row["won"] and row["result_run"] == 1),
            "after_two_plus_losses": stop_rate(lambda row: not row["won"] and row["result_run"] >= 2),
            "after_one_win": stop_rate(lambda row: row["won"] and row["result_run"] == 1),
            "after_two_plus_wins": stop_rate(lambda row: row["won"] and row["result_run"] >= 2),
            "boundary_note": "First and last window sessions excluded; a 90-minute gap operationally defines stopping.",
        },
    }


def sequence_analysis(rows: Sequence[dict[str, Any]], core: set[int], jobs_by_hero: Mapping[int, Mapping[str, Any]], hero_counts: Mapping[int, int]) -> dict[str, Any]:
    by_session: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_session[str(row["session_id"])].append(row)
    transitions: list[dict[str, Any]] = []
    repeat_positions: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    motifs: Counter[tuple[str, ...]] = Counter()
    for group in by_session.values():
        ordered = sorted(group, key=lambda row: int(row["session_index"]))
        current_hero = None
        run_position = 0
        state_sequence: list[str] = []
        loss_run = win_run = 0
        for index, row in enumerate(ordered):
            hero = int(row["hero_id"])
            if hero == current_hero:
                run_position += 1
            else:
                current_hero = hero
                run_position = 1
            bucket = "C" if hero in core else "R" if hero_counts.get(hero, 0) >= 5 else "E"
            state_sequence.append(("W" if row["won"] else "L") + bucket)
            repeat_positions["4+" if run_position >= 4 else str(run_position)].append(row)
            if index == 0:
                loss_run = 0 if row["won"] else 1
                win_run = 1 if row["won"] else 0
                continue
            previous = ordered[index - 1]
            prior_loss_run = loss_run
            prior_win_run = win_run
            previous_jobs = set(jobs_by_hero.get(int(previous["hero_id"]), {}).get("functional_jobs", ()))
            current_jobs = set(jobs_by_hero.get(hero, {}).get("functional_jobs", ()))
            transitions.append({
                "previous_won": bool(previous["won"]),
                "prior_loss_run": prior_loss_run,
                "prior_win_run": prior_win_run,
                "same_hero": int(previous["hero_id"]) == hero,
                "same_primary_job": next(iter(previous_jobs), None) == next(iter(current_jobs), None),
                "job_overlap": bool(previous_jobs & current_jobs),
                "next_core": hero in core,
                "next_reliable_stretch": hero not in core and hero_counts.get(hero, 0) >= 5,
                "next_experimental": hero_counts.get(hero, 0) < 5,
                "next_won": bool(row["won"]),
                "next_involvement": row.get("involvement_per_minute"),
                "next_death_exposure": row.get("death_exposure_per_ten"),
                "next_finishing": row.get("finishing_share"),
            })
            if row["won"]:
                win_run = prior_win_run + 1 if previous["won"] else 1
                loss_run = 0
            else:
                loss_run = prior_loss_run + 1 if not previous["won"] else 1
                win_run = 0
        for length in (3, 4, 5):
            for start in range(0, len(state_sequence) - length + 1):
                motifs[tuple(state_sequence[start:start + length])] += 1
    def transition_profile(predicate: Callable[[Mapping[str, Any]], bool]) -> dict[str, Any]:
        values = [row for row in transitions if predicate(row)]
        return {
            "n": len(values),
            "same_hero": rate(sum(row["same_hero"] for row in values), len(values)),
            "same_primary_job": rate(sum(row["same_primary_job"] for row in values), len(values)),
            "any_job_overlap": rate(sum(row["job_overlap"] for row in values), len(values)),
            "next_core": rate(sum(row["next_core"] for row in values), len(values)),
            "next_experimental": rate(sum(row["next_experimental"] for row in values), len(values)),
            "next_win": rate(sum(row["next_won"] for row in values), len(values)),
            "next_involvement_mean": mean(row["next_involvement"] for row in values),
            "next_death_exposure_mean": mean(row["next_death_exposure"] for row in values),
        }
    return {
        "transition_count": len(transitions),
        "after_win": transition_profile(lambda row: row["previous_won"]),
        "after_loss": transition_profile(lambda row: not row["previous_won"]),
        "after_exactly_one_loss": transition_profile(lambda row: not row["previous_won"] and row["prior_loss_run"] == 1),
        "after_two_plus_losses": transition_profile(lambda row: not row["previous_won"] and row["prior_loss_run"] >= 2),
        "after_exactly_one_win": transition_profile(lambda row: row["previous_won"] and row["prior_win_run"] == 1),
        "after_two_plus_wins": transition_profile(lambda row: row["previous_won"] and row["prior_win_run"] >= 2),
        "same_hero_run_position": {
            position: {"n": len(values), "metrics": metric_summary(values)}
            for position, values in sorted(repeat_positions.items())
        },
        "top_state_motifs": [
            {"length": len(motif), "motif": list(motif), "count": count}
            for motif, count in sorted(motifs.items(), key=lambda item: (-item[1], len(item[0]), item[0]))[:30]
        ],
        "motif_legend": {"W": "win", "L": "loss", "C": "60% core", "R": "reliable stretch (5+ annual games)", "E": "experimental edge (<5 annual games)"},
    }


def lifecycle_analysis(rows: Sequence[Mapping[str, Any]], hero_names: Mapping[int, str]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: (int(row["start_time"]), int(row["match_id"])))
    first_time = int(ordered[0]["start_time"])
    burn_in_end = first_time + 60 * 24 * 60 * 60
    appearances: defaultdict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in ordered:
        appearances[int(row["hero_id"])].append(row)
    eligible_for_window_entry = [values for values in appearances.values() if int(values[0]["start_time"]) >= burn_in_end]
    def reaches(target: int) -> dict[str, Any]:
        return rate(sum(len(values) >= target for values in eligible_for_window_entry), len(eligible_for_window_entry))
    first_win = [values for values in eligible_for_window_entry if values[0]["won"]]
    first_loss = [values for values in eligible_for_window_entry if not values[0]["won"]]
    def returns_within(values: Sequence[Mapping[str, Any]], days: int) -> bool:
        return len(values) >= 2 and int(values[1]["start_time"]) - int(values[0]["start_time"]) <= days * 24 * 60 * 60
    rediscoveries: list[dict[str, Any]] = []
    for hero_id, values in appearances.items():
        for previous, current in zip(values, values[1:], strict=False):
            gap_days = (int(current["start_time"]) - int(previous["start_time"])) / 86400
            if gap_days >= 60:
                rediscoveries.append({
                    "hero_id": hero_id,
                    "hero_name": hero_names.get(hero_id, f"Hero {hero_id}"),
                    "gap_days": gap_days,
                    "return_won": bool(current["won"]),
                })
    adopted = [values for values in eligible_for_window_entry if len(values) >= 5]
    return {
        "bounded_window_warning": "These are first-observed-in-window entries, not true lifetime discoveries; the 365-day left boundary prevents stronger lifecycle labels.",
        "burn_in_days": 60,
        "first_observed_after_burn_in": len(eligible_for_window_entry),
        "second_game_ever_in_remaining_window": reaches(2),
        "reaches_3_games": reaches(3),
        "reaches_5_games": reaches(5),
        "reaches_10_games": reaches(10),
        "second_game_within_30d_after_first_win": rate(sum(returns_within(values, 30) for values in first_win), len(first_win)),
        "second_game_within_30d_after_first_loss": rate(sum(returns_within(values, 30) for values in first_loss), len(first_loss)),
        "median_days_first_to_fifth_for_adopted": quantile(((int(values[4]["start_time"]) - int(values[0]["start_time"])) / 86400 for values in adopted), 0.5),
        "rediscovery_after_60d_count": len(rediscoveries),
        "rediscoveries": sorted(rediscoveries, key=lambda row: -row["gap_days"])[:30],
    }


def distribution_for_rows(rows: Sequence[Mapping[str, Any]], key: Callable[[Mapping[str, Any]], Iterable[str | int]]) -> Counter[Any]:
    result: Counter[Any] = Counter()
    for row in rows:
        values = list(key(row))
        if not values:
            continue
        for value in values:
            result[value] += 1 / len(values)
    return result


def best_session_change(
    session_blocks: Sequence[Sequence[Mapping[str, Any]]],
    key: Callable[[Mapping[str, Any]], Iterable[str | int]],
    *,
    seed: int,
) -> dict[str, Any]:
    def best(blocks: Sequence[Sequence[Mapping[str, Any]]]) -> tuple[float, int, int, Counter[Any], Counter[Any]]:
        total_matches = sum(len(block) for block in blocks)
        best_value = -1.0
        best_index = 0
        best_left: Counter[Any] = Counter()
        best_right: Counter[Any] = Counter()
        for index in range(1, len(blocks)):
            left_rows = [row for block in blocks[:index] for row in block]
            right_rows = [row for block in blocks[index:] for row in block]
            if len(left_rows) < 120 or len(right_rows) < 120:
                continue
            left = distribution_for_rows(left_rows, key)
            right = distribution_for_rows(right_rows, key)
            balance = 4 * len(left_rows) * len(right_rows) / (total_matches * total_matches)
            score = js_divergence(left, right) * balance
            if score > best_value:
                best_value, best_index, best_left, best_right = score, index, left, right
        return best_value, best_index, sum(len(block) for block in blocks[:best_index]), best_left, best_right
    point, split_session, split_match, left, right = best(session_blocks)
    rng = random.Random(seed)
    null_values: list[float] = []
    for _ in range(RANDOMIZATION_ITERATIONS):
        shuffled = list(session_blocks)
        rng.shuffle(shuffled)
        null_values.append(best(shuffled)[0])
    split_time = None
    if 0 < split_session < len(session_blocks):
        split_time = int(session_blocks[split_session][0]["start_time"])
    return {
        "weighted_js_score": point,
        "raw_js_divergence": js_divergence(left, right),
        "split_session_index": split_session,
        "split_match_index": split_match,
        "split_time": split_time,
        "split_date_utc": datetime.fromtimestamp(split_time, UTC).date().isoformat() if split_time else None,
        "cluster_permutation_p": (1 + sum(value >= point for value in null_values)) / (1 + len(null_values)) if point >= 0 else None,
        "randomization_iterations": len(null_values),
        "left_top": left.most_common(12),
        "right_top": right.most_common(12),
        "minimum_segment_matches": 120,
    }


def evolution_analysis(rows: Sequence[Mapping[str, Any]], jobs_by_hero: Mapping[int, Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: (int(row["start_time"]), int(row["match_id"])))
    by_session: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in ordered:
        by_session[str(row["session_id"])].append(row)
    session_blocks = [by_session[key] for key in sorted(by_session, key=lambda value: int(value.split("-")[-1]))]
    def hero_key(row: Mapping[str, Any]) -> tuple[int]:
        return (int(row["hero_id"]),)

    def job_key(row: Mapping[str, Any]) -> tuple[str, ...]:
        return tuple(jobs_by_hero.get(int(row["hero_id"]), {}).get("functional_jobs", ()))
    thirds = [ordered[index * len(ordered) // 3:(index + 1) * len(ordered) // 3] for index in range(3)]
    third_summaries = []
    for index, chunk in enumerate(thirds, start=1):
        hero_dist = distribution_for_rows(chunk, hero_key)
        job_dist = distribution_for_rows(chunk, job_key)
        third_summaries.append({
            "third": index,
            "start_date_utc": datetime.fromtimestamp(int(chunk[0]["start_time"]), UTC).date().isoformat(),
            "end_date_utc": datetime.fromtimestamp(int(chunk[-1]["start_time"]), UTC).date().isoformat(),
            "matches": len(chunk),
            "effective_heroes": shannon_effective(hero_dist),
            "effective_jobs": shannon_effective(job_dist),
            "top_heroes": hero_dist.most_common(8),
            "top_jobs": job_dist.most_common(8),
            "win_rate": mean(1.0 if row["won"] else 0.0 for row in chunk),
        })
    adjacent = []
    for index in range(2):
        left_hero = distribution_for_rows(thirds[index], hero_key)
        right_hero = distribution_for_rows(thirds[index + 1], hero_key)
        left_jobs = distribution_for_rows(thirds[index], job_key)
        right_jobs = distribution_for_rows(thirds[index + 1], job_key)
        adjacent.append({
            "from_third": index + 1,
            "to_third": index + 2,
            "hero_js": js_divergence(left_hero, right_hero),
            "job_js": js_divergence(left_jobs, right_jobs),
            "name_change_minus_job_change": js_divergence(left_hero, right_hero) - js_divergence(left_jobs, right_jobs),
        })
    return {
        "thirds": third_summaries,
        "adjacent_third_divergence": adjacent,
        "hero_change_point": best_session_change(session_blocks, hero_key, seed=417),
        "job_change_point": best_session_change(session_blocks, job_key, seed=418),
        "change_point_note": "Exploratory maximum split over session boundaries; session-block randomization controls repeated-match clustering. Production should use held-out thresholds and PELT/segment-neighborhood validation.",
    }


def main() -> None:
    raw_bytes = RAW_PATH.read_bytes()
    raw = json.loads(raw_bytes)
    if not isinstance(raw, list) or not all(isinstance(row, dict) for row in raw):
        raise ValueError("raw-history.json must contain a JSON array of objects")
    derived = [derive(row) for row in raw]
    exclusion_counts: Counter[str] = Counter()
    eligible: list[dict[str, Any]] = []
    for row in derived:
        reasons = eligibility_reasons(row)
        if reasons:
            exclusion_counts.update(reasons)
        else:
            eligible.append(row)
    eligible, sessions = infer_sessions(eligible)
    taxonomy = load_default_taxonomy()
    hero_names = {hero_id: entry.name for hero_id, entry in taxonomy.heroes.items()}
    jobs_by_hero = load_v6_hero_taxonomy()
    portfolio, core, hero_counts = portfolio_summary(eligible, hero_names, jobs_by_hero)
    previous_by_session: dict[str, Mapping[str, Any]] = {}
    for row in eligible:
        previous = previous_by_session.get(str(row["session_id"]))
        row["repeat_hero"] = previous is not None and previous["hero_id"] == row["hero_id"]
        previous_by_session[str(row["session_id"])] = row
        count = hero_counts[int(row["hero_id"])]
        row["portfolio_tier"] = "core" if int(row["hero_id"]) in core else "reliable_stretch" if count >= 5 else "experimental_edge"
        row["primary_job"] = jobs_by_hero.get(int(row["hero_id"]), {}).get("hero_function")
    field_rows = field_inventory(raw, eligible)
    returned_fields = {item["field"] for item in field_rows}
    start_time = min(int(row["start_time"]) for row in raw)
    end_time = max(int(row["start_time"]) for row in raw)
    transfer_metrics = [
        bootstrap_difference(eligible, lambda row: row["portfolio_tier"] == "core", lambda row: row["portfolio_tier"] != "core", metric, seed=500 + index)
        for index, metric in enumerate(("won", "involvement_per_minute", "death_exposure_per_ten", "finishing_share", "gold_per_min", "xp_per_min", "hero_damage_per_minute", "tower_damage_per_minute"))
    ]
    output = {
        "artifact": {
            "schema_version": "free-v6.1-specimen-analysis-1.0.0",
            "source": "local-only analysis of raw-history.json",
            "retrieved_at": RETRIEVED_AT.isoformat().replace("+00:00", "Z"),
            "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "request_contract": {
                "endpoint": "/players/{account_id}/matches",
                "date_days": 365,
                "significant": 1,
                "limit": None,
                "offset": None,
                "physical_http_requests": 1,
                "requested_fields": list(REQUESTED_FIELDS),
                "returned_fields": sorted(returned_fields),
                "requested_but_absent": sorted(set(REQUESTED_FIELDS) - returned_fields),
            },
        },
        "population": {
            "raw_rows": len(raw),
            "eligible_rows": len(eligible),
            "eligibility_rate": len(eligible) / len(raw),
            "exclusion_reasons_nonexclusive": dict(exclusion_counts.most_common()),
            "first_match_time": start_time,
            "first_match_date_utc": datetime.fromtimestamp(start_time, UTC).date().isoformat(),
            "last_match_time": end_time,
            "last_match_date_utc": datetime.fromtimestamp(end_time, UTC).date().isoformat(),
            "observed_span_days": (end_time - start_time) / 86400,
            "matches_per_observed_week": len(eligible) / max(1, (end_time - start_time) / (7 * 86400)),
        },
        "field_inventory": field_rows,
        "public_element_descriptives": {
            "breadth": portfolio["shannon_effective_heroes"],
            "toolkit": portfolio["fractional_shannon_effective_jobs"],
            "involvement_raw_per_minute": mean(row["involvement_per_minute"] for row in eligible),
            "finishing_raw_share": mean(row["finishing_share"] for row in eligible),
            "death_exposure_raw_per_ten": mean(row["death_exposure_per_ten"] for row in eligible),
            "transfer_note": "See core_minus_noncore_cluster_bootstrap; no external context baseline is applied in this specimen audit.",
            "consistency_note": "See global and conditional metric dispersions; production zones require calibrated thresholds.",
        },
        "portfolio": portfolio,
        "global_metrics": metric_summary(eligible),
        "contexts": {
            "portfolio_tiers": group_metric_summary(eligible, "portfolio_tier"),
            "primary_jobs": group_metric_summary(eligible, "primary_job"),
            "game_modes": group_metric_summary(eligible, "game_mode"),
            "lobby_types": group_metric_summary(eligible, "lobby_type"),
            "clusters": group_metric_summary(eligible, "cluster"),
            "duration_bands": group_metric_summary(eligible, lambda row: "<30" if row["duration_minutes"] < 30 else "30-40" if row["duration_minutes"] < 40 else "40-50" if row["duration_minutes"] < 50 else "50+"),
        },
        "core_minus_noncore_cluster_bootstrap": transfer_metrics,
        "sessions": session_analysis(eligible, sessions, core),
        "sequences": sequence_analysis(eligible, core, jobs_by_hero, hero_counts),
        "lifecycle": lifecycle_analysis(eligible, hero_names),
        "evolution": evolution_analysis(eligible, jobs_by_hero),
        "boundary_findings": {
            "lane_context_coverage": mean(1.0 if row.get("lane") is not None or row.get("lane_role") is not None or row.get("is_roaming") is not None else 0.0 for row in eligible),
            "party_size_coverage": mean(1.0 if row.get("party_size") is not None else 0.0 for row in eligible),
            "source_version_coverage": mean(1.0 if row.get("version") is not None else 0.0 for row in eligible),
            "scoreboard_extra_coverage": {
                key: sum(row.get(key) is not None for row in eligible) / len(eligible)
                for key in ("level", "last_hits", "denies", "gold_per_min", "xp_per_min", "hero_damage", "tower_damage", "hero_healing")
            },
            "rank_metadata_excluded_from_identity": {
                "average_rank_coverage": sum(row.get("average_rank") is not None for row in eligible) / len(eligible),
                "skill_coverage": sum(row.get("skill") is not None for row in eligible) / len(eligible),
            },
            "local_time_unavailable": "start_time is UTC and cluster is not a reliable player-time-zone identifier",
            "true_hero_discovery_unavailable": "the left-bounded window cannot establish lifetime novelty",
            "team_kill_context_unavailable": "one player's K+A cannot reconstruct team kills or fight participation",
        },
    }
    OUTPUT_PATH.write_text(json.dumps(rounded(output), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT_PATH),
        "raw_rows": len(raw),
        "eligible_rows": len(eligible),
        "sessions": len(sessions),
        "unique_heroes": portfolio["unique_heroes"],
        "effective_heroes": round(portfolio["shannon_effective_heroes"], 3),
        "effective_jobs": round(portfolio["fractional_shannon_effective_jobs"], 3),
    }, indent=2))


if __name__ == "__main__":
    main()

"""Protected offline/shadow evaluation for lifecycle, eras, and motifs.

This module measures candidates but deliberately stops before public copy
entitlement. Promotion requires separately supplied calibration evidence.
"""

from __future__ import annotations

import hashlib
import math
import random
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

EXPERIMENTAL_VERSION = "experimental-evolution-loops-1.1.0"


def _get(value: Any, key: str, default: Any = None) -> Any:
    return value.get(key, default) if isinstance(value, Mapping) else getattr(value, key, default)


def _ordered_sessions(matches: Sequence[Any]) -> list[list[Any]]:
    ordered = sorted(
        matches,
        key=lambda item: (
            _get(item, "started_at", _get(item, "start_time")) or 0,
            _get(item, "match_id") or 0,
        ),
    )
    grouped: dict[str, list[Any]] = defaultdict(list)
    for index, match in enumerate(ordered):
        grouped[str(_get(match, "session_id", f"match:{index}"))].append(match)
    return sorted(
        grouped.values(),
        key=lambda session: (
            _get(session[0], "started_at", _get(session[0], "start_time")) or 0,
            _get(session[0], "match_id") or 0,
        ),
    )


def _days_between(first: Any, last: Any) -> float:
    start = _get(first, "started_at", _get(first, "start_time")) or 0
    end = _get(last, "started_at", _get(last, "start_time")) or start
    return max(0.0, (float(end) - float(start)) / 86_400.0)


def _lifecycle(sessions: Sequence[Sequence[Any]]) -> dict[str, Any]:
    ordered = [match for session in sessions for match in session]
    span_days = _days_between(ordered[0], ordered[-1]) if ordered else 0.0
    first_time = int(_get(ordered[0], "start_time") or 0) if ordered else 0
    last_time = int(_get(ordered[-1], "start_time") or 0) if ordered else 0
    by_hero: dict[Any, list[tuple[int, str]]] = defaultdict(list)
    for session_index, session in enumerate(sessions):
        for match in session:
            hero = _get(match, "hero_id")
            timestamp = int(_get(match, "started_at", _get(match, "start_time")) or 0)
            if hero is not None:
                by_hero[hero].append((timestamp, str(session_index)))
    retained = dormant = returned = safe_candidates = 0
    for observations in by_hero.values():
        observations.sort()
        first = observations[0][0]
        left_safe = bool(first_time and first - first_time >= 30 * 86_400)
        right_safe = bool(last_time and last_time - first >= 30 * 86_400)
        safe_candidates += int(left_safe and right_safe)
        later_sessions = {
            session for timestamp, session in observations if timestamp - first >= 14 * 86_400
        }
        retained += int(right_safe and len(later_sessions) >= 2)
        gaps = [
            right[0] - left[0]
            for left, right in zip(observations, observations[1:], strict=False)
        ]
        has_dormancy = any(gap >= 30 * 86_400 for gap in gaps)
        dormant += int(has_dormancy)
        returned += int(has_dormancy and observations[-1][0] < last_time - 7 * 86_400)
    gates = {
        "matches_at_least_120": len(ordered) >= 120,
        "sessions_at_least_45": len(sessions) >= 45,
        "observed_days_at_least_90": span_days >= 90,
        "left_boundary_safe_candidates_at_least_5": safe_candidates >= 5,
        "retained_events_at_least_5": retained >= 5,
    }
    return {
        "first_observed_only": True,
        "left_truncated": True,
        "right_censored": True,
        "candidate_heroes": len(by_hero),
        "left_boundary_safe_candidates": safe_candidates,
        "retained_events": retained,
        "dormant_events": dormant,
        "returned_events": returned,
        "observed_days": round(span_days, 3),
        "gates": gates,
        "research_gate_passed": all(gates.values()),
    }


def _distribution(session_block: Sequence[Sequence[Any]]) -> dict[Any, float]:
    counts = Counter(_get(match, "hero_id") for session in session_block for match in session)
    counts.pop(None, None)
    total = sum(counts.values()) or 1
    return {key: value / total for key, value in counts.items()}


def _jsd(left: Mapping[Any, float], right: Mapping[Any, float]) -> float:
    keys = set(left) | set(right)
    midpoint = {key: (left.get(key, 0.0) + right.get(key, 0.0)) / 2 for key in keys}

    def divergence(source: Mapping[Any, float]) -> float:
        return sum(
            value * math.log2(value / midpoint[key])
            for key, value in source.items()
            if value > 0 and midpoint[key] > 0
        )

    return (divergence(left) + divergence(right)) / 2


def _era_candidate(sessions: Sequence[Sequence[Any]]) -> dict[str, Any]:
    if len(sessions) < 90:
        return {"candidate_boundary": None, "score": 0.0, "eligible_boundaries": 0}
    best: tuple[float, int] | None = None
    eligible = 0
    total_matches = sum(len(session) for session in sessions)
    for boundary in range(45, len(sessions) - 44):
        left, right = sessions[:boundary], sessions[boundary:]
        left_matches, right_matches = sum(map(len, left)), sum(map(len, right))
        if min(left_matches, right_matches) < 120:
            continue
        if min(
            _days_between(left[0][0], left[-1][-1]),
            _days_between(right[0][0], right[-1][-1]),
        ) < 45:
            continue
        if min(left_matches, right_matches) / total_matches < 0.10:
            continue
        eligible += 1
        score = _jsd(_distribution(left), _distribution(right))
        if best is None or score > best[0]:
            best = (score, boundary)
    return {
        "candidate_boundary": best[1] if best else None,
        "score": round(best[0], 6) if best else 0.0,
        "eligible_boundaries": eligible,
    }


def _state_alphabet(sessions: Sequence[Sequence[Any]]) -> list[list[tuple[str, Any]]]:
    heroes = Counter(_get(match, "hero_id") for session in sessions for match in session)
    total = sum(heroes.values()) or 1
    core = {hero for hero, count in heroes.items() if hero is not None and count / total >= 0.05}
    encoded: list[list[tuple[str, Any]]] = []
    for session in sessions:
        previous_hero: Any = None
        states: list[tuple[str, Any]] = []
        for position, match in enumerate(session, start=1):
            hero = _get(match, "hero_id")
            result = "W" if bool(_get(match, "won")) else "L"
            distance = "C" if hero in core else "E"
            switch = "R" if previous_hero == hero else "S"
            position_band = "O" if position == 1 else "L"
            states.append((f"{result}:{distance}:{switch}:{position_band}", hero))
            previous_hero = hero
        encoded.append(states)
    return encoded


def _motif_occurrences(
    encoded: Sequence[Sequence[tuple[str, Any]]], motif: tuple[str, ...]
) -> list[tuple[int, tuple[Any, ...]]]:
    found: list[tuple[int, tuple[Any, ...]]] = []
    width = len(motif)
    for session_index, session in enumerate(encoded):
        index = 0
        while index <= len(session) - width:
            states = tuple(item[0] for item in session[index : index + width])
            if states == motif:
                found.append((session_index, tuple(item[1] for item in session[index : index + width])))
                index += width
            else:
                index += 1
    return found


def _motifs(sessions: Sequence[Sequence[Any]]) -> dict[str, Any]:
    encoded = _state_alphabet(sessions)
    discovery = [session for index, session in enumerate(encoded) if index % 2 == 0]
    verification = [session for index, session in enumerate(encoded) if index % 2 == 1]
    candidates: Counter[tuple[str, ...]] = Counter()
    for session in discovery:
        states = [item[0] for item in session]
        for width in range(2, 6):
            candidates.update(
                tuple(states[index : index + width])
                for index in range(len(states) - width + 1)
            )
    frozen = [motif for motif, count in candidates.items() if count >= 15]
    verified: list[dict[str, Any]] = []
    for motif in frozen:
        occurrences = _motif_occurrences(verification, motif)
        session_count = len({item[0] for item in occurrences})
        hero_counts = Counter(hero for _, heroes in occurrences for hero in heroes if hero is not None)
        hero_concentration = max(hero_counts.values(), default=0) / max(1, sum(hero_counts.values()))
        transitions = list(zip(motif, motif[1:], strict=False))
        all_transitions = Counter(
            pair
            for session in verification
            for pair in zip(
                [item[0] for item in session],
                [item[0] for item in session][1:],
                strict=False,
            )
        )
        transition_total = sum(all_transitions.values()) or 1
        expected = max(
            1.0,
            len(verification)
            * min((all_transitions[pair] / transition_total for pair in transitions), default=0.0),
        )
        lift = len(occurrences) / expected
        lower = max(0.0, lift - 1.96 * math.sqrt(max(lift, 1e-9) / expected))
        midpoint = len(verification) // 2
        first_half = _motif_occurrences(verification[:midpoint], motif)
        second_half = _motif_occurrences(verification[midpoint:], motif)
        shorter_explains = any(
            len(shorter) < len(motif)
            and tuple(motif[: len(shorter)]) == shorter
            and candidates[shorter] >= candidates[motif]
            for shorter in frozen
        )
        gates = {
            "occurrences_at_least_30": len(occurrences) >= 30,
            "sessions_at_least_20": session_count >= 20,
            "lower_lift_above_1_25": lower > 1.25,
            "hero_concentration_at_most_40_percent": hero_concentration <= 0.40,
            "directional_in_both_halves": bool(first_half and second_half),
            "no_shorter_explanation": not shorter_explains,
        }
        if all(gates.values()):
            verified.append(
                {
                    "motif_digest": hashlib.sha256("|".join(motif).encode()).hexdigest()[:16],
                    "length": len(motif),
                    "occurrences": len(occurrences),
                    "sessions": session_count,
                    "lift_lower_95": round(lower, 4),
                    "gates": gates,
                }
            )
    return {
        "candidate_count": len(candidates),
        "frozen_discovery_count": len(frozen),
        "verified_candidates": verified,
        "discovery_verification_complete": True,
        "session_boundary_sensitive": True,
    }


def evaluate_experimental_candidates(
    matches: Sequence[Any],
    *,
    evolution_enabled: bool,
    loops_enabled: bool,
    calibration_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    sessions = _ordered_sessions(matches)
    ordered = [match for session in sessions for match in session]
    lifecycle = _lifecycle(sessions)
    era = _era_candidate(sessions)
    motifs = _motifs(sessions)
    calibration = dict(calibration_evidence or {})
    era_verified = (
        era["candidate_boundary"] is not None
        and calibration.get("heldout_boundary_verified") is True
        and float(calibration.get("stationary_false_era_rate", 1.0)) <= 0.05
        and calibration.get("boundary_bootstrap_within_14_days") is True
        and calibration.get("session_gap_sensitivity_passed") is True
        and calibration.get("leave_one_hero_out_passed") is True
        and calibration.get("taxonomy_perturbation_passed") is True
    )
    loops_verified = (
        bool(motifs["verified_candidates"])
        and float(calibration.get("stationary_false_loop_rate", 1.0)) <= 0.05
        and calibration.get("session_boundary_sensitivity_passed") is True
    )
    lifecycle_status = (
        "experimental"
        if evolution_enabled and len(ordered) >= 120 and len(sessions) >= 45
        else "unavailable"
    )
    era_status = (
        "experimental"
        if evolution_enabled and len(ordered) >= 240 and len(sessions) >= 90
        else "unavailable"
    )
    loop_status = "experimental" if loops_enabled and len(sessions) >= 20 else "unavailable"
    return {
        "version": EXPERIMENTAL_VERSION,
        "public_serialization_allowed": False,
        "hero_lifecycle": {"status": lifecycle_status, **lifecycle},
        "identity_eras": {
            "status": era_status,
            "maximum_eras": 3,
            "method": "session-block-segment-neighborhood",
            "result_is_primary_objective": False,
            "selection_corrected": era_verified,
            "candidate": era,
            "reason": (
                None
                if era_verified
                else "offline candidate only; held-out/sensitivity gates incomplete"
            ),
        },
        "behavioral_loops": {
            "status": loop_status,
            **motifs,
            "qualifying_support_count": len(motifs["verified_candidates"]),
            "calibration_verified": loops_verified,
        },
        "promotion_requires_separate_decision": True,
    }


def run_stationary_experimental_simulations(
    *, seed: int = 6105, replicates: int = 200
) -> dict[str, Any]:
    rng = random.Random(seed)
    false_eras = false_loops = 0
    for replicate in range(replicates):
        rows = [
            {
                "match_id": replicate * 10_000 + index,
                "start_time": 1_700_000_000 + index * 43_200,
                "hero_id": 1 + rng.randrange(12),
                "won": rng.random() < 0.5,
                "session_id": f"{replicate}:{index // 2}",
            }
            for index in range(240)
        ]
        sessions = _ordered_sessions(rows)
        false_eras += _era_candidate(sessions)["score"] >= 0.20
        false_loops += bool(_motifs(sessions)["verified_candidates"])
    return {
        "version": "experimental-stationary-simulation-1.0.0",
        "seed": seed,
        "replicates": replicates,
        "false_era_rate": false_eras / replicates,
        "false_loop_rate": false_loops / replicates,
    }


__all__ = [
    "EXPERIMENTAL_VERSION",
    "evaluate_experimental_candidates",
    "run_stationary_experimental_simulations",
]

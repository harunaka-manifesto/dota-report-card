"""Defensible, sample-aware derivations from empirical observations."""

from __future__ import annotations

from typing import Any

from .. import BEHAVIOR_RULE_VERSION


def _source_ref(empirical: dict[str, Any], field: str) -> str:
    provenance = empirical.get("provenance", {})
    source = provenance.get("source") if isinstance(provenance, dict) else None
    return f"{source or 'public_empirical'}:{field}"


def _duration_band(weighted_seconds: float) -> str:
    if weighted_seconds < 1500:
        return "earlier-biased"
    if weighted_seconds > 2700:
        return "later-biased"
    return "balanced"


def derive_behavior(empirical: dict[str, Any], *, minimum_matches: int = 20) -> dict[str, Any]:
    role_flexibility = {
        "band": "unknown",
        "reason": "source_does_not_expose_lane_or_role_distribution",
        "derived_from": [_source_ref(empirical, "bracket_performance")],
        "rule_version": BEHAVIOR_RULE_VERSION,
    }

    item_profiles = [item for item in empirical.get("item_profile", []) if isinstance(item, dict)]
    item_dependency: dict[str, Any]
    item_matches = sum(
        int(item["count"]) for item in item_profiles if isinstance(item.get("count"), int)
    )
    if item_matches >= minimum_matches and item_profiles:
        top = max(item_profiles, key=lambda item: int(item.get("count") or 0))
        top_share = int(top.get("count") or 0) / item_matches
        item_dependency = {
            "band": "high" if top_share >= 0.5 else "medium" if top_share >= 0.3 else "low",
            "top_item_id": top.get("item_id"),
            "top_phase": top.get("phase"),
            "top_item_share": round(top_share, 6),
            "observed_item_count": item_matches,
            "interpretation": "build concentration; not causal item strength",
            "derived_from": [_source_ref(empirical, "item_profile")],
            "rule_version": BEHAVIOR_RULE_VERSION,
        }
    else:
        item_dependency = {
            "band": "unknown",
            "reason": "insufficient_sample",
            "observed_item_count": item_matches,
            "minimum_sample_size": minimum_matches,
            "derived_from": [_source_ref(empirical, "item_profile")],
            "rule_version": BEHAVIOR_RULE_VERSION,
        }

    duration_rows = [item for item in empirical.get("duration_profile", []) if isinstance(item, dict)]
    duration_games = sum(
        int(item["games"]) for item in duration_rows if isinstance(item.get("games"), int)
    )
    weighted_duration = (
        sum(
            int(item.get("duration_bin_seconds", 0)) * int(item.get("games", 0))
            for item in duration_rows
        )
        / duration_games
        if duration_games
        else None
    )
    duration_profile: dict[str, Any]
    if weighted_duration is not None and duration_games >= minimum_matches:
        duration_profile = {
            "band": _duration_band(weighted_duration),
            "weighted_average_seconds": round(weighted_duration, 3),
            "sample_size": duration_games,
            "minimum_sample_size": minimum_matches,
            "derived_from": [_source_ref(empirical, "duration_profile")],
            "rule_version": BEHAVIOR_RULE_VERSION,
        }
    else:
        duration_profile = {
            "band": "unknown",
            "reason": "insufficient_sample",
            "sample_size": duration_games,
            "minimum_sample_size": minimum_matches,
            "derived_from": [_source_ref(empirical, "duration_profile")],
            "rule_version": BEHAVIOR_RULE_VERSION,
        }

    bracket_rows = [
        item
        for item in empirical.get("bracket_performance", [])
        if isinstance(item, dict) and item.get("population") == "public_aggregate"
    ]
    public_matches = sum(
        int(item["picks"]) for item in bracket_rows if isinstance(item.get("picks"), int)
    )
    meta_status = "observed" if public_matches >= minimum_matches else "unknown"
    meta_band = (
        "high"
        if public_matches >= 1000
        else "medium"
        if public_matches >= 100
        else "low"
        if public_matches >= minimum_matches
        else "unknown"
    )
    matchup_rows = [item for item in empirical.get("matchup_profile", []) if isinstance(item, dict)]
    return {
        "role_flexibility": role_flexibility,
        "item_dependency": item_dependency,
        "duration_profile": duration_profile,
        "meta_confidence": {
            "band": meta_band,
            "status": meta_status,
            "sample_size": public_matches,
            "minimum_sample_size": minimum_matches,
            "derived_from": [_source_ref(empirical, "bracket_performance")],
            "rule_version": BEHAVIOR_RULE_VERSION,
        },
        "matchup_context": {
            "band": "observed" if matchup_rows else "unknown",
            "sample_size": sum(
                int(item.get("games", 0))
                for item in matchup_rows
                if isinstance(item.get("games"), int)
            ),
            "evidence_population": "opendota_aggregate" if matchup_rows else None,
            "interpretation": "observed association; not causal evidence",
            "derived_from": [_source_ref(empirical, "matchup_profile")],
            "rule_version": BEHAVIOR_RULE_VERSION,
        },
        "provenance": {
            "rule_version": BEHAVIOR_RULE_VERSION,
            "minimum_matches": minimum_matches,
            "correlation_boundary": "Observed build, duration, and matchup data is not causal evidence.",
        },
    }

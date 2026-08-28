#!/usr/bin/env python3
"""Build the offline Death Context feasibility record from existing local evidence."""

from __future__ import annotations

import csv
import gzip
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

LOCAL_ROOT = Path("/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local")
CORPUS = LOCAL_ROOT / "corpora/opendota/v61-session-drift-expansion"
SOURCE_DIAGNOSTICS = LOCAL_ROOT / "diagnostics/free-dna-opendota-parsed-feasibility"
REQUEST_LEDGER = LOCAL_ROOT / "diagnostics/v61-session-drift-data-expansion/request_ledger.jsonl"
OUTPUT = LOCAL_ROOT / "diagnostics/free-dna-death-context-feasibility"
SCHEMA = "free-dna-death-context-feasibility-1.0.0"
NS = (10, 15, 20, 25, 30, 40, 50)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(name: str, value: Any) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / name).write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def profiles() -> list[dict[str, Any]]:
    rows = []
    for path in sorted((CORPUS / "normalized/tuning").glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            profile = json.load(handle)["profile"]
        if profile["status"] == "eligible":
            rows.append(profile)
    return rows


def parsed_details() -> list[tuple[Path, dict[str, Any]]]:
    rows = []
    for path in sorted((CORPUS / "raw/responses").glob("*.body")):
        try:
            value = load_json(path)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if (
            isinstance(value, dict)
            and value.get("version") == 22
            and (value.get("od_data") or {}).get("has_parsed") is True
        ):
            rows.append((path, value))
    return rows


def candidate_subquestions() -> dict[str, Any]:
    common = {
        "unit_of_analysis": "player-match, aggregated to the player with whole matches kept together",
        "repeated_observations": "matches; no death is treated as an independent player-level replicate",
        "controls": ["hero", "lane_role", "win/loss", "player-team ahead-state exposure", "patch"],
        "null_hypothesis": "the player's context composition equals the matched development-population composition",
        "dependency_method": "whole-match clustered bootstrap and HMAC-nested match subsamples",
    }
    return {
        "schema_version": SCHEMA,
        "branches": [
            {
                **common,
                "id": "fight_vs_nonfight",
                "question": "Of this player's deaths, what share occurs inside OpenDota-detected teamfight windows?",
                "estimand": "observed fight-window death share minus the leave-player-and-match-out expected share under matched context",
                "support_denominator": "all player deaths in selected matches; numerator is teamfights[].players[target_index].deaths",
                "required_fields": ["players[].player_slot", "players[].deaths", "teamfights[].players[].deaths", "hero_id", "lane_role", "radiant_win", "radiant_gold_adv", "patch"],
                "main_confounders": ["teamfight detector semantics", "hero", "role", "outcome", "game tempo/state", "patch"],
                "candidate_null_model": "death-weighted post-stratified matched baseline, leave target profile and match out",
                "population_common_risk": "high unless residualized; fail if at least 90% of supported profiles share one residual direction",
                "verdict": "SURVIVES_AS_SINGLE_PRIMARY_ESTIMAND",
            },
            {
                **common,
                "id": "ahead_state",
                "question": "Are the player's deaths unusually concentrated while their team is ahead?",
                "estimand": "share of deaths occurring in ahead-state minutes, residualized to matched players",
                "support_denominator": "all player deaths plus minutes spent ahead",
                "required_fields": ["exact death timestamps", "radiant_gold_adv", "player side"],
                "main_confounders": ["outcome", "hero", "role", "lead size", "game phase"],
                "candidate_null_model": "matched death share conditional on ahead-minute exposure",
                "population_common_risk": "very high; losing a lead is a common game-state relationship",
                "verdict": "REJECT_PRIMARY: no direct per-player death log; inverse kills_log is incomplete in 14/19 captured matches",
            },
            {
                **common,
                "id": "pre_objective",
                "question": "Are deaths concentrated in a fixed window before contestable objectives?",
                "estimand": "share of deaths in predeclared pre-objective windows per eligible objective opportunity",
                "support_denominator": "eligible non-overlapping objective setup windows",
                "required_fields": ["exact death timestamps", "objectives", "objective taxonomy", "player side"],
                "main_confounders": ["objective enabled by the death", "team intent", "game state", "map control"],
                "candidate_null_model": "matched window-level death incidence conditional on objective type/state",
                "population_common_risk": "high and retrospectively anchored",
                "verdict": "REJECT_PRIMARY: indirect death timing and post-death objective anchoring make the claim ambiguous",
            },
            {
                **common,
                "id": "game_phase",
                "question": "Are the player's deaths concentrated in early, mid, or late game?",
                "estimand": "phase-specific death share relative to phase duration and matched context",
                "support_denominator": "minutes observed in each predeclared phase",
                "required_fields": ["exact death timestamps", "duration", "hero", "lane_role", "outcome", "patch"],
                "main_confounders": ["duration selection", "hero power curve", "role", "outcome"],
                "candidate_null_model": "phase-duration-offset matched baseline",
                "population_common_risk": "high; phase curves are often hero/role/game-duration laws",
                "verdict": "REJECT_FROM_FAMILY: potentially descriptive, but weaker and heterogeneous with the primary",
            },
            {
                **common,
                "id": "isolation_proximity",
                "question": "Does the player die away from teammates?",
                "estimand": "teammate proximity immediately before death",
                "support_denominator": "death events with time-aligned positions for player and teammates",
                "required_fields": ["time-resolved player positions", "exact death timestamps"],
                "main_confounders": ["role", "split-push assignment", "mobility", "map objective"],
                "candidate_null_model": "matched death-event proximity baseline",
                "population_common_risk": "medium",
                "verdict": "REJECT: lane_pos is an early-game histogram, not a time-aligned proximity timeline",
            },
        ],
    }


def field_rows(details: list[tuple[Path, dict[str, Any]]]) -> list[dict[str, str]]:
    detail_count = len(details)
    rows = [
        ("death timestamps", "indirect via opponents' players[].kills_log", "YES", "NO", "LOW", "event seconds", "14/19 captured matches have fewer kill-log entries than total deaths", "NO"),
        ("player identity/slot", "players[].player_slot and hero_id", "YES", "NO", "HIGH", "player-match", "present on 190/190 parsed player rows", "YES"),
        ("teamfight windows/membership", "teamfights[start,end,players[].deaths]", "YES", "NO", "MEDIUM", "heuristic event window", f"present in all {detail_count} captured parsed details; all player arrays length 10", "NEEDS QA"),
        ("gold-advantage timeline", "radiant_gold_adv", "YES", "NO", "MEDIUM", "one-minute team series", "present in all captured parsed details; target-panel missingness unknown", "NEEDS QA"),
        ("objective timing", "objectives[].time/type", "YES", "NO", "MEDIUM", "event seconds", "present in all captured parsed details; taxonomy is heterogeneous", "NEEDS QA"),
        ("kill chronology", "players[].kills_log", "YES", "NO", "MEDIUM", "killer-perspective event seconds", "not a direct death log and does not reconcile to total deaths in 14/19 matches", "NEEDS QA"),
        ("position timeline", "lane_pos only", "NO", "YES", "HIGH", "early-game spatial histogram", "no time-aligned player/teammate positions", "NO"),
        ("hero", "players[].hero_id", "YES", "NO", "HIGH", "player-match", "present on 190/190 parsed player rows", "YES"),
        ("lane/role", "players[].lane and lane_role", "YES", "NO", "MEDIUM", "parser enum", "present on parsed rows; heuristic, not a position contract", "NEEDS QA"),
        ("win/loss", "radiant_win plus player_slot", "YES", "NO", "HIGH", "player-match", "present/derivable in captured details", "YES"),
        ("duration", "duration", "YES", "NO", "HIGH", "seconds", "present in captured details", "YES"),
        ("patch", "patch", "YES", "NO", "HIGH", "match enum", "present in all captured parsed details", "YES"),
    ]
    fields = ("field", "source", "available_in_already_parsed_detail", "requires_replay_parsing", "semantics_confidence", "unit_resolution", "missingness_provider_caveat", "safe_to_use")
    return [{field: row[index] for index, field in enumerate(fields)} for row in rows]


def detail_summary(details: list[tuple[Path, dict[str, Any]]]) -> dict[str, Any]:
    match_rows = []
    player_rows = []
    for path, match in details:
        fights = match.get("teamfights") or []
        players = match["players"]
        match_rows.append(
            {
                "teamfight_windows": len(fights),
                "teamfight_seconds": sum(max(0, row["end"] - row["start"]) for row in fights),
                "total_deaths": sum(int(row.get("deaths") or 0) for row in players),
                "kill_log_events": sum(len(row.get("kills_log") or []) for row in players),
                "teamfight_deaths": sum(sum(int(player.get("deaths") or 0) for player in row.get("players") or []) for row in fights),
                "bytes": path.stat().st_size,
            }
        )
        for index, player in enumerate(players):
            fight_deaths = sum(
                int(fight["players"][index].get("deaths") or 0)
                for fight in fights
                if len(fight.get("players") or []) == len(players)
            )
            player_rows.append((int(player.get("deaths") or 0), fight_deaths))
    return {
        "captured_parsed_details": len(details),
        "teamfight_windows_per_match_mean": statistics.fmean(row["teamfight_windows"] for row in match_rows),
        "teamfight_windows_per_match_median": statistics.median(row["teamfight_windows"] for row in match_rows),
        "fight_death_share": sum(row["teamfight_deaths"] for row in match_rows) / sum(row["total_deaths"] for row in match_rows),
        "kill_log_total_death_exact_matches": sum(row["kill_log_events"] == row["total_deaths"] for row in match_rows),
        "parsed_payload_bytes_mean": statistics.fmean(row["bytes"] for row in match_rows),
        "parsed_payload_bytes_p95": quantile([row["bytes"] for row in match_rows], .95),
        "player_match_deaths_mean": statistics.fmean(row[0] for row in player_rows),
        "scope_caveat": "The 19 seed details establish shape only and are not a representative longitudinal player panel.",
    }


def match_count_model(profile_rows: list[dict[str, Any]], detail: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = []
    counts = []
    for n in NS:
        totals = []
        for profile in profile_rows:
            parsed = sorted(
                (row for row in profile["matches"] if row.get("source_version") == "22"),
                key=lambda row: row["start_time"],
                reverse=True,
            )
            if len(parsed) >= n:
                totals.append(sum(row["deaths"] for row in parsed[:n]))
        classification = "LIKELY_TOO_SPARSE" if n <= 15 else "PLAUSIBLE" if n <= 30 else "COMFORTABLE"
        rows.append(
            {
                "matches": n,
                "eligible_profiles": len(totals),
                "coverage_fraction": len(totals) / len(profile_rows),
                "expected_deaths_mean": statistics.fmean(totals),
                "expected_deaths_median": statistics.median(totals),
                "expected_deaths_p10": quantile(totals, .10),
                "expected_deaths_p90": quantile(totals, .90),
                "provisional_teamfight_opportunities": n * detail["teamfight_windows_per_match_mean"],
                "effective_independent_match_units": n,
                "assessment": classification,
            }
        )
        counts.append({"matches": n, "profiles": len(totals), "coverage_fraction": len(totals) / len(profile_rows)})
    return (
        {
            "schema_version": SCHEMA,
            "minimum_pilot_n_per_player": 25,
            "recommended_pilot_n_per_player": 30,
            "limitation": "Death counts come from eligible parsed summary rows. Teamfight opportunities extrapolate only the 19 captured seed details and must be replaced by pilot observations.",
            "rows": rows,
        },
        {"schema_version": SCHEMA, "population_profiles": len(profile_rows), "thresholds": counts, "pipeline_warning": "data available -> support eligible -> stable signal -> statistically qualified -> published"},
    )


def latency() -> dict[str, Any]:
    by_area: dict[str, list[float]] = {"tuning_history": [], "seed_match_detail": []}
    parsed_paths = {str(path) for path, _ in parsed_details()}
    parsed = []
    with REQUEST_LEDGER.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            area = row.get("area")
            if row.get("error") is not None or area not in by_area:
                continue
            elapsed = (datetime.fromisoformat(row["completed_at"]) - datetime.fromisoformat(row["requested_at"])).total_seconds()
            by_area[area].append(elapsed)
            if row.get("raw_artifact_path") in parsed_paths:
                parsed.append(elapsed)
    def stats(values: list[float]) -> dict[str, Any]:
        return {"n": len(values), "p50_seconds": quantile(values, .50), "p90_seconds": quantile(values, .90), "p95_seconds": quantile(values, .95), "max_seconds": max(values)}
    return {
        "schema_version": SCHEMA,
        "existing_measurements": {**{area: stats(values) for area, values in by_area.items()}, "parsed_match_detail_subset": stats(parsed)},
        "not_measured": ["concurrency 1/5/10 comparison", "20-GET wall time", "30-GET wall time", "local Death Context compute", "total enrichment time"],
        "decision_bands_seconds": {"excellent_sync": "<=5", "acceptable_sync": ">5-15", "borderline": ">15-30", "prefer_background": ">30-60", "unacceptable_blocking": ">60"},
        "current_conclusion": "Existing sequential calls were fast, but no concurrent 20/30-detail batch or end-to-end enrichment was measured; a sub-minute promise is not yet justified.",
    }


def main() -> None:
    profile_rows = profiles()
    details = parsed_details()
    assert len(profile_rows) == 1609 and len(details) == 19
    detail = detail_summary(details)
    information, coverage = match_count_model(profile_rows, detail)
    candidates = candidate_subquestions()
    write_json("candidate_subquestions.json", candidates)
    rows = field_rows(details)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "field_feasibility.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_json("opportunity_denominators.json", {"schema_version": SCHEMA, "primary": {"unit": "death context composition across whole player-matches", "numerator": "deaths inside detected teamfight windows", "denominator": "all player deaths in the selected matches", "minimum_pilot_support": {"matches": 25, "total_deaths": 100}, "clustering": "whole match", "claim_boundary": "Estimates where deaths occur, not the risk of dying given a fight."}, "rejected": ["raw death count", "KDA", "per-death independent inference", "teamfight minutes without alive-state exposure"]})
    write_json("personalization_baseline_options.json", {"schema_version": SCHEMA, "selected": {"estimand": "observed fight-death share minus expected matched share", "primary_strata": ["lane_role", "outcome", "player-team ahead-exposure quintile", "patch"], "primary_minimum_reference_deaths": 100, "hero_sensitivity": "exact hero x outcome x patch, falling back to hero x outcome only when the first cell has fewer than 100 reference deaths", "cross_fit": "leave target profile and match out", "dependency": "whole-match cluster bootstrap", "common_direction_stop": "stop if >=90% of supported profiles share one residual sign"}, "rejected": ["unadjusted population share as final evidence", "raw player death share without context controls", "death-level IID bootstrap"]})
    write_json("family_coherence.json", {"schema_version": SCHEMA, "family": "Death Context — What kind of situations repeatedly lead to your deaths?", "decision": "ONE_ESTIMAND_ONLY", "retained": "fight_vs_nonfight", "discarded": ["ahead_state", "pre_objective", "game_phase", "isolation_proximity"], "reason": "The discarded branches need indirect timestamps, introduce retrospective/generic relationships, or lack position timelines; combining them would create heterogeneous correlated mini-findings."})
    write_json("event_count_model.json", {"schema_version": SCHEMA, "captured_detail_shape_evidence": detail, "interpretation": "Event volume is probably adequate by 20 matches; independent match count and personalization stability, not raw death count, are the likely bottlenecks."})
    write_json("match_count_information_model.json", information)
    panel = {"schema_version": SCHEMA, "development_profiles": 32, "parsed_match_minimum": 30, "matches_per_profile": 30, "match_detail_gets": 960, "maximum_physical_calls": 960, "sampling": "new private 32-byte salt; HMAC-SHA256 profile rank, then HMAC-SHA256 match rank; ascending digest; greedily require 30 globally unique parsed match IDs per selected profile before any detail inspection", "replacement_policy": "structural duplicate/support failures only before detail inspection; no outcome- or payload-based replacement", "nested_n": [10, 15, 20, 25, 30], "request_plan": {"preliminary_qa": "first 4 selected GETs, sequential; stop entire panel on failure", "concurrency_measurement": [1, 5, 10], "pacing_ceiling_requests_per_minute": 240, "retries": 0}, "calls": {"opendota_gets": 960, "replay_parse_requests": 0, "stratz": 0}, "cost": {"idr_pro_rata": 1920, "usd_pro_rata": .096}, "storage_ceiling_mib": 384, "owner_approval_required": True}
    assert panel["match_detail_gets"] == panel["development_profiles"] * panel["matches_per_profile"]
    write_json("tier2_panel_design.json", panel)
    write_json("latency_research_plan.json", latency())
    scenarios = []
    for details_count in (10, 15, 20, 25, 30, 40, 50):
        calls = 1 + details_count
        scenarios.append({"scenario": f"1 history + {details_count} details", "physical_calls": calls, "idr_pro_rata": calls * 2, "usd_pro_rata": calls * .0001})
    write_json("cost_model.json", {"schema_version": SCHEMA, "assumption": "Rp200/100 physical calls and $0.01/100 physical calls; currencies calculated independently", "per_user": scenarios, "pilot": panel["cost"], "hard_owner_ceiling": {"physical_calls": 960, **panel["cost"]}})
    write_json("coverage_implication.json", coverage)
    criteria = {"schema_version": SCHEMA, "continue_only_if": {"field_completeness": ">=95% for player mapping, total deaths, teamfight arrays, hero, role, outcome, patch and advantage timeline", "parsed_state": "all selected details agree with stored parsed marker and zero parse requests", "latency": "30-GET total enrichment <=30 seconds for synchronous consideration; >30 seconds means background; >60 seconds blocks Free", "heterogeneity": "residual IQR >=0.10 and dominant residual sign <90%", "controls": ">=70% direction agreement after role/outcome/state/patch adjustment and exact-hero sensitivity; median absolute attenuation <50%", "stability": "at N=25 or N=30, split-half Spearman >=0.50 and repeated nested-subsample sign agreement >=0.75 for profiles with |full residual| >=0.05", "interpretation": "user claim remains death-context composition, never skill, aggression, KDA, causality, or good/bad deaths"}, "drop_rule": "Drop Death Context if any core field/parse/interpretation gate fails, the >=90% common-direction stop triggers, controls erase the residual, or N=30 remains unstable."}
    write_json("pilot_success_criteria.json", criteria)
    write_json("minimal_live_qa.json", {"schema_version": SCHEMA, "decision": "SUBSUME_IN_PANEL", "calls": 4, "additional_calls": 0, "checks": ["stored source_version=22 agrees with detail version=22 and od_data.has_parsed=true", "teamfight/player shape and target slot mapping", "GET-only transport; no parse client or endpoint", "observed sequential latency and bytes"], "stop": "Any failure stops before the remaining 956 calls."})
    write_json("aggregate_summary.json", {"schema_version": SCHEMA, "status": "PARTIAL", "recommendation": "Run the bounded Tier-2 pilot for one fight-vs-non-fight death-composition estimand; do not add other branches.", "best_question": candidates["branches"][0]["question"], "minimum_pilot_n_per_player": 25, "recommended_pilot_n_per_player": 30, "coverage_ceiling_at_recommended_n": 391 / 1609, "panel": panel, "integrity": {"opendota_calls": 0, "replay_parse_requests": 0, "stratz_calls": 0, "old_holdout_evaluated": 0, "fresh_sealed_validation_analytically_evaluated": 0, "production_analytical_behavior_changed": False, "deployed": False}})
    expected = {"candidate_subquestions.json", "field_feasibility.csv", "opportunity_denominators.json", "personalization_baseline_options.json", "family_coherence.json", "event_count_model.json", "match_count_information_model.json", "tier2_panel_design.json", "latency_research_plan.json", "cost_model.json", "coverage_implication.json", "pilot_success_criteria.json", "minimal_live_qa.json", "aggregate_summary.json"}
    assert expected == {path.name for path in OUTPUT.iterdir() if path.is_file()}
    print(f"PASS: wrote {len(expected)} offline diagnostics to {OUTPUT}")


if __name__ == "__main__":
    main()

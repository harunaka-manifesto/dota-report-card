#!/usr/bin/env python3
"""Offline audit of parsed OpenDota coverage in the Phase-2 tuning corpus."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import random
import statistics
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

LOCAL_ROOT = Path("/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local")
CORPUS = LOCAL_ROOT / "corpora/opendota/v61-session-drift-expansion"
SOURCE_DIAGNOSTICS = LOCAL_ROOT / "diagnostics/v61-session-drift-data-expansion"
OUTPUT = LOCAL_ROOT / "diagnostics/free-dna-opendota-parsed-feasibility"
THRESHOLDS = (10, 20, 30, 40, 50, 75, 100)
REPORT_THRESHOLDS = (20, 30, 50, 75, 100)
PARSED_CONTEXT_FIELDS = ("lane", "lane_role", "is_roaming")
SCHEMA_VERSION = "free-dna-opendota-parsed-feasibility-1.0.0"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_gzip_json(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(name: str, value: Any) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / name).write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3 or len(left) != len(right):
        return None
    mean_left = statistics.fmean(left)
    mean_right = statistics.fmean(right)
    numerator = sum(
        (a - mean_left) * (b - mean_right) for a, b in zip(left, right, strict=True)
    )
    denominator = math.sqrt(
        sum((a - mean_left) ** 2 for a in left) * sum((b - mean_right) ** 2 for b in right)
    )
    return numerator / denominator if denominator else None


def normalized_entropy(matches: list[dict[str, Any]], field: str) -> float:
    counts = Counter(match[field] for match in matches)
    if len(counts) <= 1:
        return 0.0
    total = sum(counts.values())
    return -sum((count / total) * math.log(count / total) for count in counts.values()) / math.log(
        len(counts)
    )


def dominant_share(matches: list[dict[str, Any]], field: str) -> float:
    counts = Counter(match[field] for match in matches)
    return max(counts.values(), default=0) / max(1, len(matches))


def roaming_share(matches: list[dict[str, Any]]) -> float:
    return sum(bool(match["is_roaming"]) for match in matches) / max(1, len(matches))


METRICS: dict[str, Callable[[list[dict[str, Any]]], float]] = {
    "role_entropy": lambda matches: normalized_entropy(matches, "lane_role"),
    "dominant_role_share": lambda matches: dominant_share(matches, "lane_role"),
    "lane_entropy": lambda matches: normalized_entropy(matches, "lane"),
    "roaming_share": roaming_share,
}


def is_likely_parsed(match: dict[str, Any]) -> bool:
    return match.get("source_version") == "22"


def reconcile_corpus() -> dict[str, Any]:
    raw_manifest = load_json(SOURCE_DIAGNOSTICS / "raw_corpus_manifest.json")
    normalized_manifest = load_json(SOURCE_DIAGNOSTICS / "normalized_corpus_manifest.json")
    reusable = load_json(SOURCE_DIAGNOSTICS / "reusable_corpus_manifest.json")
    split_path = CORPUS / "manifests/split-manifest.json"

    raw_rows = []
    raw_file_failures = []
    for row in raw_manifest["responses"]:
        path = Path(row["path"])
        actual = sha256_file(path) if path.is_file() else None
        if actual != row["sha256"]:
            raw_file_failures.append({"ordinal": row["ordinal"], "reason": "missing_or_digest_mismatch"})
        raw_rows.append(
            {
                "ordinal": row["ordinal"],
                "path": row["path"],
                "sha256": row["sha256"],
                "bytes": row["bytes"],
                "http_status": row["http_status"],
            }
        )
    raw_digest = digest(raw_rows)

    normalized_rows = []
    normalized_file_failures = []
    for row in normalized_manifest["profiles"]:
        path = Path(row["path"])
        actual = sha256_file(path) if path.is_file() else None
        if actual != row["sha256"]:
            normalized_file_failures.append(
                {"profile_id": row["profile_id"], "reason": "missing_or_digest_mismatch"}
            )
        normalized_rows.append((row["profile_id"], row["sha256"]))
    normalized_digest = digest(normalized_rows)
    split_digest = sha256_file(split_path)

    checks = {
        "raw_file_checks_pass": not raw_file_failures,
        "raw_digest_actual": raw_digest,
        "raw_digest_expected": reusable["raw_corpus_digest"],
        "raw_digest_pass": raw_digest == reusable["raw_corpus_digest"],
        "normalized_file_checks_pass": not normalized_file_failures,
        "normalized_digest_actual": normalized_digest,
        "normalized_digest_expected": reusable["normalized_corpus_digest"],
        "normalized_digest_pass": normalized_digest == reusable["normalized_corpus_digest"],
        "split_digest_actual": split_digest,
        "split_digest_expected": reusable["split_manifest_digest"],
        "split_digest_pass": split_digest == reusable["split_manifest_digest"],
        "provider": reusable["provider"],
        "normalizer_version": reusable["normalizer_version"],
        "canonical_schema_version": reusable["normalized_schema_version"],
        "raw_response_count": raw_manifest["raw_response_count"],
        "normalized_profile_count": normalized_manifest["normalized_profile_count"],
        "eligible_tuning_profile_count": normalized_manifest["eligible_profile_count"],
        "fresh_validation_analytically_evaluated": 0,
        "phase3_data_appended": False,
        "phase3_append_evidence": "No sibling Phase-3 corpus exists in the canonical local corpora directory.",
        "raw_file_failure_count": len(raw_file_failures),
        "normalized_file_failure_count": len(normalized_file_failures),
    }
    checks["all_pass"] = all(
        checks[key]
        for key in (
            "raw_file_checks_pass",
            "raw_digest_pass",
            "normalized_file_checks_pass",
            "normalized_digest_pass",
            "split_digest_pass",
        )
    )
    return {"schema_version": SCHEMA_VERSION, **checks}


def load_profiles() -> list[dict[str, Any]]:
    profiles = []
    for path in sorted((CORPUS / "normalized/tuning").glob("*.json.gz")):
        profile = load_gzip_json(path)["profile"]
        if profile["status"] != "eligible":
            continue
        parsed = [match for match in profile["matches"] if is_likely_parsed(match)]
        profiles.append({**profile, "likely_parsed_matches": parsed})
    return profiles


def parsed_indicator_audit(profiles: list[dict[str, Any]], details: dict[str, Any]) -> dict[str, Any]:
    matches = [match for profile in profiles for match in profile["matches"]]
    versions = Counter(str(match.get("source_version")) for match in matches)
    patterns = Counter(
        (
            str(match.get("source_version")),
            *(match.get(field) is not None for field in PARSED_CONTEXT_FIELDS),
        )
        for match in matches
    )
    likely = [match for match in matches if is_likely_parsed(match)]
    context_values = {
        field: dict(sorted(Counter(str(match.get(field)) for match in likely).items()))
        for field in PARSED_CONTEXT_FIELDS
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "canonical_offline_rule": "source_version == '22'",
        "rule_name": "ALREADY_PARSED_V22",
        "confidence": "KNOWN FOR THIS CAPTURE",
        "scope_caveat": "Revalidate after provider schema/parser-version drift; the history and detail samples are not paired by match ID.",
        "evidence": [
            "All 56,219 rule-positive eligible history rows have source_version 22 and all three parser-context fields.",
            "Across 1,200 captured match-detail responses, version 22 and od_data.has_parsed=true co-occurred exactly 19 times; the remaining 1,181 had version null and has_parsed=false.",
            "Repository normalization maps history version to source_version but labels its semantics as needing mapping.",
        ],
        "eligible_history_matches": len(matches),
        "likely_parsed_matches": len(likely),
        "likely_parsed_fraction": len(likely) / len(matches),
        "source_version_values": dict(sorted(versions.items())),
        "indicator_patterns": [
            {
                "source_version": pattern[0],
                "lane_present": pattern[1],
                "lane_role_present": pattern[2],
                "is_roaming_present": pattern[3],
                "count": count,
            }
            for pattern, count in sorted(patterns.items(), key=lambda item: str(item[0]))
        ],
        "candidate_indicators": [
            {
                "field": "source_version",
                "location": "normalized history match",
                "observed_values": dict(sorted(versions.items())),
                "semantic_meaning": "OpenDota parser version; value 22 marks parsed detail in this capture",
                "evidence_source": "normalized histories plus captured detail version/od_data equivalence",
                "confidence": "KNOWN FOR THIS CAPTURE",
            },
            {
                "field": "lane/lane_role/is_roaming",
                "location": "normalized history match",
                "observed_values": context_values,
                "semantic_meaning": "parser-derived context that co-occurs with version 22, not an independent parse-state contract",
                "evidence_source": "56,219 eligible history rows",
                "confidence": "LIKELY AS SUPPORTING INDICATOR",
            },
            {
                "field": "od_data.has_parsed",
                "location": "captured match-detail response only",
                "observed_values": details["od_data_has_parsed_values"],
                "semantic_meaning": "direct match-detail parsed-state flag",
                "evidence_source": "1,200 captured seed-match detail responses",
                "confidence": "KNOWN",
            },
        ],
        "false_positive_policy": "Exact observed parser-version value; unknown future versions are not silently accepted.",
        "provider_qa_required_for_stored_corpus_status": False,
    }


def coverage(profiles: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    rows = []
    for profile in profiles:
        parsed = profile["likely_parsed_matches"]
        end = profile["collection_window"]["end_time"]
        starts = [match["start_time"] for match in parsed]
        rows.append(
            {
                "profile_id": profile["profile_id"],
                "eligible_365d_matches": len(profile["matches"]),
                "likely_already_parsed_matches": len(parsed),
                "parsed_fraction": len(parsed) / len(profile["matches"]),
                "most_recent_parsed_age_days": (end - max(starts)) / 86400 if starts else "",
                "oldest_parsed_age_days": (end - min(starts)) / 86400 if starts else "",
            }
        )
    counts = [row["likely_already_parsed_matches"] for row in rows]
    ages_recent = [float(row["most_recent_parsed_age_days"]) for row in rows if row["most_recent_parsed_age_days"] != ""]
    ages_oldest = [float(row["oldest_parsed_age_days"]) for row in rows if row["oldest_parsed_age_days"] != ""]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "profile_count": len(rows),
        "eligible_365d_match_count": sum(row["eligible_365d_matches"] for row in rows),
        "likely_parsed_match_count": sum(counts),
        "profiles_with_zero_likely_parsed": sum(count == 0 for count in counts),
        "parsed_matches_quantiles": {
            label: quantile(counts, probability)
            for label, probability in (("p10", .10), ("p25", .25), ("median", .50), ("p75", .75), ("p90", .90), ("p95", .95))
        },
        "most_recent_parsed_age_days_quantiles": {
            label: quantile(ages_recent, probability)
            for label, probability in (("p10", .10), ("p25", .25), ("median", .50), ("p75", .75), ("p90", .90), ("p95", .95))
        },
        "oldest_parsed_age_days_quantiles": {
            label: quantile(ages_oldest, probability)
            for label, probability in (("p10", .10), ("p25", .25), ("median", .50), ("p75", .75), ("p90", .90), ("p95", .95))
        },
    }
    thresholds = {
        "schema_version": SCHEMA_VERSION,
        "overall": {
            str(n): {
                "profiles": sum(count >= n for count in counts),
                "fraction": sum(count >= n for count in counts) / len(rows),
            }
            for n in THRESHOLDS
        },
        "by_total_365d_match_depth": {},
    }
    bands = (("30-49", 30, 49), ("50-99", 50, 99), ("100-199", 100, 199), ("200+", 200, 10**9))
    for label, lower, upper in bands:
        selected = [row for row in rows if lower <= row["eligible_365d_matches"] <= upper]
        thresholds["by_total_365d_match_depth"][label] = {
            "profiles": len(selected),
            "median_likely_parsed_matches": statistics.median(
                row["likely_already_parsed_matches"] for row in selected
            ) if selected else None,
            "thresholds": {
                str(n): sum(row["likely_already_parsed_matches"] >= n for row in selected) / len(selected)
                if selected else None
                for n in THRESHOLDS
            },
        }
    return rows, summary, thresholds


def detail_field_audit() -> dict[str, Any]:
    ledger_path = SOURCE_DIAGNOSTICS / "request_ledger.jsonl"
    requests = []
    with ledger_path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("area") == "seed_match_detail" and row.get("http_status") == 200:
                requests.append(row)
    match_fields = Counter()
    player_fields = Counter()
    parsed_player_fields = Counter()
    versions = Counter()
    parsed_flags = Counter()
    player_rows = 0
    parsed_player_rows = 0
    for request in requests:
        payload = load_json(Path(request["raw_artifact_path"]))
        for field, value in payload.items():
            if value is not None:
                match_fields[field] += 1
        versions[str(payload.get("version"))] += 1
        od_data = payload.get("od_data")
        parsed_flags[str(od_data.get("has_parsed")) if isinstance(od_data, dict) else "missing"] += 1
        detail_is_parsed = payload.get("version") == 22 and isinstance(od_data, dict) and od_data.get("has_parsed") is True
        for player in payload.get("players") or []:
            player_rows += 1
            if detail_is_parsed:
                parsed_player_rows += 1
            for field, value in player.items():
                if value is not None:
                    player_fields[field] += 1
                    if detail_is_parsed:
                        parsed_player_fields[field] += 1
    watched_match_fields = (
        "version", "od_data", "objectives", "teamfights", "radiant_gold_adv", "radiant_xp_adv"
    )
    watched_player_fields = (
        "purchase_log", "actions", "actions_per_min", "lane_efficiency", "lane_efficiency_pct",
        "obs_log", "sen_log", "buyback_log", "buyback_count", "kills_log", "gold_t", "xp_t",
        "lh_t", "dn_t", "lane_pos", "teamfight_participation", "item_uses", "ability_uses",
        "damage_targets", "deaths", "lane", "lane_role", "is_roaming",
    )
    return {
        "detail_response_count": len(requests),
        "player_row_count": player_rows,
        "parsed_player_row_count": parsed_player_rows,
        "version_values": dict(sorted(versions.items())),
        "od_data_has_parsed_values": dict(sorted(parsed_flags.items())),
        "watched_match_field_coverage": {
            field: {"count": match_fields[field], "fraction": match_fields[field] / max(1, len(requests))}
            for field in watched_match_fields
        },
        "watched_player_field_coverage": {
            field: {
                "all_detail_count": player_fields[field],
                "all_detail_fraction": player_fields[field] / max(1, player_rows),
                "parsed_detail_count": parsed_player_fields[field],
                "parsed_detail_fraction": parsed_player_fields[field] / max(1, parsed_player_rows),
            }
            for field in watched_player_fields
        },
        "caveat": "Seed-match detail responses establish captured shapes, not longitudinal player-level stability or target-profile coverage.",
    }


def field_inventory(profiles: list[dict[str, Any]], details: dict[str, Any]) -> list[dict[str, Any]]:
    matches = [match for profile in profiles for match in profile["matches"]]
    parsed = [match for match in matches if is_likely_parsed(match)]
    history = [
        ("lane", "history.lane", "profile.matches[].lane", "NO", "LIKELY", "NO", "enum", "lane assignment is parser-derived", "MEDIUM"),
        ("lane_role", "history.lane_role", "profile.matches[].lane_role", "NO", "LIKELY", "NO", "enum", "not a position label; support vocabulary is weak", "MEDIUM"),
        ("is_roaming", "history.is_roaming", "profile.matches[].is_roaming", "NO", "LIKELY", "NO", "boolean", "parser heuristic and rare-state sensitivity", "LOW"),
        ("party_size", "history.party_size", "profile.matches[].party_size", "NO", "NO", "NO", "count", "null does not prove solo", "LOW"),
        ("hero_variant", "history.hero_variant", "profile.matches[].hero_variant", "NO", "NO", "NO", "enum", "not a behavioral signal alone", "LOW"),
    ]
    detail = [
        ("purchase timing", "detail.players[].purchase_log", "absent", "YES", "YES", "NO", "timestamped events", "item graph and patch needed", "HIGH"),
        ("actions per minute", "detail.players[].actions/actions_per_min", "absent", "YES", "YES", "NO", "counts/rate", "hero/unit-control confounding", "LOW"),
        ("lane efficiency", "detail.players[].lane_efficiency_pct", "absent", "YES", "YES", "NO", "ratio", "OpenDota post-processing; patch-sensitive", "LOW"),
        ("vision rhythm", "detail.players[].obs_log/sen_log", "absent", "YES", "YES", "NO", "timestamped events", "role/opportunity conditional", "HIGH"),
        ("buybacks", "detail.players[].buyback_log", "absent", "YES", "YES", "NO", "timestamped events", "rare opportunity", "MEDIUM"),
        ("objectives", "detail.objectives", "absent", "YES", "YES", "NO", "timestamped events", "participation attribution incomplete", "HIGH"),
        ("kill/death timing", "detail.players[].kills_log/teamfights", "absent", "YES", "YES", "NO", "timestamped/heuristic", "death inversion and fight-detector caveats", "HIGH"),
        ("resource rhythm", "detail.players[].gold_t/xp_t/lh_t/dn_t", "absent", "YES", "YES", "NO", "minute series", "series semantics differ; role/state confounding", "HIGH"),
        ("fight timing", "detail.teamfights", "absent", "YES", "YES", "NO", "heuristic windows", "omits fights with fewer than three deaths", "MEDIUM"),
        ("gold/XP advantage", "detail.radiant_gold_adv/radiant_xp_adv", "absent", "YES", "YES", "NO", "minute series", "team state, not player attribution", "HIGH"),
        ("early lane position", "detail.players[].lane_pos", "absent", "YES", "YES", "NO", "spatial histogram", "first ten minutes; no ordering", "MEDIUM"),
        ("death context", "detail kills/teamfights/advantage", "absent", "YES", "YES", "NO", "reconstructed events", "no raw combat log or causal attribution", "MEDIUM"),
        ("full movement/cast sequence", "raw replay", "absent", "YES", "YES", "YES", "event stream", "not exposed by stock parsed detail", "LOW"),
    ]
    rows = []
    for name, raw_source, normalized, per_match, already_parsed, parse_job, unit, caveat, suitability in history + detail:
        if raw_source.startswith("history."):
            key = raw_source.split(".")[-1]
            present = sum(match.get(key) is not None for match in matches)
            parsed_present = sum(match.get(key) is not None for match in parsed)
            missingness = f"{present}/{len(matches)} overall; {parsed_present}/{len(parsed)} likely-parsed"
        else:
            missingness = "Captured detail shape only; target-profile longitudinal missingness unknown"
        rows.append(
            {
                "field_or_concept": name,
                "raw_source": raw_source,
                "normalized_source": normalized,
                "requires_per_match_get": per_match,
                "requires_match_already_parsed": already_parsed,
                "requires_new_parse_job": parse_job,
                "unit": unit,
                "missingness": missingness,
                "semantic_caveat": caveat,
                "candidate_finding_usefulness": "behavioral input" if suitability in {"HIGH", "MEDIUM"} else "context/diagnostic",
                "instant_free_suitability": suitability if per_match == "NO" else "LOW",
            }
        )
    return rows


def stability(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    rng = random.Random(20260828)
    output: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "repetitions": 40, "thresholds": {}}
    for n in THRESHOLDS:
        eligible = [profile for profile in profiles if len(profile["likely_parsed_matches"]) >= n]
        metric_rows: dict[str, Any] = {}
        for metric_name, metric in METRICS.items():
            correlations = []
            direction_agreements = []
            absolute_differences = []
            for _ in range(40):
                left_values = []
                right_values = []
                for profile in eligible:
                    sample = rng.sample(profile["likely_parsed_matches"], n)
                    rng.shuffle(sample)
                    middle = len(sample) // 2
                    left_values.append(metric(sample[:middle]))
                    right_values.append(metric(sample[middle:]))
                correlation = pearson(left_values, right_values)
                if correlation is not None:
                    correlations.append(correlation)
                if left_values:
                    center = statistics.median(left_values + right_values)
                    direction_agreements.append(
                        sum(
                            (left - center) * (right - center) >= 0
                            for left, right in zip(left_values, right_values, strict=True)
                        )
                        / len(left_values)
                    )
                    absolute_differences.extend(
                        abs(left - right)
                        for left, right in zip(left_values, right_values, strict=True)
                    )
            metric_rows[metric_name] = {
                "profiles": len(eligible),
                "median_split_half_correlation": statistics.median(correlations) if correlations else None,
                "median_direction_agreement": statistics.median(direction_agreements) if direction_agreements else None,
                "median_absolute_half_difference": statistics.median(absolute_differences) if absolute_differences else None,
            }
        output["thresholds"][str(n)] = metric_rows

    sensitivity: dict[str, Any] = {}
    for metric_name, metric in METRICS.items():
        full_values, hero_removed_values, wins, losses, early, late = [], [], [], [], [], []
        for profile in profiles:
            matches = profile["likely_parsed_matches"]
            if len(matches) < 20:
                continue
            full_values.append(metric(matches))
            dominant_hero = Counter(match["hero_id"] for match in matches).most_common(1)[0][0]
            without_hero = [match for match in matches if match["hero_id"] != dominant_hero]
            if len(without_hero) >= 10:
                hero_removed_values.append((metric(matches), metric(without_hero)))
            won = [match for match in matches if match["won"]]
            lost = [match for match in matches if not match["won"]]
            if len(won) >= 10 and len(lost) >= 10:
                wins.append(metric(won))
                losses.append(metric(lost))
            chronological = sorted(matches, key=lambda match: match["start_time"])
            middle = len(chronological) // 2
            early.append(metric(chronological[:middle]))
            late.append(metric(chronological[middle:]))
        sensitivity[metric_name] = {
            "profiles_with_20_plus": len(full_values),
            "dominant_hero_removed_correlation": pearson(
                [pair[0] for pair in hero_removed_values], [pair[1] for pair in hero_removed_values]
            ),
            "median_win_loss_absolute_difference": statistics.median(
                abs(a - b) for a, b in zip(wins, losses, strict=True)
            ) if wins else None,
            "chronological_half_correlation": pearson(early, late),
            "patch_sensitivity": "BLOCKED: patch was not retained in the canonical history projection",
        }
    output["confounder_sensitivity"] = sensitivity
    output["interpretation_rule"] = "Descriptive feasibility only; no production threshold or qualification is set."
    return output


def candidates(thresholds: dict[str, Any], stability_data: dict[str, Any]) -> list[dict[str, Any]]:
    fraction_30 = thresholds["overall"]["30"]["fraction"]
    return [
        {
            "name": "Role Shape",
            "behavioral_question": "Does the player stay in one lane-role shape or repeatedly move across roles?",
            "exact_fields": ["lane_role", "lane", "hero_id", "start_time"],
            "data_tier": 1,
            "minimum_plausible_support": 30,
            "expected_coverage": fraction_30,
            "major_confounders": ["hero pool", "parser role heuristic", "support-position collapse", "patch unavailable"],
            "distinctness": "Different from Transfer/Post-Loss/Session Drift, but overlaps hero-pool identity.",
            "personalization_potential": "MEDIUM",
            "free_suitability": "HOLD",
            "evidence_status": "Measured coverage and stability; semantics need minimal provider QA.",
        },
        {
            "name": "Roaming Tendency",
            "behavioral_question": "How consistently does the parser classify the player as roaming?",
            "exact_fields": ["is_roaming", "lane_role", "hero_id"],
            "data_tier": 1,
            "minimum_plausible_support": 30,
            "expected_coverage": fraction_30,
            "major_confounders": ["parser heuristic", "role", "hero mobility", "rare positives"],
            "distinctness": "Different measurement, but likely perceived as a role label rather than a full Finding.",
            "personalization_potential": "LOW",
            "free_suitability": "REJECT AS SECOND FINDING",
            "evidence_status": "Measured; insufficient product distinctness.",
        },
        {
            "name": "Build Adaptation",
            "behavioral_question": "Does item order change with enemy lineup and game state?",
            "exact_fields": ["purchase_log", "players", "patch", "advantage timelines"],
            "data_tier": 2,
            "minimum_plausible_support": 30,
            "expected_coverage": fraction_30,
            "major_confounders": ["hero", "role", "patch", "item graph", "team state"],
            "distinctness": "Clearly different from all current Findings.",
            "personalization_potential": "HIGH",
            "free_suitability": "BACKGROUND PILOT",
            "evidence_status": "Fields observed in detail responses; stability not measurable from this corpus.",
        },
        {
            "name": "Resource Rhythm",
            "behavioral_question": "How does farm/resource behavior change around fights and objectives?",
            "exact_fields": ["gold_t", "xp_t", "lh_t", "dn_t", "teamfights", "objectives"],
            "data_tier": 2,
            "minimum_plausible_support": 30,
            "expected_coverage": fraction_30,
            "major_confounders": ["role", "hero", "game state", "minute resolution"],
            "distinctness": "Distinct from current session/result questions.",
            "personalization_potential": "HIGH",
            "free_suitability": "BACKGROUND PILOT",
            "evidence_status": "Fields observed in detail responses; stability not measurable from this corpus.",
        },
        {
            "name": "Vision Rhythm",
            "behavioral_question": "Is vision placed proactively, reactively, or in bursts?",
            "exact_fields": ["obs_log", "sen_log", "objectives", "kills_log"],
            "data_tier": 2,
            "minimum_plausible_support": 20,
            "expected_coverage": thresholds["overall"]["20"]["fraction"],
            "major_confounders": ["role", "ward opportunity", "team vision burden"],
            "distinctness": "Clearly distinct, but support-only for many profiles.",
            "personalization_potential": "HIGH WHEN APPLICABLE",
            "free_suitability": "BACKGROUND/DEEP",
            "evidence_status": "Fields observed; opportunity coverage unknown.",
        },
        {
            "name": "Fight Clock",
            "behavioral_question": "When do the player's kill/death and fight contributions occur?",
            "exact_fields": ["kills_log", "teamfights", "gold_t", "radiant_gold_adv", "radiant_xp_adv"],
            "data_tier": 2,
            "minimum_plausible_support": 30,
            "expected_coverage": fraction_30,
            "major_confounders": ["role", "hero", "teamfight detector", "team tempo"],
            "distinctness": "Different from Post-Loss and Session Drift if defined within-match only.",
            "personalization_potential": "HIGH",
            "free_suitability": "BACKGROUND PILOT",
            "evidence_status": "Fields observed; longitudinal stability unavailable.",
        },
    ]


def distinctness_matrix(candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    current = {
        "Transfer": "cross-session behavioral transfer",
        "Post-Loss": "within-session response after result states",
        "Session Drift": "early-versus-late result movement within sessions",
    }
    rows = []
    for candidate in candidate_rows:
        for finding, question in current.items():
            name = candidate["name"]
            likely = "MEDIUM" if name == "Fight Clock" and finding in {"Post-Loss", "Session Drift"} else "LOW"
            same_confounder = "hero/role" if name != "Roaming Tendency" else "role"
            rows.append(
                {
                    "candidate": name,
                    "existing_finding": finding,
                    "same_behavioral_question": "NO",
                    "same_underlying_measurement": "NO",
                    "same_primary_confounder": same_confounder,
                    "likely_correlated": likely,
                    "different_user_story": "YES" if name != "Roaming Tendency" else "PARTIAL",
                    "existing_question": question,
                }
            )
    return rows


def two_finding_model(profiles: list[dict[str, Any]], stability_data: dict[str, Any]) -> dict[str, Any]:
    rows = {}
    for n in REPORT_THRESHOLDS:
        selected = [profile for profile in profiles if len(profile["likely_parsed_matches"]) >= n]
        role_stability = stability_data["thresholds"][str(n)]["role_entropy"]
        roam_stability = stability_data["thresholds"][str(n)]["roaming_share"]
        stable = [
            profile for profile in selected
            if abs(METRICS["role_entropy"](profile["likely_parsed_matches"][::2]) - METRICS["role_entropy"](profile["likely_parsed_matches"][1::2])) <= .20
            and abs(METRICS["roaming_share"](profile["likely_parsed_matches"][::2]) - METRICS["roaming_share"](profile["likely_parsed_matches"][1::2])) <= .15
        ]
        rows[str(n)] = {
            "data_available_for_a": len(selected) / len(profiles),
            "data_available_for_b": len(selected) / len(profiles),
            "support_eligible_for_at_least_one": len(selected) / len(profiles),
            "support_eligible_for_both": len(selected) / len(profiles),
            "descriptively_stable_for_both": len(stable) / len(profiles),
            "profiles_supporting_both": len(selected),
            "role_shape_aggregate_stability": role_stability,
            "roaming_aggregate_stability": roam_stability,
            "future_statistically_qualified": "NOT EVALUATED",
            "published": "NOT EVALUATED",
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_a": "Role Shape",
        "candidate_b": "Roaming Tendency",
        "thresholds": rows,
        "important_caveat": "These are the only two Tier-1 parsed-context concepts; support is not publication, and Roaming Tendency was rejected as a sufficiently distinct second Finding.",
    }


def cost_model() -> dict[str, Any]:
    scenarios = []
    for name, calls, retained, latency in (
        ("history-only baseline", 1, "summary history", "instant baseline"),
        ("history + two Tier-1 concepts", 1, "summary history", "instant baseline"),
        ("history + 20 per-match GETs", 21, "summary + 20 details", "likely synchronous but unverified"),
        ("history + 50 per-match GETs", 51, "summary + 50 details", "likely delayed"),
        ("history + 100 per-match GETs", 101, "summary + 100 details", "likely delayed"),
        ("history + parse submissions + polling", None, "summary + replay-derived details", "asynchronous"),
    ):
        scenarios.append(
            {
                "scenario": name,
                "physical_api_calls": calls if calls is not None else "UNKNOWN",
                "idr_per_user_pro_rata": calls * 2 if calls is not None else "UNKNOWN",
                "usd_per_user_pro_rata": calls * .0001 if calls is not None else "UNKNOWN",
                "cost_assumption": "OWNER-SUPPLIED COST ASSUMPTION: Rp200/100 calls; $0.01/100 calls",
                "expected_retained_data": retained,
                "latency_class": latency,
            }
        )
    return {"schema_version": SCHEMA_VERSION, "scenarios": scenarios}


def main() -> None:
    reconciliation = reconcile_corpus()
    if not reconciliation["all_pass"]:
        raise SystemExit("corpus reconciliation failed")
    profiles = load_profiles()
    details = detail_field_audit()
    indicator = parsed_indicator_audit(profiles, details)
    coverage_rows, coverage_summary, threshold_coverage = coverage(profiles)
    inventory = field_inventory(profiles, details)
    stability_data = stability(profiles)
    candidate_rows = candidates(threshold_coverage, stability_data)
    distinctness = distinctness_matrix(candidate_rows)
    two_finding = two_finding_model(profiles, stability_data)
    costs = cost_model()
    tiers = {
        "schema_version": SCHEMA_VERSION,
        "tier_1": {
            "product_mapping": "FREE-INSTANT",
            "fields": ["version/source_version", "lane", "lane_role", "is_roaming", "party_size", "hero_variant"],
            "limitation": "Only lane/role/roaming are parsed-derived behavioral context; insufficient for two strong Findings.",
        },
        "tier_2": {
            "product_mapping": "BACKGROUND-ENRICHMENT or FREE-WITH-EXTRA-GETS",
            "fields": ["purchase logs", "ward logs", "kill logs", "buybacks", "objectives", "minute economy", "teamfights", "advantage timelines", "lane_pos"],
            "limitation": "One detail GET per selected match under the current REST architecture.",
        },
        "tier_3": {
            "product_mapping": "DEEP-ONLY",
            "fields": ["raw movement", "ordered cast sequences", "cooldown/mana state", "full inventory state"],
            "limitation": "Requires replay parse/reprocessing and cannot support instant Free.",
        },
    }
    qa = {
        "schema_version": SCHEMA_VERSION,
        "status": "OWNER APPROVAL REQUIRED BEFORE ANY CALL",
        "tests": [
            {
                "question": "Does the history rule agree with detail parse state?",
                "minimum_calls": 2,
                "endpoint_concept": "detail GET for one rule-positive and one rule-negative stored match",
                "resolution": "Compare history version/context with detail version and od_data.has_parsed.",
                "maximum_cost": {"idr_pro_rata": 4, "usd_pro_rata": .0002},
                "stop_condition": "Any disagreement; do not use the rule as KNOWN.",
            },
            {
                "question": "Does an already-parsed detail GET avoid a parse submission and return the expected Tier-2 shape?",
                "minimum_calls": 1,
                "endpoint_concept": "detail GET for the known parsed match",
                "resolution": "Expected parsed arrays/logs present with no parse job.",
                "maximum_cost": {"idr_pro_rata": 2, "usd_pro_rata": .0001},
                "stop_condition": "Missing detail or any parse workflow requirement.",
            },
            {
                "question": "What is the actual latency for a small already-parsed batch?",
                "minimum_calls": 1,
                "endpoint_concept": "one known parsed detail fetch with timing recorded",
                "resolution": "Provides a measured single-call latency input; no SLA inference.",
                "maximum_cost": {"idr_pro_rata": 2, "usd_pro_rata": .0001},
                "stop_condition": "Rate limit, unexpected billing, or response-shape drift.",
            },
        ],
        "maximum_total_calls_if_approved": 4,
        "maximum_total_cost": {"idr_pro_rata": 8, "usd_pro_rata": .0004},
    }
    instant = {
        "schema_version": SCHEMA_VERSION,
        "architectures": {
            "A": {"calls_per_user": 1, "parse_jobs": 0, "latency": "baseline instant class", "coverage_for_two_at_n30": threshold_coverage["overall"]["30"]["fraction"], "verdict": "No: Tier-1 fields do not support two strong distinct Findings."},
            "B": {"calls_per_user": {str(n): n + 1 for n in REPORT_THRESHOLDS}, "parse_jobs": 0, "latency": "unknown; likely synchronous only at the low end", "coverage": {str(n): threshold_coverage["overall"][str(n)]["fraction"] for n in REPORT_THRESHOLDS}, "verdict": "Use as bounded background pilot, not default Free."},
            "C": {"calls_per_user": "UNKNOWN", "parse_jobs": "one per unparsed match selected", "latency": "asynchronous", "coverage": "UNKNOWN", "verdict": "Deep only."},
        },
    }
    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "status": "PARTIAL",
        "recommendation": "C. USE PARSED DATA ONLY AS BACKGROUND ENRICHMENT",
        "reason": "The one-call history layer exposes only role/lane/roaming context and just 24.30% of profiles have 30 likely-parsed matches. Strong candidates require detail GETs; their longitudinal stability is not measurable from this corpus.",
        "corpus": {"profiles": coverage_summary["profile_count"], "matches": coverage_summary["eligible_365d_match_count"], "provider": "OpenDota", "digest_verified": True},
        "parsed_indicator": indicator["canonical_offline_rule"],
        "parsed_indicator_confidence": indicator["confidence"],
        "likely_useful_n_range": "30-50 for descriptive role-context work; UNKNOWN for Tier-2 Findings",
        "integrity": {"opendota_calls": 0, "parse_jobs_submitted": 0, "stratz_calls": 0, "old_holdout_evaluated": 0, "fresh_sealed_validation_analytically_evaluated": 0, "production_analytical_behavior_changed": False, "deployed": False},
    }

    write_json("corpus_reconciliation.json", reconciliation)
    write_json("parsed_indicator_audit.json", indicator)
    write_csv("parsed_coverage_by_profile.csv", coverage_rows)
    write_json("parsed_coverage_summary.json", coverage_summary)
    write_json("parsed_threshold_coverage.json", threshold_coverage)
    write_csv("parsed_field_inventory.csv", inventory)
    write_json("data_tier_inventory.json", tiers)
    write_json("candidate_finding_shortlist.json", candidate_rows)
    write_csv("candidate_distinctness_matrix.csv", distinctness)
    write_json("stability_by_match_count.json", stability_data)
    write_json("two_finding_coverage_model.json", two_finding)
    write_json("free_architecture_cost_model.json", costs)
    write_json("instant_ux_feasibility.json", instant)
    write_json("minimal_provider_qa_plan.json", qa)
    write_json("aggregate_summary.json", aggregate)
    write_json("captured_detail_field_audit.json", details)

    required = {
        "corpus_reconciliation.json", "parsed_indicator_audit.json", "parsed_coverage_by_profile.csv",
        "parsed_coverage_summary.json", "parsed_threshold_coverage.json", "parsed_field_inventory.csv",
        "data_tier_inventory.json", "candidate_finding_shortlist.json", "candidate_distinctness_matrix.csv",
        "stability_by_match_count.json", "two_finding_coverage_model.json", "free_architecture_cost_model.json",
        "instant_ux_feasibility.json", "minimal_provider_qa_plan.json", "aggregate_summary.json",
    }
    assert required <= {path.name for path in OUTPUT.iterdir()}
    assert len(profiles) == 1609
    assert indicator["likely_parsed_matches"] == 56219
    assert reconciliation["all_pass"]
    print(json.dumps(aggregate, indent=2))


if __name__ == "__main__":
    main()

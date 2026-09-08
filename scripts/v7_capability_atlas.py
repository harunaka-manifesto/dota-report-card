#!/usr/bin/env python3
"""Neutral V7 capability atlas: what the completed corpus can support, for whom.

This runs before any candidate ranking and takes no position on which Findings
are attractive. It reports aggregate distributions only; no account, match, or
session identifier ever leaves the local corpus. It makes no provider call.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.player_analysis_v7.research.corpus import (  # noqa: E402
    CANDIDATE_TEST,
    DISCOVERY,
    corpus_paths,
    iter_players,
    read_json,
)
from app.player_analysis_v7.research.tables import (  # noqa: E402
    SESSION_GAP_SECONDS,
    expected_trajectory_length,
    has_role_context,
    is_product_context,
    is_structurally_observable,
    iter_sessions,
    mode_stratum,
    order_by_time,
    player_networth_lead,
)

QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)


def describe(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    summary: dict[str, Any] = {
        "n": len(ordered),
        "mean": round(statistics.fmean(ordered), 3),
        "min": ordered[0],
        "max": ordered[-1],
    }
    for quantile in QUANTILES:
        index = min(len(ordered) - 1, int(quantile * (len(ordered) - 1) + 0.5))
        summary[f"p{int(quantile * 100)}"] = ordered[index]
    return summary


def share_at_least(values: list[float], thresholds: tuple[int, ...]) -> dict[str, float]:
    if not values:
        return {}
    return {
        f">= {threshold}": round(
            sum(1 for value in values if value >= threshold) / len(values), 4
        )
        for threshold in thresholds
    }


def build_atlas(corpus_root: str | None) -> dict[str, Any]:
    paths = corpus_paths(corpus_root)
    run_manifest = read_json(paths.run_manifest)

    per_player: dict[str, dict[str, Any]] = {}
    history_split: Counter[str] = Counter()
    mode_rows: Counter[str] = Counter()
    lobby_rows: Counter[str] = Counter()
    leaver_rows: Counter[str] = Counter()
    patch_rows: Counter[int] = Counter()
    position_rows: Counter[str] = Counter()
    role_rows: Counter[str] = Counter()
    lane_rows: Counter[str] = Counter()
    duration_by_stratum: dict[str, list[int]] = defaultdict(list)
    parsed_by_context: dict[str, Counter[str]] = defaultdict(Counter)

    for document in iter_players(paths, "history"):
        pseudonym = document["account_pseudonym"]
        split = document["split"]
        history_split[split] += 1
        rows = document["rows"]
        ordered = order_by_time(rows)
        product_rows = [row for row in ordered if is_product_context(row)]
        standard_rows = [row for row in product_rows if mode_stratum(row) == "STANDARD"]
        turbo_rows = [row for row in product_rows if mode_stratum(row) == "TURBO"]
        role_rows_player = [row for row in product_rows if has_role_context(row)]

        for row in rows:
            mode_rows[row.get("game_mode_native") or "__MISSING__"] += 1
            lobby_rows[row.get("lobby_type_native") or "__MISSING__"] += 1
            leaver_rows[row.get("leaver_status_native") or "__MISSING__"] += 1
            patch_rows[row.get("game_version_id")] += 1
            position_rows[row.get("position_native") or "__MISSING__"] += 1
            role_rows[row.get("role_native") or "__MISSING__"] += 1
            lane_rows[row.get("lane_native") or "__MISSING__"] += 1
            duration_by_stratum[mode_stratum(row)].append(row["duration_seconds"])
            # Parsed availability against observable, allowed context only.
            context = "|".join(
                (
                    mode_stratum(row),
                    str(row.get("lobby_type_native")),
                    str(row.get("role_native")),
                    str(row.get("position_native")),
                    str(row.get("game_version_id")),
                )
            )
            parsed_by_context[context]["available" if row.get("is_parsed") else "missing"] += 1

        sessions = list(iter_sessions(product_rows))
        session_lengths = [session.length for session in sessions]
        multi_match_sessions = [length for length in session_lengths if length >= 2]
        losses_with_successor = 0
        wins_with_successor = 0
        for session in sessions:
            for index in range(session.start_index, session.end_index):
                if product_rows[index].get("is_victory") is False:
                    losses_with_successor += 1
                elif product_rows[index].get("is_victory") is True:
                    wins_with_successor += 1

        heroes = Counter(row["hero_id"] for row in product_rows)
        positions = Counter(
            row["position_native"] for row in role_rows_player if row.get("position_native")
        )

        per_player[pseudonym] = {
            "split": split,
            "completeness": document.get("completeness"),
            "history_rows": len(rows),
            "product_rows": len(product_rows),
            "standard_rows": len(standard_rows),
            "turbo_rows": len(turbo_rows),
            "rows_with_role_context": len(role_rows_player),
            "structurally_observable_rows": sum(
                1 for row in rows if is_structurally_observable(row)
            ),
            "parsed_flagged_rows": sum(1 for row in rows if row.get("is_parsed")),
            "sessions": len(sessions),
            "multi_match_sessions": len(multi_match_sessions),
            "in_session_transitions": losses_with_successor + wins_with_successor,
            "in_session_losses_with_successor": losses_with_successor,
            "in_session_wins_with_successor": wins_with_successor,
            "distinct_heroes": len(heroes),
            "top_hero_share": round(max(heroes.values()) / len(product_rows), 4)
            if product_rows
            else None,
            "distinct_positions": len(positions),
            "dominant_position_share": round(max(positions.values()) / sum(positions.values()), 4)
            if positions
            else None,
            "distinct_patches": len({row["game_version_id"] for row in product_rows}),
            "active_days": len({row["started_at"] // 86_400 for row in product_rows}),
            "parsed_flagged_product_rows": sum(
                1 for row in product_rows if row.get("is_parsed")
            ),
            "parsed_flagged_share_of_product": round(
                sum(1 for row in product_rows if row.get("is_parsed")) / len(product_rows), 4
            )
            if product_rows
            else 0.0,
            "parsed_rows": 0,
            "parsed_product_rows": 0,
            "parsed_with_trajectory": 0,
            "parsed_with_events": 0,
        }

    parsed_split: Counter[str] = Counter()
    trajectory_length_delta: Counter[int] = Counter()
    event_agreement: Counter[str] = Counter()
    kill_event_delta: Counter[int] = Counter()
    assist_event_delta: Counter[int] = Counter()
    parsed_rows_total = 0
    trajectory_rows = 0
    orientation_resolved = 0

    history_index: dict[str, dict[int, dict[str, Any]]] = {}
    for document in iter_players(paths, "history"):
        history_index[document["account_pseudonym"]] = {
            row["match_id"]: row for row in document["rows"]
        }

    for document in iter_players(paths, "parsed"):
        pseudonym = document["account_pseudonym"]
        parsed_split[document["split"]] += 1
        entry = per_player.get(pseudonym)
        history_rows = history_index.get(pseudonym, {})
        rows = document["rows"]
        parsed_rows_total += len(rows)
        product_parsed = 0
        with_trajectory = 0
        with_events = 0
        for row in rows:
            history_row = history_rows.get(row["match_id"])
            if history_row is not None and is_product_context(history_row):
                product_parsed += 1
            trajectory = row.get("radiant_networth_leads")
            if trajectory:
                trajectory_rows += 1
                with_trajectory += 1
                trajectory_length_delta[
                    len(trajectory) - expected_trajectory_length(row["duration_seconds"])
                ] += 1
                if player_networth_lead(row) is not None:
                    orientation_resolved += 1
            stats = row.get("stats") or {}
            kill_events = stats.get("kill_events")
            assist_events = stats.get("assist_events")
            if kill_events is not None:
                with_events += 1
            if history_row is not None and kill_events is not None:
                delta = len(kill_events) - history_row["kills"]
                kill_event_delta[max(-3, min(3, delta))] += 1
                event_agreement["kills_exact" if delta == 0 else "kills_differ"] += 1
            if history_row is not None and assist_events is not None:
                delta = len(assist_events) - history_row["assists"]
                assist_event_delta[max(-3, min(3, delta))] += 1
                event_agreement["assists_exact" if delta == 0 else "assists_differ"] += 1
        if entry is not None:
            entry["parsed_rows"] = len(rows)
            entry["parsed_product_rows"] = product_parsed
            entry["parsed_with_trajectory"] = with_trajectory
            entry["parsed_with_events"] = with_events

    def column(name: str, predicate: Any = None) -> list[float]:
        return [
            float(entry[name])
            for entry in per_player.values()
            if predicate is None or predicate(entry)
        ]

    discovery = lambda entry: entry["split"] == DISCOVERY  # noqa: E731
    candidate_test = lambda entry: entry["split"] == CANDIDATE_TEST  # noqa: E731
    has_parsed = lambda entry: entry["parsed_rows"] > 0  # noqa: E731

    parsed_bias = {}
    for context, counts in parsed_by_context.items():
        total = counts["available"] + counts["missing"]
        if total >= 500:
            parsed_bias[context] = {
                "rows": total,
                "parsed_share": round(counts["available"] / total, 4),
            }

    atlas: dict[str, Any] = {
        "schema_version": "v7-capability-atlas-1.0.0",
        "identities_included": False,
        "new_provider_calls": 0,
        "corpus_root": str(paths.root),
        "corpus_bindings": run_manifest["freeze"],
        "operation_registry": run_manifest["operation_registry"],
        "window": run_manifest["window"],
        "session_gap_seconds": SESSION_GAP_SECONDS,
        "denominators": {
            "source_frame_accounts": 4135,
            "frozen_cohort_accounts": 1200,
            "research_split_accounts": sum(history_split.values()),
            "accounts_by_split": dict(history_split),
            "parsed_accounts_by_split": dict(parsed_split),
            "history_rows": sum(entry["history_rows"] for entry in per_player.values()),
            "structurally_observable_rows": sum(
                entry["structurally_observable_rows"] for entry in per_player.values()
            ),
            "product_context_rows": sum(entry["product_rows"] for entry in per_player.values()),
            "standard_mode_rows": sum(entry["standard_rows"] for entry in per_player.values()),
            "turbo_rows": sum(entry["turbo_rows"] for entry in per_player.values()),
            "rows_with_role_context": sum(
                entry["rows_with_role_context"] for entry in per_player.values()
            ),
            "parsed_rows": parsed_rows_total,
            "accounts_with_no_product_context_row": sum(
                1 for entry in per_player.values() if entry["product_rows"] == 0
            ),
            "parsed_flagged_product_rows": sum(
                entry["parsed_flagged_product_rows"] for entry in per_player.values()
            ),
        },
        "row_coverage": {
            "game_mode_native": dict(mode_rows),
            "lobby_type_native": dict(lobby_rows),
            "leaver_status_native": dict(leaver_rows),
            "game_version_id": {str(key): value for key, value in patch_rows.items()},
            "position_native": dict(position_rows),
            "role_native": dict(role_rows),
            "lane_native": dict(lane_rows),
        },
        "duration_seconds_by_stratum": {
            stratum: describe([float(value) for value in values])
            for stratum, values in duration_by_stratum.items()
        },
        "per_player": {
            field: {
                "all": describe(column(field)),
                "discovery": describe(column(field, discovery)),
                "candidate_test": describe(column(field, candidate_test)),
            }
            for field in (
                "history_rows",
                "product_rows",
                "standard_rows",
                "turbo_rows",
                "rows_with_role_context",
                "sessions",
                "multi_match_sessions",
                "in_session_transitions",
                "in_session_losses_with_successor",
                "distinct_heroes",
                "distinct_positions",
                "active_days",
                "parsed_rows",
                "parsed_product_rows",
                "parsed_flagged_product_rows",
                "parsed_flagged_share_of_product",
            )
        },
        "per_player_thresholds": {
            "product_rows": share_at_least(column("product_rows"), (30, 50, 100, 200, 400)),
            "standard_rows": share_at_least(column("standard_rows"), (30, 50, 100, 200, 400)),
            "turbo_rows": share_at_least(column("turbo_rows"), (30, 50, 100, 200)),
            "rows_with_role_context": share_at_least(
                column("rows_with_role_context"), (30, 50, 100, 200, 400)
            ),
            "in_session_losses_with_successor": share_at_least(
                column("in_session_losses_with_successor"), (10, 20, 30, 50, 100)
            ),
            "multi_match_sessions": share_at_least(
                column("multi_match_sessions"), (10, 20, 30, 50)
            ),
            "parsed_product_rows_within_parsed_subset": share_at_least(
                column("parsed_product_rows", has_parsed), (30, 50, 100, 200, 400)
            ),
            "parsed_flagged_product_rows": share_at_least(
                column("parsed_flagged_product_rows"), (30, 50, 100, 200, 400)
            ),
        },
        "parsed_semantics": {
            "trajectory_rows": trajectory_rows,
            "orientation_resolved_rows": orientation_resolved,
            "length_minus_expected": {
                str(key): value for key, value in sorted(trajectory_length_delta.items())
            },
            "event_agreement": dict(event_agreement),
            "kill_event_minus_history_kills": {
                str(key): value for key, value in sorted(kill_event_delta.items())
            },
            "assist_event_minus_history_assists": {
                str(key): value for key, value in sorted(assist_event_delta.items())
            },
        },
        "parsed_availability_by_observable_context": dict(
            sorted(parsed_bias.items(), key=lambda item: -item[1]["rows"])[:60]
        ),
        "unavailable_by_construction": {
            "own_networth_trajectory": "not requested by GetParsedAcquisitionBatch v1.0.0",
            "own_last_hits_denies_trajectory": "not requested",
            "own_hero_damage_trajectory": "not requested",
            "own_death_events": "not requested",
            "playback_features": "prohibited surface",
            "rank_mmr_bracket_imp_behaviour": "prohibited surface",
        },
    }
    return atlas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", default=None)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    atlas = build_atlas(args.corpus_root)
    Path(args.out).write_text(json.dumps(atlas, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

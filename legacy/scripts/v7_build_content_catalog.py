#!/usr/bin/env python3
"""Emit the machine-readable V7 content catalog from the live registries.

The prose catalogs in ``legacy/docs/product/`` are written by hand and can drift from
the code. This file cannot: every dimension key, label, threshold, weight and
canonical copy string below is read from the module that owns it at build time,
so a rename or a re-weighting either shows up here or fails the test that
regenerates it.

Only mechanically grounded facts go in. Editorial judgement -- tone, share
safety, suggested affordances -- stays in the prose catalog, because inventing
a machine-readable home for a judgement call would give it a false authority.
The one exception is ``share_safe``, which is a hard rule rather than a taste
(a recommendation is never share-safe), so it is encoded.

Aggregate-only. No corpus read. No provider call.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "legacy" / "services" / "api"))
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))

from report_card.player_analysis_v7 import acquisition_policy as acq  # noqa: E402
from report_card.player_analysis_v7 import report_contract as contract  # noqa: E402
from report_card.player_analysis_v7.research import archetype, ranking, recommendation  # noqa: E402
from report_card.player_analysis_v7.research.owner_decisions import (  # noqa: E402
    DECISIONS,
    DECISIONS_VERSION,
    NEEDS_RESERVED_SPLIT,
    SEALED_VALIDATION_APPROVED,
)

CATALOG_VERSION = "v7-content-catalog-1.0.0"

#: Measured on DISCOVERY; the pipeline evidence is the source.
PIPELINE_EVIDENCE = REPO_ROOT / "legacy" / "docs" / "evidence" / "v7-finding-pipeline-2026-09-05.json"
RECOMMENDATION_EVIDENCE = (
    REPO_ROOT / "legacy" / "docs" / "evidence" / "v7-recommendation-selection-2026-09-06.json"
)
ARCHETYPE_EVIDENCE = REPO_ROOT / "legacy" / "docs" / "evidence" / "v7-archetype-axes-2026-09-06.json"

#: Human-readable concepts. The only hand-written map here, kept because a
#: dimension key is not a display string and the backend has nowhere else to
#: put one. Keys are validated against the live registries below, so a renamed
#: dimension fails the build rather than silently losing its concept.
DISPLAY_CONCEPT: dict[str, str] = {
    "vision_coverage": "How much of each match has one of your observer wards active?",
    "duration_tempo": "Whether your games run long or short",
    "death_clustering": "Dying again soon after you died",
    "lane_vs_jungle_share": "Farming the jungle versus the lane",
    "purchase_tempo": "How far into a game are you when you make your eighth purchase?",
    "deaths_alone_share": "How many of your deaths happen in minutes without team kill activity?",
    "spike_usage": "Using your item window",
    "position_flexibility": "Switching roles between games",
    "fight_timing_centroid": "When in a game you show up",
    "hero_novelty": "Trying heroes you have not played",
    "closer_vs_comeback": "Closing out leads versus coming back",
    "post_loss_session_continuation": "Playing on after a loss",
    "lead_retention": "Holding a lead",
    "post_loss_hero_switch": "Changing hero after a loss",
    "post_loss_requeue_latency": "After a loss, how long until your next recorded game?",
    "fight_conversion": "Turning won fights into towers",
    "last_hits_at_ten": "Last hits by minute 10",
    "first_real_item_time": "When your first real item lands",
    "first_ward_time": "When your first ward goes down",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finding_atoms() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pipeline = _load(PIPELINE_EVIDENCE)
    shipping: list[dict[str, Any]] = []
    withheld: list[dict[str, Any]] = []
    for key, row in sorted(pipeline["dimensions"].items()):
        tau = row.get("tau") or 0.0
        entry = {
            "id": key,
            "display_concept": DISPLAY_CONCEPT.get(key),
            "section": row.get("section"),
            "source_pass": row.get("source"),
            "measured_players": row.get("players"),
            "is_negative_control": bool(row.get("negative_control")),
        }
        if tau > 0.0:
            entry.update(
                {
                    "reliability_median": row["reliability"].get("p50"),
                    "tau": row.get("tau"),
                    "dependence_inflation": row.get("dependence_inflation"),
                    "dependence_curve_plateaued": row.get("dependence_curve_plateaued"),
                    "reliability_is_upper_bound": not row.get("dependence_curve_plateaued"),
                    "carries": [
                        "estimate",
                        "interval",
                        "reliability",
                        "score",
                        "direction",
                        "sample_size",
                    ],
                }
            )
            shipping.append(entry)
        else:
            entry["withheld_reason"] = (
                "negative control; must never be surfaced"
                if row.get("negative_control")
                else "tau collapsed to zero: no measurable between-player signal"
            )
            withheld.append(entry)
    shipping.sort(key=lambda row: -(row["reliability_median"] or 0.0))
    return shipping, withheld


def _recommendation_atoms() -> dict[str, Any]:
    evidence = _load(RECOMMENDATION_EVIDENCE)
    eligible = recommendation.eligible_dimensions()
    dimensions = []
    for key, dimension in recommendation.RECOMMENDATION_REGISTRY.items():
        measured = evidence["dimensions"].get(key, {})
        dimensions.append(
            {
                "id": key,
                "display_concept": DISPLAY_CONCEPT.get(key),
                "eligible": key in eligible,
                "actionability_weight": dimension.actionability,
                "higher_is_worse": dimension.higher_is_worse,
                "canonical_recommendation_text": dimension.recommendation,
                "canonical_verification_text": dimension.verification,
                "upstream_of_result": dimension.upstream,
                "outcome_contaminated": dimension.outcome_contaminated,
                "modal_sign_share": measured.get("modal_sign_share"),
                "dimension_scale": measured.get("dimension_scale"),
                "chosen_for_players": evidence["chosen_dimension_counts"].get(key, 0),
            }
        )
    dimensions.sort(key=lambda row: (not row["eligible"], -row["actionability_weight"]))
    return {
        "model_version": recommendation.RECOMMENDATION_VERSION,
        "exactly_one_ships": True,
        "runners_up_retained": 2,
        "minimum_matches_per_arm": recommendation.MIN_PER_ARM,
        "modal_sign_share_limit": recommendation.MODAL_SIGN_SHARE_LIMIT,
        "share_safe": False,
        "claims_causation": False,
        "carries": [
            "win_value",
            "loss_value",
            "gap",
            "direction",
            "reliability",
            "actionability_weight",
            "priority_score",
            "sample_wins",
            "sample_losses",
            "verification",
        ],
        "excluded_outcome_contaminated": recommendation.OUTCOME_CONTAMINATED_EXCLUSIONS,
        "excluded_downstream_of_result": recommendation.DOWNSTREAM_EXCLUSIONS,
        "dimensions": dimensions,
    }


def _archetype_atoms() -> dict[str, Any]:
    evidence = _load(ARCHETYPE_EVIDENCE)
    return {
        "model_version": archetype.ARCHETYPE_VERSION,
        "share_safe": True,
        "is_analytical": False,
        "refusal_has_no_default_label": True,
        "mode_strata": list(archetype.MODE_STRATA),
        "axes": {
            "tempo": {
                "levels": list(archetype.TEMPO_LEVELS),
                "cut": "population terciles within the dominant mode stratum",
                "copy_constraint": (
                    "relative tendency within the player's dominant mode, never a "
                    "large behavioural difference"
                ),
            },
            "fight_style": {
                "levels": list(archetype.FIGHT_STYLE_LEVELS),
                "cut": (
                    "ghost below the stratum participation tercile; otherwise "
                    "frontliner at or above the stratum median deaths per fight "
                    "minute, else opportunist"
                ),
                "copy_constraint": (
                    "'ghost' is a low-participation descriptor, not a judgement of "
                    "effort or skill"
                ),
            },
            "modifier": {
                "levels": list(archetype.MODIFIER_LEVELS),
                "cut": "absolute: session dispersion ratio above 1.0 is streaky",
                "copy_constraint": (
                    "the measure carries a small residual downward bias; values near "
                    "1.0 are genuinely ambiguous"
                ),
            },
        },
        "grid_labels": [
            {"tempo": t, "fight_style": f, "modifier": m, "label": label}
            for (t, f, m), label in sorted(
                archetype.GRID_LABELS.items(), key=lambda item: item[1]
            )
        ],
        "special_labels": [
            {
                "id": key,
                "label": label,
                "percentile_cut": archetype.SPECIAL_PERCENTILE,
                "provisional": True,
                "provisional_reason": (
                    "corpus-relative pilot value; refreshed from real pilot data, "
                    "not from a reserved split"
                ),
            }
            for key, label in sorted(archetype.SPECIAL_LABELS.items())
        ],
        "minimum_matches_in_stratum": archetype.MIN_MATCHES,
        "minimum_sessions": archetype.MIN_SESSIONS,
        "minimum_matches_per_session": archetype.MIN_SESSION_MATCHES,
        "measured_coverage": evidence["denominators"],
        "axis_without_support": evidence["axis_without_support"],
    }


def _refusal_matrix() -> list[dict[str, Any]]:
    return [
        {
            "capability": "dominant_mode",
            "reason": "no_dominant_mode_stratum",
            "condition": f"neither mode stratum reaches {archetype.MIN_MATCHES} matches",
            "cascades_to": ["archetype"],
            "fallback_permitted": False,
        },
        {
            "capability": "archetype",
            "reason": "insufficient_event_support",
            "condition": f"fewer than {archetype.MIN_MATCHES} matches in the dominant stratum",
            "cascades_to": [],
            "fallback_permitted": False,
        },
        {
            "capability": "archetype",
            "reason": "insufficient_sessions",
            "condition": (
                f"fewer than {archetype.MIN_SESSIONS} sessions of "
                f"{archetype.MIN_SESSION_MATCHES}+ matches"
            ),
            "cascades_to": [],
            "fallback_permitted": False,
        },
        {
            "capability": "recommendation",
            "reason": "insufficient_wins_or_losses_per_arm",
            "condition": (
                f"no eligible dimension has {recommendation.MIN_PER_ARM} wins and "
                f"{recommendation.MIN_PER_ARM} losses"
            ),
            "cascades_to": [],
            "fallback_permitted": False,
        },
        {
            "capability": "finding_slate",
            "reason": "fewer_than_floor_dimensions",
            "condition": f"fewer than {ranking.FINDING_FLOOR} dimensions qualify",
            "cascades_to": [],
            "fallback_permitted": False,
        },
        {
            "capability": "finding_slate",
            "reason": "no_valid_opportunities",
            "condition": "no dimension has enough support",
            "cascades_to": [],
            "fallback_permitted": False,
        },
        {
            "capability": "pass2_dependent_capabilities",
            "reason": "skipped_anonymous",
            "condition": "the account is anonymous or private",
            "cascades_to": ["archetype", "recommendation"],
            "fallback_permitted": False,
        },
        {
            "capability": "rank_display",
            "reason": "not_collected",
            "condition": "rank display disabled or unavailable",
            "cascades_to": [],
            "fallback_permitted": False,
        },
    ]


def build() -> dict[str, Any]:
    shipping, withheld = _finding_atoms()
    unknown = set(DISPLAY_CONCEPT) - (
        {row["id"] for row in shipping}
        | {row["id"] for row in withheld}
        | set(recommendation.RECOMMENDATION_REGISTRY)
    )
    if unknown:
        raise RuntimeError(
            f"DISPLAY_CONCEPT names dimensions no registry knows about: {sorted(unknown)}"
        )
    return {
        "schema_version": CATALOG_VERSION,
        "owner_decisions_version": DECISIONS_VERSION,
        "validation_status": "development",
        "production_certified": False,
        "sealed_validation_read": SEALED_VALIDATION_APPROVED,
        "decisions_needing_a_reserved_split": list(NEEDS_RESERVED_SPLIT),
        "owner_decisions": {
            key: {"choice": d.choice, "summary": d.summary, "provisional": d.provisional}
            for key, d in sorted(DECISIONS.items())
        },
        "findings": {
            "model_version": ranking.RANKING_MODEL_VERSION,
            "report_slots": ranking.REPORT_SLOTS,
            "finding_floor": ranking.FINDING_FLOOR,
            "score_line": ranking.SCORE_LINE,
            "sections": list(ranking.FINDING_SECTIONS),
            "strength_bands_exist": hasattr(contract, "StrengthBand"),
            "shipping_dimensions": shipping,
            "withheld_dimensions": withheld,
        },
        "recommendation": _recommendation_atoms(),
        "archetype": _archetype_atoms(),
        "acquisition": {
            "policy_version": acq.ACQUISITION_POLICY_VERSION,
            "full_depth_matches": acq.FULL_DEPTH_MATCHES,
            "paid_may_acquire_more_than_free": acq.PAID_MAY_ACQUIRE_MORE_THAN_FREE,
            "measured_requests_per_account": acq.MEASURED_REQUESTS_PER_ACCOUNT,
            "first_time_reports_per_day": acq.reports_per_day(),
            "stored_match_ttl_days": acq.STORED_MATCH_TTL_DAYS,
            "persistence_requirements": list(acq.PERSISTENCE_REQUIREMENTS),
            "persistence_wiring_implemented": False,
        },
        "refusal_states": _refusal_matrix(),
        "report_payload_producer_exists": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", default=str(REPO_ROOT / "legacy" / "docs" / "product" / "v7-content-catalog.json")
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the file on disk differs from a fresh build",
    )
    args = parser.parse_args()

    serialized = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    out = Path(args.out)
    if args.check:
        if not out.exists() or out.read_text(encoding="utf-8") != serialized:
            print(f"{out} is stale; regenerate with scripts/v7_build_content_catalog.py")
            return 1
        print("content catalog is current")
        return 0
    out.write_text(serialized, encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

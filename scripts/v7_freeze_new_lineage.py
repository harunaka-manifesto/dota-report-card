#!/usr/bin/env python3
"""Freeze the reviewed V7 new-lineage fit into runtime artifacts.

Inputs are aggregate DISCOVERY outputs produced by the existing Finding,
Recommendation, and Archetype pipelines. No corpus or provider is read here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services/api"))

from app.player_analysis_v7.context_projection import (  # noqa: E402
    CONTEXT_PROJECTION_SCHEMA_VERSION,
    FINDING_FACTOR_ORDER,
    RECOMMENDATION_FACTOR_ORDER,
    SHIPPING_FINDING_IDS,
    artifact_digest,
)
from app.player_analysis_v7.research.archetype import ARCHETYPE_VERSION  # noqa: E402
from app.player_analysis_v7.research.owner_decisions import DECISIONS_VERSION  # noqa: E402
from app.player_analysis_v7.research.ranking import RANKING_MODEL_VERSION  # noqa: E402
from app.player_analysis_v7.research.recommendation import RECOMMENDATION_VERSION  # noqa: E402

LINEAGE_ID = "v7-new-lineage-2026-09-08"
COMPATIBILITY_ID = "v7-new-lineage-2026-09-08-context-population-1"
CONTEXT_VERSION = "v7-context-projection-2.0.0+nl.20260908"
POPULATION_VERSION = "v7-population-parameters-2.0.0+nl.20260908"
POPULATION_SCHEMA = "v7-population-parameters-2.0.0"
SHIPPING = tuple(FINDING_FACTOR_ORDER)
WITHHELD = (
    "lane_recovery_participation",
    "lane_to_map",
    "transfer_activity",
    "transfer_risk",
)


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path}: expected a JSON object")
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signed(document: dict[str, Any]) -> dict[str, Any]:
    document["artifact_sha256"] = artifact_digest(document)
    return document


def write(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_tree(source_sha: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", f"{source_sha}^{{tree}}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def projection_dimension(key: str, row: dict[str, Any]) -> dict[str, Any]:
    projection = row["context_projection"]
    order = projection["factor_order"]
    expected = list(FINDING_FACTOR_ORDER[key])
    if order != expected:
        raise SystemExit(f"{key}: fitted factor order {order!r} != {expected!r}")
    factors = []
    coefficient_order: list[dict[str, str]] = []
    for factor in order:
        vocabulary = projection["categorical_vocabularies"][factor]
        coefficients = projection["coefficients"][factor]
        if set(vocabulary) != set(coefficients):
            raise SystemExit(f"{key}.{factor}: vocabulary/coefficient mismatch")
        coefficient_order.extend({"factor": factor, "level": level} for level in vocabulary)
        factors.append(
            {
                "name": factor,
                "categorical_vocabulary": vocabulary,
                "reference_level": None,
                "coefficients": coefficients,
                "unseen_level_behavior": {"strategy": "refuse"},
            }
        )
    return {
        "finding_id": key,
        "source_pass": "PASS2" if row["source"] == "pass2" else "PASS1_NEW_LINEAGE",
        "context_feature_schema": (
            "v7-pass2-observations-1.0.0"
            if row["source"] == "pass2"
            else "v7-luna-b-features-1.0.0"
        ),
        "factor_order": order,
        "coefficient_order": coefficient_order,
        "intercept": projection["intercept"],
        "factors": factors,
        "blocked_means": {"target_blocks": 20, "minimum_valid_blocks": 8, "minimum_per_block": 4},
        "validation": {
            "opportunities": row["opportunities"],
            "players": row["players"],
            "projection_drift": row["projection_drift"],
            "runtime_parity_tolerance": 1e-12,
        },
    }


def recommendation_projection(key: str, row: dict[str, Any]) -> dict[str, Any]:
    projection = row["context_projection"]
    if projection["factor_order"] != list(RECOMMENDATION_FACTOR_ORDER):
        raise SystemExit(f"{key}: Recommendation context factor order mismatch")
    factors = []
    coefficient_order: list[dict[str, str]] = []
    for factor in RECOMMENDATION_FACTOR_ORDER:
        vocabulary = projection["categorical_vocabularies"][factor]
        coefficients = projection["coefficients"][factor]
        coefficient_order.extend({"factor": factor, "level": level} for level in vocabulary)
        factors.append(
            {
                "name": factor,
                "categorical_vocabulary": vocabulary,
                "reference_level": None,
                "coefficients": coefficients,
                "unseen_level_behavior": {"strategy": "refuse"},
            }
        )
    return {
        "recommendation_id": key,
        "source_pass": "PASS2",
        "context_feature_schema": "v7-improvement-recommendation-1.0.0",
        "factor_order": list(RECOMMENDATION_FACTOR_ORDER),
        "coefficient_order": coefficient_order,
        "intercept": projection["intercept"],
        "factors": factors,
        "validation": {"opportunities": row["opportunities"], "players": row["players_with_a_gap"], "runtime_parity_tolerance": 1e-12},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finding", type=Path, required=True)
    parser.add_argument("--recommendation", type=Path, required=True)
    parser.add_argument("--archetype", type=Path, required=True)
    parser.add_argument("--pass1-manifest", type=Path, required=True)
    parser.add_argument("--pass1-state", type=Path, required=True)
    parser.add_argument("--pass1-canonical-tree-sha256", required=True)
    parser.add_argument("--parsed-overlay-manifest", type=Path, required=True)
    parser.add_argument("--pass2-manifest", type=Path, required=True)
    parser.add_argument("--pass2-state", type=Path, required=True)
    parser.add_argument("--pass2-hash-manifest", type=Path, required=True)
    parser.add_argument("--source-code-sha", required=True)
    parser.add_argument("--context-out", type=Path, required=True)
    parser.add_argument("--population-out", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()

    finding = read(args.finding)
    recommendation = read(args.recommendation)
    archetype = read(args.archetype)
    overlay = read(args.parsed_overlay_manifest)
    if set(SHIPPING) != SHIPPING_FINDING_IDS:
        raise SystemExit("shipping Finding registry mismatch")
    if finding.get("split") != "DISCOVERY" or recommendation.get("split") != "DISCOVERY" or archetype.get("split") != "DISCOVERY":
        raise SystemExit("every fit input must be DISCOVERY")

    evidence_dir = args.evidence_dir.resolve()
    evidence_paths = {
        "finding_fit": evidence_dir / "v7-new-lineage-finding-fit-2026-09-08.json",
        "recommendation_fit": evidence_dir / "v7-new-lineage-recommendation-fit-2026-09-08.json",
        "archetype_fit": evidence_dir / "v7-new-lineage-archetype-fit-2026-09-08.json",
    }
    for name, source in (
        ("finding_fit", args.finding),
        ("recommendation_fit", args.recommendation),
        ("archetype_fit", args.archetype),
    ):
        write(evidence_paths[name], read(source))

    source_digests = {
        "pass1_complete_manifest_sha256": sha(args.pass1_manifest),
        "pass1_state_sha256": sha(args.pass1_state),
        "pass1_canonical_tree_sha256": args.pass1_canonical_tree_sha256,
        "pass1_parsed_overlay_manifest_sha256": sha(args.parsed_overlay_manifest),
        "pass1_parsed_normalized_tree_sha256": overlay["source_normalized_tree_sha256"],
        "pass2_run_manifest_sha256": sha(args.pass2_manifest),
        "pass2_state_sha256": sha(args.pass2_state),
        "pass2_hash_manifest_sha256": sha(args.pass2_hash_manifest),
        "source_tree_sha256": git_tree(args.source_code_sha),
    }
    context = signed(
        {
            "schema_version": CONTEXT_PROJECTION_SCHEMA_VERSION,
            "artifact_version": CONTEXT_VERSION,
            "analytical_lineage_id": LINEAGE_ID,
            "population_compatibility_id": COMPATIBILITY_ID,
            "feature_schema_version": "v7-finding-context-features-2.0.0",
            "source_code_sha": args.source_code_sha,
            "estimator": {
                "algorithm": "finite-sweep-additive-categorical-gauss-seidel",
                "version": "v7-luna-b-screen-1.0.0",
                "sweeps": 10,
                "weighting": "equal_per_opportunity",
                "interactions": [],
                "player_factor": False,
                "reference_policy": "none_finite_sweep_parameterization",
            },
            "source_digests": source_digests,
            "protected_splits": {"CANDIDATE_TEST": "NOT_READ", "CALIBRATION_RESERVED": "NOT_READ", "SEALED_VALIDATION": "NOT_READ"},
            "provider_calls": {"fit_phase_stratz_calls": 0, "fit_phase_opendota_calls": 0},
            "dimensions": {
                key: projection_dimension(key, finding["dimensions"][key]) for key in SHIPPING
            },
            "recommendation_dimensions": {
                key: recommendation_projection(key, row)
                for key, row in recommendation["dimensions"].items()
            },
        }
    )
    write(args.context_out, context)

    finding_dimensions = {}
    for key, row in finding["dimensions"].items():
        ships = key in SHIPPING
        if ships and (not row["tau"] or row["tau"] <= 0):
            raise SystemExit(f"{key}: shipping dimension has no between-player spread")
        finding_dimensions[key] = {
            "mu": row["mu"],
            "tau": row["tau"],
            "dependence_inflation": row["dependence_inflation"],
            "dependence_batch_length": row["dependence_batch_length"],
            "dependence_curve_plateaued": row["dependence_curve_plateaued"],
            "reliability_is_upper_bound": not row["dependence_curve_plateaued"],
            "section": row["section"],
            "source_pass": "PASS2" if row["source"] == "pass2" else "PASS1_NEW_LINEAGE",
            "players_fitted": row["players"],
            "ships": ships,
            "status": "shipping" if ships else "withheld",
            "negative_control": key == "side_sensitivity",
            "derivation_method": "NEW_LINEAGE_REFIT_FROM_DISCOVERY",
            "source_evidence_document": str(evidence_paths["finding_fit"].relative_to(REPO_ROOT)),
            "source_evidence_sha256": sha(evidence_paths["finding_fit"]),
            "source_analytical_version": finding["ranking_model_version"],
            "source_reproducible": True,
            "source_reproducibility_note": "Bound to the completed new-lineage history, DISCOVERY-only surviving parsed overlay, and intact Pass-2 sources.",
        }
        if not ships:
            finding_dimensions[key]["withheld_reason"] = (
                "negative control; deliberate placebo"
                if key == "side_sensitivity"
                else "withheld candidate"
            )
    recommendation_dimensions = {}
    for key, row in recommendation["dimensions"].items():
        recommendation_dimensions[key] = {
            "dimension_scale": row["dimension_scale"],
            "dependence_inflation": row["dependence_inflation"],
            "modal_sign_share": row["modal_sign_share"],
            "eligible": row["eligible"],
            "outcome_contaminated": row["outcome_contaminated"],
            "status": "eligible" if row["eligible"] else "excluded",
            "derivation_method": "NEW_LINEAGE_REFIT_FROM_DISCOVERY",
            "source_evidence_document": str(evidence_paths["recommendation_fit"].relative_to(REPO_ROOT)),
            "source_evidence_sha256": sha(evidence_paths["recommendation_fit"]),
            "source_analytical_version": recommendation["recommendation_version"],
        }
    population = signed(
        {
            "schema_version": POPULATION_SCHEMA,
            "artifact_version": POPULATION_VERSION,
            "analytical_lineage_id": LINEAGE_ID,
            "population_compatibility_id": COMPATIBILITY_ID,
            "context_projection_version": CONTEXT_VERSION,
            "context_projection_sha256": context["artifact_sha256"],
            "fitted_on_split": "DISCOVERY",
            "derivation_method": "NEW_LINEAGE_REFIT_FROM_DISCOVERY",
            "refit_from_source_corpus": True,
            "validation_status": "development",
            "source_code_sha": args.source_code_sha,
            "source_digests": source_digests,
            "source_evidence": {
                name: {"path": str(path.relative_to(REPO_ROOT)), "sha256": sha(path)}
                for name, path in evidence_paths.items()
            },
            "model_versions": {
                "ranking": RANKING_MODEL_VERSION,
                "recommendation": RECOMMENDATION_VERSION,
                "archetype": ARCHETYPE_VERSION,
                "owner_decisions": DECISIONS_VERSION,
            },
            "denominators": {
                "pass1_discovery_players": finding["denominators"]["pass1_discovery_players"],
                "pass1_parsed_overlay_players": overlay["canonical_documents"],
                "pass2_discovery_players": finding["denominators"]["pass2_discovery_players"],
                "players_with_any_finding": finding["denominators"]["players_with_any_finding"],
                "recommendation_players": recommendation["denominators"]["players_with_at_least_one_candidate"],
                "archetype_joinable_players": archetype["denominators"]["joinable_players"],
            },
            "finding_dimensions": finding_dimensions,
            "withheld_dimensions": list(WITHHELD),
            "negative_control": {
                "id": "side_sensitivity",
                "tau": finding["dimensions"]["side_sensitivity"]["tau"],
                "status": "silent",
            },
            "recommendation_dimensions": recommendation_dimensions,
            "archetype_cuts": archetype["population_cuts_by_stratum"],
            "protected_splits": {"CANDIDATE_TEST": "NOT_READ", "CALIBRATION_RESERVED": "NOT_READ", "SEALED_VALIDATION": "NOT_READ"},
            "provider_calls": {"fit_phase_stratz_calls": 0, "fit_phase_opendota_calls": 0},
        }
    )
    write(args.population_out, population)
    print(f"context {context['artifact_sha256']}")
    print(f"population {population['artifact_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

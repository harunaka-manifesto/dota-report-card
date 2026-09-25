"""Synthetic-only checks for the frozen runtime context projection."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from report_card.player_analysis_v7.context_projection import (
    COMPATIBLE_POPULATION_SCHEMA_VERSION,
    CONTEXT_PROJECTION_SCHEMA_VERSION,
    FINDING_FACTOR_ORDER,
    RECOMMENDATION_FACTOR_ORDER,
    RECOMMENDATION_IDS,
    ContextProjectionError,
    UnsupportedContextLevel,
    artifact_digest,
    assert_population_compatible,
    load_context_projection,
    parse_context_projection,
    project_series,
)
from report_card.player_analysis_v7.research.features import Opportunity
from report_card.player_analysis_v7.research.screen import encode, fit_context_projection


def _factor(name: str, levels: list[str] | None = None) -> dict[str, object]:
    vocabulary = levels or ["KNOWN"]
    return {
        "name": name,
        "categorical_vocabulary": vocabulary,
        "reference_level": None,
        "coefficients": {level: 0.0 for level in vocabulary},
        "unseen_level_behavior": {"strategy": "refuse"},
    }


def _document() -> dict[str, object]:
    dimensions = {}
    for finding_id, names in FINDING_FACTOR_ORDER.items():
        factors = [
            _factor(name, ["ahead", "behind"] if name == "__arm__" else None)
            for name in names
        ]
        dimensions[finding_id] = {
            "finding_id": finding_id,
            "source_pass": "PASS2" if finding_id in {
                "vision_coverage",
                "death_clustering",
                "lane_vs_jungle_share",
                "deaths_alone_share",
                "spike_usage",
                "closer_vs_comeback",
                "fight_conversion",
            } else "PASS1_HISTORY_NEW_LINEAGE",
            "context_feature_schema": f"synthetic-{finding_id}-1",
            "factor_order": list(names),
            "coefficient_order": [
                {"factor": factor["name"], "level": level}
                for factor in factors
                for level in factor["categorical_vocabulary"]
            ],
            "intercept": 0.0,
            "factors": factors,
        }
    recommendations = {}
    for key in RECOMMENDATION_IDS:
        factors = [_factor(name) for name in RECOMMENDATION_FACTOR_ORDER]
        recommendations[key] = {
            "recommendation_id": key,
            "source_pass": "PASS2",
            "context_feature_schema": "synthetic-recommendation-1",
            "factor_order": list(RECOMMENDATION_FACTOR_ORDER),
            "coefficient_order": [
                {"factor": factor["name"], "level": level}
                for factor in factors
                for level in factor["categorical_vocabulary"]
            ],
            "intercept": 0.0,
            "factors": factors,
        }
    document: dict[str, object] = {
        "schema_version": CONTEXT_PROJECTION_SCHEMA_VERSION,
        "artifact_version": "v7-context-projection-synthetic-test",
        "analytical_lineage_id": "v7-new-lineage-synthetic-test",
        "population_compatibility_id": "v7-population-synthetic-test",
        "feature_schema_version": "v7-synthetic-features",
        "estimator": {
            "algorithm": "finite-sweep-additive-categorical-gauss-seidel",
            "version": "v7-luna-b-screen-1.0.0",
            "sweeps": 10,
            "weighting": "equal_per_opportunity",
            "interactions": [],
            "player_factor": False,
            "reference_policy": "none_finite_sweep_parameterization",
        },
        "source_digests": {
            "pass1_complete_manifest_sha256": "1" * 64,
            "pass1_state_sha256": "2" * 64,
            "pass1_canonical_tree_sha256": "3" * 64,
            "pass1_parsed_overlay_manifest_sha256": "6" * 64,
            "pass2_run_manifest_sha256": "4" * 64,
            "source_tree_sha256": "5" * 64,
        },
        "dimensions": dimensions,
        "recommendation_dimensions": recommendations,
    }
    document["artifact_sha256"] = artifact_digest(document)
    return document


def _resign(document: dict[str, object]) -> None:
    document["artifact_sha256"] = artifact_digest(document)


def test_schema_and_all_sixteen_finding_contracts_validate() -> None:
    artifact = parse_context_projection(_document())
    assert set(artifact.dimensions) == set(FINDING_FACTOR_ORDER)
    assert "fit" not in __import__(
        "report_card.player_analysis_v7.context_projection", fromlist=["__all__"]
    ).__all__


def test_missing_artifact_refuses(tmp_path: Path) -> None:
    with pytest.raises(ContextProjectionError, match="frozen context projection missing"):
        load_context_projection(tmp_path / "absent.json")


def test_digest_and_version_mismatches_refuse() -> None:
    changed = _document()
    changed["artifact_version"] = "tampered"
    with pytest.raises(ContextProjectionError, match="digest mismatch"):
        parse_context_projection(changed)

    wrong_version = _document()
    wrong_version["schema_version"] = "v7-context-projection-wrong"
    _resign(wrong_version)
    with pytest.raises(ContextProjectionError, match="projection schema"):
        parse_context_projection(wrong_version)


def test_non_finite_coefficient_and_wrong_factor_order_refuse() -> None:
    non_finite = _document()
    row = non_finite["dimensions"]["vision_coverage"]  # type: ignore[index]
    row["factors"][0]["coefficients"]["KNOWN"] = float("nan")  # type: ignore[index]
    with pytest.raises(ContextProjectionError, match="canonical JSON"):
        parse_context_projection(non_finite)

    wrong_order = _document()
    row = wrong_order["dimensions"]["vision_coverage"]  # type: ignore[index]
    row["factor_order"] = list(reversed(row["factor_order"]))  # type: ignore[index]
    _resign(wrong_order)
    with pytest.raises(ContextProjectionError, match="factor_order"):
        parse_context_projection(wrong_order)


def test_unseen_level_refuses_unless_artifact_names_a_fitted_fallback() -> None:
    refusing = parse_context_projection(_document()).finding("vision_coverage")
    context = {name: "KNOWN" for name in FINDING_FACTOR_ORDER["vision_coverage"]}
    context["mode"] = "UNSEEN"
    with pytest.raises(UnsupportedContextLevel, match="unsupported level"):
        refusing.residual(3.0, context)
    with pytest.raises(ContextProjectionError, match="unsupported context factor"):
        refusing.residual(3.0, context | {"role": "CORE"})

    fallback_document = _document()
    row = fallback_document["dimensions"]["vision_coverage"]  # type: ignore[index]
    factor = row["factors"][0]  # type: ignore[index]
    factor["categorical_vocabulary"] = ["KNOWN", "__other__"]
    factor["coefficients"] = {"KNOWN": 0.0, "__other__": 0.25}
    factor["unseen_level_behavior"] = {"strategy": "map_to_level", "level": "__other__"}
    row["coefficient_order"].insert(1, {"factor": "mode", "level": "__other__"})  # type: ignore[index]
    _resign(fallback_document)
    fallback = parse_context_projection(fallback_document).finding("vision_coverage")
    assert fallback.residual(3.0, context) == pytest.approx(2.75)


def test_research_fit_and_runtime_projection_are_numerically_identical() -> None:
    contexts = [
        (("mode", "STANDARD"), ("patch", "A"), ("hero", "1"), ("duration", "D0"),
         ("side", "R"), ("lobby", "RANKED"), ("position", "P1"), ("lane", "MID")),
        (("mode", "TURBO"), ("patch", "A"), ("hero", "2"), ("duration", "D1"),
         ("side", "D"), ("lobby", "RANKED"), ("position", "P2"), ("lane", "SAFE")),
        (("mode", "STANDARD"), ("patch", "B"), ("hero", "2"), ("duration", "D1"),
         ("side", "D"), ("lobby", "NORMAL"), ("position", "P1"), ("lane", "SAFE")),
        (("mode", "TURBO"), ("patch", "B"), ("hero", "1"), ("duration", "D0"),
         ("side", "R"), ("lobby", "NORMAL"), ("position", "P2"), ("lane", "MID")),
    ]
    values = [1.0, 2.0, 4.5, 8.0]
    encoded = encode(
        [
            (
                "p1",
                [
                    Opportunity(value, context)
                    for value, context in zip(values, contexts, strict=True)
                ],
            )
        ],
        include_arm_as_factor=False,
    )
    fit = fit_context_projection(encoded)
    document = _document()
    row = document["dimensions"]["vision_coverage"]  # type: ignore[index]
    factors = []
    for name, levels, coefficients in zip(
        encoded.factors, encoded.level_names, fit.coefficients, strict=True
    ):
        factor = _factor(name, levels)
        factor["coefficients"] = dict(zip(levels, coefficients, strict=True))
        factors.append(factor)
    row["intercept"] = fit.intercept
    row["factors"] = factors
    row["coefficient_order"] = [
        {"factor": factor["name"], "level": level}
        for factor in factors
        for level in factor["categorical_vocabulary"]
    ]
    _resign(document)
    artifact = parse_context_projection(document)
    runtime = project_series(
        artifact,
        "vision_coverage",
        [
            (value, dict(context), None)
            for value, context in zip(values, contexts, strict=True)
        ],
    )
    assert runtime == pytest.approx(fit.residual, abs=1e-12)


def test_population_binding_and_capability_provenance_fail_closed() -> None:
    artifact = parse_context_projection(_document())
    compatible = {
        "schema_version": COMPATIBLE_POPULATION_SCHEMA_VERSION,
        "analytical_lineage_id": artifact.analytical_lineage_id,
        "context_projection_sha256": artifact.artifact_sha256,
        "population_compatibility_id": artifact.population_compatibility_id,
    }
    assert_population_compatible(artifact, compatible)
    incompatible = deepcopy(compatible)
    incompatible["context_projection_sha256"] = "0" * 64
    with pytest.raises(ContextProjectionError, match="incompatible population"):
        assert_population_compatible(artifact, incompatible)

    provenance = artifact.provenance()
    expected_provenance = dict(compatible)
    expected_provenance.pop("schema_version")
    assert provenance == expected_provenance | {
        "context_projection_version": artifact.artifact_version
    }
    assert "coefficients" not in provenance

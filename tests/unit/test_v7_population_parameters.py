"""The frozen population parameters, and that they fail closed.

A runtime request has one player and cannot fit a population, so these
parameters are the only thing standing between a Finding and a number invented
from a single sample. The tests that matter are the ones proving the loader
refuses rather than defaults.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.player_analysis_v7.population import (
    ARCHETYPE_CUT_KEYS,
    POPULATION_PARAMETERS_PATH,
    POPULATION_PARAMETERS_VERSION,
    PopulationParametersError,
    load_population_parameters,
)
from app.player_analysis_v7.research.archetype import MODE_STRATA
from app.player_analysis_v7.research.recommendation import RECOMMENDATION_REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_EVIDENCE = REPO_ROOT / "docs" / "evidence" / "v7-finding-pipeline-2026-09-05.json"
ARCHETYPE_EVIDENCE = REPO_ROOT / "docs" / "evidence" / "v7-archetype-axes-2026-09-06.json"
RECOMMENDATION_EVIDENCE = (
    REPO_ROOT / "docs" / "evidence" / "v7-recommendation-selection-2026-09-06.json"
)


def params():
    return load_population_parameters()


def test_the_artifact_is_committed_and_parses() -> None:
    assert POPULATION_PARAMETERS_PATH.is_file()
    assert params().schema_version == POPULATION_PARAMETERS_VERSION


def test_sixteen_dimensions_ship_and_five_are_withheld() -> None:
    p = params()
    assert len(p.shipping_dimensions) == 16
    assert len(p.withheld_dimensions) == 5


def test_every_shipping_dimension_has_a_positive_tau() -> None:
    p = params()
    for key in p.shipping_dimensions:
        assert p.finding(key).tau > 0.0, key


def test_every_withheld_dimension_has_tau_zero_and_a_reason() -> None:
    p = params()
    for key in p.withheld_dimensions:
        row = p.finding(key)
        assert row.tau == 0.0
        assert row.withheld_reason


def test_the_negative_control_is_marked_and_withheld() -> None:
    row = params().finding("side_sensitivity")
    assert row.negative_control is True
    assert row.ships is False
    assert "placebo" in (row.withheld_reason or "")


def test_no_shipping_dimension_is_the_negative_control() -> None:
    p = params()
    assert all(not p.finding(k).negative_control for k in p.shipping_dimensions)


def test_every_recommendation_dimension_has_a_positive_scale() -> None:
    p = params()
    assert set(p.recommendations) == set(RECOMMENDATION_REGISTRY)
    for key in p.recommendations:
        assert p.recommendation(key).dimension_scale > 0.0, key


def test_seven_recommendation_dimensions_are_eligible() -> None:
    p = params()
    assert sum(1 for r in p.recommendations.values() if r.eligible) == 7


def test_both_strata_carry_every_archetype_cut() -> None:
    p = params()
    for stratum in MODE_STRATA:
        cuts = p.cuts_for(stratum)
        assert set(cuts) == set(ARCHETYPE_CUT_KEYS)


def test_the_strata_cuts_actually_differ() -> None:
    """If they matched, the mode stratification would be doing nothing and the
    axes would be measuring the queue rather than the player."""

    p = params()
    standard = p.cuts_for("STANDARD")
    turbo = p.cuts_for("TURBO")
    assert standard != turbo
    assert standard["participation_low"] != turbo["participation_low"]


# --------------------------------------------------------------------------
# fail-closed behaviour
# --------------------------------------------------------------------------


def test_an_unknown_dimension_raises_rather_than_defaulting() -> None:
    with pytest.raises(PopulationParametersError):
        params().finding("not_a_dimension")


def test_an_unknown_recommendation_dimension_raises() -> None:
    with pytest.raises(PopulationParametersError):
        params().recommendation("not_a_dimension")


def test_the_unknown_mode_stratum_is_not_a_population() -> None:
    with pytest.raises(PopulationParametersError):
        params().cuts_for("UNKNOWN")


def test_a_missing_artifact_raises_a_clear_error(tmp_path) -> None:
    with pytest.raises(PopulationParametersError, match="cannot rank"):
        load_population_parameters.__wrapped__(tmp_path / "absent.json")


def test_malformed_json_raises(tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(PopulationParametersError, match="not valid JSON"):
        load_population_parameters.__wrapped__(bad)


def test_a_stratum_missing_a_cut_is_rejected(tmp_path) -> None:
    document = json.loads(POPULATION_PARAMETERS_PATH.read_text(encoding="utf-8"))
    document["archetype_cuts"]["TURBO"].pop("tempo_low")
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(PopulationParametersError, match="missing cuts"):
        load_population_parameters.__wrapped__(broken)


# --------------------------------------------------------------------------
# agreement with the published evidence
# --------------------------------------------------------------------------


def test_finding_parameters_match_the_published_evidence() -> None:
    evidence = json.loads(PIPELINE_EVIDENCE.read_text(encoding="utf-8"))["dimensions"]
    p = params()
    for key, row in evidence.items():
        frozen = p.finding(key)
        assert frozen.tau == row["tau"], key
        assert frozen.mu == row["mu"], key
        assert frozen.dependence_inflation == row["dependence_inflation"], key


def test_recommendation_scales_match_the_published_evidence() -> None:
    evidence = json.loads(RECOMMENDATION_EVIDENCE.read_text(encoding="utf-8"))["dimensions"]
    p = params()
    for key, row in evidence.items():
        assert p.recommendation(key).dimension_scale == row["dimension_scale"], key
        assert p.recommendation(key).modal_sign_share == row["modal_sign_share"], key


def test_archetype_cuts_match_the_published_evidence() -> None:
    evidence = json.loads(ARCHETYPE_EVIDENCE.read_text(encoding="utf-8"))
    published = evidence["population_cuts_by_stratum"]
    p = params()
    for stratum in MODE_STRATA:
        for name in ARCHETYPE_CUT_KEYS:
            assert p.cuts_for(stratum)[name] == published[stratum][name], (stratum, name)


def test_the_artifact_declares_itself_uncertified() -> None:
    p = params()
    assert p.validation_status == "development"
    assert p.fitted_on_split == "DISCOVERY"


def test_the_artifact_records_its_source_evidence_digests() -> None:
    """A parameter must be traceable to the evidence that established it."""

    import hashlib

    p = params()
    for entry in p.source_evidence.values():
        path = REPO_ROOT / entry["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]


def test_the_artifact_contains_no_corpus_identifiers() -> None:
    assert "v7p_" not in POPULATION_PARAMETERS_PATH.read_text(encoding="utf-8")

from __future__ import annotations

import math
from typing import Any

import pytest
from app.player_analysis_v7 import runtime
from app.player_analysis_v7.context_projection import (
    ContextProjectionError,
    load_context_projection,
)
from app.player_analysis_v7.population import load_population_parameters
from app.player_analysis_v7.research import inference, recommendation, screen
from app.player_analysis_v7.research.features import Opportunity
from app.player_analysis_v7.research.pass2_observations import OBSERVATION_REGISTRY
from app.player_analysis_v7.research.registry import FAMILY_BY_NAME
from app.player_analysis_v7.runtime import _estimate, _recommendation, parsed_rows


def _series(key: str, *, recommendation_projection: bool = False) -> tuple[list[Opportunity], str | None, str | None]:
    artifact = load_context_projection()
    projection = (
        artifact.recommendation(key) if recommendation_projection else artifact.finding(key)
    )
    source = OBSERVATION_REGISTRY.get(key) or FAMILY_BY_NAME.get(key)
    treated = recommendation.ARM_LOSS if recommendation_projection else source.treated
    control = recommendation.ARM_WIN if recommendation_projection else source.control
    context = tuple(
        (factor.name, factor.vocabulary[0])
        for factor in projection.factors
        if factor.name != "__arm__"
    )
    rows = [
        Opportunity(float(index % 7), context, treated if index % 2 else control)
        for index in range(80)
    ]
    return rows, treated, control


def _warded_row(match_id: int, *, won: bool) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "game_mode_native": "ALL_PICK_RANKED",
        "game_version_id": 180,
        "self": {
            "is_victory": won,
            "hero_id": 86,
            "position_native": "POSITION_2",
            "role_native": "CORE",
            "lane_native": "MID_LANE",
            "is_radiant": True,
            "events": {"wards": [{"time": 0 if won else 300, "type": 0}]},
        },
    }


def test_every_finding_runtime_projection_matches_direct_frozen_math(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        screen,
        "fit_context_projection",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("runtime fit")),
    )
    artifact = load_context_projection()
    for key in sorted(artifact.dimensions):
        rows, treated, control = _series(key)
        projection = artifact.finding(key)
        residuals = [projection.residual(row.value, dict(row.ctx), row.arm) for row in rows]
        actual = _estimate(key, rows, treated=treated, control=control)
        arms = [1 if row.arm == treated else 0 for row in rows]
        expected = inference.player_inference(
            "runtime_player",
            residuals,
            arms if treated is not None else None,
            1 if treated is not None else None,
            0 if treated is not None else None,
        )
        assert actual is not None and expected is not None
        assert math.isclose(actual.delta, expected.delta, abs_tol=1e-12)
        assert math.isclose(actual.standard_error, expected.standard_error, abs_tol=1e-12)


def test_unseen_player_context_refuses_only_that_dimension() -> None:
    rows, treated, control = _series("vision_coverage")
    unknown = rows[0]
    unknown_context = tuple(
        (name, "NEW_PATCH") if name == "patch" else (name, value)
        for name, value in unknown.ctx
    )

    assert (
        _estimate(
            "vision_coverage",
            [Opportunity(unknown.value, unknown_context, unknown.arm)],
            treated=treated,
            control=control,
        )
        is None
    )
    assert _estimate("vision_coverage", rows, treated=treated, control=control) is not None


def test_frozen_artifact_failures_remain_fatal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runtime,
        "load_context_projection",
        lambda: (_ for _ in ()).throw(ContextProjectionError("artifact invalid")),
    )
    with pytest.raises(ContextProjectionError, match="artifact invalid"):
        _estimate("vision_coverage", [], treated=None, control=None)


def test_every_eligible_recommendation_uses_its_frozen_projection() -> None:
    artifact = load_context_projection()
    for key in sorted(recommendation.eligible_dimensions()):
        rows, treated, control = _series(key, recommendation_projection=True)
        assert _estimate(
            key,
            rows,
            treated=treated,
            control=control,
            recommendation_projection=True,
        ) is not None
        assert artifact.recommendation(key).finding_id == key


def test_recommendation_requires_effective_support_after_block_exclusion() -> None:
    rows: list[dict[str, Any]] = []
    for index in range(8):
        rows.extend(
            [
                _warded_row(index * 4, won=True),
                _warded_row(index * 4 + 1, won=False),
                _warded_row(index * 4 + 2, won=False),
                _warded_row(index * 4 + 3, won=False),
            ]
        )
    rows.extend(_warded_row(32 + index, won=True) for index in range(48))

    series = recommendation.opportunities(
        rows, recommendation.RECOMMENDATION_REGISTRY["first_ward_time"]
    )
    result = _estimate(
        "first_ward_time",
        series,
        treated=recommendation.ARM_LOSS,
        control=recommendation.ARM_WIN,
        recommendation_projection=True,
    )

    assert recommendation.has_denominator(series)
    assert result is not None
    assert (result.n_control, result.n_treated) == (8, 24)
    assert _recommendation(rows, load_population_parameters()) is None


def test_pass2_rows_adapt_to_pass1_parsed_feature_shape() -> None:
    rows = parsed_rows(
        [
            {
                "match_id": 7,
                "radiant_networth_leads": [0, 1],
                "self": {
                    "hero_id": 2,
                    "is_radiant": True,
                    "is_victory": False,
                    "position_native": "POSITION_5",
                    "role_native": "HARD_SUPPORT",
                    "lane_native": "SAFE_LANE",
                    "events": {
                        "kill_events": [{"time": 30}],
                        "assist_events": [{"time": 45}],
                        "item_purchases": [{"time": 60}],
                    },
                },
            }
        ]
    )
    assert rows[7]["stats"] == {
        "kill_events": [{"time": 30}],
        "assist_events": [{"time": 45}],
        "item_purchases": [{"time": 60}],
    }
    assert rows[7]["position_native"] == "POSITION_5"

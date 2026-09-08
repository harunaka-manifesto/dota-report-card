from __future__ import annotations

import math

import pytest
from app.player_analysis_v7.context_projection import load_context_projection
from app.player_analysis_v7.research import inference, recommendation, screen
from app.player_analysis_v7.research.features import Opportunity
from app.player_analysis_v7.research.pass2_observations import OBSERVATION_REGISTRY
from app.player_analysis_v7.research.registry import FAMILY_BY_NAME
from app.player_analysis_v7.runtime import _estimate, parsed_rows


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

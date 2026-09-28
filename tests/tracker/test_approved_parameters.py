from app.tracker.context import METRIC_CLASS
from app.tracker.metrics import METRICS
from app.tracker.population_parameters import current_context_parameters
from app.tracker.schema import parameter_sets
from sqlalchemy import select


def test_upgrade_registers_the_owner_approved_parameter_set(migrated_database) -> None:
    with migrated_database.connect() as connection:
        rows = connection.execute(select(parameter_sets)).mappings().all()
        parameters = current_context_parameters(connection)
    assert [(row["version"], row["status"]) for row in rows] == [("context-2026-09-v1", "APPROVED")]
    assert rows[0]["digest"] == rows[0]["parameters"]["sha256"]
    assert parameters is not None and parameters.version == "context-2026-09-v1"
    assert set(parameters.metrics) == METRICS
    assert parameters.cs_slope_regression_passed and parameters.opponent_coverage >= 0.97
    # Hero levels exist for every class-B* metric, so paired hero terms can apply.
    for metric in (metric for metric, cls in METRIC_CLASS.items() if cls == "B*"):
        assert any(key[2] == metric for key in parameters.hero_levels)

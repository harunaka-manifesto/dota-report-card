from __future__ import annotations

from app.findings.conflicts import select_story_findings
from app.findings.evaluator import evaluate_free_findings
from free_finding_helpers import make_context


def test_story_selection_is_replayable_and_references_only_published_findings() -> None:
    candidates = evaluate_free_findings(make_context())
    first = select_story_findings(candidates)
    second = select_story_findings(candidates)

    assert first == second
    published_keys = {item.key for item in candidates}
    assert set(first.ordered_finding_keys) <= published_keys
    if first.experiment_key is not None:
        experiment_keys = {
            item.experiment.key
            for item in candidates
            if item.experiment is not None
        }
        assert first.experiment_key in experiment_keys

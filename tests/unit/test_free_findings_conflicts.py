from __future__ import annotations

from app.findings.conflicts import select_story_findings
from app.findings.models import FindingCandidate, FindingExperiment


def _candidate(
    key: str,
    kind: str,
    priority: float,
    *,
    confidence: float = 0.9,
    tags: frozenset[str] = frozenset(),
    experiment_key: str | None = None,
) -> FindingCandidate:
    experiment = (
        FindingExperiment(
            key=experiment_key,
            title="Test experiment",
            instruction="Try one observable change.",
            hypothesis="The pattern may move.",
            measurement="Record the next result.",
            window_matches=5,
            window_sessions=None,
            related_finding_key=key,
        )
        if experiment_key
        else None
    )
    return FindingCandidate(
        key=key,
        kind=kind,  # type: ignore[arg-type]
        headline=key,
        body=key,
        interpretation=key,
        evidence=(),
        confidence_score=confidence,
        surprise_score=priority,
        specificity_score=priority,
        consequence_score=priority,
        actionability_score=priority,
        shareability_score=priority,
        priority_score=priority,
        experiment=experiment,
        limitations=(),
        publication_status="published",
        suppression_reason=None,
        definition_version="test-1.0.0",
        concept_tags=tags,
    )


def test_story_selection_deduplicates_concepts_and_returns_experiment_key() -> None:
    candidates = [
        _candidate("thesis", "contradiction", 0.95, tags=frozenset({"pool"}), experiment_key="observe-thesis"),
        _candidate("strength", "strength", 0.90, tags=frozenset({"pool"}), experiment_key="observe-strength"),
        _candidate("edge", "edge", 0.80, tags=frozenset({"late_game"}), experiment_key="observe-edge"),
    ]

    selection = select_story_findings(candidates)

    assert selection.thesis_key == "thesis"
    assert selection.strength_key == "strength"
    assert selection.experiment_key == "observe-edge"
    assert len(selection.ordered_finding_keys) == len(set(selection.ordered_finding_keys))


def test_conflicting_conclusions_keep_the_higher_confidence_candidate() -> None:
    selection = select_story_findings(
        [
            _candidate(
                "broad_pool_narrow_safety_zone",
                "contradiction",
                0.95,
                confidence=0.65,
            ),
            _candidate(
                "role_vs_hero_identity",
                "identity",
                0.50,
                confidence=0.90,
            ),
        ]
    )

    assert "role_vs_hero_identity" in selection.ordered_finding_keys
    assert "broad_pool_narrow_safety_zone" not in selection.ordered_finding_keys

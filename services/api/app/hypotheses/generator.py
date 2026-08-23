from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from app.hypotheses.models import DiagnosticQuestion, Hypothesis, MatchPredicate
from app.patterns.models import PatternCandidate


def generate_hypotheses(
    patterns: Iterable[PatternCandidate],
    *,
    max_hypotheses: int | None = None,
) -> list[Hypothesis]:
    """Map known summary patterns to testable, deterministic explanations."""

    hypotheses: list[Hypothesis] = []
    for pattern in patterns:
        if not pattern.unexplained:
            continue
        hypotheses.extend(_for_pattern(pattern))
    hypotheses.sort(key=lambda item: (-item.priority, item.hypothesis_id))
    if max_hypotheses is not None:
        return hypotheses[: max(0, max_hypotheses)]
    return hypotheses


def generate_diagnostic_hypotheses(
    question: DiagnosticQuestion | Mapping[str, Any] | str,
) -> list[Hypothesis]:
    """Build the v6 primary plus an optional high-reuse secondary.

    A report can provide fully serializable predicate definitions.  When it
    only provides copy, conservative outcome predicates preserve the
    positive/negative/control contract without inventing a causal claim.
    The secondary is dropped unless its declared evidence reuse is at least
    50%, as required by the Deep budget policy.
    """

    normalized = (
        question
        if isinstance(question, DiagnosticQuestion)
        else DiagnosticQuestion.from_mapping(dict(question) if isinstance(question, Mapping) else question)
    )
    primary = _hypothesis_from_diagnostic(
        normalized.diagnostic_question_id,
        normalized.primary_hypothesis or {},
        primary=True,
        reuse_fraction=1.0,
        required_families=normalized.required_data_families,
        fallback_statement=normalized.statement,
    )
    hypotheses = [primary]
    if normalized.secondary_hypothesis is not None and normalized.secondary_reuse_fraction >= 0.5:
        hypotheses.append(
            _hypothesis_from_diagnostic(
                normalized.diagnostic_question_id,
                normalized.secondary_hypothesis,
                primary=False,
                reuse_fraction=normalized.secondary_reuse_fraction,
                required_families=normalized.required_data_families,
                fallback_statement=normalized.statement,
                suffix="secondary",
            )
        )
    return hypotheses


def _hypothesis_from_diagnostic(
    question_id: str,
    value: Mapping[str, Any],
    *,
    primary: bool,
    reuse_fraction: float,
    required_families: tuple[str, ...],
    fallback_statement: str,
    suffix: str = "primary",
) -> Hypothesis:
    hypothesis_id = str(
        value.get("hypothesis_id")
        or value.get("id")
        or f"{question_id}:{suffix}"
    )
    required = tuple(
        str(item)
        for item in (value.get("required_data_families") or required_families or ("summary",))
    )
    return Hypothesis(
        hypothesis_id=hypothesis_id,
        source_pattern_id=f"diagnostic:{question_id}",
        statement=str(value.get("statement") or value.get("question") or fallback_statement),
        explanation_type=str(value.get("explanation_type") or "diagnostic_comparison"),
        priority=_bounded_float(value.get("priority"), 1.0),
        pattern_strength=_bounded_float(value.get("pattern_strength", value.get("strength")), 1.0),
        actionability=_bounded_float(value.get("actionability"), 1.0),
        required_data_families=required,
        positive_definition=_predicate(value.get("positive_definition"), "outcome", {"won": True}),
        negative_definition=_predicate(value.get("negative_definition"), "outcome", {"won": False}),
        control_definition=_predicate(value.get("control_definition"), "duration_bucket", {"bucket": "medium"}),
        min_positive=max(1, _as_int(value.get("min_positive"), 3)),
        min_negative=max(1, _as_int(value.get("min_negative"), 3)),
        min_control=max(1, _as_int(value.get("min_control"), 3)),
        target_positive=max(1, _as_int(value.get("target_positive"), 3)),
        target_negative=max(1, _as_int(value.get("target_negative"), 3)),
        target_control=max(1, _as_int(value.get("target_control"), 3)),
        confounders_to_control=tuple(str(item) for item in value.get("confounders_to_control", ())),
        expected_cost=float(value["expected_cost"]) if value.get("expected_cost") is not None else None,
        diagnostic_question_id=question_id,
        primary=primary,
        evidence_reuse_fraction=max(0.0, min(1.0, reuse_fraction)),
    )


def _predicate(value: Any, fallback_name: str, fallback_params: dict[str, Any]) -> MatchPredicate:
    if isinstance(value, MatchPredicate):
        return value
    if isinstance(value, Mapping):
        name = value.get("name")
        params = value.get("params")
        if isinstance(name, str) and isinstance(params, Mapping):
            return MatchPredicate(name, dict(params))
    return MatchPredicate(fallback_name, dict(fallback_params))


def _bounded_float(value: Any, fallback: float) -> float:
    try:
        return max(0.0, min(1.0, float(value))) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


def _as_int(value: Any, fallback: int) -> int:
    try:
        return int(value) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


# Naming aliases used by the v6 diagnostic-entry documentation.
generate_question_hypotheses = generate_diagnostic_hypotheses
generate_diagnostic_question_hypotheses = generate_diagnostic_hypotheses


def _for_pattern(pattern: PatternCandidate) -> list[Hypothesis]:
    if pattern.pattern_id == "hero_overperformance":
        hero_id = pattern.subject.get("hero_id")
        return [
            _hypothesis(
                pattern,
                suffix="timing_difference",
                statement=f"Hero {hero_id} success is explained by a different timing-to-fight pattern.",
                explanation_type="timing_difference",
                required=("summary", "role", "economy"),
                positive=MatchPredicate("hero_and_outcome", {"hero_id": hero_id, "won": True}),
                negative=MatchPredicate("hero_and_outcome", {"hero_id": hero_id, "won": False}),
                control=MatchPredicate("non_hero_same_role", {"hero_id": hero_id}),
            ),
            _hypothesis(
                pattern,
                suffix="safer_engagement",
                statement=f"Hero {hero_id} success is explained by safer engagement selection.",
                explanation_type="death_risk_difference",
                required=("summary", "role", "events"),
                positive=MatchPredicate("hero_and_outcome", {"hero_id": hero_id, "won": True}),
                negative=MatchPredicate("hero_and_outcome", {"hero_id": hero_id, "won": False}),
                control=MatchPredicate("non_hero_same_role", {"hero_id": hero_id}),
            ),
            _hypothesis(
                pattern,
                suffix="familiarity_control",
                statement=f"Hero {hero_id} success is primarily familiarity rather than a transferable playstyle.",
                explanation_type="familiarity_control",
                required=("summary", "role", "hero_pool"),
                positive=MatchPredicate("hero", {"hero_id": hero_id}),
                negative=MatchPredicate(
                    "non_hero_same_role",
                    {"hero_id": hero_id, "won": False},
                ),
                control=MatchPredicate(
                    "non_hero_same_role",
                    {"hero_id": hero_id, "won": True},
                ),
            ),
        ]
    if pattern.pattern_id in {"long_game_decline", "long_game_improvement"}:
        return [
            _hypothesis(
                pattern,
                suffix="advantage_conversion",
                statement="The long-game result is explained by conversion of mid-game advantages.",
                explanation_type="advantage_conversion",
                required=("summary", "time_series", "events"),
                positive=MatchPredicate("duration_and_outcome", {"bucket": "long", "won": True}),
                negative=MatchPredicate("duration_and_outcome", {"bucket": "long", "won": False}),
                control=MatchPredicate("duration_bucket", {"bucket": "short"}),
            ),
            _hypothesis(
                pattern,
                suffix="late_deaths",
                statement="The long-game result is explained by late death timing.",
                explanation_type="late_death_risk",
                required=("summary", "events"),
                positive=MatchPredicate("duration_and_outcome", {"bucket": "long", "won": True}),
                negative=MatchPredicate("duration_and_outcome", {"bucket": "long", "won": False}),
                control=MatchPredicate("duration_bucket", {"bucket": "short"}),
            ),
        ]
    if pattern.pattern_id == "session_decline":
        return [
            _hypothesis(
                pattern,
                suffix="decision_risk",
                statement="Late-session losses are explained by rising decision risk rather than only hero choice.",
                explanation_type="session_risk",
                required=("summary", "events"),
                positive=MatchPredicate(
                    "session_position_and_outcome",
                    {"value": 4, "operator": ">=", "won": False},
                ),
                negative=MatchPredicate(
                    "session_position_and_outcome",
                    {"value": 4, "operator": ">=", "won": True},
                ),
                control=MatchPredicate(
                    "session_position",
                    {"value": 3, "operator": "<="},
                ),
            ),
            _hypothesis(
                pattern,
                suffix="hero_selection",
                statement="Late-session decline is explained by increasingly unfamiliar hero choices.",
                explanation_type="hero_familiarity",
                required=("summary", "hero_pool", "role"),
                positive=MatchPredicate(
                    "session_position_and_outcome",
                    {"value": 4, "operator": ">=", "won": False},
                ),
                negative=MatchPredicate(
                    "session_position_and_outcome",
                    {"value": 4, "operator": ">=", "won": True},
                ),
                control=MatchPredicate(
                    "session_position",
                    {"value": 3, "operator": "<="},
                ),
            ),
        ]
    if pattern.pattern_id in {"recent_improvement", "recent_decline"}:
        return [
            _hypothesis(
                pattern,
                suffix="pool_shift",
                statement="The recent trajectory is explained by a hero-pool or role shift.",
                explanation_type="recent_context_shift",
                required=("summary", "hero_pool", "role"),
                positive=MatchPredicate("outcome", {"won": True}),
                negative=MatchPredicate("outcome", {"won": False}),
                control=MatchPredicate("duration_bucket", {"bucket": "medium"}),
            )
        ]
    if pattern.pattern_id == "consistency_collapse":
        return [
            _hypothesis(
                pattern,
                suffix="context_variance",
                statement="Death volatility is explained by game context rather than a single repeatable behavior.",
                explanation_type="context_variance",
                required=("summary", "role", "hero_pool"),
                positive=MatchPredicate("outcome", {"won": False}),
                negative=MatchPredicate("outcome", {"won": True}),
                control=MatchPredicate("duration_bucket", {"bucket": "medium"}),
            )
        ]
    if pattern.pattern_id == "hero_specialization":
        hero_id = pattern.subject.get("hero_id")
        return [
            _hypothesis(
                pattern,
                suffix="familiarity_vs_transfer",
                statement=f"Hero {hero_id} specialization reflects familiarity more than transferable role behavior.",
                explanation_type="familiarity_control",
                required=("summary", "role", "hero_pool"),
                positive=MatchPredicate("hero", {"hero_id": hero_id}),
                negative=MatchPredicate(
                    "non_hero_same_role",
                    {"hero_id": hero_id, "won": False},
                ),
                control=MatchPredicate(
                    "non_hero_same_role",
                    {"hero_id": hero_id, "won": True},
                ),
            )
        ]
    return []


def _hypothesis(
    pattern: PatternCandidate,
    *,
    suffix: str,
    statement: str,
    explanation_type: str,
    required: tuple[str, ...],
    positive: MatchPredicate,
    negative: MatchPredicate,
    control: MatchPredicate,
) -> Hypothesis:
    base = max(0.0, min(1.0, pattern.priority))
    return Hypothesis(
        hypothesis_id=f"{pattern.pattern_id}:{suffix}",
        source_pattern_id=pattern.pattern_id,
        statement=statement,
        explanation_type=explanation_type,
        priority=base,
        pattern_strength=pattern.strength,
        actionability=pattern.actionability,
        required_data_families=required,
        positive_definition=positive,
        negative_definition=negative,
        control_definition=control,
        min_positive=2,
        min_negative=2,
        min_control=2,
        target_positive=3,
        target_negative=3,
        target_control=3,
        confounders_to_control=pattern.confounders,
        expected_cost=None,
    )

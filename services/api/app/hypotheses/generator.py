from __future__ import annotations

from collections.abc import Iterable

from app.hypotheses.models import Hypothesis, MatchPredicate
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

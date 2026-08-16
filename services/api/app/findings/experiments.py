"""Small, deterministic behavior experiments attached to findings."""

from __future__ import annotations

from app.content.renderer import resolve_experiment_title
from app.findings.context import FreeFindingContext
from app.findings.models import FindingExperiment, FindingSignal


def experiment_for_finding(
    finding_key: str,
    context: FreeFindingContext,
    signals: dict[str, FindingSignal],
) -> FindingExperiment | None:
    experiment_key = {
        "broad_pool_narrow_safety_zone": "adjacent_pick_after_loss",
        "many_heroes_same_toolkit": "adjacent_toolkit_pick",
        "activity_travels_better_than_results": "stretch_conversion_rule",
        "losses_change_trust_more_than_pace": "adjacent_pick_after_loss",
        "long_session_tax": "game_four_opt_in",
        "long_game_edge": "late_game_repeat",
        "long_game_leak": "late_game_simplification",
        "form_identity_divergence": "recent_style_check",
        "strength_with_tax": "strength_tax_check",
        "signature_hero_mechanism": "adjacent_toolkit_pick",
        "role_vs_hero_identity": "role_toolkit_swap",
        "volatile_results_stable_style": "stable_style_review",
    }.get(finding_key)
    if experiment_key is None:
        return None

    title = resolve_experiment_title(experiment_key)
    if experiment_key == "adjacent_pick_after_loss":
        instruction = "In your next 5 post-loss queues, choose one adjacent comfort hero instead of immediately returning to your top comfort pick."
        hypothesis = "Your playable pool may be wider than the first familiar pick after a loss."
        measurement = "Notice whether activity and result quality stay close to your normal comfort games."
        return _experiment(title, experiment_key, instruction, hypothesis, measurement, 5, finding_key)
    if experiment_key == "adjacent_toolkit_pick":
        instruction = "For your next 5 games, keep two familiar toolkit traits and deliberately change one trait on the hero you pick."
        hypothesis = "The stable toolkit may be useful without requiring the same hero shape every time."
        measurement = "Record which familiar trait helped and which changed trait felt costly or useful."
        return _experiment(title, experiment_key, instruction, hypothesis, measurement, 5, finding_key)
    if experiment_key == "stretch_conversion_rule":
        instruction = "On your next 5 stretch-hero games, write one conversion rule before queueing: after a won fight, take an objective or reset before seeking another fight."
        hypothesis = "The gap may be in converting activity into results rather than finding action."
        measurement = "Compare how often the rule turns a good moment into an objective, reset, or safer next state."
        return _experiment(title, experiment_key, instruction, hypothesis, measurement, 5, finding_key)
    if experiment_key == "game_four_opt_in":
        instruction = "For your next 5 sessions, make game 4 an opt-in: queue only after naming one positive reason to continue."
        hypothesis = "A deliberate game-four check may change the later-session pattern."
        measurement = "Note the game-four result and whether the reason to continue was specific before queueing."
        return _experiment(title, experiment_key, instruction, hypothesis, measurement, None, finding_key, sessions=5)
    if experiment_key == "late_game_simplification":
        instruction = "In your next 5 long games, choose one late-game decision to simplify: objective first, reset after a won fight, or protect the highest-value wave."
        hypothesis = "A single repeatable late-game rule may preserve more of your usual edge."
        measurement = "After each long game, mark whether the rule was clear and whether it changed your next decision."
        return _experiment(title, experiment_key, instruction, hypothesis, measurement, 5, finding_key)
    if experiment_key == "late_game_repeat":
        instruction = "In your next 5 games, keep one late-game comfort rule visible and notice when your edge continues to show up."
        hypothesis = "Your long-game edge may be repeatable when the surrounding toolkit stays familiar."
        measurement = "Record the late-game context and the decision that felt most repeatable."
        return _experiment(title, experiment_key, instruction, hypothesis, measurement, 5, finding_key)
    if experiment_key == "recent_style_check":
        instruction = "For your next 5 games, write down one style signal before queueing: hero pool, role, or activity."
        hypothesis = "Recent form may be moving through a familiar style rather than a new identity."
        measurement = "Compare the written style signal with the result after each game."
        return _experiment(title, experiment_key, instruction, hypothesis, measurement, 5, finding_key)
    if experiment_key == "strength_tax_check":
        instruction = "For the next 5 games, keep the strength behavior and add one check for the context where its tax appears."
        hypothesis = "The trade-off may be manageable when the context is named early."
        measurement = "Record the strength behavior, the context, and whether the tax appeared."
        return _experiment(title, experiment_key, instruction, hypothesis, measurement, 5, finding_key)
    if experiment_key == "role_toolkit_swap":
        instruction = "For your next 5 games, change one hero while keeping the same job, then change one job while keeping a familiar toolkit trait."
        hypothesis = "Role may be the stable identity thread even when hero names move."
        measurement = "Note whether the role or the toolkit trait made the game feel more familiar."
        return _experiment(title, experiment_key, instruction, hypothesis, measurement, 5, finding_key)
    if experiment_key == "stable_style_review":
        instruction = "Review your next 5 games using one style note and one result note; keep them separate."
        hypothesis = "Results may swing without the underlying style moving as much."
        measurement = "Compare the range of style notes with the range of results at the end of the window."
        return _experiment(title, experiment_key, instruction, hypothesis, measurement, 5, finding_key)
    return None


def _experiment(
    title: str,
    key: str,
    instruction: str,
    hypothesis: str,
    measurement: str,
    matches: int | None,
    finding_key: str,
    *,
    sessions: int | None = None,
) -> FindingExperiment:
    return FindingExperiment(
        key=key,
        title=title,
        instruction=instruction,
        hypothesis=hypothesis,
        measurement=measurement,
        window_matches=matches,
        window_sessions=sessions,
        related_finding_key=finding_key,
    )

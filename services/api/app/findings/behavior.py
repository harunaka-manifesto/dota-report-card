"""Editorial bridge from qualified v3 semantics to player-facing stories."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.behavior.evidence import BehaviorEvidence, public_receipt_value
from app.behavior.models import ContextArchetypeResult, ElementResult, PatternResult

V3_FINDING_VERSION = "free-findings-3.0.0"


@dataclass(frozen=True, slots=True)
class BehaviorFinding:
    key: str
    kind: str
    headline: str
    body: str
    interpretation: str
    confidence: str
    confidence_score: float
    source_pattern_keys: tuple[str, ...]
    supporting_element_keys: tuple[str, ...]
    archetype_group_keys: tuple[str, ...]
    receipts: tuple[BehaviorEvidence, ...]
    experiment: Mapping[str, Any] | None = None
    share_copy: str | None = None
    editorial_score: float = 0.0
    limitations: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "kind": self.kind,
            "headline": self.headline,
            "body": self.body,
            "interpretation": self.interpretation,
            "confidence": self.confidence,
            "confidence_score": round(self.confidence_score, 6),
            "source_pattern_keys": list(self.source_pattern_keys),
            "supporting_element_keys": list(self.supporting_element_keys),
            "archetype_group_keys": list(self.archetype_group_keys),
            "receipts": [
                {
                    "key": item.key,
                    "label": item.comparison or item.key.replace("_", " ").title(),
                    "value": public_receipt_value(item),
                    "context": item.unit,
                    "confidence": "high" if item.confidence_score >= 0.75 else "moderate" if item.confidence_score >= 0.50 else "limited",
                }
                for item in self.receipts
            ],
            "experiment": dict(self.experiment) if self.experiment else None,
            "share_copy": self.share_copy,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class BehaviorStorySelection:
    ordered_finding_keys: tuple[str, ...]
    thesis_key: str | None
    strongest_key: str | None
    experiment_key: str | None
    story_version: str = "free-story-3.0.0"

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.story_version,
            "thesis_key": self.thesis_key,
            "strongest_key": self.strongest_key,
            "experiment_key": self.experiment_key,
            "ordered_pages": list(self.ordered_finding_keys),
        }


def evaluate_behavior_findings(context: Any) -> tuple[BehaviorFinding, ...]:
    """Select stories from upstream Pattern/Element results only.

    There is deliberately no raw match corpus in this function.  If a new
    story needs a new statistic, it belongs in an Element or Pattern first.
    """

    patterns: Mapping[str, PatternResult] = context.patterns
    elements: Mapping[str, ElementResult] = context.elements
    archetypes: Mapping[str, ContextArchetypeResult] = context.archetypes
    findings: list[BehaviorFinding] = []
    for pattern in patterns.values():
        if pattern.status != "qualified":
            continue
        findings.append(_finding_for_pattern(pattern, elements, archetypes))
    if not findings:
        findings.append(_fallback_finding(elements, archetypes))
    return tuple(sorted(findings, key=lambda item: (-item.editorial_score, item.key)))


def select_behavior_story(findings: tuple[BehaviorFinding, ...] | list[BehaviorFinding]) -> BehaviorStorySelection:
    ordered = sorted(findings, key=lambda item: (-item.editorial_score, item.key))
    selected: list[BehaviorFinding] = []
    for candidate in ordered:
        if any(candidate.key == item.key for item in selected):
            continue
        if candidate.archetype_group_keys and any(
            set(candidate.archetype_group_keys) == set(item.archetype_group_keys)
            for item in selected
        ):
            continue
        selected.append(candidate)
        if len(selected) >= 6:
            break
    thesis = next((item for item in selected if item.kind == "contradiction"), selected[0] if selected else None)
    strongest = next((item for item in selected if item.kind in {"strength", "edge"}), thesis)
    experiment = next((item for item in selected if item.experiment is not None), None)
    return BehaviorStorySelection(
        ordered_finding_keys=tuple(item.key for item in selected),
        thesis_key=thesis.key if thesis else None,
        strongest_key=strongest.key if strongest else None,
        experiment_key=str(experiment.experiment["key"]) if experiment and experiment.experiment else None,
    )


def _finding_for_pattern(pattern: PatternResult, elements: Mapping[str, ElementResult], archetypes: Mapping[str, ContextArchetypeResult]) -> BehaviorFinding:
    headline, body, interpretation, share = _copy(pattern.key)
    groups = tuple(
        group_key
        for group_key, archetype in archetypes.items()
        if pattern.key in archetype.contributing_patterns
    )
    receipts = tuple(pattern.evidence[:3])
    editorial_score = min(1.0, 0.55 * pattern.strength + 0.30 * pattern.confidence_score + 0.15 * min(1.0, len(groups) / 2))
    experiment = _experiment(pattern.key)
    return BehaviorFinding(
        key=pattern.key,
        kind=pattern.kind,
        headline=headline,
        body=body,
        interpretation=interpretation,
        confidence=pattern.confidence,
        confidence_score=pattern.confidence_score,
        source_pattern_keys=(pattern.key,),
        supporting_element_keys=pattern.element_keys,
        archetype_group_keys=groups,
        receipts=receipts,
        experiment=experiment,
        share_copy=share,
        editorial_score=editorial_score,
        limitations=pattern.confounders,
    )


def _fallback_finding(elements: Mapping[str, ElementResult], archetypes: Mapping[str, ContextArchetypeResult]) -> BehaviorFinding:
    strongest = max((item for item in elements.values() if item.score is not None), key=lambda item: item.confidence_score * abs(item.centered_score or 0.0), default=None)
    if strongest is None:
        first = next(iter(elements.values()), None)
        fallback_receipts = (
            BehaviorEvidence(
                "element_status",
                first.status if first is not None else "unavailable",
                "status",
                first.sample_size if first is not None else 0,
                first.coverage if first is not None else 0.0,
                0.0,
                first.label if first is not None else "Evidence",
            ),
        )
        return BehaviorFinding("behavior_still_forming", "identity", "Your report is still taking shape.", "The bounded history does not yet support a qualified relationship between two Elements.", "Unavailable evidence stays unavailable here; more readable matches may give the next Pattern enough room to qualify.", "low", 0.0, (), (first.key,) if first is not None else (), (), fallback_receipts, share_copy="My Dota report is still taking shape.", editorial_score=0.05)
    receipt = strongest.evidence[0] if strongest.evidence else BehaviorEvidence("element_score", strongest.score, "score", strongest.sample_size, strongest.coverage, strongest.confidence_score, strongest.label, strongest.source_match_ids)
    group_keys = tuple(group_key for group_key, result in archetypes.items() if strongest.key in {item.get("key") for item in result.contributing_elements})
    return BehaviorFinding("behavior_strength_fallback", "strength", f"{strongest.label} is the clearest signal so far.", f"{strongest.label} has the strongest readable shape in this bounded history. The rest of the report stays quiet until its evidence clears the gate.", "This is an Element-level observation, not a global personality label.", strongest.confidence, strongest.confidence_score, (), (strongest.key,), group_keys, (receipt,), share_copy=f"{strongest.label} is my clearest Dota signal.", editorial_score=0.35 * strongest.confidence_score)


def _copy(key: str) -> tuple[str, str, str, str]:
    values = {
        "broad_pool_narrow_toolkit": ("You play a lot of heroes. Fewer game plans.", "Your hero pool is broad, but the taxonomy sees a smaller set of tools returning underneath it.", "The names change more than the underlying toolkit does.", "I play a lot of heroes. Fewer game plans."),
        "broad_pool_narrow_safety_zone": ("Your hero pool is wide. Your safety zone is not.", "You explore broadly overall, while familiar-pool matches carry the stronger observable performance signal.", "Selection range and performance range are not the same thing here.", "My hero pool is wide. My safety zone is not."),
        "specialist_transferable_style": ("You change heroes, not the way you show up.", "The pool is concentrated, but your activity signal stays comparatively close outside it.", "A small pool can be a preference; this result does not call it a limit.", "I change heroes less than I change the screen around them."),
        "role_anchor_hero_explorer": ("You change heroes more than you change jobs.", "Hero choice moves across a wide range while credible role-context hints stay more concentrated.", "The role hint is the through-line, not an exact position claim.", "I change heroes more than I change jobs."),
        "hero_anchor_role_flex": ("The hero stays close. The role moves around it.", "Your hero pool is narrower while credible role contexts cover more ground.", "Summary role hints show context, not a guaranteed position.", "My hero pool stays close while the role context moves."),
        "signature_strength_with_tax": ("Your signature heroes do real work — off-pool games pay the tax.", "Established heroes carry a stronger performance signal, while the off-pool comparison falls behind.", "The signature is a strength with a measurable trade-off, not a verdict against experimentation.", "My signature heroes do real work. Off-pool games pay the tax."),
        "activity_travels_better_than_results": ("Your activity travels farther than your results do.", "Off-pool involvement stays closer to familiar involvement than the result proxy does.", "The missing mechanism needs richer evidence; summary history can show the gap, not explain every step inside it.", "My activity travels farther than my results do."),
        "high_involvement_controlled_exposure": ("You show up often without paying for it as often.", "Your kill involvement is high while deaths per unit of time stay comparatively controlled.", "Frequent participation and death exposure are separate signals here.", "I show up often without paying for it as often."),
        "high_involvement_high_exposure": ("You show up a lot — and pay for it often.", "High kill involvement arrives alongside high death exposure in the same summary history.", "The trade-off is visible. The timing and location behind it need Deep evidence.", "I show up a lot — and pay for it often."),
        "selective_finisher": ("You don't need every fight to finish the fight.", "Your event volume is lower, but your kill share is higher while death exposure stays controlled.", "This describes event distribution, not kill stealing or intent.", "I don't need every fight to finish the fight."),
        "losses_change_picks_more_than_pace": ("Losses change your picks more than your pace.", "After losses, your next hero moves toward familiarity while the activity signal stays comparatively close.", "The visible response is selection, not a claim about what you feel.", "Losses change my picks more than my pace."),
        "losses_change_pace_more_than_picks": ("Losses change your pace more than your picks.", "The next-match activity signal moves after losses while hero familiarity changes little.", "The history shows a pace shift; it does not name the reason behind it.", "Losses change my pace more than my picks."),
        "long_session_tax": ("Game four is where the edge starts to leak.", "You regularly reach long sessions, and later-session performance falls compared with earlier games in the same session.", "That makes game four a useful experiment boundary, not a permanent label.", "Game four is where my edge starts to leak."),
        "marathon_stability": ("Long sessions keep your numbers intact.", "Long sessions are common, while later-session performance holds or improves in the available history.", "The result is a context where your usual edge appears to survive longer.", "Long sessions keep my numbers intact."),
        "form_identity_divergence": ("Your recent form moved. Your style mostly didn't.", "Recent performance shifted while hero distribution and activity stayed comparatively stable.", "Current results can move through a familiar style; they do not automatically announce a new identity.", "My recent form moved. My style mostly didn't."),
    }
    return values.get(key, ("A pattern survived the first gate.", "Two upstream Elements moved together strongly enough to show here.", "The relationship is descriptive and stays within the evidence available.", "A Dota pattern survived the first gate."))


def _experiment(key: str) -> dict[str, str] | None:
    if key == "long_session_tax":
        return {"key": "game_four_opt_in", "title": "Make game four an opt-in", "instruction": "Before queueing game four, decide what would make it worth playing. Keep the decision visible, then compare the next few sessions.", "hypothesis": "A deliberate stop-or-continue choice changes the late-session comparison.", "measurement": "Compare game-four-plus performance with the earlier-session baseline.", "window": "5 sessions"}
    if key == "activity_travels_better_than_results":
        return {"key": "stretch_conversion_rule", "title": "Track conversion on a stretch hero", "instruction": "On one off-pool pick, note the first useful timing before you join the next fight. See whether the result gap narrows when the timing is ready.", "hypothesis": "The activity gap is smaller than the conversion gap.", "measurement": "Compare off-pool performance with and without the timing check.", "window": "10 matches"}
    return None


__all__ = ["BehaviorFinding", "BehaviorStorySelection", "V3_FINDING_VERSION", "evaluate_behavior_findings", "select_behavior_story"]

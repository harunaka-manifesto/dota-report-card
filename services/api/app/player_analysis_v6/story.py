"""Nine-beat v6 story, diagnostic routing, and share eligibility."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .constants import FINDING_FAMILY_KEYS, STORY_BEAT_KEYS
from .models import (
    DiagnosticQuestion,
    FindingFamilyResult,
    IdentitySummary,
    ShareCandidate,
    StoryBeat,
)

_BEAT_CONTENT: Mapping[str, tuple[str, str, str]] = {
    "self_estimate": ("Your estimate", "How would you describe your game?", "self_estimate"),
    "identity_reveal": ("Your identity", "Here is the pattern the summary evidence supports.", "reveal"),
    "pool_prediction": ("Your hero pool", "Predict the shape of your pool, then scrub its evolution.", "prediction_and_timeline_scrub"),
    "combat_expression": ("Combat expression", "Estimate how participation and exposure travel together.", "estimate_and_reveal"),
    "strongest_finding": ("Strongest finding", "Open the claim, evidence, interpretation, and recommendation layers.", "claim_evidence_interpretation_recommendation"),
    "secondary_finding": ("A second signal", "See a different family or the condition that changes the first finding.", "layered_claim_disclosure"),
    "recommendation": ("Choose a next step", "Pick one context-specific action for a five-game commitment.", "recommendation_choice_and_commitment"),
    "hero_mirror": ("Hero mirror", "Compare the identity thread with the heroes that carry it.", "mirror_and_share_composer"),
    "deep_fork": ("Go deeper", "Choose one diagnostic question for Deep Analysis.", "diagnostic_routing"),
}


def _findings(findings: Sequence[FindingFamilyResult] | Mapping[str, FindingFamilyResult]) -> tuple[FindingFamilyResult, ...]:
    values = tuple(findings.values()) if isinstance(findings, Mapping) else tuple(findings)
    return tuple(values)


def assemble_story(
    identity: IdentitySummary,
    findings: Sequence[FindingFamilyResult] | Mapping[str, FindingFamilyResult],
    *,
    diagnostic_questions: Sequence[DiagnosticQuestion] = (),
    hero_portfolio: Mapping[str, Any] | None = None,
) -> tuple[StoryBeat, ...]:
    """Return the fixed, ordered nine-beat story grammar."""

    values = _findings(findings)
    published = [item for item in values if item.published and item.status == "qualified"]
    if not published:
        published = [item for item in values if item.status == "qualified"]
    published.sort(key=lambda item: (-item.confidence_score, -item.identity_value, FINDING_FAMILY_KEYS.index(item.family)))
    strongest_refs = published[0].evidence_refs if published else identity.evidence_refs
    secondary_refs = published[1].evidence_refs if len(published) > 1 else ()
    payloads: Mapping[str, tuple[str, ...]] = {
        "self_estimate": (),
        "identity_reveal": identity.evidence_refs,
        "pool_prediction": tuple(
            dict.fromkeys(
                [
                    *(ref for item in values if item.family == "pool_shape" for ref in item.evidence_refs),
                    *(str(ref) for ref in (hero_portfolio or {}).get("prediction_refs", ())),
                    *(str(ref) for ref in (hero_portfolio or {}).get("timeline_refs", ())),
                ]
            )
        ),
        "combat_expression": tuple(ref for item in values if item.family == "combat_expression" for ref in item.evidence_refs),
        "strongest_finding": strongest_refs,
        "secondary_finding": secondary_refs,
        "recommendation": strongest_refs,
        "hero_mirror": tuple(
            dict.fromkeys(
                [
                    *(str(item) for item in (hero_portfolio or {}).get("evidence_refs", ())),
                    *(str(item) for item in (hero_portfolio or {}).get("hero_mirror_refs", ())),
                    *(str(item) for item in (hero_portfolio or {}).get("mirror_refs", ())),
                ]
            )
        ),
        "deep_fork": tuple(ref for question in diagnostic_questions for ref in question.evidence_refs),
    }
    result: list[StoryBeat] = []
    for order, key in enumerate(STORY_BEAT_KEYS, start=1):
        title, prompt, interaction = _BEAT_CONTENT[key]
        available = key not in {"strongest_finding", "secondary_finding"} or bool(payloads[key])
        result.append(
            StoryBeat(
                key,
                order,
                title,
                prompt,
                interaction,
                skippable=True,
                keyboard_accessible=True,
                reduced_motion_safe=True,
                available=available,
                payload_refs=tuple(dict.fromkeys(payloads[key])),
            )
        )
    return tuple(result)


build_story = assemble_story
assemble_nine_beat_story = assemble_story


def build_diagnostic_questions(
    findings: Sequence[FindingFamilyResult] | Mapping[str, FindingFamilyResult],
    *,
    max_questions: int = 3,
) -> tuple[DiagnosticQuestion, ...]:
    """Offer only evidence-qualified Deep choices from published families."""

    values = _findings(findings)
    eligible = [
        item
        for item in values
        if item.status == "qualified"
        and item.confidence in {"high", "moderate"}
        and item.evidence_refs
        and not item.blocking_confounders
    ]
    eligible.sort(key=lambda item: (-item.confidence_score, -item.actionability, FINDING_FAMILY_KEYS.index(item.family)))
    result: list[DiagnosticQuestion] = []
    for order, item in enumerate(eligible[: max(0, min(3, int(max_questions)))], start=1):
        prompt = {
            "pool_shape": "Which part of your hero pool creates the most reusable toolkit?",
            "transfer": "What changes when you leave familiar heroes?",
            "post_loss_response": "How does your next game differ after a loss?",
            "combat_expression": "Where do participation and exposure diverge?",
            "session_drift": "What changes as a play session gets longer?",
        }[item.family]
        result.append(
            DiagnosticQuestion(
                f"deep-v6-{item.family}",
                prompt,
                item.family,
                item.evidence_refs,
                item.confidence,
                True,
                order,
            )
        )
    return tuple(result)


diagnostic_questions = build_diagnostic_questions


def _share_blockers(
    *,
    confidence: str,
    evidence_refs: Sequence[str],
    recommendation: str | None = None,
    blocking_confounders: Sequence[str] = (),
    text: str | None = None,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if confidence != "high":
        blockers.append("requires high confidence")
    if not evidence_refs:
        blockers.append("missing evidence")
    if blocking_confounders:
        blockers.append("blocking confounder")
    if recommendation:
        blockers.append("recommendation cannot stand alone on a share card")
    if text and any(term in text.casefold() for term in ("early sign", "early-signal", "still forming")):
        blockers.append("early-sign wording")
    return tuple(dict.fromkeys(blockers))


def build_share_candidates(
    identity: IdentitySummary,
    findings: Sequence[FindingFamilyResult] | Mapping[str, FindingFamilyResult],
    *,
    hero_portfolio: Mapping[str, Any] | None = None,
) -> tuple[ShareCandidate, ...]:
    """Return the three card types with explicit eligibility reasons."""

    values = _findings(findings)
    strongest = next((item for item in values if item.published), None)
    identity_blockers = _share_blockers(confidence=identity.confidence, evidence_refs=identity.evidence_refs, text=identity.headline)
    candidates = [
        ShareCandidate(
            "identity",
            "identity",
            identity.headline,
            not identity_blockers,
            "eligible" if not identity_blockers else "; ".join(identity_blockers),
            identity.evidence_refs,
            identity.confidence,
            identity_blockers,
        )
    ]
    if strongest is None:
        candidates.append(ShareCandidate("strongest_finding", "finding", "Strongest finding", False, "no published finding", (), "unavailable", ("no published finding",)))
    else:
        blockers = _share_blockers(
            confidence=strongest.confidence,
            evidence_refs=strongest.evidence_refs,
            recommendation=strongest.recommendation,
            blocking_confounders=strongest.blocking_confounders,
            text=strongest.claim,
        )
        candidates.append(
            ShareCandidate(
                f"finding:{strongest.family}",
                "finding",
                strongest.claim or strongest.family.replace("_", " ").title(),
                not blockers,
                "eligible" if not blockers else "; ".join(blockers),
                strongest.evidence_refs,
                strongest.confidence,
                blockers,
            )
        )
    portfolio = hero_portfolio or {}
    portfolio_confidence = str(portfolio.get("confidence", "unavailable"))
    portfolio_refs = tuple(str(item) for item in portfolio.get("evidence_refs", ()))
    mirror_blockers = _share_blockers(confidence=portfolio_confidence, evidence_refs=portfolio_refs, text=str(portfolio.get("headline", "")))
    candidates.append(
        ShareCandidate(
            "hero_mirror",
            "hero_mirror",
            str(portfolio.get("headline", "Hero mirror")),
            not mirror_blockers,
            "eligible" if not mirror_blockers else "; ".join(mirror_blockers),
            portfolio_refs,
            portfolio_confidence,  # type: ignore[arg-type]
            mirror_blockers,
        )
    )
    return tuple(candidates)


share_eligibility = build_share_candidates
eligible_share_candidates = build_share_candidates


__all__ = [
    "assemble_story",
    "build_story",
    "assemble_nine_beat_story",
    "build_diagnostic_questions",
    "diagnostic_questions",
    "build_share_candidates",
    "share_eligibility",
    "eligible_share_candidates",
]

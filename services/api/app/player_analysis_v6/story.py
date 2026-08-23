"""Nine-beat v6 story, diagnostic routing, and share eligibility."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .constants import FINDING_FAMILY_KEYS, STORY_BEAT_KEYS
from .context_adjustment import match_field
from .copy import forbidden_copy_violations
from .deep_questions import question_spec
from .models import (
    DiagnosticQuestion,
    FindingFamilyResult,
    IdentitySummary,
    ShareCandidate,
    StoryBeat,
)
from .post_loss import build_post_loss_transitions

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

_SELF_ESTIMATE_OPTIONS = (
    {"id": "focused_repeat", "label": "I mostly repeat a small hero set."},
    {"id": "same_jobs_many_heroes", "label": "I rotate heroes, but I usually solve similar jobs."},
    {"id": "different_jobs", "label": "I change jobs as much as I change heroes."},
    {"id": "not_sure", "label": "I’m not sure yet."},
)
_COMBAT_ESTIMATE_OPTIONS = (
    {"id": "often_high_exposure", "label": "I’m involved often and I’m exposed often."},
    {"id": "often_low_exposure", "label": "I’m involved often with lower exposure."},
    {"id": "selective_low_exposure", "label": "I’m more selective and usually less exposed."},
    {"id": "varies", "label": "It changes a lot by game."},
)


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
    published.sort(key=lambda item: (-item.confidence_score, -item.identity_value, FINDING_FAMILY_KEYS.index(item.family)))
    strongest_refs = published[0].evidence_refs if published else ()
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
        if key == "recommendation":
            available = any(item.published and item.recommendation for item in values)
        options: tuple[Mapping[str, Any], ...] = ()
        if key == "self_estimate":
            options = _SELF_ESTIMATE_OPTIONS
        elif key == "combat_expression":
            options = _COMBAT_ESTIMATE_OPTIONS
        elif key == "pool_prediction":
            raw_options = (hero_portfolio or {}).get("prediction", {}).get("options", ()) if isinstance((hero_portfolio or {}).get("prediction"), Mapping) else ()
            options = tuple(item for item in raw_options if isinstance(item, Mapping))
        elif key == "recommendation":
            options = tuple(
                {
                    "id": str(item.recommendation.get("recommendation_id") or item.family),
                    "label": str(item.recommendation.get("title") or item.recommendation.get("label") or item.family),
                    "description": str(item.recommendation.get("instruction") or item.recommendation.get("action") or ""),
                }
                for item in published
                if isinstance(item.recommendation, Mapping)
            )
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
                evidence_refs=tuple(dict.fromkeys(payloads[key])),
                options=options,
                observed={
                    "published": bool(published),
                    "finding_family": published[0].family if published and key == "strongest_finding" else published[1].family if len(published) > 1 and key == "secondary_finding" else None,
                },
            )
        )
    return tuple(result)


build_story = assemble_story
assemble_nine_beat_story = assemble_story


def build_diagnostic_questions(
    findings: Sequence[FindingFamilyResult] | Mapping[str, FindingFamilyResult],
    *,
    max_questions: int = 3,
    elements: Mapping[str, Any] | None = None,
    matches: Sequence[Any] = (),
    hero_portfolio: Mapping[str, Any] | None = None,
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
    involvement_values: list[float] = []
    exposure_values: list[float] = []
    for row in matches:
        duration = match_field(row, "duration_seconds")
        if duration is None:
            duration = match_field(row, "duration")
        kills = match_field(row, "kills")
        assists = match_field(row, "assists")
        deaths = match_field(row, "deaths")
        try:
            duration_minutes = float(duration) / 60.0
            involvement = (float(kills) + float(assists)) / duration_minutes
            exposure = float(deaths) / duration_minutes * 10.0
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if duration_minutes > 0:
            involvement_values.append(involvement)
            exposure_values.append(exposure)
    involvement_cutoff = (
        sorted(involvement_values)[len(involvement_values) // 2]
        if involvement_values
        else 0.0
    )
    exposure_cutoff = (
        sorted(exposure_values)[len(exposure_values) // 2]
        if exposure_values
        else 0.0
    )
    involvement_band = max(0.01, involvement_cutoff * 0.10)
    exposure_band = max(0.01, exposure_cutoff * 0.10)
    result: list[DiagnosticQuestion] = []
    for order, item in enumerate(eligible[: max(0, min(3, int(max_questions)))], start=1):
        transfer_element = elements.get("transfer") if elements else None
        transfer_raw = transfer_element.raw_metrics if transfer_element is not None else {}
        core_ids = tuple(transfer_raw.get("core_hero_ids", ())) if isinstance(transfer_raw, Mapping) else ()
        stretch_ids = tuple(transfer_raw.get("stretch_hero_ids", ())) if isinstance(transfer_raw, Mapping) else ()
        portfolio_heroes = (hero_portfolio or {}).get("heroes", ())
        dominant_job_hero_ids = tuple(
            row.get("hero_id")
            for row in portfolio_heroes
            if isinstance(row, Mapping) and row.get("hero_id") is not None and row.get("functional_jobs")
        )
        transition_ids = tuple(match_field(item.current, "match_id") for item in build_post_loss_transitions(matches))
        session_ids = tuple(
            str(match_field(row, "session_id"))
            for row in matches
            if match_field(row, "session_id") is not None
        )
        lane_values = tuple(
            str(value)
            for row in matches
            for value in (match_field(row, "lane_context"), match_field(row, "role_hint"), match_field(row, "role"))
            if value
        )
        involvement_element = elements.get("involvement") if elements else None
        death_exposure_element = elements.get("death_exposure") if elements else None
        if item.family == "combat_expression" and (not involvement_values or not exposure_values):
            continue
        evidence_context = {
            "core_hero_ids": core_ids,
            "stretch_hero_ids": stretch_ids,
            "dominant_job_hero_ids": dominant_job_hero_ids,
            "lane_context": sorted(set(lane_values))[0] if lane_values else None,
            "direction": item.direction,
            "post_loss_match_ids": transition_ids,
            "all_match_ids": tuple(match_field(row, "match_id") for row in matches),
            "session_ids": tuple(dict.fromkeys(session_ids)),
            "combat_quadrant": {
                "involvement_zone": getattr(getattr(involvement_element, "estimate", None), "zone", "typical") or "typical",
                "exposure_zone": getattr(getattr(death_exposure_element, "estimate", None), "zone", "typical") or "typical",
                "involvement_cutoff": involvement_cutoff,
                "exposure_cutoff": exposure_cutoff,
                "involvement_typical_band": involvement_band,
                "exposure_typical_band": exposure_band,
            },
        }
        try:
            spec = question_spec(item.family, f"deep-v6-{item.family}", evidence_context=evidence_context)
        except ValueError:
            continue
        result.append(
            DiagnosticQuestion(
                question_id=str(spec["diagnostic_question_id"]),
                prompt=str(spec["statement"]),
                family=item.family,
                evidence_refs=item.evidence_refs,
                confidence=item.confidence,
                offered=True,
                order=order,
                statement=str(spec["statement"]),
                context=spec.get("context", {}),
                primary_hypothesis=spec.get("primary_hypothesis", {}),
                secondary_hypothesis=spec.get("secondary_hypothesis"),
                required_summary_metrics=spec.get("required_summary_metrics", ()),
                required_detail_metrics=spec.get("required_detail_metrics", ()),
                required_parse_metrics=spec.get("required_parse_metrics", ()),
                options=spec.get("options", ()),
                observed=spec.get("observed", {}),
                secondary_reuse_fraction=float(spec.get("secondary_reuse_fraction", 0.0) or 0.0),
                available=True,
                skippable=True,
            )
        )
    return tuple(result)


diagnostic_questions = build_diagnostic_questions


def _share_blockers(
    *,
    confidence: str,
    evidence_refs: Sequence[str],
    recommendation: Mapping[str, Any] | str | None = None,
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
    if forbidden_copy_violations(text):
        blockers.append("forbidden summary inference")
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
    identity_blockers = _share_blockers(confidence=identity.confidence, evidence_refs=identity.evidence_refs, text=" ".join((identity.headline, *identity.supporting_lines)))
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
            text=" ".join(filter(None, (strongest.claim, strongest.interpretation))),
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

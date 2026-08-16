"""Normalize existing Free DNA outputs into atomic finding signals."""

from __future__ import annotations

import math
import re
from collections import Counter
from statistics import median
from typing import Any

from app.findings.context import FreeFindingContext
from app.findings.models import FindingSignal


def derive_signals(context: FreeFindingContext) -> dict[str, FindingSignal]:
    """Return a deterministic signal map from summary-safe analysis outputs."""

    signals: dict[str, FindingSignal] = {}
    _dimension_signals(context, signals)
    _feature_signals(context, signals)
    _transition_signals(context, signals)
    _recent_style_signals(context, signals)
    _pattern_signals(context, signals)
    _hero_signals(context, signals)
    return signals


def _dimension_signals(context: FreeFindingContext, output: dict[str, FindingSignal]) -> None:
    for dimension in context.dna.dimensions:
        if dimension.status == "unavailable" or dimension.centered_score is None:
            continue
        output[f"dimension.{dimension.key}"] = FindingSignal(
            key=f"dimension.{dimension.key}",
            family="dimension",
            value=dimension.centered_score,
            unit="centered score",
            direction="positive" if dimension.centered_score > 0.08 else "negative" if dimension.centered_score < -0.08 else "neutral",
            confidence_score=_bounded(dimension.confidence_score),
            sample_size=max(0, dimension.sample_size),
            coverage=_bounded(dimension.coverage),
            source_match_ids=tuple(dimension.source_match_ids),
            public_receipt=f"{dimension.label or dimension.key.replace('_', ' ').title()} · {dimension.sample_size} matches",
            metadata={
                "receipt_key": dimension.key,
                "receipt_label": dimension.key.replace("_", " ").title(),
                "score": dimension.score,
                "label": dimension.label,
            },
        )


def _feature_signals(context: FreeFindingContext, output: dict[str, FindingSignal]) -> None:
    features = context.dna.features
    sample = features.sample_size
    coverage = features.coverage

    simple: tuple[tuple[str, Any, str, int, float, str], ...] = (
        ("unique_hero_count", features.unique_hero_count, "heroes", sample, coverage["overall"], "Hero pool"),
        ("hero_entropy", features.hero_entropy, "bits", sample, coverage["overall"], "Hero entropy"),
        ("normalized_hero_entropy", features.normalized_hero_entropy, "share", sample, coverage["overall"], "Normalized hero entropy"),
        ("effective_hero_count", features.effective_hero_count, "heroes", sample, coverage["overall"], "Effective hero pool"),
        ("top_3_share", features.top_3_share, "share", sample, coverage["overall"], "Top 3 hero share"),
        ("top_5_share", features.top_5_share, "share", sample, coverage["overall"], "Top 5 hero share"),
        ("top_10_share", features.top_10_share, "share", sample, coverage["overall"], "Top 10 hero share"),
        ("dominant_role_share", features.dominant_role_share, "share", len(features.role_match_ids), coverage["role"], "Dominant role share"),
        ("activity_median", features.activity_median, "involvement/min", len(features.activity_match_ids), coverage["activity"], "Typical activity"),
        ("activity_iqr", features.activity_iqr, "involvement/min", len(features.activity_match_ids), coverage["activity"], "Activity spread"),
        ("aggregate_kill_share", features.aggregate_kill_share, "share", len(features.orientation_match_ids), coverage["orientation"], "Kill share"),
        ("zero_involvement_rate", features.zero_involvement_rate, "rate", sample, coverage["overall"], "Zero-involvement rate"),
        ("overall_win_rate", features.overall_win_rate, "rate", sample, coverage["overall"], "Overall win rate"),
        ("session_length_p50", features.session_length_quantiles.get("p50"), "games/session", len(features.sessions), coverage["dated"], "Typical session length"),
        ("session_length_p75", features.session_length_quantiles.get("p75"), "games/session", len(features.sessions), coverage["dated"], "Long-session length"),
        ("session_duration_p50", features.session_duration_quantiles.get("p50"), "seconds", len(features.sessions), coverage["dated"], "Typical session duration"),
        ("session_duration_p75", features.session_duration_quantiles.get("p75"), "seconds", len(features.sessions), coverage["dated"], "Long-session duration"),
    )
    for key, value, unit, signal_sample, signal_coverage, label in simple:
        if value is None or signal_sample <= 0:
            continue
        output[f"feature.{key}"] = _feature_signal(
            f"feature.{key}", value, unit, signal_sample, signal_coverage, label
        )

    if features.dominant_role:
        output["feature.dominant_role"] = FindingSignal(
            key="feature.dominant_role",
            family="dna_feature",
            value=features.dominant_role,
            unit="role",
            direction=None,
            confidence_score=_sample_confidence(len(features.role_match_ids)),
            sample_size=len(features.role_match_ids),
            coverage=_bounded(coverage["role"]),
            source_match_ids=tuple(features.role_match_ids),
            public_receipt=f"Most common role: {features.dominant_role.replace('_', ' ')}",
            metadata={"receipt_key": "dominant_role", "receipt_label": "Most common role"},
        )

    _group_performance_signals(context, output)
    _endurance_signals(context, output)


def _group_performance_signals(
    context: FreeFindingContext, output: dict[str, FindingSignal]
) -> None:
    features = context.dna.features
    familiar = tuple(features.familiar_performance)
    off_pool = tuple(features.off_pool_performance)
    if familiar and off_pool:
        familiar_median = median(familiar)
        off_pool_median = median(off_pool)
        delta = familiar_median - off_pool_median
        output["feature.familiar_performance_median"] = _feature_signal(
            "feature.familiar_performance_median",
            familiar_median,
            "performance proxy",
            len(familiar),
            len(familiar) / max(1, context.eligible_matches),
            "Familiar-hero performance",
            source_match_ids=tuple(context.dna.features.familiar_match_ids),
        )
        output["feature.off_pool_performance_median"] = _feature_signal(
            "feature.off_pool_performance_median",
            off_pool_median,
            "performance proxy",
            len(off_pool),
            len(off_pool) / max(1, context.eligible_matches),
            "Off-pool performance",
            source_match_ids=tuple(context.dna.features.off_pool_match_ids),
        )
        output["feature.familiar_vs_off_pool_delta"] = _feature_signal(
            "feature.familiar_vs_off_pool_delta",
            delta,
            "performance difference",
            min(len(familiar), len(off_pool)),
            min(len(familiar), len(off_pool)) / max(1, context.eligible_matches),
            "Familiar versus off-pool gap",
            direction="positive" if delta > 0.05 else "negative" if delta < -0.05 else "neutral",
            source_match_ids=tuple(context.dna.features.familiar_match_ids + context.dna.features.off_pool_match_ids),
        )

    # Group activity by the canonical familiar-hero set already used by DNA.
    familiar_activity = [
        features.activity_by_match[item.match_id]
        for item in features.matches
        if item.hero_id in features.familiar_heroes and item.match_id in features.activity_by_match
    ]
    off_activity = [
        features.activity_by_match[item.match_id]
        for item in features.matches
        if item.hero_id not in features.familiar_heroes and item.match_id in features.activity_by_match
    ]
    if familiar_activity and off_activity:
        familiar_median = median(familiar_activity)
        off_median = median(off_activity)
        delta = off_median - familiar_median
        scale = max(features.activity_iqr, abs(familiar_median) * 0.25, 1.0)
        normalized_delta = delta / scale
        output["feature.familiar_activity_median"] = _feature_signal(
            "feature.familiar_activity_median",
            familiar_median,
            "involvement/min",
            len(familiar_activity),
            len(familiar_activity) / max(1, context.eligible_matches),
            "Familiar-hero activity",
        )
        output["feature.off_pool_activity_median"] = _feature_signal(
            "feature.off_pool_activity_median",
            off_median,
            "involvement/min",
            len(off_activity),
            len(off_activity) / max(1, context.eligible_matches),
            "Off-pool activity",
        )
        output["feature.off_pool_activity_delta"] = _feature_signal(
            "feature.off_pool_activity_delta",
            normalized_delta,
            "normalized activity difference",
            min(len(familiar_activity), len(off_activity)),
            min(len(familiar_activity), len(off_activity)) / max(1, context.eligible_matches),
            "Off-pool activity gap",
            direction="positive" if normalized_delta > 0.2 else "negative" if normalized_delta < -0.2 else "neutral",
        )


def _endurance_signals(context: FreeFindingContext, output: dict[str, FindingSignal]) -> None:
    positions = context.dna.features.endurance_by_position
    early = tuple(value for position in (1, 2) for value in positions.get(position, ()))
    late = tuple(value for position in (3, 4) for value in positions.get(position, ()))
    if not early or not late:
        return
    early_median = median(early)
    late_median = median(late)
    output["feature.endurance_early_median"] = _feature_signal(
        "feature.endurance_early_median", early_median, "performance proxy", len(early),
        len(early) / max(1, context.eligible_matches), "Early-session performance"
    )
    output["feature.endurance_late_median"] = _feature_signal(
        "feature.endurance_late_median", late_median, "performance proxy", len(late),
        len(late) / max(1, context.eligible_matches), "Late-session performance"
    )
    output["feature.endurance_delta"] = _feature_signal(
        "feature.endurance_delta", late_median - early_median, "performance difference",
        min(len(early), len(late)), min(len(early), len(late)) / max(1, context.eligible_matches),
        "Early-to-late session gap", direction="positive" if late_median - early_median > 0.05 else "negative" if late_median - early_median < -0.05 else "neutral"
    )


def _transition_signals(context: FreeFindingContext, output: dict[str, FindingSignal]) -> None:
    features = context.dna.features
    by_id = {item.match_id: item for item in features.matches}
    familiar = features.familiar_heroes
    groups: dict[str, list[Any]] = {"after_win": [], "after_loss": [], "after_two_losses": []}
    activity_groups: dict[str, list[float]] = {key: [] for key in groups}
    for session in context.dna.sessions.sessions:
        previous_losses = 0
        for previous_id, current_id in zip(session.match_ids, session.match_ids[1:], strict=False):
            previous = by_id.get(previous_id)
            current = by_id.get(current_id)
            if previous is None or current is None or previous.session_corrupt or current.session_corrupt:
                previous_losses = 0
                continue
            if previous.won:
                key = "after_win"
                previous_losses = 0
            else:
                previous_losses += 1
                key = "after_two_losses" if previous_losses >= 2 else "after_loss"
            groups[key].append(current)
            if current.match_id in features.activity_by_match:
                activity_groups[key].append(features.activity_by_match[current.match_id])

    rates: dict[str, float] = {}
    for key, rows in groups.items():
        if not rows:
            continue
        familiar_rate = sum(item.hero_id in familiar for item in rows) / len(rows)
        rates[key] = familiar_rate
        output[f"derived.{key}_familiar_pick_rate"] = _feature_signal(
            f"derived.{key}_familiar_pick_rate", familiar_rate, "rate", len(rows),
            len(rows) / max(1, context.eligible_matches),
            f"Familiar picks {key.replace('_', ' ')}",
            source_match_ids=tuple(item.match_id for item in rows),
        )
        if activity_groups[key]:
            output[f"derived.{key}_activity_median"] = _feature_signal(
                f"derived.{key}_activity_median", median(activity_groups[key]), "involvement/min",
                len(activity_groups[key]), len(activity_groups[key]) / max(1, context.eligible_matches),
                f"Activity {key.replace('_', ' ')}",
            )

    if "after_win" in rates and "after_loss" in rates:
        delta = rates["after_loss"] - rates["after_win"]
        output["derived.loss_familiarity_delta"] = _feature_signal(
            "derived.loss_familiarity_delta", delta, "rate difference",
            min(len(groups["after_win"]), len(groups["after_loss"])),
            min(len(groups["after_win"]), len(groups["after_loss"])) / max(1, context.eligible_matches),
            "Familiar-pick change after losses", direction="positive" if delta > 0.05 else "negative" if delta < -0.05 else "neutral",
            source_match_ids=tuple(item.match_id for item in groups["after_win"] + groups["after_loss"]),
        )
    if "after_two_losses" in rates and "after_win" in rates:
        delta = rates["after_two_losses"] - rates["after_win"]
        output["derived.two_loss_familiarity_delta"] = _feature_signal(
            "derived.two_loss_familiarity_delta", delta, "rate difference",
            min(len(groups["after_two_losses"]), len(groups["after_win"])),
            min(len(groups["after_two_losses"]), len(groups["after_win"])) / max(1, context.eligible_matches),
            "Familiar-pick change after two losses", direction="positive" if delta > 0.05 else "negative" if delta < -0.05 else "neutral",
            source_match_ids=tuple(item.match_id for item in groups["after_two_losses"] + groups["after_win"]),
        )

    win_activity = output.get("derived.after_win_activity_median")
    loss_activity = output.get("derived.after_loss_activity_median")
    if win_activity and loss_activity and isinstance(win_activity.value, (int, float)) and isinstance(loss_activity.value, (int, float)):
        delta = float(loss_activity.value) - float(win_activity.value)
        scale = max(features.activity_iqr, abs(float(win_activity.value)) * 0.25, 1.0)
        output["derived.loss_activity_delta"] = _feature_signal(
            "derived.loss_activity_delta", delta / scale, "normalized activity difference",
            min(win_activity.sample_size, loss_activity.sample_size),
            min(win_activity.coverage, loss_activity.coverage), "Activity change after losses",
            direction="positive" if delta / scale > 0.2 else "negative" if delta / scale < -0.2 else "neutral",
        )


def _recent_style_signals(context: FreeFindingContext, output: dict[str, FindingSignal]) -> None:
    ordered = list(context.summary_features.ordered_matches)
    recent = ordered[:20]
    prior = ordered[20:40]
    if len(recent) < 15 or len(prior) < 15:
        return
    recent_heroes = [item.hero_id for item in recent if item.hero_id is not None]
    prior_heroes = [item.hero_id for item in prior if item.hero_id is not None]
    recent_concentration = _top_share(recent_heroes, 5)
    prior_concentration = _top_share(prior_heroes, 5)
    output["feature.recent_hero_concentration"] = _feature_signal(
        "feature.recent_hero_concentration", recent_concentration, "share", len(recent_heroes),
        len(recent_heroes) / max(1, context.eligible_matches), "Recent top-5 hero share"
    )
    output["feature.prior_hero_concentration"] = _feature_signal(
        "feature.prior_hero_concentration", prior_concentration, "share", len(prior_heroes),
        len(prior_heroes) / max(1, context.eligible_matches), "Prior top-5 hero share"
    )
    output["feature.recent_hero_concentration_delta"] = _feature_signal(
        "feature.recent_hero_concentration_delta", recent_concentration - prior_concentration,
        "share difference", min(len(recent_heroes), len(prior_heroes)),
        min(len(recent_heroes), len(prior_heroes)) / max(1, context.eligible_matches),
        "Recent versus prior hero concentration", direction="positive" if recent_concentration - prior_concentration > 0.08 else "negative" if recent_concentration - prior_concentration < -0.08 else "neutral"
    )
    recent_activity = [item for item in recent if item.kills is not None and item.assists is not None]
    prior_activity = [item for item in prior if item.kills is not None and item.assists is not None]
    if len(recent_activity) >= 15 and len(prior_activity) >= 15:
        recent_rate = median(((item.kills or 0) + (item.assists or 0)) / max(item.duration_seconds / 60, 1 / 60) for item in recent_activity)
        prior_rate = median(((item.kills or 0) + (item.assists or 0)) / max(item.duration_seconds / 60, 1 / 60) for item in prior_activity)
        output["feature.recent_activity_delta"] = _feature_signal(
            "feature.recent_activity_delta", recent_rate - prior_rate, "involvement/min difference",
            min(len(recent_activity), len(prior_activity)), min(len(recent_activity), len(prior_activity)) / max(1, context.eligible_matches),
            "Recent versus prior activity", direction="positive" if recent_rate - prior_rate > 0.5 else "negative" if recent_rate - prior_rate < -0.5 else "neutral"
        )
    recent_rate = sum(item.won for item in recent) / len(recent)
    prior_rate = sum(item.won for item in prior) / len(prior)
    output["feature.recent_win_rate"] = _feature_signal(
        "feature.recent_win_rate", recent_rate, "rate", len(recent), len(recent) / max(1, context.eligible_matches), "Recent win rate"
    )
    output["feature.prior_win_rate"] = _feature_signal(
        "feature.prior_win_rate", prior_rate, "rate", len(prior), len(prior) / max(1, context.eligible_matches), "Prior win rate"
    )


def _pattern_signals(context: FreeFindingContext, output: dict[str, FindingSignal]) -> None:
    by_key: dict[str, Any] = {}
    for pattern in context.patterns:
        key = f"pattern.{pattern.pattern_id}"
        previous = by_key.get(key)
        if previous is None or pattern.priority > previous.priority:
            by_key[key] = pattern
    for key, pattern in by_key.items():
        receipt = _pattern_receipt(pattern, context)
        output[key] = FindingSignal(
            key=key,
            family="summary_pattern",
            value=pattern.effect_size,
            unit=pattern.unit,
            direction="positive" if pattern.effect_size > 0.05 else "negative" if pattern.effect_size < -0.05 else "neutral",
            confidence_score=_bounded(pattern.summary_confidence * max(pattern.stability, 0.5)),
            sample_size=max(0, pattern.sample_size),
            coverage=min(1.0, pattern.sample_size / max(1, context.eligible_matches)),
            source_match_ids=tuple(pattern.source_match_ids),
            public_receipt=receipt,
            metadata={
                "receipt_key": pattern.pattern_id,
                "receipt_label": pattern.category.title() + " pattern",
                "pattern_id": pattern.pattern_id,
                "baseline": pattern.baseline_value,
                "category": pattern.category,
                "confounders": pattern.confounders,
            },
        )


def _hero_signals(context: FreeFindingContext, output: dict[str, FindingSignal]) -> None:
    heroes = context.dna.heroes
    signature = heroes.signature
    if signature is not None:
        output["hero.signature"] = FindingSignal(
            key="hero.signature",
            family="hero_identity",
            value=signature.name,
            unit="hero",
            direction=None,
            confidence_score=_confidence_label(signature.confidence),
            sample_size=signature.matches,
            coverage=signature.matches / max(1, context.eligible_matches),
            public_receipt=f"Signature hero: {signature.name} · {signature.matches} observed games",
            metadata={"receipt_key": "signature_hero", "receipt_label": "Signature hero", "hero_id": signature.hero_id, "traits": signature.traits, "roles": signature.roles},
        )
    if heroes.patterns:
        pattern = heroes.patterns[0]
        traits = [_pretty_trait(value) for value in pattern.get("traits", [])]
        contributors = tuple(str(value) for value in pattern.get("contributors", []))
        if traits and len(contributors) >= 3:
            output["hero.pattern.primary"] = FindingSignal(
                key="hero.pattern.primary",
                family="hero_pattern",
                value=pattern.get("label", "Recognizable toolkit"),
                unit="toolkit",
                direction=None,
                confidence_score=min(0.90, 0.55 + len(contributors) * 0.08),
                sample_size=len(contributors),
                coverage=min(1.0, len(contributors) / 5),
                public_receipt=f"Toolkit traits: {', '.join(traits[:3])}",
                metadata={"receipt_key": "hero_toolkit", "receipt_label": "Hero toolkit", "traits": traits, "contributors": contributors, "key": pattern.get("key")},
            )
    if heroes.comfort_picks:
        output["hero.comfort.count"] = FindingSignal(
            key="hero.comfort.count",
            family="hero_identity",
            value=len(heroes.comfort_picks),
            unit="heroes",
            direction=None,
            confidence_score=min(0.9, 0.50 + len(heroes.comfort_picks) * 0.08),
            sample_size=sum(item.matches for item in heroes.comfort_picks),
            coverage=min(1.0, sum(item.matches for item in heroes.comfort_picks) / max(1, context.eligible_matches)),
            public_receipt=f"Comfort pool: {len(heroes.comfort_picks)} stable heroes",
            metadata={"receipt_key": "comfort_pool", "receipt_label": "Comfort pool"},
        )


def _feature_signal(
    key: str,
    value: Any,
    unit: str,
    sample_size: int,
    coverage: float,
    label: str,
    *,
    direction: str | None = None,
    source_match_ids: tuple[int, ...] = (),
) -> FindingSignal:
    confidence = _sample_confidence(sample_size) * (0.85 + 0.15 * _bounded(coverage))
    receipt = f"{label}: {_format_value(value, unit)} · n={sample_size}"
    return FindingSignal(
        key=key,
        family="dna_feature",
        value=_finite(value),
        unit=unit,
        direction=direction,
        confidence_score=_bounded(confidence),
        sample_size=max(0, sample_size),
        coverage=_bounded(coverage),
        source_match_ids=tuple(source_match_ids),
        public_receipt=receipt,
        metadata={"receipt_key": key.replace("feature.", "").replace("_", "-"), "receipt_label": label},
    )


def _pattern_receipt(pattern: Any, context: FreeFindingContext) -> str:
    subject = pattern.subject or {}
    hero_id = subject.get("hero_id")
    hero_name = context.hero_name_by_id.get(hero_id) if isinstance(hero_id, int) else None
    if pattern.pattern_id == "hero_overperformance" and hero_name:
        return f"{hero_name}: {pattern.effect_size:+.0%} versus other heroes · n={pattern.sample_size}"
    if pattern.pattern_id == "hero_specialization" and hero_name:
        return f"{hero_name}: {pattern.effect_size:.0%} of the detected pool"
    statement = re.sub(r"\bhero\s+\d+\b", "your hero", pattern.statement, flags=re.IGNORECASE)
    return statement.replace("because", "while")


def _top_share(values: list[int], limit: int) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    return sum(count for _, count in counts.most_common(limit)) / len(values)


def _pretty_trait(value: Any) -> str:
    return str(value).replace("_", " ")


def _format_value(value: Any, unit: str) -> str:
    if value is None:
        return "not available"
    if unit in {"share", "rate", "rate difference"}:
        return f"{float(value):.0%}"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _sample_confidence(sample_size: int) -> float:
    return min(1.0, max(0.0, sample_size / 30.0))


def _confidence_label(value: str) -> float:
    return {"high": 0.82, "moderate": 0.68, "low": 0.48}.get(value, 0.45)


def _finite(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _bounded(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0

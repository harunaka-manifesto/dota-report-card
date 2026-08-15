from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from math import log
from statistics import pstdev

from app.features.summary_models import SummaryFeatureSet, SummaryMatchFeature
from app.patterns.models import PatternCandidate, PatternEvidence


def detect_patterns(
    feature_set: SummaryFeatureSet,
    *,
    minimum_group_size: int = 5,
) -> list[PatternCandidate]:
    """Return ranked, summary-only observations.

    These detectors intentionally describe patterns rather than causes.  The
    latter belongs to the hypothesis/deep-scan boundary.
    """

    matches = list(feature_set.ordered_matches)
    patterns: list[PatternCandidate] = []
    if not matches:
        return patterns

    overall = _rate(matches)
    if overall is not None:
        patterns.append(
            PatternCandidate(
                pattern_id="overall_outcome_profile",
                subject={},
                statement=f"Your recent eligible win rate is {overall:.0%} across {len(matches)} matches.",
                effect_size=overall,
                sample_size=len(matches),
                stability=_sample_confidence(len(matches)),
                actionability=0.35,
                summary_confidence=_sample_confidence(len(matches)),
                unexplained=False,
                category="context",
                baseline_value=0.5,
                unit="win rate",
                source_match_ids=tuple(match.match_id for match in matches),
                evidence=(
                    PatternEvidence(
                        metric="win_rate",
                        value=overall,
                        baseline=0.5,
                        unit="win rate",
                        numerator=sum(match.won for match in matches),
                        denominator=len(matches),
                        source_match_ids=tuple(match.match_id for match in matches),
                    ),
                ),
            )
        )

    patterns.extend(_hero_overperformance(matches, minimum_group_size))
    patterns.extend(_duration_patterns(matches, minimum_group_size))
    patterns.extend(_session_patterns(matches, minimum_group_size))
    patterns.extend(_recent_patterns(matches, minimum_group_size))
    patterns.extend(_hero_pool_patterns(matches, minimum_group_size))
    patterns.extend(_consistency_patterns(matches, minimum_group_size))
    return sorted(patterns, key=lambda item: (-item.priority, item.pattern_id))


def _hero_overperformance(
    matches: list[SummaryMatchFeature], minimum_group_size: int
) -> list[PatternCandidate]:
    by_hero = _group(matches, lambda item: item.hero_id)
    results: list[PatternCandidate] = []
    for hero_id, hero_matches in by_hero.items():
        others = [match for match in matches if match.hero_id != hero_id]
        hero_rate = _rate(hero_matches)
        other_rate = _rate(others)
        if hero_id is None or hero_rate is None or other_rate is None:
            continue
        if len(hero_matches) < minimum_group_size or len(others) < minimum_group_size:
            continue
        effect = hero_rate - other_rate
        if effect < 0.12:
            continue
        source = tuple(match.match_id for match in hero_matches)
        results.append(
            PatternCandidate(
                pattern_id="hero_overperformance",
                subject={"hero_id": hero_id},
                statement=(
                    f"Your results on hero {hero_id} are {effect:.0%} better than on your other heroes."
                ),
                effect_size=effect,
                sample_size=len(hero_matches),
                stability=_directional_stability(hero_matches, others),
                actionability=0.78,
                summary_confidence=_sample_confidence(min(len(hero_matches), len(others))),
                unexplained=True,
                category="strength",
                baseline_value=other_rate,
                unit="win-rate difference",
                source_match_ids=source,
                evidence=(
                    PatternEvidence(
                        metric="hero_win_rate",
                        value=hero_rate,
                        baseline=other_rate,
                        unit="win rate",
                        numerator=sum(match.won for match in hero_matches),
                        denominator=len(hero_matches),
                        source_match_ids=source,
                    ),
                ),
                confounders=(
                    "Hero role, patch, party status, and opponent composition are not controlled at summary stage.",
                ),
                metadata={"hero_win_rate": hero_rate, "other_win_rate": other_rate},
            )
        )
    return results


def _duration_patterns(
    matches: list[SummaryMatchFeature], minimum_group_size: int
) -> list[PatternCandidate]:
    long_matches = [match for match in matches if match.duration_bucket == "long"]
    short_matches = [match for match in matches if match.duration_bucket == "short"]
    long_rate = _rate(long_matches)
    short_rate = _rate(short_matches)
    if (
        long_rate is None
        or short_rate is None
        or len(long_matches) < minimum_group_size
        or len(short_matches) < minimum_group_size
    ):
        return []
    effect = long_rate - short_rate
    if abs(effect) < 0.12:
        return []
    direction = "decline" if effect < 0 else "improvement"
    return [
        PatternCandidate(
            pattern_id=f"long_game_{direction}",
            subject={"long_threshold_seconds": 45 * 60},
            statement=(
                f"Your win rate in long games is {abs(effect):.0%} "
                f"{'lower' if effect < 0 else 'higher'} than in short games."
            ),
            effect_size=effect,
            sample_size=len(long_matches),
            stability=_directional_stability(long_matches, short_matches),
            actionability=0.76,
            summary_confidence=_sample_confidence(min(len(long_matches), len(short_matches))),
            unexplained=True,
            category="weakness" if effect < 0 else "strength",
            baseline_value=short_rate,
            unit="win-rate difference",
            source_match_ids=tuple(match.match_id for match in long_matches),
            evidence=(
                PatternEvidence(
                    metric="duration_win_rate",
                    value=long_rate,
                    baseline=short_rate,
                    unit="win rate",
                    numerator=sum(match.won for match in long_matches),
                    denominator=len(long_matches),
                    source_match_ids=tuple(match.match_id for match in long_matches),
                ),
            ),
            confounders=("Game duration is jointly determined by both teams and game state.",),
        )
    ]


def _session_patterns(
    matches: list[SummaryMatchFeature], minimum_group_size: int
) -> list[PatternCandidate]:
    early = [match for match in matches if (match.session_index or 0) <= 3]
    late = [match for match in matches if (match.session_index or 0) >= 4]
    early_rate = _rate(early)
    late_rate = _rate(late)
    if (
        early_rate is None
        or late_rate is None
        or len(early) < minimum_group_size
        or len(late) < minimum_group_size
    ):
        return []
    effect = late_rate - early_rate
    if effect >= -0.12:
        return []
    return [
        PatternCandidate(
            pattern_id="session_decline",
            subject={"late_session_index": 4},
            statement=f"Your win rate falls {abs(effect):.0%} from games 1–3 to game 4+ in a session.",
            effect_size=effect,
            sample_size=len(late),
            stability=_directional_stability(late, early),
            actionability=0.82,
            summary_confidence=_sample_confidence(min(len(early), len(late))),
            unexplained=True,
            category="weakness",
            baseline_value=early_rate,
            unit="win-rate difference",
            source_match_ids=tuple(match.match_id for match in late),
            evidence=(
                PatternEvidence(
                    metric="session_win_rate",
                    value=late_rate,
                    baseline=early_rate,
                    unit="win rate",
                    numerator=sum(match.won for match in late),
                    denominator=len(late),
                    source_match_ids=tuple(match.match_id for match in late),
                ),
            ),
            confounders=("Later games may have different heroes, parties, opponents, or match context.",),
        )
    ]


def _recent_patterns(
    matches: list[SummaryMatchFeature], minimum_group_size: int
) -> list[PatternCandidate]:
    recent = matches[: min(20, len(matches))]
    prior = matches[len(recent) : len(recent) + 40]
    recent_rate = _rate(recent)
    prior_rate = _rate(prior)
    if (
        recent_rate is None
        or prior_rate is None
        or len(recent) < minimum_group_size
        or len(prior) < minimum_group_size
    ):
        return []
    effect = recent_rate - prior_rate
    if abs(effect) < 0.12:
        return []
    direction = "improvement" if effect > 0 else "decline"
    return [
        PatternCandidate(
            pattern_id=f"recent_{direction}",
            subject={"recent_window": len(recent), "prior_window": len(prior)},
            statement=(
                f"Your recent win rate is {abs(effect):.0%} "
                f"{'up' if effect > 0 else 'down'} versus the preceding window."
            ),
            effect_size=effect,
            sample_size=len(recent),
            stability=_directional_stability(recent, prior),
            actionability=0.66,
            summary_confidence=_sample_confidence(min(len(recent), len(prior))),
            unexplained=True,
            category="form",
            baseline_value=prior_rate,
            unit="win-rate difference",
            source_match_ids=tuple(match.match_id for match in recent),
            evidence=(
                PatternEvidence(
                    metric="recent_win_rate",
                    value=recent_rate,
                    baseline=prior_rate,
                    unit="win rate",
                    numerator=sum(match.won for match in recent),
                    denominator=len(recent),
                    source_match_ids=tuple(match.match_id for match in recent),
                ),
            ),
            confounders=("Recent windows may reflect hero-pool, party, rank, or opponent changes.",),
        )
    ]


def _hero_pool_patterns(
    matches: list[SummaryMatchFeature], minimum_group_size: int
) -> list[PatternCandidate]:
    counts = {hero: count for hero, count in _counts(matches).items() if hero is not None}
    if not counts:
        return []
    total = sum(counts.values())
    top_hero, top_count = max(counts.items(), key=lambda item: (item[1], -item[0]))
    concentration = top_count / total
    if top_count < max(minimum_group_size, 8) or concentration < 0.45:
        return []
    entropy = -sum((count / total) * log(count / total, 2) for count in counts.values())
    source = tuple(match.match_id for match in matches if match.hero_id == top_hero)
    return [
        PatternCandidate(
            pattern_id="hero_specialization",
            subject={"hero_id": top_hero},
            statement=(
                f"Hero {top_hero} accounts for {concentration:.0%} of your recent games; "
                f"your hero-pool entropy is {entropy:.2f} bits."
            ),
            effect_size=concentration,
            sample_size=top_count,
            stability=_sample_confidence(top_count),
            actionability=0.58,
            summary_confidence=_sample_confidence(top_count),
            unexplained=True,
            category="identity",
            baseline_value=1 / len(counts),
            unit="hero share",
            source_match_ids=source,
            evidence=(
                PatternEvidence(
                    metric="hero_share",
                    value=concentration,
                    baseline=1 / len(counts),
                    unit="share",
                    numerator=top_count,
                    denominator=total,
                    source_match_ids=source,
                ),
            ),
            confounders=("Hero availability, draft preference, and role needs affect pool concentration.",),
            metadata={"distinct_heroes": len(counts), "entropy": entropy},
        )
    ]


def _consistency_patterns(
    matches: list[SummaryMatchFeature], minimum_group_size: int
) -> list[PatternCandidate]:
    death_values = [match.deaths for match in matches if match.deaths is not None]
    if len(death_values) < max(2 * minimum_group_size, 10):
        return []
    volatility = pstdev(death_values)
    median_deaths = sorted(death_values)[len(death_values) // 2]
    if volatility < 2.5:
        return []
    source = tuple(match.match_id for match in matches if match.deaths is not None)
    return [
        PatternCandidate(
            pattern_id="consistency_collapse",
            subject={"metric": "deaths"},
            statement=(
                f"Deaths vary widely across your recent games (spread {volatility:.1f} "
                f"around a median of {median_deaths:.0f})."
            ),
            effect_size=volatility,
            sample_size=len(death_values),
            stability=_sample_confidence(len(death_values)),
            actionability=0.7,
            summary_confidence=_sample_confidence(len(death_values)),
            unexplained=True,
            category="consistency",
            baseline_value=median_deaths,
            unit="death volatility",
            source_match_ids=source,
            evidence=(
                PatternEvidence(
                    metric="death_volatility",
                    value=volatility,
                    baseline=median_deaths,
                    unit="deaths",
                    denominator=len(death_values),
                    source_match_ids=source,
                ),
            ),
            confounders=("Hero, role, game length, and opponent context influence deaths.",),
        )
    ]


def _group(
    matches: list[SummaryMatchFeature], key: Callable[[SummaryMatchFeature], int | None]
) -> dict[int | None, list[SummaryMatchFeature]]:
    grouped: dict[int | None, list[SummaryMatchFeature]] = defaultdict(list)
    for match in matches:
        grouped[key(match)].append(match)
    return grouped


def _counts(matches: list[SummaryMatchFeature]) -> dict[int | None, int]:
    counts: dict[int | None, int] = {}
    for match in matches:
        counts[match.hero_id] = counts.get(match.hero_id, 0) + 1
    return counts


def _rate(matches: list[SummaryMatchFeature]) -> float | None:
    return sum(match.won for match in matches) / len(matches) if matches else None


def _sample_confidence(sample_size: int) -> float:
    return min(1.0, sample_size / 20.0)


def _directional_stability(
    left: list[SummaryMatchFeature], right: list[SummaryMatchFeature]
) -> float:
    if not left or not right:
        return 0.0
    left_direction = sum(match.won for match in left) >= len(left) / 2
    right_direction = sum(match.won for match in right) >= len(right) / 2
    return 1.0 if left_direction != right_direction else 0.6

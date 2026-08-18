"""Established-hero gates shared by all Hero Portfolio insights."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence

from app.hero_portfolio.models import HeroEligibility
from app.heroes.taxonomy import HeroTaxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch


def build_hero_eligibility(
    matches: Sequence[NormalizedSummaryMatch] | Iterable[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    *,
    common_thread_min_matches: int = 3,
    exception_min_matches: int = 4,
    mirror_min_matches: int = 4,
    min_share: float = 0.03,
    min_recency: float = 0.20,
    sustained_match_threshold: int = 8,
) -> tuple[HeroEligibility, ...]:
    """Return one auditable eligibility row per hero in the bounded history.

    Counts and share gates run before any winner logic.  A single lucky game
    therefore cannot become a Common Thread contributor, Exception, or Mirror.
    """

    rows = [item for item in matches if item.hero_id is not None]
    total = len(rows)
    by_hero: dict[int, list[NormalizedSummaryMatch]] = defaultdict(list)
    for item in rows:
        by_hero[int(item.hero_id)].append(item)  # type: ignore[arg-type]
    ordered = sorted(rows, key=lambda item: (item.started_at is None, item.started_at or 0, item.match_id))
    position_by_id = {item.match_id: index for index, item in enumerate(ordered)}

    results: list[HeroEligibility] = []
    for hero_id, hero_rows in sorted(by_hero.items()):
        entry = taxonomy.get(hero_id)
        matches_count = len(hero_rows)
        share = matches_count / max(total, 1)
        latest_position = max((position_by_id.get(item.match_id, 0) for item in hero_rows), default=0)
        recency = latest_position / max(len(ordered) - 1, 1)
        coverage = 1.0 if entry is not None and entry.available and entry.traits else 0.0
        reasons: list[str] = []
        if matches_count < min(common_thread_min_matches, exception_min_matches, mirror_min_matches):
            reasons.append("too_few_matches")
        if share < min_share:
            reasons.append("too_small_history_share")
        if coverage < 1.0:
            reasons.append("taxonomy_unavailable")
        recency_ok = recency >= min_recency or matches_count >= sustained_match_threshold
        if not recency_ok:
            reasons.append("stale_without_sustained_coverage")

        enough_base = matches_count >= 3 and share >= min_share and coverage >= 1.0 and recency_ok
        common = enough_base and matches_count >= common_thread_min_matches
        exception = enough_base and matches_count >= exception_min_matches
        mirror_valid_rows = [
            row
            for row in hero_rows
            if (
                row.duration_seconds is not None
                and row.duration_seconds >= 600
                and row.kills is not None
                and row.kills >= 0
                and row.deaths is not None
                and row.deaths >= 0
                and row.assists is not None
                and row.assists >= 0
            )
        ]
        mirror_metrics = (
            len(mirror_valid_rows) >= mirror_min_matches
            and len(mirror_valid_rows) / max(matches_count, 1) >= 0.75
        )
        mirror = (
            matches_count >= mirror_min_matches
            and share >= min_share
            and recency_ok
            and mirror_metrics
        )
        if not common and matches_count < common_thread_min_matches and "too_few_matches" not in reasons:
            reasons.append("common_thread_sample_gate")
        if not exception and matches_count < exception_min_matches and "too_few_matches" not in reasons:
            reasons.append("exception_sample_gate")
        if not mirror:
            if not mirror_metrics:
                reasons.append("mirror_metrics_missing_or_incomplete")
            elif matches_count < mirror_min_matches and "too_few_matches" not in reasons:
                reasons.append("mirror_sample_gate")
        results.append(
            HeroEligibility(
                hero_id=hero_id,
                matches=matches_count,
                share=share,
                recency=recency,
                coverage=coverage,
                eligible_for_common_thread=common,
                eligible_for_exception=exception,
                eligible_for_mirror=mirror,
                exclusion_reasons=tuple(dict.fromkeys(reasons)),
            )
        )
    return tuple(results)


def eligible_heroes(
    eligibility: Sequence[HeroEligibility],
    *,
    insight: str,
) -> tuple[HeroEligibility, ...]:
    """Filter eligibility rows without hiding why excluded heroes were dropped."""

    attribute = {
        "common_thread": "eligible_for_common_thread",
        "exception": "eligible_for_exception",
        "hero_exception": "eligible_for_exception",
        "mirror": "eligible_for_mirror",
        "hero_mirror": "eligible_for_mirror",
    }.get(insight)
    if attribute is None:
        raise ValueError(f"Unknown Hero Portfolio insight: {insight}")
    return tuple(item for item in eligibility if bool(getattr(item, attribute)))


__all__ = ["build_hero_eligibility", "eligible_heroes"]

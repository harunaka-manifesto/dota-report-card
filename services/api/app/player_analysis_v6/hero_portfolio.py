"""Summary-only hero portfolio adapter for the v6 report."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from app.heroes.knowledge import FullRosterHeroKnowledgeProvider
from app.heroes.taxonomy import load_default_taxonomy

from .context_adjustment import match_field
from .metrics import taxonomy_labels


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def load_v6_hero_taxonomy() -> dict[int, dict[str, Any]]:
    """Load the checked-in reviewed functional taxonomy used by v6."""

    taxonomy = load_default_taxonomy()
    provider = FullRosterHeroKnowledgeProvider(taxonomy)
    result: dict[int, dict[str, Any]] = {}
    for hero_id in sorted(taxonomy.heroes):
        entry = provider.get(hero_id)
        if entry is None or entry.review_status not in {"approved", "reviewed"}:
            continue
        jobs = tuple(dict.fromkeys((*entry.primary_functions, *entry.secondary_functions)))
        if not jobs:
            continue
        result[hero_id] = {
            "hero_function": jobs[0],
            "functional_jobs": jobs,
            "source_version": provider.version,
        }
    return result


def build_v6_hero_portfolio(
    matches: Sequence[Any],
    *,
    taxonomy_by_hero: Mapping[Any, Any] | None = None,
    min_hero_matches: int = 5,
) -> dict[str, Any]:
    """Return semantic portfolio context without fixed identity labels or rank."""

    counts = Counter(match_field(item, "hero_id") for item in matches if match_field(item, "hero_id") is not None)
    established = [(hero, count) for hero, count in counts.items() if count >= min_hero_matches]
    established.sort(key=lambda item: (-item[1], repr(item[0])))
    if not established:
        return {
            "status": "limited",
            "confidence": "unavailable",
            "headline": "Hero portfolio context is still forming.",
            "heroes": [],
            "evidence_refs": [],
            "prediction": {"prompt": "Which pool shape will your next five games resemble?", "options": []},
            "evolution": {"points": []},
        }
    total = sum(counts.values()) or 1
    hero_rows: list[dict[str, Any]] = []
    for hero, count in established:
        taxonomy = taxonomy_by_hero.get(hero) if taxonomy_by_hero else None
        jobs = taxonomy_labels(taxonomy)
        hero_rows.append({
            "hero_id": hero,
            "match_count": count,
            "share": round(count / total, 6),
            "functional_jobs": list(dict.fromkeys(jobs)),
            "evidence_refs": [f"hero:{hero}"],
        })
    common_jobs = Counter(job for row in hero_rows for job in row["functional_jobs"])
    thread = common_jobs.most_common(1)[0][0] if common_jobs else None
    refs = [ref for row in hero_rows for ref in row["evidence_refs"]]
    ordered = sorted(
        (item for item in matches if match_field(item, "hero_id") is not None),
        key=lambda item: (match_field(item, "start_time", match_field(item, "match_id", 0)) or 0),
    )
    chunk_size = max(1, len(ordered) // 3)
    timeline: list[dict[str, Any]] = []
    for index, start in enumerate(range(0, len(ordered), chunk_size)):
        chunk = ordered[start:start + chunk_size]
        if not chunk:
            continue
        chunk_counts = Counter(match_field(item, "hero_id") for item in chunk if match_field(item, "hero_id") is not None)
        timeline.append({
            "id": f"portfolio-period-{index + 1}",
            "label": ("Earlier", "Middle", "Later")[min(index, 2)],
            "position": index,
            "summary": f"{len(chunk_counts)} heroes appeared in {len(chunk)} summary matches.",
            "observed": {"hero_count": len(chunk_counts), "match_count": len(chunk)},
            "evidence": "portfolio:timeline",
        })
    prediction_options = (
        {"id": "focused_repeat", "label": "A focused repeat pool"},
        {"id": "same_jobs_many_heroes", "label": "Many heroes solving similar jobs"},
        {"id": "different_jobs", "label": "A pool spanning different jobs"},
        {"id": "not_sure", "label": "Not sure yet"},
    )
    return {
        "status": "available",
        "confidence": "high" if len(established) >= 2 else "moderate",
        "headline": "Your established heroes provide a visible portfolio thread.",
        "anchor": thread,
        "common_thread": thread,
        "heroes": hero_rows,
        "evidence_refs": refs,
        "hero_mirror_refs": refs,
        "hero_mirror": {
            "title": "Hero Mirror",
            "common_thread": thread,
            "heroes": hero_rows[:3],
            "evidence_refs": refs,
        },
        "prediction_refs": ["portfolio:prediction"],
        "timeline_refs": ["portfolio:timeline"],
        "prediction": {
            "prompt": "Which pool shape will your next five games resemble?",
            "options": list(prediction_options),
            "observed": "The observed pool is shown in the timeline below.",
            "reveal": "Your answer stays separate from the observed hero-pool evidence.",
        },
        "evolution": {
            "title": "Pool Evolution",
            "body": "The timeline is descriptive; it does not update the stable identity.",
            "points": timeline,
            "evidence_refs": ["portfolio:timeline"],
        },
        "timeline": timeline,
    }


adapt_hero_portfolio = build_v6_hero_portfolio

__all__ = ["build_v6_hero_portfolio", "adapt_hero_portfolio", "load_v6_hero_taxonomy"]

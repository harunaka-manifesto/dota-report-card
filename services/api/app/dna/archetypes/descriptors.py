from __future__ import annotations

from typing import Any

from app.dna.dimensions.models import DimensionResult

DESCRIPTOR_LABELS = {
    "breadth": ("Focused", "Exploratory"),
    "role": ("Role-anchored", "Role-fluid"),
    "adaptability": ("Comfort-driven", "Adaptable"),
    "activity": ("Reserved", "Highly involved"),
    "orientation": ("Facilitator", "Finisher"),
    "resilience": ("Resetting", "Outcome-sensitive"),
    "endurance": ("Front-loaded", "Sustained"),
    "rhythm": ("Short-burst", "Grinder"),
}

GROUPS = {
    "breadth": "hero_identity",
    "role": "hero_identity",
    "adaptability": "hero_identity",
    "activity": "combat_expression",
    "orientation": "combat_expression",
    "resilience": "session_response",
    "endurance": "session_response",
    "rhythm": "session_response",
}


def choose_descriptors(
    dimensions: tuple[DimensionResult, ...] | list[DimensionResult],
    *,
    count: int = 3,
    archetype_key: str | None = None,
) -> tuple[dict[str, str], ...]:
    candidates: list[dict[str, Any]] = []
    archetype_words = set((archetype_key or "").replace("_", " ").lower().split())
    for item in dimensions:
        if item.score is None or item.centered_score is None or not item.descriptor_eligible:
            continue
        label_pair = DESCRIPTOR_LABELS[item.key]
        label = label_pair[1] if item.score > 0.5 else label_pair[0]
        if set(label.lower().split()) & archetype_words:
            continue
        strength = abs(item.centered_score) * item.confidence_score
        if strength >= 0.12:
            candidates.append({
                "strength": strength,
                "dimension": item.key,
                "label": label,
                "group": GROUPS[item.key],
                "sign": 1 if item.centered_score >= 0 else -1,
            })

    chosen: list[dict[str, str]] = []
    selected: list[dict[str, Any]] = []
    remaining = list(candidates)
    while remaining and len(chosen) < count:
        ranked: list[tuple[float, dict[str, Any]]] = []
        for candidate in remaining:
            redundancy = max((_redundancy(candidate, item) for item in selected), default=0.0)
            mmr = float(candidate["strength"]) - 0.25 * redundancy
            # Prefer group coverage while still allowing a fourth signal from
            # a strong group once all three groups are represented.
            if candidate["group"] not in {item["group"] for item in selected}:
                mmr += 0.08
            ranked.append((mmr, candidate))
        _score, candidate = max(
            ranked,
            key=lambda item: (
                item[0], float(item[1]["strength"]), str(item[1]["dimension"]),
            ),
        )
        remaining.remove(candidate)
        selected.append(candidate)
        chosen.append({
            "key": str(candidate["dimension"]),
            "label": str(candidate["label"]),
            "dimension": str(candidate["dimension"]),
        })

    fallback = (
        {"key": "limited_history", "label": "History still forming", "dimension": "report"},
        {"key": "mixed_signals", "label": "Signals still mixed", "dimension": "report"},
        {"key": "bounded_evidence", "label": "Evidence remains bounded", "dimension": "report"},
    )
    fallback_index = 0
    while len(chosen) < count:
        candidate = fallback[fallback_index % len(fallback)]
        fallback_index += 1
        if any(item["key"] == candidate["key"] for item in chosen):
            continue
        chosen.append(candidate)
    return tuple(chosen[:count])


def _redundancy(left: dict[str, object], right: dict[str, object]) -> float:
    if left["dimension"] == right["dimension"]:
        return 1.0
    if left["group"] == right["group"] and left["sign"] == right["sign"]:
        return 0.75
    if left["group"] == right["group"]:
        return 0.35
    return 0.0

from __future__ import annotations

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
) -> tuple[dict[str, str], ...]:
    candidates: list[tuple[float, DimensionResult, str]] = []
    for item in dimensions:
        if item.score is None or item.centered_score is None:
            continue
        label_pair = DESCRIPTOR_LABELS[item.key]
        label = label_pair[1] if item.score > 0.5 else label_pair[0]
        strength = abs(item.centered_score) * item.confidence_score
        if strength >= 0.12:
            candidates.append((strength, item, label))
    candidates.sort(key=lambda item: (-item[0], item[1].key))
    chosen: list[dict[str, str]] = []
    used_groups: set[str] = set()
    for _strength, item, label in candidates:
        group = GROUPS[item.key]
        if group in used_groups and len(chosen) < min(count, 3):
            continue
        chosen.append({"key": item.key, "label": label, "dimension": item.key})
        used_groups.add(group)
        if len(chosen) >= count:
            return tuple(chosen)
    for _, item, label in candidates:
        if len(chosen) >= count:
            break
        if any(candidate["dimension"] == item.key for candidate in chosen):
            continue
        chosen.append({"key": item.key, "label": label, "dimension": item.key})
    fallback = (
        {"key": "developing_signal", "label": "Still forming", "dimension": "breadth"},
        {"key": "developing_sample", "label": "History-building", "dimension": "role"},
        {"key": "developing_direction", "label": "Direction still open", "dimension": "rhythm"},
    )
    fallback_index = 0
    while len(chosen) < count:
        candidate = fallback[fallback_index % len(fallback)]
        fallback_index += 1
        if any(item["key"] == candidate["key"] for item in chosen):
            continue
        chosen.append(candidate)
    return tuple(chosen[:count])

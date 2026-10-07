"""STRATZ field policy: provider field names that must never reach canonical data.

Enforced by the deep-match normalizer (``app.stratz.deep``).
"""

from __future__ import annotations

from typing import Any

# Provider fields that must never reach a canonical research table or a derived
# feature.  The check is name-based on purpose: a forbidden field arriving under
# a new name is caught by the semantic review, not by this gate.
FORBIDDEN_FIELD_TOKENS = (
    "rank",
    "mmr",
    "imp",
    "behavior",
    "smurf",
    "award",
    "prediction",
    "predicted",
    "winprob",
    "win_probability",
    "playback",
    "bracket",
    "leaderboard",
    "seasonrank",
)


def forbidden_fields_in(document: Any) -> set[str]:
    """Return every key in ``document`` whose name matches a forbidden token."""

    hits: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = key.lower().replace("_", "")
                for token in FORBIDDEN_FIELD_TOKENS:
                    if token in lowered:
                        hits.add(key)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(document)
    return hits

"""Enforced fencing for rank, MMR and the other forbidden surfaces.

Owner decision 5.1: rank is collected and shown in section 1 as history, and
it is **never** an analytical input. Until now that rule lived in a docstring
on ``RankDisplay``, which is a comment, not a guard — nothing stopped a future
feature from reading a rank field, and nothing would have noticed.

This module makes the rule enforceable at two levels, because either one alone
is escapable:

* **Runtime.** ``assert_row_is_analysis_safe`` refuses a row carrying a
  forbidden field, and it is called at the two doors into the analytical path:
  ``features.load_frames`` and ``pass2_tables.iter_pass2_players``. A row that
  never reaches a feature function cannot be read by one.
* **Static.** ``analytical_source_violations`` scans the analytical modules
  for references to the forbidden surfaces, so a feature that computes a rank
  proxy from something else, or imports ``RankDisplay``, fails a test rather
  than shipping.

The runtime check is shape-cached: rows in a corpus share a handful of key
structures, so the walk runs once per distinct shape rather than once per row.
That keeps a whole-corpus guard affordable, which matters — a guard that is
too slow to leave on is a guard that gets turned off.

Read-only. No provider call.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from report_card.player_analysis_v7.research.corpus import (
    FORBIDDEN_FIELD_TOKENS,
    forbidden_fields_in,
)

FENCE_VERSION = "v7-rank-fence-1.0.0"

REPO_ROOT = Path(__file__).resolve().parents[6]


class RankFenceViolation(RuntimeError):
    """A forbidden surface reached, or was referenced from, the analysis path."""


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------

_VALIDATED_SHAPES: set[int] = set()


def shape_signature(node: Any) -> Any:
    """A hashable summary of a document's key structure, ignoring values.

    Two rows with the same signature have the same key names in the same
    nesting, so validating one validates the other. Values are deliberately
    not part of the signature: the fence is about field *names*, and a rank
    smuggled in as a value under an innocent key is a different problem that
    ``forbidden_fields_in`` was never claiming to catch.
    """

    if isinstance(node, dict):
        return tuple(sorted((key, shape_signature(value)) for key, value in node.items()))
    if isinstance(node, list):
        # One representative element: a list's items share a shape in both
        # corpora, and signing every element would defeat the cache.
        return ("[]", shape_signature(node[0])) if node else ("[]",)
    return None


def assert_row_is_analysis_safe(row: Any, *, source: str) -> None:
    """Raise if ``row`` carries a forbidden field. Cached by key shape."""

    signature = hash(shape_signature(row))
    if signature in _VALIDATED_SHAPES:
        return
    found = forbidden_fields_in(row)
    if found:
        raise RankFenceViolation(
            f"{source}: a row carries forbidden field(s) {sorted(found)}. "
            "Rank, MMR and the other forbidden surfaces are display-only "
            "(owner decision 5.1) and must never reach the analysis path."
        )
    _VALIDATED_SHAPES.add(signature)


def reset_shape_cache() -> None:
    """Forget every validated shape. For tests; never needed in a run."""

    _VALIDATED_SHAPES.clear()


# ---------------------------------------------------------------------------
# Static
# ---------------------------------------------------------------------------

#: Every module that participates in computing a Finding, a recommendation, an
#: archetype or a report payload. A new analytical module belongs on this list;
#: the test below fails if one appears in the package and is not listed, so the
#: list cannot silently fall behind.
ANALYTICAL_MODULES: tuple[str, ...] = (
    "legacy/services/api/report_card/player_analysis_v7/research/archetype.py",
    "legacy/services/api/report_card/player_analysis_v7/research/features.py",
    "legacy/services/api/report_card/player_analysis_v7/research/inference.py",
    "legacy/services/api/report_card/player_analysis_v7/research/pass2_features.py",
    "legacy/services/api/report_card/player_analysis_v7/research/pass2_observations.py",
    "legacy/services/api/report_card/player_analysis_v7/research/pass2_tables.py",
    "legacy/services/api/report_card/player_analysis_v7/research/ranking.py",
    "legacy/services/api/report_card/player_analysis_v7/research/recommendation.py",
    "legacy/services/api/report_card/player_analysis_v7/research/screen.py",
    "legacy/services/api/report_card/player_analysis_v7/research/tables.py",
    "legacy/services/api/report_card/player_analysis_v7/research/tournament.py",
)

#: Modules in the research package that are not on the analysis path. Listed
#: explicitly so that "not analytical" is a decision someone made rather than
#: an omission.
NON_ANALYTICAL_MODULES: tuple[str, ...] = (
    "legacy/services/api/report_card/player_analysis_v7/research/__init__.py",
    "legacy/services/api/report_card/player_analysis_v7/research/corpus.py",  # defines the forbidden tokens
    "legacy/services/api/report_card/player_analysis_v7/research/durability.py",  # storage guard, not analysis
    "legacy/services/api/report_card/player_analysis_v7/research/rank_fence.py",  # this module
    "legacy/services/api/report_card/player_analysis_v7/research/owner_decisions.py",  # a record; computes nothing
    "legacy/services/api/report_card/player_analysis_v7/research/redteam.py",  # audits the others
    "legacy/services/api/report_card/player_analysis_v7/research/registry.py",  # candidate definitions, prose only
    "legacy/services/api/report_card/player_analysis_v7/research/variants.py",
    "legacy/services/api/report_card/player_analysis_v7/research/verdicts.py",
)

#: A word-boundary pattern per forbidden token, so ``barracks`` does not trip
#: on ``rank`` and ``impact`` does not trip on ``imp``. Substring matching is
#: right for corpus keys, which are machine-generated and short; it is wrong
#: for source code, which is prose.
_SOURCE_PATTERNS = tuple(
    (token, re.compile(rf"(?<![a-z]){re.escape(token)}(?![a-z])", re.IGNORECASE))
    for token in FORBIDDEN_FIELD_TOKENS
)

#: Identifiers that use a forbidden word in an unrelated sense, removed from a
#: line before it is scanned. The list is deliberately of exact identifiers
#: rather than a looser pattern: every entry is a decision someone made, and a
#: new name that happens to contain "rank" has to be added here on purpose
#: rather than slipping past a widened regex. ``rank_player`` orders a player's
#: Findings; it has nothing to do with the player's medal.
ORDERING_IDENTIFIERS: tuple[str, ...] = (
    "rank_player",
    "RankedFinding",
    "rank_display_is_fenced",
)

#: Lines that may legitimately name a forbidden surface: the ones explaining
#: why it is forbidden.
_ALLOWED_MENTION = re.compile(
    r"forbidden|never an analytical input|display-only|rank_fence|owner decision",
    re.IGNORECASE,
)


def _strip_comments_and_docstrings(source: str) -> list[tuple[int, str]]:
    """Code lines only, with comment text removed.

    A docstring explaining that rank is forbidden must not itself trip the
    scan, and a comment saying "we do not read rank here" is documentation of
    the rule, not a breach of it. Executable references are what matter.
    """

    lines: list[tuple[int, str]] = []
    in_docstring: str | None = None
    for number, raw in enumerate(source.splitlines(), start=1):
        line = raw
        if in_docstring:
            if in_docstring in line:
                line = line.split(in_docstring, 1)[1]
                in_docstring = None
            else:
                continue
        for quote in ('"""', "'''"):
            while quote in line:
                before, _, after = line.partition(quote)
                if quote in after:
                    line = before + " " + after.split(quote, 1)[1]
                    continue
                line = before
                in_docstring = quote
                break
            if in_docstring:
                break
        line = line.split("#", 1)[0]
        if line.strip():
            lines.append((number, line))
    return lines


def analytical_source_violations(
    modules: Iterable[str] = ANALYTICAL_MODULES, root: Path | None = None
) -> list[str]:
    """Executable references to a forbidden surface in the analysis path."""

    base = root or REPO_ROOT
    violations: list[str] = []
    for relative in modules:
        path = base / relative
        if not path.exists():
            violations.append(f"{relative}: listed as analytical but does not exist")
            continue
        for number, line in _strip_comments_and_docstrings(path.read_text(encoding="utf-8")):
            if _ALLOWED_MENTION.search(line):
                continue
            for identifier in ORDERING_IDENTIFIERS:
                line = line.replace(identifier, "")
            for token, pattern in _SOURCE_PATTERNS:
                if pattern.search(line):
                    violations.append(f"{relative}:{number}: references {token!r}: {line.strip()}")
    return violations


def unlisted_research_modules(root: Path | None = None) -> list[str]:
    """Modules in the research package on neither list.

    The static scan is only as good as its list of what to scan, so a new
    module must be classified deliberately rather than defaulting to unscanned.
    """

    base = root or REPO_ROOT
    known = set(ANALYTICAL_MODULES) | set(NON_ANALYTICAL_MODULES)
    present = {
        str(path.relative_to(base))
        for path in sorted(
            (base / "legacy" / "services" / "api" / "report_card" / "player_analysis_v7" / "research").glob(
                "*.py"
            )
        )
    }
    return sorted(present - known)


__all__ = [
    "ANALYTICAL_MODULES",
    "FENCE_VERSION",
    "NON_ANALYTICAL_MODULES",
    "ORDERING_IDENTIFIERS",
    "RankFenceViolation",
    "analytical_source_violations",
    "assert_row_is_analysis_safe",
    "reset_shape_cache",
    "shape_signature",
    "unlisted_research_modules",
]

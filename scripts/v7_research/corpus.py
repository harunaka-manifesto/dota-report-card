"""Read-only access helpers for the completed V7 STRATZ research corpus.

The corpus itself is immutable local research evidence held outside Git under an
ignored ``.local`` path.  Every module in this package treats it as read-only and
never issues a provider call.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DISCOVERY = "DISCOVERY"
CANDIDATE_TEST = "CANDIDATE_TEST"
CALIBRATION_RESERVED = "CALIBRATION_RESERVED"
SEALED_VALIDATION = "SEALED_VALIDATION"

RESEARCH_SPLITS = frozenset({DISCOVERY, CANDIDATE_TEST})
RESERVED_SPLITS = frozenset({CALIBRATION_RESERVED, SEALED_VALIDATION})

CORPUS_ROOT_ENV = "V7_CORPUS_ROOT"
FREEZE_ROOT_ENV = "V7_FREEZE_ROOT"

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


class CorpusError(RuntimeError):
    """Raised when the corpus cannot be located or is internally incoherent."""


class ReservedSplitAccess(CorpusError):
    """Raised when research code attempts to read a reserved or sealed split."""


def _require_dir(path: Path, label: str) -> Path:
    if not path.is_dir():
        raise CorpusError(f"{label} not found: {path}")
    return path


@dataclass(frozen=True)
class CorpusPaths:
    root: Path

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def normalized(self) -> Path:
        return self.root / "normalized"

    @property
    def canonical(self) -> Path:
        return self.root / "canonical"

    @property
    def canonical_history(self) -> Path:
        return self.canonical / "history"

    @property
    def canonical_parsed(self) -> Path:
        return self.canonical / "parsed"

    @property
    def derived(self) -> Path:
        return self.root / "derived"

    @property
    def ledger(self) -> Path:
        return self.root / "ledgers" / "request-ledger.jsonl"

    @property
    def run_manifest(self) -> Path:
        return self.root / "manifests" / "run-manifest.json"

    @property
    def state(self) -> Path:
        return self.root / "manifests" / "state.json"


def corpus_paths(root: str | os.PathLike[str] | None = None) -> CorpusPaths:
    raw_root = root or os.environ.get(CORPUS_ROOT_ENV)
    if not raw_root:
        raise CorpusError(
            f"corpus root not supplied; pass --corpus-root or set {CORPUS_ROOT_ENV}"
        )
    return CorpusPaths(_require_dir(Path(raw_root).expanduser().resolve(), "corpus root"))


def freeze_paths(root: str | os.PathLike[str] | None = None) -> Path:
    raw_root = root or os.environ.get(FREEZE_ROOT_ENV)
    if not raw_root:
        raise CorpusError(
            f"acquisition freeze root not supplied; pass --freeze-root or set {FREEZE_ROOT_ENV}"
        )
    return _require_dir(Path(raw_root).expanduser().resolve(), "freeze root")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_ledger(paths: CorpusPaths) -> Iterator[dict[str, Any]]:
    with paths.ledger.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def _iter_player_files(directory: Path) -> Iterator[Path]:
    yield from sorted(directory.glob("v7p_*.json"))


def iter_players(
    paths: CorpusPaths,
    table: str,
    splits: frozenset[str] | set[str] = RESEARCH_SPLITS,
) -> Iterator[dict[str, Any]]:
    """Yield canonical player documents from ``history`` or ``parsed``.

    ``splits`` fails closed: a reserved or sealed split can never be requested
    through this helper, so ordinary research commands cannot reach the
    partitions that must stay untouched until owner selection and final
    validation.
    """

    requested = frozenset(splits)
    forbidden = requested & RESERVED_SPLITS
    if forbidden:
        raise ReservedSplitAccess(
            "reserved/sealed splits are not readable by research code: "
            + ", ".join(sorted(forbidden))
        )
    if table == "history":
        directory = paths.canonical_history
    elif table == "parsed":
        directory = paths.canonical_parsed
    else:  # pragma: no cover - guarded by callers
        raise CorpusError(f"unknown canonical table: {table}")
    _require_dir(directory, f"canonical {table}")
    for path in _iter_player_files(directory):
        document = read_json(path)
        if document.get("split") in requested:
            yield document


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

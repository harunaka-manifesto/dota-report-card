"""Read-only access helpers for the completed V7 STRATZ research corpus.

The corpus itself is immutable local research evidence held outside Git under an
ignored ``.local`` path.  Every module in this package treats it as read-only and
never issues a provider call.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.player_analysis_v7.research.durability import assert_durable_corpus_root

DISCOVERY = "DISCOVERY"
CANDIDATE_TEST = "CANDIDATE_TEST"
CALIBRATION_RESERVED = "CALIBRATION_RESERVED"
SEALED_VALIDATION = "SEALED_VALIDATION"

RESEARCH_SPLITS = frozenset({DISCOVERY, CANDIDATE_TEST})
RESERVED_SPLITS = frozenset({CALIBRATION_RESERVED, SEALED_VALIDATION})

CORPUS_ROOT_ENV = "V7_CORPUS_ROOT"
FREEZE_ROOT_ENV = "V7_FREEZE_ROOT"

#: Every read of CANDIDATE_TEST is appended here *before* any row is yielded.
#: Ledgering after the fact does not work: an aborted read leaves the data seen
#: and the ledger clean, which is exactly the failure this control exists for.
CANDIDATE_TEST_LEDGER = (
    Path(__file__).resolve().parents[5] / "docs" / "evidence" / "v7-candidate-test-access-ledger.jsonl"
)

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
    durable = assert_durable_corpus_root(raw_root, purpose="corpus loader root")
    return CorpusPaths(_require_dir(durable, "corpus root"))


def freeze_paths(root: str | os.PathLike[str] | None = None) -> Path:
    raw_root = root or os.environ.get(FREEZE_ROOT_ENV)
    if not raw_root:
        raise CorpusError(
            f"acquisition freeze root not supplied; pass --freeze-root or set {FREEZE_ROOT_ENV}"
        )
    durable = assert_durable_corpus_root(raw_root, purpose="corpus freeze root")
    return _require_dir(durable, "freeze root")


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


def record_candidate_test_read(reason: str, ledger: Path | None = None) -> None:
    """Append one line to the confirmation-split access ledger.

    Called before any CANDIDATE_TEST row is handed out, so a crashed or aborted
    read still leaves a record. The ledger is the audit trail for the rule that
    the confirmation split is read once; it is not itself the enforcement.
    """

    target = ledger or CANDIDATE_TEST_LEDGER
    entry = {
        "read_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reason": reason,
        "argv": sys.argv[:8],
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def iter_players(
    paths: CorpusPaths,
    table: str,
    splits: frozenset[str] | set[str] = frozenset({DISCOVERY}),
    *,
    candidate_test_reason: str | None = None,
    ledger: Path | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield canonical player documents from ``history`` or ``parsed``.

    The default is **DISCOVERY only**. Exploratory work must not be able to
    reach the confirmation split by leaving an argument off: an earlier version
    defaulted to both research splits, and a descriptive atlas silently read all
    900 accounts because of it.

    ``splits`` fails closed on the reserved partitions, which can never be
    requested at all. Requesting CANDIDATE_TEST additionally requires a written
    ``candidate_test_reason``, which is appended to the access ledger before the
    first row is yielded.
    """

    requested = frozenset(splits)
    forbidden = requested & RESERVED_SPLITS
    if forbidden:
        raise ReservedSplitAccess(
            "reserved/sealed splits are not readable by research code: "
            + ", ".join(sorted(forbidden))
        )
    if CANDIDATE_TEST in requested:
        if not candidate_test_reason:
            raise CorpusError(
                "reading CANDIDATE_TEST requires an explicit candidate_test_reason; "
                "the confirmation split is not a split you reach by default"
            )
        record_candidate_test_read(candidate_test_reason, ledger)
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

def manifest_digests(root: str | os.PathLike[str] | Path) -> dict[str, str]:
    """Digests of a corpus run manifest, both ways, always both.

    Two reasonable digests exist for the same artefact — the raw bytes on disk
    and a canonicalised re-serialisation — and they do not agree. Emitting only
    one invites two research documents to quote different digests for an
    identical, unchanged corpus and look like a provenance failure. Every V7
    analysis records both.
    """

    manifest = Path(root) / "manifests" / "run-manifest.json"
    if not manifest.is_file():
        return {}
    raw = manifest.read_bytes()
    canonical = json.dumps(
        json.loads(raw.decode("utf-8")), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "run_manifest_file_sha256": hashlib.sha256(raw).hexdigest(),
        "run_manifest_canonical_sha256": hashlib.sha256(canonical).hexdigest(),
    }

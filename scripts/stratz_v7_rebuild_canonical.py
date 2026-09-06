#!/usr/bin/env python3
"""Rebuild the canonical corpus layer from the normalized layer already on disk.

On 2026-09-07 the ``canonical/`` layer of the Pass-1 corpus was found empty
(history) and partial (parsed) inside a ``/private/tmp`` worktree, which is not
durable storage on macOS. The ``normalized/`` and ``raw/`` layers survived
intact.

``canonical`` is a pure function of ``normalized`` plus the account metadata in
``manifests/state.json`` and the frozen split manifest. This script recomputes
it by calling the corpus runner's own ``canonicalize_history`` and
``canonicalize_parsed`` -- the same functions that produced the originals -- so
the result is the same artifact, not a reconstruction of one.

**Makes no provider call.** It reads only files already on disk. It refuses to
write an account whose rebuilt row count disagrees with the count the run state
recorded at collection time, which is the check that the rebuild reproduces the
original rather than merely producing something plausible.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.stratz_v7_corpus_runner import (  # noqa: E402
    canonicalize_history,
    canonicalize_parsed,
)


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _split_lookup(split_manifest: Path) -> dict[str, tuple[str, int]]:
    manifest = _read_json(split_manifest)
    return {
        member["pseudonym"]: (member["split"], int(member["source_position"]))
        for member in manifest["members"]
    }


def rebuild_history(root: Path, splits: dict[str, tuple[str, int]], *, dry_run: bool) -> dict[str, int]:
    state = _read_json(root / "manifests" / "state.json")
    window = _read_json(root / "manifests" / "run-manifest.json")["window"]
    accounts = state["history"]["accounts"]

    counts = {"rebuilt": 0, "already_present": 0, "skipped_no_pages": 0, "mismatch": 0}
    mismatches: list[str] = []

    for pseudonym, account_state in sorted(accounts.items()):
        target = root / "canonical" / "history" / f"{pseudonym}.json"
        if target.is_file():
            counts["already_present"] += 1
            continue
        pages = []
        for page in account_state.get("pages", ()):
            path = root / str(page.get("normalized_path", ""))
            if path.is_file():
                pages.append(_read_json(path))
        if not pages:
            counts["skipped_no_pages"] += 1
            continue
        split, source_position = splits[pseudonym]
        status = account_state.get("status", "complete")
        completeness = "truncated" if status == "truncated" else status
        canonical = canonicalize_history(
            pages,
            pseudonym=pseudonym,
            source_position=source_position,
            split=split,
            window_start=int(window["start_timestamp"]),
            window_end=int(window["end_timestamp"]),
            completeness=str(completeness),
        )
        expected = account_state.get("history_row_count")
        if expected is not None and canonical["unique_match_count"] != expected:
            counts["mismatch"] += 1
            mismatches.append(
                f"{pseudonym}: rebuilt {canonical['unique_match_count']} rows, "
                f"state recorded {expected}"
            )
            continue
        if not dry_run:
            _write_json(target, canonical)
        counts["rebuilt"] += 1

    if mismatches:
        raise SystemExit(
            "refusing to complete: "
            + f"{len(mismatches)} account(s) did not reproduce their recorded row count\n"
            + "\n".join(mismatches[:10])
        )
    return counts


def rebuild_parsed(root: Path, splits: dict[str, tuple[str, int]], *, dry_run: bool) -> dict[str, int]:
    state = _read_json(root / "manifests" / "state.json")
    accounts = state["parsed"]["accounts"]

    counts = {"rebuilt": 0, "already_present": 0, "skipped_no_batches": 0, "mismatch": 0}
    mismatches: list[str] = []

    for pseudonym, account_state in sorted(accounts.items()):
        target = root / "canonical" / "parsed" / f"{pseudonym}.json"
        if target.is_file():
            counts["already_present"] += 1
            continue
        batches = []
        for batch in account_state.get("batches", ()):
            path = root / str(batch.get("normalized_path", ""))
            if path.is_file():
                batches.append(_read_json(path))
        if not batches:
            counts["skipped_no_batches"] += 1
            continue
        split, source_position = splits[pseudonym]
        canonical = canonicalize_parsed(
            batches,
            pseudonym=pseudonym,
            source_position=source_position,
            split=split,
        )
        expected = account_state.get("parsed_row_count")
        actual = len(canonical.get("rows", ()))
        if expected is not None and actual != expected:
            counts["mismatch"] += 1
            mismatches.append(f"{pseudonym}: rebuilt {actual} rows, state recorded {expected}")
            continue
        if not dry_run:
            _write_json(target, canonical)
        counts["rebuilt"] += 1

    if mismatches:
        raise SystemExit(
            "refusing to complete: "
            + f"{len(mismatches)} parsed account(s) did not reproduce their recorded row count\n"
            + "\n".join(mismatches[:10])
        )
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", required=True)
    parser.add_argument("--split-manifest", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.corpus_root).expanduser().resolve()
    splits = _split_lookup(Path(args.split_manifest).expanduser().resolve())

    history = rebuild_history(root, splits, dry_run=args.dry_run)
    print(f"history  {history}")
    parsed = rebuild_parsed(root, splits, dry_run=args.dry_run)
    print(f"parsed   {parsed}")
    print("dry run: nothing written" if args.dry_run else "canonical layer rebuilt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a DISCOVERY-only parsed overlay from surviving normalized batches.

The completed new-lineage collector intentionally recollected history only.
This deterministic, offline step joins its 600 DISCOVERY pseudonyms to the
surviving Pass-1 normalized parsed batches. It never enumerates or reads a
non-DISCOVERY account and never modifies either source corpus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from legacy.scripts.stratz_v7_corpus_runner import canonicalize_parsed  # noqa: E402

SCHEMA_VERSION = "v7-pass1-parsed-overlay-1.0.0"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def tree_digest(rows: list[tuple[str, str]]) -> str:
    payload = "".join(f"{sha}  {name}\n" for name, sha in rows).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-root", required=True)
    parser.add_argument("--surviving-parsed-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    history_root = Path(args.history_root).resolve()
    parsed_root = Path(args.surviving_parsed_root).resolve()
    out = Path(args.out).resolve()
    history_files = sorted((history_root / "canonical/history").glob("v7p_*.json"))
    if len(history_files) != 600:
        raise SystemExit(f"expected 600 completed DISCOVERY histories, found {len(history_files)}")

    source_hashes: list[tuple[str, str]] = []
    documents = rows = 0
    for history_path in history_files:
        history = read_json(history_path)
        if history.get("split") != "DISCOVERY":
            raise SystemExit(f"non-DISCOVERY history reached overlay: {history_path.name}")
        pseudonym = str(history["account_pseudonym"])
        batch_dir = parsed_root / "normalized/parsed" / pseudonym
        batch_paths = sorted(batch_dir.glob("batch-*.json"))
        if not batch_paths:
            continue
        batches = []
        for path in batch_paths:
            batch = read_json(path)
            if batch.get("account_pseudonym") != pseudonym or batch.get("split") != "DISCOVERY":
                raise SystemExit(f"parsed source identity mismatch: {path}")
            batches.append(batch)
            source_hashes.append((str(path.relative_to(parsed_root)), digest(path)))
        canonical = canonicalize_parsed(
            batches,
            pseudonym=pseudonym,
            source_position=int(history["source_position"]),
            split="DISCOVERY",
        )
        write_json(out / "canonical/parsed" / f"{pseudonym}.json", canonical)
        documents += 1
        rows += len(canonical["rows"])

    source_hashes.sort()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "lineage": "v7-pass1-new-lineage-2026-09-08",
        "split": "DISCOVERY",
        "source_history_root": str(history_root),
        "source_parsed_root": str(parsed_root),
        "source_normalized_file_count": len(source_hashes),
        "source_normalized_tree_sha256": tree_digest(source_hashes),
        "canonical_documents": documents,
        "canonical_rows": rows,
        "candidate_test_read": False,
        "calibration_reserved_read": False,
        "sealed_validation_read": False,
        "provider_calls": 0,
    }
    write_json(out / "manifests/overlay-manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

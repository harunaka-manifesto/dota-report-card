#!/usr/bin/env python3
"""SHA-256 manifest for a corpus's immutable artifacts.

Written for the 2026-09-07 durability move. A byte count and a file count say
a copy is the same size; a digest says it is the same data. Only the layers
that are genuinely immutable are hashed -- canonical documents and manifests --
because those are what analysis reads and what an audit would need to trust.

``--verify`` re-hashes and reports any file that changed, vanished or appeared.

Read-only. No provider call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

#: Layers worth hashing: written once by the collector and never edited.
IMMUTABLE_LAYERS = ("canonical", "manifests")

_CHUNK = 1 << 20


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            hasher.update(chunk)
    return hasher.hexdigest()


def build(root: Path) -> dict[str, Any]:
    entries: dict[str, dict[str, Any]] = {}
    total_bytes = 0
    for layer in IMMUTABLE_LAYERS:
        directory = root / layer
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.name == ".DS_Store":
                continue
            relative = path.relative_to(root).as_posix()
            size = path.stat().st_size
            total_bytes += size
            entries[relative] = {"sha256": _digest(path), "bytes": size}
    return {
        "schema_version": "v7-corpus-hash-manifest-1.0.0",
        "root_name": root.name,
        "layers": list(IMMUTABLE_LAYERS),
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "files": entries,
    }


def verify(root: Path, manifest: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    recorded = manifest["files"]
    for relative, entry in recorded.items():
        path = root / relative
        if not path.is_file():
            problems.append(f"missing: {relative}")
            continue
        if _digest(path) != entry["sha256"]:
            problems.append(f"changed: {relative}")
    present = {
        p.relative_to(root).as_posix()
        for layer in IMMUTABLE_LAYERS
        for p in (root / layer).rglob("*")
        if (root / layer).is_dir() and p.is_file() and p.name != ".DS_Store"
    }
    for relative in sorted(present - set(recorded)):
        problems.append(f"unexpected: {relative}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    out = Path(args.out)

    if args.verify:
        manifest = json.loads(out.read_text(encoding="utf-8"))
        problems = verify(root, manifest)
        if problems:
            print(f"{len(problems)} problem(s) against {out}:")
            for line in problems[:20]:
                print(f"  {line}")
            return 1
        print(f"verified {manifest['file_count']} files against {out}")
        return 0

    manifest = build(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}: {manifest['file_count']} files, {manifest['total_bytes']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

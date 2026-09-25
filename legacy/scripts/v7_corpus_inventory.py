#!/usr/bin/env python3
"""Exact per-layer inventory of a V7 corpus root, measured from disk.

Written for the 2026-09-07 corpus-loss closeout, where two figures reported
from memory disagreed with each other. Everything here is counted, never
recalled: file counts, account counts, row counts read out of the documents
themselves, and bytes.

The account/row counts are deliberately read from the artifacts rather than
from ``state.json``, because the point of the exercise is to establish what is
*on disk now*, not what the run believed it wrote.

Read-only. No provider call.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _bytes_and_files(root: Path, pattern: str = "**/*") -> tuple[int, int]:
    total = count = 0
    if not root.exists():
        return 0, 0
    for path in root.glob(pattern):
        if path.is_file():
            count += 1
            total += path.stat().st_size
    return total, count


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024.0
    return f"{n:.1f}GB"


def _canonical_stats(directory: Path, row_key: str) -> dict[str, Any]:
    """Accounts and rows actually present in a canonical layer."""

    if not directory.is_dir():
        return {"accounts": 0, "rows": 0, "splits": {}}
    accounts = rows = 0
    splits: Counter[str] = Counter()
    for path in sorted(directory.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        accounts += 1
        splits[str(document.get("split"))] += 1
        value = document.get(row_key)
        if isinstance(value, int):
            rows += value
        elif isinstance(document.get("rows"), list):
            rows += len(document["rows"])
    return {"accounts": accounts, "rows": rows, "splits": dict(sorted(splits.items()))}


def _nested_stats(directory: Path, pattern: str) -> dict[str, Any]:
    """Per-account subdirectories and the payload files inside them.

    A subdirectory that exists but holds no payload file is reported
    separately: that is exactly the shape the 2026-09-07 loss left behind, and
    counting directories alone is what made a first report say a layer had
    survived when its contents had not.
    """

    if not directory.is_dir():
        return {"account_dirs": 0, "populated_dirs": 0, "empty_dirs": 0, "files": 0}
    account_dirs = populated = files = 0
    for child in sorted(directory.iterdir()):
        if not child.is_dir():
            continue
        account_dirs += 1
        inner = list(child.glob(pattern))
        if inner:
            populated += 1
            files += len(inner)
    return {
        "account_dirs": account_dirs,
        "populated_dirs": populated,
        "empty_dirs": account_dirs - populated,
        "files": files,
    }


def inventory(root: Path, label: str) -> dict[str, Any]:
    out: dict[str, Any] = {"label": label, "path": str(root), "exists": root.exists()}
    if not root.exists():
        return out

    layers: dict[str, Any] = {}

    raw_bytes, raw_files = _bytes_and_files(root / "raw")
    by_operation: Counter[str] = Counter()
    if (root / "raw").is_dir():
        for path in (root / "raw").iterdir():
            if path.is_file():
                stem = path.name.split("-", 1)[-1]
                by_operation[stem.rsplit(".", 1)[0]] += 1
    layers["raw"] = {
        "files": raw_files,
        "bytes": raw_bytes,
        "bytes_human": _human(raw_bytes),
        "by_operation": dict(sorted(by_operation.items())),
    }

    for name, pattern in (("history", "page-*.json"), ("parsed", "batch-*.json")):
        directory = root / "normalized" / name
        stats = _nested_stats(directory, pattern)
        size, _ = _bytes_and_files(directory)
        stats["bytes"] = size
        stats["bytes_human"] = _human(size)
        layers[f"normalized/{name}"] = stats

    for name, row_key in (("history", "unique_match_count"), ("parsed", "parsed_row_count")):
        directory = root / "canonical" / name
        stats = _canonical_stats(directory, row_key)
        size, files = _bytes_and_files(directory)
        stats.update({"files": files, "bytes": size, "bytes_human": _human(size)})
        layers[f"canonical/{name}"] = stats

    # Pass 2 nests normalized batches directly under normalized/<account>/
    # rather than normalized/parsed/<account>/. Probing only the Pass-1 shape
    # is what made a first pass report this layer as absent when 13,253 files
    # were present.
    flat_normalized = _nested_stats(root / "normalized", "batch-*.json")
    if flat_normalized["files"]:
        size, _ = _bytes_and_files(root / "normalized")
        flat_normalized["bytes"] = size
        flat_normalized["bytes_human"] = _human(size)
        layers["normalized (flat)"] = flat_normalized

    # Pass-2 keeps its canonical documents flat rather than under history/parsed.
    flat = _canonical_stats(root / "canonical", "collected_match_count")
    if flat["accounts"]:
        size, files = _bytes_and_files(root / "canonical", "*.json")
        flat.update({"files": files, "bytes": size, "bytes_human": _human(size)})
        layers["canonical (flat)"] = flat

    for name in ("manifests", "ledgers", "derived"):
        size, files = _bytes_and_files(root / name)
        layers[name] = {"files": files, "bytes": size, "bytes_human": _human(size)}

    out["layers"] = layers
    total, files = _bytes_and_files(root)
    out["total"] = {"files": files, "bytes": total, "bytes_human": _human(total)}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", required=True, metavar="LABEL=PATH")
    parser.add_argument("--out")
    args = parser.parse_args()

    report = []
    for entry in args.root:
        label, _, path = entry.partition("=")
        report.append(inventory(Path(path).expanduser(), label))

    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    for block in report:
        print(f"\n=== {block['label']} ({'present' if block['exists'] else 'ABSENT'})")
        print(f"    {block['path']}")
        for name, layer in (block.get("layers") or {}).items():
            summary = ", ".join(
                f"{k}={v}" for k, v in layer.items() if k not in {"bytes", "by_operation"}
            )
            print(f"    {name:22s} {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Check that local links in the tracker and root documentation resolve."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]

TRACKER_DOCS = ROOT / "docs" / "tracker"
ROOT_DOCS = (
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "ARCHITECTURE.md",
    ROOT / "research" / "README.md",
)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _local_link_target(document: Path, raw: str) -> Path | None:
    destination = raw.strip()
    if destination.startswith("<"):
        destination = destination.split(">", 1)[0][1:]
    else:
        destination = re.split(r'\s+[\"\']', destination, maxsplit=1)[0]
    parsed = urlsplit(destination)
    if parsed.scheme or parsed.netloc:
        return None
    target = unquote(parsed.path)
    if not target:
        return None
    if target.startswith("/"):
        return ROOT / target.lstrip("/")
    return (document.parent / target).resolve()


def main() -> int:
    failures: list[str] = []

    documents = [*ROOT_DOCS, *sorted(TRACKER_DOCS.rglob("*.md"))]
    if not TRACKER_DOCS.exists():
        failures.append("missing tracker documentation tree")

    tracker_links = 0
    for path in documents:
        if not path.exists():
            failures.append(f"missing active doc: {path.relative_to(ROOT)}")
            continue
        for raw_target in LINK_RE.findall(path.read_text(encoding="utf-8")):
            target = _local_link_target(path, raw_target)
            if target is not None:
                tracker_links += 1
                if not target.exists():
                    failures.append(f"broken tracker link in {path.relative_to(ROOT)}: {raw_target}")

    if failures:
        print("docs-check: failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"docs-check: ok ({len(documents)} tracker documents, {tracker_links} local links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Check tracker documentation links and scan active source for the cancelled classifier domain."""

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
ACTIVE_SOURCE_ROOTS = (
    ROOT / "services",
    ROOT / "legacy",
    ROOT / "tests",
    ROOT / "README.md",
    ROOT / "ARCHITECTURE.md",
    ROOT / "docs",
)


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


def _legacy_classifier_surface(path: Path) -> bool:
    """The cancelled report classifier does not prohibit tracker role inference."""
    relative = path.relative_to(ROOT)
    if any(part in {"archive", "_archive", "node_modules", ".next", "dist", "build"}
           for part in relative.parts):
        return False
    exempt_roots = (
        "docs/tracker", "docs/prompts",
        "services/api/app/tracker", "tests/tracker",
    )
    return not any(relative.is_relative_to(prefix) for prefix in exempt_roots)


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

    # The cancelled domain is the CLASSIFIER work, not the archetype surface.
    # V6.1 ships `archetype_contract` as a real, versioned, not-ready interface
    # (`StoryArchetypeModuleV61Schema`, `STORY_ARCHETYPE_CONTRACT_VERSION`), and
    # the story renders it, so the word is no longer evidence of a revival.
    cancelled = re.compile(r"\b(?:classifier|classifiers)\b", re.IGNORECASE)
    for root in ACTIVE_SOURCE_ROOTS:
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx", ".js", ".mjs", ".md"}:
                continue
            if not _legacy_classifier_surface(path):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if cancelled.search(text):
                failures.append(f"cancelled classifier-domain reference in active source: {path.relative_to(ROOT)}")

    if failures:
        print("docs-check: failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"docs-check: ok ({len(documents)} tracker documents, {tracker_links} local links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

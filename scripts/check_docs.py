#!/usr/bin/env python3
"""Check active architecture docs, local links, and generated model coverage."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.behavior.elements.registry import ELEMENT_REGISTRY  # noqa: E402
from app.behavior.patterns.registry import PATTERN_REGISTRY  # noqa: E402

ACTIVE_DOCS = (
    ROOT / "README.md",
    ROOT / "ARCHITECTURE.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "architecture" / "README.md",
    ROOT / "docs" / "architecture" / "free-dna-system.md",
    ROOT / "docs" / "architecture" / "elements.md",
    ROOT / "docs" / "architecture" / "patterns.md",
    ROOT / "docs" / "architecture" / "hero-portfolio.md",
    ROOT / "docs" / "architecture" / "report-flow.md",
    ROOT / "docs" / "architecture" / "data-provenance.md",
    ROOT / "docs" / "architecture" / "model-catalog.md",
    ROOT / "docs" / "evidence-contract.md",
    ROOT / "docs" / "opendota-data-inventory.md",
    ROOT / "docs" / "system-behavior-baseline.md",
)

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FORBIDDEN_ACTIVE_PHRASES = (
    "free-dna-report-2.0.0",
    "free-dna-report-3.0.0",
    "23 elements",
    "15 patterns",
    "psychological diagnosis",
)


def _local_link_target(document: Path, raw: str) -> Path | None:
    target = raw.split("#", 1)[0].split("?", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:", "<")):
        return None
    if target.startswith("/"):
        return ROOT / target.lstrip("/")
    return (document.parent / target).resolve()


def main() -> int:
    failures: list[str] = []
    for path in ACTIVE_DOCS:
        if not path.exists():
            failures.append(f"missing active doc: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in FORBIDDEN_ACTIVE_PHRASES:
            if phrase.casefold() in text.casefold():
                failures.append(f"stale or unsafe phrase in {path.relative_to(ROOT)}: {phrase}")
        for raw_target in LINK_RE.findall(text):
            target = _local_link_target(path, raw_target)
            if target is not None and not target.exists():
                failures.append(f"broken link in {path.relative_to(ROOT)}: {raw_target}")

    catalog = (ROOT / "docs" / "architecture" / "model-catalog.md").read_text(encoding="utf-8")
    for key in (*ELEMENT_REGISTRY, *PATTERN_REGISTRY):
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(key)}(?![A-Za-z0-9_])", catalog) is None:
            failures.append(f"registry key missing from model catalog: {key}")

    generator = ROOT / "scripts" / "generate_dna_model_catalog.py"
    result = subprocess.run(
        [sys.executable, str(generator), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        failures.append(result.stdout.strip() or result.stderr.strip() or "generated catalog is stale")

    if failures:
        print("docs-check: failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("docs-check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

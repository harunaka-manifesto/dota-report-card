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
from app.ingestion.summary_history_contract import (  # noqa: E402
    SUMMARY_HISTORY_PROJECTION,
    request_manifest,
)
from app.player_analysis_v6.constants import (  # noqa: E402
    FINDING_FAMILY_KEYS,
    PUBLIC_ELEMENT_KEYS,
)
from app.player_analysis_v61.copy import SEMANTIC_COPY_REGISTRY  # noqa: E402
from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_REGISTRY  # noqa: E402
from app.player_analysis_v61.supporting_signals import SUPPORTING_SIGNAL_REGISTRY  # noqa: E402
from app.player_analysis_v61.versions import VERSION_SURFACES  # noqa: E402

ACTIVE_DOCS = (
    ROOT / "README.md",
    ROOT / "ARCHITECTURE.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "architecture" / "README.md",
    ROOT / "docs" / "architecture" / "free-dna-system.md",
    ROOT / "docs" / "architecture" / "elements.md",
    ROOT / "docs" / "architecture" / "patterns.md",
    ROOT / "docs" / "architecture" / "pattern-presentation.md",
    ROOT / "docs" / "architecture" / "hero-relationships.md",
    ROOT / "docs" / "architecture" / "hero-knowledge.md",
    ROOT / "docs" / "architecture" / "hero-matchups-and-synergies.md",
    ROOT / "docs" / "architecture" / "hero-portfolio.md",
    ROOT / "docs" / "architecture" / "report-flow.md",
    ROOT / "docs" / "architecture" / "data-provenance.md",
    ROOT / "docs" / "architecture" / "dota-dna-ssot.md",
    ROOT / "docs" / "architecture" / "free-dna-v6-statistics.md",
    ROOT / "docs" / "architecture" / "free-dna-v6.1-feature-graph.md",
    ROOT / "docs" / "architecture" / "deep-diagnostics-v2.md",
    ROOT / "docs" / "architecture" / "model-catalog.md",
    ROOT / "docs" / "decisions" / "0001-free-dna-v6.1-additive-generation.md",
    ROOT / "docs" / "qa" / "free-dna-v6.1-release-gates.md",
    ROOT / "docs" / "operations" / "free-dna-v6.1-release.md",
    ROOT / "docs" / "design" / "free-dna-v6.1-figma-documentation-update-agent-brief.md",
    ROOT / "docs" / "generated" / "free-dna-v6.1-copy-review.md",
    ROOT / "docs" / "evidence-contract.md",
    ROOT / "docs" / "opendota-data-inventory.md",
    ROOT / "docs" / "system-behavior-baseline.md",
)

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ACTIVE_SOURCE_ROOTS = (
    ROOT / "services",
    ROOT / "apps",
    ROOT / "packages",
    ROOT / "tests",
    ROOT / "README.md",
    ROOT / "ARCHITECTURE.md",
    ROOT / "docs",
)
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

    feature_graph = (
        ROOT / "docs" / "architecture" / "free-dna-v6.1-feature-graph.md"
    ).read_text(encoding="utf-8")
    if len(PUBLIC_ELEMENT_KEYS) != 7 or len(FINDING_FAMILY_KEYS) != 5:
        failures.append("V6.1 public ontology must remain exactly 7 Elements and 5 roots")
    if len(SUPPORTING_SIGNAL_REGISTRY) != 128:
        failures.append("V6.1 supporting-signal registry must contain exactly 128 keys")
    if len(SEMANTIC_OUTCOME_REGISTRY) != 29:
        failures.append("V6.1 semantic-outcome registry must contain exactly 29 keys")
    if set(SEMANTIC_COPY_REGISTRY) != set(SEMANTIC_OUTCOME_REGISTRY):
        failures.append("V6.1 semantic copy must cover every outcome exactly")

    for key in (*PUBLIC_ELEMENT_KEYS, *FINDING_FAMILY_KEYS):
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(key)}(?![A-Za-z0-9_])", catalog) is None:
            failures.append(f"V6.1 public key missing from model catalog: {key}")
    for key in SUPPORTING_SIGNAL_REGISTRY:
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(key)}(?![A-Za-z0-9_])", catalog) is None:
            failures.append(f"V6.1 supporting signal missing from model catalog: {key}")
    for key in SEMANTIC_OUTCOME_REGISTRY:
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(key)}(?![A-Za-z0-9_])", catalog) is None:
            failures.append(f"V6.1 outcome missing from model catalog: {key}")
    for surface in VERSION_SURFACES:
        if surface.version not in feature_graph:
            failures.append(f"V6.1 version surface missing from feature graph: {surface.key}")
    for field in SUMMARY_HISTORY_PROJECTION:
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(field)}(?![A-Za-z0-9_])", feature_graph) is None:
            failures.append(f"canonical summary field missing from feature graph: {field}")
    manifest = request_manifest()
    if manifest["physical_request_count"] != 1 or manifest["rank_or_mmr_used"] is not False:
        failures.append("canonical summary manifest violates the Free request boundary")

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

    copy_generator = ROOT / "scripts" / "generate_copy_review_catalog.py"
    copy_result = subprocess.run(
        [sys.executable, str(copy_generator), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if copy_result.returncode:
        failures.append(
            copy_result.stdout.strip()
            or copy_result.stderr.strip()
            or "generated copy review catalog is stale"
        )

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
            if any(part in {"archive", "node_modules", ".next", "dist", "build"} for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if cancelled.search(text):
                failures.append(f"cancelled classifier-domain reference in active source: {path.relative_to(ROOT)}")

    if failures:
        print("docs-check: failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("docs-check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

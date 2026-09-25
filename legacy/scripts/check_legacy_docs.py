#!/usr/bin/env python3
"""Check active legacy report-card docs, local links, and generated model coverage."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "legacy" / "services" / "api"))

from report_card.behavior.elements.registry import ELEMENT_REGISTRY  # noqa: E402
from report_card.behavior.patterns.registry import PATTERN_REGISTRY  # noqa: E402
from report_card.player_analysis_v6.constants import (  # noqa: E402
    FINDING_FAMILY_KEYS,
    PUBLIC_ELEMENT_KEYS,
)
from report_card.player_analysis_v61.copy import SEMANTIC_COPY_REGISTRY  # noqa: E402
from report_card.player_analysis_v61.semantic_outcomes import (  # noqa: E402
    SEMANTIC_OUTCOME_REGISTRY,
)
from report_card.player_analysis_v61.supporting_signals import (  # noqa: E402
    SUPPORTING_SIGNAL_REGISTRY,
)
from report_card.player_analysis_v61.versions import VERSION_SURFACES  # noqa: E402

ACTIVE_DOCS = (
    ROOT / "legacy" / "docs" / "README.md",
    ROOT / "legacy" / "docs" / "architecture" / "README.md",
    ROOT / "legacy" / "docs" / "architecture" / "free-dna-system.md",
    ROOT / "legacy" / "docs" / "architecture" / "elements.md",
    ROOT / "legacy" / "docs" / "architecture" / "patterns.md",
    ROOT / "legacy" / "docs" / "architecture" / "pattern-presentation.md",
    ROOT / "legacy" / "docs" / "architecture" / "hero-relationships.md",
    ROOT / "legacy" / "docs" / "architecture" / "hero-knowledge.md",
    ROOT / "legacy" / "docs" / "architecture" / "hero-matchups-and-synergies.md",
    ROOT / "legacy" / "docs" / "architecture" / "hero-portfolio.md",
    ROOT / "legacy" / "docs" / "architecture" / "report-flow.md",
    ROOT / "legacy" / "docs" / "architecture" / "data-provenance.md",
    ROOT / "legacy" / "docs" / "architecture" / "dota-dna-ssot.md",
    ROOT / "legacy" / "docs" / "architecture" / "stratz-v7-provider-contract.md",
    ROOT / "legacy" / "docs" / "architecture" / "free-dna-v6-statistics.md",
    ROOT / "legacy" / "docs" / "architecture" / "free-dna-v6.1-feature-graph.md",
    ROOT / "legacy" / "docs" / "architecture" / "deep-diagnostics-v2.md",
    ROOT / "legacy" / "docs" / "architecture" / "model-catalog.md",
    ROOT / "legacy" / "docs" / "decisions" / "0001-free-dna-v6.1-additive-generation.md",
    ROOT / "legacy" / "docs" / "qa" / "free-dna-v6.1-release-gates.md",
    ROOT / "legacy" / "docs" / "operations" / "free-dna-v6.1-release.md",
    ROOT / "legacy" / "docs" / "design" / "free-dna-v6.1-figma-documentation-update-agent-brief.md",
    ROOT / "legacy" / "docs" / "generated" / "free-dna-v6.1-copy-review.md",
    ROOT / "legacy" / "docs" / "evidence-contract.md",
    ROOT / "legacy" / "docs" / "agent" / "analytical-learnings-and-gotchas.md",
    ROOT / "legacy" / "docs" / "opendota-data-inventory.md",
    ROOT / "legacy" / "docs" / "system-behavior-baseline.md",
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

    catalog = (ROOT / "legacy" / "docs" / "architecture" / "model-catalog.md").read_text(encoding="utf-8")
    for key in (*ELEMENT_REGISTRY, *PATTERN_REGISTRY):
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(key)}(?![A-Za-z0-9_])", catalog) is None:
            failures.append(f"registry key missing from model catalog: {key}")

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

    feature_graph = (
        ROOT / "legacy" / "docs" / "architecture" / "free-dna-v6.1-feature-graph.md"
    ).read_text(encoding="utf-8")
    for surface in VERSION_SURFACES:
        if surface.version not in feature_graph:
            failures.append(f"V6.1 version surface missing from feature graph: {surface.key}")

    sys.path.insert(0, str(ROOT / "services" / "api"))
    from app.ingestion.summary_history_contract import (  # noqa: E402
        SUMMARY_HISTORY_PROJECTION,
        request_manifest,
    )

    for field in SUMMARY_HISTORY_PROJECTION:
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(field)}(?![A-Za-z0-9_])", feature_graph) is None:
            failures.append(f"canonical summary field missing from feature graph: {field}")
    manifest = request_manifest()
    if manifest["physical_request_count"] != 1 or manifest["rank_or_mmr_used"] is not False:
        failures.append("canonical summary manifest violates the Free request boundary")

    generator = ROOT / "legacy" / "scripts" / "generate_dna_model_catalog.py"
    result = subprocess.run(
        [sys.executable, str(generator), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        failures.append(result.stdout.strip() or result.stderr.strip() or "generated catalog is stale")

    copy_generator = ROOT / "legacy" / "scripts" / "generate_copy_review_catalog.py"
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

    if failures:
        print("check-legacy-docs: failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"check-legacy-docs: ok ({len(ACTIVE_DOCS)} legacy documents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

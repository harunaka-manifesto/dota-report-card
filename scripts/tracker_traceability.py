"""Report SSOT acceptance traceability and verify every cited test exists.

    uv run python -m scripts.tracker_traceability [--strict]

`--strict` exits non-zero when a cited test is missing or a rule lacks a
recognised status. Coverage gaps (partial/uncovered) are reported, not hidden.
"""
from __future__ import annotations

import ast
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "docs/tracker/architecture/evidence/backend-acceptance-traceability.json"
STATUSES = {"covered", "partial", "client_only", "owner_blocked", "uncovered"}


def _test_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    return {node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test")}


def verify() -> tuple[dict[str, int], list[str]]:
    record = json.loads(RECORD.read_text())
    problems: list[str] = []
    cache: dict[str, set[str]] = {}
    for rule in record["rules"]:
        if rule.get("status") not in STATUSES:
            problems.append(f"{rule['id']}: unknown status {rule.get('status')!r}")
        if rule.get("status") == "covered" and not rule.get("tests"):
            problems.append(f"{rule['id']}: covered without tests")
        for node in rule.get("tests", []):
            file, _, name = node.partition("::")
            path = ROOT / file
            if not path.exists():
                problems.append(f"{rule['id']}: missing file {file}")
                continue
            names = cache.setdefault(file, _test_names(path))
            if name.split("[")[0] not in names:
                problems.append(f"{rule['id']}: missing test {node}")
    return dict(Counter(rule["status"] for rule in record["rules"])), problems


def main() -> None:
    counts, problems = verify()
    record = json.loads(RECORD.read_text())
    print(json.dumps(counts, sort_keys=True))
    for status in ("uncovered", "partial"):
        for rule in record["rules"]:
            if rule["status"] == status:
                print(f"{status:9} {rule['id']}: {rule.get('note', '')}")
    for problem in problems:
        print("ERROR", problem)
    if "--strict" in sys.argv and problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

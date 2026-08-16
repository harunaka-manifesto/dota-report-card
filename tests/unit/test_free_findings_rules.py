from __future__ import annotations

from app.findings.copy import copy_lint_value
from app.findings.evaluator import evaluate_free_candidates, evaluate_free_findings
from free_finding_helpers import make_context


def test_rules_are_deterministic_and_publish_receipt_backed_findings() -> None:
    context = make_context()
    first = evaluate_free_candidates(context)
    second = evaluate_free_candidates(context)

    assert [item.as_dict() for item in first] == [item.as_dict() for item in second]
    published = evaluate_free_findings(context)
    assert published
    assert any(item.kind == "strength" for item in published)
    assert all(len(item.evidence) >= 2 for item in published)
    assert all(len(item.evidence_families) >= 2 for item in published)
    assert all(copy_lint_value(item.headline) == [] for item in published)
    assert all(copy_lint_value(item.body) == [] for item in published)
    assert all(copy_lint_value(item.interpretation) == [] for item in published)


def test_candidate_projection_keeps_match_provenance_internal() -> None:
    candidates = evaluate_free_candidates(make_context())

    for candidate in candidates:
        public = candidate.as_dict()
        assert "source_match_ids" in str(public)  # internal test projection retains receipts for QA
        assert all("account_id" not in str(receipt).casefold() for receipt in public["evidence"])

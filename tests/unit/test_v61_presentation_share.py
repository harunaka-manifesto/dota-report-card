from __future__ import annotations

from copy import deepcopy

import pytest
from app.analysis.source import MappingSource
from app.core.config import Settings
from app.main import create_app
from app.player_analysis_v6.story import build_v61_presentation_metadata
from app.reports.dna_assembly_v61 import _apply_v61_presentation
from app.share.service import build_share_svg
from app.storage.repository import InMemoryRepository
from fastapi.testclient import TestClient

PAGE_LABELS = {
    "self-estimate": "Start",
    "identity-reveal": "Shape",
    "pool-evolution": "Pool",
    "combat-expression": "Change",
    "strongest-finding": "After loss",
    "secondary-finding": "Match",
    "recommendation": "Session",
    "hero-mirror": "Signature",
    "deep-diagnostic": "Share",
}


def _report() -> dict[str, object]:
    pages = [
        {
            "id": page_id,
            "available": True,
            "observed": {"finding": {"published": True, "direction": "positive"}},
            "content": {},
            "evidence_refs": ["hero:7", "match:7001", "session:private"],
        }
        for page_id in PAGE_LABELS
    ]
    return {
        "schema_version": "free-dna-report-6.1.0",
        "report_id": "report-private",
        "metadata": {"eligible_matches": 37},
        "identity_summary": {
            "headline": "A measured, flexible shape.",
            "supporting_lines": ["A recurring portfolio thread: 7."],
            "slots": {
                "primary": {"text": "Flexible toolkit"},
                "twist": {"text": "Changes by context"},
                "anchor": {"text": "7"},
            },
        },
        "hero_portfolio": {
            "status": "available",
            "common_thread": "teamfight",
            "evidence_refs": ["hero:7"],
            "heroes": [
                {
                    "hero_id": 7,
                    "display_name": "Axe",
                    "portrait_url": "https://example.test/axe.png",
                    "match_count": 20,
                    "share": 20 / 37,
                    "functional_jobs": ["teamfight", "push"],
                }
            ],
        },
        "findings": [
            {
                "family": "pool_shape",
                "published": True,
                "claim": "Your hero choices cover a wider set of repeatable jobs.",
                "interpretation": "The summary history shows a broad job shape.",
                "evidence_text": "Observed across the summary history.",
            }
        ],
        "share_candidates": [
            {"id": "identity", "kind": "dynamic_identity", "eligible": True, "payload": {}},
            {
                "id": "finding:pool_shape",
                "kind": "strongest_finding",
                "eligible": True,
                "payload": {},
            },
            {"id": "hero-mirror", "kind": "hero_mirror", "eligible": True, "payload": {}},
        ],
        "pages": pages,
        "elements": [{"key": "breadth", "estimate": 0.4}],
        "supporting_evidence": {"pool_shape": {"estimate": 0.2}},
        "selection_audit": {"published": ["pool_shape"]},
        "reproducibility": {"seed": 17},
        "methodology": {"version": "frozen"},
        "quality": {"status": "qualified"},
        "versions": {"report": "free-dna-report-6.1.0"},
    }


def test_v61_presentation_metadata_carries_the_nine_public_beats() -> None:
    for page_id, label in PAGE_LABELS.items():
        metadata = build_v61_presentation_metadata(
            page_id,
            eligible_match_count=37,
            state="qualified",
            evidence_refs=("supporting:summary",),
        )
        assert metadata["chapter_label"] == label
        assert metadata["sample_copy"] == "37 matches. One recurring signal."
        assert metadata["supporting_copy"] == "Here’s what we found in the way you play."
        assert metadata["depth_controls"]["methodology"] == "How we measured this."
        assert metadata["evidence_refs"] == ["supporting:summary"]


def test_v61_projection_preserves_analytical_fields_and_removes_public_ids() -> None:
    report = _report()
    stable_keys = (
        "metadata",
        "elements",
        "findings",
        "supporting_evidence",
        "selection_audit",
        "reproducibility",
        "methodology",
        "quality",
        "versions",
    )
    before = deepcopy({key: report[key] for key in stable_keys})

    _apply_v61_presentation(report)  # type: ignore[arg-type]

    assert {key: report[key] for key in stable_keys} == before
    portfolio = report["hero_portfolio"]  # type: ignore[index]
    assert portfolio["heroes"][0]["display_name"] == "Axe"
    assert portfolio["heroes"][0]["mapped_jobs"] == ["Fight control", "Tower pressure"]
    assert "hero_id" not in repr(portfolio)
    assert "hero:7" not in repr(portfolio)
    assert report["identity_summary"]["slots"]["anchor"]["text"] == "Axe"  # type: ignore[index]
    assert "7" not in repr(report["identity_summary"])  # type: ignore[index]
    assert "match:7001" not in repr(report["pages"])  # type: ignore[index]
    assert "session:private" not in repr(report["pages"])  # type: ignore[index]

    candidates = {item["id"]: item for item in report["share_candidates"]}  # type: ignore[index]
    assert candidates["identity"]["payload"]["title"] == "Your Dota Signature"
    assert candidates["finding:pool_shape"]["payload"]["title"].startswith("Your hero choices")
    assert candidates["hero-mirror"]["payload"]["body"].startswith("Axe")


def test_v61_share_svg_is_schema_versioned_and_eligibility_bound() -> None:
    report = _report()
    _apply_v61_presentation(report)  # type: ignore[arg-type]
    svg, _ = build_share_svg(report, card_type="hero-mirror", show_name=False)

    assert "Axe" in svg
    assert "FREE DNA / SHARE-SVG-6.1.0" in svg
    for private_value in ("report-private", "hero:7", "match:7001", "session:private"):
        assert private_value not in svg

    ineligible = deepcopy(report)
    ineligible["share_candidates"][2]["eligible"] = False  # type: ignore[index]
    with pytest.raises(ValueError, match="not eligible"):
        build_share_svg(ineligible, card_type="hero-mirror", show_name=False)

    v6 = {
        "schema_version": "free-dna-report-6.0.0",
        "identity_summary": {"headline": "A stable shape."},
        "share_candidates": [
            {
                "id": "identity",
                "kind": "dynamic_identity",
                "eligible": True,
                "payload": {"title": "Identity", "body": "Summary"},
            }
        ],
    }
    v6_svg, _ = build_share_svg(v6, card_type="identity", show_name=False)
    assert "FREE DNA / SHARE-SVG-6.0.0" in v6_svg


def test_follow_up_response_is_aggregate_only_and_privacy_safe() -> None:
    repository = InMemoryRepository()
    report_id = repository.save_report(
        account_id=42,
        data_cutoff=100,
        model_version="free-dna-model-6.0.0",
        template_version="templates-6.0.0",
        report={"identity": {"account_id": 42}},
        evidence=[],
    )
    session, token = repository.create_interaction_session(
        report_id,
        recommendation_baseline={"metric": "win_rate", "value": 0.5},
    )
    match_ids = [7001 + index for index in range(5)]
    source = MappingSource(
        player={"profile": {"account_id": 42}},
        matches=[
            {
                "match_id": match_id,
                "game_mode": 1,
                "duration": 1800,
                "won": index % 2 == 0,
                "leaver_status": 0,
                "start_time": 200 + index,
            }
            for index, match_id in enumerate(match_ids)
        ],
        details={},
    )
    client = TestClient(create_app(Settings(), source=source, repository=repository))

    response = client.post(
        f"/v1/report-interactions/{session.session_id}/follow-up",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    serialized = repr(body)
    assert "session_id" not in body
    assert "match_ids" not in serialized
    assert all(str(match_id) not in serialized for match_id in match_ids)
    assert body["guardrail"] == (
        "This compares the next five matching games. It does not claim causality "
        "or change your Signature."
    )

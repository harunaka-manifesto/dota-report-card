from app.share.service import RENDERER_VERSION, build_share_svg, share_cache_key


def _report() -> dict[str, object]:
    return {
        "report_id": "report-42",
        "schema_version": "free-dna-report-5.2.0",
        "identity": {"display_name": "A very long player name that should fit", "avatar_url": None},
        "shares": {
            "final": {
                "strongest_elements": [
                    {"label": "Breadth", "zone": "high"},
                    {"label": "Presence", "zone": "steady"},
                ],
                "strongest_patterns": [{"label": "Same Playbook"}, {"label": "Bounceback"}],
                "hero_portfolio": {
                    "common_thread": "Fight control",
                    "exception_hero": "Earthshaker",
                    "pool_direction": "New heroes. Same taste. Your jobs barely moved.",
                },
                "hero_mirror": {"hero_name": "Mars"},
            }
        },
    }


def test_share_card_uses_midnight_specimen_identity_hierarchy() -> None:
    svg, cache_key = build_share_svg(_report(), card_type="final", show_name=False, show_avatar=False)

    assert RENDERER_VERSION == "share-svg-5.0.0"
    assert cache_key == share_cache_key(
        _report(), card_type="final", show_name=False, show_avatar=False
    )
    assert 'fill="#0B0C0B"' in svg
    assert "fill:#F7F4EC" in svg
    assert 'url(#aurora)' in svg
    assert 'url(#grain)' in svg
    assert "YOUR PLAYING SHAPE" in svg
    for label in ("ELEMENTS", "PATTERNS", "HERO PORTFOLIO", "HERO MIRROR"):
        assert label in svg
    assert "Same Playbook" in svg
    assert "Fight control" in svg
    assert "Earthshaker" in svg
    assert "Mars" in svg
    assert "PRIVATE BY DEFAULT" in svg
    assert "report-42" not in svg


def test_share_card_escapes_personal_copy_and_does_not_render_analytical_proof() -> None:
    report = _report()
    report["identity"] = {"display_name": "<player> & friend", "avatar_url": None}
    final = report["shares"]["final"]  # type: ignore[index]
    final["strongest_patterns"] = [{"label": "<Pattern>"}]  # type: ignore[index]
    svg, _ = build_share_svg(report, card_type="final", show_name=True, show_avatar=False)

    assert "&lt;player&gt; &amp; friend" in svg
    assert "&lt;Pattern&gt;" in svg
    assert "<player>" not in svg
    assert "<Pattern>" not in svg
    for term in ("confidence", "coverage", "evidence", "provenance", "cohort", "sample size"):
        assert term not in svg.lower()


def test_v6_share_cards_require_server_eligibility_and_scan_rendered_copy() -> None:
    report = {
        "report_id": "v6-report-42",
        "schema_version": "free-dna-report-6.0.0",
        "identity": {"display_name": "V6 player"},
        "identity_summary": {"headline": "Your pool covers a compact set of jobs."},
        "share_candidates": [
            {
                "id": "identity",
                "kind": "dynamic_identity",
                "eligible": True,
                "payload": {"title": "Compact toolkit", "reason": "High-confidence observed summary"},
            },
            {
                "id": "hero-mirror",
                "kind": "hero_mirror",
                "eligible": False,
                "payload": {"title": "Mirror", "reason": "Not enough evidence"},
            },
        ],
    }
    svg, cache_key = build_share_svg(report, card_type="identity", show_name=False)
    assert "COMPACT TOOLKIT" in svg
    assert "V6 player" not in svg
    assert cache_key

    import pytest

    with pytest.raises(ValueError, match="not eligible"):
        build_share_svg(report, card_type="hero-mirror")

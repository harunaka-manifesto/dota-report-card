from pathlib import Path

from scripts.check_docs import ROOT, _legacy_classifier_surface, _local_link_target


def test_document_links_and_legacy_scope(tmp_path: Path) -> None:
    document = tmp_path / "README.md"
    target = tmp_path / "a b.md"
    target.touch()
    assert _local_link_target(document, 'a%20b.md#heading "title"') == target
    assert _local_link_target(document, "<a b.md#heading>") == target
    assert _local_link_target(document, "#heading") is None
    assert _local_link_target(document, "https://example.com/missing") is None
    assert _local_link_target(document, "mailto:person@example.com") is None
    missing = _local_link_target(document, "missing.md")
    assert missing is not None and not missing.exists()
    assert _legacy_classifier_surface(ROOT / "legacy/services/api/report_card/player_analysis_v61/copy.py")
    assert _legacy_classifier_surface(ROOT / "tests/unit/test_legacy.py")
    assert not _legacy_classifier_surface(ROOT / "docs/tracker/app_foundation/SSOT.md")
    assert not _legacy_classifier_surface(ROOT / "services/api/app/tracker/roles.py")
    assert not _legacy_classifier_surface(ROOT / "tests/tracker/test_roles.py")
    assert not _legacy_classifier_surface(ROOT / "docs/prompts/example.md")

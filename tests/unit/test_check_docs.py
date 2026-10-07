from pathlib import Path

from scripts.check_docs import _local_link_target


def test_document_link_targets_resolve(tmp_path: Path) -> None:
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

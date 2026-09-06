"""A research corpus may not live on volatile storage.

These tests exist because it did. On 2026-09-07 the Pass-1 history corpus was
lost from a path that *looked* durable -- ``<repo>/.local/corpora/...`` -- and
was a symlink into ``/private/tmp``. The test that matters most here is the
symlink one: a guard that only inspects the path as written would have passed
the exact configuration that lost the data.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.player_analysis_v7.research.durability import (
    OVERRIDE_ACKNOWLEDGEMENT,
    OVERRIDE_ENV,
    VOLATILE_ROOTS,
    VolatileCorpusRoot,
    assert_durable_corpus_root,
    is_volatile,
)

#: The four roots the owner required be covered.
GUARDED_PURPOSES = (
    "collector output root",
    "corpus loader root",
    "analysis runner root",
    "resume/checkpoint root",
)


@pytest.mark.parametrize("root", VOLATILE_ROOTS)
def test_every_declared_volatile_root_is_detected(root: str) -> None:
    assert is_volatile(f"{root}/some-corpus")


@pytest.mark.parametrize("purpose", GUARDED_PURPOSES)
def test_each_guarded_purpose_refuses_a_volatile_root(purpose: str) -> None:
    with pytest.raises(VolatileCorpusRoot) as excinfo:
        assert_durable_corpus_root("/private/tmp/whatever/corpora", purpose=purpose)
    assert purpose in str(excinfo.value)


def test_a_durable_path_is_returned_resolved(tmp_path: Path) -> None:
    resolved = assert_durable_corpus_root(tmp_path, purpose="corpus loader root")
    assert resolved == tmp_path.resolve()


def test_a_symlink_into_volatile_storage_is_caught(tmp_path: Path) -> None:
    """The 2026-09-07 configuration exactly: a durable-looking path whose
    target was volatile. A string check passes this; only resolution catches
    it."""

    volatile_target = Path("/private/tmp")
    link = tmp_path / "local"
    link.symlink_to(volatile_target)

    assert not is_volatile(tmp_path)  # the containing directory is fine
    assert is_volatile(link)  # the link is not
    with pytest.raises(VolatileCorpusRoot):
        assert_durable_corpus_root(link / "corpora", purpose="corpus loader root")


def test_the_error_says_the_check_follows_symlinks(tmp_path: Path) -> None:
    """Whoever hits this needs to know why a path that reads as durable was
    rejected, or they will conclude the guard is broken."""

    with pytest.raises(VolatileCorpusRoot, match="follows symlinks"):
        assert_durable_corpus_root("/tmp/corpora", purpose="collector output root")


def test_the_error_points_at_the_incident_record() -> None:
    with pytest.raises(VolatileCorpusRoot, match="v7-corpus-loss-incident-2026-09-07"):
        assert_durable_corpus_root("/tmp/corpora", purpose="analysis runner root")


# --------------------------------------------------------------------------
# the override
# --------------------------------------------------------------------------


def test_the_override_permits_a_volatile_root(monkeypatch) -> None:
    monkeypatch.setenv(OVERRIDE_ENV, OVERRIDE_ACKNOWLEDGEMENT)
    assert assert_durable_corpus_root("/tmp/corpora", purpose="collector output root")


def test_a_truthy_value_is_not_enough(monkeypatch) -> None:
    """An override that accepts "1" gets typed by reflex. This one has to be
    meant."""

    for value in ("1", "true", "yes", "TRUE", ""):
        monkeypatch.setenv(OVERRIDE_ENV, value)
        with pytest.raises(VolatileCorpusRoot):
            assert_durable_corpus_root("/tmp/corpora", purpose="collector output root")


def test_the_override_is_case_and_whitespace_forgiving(monkeypatch) -> None:
    monkeypatch.setenv(OVERRIDE_ENV, f"  {OVERRIDE_ACKNOWLEDGEMENT.upper()}  ")
    assert assert_durable_corpus_root("/tmp/corpora", purpose="corpus loader root")


def test_the_acknowledgement_states_the_consequence() -> None:
    """A phrase that does not say what is being accepted is a password, not an
    acknowledgement."""

    assert "deleted" in OVERRIDE_ACKNOWLEDGEMENT


# --------------------------------------------------------------------------
# the guard is actually wired in
# --------------------------------------------------------------------------


def test_the_corpus_loader_refuses_a_volatile_root() -> None:
    from app.player_analysis_v7.research.corpus import CorpusError, corpus_paths

    with pytest.raises((VolatileCorpusRoot, CorpusError)):
        corpus_paths("/private/tmp/not-a-corpus")


def test_the_freeze_loader_refuses_a_volatile_root() -> None:
    from app.player_analysis_v7.research.corpus import CorpusError, freeze_paths

    with pytest.raises((VolatileCorpusRoot, CorpusError)):
        freeze_paths("/private/tmp/not-a-freeze")

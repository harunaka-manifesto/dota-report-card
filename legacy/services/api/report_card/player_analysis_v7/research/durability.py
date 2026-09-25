"""Refuse to keep a research corpus on volatile storage.

On 2026-09-07 the Pass-1 history corpus was lost from
``/private/tmp/dota-report-card-v7-research/.local`` -- roughly 2,900 provider
requests of irreplaceable data, gone at every layer
(``legacy/docs/evidence/v7-corpus-loss-incident-2026-09-07.md``). This module exists
so that cannot happen quietly a second time.

**The check resolves symlinks, and that is the whole point.** The lost corpus
was reached through a path that looked entirely durable:
``<repo>/.local/corpora/stratz/...`` -- a symlink whose target was under
``/private/tmp``. Any guard matching on the literal path string would have
passed it. ``Path.resolve()`` is what makes this a real invariant rather than a
spelling check.

There is an override, because an emergency is a real thing, but it is
deliberately awkward: an environment variable set to an exact acknowledgement
phrase. A truthy ``1`` would get typed by reflex; a sentence has to be meant.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Filesystem roots that do not survive a reboot, a cleaner, or a bad night.
#: Stored resolved, since that is what they are compared against.
VOLATILE_ROOTS: tuple[str, ...] = (
    "/tmp",
    "/private/tmp",
    "/var/tmp",
    "/private/var/tmp",
)

#: Set to ``OVERRIDE_ACKNOWLEDGEMENT`` to permit a volatile root anyway.
OVERRIDE_ENV = "V7_ALLOW_VOLATILE_CORPUS_ROOT"

OVERRIDE_ACKNOWLEDGEMENT = "i accept that this corpus can be deleted without warning"


class VolatileCorpusRoot(RuntimeError):
    """A corpus path resolved onto storage that does not survive."""


def _override_granted() -> bool:
    value = os.environ.get(OVERRIDE_ENV, "")
    return value.strip().lower() == OVERRIDE_ACKNOWLEDGEMENT


def is_volatile(path: str | os.PathLike[str]) -> bool:
    """Whether ``path`` resolves onto a volatile root, symlinks followed."""

    resolved = Path(path).expanduser().resolve()
    for root in VOLATILE_ROOTS:
        root_path = Path(root)
        if resolved == root_path or root_path in resolved.parents:
            return True
    return False


def assert_durable_corpus_root(
    path: str | os.PathLike[str], *, purpose: str
) -> Path:
    """Return ``path`` resolved, or raise if it lives on volatile storage.

    ``purpose`` names the caller -- collector output, corpus loader, analysis
    runner, resume checkpoint -- so the error says which of them was about to
    write somewhere it should not.
    """

    resolved = Path(path).expanduser().resolve()
    if not is_volatile(resolved):
        return resolved
    if _override_granted():
        return resolved
    raise VolatileCorpusRoot(
        f"{purpose} resolves to {resolved}, which is volatile storage. "
        "A V7 corpus was lost from exactly such a path on 2026-09-07; see "
        "legacy/docs/evidence/v7-corpus-loss-incident-2026-09-07.md. Note that the "
        "path as written may look durable -- this check follows symlinks. "
        f"To proceed anyway set {OVERRIDE_ENV} to the exact phrase "
        f"{OVERRIDE_ACKNOWLEDGEMENT!r}."
    )


__all__ = [
    "OVERRIDE_ACKNOWLEDGEMENT",
    "OVERRIDE_ENV",
    "VOLATILE_ROOTS",
    "VolatileCorpusRoot",
    "assert_durable_corpus_root",
    "is_volatile",
]

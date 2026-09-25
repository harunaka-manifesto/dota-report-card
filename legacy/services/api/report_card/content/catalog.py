"""Versioned, provider-neutral Free DNA copy catalog."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def load_free_dna_copy() -> dict[str, Any]:
    path = Path(__file__).with_name("free_dna") / "en.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not value.get("copy_version"):
        raise ValueError("Free DNA copy catalog is missing copy_version")
    return value


def copy_version() -> str:
    return str(load_free_dna_copy()["copy_version"])


@lru_cache(maxsize=1)
def load_free_dna_semantic_copy() -> dict[str, Any]:
    """Load the finite v5.3 semantic outcome and recommendation library."""

    path = Path(__file__).with_name("free_dna") / "semantic_en.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not value.get("copy_version"):
        raise ValueError("Free DNA semantic copy catalog is missing copy_version")
    return value


def semantic_copy_version() -> str:
    return str(load_free_dna_semantic_copy()["copy_version"])

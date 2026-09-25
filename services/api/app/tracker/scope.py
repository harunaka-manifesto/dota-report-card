"""The one place entitlement meets persisted history (ADR 0004).

Free History = bootstrap + every match from the original link date onward;
Pro History = everything retained. Acquisition, feature extraction, metrics,
roles and insights never read scope; they receive the entitled history this
filter selects from already-persisted, identically computed results.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement, FromClause, or_, true


def entitled(profile: Any, links: FromClause) -> ColumnElement[bool]:
    if profile["active_scope"] == "PRO":
        return true()
    return or_(links.c.origin == "BOOTSTRAP", links.c.provider_started_at >= profile["original_linked_at"])


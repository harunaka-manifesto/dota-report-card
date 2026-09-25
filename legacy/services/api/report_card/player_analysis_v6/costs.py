"""Free v6 cost invariants."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import FreeCostLedger


def new_free_cost_ledger(*, history_reads: int = 0) -> FreeCostLedger:
    return FreeCostLedger(history_reads=history_reads)


def free_cost_invariant(value: FreeCostLedger | Mapping[str, Any]) -> bool:
    if isinstance(value, FreeCostLedger):
        return value.compliant
    try:
        history = value.get("history_reads", value.get("history_requests", 0))
        detail = value.get("detail_reads", value.get("detail_requests", 0))
        parse = value.get("parse_calls", value.get("parse_requests", 0))
        limits = value.get("limits", {})
        return (
            int(history) <= 1
            and int(detail) == 0
            and int(parse) == 0
            and int(limits.get("detail_reads", limits.get("detail_requests", 0))) == 0
            and int(limits.get("parse_calls", limits.get("parse_requests", 0))) == 0
        )
    except (AttributeError, TypeError, ValueError):
        return False


def assert_free_cost(value: FreeCostLedger | Mapping[str, Any]) -> None:
    if not free_cost_invariant(value):
        raise AssertionError("Free v6 permits one history read and zero detail/parse calls")


validate_free_cost = free_cost_invariant
is_free_cost_compliant = free_cost_invariant


__all__ = [
    "FreeCostLedger",
    "new_free_cost_ledger",
    "free_cost_invariant",
    "assert_free_cost",
    "validate_free_cost",
    "is_free_cost_compliant",
]

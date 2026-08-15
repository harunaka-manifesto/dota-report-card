from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class CostPolicy:
    """Deployment-specific relative units, not a baked-in monetary price."""

    history_read_units: float = 1.0
    detail_read_units: float = 1.0
    parse_request_units: float = 5.0
    parse_poll_units: float = 0.1

    def units_for(self, operation: str) -> float:
        values = {
            "history": self.history_read_units,
            "detail": self.detail_read_units,
            "parse": self.parse_request_units,
            "parse_status": self.parse_poll_units,
        }
        if operation not in values:
            raise ValueError(f"Unknown data-cost operation: {operation}")
        return max(0.0, values[operation])


@dataclass(slots=True)
class DataCostLedger:
    history_requests: int = 0
    detail_requests: int = 0
    parse_requests: int = 0
    parse_status_requests: int = 0
    cache_hits: int = 0
    existing_deep_matches: int = 0
    estimated_cost_units: float = 0.0
    monetary_cost_estimate: Decimal | None = None
    events: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        operation: str,
        *,
        policy: CostPolicy,
        match_id: int | None = None,
        cache_hit: bool = False,
        existing: bool = False,
        units: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> float:
        field_by_operation = {
            "history": "history_requests",
            "detail": "detail_requests",
            "parse": "parse_requests",
            "parse_status": "parse_status_requests",
        }
        field_name = field_by_operation.get(operation)
        if field_name is None:
            raise ValueError(f"Unknown data-cost operation: {operation}")
        if not cache_hit and not existing:
            setattr(self, field_name, getattr(self, field_name) + 1)
        if cache_hit:
            self.cache_hits += 1
        if existing:
            self.existing_deep_matches += 1
        charge = max(0.0, policy.units_for(operation) if units is None else units)
        self.estimated_cost_units += charge
        self.events.append(
            {
                "operation": operation,
                "match_id": match_id,
                "estimated_units": charge,
                "cache_hit": cache_hit,
                "existing": existing,
                "metadata": dict(metadata or {}),
            }
        )
        return charge

    def as_dict(self) -> dict[str, Any]:
        return {
            "history_requests": self.history_requests,
            "detail_requests": self.detail_requests,
            "parse_requests": self.parse_requests,
            "parse_status_requests": self.parse_status_requests,
            "cache_hits": self.cache_hits,
            "existing_deep_matches": self.existing_deep_matches,
            "estimated_cost_units": round(self.estimated_cost_units, 4),
            "monetary_cost_estimate": (
                str(self.monetary_cost_estimate) if self.monetary_cost_estimate is not None else None
            ),
            "events": list(self.events),
        }


CostLedger = DataCostLedger


@dataclass(frozen=True, slots=True)
class BudgetDecision:
    allowed: bool
    operation: str
    estimated_cost: float
    reason: str


@dataclass(slots=True)
class BudgetState:
    max_parse_requests: int = 0
    max_data_cost_per_report: float = 50.0
    parse_requests: int = 0
    estimated_cost_units: float = 0.0

    def can_spend(
        self,
        operation: str,
        estimated_cost: float,
        *,
        hypothesis_priority: float = 1.0,
    ) -> BudgetDecision:
        cost = max(0.0, estimated_cost)
        if operation == "parse" and self.parse_requests >= max(0, self.max_parse_requests):
            return BudgetDecision(False, operation, cost, "MAX_PARSE_REQUESTS")
        if self.estimated_cost_units + cost > max(0.0, self.max_data_cost_per_report):
            return BudgetDecision(False, operation, cost, "MAX_DATA_COST_PER_REPORT")
        if hypothesis_priority <= 0:
            return BudgetDecision(False, operation, cost, "HYPOTHESIS_NOT_ACTIONABLE")
        return BudgetDecision(True, operation, cost, "WITHIN_BUDGET")

    def spend(self, operation: str, estimated_cost: float) -> BudgetDecision:
        decision = self.can_spend(operation, estimated_cost)
        if decision.allowed:
            self.estimated_cost_units += decision.estimated_cost
            if operation == "parse":
                self.parse_requests += 1
        return decision

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_parse_requests": self.max_parse_requests,
            "max_data_cost_per_report": self.max_data_cost_per_report,
            "parse_requests": self.parse_requests,
            "estimated_cost_units": round(self.estimated_cost_units, 4),
        }

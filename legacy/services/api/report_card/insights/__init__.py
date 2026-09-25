"""Registered insight definitions, gates, ranking, and deterministic templates."""

from report_card.insights.evaluator import InsightContext, evaluate_insights
from report_card.insights.registry import INSIGHT_REGISTRY

__all__ = ["INSIGHT_REGISTRY", "InsightContext", "evaluate_insights"]

"""Registered insight definitions, gates, ranking, and deterministic templates."""

from app.insights.evaluator import InsightContext, evaluate_insights
from app.insights.registry import INSIGHT_REGISTRY

__all__ = ["INSIGHT_REGISTRY", "InsightContext", "evaluate_insights"]

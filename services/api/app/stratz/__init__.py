"""STRATZ transport, canonical models, GraphQL queries and the fail-closed
deep-match normalizer shared by the fresh V7/tracker STRATZ path.

The legacy V7 provider aggregate (``StratzProvider`` and its re-exports,
plus the batch-normalizer used only by that aggregate) lives in
``report_card.stratz`` because it is reachable only from the legacy /v1 API
composition root, not from ``app.tracker``.
"""

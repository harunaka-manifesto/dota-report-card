"""Legacy report-card ingestion normalization: eligibility filtering and
parse coverage that only the deprecated /v1 pipeline uses.

``app.ingestion`` (the fresh/shared package) keeps ``summary_history_contract``
and ``summary_normalize``, which the fresh STRATZ path also depends on.
"""

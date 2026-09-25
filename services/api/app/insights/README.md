# Legacy report insight registry — not the tracker insight engine

This package serves the live report-card product (`app/analysis`, `app/reports`). It is not
the V1 post-match insight engine. The tracker implements the normative annex
(`docs/tracker/_archive/engine_specs/POST-MATCH-INSIGHTS-SSOT.md` and its JSON contract) in
`app/tracker/insights.py`. Keep this package unchanged for persisted-report compatibility.

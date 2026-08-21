# System behavior baseline

The active baseline is Free DNA v5:

- One bounded summary-history read.
- Exactly 18 Elements and 11 active Patterns in every validated report.
- Previous 365 days of usable summary history, with recency and session-balanced weighting.
- Independent Hero Portfolio with four guarded insights.
- Ordered story ending in Hero Mirror, final share, and Deep Dive teaser.
- detail_requests = 0 and parse_requests = 0.
- No raw rows, source match IDs, private metrics, or account IDs in public output.
- Deterministic ranking, copy, version fingerprints, and cache keys.

The contract is enforced by the v5 Pydantic schema, registry validation,
summary-only source tests, and the web story fixture.

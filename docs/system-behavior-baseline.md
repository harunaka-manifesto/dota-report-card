# System behavior baseline

The active baseline is Free DNA v5.2 at repository baseline `3670c49`:

- One bounded summary-history read.
- Exactly 18 Elements and 11 active Patterns in every validated report.
- Previous 365 days of usable summary history, with recency and session-balanced weighting.
- Independent Hero Portfolio with four guarded insights.
- Ordered story ending in Hero Mirror, final share, and Deep Dive teaser.
- detail_requests = 0 and parse_requests = 0.
- No raw rows, source match IDs, private metrics, or account IDs in public output.
- Deterministic ranking, copy, version fingerprints, and cache keys.
- `pattern-outcomes-5.2.0` covers 32 semantic outcome branches across P01–P11;
  `hero-recommendations-semantic-1.1.0` covers 14 recommendation IDs.
- Active semantic copy is `free-dna-semantic-copy-5.3.0`; the
  `free-dna-copy-5.5.0` catalog is retained for historical compatibility.
- Hero knowledge uses the `hero-knowledge-semantic-freeze-full-roster-v1`
  snapshot declared by the checked-in manifest; structural taxonomy fallback is
  compatibility-only for unavailable or unapproved records.

The contract is enforced by the v5 Pydantic schema, registry validation,
summary-only source tests, and the web story fixture.

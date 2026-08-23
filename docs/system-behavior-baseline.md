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

## Additive v6 baseline

The v6 path is implemented but opt-in and disabled by default. It preserves the
v5 baseline above and adds a strict `free-dna-report-6.0.0` validator, seven
summary-only Elements, five FDR-controlled finding families, a nine-beat story,
and token-protected interaction state. Free v6 has one history request and
exactly zero detail, parse, and parse-status requests.

Startup is fail-closed when the flag is enabled: both
`FREE_DNA_V6_BASELINE_ARTIFACT` and `FREE_DNA_V6_THRESHOLD_ARTIFACT` must point
to validated, versioned, non-MMR artifacts. The checked-in fixtures are not
production calibration. A private 1,130-profile corpus has produced 791-player
training candidates and a sealed 339-player holdout; those candidates are not
approved production artifacts until measured synthetic/holdout gates, external
review, promotion checks, and operator authorization pass.

Deep v2 is an explicitly selected continuation from an immutable report
question. Its actual acquisition budget is at most 25 detail reads, 25 parses,
and 160 relative cost units; unsupported evidence yields a recorded abstention.

# Free DNA system

## Product chain

summary history → sessions/features → Elements → Patterns → Hero Portfolio → report story

The API owns normalization, scoring, eligibility, ranking, assembly, and
strict validation. The web app presents the immutable snapshot and records
privacy-safe interaction events.

## Stages

1. Resolve a public player and fetch one bounded summary-history window.
2. Normalize common-eligible rows while retaining nullable fields.
3. Infer sessions and derive reusable summary features.
4. Score the exact 17 Element registry entries.
5. Evaluate the exact 14 Pattern registry entries.
6. Evaluate Hero Portfolio independently from Element scores.
7. Rank deterministic highlights and assemble ordered v4 pages.
8. Validate free-dna-report-4.0.0, persist the public snapshot, and expose
   the final share card.

## Boundaries

Free has no match-detail reads, no replay parsing, no browser-side scoring, and
no fallback that fills unavailable evidence. A limited history can produce a
valid partial report. Deep Scan is a separate opt-in pipeline.

## Versioning

The report carries versions for session policy, features, behavior model,
Element and Pattern registries, Hero Portfolio, Hero Mirror, story, copy,
template, share renderer, and the compatibility fingerprint.

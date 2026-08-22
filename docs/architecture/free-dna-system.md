# Free DNA system

## Product chain

summary history → sessions/features → Elements → Patterns → Hero Portfolio → report story

The API owns normalization, scoring, eligibility, ranking, assembly, and
strict validation. The web app presents the immutable snapshot and records
privacy-safe interaction events.

## Stages

1. Resolve a public player and fetch one previous-365-day summary-history window.
2. Normalize common-eligible rows while retaining nullable fields.
3. Infer sessions and derive reusable summary features.
4. Score the exact 18 Element registry entries.
5. Evaluate the exact 11 active Pattern registry entries.
6. Evaluate Hero Portfolio independently from Element scores.
7. Rank deterministic highlights, classify Pattern presentation outcomes, and
   assemble ordered v5.2 pages.
8. Validate `free-dna-report-5.2.0`, persist the public snapshot, and expose
   the final share card.

## Boundaries

Free has no match-detail reads, no replay parsing, no browser-side scoring, and
no fallback that fills unavailable evidence. A limited history can produce a
valid partial report. The raw summary-history cache is short-lived and explicit
(120 seconds by default); derived reports remain keyed by their input snapshot
and model fingerprint. Deep Scan is a separate opt-in pipeline.

Pattern qualification is finite and registry-owned: only the Element zones in
the winning clause contribute authoritative confidence, coverage, quality,
receipts, blockers, and strength. Coverage is checked against each Element's
own registry minimum, and selected Elements must also meet the 0.45 confidence
gate. Actions are downstream evidence consumers with resolved, fallback, and
unresolved states; action evidence never changes Pattern qualification.

## Versioning

The report carries versions for model, session policy, recency weighting,
performance proxy, features, behavior model,
Element and Pattern registries, Pattern ranking and actions, hero taxonomy,
hero relationships and expressions, player-relative reliability, matchup and
synergy artifacts, situations, Hero Portfolio configuration, Hero Mirror,
story, copy, Pattern presentation, template, share renderer, and the
compatibility fingerprint. Presentation thresholds are deterministic and
centralized; the web app never invents its own display bands. The normalized
hero-knowledge provider is an independent seam with its own snapshot version.
The comparable-baseline resolver has its own version and is included in the
report versions and analysis fingerprint. Historical v5.0 snapshots remain
readable with their original versions and payload fields.

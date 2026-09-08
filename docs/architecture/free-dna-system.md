# Free DNA system

This document describes the retained V5.2-compatible OpenDota runtime path.
V7 is a separate STRATZ-native staging lineage; see the [V7 provider
contract](stratz-v7-provider-contract.md) and [analytical learnings and
gotchas](../../docs/agent/analytical-learnings-and-gotchas.md).

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
story, legacy and semantic copy, semantic outcomes and recommendations, Pattern
presentation, template, share renderer, and the compatibility fingerprint.
Presentation thresholds are deterministic and centralized; the web app never
invents its own display bands. The normalized hero-knowledge provider is an
independent seam with the active full-roster snapshot version declared by the
manifest. The ten-hero pilot snapshot is retained as historical compatibility
evidence, not as the active roster denominator.
The comparable-baseline resolver has its own version and is included in the
report versions and analysis fingerprint. Historical v5.0 snapshots remain
readable with their original versions and payload fields. Historical v4, v5.0,
and v5.1 snapshots are compatibility artifacts, not active baselines.

## V6.1 generation boundary

V6.1 is selected only for new generation when `FREE_DNA_V61_ENABLED=true` and
validated V6.1 artifacts are present. The V6 and V6.1 generation flags are
mutually exclusive. V6.1 reuses the summary-only product boundary but owns a
separate canonical one-request cache key, projection audit, version matrix,
schema validator, compatibility fingerprint, and share renderer. See the
[V6.1 feature graph](free-dna-v6.1-feature-graph.md) for its complete 7/5
ontology, private graph, semantic outcomes, and release states.

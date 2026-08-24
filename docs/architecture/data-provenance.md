# Data provenance

## Free source boundary

The public Free report is derived from one bounded summary-history request plus
the public profile. Raw payloads remain server-side. The public projection
carries a history hash, date bounds, counts, quality warnings, receipts, and
version fingerprints.

The cost contract is strict:

~~~json
{
  "detail_requests": 0,
  "parse_requests": 0
}
~~~

## Privacy

Public output omits account IDs, source match IDs, normalized/private record
references, raw scorer metrics, and raw match rows. Display name and avatar
are sanitized. Share cards never include a raw identifier.

## Evidence handling

Missing source fields remain missing through normalization, feature coverage,
Element scoring, Pattern qualification, and Portfolio eligibility. Each layer
may lower confidence or return unavailable/no-clear; it cannot create a
synthetic neutral value.

## Hero action artifacts

P01 and P02 are derived from the reviewed hero taxonomy, bounded hero history,
and explicitly versioned relationship, expression, and reliability artifacts.
Matchup and teammate examples are read from checked-in aggregate snapshots
only; when those snapshots do not clear their confidence gate, the report
emits a useful situation and an explicit limitation instead of inventing named
examples. The action provenance versions are included in the Free analysis
fingerprint.

Drift, Recovery, and their session-aware actions use the same versioned
leave-group-out comparable-baseline resolver. It reports the selected fallback
level and reference sample, excludes the target session, and is included in
report reproducibility metadata as `context_baseline_version`. Recovery's final
delta is clustered once per independent session before the recency-weighted
aggregate is calculated.

## Hero knowledge snapshots

Hero knowledge follows the source hierarchy in [Hero data sources](hero-data-sources.md):
Valve owns official mechanics, OpenDota contributes bounded aggregate empirical
context, optional Valve Dota Plus enrichment is not a v5.2 dependency, and the
existing DotaCoach corpus remains editorial/research evidence. Raw source
payloads, normalized facts, derived characteristics, and approved editorial
fields are separate layers.

Every generated knowledge record carries a field-source map, source snapshot
versions, fetch timestamps, raw hashes where applicable, and derivation rule
versions. The API consumes the frozen snapshot through
`HeroKnowledgeRepository`; it does not make source requests during report
generation. Unknown fields remain unknown rather than becoming neutral values.

## V6.1 canonical projection

V6.1 makes the physical request contract executable in
`ingestion/summary_history_contract.py`: one request, one exact 20-field
projection, a previous-365-day window, provider-limit completeness state,
required/optional coverage, and raw/normalized hashes. Runtime, calibration,
fixtures, and documentation must use that owner. Optional context below 80%
coverage cannot support a public conditional claim. `average_rank`,
`rank_tier`, rank, MMR, and skill-bracket fields are forbidden analytical
inputs.

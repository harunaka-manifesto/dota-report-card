# Evidence contract

## Free v3 summary boundary

The active Free report is `free-dna-report-3.0.0`. Its evidence chain is:

`summary observation → Element → Pattern → context Archetype → Finding`

An Element carries a bounded score or an explicit unavailable status, confidence,
sample size, coverage, receipts, confounders, and missing-data reasons. A
qualified Pattern must name the upstream Elements it connects. A context
Archetype is classified separately inside its registered group; close groups can
remain unclassified. A public Finding names its supporting Elements and source
Patterns and keeps its interpretation separate from the receipts.

Free receipts are summary-history evidence. They do not imply a replay read,
causal explanation, hidden intent, or a percentile against an invented cohort.
The report’s methodology and cost sections say that the Free path used one
bounded history read and zero match-detail/replay-parse requests. Private source
match IDs and raw metrics are stripped before the public report is validated.

v1/v2 evidence objects remain readable for stored snapshots; this section is the
contract for new Free analyses.

Every evaluated insight is persisted as an evidence object, whether it is published or suppressed. The object contains stable insight and concept IDs, report scope, player and cohort metrics, unit, match/situation/parsed-match denominators, parse coverage, role certainty, selected cohort fallback, interval, confidence, confounders, action target, source match IDs, and feature/cohort/model/template versions.

The provenance map links the same source match IDs to the raw OpenDota payload endpoint, normalized match record, and derived feature record. A published card is a projection of this object; it does not recalculate metrics.

Templates may choose approved phrasing, but may not add findings, modify values or denominators, omit material confounders, or upgrade confidence.

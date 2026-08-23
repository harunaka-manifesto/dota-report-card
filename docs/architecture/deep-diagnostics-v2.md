# Deep diagnostics v2

Deep is an explicit continuation from a published Free v6 diagnostic question.
The report stores the complete server-authored question specification—primary
hypothesis, optional secondary hypothesis, evidence reuse, data families,
positive/negative/control definitions, and sample targets. The client submits
only `diagnostic_question_id`; the API resolves that exact immutable object and
persists it in the Deep job metadata.

## Acquisition

Acquisition has two bounded stages:

1. Stage A selects up to 25 evidence matches for detail hydration. Cached detail
   and parsed evidence are preferred and cost zero. New detail candidates need
   marginal information gain ≥0.05.
2. Stage B evaluates only the Stage-A matches for missing evidence families.
   New parses need cost-adjusted information gain ≥0.10 and are executed through
   the source parse transport. Parse status polling is recorded when the
   adapter exposes it.

The actual ledger—not the estimate in the selection plan—is authoritative:
maximum 25 detail reads, maximum 25 parse requests, and maximum 160 relative
cost units. If a parse transport is unavailable, the job records parse
unavailability and abstains when sufficiency cannot be met.

## Evidence and output

Moderate resolution needs at least three positive, negative, and control
examples plus complete required-family coverage. High resolution needs eight of
each and practical effect ≥0.15. An insufficient result includes an explicit
stopping/abstention reason and no behavior-change recommendation.

Resolved output separates observation, positive evidence, negative evidence,
control evidence, bounded interpretation, unresolved alternatives, a
context-specific deterministic recommendation, and a verification rule. It
does not claim causality or update stable identity.

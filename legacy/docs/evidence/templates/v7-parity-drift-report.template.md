# V7 new-lineage parity and drift report

Lineage ID: `FILL_AFTER_COMPLETE`

Projection digest: `FILL_AFTER_COMPLETE`

Population digest: `FILL_AFTER_COMPLETE`

## Declarations

- Pass-1 status/phase gate: `FILL`
- CANDIDATE_TEST read: `NO`
- CALIBRATION_RESERVED read: `NO`
- SEALED_VALIDATION read: `NO`
- Fit-phase STRATZ calls: `0`
- Fit-phase OpenDota calls: `0`
- Numeric parity tolerance: `FILL_BEFORE_COMPARISON`

## Runtime parity

For each of 16 Findings record maximum absolute/relative error for residual,
delta, SE, D, mu, tau, z, reliability, score, and posterior interval; then
record exact ranking and selection agreement. Add corresponding Recommendation
and Archetype rows. Any failed row blocks integration.

## Historical drift

Compare the new lineage to historical reviewed V7 outputs. Report population
composition, support, context vocabulary, adjusted estimates, mu/tau/D,
Recommendation eligibility/scales, Archetype cuts, and output coverage. Label
all differences as new-lineage drift, never restoration. Do not tune against
this report.

## Decision

`PASS | OWNER_DECISION_REQUIRED | FAIL`

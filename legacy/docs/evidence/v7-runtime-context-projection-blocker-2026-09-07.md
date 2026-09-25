# V7 runtime context-projection blocker — 2026-09-07

## Status

`BLOCKED` for end-to-end analytical runtime assembly. Deterministic descriptive
assembly is not blocked.

## Executable finding

The reviewed Finding estimator first fits additive categorical context effects
across the research population (`research.screen.project_out_context`) and only
then estimates each player's residual level or within-player contrast. The
checked-in `population-parameters-1.0.0.json` freezes `mu`, `tau`, dependence
inflation, recommendation scales, and archetype cuts. It does **not** freeze the
context level vocabulary or fitted context effects needed to residualize a new
runtime player's opportunities.

Calling the research projection with one runtime player is not equivalent. It
grand-centres that player's observations; for level families the player's mean
residual becomes zero. Comparing unadjusted runtime values with adjusted
population `mu`/`tau` is also invalid. Either path changes the approved
estimand while producing plausible-looking output.

The committed evidence contains projection convergence diagnostics, not the
fitted effects. Pass-1 opportunity rows are no longer source-reproducible, so
the original Pass-1 effects cannot now be recovered. Pass-2 source survives,
but refitting it is outside this phase's frozen-research authority.

## Why this is not the corpus incident used as an excuse

The incident does not prevent assembly, persistence, descriptive facts, or
contracts; those are implemented independently. It prevents one specific
mathematical input that the prior runtime artifact design omitted. The missing
input affects correct player estimates and every downstream Finding,
Recommendation, and Archetype selection.

## Owner decision required

Any resolution changes analytical lineage and requires explicit authority:

1. authorize a new corpus lineage and refit a runtime-complete projection
   artifact for all 16 dimensions;
2. authorize a new runtime estimator and revalidate it; or
3. restrict runtime capability to dimensions whose complete fitted transform
   can be recovered, changing D4 and the product contract.

Until then, runtime analytical producers must fail closed. No provider calls,
reserved-split reads, refits, or replacement evidence were used to establish
this blocker.

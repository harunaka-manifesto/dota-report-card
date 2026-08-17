# Hero Portfolio

Hero Portfolio is an independent summary-history layer. It does not reuse a
Pattern score as a hero answer and does not assign a global player label.
Version: hero-portfolio-1.0.0. Hero Mirror version: hero-mirror-1.0.0.

## Eligibility

Eligibility is shared across insights but has separate booleans for Common
Thread, Exception, and Mirror. Gates include minimum appearances, minimum pool
share, usable taxonomy coverage, recency, and metric completeness. One-game
heroes cannot qualify merely because they are unusual.

## Common Thread

Common Thread compares established heroes through reviewed taxonomy traits.
Trait weights are capped per hero so one heavily sampled hero cannot dominate.
The result includes the leading trait, secondary traits, weighted coverage,
denominator, confidence, and four deterministic answer choices.

## Exception

Exception finds the most functionally distant established hero from the
candidate-excluded pool centroid. A minimum candidate count, distance floor,
and runner-up margin are required. No clear result is valid output.

## Pool Evolution

Pool Evolution compares stable chronological windows. It measures hero
distribution shift separately from taxonomy-toolkit distribution shift and
maps the pair into new_heroes_new_toolkit, new_heroes_same_toolkit,
stable_core_new_branch, or broadly_stable.

## Hero Mirror

Hero Mirror compares Involvement, Finishing, Deaths, and credible Role context
with sufficiently sampled hero references. The candidate is excluded from its
reference where possible and otherwise contributes through a capped fallback.
Shrinkage pulls small samples toward the reference. Missing dimensions reduce
coverage and confidence. A margin gate prevents weak runner-up wins.

Mirror copy says it is not a personality test. Taxonomy supplies candidate
context and labels, not the core behavior score.

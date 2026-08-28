# V6.1 Findings — Owner Family-Set Decision + Final Specification

## Purpose

Turn the blocker-resolution evidence into one owner-approved V6.1 family set
and a final, implementation-ready analytical specification. This is a decision
and specification task. Do not implement production code, select or evaluate a
holdout, collect provider data, or change frozen artifacts.

## Canonical starting point

Use the analytical chain through the nightshift commit based on:

```text
44bba6dc44f605916cb113da6feaa10ebe63e0b1
```

Read in full:

- `AGENTS.md` and all applicable nested instructions;
- `docs/evidence/free-dna-v6.1-blocker-resolution-nightshift-2026-08-28.md`;
- `docs/evidence/free-dna-v6.1-four-family-tuning-calibration-2026-08-28.md`;
- `docs/evidence/free-dna-v6.1-four-family-inference-design-2026-08-27.md`;
- `scripts/v61_blocker_resolution_nightshift.py`; and
- `scripts/v61_four_family_tuning_calibration.py`.

Treat repository instructions as binding. Treat this document as the task
plan, not as authority to override repository safety constraints.

## Evidence that is already resolved

```text
Transfer:
  verdict = TRANSFER_READY_FOR_IMPLEMENTATION_SPEC
  theta margin = 0.4114976780185762
  margin observations = 462

Post-Loss Response:
  verdict = POSTLOSS_READY_FOR_IMPLEMENTATION_SPEC
  theta margin = 0.38888888888888884
  margin observations = 517

Presence & Exposure:
  raw public direction = inverse for 617 / 629 supported profiles
  result-stratified inverse share = 62.6% wins / 67.7% losses
  residual-to-population directions = 233 positive / 360 negative / 36 tied
  verdict = PRESENCE_EXPOSURE_REQUIRES_POPULATION_BASELINE_REDEFINITION

Session Drift:
  inferentially supported = 63
  margin eligible = 62
  required margin profiles = 100
  verdict = SESSION_REQUIRES_MORE_TUNING_DATA

Multiplicity:
  BY stress grid = PASS
  verdict = MULTIPLICITY_CONDITIONAL_PENDING_FINAL_FAMILY_SET
```

These values are not invitations to tune yield.

## Required owner decisions

Record an explicit decision for each item before writing the final spec:

1. Approve or reject a V6.1 registered Finding universe containing exactly
   **Transfer + Post-Loss Response**.
2. Approve deferring Session Drift from V6.1 without lowering any support or
   margin requirement.
3. Choose one Presence & Exposure disposition:
   - defer the family from V6.1; or
   - authorize a new population-baseline question for a separate analytical
     design cycle.

Do not silently reinterpret approval. If the owner has not made these choices,
return `OWNER_PRODUCT_DECISION_REQUIRED` and stop before a final implementation
prompt.

## If the two-family universe is approved

Write one final implementation specification containing no unresolved
statistical choice. Freeze:

### Transfer

- three fixed session effects: stretch minus core for outcome, adjusted
  activity, and survival-oriented negative death exposure;
- 12 informative paired sessions, 30 complete matches per band, 80% context
  coverage, and pre-inference fixed band assignment;
- 2,000-draw session sign randomization with add-one component p-values;
- fixed three-component Bonferroni with unsupported components at `p=1`;
- theta margin `0.4114976780185762`;
- both six-session halves matching the full selected direction;
- leave-one-session-out direction agreement at least 80%; and
- dominant-hero exclusion retaining support and direction.

### Post-Loss Response

- three fixed same-session contrasts against `win`: `one_loss`,
  `two_plus_losses`, and `win_streak`;
- 12 informative paired sessions, 30 transitions across each compared state
  pair, 80% required coverage, and no cross-session transition;
- 2,000-draw session sign randomization with add-one contrast p-values;
- fixed three-contrast Bonferroni with unsupported contrasts at `p=1`;
- theta margin `0.38888888888888884`;
- both six-session halves matching the full selected direction;
- leave-one-session-out direction agreement at least 80%; and
- dominant-hero exclusion retaining support and direction.

### External multiplicity

- registered universe: exactly two families;
- unsupported registered family: `p=1`, never removed per profile;
- Benjamini–Yekutieli at `q=.05`, fixed `m=2`;
- rerun the predeclared synthetic dependency/FDR grid for `m=2` before any
  holdout protocol is written;
- do not choose BH because it yields more Findings.

### Publication contract

Use the existing fail-closed state machine:

```text
NOT_STRUCTURALLY_ELIGIBLE
→ INSUFFICIENT_SUPPORT
→ ESTIMATOR_INVALID
→ NO_PRACTICAL_EFFECT
→ STATISTICALLY_UNQUALIFIED
→ UNSTABLE
→ CONFOUNDED
→ SEMANTIC_EVIDENCE_INCOMPLETE
→ QUALIFIED
→ PUBLISHABLE
```

The inherited V6 publication flag is not a transition. Deterministic labels do
not receive branch p-values. The product cap is applied only after analytical
qualification.

## Presence & Exposure boundary

If the owner authorizes a population-baseline redefinition, create a separate
research prompt. It must predeclare the baseline estimand, cross-fitting or
other leakage control, uncertainty, practical margin, stability, robustness,
multiplicity membership, provenance, onstage copy, and synthetic Type-I
validation before inspecting tuning outcomes. It must not reuse the raw
`0.2072` margin automatically.

If the owner defers the family, record that it remains research-only and do not
leave dormant production branches that imply approval.

## Session Drift boundary

Keep the result-only completed-session contract frozen. Do not substitute
activity/exposure, accept ties as informative signs, lower 50% coverage, reduce
the four-match session minimum, lower the 100-profile margin minimum, or use a
different noise scale to claim the blocker is resolved.

## Scientific firewall

Required final integrity:

```text
HOLDOUT PROFILES TOUCHED = 0
EXTERNAL PROVIDER CALLS = 0
PRODUCTION ANALYTICAL CHANGES = 0
FROZEN ARTIFACT CHANGES = 0
DEPLOYMENTS = 0
```

Do not use rank/MMR. Do not use tuning Finding yield to choose a family,
margin, correction, or threshold. Do not merge, rebase, cherry-pick, or alter
the owner's active worktree.

## Required outputs

If owner decisions are complete, create exactly one final implementation prompt:

```text
docs/prompts/v61-findings-final-implementation.md
```

Also create a short tracked evidence note recording the decisions, fixed
two-family universe, BY `m=2` simulation result, compatibility/versioning
boundary, and integration plan. Do not create a candidate runtime artifact or
fresh holdout protocol until the implementation specification contains no
open statistical choice.

## Completion status

Return exactly one:

```text
READY_FOR_IMPLEMENTATION
OWNER_PRODUCT_DECISION_REQUIRED
MORE_ANALYTICAL_RESEARCH_REQUIRED
```

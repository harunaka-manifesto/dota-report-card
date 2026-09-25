# V7 new-lineage post-COMPLETE execution plan

## Hard start gate

Do nothing in this plan unless the final recollection state says exactly:

```text
status == COMPLETE
phase == PASS1_HISTORY_NEW_LINEAGE_COMPLETE
```

If either value differs, stop. Do not infer completion from file counts. At all
times refuse `CANDIDATE_TEST`, `CALIBRATION_RESERVED`, and `SEALED_VALIDATION`.
Fresh provider calls remain separately unauthorized.

## Sequential checklist

1. **Corpus integrity.** Snapshot the completed run/state/hash manifests;
   validate phase/status, account terminal states, identity exclusion, split
   declarations, write-completion markers, and absence of protected-split
   access. Verify no acquisition process still owns the corpus.
2. **Final counts and digests.** Record attempted/complete/no-data accounts,
   history and parsed document/row counts, acquisition timestamps, request
   ledger count, all manifest/source digests, new corpus ID, and provider-call
   declaration. Freeze an immutable input manifest.
3. **Context projection fit.** Build the 16 opportunity sets from completed
   Pass-1 plus surviving Pass-2 using the reviewed final producer's 20/8/4
   blocked geometry; do not substitute the level-family research helper;
   fit the frozen ten-sweep dimension-specific categorical projections; record
   vocabulary/order/intercept/corrections/convergence and refuse unsupported
   levels. Emit and self-digest `v7-context-projection-<version>.json`.
4. **Population refit.** Apply those exact residuals, estimate blocked player
   values/SE and `D`, then refit `mu/tau`; run negative-control and withheld
   gates. Fit Recommendation context/scales/`D` and re-run the fixed sign screen.
   Regenerate mode-stratified Archetype cuts. Emit a new population artifact
   with the same lineage ID, projection digest, and compatibility ID.
5. **Runtime parity.** For every dimension compare research residuals,
   `delta_hat`, SE, `D`, `mu`, `tau`, z, reliability, score, shrinkage interval,
   ranking, and final selection against runtime. Require numeric parity; no
   threshold or candidate changes.
6. **Historical drift audit.** Compare new-lineage outputs with historical V7
   evidence as a lineage comparison, not restoration. Separate corpus-composition,
   context-fit, and estimator effects. Escalate material semantic drift; do not
   tune it away.
7. **Recommendation verification.** Confirm exactly seven eligible canonical
   instructions, >=15 observations/arm, contamination/sign rules, scale and
   dependence binding, one private selection, canonical copy, verification
   measure, and associational wording. Confirm no recommendation enters the
   public projection.
8. **Archetype verification.** Confirm 18 grid labels, dominant stratum, all
   three axes, refusal/no-default behavior, Lighthouse precedence, special
   replacement, new cuts, and no public rarity.
9. **Capability integration.** Bind projection and population compatibility
   before analytics. Wire canonical observations -> frozen projection ->
   inference -> population -> ranking -> Findings, then independent
   Recommendation/Archetype, capability payload, persistence, and API. Stamp
   lineage/projection/population provenance without exposing coefficients.
10. **Full QA.** Run schema/digest/version/unsupported-level tests, all V7 unit
    and contract tests, rank/protected-split/privacy fences, synthetic and real
    parity, persistence/API round trips, lint/typecheck/build as applicable,
    and the phase-close assertions. Record zero protected reads and actual
    provider-call count. Stop before deployment or frontend work.

## Required outputs

- signed context-projection artifact and manifest;
- compatible signed population artifact and fit manifest;
- source-digest and estimator-identity inventory;
- parity/drift report with explicit tolerances;
- Recommendation and Archetype verification sections;
- QA log and owner decision packet for any unresolved semantic change.

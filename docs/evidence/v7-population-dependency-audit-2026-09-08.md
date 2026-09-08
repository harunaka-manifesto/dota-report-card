# V7 population-artifact dependency audit — pre-fit

No value was refit. `PROVABLY_REUSABLE` means the definition is deterministic
and corpus-independent; it does not authorize copying an old fitted value into
a new artifact without rebinding provenance.

| Object | Classification | Reason / action after COMPLETE |
|---|---|---|
| Finding response definitions and 16 shipping IDs | `PROVABLY_REUSABLE` | Frozen source definitions; parity-test builders before fit. |
| Context factor families, ordering, ten-sweep algorithm, equal opportunity weighting, no interactions/player factor | `PROVABLY_REUSABLE` | Exact existing model definition. |
| Context categorical vocabularies, intercepts, and level corrections | `REQUIRES_NEW_LINEAGE_REFIT` | Depend on the completed fitting population. |
| Finding `mu` and `tau` | `REQUIRES_NEW_LINEAGE_REFIT` | Depend on new adjusted player estimates. Old adjusted values are incompatible by default. |
| Finding dependence inflation `D` | `REQUIRES_NEW_LINEAGE_REFIT` | Must be measured on new-lineage residual series. Pass-2-only values may reproduce, but must be proved and rebound. |
| Finding ranking equations, section mapping, deterministic tie break, 3-slot selection, D1 floor/score behavior | `PROVABLY_REUSABLE` | Fixed design/owner decisions; no tuning authorized. |
| Final blocked-means geometry | `PROVABLY_REUSABLE` | Reviewed final producer used 20/8/4 for all families. `block_config` differs for levels but is not the final producer; substituting it would require a new estimator decision. |
| Recommendation seven instructions, upstream rule, minimum 15/arm, actionability weights, private-only projection, associational wording | `PROVABLY_REUSABLE` | Deterministic contract and copy. |
| Recommendation context coefficients, per-dimension scales, `D`, modal-sign shares and contamination verdict evidence | `REQUIRES_NEW_LINEAGE_REFIT` | Population-derived. Re-run the predeclared 0.95 contamination screen; do not tune it. |
| Archetype 18 labels, two special names/precedence, axes, dominant-mode and refusal rules, modifier cut 1.0, no-public-rarity rule | `PROVABLY_REUSABLE` | Definition/design constants. |
| Archetype tempo, participation, deaths, Lighthouse, and Closer cuts | `REQUIRES_NEW_LINEAGE_REFIT` | Population quantiles over the new joinable lineage. |
| Existing `population-parameters-1.0.0.json` as a runtime bundle | `REQUIRES_NEW_LINEAGE_REFIT` | It explicitly says evidence-derived, not refit from source, and lacks a context-projection compatibility identity. It remains historical evidence and must not be overwritten. |
| Pass-2 canonical data and its deterministic estimators | `PROVABLY_REUSABLE` | Surviving source is complete and read-only; integrity and reviewed-output parity are recorded separately. |
| Pass-2 fitted values under the new combined lineage | `UNRESOLVED` | Exact reproduction is plausible and previously observed, but final compatibility must be established against the new signed projection/population bundle. |
| CANDIDATE_TEST, CALIBRATION_RESERVED, SEALED_VALIDATION | `PROVABLY_REUSABLE` as clean reserved assets | Not read or spent in this phase. Their statistics are not dependencies of pre-fit preparation. |

## Family impact

- Findings: blocked until all 16 projections and compatible `mu/tau/D` exist.
- Recommendation: independently defined but blocked for runtime production
  until its own context projection, scale, dependence, and contamination audit
  are bound to the new lineage.
- Archetype: not blocked by Finding residualization. It is blocked only on
  regenerating population cuts over the new joinable lineage; definitions and
  refusal behavior are ready.

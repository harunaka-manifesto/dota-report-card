# V7 NEW-LINEAGE historical drift audit

Overall classification: `EXPECTED_DRIFT`.

This is a diagnostic comparison to surviving aggregate evidence. No historical
number was used as a fit target, no threshold or candidate changed, and no
reserved or sealed cohort was read.

| Family | Classification | Evidence |
|---|---|---|
| Eight Pass-2 dimensions | `MATCHES_CLOSELY` | Player/opportunity denominators reproduce exactly. `mu`, `tau`, and `D` reproduce to the precision retained in the historical aggregate JSON. |
| History-only Pass-1 dimensions | `EXPECTED_DRIFT` | One fewer estimable player; `tau` changes by 0.08% to 0.42%, with unchanged definitions and estimator. |
| Parsed Pass-1 dimensions | `EXPECTED_DRIFT` | The surviving DISCOVERY-only parsed overlay has 58 accounts versus roughly 116 historically. `tau` changes are purchase tempo -1.44%, lead retention -6.79%, position flexibility -17.31%, and fight timing centroid -26.96%. The direction and magnitude follow the explicitly smaller parsed support; no coefficient was solved backward or tuned. |
| Recommendation | `MATCHES_CLOSELY` | Pass-2 source is unchanged: seven eligible instructions, two contamination exclusions, minimum 15/arm, and scale/dependence outputs reproduce. |
| Archetype | `MATCHES_CLOSELY` | Both mode-stratified cut sets and denominators reproduce: 276 joinable, 262 assigned, all 18 normal cells available plus two specials. |

The larger parsed-family movements are material in size but explained by the
known, audited loss of half the historical parsed denominator. They do not
alter any estimand, sign convention, candidate, threshold, or public meaning.
They are therefore expected lineage drift rather than unexplained analytical
drift. Historical Pass-1 evidence remains historical and was not overwritten.

Provider calls: STRATZ 0, OpenDota 0. `CANDIDATE_TEST`,
`CALIBRATION_RESERVED`, and `SEALED_VALIDATION`: not read.

# V7 runtime mathematical contract — pre-fit freeze

Status: deterministic contract only. The new Pass-1 recollection was incomplete
when this document was written. No row, coefficient, population statistic, cut,
threshold, or drift conclusion from that partial corpus appears here.

Sources: `research/features.py`, `pass2_observations.py`, `screen.py`,
`inference.py`, `ranking.py`, `recommendation.py`, `archetype.py`, and the
reviewed V7 evidence through 2026-09-07.

## Common Finding estimand

For Finding dimension `d`, opportunity `i` has response `Y_di`, player `p(i)`,
and categorical context `X_di`. The population context fit is dimension-specific:

```text
f_d(X_di) = a_d + sum_j beta_dj[X_dij]
r_di      = Y_di - f_d(X_di)
```

`a_d` is the grand opportunity-weighted mean. Starting with `Y-a_d`, the
canonical fitter makes ten Gauss-Seidel sweeps over factors in discovery order.
For each factor and level it subtracts the current residual group mean. The
frozen `beta_dj[level]` is the sum of those ten applied corrections. There are
no interactions and player is not a factor. Every opportunity has equal weight;
players are therefore weighted in proportion to eligible opportunities during
context fitting.

This is a finite-sweep parameterization, not treatment coding. It has no
reference level. Runtime artifacts must carry `reference_level: null`, the
factor order, vocabulary order, intercept, and every accumulated correction.
Absent factors follow the research encoder's explicit `__missing__` level only
when that level was fitted. An unseen level otherwise refuses the affected
dimension. A mapped fallback is legal only when the artifact explicitly names
a fitted fallback level; zero is never an implicit fallback.

For a level Finding, chronological residuals for player `p` are divided into up
to 20 near-equal contiguous blocks. For a contrast Finding, `__arm__` is also a
population context factor and each valid block supplies the treated-minus-control
residual difference. In the reviewed final Finding pipeline, all dimensions call
`infer_all` with its defaults: at least eight valid blocks and four opportunities
per block. This differs from `block_config`, whose level-family research design
declares four blocks and 100 opportunities per block. The reviewed final pipeline
is the shipping-output producer, so 20/8/4 is the frozen new-lineage parity
contract. `block_config` must not silently replace it. Changing this geometry
would require a separate owner-authorized estimator lineage because it changes
SE and downstream population parameters.

For valid block statistics `b_pk`, with `K_p` valid blocks:

```text
delta_hat_pd = mean_k(b_pk)
SE_pd        = sample_sd_k(b_pk) / sqrt(K_p)
```

The dependence inflation `D_d` is the variance ratio at the longest measurable
batch in `(1,5,10,25,50,100)`, floored at 1. If no non-unit batch is measurable,
the pipeline uses 1 and records that optimistic fallback. If the curve is still
rising, reliability is explicitly an upper bound.

Across estimable DISCOVERY players:

```text
mu_d    = mean_p(delta_hat_pd)
tau_d^2 = max(0, sample_var_p(delta_hat_pd) - mean_p(SE_pd^2 * D_d))
z_pd    = (delta_hat_pd - mu_d) / tau_d                 when tau_d > 0
r_pd    = tau_d^2 / (tau_d^2 + SE_pd^2 * D_d)
score   = abs(z_pd) * r_pd
posterior point = mu_d + r_pd * (delta_hat_pd - mu_d)
posterior var   = (1-r_pd) * tau_d^2
```

`tau=0` withholds the dimension. Ranking is descending `(score, key)`, followed
by the frozen stratified-selection and D1 score-gate behavior. The new context
fit and new Pass-1 population imply a new `mu/tau/D` lineage except where exact
reproduction is proved and rebound explicitly.

## Dimension contracts

All Pass-1 rows are product-context history rows: supported mode, ordinary
matchmaking lobby, clean leaver state, and a joined parsed row where marked.
All Pass-2 rows are the surviving DISCOVERY deep-match corpus and pass its
product-context gate. Context level vocabularies are empirical and therefore
remain blocked until completion; the factor families themselves are frozen
below.

| Finding | Y and observation unit | Eligible population / support | Context in order | Arms | Source | Rec. | Arch. |
|---|---|---|---|---|---|---|---|
| `vision_coverage` | Per-match share of minutes with an own observer ward alive. | Computable match; player must have placed an observer ward at least once. Final blocked-estimator gate applies. | mode, patch, hero, duration, side, lobby, position, lane | level | Pass-2 | yes | Lighthouse special input |
| `duration_tempo` | `log(max(duration_seconds,1))`, one match. | Product-context history; registry support 100. | mode, patch, hero, lobby, result | level | Pass-1 | no | no |
| `death_clustering` | Indicator that a consecutive own death-to-death gap is <=90 seconds, one gap. | At least two death events in a match; final blocked-estimator gate. | Pass-2 common eight | level | Pass-2 | candidate but contamination screen excludes | no |
| `lane_vs_jungle_share` | `jungle_gold/(lane_gold+jungle_gold)`, one match. | Both creep-gold components available and total >0. | Pass-2 common eight | level | Pass-2 | yes | no |
| `purchase_tempo` | Normalized game progress of the eighth recorded item purchase, one match. | Joined parsed match with >=8 timed purchases; registry support 40. | mode, patch, hero, duration, side, lobby, position, role, lane | level | Pass-1 parsed | no | no |
| `deaths_alone_share` | Per-match share of own death minutes with no team kill activity. | Match with computable death share. | Pass-2 common eight | level | Pass-2 | yes | no |
| `spike_usage` | Seconds from first real-item purchase to next own kill or assist, one match. | Both supported events exist. Mean, not the census median. | Pass-2 common eight | level | Pass-2 | yes | no |
| `position_flexibility` | Indicator that parsed position changed from the preceding parsed match, one adjacent in-session pair. | Both positions known and gap <=3h; registry support 40. | mode, patch, hero, duration, side, lobby, previous position | level | Pass-1 parsed | no | no |
| `fight_timing_centroid` | Mean normalized progress of own kill and assist event times, one match. | Joined parsed match with >=3 own fight events; registry support 40. | mode, patch, hero, duration, side, lobby, position, role, lane | level | Pass-1 parsed | no | archetype independently recomputes a related axis |
| `hero_novelty` | Indicator hero was unseen in prior 30 days, one match after a 30-match warm-up. | Product-context history after warm-up; registry support 100. | mode, patch, lobby | level | Pass-1 | no | no |
| `closer_vs_comeback` | Win indicator, one observation for each match crossing +10k and/or -10k team lead; a match may enter both arms. | Lead trajectory exists and crosses an arm threshold. | Pass-2 common eight, `__arm__` | ahead minus behind | Pass-2 | explicitly downstream/circular, excluded | Closer special input |
| `post_loss_session_continuation` | Indicator another match follows within the same <=3h-gap session, one non-right-censored match. | Product-context history; final observed row dropped; registry support 60 and 25/arm. | mode, patch, hero, duration, side, lobby, 4-hour bucket, `__arm__` | loss minus win | Pass-1 | no | session data independently feeds modifier |
| `lead_retention` | Win indicator conditional on midpoint own-team lead magnitude >=5000, one match. | Joined parsed trajectory length >=8; registry support 40 and 15/arm. | mode, patch, hero, duration, side, lobby, position, role, lane, `__arm__` | ahead minus behind | Pass-1 parsed | downstream/team outcome, excluded | no |
| `post_loss_hero_switch` | Indicator next in-session hero differs, one adjacent transition. | Product-context pair in same <=3h-gap session; registry support 60 and 25/arm. | mode, patch, hero, duration, side, lobby, `__arm__` | loss minus win | Pass-1 | no | no |
| `post_loss_requeue_latency` | `log(max(next_start-current_end,1))`, one adjacent transition. | Product-context pair in same <=3h-gap session; registry support 60 and 25/arm. | mode, patch, hero, duration, side, lobby, `__arm__` | loss minus win | Pass-1 | no | no |
| `fight_conversion` | Indicator enemy tower falls one or two minutes after a won-fight minute, one won-fight minute. | Own team has >=3 kills and enemy has zero in the minute; side and tower event known. | Pass-2 common eight | level | Pass-2 | candidate but contamination screen excludes | no |

“Pass-2 common eight” means `mode, patch, hero, duration, side, lobby,
position, lane`. Pass-1 parsed controls include role; Pass-2 controls do not.
That difference is source-defined and must not be normalized away during fit.

## Recommendation contract

Exactly one private note is selected from seven canonical instructions:
`last_hits_at_ten`, `deaths_alone_share`, `first_real_item_time`,
`first_ward_time`, `lane_vs_jungle_share`, `vision_coverage`, and `spike_usage`.
Each observation is one supported Pass-2 match, armed `loss` versus `win`, with
context `(mode, patch, hero, position, role, lane)`. Duration and side are
deliberately excluded. Unlike Finding contrasts, arm is **not** projected out:
the estimand is the player's own loss-minus-win gap, not unusualness relative
to a population gap.

A candidate needs at least 15 observations in each arm. Its population-fitted
unit scale is the sample SD of all context residuals. Reliability is
`scale^2/(scale^2+SE^2*D)` and priority is
`abs(gap/scale)*reliability*actionability`. The chosen instruction must match
the registry exactly and uses associational wording only. Design-time upstream
checks remain fixed. Outcome-contamination and sign-agreement measurements,
context coefficients, scale, and `D` must be verified/rebound in the new
lineage; no recommendation value was computed in this phase.

## Archetype contract

Archetype is independent of Finding residualization. It has 18 fixed normal
labels (3 tempo x 3 fight-style x 2 modifier), plus `The Lighthouse` and `The
Closer`. A dominant STANDARD or TURBO stratum with >=20 matches is required.
Any missing axis refuses the whole label; there is no default. Lighthouse has
special precedence, a special replaces the normal label, and rarity is never
public.

Tempo is mean per-match normalized kill/assist timing. Fight style combines
fight-minute participation and deaths per fight minute. The session modifier
is observed between-session win-rate variance divided by its binomial expected
variance, needs >=8 sessions of >=3 matches, and uses the fixed semantic cut
1.0. Population tempo terciles, participation lower tercile, deaths median,
and both special quantile cuts require new-lineage regeneration because the
joinable population changes. No archetype cut was derived here.

## Unresolved until the corpus is complete

- Actual level vocabularies, counts, reference-free coefficient vectors, and
  whether every factor has adequate support.
- New-lineage context intercepts/corrections and convergence diagnostics.
- New `mu`, `tau`, `D`, Recommendation scales/contamination measurements, and
  Archetype population cuts.
- New-to-historical drift results and any resulting owner decision.

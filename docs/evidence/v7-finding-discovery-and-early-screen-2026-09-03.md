# V7 Finding discovery and discovery-only early screen — 2026-09-03

Broad STRATZ-native candidate discovery over the completed corpus, followed by
a cheap screen whose only job is to kill weak ideas before statistical
engineering becomes expensive. **DISCOVERY split only.** No inference, no
p-value, no alpha, no tuned threshold, and no provider request of any kind.

```text
PHASE: V7_FINDING_DISCOVERY_AND_EARLY_SCREEN
STATUS: FROZEN
SPLIT USED: DISCOVERY
CANDIDATE_TEST TOUCHED: NO
CALIBRATION_RESERVED TOUCHED: NO
SEALED_VALIDATION TOUCHED: NO
NEW STRATZ PHYSICAL CALLS: 0
OPENDOTA CALLS: 0
RANK / MMR / IMP / BEHAVIOUR / PLAYBACK USED: NO
```

## Provenance

| item | value |
|---|---|
| code SHA | `dd0930269fcd324b56d230f11d83ffddcd0aaf9c` |
| corpus run-manifest digest | `256676abc8254b6d1dd804a371ea1636469710fee57ca3ce8151dee25a4ed704` |
| split-manifest digest | `ef24c63b1c2f56e4bb21b4947b0b43dedf0550bd3547ee818cc9346f4275d885` |
| feature version | `v7-luna-b-features-1.0.0` |
| screen version | `v7-luna-b-screen-1.0.0` |
| registry version | `v7-luna-b-candidate-registry-1.0.0` |
| candidate-definition version | `v7-luna-b-candidates-1.0.0` |
| full registry digest | `24de598a5ad044d0d2a3d26e6b22353932fbebc301c41b1489f8b6151fdd0164` |
| **frozen serious-candidate digest** | `f9f5af7806ee5936e40d826eeb5904fe8bffa488995c967a959f8e9e5456086c` |
| seed | `20260903` |

Reproduce with:

```bash
uv run python scripts/v7_discovery_screen.py --corpus-root <corpus> --out docs/evidence/v7-discovery-screen-2026-09-03.json
```

The machine-readable registry, every screen metric, and the redundancy matrix
live in `docs/evidence/v7-discovery-screen-2026-09-03.json`. That file carries
all 36 explored families, including the pruned ones, so the later tournament
can account for the full multiplicity universe rather than only the survivors.

## Denominators

Reach is quoted against two denominators, always both, never whichever flatters:

```text
DISCOVERY sampled accounts               600
DISCOVERY product-eligible accounts      553   (accounts with >=1 product-context match)
DISCOVERY parsed-detail accounts         116
DISCOVERY truncated-history accounts       8
corpus-wide sampled / product-eligible   900 / 835
```

A parsed-dependent family's `reach of sampled` is bounded above by 116/600 =
0.193 **as an artefact of the corpus design**, not of the candidate: parsed
detail was only collected for the predeclared subset. For those families the
decision-relevant number is reach of the parsed-eligible denominator, and both
appear in every table below.

## Method

Opportunities are extracted per family by deterministic extractors
(`scripts/v7_research/features.py`), then screened
(`scripts/v7_research/screen.py`):

- **Context adjustment** removes additive categorical effects — mode, patch,
  hero, duration bucket, side, lobby, and where available position, role and
  lane — by alternating group-mean removal. Player is deliberately *not* a
  factor, since removing it would remove the signal. Because hero and mode are
  themselves player choices, this adjustment is conservative: it takes
  player-driven context choice out of the residual, so reported heterogeneity
  is a lower bound.
- **Heterogeneity** uses a method-of-moments split,
  `sigma_between^2 = max(0, Var(player values) - mean(SE^2))`, and reliability
  `sigma_b^2 / (sigma_b^2 + mean SE^2)` — the share of observed spread that is
  real rather than noise.
- **Preliminary stability** is a within-player split-half correlation over
  each player's own matches, reported raw (`r`) and Spearman–Brown corrected
  (`SB`). SB is the headline stability number.
- **Information reach** is the share of supported players whose own estimate
  clears a signal-to-noise bar of 1 and of 2.
- Every family pools Turbo with standard modes and carries mode as context,
  per the capability atlas; minute-indexed quantities use normalised game
  progress rather than wall-clock minutes.

**`side_sensitivity` is a planted negative control**: the "effect" of starting
on Radiant versus Dire, which no player controls and which should therefore
show no stable individual differences. It returns `sigma_between = 0`,
reliability `0.000`, split-half SB `+0.036`. The screen does not manufacture
individuality.

## The candidate universe — 36 families explored

Ordered by Spearman–Brown stability. `prs` marks parsed dependence. `reachS`
and `reachE` are reach of sampled and of the applicable eligible denominator.
`eta2P` is the raw share of opportunity variance attributable to the player
before context adjustment; `maxCtx` names the single largest context factor.

| family | prs | reachS | reachE | reliability | SB | eta2P | maxCtx | obs median | verdict |
|---|:--:|---:|---:|---:|---:|---:|---|---:|---|
| duration_tempo | n | 0.843 | 0.915 | 0.990 | +0.988 | 0.327 | mode 0.410 | 553 | **serious** |
| purchase_tempo | Y | 0.190 | 0.983 | 0.987 | +0.977 | 0.221 | hero 0.131 | 461 | **serious** |
| hero_novelty | n | 0.828 | 0.899 | 0.975 | +0.973 | 0.084 | lobby 0.002 | 537 | **serious** |
| risk_appetite | n | 0.843 | 0.915 | 0.985 | +0.967 | 0.149 | hero 0.068 | 553 | pruned — percentile |
| requeue_tempo | n | 0.810 | 0.879 | 0.979 | +0.962 | 0.140 | mode 0.032 | 378 | pruned — percentile |
| involvement_level | n | 0.843 | 0.915 | 0.966 | +0.956 | 0.092 | mode 0.074 | 553 | pruned — KDA |
| session_length | n | 0.837 | 0.908 | 0.968 | +0.952 | 0.177 | hour 0.005 | 178 | pruned — calendar fact |
| kill_share | Y | 0.190 | 0.983 | 0.955 | +0.942 | 0.110 | hero 0.159 | 459 | pruned — role restatement |
| early_fight_rate | Y | 0.190 | 0.983 | 0.946 | +0.941 | 0.064 | hero 0.053 | 461 | pruned — redundant |
| fight_timing_centroid | Y | 0.190 | 0.983 | 0.869 | +0.925 | 0.040 | hero 0.055 | 460 | **serious** |
| post_loss_hero_switch | n | 0.848 | 0.920 | 0.897 | +0.897 | 0.123 | hero 0.029 | 378 | **serious** |
| first_fight_timing | Y | 0.190 | 0.983 | 0.902 | +0.889 | 0.052 | hero 0.051 | 461 | pruned — redundant |
| position_flexibility | Y | 0.188 | 0.974 | 0.932 | +0.882 | 0.088 | hero 0.031 | 303 | **serious** |
| post_loss_requeue_latency | n | 0.848 | 0.920 | 0.802 | +0.796 | 0.140 | mode 0.032 | 378 | **serious** |
| post_loss_session_continuation | n | 0.878 | 0.953 | 0.814 | +0.791 | 0.052 | duration 0.008 | 552 | **serious** |
| transfer_risk | n | 0.800 | 0.868 | 0.667 | +0.651 | 0.150 | hero 0.069 | 529 | **serious** |
| transfer_activity | n | 0.800 | 0.868 | 0.591 | +0.623 | 0.094 | mode 0.074 | 529 | **serious** |
| lead_retention | Y | 0.185 | 0.957 | 0.462 | +0.572 | 0.006 | arm 0.279 | 242 | **serious** (weak) |
| lane_recovery_participation | Y | 0.188 | 0.974 | 0.472 | +0.440 | 0.052 | arm 0.045 | 353 | **serious** (weak) |
| state_responsive_purchasing | Y | 0.178 | 0.922 | 0.257 | +0.403 | 0.157 | hero 0.079 | 169 | pruned |
| comeback_participation | Y | 0.188 | 0.974 | 0.474 | +0.389 | 0.008 | duration 0.010 | 424 | pruned |
| weekend_shift | n | 0.847 | 0.919 | 0.323 | +0.385 | 0.092 | mode 0.074 | 553 | pruned |
| offpeak_shift | n | 0.570 | 0.618 | 0.454 | +0.377 | 0.091 | mode 0.074 | 562 | pruned |
| post_loss_risk_shift | n | 0.848 | 0.920 | 0.333 | +0.345 | 0.153 | hero 0.069 | 378 | pruned |
| post_loss_mode_switch | n | 0.848 | 0.920 | 0.235 | +0.337 | 0.062 | mode 0.006 | 378 | pruned |
| post_loss_next_outcome | n | 0.848 | 0.920 | 0.210 | +0.333 | 0.004 | side 0.004 | 378 | pruned — outcome |
| session_drift_risk | n | 0.853 | 0.926 | 0.283 | +0.300 | 0.154 | hero 0.070 | 306 | pruned |
| layoff_return | n | 0.538 | 0.584 | 0.188 | +0.287 | 0.095 | mode 0.072 | 398 | pruned |
| warmup_first_match | n | 0.838 | 0.910 | 0.235 | +0.272 | 0.096 | mode 0.070 | 419 | pruned |
| session_drift_activity | n | 0.853 | 0.926 | 0.131 | +0.178 | 0.101 | mode 0.069 | 306 | pruned |
| transfer_outcome | n | 0.800 | 0.868 | 0.209 | +0.150 | 0.004 | side 0.004 | 529 | pruned — outcome |
| session_drift_outcome | n | 0.853 | 0.926 | 0.166 | +0.149 | 0.005 | side 0.004 | 306 | pruned — outcome |
| state_responsive_participation | Y | 0.178 | 0.922 | 0.000 | +0.129 | 0.037 | hero 0.027 | 169 | pruned — no heterogeneity |
| lane_recovery_outcome | Y | 0.188 | 0.974 | 0.145 | +0.113 | 0.004 | arm 0.053 | 353 | pruned — outcome |
| side_sensitivity | n | 0.877 | 0.951 | 0.000 | +0.036 | 0.003 | arm 0.004 | 553 | negative control |
| state_responsive_participation_minutes | Y | 0.187 | 0.966 | 0.003 | −0.090 | 0.006 | mode 0.004 | 1,542 | pruned — sampling variant |

## What the screen actually found

### 1. Match outcomes are not a personal trait

Every family whose response is a match result collapses:
`post_loss_next_outcome` SB +0.333 with reliability 0.210,
`transfer_outcome` +0.150, `session_drift_outcome` +0.149,
`lane_recovery_outcome` +0.113. Their raw player variance shares are
0.4–0.5%, barely above the negative control's 0.3%.

The honest reading is that **whether you win the next game is not who you
are**. This is not a measurement failure; it is the answer. It kills the
outcome form of three of the four inherited concepts at once, and it is the
single most useful result of this phase because it redirects the whole
portfolio towards behaviour.

### 2. Behaviour is stable; the behavioural form of the same ideas survives

The same setback that does not move outcomes moves *choices*, strongly:
after a loss, whether you keep playing (SB +0.791), whether you switch hero
(+0.897), and how fast you re-queue (+0.796) are all stable individual
differences at ~92–95% reach of eligible accounts.

### 3. Extremely stable is not the same as worth publishing

`risk_appetite` (deaths per ten minutes), `involvement_level`
(kills+assists per ten minutes), `requeue_tempo`, `session_length` and
`duration_tempo` all reproduce beautifully — SB +0.95 to +0.99. Four of them
are pruned anyway. Reliability that high is what a *level* statistic looks
like, and a level statistic is a population percentile or a calendar fact, not
a behavioural response. `involvement_level` is KDA in costume and
`risk_appetite` is a death rate; publishing either as a Finding would violate
the rule that a Finding must not reduce to raw performance, and would invite a
good/bad reading of a number that is mostly position mix.

`duration_tempo` is carried forward despite being a level family, on the
strength of exceptional reach and stability — but with an explicit flag that
it attributes a ten-player outcome to one player and that mode alone explains
41% of its variance. The tournament must adjudicate that, not this phase.

### 4. Game-state responsiveness is dead

The most attractive story in the universe — "when your team falls behind, do
you fight harder or go quiet?" — has **no between-player heterogeneity at
all**: `sigma_between = 0`, reliability 0.000, SB +0.129. The minute-sampled
variant is worse, with a *negative* split-half of −0.090 despite 208,466
nominal opportunities, because minutes inside a match are strongly dependent
and the nominal count is not information.

Everyone responds to a deficit about the same way. That is a population-common
effect, which belongs in reference context, not in a personal Finding. It is
recorded here rather than quietly dropped precisely because it is the
candidate a product owner would most want to be true.

### 5. Parsed candidates are strong but corpus-thin

Parsed families reach 92–98% of the parsed-eligible accounts and are among the
most stable in the universe. Their limitation is the number of *research*
accounts — 116 in DISCOVERY — which constrains how precisely between-player
heterogeneity can be estimated, not whether the Finding could ship. Both
denominators must be carried into the tournament and the portfolio analysis.

## Frozen serious candidates — 12

Frozen digest `f9f5af7806ee5936e40d826eeb5904fe8bffa488995c967a959f8e9e5456086c`.
The freeze was performed **after** the screen ran over the whole universe, so
it reflects evidence rather than expectation.

| # | candidate | prs | reachS | reachE | SB | info reach SNR≥1 / ≥2 | obs p25/median/p75 | support bar |
|---|---|:--:|---:|---:|---:|---|---|---|
| 1 | post_loss_session_continuation | n | 0.878 | 0.953 | +0.791 | 0.973 / 0.731 | 289 / 553 / 923 | 60 (25/arm) |
| 2 | post_loss_hero_switch | n | 0.848 | 0.920 | +0.897 | 1.000 / 0.902 | 185 / 378 / 664 | 60 (25/arm) |
| 3 | post_loss_requeue_latency | n | 0.848 | 0.920 | +0.796 | 0.980 / 0.664 | 185 / 378 / 664 | 60 (25/arm) |
| 4 | hero_novelty | n | 0.828 | 0.899 | +0.973 | 1.000 / 1.000 | 288 / 537 / 916 | 100 |
| 5 | transfer_risk | n | 0.800 | 0.868 | +0.651 | 0.881 / 0.371 | 291 / 529 / 899 | 60 (25/arm) |
| 6 | transfer_activity | n | 0.800 | 0.868 | +0.623 | 0.815 / 0.210 | 291 / 529 / 899 | 60 (25/arm) |
| 7 | duration_tempo | n | 0.843 | 0.915 | +0.988 | 1.000 / 1.000 | 289 / 553 / 923 | 100 |
| 8 | position_flexibility | Y | 0.188 | 0.974 | +0.882 | 1.000 / 0.965 | 175 / 303 / 468 | 40 |
| 9 | fight_timing_centroid | Y | 0.190 | 0.983 | +0.925 | 0.982 / 0.860 | 296 / 460 / 714 | 40 |
| 10 | purchase_tempo | Y | 0.190 | 0.983 | +0.977 | 1.000 / 1.000 | 297 / 461 / 721 | 40 |
| 11 | lead_retention | Y | 0.185 | 0.957 | +0.572 | 0.577 / 0.018 | 147 / 242 / 396 | 40 (15/arm) |
| 12 | lane_recovery_participation | Y | 0.188 | 0.974 | +0.440 | 0.690 / 0.080 | 221 / 353 / 530 | 40 (15/arm) |

Candidates 11 and 12 are carried as **weak**: their SNR≥2 information reach is
0.018 and 0.080, meaning almost no individual player's own estimate is
separated from zero by two standard errors. They enter the tournament as
likely rejects that deserve one honest test, not as expected finalists.

## Cross-candidate redundancy (Spearman, DISCOVERY)

Only pairs above |0.3| are worth naming; everything else is below 0.28.

| pair | rho | reading |
|---|---:|---|
| post_loss_session_continuation ↔ post_loss_requeue_latency | −0.602 | the strongest overlap in the set: stopping and taking a long gap are close to the same act. The portfolio should carry one, or one family with two facets. |
| fight_timing_centroid ↔ purchase_tempo | +0.508 | both answer "when does your game happen". Related but not interchangeable — one is fights, one is build. |
| lead_retention ↔ post_loss_session_continuation | −0.367 | diffuse; lead_retention correlates weakly with several others, which is a sign of noise rather than shared meaning. |
| post_loss_requeue_latency ↔ lead_retention | +0.349 | as above. |
| post_loss_hero_switch ↔ lead_retention | +0.317 | as above. |
| transfer_risk ↔ transfer_activity | −0.316 | expected; two facets of one Transfer idea. |
| transfer_activity ↔ lead_retention | +0.308 | as above. |

The frozen set is largely orthogonal. Behavioural diversity is available;
redundancy is not the binding constraint on the portfolio.

## Preliminary verdicts on the four inherited concepts

| concept | verdict | evidence |
|---|---|---|
| **Post-Loss** | **SURVIVES STRONGLY — as behaviour, not outcome** | The next-match *result* form is dead (reliability 0.210, SB +0.333). Three behavioural forms are strong: session continuation (+0.791), hero switch (+0.897), re-queue latency (+0.796), all at 92–95% reach of eligible. |
| **Transfer** | **SURVIVES WITH REDESIGN** | The outcome form is dead (SB +0.150). Recast as a within-player contrast on behaviour it holds: `transfer_risk` +0.651, `transfer_activity` +0.623 — but only 37% and 21% of players clear SNR≥2, so it is materially weaker than Post-Loss. |
| **Session Drift** | **REJECTED** | All three forms fail: outcome +0.149, activity +0.178, risk +0.300. Within-session position simply does not carry stable individual differences in this corpus. |
| **Lane Recovery** | **DEMOTED TO ELEMENT** | The outcome form is dead (+0.113). The participation form is weak (+0.440) with 8% of players clearing SNR≥2, and it is parsed-dependent. It enters the tournament only so the rejection is on the record with a proper test. |

Only one of the four inherited concepts is portfolio-grade unchanged, and it
is the one nobody would have picked as the safe bet: not the outcome story,
but what a player *does* after losing.

## Judgement calls the orchestrator and red-team should second-guess

1. **`duration_tempo` was kept** despite being a level family whose largest
   context factor is mode at 41% of variance. It is the weakest justification
   in the frozen set.
2. **The context adjustment removes hero**, which is itself a player choice.
   That is conservative for heterogeneity but it may over-remove real signal
   from the Transfer families, whose whole point is hero choice.
3. **The 3-hour session gap** is a modelling choice, not a measurement.
   `post_loss_session_continuation` is partly a definition artefact and must be
   shown stable across gap thresholds before it ships.
4. **`hero_novelty` is mechanically anti-correlated with match volume**, so it
   partly measures how much someone plays. It needs volume adjustment.
5. **Single-draft and random-draft matches make the hero non-chosen**, which
   contaminates `post_loss_hero_switch` and both Transfer families. They are a
   small share (11,297 of 580,323 rows) but are not yet excluded.
6. **Split-half stability is not test-retest stability.** Splitting a player's
   own matches at random cannot detect drift over a 365-day window; a
   chronological split would say something different and has not been run.
7. **The parsed families' `reachS` of ~0.19 is a corpus artefact**, and quoting
   it as candidate reach would be wrong. Quoting `reachE` alone would also be
   wrong. Both are carried; the tournament must not silently pick one.

## Validation

```text
ruff check scripts tests: PASS
pytest -q tests/unit: 702 passed
negative control (side_sensitivity): sigma_between 0, reliability 0.000, SB +0.036 — PASS
projection convergence drift: < 1e-4 on every family
```

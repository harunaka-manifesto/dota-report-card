# The V7 Finding pipeline, end to end — 2026-09-05

Every previous document measured one stage. This one runs the whole chain over
the real corpus and reports what a player actually receives.

```text
PHASE: V7_FINDING_PIPELINE
STATUS: MEASURED — full run over DISCOVERY, both corpora
NEW PROVIDER CALLS: 0
CORPUS READ: YES — DISCOVERY only, Pass 1 and Pass 2
CANDIDATE_TEST READ: NO — ledger byte-identical before and after
```

Artifacts:

- `scripts/v7_finding_pipeline.py` — the run
- `scripts/v7_research/pass2_observations.py` — per-observation series for the
  eight Pass-2 dimensions
- `docs/evidence/v7-finding-pipeline-2026-09-05.json` — aggregate-only output

## 1. What the pipeline does

```text
features / observations
  -> inference        context removed, blocked means, dependence-robust SE
  -> population        mu and tau per dimension, consistently estimated
  -> ranking           z, reliability, score, shrunk estimate
  -> selection         stratified into the three Finding-carrying sections
```

The one architectural decision worth naming: **Pass-2 dimensions go through the
same estimator as Pass-1 families.** `pass2_features` produces one number per
player, which is the right shape for a census and the wrong shape for ranking —
a standard error needs the series the number came from. `pass2_observations`
emits that series as the same `Opportunity` records Pass 1 uses, so one
inference layer, one population fit, and one comparable reliability scale cover
both halves. A bespoke Pass-2 standard error would have put two incomparable
scales into the same ranking and nothing would have flagged it.

Unit tests pin the two layers together: for every dimension, the length of the
series equals the census observation count and its mean (median, for
`spike_usage`) equals the census value. Measured over three real accounts before
the tests were written, all eight dimensions agreed on observation count
exactly.

## 2. Result

543 players receive a slate. 531 of them (97.8%) receive a full five Findings;
520 (95.8%) get all three sections covered.

| Findings above the 0.25 score line | players | share |
|---:|---:|---:|
| 5 | 285 | 52.5% |
| 4 | 110 | 20.3% |
| 3 | 86 | 15.8% |
| 2 | 39 | 7.2% |
| 1 | 16 | 2.9% |
| 0 | 7 | 1.3% |

**88.6% of players carry three or more Findings above the line.** The owner's
target was 80–90%. The old rule — "significantly different from the population
average" — reached 15.4% and could not be fixed by choosing better candidates.

What changed is the rule, not the data. That is worth stating plainly rather
than presenting the number as a discovery: ranking a player against the
population spread will place most players somewhere on that spread by
construction, and 0.25 is a comparison line carried over from the reliability
table, not a certified publication threshold. The claim this run supports is
"the report has enough well-measured material to fill five slots for nearly
everyone", not "each of those five is individually significant". The owner
asked for the former explicitly.

## 3. Per-dimension reliability

`D` is the dependence inflation read off each family's own variance-ratio curve.
`b` is the batch length it was measured at.

| dimension | source | players | `tau` | reliability (median) | `D` | `b` | plateaued |
|---|---|---:|---:|---:|---:|---:|---|
| vision_coverage | pass2 | 267 | 0.1093 | **0.985** | 1.00 | 100 | yes |
| duration_tempo | pass1 | 538 | 0.1126 | **0.976** | 2.56 | 100 | no |
| death_clustering | pass2 | 273 | 0.0468 | **0.925** | 1.74 | 100 | yes |
| lane_vs_jungle_share | pass2 | 266 | 0.0494 | **0.924** | 3.08 | 50 | no |
| purchase_tempo | pass1 | 116 | 0.0566 | **0.921** | 4.65 | 100 | no |
| deaths_alone_share | pass2 | 266 | 0.0390 | **0.893** | 1.22 | 50 | yes |
| spike_usage | pass2 | 266 | 31.06 | **0.887** | 1.53 | 50 | no |
| position_flexibility | pass1 | 114 | 0.1077 | **0.828** | 2.44 | 100 | no |
| fight_timing_centroid | pass1 | 116 | 0.0116 | **0.810** | 1.74 | 100 | no |
| hero_novelty | pass1 | 525 | 0.1187 | **0.736** | 5.25 | 100 | no |
| closer_vs_comeback | pass2 | 264 | 0.0497 | **0.651** | 1.30 | 100 | yes |
| post_loss_session_continuation | pass1 | 536 | 0.0679 | **0.537** | 2.70 | 100 | no |
| lead_retention | pass1 | 109 | 0.0510 | **0.480** | 1.00 | 100 | yes |
| post_loss_hero_switch | pass1 | 527 | 0.0704 | **0.463** | 4.64 | 100 | no |
| post_loss_requeue_latency | pass1 | 527 | 0.1305 | **0.380** | 2.98 | 100 | no |
| fight_conversion | pass2 | 273 | 0.0087 | **0.257** | 1.02 | 100 | yes |
| lane_recovery_participation | pass1 | 113 | 0.0000 | 0.000 | 1.65 | 100 | yes |
| lane_to_map | pass2 | 258 | 0.0000 | 0.000 | 2.20 | 50 | no |
| transfer_activity | pass1 | 501 | 0.0000 | 0.000 | 2.66 | 100 | no |
| transfer_risk | pass1 | 501 | 0.0000 | 0.000 | 3.02 | 100 | no |
| **side_sensitivity (negative control)** | pass1 | 536 | **0.0000** | **0.000** | 1.06 | 100 | yes |

Sixteen dimensions carry between-player signal. Five go to exactly zero: under a
consistent `tau`, their entire observed spread is explained by
dependence-inflated measurement error, so there is nothing left to rank.

## 4. Two defects this run caught

**`D` went unmeasured on four Pass-2 dimensions.** The first run read `D` at a
fixed batch length of 100. `inference.variance_ratio_curve` needs at least five
blocks per player, and the per-match Pass-2 dimensions give roughly 470
observations per player — four blocks of 100, one short — so the curve returned
`nan` and the code fell back to `D = 1.0`, i.e. independence. That is the
optimistic direction: it understates measurement variance and overstates
reliability, and it happened on four of the highest-reliability dimensions in
the table. The fix reads `D` at the longest batch length the data supports.

The consequence was not cosmetic. **`lane_to_map` fell from reliability 0.598 to
exactly 0.000.** Its apparent between-player spread was dependence-inflated
measurement error the whole time. The first run would have published a Finding
that does not exist.

**A measured `D` below 1.0.** `vision_coverage` measured 0.810 and
`lead_retention` 0.912 — batch means varying *less* than independence predicts.
That is sampling noise far more often than real negative serial dependence, and
accepting it would hand those dimensions free reliability, so `D` is floored at
1.0 and the raw value is recorded alongside. `lead_retention` moved 0.537 to
0.480 as a result.

## 5. Acceptance assertions

All four passed on the corrected run.

1. **The negative control is silent.** `side_sensitivity` estimates `tau`
   exactly 0, gives all 536 players reliability 0, and puts nobody above the
   score line. No rule in the pipeline names the control; it is measured like
   any other dimension. This is the check that the estimator will not
   manufacture a Finding from noise, and the two independent zero collapses in
   §4 are the same behaviour showing up where it was not being watched for.
   The assertion also refuses to pass vacuously — a control with fewer than two
   estimable players is a failure, not a pass.
2. **Every reliability lies in `[0, 1]`.**
3. **No pseudonym reaches the output**, from either corpus, and the substring
   `v7p_` is rejected explicitly.
4. **CANDIDATE_TEST was never read.** DISCOVERY is the only split requested and
   the access ledger is byte-identical before and after the run.

## 6. Known limits

- **`D` is a lower bound wherever the curve has not plateaued** (the `no` rows
  in §3). Where within-player dependence is still rising at the longest
  measurable batch length, the reliability in that row is an upper bound. This
  is the same limitation the tournament recorded for level families over a
  365-day window; contrast families plateau, level families largely do not.
- **`spike_usage` changes estimand between the census and the ranking.** The
  census reports the median gap; the blocked-means estimator takes the mean of
  the same series. The mean of a heavy-tailed gap is the less robust of the two.
  Read the ranking figure as "mean seconds to first impact", not as the census
  number under another name.
- **The 0.25 line is a comparison scale, not a publication threshold.** Cut
  points are calibration work against the reserved split.
- **Pass 2 has no negative control of its own.** `side_sensitivity` is a Pass-1
  family. The two Pass-2 zero collapses are reassuring but they are not a
  designed control, and a Pass-2 control belongs in the calibration phase.
- **Section placement is topical, not a verdict.** A family sits under the
  question it answers; direction decides whether it reads as a strength or a
  cost at render time.

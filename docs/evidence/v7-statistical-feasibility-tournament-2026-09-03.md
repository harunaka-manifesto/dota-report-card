# V7 statistical feasibility tournament — 2026-09-03

An independent statistical assessment of the twelve candidates discovery froze.
The question is not "did discovery find something" but **is each candidate
scientifically capable of becoming a high-reach, valid, personal Finding**. The
inference design was frozen to disk with its own digest before any confirmation
data was read, and CANDIDATE_TEST was read exactly once.

```text
PHASE: V7_LUNA_C_STATISTICAL_FEASIBILITY_TOURNAMENT
STATUS: COMPLETE
SPLITS USED: DISCOVERY (design, calibration, probes) + CANDIDATE_TEST (one confirmation pass)
CANDIDATE_TEST PASSES EXECUTED: 1
CALIBRATION_RESERVED TOUCHED: NO
SEALED_VALIDATION TOUCHED: NO
NEW STRATZ CALLS: 0    OPENDOTA CALLS: 0    PLAYBACK: 0    NETWORK: none
RANK / MMR / IMP / BEHAVIOUR / SMURF / AWARD / PREDICTION USED: NO
PUBLICATION THRESHOLDS CHOSEN: NO
MULTIPLICITY FAMILY FROZEN: NO
POPULATION PERCENTILES BUILT: NO
```

## Provenance

| item | value |
|---|---|
| base SHA | `40c9c7061d31b6eb200d924b117430597a4ff99e` |
| branch | `v7/luna-c-statistical-tournament` |
| corpus run-manifest digest (canonical JSON) | `d45bf9a04d5c2c0c01c115347900eb1cd0e923d3f0570e368b8ce8d3848ec176` |
| corpus run-manifest digest (raw file) | `256676abc8254b6d1dd804a371ea1636469710fee57ca3ce8151dee25a4ed704` |
| feature version | `v7-luna-b-features-1.0.0` (unmodified) |
| registry version | `v7-luna-b-candidate-registry-1.0.0` (unmodified) |
| candidate-definition version | `v7-luna-b-candidates-1.0.0` (unmodified) |
| **frozen serious-candidate digest — recomputed** | `f9f5af7806ee5936e40d826eeb5904fe8bffa488995c967a959f8e9e5456086c` ✅ matches |
| inference version | `v7-luna-c-inference-1.0.0` |
| tournament version | `v7-luna-c-tournament-1.0.0` |
| verdict version | `v7-luna-c-verdicts-1.0.0` |
| **frozen inference-design digest** | `4b702dc29f7cd60caecd74ec2bdba3ff5775038fed664e1eb0fa9ffedc4573f3` |
| seed | `20260903` |
| Type-I replicates per null | 80 |

The frozen registry digest was recomputed from the code before anything else
ran and matches the digest discovery published, so this document evaluates
exactly the twelve candidates that were frozen.

The corpus is byte-identical to the one discovery used. Two digests appear
above because two reasonable digests of the same manifest exist — the raw bytes
on disk and a canonicalised re-serialisation — and the discovery and tournament
scripts originally computed different ones. `manifest_digests()` in
`scripts/v7_research/corpus.py` now emits both from a single shared helper, so
no future document can quote one digest and appear to contradict another. The
JSON artefacts in this phase predate that change and carry the canonical digest
only; they were **not** regenerated, because regenerating them would have spent
a second CANDIDATE_TEST pass to fix a provenance label.

Reproduce, in this order:

```bash
uv run python scripts/v7_statistical_tournament.py freeze-design \
    --out docs/evidence/v7-inference-design-2026-09-03.json
uv run python scripts/v7_statistical_tournament.py discovery \
    --corpus-root <corpus> --design docs/evidence/v7-inference-design-2026-09-03.json \
    --out docs/evidence/v7-statistical-tournament-discovery-2026-09-03.json
uv run python scripts/v7_statistical_tournament.py candidate-test \
    --corpus-root <corpus> --design docs/evidence/v7-inference-design-2026-09-03.json \
    --out docs/evidence/v7-statistical-tournament-candidate-test-2026-09-03.json
uv run python scripts/v7_statistical_tournament.py summarise \
    --discovery ...discovery....json --candidate-test ...candidate-test....json \
    --out docs/evidence/v7-statistical-feasibility-tournament-2026-09-03.json
```

`docs/evidence/v7-candidate-test-access-ledger.jsonl` carries one line per
CANDIDATE_TEST read. It carries **one** line.

## Denominators

Every reach number below is quoted against these, and never against whichever
flatters.

```text
                                    DISCOVERY   CANDIDATE_TEST
sampled accounts                          600              300
product-eligible accounts                 553              282
parsed-detail accounts                    116              119
```

Five denominators are reported per candidate and are never conflated:

```text
sampled                  every account in the split
product-eligible         >= 1 ordinary-lobby match the player finished
structurally eligible    the family produces >= 1 opportunity for this account
information eligible     clears the support bar AND supplies enough valid blocks
                         for a dependence-robust standard error
provisionally qualified  two-sided p < 0.01, unadjusted, on the unshrunk estimate
```

`provisionally qualified` is a **comparison scale for candidates only**. It is
not a publication rule, it carries no multiplicity correction, and this phase
does not choose the level that will ship.

## The frozen inference design

Written to `docs/evidence/v7-inference-design-2026-09-03.json` before the
confirmation split was opened; the confirmation stage refuses to run if the
digest no longer matches the code.

**Unit of observation.** One opportunity, in the player's own chronological
order. Every extractor emits in row order; a unit test asserts it, because the
whole chronological analysis depends on it.

**Estimand.** After additive categorical context effects are projected out over
the split, a *level* family's estimand for player `p` is `E[residual | p]`, and
a *contrast* family's is `E[residual | p, treated] − E[residual | p, control]`.
The arm is carried as an ordinary context factor, so the **population** average
response is removed before any player is compared: a response everyone shares
is not that player's identity (learning 9).

**The null data-generating process, written down before any p-value.** It
differs by family type, and that difference turned out to be the whole story.

- *Contrast family.* H0(p): within `p`'s own sequence, the arm label carries no
  information about the response. The null relabels `p`'s arms by a **circular
  shift**, which preserves the autocorrelation of both series and the arm counts
  exactly. An i.i.d. within-player permutation is carried as a second
  construction so the cost of dependence is measured rather than assumed.
- *Level family.* A within-player permutation leaves a player's mean unchanged,
  so **it is not a null for a level estimand at all** — it would test nothing.
  The estimand-matching null exchanges contiguous residual **blocks** between
  players inside a mode stratum, preserving each player's volume, stratum
  profile and within-block dependence. Block lengths of 25, 100 and 200 are all
  reported, plus the i.i.d. case.

**Test statistic.** Batched means over contiguous chronological blocks; the
estimate is the mean of the valid block statistics, the standard error is
`sd(block statistics)/sqrt(K)`, referred to Student `t` on `K−1` df, two-sided.

**Block geometry, chosen from a measurement rather than a preference.** See
§2 — contrast families use 20 blocks with a floor of 4 opportunities each;
level families use blocks of at least 100 opportunities with a floor of 4
blocks.

**Partial pooling.** `δ_p ~ N(μ, τ²)`, `δ̂_p | δ_p ~ N(δ_p, SE_p²)`, with `τ²`
by Paule–Mandel (which, unlike DerSimonian–Laird, does not assume the standard
errors are homogeneous — they range over an order of magnitude here).
Qualification is decided on the **unshrunk** statistic, and the reach a
shrunken rule *would* have manufactured is reported as its own column.

---

## 1. The negative control: the method does not manufacture individuality

`side_sensitivity` — Radiant versus Dire, which no player controls — was run
through the entire pipeline on both splits.

| measure | DISCOVERY | CANDIDATE_TEST |
|---|---|---|
| information-eligible | 527 / 553 product-eligible | 269 / 282 |
| provisionally qualified at 0.01 | **5 (0.95%)** | **5 (1.9%)** |
| provisionally qualified at 0.05 | 24 (4.6%) | — |
| τ | 0.0145 | 0.0327 |
| I² | 0.064 | — |
| median shrinkage factor | 0.113 | — |
| chronological split-half SB | **−0.073** | **+0.218** |
| realised Type-I, circular null | 0.0500 / 0.0103 | 0.0496 / 0.0097 |
| measured dependence ratio V(100)/V(1) | **1.06** | — |

The method finds nothing where there is nothing. Its rejection rate on the
control matches nominal, its heterogeneity is near zero, and its dependence
diagnostic is flat at 1.06 while every behavioural family reads 1.65–5.25.

**But the control also produced this phase's most useful auxiliary number.**
Its *chronological* split-half was −0.073 on one split and **+0.218** on the
other. That is a pure-noise statistic taking values up to +0.22 at these sample
sizes. So:

> **A chronological split-half below roughly +0.25 is not evidence of
> stability.** It is inside the negative control's own range.

That band is applied below, and it is what demotes `transfer_activity` and
`lead_retention`.

---

## 2. The central result: contrast estimands are inferentially safe, level
estimands are not

Before trusting any block length, the *actual* within-player serial dependence
was measured. For batch length `b`, `V(b) = b · Var(batch means)`; under
independence `V(b)/V(1) = 1` for all `b`, and under dependence of range `R` it
rises and plateaus once `b > R`.

| family | V(5) | V(25) | V(100) | type |
|---|---:|---:|---:|---|
| hero_novelty | 1.38 | 2.71 | **5.25** | level |
| purchase_tempo | 1.31 | 2.35 | **4.65** | level |
| post_loss_hero_switch | 1.45 | 2.41 | 4.64 | contrast |
| transfer_risk | 1.14 | 1.64 | 3.02 | contrast |
| post_loss_requeue_latency | 1.11 | 1.69 | 2.98 | contrast |
| post_loss_session_continuation | 0.91 | 1.43 | 2.70 | contrast |
| transfer_activity | 1.14 | 1.54 | 2.66 | contrast |
| duration_tempo | 1.11 | 1.53 | 2.56 | level |
| position_flexibility | 1.25 | 1.70 | 2.44 | level |
| fight_timing_centroid | 1.05 | 1.25 | 1.74 | level |
| lane_recovery_participation | 1.09 | 1.34 | 1.65 | contrast |
| lead_retention | 0.98 | 0.93 | 0.91 | contrast |
| **side_sensitivity (control)** | 1.00 | 1.02 | **1.06** | contrast |

**The curve has not plateaued by `b = 100` for any behavioural family.** A
365-day history drifts — patch, meta, hero pool, life — and no block length this
corpus can support is long enough to contain that drift. That has two opposite
consequences:

- A **contrast** estimand differences the drift out *within the player*. Its
  null — the circular shift — preserves the real dependence exactly, so its
  Type-I is directly measurable rather than assumed. **All seven contrast
  families measure calibrated or conservative on both splits.**
- A **level** estimand does not difference anything out. Its uncertainty must
  absorb the full dependence, and it demonstrably cannot.

Realised Type-I at nominal 0.05 / 0.01, DISCOVERY (80 replicates each; the
Monte-Carlo error is computed across replicates, not across the dependent
player tests inside one replicate, and runs 0.001–0.005):

| family | i.i.d. | range 25 | range 100 | range 200 | verdict |
|---|---:|---:|---:|---:|---|
| duration_tempo | 0.049/0.009 | 0.115/0.039 | 0.138/0.043 | 0.214/0.086 | anticonservative |
| hero_novelty | **0.076/0.019** | 0.064/0.016 | 0.093/0.032 | 0.185/0.080 | anticonservative even i.i.d. |
| purchase_tempo | 0.056/0.011 | 0.059/0.014 | 0.083/0.020 | 0.199/0.079 | anticonservative |
| position_flexibility | 0.041/0.007 | 0.053/0.011 | 0.079/0.020 | 0.192/0.074 | anticonservative beyond 25 |
| fight_timing_centroid | 0.048/0.008 | 0.049/0.011 | 0.069/0.016 | 0.152/0.047 | anticonservative beyond 25 |

Contrast families, primary circular-shift null, both splits:

| family | DISCOVERY 0.05/0.01 | CANDIDATE_TEST 0.05/0.01 |
|---|---|---|
| post_loss_session_continuation | 0.0508 / 0.0099 | 0.0525 / 0.0104 |
| post_loss_hero_switch | 0.0500 / 0.0091 | 0.0480 / 0.0087 |
| post_loss_requeue_latency | 0.0488 / 0.0100 | 0.0481 / 0.0085 |
| transfer_risk | 0.0488 / 0.0082 | 0.0447 / 0.0086 |
| transfer_activity | 0.0475 / 0.0090 | 0.0470 / 0.0084 |
| lead_retention | 0.0549 / 0.0137 | 0.0440 / 0.0100 |
| lane_recovery_participation | 0.0507 / 0.0102 | 0.0498 / 0.0100 |
| **side_sensitivity (control)** | 0.0500 / 0.0103 | 0.0496 / 0.0097 |

Longer batches were tried on DISCOVERY and rejected as a fix: at a batch length
of 100, `duration_tempo` still reads 0.135/0.045 against a range-100 null while
losing 27% of its information-eligible players. The level families' block
geometry (≥100 per block, ≥4 blocks) is the most honest available, not a
sufficient one. **Saying so is the result.**

### Method is not the same as signal

Two of the three D grades come from families whose *test* is fine. The circular
null certifies `lane_recovery_participation` at 0.0498/0.0100 — and then the
real data returns 2 of 113 rejections on the confirmation split. That is the
null rate. The method worked; the candidate did not.

---

## 3. What honest uncertainty costs in reach

The screen reported information reach against a method-of-moments SNR. Under
the inferential model with a dependence-robust standard error, the level
families lose a large share of their eligible population outright, because a
player needs 400 opportunities to supply four blocks of 100.

| family | screen reach of sampled | tournament information-eligible / sampled | of applicable denominator |
|---|---:|---:|---:|
| duration_tempo | 0.843 | **372 / 600 = 0.620** | 372 / 553 = 0.673 |
| hero_novelty | 0.828 | **355 / 600 = 0.592** | 355 / 553 = 0.642 |
| position_flexibility | 0.188 | **37 / 600 = 0.062** | 37 / 116 = 0.319 |
| fight_timing_centroid | 0.190 | 67 / 600 = 0.112 | 67 / 116 = 0.578 |
| purchase_tempo | 0.190 | 68 / 600 = 0.113 | 68 / 116 = 0.586 |
| post_loss_session_continuation | 0.878 | 527 / 600 = 0.878 | 527 / 553 = 0.953 |
| post_loss_hero_switch | 0.848 | 511 / 600 = 0.852 | 511 / 553 = 0.924 |
| post_loss_requeue_latency | 0.848 | 511 / 600 = 0.852 | 511 / 553 = 0.924 |
| transfer_risk / transfer_activity | 0.800 | 495 / 600 = 0.825 | 495 / 553 = 0.895 |
| lead_retention | 0.185 | 109 / 600 = 0.182 | 109 / 116 = 0.940 |
| lane_recovery_participation | 0.188 | 113 / 600 = 0.188 | 113 / 116 = 0.974 |

The contrast families lose nothing. The level families lose between a fifth and
four-fifths of their reach.

### Shrinkage does not rescue it, and would fake it

Reported as a distribution, never as one number. `shrinkage_reach_inflation` is
the extra share of players a posterior-based rule would have declared credibly
non-zero, over the unshrunk rule.

| family | B p10 | B median | B p90 | reach a shrunken rule would have added |
|---|---:|---:|---:|---:|
| duration_tempo | 0.968 | 0.989 | 0.996 | **+15.3 pts** |
| purchase_tempo | 0.946 | 0.982 | 0.996 | **+13.2 pts** |
| hero_novelty | 0.732 | 0.921 | 0.985 | **+13.2 pts** |
| fight_timing_centroid | 0.811 | 0.909 | 0.972 | +11.9 pts |
| position_flexibility | 0.889 | 0.957 | 0.979 | +10.8 pts |
| post_loss_hero_switch | 0.709 | 0.905 | 0.975 | −0.6 pts |
| post_loss_session_continuation | 0.635 | 0.870 | 0.950 | −0.6 pts |
| post_loss_requeue_latency | 0.592 | 0.845 | 0.942 | −0.4 pts |
| transfer_risk | 0.239 | 0.554 | 0.803 | −2.2 pts |
| transfer_activity | 0.203 | 0.510 | 0.767 | −1.8 pts |
| lane_recovery_participation | 0.129 | 0.378 | 0.587 | −1.8 pts |
| **side_sensitivity (control)** | 0.029 | 0.113 | 0.260 | −0.8 pts |

The pattern is exactly the warning the packet raised: **the families whose
p-values are least trustworthy are the ones where shrinkage would have bought
the most apparent reach.** Qualification is therefore decided unshrunk, and the
control's shrinkage factors (median 0.113) confirm the pooling model does not
invent structure.

### Power

Minimum detectable effect at two-sided 0.05 and 80% power, at the p25 / median
/ p75 of each family's own standard error, in the estimand's own units.

| family | units | MDE p25 | MDE median | MDE p75 | observed \|δ\| median |
|---|---|---:|---:|---:|---:|
| post_loss_session_continuation | probability | 0.084 | 0.111 | 0.150 | 0.064 |
| post_loss_hero_switch | probability | 0.072 | 0.102 | 0.147 | 0.047 |
| post_loss_requeue_latency | log seconds | 0.200 | 0.278 | 0.391 | 0.138 |
| hero_novelty | probability | 0.063 | 0.100 | 0.166 | 0.076 |
| transfer_risk | deaths / 10 min | 0.242 | 0.348 | 0.491 | 0.113 |
| transfer_activity | (K+A) / 10 min | 0.678 | 0.893 | 1.307 | 0.303 |
| duration_tempo | log seconds | 0.025 | 0.033 | 0.045 | 0.026 |
| purchase_tempo | game progress | 0.020 | 0.029 | 0.040 | 0.033 |
| fight_timing_centroid | game progress | 0.010 | 0.014 | 0.017 | 0.008 |
| position_flexibility | probability | 0.060 | 0.084 | 0.116 | 0.078 |
| lead_retention | probability | 0.123 | 0.157 | 0.204 | 0.056 |
| lane_recovery_participation | events / 10 min | 1.072 | 1.306 | 1.847 | 0.370 |

`transfer_risk`, `transfer_activity`, `lead_retention` and
`lane_recovery_participation` all sit with a median observed effect well below
their median MDE — the typical player simply cannot be measured for them. That
is why their qualified shares are 6–8% and lower.

---

## 4. The seven judgement calls discovery flagged

### 4.1 Does `duration_tempo` survive as anything other than a mode-mix statistic? **No.**

A player's estimate computed on Turbo matches alone and on standard matches
alone agree at **Spearman +0.495 across 168 players**, against a within-mode
split-half reliability near +0.99. Between-player spread is also mode-specific:
τ 0.145 inside Turbo versus 0.085 inside standard. Mode explains 41% of raw
opportunity variance and lobby a further 34%. The pooled per-player number is
about half one personal tempo and half a mode-mix artefact — and it attributes a
ten-player outcome to one player. Add the worst Type-I on the confirmation split
(0.171/0.076 at dependence range 25). **Graded C. Discovery's own weakest
justification was correctly identified as weak.**

### 4.2 Does removing hero from the projection over-remove the Transfer signal? **Yes, materially.**

| family | τ with hero | τ without hero | chrono SB with | chrono SB without | ρ between the two views | sd ratio |
|---|---:|---:|---:|---:|---:|---:|
| transfer_risk | 0.1311 | **0.2031** | +0.467 | **+0.609** | +0.768 | 1.253 |
| transfer_activity | 0.3076 | **0.4009** | +0.390 | **+0.496** | +0.799 | 1.128 |

Removing hero raises between-player spread by 55% and 30% and lifts
chronological stability by 0.14 and 0.11. Discovery's suspicion was right: hero
is close to the treatment itself, and projecting it out removes part of what the
Transfer estimand is about.

**But the correction is not free**, and I do not recommend simply adopting the
hero-free version. Without hero in the projection, a player whose stretch pool
happens to contain harder heroes shows a larger δ that is a hero-mix effect, not
personal responsiveness. The right resolution is a hero-*difficulty* covariate
estimated from the population, not hero identity — which is a redesign, not a
switch. **This is an open estimand question, and it is why `transfer_risk` is B
rather than A.**

### 4.3 Is `post_loss_session_continuation` stable across session-gap thresholds? **Yes, comfortably.**

Per-player agreement with the frozen 3-hour definition:

| family | 2 h | 4 h | 6 h |
|---|---:|---:|---:|
| post_loss_session_continuation | +0.982 | +0.991 | **+0.973** |
| post_loss_hero_switch | +0.979 | +0.985 | +0.972 |
| position_flexibility | +0.996 | +0.998 | +0.997 |
| post_loss_requeue_latency | +0.940 | +0.954 | **+0.913** |

Discovery's worry that the estimand is "partly a definition artefact" is not
supported for session continuation: ρ ≥ +0.973 over a threefold range of the
threshold, with τ moving only 0.088–0.103. `post_loss_requeue_latency` is the
sensitive one (ρ +0.913 at 6 h, τ 0.195 → 0.263), which is mechanical — the
session boundary truncates the latency being measured — and contributes to its B.

### 4.4 Does `hero_novelty` survive volume adjustment? **No.**

The per-player estimate correlates **−0.526** (Spearman) with log match volume.
Capping every player's exposure at their first 500 matches moves that only to
**−0.349**, while the estimates themselves agree at ρ +0.944 — i.e. the volume
dependence is not a truncation artefact that an exposure cap removes. It is
mechanical: play more, and a hero is likelier to have been seen in the last 30
days. Combined with a test that is anticonservative *even under the i.i.d. null*
(0.076/0.019), **graded C**. It needs an estimand that conditions on opportunity
rather than a post-hoc adjustment.

### 4.5 What is the effect of excluding single-draft and random-draft matches? **Essentially nothing.**

| family | ρ with baseline | information-eligible before → after | τ before → after |
|---|---:|---|---|
| hero_novelty | +0.993 | 355 → 348 | 0.1020 → 0.1031 |
| post_loss_hero_switch | +0.993 | 511 → 508 | 0.1068 → 0.1092 |
| transfer_risk | +0.968 | 495 → 492 | 0.1311 → 0.1356 |
| transfer_activity | +0.956 | 495 → 492 | 0.3076 → 0.3017 |

11,297 of 580,323 rows is 1.9%, and the contamination discovery flagged is real
but immaterial. Excluding them is the cleaner definition and costs 3–7 accounts;
either choice is defensible and neither changes a grade.

### 4.6 Chronological versus random split-half. **The random split was flattering everything.**

| family | random SB | **chronological SB** | drop |
|---|---:|---:|---:|
| duration_tempo | +0.988 | +0.912 | 0.076 |
| purchase_tempo | +0.977 | +0.937 | 0.040 |
| hero_novelty | +0.973 | +0.835 | 0.138 |
| fight_timing_centroid | +0.925 | +0.766 | 0.159 |
| post_loss_hero_switch | +0.897 | +0.781 | **0.116** |
| position_flexibility | +0.882 | +0.796 | 0.086 |
| post_loss_requeue_latency | +0.745 | +0.737 | 0.008 |
| post_loss_session_continuation | +0.758 | +0.754 | 0.004 |
| transfer_risk | +0.635 | +0.467 | **0.168** |
| lane_recovery_participation | +0.589 | +0.414 | 0.175 |
| transfer_activity | +0.549 | +0.390 | **0.159** |
| lead_retention | +0.431 | +0.366 | 0.065 |
| side_sensitivity (control) | −0.064 | −0.073 | — |

Discovery was right that a random split cannot see drift. The correction is
0.00–0.18 and hits hardest exactly where it matters: the two Transfer families
and `hero_novelty`. Read alongside §1, the control's own chronological figure of
+0.218 on the confirmation split means **nothing below ~+0.25 should be read as
stability at all**.

### 4.7 Parsed reach: both denominators, always.

Both are carried in every table above. The parsed families' reach of sampled
(0.06–0.19) is a corpus-design artefact — parsed detail was only collected for
the predeclared subset — and their reach of parsed-eligible (0.32–0.97) is the
candidate property. Neither alone is the answer.

A further probe not asked for but worth having: the history-only families were
recomputed on parsed matches only, to see how much parsed selection would move
the estimand if a candidate were ever restricted to it.

| family | ρ with the full-history estimate | accounts |
|---|---:|---:|
| hero_novelty | +0.990 | 62 |
| duration_tempo | +0.944 | 68 |
| post_loss_session_continuation | +0.920 | 113 |
| post_loss_requeue_latency | +0.903 | 108 |
| post_loss_hero_switch | +0.889 | 108 |
| transfer_activity | +0.718 | 106 |
| transfer_risk | +0.695 | 106 |

The Post-Loss families are robust to parsed selection. The Transfer families are
the most sensitive at ρ ≈ +0.70, which is another reason they are not A.

---

## 5. The confirmation pass

One pass. No definition was changed after it, and nothing below was rescued.

| family | D info-elig | C info-elig | D qualified 0.01 | C qualified 0.01 | D τ | C τ | D chrono SB | **C chrono SB** | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| post_loss_session_continuation | 527 | 269 | 145 (27.5%) | 60 (22.3%) | 0.098 | 0.089 | +0.754 | +0.749 | confirmed |
| post_loss_hero_switch | 511 | 263 | 103 (20.2%) | 45 (17.1%) | 0.107 | 0.077 | +0.781 | +0.737 | confirmed |
| post_loss_requeue_latency | 511 | 263 | 114 (22.3%) | 47 (17.9%) | 0.219 | 0.210 | +0.737 | +0.758 | confirmed |
| hero_novelty | 355 | 182 | 109 (30.7%) | 59 (32.4%) | 0.102 | 0.114 | +0.835 | +0.862 | confirmed, still uncalibrated |
| transfer_risk | 495 | 257 | 39 (7.9%) | 20 (7.8%) | 0.131 | 0.130 | +0.467 | +0.552 | confirmed, weak |
| transfer_activity | 495 | 257 | 30 (6.1%) | 18 (7.0%) | 0.308 | 0.282 | +0.390 | **+0.176** | **stability fails** |
| duration_tempo | 372 | 190 | 120 (32.3%) | 70 (36.8%) | 0.094 | 0.073 | +0.912 | +0.890 | confirmed, still uncalibrated |
| position_flexibility | 37 | 32 | 13 (35.1%) | 9 (28.1%) | 0.106 | 0.082 | +0.796 | +0.833 | confirmed, tiny reach |
| fight_timing_centroid | 67 | 60 | 16 (23.9%) | 15 (25.0%) | 0.013 | 0.015 | +0.766 | +0.800 | confirmed, Type-I worse |
| purchase_tempo | 68 | 60 | 35 (51.5%) | 27 (45.0%) | 0.062 | 0.046 | +0.937 | +0.873 | confirmed |
| lead_retention | 109 | 112 | 5 (4.6%) | 5 (4.5%) | 0.055 | 0.053 | +0.366 | +0.305 | at the null |
| lane_recovery_participation | 113 | 113 | 4 (3.5%) | **2 (1.8%)** | 0.344 | 0.475 | +0.414 | +0.596 | **at the null** |
| side_sensitivity (control) | 527 | 269 | 5 (0.95%) | 5 (1.9%) | 0.015 | 0.033 | −0.073 | **+0.218** | control behaved |

`lane_recovery_participation` returns 1.8% of players against a *measured* null
rate of 1.0% on the same split. `lead_retention` returns 4.5% against a measured
1.0%. `transfer_activity`'s chronological stability lands inside the negative
control's own band.

---

## 6. Grades

| candidate | grade | one-line reason |
|---|:--:|---|
| `post_loss_session_continuation` | **A** | Calibrated null on both splits, 95.3%/95.4% of product-eligible, τ 0.098 with I² 0.796, chronological stability +0.75 on both, and ρ ≥ +0.92 through every declared probe. |
| `post_loss_hero_switch` | **A** | Best heterogeneity-to-noise among the calibrated families (τ 0.107, I² 0.845), 92.4%/93.3% reach, chronological +0.78/+0.74, and the draft contamination discovery feared moves nothing (ρ +0.993). |
| `post_loss_requeue_latency` | **B** | As statistically sound as the two A candidates, but ρ −0.58 with session continuation and the most session-gap-sensitive family in the set. |
| `transfer_risk` | **B** | The only Transfer form that survives confirmation (chronological +0.47 → +0.55), but only ~8% of players clear the bar and the hero-in-projection question leaves the estimand unsettled. |
| `purchase_tempo` | **B** | The strongest heterogeneity in the whole set (I² 0.969, chronological +0.94/+0.87, 45–52% qualified), but a level family whose p-value cannot be certified, on an item vocabulary the atlas rates unverified. |
| `hero_novelty` | **C** | Correlates −0.526 with match volume (−0.349 after exposure capping) and is anticonservative even under the i.i.d. null; it partly measures how much you play. |
| `duration_tempo` | **C** | Turbo-only and standard-only estimates agree at only ρ +0.495 against near-perfect within-mode reliability, so it is substantially a mode-mix statistic; worst Type-I on the confirmation split. |
| `position_flexibility` | **C** | Statistically healthy (I² 0.933, chronological +0.80/+0.83) but honest block geometry leaves it reaching 32%/27% of parsed-eligible accounts. |
| `fight_timing_centroid` | **C** | Real and stable, but the p10–p90 spread is ±1.5% of game progress — half a minute — which is too small to narrate, and the null degraded between splits. |
| `transfer_activity` | **D** | Chronological stability falls from +0.390 to +0.176, inside the negative control's own band of −0.073 to +0.218. A confirmation failure. |
| `lead_retention` | **D** | 4.6% and 4.5% qualified against a measured Type-I of 1.4% and 1.0%; a team-level outcome estimand with chronological stability at the control band's edge. |
| `lane_recovery_participation` | **D** | 3.5% then 1.8% qualified against a measured Type-I of exactly 1.0%. The confirmation is indistinguishable from the null. |

## 7. The A/B decision table

| | `post_loss_session_continuation` | `post_loss_hero_switch` | `post_loss_requeue_latency` | `transfer_risk` | `purchase_tempo` |
|---|---|---|---|---|---|
| **grade** | **A** | **A** | **B** | **B** | **B** |
| **player-facing concept** | Does a loss make you keep playing, or stop for the day? | After a loss, do you change hero or run it back? | When you lose, do you jump straight back in or take a breath? | Do you die more when you step off your comfort heroes? | How far into a game are you when your build comes together? |
| **inherited vs novel** | inherited (Post-Loss), recast to behaviour | inherited (Post-Loss), recast to behaviour | inherited (Post-Loss), recast to behaviour | inherited (Transfer), recast to a within-player contrast | novel (STRATZ-native item timing) |
| **unit of observation** | one in-session match with a known successor state | one in-session match transition | one in-session match transition | one match after a 50-match comfort-pool warm-up | one parsed match with ≥8 purchases |
| **estimand** | Δ context-adjusted P(another match follows), loss − win | Δ context-adjusted P(next hero differs), loss − win | Δ context-adjusted log gap to next match, loss − win | Δ context-adjusted deaths/10 min, stretch − comfort | mean context-adjusted game progress at the 8th purchase |
| **structural reach** | 552/553 = 99.8% of product-eligible | 551/553 = 99.6% | 551/553 = 99.6% | 530/553 = 95.8% | 116/116 = 100% of parsed-eligible |
| **information reach** | 527/553 = 95.3% (D), 269/282 = 95.4% (C) | 511/553 = 92.4%, 263/282 = 93.3% | 511/553 = 92.4%, 263/282 = 93.3% | 495/553 = 89.5%, 257/282 = 91.1% | 68/116 = 58.6%, 60/119 = 50.4%; **11.3% of sampled** |
| **median obs/player** | 552 (p25 289, p75 923) | 378 (185, 664) | 378 (185, 664) | 529 (291, 898) | 461 (297, 720) |
| **candidate-test reach** | 269/300 sampled = 89.7% | 263/300 = 87.7% | 263/300 = 87.7% | 257/300 = 85.7% | 60/300 = 20.0%; 50.4% of parsed-eligible |
| **between-player heterogeneity** | τ 0.098, I² 0.796 (C: τ 0.089) | τ 0.107, I² 0.845 (C: 0.077) | τ 0.219, I² 0.765 (C: 0.210) | τ 0.131, I² 0.427 (C: 0.130) | τ 0.062, I² 0.969 (C: 0.046) |
| **preliminary stability (chronological SB)** | +0.754 / +0.749 | +0.781 / +0.737 | +0.737 / +0.758 | +0.467 / +0.552 | +0.937 / +0.873 |
| **parsed dependency** | none | none | none | none | full; and item semantics unverified |
| **role/position coverage** | all roles; role not observed for the family | all roles | all roles | all roles | CORE 62%, HARD_SUPPORT 20%, LIGHT_SUPPORT 18% of opportunities |
| **patch/context sensitivity** | largest η² is duration at 0.008 | hero 0.029 | mode 0.032, lobby 0.027 | hero 0.069, mode 0.041 | hero 0.131, position 0.070 |
| **main confounders** | time of day, real-life schedule, accumulated session length, right-censoring | hero pool size, mode, party role assignment | queue times, party regrouping, time of day | hero difficulty, position, pool size | consumables, unverified item vocabulary, position, game length |
| **provisional null-model viability** | STRONG: 0.0508/0.0099 and 0.0525/0.0104 | STRONG: 0.0500/0.0091 and 0.0480/0.0087 | STRONG: 0.0488/0.0100 and 0.0481/0.0085 | STRONG, slightly conservative: 0.0488/0.0082 and 0.0447/0.0086 | WEAK: i.i.d. fine, but 0.083/0.020 at dependence range 100 |
| **expected publication reach (provisional)** | roughly a quarter of information-eligible users; structurally near-universal | roughly a fifth; structurally near-universal | roughly a fifth; structurally near-universal | **likely low** — about 8% of information-eligible | **likely high among parsed-eligible** (45–52%), but only 11% of sampled |
| **report-time cost** | history only; one linear pass, milliseconds | history only; milliseconds | history only; milliseconds | history only; milliseconds | parsed detail; one sort per match, moderate |
| **narrative quality** | high — recognisable, non-judgemental | high — a concrete visible act | high — "you are a chaser" | high — vivid and directional | high and unusually concrete |
| **distinctiveness** | high, but ρ −0.58 with requeue latency | high; no \|ρ\| > 0.30 with anything | moderate; ρ −0.58 with continuation | good; ρ −0.36 with transfer_activity | moderate; ρ +0.47 with fight_timing_centroid |
| **primary failure risk** | right-censoring at the observation edge; session-gap convention | hero-pool size is a lurking third variable not in the projection | portfolio redundancy plus definitional sensitivity | hero is in the projection and is close to the treatment itself | unverified item vocabulary; level-family SE cannot be certified |

## 8. Portfolio consequence

Counting how many of the twelve each player provisionally qualifies for, at the
unadjusted 0.01 level, **before any multiplicity correction** — that is, this is
an optimistic bound, not a forecast:

| qualified findings | DISCOVERY (of 600) | CANDIDATE_TEST (of 300) |
|---|---:|---:|
| 0 | 261 | 119 |
| 1 | 144 | 81 |
| 2 | 87 | 50 |
| 3 | 53 | 25 |
| ≥4 | 55 | 25 |

```text
≥1 finding   339/600 = 56.5%      181/300 = 60.3%
≥2 findings  195/600 = 32.5%      100/300 = 33.3%
≥3 findings  108/600 = 18.0%       50/300 = 16.7%
             (19.5% of product-eligible)  (17.7% of product-eligible)
```

**Against a design target of ≥3 qualified Findings for 80–90% of sufficiently
active eligible users, the frozen twelve deliver roughly 18%** — and that is
before multiplicity, before publication-effect thresholds, and while still
counting the C and D candidates. Restricted to the A and B candidates the
number will be lower still.

This is a portfolio-design result, not a licence to relax anything. The correct
response, per learning 1, is candidate redesign, and §9 says where.

## 9. What I would tell the orchestrator to change

1. **The Post-Loss territory is the portfolio's spine and is under-exploited.**
   Three of its behavioural forms are the only calibrated, high-reach, stable
   candidates in the set, and two of them overlap. More *distinct* behavioural
   responses to a setback would raise portfolio reach far more cheaply than
   rescuing any level family.
2. **Prefer contrast estimands to level estimands, as a design rule.** This is
   the phase's most transferable finding: within-player differencing is what
   makes a valid p-value reachable over a drifting 365-day window. Every level
   family here failed calibration; every contrast family passed.
3. **`purchase_tempo` deserves a contrast reformulation.** It has the best
   heterogeneity in the set. Recast as a within-player contrast — build tempo on
   comfort versus stretch heroes, or after a loss versus a win — it would inherit
   the calibrated null and could become an A.
4. **Verify the item vocabulary before anything is built on it.** The atlas
   already flags it; `purchase_tempo`'s B is partly that flag's fault.
5. **Do not adopt the hero-free Transfer projection as-is.** It raises τ by 55%
   for the right-looking reason and the wrong actual reason. Model hero
   *difficulty*, not hero identity.

## 10. My own judgement calls the orchestrator should challenge

1. **Block geometry.** I chose ≥100 opportunities per block for level families
   and 20 blocks for contrast families from a measured dependence curve — but
   the curve never plateaus, so no choice is provably right. A different reader
   might set the level bar at 200 and reject `purchase_tempo` outright, or at 25
   and grade it A. The sweep is published so this is checkable.
2. **The negative control's chronological band.** I used two observations
   (−0.073, +0.218) to set a "below +0.25 is not stability" rule. Two points is
   thin. It is the reason `transfer_activity` is D rather than C, and that grade
   should be challenged.
3. **The provisional 0.01 level.** Chosen as a comparison scale only. Every
   qualified-share number moves if it moves, though the *ordering* of candidates
   is stable at 0.05 as well.
4. **The block-reassignment null for level families may be slightly adversarial.**
   When the planted block length is close to the estimator's own batch length,
   misaligned batches share blocks and the standard error understates. Some of
   the range-25 anticonservatism could be that artefact rather than a real
   defect. The range-100 and range-200 results are not vulnerable to it, and they
   are worse, so the conclusion holds — but the range-25 column should be read
   with that caveat.
5. **Type-I was measured by permuting residuals with the context projection held
   fixed**, rather than re-projecting inside every replicate. That is the
   standard fixed-design approach and it is what made 80 replicates × 13 families
   affordable, but it is an approximation.
6. **`duration_tempo` at C rather than D.** It carries real individual
   information *within a mode*. I kept it at C on that basis; someone weighing
   "a ten-player outcome attributed to one player" more heavily would reject it.
7. **`post_loss_requeue_latency` at B rather than A.** The demotion is entirely
   portfolio reasoning (ρ −0.58 with session continuation) plus gap sensitivity.
   On its own statistics it is an A.
8. **I did not rescue anything, and two probes were repaired mid-DISCOVERY.**
   The volume-equalisation and mode-split probes initially returned no players
   because the level block geometry needs 400 opportunities; I raised the cap to
   500 and declared a relaxed *descriptive* geometry for point-estimate
   comparisons only, re-ran DISCOVERY end to end, and then froze. No p-value is
   read from a relaxed run. This happened before the confirmation pass.

## Validation

```text
frozen serious-candidate digest recomputed: f9f5af78...5086c — MATCHES discovery
frozen inference-design digest:             4b702dc2...573f3 — written before CANDIDATE_TEST
CANDIDATE_TEST passes executed:             1 (ledger: docs/evidence/v7-candidate-test-access-ledger.jsonl)
reserved / sealed splits touched:           NO (corpus reader fails closed; unit-tested)
new provider calls:                         0
negative control:                           tau 0.0145, I2 0.064, 5/527 at nominal 0.01,
                                            Type-I 0.0500/0.0103 — PASS
uv run ruff check scripts tests:            PASS
uv run pytest -q tests/unit:                758 passed
```

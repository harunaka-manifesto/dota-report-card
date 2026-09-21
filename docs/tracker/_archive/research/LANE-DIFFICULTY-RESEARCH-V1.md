# Lane Difficulty V1 — Research & Decision Document

Status: RESEARCH / DECISION PROPOSAL (not yet an ACTIVE SSOT)
Date: 2026-09-20
Scope: whether and how to contextualise laning metrics by lane difficulty
Audience: product, design, backend, coding agents

Related contracts:
[Role Metrics & Personal Baselines V1](../superseded_ssots/role-metrics-and-baselines-v1.md) ·
[Role Resolution & Correction V1](../superseded_ssots/role-resolution-and-correction-v1.md) ·
[Post-Match Insights SSOT](../engine_specs/POST-MATCH-INSIGHTS-SSOT.md) ·
[Post-Match Intelligence Feasibility V1](post-match-intelligence-feasibility-v1.md)

Reproduction code: [`lane-difficulty-research-code/`](../scripts/lane-difficulty-research-code)

---

## 0. Evidence base and its limits

Everything numeric below was computed **offline, read-only**, from data already
in this repository. No new STRATZ calls were made this session: `STRATZ_API_TOKEN`
is not present in the environment and I did not go looking for it. §3 marks
every signal as CONFIRMED (observed in real payloads) or UNVERIFIED (schema-only
or not collected). §15 lists exactly which probes must be run before this
becomes an SSOT.

| Corpus | Contents | Used for |
|---|---|---|
| `.local/corpora/stratz/v7-pass2-2026-09-04/canonical` | 278 accounts × ≤500 matches → **96,520** usable matches; all ten players' `hero_id`/`lane`/`position`, tracked player's trajectories | primary model fitting, personal-baseline test |
| `.local/stratz-probe/*/raw` | 1,295 cached responses → **12,048** matches with **ten-player** `stats` | ten-player validation, field-coverage audit |
| Merged, deduplicated on `(match_id, hero, position)` | **98,263** matches / **197,560** lane-side rows | all §5 / §10 / §11 numbers |

**Population caveat (important).** These are active, public, parse-heavy
accounts, not a random sample of Dota, and — per the project's existing rank
fence — nothing here is conditioned on bracket. Effects are population averages
across mixed skill. §11 shows a falsification test proving the effect is not a
skill proxy, but the magnitudes should be re-estimated on the production
corpus before shipping numbers.

---

## 1. Executive Recommendation

**PARTIALLY — YES for a narrow, core-only, Standard-only V1. NO to the model as
originally framed.**

Build a **draft-only lane difficulty score**: a population-fitted additive
effect of the lane's opponent heroes and lane-partner hero on the laning
checkpoint metrics, computed from hero identity, lane and position **only** —
nothing the player did in the match may enter it. Collapse it to three
user-facing states with **wide-Normal 20/60/20 thresholds, not terciles**. Apply
it to **Carry, Mid and Offlane in the Standard bucket only**; ship it as a
**delta on the player's existing personal rolling baseline**, never as a
separate set of personal baselines. It modifies **CS and Net Worth at the
locked checkpoint and nothing else**.

Two findings force that narrowing, and both contradict the brief's premises:

1. **Own hero identity is a bigger source of unfairness than lane difficulty,**
   and the current baseline contract does not control for it at all
   (§7.3 of the metrics SSOT keys baselines on bucket + role only). Against a
   real personal rolling baseline, hero adjustment cuts residual variance by
   10–22%; difficulty adjustment cuts it by 4–8% (§8). If you only ship one,
   ship hero.
2. **"Difficulty" is not one number.** The brief's own example is wrong in the
   data: **Underlord is one of the *easiest* safelane opponents for a Carry's
   CS (+2.1 CS @10)**, and Pudge is a perfectly good safelane partner
   (+110 net worth, +157 XP @10). Effects on CS and Net Worth correlate +0.84;
   CS and XP only +0.49 for side lanes; CS and deaths −0.59. One scalar applied
   to every metric would be wrong (§7).

---

## 2. Is the Mental Model Sound?

**"Easy / Normal / Difficult → adjusted metric expectations" is sound in
principle and wrong in three specifics.**

What is right:

- The lane you were drafted into really does move your laning output, by an
  amount users would notice. At 20/60/20 thresholds the gap between a Difficult
  and an Easy Carry lane is **+9.8 CS and +445 net worth at 10:00** (§5). That
  is roughly the size of the injustice the brief describes.
- The signal is genuinely **exogenous**: it is computed from hero identity
  before the horn, so it cannot be caused by the player's mistakes.
- Three states is enough. Collapsing the continuous score to three buckets
  loses information, but the lost information is smaller than the metric's own
  noise, so the user-facing loss is not what matters — threshold *stability* is
  (§5.4).

What is wrong:

- **Terciles are wrong.** Labelling a third of lanes "Difficult" produces a
  weaker claim *and* an unstable one: two models trained on independent halves
  of the same data disagree on the tercile label for 33% of Carry lanes, and
  flip a lane between Easy and Difficult 1.7% of the time. At 20/60/20 the
  extreme flip rate is **0.07%** and the claim is 24% stronger (§5.4).
- **One difficulty per match is wrong.** It must be per-metric (§7).
- **"Difficult lane → lower expectation for everything" is wrong.** Applying
  the difficulty offset to deaths is the exact circularity the brief warns
  about, wearing a legitimate-looking hat (§6).

And one thing the brief overestimates: even after adjustment, the residual sd
of Carry CS@10 against a personal baseline is ~10.2 CS on a mean of 44. **Draft
explains a real but minority share of laning variance.** The label must be
positioned as context, never as an explanation.

---

## 3. What STRATZ Can Actually Provide

CONFIRMED = observed populated in real cached payloads with the stated coverage.
Coverage figures are from the 98,263-match merged corpus unless noted.

### 3.1 Signals the V1 model needs

| Signal | STRATZ field | Confirmed? | Reliability | Cost | V1? |
|---|---|---|---|---|---|
| Hero identity, all ten | `match.players[].heroId` | **CONFIRMED** | 100% | in every batch | **YES** |
| Lane assignment | `match.players[].lane` (`MatchLaneType`) | **CONFIRMED** | non-null in 98.7% of matches; `JUNGLE`/`ROAMING`/`UNKNOWN` only 0.61% of players | free with players | **YES** |
| Position 1–5 | `match.players[].position` | **CONFIRMED** | non-null in 97.3% of matches; when present, exactly one of each position per team | free | **YES** |
| Faction | `match.players[].isRadiant` | **CONFIRMED** | 100% | free | **YES** |
| Patch | `match.gameVersionId` | **CONFIRMED** | 100% | free | **YES** |
| Bucket | `match.gameMode` / `lobbyType` | **CONFIRMED** | 100% | free | **YES** |
| CS@10 | `stats.lastHitsPerMinute` — **per-minute delta**, `sum(lh[0:10])` | **CONFIRMED** (re-verified: `sum(series)` = `numLastHits` ±1) | 97% of ≥11-min matches | ten-player batch | **YES** (target) |
| NW@10 | `stats.networthPerMinute` — **cumulative**, `nw[10]`; length = duration_min + 1 | **CONFIRMED** | 97% | ten-player batch | **YES** (target) |
| Abandon gate | `players[].leaverStatus` | CONFIRMED (`NONE`, `DISCONNECTED` seen; enum unmapped) | 3.1% of rows excluded | free | **YES** (exclusion only) |

Lane pairing is reconstructed deterministically: `SAFE_LANE` is bottom for
Radiant and top for Dire, `OFF_LANE` the mirror, `MID_LANE` is mid. Opponents
are the enemy players in the same *physical* lane. **97.7% of Standard core
matches resolve to a clean 2v2 or 1v1 shape**; end-to-end eligibility including
null lane/position is ~94%.

### 3.2 Signals evaluated and rejected

| Signal | STRATZ field | Confirmed? | Verdict |
|---|---|---|---|
| Realised lane outcome | `match.{top,mid,bottom}LaneOutcome` | **CONFIRMED** populated (94%); values `TIE`/`*_VICTORY`/`*_STOMP` | **FORBIDDEN as difficulty input** — it is the realised result, i.e. exactly the circularity in §6. Keep as a QA label only. |
| Per-lane creep kills | `match.laneReport` | **CONFIRMED but BROKEN** | Buckets are 30 s. `dire` has `2 × duration_min` entries; **`radiant` is always exactly 18 entries** regardless of a 16- or 64-minute match. Asymmetric and undocumented. Do not use. (Supersedes the earlier "shape unresolved" note.) |
| Continuous player position | `stats.locationReport` | **CONFIRMED and UNUSABLE** | Returns `{positionX, positionY}` with **no `time` field**, and a **duration-independent fixed length** (66–68 for both a 16-min and a 56-min match). Cannot be aligned to a minute. This alone kills Model 4. |
| Playback positions | `playbackData.playerUpdatePositions` | CONFIRMED unreliable | ≤90-day window, availability flips day-to-day (0% on 2026-09-15, ~31% on 2026-09-16). Not viable for a deterministic contract. |
| Rank / bracket | `averageRank`, `rank`, `bracket` | n/a | **Graded F by existing policy** (feasibility SSOT §2.2); rank fence enforced in code. Model must not condition on bracket. |
| Party | `players[].partyId` | CONFIRMED partial | 8% coverage, null ≠ solo. Unusable. |
| STRATZ's own scores | `imp`, `award`, `behavior`, `intentionalFeeding` | n/a | **Graded F** — opaque, unversionable model outputs. |
| Population hero baselines | `MatchPlayerType.heroAverage` → `HeroPositionTimeDetailType {cs, networth, xp, deaths, level, …}` keyed by hero + position + `bracketBasicIds` + week | **UNVERIFIED — schema only, never fetched** | Potentially a free, STRATZ-maintained substitute for our own hero effect. **Must be probed** (§15). Even if it works it gives no opponent effect. |
| Hero-vs-hero aggregates | `DotaQuery.heroStats` (`HeroStatsQuery`) | **UNVERIFIED — never introspected** | Would only supply win rates, which are contaminated and are not a CS expectation. Low priority. |

### 3.3 Useful confirmations for other metrics

- `stats.level` is a list of **timestamps in seconds** at which each level was
  reached (first value can be negative = pre-horn). `level[5]` is level-6 time —
  this directly satisfies `mid.level_6_time.v1`.
- `deathEvents[]` carries `time`, `positionX/Y`, `timeDead`, `goldFed`, `xpFed`.
- `experiencePerMinute` is a per-minute XP delta (so XP@10 = `sum(xp[0:10])`).

---

## 4. Recommended Definition of Laning Stage

**Do not invent one. Reuse the checkpoints already locked.**

- Standard bucket: **10:00**. Turbo: **8:00**. This is already the `late`
  convention in `OWN_LANE_VS_USUAL` and the checkpoint in
  `carry.last_hits_at_10.v1` / `carry.net_worth_at_20.v1`'s family.
- **Lane difficulty has no window of its own.** It is a draft-time property.
  The only thing the checkpoint controls is *which target the population
  effects were fitted against* — so fit one effect table per metric, at that
  metric's own checkpoint.

Evidence that a dynamic lane-end detector is not worth building: the draft
signal is strongest early and decays monotonically, which is what you would
expect if lanes dissolve into open play. Carry, environment-only CV R²:

| Checkpoint | CS | Net worth |
|---|---|---|
| 8:00 | +0.069 | +0.062 |
| 10:00 | +0.061 | +0.059 |
| 12:00 | +0.050 | +0.046 |

A fixed checkpoint is fine. If a future metric wants maximum draft signal,
8:00 is the better checkpoint — but that is a metric-registry decision, not a
difficulty decision.

---

## 5. Recommended Definition of Lane Difficulty

### 5.1 Inputs (the complete allowed set)

```
own_hero_id, own_position, own_lane, own_is_radiant
lane_ally_hero_ids[]        (same team, same physical lane)
lane_opponent_hero_ids[]    (other team, same physical lane)
progression_bucket          (STANDARD only in V1)
model_version, parameter_set_version
```

Nothing else. No timeline, no events, no outcome, no rank, no teammate
behaviour, no realised anything.

### 5.2 Offline parameter fitting (population pipeline)

For each `(progression_bucket, position_group, metric, checkpoint)` cell —
V1 cells are `STANDARD × {P1, P2, P3} × {CS, NW} × {10:00}` — fit a shrunken
additive model by backfitting, 6 passes:

```
y ≈ grand_mean
    + own[own_hero]
    + Σ opp[h]   for h in lane_opponent_hero_ids
    + Σ ally[h]  for h in lane_ally_hero_ids

effect[g] = Σ residual_g / (n_g + k),    k = 40
```

`k = 40` is empirical-Bayes shrinkage toward zero: a hero seen 5 times gets
~11% of its raw effect, a hero seen 400 times gets ~91%. A hero never seen gets
exactly 0 and therefore contributes NORMAL. Shrinkage sensitivity is mild
(§5.4 table is materially unchanged at k = 25, 60 or 150), so `k` is not a
knob anyone needs to tune.

Fitting inputs are restricted to: bucket-eligible, `duration ≥ 660 s`, tracked
player not a leaver, non-null `lane` and `position`, lane shape ∈ {2v2, 1v1}.

### 5.3 Runtime score (deterministic, no model at request time)

```
env_offset(match, metric) = Σ opp[h] + Σ ally[h]      # lookup + addition only
difficulty_score          = env_offset(match, NW@10)  # the primary score
```

The **primary score is fitted on net worth**, not CS: net worth is the metric
the existing lane cards already use, the effect is the most consistent across
roles, and the CS↔NW effect correlation of +0.84–0.94 means the NW-fitted score
also ranks CS lanes correctly.

### 5.4 Bucketing — use 20/60/20, not terciles

Thresholds are the 20th and 80th percentiles of `difficulty_score` over the
fitting corpus for that cell, frozen into the parameter set as **absolute
numbers**. (For Mid, quantile cuts placed at runtime jitter badly because a
1v1 score takes only ~127 distinct values; absolute frozen thresholds are
mandatory there.)

```
difficulty_score <= lo   → DIFFICULT
difficulty_score >= hi   → FAVOURABLE
otherwise                → TYPICAL
```

Half-sample replication, ~16–17k rows per cell (merged corpus, CS@10 target,
k = 40). "agree" = two independently fitted models assign the same label;
"flip" = one says DIFFICULT, the other FAVOURABLE.

| Cell | band | agree | extreme flip | CS@10 gap D→E | NW@10 gap | winrate D / E |
|---|---|---|---|---|---|---|
| Carry Std | 33/33/33 | 66.7% | 1.71% | +7.9 | +366 | .497 / .519 |
| Carry Std | 25/50/25 | 69.7% | 0.25% | +9.0 | +417 | .493 / .527 |
| **Carry Std** | **20/60/20** | **72.7%** | **0.07%** | **+9.8** | **+445** | .496 / .522 |
| Carry Std | 15/70/15 | 78.1% | 0.00% | +10.8 | +495 | .502 / .527 |
| **Mid Std** | **20/60/20** | **88.8%** | **0.00%** | **+9.5** | **+472** | .507 / .517 |
| **Offlane Std** | **20/60/20** | **72.7%** | **0.03%** | **+8.8** | **+464** | .508 / .506 |
| Support Std | 20/60/20 | 62.0% | 1.16% | +3.0 | +142 | .506 / .498 |
| Carry Turbo | 20/60/20 | 59.8% | 1.19% | +9.4 | +862 | .497 / .517 |

Score reliability (half-sample correlation, Spearman-Brown corrected to the
full corpus): Mid +0.93 → **+0.96**, Carry +0.83 → **+0.90**, Offlane +0.82 →
**+0.90**, Support +0.67 → +0.80, **Carry Turbo +0.57 → +0.73**.

The winrate column is the single most important row of evidence for trust:
**difficulty does not predict winning** (.49–.53 everywhere). A user cannot
read "Difficult lane" as "we were doomed", and the app is not quietly
re-deriving match outcome.

### 5.5 Fallback behaviour

| Condition | Behaviour |
|---|---|
| `lane` or `position` null for the viewer or any lane participant | `difficulty = UNAVAILABLE`; no label, no baseline adjustment |
| Lane shape not 2v2 or 1v1 | `difficulty = UNAVAILABLE` (2.3% of Standard core matches) |
| Viewer lane is `JUNGLE`, `ROAMING`, `UNKNOWN` | `UNAVAILABLE` |
| Effective role is Support | Feature not applicable in V1 |
| Bucket is Turbo | Feature not applicable in V1 |
| A hero has no fitted effect (new hero, rare pick) | Its effect is 0; the rest of the lane still scores. Shrinkage makes this self-correcting. |
| Personal baseline not yet ready (< 5 priors) | Label may still render; **no baseline adjustment** (there is nothing to adjust) |

`UNAVAILABLE` is never rendered as "Typical". Absence of a label is the
correct output; the metric shows unadjusted, exactly as today.

---

## 6. Avoiding Circularity — mandatory rules

The failure mode is: classify the lane as Difficult *using evidence the player
produced*, then use that classification to excuse the same evidence.

**FORBIDDEN as difficulty inputs. This list is normative.**

| Forbidden | Why |
|---|---|
| Any value of the metric being adjusted, at any timestamp | Direct circularity |
| Any other trajectory of the viewer or any other player (`lastHitsPerMinute`, `networthPerMinute`, `experiencePerMinute`, `deniesPerMinute`, `campStack`, …) | Contaminated by the viewer's own play |
| `killEvents`, `deathEvents`, `assistEvents`, `runes`, `wards`, `itemPurchases`, `itemUsed` | Realised behaviour |
| `{top,mid,bottom}LaneOutcome` | It *is* the realised lane result |
| `laneReport`, `towerDeaths`, `radiantNetworthLeads`, `radiantExperienceLeads`, `firstBloodTime`, `analysisOutcome` | Realised match state |
| Match outcome, `didRadiantWin`, `isVictory` | Outcome leakage |
| `imp`, `award`, `behavior`, `intentionalFeeding`, `streakPrediction` | Provider model outputs, already F-graded |
| Rank, bracket, MMR, party | Policy fence; also a skill proxy |
| Whether a lane partner later left, roamed, or underperformed | Cannot be measured deterministically (§3.2), and is partly caused by the viewer |

**ALLOWED:** hero ids of the lane participants, lane, position, faction,
bucket, patch, and the frozen parameter set. That is the entire list.

**Structural argument.** Every allowed input is fixed before the first creep
wave. No sequence of player actions can change any of them. The score is
therefore exogenous *by construction*, not by statistical argument — which is
the only kind of non-circularity worth trusting.

**Empirical confirmation (§11).** The score correlates +0.24 with the viewer's
own CS@10, but only **+0.04** with the allied mid-laner's CS and **+0.05** with
the enemy mid-laner's CS in the same match, and **−0.004** with the viewer's CS
when the score is built from the *wrong* lane's heroes. It is lane-local and is
not a disguised skill or bracket measure.

**One acknowledged residual.** Drafts are chosen, not assigned. A player who
habitually first-picks a greedy carry into open drafts will see more Difficult
lanes. V1 does not correct for this, and the `NORMAL`-heavy 60% band limits how
often it matters. Flagged in §15.

---

## 7. Difficulty × Metric Matrix

The brief's instinct — "do not force one modifier across every metric" — is
correct, and the data is unambiguous. Standardised opponent effects (as % of
that metric's sd), Carry safelane:

| Opponent | CS@10 | NW@10 | XP@10 | Deaths<10 |
|---|---|---|---|---|
| **Underlord** | **+17.1%** | +9.1% | +0.7% | −16.9% |
| Wraith King | +19.6% | **−0.1%** | −4.6% | −4.8% |
| Enigma | +34.6% | +11.6% | +23.9% | −3.7% |
| Tidehunter | +17.9% | +29.4% | +18.9% | −19.3% |
| Viper | −40.1% | −33.2% | −9.0% | +26.2% |
| Warlock | −24.5% | −31.7% | −6.8% | **−1.1%** |
| Skywrath Mage | −24.6% | −34.5% | −16.2% | +23.2% |

Cross-metric correlation of the fitted effects (Carry / Mid):
CS↔NW **+0.84 / +0.94**, CS↔XP **+0.49 / +0.93**, CS↔deaths **−0.59 / −0.52**.

Transfer test — reusing one CS-fitted score with a per-metric linear rescale,
out-of-fold R² against a natively-fitted model (Carry):
CS 0.182 vs 0.183 (no loss) · NW 0.098 vs 0.114 (−14%) · XP 0.071 vs 0.093
(−24%) · **deaths 0.058 vs 0.086 (−33%)**.

| Metric | Adjust baseline? | Reason | Method |
|---|---|---|---|
| `carry.last_hits_at_10.v1` (CS@10) | **YES** | Largest, cleanest draft effect; ±5 CS at the bucket edges | Additive `env_offset` fitted on CS@10 |
| `carry.net_worth_at_20.v1` | **NO at 20:00** — **YES if a NW@10 metric is added** | The draft effect has decayed by minute 12 and NW@20 is dominated by mid-game play | Do not adjust NW@20. Adjust NW@10 where it exists (`mid.net_worth_at_20.v1` likewise unadjusted) |
| `mid.lane_net_worth_advantage_at_10.v1` | **YES** | It is a lane metric at the right checkpoint | `env_offset` fitted on the *gap*, not on own NW |
| `offlane.net_worth_at_10.v1` | **YES** | Same as Carry | `env_offset` fitted on NW@10 |
| `offlane.lane_net_worth_advantage_at_10.v1` | **YES** | Lane metric at the right checkpoint | as Mid |
| `mid.level_6_time.v1` | **NOT V1** | XP effects diverge from CS (+0.49 correlation for side lanes) and level-6 time is a timing, not a rate; needs its own fit | Later, with its own effect table |
| `carry.cs_10_to_20.v1` | **NO** | Draft effect has decayed; this is a farming-pattern metric, not a lane metric | Informational label only |
| `carry.dead_time.v1`, deaths generally | **NO — explicitly forbidden** | Death is the metric most confounded with player error. Difficult lanes really do carry +0.44 deaths at the bucket edges, but adjusting it means the app tells a player their deaths were fine *because of the draft*, which is exactly the trust-destroying outcome §"Important Product Principle" warns against | May display the difficulty label beside it; must not move the baseline |
| `*.hero_damage_share.v1`, `*.tower_damage_share.v1`, `offlane.objective_involvement.v1`, `*.fight_presence.v1` | **NO** | Whole-match, team-relative, not laning metrics | Not applicable |
| All Support metrics | **NO in V1** | Effect too small and score too unreliable (§9) | Not applicable |

---

## 8. Personal Baseline Architecture

**Recommendation: Approach B — one personal baseline per role, plus a
population difficulty *delta*. Reject Approach A outright.**

Approach A (separate Easy/Normal/Difficult personal baselines) fails on
arithmetic before it fails on statistics. The metrics SSOT already requires 5
priors and a 20-match window per `bucket + role + metric + version`; splitting
into three difficulty cohorts triples the requirement, and the insights SSOT
already records that a hero key only reaches N ≥ 20 in 11.5% of evaluations.
It would also require a full rebuild whenever the parameter set changes.

### 8.1 The adjustment must be *relative to the baseline window*

This is the part that is easy to get wrong. The player's rolling baseline
already contains the average difficulty of the lanes they usually get. Adding
the raw offset would double-count it. The correct form:

```
delta_env         = env_offset(current_match) - median(env_offset(b) for b in baseline_window)
adjusted_baseline = baseline_median + delta_env
direction_delta   = current_value - adjusted_baseline      (sign per metric direction)
```

`env_offset` is stored once per observation, so the median over the window is a
cheap deterministic lookup. A player who always gets hard lanes has a baseline
that already reflects it, and `delta_env ≈ 0` — which is correct: their
*unusual* lanes are what should move the expectation.

### 8.2 Does it actually work?

Tested against the real contract — per-account chronological order, median of
the ≤20 prior same-role observations, ≥5 priors required. Residual variance
reduction vs. the unadjusted personal baseline:

| Cohort | Metric | obs | difficulty | hero | both |
|---|---|---|---|---|---|
| Carry Std | CS@10 | 6,819 | **+6.7%** | +10.0% | +16.5% |
| Mid Std | CS@10 | 7,589 | **+7.7%** | +16.5% | +24.0% |
| Offlane Std | CS@10 | 5,459 | **+7.2%** | +7.2% | +14.4% |
| Support Std | CS@10 | 10,430 | +3.9% | +12.8% | +16.6% |
| Carry Turbo | CS@10 | 9,962 | **+1.7%** | +21.6% | +23.4% |
| Carry Std | NW@10 | 6,819 | **+6.9%** | +5.6% | +12.4% |
| Mid Std | NW@10 | 7,589 | **+6.3%** | +6.6% | +12.8% |
| Offlane Std | NW@10 | 5,459 | **+6.8%** | +5.1% | +11.9% |
| Carry Turbo | NW@10 | 9,962 | +4.2% | +5.2% | +9.3% |

Read honestly: Carry CS@10 MAE improves 8.75 → 8.46 with difficulty, 8.75 →
8.07 with hero + difficulty. **A real fairness gain, not a large accuracy
gain.** And the same pipeline that produces `opp[]` and `ally[]` produces
`own[]` for free, so the hero correction costs nothing extra to ship. Ship
both; label only difficulty.

---

## 9. Role Handling

| Role | Lane shape | Score reliability | Effect size | V1 verdict |
|---|---|---|---|---|
| **Mid** | 1v1, 98.7% of the time | **+0.96** | +9.5 CS / +472 NW | **YES — best case.** Only ~127 distinct opponents, so the space is genuinely small; absolute frozen thresholds required (score is lumpy) |
| **Carry** | 2v2, 95.0% | **+0.90** | +9.8 CS / +445 NW | **YES** |
| **Offlane** | 2v2, 95.0% | **+0.90** | +8.8 CS / +464 NW | **YES** |
| **Support** | 2v2, 94.6–95.4% | +0.80 | +3.0 CS / +142 NW | **NO.** Environment adds only +1.4pp (P4) / +2.7pp (P5) CV R² beyond own hero, vs +5.4pp for Carry; the personal-baseline gain is 3.9%. Consistent with the insights SSOT already restricting lane cards to cores |
| **Turbo, any role** | — | **+0.73** (Carry) | — | **NO.** Personal-baseline gain is 1.7%; Standard-fitted effects transfer to Turbo at only +0.52 correlation, so Turbo would need its own parameter set to buy almost nothing. Hero adjustment, by contrast, is worth 21.6% in Turbo — ship that instead |

Do not force symmetry. The correct V1 surface is **Carry / Mid / Offlane,
Standard only** — about 23% of a typical user's tracked matches in this corpus.

---

## 10. Sample Fragmentation Analysis

Theoretical space, 127 heroes: a Carry lane is (own) × (ally) × (unordered
opponent pair) = 127 × 126 × C(126,2) ≈ **125 million** combinations, before
patch, bucket and side. Mid is 127 × 126 ≈ **16,002** — three orders of
magnitude smaller, which is why Mid is the strongest cell in every table.

Observed, 10,450 Carry Standard 2v2 lanes:

| | Carry | Mid |
|---|---|---|
| Distinct (own, ally, opponents) | **10,387** | 3,370 |
| Singletons | **99.4%** | 50.8% |
| Max observations for one combination | **2** | 53 |
| Distinct opponent sets | 3,069 | 125 |
| Median observations per opponent set | **2** | 25 |
| Opponent sets with ≥ 30 observations | **13** | 57 |

**Exact-combination lookup is impossible for side lanes and is unnecessary
everywhere.** Adding an exact opponent-set interaction term on top of the
additive model made out-of-sample accuracy *worse or equal in all 28 cells
tested* — Carry CS@10 0.2015 with the interaction vs **0.2048** without; Mid
0.2839 vs 0.2828 (noise). The interaction overfits and buys nothing.

**Fallback hierarchy (there is only one level, which is the point):**

1. Sum the shrunken per-hero effects for every hero present.
2. A hero with no fitted effect contributes 0.
3. If the lane shape or lane assignment is unusable, emit `UNAVAILABLE`.

Coverage at current scale: at ~17k rows per cell, 86 of 127 heroes have ≥100
opponent observations for Carry, covering **94.8%** of opponent slots (Offlane
95.3%, Mid 86.4%). Shrinkage handles the tail without a special case.

Product-friendly statement: *we never ask "how does this exact five-hero
situation usually go"; we ask "how much does each of these heroes usually move
a lane", and add them up. The second question has thousands of examples per
hero; the first has two.*

---

## 11. Validation Results

### 11.1 Face validity

Fitted CS@10 opponent effects (Carry safelane, n = 16,692, heroes with ≥150
observations):

Hardest — Viper −4.95, Sniper −4.24, Witch Doctor −3.72, Skywrath Mage −3.04,
Silencer −3.02, Warlock −3.02, Razor −2.92, Jakiro −2.88.
Easiest — Enigma +4.27, Dark Seer +3.31, Alchemist +3.27, Earth Spirit +3.16,
Sand King +3.08, Wraith King +2.41, Tidehunter +2.21, Magnus +2.14.

Mid, hardest — **Huskar −11.88**, Outworld Destroyer −6.33, Viper −5.29,
Necrophos −4.55, Sniper −3.98, Shadow Fiend −3.55. Easiest — Keeper of the
Light +7.19, Broodmother +6.88, Tinker +2.38, Storm Spirit +2.19.

Lane partners (Carry) — best: Undying +4.07, Winter Wyvern +3.52, Silencer
+2.52, Warlock +2.50, Dazzle +2.47. Worst: Spirit Breaker −1.75, Invoker
−1.67, Techies −1.49, Shadow Shaman −1.16.

Every one of these is what a Dota player would say, unprompted — ranged harass
offlanes are hard, melee farming offlanes are easy, Huskar mid ruins your
creep equilibrium, "supports" who are actually cores make bad lane partners.
The model was not told any of this.

### 11.2 Falsification tests (this is the section that matters)

| Test | Expected if real | Carry Std | Turbo |
|---|---|---|---|
| A. score vs **own** CS@10 | clearly positive | **+0.238** | +0.121 |
| B. score vs **allied mid-laner's** CS@10 | ~0 if not a bracket proxy | **+0.043** | +0.027 |
| B2. score vs **enemy mid-laner's** CS@10 | ~0 | **+0.053** | +0.023 |
| D. **placebo**: score built from the *other* side lane's heroes, vs own CS@10 | ~0 | **−0.004** | +0.023 |

The signal is lane-local. It is not a skill, bracket or lobby-quality proxy.

One result that did *not* come out as predicted: the score's correlation with
the **direct lane opponent's** CS@10 is −0.019, not clearly negative. Lane CS
is not zero-sum — both sides of a passive lane can farm well — so a lane that
is "easy for me" is not automatically "hard for them". Do not build any
symmetry assumption into the model or the copy.

### 11.3 Worked examples — Phantom Assassin safelane

878 PA safelane Standard matches in the corpus. PA's own hero effect is
**−4.94 CS@10** (she is a poor early farmer relative to the carry pool — which
is exactly the unfairness the current hero-blind baseline creates).
Thresholds: DIFFICULT ≤ −2.35, FAVOURABLE ≥ +2.32.

| Match | Label | env | Lane | Expected CS@10 | Actual | Δ | deaths<10 |
|---|---|---|---|---|---|---|---|
| 8808139420 | DIFFICULT | −10.48 | PA + Slark vs **Viper / Ogre Magi** | 28.3 | 29 | +0.7 | 5 |
| 8657133292 | DIFFICULT | −8.58 | PA + Chen vs **Huskar / Bristleback** | 30.2 | 41 | +10.8 | 2 |
| 8845459138 | DIFFICULT | −8.13 | PA + Ringmaster vs **Huskar / AA** | 30.7 | 50 | **+19.3** | 1 |
| 8504043544 | TYPICAL | −2.35 | PA + Invoker vs Axe / Tiny | 36.5 | 33 | −3.5 | 5 |
| 8664217799 | TYPICAL | −2.32 | PA + Witch Doctor vs Slardar / Sniper | 36.5 | 43 | +6.5 | 1 |
| 8555825936 | FAVOURABLE | +2.35 | PA + Clockwerk vs Rubick / Legion | 41.2 | 48 | +6.8 | 2 |
| 8881841792 | FAVOURABLE | +2.36 | PA + Rubick vs Leshrac / Dawnbreaker | 41.2 | 31 | **−10.2** | 2 |

Sensible: "PA + Slark vs Viper/Ogre" is a genuinely brutal lane and the model
says so; the player hit 29 CS, which reads as par, not as failure. "PA + Chen"
is flagged Difficult partly because Chen is a jungler, not a lane partner —
also correct.

**Deliberate failure cases:**

- *Match 8845459138* — model says 30.7, player got 50. A +19 CS miss. The
  model has no way to know the enemy Huskar fed, rotated, or simply lost. This
  is the honest ceiling of a draft-only model, and it is why the label must
  never be phrased as a prediction.
- *Match 8881841792* — "Favourable" lane, 31 CS. If the app pairs
  `FAVOURABLE` with `BELOW` here, the copy has to be careful: the lane was
  favourable on paper and the player still farmed badly, which is a fair
  observation, but it is one sentence away from sounding accusatory.
- *Match 8504043544* — 5 deaths before 10:00 in a Typical lane. The model
  correctly refuses to call this lane hard. Good: this is the §6 scenario the
  whole design exists to prevent.
- **Structural failure: PA + Invoker / PA + Chen.** STRATZ assigns a lane to
  every player, so a jungling Chen or a roaming Invoker is recorded as a
  "safelane partner" and drags the score toward Difficult. This is arguably
  correct (a partner who is not there *is* a harder lane) but it is realised
  behaviour smuggled in through the lane label, and it is the one place where
  the exogeneity argument in §6 is not airtight. Quantify before shipping.

---

## 12. Deterministic Output Model

Orthogonal states only:

| Dimension | States | Source |
|---|---|---|
| Difficulty | `DIFFICULT`, `TYPICAL`, `FAVOURABLE`, `UNAVAILABLE` | §5.4 |
| Performance vs adjusted baseline | `ABOVE`, `IN_LINE`, `BELOW`, `NOT_READY` | existing comparison engine |
| Metric | CS@10, NW@10 (+ the two lane-gap metrics) | metric registry |

**Copy is generated from difficulty × performance only — 3 × 3 = 9 patterns**,
plus 2 degenerate rows (`UNAVAILABLE` → render today's unadjusted copy;
`NOT_READY` → `BASELINE_BUILDING`, label may still show). The metric name is a
**slot**, not a new string, so adding a metric adds zero copy.

| | ABOVE | IN_LINE | BELOW |
|---|---|---|---|
| **DIFFICULT** | "Strong {metric} for a difficult lane" | "Held your usual {metric} in a difficult lane" | "{metric} below your usual — the lane was a difficult one" |
| **TYPICAL** | "Above your usual {metric}" | "In line with your usual {metric}" | "Below your usual {metric}" |
| **FAVOURABLE** | "Above your usual {metric} in a favourable lane" | "Your usual {metric} in a favourable lane" | "Below your usual {metric} despite a favourable lane" |

**Total user-facing strings: 9 + 2.** No trend dimension is introduced here —
trend already has its own contract in Progress & History V1 and composing it
in would multiply the space by 3 for no evidenced benefit.

**Wording.** Use **Favourable / Typical / Difficult**, not Easy / Normal /
Difficult. "Easy" is an accusation when paired with `BELOW`, and it overclaims:
the label describes the *draft*, not how the lane went. "Favourable" is
ordinary Dota vocabulary and carries the on-paper meaning correctly.

---

## 13. Engineering / API Cost

| Item | Cost |
|---|---|
| Runtime computation | 2–4 dictionary lookups plus an addition. Microseconds. No model at request time |
| Runtime API cost | **Zero additional calls.** `heroId`, `lane`, `position`, `isRadiant` are already in the ten-player batch |
| Parameter set size | 3 roles × 2 metrics × 3 tables × ~127 heroes ≈ **2,300 floats**, plus 6 thresholds. Well under 100 KB of JSON; ship it in the app bundle or a single cached endpoint |
| Per-observation storage | one float (`env_offset`) per metric per observation, plus a `parameter_set_version` string |
| Offline fitting corpus | ~10–15k Standard matches per refresh gives ≥17k rows per role cell. At the validated **16 matches per lean request**, that is **≈650–950 STRATZ requests** |
| Fitting compute | Backfitting over 17k rows × 6 passes × 4 targets ran in **~5 seconds** of single-threaded Python. Not a pipeline problem |
| Refresh cadence | Quarterly, or on a major patch. Opponent effects correlate **+0.74** between patch 180/181 and 182 for heroes with ≥60 observations — stable enough that per-patch retraining is unnecessary |
| Backfill / recalculation | `env_offset` is a pure function of (hero ids, lane, position, bucket, parameter_set_version). Recomputing history is a local re-read of stored match rows — **no STRATZ calls** |
| Incremental new matches | Fully incremental |
| Determinism | Same payload + same `model_version` + same `parameter_set_version` ⇒ same label and same adjusted baseline, always |

Follow the existing patch rule: **do not** add same-patch gating to lane
comparisons (the insights SSOT already establishes lane metrics do not drift
materially between patches; only item timings do).

---

## 14. V1 vs Later

**V1 REQUIRED**

1. Offline additive effect tables for `STANDARD × {P1, P2, P3} × {CS@10, NW@10}`, shrinkage k = 40, frozen absolute 20/60/20 thresholds.
2. `env_offset` and `difficulty` stored per observation with `parameter_set_version`.
3. Baseline adjustment as a **window-relative delta** (§8.1) for CS@10, NW@10 and the two lane-gap metrics.
4. **Own-hero correction shipped in the same release** — same pipeline, larger effect (§8.2). Not labelled; it just makes the baseline fair.
5. The forbidden-input list (§6) encoded as a test, not a comment.
6. `UNAVAILABLE` fallback and the 9 + 2 copy patterns.
7. Never adjust deaths or dead time.

**V1 OPTIONAL**

- Showing the label on the Match Detail lane card even when the baseline is not ready.
- Difficulty as a secondary fact on `OWN_LANE_VS_USUAL` / `OPP_START_VS_HISTORY` (both are already cores-only).
- Storing XP@10 and deaths effect tables without using them, to keep the option open cheaply.

**LATER / NOT WORTH IT YET**

- Turbo (gain 1.7%; needs its own parameter set).
- Support (gain 3.9%, reliability 0.80).
- XP / level-6 difficulty (needs its own fit; CS↔XP effect correlation only +0.49 for side lanes).
- Bracket-conditioned effects (blocked by the rank fence anyway).

**NOT WORTH IT — with evidence**

- **Exact lane-combination lookup.** 99.4% singletons; interaction terms made every cell worse or equal (§10).
- **Model 4 (realised external lane context).** `locationReport` has no timestamps and a duration-independent length; `laneReport.radiant` is truncated to 18 half-minute buckets; playback availability flips day to day. Not measurable deterministically — and even if it were, it would reintroduce the attribution problem the design exists to avoid.
- **Any ML model.** The additive model with shrinkage is already at the interaction ceiling.

---

## 15. Risks / Things We Cannot Reliably Know

1. **Unverified this session.** `heroAverage`, `heroStats`, and bracket fields were never fetched. The `heroAverage` probe is genuinely worth running — it may hand us the own-hero correction for free, maintained by STRATZ, keyed by hero + position + bracket + week. Required probes: (a) does `MatchPlayerType.heroAverage` return populated rows, at what complexity cost, and what is `time` bucketed by; (b) introspect `HeroStatsQuery`; (c) re-confirm `lane`/`position` coverage on a fresh random sample.
2. **Corpus is not representative.** 278 parse-heavy public accounts plus probe accounts. Magnitudes must be re-estimated on production data; the *structure* of the finding (additive beats interaction, wide-Normal beats terciles, hero ≥ difficulty) is robust enough to design against.
3. **No bracket conditioning, by policy.** A Viper offlane is not equally oppressive at every skill level. The pooled effect is a population average and will be somewhat wrong at both tails.
4. **Draft is chosen, not assigned** (§6). Residual self-selection is not corrected in V1.
5. **The `lane` label absorbs some realised behaviour.** A jungling or roaming "lane partner" is still recorded in the lane. This is the weakest point in the exogeneity argument and needs quantifying (§11.3).
6. **Threshold stability is the real risk, not effect size.** At 20/60/20, two independently fitted models still disagree on ~27% of Carry labels — almost all of it Typical↔extreme boundary jitter, with extreme flips at 0.07%. Freeze thresholds in a versioned parameter set and change them only with a version bump and a documented rebuild.
7. **Most laning variance is unexplained.** Residual sd after hero + difficulty adjustment is ~10.2 CS on a mean of 44. The product must not imply the label explains the match.
8. **We cannot know whether a lane partner was actually useless.** The brief's motivating example is not measurable. Pudge as a safelane partner is +110 net worth and +157 XP at 10:00 in this data — the folk belief is not supported. If the app implies it can see partner quality, it will be caught being wrong.
9. **Enum drift.** `leaverStatus` is not fully mapped; `MatchLaneType` could gain values. Unknown enum ⇒ `UNAVAILABLE`, fail closed, consistent with the integrity policy.

---

## 16. Final V1 Contract (proposed SSOT seed)

**Definition.** *Lane Difficulty* is a deterministic, population-derived
estimate of how much the **drafted composition of the player's lane** typically
moves a laning-checkpoint metric, expressed in that metric's own units. It is a
property of the draft, not of the match that was played. It is not a
prediction, not a win probability, and not a judgement.

**When computed.** Once, at match processing, after `effective_role` is
resolved. Recomputed only on role correction or a `parameter_set_version` bump.

**Allowed inputs.** Hero ids of the viewer, their lane allies and their lane
opponents; `lane`; `position`; `isRadiant`; `progression_bucket`;
`model_version`; `parameter_set_version`. Nothing else.

**Forbidden inputs.** Every trajectory, event, outcome, lane-outcome enum,
provider score, rank/bracket/party field, and any post-horn state — the
normative list is §6.

**Categories.** Exactly three, plus one absence state:
`DIFFICULT`, `TYPICAL`, `FAVOURABLE`, `UNAVAILABLE`.
`UNAVAILABLE` is never rendered as `TYPICAL`.

**Applicability.** `progression_bucket = STANDARD` and
`effective_role ∈ {Carry, Mid, Offlane}` only. Support and Turbo receive no
label and no adjustment in V1.

**Metrics it modifies.** CS@10, NW@10, and the Mid/Offlane lane net-worth
advantage at 10:00. It modifies nothing else, and it **never** modifies deaths,
dead time, damage shares, objective metrics, or any whole-match metric.

**Baseline adjustment.**
`adjusted_baseline = baseline_median + (env_offset(current) − median(env_offset over the baseline window))`.
The personal baseline keying is unchanged: `bucket + effective_role +
metric_id + metric_version`. **No difficulty-specific personal baselines are
created.**

**Confidence / minimum data.** The label requires a resolved 2v2 or 1v1 lane
shape with non-null `lane` and `position` for every participant. The baseline
adjustment additionally requires `BASELINE_READY` (≥5 priors). Heroes absent
from the parameter set contribute 0.

**Determinism and versioning.** `(match payload, model_version,
parameter_set_version)` ⇒ identical label, `env_offset` and adjusted baseline,
always. Thresholds are frozen absolute numbers inside the parameter set, never
runtime quantiles. A parameter-set change is a version bump and triggers the
same deterministic, idempotent rebuild path as a role correction. Both versions
are retained per observation for QA and error analysis.

**Product guard rails.** The label may contextualise a metric; it may never
appear as a reason, a cause or an excuse. Forbidden copy: "not your fault",
"you lost lane because", "unwinnable lane", "your support was bad", anything
implying the outcome, and any claim about a teammate's quality.

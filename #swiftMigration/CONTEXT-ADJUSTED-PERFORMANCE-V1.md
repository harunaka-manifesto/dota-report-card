# Context-Adjusted Performance V1 — Final Decision Document

Status: SSOT-READY PROPOSAL (promote on owner sign-off)
Date: 2026-09-20
Supersedes as the leading hypothesis: [Lane Difficulty Research V1](LANE-DIFFICULTY-RESEARCH-V1.md)
Reproduction code: [`lane-difficulty-research-code/pass2/`](lane-difficulty-research-code/pass2/)

Related contracts:
[Role Metrics & Personal Baselines V1](role-metrics-and-baselines-v1.md) ·
[Role Resolution & Correction V1](role-resolution-and-correction-v1.md) ·
[Progress & History V1](progress-and-history-v1.md) ·
[Post-Match Insights SSOT](POST-MATCH-INSIGHTS-SSOT.md) ·
[Post-Match Intelligence Feasibility V1](post-match-intelligence-feasibility-v1.md)

### Evidence classes used below

| Tag | Meaning |
|---|---|
| **[STRATZ-LIVE]** | Confirmed this session by a live STRATZ GraphQL call (635 + 12 calls, 0 failures) |
| **[PAYLOAD]** | Confirmed from cached STRATZ payloads in `.local/` |
| **[EMPIRICAL]** | Computed here from 94,888 tracked-player matches (v7 Pass-2 canonical, 278 accounts) and/or the 12,048-match ten-player probe cache |
| **[REPO]** | Read from an existing contract or module in this repository |
| **[INFERENCE]** | Reasoned, not directly measured — labelled at each use |

---

## 1. Executive Decision

# LOCK WITH CONDITIONS

The context-adjustment model survives. It also got **simpler and better sourced** than the V1 hypothesis: both population terms now come straight from STRATZ aggregate endpoints that we confirmed live this session, so **we do not have to build, fit or maintain a population corpus at all**.

```
context_adjusted_expectation
  = personal_rolling_baseline
  + (own_hero_population_level      − median over the baseline window)
  + (lane_opponent_population_effect − median over the baseline window)
```

- Own-hero term ← `heroStats.stats(heroIds, positionIds, groupByTime)` **[STRATZ-LIVE]**
- Lane term ← `heroStats.laneOutcome(heroId, isWith:false, positionIds)` **[STRATZ-LIVE]**
- **Lane partner (ally) term is dropped from V1** — it buys +0.54pp of CS variance and is the only teammate-attribution surface in the system.
- Scope: `STANDARD` × {Carry, Mid, Offlane} × the laning-checkpoint metrics.
- User-facing lane context: `DIFFICULT` / `TYPICAL` / `FAVOURABLE` / `UNAVAILABLE`, 20/60/20 bands, driven by **CS** (not NW — see §6).

**The three blocking conditions** (all mechanical, none statistical):

1. **`csCount` semantics are undocumented.** STRATZ does not state what window `laneOutcome.csCount` covers. We established empirically that it behaves like CS at ≈ minute 11 and that the derived effects correlate **+0.87 / +0.93 / +0.88** with our independently fitted CS@10 effects, and we absorb the scale with a frozen per-role slope. Before lock, file/confirm the definition with STRATZ or freeze the empirical slope with a regression test that fails if the relationship drifts.
2. **One week of `laneOutcome` does not cover enough heroes.** At one week, 95.0% / 90.1% / 94.7% of Carry / Mid / Offlane matches have every lane opponent in the table. Production must pool a rolling **4–8 week** window and re-verify coverage ≥ 97%; Mid is the binding constraint.
3. **Adjustment caps must ship with the model.** Uncapped, the hero term reaches 21 CS on a single match (p99 = 13.4). A ±8 CS cap costs ~0 accuracy for Carry/Offlane and 1.5pp for Mid, and removes an output no user would believe.

Nothing else is blocking. Everything below is settled.

---

## 2. What Changed Since Lane Difficulty Research V1

Only material changes are listed. Everything not listed here stands.

| # | V1 said | Now | Why |
|---|---|---|---|
| 1 | Build our own population corpus (~650 STRATZ requests, our own fitting pipeline) | **Use STRATZ `heroStats` aggregates.** No corpus, no fitting. | Fully STRATZ-sourced parameters beat our own corpus fit in the real pipeline: Carry **13.44%** vs 11.86%, Mid **22.51%** vs 20.67%, Offlane **10.13%** vs 9.79% residual-variance reduction **[EMPIRICAL]** |
| 2 | Primary lane score fitted on **net worth** | Primary score is **CS** | `laneOutcome` exposes only `csCount`. CS drives NW with **0.00–0.26%** visible contradiction (§6), so nothing is lost |
| 3 | Ally (lane-partner) term included | **Dropped from V1** | Worth only +0.54pp CS variance; carries the entire teammate-attribution risk **[EMPIRICAL]** |
| 4 | Exact-combination lookup impossible *because the data is sparse* | Impossible *even when the data is not sparse* | With 784,361 population lane observations and 1,669–2,392 populated pair cells, exact (viewer hero × opponent hero) pairs scored **+4.44%** vs pooled **+4.50%**. The interaction is genuinely ~zero, not merely unmeasurable **[EMPIRICAL]** |
| 5 | Lane-partner leakage was a qualitative warning | Quantified and largely dismissed | `lane` is ≥97% predictable from (hero, position) for P1–P3 and 97.6% for P4 (§3.2) |
| 6 | Hero adjustment "shipped alongside" difficulty | **Hero adjustment is the larger, broader change** and applies to metrics far outside laning (healing 47.7%, damage shares 19–22%) | Full 15-metric × 4-role × 2-bucket sweep (§3.1) |
| 7 | Turbo excluded on weak effect | Turbo excluded, **and** the STRATZ source does not cover it | STRATZ hero stats beat ours on every Standard cell and lose on every Turbo cell — evidence the endpoint is Standard-only **[EMPIRICAL/INFERENCE]** |

---

## 3. Remaining Validation Results

### 3.1 Blocker A — should own-hero adjustment become part of the global baseline model?

**Answer: yes, but selectively, and it is a bigger change than lane context.**

Method **[EMPIRICAL]**: the real locked contract — per account, chronological, median of the ≤20 prior same-role-and-bucket observations, ≥5 priors required. Population effects fitted account-out-of-fold so a player never contributes to the hero effect applied to their own match. `B` = + own-hero adjustment; `C` = `B` + lane environment. Figures are residual-variance reduction versus the unadjusted personal baseline.

STANDARD bucket, selected rows from the full 15-metric sweep:

| Metric | Carry B / C | Mid B / C | Offlane B / C | Support B / C |
|---|---|---|---|---|
| `last_hits_at_10` | 7.7 / **11.7** | 13.4 / **19.6** | 4.3 / **9.4** | 3.5 / 4.4 |
| `net_worth_at_10` | 2.8 / **6.2** | 4.1 / **8.8** | 2.9 / **6.7** | 3.4 / 5.2 |
| `level_6_time` | 2.1 / **5.8** | 2.8 / **7.4** | 1.7 / **5.1** | 1.3 / 3.8 |
| `deaths_before_10` | 3.6 / 6.8 | 6.3 / 8.5 | 1.6 / 4.4 | 2.1 / 5.1 |
| `net_worth_at_20` | **7.0** / 8.7 | 3.9 / 4.8 | 3.7 / 5.1 | 6.8 / 7.6 |
| `cs_10_to_20` | **21.2** / 20.2 | **20.3** / 20.5 | **11.6** / 10.7 | **16.4** / 15.9 |
| `healing_per10` | **51.9** / 51.5 | **41.3** / 41.0 | **37.5** / 36.5 | **47.7** / 47.4 |
| `hero_damage_share` | **7.4** / 8.5 | **5.5** / 5.5 | **8.4** / 9.3 | **21.9** / 21.7 |
| `tower_damage_share` | **7.3** / 7.0 | **15.7** / 15.3 | **10.6** / 10.0 | **19.4** / 19.2 |
| `fight_presence` | 6.6 / 6.3 | 4.9 / 4.6 | 1.8 / 1.1 | 4.7 / 4.4 |
| `camps_stacked_at_20` | **11.3** / 10.3 | 8.7 / 7.8 | 3.8 / 3.3 | −0.7 / −1.1 |
| `objective_involvement` | 1.0 / −0.1 | 0.5 / 0.0 | 0.4 / −0.6 | 0.2 / −0.5 |
| `observer_wards_per10` | −0.3 / −0.9 | −3.8 / −4.4 | −0.6 / −1.7 | 2.9 / 3.5 |
| `dewards_per10` | 2.4 / 1.5 | 2.6 / 2.2 | 1.5 / 1.2 | 2.1 / 2.3 |
| `deaths_total` | 3.8 / 4.4 | **35.9** / 35.8 | 1.5 / 1.8 | 2.4 / 2.6 |

Answers to the nine questions:

1. **Consistently?** No. Hero adjustment ranges from **+51.9%** (Carry healing) to **−3.8%** (Mid observer wards). It must be enabled per metric, never globally.
2. **Which metrics?** Those where hero identity is a first-order determinant of the *opportunity*: healing, damage shares, camps stacked, mid-game CS, `deaths_total` for Mid. Full matrix in §6.
3. **Beyond laning?** **Yes — and that is where its largest wins are.** Healing (37–52%), tower damage share (7–19%), hero damage share (6–22%) are whole-match metrics with no lane component at all.
4. **Where does it become overfitting?** A clean, testable rule emerged: **when the personal baseline median sits at or near the metric's floor, adjustment adds noise.** Observer wards for cores have a baseline median of 0; hero adjustment moves variance by ≈0 but moves **MAE by −19.7% to −33.7%** — strictly worse output. Same for `camps_stacked` (−1.8 to −10.5 MAE) and `dewards` for cores. Normative rule in §16.
5. **Does simple additive work?** Yes, and STRATZ's population mean works better than our own fitted effect on every Standard cell:

   | CS@10 variance reduction | our fitted `own[]` | STRATZ `heroStats.stats` | both, 50/50 |
   |---|---|---|---|
   | Carry STANDARD | +8.0% | **+9.0%** | +9.3% |
   | Mid STANDARD | +13.8% | **+15.7%** | +15.9% |
   | Offlane STANDARD | +4.3% | **+5.6%** | +5.7% |
   | Support STANDARD | +2.9% | **+12.4%** | +10.0% |
   | Carry **TURBO** | **+17.0%** | +8.6% | +15.1% |
   | Mid **TURBO** | **+20.4%** | +16.0% | +20.0% |

   The Turbo reversal is the evidence that `heroStats.stats` is Standard-only; corroborated by level (STRATZ NW@10 ≈ 3,454 vs our Standard 3,788 and our Turbo 8,398). **[EMPIRICAL / INFERENCE]**
6. **Interaction with the player's own hero experience?** None in V1. The adjustment is window-relative, so a one-hero player gets `≈ 0` automatically and a hero-switcher gets the correction. That is the correct behaviour with no extra machinery.
7. **Per-hero personal baselines?** **No.** Already rejected upstream — the Insights SSOT records hero keys reaching N ≥ 20 in only **11.5%** of evaluations **[REPO]**. Nothing here changes that.
8. **Does the rolling 20 still make sense?** Yes. The window is what makes the adjustment relative, and §11 shows hero-mix drift is a minority (5.8–30.4%) of baseline drift — large enough to correct, not large enough to invalidate the window.
9. **Global or only where lane context is used?** **Global, per the §6 matrix** — restricting it to laning metrics would forfeit its largest wins.

### 3.2 Blocker B — does STRATZ `lane` leak realised behaviour?

**Answer: outcome (1) with a trim — the assignment is good enough, and we drop the one component that carried the risk.**

**How STRATZ determines `lane`** — not documented by STRATZ. What we can state: the value is one of `SAFE_LANE / MID_LANE / OFF_LANE / JUNGLE / ROAMING / UNKNOWN` **[PAYLOAD]**, it is present on unparsed as well as parsed rows, and it is near-deterministic given (hero, position) — which is what a draft/role-derived label looks like, not what a trajectory classifier looks like. We did **not** find a way to reproduce it from telemetry, and `locationReport` (the obvious candidate input) carries no timestamps. **[INFERENCE]**

**Measured determinism [EMPIRICAL]**, modal-lane share per (hero, position) cell, n ≥ 80:

| Position | cells | median modal share | p10 | min |
|---|---|---|---|---|
| POSITION_1 | 47 | **1.000** | 1.000 | 0.988 |
| POSITION_2 | 66 | **1.000** | 0.993 | 0.967 |
| POSITION_3 | 62 | **1.000** | 0.994 | 0.980 |
| POSITION_4 | 57 | 0.976 | 0.897 | **0.775** |
| POSITION_5 | 53 | 0.986 | 0.967 | 0.938 |

Worst cells are all supports: Monkey King P4 0.77, Axe P4 0.82, Io P4 0.85, Nature's Prophet P4 0.88 — and the minority values are `JUNGLE` / `ROAMING` / `UNKNOWN`, which **already fail our lane gate** and produce `UNAVAILABLE`.

**Realised early presence [EMPIRICAL]** — from 10,935 players with ≥1 positioned event before 10:00 in the ten-player cache (kill/death/assist/ward coordinates; data-derived lane centroids BOT (155,103), TOP (99,148), MID (125,125)):

| Position | share of early positioned events inside the assigned lane |
|---|---|
| POSITION_1 | 0.846 |
| POSITION_2 | 0.631 |
| POSITION_3 | 0.815 |
| POSITION_4 | 0.773 |
| POSITION_5 | 0.784 |

Supports are only modestly below cores, and mid is the *lowest* of all (0.631) because mid players fight off-lane — so this metric has a high noise floor and does not indicate support-specific contamination. The genuine outliers are Spirit Breaker P4 **0.559**, Pudge P4 0.695, Nature's Prophet P4 0.681.

**Does the ally term earn its keep?** [EMPIRICAL], STANDARD, personal-baseline residual-variance reduction:

| Metric / role | hero only | + opponents | + opponents **and ally** | ally increment |
|---|---|---|---|---|
| CS@10 Carry | 7.81 | 11.58 | 12.12 | **+0.54** |
| CS@10 Mid | 13.76 | 20.06 | 20.06 | +0.00 (1v1, sanity check) |
| CS@10 Offlane | 4.41 | 9.10 | 9.67 | +0.57 |
| NW@10 Carry | 4.10 | 7.40 | 8.88 | +1.48 |
| NW@10 Offlane | 3.06 | 6.56 | 7.04 | +0.48 |
| level-6 Carry | 2.13 | 4.28 | 5.98 | +1.70 |
| level-6 Offlane | 1.52 | 2.67 | 5.09 | +2.42 |
| deaths<10 Carry | 3.75 | 6.50 | 7.01 | +0.51 |

**Decision: drop the ally term from V1.** On the canonical label metric it is 4.5% of the signal. It is also the only place in the system where a coefficient attaches to a teammate's hero — a user could reverse-engineer "the app thinks my Spirit Breaker made my lane hard", which violates the no-teammate-blame rule in substance even if no string ever says it. The measured cost is NW −17% and level-6 −29%/−48% relative; we take it, and list the ally term as OPTIONAL-LATER (§15).

There is no residual circularity concern for the opponent term: **the score cannot be changed by anything the viewer does**, because every input is fixed at the horn. The honest remaining caveat is conceptual, not statistical — an opponent coefficient blends "this hero contests CS hard" with "this hero often isn't in the lane". Both are properties of the drafted hero, known before the first creep wave.

### 3.3 Blocker C — population replication

**Replicated at population scale, from a completely independent source.** [STRATZ-LIVE]

635 `laneOutcome` calls, 0 failures, **2,758,610 population lane observations** in one week. Comparison against our independently fitted partial effects on the 94,888-match corpus:

| Role | STRATZ lane observations | pooled heroes | corr(STRATZ pooled, our fitted partial) | slope |
|---|---|---|---|---|
| Carry (P1) | 666,743 | 61 | **+0.874** (53 heroes) | 0.748 |
| Mid (P2) | 271,486 | 23 | **+0.929** (22 heroes) | 0.778 |
| Offlane (P3) | 630,139 | 55 | **+0.881** (42 heroes) | 0.722 |
| Carry ally (`isWith`) | 395,038 | — | +0.818 | 0.85 |

Face validity, straight from the STRATZ population, never told anything about Dota:

- **Carry** hardest: Viper −6.2, Witch Doctor −3.8, Silencer −3.7, Necrophos −3.6, Razor −3.5, Jakiro −3.4. Easiest: Dark Seer +5.1, Enigma +3.6, Sand King +3.4, Earth Spirit +3.3, Primal Beast +2.8, Wraith King +2.6.
- **Mid** hardest: Outworld Destroyer −6.5, Arc Warden −3.8, Necrophos −3.2, Sniper −2.6. Easiest: Keeper of the Light +8.9, Tinker +4.5, Pangolier +3.6, Puck +3.3.
- **Offlane** hardest: **Drow Ranger −5.8**, Sniper −4.3, Skywrath Mage −2.8, Witch Doctor −2.7, Silencer −2.6. Easiest: **Wraith King +6.1**, Sven +3.7, Luna +3.4, Nature's Prophet +3.1.

The offlane list is the strongest evidence that this is real and role-specific: the model independently learned that a Drow safelane is the offlaner's nightmare and a Wraith King safelane is a free lane — the exact inverse of the Carry list, with no shared parameters.

Replication scorecard:

| V1 finding | Verdict |
|---|---|
| Own-hero effect is substantial | **REPLICATED** — and larger than V1 claimed, across 15 metrics |
| Lane environment effect is substantial enough to matter | **REPLICATED** — +3.8 to +6.3pp on top of hero, population-confirmed |
| Additive effects remain stable | **REPLICATED** — corr +0.87/+0.93/+0.88 vs an independent corpus |
| Exact interaction terms unnecessary | **REPLICATED, and strengthened** — pairwise +4.44% vs pooled +4.50% at 54–71% pairwise coverage |
| Wide-Typical (20/60/20) bucketing sensible | **REPLICATED** — extreme-flip 0.24% (Carry) / 0.00% (Mid) / 0.06% (Offlane) at band 0.20 |
| Carry/Mid/Offlane stronger than Support | **REPLICATED** — Support CS gap +2.7 vs +8.4…+9.8; score reliability 0.751 vs 0.834–0.948 |
| Turbo weak | **REPLICATED, and now also unsupported by the data source** |
| Labels have face validity | **REPLICATED** (lists above) |
| NW should be the primary label metric | **CONTRADICTED** — CS is, and loses nothing (§6) |
| Ally term worth keeping | **CONTRADICTED for V1** — +0.54pp on CS |

---

## 4. Final Statistical Architecture

All quantities are in the metric's native units.

**Personal baseline** (unchanged, from Role Metrics V1 §7) — median of the ≤20 most recent prior measured observations sharing `progression_bucket + effective_role + metric_id + metric_version`, minimum 5 priors:

```
B = median{ y_j : j ∈ W },    W = the ≤20-match baseline window
```

**Own-hero adjustment** — population level for this hero at this position, minus the same quantity over the baseline window:

```
h(m)  = heroStats.stats[hero(m), position(m), t].field      # NULL if matchCount < 300
Δ_h   = clamp( h(current) − median{ h(j) : j ∈ W, h(j) ≠ NULL },  ±cap )
        requires ≥3 non-NULL values in W, else Δ_h = 0
```

**Lane-environment adjustment** — sum over the drafted lane opponents of the pooled population effect, again window-relative:

```
e_raw(m) = Σ_{o ∈ lane_opponents(m)} OPP[position(m)][o]
E(m)     = slope[role] · e_raw(m)                            # slope frozen per role
Δ_e      = clamp( E(current) − median{ E(j) : j ∈ W, E(j) ≠ NULL },  ±0.8·cap )
           requires ≥3 non-NULL values in W, else Δ_e = 0
```

where `OPP[position][o]` is derived once, offline, from `heroStats.laneOutcome`:

```
for each heroId1 = a with Σ_b matchCount(a,b) ≥ 3000:
    base(a)      = Σ_b csCount(a,b) / Σ_b matchCount(a,b)
    effect(a,b)  = csCount(a,b)/matchCount(a,b) − base(a)         # only if matchCount(a,b) ≥ 20
OPP[position][b] = Σ_a effect(a,b)·matchCount(a,b) / Σ_a matchCount(a,b)
                   defined only where Σ_a matchCount(a,b) ≥ 500
```

**Context-adjusted expectation and performance residual:**

```
Ê   = B + Δ_h + Δ_e
res = y − Ê                                   (higher-is-better)
    = Ê − y                                   (lower-is-better)
state = ABOVE   if res ≥ +τ·σ_pop
        BELOW   if res ≤ −τ·σ_pop
        IN_LINE otherwise
```

`σ_pop` is the metric's frozen population standard deviation; `τ` is a frozen per-metric constant in the parameter set (V1 default `τ = 0.35`, which puts roughly a third of observations in each state). **Caps:** `cap = 0.75 · σ_pop`; for CS@10 that is ≈ ±8 CS. Measured cost of the cap **[EMPIRICAL]**: Carry 13.60% → 13.60%, Offlane 10.14% → 10.15%, Mid 22.66% → 21.11%. Uncapped, |Δ_h| reaches **21.0 CS** (p99 = 13.4, 2.66% of observations exceed 10 CS); |Δ_e| reaches 10.6 CS (p99 = 7.5).

The model is **the additive shrunken form from V1, unchanged**. No ML. The only structural change is that the coefficients are read from STRATZ instead of fitted by us, which removes the shrinkage constant `k` from the runtime contract entirely (STRATZ's own counts do the work, gated by `matchCount` minimums).

---

## 5. Final Lane Context Model

| | |
|---|---|
| **Inputs** | viewer `heroId`, `position`, `lane`, `isRadiant`; lane opponents' `heroId`, `lane`, `isRadiant`; `progression_bucket`; `parameter_set_version` |
| **Physical lane** | `MID_LANE → MID`; `SAFE_LANE → BOT` if Radiant else `TOP`; `OFF_LANE → TOP` if Radiant else `BOT` |
| **Lane opponents** | enemy-team players resolving to the same physical lane |
| **Model** | `E = slope[role] · Σ OPP[position][opponent]`, from §4 |
| **Categories** | `DIFFICULT` · `TYPICAL` · `FAVOURABLE` · `UNAVAILABLE` |
| **Thresholds** | frozen absolute numbers at the population 20th / 80th percentile, never runtime quantiles |
| **V1 thresholds** (CS units, from the STRATZ parameter set) | Carry `≤ −2.05` / `≥ +1.52` · Mid `≤ −2.01` / `≥ +2.04` · Offlane `≤ −1.91` / `≥ +1.32` |
| **Versioning** | `(parameter_set_version, model_version)` stored per observation; a change is a version bump and a deterministic rebuild |

**Stability and effect size** [EMPIRICAL], opponents-only CS model, two models fitted on independent halves of the corpus:

| Role | half-sample score corr | Spearman-Brown (full) | band 0.20 agree | extreme flip | CS@10 gap D→F | NW@10 gap | winrate D / F |
|---|---|---|---|---|---|---|---|
| Carry | +0.715 | **+0.834** | 65.1% | 0.24% | **+9.3** | +393 | .505 / .545 |
| Mid | +0.902 | **+0.948** | 82.5% | 0.00% | **+9.8** | +461 | .532 / .564 |
| Offlane | +0.815 | **+0.898** | 70.5% | 0.06% | **+8.4** | +416 | .532 / .531 |
| Support | +0.601 | +0.751 | 59.1% | 1.73% | +2.7 | +92 | .515 / .518 |

These are a **lower bound** on shipped stability: they come from a 7.5k-row corpus fit, whereas the shipped parameters are read from 271k–667k population lane observations per position per week.

**Honest caveat on the winrate column.** V1 reported the label as winrate-flat. At the final V1 form the spread is **+4.0pp (Carry), +3.2pp (Mid), −0.1pp (Offlane)** between Difficult and Favourable. It is small, and Offlane is flat, but it is not exactly zero — facing Viper correlates mildly with the enemy having drafted well. This is a reason to keep the label out of outcome copy (§12), not a reason to withhold it.

**Fallback** — see §13.

---

## 6. Context × Metric Matrix

Classes: **A** personal baseline only · **B** + own-hero adjustment · **C** + own-hero + lane environment · **D** do not baseline-adjust · **E** not reliably interpretable.

All decisions are read off the §3.1 sweep. "Scored?" means the metric may emit `ABOVE / IN_LINE / BELOW`.

| Metric | Role | Hero adj? | Lane adj? | Class | Scored as performance? | Reason |
|---|---|---|---|---|---|---|
| `carry.last_hits_at_10.v1` | Carry | **Yes** | **Yes** | **C** | Yes | 7.7 → 11.7; the flagship case |
| `carry.cs_10_to_20.v1` | Carry | **Yes** | No | **B** | Yes | Hero **21.2%**; lane *decreases* it (20.2) — draft effect has decayed by min 12 |
| `carry.net_worth_at_20.v1` | Carry | **Yes** | No | **B** | Yes | Hero 7.0; lane +1.7 only, and 20:00 is past the lane |
| `carry.dead_time.v1` | Carry | No | **No — forbidden** | **D** | Yes, unadjusted | Circularity (V1 §6) *and* the highest cross-metric label contradiction (§7 below). Also uncomputable today: canonical `death_events` carry only `{time}`, no `timeDead` **[PAYLOAD]** |
| `carry.hero_damage_share.v1` | Carry | **Yes** | No | **B** | Yes | Hero 7.4; lane adds 1.1 on a whole-match metric — noise |
| `carry.tower_damage_share.v1` | Carry | **Yes** | No | **B** | Yes | Hero 7.3; lane −0.3 |
| `mid.lane_net_worth_advantage_at_10.v1` | Mid | **No** | **Yes** | **C\*** | Yes | A *difference* between two players: the viewer's own hero level cancels only partially, so apply the lane term and the **paired** hero term `h(viewer) − h(counterpart)` |
| `mid.level_6_time.v1` | Mid | **Yes** | **Yes** | **C** | Yes | 2.8 → 7.4; the largest *relative* lane gain of any metric |
| `mid.early_fight_presence.v1` | Mid | **Yes** | No | **B** | Yes | Whole-team ratio; hero 4.9, lane −0.3 |
| `mid.net_worth_at_20.v1` | Mid | **Yes** | No | **B** | Yes | Hero 3.9, lane +0.9 |
| `mid.tower_damage_share.v1` | Mid | **Yes** | No | **B** | Yes | Hero **15.7%** |
| `offlane.lane_net_worth_advantage_at_10.v1` | Offlane | **No** | **Yes** | **C\*** | Yes | As Mid; paired hero term |
| `offlane.net_worth_at_10.v1` | Offlane | **Yes** | **Yes** | **C** | Yes | 2.9 → 6.7 |
| `offlane.fight_presence.v1` | Offlane | No | No | **A** | Yes | Hero 1.8, lane −0.7 — nothing to correct |
| `offlane.objective_involvement.v1` | Offlane | No | No | **E** | **No — demote to diagnostic** | Hero **0.4%**, lane **−0.6%**; tiny integer denominators; nothing in it is attributable |
| `support.fight_presence.v1` | Support | No | No | **A** | Yes | Hero 4.7, lane 4.4 — below the cost of the machinery |
| `support.observer_wards_placed.v1` | Support | No | No | **A** | Yes | Hero 2.9 for Support; **−0.3 to −3.8 and MAE −19.7…−33.7% for cores** — the floor rule (§16) |
| `support.vision_denial.v1` | Support | No | No | **A** | Yes | Hero 2.1, MAE +1.2 — marginal, not worth a term |
| `support.camps_stacked_at_20.v1` | Support | No | No | **A** | Yes | Hero **−0.7%** for Support (it helps *cores*, who do not have this metric) |
| `support.healing.v1` | Support | **Yes** | No | **B** | Yes | Hero **47.7%** — the single largest correction in the system |

`C*` = lane adjustment plus a *paired* hero term, not the plain own-hero term.

**Net V1 change surface:** 3 metrics become class **C** (+2 as `C*`), 9 become class **B**, 6 stay **A**, 1 stays **D**, 1 is demoted to **E**.

---

## 7. Performance vs Diagnostic vs Context vs Outcome

Two tests, both answerable from the sweep: *can the player reasonably move it?* and *can we interpret movement without pretending circumstances were identical?*

**Performance metrics** — emit `ABOVE / IN_LINE / BELOW`:
`carry.last_hits_at_10`, `carry.cs_10_to_20`, `carry.net_worth_at_20`, `carry.hero_damage_share`, `carry.tower_damage_share`, `mid.lane_net_worth_advantage_at_10`, `mid.level_6_time`, `mid.early_fight_presence`, `mid.net_worth_at_20`, `mid.tower_damage_share`, `offlane.lane_net_worth_advantage_at_10`, `offlane.net_worth_at_10`, `offlane.fight_presence`, `support.fight_presence`, `support.observer_wards_placed`, `support.vision_denial`, `support.camps_stacked_at_20`, `support.healing`.

**Diagnostic metrics** — display the number and the personal median, never a good/bad state:
- `offlane.objective_involvement` — **recommended demotion.** Hero 0.4%, lane −0.6%, and the denominator is "enemy towers your team destroyed", frequently 1–3, so one tower moves the ratio by 33–100%. It explains what happened; it cannot rank how you played.
- `carry.dead_time` — **stays scored but unadjusted** (owner's existing lock). It is the one metric where adjusting would be indistinguishable from excusing.
- `deaths_before_10` (not a locked metric; used internally) — diagnostic only.

**Context metrics** — never scored, never trended:
lane context label, lane shape, `position`/`lane`/`role`, hero identity, `Δ_h`, `Δ_e`, `parameter_set_version`.

**Outcome metrics** — describe the match, imply nothing about the individual:
`isVictory`, `{top,mid,bottom}LaneOutcome`, `radiantNetworthLeads`, every Tier-A/B insight card in the Post-Match Insights registry.

**Answer to Part 6 — the multi-metric coherence problem.** **Option A, with CS as the canonical label metric.** Measured visible contradiction rate [EMPIRICAL] — label from the CS environment score, each other metric carrying its own hidden adjustment, "visible contradiction" = labelled `DIFFICULT` while that metric's own offset is favourable by ≥ 0.10 sd, or the mirror:

| Label vs | Carry | Mid | Offlane |
|---|---|---|---|
| `net_worth_at_10` (corr +0.84 / +0.92 / +0.89) | **0.11%** | **0.00%** | **0.26%** |
| `level_6_time` (corr +0.68 / +0.90 / +0.67) | 1.10% | 0.00% | 0.54% |
| `deaths_before_10` (corr +0.42 / +0.48 / +0.45) | **5.00%** | 0.64% | **4.77%** |

A single CS-driven badge is coherent with the NW and level-6 adjustments essentially always. The only metric that would visibly fight the badge is deaths — which we already exclude for circularity. Two independent lines of evidence, one exclusion. Option B (composite score) buys nothing over this; Option C (no badge) throws away the product value.

---

## 8. Final Post-Match Processing Pipeline

Deterministic, ordered. Steps 1–3 and 9–11 already exist; 4–8 are new.

```
 1. INGEST            STRATZ match payload
 2. ELIGIBILITY       bucket ∈ {STANDARD, TURBO}; duration ≥ 600; tracked player not a leaver;
                      match-integrity gates                            [Role Metrics V1 §6]
 3. ROLE              consume upstream effective_role                  [Role Resolution V1]
 4. LANE RESOLUTION   physical lane; lane opponents; lane shape
                      → lane_context_eligible ∈ {true, false}
 5. RAW METRICS       measure each locked metric → value or N/A        [Role Metrics V1 §9]
 6. CONTEXT TERMS     per metric, per its §6 class:
                        h(current), E(current)                          (NULL-able)
                      persist them on the observation
 7. BASELINE          B = median of ≤20 priors, ≥5 required            [Role Metrics V1 §7]
 8. ADJUST            Δ_h, Δ_e (window-relative, ≥3 non-NULL priors, capped)
                      Ê = B + Δ_h + Δ_e
 9. COMPARE           res = ±(y − Ê) → ABOVE | IN_LINE | BELOW | NOT_READY
10. LANE LABEL        E(current) vs frozen thresholds
                      → DIFFICULT | TYPICAL | FAVOURABLE | UNAVAILABLE
11. RENDER            deterministic templates (§9)
```

Ordering notes that matter:

- **4 before 6**, because the lane term is undefined without a resolved lane.
- **7 before 8**, because both adjustments are defined relative to the baseline window, not absolutely. Reversing them double-counts the environment the player usually faces.
- **10 is independent of 9.** The label is computed from the draft alone and never reads the residual. This is what makes §12's separation real rather than stylistic.
- **The Post-Match Insights engine (cards) does not participate.** It keeps its own raw, record-based history system (N ≥ 20, window ≤ 50) **[REPO]**. See §12 and §17.

**Persistence, per observation:**

| Field | Why |
|---|---|
| `raw_value`, `comparison_value` | existing |
| `hero_pop_level` (`h`), `lane_env_score` (`E`) | so the window median is a lookup, and so a rebuild needs no STRATZ calls |
| `delta_hero`, `delta_env`, `adjusted_expectation`, `residual`, `performance_state` | derived; recomputed on rebuild |
| `lane_context` | derived |
| `parameter_set_version`, `model_version`, `metric_version` | rebuild key |
| `lane_context_eligible` + `unavailable_reason` | diagnostics |

**What triggers a rebuild:** a role correction (existing contract), a `metric_version` bump (existing), or a `parameter_set_version` bump (new). All three replay the same deterministic path. A rebuild **never calls STRATZ** — `h` and `E` are pure functions of stored hero ids, lane and position, and the parameter set.

---

## 9. Deterministic UI State Model

Finite enums:

```
PerformanceState  : ABOVE | IN_LINE | BELOW | NOT_READY        (4)
LaneContext       : DIFFICULT | TYPICAL | FAVOURABLE | UNAVAILABLE  (4)
TrendState        : Improving | Stable | Declining | Insufficient History  (4, existing)
```

**Composition rule (normative): they are never composed into one sentence.**

| Dimension | Surface | Rationale |
|---|---|---|
| `LaneContext` | a **badge** on the lane-metric group, once per match | It is a property of the match, not of a metric |
| `PerformanceState` | a **per-metric state line** | It is what the player can act on |
| `TrendState` | the **Progress surface**, not the post-match card | Different time horizon, different contract, already has its own UI |

```
CS @10                    52
Above your adjusted expectation
                                        [ Difficult lane ]
```

**Template count:**

| Group | Strings |
|---|---|
| Performance state line (`{metric}` is a slot) | 4 — `"Above your adjusted expectation"`, `"In line with your adjusted expectation"`, `"Below your adjusted expectation"`, `"Building your {metric} baseline"` |
| Lane context badge | 3 — `"Difficult lane"`, `"Typical lane"`, `"Favourable lane"` (`UNAVAILABLE` renders **nothing**) |
| Explainer (one tap, static) | 1 — `"Expectation = your recent {role} median, adjusted for the hero you played and the heroes you laned against."` |
| Unadjusted-metric variant | 1 — `"Above/In line with/Below your usual"` reused with a different noun for class **A**/**D** metrics (3 forms, shared with the 4 above via a slot) |

# Total new deterministic strings: 9.

No string contains two dimensions. Adding a metric adds **zero** strings. If a future dimension must be composed, it goes in the layout, not the copy.

---

## 10. Worked Match Examples

Real matches from the corpus, scored with the shipped STRATZ parameter set (frozen thresholds from §5, `τ = 0.35`, σ_pop = 11.1 CS). `Δ_h` and `Δ_e` are hidden from the user.

**1 — DIFFICULT / ABOVE / LOSS** · match 8753257719 · Carry Bloodseeker
Lane: Bloodseeker + Spirit Breaker vs **Axe / Enchantress**
CS@10 **22** · baseline 14.0 · Δ_h +0.07 · Δ_e **−2.41** · expectation **11.7** · residual **+10.3**
→ *CS @10 · 22 · Above your adjusted expectation · [Difficult lane]*

**2 — FAVOURABLE / BELOW / WIN** · match 8668175486 · Carry Faceless Void
Lane: Faceless Void + Disruptor vs Rubick / Magnus
CS@10 **37** · baseline 41.0 · Δ_h −2.53 · Δ_e **+2.61** · expectation **41.1** · residual **−4.1**
→ *CS @10 · 37 · Below your adjusted expectation · [Favourable lane]*
The match was won. The card does not mention that, and does not soften the state.

**3 — TYPICAL / ABOVE / WIN** · match 8489059428 · Mid Rubick
Lane: Rubick vs Void Spirit · CS@10 **52** · baseline 44.5 · Δ_h 0.00 · Δ_e +2.66 · expectation **47.2** · residual **+4.8**
→ *CS @10 · 52 · Above your adjusted expectation · [Typical lane]*
Note Δ_e is positive yet the label is `TYPICAL`: +2.66 is inside Mid's `+2.04 … ` band only because the *window median* was also positive. Label and adjustment are independent by design.

**4 — DIFFICULT / IN_LINE / LOSS** · match 8578269225 · Offlane Magnus
Lane: Magnus + Invoker vs **Witch Doctor / Slark** · CS@10 **35** · baseline 35 · Δ_h +4.04 · Δ_e **−2.40** · expectation **36.6** · residual −1.6
→ *CS @10 · 35 · In line with your adjusted expectation · [Difficult lane]*

**5 — FAVOURABLE / ABOVE / WIN** · match 8818751353 · Offlane Legion Commander
Lane: LC + Lion vs Alchemist / Techies · CS@10 **34** · baseline 18.5 · Δ_h +4.16 · Δ_e **+4.66** · expectation **27.3** · residual **+6.7**
→ *CS @10 · 34 · Above your adjusted expectation · [Favourable lane]*
Both corrections fire: the player normally offlanes lower-CS heroes, and Alchemist/Techies contest almost nothing. Without them, 34 vs a baseline of 18.5 would have read as a spectacular game; it was a good one.

**6 — DIFFICULT / BELOW / LOSS** · match 8495527259 · Mid Rubick
Lane: Rubick vs **Necrophos** · CS@10 **38** · baseline 46.0 · Δ_h 0.00 · Δ_e −2.50 · expectation **43.5** · residual **−5.5**
→ *CS @10 · 38 · Below your adjusted expectation · [Difficult lane]*
**This is the case the whole design exists to get right.** The lane was genuinely hard and the player still under-performed for it. The card says so.

**7 — TYPICAL / BELOW / WIN** · match 8813965061 · Carry Naga Siren
Lane: Naga + Treant vs Ogre Magi / Rubick · CS@10 **23** · baseline 28.0 · Δ_h **+4.17** · Δ_e −0.02 · expectation **32.1** · residual **−9.1**
→ *CS @10 · 23 · Below your adjusted expectation · [Typical lane]*
The hero correction makes the verdict *harsher*, not kinder — Naga farms more than this player's usual carries. Context adjustment is not a discount.

**8 — Baseline not ready** · fewer than 5 priors for `Carry / STANDARD / carry.last_hits_at_10.v1`
→ *CS @10 · 41 · Building your CS @10 baseline*. The lane badge **may still render** — it needs no history. No `ABOVE/BELOW`.

**9 — Lane context unavailable** · the viewer's lane is `ROAMING`, or the shape is `2v1`, or an opponent is missing from the parameter set
→ *CS @10 · 44 · Above your adjusted expectation* with `Δ_e = 0` and **no badge at all**. `UNAVAILABLE` is never drawn as "Typical".

---

## 11. Progression Impact

**Decision: A — the locked 10-match trend stays on the raw rolling baseline. No change to Progress & History V1.**

The trend is defined **[REPO]** over "the ordered ten-point baseline sequence" — it tracks the movement of the rolling baseline, not per-match residuals. Switching it to context-adjusted residuals would make it more statistically pure and much less explainable, and the measured problem does not justify that.

Measured [EMPIRICAL] — 10-point baseline drift, STANDARD:

| Metric / role | sd(raw 10-pt drift) | sd(hero-mix drift) | hero-mix share of raw variance | corr | sign flips if adjusted |
|---|---|---|---|---|---|
| CS@10 Carry | 3.15 | 1.25 | 15.6% | +0.225 | 7.5% |
| CS@10 Mid | 3.69 | 2.04 | **30.4%** | +0.311 | **10.8%** |
| CS@10 Offlane | 3.20 | 1.21 | 14.2% | +0.193 | 6.7% |
| NW@10 Carry | 191 | 46 | 5.8% | +0.142 | 5.2% |
| NW@10 Mid | 215 | 67 | 9.6% | +0.189 | 6.8% |

Hero-pool drift is a real but minority contaminant. **It produces one concrete, binding requirement instead of a contract change:**

> The trend evaluator's "meaningful movement" calibration — currently undefined by Progress & History V1 §"Semantic evaluation", which explicitly forbids inventing a number — **must be set above the hero-mix noise floor**: ≥ 1.25 CS (Carry/Offlane), ≥ 2.04 CS (Mid), ≥ 46 gold (Carry NW@10), ≥ 67 gold (Mid NW@10) of 10-point baseline drift. Below those values, an `Improving`/`Declining` verdict is more likely to be a hero-pool change than a skill change.

This satisfies the existing contract (it supplies a floor for a parameter the SSOT deliberately left open) without introducing a fifth trend state, a second trend system, or an opaque residual.

`Δ_h` and `Δ_e` **are** persisted per observation, so a future `v2` trend on adjusted residuals is a pure replay with no refetch.

---

## 12. Personal Performance vs Match Diagnosis — Boundary Contract

Two systems. They share a match id and nothing else.

| | **Personal Performance** | **Match Diagnosis** |
|---|---|---|
| Question | "How did you perform relative to a reasonable expectation?" | "What patterns contributed to how this match went?" |
| Owner | Role Metrics & Personal Baselines + this document | Post-Match Insights SSOT |
| Surface | per-metric states, lane-context badge | Tier A/B cards, ≤ 3 per match |
| History system | rolling 20-match median, ≥ 5 priors | record window ≤ 50, N ≥ 20 |
| Adjusted by context? | Yes, per §6 | **No** — records must stay raw and comparable |
| May mention lane context? | Yes (badge only) | **No** |
| May mention match outcome? | **No** | Yes |
| May mention a teammate? | **No** | Only as a neutral named fact, per existing card rules |

**Normative rules:**

1. Lane context is an input to *expectation*. It is never an input to, an explanation of, or a modifier of outcome.
2. No card, string or badge may place `LaneContext` and `isVictory` in the same sentence, the same claim, or the same causal frame.
3. Insight cards must not read `lane_context`, `delta_env`, `delta_hero` or `adjusted_expectation`. `OWN_LANE_VS_USUAL` and `OPP_START_VS_HISTORY` stay on **raw** values — a "worst lane gap across your last 50" record is only meaningful if every value in the window was measured the same way.
4. Performance state must not be suppressed, softened or upgraded because of the label. `DIFFICULT + BELOW` renders exactly as `TYPICAL + BELOW` does (example 6).
5. A "why you lost" surface may never cite lane context as a cause, even where the correlation exists (§5: up to +4.0pp winrate).
6. The four contradictory combinations — `DIFFICULT + ABOVE + LOSS`, `FAVOURABLE + BELOW + WIN`, `DIFFICULT + BELOW + WIN`, `FAVOURABLE + ABOVE + LOSS` — are **expected, correct output**, not defects. Examples 1, 2 and 7 are all of them.

---

## 13. Failure / UNAVAILABLE Rules

Fail closed. `UNAVAILABLE` is a rendered absence, never a `TYPICAL` default.

| Situation | Frequency [EMPIRICAL] | Rule |
|---|---|---|
| Lane shape is `2v2` or `1v1` | 97.7% of Standard core matches | compute normally |
| Lane shape `2v1` / `1v2` | 1.6% | **`UNAVAILABLE`** — asymmetric lanes are not what the coefficients describe |
| Tri-lane or larger against the viewer | 0.31% | **`UNAVAILABLE`** |
| Solo core in a side lane (`1vN`) | 0.75% | **`UNAVAILABLE`** |
| No opponent resolves to the viewer's lane | 0.08% | **`UNAVAILABLE`** |
| Viewer lane is `JUNGLE` / `ROAMING` / `UNKNOWN` | <0.01% for cores | **`UNAVAILABLE`** |
| `lane` or `position` null for any lane participant | 2.7% of matches (position), 1.3% (lane) | **`UNAVAILABLE`** |
| Any lane opponent missing from `OPP[]` | 5.0% / 9.9% / 5.3% at one week; target < 3% with a 4–8 week pool | **`UNAVAILABLE`** (never partial-sum) |
| Viewer `(hero, position)` has `matchCount < 300` in `heroStats` | 3.15% at one week, 0.87% at `<100` | `Δ_h = 0`; metric still scored; **no** lane-context impact |
| Viewer hero absent from the population table entirely | **0.00%** — STRATZ covers all 127 | `Δ_h = 0` |
| Brand-new hero after a patch | not observed | `Δ_h = 0`, `UNAVAILABLE` if it is a lane opponent. Self-heals within one parameter refresh |
| Support hero played as a core / core played as support | 1.35% below a 1% population position share; 5.8% below 5% | compute normally **if** `matchCount ≥ 300`, else `Δ_h = 0`. The position-specific table already handles it |
| Fewer than 5 baseline priors | — | `NOT_READY`; badge may still render; `Δ_h = Δ_e = 0` |
| Fewer than 3 non-NULL `h`/`E` values in the window | — | that term is 0; the other still applies |
| Role corrected by the user | — | full deterministic rebuild; `h` and `E` recomputed from stored hero ids against the same `parameter_set_version` |
| Viewer has ≥ 8 deaths before 10:00 | 0.15% | Insights' feeding guard is match-level and stays theirs. Role metrics keep their own eligibility; do **not** import the guard |
| Enum drift (`MatchLaneType` gains a value) | — | unknown enum ⇒ `UNAVAILABLE` |
| Turbo, or Support role | — | out of V1 scope: no badge, no adjustment, metrics render on the raw personal baseline |

---

## 14. Engineering Impact

| | |
|---|---|
| **Runtime API calls** | **Zero extra.** `heroId`, `lane`, `position`, `isRadiant` are already in the existing batch |
| **Runtime compute** | ≤ 4 dictionary lookups, 2 medians over ≤ 20 stored floats, 2 clamps. Microseconds. No model at request time |
| **Offline fetch** | `heroStats.stats`: **5 calls** (one per position, all 127 heroes, ~157 KB each). `heroStats.laneOutcome`: **381 calls** for P1/P2/P3 `vs` only, after dropping the ally term (635 with it). Measured: 635 calls in **916 s**, 0 failures, at 1.2 s/call **[STRATZ-LIVE]** |
| **Refresh cadence** | Quarterly, or on a major patch. Pool a rolling 4–8 week window (condition 2). Patch stability was +0.74 across 180/181→182 for heroes with ≥60 observations **[EMPIRICAL, V1]** |
| **Parameter set size** | `OPP`: 3 positions × ≤127 heroes. `HERO`: 5 positions × 127 heroes × the fields used. Plus 6 thresholds, 3 slopes, per-metric `σ_pop`/`τ`/`cap`. **< 150 KB of JSON** |
| **Per-observation storage** | 2 floats (`h`, `E`) + 2 short strings (`parameter_set_version`, `lane_context`). ~40 bytes |
| **Backfill** | A local replay over stored match rows. **No STRATZ calls.** Idempotent |
| **Incremental** | Fully — new matches need only the current parameter set |
| **Versioning** | `(model_version, parameter_set_version)` per observation; a bump triggers the same rebuild path as a role correction. Both old and new retained for QA |
| **Determinism** | Same payload + same versions ⇒ identical `Ê`, residual, state and label, always |
| **New offline pipeline** | One scheduled job: fetch → derive `OPP`/`HERO` → validate coverage ≥ 97% and slope drift → publish a versioned artefact. No training, no corpus, no ML |

---

## 15. V1 Scope

### REQUIRED

1. Offline parameter job: `heroStats.stats` (5 calls) + `heroStats.laneOutcome` P1/P2/P3 `vs` (381 calls), 4–8 week pool, published as a versioned artefact with frozen thresholds, slopes, `σ_pop`, `τ` and caps.
2. Lane resolution (physical lane, opponents, shape) and the `UNAVAILABLE` gate of §13.
3. Window-relative `Δ_h` and `Δ_e` with caps at `±0.75·σ_pop` / `±0.6·σ_pop`.
4. The §6 matrix, exactly: 3 metrics class **C**, 2 class **C\***, 9 class **B**, 6 class **A**, 1 class **D**, 1 demoted to **E**.
5. Per-observation persistence of `h`, `E`, `parameter_set_version`.
6. Lane-context badge, `STANDARD` × {Carry, Mid, Offlane} only, 20/60/20 frozen thresholds.
7. The 9 deterministic strings of §9, with the never-compose rule.
8. Forbidden-input list (§16) encoded as a test, not a comment.
9. Trend calibration floors from §11 written into the calibration binding.
10. Regression test on the `csCount` slope (condition 1) and on parameter coverage ≥ 97% (condition 2).

### OPTIONAL

- Badge rendered when the baseline is not ready (it costs nothing and is honest).
- Storing `Δ` tables for XP and deaths without using them, to keep the option cheap.
- A one-tap explainer showing `baseline → hero → lane → expectation`.

### NOT V1

- **The lane-partner (ally) term.** +0.54pp on CS; the only teammate-attribution surface. Revisit only if NW@10 or level-6 becomes a headline metric.
- **Turbo.** 1.7% personal-baseline gain, score reliability 0.73, and the STRATZ source does not cover it.
- **Support lane context.** CS gap +2.7 vs +8.4…+9.8; reliability 0.751. (Support *hero* adjustment for healing and damage shares **is** in scope — that is class **B**, not lane context.)
- **Exact (viewer hero × opponent hero) pairs.** +4.44% vs +4.50% pooled, with 54–71% coverage at population scale. Settled twice now.
- **Context-adjusted trend.** §11.
- **Any ML, any runtime model, any LLM.**
- **Realised lane context of any kind** — `locationReport` has no timestamps, `laneReport.radiant` is truncated to 18 buckets, playback availability flips daily **[PAYLOAD]**.
- **Bracket conditioning.** Blocked by the existing rank fence **[REPO]**.

---

## 16. Final V1 Contract

**Definition.** *Context-adjusted expectation* is the player's own recent median for a metric, shifted by two population-derived, draft-fixed quantities: the level this hero normally reaches at this position, and the effect the drafted lane opponents normally have. It is an expectation, not a prediction, not a win probability, and not a judgement about anyone.

*Lane context* is a three-state summary of the second quantity alone. It is a property of the draft. It never modifies a verdict; it modifies what the verdict is measured against.

**When computed.** Once at match processing, after `effective_role` resolves. Recomputed only on role correction, `metric_version` bump, or `parameter_set_version` bump. Never at read time.

**Allowed inputs.** Viewer `heroId`, `position`, `lane`, `isRadiant`; lane opponents' `heroId`, `lane`, `isRadiant`; `progression_bucket`; the frozen parameter set; the player's own prior observations of the same metric. Nothing else.

**Forbidden inputs (normative).** Any trajectory or event of any player in this match; the metric being scored, at any timestamp; `{top,mid,bottom}LaneOutcome`; `laneReport`; `towerDeaths`; `radiantNetworthLeads`/`radiantExperienceLeads`; `firstBloodTime`; `analysisOutcome`; `didRadiantWin` / `isVictory`; `imp`, `award`, `behavior`, `intentionalFeeding`, `streakPrediction`; rank, bracket, MMR, `partyId`; **the lane-partner hero** (V1); anything about what a teammate or opponent actually did after the horn.

**Applicable scope.** `progression_bucket = STANDARD`; `effective_role ∈ {Carry, Mid, Offlane}` for lane context. Own-hero adjustment additionally applies to Support and to the whole-match metrics listed class **B** in §6. Turbo receives neither.

**Metrics.** Exactly the §6 matrix. Lane adjustment touches 5 metrics (3 **C**, 2 **C\***). Hero adjustment touches 14. Nothing else is adjusted, and **deaths, dead time and objective involvement are never lane-adjusted**.

**Baseline interaction.** The personal baseline keying is unchanged: `progression_bucket + effective_role + metric_id + metric_version`. **No context-specific or hero-specific personal baselines are created.** Both adjustments are differences against the baseline window's own median, so a player who always plays one hero into hard lanes is corrected by ≈ 0 — correctly.

**Progression interaction.** None. The locked 10-point trend continues to run on raw rolling baselines. The only obligation is the calibration floor of §11.

**Deterministic states.** `PerformanceState` ∈ {ABOVE, IN_LINE, BELOW, NOT_READY}. `LaneContext` ∈ {DIFFICULT, TYPICAL, FAVOURABLE, UNAVAILABLE}. They are never composed in one string. 9 templates total.

**Fallback.** §13, fail closed. `UNAVAILABLE` renders no badge and sets `Δ_e = 0`; it is never rendered as `TYPICAL`. A missing hero level sets `Δ_h = 0` and never blocks the metric.

**Confidence / minimum data.** Lane context requires a resolved 2v2 or 1v1 shape, non-null `lane` and `position` for every participant, and every lane opponent present in `OPP[]`. `Δ_h` requires `matchCount ≥ 300` and ≥3 non-NULL window values. `Δ_e` requires ≥3 non-NULL window values. Performance state requires `BASELINE_READY` (≥5 priors).

**Versioning and rebuild.** `(match payload, model_version, parameter_set_version, metric_version)` ⇒ identical output, always. Thresholds, slopes, caps and `τ` are frozen absolute numbers inside the parameter set, never computed at runtime. Any bump triggers a deterministic, idempotent rebuild that reads only stored data.

**Copy guardrails.** The label may contextualise a metric. It may never appear as a reason, a cause, or an excuse. Forbidden: "not your fault", "you lost because", "unwinnable lane", "your support was bad", any teammate-quality claim, any sentence containing both the label and the match result, and any softening of `BELOW` because the lane was `DIFFICULT`.

---

## 17. Required Changes to Existing SSOTs

| # | Document | Section | Old assumption | New rule | Why |
|---|---|---|---|---|---|
| 1 | **Role Metrics & Personal Baselines V1** | §7 *Comparison semantics* | `value_delta = x − b` against the raw rolling median | `value_delta = x − (b + Δ_h + Δ_e)` for metrics in classes **B**/**C**/**C\***; classes **A**/**D** unchanged. Define `Δ` per §4 | The comparison is the thing this research changes. Without this edit the whole model has no effect |
| 2 | **Role Metrics & Personal Baselines V1** | §9 registry | Each entry has no context fields | Add `context_class ∈ {A,B,C,C*,D,E}`, `sigma_pop`, `tau`, `cap` to every entry, per §6 | The registry is the declared source of truth for metric behaviour |
| 3 | **Role Metrics & Personal Baselines V1** | §9 `offlane.objective_involvement.v1` | LOCKED as a scored performance metric | Demote to **diagnostic**: display value and personal median, emit no `ABOVE/IN_LINE/BELOW` | Hero adjustment 0.4%, lane −0.6%, denominator frequently 1–3 towers. It cannot be scored honestly |
| 4 | **Role Metrics & Personal Baselines V1** | §8 *N/A versus zero* | Covers N/A vs 0 for values | Add the **floor rule**: a metric whose baseline-window median sits at the metric's floor must not receive a population adjustment | Measured: adjusting core ward counts moves MAE by −19.7% to −33.7% |
| 5 | **Role Metrics & Personal Baselines V1** | §13 *Hard invariants* | — | Add: "no per-hero and no per-context personal baselines"; "deaths and dead time are never context-adjusted"; "context is never an input to a performance state, only to the expectation it is measured against" | Makes the circularity guarantee testable |
| 6 | **Progress & History V1** | §*Semantic evaluation* (calibration) | Thresholds intentionally undefined | Add the hero-mix noise floors of §11 as a **lower bound** on the meaningful-movement threshold | The SSOT forbids inventing a number; this supplies a measured floor instead |
| 7 | **Post-Match Insights SSOT** | §7.3 comparator cohorts, §9.4, §9.5 | Lane cards use raw values | **No change to behaviour** — add an explicit note that Insights cards never read `lane_context`, `delta_env`, `delta_hero` or `adjusted_expectation` | Prevents the two history systems from silently merging; records must stay raw |
| 8 | **Post-Match Intelligence Feasibility V1** | §2.2 field inventory | `laneReport` = "N, shape unresolved"; `locationReport` untested | Update to the measured failure modes: `laneReport.radiant` is truncated to exactly 18 half-minute buckets regardless of duration; `locationReport` has no `time` field and a duration-independent length | Both currently read as "re-investigate later"; they are closed |
| 9 | **Post-Match Intelligence Feasibility V1** | §2.2 | `heroStats` noted only as "aggregate item timings unusable" | Add `heroStats.stats` and `heroStats.laneOutcome` as **V** (verified, in use), with the Standard-only and `csCount`-semantics caveats | They are now load-bearing production dependencies |
| 10 | **Role Resolution & Correction V1** | §11 rebuild contract | Rebuild covers observations, baselines, PBs | Add `lane_context`, `delta_hero`, `delta_env`, `adjusted_expectation` to the rebuilt derived state; confirm the rebuild makes no provider calls | A role correction changes `position`, which changes both adjustments |
| 11 | **Match Lifecycle V1** | — | — | **No change.** Lane-context unavailability is a metric-level state, never a lifecycle failure | Stated explicitly so nobody routes it there |
| 12 | **Dota Tracker V1 Product SSOT** | — | — | **No change required.** The badge is a new element inside an existing surface | Coexists |

---

## Appendix — Risks that survive

1. **`csCount` is undocumented.** Mitigated by the frozen slope and a drift test (condition 1), not by knowledge.
2. **STRATZ is now a load-bearing modelling dependency, not just a data feed.** If `heroStats` changes shape or semantics, the parameter job breaks. Mitigation: the job validates coverage and slope before publishing; a failed validation keeps the previous artefact, and the product degrades to `Δ_e = 0`, not to a wrong number.
3. **No bracket conditioning** (rank fence). A Viper offlane is not equally oppressive at every skill level; the coefficient is a population average. Note that STRATZ's population skews lower than our corpus (CS@10 41.4 vs 45.4), which is harmless because every term is window-relative.
4. **Draft is chosen, not assigned.** A player who habitually first-picks greedy carries sees more `DIFFICULT` lanes. Not corrected in V1; the 60% `TYPICAL` band limits the exposure.
5. **The label carries a small winrate tilt** (+4.0pp Carry, +3.2pp Mid, −0.1pp Offlane). §12 rule 5 exists because of this number.
6. **Most laning variance stays unexplained.** After both corrections, residual sd is ≈ 10.2 CS on a mean of 44. The product must never imply the expectation explains the match.
7. **The hero term is the volatile one.** p99 = 13.4 CS, max 21.0 uncapped. The cap is not optional polish; it is the difference between a believable number and an absurd one.

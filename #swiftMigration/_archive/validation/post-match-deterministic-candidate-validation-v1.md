# Post-Match Deterministic Candidate Validation V1

Status: RESEARCH VALIDATION — candidate menu for product selection (non-normative)
Date: 2026-09-15
Primary source of truth: [Post-Match Intelligence Deep Research V2](../research/post-match-intelligence-deep-research-v2.md)
Scope: the four locked families — Lane Story · Match Turning Point · Hidden Enemy Activity · Item Execution & Power Spikes
Machine-readable outputs: [`post-match-candidate-validation-data/`](../generated_data/post-match-candidate-validation-data)
(`candidate-results.csv`, `candidate-definitions.json`, `candidate-examples.json`, `final_metrics.json`, `patch_v3_results.json`, `research-code/`)
Provider calls this phase: STRATZ 274 (4 history lists, 112 core batches, 65 reports batches, 90 playback, 3 diagnostics). OpenDota 0.
Identifiers: none. Accounts appear only as `acct0…acct8`.

This phase stops at a validated candidate menu. It does not define copy templates, the cross-family ranker, UI, SSOT, backend code, or FE contracts.

---

## 1. Executive Summary

**Tested:** 35 candidate shapes (8 lane, 9 turning point, 10 hidden enemy, 8 item) plus 6 tuned variants, calculated deterministically over **886 eligible parsed matches** (484 Standard, 402 Turbo). That is **8,860 player viewpoints** and **1,772 team units**. Personal history was replayed chronologically for **9 real accounts** (65–96 usable matches each).

**Survived (STRONG or STRONG BUT SITUATIONAL):** 18 shapes.

| Family | Strong menu |
|---|---|
| Lane Story | Lane Lead Path (cores), Counterpart Extreme Start, Support Lane Pair, CS-vs-Gold Split, Level-6 Race (Mid), Own Lane vs Usual (history) |
| Match Turning Point | Comeback / Lost Lead, Sustained Lead Flip, Structures Lost While You Were Dead |
| Hidden Enemy Activity | Enemy Stacking (Standard), Our Vision Cleared, Enemy Barely Warded, Enemy Smoke Volume (rate), Enemy Boss Control, Enemy Early-Rich Hero; Smoke → Kills (playback-dependent) |
| Item Execution & Power Spikes | Enemy Core Early Key Item, Own Key Item Timing vs Your History |

### Strongest findings

1. **Lane counterpart data is clean and fires at a healthy rate.** Every parsed match yields a unique counterpart. A meaningful lane story (blowout, separation, or flip at or beyond the bucket p90) appears for **~11%** of viewpoints in both modes and all roles. The "crushed" shape co-occurs with a statistically extreme opponent start **56%** of the time, a natural two-part story.
2. **Comebacks and lost leads are the cleanest turning points:** 10.2% of team units at the bucket p90 deficit (Standard ≥12.3k, Turbo ≥18.3k). Sustained lead flips after the lane phase fire 10.6%, and 53% of them are the same match as a comeback or lost lead.
3. **"What fell while you were dead" is personal and loss-skewed.** ≥4 towers/barracks lost during a single death timer (excluding the last 3 minutes) fires in 10.3% of viewpoints: 17.5% of losses, 3.2% of wins.
4. **Hidden enemy activity is the richest family.** Stacking, vision clearance, smoke rate, bosses, and early-rich heroes each fire 6–10% with low mutual overlap. At least one fires for ~31% of team units.
5. **Enemy early key items are strong and common enough:** 18% of units have an enemy core buying a spike item at or earlier than the bucket's core p5 (e.g. BKB ≤21:28 Standard).

### Surprising failures

- **"Bought but never activated" is almost non-existent.** For active items still in the main inventory at match end and held ≥10 min (Standard) / ≥6 min (Turbo), the never-activated share is **0.5% / 1.2%**, mostly Mjollnir (passive value). The v2 P0 card does not survive. See v2 §Corrections.
- **Lane lead flips are rare.** Ahead early then behind (or reverse) at meaningful magnitude happens in **0.2%** of core lanes. Sustained minute-level flips occur in 0.8%.
- **"Heavy enemy vision" is stock-capped.** Observer placement rate is nearly constant (Standard p50 4.23 vs p90 4.69 per 10 min); raw counts correlate **0.87** with match length. Only clearance and the *absence* of enemy vision carry signal.
- **The largest swing window mostly describes stomps getting worse:** 84% of p90 windows are LEAD_EXTENDED or DEFICIT_DEEPENED.
- **Clash → structures is everywhere:** ≥4 structures within 90 s of a lopsided clash in 35% of team units, even excluding the final push.
- **Lane item races between counterparts are either absurd or rare.** "Same item" comparisons produce "Blink at 90:18 vs 11:14". Restricted to both players' first two key items, they fire for 1.6% of cores.
- **Two data regressions:** `inventoryReport` is empty in the current patch, and STRATZ playback returned null for every match during this run.

### Standard vs Turbo and role differences

- **Turbo stacking is not a story:** team stacks by 15:00 have p90 = 3; ≥5 stacks with a ≥4 edge occurs in 1.5% of Turbo units vs 8.7% (≥7) in Standard.
- **Turbo lane numbers are 2× larger**, so thresholds must be bucketed: core lane-end NW diff p90 is 1,831 Standard vs 3,829 Turbo.
- **Supports' own counterpart NW diffs are small and noisy.** Their lane flips are ±300–400 gold. Supports get a better lane story from the lane pair (both heroes): 9.6%.
- **The Level-6 race needs role-specific thresholds:** p90 is 111 s for Mid vs 176 s for Carry/Offlane in Standard.

---

## 2. Candidate Architecture

### 2.1 Canonical deterministic candidate schema

```json
{
  "candidate_id": "L1_LANE_LEAD_PATH",
  "version": "1.0.0",
  "family": "lane | turning | hidden | items",
  "name": "Lane net-worth path vs counterpart",
  "question_answered": "How did my lane go against the player I actually laned with?",
  "why_player_cares": "one sentence",

  "unit": "viewpoint | team",
  "required_sources": ["STRATZ.match.stats (core op)", "STRATZ reports op (optional)", "STRATZ playback (optional)"],
  "required_fields": ["players.position", "players.lane", "players.stats.networthPerMinute", "..."],
  "eligibility_rules": ["match eligible (§2.3)", "counterpart resolved", "duration >= late checkpoint", "no feeding-guard violation"],

  "calculation": "deterministic formula referencing primitives",
  "shapes": {"SHAPE_NAME": "rule"},
  "trigger_rule": {"raw": "rule", "tuned": "rule", "strong": "rule"},
  "thresholds": {"STANDARD": {}, "TURBO": {}},
  "threshold_source": "corpus distribution (percentile, bucket[, role/position])",
  "severity_or_magnitude": {"metric": "abs(nwdiff_late)", "units": "gold"},

  "history_scope": "none | bucket | bucket+role | bucket+item",
  "history_requirement": "record among prior N / percentile among prior N",
  "minimum_history_n": 10,

  "output_slots": {"shape": "enum", "early_diff": "int gold", "late_diff": "int gold", "checkpoint_minutes": "int", "opponent_hero": "string", "...": "..."},

  "evidence_level": "RAW FACT | DERIVED FACT | VALIDATED HEURISTIC",
  "reliability": "high | medium | low",
  "playback_required": false,
  "redundancy_group": "lane_path",
  "co_fire_notes": "measured overlaps",

  "known_failure_modes": ["..."],
  "prohibited_interpretations": ["..."]
}
```

The complete registry, with all measured thresholds per bucket, is in `candidate-definitions.json`.

### 2.2 Shared primitives (research implementation `research-code/primitives.py`, `metrics.py`)

| Primitive | Definition | Validated basis |
|---|---|---|
| `eligible_match` | Standard (All Pick ranked/unranked) or Turbo; 10 humans; duration ≥600 s; all ten players have stats; no abandon-type leaver; one player per position per team | v2 §2 |
| `counterpart` | P1↔enemy P3, P2↔P2, P3↔P1, P4↔P5, with the same map lane (`SAFE` Radiant = bot, etc.) | 98–99% core agreement, 94–99% supports |
| `nw(p, t)` | `networthPerMinute[t]` = net worth at t:00 | exact vs team lead curve |
| `cs(p, t)`, `xp(p, t)` | sum of the first t per-minute deltas | v2 §10.3 |
| `level_time(p, L)` | `stats.level[L-1]` seconds | v2 |
| `stacks_by(p, t)` | `campStack[t-1]` cumulative | v2 |
| `lead_curve(m, side)` | Σ team NW[t] − Σ enemy NW[t] per minute | exact |
| `structures(m)` | `towerDeaths` classified tower/barracks/ancient/shrine; owner = `isRadiant` | v2 |
| `clashes(m)` | deaths both teams chained ≤20 s and ≤30 grid units of centroid; ≥3 deaths | v2 heuristic 1.0.0 |
| `observers_placed`, `observers_destroyed_by` | `wards.type==0`; `wardDestruction.isWard` | v2 |
| `item_uses`, `purchases`, `final inventory` | `itemUsed`, `itemPurchases`, `item0..5Id` | v2 |
| `farm_other_count(npc)` | Roshan 133, Tormentor 861 counts | 13/13 |
| `turn_window` | best W-minute window (Standard 8, Turbo 5) starting after lane end, maximizing \|Δlead\| / total NW at window end | this phase |
| `sustained_runs` | lead state (≥+1,500 / ≤−1,500) held ≥3 minutes; flips = consecutive opposite runs | this phase |
| `feeding_guard` | any player with ≥8 deaths before the late lane checkpoint (18 of 886 matches) | this phase |
| history helper | prior values in scope, ordered by match start; record / percentile / median | this phase |

**Checkpoints (bucketed):**

| | early | late (lane end) | lane-path window | economy | stacks | swing window | NW goal |
|---|---|---|---|---|---|---|---|
| Standard | 5:00 | 10:00 | 1–12 | 20:00 | 20:00 | 8 min | 10,000 |
| Turbo | 4:00 | 8:00 | 1–9 | 12:00 | 15:00 | 5 min | 15,000 |

### 2.3 Corpus

| Measure | Value |
|---|---|
| Matches loaded | 1,013 |
| Excluded | 127 (no stats 61, abandon-type leaver 56, other mode 8, short 2) |
| Eligible | **886** (484 Standard, 402 Turbo) |
| Viewpoints / team units | 8,860 / 1,772 |
| With reports (chat events) | 822 |
| With cached playback | 97 matches (the new 90 playback calls returned null) |
| History sequences | 9 accounts, 65–96 usable matches each; enemy-team comparisons keyed by bucket, lane comparisons by bucket + role |
| Feeding-guard matches | 18 (2.0%) |

**Threshold policy.** Every threshold is derived from the corpus distribution of the same bucket, and where relevant the same role or counterpart position. Raw rules sit near p75, tuned near p90, strong near p95, unless a fixed domain floor is stated. Percentile rules fire at ~10% by construction; **frequency is therefore not evidence of meaning**, and each verdict also rests on example review and overlap. Thresholds are in-sample for this corpus (8 tracked accounts plus a stratified random set) and should be re-fitted on production data.

---

## 3. Family 1 — Lane Story

### 3.1 Results

| Candidate | Calculation | Eligibility | Raw fire | Tuned fire | Role coverage (tuned C / M / O / S) | History need | Redundancy | Verdict |
|---|---|---|---:|---:|---|---|---|---|
| **L1 Lane Lead Path** | NW diff vs counterpart at early and late checkpoints → shapes | 98.6% | 59.7% | **10.9%** (strong 6.0%) | 9.7 / 11.9 / 9.7 / 11.7 | none | L5 27%, L7 42%, L4 37% of L4 | **STRONG** (cores); supports → L8 |
| L2 Sustained Lane Flip | first ≥3-min run beyond ±p50 followed by opposite run | 98.6% | 1.0% | 0.8% | 0.4 / 0.1 / 0.4 / 1.5 | none | 35% inside L1 | **TOO RARE** |
| **L3 CS-vs-Gold Split** | CS diff and NW diff at lane end have opposite signs; \|CS\| ≥ p50 (12), \|NW\| ≥ p25 | 59.9% (cores) | 12.1% | **2.3%** (Std 1.7, Turbo 3.1) | 2.0 / 2.8 / 2.0 / — | none | L1 7% (distinct) | **STRONG BUT SITUATIONAL** |
| **L4 Level-6 Race** | \|L6 time diff\| ≥ role p90 (Std Mid 111 s, C/O 176 s; Turbo 65 / 115 s) | 59.9% | 37.8% | **10.2%** | 10.2 / 10.3 / 10.2 / — | none | L1 37% of L4 | **STRONG** (Mid) / NEEDS TUNING (Carry–Offlane) |
| **L5 Counterpart Extreme Start** | counterpart CS@late (P1–P3) or NW@late (P4–P5) ≥ p90 for that counterpart position | 98.6% | 21.2% | **10.5%** (strong 5.4%) | 10.3 / 11.3 / 10.7 / 10.2 | optional: record among ≥10 prior (bucket + role) | co-fires with L1 behind 56% | **STRONG** |
| **L6 Own Lane vs Usual** | own lane-end NW diff is best or worst among ≥10 prior (bucket + role) | 47.8% have ≥10 prior (steady state 70.6%) | — | **9.0% of available** | all roles | required | L1 (same metric) | **STRONG BUT SITUATIONAL** |
| L7 Lane Death Trade | \|deaths before lane end diff\| ≥3 | 98.6% | 39.8% | 17.1% (Std 15.4, Turbo 19.0) | 15.4 / 15.7 / 15.4 / 19.4 | none | L1 42% of L1 | **REDUNDANT** (use as an L1 slot) |
| **L8 Support Lane Pair** | Σ NW of both heroes in your map lane vs theirs at lane end ≥ p90 (Std 2,260; Turbo 4,869) | 38.2% of all viewpoints (≈96% of supports) | 34.9% | **9.6%** | supports only | none | L1 37% of L8 | **STRONG** (supports) |

### 3.2 L1 shape distribution (all eligible, Standard cores; Turbo within ±0.5 pp)

| Shape | Rule (T = role-group thresholds) | Share |
|---|---|---:|
| SMALL_GAP | none of the below | 39.9% |
| MODERATE_AHEAD / BEHIND | \|late\| ≥ p50 | 19.8% each |
| DEAD_EVEN | \|early\| ≤ p25 and \|late\| ≤ p25 | 10.1% |
| DOMINATED / CRUSHED | \|late\| ≥ p90 and early already ≥ p50 same direction | 4.6% each |
| PULLED_AWAY / FELL_BEHIND | \|late\| ≥ p90 from an even early lane | 0.4% each |
| LOST_LEAD / RECOVERED | early ≥ +p50 then late ≤ −p50 (or reverse) | 0.2% each (supports 0.8%, but ±300–400 gold) |

Tuned = DOMINATED, CRUSHED, PULLED_AWAY, FELL_BEHIND, LOST_LEAD, RECOVERED.

### 3.3 Thresholds

| | Standard core | Standard support | Turbo core | Turbo support |
|---|---:|---:|---:|---:|
| \|NW diff\| early p25 / p50 | 161 / 340 | 99 / 212 | 328 / 669 | 194 / 418 |
| \|NW diff\| late p25 / p50 / p75 / p90 / p95 | 345 / 738 / 1,288 / 1,831 / 2,254 | 193 / 415 / 701 / 1,070 / 1,239 | 733 / 1,538 / 2,572 / 3,829 / 4,449 | 458 / 993 / 1,624 / 2,377 / 2,838 |
| \|CS diff\| late p50 | 12 | 4 | 11 | 5 |
| Counterpart CS@late p90 (vs P1 / P2 / P3) | 60 / 63 / 53 | — | 48 / 48 / 39 | — |
| Counterpart NW@late p90 (vs P4 / P5) | — | 2,762 / 2,667 | — | 5,820 / 5,508 |

**Why these values.** p50 of \|early\| separates "ahead" from noise; p90 of \|late\| is where lane gaps stop being ordinary. Counterpart thresholds must be keyed by the counterpart's position: a pooled core threshold fired for 3.2% of Carries (facing offlaners) and 16.3% of Mids.

### 3.4 Real examples (diagnostic renderings)

- `[CRUSHED] -1088 @5:00 → -2742 @10:00 vs Phantom Assassin (P1); CS 19-54, deaths 2-0` — Standard Offlane Mars, loss.
- `[DOMINATED] +599 @5:00 → +2314 @10:00 vs Wraith King (P3); CS 75-25` — Standard Carry Necrophos, win.
- `[RECOVERED] -932 @4:00 → +1553 @8:00 vs Necrophos (P2)` — Turbo Mid Invoker, loss.
- `[CS_BEHIND_GOLD_AHEAD] CS -37, NW +656 @10:00 vs Meepo | kill+assist gold 400 vs 0, deaths 0 vs 1` — Standard Mid Rubick.
- `[CS_BEHIND_GOLD_AHEAD] CS -40, NW +751 @8:00 vs Tinker | kill+assist gold 1290 vs 0, deaths 0 vs 6` — Turbo Mid Invoker.
- `[USER_FIRST] L6 you 4:56 vs Tinker 7:55 (Δ179s)` — Standard Mid Kez.
- `[STRONG] Keeper of the Light (P2) CS 66 @10:00 (p90 63)`; history: `STA mid Lina: counterpart CS 72 vs prior n=45, median 45, previous max 65`.
- `L6: STA mid Earthshaker lane diff -2,165 vs prior n=18, median +345, previous worst -1,008`.
- `[PAIR] your lane pair -7,623 NW @8:00` — Turbo Support Pudge, loss.

### 3.5 Failure cases

- **Griefers:** 18 matches have a player with ≥8 deaths before lane end. Examples: "Tinker 18 deaths before 10:00"; "CS +32, NW −691 with 9 deaths". The feeding guard is required for L1, L3, L7.
- **Support flips** are ±300–400 gold. They are technically correct but not interesting; restrict flip shapes to cores or use L8.
- **Hero farm profiles** (Alchemist, Anti-Mage, Meepo) make L5 fire for ordinary games of those heroes. The hero name must be an output slot. Hero-conditioned thresholds are not viable at this sample size.
- **Turbo mid extremes** (±11k at 8:00) are real, but read differently from Standard.
- **L4 for Carry vs Offlane** compares heroes with different XP roles (a safe-lane carry often reaches level 6 later by design).
- **L3 borderline cases** (CS −11, NW +743) are true but less striking than extremes (CS −37, NW +656 with 0 deaths).

### 3.6 Recommended Lane Story pool

| Candidate | Role | Frequency | Comment |
|---|---|---|---|
| **L1 Lane Lead Path** (cores, feeding guard) | Carry / Mid / Offlane | ~11% | Core lane narrative; use L7 deaths and CS as supporting slots |
| **L5 Counterpart Extreme Start** | all | ~10.5% (+ history record ~6% of available) | Best as a companion to L1 behind shapes (56% co-fire) or standalone |
| **L8 Support Lane Pair** | Support | ~10% of supports | The only reliable support lane story |
| **L3 CS-vs-Gold Split** | cores | 2.3% (Turbo 3.1%) | Excellent when it appears; distinct from L1 |
| **L4 Level-6 Race** | Mid (primary) | ~10% | Carry/Offlane version needs hero-aware rules |
| **L6 Own Lane vs Usual** | all | ~9% of users with ≥10 prior | History-gated personal context |

---

## 4. Family 2 — Match Turning Point

### 4.1 Results (team units unless noted)

| Candidate | Calculation | Eligibility | Raw fire | Tuned fire | Coverage | History need | Redundancy | Verdict |
|---|---|---|---:|---:|---|---|---|---|
| T1 Turn Window | best post-lane W-min window by \|Δlead\| / total NW at end; ≥ p90 (Std 17.4%, Turbo 19.0%) | 99.8% | 25.1% | 10.2% (strong 5.2%) | Std 10.1 / Turbo 10.2; start minute p50 21 / 14 | none | T7/T8 ~100%; T3 4%; T2 7% | **NEEDS TUNING** (84% are stomps extending) |
| **T2 Sustained Lead Flip** | after lane end, consecutive ≥3-min runs of opposite sign; min(peak before, peak after) ≥ p75 (Std 7.9k, Turbo 14.2k) | 99.8% | 36.1% | **10.6%** (strong 4.6%) | Std 9.9 / Turbo 11.5 | none | T3 53% | **STRONG** |
| **T3 Comeback / Lost Lead** | win after min lead ≤ −p90 deficit, or loss after max lead ≥ same (Std 12,263; Turbo 18,332) | 100% | 25.2% | **10.2%** (strong 5.2%) | Std 10.1 / Turbo 10.2 | none | T2 53% | **STRONG** |
| T4 Stalled Advantage | lead ≥ p75 of positive lead@econ (Std 8,271; Turbo 11,432) for ≥10 / 6 min with ≤2 enemy structures | 99.7% | 1.6% | 1.6% | | none | T3 59% | **TOO RARE** |
| T5 Clash → Structures | lopsided clash (death margin ≥2) followed by ≥4 of loser's structures within 90 s, excluding last 3 min | 100% | 51.7% (≥3) | 35.4% (strong ≥6: 12.2%) | | none | T6 77% of T6 | **TOO COMMON / NEEDS TUNING** |
| **T6 Structures Lost While You Were Dead** | max towers/barracks of own side lost inside one `[death, death+timeDead]`, excluding last 3 min; ≥4 | 100% (viewpoints) | 21.2% (≥3) | **10.3%** (strong ≥6: 2.8%) | C 11.7 / M 10.9 / O 11.2 / S 8.9; wins 3.2 / losses 17.5 | none | T5 77% | **STRONG BUT SITUATIONAL** |
| T7 Objective-Heavy Turn | T1 tuned and ≥3 structures in window | 99.8% | 24.9% | 10.1% | | none | T1 99% | **REDUNDANT** (slot of T1) |
| T8 Death-Heavy Turn | T1 tuned and death margin ≥6 | 99.8% | 24.8% | 10.0% | | none | T1 98% | **REDUNDANT** (slot of T1) |
| T9 Tormentor in Turn | Tormentor chat time inside tuned T1 window | 92.6% | 8.7% | 0.6% | | none | T1 | **TOO RARE** |

### 4.2 Distributions

| Measure | Standard | Turbo |
|---|---:|---:|
| Normalized swing p75 / p90 / p95 | 14.7% / 17.4% / — | 15.4% / 19.0% / — |
| Units with a sustained flip whose new run starts after lane end (T2 raw, both buckets combined) | 36.1% | 36.1% |
| Flip min-peak p50 / p75 | 5.1k / 7.9k | 9.0k / 14.2k |
| Comeback deficit (winners) p75 / p90 | 6,180 / 12,263 | 8,990 / 18,332 |
| T1 tuned shapes | LEAD_EXTENDED / DEFICIT_DEEPENED 43 each, FLIPPED 4 each, SWUNG 2 each | 33 each, FLIPPED 6 each, SWUNG 2 each |
| Structures while dead (single death, excl. last 3 min) ≥3 / ≥4 / ≥5 | 22% / 11% / 6% | 20% / 10% / 4% |
| Lopsided clash → own side lost ≥3 / ≥4 / ≥5 structures in 90 s (excl. last 3 min) | 27% / 17% / 10% | 29% / 20% / 12% |

### 4.3 Real examples

- `[GAME_FLIPPED_AGAINST] peak +31,006 (4:00–29:00) → -48,138 (30:00–41:00)` — Standard Support Invoker, loss.
- `[GAME_FLIPPED_FOR] peak -16,143 (6:00–20:00) → +51,284 (23:00–29:00)` — Turbo Support Earthshaker, win.
- `[COMEBACK_WIN] trailed by 13,095` — Standard Carry Luna.
- `[LOST_FROM_AHEAD] led by 30,990` — Standard Carry Faceless Void.
- `[STRUCTURES_WHILE_DEAD] died 26:48, dead 75s, 6 towers/barracks lost meanwhile` — Turbo Offlane Earthshaker.
- `[STALLED_ADVANTAGE] lead ≥8,271 for 18 min (40:00–57:00, peak +14,222); enemy structures taken 0` — Standard Mid Lion.
- T1 boring case: `[DEFICIT_DEEPENED] 10:00–15:00 lead -21,432 → -60,230` — a Turbo stomp getting worse.
- T1 good case: `[FLIPPED_AGAINST] 28:00–36:00 lead +25,895 → -48,138; 5 structures`.

### 4.4 Failure cases

- **T1 selects the snowball window in one-sided games.** Unless restricted to flip/evaporation/erasure shapes, it tells stomp players what they already know. Restricted to those shapes, it becomes a near-duplicate of T2.
- **T5 fires in a third of matches** because high-ground pushes follow won fights. Even ≥6 structures (12%) is mostly the end-game sequence.
- **T6 in long games:** late deaths with 100 s timers routinely span a tower. It is still personal, but loss-skewed and potentially blame-adjacent; only temporal wording is allowed.
- **Mirror symmetry:** T2/T3 fire for both teams of the same match (comeback for one side, lost lead for the other). Unit rates are per team.
- **Late-game gold swings** reach 70k+ in long games; absolute gold values need context (percent of total NW).

### 4.5 Recommended Turning Point pool

| Candidate | Frequency | Comment |
|---|---|---|
| **T3 Comeback / Lost Lead** | ~10% | Cleanest; outcome-anchored |
| **T2 Sustained Lead Flip** | ~11% | Timeline story; merges naturally with T3 (53%) |
| **T6 Structures Lost While You Were Dead** | ~10% of viewpoints (17.5% of losses) | Personal; distinct from T2/T3 (5% overlap) |
| T1 Turn Window restricted to FLIPPED / LEAD_EVAPORATED / DEFICIT_ERASED | ~1–2% beyond T2 | Optional; mostly a T2 variant |
| T4 Stalled Advantage | 1.6% | Good story, likely too rare for V1 |

---

## 5. Family 3 — Hidden Enemy Activity

### 5.1 Results (team units)

| Candidate | Calculation | Eligibility | Raw fire | Tuned fire | Coverage | History need | Redundancy | Verdict |
|---|---|---|---:|---:|---|---|---|---|
| **H1 Enemy Stacking Edge** | enemy stacks by checkpoint ≥ p90 (Std 7) and edge ≥ p90 (Std 4) | 99.8% | 27.5% | **8.1%** (Std 8.7 / Turbo 7.5) | Turbo with meaningful floor ≥5: 1.5% | optional (bucket; record 3.3% of available; availability 80.7%, steady 93%) | H8 14% | **STRONG** (Standard) / **TOO RARE** (Turbo) |
| H2 Enemy Vision (count-based) | enemy observers ≥ p90 or our observers destroyed ≥ p90 | 100% | 21.9% | 20.4% | | bucket | H9 | **TOO COMMON / duration-biased** (count corr with duration 0.87) |
| **H2r-a Our Vision Cleared** | own observers ≥8; share destroyed ≥ p75; destroyed per 10 min ≥ p90 | 100% | — | **10.1% / 9.2%** | | bucket | | **STRONG** |
| **H2r-b Enemy Barely Warded** | enemy observers per 10 min ≤ p10 (Std 3.32; Turbo 2.66) | 100% | — | **10.2% / 10.1%** | | bucket | | **STRONG BUT SITUATIONAL** |
| H2r-c Heavy Enemy Vision (rate) | enemy observer rate ≥ p90 | 100% | — | 10.1% | p50 4.23 vs p90 4.69 per 10 min | | | **TOO COMMON / BORING** (stock-capped) |
| **H3 Enemy Smoke Volume (rate)** | smokes per 10 min ≥ p90, ≥4 (Std) / ≥3 (Turbo), and ≥ own + 2 | 100% | 28.0% (count p75) | **6.0% / 8.0%** | count version 10.8% (duration corr 0.31) | bucket (record 2.0%) | H4 12% | **STRONG** |
| H4 Smoke → Kills | enemy smokes followed by an enemy kill ≤60 s: ≥3 and ≥50% | 1.9% (playback) | 76.5% | 50% of eligible (17 units) | | none | H3 | **STRONG BUT SITUATIONAL / TECHNICALLY WEAK** (playback availability) |
| **H5 Enemy Boss Control** | enemy Roshan ≥2 with ours 0, or Roshan+Tormentor ≥3 with ours 0 | 100% | 34.1% | **8.2%** (Std 9.3 / Turbo 7.0) | wins 3.6 / losses 12.9 | bucket | T3 19% | **STRONG** |
| **H6 Enemy Early-Rich Hero** | fastest enemy hero to NW goal ≤ p10 (Std 18 min to 10k; Turbo 12 min to 15k) and ≥3 min before your team's first | 97.6% | 13.0% | **9.3%** (Std 10.0 / Turbo 8.3) | wins 4.7 / losses 13.6 | bucket (record 2.2%) | H7 52% of H7; I3 41% of H6 | **STRONG** |
| H7 Enemy Economy Concentration | enemy top share of team NW ≥ p90 (31.4%) and ≥ own top + 5 pp | 99.9% | 10.1% | 5.8% | | none | H6 52% | **REDUNDANT** |
| H8 Enemy Core Jungle Reliance | richest enemy core's neutral+ancient share of report creep gold ≥ p90 and ≥45% | 99.9% | 10.1% | 8.9% | | none | H1 13% | **TECHNICALLY WEAK** (partial farm report; odd picks) |
| H9 Short-Lived Observers | ≥4 own observers destroyed ≤90 s after placement and ≥25% | 1.9% (playback) | 41.2% | 14.7% of eligible (5 units) | | none | H2 | **TECHNICALLY WEAK** (playback) |
| H10 Hidden Activity Stack | ≥2 of H1, H2, H3, H5, H8 tuned | 100% | 11.5% | 11.5% (≥3: 1.5%) | | none | members | **NEEDS TUNING** (meta signal for ranking, not a card) |

### 5.2 Distributions and thresholds

| Measure | Standard | Turbo |
|---|---:|---:|
| Enemy stacks by checkpoint p50 / p75 / p90 / p95 | 3 / 5 / 7 / 9 (by 20:00) | 1 / 2 / 3 / 4 (by 15:00) |
| Stack edge (enemy − own) p90 | 4 | 2 |
| Enemy observers per 10 min p10 / p50 / p90 | 3.32 / 4.23 / 4.69 | 2.66 / 4.03 / 4.82 |
| Our observers destroyed p90 (count) / share p75 | 9 / 37% | 5 / 40% |
| Enemy smokes per 10 min p90 | 1.60 | 1.65 |
| Enemy fastest to NW goal p10 | 18 min (10k) | 12 min (15k) |
| Enemy top-hero NW share p90 | 31.4% | 31.5% |
| Enemy Roshan ≥1 and ours 0 | 31.6% of units | 27.1% |

### 5.3 Real examples

- `[ENEMY_STACKED_MORE] enemy 19 vs your team 3 camps stacked by 20:00` — Standard Support Rubick, loss.
- History: `acct0 STA offlane: enemy stacks 15 vs prior n=82, median 4, previous max 11`.
- `OUR_VISION_CLEARED: 34m — they destroyed 9 of your team's 11 observers`.
- `ENEMY_BARELY_WARDED: 44m — enemy placed 5 observers (1.1/10m); yours 21`.
- `[ENEMY_SMOKE_HEAVY] enemy used Smoke 8 times (your team 2)` — Standard Support Zeus.
- `[SMOKES_INTO_KILLS] 8 of 11 enemy smokes were followed by an enemy kill within 60s` — Standard (playback).
- `[BOSSES] enemy Roshan 2 vs yours 0; Tormentor 3 vs 0` — Standard Mid Void Spirit, loss.
- `[ENEMY_EARLY_RICH] Lina (P2) reached 15,000 NW at 8:00; your team's first at 17:00` — Turbo.
- History: `acct0 STA mid: Necrophos reached 10k at 18:00 vs prior n=34, median 21:00, previous fastest 19:00`.

### 5.4 Failure cases

- **Count-based vision and smoke candidates select long games:** 90-minute matches fill the extremes. Per-10-minute rates remove this (corr 0.01 / −0.01).
- **Heavy enemy vision** is capped by observer stock, so p90 differs from median by ~10%.
- **Turbo stacks are near zero**; any Turbo stacking card is trivia ("3 vs 1").
- **H5/H6 are loss-skewed (13% of losses vs 4% of wins)**; they can read as explanation. Only factual counts and timings are allowed.
- **H8 relies on a partial farm report** and sometimes names an unexpected "richest core" (e.g. Ogre Magi at 70%).
- **H4/H9 need playback,** which was unavailable during this run.

### 5.5 Recommended Hidden Enemy pool

| Candidate | Frequency | Comment |
|---|---|---|
| **H1 Enemy Stacking Edge** (Standard only) | ~9% of Standard | Classic "invisible work" |
| **H2r-a Our Vision Cleared** | ~10% | Replaces count-based vision |
| **H2r-b Enemy Barely Warded** | ~10% | Counter-intuitive, rarely noticed |
| **H3 Enemy Smoke Volume (rate)** | 6–8% | Upgrade to H4 when playback exists |
| **H5 Enemy Boss Control** | ~8% | High clarity |
| **H6 Enemy Early-Rich Hero** | ~9% | Absorbs H7 as a slot |
| H4 Smoke → Kills (optional enrichment) | playback only | Strong examples; availability unreliable |

---

## 6. Family 4 — Item Execution & Power Spikes

### 6.1 Results

| Candidate | Calculation | Eligibility | Raw fire | Tuned fire | Coverage | History need | Redundancy | Verdict |
|---|---|---|---:|---:|---|---|---|---|
| I1 Unused Active Item | active item bought, `itemUsed` 0, in main inventory at end, held ≥10 min (Std) / ≥6 min (Turbo) | 93.8% | 24.3% | 1.9% (Std 0.8 / Turbo 3.2); excl. Mjollnir 1.2% | C 2.7 / M 2.7 / O 1.5 / S 1.3 | none | I2 6% | **TOO RARE** (raw version misleading) |
| I2 Activation Rate Extreme | uses per 10 min held (≥15 min) ≤ item p10 (and ≤2 uses) or ≥ item p95 | 41.6% | 8.9% | 8.9% (HIGH 270, LOW 57) | | none | I1 | **REJECT** (HIGH trivial: "Tinker Blink 105×"; LOW 0.6%) |
| **I3 Enemy Core Early Key Item** | enemy P1–P3 first purchase of a spike item (BKB, Blink, Radiance, Midas, Manta, Desolator, BFury, Maelstrom, Aghanim's, Orchid) ≤ core p5 for that item | 99.3% | 32.4% (≤ p10) | **18.2%** (strong: BKB/Blink/Radiance/BFury/Manta 11.1%) | wins 14.7 / losses 21.6 | optional (bucket; earliest enemy BKB record 4.0% of available; availability 75.3%) | H6 20% of I3; I5 14% | **STRONG** |
| I4 Lane Item Race (unrestricted) | earliest common key item of user and counterpart, gap ≥ p90 | 32.1% | 25.2% | 10.8% | cores | none | | **REJECT** (absurd extremes: 90:18 vs 11:14) |
| I4r Lane Item Race (restricted) | same item among both players' first two key items, both before 35 / 20 min, gap ≥ p90 (Std 672 s, Turbo 407 s) | 14.8% / 17.3% of cores | — | 1.5% / 1.7% of cores | cores | none | L1 8% | **TOO RARE** |
| I5 Enemy Spike Cluster | earliest ≥3 enemy core big items (≥4,000 cost) by ≥2 heroes within 4 min, at ≤ p10 time (Std 21:26, Turbo 8:36) | 100% | 80.0% | 8.2% | | none | I3 31% of I5 | **TOO COMMON / BORING** (raw) — weak when tuned |
| I6 Enemy Spike Before Turn | enemy big item in [window−3 min, window+1 min] of tuned adverse T1 window | 5.1% | 70.0% (control window 19%) | 70.0% | | none | T1 100% | **REDUNDANT** (enrichment slot) |
| I7 First Activation Delay | first use of a key active item ≥7 min after purchase | 1.5% (playback) | 20.1% | 5.2% (7 cases) | | none | I1 | **TECHNICALLY WEAK** (playback) |
| **I8 Own Key Item Timing vs History** | user's first purchase time of a spike item is earliest or latest among ≥10 prior purchases of that item (bucket) | 56.4% of key-item purchases have ≥10 prior (≥5: 72.1%) | — | **early record 4.8%, late record 5.2% of available** | all | required | | **STRONG BUT SITUATIONAL** |

### 6.2 Distributions and thresholds

**Active item non-use.** P(uses == 0 | in main inventory at end, held ≥ H):

| H (min) | 1 | 3 | 5 | 8 | 10 | 15 | 20 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Standard | 2.7% | 1.6% | 1.1% | 0.6% | 0.5% | 0.2% | 0.2% |
| Turbo | 5.4% | 3.1% | 2.2% | 1.6% | 1.2% | 0.7% | 1.0% |

By item (Standard, held ≥10 min): Mjollnir 11/142 unused; BKB 5/781; Manta 2/429; Blade Mail 2/297.

**Enemy core key item p5 / p10:**

| Item | Standard p5 | Standard p10 | Turbo p5 | Turbo p10 |
|---|---|---|---|---|
| BKB | 21:28 | 22:57 | 10:39 | 11:36 |
| Blink | 9:53 | 10:40 | 4:27 | 4:59 |
| Radiance | 13:46 | 14:37 | 6:31 | 6:55 |
| Hand of Midas | 6:04 | 6:52 | 2:52 | 3:20 |
| Manta | 15:36 | 16:46 | 7:42 | 8:24 |
| Desolator | 13:58 | 15:37 | 6:29 | 6:45 |
| Battle Fury | 12:01 | 12:54 | 5:48 | 6:22 |
| Maelstrom | 11:09 | 11:59 | 5:07 | 5:35 |
| Aghanim's Scepter | 16:05 | 17:56 | 7:25 | 8:06 |
| Orchid | 12:41 | 13:35 | 6:03 | 6:45 |

### 6.3 Real examples

- `[ENEMY_EARLY_ITEM] Dawnbreaker (P3) black_king_bar at 17:31 (core p5 21:28)` — Standard Mid Storm Spirit, loss.
- `[ENEMY_EARLY_ITEM] Phantom Assassin (P1) desolator at 6:19 (core p5 6:29)` — Turbo.
- History: `acct0 STA support: Sven BKB at 18:38 vs prior n=39 earliest enemy BKB median 28:11, previous earliest 20:56`.
- `I8: acct0 STA Death Prophet Aghanim's at 16:08 vs prior n=24, your previous best 19:03, median 26:37`.
- I1 misleading: `item_mjollnir bought 40:29, in inventory at end, uses 0`.
- I1 genuine: `item_cyclone bought 16:46, in inventory at end (43 min), uses 0` — Standard Mid Venomancer.
- I2 trivial: `item_blink held 39.2 min, activated 105x`.
- I4 absurd: `blink: you 11:14 vs Tiny 90:18`.
- I7 (playback): `item_manta bought 17:47, first used 28:01`.

### 6.4 Failure cases

- **Item upgrades** (Force Staff → Hurricane Pike, Mekansm → Greaves, Eul's → Wind Waker, Shadow Blade → Silver Edge) made the raw "never used" rule fire in 24% of viewpoints. The "still in main inventory at end" requirement is mandatory.
- **Passive-value active items** (Mjollnir) must be excluded or the card misleads.
- **`inventoryReport` is empty in the current patch,** so held time can only be approximated as purchase → match end for items in the final inventory.
- **I3 is loss-skewed** (21.6% of losses) and can be read as explanation; timing facts only.
- **I8 history is item-specific;** users who rarely buy the same item get nothing.

### 6.5 Recommended Item pool

| Candidate | Frequency | Comment |
|---|---|---|
| **I3 Enemy Core Early Key Item** | ~18% (strong subset ~11%) | The family's anchor |
| **I8 Own Key Item Timing vs History** | ~10% of eligible purchases | Personal; history-gated |
| I1 Unused Active Item (strict, excl. Mjollnir) | ~1.2% | Rare "delight" only if the owner accepts rarity |
| I7 First Activation Delay | playback only | Defer |

**Honest assessment:** this family is the weakest of the four. Its value rests on two candidates, and the execution half ("did I use my tools?") did not survive real data.

---

## 7. Cross-Candidate Overlap Matrix

P(B | A) = share of A's tuned firings where B also fired (viewpoint level).

| A | B | n(A) | n(B) | both | P(B\|A) | P(A\|B) | Reading |
|---|---|---:|---:|---:|---:|---:|---|
| T1 Turn Window | T7 Objective-Heavy | 900 | 890 | 890 | 0.99 | 1.00 | Same story → merge |
| T1 Turn Window | T8 Death-Heavy | 900 | 880 | 880 | 0.98 | 1.00 | Same story → merge |
| I6 Spike Before Turn | T1 | 315 | 900 | 315 | 1.00 | 0.35 | Enrichment of T1 |
| T2 Lead Flip | T3 Comeback/Lost | 940 | 900 | 480 | 0.51 | 0.53 | Strongly related; combinable |
| T5 Clash → Structures | T6 While Dead | 3,140 | 917 | 705 | 0.22 | 0.77 | T6 is mostly inside T5 |
| L1 Lane Path | L7 Death Trade | 956 | 1,490 | 402 | 0.42 | 0.27 | L7 as L1 slot |
| L1 behind shapes | L5 Strong opponent | 436 | — | 243 | 0.56 | — | Natural combination |
| L1 Lane Path | L5 Extreme Start (all) | 956 | 920 | 259 | 0.27 | 0.28 | Related, distinct |
| L1 Lane Path | L4 Level-6 | 956 | 542 | 200 | 0.21 | 0.37 | Partial |
| L1 Lane Path | L3 CS-vs-Gold | 956 | 122 | 8 | 0.01 | 0.07 | Distinct |
| L1 Lane Path | L8 Support Pair | 956 | 326 | 120 | 0.13 | 0.37 | Supports: choose one |
| H6 Early-Rich | H7 Concentration | 800 | 510 | 265 | 0.33 | 0.52 | H7 → H6 slot |
| H6 Early-Rich | I3 Enemy Early Item | 800 | 1,600 | 325 | 0.41 | 0.20 | Cross-family related |
| H5 Bosses | T3 Comeback/Lost | 730 | 900 | 140 | 0.19 | 0.16 | Distinct |
| H1 Stacking | H8 Jungle | 720 | 790 | 100 | 0.14 | 0.13 | Distinct |
| H3 Smokes | H4 Smoke → Kills | 960 | 85 | 10 | 0.01 | 0.12 | Different subsets (playback) |
| I3 Enemy Early Item | I5 Cluster | 1,600 | 725 | 225 | 0.14 | 0.31 | Weakly related |
| T1 Turn Window | T3 Comeback/Lost | 900 | 900 | 40 | 0.04 | 0.04 | T1 ≠ comeback (mostly stomps) |
| T1 Turn Window | T6 While Dead | 900 | 917 | 46 | 0.05 | 0.05 | Distinct |
| L5 Extreme Start | H6 Early-Rich | 920 | 800 | 163 | 0.18 | 0.20 | Cross-family related |
| I4 Lane Item Race | L1 Lane Path | 308 | 956 | 26 | 0.08 | 0.03 | Distinct |

Full pairwise co-fire (lift and conditional probabilities) is in `candidate-examples.json → cofire`.

**Stories that are effectively the same:** T1 / T7 / T8 / I6 (one window); T2 / T3 (half the time); T5 ⊃ T6 (most T6 cases occur alongside a clash conversion, but T6 is personal); H6 / H7; L1 / L7.

---

## 8. Frequency Distribution

| Candidate | Unit | Eligible % | Raw fire % | Tuned fire % | Strong-output % | Standard | Turbo | Playback? | History? |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| L1 Lane Lead Path | viewpoint | 98.6 | 59.7 | 10.9 | 6.0 | 10.9 | 11.0 | No | No |
| L2 Sustained Lane Flip | viewpoint | 98.6 | 1.0 | 0.8 | 0.1 | 1.2 | 0.3 | No | No |
| L3 CS-vs-Gold Split | viewpoint | 59.9 | 12.1 | 2.3 | 0.7 | 1.7 | 3.1 | No | No |
| L4 Level-6 Race | viewpoint | 59.9 | 37.8 | 10.2 | 3.5 | 10.2 | 10.2 | No | No |
| L5 Counterpart Extreme | viewpoint | 98.6 | 21.2 | 10.5 | 5.4 | 10.5 | 10.6 | No | Optional |
| L6 Own Lane vs Usual | viewpoint | 47.8* | — | 9.0* | — | — | — | No | **Yes** |
| L7 Lane Death Trade | viewpoint | 98.6 | 39.8 | 17.1 | 6.7 | 15.4 | 19.0 | No | No |
| L8 Support Lane Pair | viewpoint | 38.2 | 34.9 | 9.6 | 3.5 | 9.9 | 9.3 | No | No |
| T1 Turn Window | team | 99.8 | 25.1 | 10.2 | 5.2 | 10.1 | 10.2 | No | No |
| T2 Lead Flip | team | 99.8 | 36.1 | 10.6 | 4.6 | 9.9 | 11.5 | No | No |
| T3 Comeback / Lost Lead | team | 100 | 25.2 | 10.2 | 5.2 | 10.1 | 10.2 | No | No |
| T4 Stalled Advantage | team | 99.7 | 1.6 | 1.6 | 0.6 | 1.7 | 1.6 | No | No |
| T5 Clash → Structures | team | 100 | 51.7 | 35.4 | 12.2 | 33.5 | 37.8 | No | No |
| T6 Structures While Dead | viewpoint | 100 | 21.2 | 10.3 | 2.8 | 11.0 | 9.5 | No | No |
| T7 Objective-Heavy Turn | team | 99.8 | 24.9 | 10.1 | 5.2 | 9.9 | 10.2 | No | No |
| T8 Death-Heavy Turn | team | 99.8 | 24.8 | 10.0 | 4.8 | 9.9 | 10.0 | No | No |
| T9 Tormentor in Turn | team | 92.6 | 8.7 | 0.6 | 0.2 | 1.1 | 0.0 | No | No |
| H1 Enemy Stacking | team | 99.8 | 27.5 | 8.1 | 4.9 | 8.7 | 7.5† | No | Optional |
| H2 Vision (count) | team | 100 | 21.9 | 20.4 | 7.8 | 17.8 | 23.6 | No | Optional |
| H2r-a Our Vision Cleared | team | 100 | — | ~9.7 | — | 10.1 | 9.2 | No | Optional |
| H2r-b Enemy Barely Warded | team | 100 | — | ~10.2 | — | 10.2 | 10.1 | No | Optional |
| H3 Smokes (count / rate) | team | 100 | 28.0 | 10.8 / 7.0 | 3.6 | 9.9 / 6.0 | 11.9 / 8.0 | No | Optional |
| H4 Smoke → Kills | team | 1.9 | 76.5 | 50.0‡ | 26.5‡ | 68.8‡ | 33.3‡ | **Yes** | No |
| H5 Enemy Boss Control | team | 100 | 34.1 | 8.2 | 1.4 | 9.3 | 7.0 | No | Optional |
| H6 Enemy Early-Rich Hero | team | 97.6 | 13.0 | 9.3 | 5.3 | 10.0 | 8.3 | No | Optional |
| H7 Economy Concentration | team | 99.9 | 10.1 | 5.8 | 2.6 | 5.1 | 6.6 | No | No |
| H8 Core Jungle Reliance | team | 99.9 | 10.1 | 8.9 | 4.3 | 8.0 | 10.1 | No | No |
| H9 Short-Lived Observers | team | 1.9 | 41.2 | 14.7‡ | 8.8‡ | 18.8‡ | 11.1‡ | **Yes** | No |
| H10 Hidden Activity Stack | team | 100 | 11.5 | 11.5 | 1.5 | 11.0 | 12.1 | No | No |
| I1 Unused Active Item | viewpoint | 93.8 | 24.3 | 1.9 | 1.2 | 0.8 | 3.2 | No | No |
| I2 Activation Rate Extreme | viewpoint | 41.6 | 8.9 | 8.9 | 0.2 | 9.0 | 8.7 | No | No |
| I3 Enemy Early Key Item | team | 99.3 | 32.4 | 18.2 | 11.1 | 18.7 | 17.6 | No | Optional |
| I4 Lane Item Race (unrestricted / restricted) | viewpoint | 32.1 / ~16 | 25.2 | 10.8 / ~1.6 | 3.4 | 11.2 / 1.5 | 10.5 / 1.7 | No | No |
| I5 Enemy Spike Cluster | team | 100 | 80.0 | 8.2 | 4.5 | 7.0 | 9.6 | No | No |
| I6 Spike Before Turn | team | 5.1 | 70.0 | 70.0 | 43.3 | 49.0 | 95.1 | No | No |
| I7 First Activation Delay | viewpoint | 1.5 | 20.1 | 5.2‡ | 2.2‡ | 7.4‡ | 3.0‡ | **Yes** | No |
| I8 Own Item Timing vs History | purchase | 56.4* | — | ~10* | — | — | — | No | **Yes** |

\* Share of evaluations with ≥10 prior comparators, and fire rate among those.
† Turbo tuned rule is trivial (3 vs 1); with a floor of ≥5 stacks and a ≥4 edge: 1.5%.
‡ Small playback sample (5–17 firings).

**Frequency bands (tuned rules):**

| Band | Candidates |
|---|---|
| Almost every match (>50%) | I5 raw (80%), L1 raw shapes (60%), T5 raw (52%) — descriptive noise |
| ~30–50% | T5 tuned (35%), T2 raw (any flip, 36%), L7 raw (40%), L4 raw (38%) |
| ~10–30% | H2 count (20%), I3 (18%), L7 (17%), H10 (11.5%), L1 (11%), H3 count (11%), T2 (10.6%), L5 (10.5%), T6 (10.3%), T1 (10.2%), T3 (10.2%), L4 (10.2%), H2r-a (~10%), H2r-b (~10%) |
| <10% | L8 (9.6% of supports), H6 (9.3%), H8 (8.9%), H5 (8.2%), H1 (8.1%), I5 tuned (8.2%), H3 rate (6–8%), H7 (5.8%), L3 (2.3%), I1 (1.9%), T4 (1.6%), I4r (1.6%) |
| Almost never (<1%) | L2 (0.8%), T9 (0.6%), I2 LOW (0.6%), Turbo stacking with floor (1.5% of Turbo) |

**Coverage of the recommended pools** (viewpoints, feeding guard applied; pool = L1, L5, L4, L3, L8 / T1, T2, T3, T6 / H1, H3, H5, H6 / I3):

| Family | Any tuned candidate | Standard | Turbo | Carry | Mid | Offlane | Support |
|---|---:|---:|---:|---:|---:|---:|---:|
| Lane | 24.8% | 24.7% | 24.9% | 26.2% | 27.5% | 25.2% | 22.5% |
| Turning | 31.5% | 31.6% | 31.3% | 32.5% | 31.9% | 32.1% | 30.4% |
| Hidden | 30.9% | 31.9% | 29.7% | 30.9% | 30.9% | 30.9% | 30.9% |
| Items | 17.9% | 18.3% | 17.4% | 17.9% | 17.9% | 17.9% | 17.9% |

Families with ≥1 firing per viewpoint: 0 → 32%, 1 → 39%, 2 → 22%, 3 → 6%, 4 → 1%. Adding H2r-a/H2r-b and the history-gated L6/I8 raises coverage; about a third of matches would still have no card from these pools. That is a product decision (§11).

---

## 9. Candidate Graveyard

| Candidate / variant | Status | Why |
|---|---|---|
| L2 Sustained Lane Flip | TOO RARE | 0.8% of viewpoints; flips mostly supports at ±400 gold |
| L1 flip shapes for supports | REJECT | ±300–400 gold "lost leads" are noise |
| L7 Lane Death Trade (headline) | REDUNDANT | 42% co-fire with L1; griefer extremes; keep as a slot |
| L4 Level-6 for Carry vs Offlane | NEEDS TUNING | Different XP roles; hero-aware rule needed |
| T1 Turn Window (unrestricted) | NEEDS TUNING | 84% of p90 windows are stomps extending |
| T1 early-window version (normalized by start NW) | REJECT | Picked minute 1–2 windows (tiny denominators) |
| T4 Stalled Advantage | TOO RARE | 1.6% |
| T5 Clash → Structures (≥2 / ≥3 / ≥4) | TOO COMMON | 84% / 52% / 35%; even excluding the last 3 minutes |
| T7 Objective-Heavy Turn | REDUNDANT | ~100% inside T1 |
| T8 Death-Heavy Turn | REDUNDANT | ~100% inside T1 |
| T9 Tormentor in Turn | TOO RARE | 0.6% |
| H2 count-based vision | TOO COMMON / MISLEADING | Duration correlation 0.87; long games dominate |
| H2r-c Heavy enemy vision (rate) | BORING | Observer stock caps placement rate |
| H3 count-based smokes | NEEDS TUNING → replaced by rate | Duration correlation 0.31 |
| H1 Turbo stacking | TOO RARE | ≥5 stacks with ≥4 edge: 1.5% |
| H7 Enemy Economy Concentration | REDUNDANT | 52% inside H6; 31–33% shares are unremarkable |
| H8 Enemy Core Jungle Reliance | TECHNICALLY WEAK | Partial farm report; odd richest-core picks |
| H9 Short-Lived Observers | TECHNICALLY WEAK | Playback-dependent; 5 cases |
| H10 Hidden Activity Stack (as a card) | NEEDS TUNING | Better as a ranking signal |
| I1 Unused Active Item (raw) | MISLEADING | Upgrades/sales counted as unused (24% raw) |
| I1 Unused Active Item (strict) | TOO RARE | 0.5% (Std) / 1.2% (Turbo) of held items; Mjollnir-dominated |
| I2 High activation rate | REJECT | Hero-mechanics trivia (Tinker Blink 105×) |
| I2 Low activation rate | TOO RARE | 0.6% |
| I4 Lane Item Race (unrestricted) | REJECT | Absurd comparisons (90:18 vs 11:14) |
| I4r Lane Item Race (restricted) | TOO RARE | 1.6% of cores |
| I5 Enemy Spike Cluster | TOO COMMON / BORING | 80% raw; decile-by-construction when tuned |
| I6 Spike Before Turn | REDUNDANT | 70% of adverse turns; enrichment slot only |
| I7 First Activation Delay | TECHNICALLY WEAK | Playback-dependent; 7 cases |
| Held-duration rules using `inventoryReport` | TECHNICALLY UNAVAILABLE | Empty in current patch |
| Any playback-required headline | TECHNICALLY WEAK (for now) | Playback returned null for all 90 requests on 2026-09-15 |

---

## 10. FINAL REVIEW TABLE

Frequency = tuned fire rate. Reliability = data and semantic confidence. Product value = surprise × personal relevance × explanatory power, judged from real examples.

### Lane Story

| Candidate | What it detects | Frequency | Reliability | Product value | Verdict |
|---|---|---|---|---|---|
| ★ **L1 Lane Lead Path** (cores) | Blowout / separation / flip vs actual counterpart at 5 and 10 (4 and 8 Turbo) | ~11% | High | High | STRONG |
| ★ **L5 Counterpart Extreme Start** | Opponent's lane-end CS/NW in the top decile for that position (+ personal record) | ~10.5% | High | High | STRONG |
| ★ **L8 Support Lane Pair** | Your 2v2 lane pair's NW gap at lane end | ~10% of supports | High | Medium–High | STRONG |
| ★ **L3 CS-vs-Gold Split** | Behind in last hits but ahead in gold (or reverse), with kill/death slots | 2.3% | High | Very high | STRONG BUT SITUATIONAL |
| ★ **L4 Level-6 Race** (Mid) | Level-6 gap beyond role p90 | ~10% | High | Medium | STRONG (Mid) |
| ★ **L6 Own Lane vs Usual** | Best/worst lane result among ≥10 prior | ~9% of users with history | High | High | STRONG BUT SITUATIONAL |
| L7 Lane Death Trade | Lopsided lane deaths | 17% | High (guard needed) | Medium | REDUNDANT (slot) |
| L2 Sustained Lane Flip | Minute a lane changed hands | 0.8% | High | Medium | TOO RARE |

### Match Turning Point

| Candidate | What it detects | Frequency | Reliability | Product value | Verdict |
|---|---|---|---|---|---|
| ★ **T3 Comeback / Lost Lead** | Won from ≥ p90 deficit / lost from ≥ p90 lead | ~10% | High | High | STRONG |
| ★ **T2 Sustained Lead Flip** | Game changed hands after laning with large leads both ways | ~11% | High | High | STRONG |
| ★ **T6 Structures While Dead** | ≥4 towers/barracks lost during one of your death timers | ~10% (17.5% of losses) | High | High (personal) | STRONG BUT SITUATIONAL |
| T1 Turn Window (flip shapes only) | Largest relative swing that flipped / erased / evaporated a lead | ~1–2% beyond T2 | High | Medium | NEEDS TUNING |
| T4 Stalled Advantage | Long big lead without structures | 1.6% | High | High | TOO RARE |
| T5 Clash → Structures | Buildings after a lopsided clash | 35% | Medium (heuristic) | Low (common) | TOO COMMON |
| T7 / T8 / T9 | Turn window variants | — | — | — | REDUNDANT / TOO RARE |

### Hidden Enemy Activity

| Candidate | What it detects | Frequency | Reliability | Product value | Verdict |
|---|---|---|---|---|---|
| ★ **H1 Enemy Stacking Edge** (Standard) | Enemy stacked ≥7 by 20:00 with ≥4 edge (+ personal record) | ~9% of Standard | High | High | STRONG |
| ★ **H2r-a Our Vision Cleared** | Unusual share and rate of your observers destroyed | ~10% | High | High | STRONG |
| ★ **H2r-b Enemy Barely Warded** | Enemy observer rate in the bottom decile | ~10% | High | Medium–High | STRONG BUT SITUATIONAL |
| ★ **H3 Enemy Smoke Volume (rate)** | Top-decile smoke rate and more than your team | 6–8% | High | High | STRONG |
| ★ **H5 Enemy Boss Control** | Enemy took ≥2 Roshans (or ≥3 bosses) and you took none | ~8% | High | High | STRONG |
| ★ **H6 Enemy Early-Rich Hero** | Enemy hero hit NW goal in the fastest decile, ≥3 min before your team | ~9% | High | High | STRONG |
| H4 Smoke → Kills | Enemy smokes followed by kills ≤60 s | playback only | High when present | Very high | STRONG BUT SITUATIONAL / TECHNICALLY WEAK |
| H7 Economy Concentration | Enemy top-hero NW share | 5.8% | High | Low | REDUNDANT |
| H8 Core Jungle Reliance | Richest enemy core's jungle share | 8.9% | Medium–Low | Medium | TECHNICALLY WEAK |
| H9 Short-Lived Observers | Your observers destroyed ≤90 s | playback only | High when present | High | TECHNICALLY WEAK |
| H10 Hidden Activity Stack | ≥2 hidden signals | 11.5% | High | Ranking signal | NEEDS TUNING |

### Item Execution & Power Spikes

| Candidate | What it detects | Frequency | Reliability | Product value | Verdict |
|---|---|---|---|---|---|
| ★ **I3 Enemy Core Early Key Item** | Enemy core's spike item ≤ p5 timing (+ personal record) | ~18% (strong subset ~11%) | High | High | STRONG |
| ★ **I8 Own Key Item Timing vs History** | Your fastest/slowest timing of an item among ≥10 prior | ~10% of eligible purchases | High | High | STRONG BUT SITUATIONAL |
| I1 Unused Active Item (strict) | Held active item never activated | ~1.2% | High | High when real | TOO RARE |
| I7 First Activation Delay | Long gap from purchase to first use | playback only | High when present | Medium | TECHNICALLY WEAK |
| I4r Lane Item Race | Same early key item much earlier/later than counterpart | 1.6% of cores | High | Medium | TOO RARE |
| I5 / I6 / I2 / I4 | Cluster, spike-before-turn, activation rates, unrestricted race | — | — | — | TOO COMMON / REDUNDANT / REJECT |

---

## 11. QUESTIONS FOR PRODUCT OWNER

1. **Lane Story has six strong shapes.** I recommend choosing **2–3**:
   - (a) **L1 Lane Lead Path** for cores plus **L8 Support Lane Pair** for supports — the backbone, with roughly equal role coverage (~10% each).
   - (b) **L5 Counterpart Extreme Start**, as a standalone or merged into L1 when you were behind (56% overlap). Merging makes "you lost the lane to an unusually strong opponent" one card but reduces total lane coverage.
   - (c) **L3 CS-vs-Gold Split** — rare (2–3%) but the most surprising lane card. Is a rare delight worth V1 complexity?
   - (d) **L4 Level-6 Race** — only convincing for Mid today. Accept Mid-only?
   - (e) **L6 Own Lane vs Usual** — needs ≥10 prior games in the same role and mode; about half of evaluations have that today. Include history-gated cards in V1?

2. **Turning Point has three strong shapes.** I recommend **2**:
   - (a) **T3 Comeback / Lost Lead** and **T2 Sustained Lead Flip** — either as two candidates or one merged "lead story" (they coincide half the time).
   - (b) **T6 Structures Lost While You Were Dead** — personal and distinct, but fires mainly in losses (17.5% vs 3.2% of wins). Comfortable surfacing it after losses?
   - (c) Should the "largest swing window" survive at all, given that unrestricted it mostly narrates stomps?

3. **Hidden Enemy Activity has six strong shapes plus one playback-dependent one.** I recommend **3–4**:
   - Stacking (Standard only), Our Vision Cleared, Enemy Barely Warded, Smoke Volume, Boss Control, Early-Rich Hero.
   - Accept that **stacking is Standard-only** (Turbo stacking is not meaningful)?
   - **Smoke → Kills** is the most compelling smoke card but needs playback, which returned null for every request today. Ship Smoke Volume only, or also build the playback upgrade as optional?

4. **Item Execution & Power Spikes is thin.** Only **I3 Enemy Core Early Key Item** and history-gated **I8 Own Key Item Timing** survived. The "did I use my tools?" half did not. Choose one:
   - (a) accept a two-candidate family (~18% coverage);
   - (b) keep **I1 Unused Active Item** as a rare (~1%) delight despite its rarity; or
   - (c) re-scope the family toward power-spike timing only.

5. **Coverage target.** With the recommended pools, about **one third of matches produce no card** in any family. Is "nothing notable" acceptable, or should lower-threshold (p80) variants exist as fallbacks, at the cost of surprise?

6. **Personal-history cards.** Records require ≥10 prior comparators. Enemy-team comparisons are available for ~81% of evaluations (93% at steady state); role-scoped lane comparisons for ~48% (71% steady state). Accept history cards appearing only for established users?

7. **Loss skew.** H5, H6, I3, and T6 fire 2–4× more often in losses. They are factual, but together they can feel like an explanation for losing. Balance by outcome at selection time, or show whatever fires?


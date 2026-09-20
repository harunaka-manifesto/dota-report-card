# Post-Match Tier B — Match Shape & Fallback Intelligence Validation V1

**Status:** Research validation. Section 13 is a **RECOMMENDATION FOR PRODUCT REVIEW — NOT YET SSOT**.
**Date:** 2026-09-15
**Primary inputs:** `post-match-deterministic-candidate-validation-v1.md`, `post-match-intelligence-deep-research-v2.md`, `post-match-candidate-validation-data/`
**Outputs:** `post-match-tier-b-validation-data/` — `tier-b-shape-definitions.json`, `tier-b-match-classifications.csv`, `tier-b-threshold-grid.csv`, `tier-b-review-examples.json`, `tier-b-overlap-with-tier-a.csv`, `tier-b-review-sheet.html` / `.md`, result JSONs, and `research-code/`.

**How to read the numbers.** Unless stated otherwise:
- A *match* is one team perspective of one match.
- A *viewpoint* is one of the ten players.
- *Tier-A-empty* means no candidate from the product Tier A pool fired for that viewpoint.

Review ratings come from one rater (this research model) applying a written rubric. They are not a panel of Dota players. The HTML review sheet lets you re-rate every example.

---

## 1. Executive Verdict

**Did the six-shape classifier work?** Yes, after one revision.

The first version (v1) was stable and exactly mirror-symmetric, but it failed the product review in two places:
- **CLOSE_THROUGHOUT was misleading in 38% of reviewed examples.** It was used as the "whatever is left" bucket, so games with a persistent 8–16k lead were called close.
- **About 20% of games got no shape at all.** Most were gradual or late separations, or small persistent leads.

The revised classifier (v2) keeps the six conceptual shapes and adds the following:
- **Phase-binned lead bands.** Relative leads shrink by 35–40% after minute 40 (Standard) or 26 (Turbo).
- **Gold confirmation** for erosion and recovery.
- **A positive CLOSE_THROUGHOUT rule.**
- **A second path each** for late separation and for a persistent small lead.
- **A seventh state, LEAD_SWAPPED** (2% of games), so every game gets exactly one label.
- **A never-displayed UNCLEAR fallback.**

On development and holdout data v2 has:
- 0 mirror inconsistencies across 1,094 matches;
- mean perturbation agreement of 0.95;
- 0% highly unstable labels.

**Which shapes survived?**

Review figures are pooled GOOD / ACCEPTABLE / BORING / MISLEADING ratings for candidates still valid under v2.

| Shape | Share of matches (dev / holdout) | Share of Tier-A-empty viewpoints | Review (pooled, v2-valid) | Verdict |
|---|---:|---:|---|---|
| EVEN_THEN_SEPARATED | 13.3% / 14.9% | 17.1% | 35 / 55 / 8 / 2 (n=49) | **STRONG** |
| LEAD_ERODED | 6.1% / 4.2% | 4.1% | 50 / 46 / 4 / 0 (n=26) | **STRONG BUT SITUATIONAL** — 75% of its viewpoints already have Tier A (T2/T3) |
| DEFICIT_RECOVERED | 4.4% / 7.3% | 2.1% | 27 / 67 / 7 / 0 (n=15) | **STRONG BUT SITUATIONAL** — 87% already have Tier A |
| ONE_SIDED | 17.1% / 15.7% | 16.9% | 2 / 0 / 98 / 0 (n=52) | **Keep as a classifier state; never display** (TOO COMMON / BORING) |
| STEADY_EDGE | 17.3% / 19.9% | 20.3% | 3 / 61 / 36 / 0 (n=61) | **NEEDS TUNING** — acceptable fallback at best |
| CLOSE_THROUGHOUT (v2 positive rule) | 13.2% / 13.8% | 14.6% | 60 / 35 / 2 / 2 (n=43) | **STRONG** (v1 fallback version: REJECT) |
| LEAD_SWAPPED (added) | 1.6% / 2.7% | 0.3% | 0 / 100 / 0 / 0 (n=2) | **TOO RARE in Tier-A-empty** (mostly Tier A T2) |
| UNCLEAR (fallback) | 20.9% / 19.9% | 20.1% | 100% BORING | Never displayed |

**Merge or split?**
- **Split STEADY_EDGE** into its two entry paths ("edge share" and "lean").
- **Merge late separation into EVEN_THEN_SEPARATED** (second path).
- **Merge prolonged parity / decided-late into CLOSE_THROUGHOUT** (an output slot).
- **Structures stay modifiers only.**

**What Tier B adds to Tier-A-empty matches.** Recommended display gate: score ≥ 45, excluding ONE_SIDED, UNCLEAR and rejected signals.

| Estimate | GOOD | ACCEPTABLE | Shown but BORING | Shown but MISLEADING | Nothing |
|---|---:|---:|---:|---:|---:|
| Model (all 2,902 Tier-A-empty viewpoints, per-kind review rates) | 24.1% | 31.0% | 5.7% | 0.5% | 38.7% |
| Direct check (fresh holdout sample, n=60) | 20.0% | 26.7% | 3.3% | 0.0% | 50.0% |

**Useful deterministic insight across all well-parsed matches.** Tier A 66.6%, plus Tier B GOOD/ACCEPTABLE 18.5 pp by the model (15.6 pp by the holdout check), gives **82–85%**. This assumes Tier A insights are useful, which the previous phase validated separately.

**What remains uncovered.** Roughly **13–17% of viewpoints** have nothing worth saying:
- UNCLEAR trajectories without a moderate signal;
- Turbo stomps too short for a post-lane window (SHORT_WINDOW, 9% of Turbo viewpoints);
- disproportionately supports (45% of their Tier-A-empty viewpoints get nothing) and wins (44%).

---

## 2. Corpus & Validation Design

| Item | Value |
|---|---|
| Eligible matches (from previous phase) | 886 (484 Standard, 402 Turbo); 18 feeding-guard matches excluded from fitting and evaluation, reported as an edge case |
| Evaluation population | 868 matches, 8,680 viewpoints, 1,736 team perspectives |
| **Development set** | 607 matches (thresholds fitted here only) |
| **Holdout set** | 261 matches (138 Standard / 123 Turbo): all matches of two complete tracked accounts (acct2 — 87, Standard-heavy; acct6 — 93, Turbo-heavy) plus 81 stratified random matches (mode × duration tercile × Radiant win) |
| **Independent older-patch sample (new)** | 14 STRATZ calls (lean query: net worth per minute, tower deaths, positions; 16 matches per call). 217 fetched, 208 eligible (8 abandon, 1 short). Patch 180 (174) / 181 (34), Sep–Dec 2025; 89 Standard / 119 Turbo. Ledger total now 410 calls. The token was read from the environment and never printed. |
| Patches in the current corpus | 182: 831 matches, 180: 32, 181: 5 |
| Post-lane window length p10 / p50 / p90 | Standard 19 / 31 / 47 min; Turbo 8 / 15 / 25 min |
| History availability | 779 tracked viewpoints; 628 (7.2%) have ≥10 prior matches in the same mode. **Tier B uses no history.** |
| Human review | Round v1: 396 items from dev + holdout. Per shape: 15 random stratified by mode × win/loss, 10 borderline, 10 strongest. Per signal: 10 random. Plus 60 random Tier-A-empty "best candidate" items. Round v2: 160 items from a **fresh holdout-only** sample sharing no match side with round v1. |

### Phase 1 — Tier A gate reconstruction

Pool used, playback excluded:
- **Lane:** L1 (cores), L8, L5, L3, L6 (history).
- **Turning:** T2 + T3 as one Lead Story, and T6.
- **Hidden:** H1 (Standard), H2r-a, H2r-b, H3 rate, H5, H6.
- **Items:** I3, I8 (history).

| Result | Value |
|---|---|
| **Tier-A-empty viewpoints** | **33.4%** (32.1% if L4 Level-6 Race is added as a sensitivity check) |
| By mode | Standard 31.9%, Turbo 35.3% |
| By role | Carry 32.7%, Mid 32.5%, Offlane 33.1%, Support 34.4% |
| By outcome | **Wins 41.8%**, losses 25.1% (Tier-A-empty is 62.5% wins) |
| Established history users | 30.7% vs 33.6% for everyone else |
| Team perspectives where all five viewpoints are empty | 16.7% |
| Viewpoints that only one candidate covers | I3 6.2%, H2r-b 4.4%, H2r-a 3.4%, L5 2.8%, T6 2.7%, H3r 2.7%, H5 2.2%, T2 2.0%, L1 1.6%, T3 1.3%, H1 1.3%, L8 1.0% |

**Why 33.4% and not ~32%.** The earlier 32% used a different pool: L1 for all roles, L4, T1, H1 in Turbo, and count-based H3. That pool had no H2r-a/b, L6 or I8. Removing L4 and T1 costs more coverage than adding the rate-based vision candidates gains. The history candidates (L6 0.4%, I8 0.8% of viewpoints) barely move the total because only tracked accounts have history.

Tier A thresholds are the previous phase's in-sample values and were not refitted. Tier B thresholds were fitted on the development set only.

---

## 3. Final Lead Normalization

### 3.1 Normalization

**Chosen:** R(t) = (team NW − enemy NW) / (team NW + enemy NW) at t:00. The opposite perspective is exactly −R, which is why mirror symmetry holds by construction.

Relative leads make modes comparable. The meaningful-edge band before minute 20 is 0.094 in Standard and 0.101 in Turbo.

### 3.2 Smoothing

| Smoothing | State changes per 10 window-minutes | Mean neighbour agreement (528-config grid) | Flip → LEAD_SWAPPED recall | Comeback shape recall |
|---|---:|---:|---:|---:|
| raw | 0.835 | 94.2% | 4.6% | 41.5% |
| **3-min median** | 0.486 | 94.9% | 7.7% | **44.6%** |
| 3-min mean | 0.490 | 95.0% | 7.7% | 43.1% |
| 5-min median | 0.378 | **95.5%** | 9.2% | 41.5% |

Flip recall counts Tier A T2 perspectives; comeback recall counts T3 perspectives; both at bands 50/70/90 and a 3-minute run.

**Why the 3-minute median won.** It removes 42% of raw flicker. The 5-minute median is marginally more stable (0.954 vs 0.952 in the finalists), but it blurs recoveries: DEFICIT_RECOVERED stable share falls from 76% to 56%. Smoothing is computed on R truncated at the window end, so the excluded final push cannot leak into the window.

### 3.3 Analysis window

- **Start:** Standard 10:00, Turbo 8:00.
- **End:** match end − 3 minutes.

Label agreement against the 3-minute exclusion:

| End exclusion | Agreement vs 3 min | Largest changes |
|---|---:|---|
| 0 min | 78.3% | CLOSE → EVEN_THEN_SEPARATED (37 matches: the final push manufactures a separation) |
| 2 min | 90.8% | Same pattern, smaller (13) |
| **3 min** | — | — |
| 5 min | 84.7% | ONE_SIDED → SHORT_WINDOW (17), EVEN_THEN_SEPARATED → CLOSE (15): deletes real late separations and Turbo games |

**Minimum window: 9 minutes.**

| Minimum window | SHORT_WINDOW share (dev) | Notes |
|---|---:|---|
| 6 min | 1.0% | — |
| **9 min** | 5.9% (Turbo 12.3%) | Chosen |
| 12 min | 15.0% | — |

Windows of 9–11 minutes already have the lowest confidence (0.895 vs 0.953 for 12–19 minutes), so shorter windows were not accepted.

### 3.4 Lead bands and phase bins

|R| distributions drift materially with game time (development data):

| Minute bin | Standard p50 / p70 / p90 | Turbo bin | Turbo p50 / p70 / p90 |
|---|---|---|---|
| 10–19 | 0.064 / 0.094 / 0.156 | 8–13 | 0.065 / 0.101 / 0.164 |
| 20–29 | 0.065 / 0.103 / 0.180 | 14–19 | 0.066 / 0.099 / 0.169 |
| 30–39 | 0.057 / 0.091 / 0.143 | 20–25 | 0.052 / 0.080 / 0.131 |
| 40+ | 0.041 / 0.064 / 0.107 | 26+ | 0.041 / 0.064 / 0.105 |

Late-game relative leads are 35–40% smaller because total net worth keeps growing. Thresholds are therefore looked up by absolute minute bin.

**Bands: CLOSE = p50, MEANINGFUL_EDGE = p70, STRONG_EDGE = p90** of |R| (development data, same mode, same phase bin).

**Grid results:**
- **Edge band:** p75 had the highest neighbour agreement (95.7%). But it pushed "no sustained edge" to 53–58% of matches and cut comeback shape recall from 44.6% to 38.5% (26.2% with phase bins). Rejected.
- **Close band:** p40 / p50 / p60 were indistinguishable (94.8 / 95.0 / 94.8%).
- **Strong band:** p85 and p90 gave identical labels. The strong band is only used in the ONE_SIDED clause, which is non-binding.

Frozen values:

| Mode | Phase bin (minutes) | CLOSE | MEANINGFUL_EDGE | STRONG_EDGE |
|---|---|---:|---:|---:|
| Standard | 10–19 | 0.0637 | 0.0943 | 0.1563 |
| Standard | 20–29 | 0.0653 | 0.1032 | 0.1803 |
| Standard | 30–39 | 0.0568 | 0.0914 | 0.1429 |
| Standard | 40+ | 0.0409 | 0.0641 | 0.1073 |
| Turbo | 8–13 | 0.0649 | 0.1008 | 0.1638 |
| Turbo | 14–19 | 0.0657 | 0.0994 | 0.1687 |
| Turbo | 20–25 | 0.0522 | 0.0798 | 0.1310 |
| Turbo | 26+ | 0.0407 | 0.0635 | 0.1054 |

### 3.5 Sustained runs and hysteresis

- **Run length:** a meaningful edge must hold for **≥3 consecutive smoothed minutes**. 2, 3 and 4 minutes were equivalent (neighbour agreement 94.9 / 94.8 / 95.0%), so the prompt's 3 was kept.
- **Hysteresis rejected.** Entering at p70 and staying while above p60 lowered stability (0.947 vs 0.952), inflated ONE_SIDED and STEADY_EDGE, and raised comeback contradictions from 7.7% to 10.8%.

### 3.6 Gold confirmation for erosion and recovery

Relative erosion alone labelled long games where the gold gap never shrank. Example: "their lead peaked at 15.6% at 45:00 and was 5.2% by 93:00", while the gold deficit only moved from 30.5k to 23.7k.

LEAD_ERODED and DEFICIT_RECOVERED now require:
- relative erosion ≥ 50%;
- **gold erosion ≥ 50% measured from the gold peak**;
- a gold peak of at least **5,000 (Standard) / 8,000 (Turbo)**.

This also fixed a rendering defect where the quoted "peak" was the relative peak rather than the gold peak. That defect caused 5 of 26 v1 LEAD_ERODED examples to read as misleading.

---

## 4. Shape-by-Shape Validation

General notes for every shape:
- **Stability** is the share of 34 perturbations returning the same label.
- **Mirror consistency** is 100% (0 mismatches in 1,094 matches, both perspectives).
- **Win/loss rates** over the full corpus are identical by construction, because every match contributes one winner and one loser perspective. Tier-A-empty rates are reported instead.
- **Duration** figures are the share of short / medium / long terciles in the full corpus.

### 4.1 EVEN_THEN_SEPARATED — STRONG

**Definition.** Either path qualifies.
- **Path 1 (thirds):**
  - the first third of the window is ≥65% CLOSE;
  - side s starts its first sustained edge at ≥30% of the window, with no earlier sustained edge by either side;
  - ≥60% of the final third is inside side-s runs;
  - no opposite sustained run afterwards.
- **Path 2 (transition, added for late separations):**
  - the window's first sustained run belongs to s and starts at ≥ max(30% of the window, 3 minutes);
  - ≥65% CLOSE before it;
  - ≥60% of the minutes after it are inside s runs, and at least 3 minutes remain;
  - no opposite sustained run.

| Metric | Value |
|---|---|
| Frequency | dev 13.3%, holdout 14.9%, old patch 13.9%; Tier-A-empty viewpoints 17.1% |
| Standard / Turbo (dev) | 16.6% / 9.4% |
| Tier-A-empty wins / losses | 16.3% / 18.6% |
| Duration short / medium / long | 11.3 / 15.4 / 14.9% (correlation 0.04) |
| Modifiers | STRUCTURE_ALIGNED 84% (uninformative); STRUCTURE_COUNTERTREND 4.9% |
| Stability | 0.947 |
| Review (pooled) | GOOD 35%, ACCEPTABLE 55%, BORING 8%, MISLEADING 2% (n=49) |
| Review (fresh holdout) | GOOD 50%, ACCEPTABLE 33%, BORING 17% (n=12) |

**Examples:**
- "Until 30:00 the net-worth gap stayed within 3.6k. From 33:00 the enemy held a sustained lead: 16.5k at 33:00, 25.2k at 37:00." (Standard loss, 40 min — GOOD)
- "Until 21:00 the net-worth gap stayed within 6.3k. From 24:00 your team held a sustained lead: 11.2k at 24:00, 37.8k at 36:00." (Standard win, 39 min — GOOD)

**Failures:**
- **Early-separating Turbo stomps.** "Until 11:00 … from 14:00 …" rated BORING.
- **v1 rendering bug.** v1 quoted the largest pre-separation gap up to the separation minute ("stayed small (largest 15.5k)"), which contradicted the lead at separation. v2 measures the gap only up to separation − 3 minutes.

### 4.2 LEAD_ERODED — STRONG BUT SITUATIONAL

**Definition.**
- A sustained +edge run starts in the first two thirds of the window.
- No sustained −edge run anywhere.
- Relative erosion ≥ 50%, gold erosion from the gold peak ≥ 50%, and gold peak ≥ 5k (Standard) / 8k (Turbo).

| Metric | Value |
|---|---|
| Frequency | dev 6.1%, holdout 4.2%, old patch 3.8%; Tier-A-empty 4.1% |
| Overlap with Tier A | Only 25% of its viewpoints are Tier-A-empty (T2 36%, T3 39%) |
| Standard / Turbo | 5.1% / 7.2% |
| Tier-A-empty wins / losses | 4.9% / 2.8% |
| Duration short / medium / long | 1.4 / 4.4 / 10.6% (correlation 0.20) — partly inherent, since a lead needs time to erode |
| Modifiers | NO_STRUCTURE_CONVERSION 10.8% |
| Stability | 0.955 |
| Review (pooled) | GOOD 50%, ACCEPTABLE 46%, BORING 4% (n=26) |

**Examples:**
- "Your team's lead peaked at 32.9k at 18:00 and was 2.7k by 34:00; the enemy never held a sustained lead." (Turbo win — GOOD)
- "Your team's lead peaked at 23.8k at 20:00 and was 9.3k by 31:00…" (Turbo win — GOOD)

**Failures:**
- **Small Turbo lane-end leads** ("peaked at 8.5k at 11:00") are BORING; the gold floor removes most of them.

### 4.3 DEFICIT_RECOVERED — STRONG BUT SITUATIONAL

**Definition.** The exact mirror of LEAD_ERODED, applied to the opponent's lead.

| Metric | Value |
|---|---|
| Frequency | dev 4.4%, holdout 7.3%; Tier-A-empty 2.1% |
| Overlap with Tier A | 13% of its viewpoints are Tier-A-empty (DEFICIT_RECOVERED co-occurs with H6 22%, I3 34%, H5 19%) |
| Tier-A-empty wins / losses | 1.4% / 3.1% |
| Modifiers | NO_STRUCTURE_CONVERSION 7.4% |
| Stability | 0.955 |
| Review (pooled) | GOOD 27%, ACCEPTABLE 67%, BORING 7% (n=15) |

**Example:** "The enemy's lead peaked at 42.9k at 25:00 and was 6.9k by 37:00; your team never held a sustained lead." (Turbo loss — GOOD)

### 4.4 ONE_SIDED — valid state, never displayed

**Definition.**
- Side s owns ≥70% of window minutes inside sustained runs.
- Its first run starts within the first 33% of the window.
- No opposite sustained run.
- A strong edge for ≥3 minutes, or ≥3 net structures.

| Metric | Value |
|---|---|
| Frequency | dev 17.1%, holdout 15.7%, old patch 21.6%; Tier-A-empty 16.9% |
| Standard / Turbo | 20.8% / 12.7% |
| Duration short / medium / long | **37.2 / 9.1 / 3.5%** (correlation −0.33): stomps end early, which is inherent |
| Stability | 0.966 |
| Review | BORING 98% (n=52) |

**Why it must exist.** It absorbs stomps that would otherwise turn into "turning points" or "steady edges". The share, first-edge and structure parameters barely move labels: 60–75% share changes ONE_SIDED by 2 pp, and the structure clause is non-binding. The single GOOD example came from its NO_STRUCTURE_CONVERSION enrichment: "the enemy led for 32 minutes (19:00–50:00) with no net tower/barracks change."

### 4.5 STEADY_EDGE — NEEDS TUNING

**Definition.** Either path qualifies.
- **Path 1:**
  - s owns ≥50% of window minutes inside sustained runs;
  - the first-half and second-half medians both favour s;
  - no opposite run.
- **Path 2 (lean, added):**
  - s is ahead in ≥80% of window minutes;
  - median(s·R) ≥ the median CLOSE threshold;
  - both half-medians favour s;
  - no opposite run.

| Metric | Value |
|---|---|
| Frequency | dev 17.3% (lean path 67%), holdout 19.9%; Tier-A-empty 20.3% |
| Tier-A-empty wins / losses | 20.8% / 19.4% |
| Duration short / medium / long | 21.2 / 22.7 / 10.4% |
| Stability | 0.964 |
| Review | GOOD 3%, ACCEPTABLE 61%, BORING 36% (n=61) |

**Example:** "Your team was ahead in net worth for 100% of 10:00–34:00 and the enemy never held a clear lead for 3 straight minutes (largest lead 13.2k at 26:00)." (ACCEPTABLE)

**Failure:** big-lead Turbo games that just miss ONE_SIDED ("largest lead 25.5k") are BORING. It absorbs the persistent-lead games that made v1 CLOSE_THROUGHOUT misleading, which is its main value.

### 4.6 CLOSE_THROUGHOUT — STRONG (positive rule)

**Definition.**
- No sustained edge run by either side.
- CLOSE share ≥60% of window minutes.
- The largest gap held for 3 straight minutes, in either direction, is < 7,500 gold.

**Why a positive rule.** As a fallback, v1 was 38% MISLEADING (n=52). All 16 misleading v1 examples had either close share < 0.6 or a sustained gap ≥ 7.5k. The rule was calibrated on that review and **then validated on the fresh holdout sample**: 8 GOOD, 3 ACCEPTABLE, 1 MISLEADING out of 12.

| Metric | Value |
|---|---|
| Frequency | dev 13.2%, holdout 13.8%, old patch 10.1%; Tier-A-empty 14.6% |
| Tier-A-empty wins / losses | 14.1% / 15.3% |
| Duration short / medium / long | 7.8 / 19.2 / 13.1% (correlation 0.01) |
| Stability | 0.940, the lowest; the CT gold ±1,000 perturbation moves it most |
| Review (pooled) | GOOD 60%, ACCEPTABLE 35%, BORING 2%, MISLEADING 2% (n=43) |

**Diagnostic output slots:**
- close_share;
- max 3-minute gap (gold);
- latest close minute;
- first meaningful edge minute (always none);
- nontrivial lead changes.

**Examples:**
- "Between 10:00 and 55:00 the net-worth gap never stayed above 6.5k for 3 straight minutes. The game was still close at 55:00." (Standard loss, 58 min — GOOD)
- "Between 10:00 and 50:00 … never stayed above 6.3k … still close at 50:00." (Standard win, 53 min — GOOD)

**Remaining failure:** a team 4–7k ahead for 12 minutes in a 31-minute game still passes, because 63% close share is just above the floor. Rated MISLEADING.

### 4.7 LEAD_SWAPPED (added) and UNCLEAR

**LEAD_SWAPPED:** sustained runs by both sides.
- 1.6–2.7% of matches, but only 0.3% of Tier-A-empty viewpoints (T2 82%, T3 71% of its viewpoints).
- Stability 0.985.
- It is needed so every game gets a label.

**UNCLEAR:**
- Share: 20.9% dev / 19.9% holdout / 16.8% old patch.
- Duration short / medium / long: 5.8 / 23.8 / 32.5% (correlation 0.23 — long games are messy).
- Stability 0.934. Never displayed.
- In the fresh review, its remaining members are: small leads of 1–2 minutes followed by collapse, back-and-forth swings, and late separations shorter than 3 minutes before the window end.

---

## 5. Mutual Exclusivity & Tie-Breaking

The classifier returns exactly one label for every eligible perspective. This was verified for all 1,736 current and 416 older-patch perspectives.

**Raw overlaps before priority (v2):**

| Set | 0 raw shapes (→ UNCLEAR) | 1 | 2 | 3 | SHORT_WINDOW |
|---|---:|---:|---:|---:|---:|
| Dev (607) | 127 | 296 | 146 | 2 | 36 |
| Holdout (261) | 52 | 140 | 64 | 1 | 4 |

| Overlap | Dev | Holdout |
|---|---:|---:|
| ONE_SIDED & STEADY_EDGE | 106 | 42 |
| EVEN_THEN_SEPARATED & STEADY_EDGE | 19 | 9 |
| DEFICIT_RECOVERED & STEADY_EDGE | 13 | 7 |
| LEAD_ERODED & STEADY_EDGE | 12 | 7 |
| DEFICIT_RECOVERED & ONE_SIDED | 2 | 1 |
| EVEN_THEN_SEPARATED & LEAD_ERODED | 0 | 1 |

**Final priority:** EVEN_THEN_SEPARATED → LEAD_ERODED → DEFICIT_RECOVERED → ONE_SIDED → STEADY_EDGE → LEAD_SWAPPED → CLOSE_THROUGHOUT → UNCLEAR.

- **Almost every conflict involves STEADY_EDGE**, the broadest shape, so it sits below every more specific edge shape.
- **The rare erosion/recovery vs ONE_SIDED conflicts go to erosion/recovery**, because the erosion is the non-obvious fact.
- **CLOSE_THROUGHOUT cannot conflict with any edge shape**, since it requires no sustained run.
- **LEAD_SWAPPED cannot conflict with erosion, recovery, ONE_SIDED or STEADY_EDGE**, since they all forbid opposite runs.
- **Unresolved cases:** none.

**Final one-label distribution:**

| Label | Dev | Holdout | Old patch |
|---|---:|---:|---:|
| EVEN_THEN_SEPARATED | 13.3% | 14.9% | 13.9% |
| LEAD_ERODED | 6.1% | 4.2% | 3.8% |
| DEFICIT_RECOVERED | 4.4% | 7.3% | 4.3% |
| ONE_SIDED | 17.1% | 15.7% | 21.6% |
| STEADY_EDGE | 17.3% | 19.9% | 18.3% |
| LEAD_SWAPPED | 1.6% | 2.7% | 3.4% |
| CLOSE_THROUGHOUT | 13.2% | 13.8% | 10.1% |
| UNCLEAR | 20.9% | 19.9% | 16.8% |
| SHORT_WINDOW | 5.9% | 1.5% | 7.7% |

**Mirror consistency:** 100%. LEAD_ERODED ↔ DEFICIT_RECOVERED, FOR ↔ AGAINST, and CLOSE_THROUGHOUT ↔ CLOSE_THROUGHOUT all held for 1,094 of 1,094 matches. There were no data anomalies.

---

## 6. Threshold Sensitivity

**Perturbation stability (34 deterministic variants per match):**

| Set | Mean agreement | Stable (≥0.9) | Borderline (0.7–0.9) | Highly unstable (<0.7) |
|---|---:|---:|---:|---:|
| Dev | 0.951 | 80.4% | 19.6% | 0.0% |
| Holdout | 0.947 | 78.5% | 21.5% | 0.0% |
| Old patch | 0.945 | 78.8% | 21.2% | 0.0% |

The 26-variant core used for v1 gives 0.941 on dev. The least stable single perturbations are window end ±2 minutes (84–87% agreement), window start ±2 (87–89%) and edge percentile ±5 (~90%).

| Class | Rules |
|---|---|
| **Robust** | CLOSE percentile (p40–p60); STRONG percentile (p85/p90); run length 2–4 min; ONE_SIDED share 60–75%, first-edge 25–40%, structures 2–4; separation final-third share 50–70%; erosion reference (peak / run median / p90 differ ≤1 pp); lean share 0.75 vs 0.80 (0.2 pp); mirror rule |
| **Borderline** | Edge percentile ±5; window start/end ±2 minutes; separation close share 0.55–0.75 (v1: separation 8.9% → 6.1%); erosion 35% / 65% (v1: lead-eroded 9.7% → 7.4%); CLOSE_THROUGHOUT gold guard 6,500 vs 7,500 (CLOSE_THROUGHOUT 9.6% vs 13.2%) |
| **Brittle / rejected** | CLOSE_THROUGHOUT as a fallback; relative-only erosion; absolute-gap lane composite; windows of 9–11 minutes (confidence 0.895) |

**shape_confidence recommendation.** Emit the perturbation agreement deterministically.
- **< 0.7:** never display. No v2 match fell below 0.7.
- **0.7–0.9:** display only for kinds whose review GOOD rate is ≥ 40%.
- **≥ 0.9:** normal.

**Recommended frozen V1 values:** the Section 3.4 threshold table plus the Section 13 rule parameters.

**Patch / time stability (Phase 8):**
- **Label agreement when thresholds are refitted on the new data vs frozen:** holdout 87.0%, older-patch sample 81.7%.
- **Older-patch relative leads were larger.** Meaningful-edge band 20–29 min: Standard 0.117 vs 0.103 frozen; Turbo 14–19 min: 0.133 vs 0.099.
- **ONE_SIDED more common, CLOSE_THROUGHOUT less** in the older patch (21.6% vs 17.1%; 10.1% vs 13.2%).
- **The population is confounded.** The older sample is random public matches; the current corpus is mostly tracked accounts. Inside the current corpus, the early vs late chronological halves also differ (ONE_SIDED 12.4% vs 21.0%) for the same population reason. Held-out accounts differ too: acct6 has DEFICIT_RECOVERED 10.8% vs dev 4.4%.
- Modifier rates are stable (STRUCTURE_BURST 84–92%, STRUCTURE_ALIGNED 50–59%, NO_STRUCTURE_CONVERSION 1–2%).

**Conclusion:** version the thresholds per mode and recalibrate on the production population periodically, and after major gameplay patches, with shape-frequency drift monitoring. Nothing requires patch-specific logic.

---

## 7. Structure Modifier Validation

Rates below are share of matches on development data.

| Modifier | Variant tested | Rate | Finding | Verdict |
|---|---|---:|---|---|
| STRUCTURE_ALIGNED | leader net ≥ 1 / 2 / 3 during edge minutes (lag 0 / 2 min) | 56.3 / 49.9 / 44.0% | Present in 97% of ONE_SIDED, 72% of STEADY_EDGE, 84% of EVEN_THEN_SEPARATED; restates the shape | **REDUNDANT — reject** |
| STRUCTURE_COUNTERTREND | trailing side +1 / +2 / +3 during the leader's edge minutes (lag 0; lag 2 in brackets) | 2.6 / 0.7 / 0.3% (4.4 / 1.6 / 1.2%) | At +2: 8 matches, all EVEN_THEN_SEPARATED; the examples are interesting | **TOO RARE as a candidate; keep as enrichment text** |
| NO_STRUCTURE_CONVERSION | edge run ≥8 (Standard) / ≥5 (Turbo) minutes with 0 net structures; tolerance ±1; alternative minimum lengths | 2.0% (±1: 6.4%; 6/4 min: 3.1%; 10/6 min: 1.5%) | LEAD_ERODED 10.8%, DEFICIT_RECOVERED 7.4%; produced two GOOD examples | **Keep as enrichment (tolerance 0)** |
| STRUCTURE_BURST | 2 / 3 / 4 structures in 3 / 5 / 7 minutes, final 3 minutes excluded | 57–94% | End-game pushes before the exclusion window | **TOO COMMON — reject** |

**Decision: (A) modifiers only.**
- **(B) participation in classification** was tested through ONE_SIDED's "≥3 net structures or strong edge" clause. Dropping it or moving it between 2 and 4 structures changes ONE_SIDED by ≤0.5 pp, so structures add nothing to classification.
- **(C) a separate countertrend candidate** fires in 0.7% of matches, too rarely to justify a slot.

---

## 8. Tier B Scoring Validation

### 8.1 The formula as proposed (v1) did not order quality

On 395 rated v1 candidates, the Spearman correlation between score and content rating was 0.405. Raising the cutoff made the random Tier-A-empty "best candidate" sample *worse*:

| v1 cutoff | Coverage | GOOD | ACCEPTABLE | BORING | MISLEADING |
|---:|---:|---:|---:|---:|---:|
| 0 | 100% | 22% | 27% | 38% | 12% |
| 50 | 70% | 29% | 31% | 33% | 7% |
| 60 | 30% | 17% | 28% | 50% | 6% |
| 65 | 18% | 9% | 27% | 55% | 9% |

**Causes:**
- A composite scored the same vision metric twice.
- ONE_SIDED and STEADY_EDGE got trajectory credit for restating the result.
- Tiny moderate signals scored like meaningful ones.

### 8.2 Revised scoring (v2)

**Explanatory-structure weights by shape:**

| Shape | Weight |
|---|---:|
| EVEN_THEN_SEPARATED, LEAD_ERODED, DEFICIT_RECOVERED, LEAD_SWAPPED | 1.0 |
| CLOSE_THROUGHOUT | 0.6 |
| STEADY_EDGE | 0.4 |
| ONE_SIDED | 0.2 |

**Other changes:**
- Corroboration credit goes only to composites of independent metrics.
- Magnitude floors on moderate signals.
- An explicit display-exclusion list.
- HistoryContext stays 0: no Tier B history signal was validated.

**Pooled ratings of displayable candidates still valid under v2** (n=290):

| Cutoff | n | GOOD | ACCEPTABLE | BORING | MISLEADING |
|---:|---:|---:|---:|---:|---:|
| 0 | 290 | 36% | 51% | 12% | 0.7% |
| 40 | 239 | 44% | 49% | 6% | 0.8% |
| **45** | **221** | **46%** | **48%** | **6%** | **0%** |
| 50 | 194 | 47% | 47% | 6% | 0% |
| 55 | 139 | 55% | 38% | 7% | 0% |
| 60 | 69 | 62% | 29% | 9% | 0% |
| 65 | 35 | 66% | 23% | 11% | 0% |
| 70 | 20 | 70% | 10% | 20% | 0% |

- **Spearman correlation (v2 score vs rating):** 0.546 over all rated kinds; 0.443 within displayable kinds.
- **Fresh holdout funnel (n=60 random Tier-A-empty viewpoints, best displayable candidate):**

| Cutoff | GOOD | ACCEPTABLE | BORING | MISLEADING | Nothing |
|---:|---:|---:|---:|---:|---:|
| 0 | 22% | 33% | 12% | 2% | 32% |
| 40 | 22% | 27% | 5% | 2% | 45% |
| **45** | 20% | 27% | 3% | 0% | 50% |
| 50 | 17% | 18% | 3% | 0% | 62% |
| 55 | 17% | 10% | 3% | 0% | 70% |
| 60 | 7% | 3% | 0% | 0% | 90% |

**Recommended cutoff: 45.**
- It removes most boring big-lead STEADY_EDGE games (scores 25–30) and weak lane-rank lines.
- It keeps 94% GOOD+ACCEPTABLE among displayed candidates, with no misleading examples at or above 45.
- 50 costs another 8–12 pp of coverage for almost no quality gain.
- 60 and above give up most coverage.

**Interpretation:** the score works as a display gate and a tie-breaker. Most of the trust comes from the kind-level eligibility list, not from the score.

---

## 9. Moderate Composite Validation

"All" and "Tier-A-empty" are share of viewpoints; loss skew is the loss rate divided by the win rate, both measured in Tier-A-empty.

| Composite | Rule | All / Tier-A-empty | Loss skew | Review (pooled, v2-valid) | Adds insight over its parts? | Causal risk | Verdict |
|---|---|---:|---:|---|---|---|---|
| Economy: enemy stack edge + early-rich hero | stack ≥p75, edge ≥4 **and** rich ≤p25, ≥3 min earlier | 1.6% / 0.1% | 6–8× | v1: ACCEPTABLE 62%, BORING 38% (n=8) | No — the rich hero alone rates better (GOOD 71%) | "while" juxtaposition invites a causal reading | **TOO RARE / REJECT** |
| Vision: observer clearance + low surviving ratio | rate ≥p75 and share ≥p75 | 20.3% / 13.3% (v1) | 1.7× | BORING 82% (n=17) | No — same metric twice | Low | **REJECT.** Replaced by OBSCLEAR_MOD (share ≥45%, ≥4 destroyed): ACCEPTABLE 100% (n=7), never GOOD |
| Power spike: NW goal early + early key item (same hero) | rich ≤p25 and ≥3 min earlier, and the hero's spike item ≤p25 | 9.6% / 3.6% | **8.1×** | GOOD 67%, ACCEPTABLE 7%, BORING 27% (n=15) | Yes — names the item and its timing | v1 connector "by then" was **WRONG** when the item came later (5 of 12); now time-ordered | **STRONG BUT SITUATIONAL (loss-skewed)** |
| Match development: moderate separation + structure edge | shape + STRUCTURE_ALIGNED | 50% of matches | — | — | No — 84–97% of edge shapes | — | **REDUNDANT** |
| Lane: NW gap + CS gap in the same direction | v1 absolute p50 → v2.1 beyond p75/p25 **of the same position pairing**; offlaner-behind-vs-carry suppressed | 16.2% / 13.2% | 0.76× | GOOD 41%, ACCEPTABLE 59% (n=22; fresh holdout 40 / 60) | Yes — personal and counterpart-specific | Low | **STRONG** (v1 absolute version: 30% MISLEADING) |
| Countertrend: NW advantage + structure disadvantage | STRUCTURE_COUNTERTREND | 0.7% of matches | — | Interesting where present | Yes | Must stay "during", never "because" | **TOO RARE — enrichment only** |
| *(Phase 16)* Lane vs the other two lanes | own lane is the only one of three with that sign; magnitude floors | 7.0% / 5.6% | 0.97× | GOOD 45%, ACCEPTABLE 50%, BORING 5% (n=22) | Yes — a context the player cannot see | Low | **STRONG BUT SITUATIONAL** |
| *(Phase 16)* Multiple moderate hidden signals | ≥2 of stack / vision / smoke / rich | 6.6% / 1.5% | **34×** | v1: GOOD 8%, ACCEPTABLE 58%, BORING 33% (n=12) | Marginal | Reads as "reasons you lost" | **REJECT or balance** |

**Moderate single signals kept:**
- **RICH_MOD** (GOOD 71%, n=14; loss skew 7.3×).
- **SMOKE_MOD** (enemy smokes ≥ own + 4; GOOD 44%, ACCEPTABLE 56%, n=9).
- **STACK_MOD** (edge ≥4; ACCEPTABLE, n=3 — too rare to judge).

**Rejected:**
- **BOSS_MOD** (one enemy Roshan vs zero): 100% BORING, 9.3× loss-skewed.
- **ITEM_EARLY_MOD** (any enemy core spike item ≤p25): fires in 63% because 5 cores × 10 items gives many chances.
- **LANE_NW_MODERATE**: superseded by the lane composite.

All rendered composites use only "while", "and", "then", "by", "during". No rendering uses causal verbs.

---

## 10. Tier A → Tier B Coverage Funnel

Recommended gate (score ≥45, exclusions as in Section 13). This is the model estimate over all 8,680 non-feeding viewpoints, using per-kind review rates.

```text
100%  parsed eligible viewpoints (868 matches × 10)
 ↓
66.6% Tier A insight available
 ↓
33.4% Tier A empty
 ↓
 8.1% Tier B strong/useful explanation (GOOD)        = 24.1% of Tier-A-empty
10.4% Tier B acceptable fallback (ACCEPTABLE)        = 31.0% of Tier-A-empty
 1.9% Tier B shown but boring                        =  5.7% of Tier-A-empty
 0.2% Tier B shown but misleading                    =  0.5% of Tier-A-empty
12.9% nothing useful (no displayable candidate ≥45)  = 38.7% of Tier-A-empty
 ─────
85.0% of viewpoints end with Tier A or a GOOD/ACCEPTABLE Tier B insight
```

**Holdout direct check** (fresh n=60 Tier-A-empty viewpoints): GOOD 20%, ACCEPTABLE 27%, BORING 3%, MISLEADING 0%, nothing 50%. That gives about **82%** overall, versus 85% from the model. The sample is small (±13 pp), so treat **82–85%** as the range.

**Segments (model):**

| Segment | Viewpoints | Tier A | Tier-A-empty | GOOD / ACCEPTABLE / BORING / MISLEADING / nothing within empty | Useful overall |
|---|---:|---:|---:|---|---:|
| Standard | 4,690 | 68.1% | 31.9% | 25.6 / 32.1 / 5.8 / 0.5 / 35.9 | 86.5% |
| Turbo | 3,990 | 64.7% | 35.3% | 22.5 / 29.8 / 5.6 / 0.5 / 41.5 | 83.2% |
| Carry | 1,736 | 67.3% | 32.7% | 26.4 / 33.4 / 5.7 / 0.4 / 34.2 | 86.8% |
| Mid | 1,736 | 67.5% | 32.5% | 25.1 / 33.2 / 4.9 / 0.4 / 36.5 | 86.4% |
| Offlane | 1,736 | 66.9% | 33.1% | 26.6 / 34.6 / 5.7 / 0.5 / 32.7 | 87.1% |
| Support | 3,472 | 65.6% | 34.4% | 21.4 / 27.2 / 6.1 / 0.5 / **44.7** | 82.3% |
| Win | 4,340 | 58.2% | 41.8% | 20.9 / 29.7 / 5.1 / 0.4 / **43.8** | **79.3%** |
| Loss | 4,340 | 74.9% | 25.1% | 29.5 / 33.3 / 6.7 / 0.5 / 30.1 | 90.7% |
| Established (≥10 prior same-mode matches) | 628 | 69.3% | 30.7% | 24.7 / 33.7 / 6.4 / 0.5 / 34.7 | 87.2% |
| New / no history | 8,052 | 66.4% | 33.6% | 24.1 / 30.8 / 5.7 / 0.5 / 38.9 | 84.8% |
| Dev | 6,070 | 66.7% | 33.3% | 24.4 / 30.8 / 5.5 / 0.4 / 38.9 | 85.1% |
| Holdout | 2,610 | 66.3% | 33.7% | 23.6 / 31.6 / 6.1 / 0.5 / 38.2 | 84.9% |

**Outcome balance (Phase 12):**
- **Shape labels are outcome-neutral by construction**; outcome is never an input.
- **Displayed Tier B still skews to losses:** 69.9% of Tier-A-empty losses get a displayed Tier B, versus 56.2% of wins.
- **Loss-skewed kinds in the displayed mix:** the power-spike composite (8.1×), RICH_MOD (7.3×), OBSCLEAR_MOD (2.5×) and SMOKE_MOD (2.2×).
- **Balanced kinds:** the lane composite (0.76×), lane vs other lanes (0.97×), STACK_MOD (0.8×) and all shapes.

Wins are already the weaker segment: Tier A empty 41.8% and useful overall 79.3%. A later ranking step needs a negative-insight balancing rule. Not implemented here.

**Duration bias (Phase 13):**
- **LEAD_ERODED / DEFICIT_RECOVERED:** correlation 0.20. Partly inherent; phase bins and gold confirmation reduced DEFICIT_RECOVERED's long-game rate from 14.4% to 5.4%.
- **UNCLEAR:** 0.23.
- **ONE_SIDED:** −0.33 (inherent).
- **SHORT_WINDOW:** −0.30 (by definition).
- **EVEN_THEN_SEPARATED 0.04, CLOSE_THROUGHOUT 0.01, STEADY_EDGE −0.10.**
- **Every moderate signal:** |correlation| ≤ 0.15. Smoke and vision signals use per-10-minute rates.

No displayed Tier B kind is a secret long-game detector.

---

## 11. Examples From the Formerly Empty 32%

Every example below comes from a viewpoint where **no Tier A candidate fired**. The text is a plain factual research rendering, **not production copy**. Ratings are from the review.

**EVEN_THEN_SEPARATED**
- GOOD — Standard loss, 40 min, Support: "Until 30:00 the net-worth gap stayed within 3.6k. From 33:00 the enemy held a sustained lead: 16.5k at 33:00, 25.2k at 37:00."
- GOOD — Turbo win, 34 min, Support: "Until 21:00 the net-worth gap stayed within 7.9k. From 24:00 your team held a sustained lead: 18.3k at 24:00, 24.1k at 31:00."
- GOOD — Standard win, 55 min, Support: "Until 30:00 the net-worth gap stayed within 6.7k. From 33:00 your team held a sustained lead: 12.5k at 33:00, 26.4k at 52:00."
- BORING — Turbo win, 20 min, Support: "Until 11:00 the net-worth gap stayed within 3.1k. From 14:00 your team held a sustained lead…"

**LEAD_ERODED / DEFICIT_RECOVERED**
- GOOD — Turbo win, 37 min, Carry: "Your team's lead peaked at 32.9k at 18:00 and was 2.7k by 34:00; the enemy never held a sustained lead."
- GOOD — Turbo win, 48 min, Support: "Your team's lead peaked at 20.4k at 21:00 and was 4.3k by 45:00; the enemy never held a sustained lead."
- GOOD — Turbo loss, 40 min, Mid: "The enemy's lead peaked at 42.9k at 25:00 and was 6.9k by 37:00; your team never held a sustained lead."

**CLOSE_THROUGHOUT**
- GOOD — Standard loss, 58 min, Support: "Between 10:00 and 55:00 the net-worth gap never stayed above 6.5k for 3 straight minutes. The game was still close at 55:00."
- GOOD — Standard loss, 38 min, Carry: "Between 10:00 and 35:00 the net-worth gap never stayed above 2.7k for 3 straight minutes. The game was still close at 35:00."
- MISLEADING — Standard win, 31 min, Offlane: "Between 10:00 and 28:00 the net-worth gap never stayed above 6.2k… still close at 27:00." (The team was 4–7k ahead from 16:00.)

**STEADY_EDGE**
- GOOD — Standard loss, 39 min, Support: "The enemy was ahead in net worth for 100% of 10:00–36:00 and your team never held a clear lead for 3 straight minutes (largest lead 16.6k at 36:00). The enemy led for 14 minutes (10:00–23:00) with no net tower/barracks change."
- ACCEPTABLE — Standard win, 37 min, Mid: "Your team was ahead in net worth for 100% of 10:00–34:00 and the enemy never held a clear lead for 3 straight minutes (largest lead 13.2k at 26:00)."
- BORING — Turbo loss, 29 min, Support: "The enemy was ahead in net worth for 100% of 8:00–26:00 … (largest lead 25.5k at 25:00)."

**Lane composite (position-pairing normalized)**
- GOOD — Turbo win, 22 min, Offlane: "by 8:00 you were +2.7k net worth and +8 last hits against Faceless Void (P1)"
- GOOD — Standard win, 45 min, Carry: "by 10:00 you were -1.1k net worth and -10 last hits against Snapfire (P3)"
- GOOD — Standard win, 44 min, Mid: "by 10:00 you were +1.7k net worth and +36 last hits against Ogre Magi (P2)"

**Lane vs the other two lanes**
- GOOD — Turbo loss, 26 min, Support: "at 8:00 your lane was the only one ahead (+4.2k); top -6.1k, mid -5.2k"
- GOOD — Turbo loss, 23 min, Support: "at 8:00 your lane was the only one behind (-6.4k); top +5.6k, mid +1.3k"
- BORING — Standard loss, 45 min, Support: "at 10:00 your lane was the only one ahead (+1.1k); mid -1.4k, bot -1.4k"

**Enemy economy and hidden activity (moderate)**
- GOOD — Turbo loss, 22 min, Support: "Wraith King (P1) bought Radiance at 6:49 and reached 15,000 net worth at 13:00 (your team's first at 17:00)"
- GOOD — Standard loss, 30 min, Offlane: "Sniper (P2) reached 10,000 net worth at 19:00 (your team's first at 24:00)"
- GOOD — Standard win, 46 min, Offlane: "the enemy used Smoke 7 times (your team 0)"
- ACCEPTABLE — Standard loss, 32 min, Support: "the enemy destroyed 6 of your team's 11 observers (55%)"
- BORING — Standard loss, 32 min, Offlane: "Ember Spirit (P2) reached 10,000 net worth at 20:00 (your team's first at 30:00), then bought Black King Bar at 24:53"

**Nothing** (16 of 60 holdout samples had no candidate at all)
- Standard win, 39 min, Support — shape UNCLEAR, no moderate signal.
- UNCLEAR, Turbo loss, 28 min: a +12k lead at 16:00 was lost from 20:00. No 3-minute sustained edge, so no shape — a missed story that Tier A T3 also did not reach.

---

## 12. Failure Graveyard

| Failure | Evidence |
|---|---|
| CLOSE_THROUGHOUT as "whatever is left" | 38% MISLEADING (n=52); persistent 8–16k leads called close |
| "Largest 3-minute gap" computed with same-sign minutes | Swinging games showed "0.6k" while leads moved ±6k; replaced by the either-direction gap |
| Absolute gold guard at p40–p80 of the distribution (12–23k) | Barely changed CLOSE_THROUGHOUT (30.8% → 26.7%); 26% of T3 perspectives stayed "close" |
| Relative-only erosion / recovery | Long games "recovered" while the gold gap held steady; rendering quoted the relative peak (5 of 26 LEAD_ERODED misleading) |
| Constant bands across game time | Late relative leads 35–40% smaller; long-game DEFICIT_RECOVERED 14.4% |
| Edge percentile p75 | Most stable, but "no sustained edge" 53–58% and comeback recall −6 to −18 pp |
| Hysteresis (enter p70, stay p60) | Lower stability (0.947 vs 0.952), more comeback contradictions (10.8%) |
| No end exclusion | Final push created 37 false separations (78% agreement vs 3 min) |
| 5-minute exclusion | Turbo games collapse to SHORT_WINDOW; late separations lost |
| 6-minute minimum window | Windows of 9–11 min already least stable (0.895) |
| Thirds-only separation | Late separations fell into UNCLEAR (34 matches moved to separation in v2) |
| ONE_SIDED structure clause | Non-binding (±0.5 pp for 2–4 structures) |
| STRUCTURE_ALIGNED / STRUCTURE_BURST modifiers | 50% / 87% of matches; restate the shape |
| Repeated parity regaining | 0% of Tier-A-empty matches; no such pattern after smoothing |
| ≥4 nontrivial lead changes | 0 matches; back-and-forth games appear as LEAD_SWAPPED / UNCLEAR |
| Vision composite (clearance + low surviving ratio) | 82% BORING; same metric twice |
| BOSS_MOD (one enemy Roshan vs zero) | 100% BORING, 9.3× loss-skewed |
| ITEM_EARLY_MOD (any enemy core spike item ≤p25) | Fires 63% (multiple comparisons) |
| Absolute-gap lane composite | 30% MISLEADING (offlaners "behind" safe-lane carries) |
| Power-spike connector "by then" | Factually WRONG when the item followed the milestone (5 of 12) |
| Economy composite | 0.1% of Tier-A-empty after floors; component alone rates better |
| Multiple moderate hidden signals | 34× loss skew in Tier-A-empty |
| v1 score formula | Higher cutoffs produced more BORING (≥60: 50% BORING) |
| Transition-only separation detection (instead of thirds OR transition) | Less stable (0.945), more contradictions |
| 5-minute median smoothing | Stability tie, but DEFICIT_RECOVERED stable share 56% vs 76% |

---

## 13. FINAL RECOMMENDED TIER B CONTRACT

**RECOMMENDATION FOR PRODUCT REVIEW — NOT YET SSOT**

Machine-readable version: `post-match-tier-b-validation-data/tier-b-shape-definitions.json`.

### Inputs
- Batchable only; playback is not required.
- `players[].stats.networthPerMinute` for all 10 players.
- `towerDeaths` (time, npcId, isRadiant = owner; towers and barracks only).
- `durationSeconds`, `gameMode` / `lobbyType`.
- Moderate signals add the existing primitives: lane counterpart CS/NW, camp stacks, observer placement and destruction, smoke uses, per-minute hero NW, item purchase times.
- Match outcome is used for context only, never for detection.

### Normalization
- R(t) = L(t) / (team NW(t) + enemy NW(t)) at t:00.
- Centered 3-minute median, computed on R truncated at the window end.

### Window
- **Start:** Standard 10:00 / Turbo 8:00.
- **End:** floor((duration − 3 min) / 60).
- **Minimum:** 9 minutes; otherwise SHORT_WINDOW.

### Thresholds
- **Bands:** CLOSE p50, MEANINGFUL_EDGE p70, STRONG_EDGE p90 of |R|.
- **Fitted per mode × phase bin:** Standard edges at minutes 20 / 30 / 40; Turbo at 14 / 20 / 26 (values in Section 3.4).
- **Sustained run:** ≥3 minutes.
- **Hysteresis:** none.
- **Version and recalibration:** version per mode; recalibrate periodically and after major patches.

### Shape definitions
As in Section 4:
- **EVEN_THEN_SEPARATED** (thirds OR transition path);
- **LEAD_ERODED / DEFICIT_RECOVERED** (relative + gold erosion ≥50%, gold peak ≥5k / 8k);
- **ONE_SIDED** (≥70% edge share, first edge ≤33%, no opposite run);
- **STEADY_EDGE** (≥50% edge share, or ≥80% ahead with median ≥ CLOSE);
- **LEAD_SWAPPED** (sustained runs by both sides);
- **CLOSE_THROUGHOUT** (no sustained run, close share ≥60%, 3-minute gap <7,500);
- **UNCLEAR.**

### Priority
EVEN_THEN_SEPARATED → LEAD_ERODED → DEFICIT_RECOVERED → ONE_SIDED → STEADY_EDGE → LEAD_SWAPPED → CLOSE_THROUGHOUT → UNCLEAR.

### Mirror rule
The opponent's label must equal the mirrored label. This is a required test.

### shape_confidence
- Agreement across the 34 listed perturbations.
- Hide if < 0.7.
- Between 0.7 and 0.9, display only kinds with a pooled review GOOD rate ≥40%: CLOSE_THROUGHOUT, LEAD_ERODED, the lane composite, lane vs other lanes, the power-spike composite, RICH_MOD and SMOKE_MOD. EVEN_THEN_SEPARATED is 35% pooled and 50% on the fresh sample, so it is not on the list.

### Structure modifiers
- **Enrichment text only:** NO_STRUCTURE_CONVERSION (edge ≥8 / 5 min, 0 net) and STRUCTURE_COUNTERTREND (trailing side ≥2 more).
- **Not used:** STRUCTURE_ALIGNED, STRUCTURE_BURST.

### Moderate signals (Tier B)
Definitions in the JSON:
- C_LANE_NW_CS (pairing-normalized);
- X_LANE_VS_OTHER_LANES;
- C_SPIKE_RICH_ITEM;
- RICH_MOD;
- SMOKE_MOD;
- OBSCLEAR_MOD;
- STACK_MOD (Standard only);
- X_HIDDEN_MULTI and C_ECON_STACK_RICH — computed, pending the balancing decision.

### Score formula
TierBScore = (35·SignalStrength + 25·ExplanatoryStructure + 20·PlayerRelevance + 15·Corroboration + 5·HistoryContext) · Reliability

**Explanatory structure:**

| Kind | Weight |
|---|---:|
| EVEN_THEN_SEPARATED, LEAD_ERODED, DEFICIT_RECOVERED, LEAD_SWAPPED, power-spike composite | 1.0 |
| Lane vs other lanes, multiple hidden signals, economy composite | 0.8 |
| CLOSE_THROUGHOUT, lane composite | 0.6 |
| Single hidden signal | 0.5 |
| STEADY_EDGE | 0.4 |
| ONE_SIDED | 0.2 |

**Player relevance:**

| Level | Weight |
|---|---:|
| User's lane | 0.9 |
| Counterpart | 0.75 |
| Team | 0.5 |

**Corroboration:**
- 1.0 for independent-metric composites.
- 0.5 for the lane composite and for a shape with an enrichment modifier.
- Otherwise 0.

**HistoryContext:** 0.

**Reliability:**
- shape_confidence for shapes;
- 1.0 for raw facts;
- 0.9 for lane counterpart signals;
- 0.85 for lane vs other lanes.

### Score cutoff
- **Display floor: 45.**
- **Excluded from display:** ONE_SIDED, UNCLEAR, SHORT_WINDOW, BOSS_MOD, ITEM_EARLY_MOD, LANE_NW_MODERATE, the vision composite.

### Output slots
- **Every Tier B item:** id, family, label and direction, score and components, shape_confidence, facts (minutes, gold values, counts), enrichment modifiers, window start/end.
- **Plus the shape-specific slots in the JSON.**

### Fallback behaviour
1. Tier A first.
2. If Tier A is empty: the highest-scoring displayable Tier B candidate ≥45.
3. If none: an explicit "nothing notable" state. No filler.
4. Feeding-guard matches: suppress match-shape Tier B (economy distorted by one player).

---

## 14. Product Decisions Remaining

1. **Accept a "nothing notable" state for about 13–17% of viewpoints?** It is concentrated in wins (18% of all wins), supports (15%) and Turbo (15%). Lowering the gate to 0 cuts it to about 9%, but adds boring outputs (8% of Tier-A-empty).
2. **Show ACCEPTABLE-level Tier B, or only GOOD-prone kinds?** GOOD-prone kinds (pooled GOOD ≥40%, n ≥5) are CLOSE_THROUGHOUT, LEAD_ERODED, the lane composite, lane vs other lanes, the power-spike composite, RICH_MOD and SMOKE_MOD. Showing only those:
   - drops GOOD+ACCEPTABLE Tier B from 18.5 pp to 12.3 pp of all viewpoints;
   - raises "nothing notable" from 12.9% to 20.6%;
   - cuts shown-but-boring from 1.8% to 0.5%.
3. **Should STEADY_EDGE be displayed at all?** It is ACCEPTABLE 61% / BORING 36%, and it is the most frequent shape in Tier-A-empty.
4. **Negative-insight balancing.** The power-spike composite (8×), RICH_MOD (7×) and the multiple-hidden-signals composite (34×) are loss-skewed, and wins already get less coverage. Cap enemy-advantage Tier B items per card, prefer shape or lane items in losses, or accept the skew?
5. **Winners labelled "the enemy was ahead" (17 matches), and the mirror case for losers.** These are comebacks inside the final 3 excluded minutes that Tier A T3 did not reach. Show them as trajectory facts with the window end stated, or suppress them?
6. **Should enrichment modifiers be shown?** Countertrend structures (0.7%) and "led N minutes with no structure change" (2%) are rare but among the more interesting lines.
7. **Owner re-rating before lock.** All ratings come from one research rater. Re-rate at least the v2 round in `tier-b-review-sheet.html` before this contract is promoted to SSOT.

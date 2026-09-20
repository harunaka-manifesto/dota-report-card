# Post-Match Final Ranking, History and Player-Context Audit

**Status:** Final recommendation for the three open areas in `POST-MATCH-INSIGHT-DECISIONS-V1.md` (§22.1–22.3). Also closes the vision-reconstruction holdout (§22.4) and adds evidence for the Smoke→Kills lock (§22.5).
**Date:** 2026-09-16
**Machine-readable contract:** [`post-match-final-audit-data/final-candidate-contract.json`](../generated_data/post-match-final-audit-data/final-candidate-contract.json)
**Evidence folder:** [`post-match-final-audit-data/`](../generated_data/post-match-final-audit-data) — results JSON, every rating file, review sheets, and research code.
**Workspace (git-ignored):** `.local/stratz-probe/final-audit-2026-09-16/`

Rendered sentences in this report are diagnostic research renderings, not product copy.

**How to read the ratings.** Ratings are GOOD / ACCEPTABLE / BORING / MISLEADING (G/A/B/M) and come from one rater (this research model) applying the written rubric in §3.2. Where a guard was tuned on examples, the tuning examples and the validation examples are reported separately.

---

# 1. Executive verdict

## Ranking — settled

The owner's proposed simple rule (severity bands, then normalized exceedance, then top 3) is **not good enough on its own**.
- Against 120 manually ranked real recaps (332 cards), band-only and exceedance-only orderings agree with the manual order on 57–58% of card pairs. Random ordering scores 50%.
- The reason is structural: the **type** of card matters more than how far past its own threshold it is. Players almost always want "you won from 24k down" above "their Clinkz bought Desolator early", whatever the percentiles say.

The next-simplest rule that works adds **one coarse class layer** and **one specific combination guard**:

1. **Match-story guard.** Keep at most one card from the match-story family: Comeback Win, Lost From Ahead, Close Most of Game, Even Then Separated, Lead Flip, Lead Eroded, Deficit Recovered, Late Reversal. Keep the first eligible card in that order.
2. **Sort** by:
   - rank class — 1 = Comeback Win / Lost From Ahead; 3 = Enemy Early Item / Vision Region Sweep; 2 = everything else;
   - then severity band (EXTREME > STRONG > NOTABLE);
   - then the normalized level inside the band;
   - then a fixed tie order.
3. **Show** the first 1–3 cards. Never fill.

**Validated result on the manual set:**

| Rule | Pairwise agreement | Top-1 agreement |
|---|---:|---:|
| Final rule | 83% | 80% |
| Band-only, same guard | 64% | 54% |
| Random, same guard | 50% | 43% |

- **Cross-validated:** class assignments learned on half the reviews and tested on the other half give 79% pairwise and 75% top-1.
- **Why the guard is needed:** same-story pairs appeared in 51 of 120 multi-card recaps (for example "Comeback Win" plus "Lead Flip" describing the same swing). 52 of the 61 cards the guard removes are ones the manual review had independently marked as duplicates.

## History — settled

| Claim level | Minimum comparable prior matches (N) |
|---|---|
| Any historical wording | 10 |
| Median-only "vs your usual" line (never a card by itself) | 10 |
| Record wording ("your fastest / best / worst / highest across your last N …") and card eligibility | **20** |
| "One of your 3 fastest…" and "top 10% of your last N" | **30** |
| "ever", "all-time", "personal record", exact percentiles | never, in insight cards |

- **Window:** the **most recent 50 comparable eligible matches** in the user's currently entitled history.
- **Item timing** additionally requires the **same major patch** (7.xx). BKB timing shifted about 2.5 minutes between 7.39 and 7.40; no other metric drifted materially.
- **Comparator keys:**
  - own lane and opponent start: mode bucket + effective role (cores only);
  - own item: bucket + role + item + major patch (hero not included — only 11.5% availability);
  - enemy-team enrichments: bucket only (enemy metrics do not depend on the user's role).
- **Why N = 20:** a "record in your last 20" is still in the top 5% of that account's 60-match reference **80–90%** of the time, versus 56–63% at N = 10 and 25–27% at N = 3. The theoretical record rate at N prior matches is 1/(N+1): 4.8% at N = 20, measured 4.6–4.9%.

## Player-context audit — settled

Every surviving card was reviewed on real matches (about 1,100 ratings in total; §7). Changes:

**Removed (3)**
- **Dramatic Lane Lead Path / Reversal.**
  - Meaningful lane reversals do not happen at the 5/10-minute checkpoints: 0 of 5,202 core lanes had an early lead of at least p75 that flipped to an opposite gap of at least p50.
  - What the card actually fired on was ordinary blowouts: 0 GOOD, 83% BORING.
  - This reverses an owner KEEP, so it needs an explicit owner acknowledgment.
- **Turbo Enemy Smoke Volume.** 0 GOOD in 24 Turbo examples; Smoke Volume becomes Standard-only.
- **"Slowest ever item" direction of Own Item Timing.** 12 of 14 BORING, mostly late situational buys in long games.

**Guarded (13)** — Lead Flip, Lead Eroded, Deficit Recovered, Close Most of Game, Even Then Separated, Enemy Smoke Volume, Vision Quick Clears, Vision Region Sweep, Enemy Early-Rich Hero, Enemy Early Item, Own Lane vs Usual, Opponent Start vs History, Own Item vs History. Details in §9. The biggest finding: before its guard, **Lead Eroded was misleading 43% of the time** (it labelled real 8–21k gold flips as "erosion").

**Unchanged** — Comeback Win and Lost From Ahead (only a final-3-minutes exclusion), Enemy Stacking (Standard), Late Reversal.

**Result on fresh holdouts after the final guards:** 0 misleading cards in 84 fresh ratings (the lean-corpus holdout); pooled fresh GOOD rates are 40–85% depending on the candidate.

## Two external blockers resolved today

**1. Vision stats-only ward reconstruction — validated.** Playback returned data again today (34 of 110 fresh matches). On those unseen matches:

| Measure | Result |
|---|---:|
| Deward identity precision | **99.1%** |
| Coverage | 79% |
| Region correct | 99.1% |
| Quick-clear classification | 99.5% |

It produced no false Quick Clears or Sweep fires; the 3 disagreements were misses. The method is production-usable, with counts worded as lower bounds.

**2. Smoke→Kills modified rule — replicated.** On 66 fresh team units, teams where the rule fired had 62 Smokes followed by a kill against 38.2 expected at matched ordinary moments (×1.6). Suppressed teams were at chance (47 vs 49.7). Recommendation: **lock** it, as an enrichment on the Standard-only Smoke card.

## Uncomfortable consequence — reported, not "fixed"

With the owner's removals plus these guards, **57% (no-history corpus) to 61% (established accounts) of viewpoints get no special card.** Turbo is at 67–72%.
- The accepted 13–17% was measured on the earlier, larger pool: Support Lane Pair, Boss Control, Steady Edge, the Tier B moderate signals, CS-vs-Gold, and others that have since been removed.
- The audit guards cost 26 points of coverage, and each removed slice was majority BORING or MISLEADING in review (§12).
- As instructed, no guard was loosened for coverage. The generic "no special insight" post-match state is now the **majority** experience, and the product plan should reflect that.

---

# 2. Final ranking contract

## 2.1 Pipeline

```text
match payload (+ entitled history)
  → global eligibility (mode bucket, 10 humans, ≥10 min, all stats, no abandon leaver, positions complete, feeding guard)
  → per-candidate eligibility + guards (§9, contract JSON)          → cards[] with facts
  → per-card severity: magnitude → ladder (q, s, e) → level, band   → cards[] with band, level
  → match-story family guard (keep ≤1)
  → sort (rank class ↑, band ↓, level ↓, tie order ↑)
  → take first min(3, n). n may be 0.
```

**Feeding guard.** If any player has at least 8 deaths before 10:00 (Standard) / 8:00 (Turbo), the match gets no cards (18 of 886 matches). Economy-based facts are distorted in those matches.

## 2.2 Severity: level and band

For a candidate with ladder (q = qualify, s = strong, e = extreme) and magnitude v, oriented so that bigger is more extreme:

```text
v < q           → not eligible
q ≤ v < s       → level = (v − q) / (s − q)                    band NOTABLE (1)
s ≤ v < e       → level = 1 + (v − s) / (e − s)                band STRONG (2)
v ≥ e           → level = min(3, 2 + (v − e) / (e − s))        band EXTREME (3)
```

**Ladders (Standard / Turbo).** These come from the 886-match corpus distributions; the percentile noted is of the population the candidate is drawn from.

| Candidate | Magnitude v | NOTABLE q | STRONG s | EXTREME e | Basis |
|---|---|---|---|---|---|
| Comeback Win | max enemy lead, final 3 min excluded | 12,000 / 18,300 | 19,500 / 23,700 | 31,000 / 33,500 | winners' max deficit p90 / p95 / p99 |
| Lost From Ahead | max own lead, final 3 min excluded | same | same | same | mirror |
| Lead Flip | min(peak before, peak after) | 7,900 / 14,200 | 12,100 / 19,400 | 21,900 / 27,500 | flip min-peak p75 / p90 / p97.5 |
| Enemy Stacking (Std) | enemy stacks by 20:00 | 7 | 9 | 13 | team p90 / p95 / p99 |
| Vision Quick Clears | observers cleared ≤90 s | 4 / 4 | 5 / 5 | 6 / 6 | Std p95 / p97.5 / p99; Turbo p97.5 / p99 / >p99 |
| Vision Region Sweep | observers in one region in 5 min | 3 | 4 | 5 | categorical (4+ is about 1% of teams) |
| Enemy Smoke Volume (Std) | enemy minus own Smoke uses | 4 | 6 | 8 | difference p90 / – / p99 |
| Enemy Early-Rich Hero | minutes ahead of your team's first | 3 / 3 | 5 / 4 | 7 / 6 | gap p75 / p90 / p97.5 |
| Enemy Early Item | (p5 − t) / p5 | 0.10 | 0.15 | 0.22 | fire margin distribution p50 / p75 / p90 |

**History cards** (N = window size, capped at 50):

| Card | STRONG if | EXTREME if |
|---|---|---|
| Own Lane vs Usual | N = 50, or lane gap ≥ core p95 (2,253 / 4,449) | both |
| Opponent Start vs History | N = 50, or counterpart CS ≥ position p95 | both |
| Own Item vs History | N = 50, or record margin ≥ 120 s / 60 s | both |

- NOTABLE otherwise (20 ≤ N < 50).
- Level = (band − 1) + min(0.99, N / 50).

**Tier B cards** (categorical, fixed levels):

| Card | STRONG | EXTREME | Level |
|---|---|---|---|
| Close Most of Game | close share ≥ 0.90, still close within 2 min of window end, and window ≥ 30 / 20 min | none | NOTABLE: (share − 0.75) / 0.15 × 0.99; STRONG: 1 + (share − 0.9) × 5 |
| Even Then Separated | separation ≥ 30 / 20 min and pre-separation gap ≤ 5,000 | none | STRONG 1.0; NOTABLE 0.5 |
| Lead Eroded / Deficit Recovered | peak ≥ 10k / 15k and gold erosion ≥ 75% | peak ≥ 15k / 22k and erosion ≥ 90% | NOTABLE: min(0.99, (erosion − 0.5) × 2); STRONG: 1 + min(0.99, (erosion − 0.75) × 4); EXTREME: 2.0 |
| Late Reversal | peak enemy lead in the final run ≥ 10k / 15k | none | STRONG 1.0; NOTABLE 0.5 |

**Why not the same percentile tiers everywhere.**
- Several metrics are integer counts with ties (stacks, Smoke difference, quick clears), so p95 and p97.5 collapse into the same value.
- Turbo Quick Clears already qualify at p97.5.
- The shape cards have no continuous magnitude that players experience as "more extreme".

The ladders use each metric's own natural steps; the ranking evidence (§3) shows that band differences carry about 7 points of pairwise agreement **within** a class.

## 2.3 Match-story family guard

Precedence, first eligible wins:

1. COMEBACK_WIN
2. LOST_FROM_AHEAD
3. CLOSE_MOST_OF_GAME
4. EVEN_THEN_SEPARATED
5. LEAD_FLIP
6. LEAD_ERODED
7. DEFICIT_RECOVERED
8. LATE_REVERSAL

Built-in exclusivity:
- Comeback Win and Lost From Ahead are exclusive by result.
- Close Most of Game, Even Then Separated, Lead Eroded and Deficit Recovered are exclusive Tier B labels.

**Why this is a specific guard, not the rejected generic engine.**
- It touches one family that the decision document already defines as one coherent Match Lead Story.
- It fires on a repeated harmful pattern measured on both corpora:

| Kept | Suppressed | Times |
|---|---|---:|
| Lost From Ahead | Lead Flip | 280 |
| Comeback Win | Lead Flip | 274 |
| Comeback Win | Late Reversal | 219 |
| Comeback Win | Deficit Recovered | 117 |
| Lost From Ahead | Lead Eroded | 107 |
| Close Most of Game | Lead Flip | 56 |
| Comeback Win / Lost From Ahead | Close Most of Game | 48 |

- In the recap audit, all three weak recaps were contradictory Close Most of Game + Lead Flip pairs: "close 79–100% of minutes" next to "you led by 11k, then they led by 9k".
- No other combination guard was justified (§8).

## 2.4 Rank classes and tie order

| Class | Cards | Evidence (mean manual position; 0 = top, 1 = bottom; duplicates removed) |
|---|---|---|
| 1 | Comeback Win, Lost From Ahead | 0.02 (n = 27), 0.08 (n = 18) |
| 3 | Enemy Early Item, Vision Region Sweep | 0.90 (n = 32), 0.94 (n = 15) |
| 2 | all others | 0.17–0.63 |

- **Stability:** in 40 cross-validation splits, class 1 = {Comeback, Lost} and class 3 = {Early Item, Sweep} were the modal learned sets.
- **Why class 3:** these two describe a narrow detail: one item purchase, or one region's wards over five minutes.

**Tie order** (only when class, band and level are exactly equal):

COMEBACK_WIN > LOST_FROM_AHEAD > EVEN_THEN_SEPARATED > OWN_LANE_VS_USUAL > ENEMY_SMOKE_VOLUME > ENEMY_STACKING > LEAD_ERODED > OWN_ITEM_VS_HISTORY > VISION_QUICK_CLEARS > CLOSE_MOST_OF_GAME > LEAD_FLIP > DEFICIT_RECOVERED > ENEMY_EARLY_RICH > OPP_START_VS_HISTORY > LATE_REVERSAL > ENEMY_EARLY_ITEM > VISION_REGION_SWEEP

This is the measured standalone order.

**Not used:** Tier A over Tier B, own vs enemy balancing, win/loss balancing, diversity quotas. Tested: a Tier A tie-break lowered top-1 agreement from 45% to 43%.

## 2.5 Missing-data behaviour

| Missing | Behaviour |
|---|---|
| Unparsed match / missing any player's `networthPerMinute` | No cards (global ineligibility) |
| Wards or `wardDestruction` missing for a team | Vision cards ineligible for that team |
| Lane counterpart unresolved (no unique position counterpart in the same map lane) | Own Lane and Opponent Start ineligible |
| History N below gate | History card ineligible; enemy cards render without a history line |
| Playback null, or item events empty | Smoke→Kills enrichment silently absent; vision uses stats reconstruction |
| Playback present but Smoke count ≠ stats count | Enrichment absent |
| Tier B shape_confidence < 0.7, or SHORT_WINDOW / UNCLEAR | No Tier B card |
| Feeding guard | No cards |

## 2.6 Worked examples (real matches; manual order in brackets)

**Example 1 — Standard offlane Tidehunter, win, 42 minutes.** Six cards were eligible.

| Card | Band | Level | Fact |
|---|---|---:|---|
| COMEBACK_WIN | 2 | 1.03 | trailed by 19.8k at 33:00 |
| DEFICIT_RECOVERED | 2 | 1.16 | family, suppressed |
| LATE_REVERSAL | 2 | 1.00 | family, suppressed |
| OPP_START_VS_HISTORY | 2 | 1.40 | Shadow Fiend 91 CS at 10:00, highest in your last 20 |
| OWN_LANE_VS_USUAL | 1 | 0.40 | worst lane in your last 20, −2.2k |
| ENEMY_EARLY_RICH | 1 | 0.50 | Shadow Fiend 10k NW at 17:00, your first at 21:00 |

- Family guard keeps Comeback Win and drops the other two.
- Sort: Comeback Win (class 1) → Opponent Start (class 2, band 2) → Early-Rich (class 2, band 1, level 0.50) → Own Lane (class 2, band 1, level 0.40).
- **Shown:** Comeback Win, Opponent Start, Early-Rich.
- Manual order: Comeback > Opponent Start > Own Lane > Early-Rich. Top 2 agree; #3 swaps two near-equal cards.

**Example 2 — Standard support Jakiro, loss, 46 minutes.** Cards: LOST_FROM_AHEAD (b1, led by 12.2k at 30:00), CLOSE_MOST_OF_GAME (b1), ENEMY_STACKING (b3: 21 stacks vs 1), LEAD_FLIP (b1).
- Family guard keeps Lost From Ahead.
- **Shown:** Lost From Ahead, Enemy Stacking.
- Manual order: Stacking > Lost > Close > Flip. This is one of the 20% top-1 disagreements: an EXTREME hidden card against a borderline class-1 story. Promotion rules ("EXTREME jumps one class") were tested and lowered overall agreement (§3.4), so no exception is added.

**Example 3 — Standard support Silencer, loss, 29 minutes.** Cards: ENEMY_STACKING (b1, 7 vs 1), ENEMY_EARLY_ITEM (b3, Kez Desolator 10:10, typical 21:20), ENEMY_EARLY_RICH (b2, Kez 10k at 15:00 vs 20:00).
- **Shown:** Early-Rich, Stacking, Early Item.
- Manual order: Early-Rich > Early Item > Stacking.

**Example 4 — Standard carry Phantom Lancer, win, 55 minutes.** Cards: OWN_ITEM_VS_HISTORY (b2, Manta 13:10, fastest of your last 50 Standard carry Mantas; previous 14:21) and CLOSE_MOST_OF_GAME (b2, level 1.5).
- Both are class 2 and band 2; level 1.99 beats 1.50.
- **Shown:** Own Item, Close. Matches the manual order.

---

# 3. Ranker validation

## 3.1 Competition corpus

**120 viewpoints, 332 cards.** One viewpoint per team per match. Cards were shuffled and shown without band or level.

| Source | Viewpoints | Composition |
|---|---:|---|
| Tuning corpus, guard set v3 | 70 | 28 with two cards, 26 with three, 16 with four or more |
| Fresh lean corpus, with history | 50 | 38 containing at least one history card, 12 with three or more |

Subsets:

| Subset | Viewpoints |
|---|---:|
| Tier A vs Tier B competition | 53 |
| Enemy vs own/match | 79 |
| History vs non-history | 36 |
| Three or more cards | 68 |
| Four or more cards | 21 |

Sheets: `review-sheets/rank_sheet.txt`, gold order in `review-sheets/rank_gold.txt`.

## 3.2 Manual ranking rubric

Cards were ordered most-worth-showing first by applying, in this order:
1. Would this player care?
2. Is it surprising or hidden?
3. Does it capture the shape of the match?
4. Is the magnitude notable?
5. Is it trustworthy?
6. Does it avoid "so what?"
7. Does it avoid a misleading implication?

Same-story pairs were marked `dup`.

## 3.3 Variants tested (all 120 viewpoints; no family guard unless stated)

| Variant | Top-1 | Pairwise | Kendall | Top-3 set (4+ cards) | Bad displacements* |
|---|---:|---:|---:|---:|---:|
| Random | 38.8 | 50.0 | 0.00 | 72.9 | 10.5 |
| M1 band → level | 45.0 | 57.5 | 0.16 | 74.6 | 9 |
| M1b band → exceedance ratio | 45.8 | 56.6 | 0.15 | 73.0 | 10 |
| M2 exceedance ratio (clipped 0–3) | 46.7 | 57.5 | 0.17 | 74.6 | 9 |
| M3 piecewise level (0 / 1 / 2) | 45.8 | 57.8 | 0.17 | 74.6 | 9 |
| M1 + Tier A tie-break | 43.3 | 56.6 | 0.13 | 77.8 | 9 |
| M4 band → learned type priority (CV) | 56.6 | 66.8 | – | 79.3 | 5 |
| M5 learned type priority only (CV) | 70.0 | 77.5 | – | 84.8 | 2 |
| M6 3-class → band → level (CV) | 71.7 | 77.3 | – | 82.2 | 3 |

\*Manual-last card enters the model's top 3 while a manual top-2 card is left out.

**With the lead-family guard** (107 viewpoints still have 2+ cards):

| Variant | Top-1 | Pairwise | Top-3 set |
|---|---:|---:|---:|
| Random | 43.3 | 50.0 | 75.1 |
| Bands only | 54.2 | 64.0 | 73.3 |
| Exceedance only | 57.0 | 65.5 | 73.3 |
| **Final contract** (full family guard, class → band → level → tie order) | **80.4** | **83.0** | **80.0** |
| Final contract, class learned on half (40 splits) | 74.5 | 79.1 | – |
| Class only (random within class) | 69.3 | 74.6 | 79.2 |
| Class → band (random within band) | 77.7 | 81.3 | 83.0 |

Other checks:
- The guard dropped the manual #1 card in 1 of 107 viewpoints. In that match the manual review preferred "close most of the game" over a comeback whose deficit appeared only just before the end.
- 52 of 61 suppressed cards had been independently marked `dup`.

**Subset pairwise agreement (M6 vs M1):**

| Subset | M6 | M1 |
|---|---:|---:|
| Tier A vs B | 85.0 | 60.1 |
| History vs non-history | 76.4 | 52.8 |
| Enemy vs own/match | 83.3 | 58.3 |
| 4+ cards | 78.4 | 54.0 |

## 3.4 Major failures and rejected refinements

- **Severity alone fails because cards from different candidates are not commensurate.**
  - A p99 Early Item (for example 27% earlier than p5) is still less interesting than a p90 comeback.
  - Band-only ranking put Early Item or Sweep in the top 3 over better cards 9–10 times.
- **"EXTREME promotes one class"** lowered pairwise agreement (82.3 → 77.3 in the 3-class variant, 80.4 → 74.4 in the class-1-only variant). Extreme stacking or early-item cards then displaced comebacks too often.
- **Additive class + band** was no better than lexicographic (80.1 vs 81.9).
- **Two classes only** (story vs rest) scored 75.1 pairwise; the class-3 layer is worth about 8 points.
- **Putting Even Then Separated in class 1** changed nothing (it never co-fires with class 1). Kept in class 2 for simplicity.
- **Remaining top-1 misses (about 20%)** are mostly two patterns:
  - an extreme hidden fact against a borderline class-1 story (Example 2);
  - a history card against a mid-level enemy card.

  Both are defensible either way; no further rule is justified by 120 reviews.

## 3.5 Why this is the simplest acceptable rule

Every piece removed costs measurable agreement:

| Removed | Pairwise loses |
|---|---:|
| Class layer | 19 points |
| Band inside class | about 7 points |
| Family guard | duplicates reappear in 43% of multi-card recaps |

Every piece added on top (promotion, Tier A tie-break, additive score) did not help. The only fixed-priority element is a 3-level class list with two members at each end, derived from the review and stable under cross-validation. It is not a free-form weight vector.

---

# 4. Final history contract

## 4.1 Summary table

| Card | Comparator key | Min N (card) | Window | Mode | Role | Hero / item | Allowed claim | Not allowed | Sparse history |
|---|---|---:|---|---|---|---|---|---|---|
| Own Lane vs Usual | bucket + effective role | 20 | last ≤50 comparable | separate | **cores only** (Carry / Mid / Offlane) | hero not in key | "Your lane gap at 10:00 was +2.8k — your best across your last 50 Standard Carry matches (previous best +2.0k)." Median line allowed at N ≥ 10. | "best ever", "personal record", "you won/lost lane because…" | Card ineligible |
| Opponent Start vs History | bucket + effective role (implies counterpart position) | 20 | last ≤50 | separate | cores only | counterpart hero named as a fact only | "Their Shadow Fiend had 91 CS at 10:00 — the most any opposing Carry has had against you across your last 20 Standard Offlane matches." | "strongest opponent ever", "outplayed you", skill claims | Card ineligible (no population-only version; owner decision) |
| Own Item vs History | bucket + role + item + major patch | 20 | last ≤50 purchases | separate | yes | item yes; hero no | "Your 13:10 Manta was your fastest across your last 50 Standard Carry Manta purchases (previous 14:21)." | slowest-record cards; "ever"; "fastest on this hero" | Card ineligible |
| Enemy Early-Rich (enrichment) | bucket | 20 | last ≤50 | separate | no | none | Secondary line: "the earliest an enemy hero reached 10k across your last N Standard matches" | changing eligibility or band from history | Card shows without the line |
| Enemy Early Item (enrichment) | bucket + item | 20 | last ≤50 enemy purchases of that item + major patch | separate | no | item yes | "earliest enemy BKB across your last N Standard matches" | "earliest ever" | Line absent |
| Enemy Stacking (enrichment) | bucket | 20 | last ≤50 | Standard | no | – | "most stacks an enemy team has made against you across your last N Standard matches" | – | Line absent |
| Enemy Smoke Volume (enrichment) | bucket | 20 | last ≤50 | Standard | no | – | "most enemy Smokes across your last N Standard matches" (on the Smoke-difference or rate value actually shown) | – | Line absent |

## 4.2 Claim levels (all history wording)

| N (comparable prior matches in window) | Allowed |
|---|---|
| < 10 | Nothing historical |
| 10–19 | Median-only secondary line ("about 2 minutes earlier than your usual across your last 14") — **never a card by itself** |
| ≥ 20 | Record wording: "your fastest / slowest* / best / worst / highest / most across your last N {mode} {role} [item] …". Makes history cards eligible |
| ≥ 30 | "one of your 3 fastest / best across your last N"; "top 10% of your last N"; "unusually early for you" |
| any N | Never: "ever", "all-time", "personal record", "PB", exact percentiles ("top 7%") |

\*"Slowest" is allowed wording but no V1 card uses it.

**Rules for the numbers:**
- N is always stated.
- "Your usual" always means the window median.
- Records are strict: they must beat the previous record by the card's margin (lane 100 / 200 gold; item 60 / 30 s).
- An exact tie is not a record.
- **"Ever" contract:** insight cards never say "ever". The existing Personal Best system keeps its own separate rules, and even there "ever" requires a completeness flag the app does not have today.

## 4.3 Sparse-history and new-user fallback

- **History-required cards** are simply absent below N = 20. The recap is not padded.
- **Enemy cards** render without the history line below N = 20.
- **No fake personal baseline** (population numbers presented as "your usual") is ever used.
- **Free users at link time:** with a 30-match bootstrap per bucket, the role cohort reaches N ≥ 20 for only 0–34% of evaluations (§5.3). History cards appear once enough post-link matches accumulate. This is expected, not a defect.

---

# 5. History sample-size evidence

## 5.1 Data

**Real chronological histories: 31 accounts, 9,930 eligible rows.**
- Most accounts have 320–383 rows; three have 20, 62 and 65.
- Split: 5,075 Standard / 4,855 Turbo; 2,717 carry / 2,419 mid / 1,767 offlane / 3,027 support.
- Patches: 182 (7.40b-era id) 8,436; 180 (7.39) 1,097; others 390.
- Account spans: 18–905 days.
- Fetched with a lean ten-player query: net worth, last hits, camp stacks, item purchases, item uses, deaths, towers. 16 matches per request.

**Stability method.** For every evaluation with at least R prior values in its cohort (R = 60 for lane and enemy metrics, 40 for items), the claim computed on the most recent N prior values was compared with the same claim computed on the most recent R prior values.

- **Record precision** = share of "record in last N" claims whose value is also in the top 5% of the R-reference.
- **Top-3 precision** = share of "top 3 of last N" claims whose value is in the top 10% of the reference.
- **Unusual precision** = share of "beyond the p90 of last N" claims that are beyond the p90 of the reference.

Caveat: the reference window contains the N window, so values near N = 50 are optimistic by construction. The trend up to N = 30 is the informative part.

## 5.2 Availability (share of evaluations with at least N comparable prior matches)

Established tracked accounts, all matches in their histories.

| Cohort | N=3 | 5 | 7 | 10 | 15 | 20 | 25 | 30 | 50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Lane / opponent: bucket | 98.3 | 97.2 | 96.1 | 94.5 | 91.9 | 89.4 | 87.1 | 84.7 | 75.9 |
| Lane / opponent: **bucket + role** | 93.7 | 90.0 | 86.6 | 81.9 | 74.9 | **68.7** | 63.0 | 57.7 | 40.7 |
| Lane / opponent: bucket + position | 92.3 | 87.9 | 83.8 | 78.3 | 70.3 | 63.3 | 56.9 | 51.3 | 34.0 |
| Own item: bucket + item | 92.3 | 87.8 | 83.8 | 78.5 | 71.1 | 64.8 | 59.4 | 54.6 | 40.2 |
| Own item: **bucket + role + item** | 81.3 | 73.1 | 66.6 | 58.5 | 48.3 | **40.0** | 33.1 | 27.6 | 14.2 |
| Own item: bucket + hero + item | 49.5 | 38.0 | 30.6 | 23.3 | 15.8 | 11.5 | 8.6 | 6.9 | 2.8 |
| Enemy stacks: **bucket** | 98.5 | 97.5 | 96.5 | 95.2 | 92.9 | **90.6** | 88.5 | 86.4 | 78.3 |
| Enemy stacks: bucket + role | 94.6 | 91.4 | 88.3 | 83.9 | 77.1 | 70.8 | 65.0 | 59.7 | 42.7 |
| Enemy Smoke rate: bucket | 98.3 | 97.2 | 96.1 | 94.6 | 92.0 | 89.6 | 87.2 | 84.9 | 76.2 |
| Enemy goal minute: bucket | 98.2 | 97.1 | 96.0 | 94.4 | 91.8 | 89.3 | 86.9 | 84.6 | 75.7 |
| Enemy item: bucket + item | 96.0 | 93.4 | 91.0 | 87.6 | 82.2 | 77.2 | 72.6 | 68.1 | 52.2 |

**Bucket + role at N ≥ 20:**

| Role | Standard | Turbo |
|---|---:|---:|
| Carry | 75.7 | 68.4 |
| Mid | 77.1 | 53.3 |
| Offlane | 61.7 | 57.0 |
| Support | 63.0 | 76.9 |

## 5.3 Free-bootstrap reality

History is the 30 most recent matches of the bucket at link time. Share of evaluations with a role cohort of at least N inside those 30:

| Segment | N ≥ 10 | N ≥ 20 | N ≥ 30 |
|---|---:|---:|---:|
| Standard carry / mid | 76 | 25–34 | 2 |
| Standard offlane / support | 45 | 13–16 | 0 |
| Turbo carry / mid | 45–46 | 8–14 | 0 |
| Turbo offlane | 23 | 0 | 0 |
| Turbo support | 84 | 20 | 0 |
| Item cohort (Standard / Turbo) | 58 / 67 | 8 / 19 | – |

## 5.4 Stability by N

**Own lane gap** (bucket + role; 3,255 evaluations with a 60-match reference):

| N | Record rate | Record precision | Top-3 precision | Unusual precision | Rank error | Median error (IQR) |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 24.1% | 25.1% | – | – | 0.178 | 0.389 |
| 5 | 16.0 | 36.2 | 22.9 | – | 0.136 | 0.312 |
| 7 | 12.0 | 45.5 | 30.8 | – | 0.115 | 0.266 |
| 10 | 8.9 | 57.8 | 41.5 | 59.8 | 0.095 | 0.220 |
| 15 | 6.2 | 72.3 | 57.8 | 60.9 | 0.076 | 0.182 |
| **20** | 4.9 | **79.7** | 71.1 | 73.5 | 0.062 | 0.149 |
| 25 | 4.1 | 86.1 | 82.5 | 72.1 | 0.052 | 0.127 |
| **30** | 3.4 | 91.9 | **90.6** | **81.8** | 0.044 | 0.107 |
| 50 | 1.9 | 99.2 | 99.7 | 93.0 | 0.019 | 0.040 |

**Record precision** (top 5% of the reference), all metrics:

| Metric | N=3 | 5 | 7 | 10 | 15 | 20 | 25 | 30 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Opponent start | 26.7 | 38.7 | 48.1 | 63.2 | 79.4 | **89.3** | 92.9 | 97.0 |
| Own item timing (both directions) | 27.2 | 38.4 | 48.4 | 60.1 | 77.0 | **89.0** | 93.9 | 97.5 |
| Enemy stacks | 23.8 | 35.3 | 44.4 | 55.9 | 72.3 | **80.0** | 85.5 | 95.0 |
| Enemy Smoke rate | 25.3 | 36.3 | 45.1 | 56.6 | 72.4 | **83.0** | 89.9 | 95.4 |
| Enemy goal minute | 19.0 | 28.5 | 37.9 | 50.8 | 67.2 | **82.5** | 87.7 | 90.8 |
| Enemy item timing | 26.9 | 38.7 | 49.3 | 63.2 | 79.8 | **90.3** | 96.8 | 99.7 |

**Top-3 and "unusual" precision:**

| Metric | Top-3 precision N=20 | Top-3 precision N=30 | Unusual precision N=20 | Unusual precision N=30 |
|---|---:|---:|---:|---:|
| Opponent start | 72.0 | 90.1 | 77.6 | 84.3 |
| Own item | 75.7 | 95.4 | 78.1 | 89.0 |
| Enemy stacks | 50.8 | 73.1 | 72.2 | 80.6 |
| Enemy Smoke | 73.8 | 92.2 | 74.8 | 83.2 |
| Enemy goal minute | 32.5 | 44.5 | 76.8 | 82.8 |
| Enemy item | 76.1 | 96.2 | 83.8 | 90.5 |

Integer metrics with many ties (stacks, whole goal minutes) make "top 3" unreliable. Top-3 wording is therefore allowed only for continuous metrics (lane gap, CS, item seconds, Smoke rate).

**Label flip rate** (a record at N that is not top-5% on the reference) is 1 − record precision:

| N | Flip rate |
|---:|---|
| 5 | 61–72% |
| 10 | 37–49% |
| 20 | 10–20% |
| 30 | 2–9% |

## 5.5 Why these cutoffs

- **N = 20 for records.** This is where "record in last N" stops being mostly noise: precision rises from 50–63% at N = 10 to 80–90%, and availability is still 69% for role cohorts and 89–91% for enemy cohorts. N = 30 would raise precision to 91–97% but cut role-cohort availability to 58% and item availability to 28%.
- **N = 30 for "one of your…", "top 10%" and "unusually…".** These claims imply rarity, and they reach at least 80% precision only at N = 30.
- **N = 10 for median lines.** The median error is 0.22 IQR, about as good as the product's existing previous-20 baseline methodology tolerates. It is used for a secondary line only.
- **Window cap of 50.** Precision and median error saturate (99% and 0.04 IQR). A longer window mostly adds old patches (§6). It also keeps the claim "across your last 50" short and true.

---

# 6. Patch / recency decision

**Policy.** Use the **most recent 50 comparable eligible matches** from the user's currently entitled retained history. There is no calendar limit. **Own and enemy item timings additionally require the same major patch** (7.xx; lettered sub-patches count as the same). This is recomputed deterministically whenever the methodology or entitlement changes, as the existing progress rules require.

**Evidence** (7.39 = id 180 vs 7.40/b = id 182):

| Metric | Pooled change | Within account (accounts with ≥15 matches in each) | Verdict |
|---|---|---|---|
| Core lane gap at 10:00 | 790 → 773 | −84 gold (6 accounts) | no patch logic |
| Opponent CS at 10:00 | 42 → 42 | 0 (6) | no patch logic |
| **BKB first purchase** | 27:22 → 29:56 (+153 s) | **+130 s (4 accounts, all positive: +94 to +218)** | **patch-scope item timing** |
| Blink first purchase | 18:23 → 17:58 | −41 s (5 accounts, mixed sign) | covered by the same item rule |
| Enemy stacks by 20:00 | 3 → 3 | 0 (7) | no patch logic |
| Enemy Smoke rate | 0.96 → 0.86 per 10 min | 0.0 (7) | no patch logic |
| Enemy goal minute | 21 → 21 | +1 min (7) | no patch logic |
| Duration (Standard) | 40.2 → 40.9 min | +1.1 min | no patch logic |

**External context:**
- 7.39 reworked the map and jungle camps.
- 7.40 reworked neutral items.
- 7.41 reworked level 10/15 talents and moved Roshan between two pits.

Item cost and economy changes are exactly the kind of patch effect that moves item timings. Lane gaps and stack counts measured relative to the opponent or team did not move.

**Why not "current patch only" for everything.** Every major patch would wipe all history cards for weeks, with no measured benefit for five of the six metric types.
**Why not "all retained".** Pro history can span years (tracked accounts span up to 905 days), which would mix several patches into item records and make "last N" wording long.

---

# 7. Candidate-by-candidate player audit

**Samples.**

| Sample | What it is |
|---|---|
| R1 | Round 1: 30 random stratified real firings per candidate on the pre-audit definitions (mode × win/loss, spread across roles and durations; borderline and extreme cases appear naturally) |
| H | Fresh holdout (no example reused), guard set v2 |
| K | Second fresh holdout, v3 |
| J | Third fresh holdout from the separate lean corpus, never used for tuning, final definitions |

"R1 retained" = the Round 1 examples that still fire under the final definition. Those ratings are in-sample for any guard tuned on them.

## 7.1 Summary

| Candidate | R1 pre-audit G/A/B/M | Final-definition evidence G/A/B/M | Major failure modes found | Final status |
|---|---|---|---|---|
| Dramatic Lane Path / Reversal | 0/4/25/1 (+ census of 40 separation/reversal cases: 0/16/23/1) | – | Obvious blowouts; reversals of ±300 gold; offlane-vs-carry role norm; Alchemist gold-gifting | **REMOVE** |
| Own Lane vs Usual | 15/14/1/0 (v1 contract) | J cores: 5/3/0/0 | Supports (0 of 8 GOOD); near-tie records | **KEEP WITH GUARD** (cores only, margin) |
| Opponent Start vs History | 16/11/3/0 | cores in R1: 14/5/0/0 | Support counterpart NW records (2/6/3); farming heroes inflate CS | **KEEP WITH GUARD** (cores only) |
| Comeback Win | 23/6/0/1 | R1 retained 23/6/0/0; H 15/5/0/0 | Deficit only in final minutes of a game the team led; won-while-behind cases need careful wording | **KEEP WITH GUARD** (exclude final 3 min) |
| Lost From Ahead | 22/8/0/0 | H 14/6/0/0 | Lost while still ahead (base race), peak lead late | **KEEP** (wording rule) |
| Major Sustained Lead Flip | 16/11/1/2 | H 10/10/0/0 | Final-push run shown as a flip; an early small flip hides the decisive later swing | **KEEP WITH GUARD** |
| Enemy Stacking (Std) | 12/15/3/0 | H 7/12/1/0 | 7-stack cards in stomp wins are meh | **KEEP** |
| Vision Quick Clears | 12/14/4/0 | R1 retained 12/12/0/0; H 8/12/0/0 | Turbo "3 of 9" in short stomps | **KEEP WITH GUARD** (Turbo 4) |
| Vision Region Sweep | 7/12/11/0 | H 5/11/4/0; K 3/9/0/0 | Wards near natural expiry; team already ≥10k ahead; lane-phase river wards | **KEEP WITH GUARD** |
| Enemy Smoke Volume | 6/13/11/0 | Std only: R1 retained 6/2/0/0; H Std 5/5/0/0 | Small asymmetry (8 vs 6); Turbo 0 GOOD in 24 | **KEEP WITH GUARD** (Standard only, difference ≥4) |
| Smoke → Kills (enrichment) | prior spike 5/3/1/0 (9 fires) | fresh playback replication: fires ×1.6 over chance, suppressed at chance | Coincidental kills; Smokes cast inside running fights | **KEEP as enrichment; recommend owner lock** |
| Enemy Early-Rich Hero | 9/18/3/0 | H 7/11/2/0; K 9/3/0/0 | Alchemist; "your team never reached it" in 15-minute stomps | **KEEP WITH GUARD** |
| Enemy Early Item | 0/9/20/1 | H 7/13/0/0 | Margins of 0–2% ("at p5"); Midas / Aghanim's semantics; Alchemist gifting | **KEEP WITH GUARD** (item list, margin, typical-time context) |
| Own Item vs History | 7/8/15/0 | J 10/2/0/0 | Slowest records (12/14 BORING); 1–30 s margins | **KEEP WITH GUARD** (fastest only, margin, role and patch key) |
| Close Most of Game | 13/9/5/3 | R1 retained 13/6/0/0; H 11/8/0/1; K 9/3/0/0; J 7/5/0/0 | 62–72% close share with a persistent 5–7k lead; 11–15-minute Turbo windows | **KEEP WITH GUARD** |
| Even Then Separated | 6/7/9/8 | K 11/1/0/0; J 9/3/0/0 | "Even" periods with 8–16k gaps; Turbo stomps under 28 minutes | **KEEP WITH GUARD** |
| Lead Eroded | 4/10/3/**13** | J 6/6/0/0 | Real flips (enemy +8–21k) labelled "eroded"; interim flips; Turbo lane-phase peaks | **KEEP WITH GUARD** |
| Deficit Recovered | 6/21/3/0 | J 7/5/0/0 | Still 9–12k behind called "recovered"; interim flips; lane-phase peaks; 3-minute medians that did not match minute values | **KEEP WITH GUARD** |
| Late Reversal (winner-only) | 11/5/0/0 | H 3/1/0/0; J 9/3/0/0 | Nearly always the same story as Comeback Win | **KEEP** (family guard) |
| Structure contradiction (enrichment) | seen in 6 reviewed cards, all read naturally | – | – | **KEEP as enrichment** |

## 7.2 Notes by candidate (the 18 checks)

**Dramatic Lane Path — REMOVE.**
- In the owner's sense (a large early lead becoming a large deficit), the event does not exist at the 5:00 / 10:00 checkpoints: 0 of 5,202 core lanes, even using the peak gap between minutes 3 and 8.
- What remains is ordinary lane narration, which the owner already rejected.
  - Blowouts: 480 of 540 fires, 83% BORING. The player already knows (check 1).
  - Separations from an even start: acceptable at best.
- **Failure cases:**
  - An offlaner "losing the lead" to a carry (check 4).
  - Alchemist gifting items (check 12).
- The personal lane story now lives in Own Lane vs Usual and Opponent Start vs History, which rated much better.

**Own Lane vs Usual.**
- Cores: record lanes such as "your worst in your last 50 Carry games" rated GOOD 15 of 25.
- Supports: 0 of 8 GOOD. A support's own net-worth gap to the enemy support is a weak lane read (check 17), which mirrors the owner's reason for removing Support Lane Pair.
- Near-tie records (−1.5k vs −1.5k) read as silly (check 11). Hence the 100 / 200 gold margin.

**Opponent Start vs History.**
- Core counterparts: GOOD 14 of 19.
- Support counterparts (P4/P5 net worth): GOOD 2 of 11.
- Farming heroes (KotL, Nature's Prophet, Tinker) produce the most records (check 12). The claim is still literally true and was rated fine, so no hero exclusion is added. The hero is always named.

**Comeback Win / Lost From Ahead.**
- These are the most valued cards (manual position 0.02 / 0.08).
- **Failure:** a "comeback" whose deficit appeared only in the final 2–3 minutes of a game the team had led (checks 9, 10). Fixed by excluding the final 3 minutes.
- **Remaining oddities** are real but strange Turbo matches, such as winning while 67k behind or losing while 67k ahead (base races, megacreeps). These are:
  - wins while still behind at the end;
  - losses while still ahead at the end.

  Wording must say "trailed by X at T and won" or "led by X at T and lost". Never say "the game turned" or "threw" (checks 3, 15).

**Lead Flip.**
- Pre-guard: 2 misleading cards (a small mid-game flip was shown while a later, bigger opposite run decided the game) and several final-push flips.
- Fixes:
  - use the latest qualifying flip;
  - exclude the final 3 minutes.
- Holdout: 0 misleading in 20.
- A "flip in your favour" in a loss is a true paradox. The result slot is mandatory in copy (check 3).

**Enemy Stacking (Standard).**
- Hidden work, rated well; loss and win rates are similar.
- Copy states both counts. It must not imply your supports failed (check 14). "Your team stacked 0" is a fact, not a verdict.
- Turbo stays removed (owner decision; not re-tested).

**Vision Quick Clears / Region Sweep.**
- Hidden and concrete.
- **Sweep failure cases** (checks 2, 8, 16):
  - wards that had nearly expired anyway (median lifetime above 180 s);
  - sweeps while already 10k or more ahead or behind;
  - lane-phase rune-ward clears before 5:00.

  All three are guarded.
- Turbo Quick Clears at 3 were boring in short stomps. The threshold is now 4 in both modes.
- **Reconstruction:** 99.1% precise on the fresh playback holdout (§14.4). Counts are lower bounds and copy must say "at least".

**Enemy Smoke Volume.**
- Hiddenness is the value, but "enemy 10 Smokes vs your 7" is "so what" (check 2).
- Turbo counts of 3–5 in 20-minute games never rated GOOD (check 6).
- Guard: Standard only, and at least 4 more Smokes than your team.

**Smoke → Kills.** A sequence, not a cause (check 15). See §10 for the exact safe sentence.

**Enemy Early-Rich Hero.**
- Useful context without history, as the owner expected.
- Stomps where your team never reached the goal, or where the game ended within minutes, only restate the result (checks 8, 16). Guard: your team must reach the goal, and the match must continue at least 8 more minutes.
- Alchemist's economy profile is excluded (check 12).

**Enemy Early Item.**
- Worst pre-audit card: 0 GOOD, 67% BORING.
- **Correction to my own first reading:** hero-typical rushes are *not* the main problem. On 4,216 fires with a per-hero reference built from the new corpus, 87% were in that hero's own fastest 10%, and only 3% were typical for the hero. The real problems:
  - margins of 0–2% below p5, which look like normal timing;
  - Midas (a farming item) and Aghanim's (hero-specific effect, can be gifted);
  - copy without a reference point.
- With a 10% margin, the reduced item list and the typical-time reference, the fresh holdout rated 7 GOOD / 13 ACCEPTABLE / 0 BORING.
- **Wording:** "bought", never "finished" or "completed". A purchase event is the only thing observed.

**Own Item vs History.**
- Slowest-record cards are mostly long games or situational late purchases (checks 2, 5): removed.
- Fastest records with meaningful margins: 10 of 12 GOOD on fresh data.
- The cohort must include role (support vs core BKB timings differ by a median 4.5–8 minutes; check 4) and major patch (§6).

**Close Most of Game.**
- **Failure cases** (checks 1, 6, 11):
  - "Close" with a 62–72% close share, where one side held a 5–7k lead for 25 minutes;
  - 11–15-minute Turbo windows.
- Guards: close share at least 0.75; window at least 20 / 16 minutes.
- Copy must say "most of", never "throughout" (owner rule; the median close share is still 89%).

**Even Then Separated.**
- Pre-guard 27% misleading: the "even" phase contained 8–16k single-minute gaps, because late-game relative bands are loose.
- Turbo "even until 13:00" in a 21-minute stomp is just the laning phase (check 16).
- **Guards:**
  - pre-separation gap at most 7,500;
  - window at least 18 / 20 minutes;
  - the separating side must be the winner (check 3).
- Fresh holdouts: 20 GOOD / 4 ACCEPTABLE.

**Lead Eroded / Deficit Recovered.**
- Pre-guard, Lead Eroded was 43% misleading. The Tier B relative bands shrink late, so "your lead eroded" was shown for games where the enemy then led by 8–21k (checks 3, 10).
- **Guards:**
  - the end-of-window value must stay on the original side or within the floor;
  - no interim opposite lead beyond twice the floor;
  - the peak must come at least 6 minutes after the window start (no Turbo lane-phase leads);
  - Turbo floor raised to 10k;
  - "recovered" requires the remaining gap to be at most max(½ floor, ¼ of the peak) (check 10).
- The fresh lean holdout: 13 GOOD / 11 ACCEPTABLE / 0 BORING / 0 MISLEADING.
- **Deficit Recovered copy** must state the result and must not imply a comeback when the team lost. Pattern: "cut a 24k deficit to 1.4k by 48:00; Dire won."
- **Rendering fix:** use the actual minute value, not the 3-minute median the research renderer printed. One review showed "7.6k by 32:00" while the 32:00 value was 13.0k.

**Late Reversal.**
- Rates well.
- It is the same story as Comeback Win 219 of the times both fire; the family guard handles this (check 18).

## 7.3 What the rating process cannot guarantee

- One rater, no player panel.
- Ratings of fresh examples used the final definitions, but guard design was informed by earlier rounds. A second fresh holdout followed each change (K and J).
- The owner should still re-rate the sheets in `review-sheets/` before copy is finalised.

---

# 8. Cross-card recap audit

**Sample.** 60 complete selected recaps: 12 one-card, 20 two-card, 28 three-card, drawn from both corpora. Rated as a whole.

**Result: 36 GOOD / 21 ACCEPTABLE / 3 WEAK / 0 BAD.**

**Weak recaps (all three are the same pattern).** Close Most of Game + Lead Flip ("close 79% of minutes; gap never held above 7.4k" next to "your team led up to 7.9k … then enemy led up to 9.7k"). Both are true, but together they read as a contradiction. This is now covered by the family guard: 56 such pairs across both corpora.

**Checked and deliberately *not* guarded:**

| Combination | Why no guard |
|---|---|
| Enemy Early-Rich + Enemy Early Item on the same hero ("Ursa bought Battle Fury at 5:02 … reached 15k at 11:00") | Reads as one coherent snowball story; the earlier research also rated this pair GOOD. |
| Own Lane Worst + Opponent Start Record for the same lane | Complementary ("your worst lane; the most CS a Carry has had against you"). |
| Quick Clears + Region Sweep | Different facts about the same vision fight; read fine (for example "9 of 25 cleared within 90 s" + "4 in their half within 4 minutes"). |
| Three enemy-side cards in a loss (stacks + Smokes + early-rich) | Factual; the owner explicitly allows enemy-dominated recaps. Each card is non-causal. |
| Comeback Win + a hidden enemy card | Normal and good. |

**Conclusion.** The family guard is the only combination rule. No generic diversity, merge or balancing logic is needed.

---

# 9. Final player-context guards

| Candidate | Guard | Reason | Exact condition |
|---|---|---|---|
| All | Feeding guard | Economy distorted by one player | Any player with ≥8 deaths before 10:00 (Std) / 8:00 (Turbo) → no cards |
| Match-story family | Keep at most one | Same-story duplicates in 43% of multi-card recaps; contradictions | Precedence §2.3 |
| Comeback Win / Lost From Ahead | Final-minutes exclusion | Deficits or leads created only by the end push | Compute the max over minute samples 0..L−4 |
| Lead Flip | Final-minutes truncation; latest flip | Final-push runs; early small flip hides the decisive swing | Runs on the lead curve without its last 3 samples; display the last flip with min peak ≥ q |
| Lead Eroded / Deficit Recovered | Real-reduction rules | 43% misleading pre-guard | peak ≥ floor (5k / 10k); peak minute ≥ window start + 6; end value ∈ [−floor, max(0.5·floor, 0.25·peak)]; minimum after peak ≥ −2·floor |
| Close Most of Game | Majority and length | "Close" with persistent leads; tiny Turbo windows | close share ≥ 0.75; window ≥ 20 min (Std) / 16 (Turbo); confidence ≥ 0.7 |
| Even Then Separated | Credible "even"; not a stomp; outcome-consistent | 8–16k gaps called even; Turbo stomps; separation by the loser | max \|lead\| from window start to separation−3 ≤ 7,500; window ≥ 18 (Std) / 20 (Turbo); separating side = winner |
| Late Reversal | Winner-only (existing) | Brief late lead then loss is not a comeback | win AND the last sustained run is the enemy's, ending in the last 25% of the window, with peak ≥ 5k / 8k |
| Enemy Smoke Volume | Standard only; real asymmetry | Turbo never GOOD; small differences read "so what" | bucket = STANDARD; enemy ≥ 4; enemy − own ≥ 4; rate ≥ 1.60 / 10 min |
| Vision Quick Clears | Turbo floor | Turbo "3 of 9" in short stomps | count ≤90 s ≥ 4 (both modes); ≥25% of placed; clears before end − 5 min; counts are lower bounds |
| Vision Region Sweep | Cut-short wards; undecided game; not the laning phase | Near-expiry wards; stomps either way; rune wards | first clear ≥ 5:00; last clear < end − 5 min; \|lead at first clear\| < 10,000; median lifetime ≤ 180 s |
| Enemy Early-Rich Hero | Not a stomp restatement; hero profile | "Your team never reached it"; Alchemist | your team reached the goal; duration − goal minute ≥ 8; hero ≠ Alchemist |
| Enemy Early Item | Meaningful margin; clean item semantics; reference in copy | 67% boring pre-guard | item ∈ {BKB, Blink, Manta, Battle Fury, Radiance, Desolator, Maelstrom, Orchid}; t ≤ 0.90 × core p5; copy includes the bucket's typical core time |
| Own Lane vs Usual | Cores only; margin | Support lane gaps not meaningful; near-ties | role ≠ support; beats previous record by ≥100 (Std) / 200 (Turbo) gold |
| Opponent Start vs History | Cores only; population gate | Support NW records weak | role ≠ support; value ≥ position p90; strict window max |
| Own Item vs History | Fastest only; margin; cohort | Slowest records boring; role and patch confounds | fastest; margin ≥ 60 s (Std) / 30 s (Turbo); key bucket + role + item + major patch |
| Tier B shapes | Confidence | Unstable labels | shape_confidence ≥ 0.7 |

---

# 10. Safe semantic claims

| Candidate | SAFE TO SAY | DO NOT SAY |
|---|---|---|
| Comeback Win | "You trailed by 19.8k at 33:00 and won." Optionally "still behind at 39:00". If behind at the end: "won despite trailing by X". | "You came back because…", "clutch", "outplayed", "they threw" |
| Lost From Ahead | "Your team led by 13.6k at 28:00 and lost." | "You threw", "the game turned at…" (unless a flip card shows it), any blame |
| Lead Flip | "Your team led by up to 10.2k (4:00–31:00); then the enemy led by up to 20.7k (33:00–44:00)." Always state the result. | "The fight at X flipped the game", "momentum", cause of the swing |
| Close Most of Game | "The net-worth gap stayed within 5.4k for most of 10:00–41:00." Allowed: "Still close at 41:00." | "The game was even throughout", "anyone's game", "you should have won" |
| Even Then Separated | "Until 23:00 the gap never exceeded 5.4k; from 26:00 your team held a sustained lead." | "This fight / this item decided the game" |
| Lead Eroded | "Your 11.4k lead at 27:00 was down to 1.2k by 36:00." Add the result. | "You threw your lead", percentages without gold values |
| Deficit Recovered | "You cut the enemy's 24.4k lead to 1.4k by 48:00; the enemy won." | "Comeback" (unless you won — and then Comeback Win is shown instead), "you recovered" when still ≥ floor behind |
| Late Reversal | "The enemy led by up to 21k until 50:00; you won at 59:37." | "You always had it" |
| Own Lane vs Usual | "Your lane gap at 10:00 was −2.9k — your worst across your last 50 Standard Offlane matches (previous worst −1.8k)." | "ever", "your worst lane ever", "you lost lane because" |
| Opponent Start vs History | "Their Shadow Fiend had 91 CS at 10:00 — the most an opposing Carry has had against you across your last 20 Standard Offlane matches." | "strongest opponent you've faced", "they outplayed you", MMR/skill claims |
| Own Item vs History | "Your 18:35 BKB was your fastest across your last 50 Standard Mid BKB purchases (previous 20:19)." | "fastest ever", "finished BKB" (purchase ≠ completion wording), advice |
| Enemy Stacking | "Their team stacked 13 camps by 20:00; yours stacked 3." | "Their stacks won them the game", "your supports didn't stack" |
| Vision Quick Clears | "At least 8 of your 20 observers were destroyed within 90 seconds of being placed (4 within a minute)." | "They could see you", "your wards were in bad spots", "you had no vision" |
| Vision Region Sweep | "Between 18:48 and 22:32, at least 4 of your observers in their half were destroyed; they had lasted 12–114 seconds." Allowed (evidence clause): "the enemy placed N Sentries there." | Map-visibility %, "they blinded your jungle", "this led to deaths" |
| Enemy Smoke Volume | "They used Smoke 9 times; your team used it 3 times." Enrichment: "7 of their 9 Smokes were followed by a kill within a minute." | "successful Smokes", "Smoke ganks worked", "their Smokes killed you", "resulted in kills" |
| Enemy Early-Rich Hero | "Their Kez reached 10k net worth at 15:00; your team's first hero got there at 20:00." | "That's why you lost", "unkillable", "snowballed because…" |
| Enemy Early Item | "Their Sven bought Black King Bar at 17:41 — about 11 minutes earlier than a typical core BKB." | "finished / completed / rushed to counter you", "counter-built", intent |
| Structure contradiction (enrichment) | "The enemy led for 21 minutes (12:00–33:00) with no net tower/barracks change." | "They failed to close", "wasted their lead" |
| History (all) | "across your last N {Standard / Turbo} {role} [item] matches"; "your usual (median) is …" when N ≥ 10 | "ever", "all-time", "personal record", exact percentiles, "unusually…" below N = 30 |

---

# 11. Final candidate pool

| Tier | Family | Candidate | Eligibility (summary) | Severity / ranking input | History? | Mode | Guard | Final verdict |
|---|---|---|---|---|---|---|---|---|
| A | Lane | Dramatic Lane Lead Path / Reversal | – | – | – | – | – | **REMOVE** (does not occur; blowouts obvious) |
| A | Lane | Own Lane vs Usual | cores; record in last ≤50 bucket + role; N ≥ 20 | band by N = 50 / pop p95; class 2 | required | Std + Turbo | cores only; margin | **KEEP WITH GUARD** |
| A | Lane | Extreme Opponent Start vs Your History | cores; counterpart CS ≥ pos p90 and record in last ≤50; N ≥ 20 | band by N = 50 / pos p95; class 2 | required | Std + Turbo | cores only | **KEEP WITH GUARD** |
| A | Match lead story | Comeback Win | win; deficit ≥ q (excluding final 3 min) | ladder 12.0 / 19.5 / 31.0k (Std), 18.3 / 23.7 / 33.5k (Turbo); class 1 | no | both | final 3 min | **KEEP WITH GUARD** |
| A | Match lead story | Lost From Ahead | loss; lead ≥ q (excluding final 3 min) | same; class 1 | no | both | final 3 min; wording | **KEEP WITH GUARD** |
| A | Match lead story | Major Sustained Lead Flip | latest flip, min peak ≥ q (truncated curve) | 7.9 / 12.1 / 21.9k (Std), 14.2 / 19.4 / 27.5k (Turbo); class 2 | no | both | truncation; latest flip; family | **KEEP WITH GUARD** |
| A | Hidden enemy | Enemy Stacking Edge | enemy ≥7 by 20:00, edge ≥4 | 7 / 9 / 13; class 2 | optional line | Standard only | – | **KEEP** |
| A | Hidden enemy | Vision Quick Clears | ≥4 cleared ≤90 s and ≥25% | 4 / 5 / 6; class 2 | no | both | Turbo 4; end − 5 min; lower-bound copy | **KEEP WITH GUARD** (reconstruction validated) |
| A | Hidden enemy | Vision Region Sweep | ≥3 in a region within 5 min | 3 / 4 / 5; class 3 | no | both | ≥5:00; \|lead\| < 10k; median life ≤180 s; end − 5 | **KEEP WITH GUARD** (reconstruction validated) |
| A | Hidden enemy | Enemy Smoke Volume | rate ≥1.60, ≥4, diff ≥4 | diff 4 / 6 / 8; class 2 | optional line | **Standard only** | diff ≥4; Std only | **KEEP WITH GUARD** |
| A | Hidden enemy | Smoke → Kills | enrichment rule §8 of the Smoke report | none (no band change) | no | Standard (inherits base card) | playback usable, count-matched | **KEEP as enrichment; recommend LOCK** |
| A | Hidden enemy | Enemy Early-Rich Hero | goal ≤18 / 12 min, ≥3 min before your team | gap 3 / 5 / 7 (Std), 3 / 4 / 6 (Turbo); class 2 | optional line | both | Alchemist; your team reached it; +8 min tail | **KEEP WITH GUARD** |
| A | Power spikes | Enemy Core Early Key Item | P1–P3, 8-item list, ≥10% earlier than p5 | margin 0.10 / 0.15 / 0.22; class 3 | optional line | both | item list; margin; typical time in copy | **KEEP WITH GUARD** |
| A | Power spikes | Own Key Item Timing vs Your History | fastest record, margin; N ≥ 20 | band by N = 50 / margin; class 2 | required | both | fastest only; role + patch key | **KEEP WITH GUARD** |
| B | Match story | Close Most of Game | CT v2 + share ≥0.75 + window ≥20 / 16 | NOTABLE / STRONG; class 2 | no | both | share; window; family | **KEEP WITH GUARD** |
| B | Match story | Even Then Separated | ETS v2 + pre-gap ≤7.5k + window + winner | NOTABLE / STRONG; class 2 | no | both | as listed; family | **KEEP WITH GUARD** |
| B | Match story | Lead Eroded | LE v2 + reduction rules | N / S / E; class 2 | no | both | as listed; family | **KEEP WITH GUARD** |
| B | Match story | Deficit Recovered | DR v2 + reduction rules | N / S / E; class 2 | no | both | as listed; family; result in copy | **KEEP WITH GUARD** |
| B | Match story | Late Reversal (winner-only) | enemy's last run ends in the last 25% of the window; win | N / S; class 2 | no | both | family | **KEEP** |
| B | Enrichment | Structure contradiction | appended text only | – | no | both | – | **KEEP (enrichment only)** |

---

# 12. Coverage after all final guards

## 12.1 Coverage by segment

Final contract (family guard, top 3). Values are percentages of viewpoints.

| Segment | ≥1 card | ≥2 cards | ≥3 cards | No special insight |
|---|---:|---:|---:|---:|
| **Tuning corpus** (886 matches, 8,680 viewpoints; no history; vision available) | **42.6** | 8.8 | 1.9 | **57.4** |
| Standard | 51.1 | 12.3 | 2.7 | 48.9 |
| Turbo | 32.7 | 4.6 | 1.0 | 67.3 |
| Win | 38.2 | 7.8 | 1.6 | 61.8 |
| Loss | 47.0 | 9.7 | 2.2 | 53.0 |
| Each role (team-level cards dominate) | 42.6 | 8.8 | 1.9 | 57.4 |
| **Fresh lean corpus** (9,581 viewpoints; established accounts with history; *no vision data*) | **38.9** | 7.4 | 1.0 | **61.1** |
| Standard | 49.4 | 10.5 | 1.4 | 50.6 |
| Turbo | 28.3 | 4.2 | 0.5 | 71.7 |
| Win | 34.4 | 6.4 | 0.9 | 65.6 |
| Loss | 43.5 | 8.4 | 1.0 | 56.5 |
| Carry | 40.0 | 8.0 | 0.9 | 60.0 |
| Mid | 41.8 | 8.7 | 1.4 | 58.2 |
| Offlane | 41.4 | 8.1 | 1.1 | 58.6 |
| Support | 34.2 | 5.4 | 0.6 | 65.8 |

The lean corpus has no vision fields. Vision cards covered 1.3–2.0% of viewpoints on their own in the tuning corpus, so for established users with vision data the "no insight" rate would be about 59–60%.

**Top-card mix (tuning corpus):**

| Card | Share of viewpoints |
|---|---:|
| Close Most of Game | 6.9% |
| Enemy Early-Rich | 5.4% |
| Comeback Win | 5.0% |
| Lost From Ahead | 5.0% |
| Even Then Separated | 4.9% |
| Enemy Early Item | 3.3% |
| Stacking | 3.3% |
| Lead Flip | 2.5% |
| Quick Clears | 2.0% |
| Sweep | 1.7% |
| Lead Eroded | 1.0% |
| Deficit Recovered | 0.9% |
| Smoke | 0.7% |

## 12.2 Where the coverage went

Any-card coverage, tuning corpus:

| Stage | Coverage |
|---|---:|
| Earlier research pool, Tier A + Tier B with Steady Edge and moderate signals (from the Tier B report) | 82–85% useful |
| Locked pool with pre-audit definitions (owner removals applied; Dramatic Lane still firing on blowouts) | 69.0% |
| − Dramatic Lane removed | 67.1% |
| − Enemy Early Item guard (was 67% BORING) | 62.3% |
| − Even Then Separated guard (was 57% BORING + MISLEADING) | 56.9% |
| − Close Most guard | 53.2% |
| − Smoke: Turbo removed, difference ≥ 4 | 49.9% |
| − Lead Eroded / Deficit Recovered guards | 47.6% |
| − Sweep / Quick Clears guards | 45.2% |
| − Early-Rich guard | 44.0% |
| − Lead Flip guard | **42.6%** |

**Interpretation.**
- About 15 points were lost to the owner's candidate removals and about 26 to the player-context guards.
- Every guard removed a slice that the review rated majority BORING or MISLEADING.
- The earlier "13–17% no insight" assumption no longer describes V1. **About 57–61% of viewpoints will show the generic post-match state.** This should drive the design of that state; it is not a reason to relax thresholds.

---

# 13. Implementation pseudocode

```text
CONST LADDER, TIE_ORDER, CLASS1 = {COMEBACK_WIN, LOST_FROM_AHEAD}, CLASS3 = {ENEMY_EARLY_ITEM, VISION_REGION_SWEEP}
CONST FAMILY = [COMEBACK_WIN, LOST_FROM_AHEAD, CLOSE_MOST_OF_GAME, EVEN_THEN_SEPARATED,
                LEAD_FLIP, LEAD_ERODED, DEFICIT_RECOVERED, LATE_REVERSAL]
CONST W = 50, N_CARD = 20, N_MEDIAN = 10, N_RARITY = 30

function post_match_cards(match, viewer, history):
    if not globally_eligible(match): return []
    if feeding_guard(match): return []
    b = bucket(match); side = viewer.team
    cards = []
    // ---- team / match candidates (Tier A)
    lc = lead_curve(match, side)                              // Σ own NW − Σ enemy NW per minute
    core = lc[0 : len(lc) − 3]                                // final 3 minutes excluded
    if viewer.won and max(−core) ≥ LADDER.COMEBACK[b].q: cards += card(COMEBACK_WIN, v = max(−core))
    if not viewer.won and max(core) ≥ LADDER.LOST[b].q:  cards += card(LOST_FROM_AHEAD, v = max(core))
    flips = sustained_flips(core, threshold = 1500, run = 3, new_run_start ≥ lane_end(b))
    q = [f for f in flips if min(f.peak_before, f.peak_after) ≥ LADDER.FLIP[b].q]
    if q: cards += card(LEAD_FLIP, flip = last(q), v = min(last(q).peaks))
    if b == STANDARD: maybe_add(ENEMY_STACKING)                // enemy ≥7 by 20:00 and edge ≥4
    idents = reconstruct_ward_identity(match, side)           // playback exact if usable, else sentry rule
    maybe_add(VISION_QUICK_CLEARS, idents); maybe_add(VISION_REGION_SWEEP, idents, lc)
    if b == STANDARD: maybe_add(ENEMY_SMOKE_VOLUME) and maybe_enrich(SMOKE_TO_KILLS, playback)
    maybe_add(ENEMY_EARLY_RICH); maybe_add(ENEMY_EARLY_ITEM)
    // ---- Tier B (frozen classifier)
    shape = classify_shape(match, side)                       // label, detail, runs, confidence
    if shape.confidence ≥ 0.7:
        maybe_add_tier_b(shape, viewer.won)                   // CLOSE / ETS / LE / DR with §9 guards
        maybe_add(LATE_REVERSAL, shape, viewer.won)
    // ---- history cards (viewer only)
    if viewer.role != SUPPORT and counterpart_resolved(viewer):
        win = history.last(W, key = (b, viewer.role), metric = lane_gap)
        if len(win) ≥ N_CARD and is_record(viewer.lane_gap, win, margin = 100 if b == STANDARD else 200):
            cards += history_card(OWN_LANE_VS_USUAL, N = len(win))
        win = history.last(W, key = (b, viewer.role), metric = counterpart_cs)
        if len(win) ≥ N_CARD and viewer.counterpart_cs ≥ POP_P90[b][counterpart_pos]
           and viewer.counterpart_cs > max(win):
            cards += history_card(OPP_START_VS_HISTORY, N = len(win))
    for item in SPIKE_ITEMS ordered:
        t = viewer.first_purchase(item); if t is null: continue
        win = history.last(W, key = (b, viewer.role, item, major_patch(match)), metric = first_purchase)
        if len(win) ≥ N_CARD and t ≤ min(win) − (60 if b == STANDARD else 30):
            cards += history_card(OWN_ITEM_VS_HISTORY, item, N = len(win)); break
    // ---- severity
    for c in cards:
        if c.tier == A and c.id in LADDER: (c.level, c.band) = ladder_level(c.magnitude, LADDER[c.id][b])
        else if c.tier == B:               (c.level, c.band) = tier_b_band(c, b)          // §2.2
        else:                              (c.level, c.band) = history_band(c)            // §2.2
    return select(cards)

function select(cards):
    fam = [c for c in cards if c.id in FAMILY]
    keep = argmin over fam of FAMILY.index(c.id)               // null if fam empty
    pool = [c for c in cards if c.id not in FAMILY] + ([keep] if keep else [])
    sort pool by (class(c.id) asc, c.band desc, c.level desc, TIE_ORDER.index(c.id) asc)
    return pool[0 : min(3, len(pool))]

function class(id): return 1 if id in CLASS1 else 3 if id in CLASS3 else 2

function history_line_allowed(N, claim):
    if N < N_MEDIAN: return false
    if claim == MEDIAN: return true
    if claim == RECORD: return N ≥ N_CARD
    if claim in {TOP3, TOP10PCT, UNUSUAL}: return N ≥ N_RARITY and metric_is_continuous
    return false                                              // "ever", "all-time", exact percentiles never
```

---

# 14. Research appendix

## 14.1 STRATZ calls (this pass)

Workspace ledger `.local/stratz-probe/final-audit-2026-09-16/ledger.jsonl`: **896 logged requests**, 878 HTTP 200 and 18 HTTP 403.

| Purpose | Logged requests | Result |
|---|---:|---|
| Account discovery (first 100 parsed matches for 90 candidate accounts, 6 per request) | 27 | 12 initially failed with 403 "different IP Addresses" and were re-run; 87 accounts had full pages |
| History paging (31 selected accounts, pages 2–4) | 16 | 12,137 history rows |
| Lean ten-player stats (16 matches per request) | 713 | 11,394 matches fetched; 9,930 eligible tracked-account rows; 9,582 fresh evaluation viewpoints |
| Batch-size probes | 6 | all 403 IP-lock; lean batch of 16 then succeeded in production runs |
| heroStats introspection and sample | 4 | aggregate item-timing buckets drop the tails, so they are unusable for hero-level p5 |
| Playback availability probes | 2 | both non-null (2026-09-16 evening) |
| Fresh holdout stats (8 matches per request) | 18 | 108 matches |
| Fresh holdout playback (1 per request) | 110 | **34 non-null (31%)** for matches ≤20 days old |

- **Retries:** the client retried 403 IP-lock responses and 429/5xx errors internally (up to 16 attempts, 45 s apart for 403). Those extra physical attempts are not logged separately.
- **403 cause:** the "different IP Addresses" error coincided with the token's hourly quota falling faster than this workspace was spending it, which suggests concurrent use of the same token from another address.
- **Token handling:** read from the environment, never printed.
- **Data volume and privacy:** 215.6 MB of responses. Account ids stay local; accounts appear as h00–h30.

## 14.2 Corpora

| Corpus | Size | Use |
|---|---|---|
| Tuning corpus (earlier phases) | 886 eligible matches, 8,680 non-feeding viewpoints, 1,736 team units; patches 180 / 181 / 182 | Candidate audit, ladders, ranking review (70), coverage |
| Lean history corpus (new) | 31 accounts, 9,930 eligible rows (5,075 Std / 4,855 Turbo) | History availability, stability, patch drift, hero typicality |
| Lean fresh viewpoints | 9,582 (matches not in the tuning corpus); Tier B classified with frozen thresholds plus 34-perturbation confidence | Holdout-3, ranking review (50), coverage with history |
| Fresh playback holdout | 33 matches / 66 team units with playback + stats | Vision reconstruction and Smoke→Kills replication |

**Exclusions.**
- Lean corpus: leaver 628, no stats 1,229, missing (fetch gaps) 338, other mode 3, under 10 minutes 9.
- Feeding-guard matches were excluded from every card evaluation.

## 14.3 Rating volume

| Round | Ratings |
|---|---:|
| Round 1 (Tier A + Tier B) | 466 |
| Dramatic-lane census | 40 |
| History round 1 | 90 |
| Holdout v2 | 264 |
| Holdout-2 (v3) | 68 |
| Holdout-3 (lean, final) | 84 |
| Recap sets | 60 |
| Ranking review | 120 viewpoints / 332 cards |

Files: `ratings_*.json`, `review-sheets/`.

## 14.4 Fresh playback holdout detail (vision)

- 66 team units; 933 observers placed per stats (915 per playback); 281 enemy observer clears per stats (273 in playback truth).
- **Identity precision:** tier A (sentry rule) 99.0%; tier C (single alive candidate) 100%; overall **99.1%**.
- **Coverage:** tier A 75.8%, tier C 3.2%, unresolved 21%.
- **Region correct:** 99.1%. **Quick-clear classification agreement:** 99.5%. **Mean absolute quick-count error:** 0.41.

**Rule agreement (truth vs estimate):**

| Rule | Both yes | Missed | False positive | Both no |
|---|---:|---:|---:|---:|
| Quick Clears | 3 | 2 | 0 | 61 |
| Sweep | 3 | 1 | 0 | 62 |

The earlier 92% figure was tuned and scored on the same 18 matches; the fresh result supersedes it.

## 14.5 Fresh playback holdout detail (Smoke → Kills)

- **Units:** 66 team units; playback Smoke events matched stats counts for all 66 (72 other rows had no item events and were treated as no playback).
- **Rule fires:** 15 of 66 units (23%; the earlier spike found 26%).
- **Fired teams:** 62 followed Smokes against 38.2 expected at matched ordinary moments (×1.62). Earlier spike: 44 vs 27.3.
- **Suppressed teams with ≥3 Smokes:** 47 vs 49.7 expected (chance).
- **Base rate:** a kill within 60 s at ordinary moments happened 55.6% of the time; after a Smoke, 67.6%.
- **Standard Smoke-card overlap:** 3 of 5 qualifying Standard units were enriched.

## 14.6 External sources

**Product and statistics references (history design)**

| Source | What it informed |
|---|---|
| [Strava — Best Efforts overview](https://support.strava.com/hc/en-us/articles/19685360245005-Best-Efforts-Overview) and [All-Time PRs](https://support.strava.com/hc/en-us/articles/216918487-All-Time-PRs) (accessed 2026-09-16) | Automatic "best efforts" are computed only from uploaded activities, shown as the top three efforts. "All-Time PRs" are a separate, manually entered record. Informed separating in-app records from "ever" claims. |
| [Hevy — Live PR](https://www.hevyapp.com/features/live-pr/) (accessed 2026-09-16) | No PR is awarded the first time an exercise is logged, because there is nothing to compare with. Consistent with "no record claim without prior history". |
| Garmin Connect personal-record criteria (support page returned 403) | Not used. |
| Record statistics: [Extremes and Records (arXiv 1907.00944)](https://arxiv.org/pdf/1907.00944) and [arXiv physics/0509088](https://arxiv.org/pdf/physics/0509088) | For independent values, P(the n-th observation is a record) = 1/n. Used to predict record fire rates (1/(N+1)); measured rates matched. |

**Dota mechanics and analytics**

| Source | What it informed |
|---|---|
| [STRATZ — A Tale of Three Lanes](https://medium.com/stratz/a-tale-of-three-lanes-e4242733a8ee) | Lane outcomes judged at 10:00 (7:00 Turbo); side lanes drawn about 26% and mid about 32%; stomps 8–13%. Supports the finding that lanes separate early and rarely reverse. |
| [Dota 2 patches 7.39 / 7.40 / 7.41](https://www.dota2.com/patches/7.41) (via search summary) | Patch-scope decision (§6): map rework, neutral-item rework, talent and Roshan changes. |
| [Liquipedia — Game Modes](https://liquipedia.net/dota2/Game_Modes) and [Turbo guide (neznakov)](https://neznakov.ru/guides-turbo-rezhim-en) (via search summary) | Turbo: doubled building bounty, 25% faster respawns, halved Roshan respawn, no gold loss on death. Explains Turbo's different Smoke, stack and lane magnitudes. |
| [Liquipedia — Stacking](https://liquipedia.net/dota2/Stacking) (via search summary) | The stacker receives a share of the bounty. Supports stacking as real, hidden economic work. |

**Player-perspective sources**

| Source | What it informed |
|---|---|
| [neznakov — How to analyze your Dota 2 matches](https://neznakov.ru/guides-analiz-matchej-en) | Deaths are the main takeaway; item timings "on time or late" matter; focus on 1–2 recurring points. Supports item-timing and personal-record cards over stat dumps. |
| [BSJ — replay analysis guide](https://bsjdota.com/blog/how-to-analyze-your-dota-2-matches-with-replays/) (search summary) | Coaches' focus areas: deaths, item timings, vision. |
| [Steam discussion — Dota Plus value](https://steamcommunity.com/app/570/discussions/0/4334230664481837343) | Players distrust automated "match quality" labels and item suggestions that contradict what they experienced. Supports "no verdicts, only facts". |
| [ONE Esports — Dota 2 post-game analytics](https://www.oneesports.gg/dota2/how-to-view-post-game-analytics-in-dota-2/) and [Dota Plus](https://www.dota2.com/plus) | Dota Plus compares a player to bracket averages. Our cards instead compare to the player's own history and hidden enemy behaviour, so they do not duplicate it. |
| [Dotabuff — Better Life for Supports?](https://www.dotabuff.com/blog/2016-12-23-better-life-for-supports) and [winio — What actually predicts wins](https://winio.ai/blog/articles/what-actually-predicts-wins-in-dota-2) | End-game GPM/XPM mostly reflect winning, and raw economy comparisons across roles mislead. Supports role-scoped history, cores-only lane cards, and no support economy verdicts. |

## 14.7 Reddit / forum themes and the Reddit limitation

Reddit could not be read: the fetch tool refused old.reddit.com, and the in-app browser blocked reddit.com under its safety policy. Search results did not surface Reddit threads.

Player-expectation themes therefore come from Steam discussions, coaching guides and analyst blogs. Recurring themes:
1. Stats that restate the result (end-game GPM, "you were ahead") are called useless.
2. Players value knowing *when* things happened (item timings, when a lane or game turned).
3. Role-blind comparisons (support economy against carries) are resented.
4. Automated verdicts and "quality ratings" that contradict how the game felt destroy trust.
5. Vision, stacking and Smoke are recognised as invisible work.

These themes were used only to shape the rubric, not as data facts.

## 14.8 Limitations and remaining uncertainty

- **Single rater.** No player panel; owner re-rating is still advised before copy is locked.
- **Thresholds come from one corpus.**
  - Ladders and population gates come from 886 matches, mostly tracked accounts. Refit on production data at launch and after major patches (drift monitoring as in the Tier B report).
  - The lean corpus confirms that frequencies transfer: for example Enemy Early-Rich 7.4% vs 7.2%, Smoke 1.7% vs 1.3%, Close Most 6.4% vs 8.1%.
- **History evidence.**
  - Only 31 accounts, mostly active players; three have short histories.
  - Within-account patch comparisons rest on 4–7 accounts. The BKB shift is consistent in sign but small in sample, which is why the patch scope is limited to item timings.
- **Ranking evidence.**
  - 120 viewpoints; the class-3 membership rests on 32 and 15 card appearances.
  - About 20% top-1 disagreement remains; the rule is the best of the simple families tested, not an oracle.
- **Smoke→Kills.** Two small samples (34 + 66 units). The direction is replicated; the 70% and f ≥ 2 cut points remain provisional.
- **Playback availability.** 31% of recent matches today; 0% on the two previous days. Both enrichments must stay optional.
- **Vision reconstruction.** Validated on 33 fresh matches, all from the current patch. Re-check after any patch that changes ward or sentry mechanics.
- **Hero-specific effects.** Handled only through the Alchemist exclusion and naming heroes in copy; hero-conditioned thresholds were not built (owner constraint on corpus size).

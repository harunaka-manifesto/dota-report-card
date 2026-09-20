# Post-Match Insights — Single Source of Truth (V1)

**Project:** Dota Tracker
**Area:** Deterministic post-match insight engine
**Status:** FINAL — NORMATIVE. Owner-locked 2026-09-17.
**Contract version:** `post-match-insights 1.0.0`
**Machine-readable companion:** [`post-match-final-audit-data/final-candidate-contract.json`](post-match-final-audit-data/final-candidate-contract.json)

---

# 1. Status and authority

1. This document is the normative engineering and product contract for V1 Post-Match Insights.
2. It supersedes every earlier recommendation and decision document for **normative behaviour**, including:
   - `POST-MATCH-INSIGHT-DECISIONS-V1.md` (kept as the decision history);
   - `POST-MATCH-FINAL-RANKING-HISTORY-PLAYER-AUDIT.md`;
   - `post-match-tier-b-match-shape-validation-v1.md` and `post-match-tier-b-validation-data/tier-b-shape-definitions.json`;
   - `post-match-deterministic-candidate-validation-v1.md`, `post-match-intelligence-deep-research-v2.md`, `post-match-intelligence-feasibility-v1.md`;
   - `VISION-INSIGHT-ENRICHMENT-RESEARCH.md`, `SMOKE-TO-KILLS-VALIDATION.md`.
3. Those documents remain **supporting evidence**. Their candidate tables, thresholds and open questions are not the current product menu.
4. This Markdown file and the JSON contract MUST agree. If they ever disagree, the disagreement is a defect. Fix it; do not pick one silently.
5. Reference implementations of every rule exist as research code in `post-match-final-audit-data/research-code/`, `post-match-tier-b-validation-data/research-code/` and `vision-insight-research-code/`. Where this document and the research code differ, this document wins. The known differences are listed in §19.2.

Keywords MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are used as in RFC 2119.

---

# 2. Scope

**In scope**

- Insight candidate generation from one parsed match and the account's retained history.
- Eligibility, missing-data behaviour, player-context guards.
- History comparators, windows and claim levels.
- Severity bands and levels.
- The Match Lead Story suppression rule, ranking and selection of 0–3 cards.
- Enrichment lines (Smoke → Kills, structure contradiction, history lines).
- Semantic restrictions on what any card may claim.
- Versioning of insight outputs.

**Out of scope** (owned elsewhere)

- UI visuals, card layout, animation.
- Final consumer prose. This document fixes **semantic** claims only; copy templates are written later inside these limits.
- The content and design of the normal / no-special-insight post-match state.
- Progression, baselines, trends, Personal Bests (`progress-and-history-v1.md`, `role-metrics-and-baselines-v1.md`).
- Role classification and correction (`role-resolution-and-correction-v1.md`).
- Match lifecycle and ingestion (`match-lifecycle-v1.md`).
- Free / Pro entitlement and subscription gating. No gating of insight cards is decided here.

---

# 3. Core principles

1. **Deterministic production.** No LLM analyses any production match. Every card comes from STRATZ fields, deterministic derived calculations, eligibility rules, guards, history comparators, severity ladders, the ranking rule, and predefined semantic templates. LLMs MAY be used offline for research only.
2. **At most three cards.** A recap shows 0, 1, 2 or 3 cards. Three is a ceiling, not a target. The engine MUST NOT fill empty slots.
3. **Quality over coverage.** A card type must be product-approved (§8). A high score MUST NOT rescue a boring or misleading type. "Not boring wins."
4. **Tier is taxonomy, not priority.** Tier A does not automatically outrank Tier B. There is no Tier A bonus and no Tier B penalty.
5. **No balancing.** No own/enemy balancing, no positive/negative balancing, no win/loss balancing.
6. **No generic diversity engine.** No one-card-per-family rule, no redundancy groups, no merge logic, no composite cards, no diversity quotas. The **only** combination rule is the Match Lead Story suppression rule (§12.2), which is empirically justified.
7. **Sequence, never cause.** Cards may say *after, before, within, followed by, while, during*. They MUST NOT imply causality (§13).
8. **Missing is not zero.** Missing source data makes a candidate ineligible; it never becomes a zero value (§6).
9. **Standard and Turbo never mix.** Thresholds, distributions and history cohorts are per mode bucket.
10. **Playback is optional.** No card depends on playback. Playback can only add the Smoke → Kills enrichment.
11. **No visibility claims.** Ward data never supports claims about what anyone could see.

---

# 4. Terminology

| Term | Definition |
|---|---|
| **Candidate** | An approved card type, identified by a canonical ID such as `COMEBACK_WIN`. |
| **Occurrence / card** | One candidate firing for one viewpoint of one match, with its slots, band, level and optional enrichments. |
| **Viewpoint** | One tracked player (the viewer) in one match. Team-unit candidates evaluate the viewer's team. |
| **Tier A** | Anomaly-like, exceptional, hidden or history-personal facts. |
| **Tier B** | Match-shape context from the frozen Tier B classifier. Not "weaker Tier A". |
| **Bucket** | `STANDARD` (gameMode `ALL_PICK` or `ALL_PICK_RANKED` with lobbyType `RANKED` or `UNRANKED`) or `TURBO` (gameMode `TURBO`). Nothing else is eligible. |
| **Effective role** | The viewer's current role from the Role Resolution SSOT: carry, mid, offlane or support. STRATZ `position` 1/2/3/4–5 was the research proxy. |
| **Core** | Effective role carry, mid or offlane. |
| **Lane counterpart** | Carry → enemy `POSITION_3`; mid → enemy `POSITION_2`; offlane → enemy `POSITION_1`. Resolved only if exactly one such enemy exists **and** its map lane equals the viewer's. Map lane: `MID_LANE` → mid; `SAFE_LANE` → bot (Radiant) / top (Dire); `OFF_LANE` → top (Radiant) / bot (Dire). |
| **L(t)** | Team net-worth lead at minute t: Σ your players' `stats.networthPerMinute[t]` − Σ enemy players' values. Index t is read as t:00. The curve ends at the first t where any of the ten arrays lacks a value. All constants were fitted under this indexing; implementations MUST NOT re-index. |
| **Core curve** | L without its final 3 samples: `L[0 .. len(L)−4]` (if `len(L) ≤ 3`, `L[0..0]`). |
| **R(t)** | `L(t) / (your team NW(t) + enemy NW(t))`; 0 if the denominator is 0. |
| **CS(p, t)** | Σ `stats.lastHitsPerMinute[0 .. t−1]`; unknown if the array has fewer than t entries. |
| **NW(p, t)** | `stats.networthPerMinute[t]`. |
| **Checkpoints** | Standard: late 10, lane end 12, stacks 20, net-worth goal 10,000. Turbo: late 8, lane end 9, net-worth goal 15,000. |
| **History comparator** | The cohort key and window used to compare the current value with the viewer's own prior values (§7). |
| **N** | Number of values in the history window, 0–50. |
| **Severity band** | NOTABLE (1), STRONG (2), EXTREME (3). |
| **Level** | A continuous position inside the candidate's ladder, used to order cards within a band. |
| **Ranking class** | 1, 2 or 3. **Lower number ranks first.** |
| **Match Lead Story group** | The eight story candidates of which at most one card is kept (§12.2). |
| **Enrichment** | An optional secondary line attached to a displayed card. It never creates a card and never changes band, level or rank. |
| **Playback** | STRATZ `playbackData`. Available only for recent matches and operationally unreliable. |
| **Frozen source checkpoint** | The provider data the match lifecycle froze when the match became READY (`match-lifecycle-v1.md`). |

---

# 5. Processing pipeline

```text
parsed match (frozen source checkpoint) + viewer + entitled retained history
  1. global eligibility ............................. fail → NOT_ELIGIBLE(reason), 0 cards
  2. feeding guard .................................. fail → NOT_ELIGIBLE(FEEDING), 0 cards
  3. shared derivations: L, core curve, R, Tier B classification + shape_confidence,
     ward reconstruction, lane counterpart
  4. per-candidate eligibility: source checks, mode, role, thresholds, guards
  5. history-required candidates: comparator window, N ≥ 20, record rule
  6. severity: band + level for each eligible card
  7. enrichments: Smoke → Kills, structure contradiction, history lines
  8. Match Lead Story suppression: keep ≤ 1 group card
  9. sort: rank class ↑, band ↓, level ↓, tie order ↑
 10. select the first min(3, n) cards; n may be 0
  → status EVALUATED, cards[0..3]
```

## 5.1 Global eligibility

A match is evaluated only if **all** hold:

1. Bucket is `STANDARD` or `TURBO`.
2. `numHumanPlayers == 10`.
3. `durationSeconds ≥ 600`.
4. All ten players have a non-empty `stats.networthPerMinute`.
5. No player has `leaverStatus` in {`ABANDONED`, `AFK`, `DISCONNECTED_TOO_LONG`, `NEVER_CONNECTED`, `NEVER_CONNECTED_TOO_LONG`, `FAILED_TO_READY_UP`, `DECLINED_READY_UP`}.
6. Each team has exactly one player at each of `POSITION_1` … `POSITION_5`.

Otherwise the output is `NOT_ELIGIBLE(reason)` with 0 cards.

## 5.2 Feeding guard

If any player has **≥ 8** `deathEvents` with `time < 600` (Standard) / `< 480` (Turbo), the match gets **no card of any kind**: `NOT_ELIGIBLE(FEEDING)`. One player's feeding distorts every economy fact. Feeding-guarded matches also never enter any history window.

## 5.3 Output

```text
InsightResult {
  status:           EVALUATED | NOT_ELIGIBLE(reason)
  contract_version: "post-match-insights 1.0.0"
  cards:            [Card]  // length 0..3, in display order
}
Card {
  candidate_id, tier, family, band, level, rank_class,
  slots { ... },              // candidate-specific facts (§9)
  enrichments [ ... ],        // optional (§10, §11, §7.6)
  history_line?               // optional (§7.6)
}
```

`EVALUATED` with 0 cards and `NOT_ELIGIBLE` both render the normal post-match state. The distinction exists for diagnostics and analytics.

---

# 6. Eligibility and lifecycle dependencies

## 6.1 Missing data is never zero

| Situation | Behaviour |
|---|---|
| Match unparsed, or any player lacks `networthPerMinute` | `NOT_ELIGIBLE`; 0 cards. |
| Match not yet READY | The engine is not run. Insights are computed from the frozen source checkpoint. |
| Any field a candidate needs is null/absent for a required player | That candidate is ineligible. Other candidates still evaluate. |
| `campStack` missing or shorter than 20 entries for any player, or duration < 20:00 | `ENEMY_STACKING` ineligible. |
| `stats.wards` missing for any player, or `wardDestruction` missing for any enemy player | Both vision cards ineligible for that team. An empty array from a present field is a real zero (stats arrays were validated complete). |
| `itemUsed` missing for any player | `ENEMY_SMOKE_VOLUME` ineligible. |
| `itemPurchases` missing for a player | That player contributes no item timings; item candidates that need that player are ineligible. |
| `lastHitsPerMinute` shorter than the late checkpoint for the counterpart | `OPP_START_VS_HISTORY` ineligible. |
| Lane counterpart unresolved | `OWN_LANE_VS_USUAL` and `OPP_START_VS_HISTORY` ineligible. |
| `towerDeaths` absent (null) | Tier B cards are ineligible (the classifier's OS clause and the structure enrichment need structures). A present, empty array means 0 structures destroyed. |
| Tier B window < 9 minutes (`SHORT_WINDOW`), label `UNCLEAR`, or `shape_confidence < 0.7` | No Tier B card (includes Late Reversal). |
| Viewer's effective role unknown | History-required cards ineligible. Team-unit cards still evaluate. |
| History N below the gate | History card ineligible; enemy cards render without a history line (§7). |
| Playback null, item-use events all empty, or Smoke counts mismatched | Smoke → Kills enrichment absent. The base Smoke card is unaffected. |
| A clear cannot be matched to a ward | It is unresolved: not identified, not counted. Vision counts are lower bounds (§10). |

## 6.2 Lifecycle integration

1. Insights MUST be computed from the **frozen source checkpoint** of a READY match. Passive provider enrichment after READY (for example playback arriving later) is ignored, consistent with `match-lifecycle-v1.md`.
2. The history input is the account's currently entitled retained history, restricted to matches strictly before the evaluated match (§7.1).
3. The lifecycle MAY attempt a bounded playback fetch before READY. It MUST NOT delay READY to wait for playback.

---

# 7. History contract

## 7.1 Window

- **Prior** = a match of the same account strictly earlier in `(startDateTime, matchId)` order.
- **Comparable** = globally eligible, not feeding-guarded, same comparator key, and the metric is measurable in that match. An unmeasurable metric is excluded, never counted as zero.
- **Window** = the most recent **50** comparable prior values in the currently entitled retained history. There is no calendar limit. Unlimited lifetime history MUST NOT be used.
- **N** = the number of values in the window (0–50). N MUST be stated in any history wording.
- Priors use their own current effective role. A role correction moves a match between cohorts.

## 7.2 Claim levels

| N | Allowed |
|---|---|
| **< 10** | No historical claim of any kind. |
| **10–19** | A median-only secondary line on an already-eligible card ("the median across your last 14 …"). History MUST NOT create a card. |
| **≥ 20** | Record wording: "fastest / best / worst / highest / most across your last N {mode} {role} [item] …". History-required cards become eligible. |
| **≥ 30** | Rarity wording, **continuous metrics only**: "one of your 3 fastest across your last N", "top 10% of your last N", "unusually early for you". |
| **Never** | "ever", "all-time", "personal record", "PB", exact percentiles ("top 7%"), fake precision beyond the sample, population data presented as "your usual". |

Definitions:

- **"Your usual"** = the window median. It is used only for the viewer's own metrics.
- **Record**: strict, and it must beat the previous record by the card's margin. An exact tie is never a record.
- **Top 3**: fewer than 3 window values are better than the current value, and it is not a record.
- **Top 10% / unusually**: the current value is better than the window's 90th percentile (10th for timings), nearest-rank.
- **Continuous metrics:** own lane gap, counterpart CS, own item time, enemy item time, enemy Smoke rate.
- **Integer metrics (no rarity wording):** enemy stacks, enemy goal minute.

## 7.3 Comparator cohorts

| Use | Comparator key | Metric | Direction | Record margin |
|---|---|---|---|---|
| `OWN_LANE_VS_USUAL` | bucket + effective role (cores only) | NW(viewer, late) − NW(counterpart, late) | best and worst | 100 gold (Std) / 200 (Turbo) |
| `OPP_START_VS_HISTORY` | bucket + effective role (cores only) | CS(counterpart, late) | highest | strict |
| `OWN_ITEM_VS_HISTORY` | bucket + effective role + item + **major patch** | first purchase time | **fastest only** | 60 s (Std) / 30 s (Turbo) |
| Enemy Early-Rich line | bucket | earliest enemy net-worth-goal minute | earliest | strict |
| Enemy Stacking line | bucket | enemy stacks by 20:00 | highest | strict |
| Enemy Smoke Volume line | bucket | enemy Smoke uses per 10 minutes | highest | strict |
| Enemy Early Item line | bucket + item + **major patch** | earliest enemy P1–P3 first purchase of that item | earliest | 60 s (Std) / 30 s (Turbo) |

- Hero is never part of a key (only 11.5% availability at N ≥ 20).
- Enemy-team metrics do not depend on the viewer's role, so role is never part of their key.
- Slowest item records are removed.

## 7.4 Patch rule

- **Only item-timing comparisons** (own item card, enemy item line) require the **same major patch** (7.xx; lettered sub-patches are the same major patch).
- Reason: BKB first-purchase timing moved about +2 to +2.5 minutes between 7.39 and 7.40 within accounts; lane gap, counterpart CS, stacks, Smoke rate and goal minutes did not drift materially.
- Same-patch gating MUST NOT be applied to any other comparison.

## 7.5 Fallback

- History-required cards are simply absent below N = 20. The recap is not padded.
- Enemy cards render without a history line below N = 10 (and without record wording below N = 20).
- The engine MUST NOT invent a personal baseline or put population numbers into "your usual" copy.
- A new or free-bootstrap user (30 matches per bucket at link time) reaches N ≥ 20 for role cohorts in only 0–34% of evaluations. This is expected, not a defect.

## 7.6 History lines on cards

- At most **one** history line per card.
- Precedence: record (N ≥ 20) > rarity (N ≥ 30, continuous metric) > median (N ≥ 10).
- History lines MUST NOT change eligibility, band, level or rank.
- **Hosts:**
  - `ENEMY_EARLY_RICH`, `ENEMY_STACKING`, `ENEMY_SMOKE_VOLUME`, `ENEMY_EARLY_ITEM` MAY carry an enemy-cohort line. Enemy lines are phrased about the enemy teams the viewer faced ("the earliest enemy BKB across your last 34 Standard matches"), never as "your usual".
  - The three history-required cards carry their record as the headline and MAY show the window median as a secondary fact.

## 7.7 Evidence summary

31 real accounts, 9,930 usable history rows (about 11.8k fetched before filtering). Share of "record across your last N" claims that stay in the top 5% of a longer 60-match reference:

| N | 3 | 10 | 20 | 30 |
|---|---|---|---|---|
| Record precision | 19–27% | 51–63% | **80–90%** | 91–100% |

Rarity claims reach ≥ 80% precision only at N = 30. The old universal "≥ 10 prior matches" record rule is superseded.

---

# 8. Candidate registry

17 card types and 2 enrichments ship in V1.

| Tier / family | Count |
|---|---|
| Tier A — Lane Story | 2 |
| Tier A — Match Lead Story | 3 |
| Tier A — Hidden Enemy Activity | 5 (+ Smoke → Kills enrichment) |
| Tier A — Power Spikes & Item Timings | 2 |
| Tier B — Match Lead Story (match shape) | 5 (+ structure-contradiction enrichment) |
| **Total** | **17 cards + 2 enrichments** |

## 8.1 Registry table

"Story" = member of the Match Lead Story group, with its priority (§12.2). Ladders are (NOTABLE q, STRONG s, EXTREME e); "hist" means the history band rule (§9.0). Class 1 ranks before 2, and 2 before 3.

| ID | Name | Tier | Family | Mode | Role | History | Patch | Playback | Metric | Qualify | Severity | Class | Story |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `COMEBACK_WIN` | Comeback Win | A | Match Lead Story | Std + Turbo | all | none | – | – | max enemy lead on core curve | ≥ 12,000 / 18,300, and won | 12,000 / 19,500 / 31,000; Turbo 18,300 / 23,700 / 33,500 | 1 | 1 |
| `LOST_FROM_AHEAD` | Lost From Ahead | A | Match Lead Story | Std + Turbo | all | none | – | – | max own lead on core curve | ≥ 12,000 / 18,300, and lost | same as Comeback | 1 | 2 |
| `LEAD_FLIP` | Major Sustained Lead Flip | A | Match Lead Story | Std + Turbo | all | none | – | – | min(peak before, peak after) of latest flip | ≥ 7,900 / 14,200 | 7,900 / 12,100 / 21,900; Turbo 14,200 / 19,400 / 27,500 | 2 | 5 |
| `OWN_LANE_VS_USUAL` | Own Lane vs Your Usual | A | Lane Story | Std + Turbo | cores | required, N ≥ 20 | – | – | own lane NW gap at late | best/worst record by ≥ 100 / 200 | hist | 2 | – |
| `OPP_START_VS_HISTORY` | Extreme Opponent Start vs Your History | A | Lane Story | Std + Turbo | cores | required, N ≥ 20 | – | – | counterpart CS at late | ≥ position p90, strict record | hist | 2 | – |
| `OWN_ITEM_VS_HISTORY` | Own Key Item Timing vs Your History | A | Power Spikes & Item Timings | Std + Turbo | all | required, N ≥ 20 | same major | – | own first purchase time | fastest by ≥ 60 / 30 s | hist | 2 | – |
| `ENEMY_STACKING` | Enemy Stacking Edge | A | Hidden Enemy Activity | **Std only** | all | optional line | – | – | enemy stacks by 20:00 | ≥ 7 and edge ≥ 4 | 7 / 9 / 13 | 2 | – |
| `VISION_QUICK_CLEARS` | Vision Quick Clears | A | Hidden Enemy Activity | Std + Turbo | all | none | – | not used | identified clears ≤ 90 s | ≥ 4 and ≥ 25% of placed | 4 / 5 / 6 | 2 | – |
| `VISION_REGION_SWEEP` | Vision Region Sweep | A | Hidden Enemy Activity | Std + Turbo | all | none | – | not used | identified clears in one region within 5 min | ≥ 3 | 3 / 4 / 5 | **3** | – |
| `ENEMY_SMOKE_VOLUME` | Enemy Smoke Volume | A | Hidden Enemy Activity | **Std only** | all | optional line | – | enrichment only | enemy − own Smoke uses | rate ≥ 1.60, enemy ≥ 4, **edge ≥ 4** | 4 / 6 / 8 | 2 | – |
| `ENEMY_EARLY_RICH` | Enemy Early-Rich Hero | A | Hidden Enemy Activity | Std + Turbo | all | optional line | – | – | minutes before your team's first to the goal | goal ≤ 18 / 12 min, gap ≥ 3 | 3 / 5 / 7; Turbo 3 / 4 / 6 | 2 | – |
| `ENEMY_EARLY_ITEM` | Enemy Core Early Key Item | A | Power Spikes & Item Timings | Std + Turbo | all | optional line | line only | – | (p5 − t) / p5 | ≥ 0.10 | 0.10 / 0.15 / 0.22 | **3** | – |
| `CLOSE_MOST_OF_GAME` | Close Most of Game | B | Match Lead Story | Std + Turbo | all | none | – | – | close share | CT label, share ≥ 0.75, window ≥ 20 / 16 | NOTABLE / STRONG | 2 | 3 |
| `EVEN_THEN_SEPARATED` | Even Then Separated | B | Match Lead Story | Std + Turbo | all | none | – | – | separation minute, pre-gap | ETS label, pre-gap ≤ 7,500, window ≥ 18 / 20, separator won | NOTABLE / STRONG | 2 | 4 |
| `LEAD_ERODED` | Lead Eroded | B | Match Lead Story | Std + Turbo | all | none | – | – | gold peak, gold erosion | LE label + reduction guards | NOTABLE / STRONG / EXTREME | 2 | 6 |
| `DEFICIT_RECOVERED` | Deficit Recovered | B | Match Lead Story | Std + Turbo | all | none | – | – | mirror of Lead Eroded | DR label + mirror guards | NOTABLE / STRONG / EXTREME | 2 | 7 |
| `LATE_REVERSAL` | Late Reversal | B | Match Lead Story | Std + Turbo | all | none | – | – | peak enemy lead in last run | won; enemy's last run ends in last 25% | NOTABLE / STRONG | 2 | 8 |
| `SMOKE_TO_KILLS` | Smoke → Kills (enrichment) | A | Hidden Enemy Activity | Std (inherits) | – | none | – | **required** | Smokes followed by a kill | §11 | none | – | – |
| `STRUCTURE_CONTRADICTION` | Structure contradiction (enrichment) | B | Match Lead Story | Std + Turbo | – | none | – | – | net structures during a lead run | §9.17 | none | – | – |

Player-context guards, safe claims and forbidden claims for every row are in §9 and §13.

## 8.2 Tie order

Used only when class, band and level are exactly equal (after rounding level to 3 decimals):

1. `COMEBACK_WIN`
2. `LOST_FROM_AHEAD`
3. `EVEN_THEN_SEPARATED`
4. `OWN_LANE_VS_USUAL`
5. `ENEMY_SMOKE_VOLUME`
6. `ENEMY_STACKING`
7. `LEAD_ERODED`
8. `OWN_ITEM_VS_HISTORY`
9. `VISION_QUICK_CLEARS`
10. `CLOSE_MOST_OF_GAME`
11. `LEAD_FLIP`
12. `DEFICIT_RECOVERED`
13. `ENEMY_EARLY_RICH`
14. `OPP_START_VS_HISTORY`
15. `LATE_REVERSAL`
16. `ENEMY_EARLY_ITEM`
17. `VISION_REGION_SWEEP`

---

# 9. Candidate specifications

## 9.0 Shared severity rules

**Ladder level** for a magnitude v and ladder (q, s, e):

```text
v < q          → ineligible
q ≤ v < s      → level = (v − q) / (s − q)                band NOTABLE (1)
s ≤ v < e      → level = 1 + (v − s) / (e − s)            band STRONG (2)
v ≥ e          → level = min(3, 2 + (v − e) / (e − s))    band EXTREME (3)
band = 1 if level < 1; 2 if level < 2; else 3
```

**History band** (the three history-required cards):

- STRONG if N = 50 **or** the candidate's population-extreme condition holds.
- EXTREME if **both** hold.
- NOTABLE otherwise (20 ≤ N < 50 and not population-extreme).
- Level = (band − 1) + min(0.99, N / 50).

**Tier B levels** are fixed per candidate (below).

All levels MUST be rounded to 3 decimal places before comparison.

---

## 9.1 `COMEBACK_WIN` — Comeback Win

- **Tier / family:** A / Match Lead Story.
- **Question answered:** Did my team win from a genuinely major deficit?
- **Required data:** all ten `networthPerMinute`; match result.
- **Mode / role / history:** Standard + Turbo; any role; no history.
- **Eligibility:** the viewer's team won.
- **Calculation:** deficit = max(−L(t)) over the core curve. deficit_minute = the first t reaching it.
- **Qualifying threshold:** deficit ≥ 12,000 (Std) / 18,300 (Turbo).
- **Severity:** ladder 12,000 / 19,500 / 31,000 (Std); 18,300 / 23,700 / 33,500 (Turbo).
- **Guards:** final-3-minute exclusion (the core curve). A deficit created only in the final push does not count.
- **Enrichment:** none.
- **Ranking class:** 1. **Story group:** priority 1.
- **Slots:** deficit, deficit_minute, last_minute_behind (on the core curve), final_lead_sign (full curve), win_time.
- **Safe claim:** "You trailed by 19.8k at 33:00 and won." Optionally "still behind at 39:00". If still behind at the end: "won despite trailing by X".
- **Forbidden:** "because", "clutch", "outplayed", "they threw", "the game turned".
- **Missing data:** `NOT_ELIGIBLE` globally.
- **Known limitation:** Turbo base-race wins while far behind are real but strange; wording must stay "trailed by X at T and won".

## 9.2 `LOST_FROM_AHEAD` — Lost From Ahead

- **Tier / family:** A / Match Lead Story.
- **Question answered:** Did my team lose from a genuinely major lead?
- **Required data / mode / role / history:** as Comeback Win.
- **Eligibility:** the viewer's team lost.
- **Calculation:** lead = max(L(t)) over the core curve; lead_minute = first t reaching it.
- **Qualifying threshold:** lead ≥ 12,000 (Std) / 18,300 (Turbo).
- **Severity:** same ladder as Comeback Win.
- **Guards:** final-3-minute exclusion.
- **Ranking class:** 1. **Story group:** priority 2.
- **Slots:** lead, lead_minute, final_lead (full curve).
- **Safe claim:** "Your team led by 13.6k at 28:00 and lost."
- **Forbidden:** "threw", "throw", "the game turned at …", any blame.
- **Known limitation:** losses while still ahead (base races) exist; never imply a turn.

## 9.3 `LEAD_FLIP` — Major Sustained Lead Flip

- **Tier / family:** A / Match Lead Story.
- **Question answered:** Did control of the game genuinely change hands after laning?
- **Required data / mode / role / history:** `networthPerMinute`; Standard + Turbo; any role; none.
- **Calculation (on the core curve):**
  1. sign(t) = +1 if L(t) ≥ 1,500; −1 if L(t) ≤ −1,500; else 0.
  2. A sustained run is a maximal block of equal non-zero sign lasting ≥ 3 minutes.
  3. A flip is two consecutive sustained runs (in run order, shorter blocks ignored) of opposite sign, where the second run starts at minute ≥ lane end (Std 12 / Turbo 9).
  4. Flip magnitude = min(max |L| inside run 1, max |L| inside run 2).
  5. Qualifying flips have magnitude ≥ q. The **latest** qualifying flip is displayed.
- **Qualifying threshold:** 7,900 (Std) / 14,200 (Turbo).
- **Severity:** ladder 7,900 / 12,100 / 21,900 (Std); 14,200 / 19,400 / 27,500 (Turbo).
- **Guards:** final-3-minute truncation; latest flip (an early small flip must not hide the decisive later swing).
- **Ranking class:** 2. **Story group:** priority 5.
- **Slots:** direction (FLIP_FOR / FLIP_AGAINST), peak_before, run_before, peak_after, run_after, result.
- **Safe claim:** "Your team led by up to 10.2k (4:00–31:00); then the enemy led by up to 20.7k (33:00–44:00)." The result is always stated.
- **Forbidden:** "the fight at X flipped the game", "momentum", any cause of the swing.
- **Known limitation:** a flip in your favour inside a loss is a true paradox; the mandatory result slot handles it.

## 9.4 `OWN_LANE_VS_USUAL` — Own Lane vs Your Usual

- **Tier / family:** A / Lane Story.
- **Question answered:** How unusual was this lane for me?
- **Required data:** viewer and counterpart `networthPerMinute`, `position`, `lane`; history.
- **Mode:** Standard + Turbo (separate cohorts).
- **Role:** **cores only** (carry, mid, offlane).
- **History:** required; key bucket + effective role; N ≥ 20; window ≤ 50.
- **Eligibility:** counterpart resolved.
- **Calculation:** value = NW(viewer, late) − NW(counterpart, late), late = 10 (Std) / 8 (Turbo).
- **Qualifying threshold:**
  - best record: value − max(window) ≥ margin; or
  - worst record: min(window) − value ≥ margin;
  - margin = 100 (Std) / 200 (Turbo) gold.
- **Severity:** history band; population-extreme condition = |value| ≥ core lane-gap p95 (2,254 Std / 4,449 Turbo).
- **Guards:** cores only (support lane gaps were 0 of 8 GOOD); record margin (near-tie records read as silly).
- **Enrichment:** window median MAY be shown as a secondary fact.
- **Ranking class:** 2. **Story group:** no.
- **Slots:** value, direction (BEST / WORST), N, window_median, previous_record, counterpart_hero, counterpart_position.
- **Safe claim:** "Your lane gap at 10:00 was −2.9k: your worst across your last 50 Standard Offlane matches (previous worst −1.8k)."
- **Forbidden:** "ever", "personal record", "your worst lane ever", "you won/lost lane because".
- **Missing data:** counterpart unresolved, role unknown or N < 20 → ineligible.
- **Known limitation:** late-checkpoint gap only; not a full lane story.

## 9.5 `OPP_START_VS_HISTORY` — Extreme Opponent Start vs Your History

- **Tier / family:** A / Lane Story.
- **Question answered:** Was my lane opponent's start unusually strong relative to the opponents I normally face?
- **Required data:** counterpart `lastHitsPerMinute`, positions, lanes; history.
- **Mode / role:** Standard + Turbo; **cores only**.
- **History:** required; key bucket + effective role; N ≥ 20. No population-only version exists.
- **Calculation:** value = CS(counterpart, late).
- **Qualifying threshold (all):**
  - value ≥ population p90 for the counterpart position — Std P1 60 / P2 63 / P3 53; Turbo 48 / 48 / 39;
  - value > max(window) (strict);
  - N ≥ 20.
- **Severity:** history band; population-extreme condition = value ≥ position p95 — Std P1 64 / P2 70 / P3 57; Turbo 53 / 53 / 42.
- **Guards:** cores only (support counterpart records were 2 of 11 GOOD); population gate; strict maximum.
- **Ranking class:** 2. **Story group:** no.
- **Slots:** counterpart_hero, counterpart_position, value, N, window_median, previous_high, your_lane_diff.
- **Safe claim:** "Their Shadow Fiend had 91 CS at 10:00: the most an opposing Carry has had against you across your last 20 Standard Offlane matches."
- **Forbidden:** "strongest opponent you've faced", "they outplayed you", MMR or skill claims.
- **Known limitation:** farming heroes produce more records; the claim stays literally true and the hero is always named.

## 9.6 `OWN_ITEM_VS_HISTORY` — Own Key Item Timing vs Your History

- **Tier / family:** A / Power Spikes & Item Timings.
- **Question answered:** Was this item timing unusually fast for me?
- **Required data:** viewer `itemPurchases`; `gameVersionId`; history.
- **Mode / role:** Standard + Turbo; any role (role is in the key).
- **History:** required; key bucket + effective role + item + **major patch**; N ≥ 20; window = last ≤ 50 prior first purchases.
- **Items (list order):** Black King Bar, Blink Dagger, Radiance, Hand of Midas, Manta Style, Desolator, Battle Fury, Maelstrom, Aghanim's Scepter, Orchid Malevolence.
- **Calculation:** t = the viewer's first purchase time of the item.
- **Qualifying threshold:** t ≤ min(window) − margin; margin = 60 s (Std) / 30 s (Turbo). **Fastest only.**
- **At most one card per match:** the first qualifying item in list order.
- **Severity:** history band; population-extreme condition = min(window) − t ≥ 120 s (Std) / 60 s (Turbo).
- **Guards:** fastest only (slowest records were 12 of 14 BORING); margin; role and patch in the key.
- **Ranking class:** 2. **Story group:** no.
- **Slots:** item, time, previous_fastest, window_median, N, hero.
- **Safe claim:** "Your 18:35 BKB was your fastest across your last 50 Standard Mid BKB purchases (previous 20:19)."
- **Forbidden:** "fastest ever", "finished / completed" (a purchase is what is observed), advice, "fastest on this hero", any slowest-record card.
- **Known limitation:** item cohorts reach N ≥ 20 in only about 40% of evaluations for established accounts.

## 9.7 `ENEMY_STACKING` — Enemy Stacking Edge

- **Tier / family:** A / Hidden Enemy Activity.
- **Question answered:** Did the enemy do an unusual amount of hidden stacking work?
- **Required data:** `campStack` for all ten players.
- **Mode:** **Standard only**. **Role:** any. **History:** optional line.
- **Eligibility:** duration ≥ 20:00.
- **Calculation:** enemy = Σ enemy `campStack[19]`; own = Σ own `campStack[19]`.
- **Qualifying threshold:** enemy ≥ 7 **and** enemy − own ≥ 4.
- **Severity:** ladder on enemy stacks: 7 / 9 / 13.
- **Guards:** Standard only.
- **Enrichment:** bucket-cohort history line (integer metric: record or median only).
- **Ranking class:** 2. **Story group:** no.
- **Slots:** enemy, own.
- **Safe claim:** "Their team stacked 13 camps by 20:00; yours stacked 3."
- **Forbidden:** "their stacks won them the game", "your supports didn't stack".
- **Known limitation:** 7-stack cards in stomp wins are only acceptable.

## 9.8 `VISION_QUICK_CLEARS` — Vision Quick Clears

- **Tier / family:** A / Hidden Enemy Activity.
- **Question answered:** Were our observers repeatedly found almost immediately?
- **Required data:** `stats.wards` (all ten players), enemy `stats.wardDestruction`.
- **Mode / role / history:** Standard + Turbo; any; none.
- **Calculation:** stats-only reconstruction (§10). quick = identified clears with life ≤ 90 s and clear time < duration − 300 s.
- **Qualifying threshold:** quick ≥ 4 (both modes) **and** quick ≥ 0.25 × observers placed by your team (placed ≥ 1).
- **Severity:** ladder 4 / 5 / 6 (both modes).
- **Guards:**
  - minimum 4 in Turbo too (Turbo "3 of 9" was boring);
  - clears in the final 5 minutes excluded;
  - counts are lower bounds and copy MUST say "at least".
- **Ranking class:** 2. **Story group:** no.
- **Slots:** count, count_within_60s, placed, destroyed_total, lower_bound_flag (always true).
- **Safe claim:** "At least 8 of your 20 observers were destroyed within 90 seconds of being placed (4 within a minute)."
- **Forbidden:** "they could see you", "your wards were in bad spots", "you had no vision", any visibility percentage.
- **Known limitation:** about 21% of clears are unresolved, so some true fires are missed (2 of 5 in the holdout). None are invented.

## 9.9 `VISION_REGION_SWEEP` — Vision Region Sweep

- **Tier / family:** A / Hidden Enemy Activity.
- **Question answered:** Did the enemy systematically clear one area?
- **Required data:** as Quick Clears, plus `networthPerMinute`.
- **Mode / role / history:** Standard + Turbo; any; none.
- **Calculation:** for each identified clear a, in clear-time order:
  1. cluster = identified clears x with region(x) = region(a) and a.t ≤ x.t ≤ a.t + 300;
  2. reject the cluster if **any** holds:
     - a.t < 300 (laning-phase rune-ward clears);
     - max(x.t) ≥ duration − 300 (final push);
     - |L(min(len(L) − 1, ⌊a.t / 60⌋))| ≥ 10,000 (stomp either way);
     - median(x.life) > 180 s (wards near natural expiry);
  3. keep the largest surviving cluster (ties: earliest a).
- **Qualifying threshold:** cluster size ≥ 3.
- **Severity:** ladder 3 / 4 / 5.
- **Guards:** the four rejections above; counts are lower bounds.
- **Evidence clause:** enemy Sentries placed in the same region during [start − 90 s, end]; shown only if ≥ 1.
- **Ranking class:** **3**. **Story group:** no.
- **Slots:** region, start, end, lifetimes_rounded, enemy_sentries_in_region.
- **Safe claim:** "Between 18:48 and 22:32, at least 4 of your observers in their half were destroyed; they had lasted 12–114 seconds." Allowed: "the enemy placed 3 Sentries there."
- **Forbidden:** map-visibility percentages, "they blinded your jungle", "this led to deaths", "map control".
- **Known limitation:** conservative; 1 of 4 true sweeps missed in the holdout.

## 9.10 `ENEMY_SMOKE_VOLUME` — Enemy Smoke Volume

- **Tier / family:** A / Hidden Enemy Activity.
- **Question answered:** Did the enemy use far more Smoke than my team?
- **Required data:** `itemUsed` for all ten players (item id 188, Smoke of Deceit).
- **Mode:** **Standard only**. Turbo Smoke Volume is removed.
- **Role:** any. **History:** optional line.
- **Calculation:** enemy = Σ enemy `itemUsed.count` for id 188; own likewise; rate = enemy × 600 / durationSeconds.
- **Qualifying threshold (all):**
  - rate ≥ 1.60 per 10 minutes;
  - enemy ≥ 4;
  - **enemy − own ≥ 4** (the enemy is at least 4 Smokes ahead).
- **Magnitude / severity:** enemy − own; ladder 4 / 6 / 8.
- **Guards:** Standard only; edge ≥ 4 (small gaps such as 8 vs 6 read as "so what").
- **Enrichments:** Smoke → Kills (§11); bucket-cohort history line on the Smoke rate.
- **Ranking class:** 2. **Story group:** no.
- **Slots:** enemy_uses, own_uses, optional smoke_followed_by_kill (k, n).
- **Safe claim:** "They used Smoke 9 times; your team used it 3 times."
- **Forbidden:** "successful Smokes", "Smoke ganks worked", "their Smokes killed you", "resulted in kills".

## 9.11 `ENEMY_EARLY_RICH` — Enemy Early-Rich Hero

- **Tier / family:** A / Hidden Enemy Activity.
- **Question answered:** Did an enemy hero get rich unusually early compared with my team?
- **Required data:** `networthPerMinute`, `heroId`, `position`.
- **Mode / role / history:** Standard + Turbo; any; optional line.
- **Calculation:**
  - goal = 10,000 (Std) / 15,000 (Turbo);
  - a player's goal minute = the first t with NW(p, t) ≥ goal;
  - m = the earliest enemy goal minute (tie: lower position number, then lower heroId);
  - own = the earliest goal minute on your team;
  - gap = own − m.
- **Qualifying threshold (all):**
  - m ≤ 18 (Std) / 12 (Turbo);
  - own exists (your team reached the goal);
  - gap ≥ 3;
  - that enemy hero is not Alchemist;
  - duration / 60 − m ≥ 8.
- **Magnitude / severity:** min(gap, 12); ladder 3 / 5 / 7 (Std), 3 / 4 / 6 (Turbo).
- **Guards:** your team reached the goal and the match lasted ≥ 8 more minutes (otherwise the card only restates a stomp); Alchemist excluded (economy profile, gold gifting).
- **Enrichment:** bucket-cohort history line (integer metric: record or median only).
- **Ranking class:** 2. **Story group:** no.
- **Slots:** hero, position, minute, your_team_minute.
- **Safe claim:** "Their Kez reached 10k net worth at 15:00; your team's first hero got there at 20:00."
- **Forbidden:** "that's why you lost", "unkillable", "snowballed because".

## 9.12 `ENEMY_EARLY_ITEM` — Enemy Core Early Key Item

- **Tier / family:** A / Power Spikes & Item Timings.
- **Question answered:** Did an enemy core buy a key spike item unusually early?
- **Required data:** enemy `itemPurchases`, positions, heroes.
- **Mode / role / history:** Standard + Turbo; any; optional line (bucket + item + major patch).
- **Items (list order):** Black King Bar, Blink Dagger, Manta Style, Battle Fury, Radiance, Desolator, Maelstrom, Orchid Malevolence. Hand of Midas and Aghanim's Scepter are excluded.
- **Calculation:**
  - for each item: t = the earliest first purchase among enemy P1–P3;
  - margin = (p5 − t) / p5, with p5 = the bucket core p5 for that item;
  - display the largest margin (ties: item list order).
- **Qualifying threshold:** margin ≥ 0.10 (t ≤ 0.90 × p5).
- **Severity:** ladder 0.10 / 0.15 / 0.22 (both modes).
- **Reference p5 and typical core time** (typical = bucket median of enemy P1–P3 first purchases; frozen):

| Item | Std p5 | Std typical | Turbo p5 | Turbo typical |
|---|---|---|---|---|
| Black King Bar | 21:28 | 28:38 | 10:39 | 15:30 |
| Blink Dagger | 9:53 | 14:39 | 4:27 | 7:30 |
| Manta Style | 15:36 | 22:52 | 7:42 | 11:29 |
| Battle Fury | 12:01 | 15:45 | 5:48 | 8:18 |
| Radiance | 13:46 | 17:59 | 6:31 | 9:18 |
| Desolator | 13:58 | 21:20 | 6:29 | 10:32 |
| Maelstrom | 11:09 | 15:15 | 5:07 | 7:50 |
| Orchid Malevolence | 12:41 | 22:10 | 6:03 | 11:02 |

- **Guards:** curated list; ≥ 10% earlier than p5; the typical core time MUST appear in copy; "bought" wording only.
- **Ranking class:** **3**. **Story group:** no.
- **Slots:** hero, position, item, time, typical_core_time.
- **Safe claim:** "Their Sven bought Black King Bar at 17:41, about 11 minutes earlier than a typical core BKB."
- **Forbidden:** "finished", "completed", "rushed to counter you", "counter-built", any intent.
- **Known limitation:** no hero-conditioned reference; 87% of fires were already in the hero's own fastest 10%, so the hero-typical risk is small.

## 9.13 `CLOSE_MOST_OF_GAME` — Close Most of Game

- **Tier / family:** B / Match Lead Story.
- **Question answered:** Was this game genuinely competitive for most of its length?
- **Required data:** `networthPerMinute`, `towerDeaths`, duration.
- **Mode / role / history:** Standard + Turbo; any; none.
- **Eligibility (all):**
  - Tier B label = `CT` (§9.18);
  - close_share ≥ 0.75;
  - window length n ≥ 20 (Std) / 16 (Turbo);
  - shape_confidence ≥ 0.7.
- **Severity:**
  - STRONG if close_share ≥ 0.90 **and** latest_close_minute ≥ E − 2 **and** n ≥ 30 (Std) / 20 (Turbo): level = 1 + (close_share − 0.9) × 5;
  - otherwise NOTABLE: level = (close_share − 0.75) / 0.15 × 0.99;
  - no EXTREME.
- **Guards:** share and window length (persistent 5–7k leads and 11–15-minute Turbo windows were misleading).
- **Enrichment:** structure contradiction (§9.17).
- **Ranking class:** 2. **Story group:** priority 3.
- **Slots:** window_start, window_end, close_share, max_3min_gap, latest_close_minute.
- **Safe claim:** "The net-worth gap stayed within 5.4k for most of 10:00–41:00." Allowed: "Still close at 41:00."
- **Forbidden:** "even throughout", "the game was even the entire time", "anyone's game", "you should have won".

## 9.14 `EVEN_THEN_SEPARATED` — Even Then Separated

- **Tier / family:** B / Match Lead Story.
- **Question answered:** When did this stop being an even game?
- **Eligibility (all):**
  - Tier B label = `ETS_FOR` or `ETS_AGAINST`;
  - the separating side won the match;
  - pre_max ≤ 7,500, where pre_max = max |L(t)| for t in [S, max(S, sep − 3)] on the raw gold curve;
  - n ≥ 18 (Std) / 20 (Turbo);
  - shape_confidence ≥ 0.7.
- **Severity:** STRONG (level 1.0) if sep ≥ 30 (Std) / 20 (Turbo) **and** pre_max ≤ 5,000; else NOTABLE (level 0.5). No EXTREME.
- **Guards:** credible "even" phase; not a short stomp; outcome-consistent.
- **Ranking class:** 2. **Story group:** priority 4.
- **Slots:** side, even_until = max(S, sep − 3), max_gap_before = pre_max, separation_minute, lead_at_separation, lead_at_window_end.
- **Safe claim:** "Until 23:00 the gap never exceeded 5.4k; from 26:00 your team held a sustained lead."
- **Forbidden:** "this fight / this item decided the game".

## 9.15 `LEAD_ERODED` — Lead Eroded

- **Tier / family:** B / Match Lead Story.
- **Question answered:** Did a large lead of ours shrink substantially?
- **Eligibility (all), with floor = 5,000 (Std) / 10,000 (Turbo):**
  - Tier B label = `LE`;
  - gold_peak ≥ floor;
  - peak_minute ≥ S + 6;
  - −floor ≤ L(E) ≤ max(0.5 × floor, 0.25 × gold_peak);
  - min over t in [peak_minute, E] of L(t) ≥ −2 × floor (no interim opposite lead beyond twice the floor);
  - shape_confidence ≥ 0.7.
- **Severity** (gold_erosion = (gold_peak − gold_late) / gold_peak, both from the classifier):
  - EXTREME (level 2.0): gold_peak ≥ 15,000 (Std) / 22,000 (Turbo) **and** gold_erosion ≥ 0.90;
  - STRONG: gold_peak ≥ 10,000 / 15,000 **and** gold_erosion ≥ 0.75; level = 1 + min(0.99, (gold_erosion − 0.75) × 4);
  - NOTABLE: level = min(0.99, (gold_erosion − 0.5) × 2).
- **Guards:** before these guards the card was misleading 43% of the time (real 8–21k flips labelled "erosion").
- **Ranking class:** 2. **Story group:** priority 6.
- **Slots:** peak, peak_minute, value_at_window_end (the actual L(E), never a 3-minute median), window_end_minute, result.
- **Safe claim:** "Your 11.4k lead at 27:00 was down to 1.2k by 36:00." The result is stated.
- **Forbidden:** "you threw your lead", percentages without gold values.

## 9.16 `DEFICIT_RECOVERED` — Deficit Recovered

- **Tier / family:** B / Match Lead Story.
- **Question answered:** Did my team recover most of a large deficit?
- **Eligibility and severity:** exact mirror of `LEAD_ERODED`, with label `DR` and every L replaced by −L. "Recovered" therefore requires the remaining gap to be at most max(½ floor, ¼ peak).
- **Ranking class:** 2. **Story group:** priority 7.
- **Slots:** enemy_peak, peak_minute, enemy_value_at_window_end (actual), window_end_minute, result.
- **Safe claim:** "You cut the enemy's 24.4k lead to 1.4k by 48:00; the enemy won."
- **Forbidden:** "comeback" in a loss; "you recovered" while still ≥ floor behind. In a win, a higher-priority story card (usually Comeback Win) is shown instead whenever one is eligible.

## 9.17 `LATE_REVERSAL` — Late Reversal, and the structure-contradiction enrichment

**`LATE_REVERSAL`**

- **Tier / family:** B / Match Lead Story.
- **Question answered:** Did my team win after the enemy held a real lead late into the game?
- **Eligibility (all):**
  - the viewer's team won (winner-only);
  - Tier B label ∉ {`SHORT_WINDOW`, `UNCLEAR`};
  - the last sustained Tier B run (on smoothed R) belongs to the enemy;
  - that run ends at minute ≥ S + 0.75 × n − 1;
  - peak = max of −L(t) over the run's minutes ≥ floor (5,000 Std / 8,000 Turbo);
  - shape_confidence ≥ 0.7.
- **Severity:** STRONG (level 1.0) if peak ≥ 10,000 (Std) / 15,000 (Turbo); else NOTABLE (level 0.5).
- **Ranking class:** 2. **Story group:** priority 8.
- **Slots:** run_start, run_end, max_enemy_lead, lead_at_window_end, win_time.
- **Safe claim:** "The enemy led by up to 21k until 50:00; you won at 59:37."
- **Forbidden:** "you always had it". A loss after a brief late lead is never a comeback.

**`STRUCTURE_CONTRADICTION` (enrichment only, never a card)**

- Attaches to a displayed Tier B card only.
- **NO_STRUCTURE_CONVERSION:** a sustained Tier B run of ≥ 8 (Std) / 5 (Turbo) minutes whose leader has exactly 0 net towers/barracks over [run start, run end + 1 min).
- **STRUCTURE_COUNTERTREND:** over all of one side's sustained-run minutes, that side's net towers/barracks ≤ −2.
- **Safe claim:** "The enemy led for 21 minutes (12:00–33:00) with no net tower/barracks change."
- **Forbidden:** "they failed to close", "wasted their lead".

## 9.18 Frozen Tier B classifier (shared input of §9.13–9.17)

The classifier is frozen as `tier-b-match-shape 2.0`. Its constants are in the JSON contract (`tier_b_classifier`). Engineering MUST implement it exactly; the reference is `post-match-tier-b-validation-data/research-code/shape.py` with the final parameters.

**Window and series**

- S = 10 (Std) / 8 (Turbo).
- E = min(len(R) − 1, ⌊(durationSeconds − 180) / 60⌋).
- n = E − S + 1. If n < 9 → `SHORT_WINDOW`.
- a[i] = centered 3-minute median of R truncated at E (a 2-value median at the edges is their mean), for absolute minutes S … E.

**Thresholds**

- Phase bin = number of edges ≤ absolute minute. Edges: Std 20 / 30 / 40; Turbo 14 / 20 / 26.
- Close C = p50, edge E_thr = p70, strong S_thr = p90 of the frozen |R| reference for that bucket and bin:

| Bucket | Bin | C (p50) | Edge (p70) | Strong (p90) |
|---|---|---|---|---|
| Std | 10–19 | 0.0637 | 0.0943 | 0.1563 |
| Std | 20–29 | 0.0653 | 0.1032 | 0.1803 |
| Std | 30–39 | 0.0568 | 0.0914 | 0.1429 |
| Std | 40+ | 0.0409 | 0.0641 | 0.1073 |
| Turbo | 8–13 | 0.0649 | 0.1008 | 0.1638 |
| Turbo | 14–19 | 0.0657 | 0.0994 | 0.1687 |
| Turbo | 20–25 | 0.0522 | 0.0798 | 0.1310 |
| Turbo | 26+ | 0.0407 | 0.0635 | 0.1054 |

  The p45 / p55 / p65 / p75 / p85 / p95 values needed for shape_confidence are in the JSON.

**States and runs**

- state[i] = +1 if a[i] ≥ E_thr(i); −1 if a[i] ≤ −E_thr(i); else 0. No hysteresis.
- A sustained run is a maximal block of equal non-zero state of length ≥ 3.
- close[i] = |a[i]| ≤ C(i); close_share = mean(close).
- msg = the largest gold gap held for 3 straight minutes: max over i of min(|L(S+i)|, |L(S+i+1)|, |L(S+i+2)|).
- latest_close_minute = S + the last i with close[i].

**Raw shapes** (for s ∈ {+1, −1}; t3 = max(1, ⌊n/3⌋); half = ⌊n/2⌋; h = ⌈2n/3⌉)

- **ETS, thirds path:**
  - sep = the first s-run starting at ≥ 0.30 n;
  - close share of a[0..t3) ≥ 0.65;
  - no run of either side starts before sep;
  - the share of the last t3 minutes inside s-runs ≥ 0.60;
  - no −s run starts at or after sep.
- **ETS, transition path** (only if the thirds path did not fire):
  - the first run of the window belongs to s and starts at τ ≥ max(0.30 n, 3);
  - close share of a[0..τ) ≥ 0.65;
  - the share of minutes τ..n−1 inside s-runs ≥ 0.60;
  - no −s runs;
  - n − τ ≥ 3.
- **LE (s = +1) / DR (s = −1):**
  - some s-run starts before h, and no −s run exists;
  - ref = max of s·a[0..h);
  - late = median of s·a over the last 3 window minutes;
  - peak index pk = the first argmax over i < h of s·L(S+i);
  - gold_peak = s·L(S+pk);
  - gold_late = median of s·L(t) for t in [E−2, E];
  - require ref > 0, (ref − late) / ref ≥ 0.50, gold_peak > 0, (gold_peak − gold_late) / gold_peak ≥ 0.50, and gold_peak ≥ 5,000 (Std) / 8,000 (Turbo);
  - peak_minute = S + pk.
- **OS:**
  - the share of window minutes inside s-runs ≥ 0.70;
  - the first s-run starts ≤ 0.33 n;
  - no −s run;
  - and (the longest block with s·a ≥ S_thr is ≥ 3 minutes, or s × net structures over the window ≥ 3).
- **SE, path 1:** s-run share ≥ 0.50, median of a[0..half) and of a[half..n) both favour s, no −s run.
- **SE, path 2 (if path 1 did not fire):** no −s run; share of minutes with s·a > 0 ≥ 0.80; s·median(a) ≥ median of the C(i) values; both half-medians favour s.
- **SWAP:** runs of both sides exist; direction = the sign of the last run.
- **CT:** no runs at all; close_share ≥ 0.60; msg < 7,500.

**Label**

- The first matching shape in the order ETS → LE → DR → OS → SE → SWAP → CT; otherwise `UNCLEAR`.
- Displayable labels: CT, ETS_*, LE, DR (subject to the §9.13–9.16 guards).
- OS, SE, SWAP, UNCLEAR and SHORT_WINDOW are never displayed. OS, SE and SWAP still permit Late Reversal.

**Mirror rule (required test).** The enemy view's label equals the mirrored label: LE ↔ DR, *_FOR ↔ *_AGAINST, CT ↔ CT.

**shape_confidence** = the share of the 34 perturbations whose label equals the unperturbed label:

- close / edge / strong percentile ±5;
- run length ±1;
- OS share, SE share, ETS close share, ETS final share ±0.05;
- erosion ±0.10;
- window start −2, −1, +1, +2;
- end exclusion −2, −1, +1, +2 (floored at 0);
- CT close share ±0.05;
- SE lean share ±0.05;
- CT gold ±1,000;
- LE gold floor ±1,000.

Thresholds under perturbation come from the frozen reference percentiles; they are never refitted per match. Tier B cards require confidence ≥ 0.7.

**Superseded Tier B research elements** (MUST NOT be implemented):

- the TierBScore formula and its 45 cutoff;
- the 0.7–0.9 confidence display allow-list;
- all "moderate signals" (lane composite, lane vs other lanes, power-spike composite, RICH_MOD, SMOKE_MOD, OBSCLEAR_MOD, STACK_MOD, multi-signal and economy composites);
- "Tier A first, then Tier B" fallback.

---

# 10. Vision reconstruction algorithm

**Status: VALIDATED and approved for V1.** This is the single canonical method for both vision cards.

## 10.1 Inputs (per team viewpoint)

| Input | Source |
|---|---|
| Own observers | your players' `stats.wards` rows with `type == 0`: (t0, x, y), sorted by (t0, x, y) |
| Enemy Sentries | enemy players' `stats.wards` rows with `type == 1`: (ts, x, y) |
| Clears | enemy players' `stats.wardDestruction` rows with `isWard == true`: times, ascending |
| Placed | count of own observers |
| Destroyed total | count of clears |

Coordinates are STRATZ cell units (1 cell = 64 world units). Distances are Euclidean in cells. Nominal observer life is 360 s.

## 10.2 Identity matching

```text
taken ← ∅
for each clear time t (ascending):
    cands ← { i : t0_i ≤ t < min(t0_i + 360, duration) and i ∉ taken }
    scored ← []
    for i in cands:
        ev ← { sentry : t − 90 ≤ ts ≤ t and dist(sentry, observer_i) ≤ 10 }
        if ev ≠ ∅: scored.append((min dist over ev, min (t − ts) over ev, i))
    sort scored ascending
    if len(scored) == 1:                                       pick scored[0].i   (tier A)
    elif len(scored) ≥ 2 and scored[0].dist + 3 < scored[1].dist: pick scored[0].i   (tier A)
    elif len(cands) == 1:                                      pick the only cand (tier C)
    else:                                                      unresolved
    if picked i: taken ← taken ∪ {i}
                 emit {t, t0 = t0_i, x_i, y_i, life = t − t0_i, region = region(x_i, y_i, side)}
```

- **Proximity rule:** an enemy Sentry placed within the 90 s before the clear and within 10 cells (640 world units) of the observer.
- **Conflict resolution:** when several alive observers have Sentry evidence, the closest wins only if it is more than 3 cells closer than the next. Otherwise the clear stays unresolved unless exactly one observer is alive.
- **No reuse:** an identified observer cannot be matched again.
- **No second pass.** The research code had a second, wider pass configured to W2 = 0 / R2 = 0 whose picks were discarded; V1 has none.
- **Unmatched behaviour:** unresolved clears are never guessed and never counted. They are included only in `destroyed_total`.
- **Precision-oriented design:** the method prefers missing a clear to misidentifying one. Every displayed count is a lower bound, and copy MUST say "at least".

## 10.3 Region

```text
label ← REGION_LABEL_CELLS[(⌊x/8⌋, ⌊y/8⌋)] or none      // frozen table in the JSON contract
if label ends with BASE or FOUNTAIN:
    OWN_BASE if (label starts with RADIANT) == (side is Radiant) else ENEMY_BASE
elif |x + y − 252| ≤ 10 or label ∈ {RIVER, ROSHAN}:
    RIVER
else:
    OWN_HALF if (x + y < 252) == (side is Radiant) else ENEMY_HALF
```

## 10.4 Card rules and fallback

- **Quick Clears rule:** §9.8. **Region Sweep rule:** §9.9, including the final-minute guard (last clear < end − 5 min), the stomp guard (|lead at first clear| < 10,000), the laning-phase guard (first clear ≥ 5:00) and the near-expiry guard (median life ≤ 180 s).
- **Playback:** V1 MUST NOT use playback `wardEvents` for card eligibility, even when present. One method keeps outputs deterministic and recomputable after playback expires (§19.2).
- **Fallback:** a ward that cannot be reconstructed is simply not counted. If fewer clears are identified than a rule needs, the card does not fire. There is no playback or population substitute.
- **Prohibited outputs:** visibility percentage, "enemy saw you", "the deward caused a death", map-control claims.

## 10.5 Validation

Fresh playback holdout: 33 unseen matches, 66 team units.

| Measure | Result |
|---|---|
| Identity precision | 99.1% (tier A 99.0%, tier C 100%) |
| Coverage | 79% |
| Region correct | 99.1% |
| ≤ 90 s classification agreement | 99.5% |
| Quick-count mean absolute error | 0.41 |
| Quick Clears rule | 3 hits, 2 misses, **0 false fires** |
| Region Sweep rule | 3 hits, 1 miss, **0 false fires** |

The method MUST be re-validated after any patch that changes observer or Sentry mechanics or the map layout (region cells, river diagonal).

---

# 11. Smoke → Kills enrichment algorithm

**Status: LOCKED.** An optional enrichment on `ENEMY_SMOKE_VOLUME` only (so Standard only). It is never a card and never changes band, level or rank. The old "≥ 3 Smokes and ≥ 50% followed" rule is removed.

## 11.1 Preconditions

1. `ENEMY_SMOKE_VOLUME` is eligible for the viewer's team.
2. Playback is **usable** in the frozen source checkpoint:
   - `playbackData` is non-null;
   - the total number of `players[].playbackData.itemUsedEvents` across all ten players is > 0 (an all-empty payload means "no playback", never "0 Smokes");
   - the enemy's playback Smoke event count (`itemId == 188`) equals the enemy's stats `itemUsed` count for id 188.

## 11.2 Rule

```text
t1 < t2 < … < tn ← enemy Smoke activation times (playback itemUsedEvents, itemId 188)
require n ≥ 3
window(i) ← (t_i, min(t_i + 60, t_{i+1})]           // last window: (t_n, t_n + 60]
kill      ← a deathEvents row of a player on YOUR team whose attacker heroId is on the enemy team
k ← #windows containing ≥ 1 kill
f ← #windows containing ≥ 1 kill whose joined enemy killEvents row (same target, same time) has isSmoke == true
fire ⇔ k ≥ 3 ∧ k ≥ 0.70 · n ∧ f ≥ 2
display: k and n
```

**Attribution and confirmation**

- Truncating each window at the next same-team Smoke means a kill counts only for the most recent Smoke. Displayed k is never double-counted.
- `isSmoke` is a confirmation gate only. It never appears in a displayed number.
- No minimum delay; no phase- or mode-specific window; the unit is Smokes, never kills.
- Pre-horn Smokes count normally. Smokes whose window runs past the game's end stay in n.

## 11.3 Evidence

- Original study: 9 fires, 44 followed windows vs 27.3 expected at matched ordinary moments.
- Fresh replication: 62 followed windows vs 38.2 expected (×1.6); suppressed teams at chance (47 vs 49.7).
- Base rate: a team gets a kill within 60 s at about 56–58% of ordinary moments, so "a kill followed a Smoke" is not impressive on its own. The 70% share and the `isSmoke` gate are what make the line meaningful.

## 11.4 Semantics

- **Safe (temporal only):** "5 of their 7 Smokes were followed by a kill within a minute."
- **Never:**
  - "5 successful Smokes";
  - "5 Smokes resulted in / led to kills";
  - "their Smokes caused 5 kills";
  - "they ganked you 5 times";
  - hero-specific victim claims;
  - claims about who was in the Smoke;
  - comparisons with "normal" rates;
  - any window other than 60 s.

---

# 12. Ranking and selection

## 12.1 Order of operations

1. Generate all eligible cards with band and level (§9).
2. Apply the Match Lead Story suppression rule (§12.2).
3. Sort (§12.3).
4. Return the first min(3, n) cards. Never fill.

## 12.2 Match Lead Story suppression (the only combination rule)

Keep **at most one** card from this group: the eligible member earliest in this list. Drop the rest **before** sorting.

1. `COMEBACK_WIN`
2. `LOST_FROM_AHEAD`
3. `CLOSE_MOST_OF_GAME`
4. `EVEN_THEN_SEPARATED`
5. `LEAD_FLIP` (Major Sustained Lead Flip)
6. `LEAD_ERODED`
7. `DEFICIT_RECOVERED`
8. `LATE_REVERSAL`

**Why this is allowed**

- Same-story duplicates appeared in about 43% of multi-card recaps (Lost + Lead Flip 280, Comeback + Lead Flip 274, Comeback + Late Reversal 219, Comeback + Deficit Recovered 117, Lost + Lead Eroded 107).
- It removed the only contradictory recaps found (Close Most + Lead Flip, 56 cases).
- 52 of the 61 cards it removed in the gold set had independently been marked duplicates. It dropped the human-ranked best card in 1 of 107 viewpoints.

This is a targeted rule, not a redundancy engine. No other combination rule exists.

## 12.3 Sort key

| Key | Direction |
|---|---|
| 1. Ranking class | **ascending — class 1 ranks first, then class 2, then class 3** |
| 2. Band | descending (EXTREME 3 > STRONG 2 > NOTABLE 1) |
| 3. Level (rounded to 3 decimals) | descending |
| 4. Tie order (§8.2) | ascending |

**Classes**

- **1:** `COMEBACK_WIN`, `LOST_FROM_AHEAD`.
- **3:** `ENEMY_EARLY_ITEM`, `VISION_REGION_SWEEP`.
- **2:** every other card.

**Consequences**

- An EXTREME class-3 card never outranks a NOTABLE class-2 card. "EXTREME promotes a class" was tested and lowered agreement.

**Not used:** Tier A bonus, Tier B penalty, own/enemy or win/loss balancing, family caps, diversity bonus, additive scores.

## 12.4 Pseudocode

```text
FAMILY    = [COMEBACK_WIN, LOST_FROM_AHEAD, CLOSE_MOST_OF_GAME, EVEN_THEN_SEPARATED,
             LEAD_FLIP, LEAD_ERODED, DEFICIT_RECOVERED, LATE_REVERSAL]
CLASS1    = {COMEBACK_WIN, LOST_FROM_AHEAD}
CLASS3    = {ENEMY_EARLY_ITEM, VISION_REGION_SWEEP}
TIE_ORDER = §8.2

function rank_class(id): return 1 if id ∈ CLASS1 else (3 if id ∈ CLASS3 else 2)

function select(cards):
    story = [c ∈ cards : c.id ∈ FAMILY]
    keep  = argmin over story of FAMILY.index(c.id)        // none if story is empty
    pool  = [c ∈ cards : c.id ∉ FAMILY] + ([keep] if keep else [])
    sort pool by (rank_class(c.id) ASC, c.band DESC, round(c.level, 3) DESC, TIE_ORDER.index(c.id) ASC)
    return pool[0 : min(3, len(pool))]
```

## 12.5 Validation

- Gold set: 120 manually ranked multi-card viewpoints, 332 cards.
- Final rule: **83%** pairwise agreement, **80%** top-1.
- Split-half class learning: 79% pairwise, 75% top-1.
- Band-only with the same guard: 64% pairwise; random: 50%.
- The remaining ~20% top-1 disagreements are defensible either way; no further rule is justified.

---

# 13. Semantic / copy safety contract

## 13.1 Allowed

- was, reached, bought, used, destroyed, stacked;
- followed by, within, after, before, while, during, until, from … to;
- led by, trailed by, cut … to;
- "across your last N {mode} {role} [item] matches";
- "the median across your last N …" (N ≥ 10);
- "one of your 3 …", "top 10% of your last N", "unusually … for you" (N ≥ 30, continuous metrics only);
- "at least N" (mandatory for vision counts);
- "for most of" (Close Most of Game);
- the match result, stated factually.

## 13.2 Prohibited

| Category | Prohibited |
|---|---|
| Causality | because, caused, resulted in, led to, cost you, won them the game, punished, that's why, decided the game, momentum |
| Judgement | threw / throw, outplayed, clutch, should have, failed to, wasted, bad wards, your supports didn't … |
| Intent | counter-built, rushed to counter you, successful (in the causal sense), ganked you |
| Visibility | they saw you, you had no vision, blinded, map control, any visibility percentage |
| History overreach | ever, all-time, personal record, PB, exact percentiles, rarity wording below N = 30, any history wording below N = 10, population data as "your usual" |
| Purchase semantics | finished, completed (use "bought") |
| Shape overreach | throughout, even the entire time, anyone's game, "comeback" in a loss |

## 13.3 Rules

1. Every card states only observed facts: values, times, counts, the result, and scoped history.
2. Lead-story and Tier B cards MUST state the match result where §9 requires it.
3. Enemy-side cards MUST NOT imply the viewer's team failed.
4. Copy MUST use actual minute values, never smoothed medians, for displayed gold numbers.
5. Final copy templates are written later and MUST stay within this section and the per-candidate claims in §9.

---

# 14. Coverage and expected behaviour

**Accepted expectation: about 57–61% of eligible viewpoints show no special insight card.**

| Population | No card | Standard | Turbo | Win | Loss |
|---|---|---|---|---|---|
| Tuning corpus (886 matches, 8,680 viewpoints; no history; vision) | **57.4%** | 48.9% | 67.3% | 61.8% | 53.0% |
| Established accounts (9,581 fresh viewpoints; history; no vision data) | **61.1%** | 50.6% | 71.7% | 65.6% | 56.5% |

- Established accounts with vision data: about 59–60%. Supports: about 66%.
- Multi-card recaps: ≥ 2 cards 7–9%; 3 cards 1–2%.
- Most common top cards: Close Most of Game, Enemy Early-Rich, Comeback Win, Lost From Ahead, Even Then Separated.

**Why coverage is sparse**

1. The owner intentionally removed many statistically valid but boring candidates (about −15 points).
2. Player-context guards removed further slices that review rated majority BORING or MISLEADING (about −26 points).
3. Quality over coverage is an explicit product choice.

The old "13–17% no insight" assumption is **superseded**. It was measured on the larger pre-removal pool.

**Rules**

- Sparse coverage is **not** an engine failure.
- Thresholds and guards MUST NOT be loosened, removed candidates MUST NOT return, and fallback anomalies MUST NOT be added for coverage.
- The post-match surface MUST support two states:
  - **special-insight state:** 1–3 cards;
  - **normal / no-special-insight state:** 0 cards. It is the **majority** experience. Its design is out of scope here.

---

# 15. Rejected and prohibited candidates (graveyard)

These MUST NOT be revived without a new owner decision backed by new evidence.

| Candidate / idea | Status | Reason |
|---|---|---|
| Dramatic Lane Lead Path / Lane Reversal (`LANE_DRAMATIC`) | **REMOVED** (owner, 2026-09-17) | 0 genuine early reversals in 5,202 core lanes; fires were ordinary blowouts (0 GOOD, 83% BORING) |
| Enemy Smoke Volume in Turbo | **REMOVED** (owner, 2026-09-17) | 0 GOOD in 24 reviewed |
| Old Smoke → Kills ≥ 50% rule | REMOVED | fired at chance |
| Own item slowest-record direction | REMOVED | 12 of 14 BORING |
| Supports in Own Lane / Opponent Start | REMOVED | 0 of 8 / 2 of 11 GOOD |
| Hand of Midas, Aghanim's in Enemy Early Item | REMOVED | farm / gift / hero-specific semantics |
| Enemy Stacking in Turbo | REMOVED | too rare / trivial |
| Ordinary Lane Lead Path | REMOVED | player already knows |
| Support Lane Pair | REMOVED | player already feels it |
| CS-vs-Gold Split | REMOVED | not useful |
| Level-6 Race | REMOVED | visible in game |
| Generic unrestricted Swing Window | REMOVED | narrates stomps |
| Structures Lost While You Were Dead | REMOVED | owner selection |
| Raw vision-cleared count | REMOVED | "so what?"; replaced by Quick Clears / Region Sweep |
| Enemy Barely Warded | REMOVED | not useful enough |
| Enemy Boss Control | REMOVED | objectives are visible |
| Unused Active Item | REMOVED | misleading or too rare |
| Activation-rate extremes | REMOVED | trivia |
| Lane Item Race | REMOVED | nonsensical or too rare |
| Spike cluster / spike-before-turn | REMOVED | common / redundant |
| Tier B `STEADY_EDGE`, `ONE_SIDED`, `LEAD_SWAPPED` (weak fallback), `UNCLEAR` as cards | REMOVED | boring or not an insight (labels still exist inside the classifier) |
| Tier B moderate signals and composite cards | REMOVED | superseded by the final pool |
| Stats-only `isSmoke` line without playback | NOT APPROVED | never validated |
| Literal or geometric map-visibility percentage | PROHIBITED | data does not support visibility |
| Deward → death, deward → tower / net-worth consequence | PROHIBITED | confounded |
| "No ward standing" gaps as enemy pressure | PROHIBITED | wards expire naturally |
| Ward age from deward bounty | PROHIBITED | field does not encode age |
| "Tier A first", exactly-three cards, forced fill, side/result balancing, diversity quotas, generic merge/redundancy/composite engines, universal percentile ranker | PROHIBITED architecture | owner-locked principles |
| Universal "≥ 10 prior matches" record rule | SUPERSEDED | record precision only 51–63% at N = 10 |
| Former product label "Item Execution & Power Spikes" | SUPERSEDED | the family is "Power Spikes & Item Timings" |
| Former Tier B name `CLOSE_THROUGHOUT` | SUPERSEDED | now `CLOSE_MOST_OF_GAME` (classifier label `CT`) |

---

# 16. Deterministic pseudocode (end to end)

```text
function post_match_insights(match, viewer, history) -> InsightResult:
    reason = global_ineligibility(match)                          // §5.1
    if reason: return NOT_ELIGIBLE(reason), []
    b = bucket(match)
    if feeding_guard(match, b): return NOT_ELIGIBLE(FEEDING), []  // §5.2

    side  = viewer.team
    L     = lead_curve(match, side)
    core  = L[0 : max(1, len(L) − 3)]
    shape = classify_tier_b(match, side, b)                       // §9.18: label, runs, S, E, n, detail, confidence
    ids   = reconstruct_wards(match, side) if vision_fields_present(match) else null   // §10
    cards = []

    // ---- Match Lead Story (Tier A)
    if viewer.won and max(−core) ≥ LAD.COMEBACK[b].q:     add(COMEBACK_WIN,    v = max(−core))
    if not viewer.won and max(core) ≥ LAD.COMEBACK[b].q:  add(LOST_FROM_AHEAD, v = max(core))
    flips = sustained_flips(core, ±1500, run ≥ 3, second_run_start ≥ LANE_END[b])
    q = [f ∈ flips : f.min_peak ≥ LAD.FLIP[b].q]
    if q:                                                  add(LEAD_FLIP, flip = last(q), v = last(q).min_peak)

    // ---- Hidden enemy activity
    if b == STANDARD:                            try_add(ENEMY_STACKING)          // §9.7
    if ids != null:                              try_add(VISION_QUICK_CLEARS, ids) // §9.8
                                                 try_add(VISION_REGION_SWEEP, ids, L) // §9.9
    if b == STANDARD and try_add(ENEMY_SMOKE_VOLUME):                              // §9.10
        if playback_usable(match, enemy_of(side)): maybe_enrich(SMOKE_TO_KILLS)    // §11
    try_add(ENEMY_EARLY_RICH)                                                      // §9.11
    try_add(ENEMY_EARLY_ITEM)                                                      // §9.12

    // ---- Tier B
    if shape.label ∉ {SHORT_WINDOW, UNCLEAR} and shape.confidence ≥ 0.7:
        if shape.label == CT:              try_add(CLOSE_MOST_OF_GAME, shape)      // §9.13
        if shape.label ∈ {ETS_FOR, ETS_AGAINST}: try_add(EVEN_THEN_SEPARATED, shape, viewer.won)
        if shape.label == LE:              try_add(LEAD_ERODED, shape, L)
        if shape.label == DR:              try_add(DEFICIT_RECOVERED, shape, L)
        if viewer.won:                     try_add(LATE_REVERSAL, shape, L)        // §9.17
        attach_structure_contradiction(tier_b_cards, shape)

    // ---- History-required (viewer only)
    role = viewer.effective_role
    if role ∈ {CARRY, MID, OFFLANE} and counterpart_resolved(match, viewer):
        w = history.window(key = (b, role), metric = LANE_GAP, max = 50)
        v = lane_gap(match, viewer, LATE[b]); m = LANE_MARGIN[b]
        if len(w) ≥ 20 and (v − max(w) ≥ m or min(w) − v ≥ m): add_hist(OWN_LANE_VS_USUAL, v, w)
        w = history.window(key = (b, role), metric = COUNTERPART_CS, max = 50)
        c = counterpart_cs(match, viewer, LATE[b])
        if len(w) ≥ 20 and c ≥ POP_P90[b][counterpart_pos] and c > max(w): add_hist(OPP_START_VS_HISTORY, c, w)
    if role is known:
        for item in OWN_ITEMS (list order):
            t = first_purchase(viewer, item); if t is null: continue
            w = history.window(key = (b, role, item, major_patch(match)), metric = FIRST_PURCHASE, max = 50)
            if len(w) ≥ 20 and t ≤ min(w) − ITEM_MARGIN[b]: add_hist(OWN_ITEM_VS_HISTORY, t, w); break

    // ---- Severity (§9.0) and history lines (§7.6)
    for c in cards:
        (c.band, c.level) = severity(c, b)
        c.level = round(c.level, 3)
        c.history_line = history_line(c, history, b)             // enemy hosts; never changes band / level

    return EVALUATED, select(cards)                              // §12.4
```

**Required properties (tests MUST cover them)**

- Same inputs + same contract version ⇒ byte-identical output.
- 0 ≤ len(cards) ≤ 3.
- At most one Match Lead Story card.
- Mirror consistency of Tier B labels.
- No Standard value ever enters a Turbo window, and vice versa.
- No missing value is ever treated as zero.

---

# 17. Test vectors

Times are mm:ss; gold values are team net-worth leads from the viewer's side. Values not mentioned are assumed not to trigger any candidate.

**TV-1 — No card (Standard win, 38 min, support)**
- Max deficit on core curve 6,000 (< 12,000).
- Stacks 4 vs 2. Smokes 5 vs 3. Enemy first 10k at 21:00.
- Tier B label `SE_FOR` (never displayed; no enemy last run, so no Late Reversal).
- Support, so no lane history.
- **Eligible:** none. **Output:** `EVALUATED`, `[]`. The normal post-match state renders.

**TV-2 — Feeding guard (Standard, 41 min)**
- An enemy player has 9 deaths before 10:00. A Comeback Win (deficit 22k) would otherwise qualify.
- **Output:** `NOT_ELIGIBLE(FEEDING)`, `[]`. The match also never enters any history window.

**TV-3 — One card (Standard support loss, 34 min)**
- Enemy stacks 13, own 3 (edge 10).
- Level = min(3, 2 + (13 − 13) / (13 − 9)) = 2.000 → EXTREME.
- **Output:** `[ENEMY_STACKING (c2, b3, 2.000)]`.

**TV-4 — More than 3 eligible, story suppression, Comeback vs Lead Flip, history N = 24 (Standard offlane win, 44 min)**

| Candidate | Fact | Class | Band | Level |
|---|---|---|---|---|
| `COMEBACK_WIN` | deficit 19,800 | 1 | 2 | 1 + 300/11,500 = 1.026 |
| `LEAD_FLIP` | min peak 9,000 | – | 1 | 0.262 — suppressed |
| `LATE_REVERSAL` | enemy run peak 9,000 | – | 1 | 0.500 — suppressed |
| `OPP_START_VS_HISTORY` | enemy carry 66 CS at 10:00; P1 p90 60 ✓; > window max 61; N = 24 | 2 | 2 (66 ≥ p95 64) | 1 + 0.48 = 1.480 |
| `ENEMY_STACKING` | 9 vs 2 | 2 | 2 | 1.000 |
| `ENEMY_EARLY_RICH` | enemy 10k at 14:00, own 19:00, gap 5 | 2 | 2 | 1.000 |
| `ENEMY_EARLY_ITEM` | margin 0.25 | 3 | 3 | 2 + 0.03/0.07 = 2.429 |

- The story rule keeps Comeback Win (priority 1) and drops Lead Flip and Late Reversal.
- Sort: Comeback (class 1) → Opponent Start (class 2, band 2, 1.480) → Stacking and Early-Rich tie at band 2, level 1.000 → tie order puts Stacking (6) before Early-Rich (13) → Early Item last (class 3, even though EXTREME).
- **Output:** `[COMEBACK_WIN, OPP_START_VS_HISTORY, ENEMY_STACKING]`.
- History wording allowed on Opponent Start: "across your last 24 Standard Offlane matches" (record); no rarity wording (N < 30).

**TV-5 — Final-push exclusion and story priority (Standard win, 47 min)**
- The only deficit ≥ 12,000 (13,000) appears in the final 3 minute samples, so it is outside the core curve → no Comeback Win.
- Lead Flip: enemy run peaks 10,500 (16:00–24:00), then own run peaks 14,000 (27:00–40:00); min 10,500 → level 2,600/4,200 = 0.619, band 1.
- Close Most of Game: label CT, close share 0.82, n = 34, confidence 0.85 → NOTABLE, level (0.82 − 0.75)/0.15 × 0.99 = 0.462.
- Story rule: Close Most (priority 3) beats Lead Flip (priority 5).
- **Output:** `[CLOSE_MOST_OF_GAME]`.

**TV-6 — History N = 9 (Standard carry loss, 36 min)**
- Own lane gap +3,100, which beats the prior window max by 900, but N = 9 → no card and no historical wording.
- Enemy Sven buys BKB at 17:41 (1,061 s). p5 = 1,288 s → margin 0.1762 → STRONG, level 1 + 0.0262/0.07 = 1.375.
- Enemy item history window (Std + BKB + current major patch) N = 9 → no line.
- **Output:** `[ENEMY_EARLY_ITEM (c3, b2, 1.375)]`, with typical core BKB 28:38 in copy ("about 11 minutes earlier").

**TV-7 — History N = 15 (Standard mid win, 39 min)**
- Own Manta 90 s faster than any prior Standard Mid Manta on this patch, but N = 15 → `OWN_ITEM_VS_HISTORY` ineligible.
- The fact MUST NOT appear anywhere as a record; there is no host card for an own-median line.
- Enemy Early-Rich: 10k at 15:00, own 20:00 → gap 5 → STRONG, level 1.000.
- Enemy goal-minute bucket window N = 15; 15:00 is also the earliest in that window, but record wording is not allowed below N = 20.
- **Output:** `[ENEMY_EARLY_RICH]` with at most a median line: "the median across your last 15 Standard matches was 21:00".

**TV-8 — History N = 24 own-item record (Standard mid win, 42 min)**
- Own BKB at 18:35 (1,115 s); window (Std, Mid, BKB, same major patch) N = 24; min 20:19 (1,219 s).
- Margin 104 s ≥ 60 → record. 104 < 120 and N < 50 → NOTABLE, level 0 + 24/50 = 0.480.
- Enemy Smoke Volume: 9 vs 3, rate 9 × 600 / 2,520 = 2.14 ≥ 1.60 → edge 6 → STRONG, level 1.000.
- Smoke history line (N = 24): not a record → median line only (rarity wording needs N ≥ 30).
- **Output:** `[ENEMY_SMOKE_VOLUME (c2, b2, 1.0), OWN_ITEM_VS_HISTORY (c2, b1, 0.48)]`.
- Own-item wording: "fastest across your last 24 Standard Mid BKB purchases (previous 20:19)". Never "ever".

**TV-9 — Playback absent (Standard loss, 45 min)**
- Enemy Smokes 8, own 2, rate 1.78 → edge 6 → STRONG, level 1.000.
- `playbackData` is null → no Smoke → Kills line.
- Vision (stats reconstruction, independent of playback): 5 identified quick clears out of 18 placed (27.8%) → STRONG, level 1.000.
- Both are class 2, band 2, level 1.000 → tie order: Smoke Volume (5) before Quick Clears (9).
- **Output:** `[ENEMY_SMOKE_VOLUME, VISION_QUICK_CLEARS]`. Quick Clears copy says "at least 5 of your 18".

**TV-10 — Smoke enrichment present (Standard loss, 42:00)**
- Enemy Smokes 7, own 1 (edge 6); rate 1.67. Playback non-null; item events present; playback enemy Smoke count 7 = stats 7.
- Smokes at 10:00, 11:40, 12:10, 20:00, 25:00, 30:00, 40:00. Windows: (10:00, 11:00], (11:40, 12:10], (12:10, 13:10], (20:00, 21:00], (25:00, 26:00], (30:00, 31:00], (40:00, 41:00].
- Kills of your heroes by enemy heroes: 10:50 (isSmoke), 12:25 (isSmoke), 20:30, 25:40 (isSmoke), 31:40, 40:30.
- k = 5 (windows 1, 3, 4, 5, 7). The 12:25 kill belongs only to the 12:10 Smoke; naive counting without truncation would wrongly give 6. The 31:40 kill is outside every window.
- f = 3. Check: 5 ≥ 3, 5 ≥ 4.9, 3 ≥ 2 → fires.
- **Output:** `[ENEMY_SMOKE_VOLUME + enrichment "5 of their 7 Smokes were followed by a kill within a minute."]`. Band and level unchanged (2, 1.000).

**TV-11 — Vision reconstruction with unmatched clears (Turbo loss, 26 min)**
- Own observers: W0 (6:40, 100, 100), W1 (6:50, 150, 140), W2 (15:00, 120, 110), W3 (15:50, 180, 60). Enemy Sentry at 7:20 at (102, 101). Clears at 7:30, 7:50, 16:40.
- 7:30: candidates W0, W1. Only W0 has Sentry evidence (2.2 cells, 10 s old) → W0, tier A, life 50 s.
- 7:50: candidate W1 only (W0 taken); no evidence → tier C, life 60 s.
- 16:40: candidates W2, W3; no evidence; two candidates → **unresolved**, not counted.
- Quick clears = 2 (< 4) → no Quick Clears. No region has 3 identified clears → no Sweep.
- **Output (vision part):** no vision card. Diagnostic: placed 4, destroyed_total 3, identified 2.

**TV-12 — Turbo restrictions (Turbo loss, 24 min, offlane)**
- Enemy Smokes 6 vs 1 → ineligible (Standard only).
- Enemy stacks 10 vs 1 → ineligible (Standard only).
- Quick clears 3 of 9 → ineligible (minimum 4).
- Tier B `LE` with gold peak 9,000 → ineligible (Turbo floor 10,000).
- Enemy Early-Rich: 15k at 11:00 (≤ 12), own at 15:00, gap 4, 13 minutes remain, not Alchemist → Turbo ladder (3, 4, 6) → STRONG, level 1.000.
- The own-lane window uses only Turbo Offlane priors. Standard Offlane matches never count toward its N.
- **Output:** `[ENEMY_EARLY_RICH]`.

**TV-13 — Class beats band (Standard support loss, 46 min; audit example 2)**
- Candidates: `LOST_FROM_AHEAD` (lead 12,200 → band 1, level 0.027), `CLOSE_MOST_OF_GAME` (band 1), `ENEMY_STACKING` (21 vs 1 → min(3, 2 + 8/4) = 3.000, band 3), `LEAD_FLIP` (band 1).
- The story rule keeps Lost From Ahead.
- Sort: Lost (class 1) → Stacking.
- **Output:** `[LOST_FROM_AHEAD, ENEMY_STACKING]`.

---

# 18. Versioning and retroactivity

1. **Stamping.** Every insight result MUST record `contract_version`. Thresholds, ladders, guards, frozen reference tables, history definitions, the classifier, the reconstruction method and the ranking rule are all part of the version.
2. **Change control.**
   - Any change to those elements requires a new contract version and a coordinated update of this document and the JSON.
   - Threshold refits (on production data at launch and after major patches, with Tier B shape-frequency drift monitoring) are version changes, not silent edits.
3. **Nature of cards.**
   - Post-match cards are **derived, ephemeral recap content** attached to a match.
   - They are **not** progression. They never feed baselines, trends or Personal Bests, and never create celebration or notification events.
   - They are not an append-only event ledger.
4. **Computation time and inputs.**
   - The canonical result is computed when the match becomes READY, from the frozen source checkpoint and the ordered prior history available then.
   - Later passive provider data (including playback) never changes it.
5. **Definition changes.**
   - A recap MUST NOT mix cards from different contract versions.
   - When a stored result's version is not current, the system MUST either recompute it deterministically under the current version (frozen source checkpoint + retained prior history) or not display it.
   - Recomputation is deterministic and idempotent. It sends no notifications.
   - This mirrors the project principle that one methodology applies across canonical history (`progress-and-history-v1.md`), without the progression rule that delivered events stay immutable, because cards are not events.
6. **History definition changes** (window size, N gates, cohort keys, patch scope) follow rule 5. Recomputed results use the retained, entitled history that exists at recomputation time.
7. **Role correction.**
   - A confirmed role correction of match M reopens M's insight result, which is recomputed.
   - Later matches whose windows included M SHOULD be recomputed when next displayed.
   - This never triggers notifications.
8. **Entitlement changes** do not rewrite already-computed results for display. Any recomputation uses the entitlement current at recomputation time.
9. **Playback-dependent enrichment** is evaluated only from the frozen source checkpoint. Recomputation MUST NOT invent or drop it from anything other than that checkpoint.
10. **Vision** uses the stats-only method in every version-1 computation, so vision results do not depend on playback retention.

---

# 19. Open issues and reconciliation

## 19.1 Open issues

No product question remains open. The remaining items are routine engineering obligations, not blockers:

1. **Constant packaging.**
   - Ship the JSON contract's frozen tables (Tier B reference percentiles, region label cells, item p5 and typical times) as versioned app/server constants.
   - Maintain the `gameVersionId` → major-patch mapping as patches ship.
2. **Production refit and monitoring.**
   - All ladders and gates come from one 886-match corpus.
   - Refit on production data at launch and after major patches (a version change, §18).
   - Re-validate the vision reconstruction after ward, Sentry or map changes.
3. **Owner re-rating of copy.** All quality ratings came from one research rater. Copy templates SHOULD be spot-checked by the owner when written. This does not block the engine.

## 19.2 Reconciliations made while writing this SSOT

| Topic | Sources disagreed / were silent | Resolution |
|---|---|---|
| Dramatic Lane Path | Decisions doc: owner KEEP; audit: REMOVE | **REMOVED** (owner, 2026-09-17). |
| Smoke Volume mode | Decisions doc: Std + Turbo; audit: Std only, edge ≥ 4 | **Standard only, edge ≥ 4** (owner). |
| Smoke → Kills | Pending owner lock | **LOCKED** with the modified rule (owner). |
| Vision with playback present | Audit pseudocode: "playback exact if usable, else sentry rule"; no ward-playback completeness guard was ever validated, and playback stats counts differed (933 vs 915 observers) | V1 uses the **stats-only reconstruction only**. This keeps results deterministic, recomputable after playback expires, and on the validated method. |
| Research reconstruction second pass | Code ran a W2 = 0 / R2 = 0 pass whose picks were discarded but still marked "taken" | No second pass. Effect is negligible (it matches only a Sentry at the identical cell and second). |
| Late Reversal label condition | Contract text omitted it; the reference code evaluates it only when the label is not SHORT_WINDOW / UNCLEAR | Condition written into the contract. |
| Ladder qualify values | Research eligibility used unrounded percentiles (e.g. 12,169; 7,932; Turbo flip 14,181) while levels used the rounded ladder | The **rounded ladder** (12,000; 7,900; 14,200 …) is used for eligibility and level alike. |
| Own-lane population p95 (Std) | Report and old contract: 2,253; history code: 2,254 | **2,254** (the value the history research used). |
| Level rounding | Research rounded some levels to 3 decimals and not others | All levels are rounded to 3 decimals before sorting. |
| Enemy Early-Rich hero tie-break | Research broke ties by hero name | Lower position number, then lower heroId. Eligibility and band are unaffected. |
| Enemy-cohort history line wording | Audit allowed "the Smoke difference or rate value actually shown" | Line uses the **validated Smoke rate** metric. Enemy item lines use the 60 / 30 s item margin. Stacks and goal minutes use strict records. |
| History median lines at N = 10–19 | Where they attach was unstated | Only on already-eligible enemy cards (enemy wording). Own-metric medians appear only on history cards (which need N ≥ 20). |
| Typical core item time | Referenced but not tabulated | Frozen medians tabulated (§9.12; BKB Std 28:38). |
| Tier B scoring / moderate signals | Tier B report recommended them | Superseded by the final audit pipeline; not implemented. |
| `CLOSE_THROUGHOUT` naming | Old contract text | Classifier label `CT`; card `CLOSE_MOST_OF_GAME`. |

---

*End of normative contract.*

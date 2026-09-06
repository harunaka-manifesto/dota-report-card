# V7 backend capability manifest

```text
PHASE: V7_BE_CAPABILITY_MANIFEST
STATUS: inventory of measured, owner-approved development capability
VALIDATION: NOT production-certified — SEALED_VALIDATION untouched
NEW PROVIDER CALLS: 0
CALIBRATION_RESERVED: not read
SEALED_VALIDATION: not read
```

This is the canonical inventory of what the V7 analytical backend can hand a
product layer. It is organised by **capability**, not by report section, and it
deliberately makes no claim about sequence, screen order or story. Those are the
owner's.

Everything here is built from the current branch: the implementations in
`services/api/app/player_analysis_v7/research/`, the report contract in
`services/api/app/player_analysis_v7/`, the owner decision record, and the
measured evidence in `docs/evidence/`. Where documentation and code disagreed,
the code won and the discrepancy is flagged in §0.2 rather than harmonised away.

---

## 0. Read this before using anything below

### 0.1 Three tiers of availability — the most important distinction in this document

Not everything in the report contract has code behind it. A design agent that
misses this will design screens for data that does not exist.

| tier | meaning | what is in it |
|---|---|---|
| **A — Measured** | Implemented, run over the real corpus, numbers in evidence files | Findings, Recommendation, Archetype |
| **B — Contract-shaped** | A typed, validated Pydantic model exists; **nothing computes it** | History, hero contrasts, death profile, telling-sign, team-in-wins, between-match/in-game loss response, share card, paid bridge, closing, provenance |
| **C — Not available** | Rejected, collapsed, or never built | §9 |

**Every capability in this manifest is labelled A, B or C.** Tier B is not
vapour — the shapes are settled and validated — but no code fills them today,
because there is no V7 report assembly pipeline. See §8.

### 0.2 Discrepancies found between documentation and implementation

Flagged, not silently fixed, per instruction.

| # | discrepancy | current intended truth |
|---|---|---|
| 1 | The report contract defines ten sections' worth of models, but **no producer exists for any of them** — `ReportPayload` is never constructed outside the contract file and its tests. | The contract is a *specification of shape*, agreed and validated. The *measured capability* lives in the research scripts. Assembly is the next phase's work, not a missing file. |
| 2 | `docs/evidence/v7-report-narrative-and-data-requirements-2026-09-04.md` describes sections 1–9 as the report's structure, and several richly specified contrast models (`CoreHeroGoodContrast`, `SupportHeroGoodContrast`, `TellingSignMinute`, `TeamInWinsProjection`, `DeathProfile`) follow from it. None of these is computed anywhere. | These are Tier B. They are a design target the owner may keep, change or drop; the manifest does not treat the §1–9 layout as sacred, as instructed. |
| 3a | The Pass-1 source corpus is gone, so the Pass-1 fits cannot be re-derived. | Recorded per dimension in the frozen parameters; see §0.3. |
| 3 | The ranking-model document originally required a strength band and deferred its cut points to calibration. | Withdrawn under owner decision D2. The document is amended in place with the measurement that withdrew it. There is no band. See §3.6. |
| 4 | `Recommendation.upstream_of_result` exists in the contract as an optional literal, and the implementation carries eligibility as two design-time booleans (`upstream`, `outcome_contaminated`) rather than one field. | The implementation is the truth. The contract field is a coarser summary of a two-rule test; see §4.5. |

### 0.3 Provenance caveat on the Pass-1 dimensions

The Pass-1 history corpus was lost on 2026-09-07
(`docs/evidence/v7-corpus-loss-incident-2026-09-07.md`, CAUSE: UNATTRIBUTED).

The twelve Pass-1 Finding families remain **auditable** — every figure is
committed, digested and traceable to the evidence document that established it
— and they are **no longer source-reproducible**, because the corpus that
produced them no longer exists. They are marked `source_reproducible: false` in
the frozen population parameters, one dimension at a time.

Pass-2 is intact and fully reproducible: canonical re-derives from normalized,
which re-derives from raw. That covers 8 of the 16 Finding dimensions, all 9
recommendation dimensions, and the entire archetype.

Nothing about the product changes. What changes is the claim that may be made
about how a Pass-1 number could be rechecked.

### 0.4 Validation status of everything below

**Current:** intended V7 backend capability, measured on DISCOVERY development
research data and approved by the owner on 2026-09-06.

**Not yet:** production-certified. `SEALED_VALIDATION` (150 accounts, zero rows
collected) remains untouched and is opened only on the owner's express
approval. `CALIBRATION_RESERVED` (150 accounts, zero rows) is also unspent — the
owner closed D2 and D7 on DISCOVERY evidence rather than spend it.

No output below should be described to a user, or in design work, as validated.

### 0.4 Population denominators these numbers come from

| corpus | accounts | note |
|---|---:|---|
| Pass-1 DISCOVERY (match history) | 600 | history-only families |
| Pass-2 DISCOVERY (parsed, event-level) | 276 | everything needing per-event detail |
| Players receiving at least one Finding | 543 | of 600 |
| Players joinable across both corpora | 276 | archetype needs this |

In production a single user is fetched at full depth (§7), so the "conditional
on Pass-2" caveats below are a research-coverage artifact, not a product limit —
provided acquisition succeeds for that user.

---

## 1. Capability index

| # | capability | tier | kind | can refuse? |
|---|---|---|---|---|
| A1 | Report/window metadata | B | metadata | no |
| A2 | Match and parsed-match counts | B | metadata | no |
| A3 | Dominant mode stratum | **A** | metadata | **yes** |
| A4 | Support/eligibility indicators | **A** | metadata | no |
| A5 | Rank display | B | metadata (display-only, fenced) | yes |
| B1 | Finding object | **A** | ranked Finding | n/a |
| B2 | Finding slate (selection + D1 gate) | **A** | ranked Finding | **yes** |
| B3 | 16 shipping Finding dimensions | **A** | analytical measurement | per-dimension |
| C1 | Improvement recommendation | **A** | recommendation | **yes** |
| C2 | Recommendation runners-up | **A** | recommendation | yes |
| D1 | Archetype label + axes | **A** | playful identity | **yes** |
| D2 | Special archetype override | **A** | playful identity | yes (rare by design) |
| E1 | Share-safe ingredient set | B (derived from A) | mixed | inherits |
| F1 | Deeper-analysis material | B | mixed | inherits |
| G1 | Refusal states | **A** | metadata | n/a |
| H1 | Provenance / version block | B | metadata | no |

---

## 2. A — Player and report metadata

### A1. Report and window metadata — Tier B

| field | | |
|---|---|---|
| **Meaning** | When the report was generated and what span of play it covers | |
| **Source** | `ReportProvenance.generated_at`; window is Pass-1 corpus `window.{days,start_timestamp,end_timestamp}` | |
| **Shape** | ISO-8601 string; window is `{days: int, start: epoch, end: epoch}` | |
| **Example** | `generated_at: "2026-09-06T14:20:11Z"`, window 365 days | |
| **Availability** | Always, once assembly exists | |
| **Kind / frame** | Metadata; raw descriptive | |
| **Carries** | No estimate, interval, reliability, score or direction | |
| **FE may claim** | "Based on your last 365 days" | |
| **FE must not claim** | That the window is the player's whole career | |
| **Status** | Contract-shaped; **no producer** | |

### A2. Match and parsed-match counts — Tier B

Total matches in window, product-context matches (ordinary matchmaking the
player finished), and parsed matches available. The distinction matters: many
capabilities need *parsed* matches, and a user with few is a legitimate refusal
case (§6).

Sources: Pass-1 history row count; `tables.is_product_context`;
`pass2_tables.is_pass2_product_context`. Always available once assembled. No
estimate/interval. FE may state counts as facts; FE must not present the parsed
count as a quality score.

### A3. Dominant mode stratum — Tier A, **refusal-capable**

| | |
|---|---|
| **Meaning** | Whether the player mostly queues Standard or Turbo. Every archetype axis is measured and cut *inside* this stratum. |
| **Source** | `archetype.dominant_stratum()` over `tables.mode_stratum` |
| **Shape** | `"STANDARD"` \| `"TURBO"` \| `None` |
| **Example** | `"TURBO"` |
| **Availability** | Conditional — `None` when neither stratum reaches 20 matches |
| **Eligibility** | ≥ `MIN_MATCHES` (20) product-context matches in one stratum |
| **Refusal reason** | `no_dominant_mode_stratum` — 4 of 276 research players |
| **Kind / frame** | Metadata; **mode-relative** — this is the frame everything archetype-shaped is expressed in |
| **Carries** | No estimate/interval/score |
| **FE may claim** | "Most of your games are Turbo"; use it to caption archetype output |
| **FE must not claim** | That Standard and Turbo players are comparable on any archetype axis. **Cuts differ per stratum** — a player at 0.45 fight participation is a ghost in Turbo and is not in Standard. |
| **Caveats** | `"UNKNOWN"` is a fail-closed bucket and is never a dominant stratum |
| **Status** | Measured on DISCOVERY; owner-approved (D5); not sealed-validated |

### A4. Support / eligibility indicators — Tier A

Per capability, the counts behind it: `sample_size` on a Finding,
`sample_wins`/`sample_losses` on a recommendation, `matches`/`sessions` on
archetype measurements. Always available where the parent capability is.

FE may use these as evidence ("across 412 of your matches"). FE must not
convert a sample size into a confidence percentage.

### A5. Rank display — Tier B, **fenced**

| | |
|---|---|
| **Meaning** | Rank movement across the window, **for display only** |
| **Source** | `report_contract.RankDisplay` — `start_rank_label`, `end_rank_label`, `direction` |
| **Shape** | Two display labels (e.g. `"Legend 3"`) plus a direction literal |
| **Availability** | Conditional; absent when not collected or disabled |
| **Kind / frame** | Metadata; raw descriptive |
| **FE may claim** | "You went from Legend 2 to Legend 4 this year" as a fact |
| **FE must not claim** | **Anything analytical.** Rank must never appear as an explanation, a cause, a comparison baseline, or an input to any Finding, recommendation or archetype |

**This fence is enforced, not documented.** `services/api/app/player_analysis_v7/research/rank_fence.py`
refuses any corpus row carrying a rank/MMR-shaped field at both doors into the
analysis (`features.load_frames`, `pass2_tables.iter_pass2_players`), and a
static scan fails the build if an analytical module references one. Values are
display labels, never raw MMR. See owner decision 5.1.

---

## 3. B — Findings

### 3.1 The Finding object — Tier A

Exact fields, from `report_contract.Finding`:

| field | type | meaning |
|---|---|---|
| `dimension_key` | `str` | canonical dimension id (§3.5) |
| `section` | `"what_is_good" \| "what_is_costing_you" \| "response_to_a_loss"` | topical placement, not a verdict |
| `direction` | `"positive" \| "negative" \| "zero"` | `sign(z)` |
| `z` | `float` | `(δ̂ − μ) / τ` — the player's position on the population spread |
| `reliability` | `float` in `[0,1]` | `τ² / (τ² + SE²·D)` — how much of the estimate is signal |
| `score` | `float ≥ 0` | `\|z\| × reliability`. **Enforced** by a model validator |
| `estimate` | `{point, interval_low, interval_high}` | shrunk point estimate with a 95% interval |
| `sample_size` | `int ≥ 1` | matches supporting the estimand |
| `player_facing_question` | `str` | the copy hook, never the raw key |

**There is no strength band.** See §3.6.

### 3.2 What the numbers mean, precisely

- **`z` is population-relative.** It says where the player sits on the spread of
  *other players'* values for this dimension. It is the ruler, not the bar —
  the owner's redefinition is explicit that a player does not need to be unusual
  to be told what they are.
- **`reliability` is a shrinkage weight, not a confidence.** It is the share of
  observed spread attributable to real between-player differences rather than
  measurement noise. **A reliability of 0.92 is not "92% confident".**
- **`score` is a ranking quantity.** It orders a player's own dimensions. It is
  not a percentile, a grade, or a comparison to other players' scores.
- **`estimate` is player-relative and in the dimension's own units.** It is
  shrunk toward the population mean in proportion to reliability.
- **`direction`** selects between two opposite copy variants of the same
  dimension: "you keep playing after a loss" and "you stop for the day" are one
  dimension, two Findings.

### 3.3 Selection behaviour — Tier A (backend behaviour, not UI sequence)

`ranking.select_stratified` then `ranking.apply_score_gate`:

1. **Section representation first.** The top-scoring Finding of each present
   section is taken before anything else, so no Finding-carrying section is
   left empty by score alone.
2. **Then fill by score** up to `REPORT_SLOTS` (5).
3. **Then gate (owner decision D1).** Each present section's best Finding is
   protected; the slate is topped up to `FINDING_FLOOR` (3) by rank; anything
   else must clear `SCORE_LINE` (0.25) to keep its slot.

Measured on 543 players: 400 receive five, 85 four, 50 exactly three, and 8
fewer than three **because they lack the dimensions**, not because the gate
removed them. Three-section coverage is 520 of 543.

> **This is what the backend hands over. It is not a display order.** The array
> arrives ranked by `(−score, key)`; what the UI does with that is the owner's
> decision.

### 3.4 What FE may and may not claim from a Finding

**May:** state the estimate with its units; state the direction; use
`sample_size` as evidence; order Findings by `score`; say a Finding is stronger
*for this player* than another of their own Findings.

**Must not:** convert `score` or `z` into a percentile or "top X%" — the backend
provides no percentile; call `reliability` a confidence level; compare one
player's `score` to another's; describe a Finding as a diagnosis or a cause;
present a Finding whose interval spans zero as a settled fact — the contract
allows it to ship, and it must be phrased as a tendency.

### 3.5 The 16 shipping dimensions — Tier A

All sixteen ship (owner decision D4: reliability shrinkage is the only gate; no
second hard cutoff). Reliability is the DISCOVERY median.

`ctx` = context-adjusted for hero, position, role, lane, patch, mode, duration
bucket and side before any between-player comparison.

| # | dimension | section | source | concept | estimand & units | reliability | n | notes |
|---:|---|---|---|---|---|---:|---:|---|
| 1 | `vision_coverage` | good | Pass 2 | Map covered by your own wards | mean per-match share of minutes with an own observer ward alive; share `[0,1]` | **0.985** | 267 | Empty for a player who never warded — out of scope, not "worst warder" |
| 2 | `duration_tempo` | good | Pass 1 | Whether your games run long or short | mean ctx log match duration | **0.976** | 538 | `D` not plateaued → reliability is an upper bound |
| 3 | `death_clustering` | costing | Pass 2 | Dying again soon after dying | share of death-to-death gaps ≤ 90 s | **0.925** | 273 | Ships as a Finding; **excluded** from recommendations (§4.6) |
| 4 | `lane_vs_jungle_share` | good | Pass 2 | Farming neutrals vs lane creeps | mean per-match share of creep gold from neutrals | **0.924** | 266 | `D` not plateaued |
| 5 | `purchase_tempo` | good | Pass 1 | When your build comes online | mean ctx normalised progress at the 8th item purchase | **0.921** | 116 | Parsed-dependent; `D` not plateaued |
| 6 | `deaths_alone_share` | costing | Pass 2 | Dying away from the fight | mean per-match share of deaths in a minute with no team kill activity | **0.893** | 266 | |
| 7 | `spike_usage` | good | Pass 2 | Using your item window | mean seconds from first real item to next kill/assist | **0.887** | 266 | **Estimand differs from the census**, which reports the median of the same series |
| 8 | `position_flexibility` | good | Pass 1 | Switching position between games | mean ctx probability position changes between consecutive in-session matches | **0.828** | 114 | Parsed-dependent |
| 9 | `fight_timing_centroid` | good | Pass 1 | When in a game you show up | mean ctx normalised-progress centroid of own kill/assist times | **0.810** | 116 | Parsed-dependent |
| 10 | `hero_novelty` | good | Pass 1 | Trying heroes you have not played | mean ctx rate of a hero unseen in 30 days | **0.736** | 525 | `D` = 5.25, the largest; reliability is an upper bound |
| 11 | `closer_vs_comeback` | response | Pass 2 | Closing out leads vs coming back | win rate given a 10k lead **minus** win rate given a 10k deficit | **0.651** | 264 | Contrast; **excluded** from recommendations |
| 12 | `post_loss_session_continuation` | response | Pass 1 | Playing on after a loss | ctx probability another match follows in-session, loss vs win | **0.537** | 536 | |
| 13 | `lead_retention` | costing | Pass 1 | Holding a lead | ctx win indicator, decided-ahead vs decided-behind | **0.480** | 109 | Parsed-dependent; **excluded** from recommendations |
| 14 | `post_loss_hero_switch` | response | Pass 1 | Changing hero after a loss | ctx probability next hero differs, loss vs win | **0.463** | 527 | |
| 15 | `post_loss_requeue_latency` | response | Pass 1 | How fast you requeue after a loss | ctx log gap to next match, loss vs win | **0.380** | 527 | |
| 16 | `fight_conversion` | costing | Pass 2 | Turning won fights into objectives | rate a won fight minute is followed by an enemy tower within 2 min | **0.257** | 273 | Lowest reliability; **excluded** from recommendations |

**Section 4 ("response to a loss") is carried almost entirely by dimensions 12,
14 and 15 — the three lowest-reliability level families — plus the contrast at
11.** The owner was shown this when choosing D4 = all sixteen.

**Pass-2 dependence:** dimensions 1, 3, 4, 6, 7, 11, 16 require parsed
event-level data. Dimensions 5, 8, 9, 13 require Pass-1 parsed data. The rest
need match history only.

**`D` not plateaued** on dimensions 2, 4, 5, 8, 9, 10, 12, 14, 15: the
variance-ratio curve was still rising at the longest measurable batch length, so
`D` is a lower bound and those reliabilities are **upper bounds**.

### 3.6 There is no strength band — Tier C

`StrengthBand`, `default_strength_band` and the band-monotonicity check were
**removed** under owner decision D2, on measurement:

- Over 4,983 player-Findings, the best cut points keeping all three bands
  populated above 5% leave **65.2%** with a 95% interval straddling a boundary.
- A typical interval on `|z| × reliability` is ≈ **0.6 wide**; three populated
  bands need cuts ≈ **0.5 apart**. The interval is wider than the band.
- The interval is dominated by *within-player* measurement error, so **no cohort
  size narrows it**. `CALIBRATION_RESERVED` would have reproduced the result.

**What FE receives instead:** `direction`, `score`, and `estimate` with its
interval. Do not reconstruct slight/moderate/pronounced from `score`. Evidence:
`docs/evidence/v7-cut-point-calibration-dry-run-2026-09-06.md`.

### 3.7 Dimensions that do NOT ship as Findings — Tier C

Five dimensions estimate `τ = 0` under a consistent estimator: their entire
observed between-player spread is explained by dependence-inflated measurement
error. **There is nothing to rank, and no Finding is produced.** Do not design
for these.

| dimension | n | why it is absent |
|---|---:|---|
| `transfer_risk` | 501 | τ = 0 |
| `transfer_activity` | 501 | τ = 0 |
| `lane_to_map` | 258 | τ = 0 — collapsed from an apparent 0.598 once `D` was measured correctly |
| `lane_recovery_participation` | 113 | τ = 0 |
| `side_sensitivity` | 536 | τ = 0 — **the negative control**, and it is supposed to be silent |

`side_sensitivity` is a deliberate placebo. Its silence is the check that the
estimator will not manufacture a Finding from noise. It must never be surfaced.

---

## 4. C — Improvement recommendation

### 4.1 What it is — Tier A

**Exactly one** recommendation per report, drawn from the player's own win/loss
gap. It is a different computation from the Finding ranking on purpose: the most
distinctive thing about a player is often the thing they should keep doing.

### 4.2 The payload

From `report_contract.Recommendation` and `recommendation.ScoredRecommendation`:

| field | type | meaning |
|---|---|---|
| `dimension_key` | `str` | which of the 7 eligible dimensions won |
| `observation` | `{win_value, loss_value, gap}` | the player's own values and the difference, in the dimension's units |
| `direction` | literal | which way the gap runs |
| `recommendation_text` | `str` | imperative, doable next game |
| `verification` | `str` | the exact measurement that will confirm or refute it |
| `sample_wins`, `sample_losses` | `int` | support on each arm |
| `reliability` | `float` | `s² / (s² + SE²·D)` on the dimension's own scale |
| `actionability_weight` | `float` in `[0,1]` | fixed by design, never fitted |
| `priority_score` | `float` | `\|gap/s\| × reliability × actionability` |

The **`verification` field is what separates this from advice.** Every
recommendation names the measurement that will test it, computed from fields
already collected.

### 4.3 Why `tau_d` is not the denominator

The model originally standardised the gap by `tau_d`, the between-player spread
of gaps. **Measured, `tau_d` is exactly zero on every dimension** — for last
hits at minute 10 the between-player variance of the gap is 3.19 against a
dependence-inflated measurement variance of 5.55.

The gaps are not in doubt: the median player takes **2.4 fewer last hits by
minute 10 in their losses**, and 248 of 262 have a negative gap. What is
unmeasurable is how much players *differ* in it. Dividing by `tau_d` asks "is
your gap unusual", which the model's own constraint 3 forbids.

The denominator is `s_d`, the dimension's **own pooled match-to-match spread** —
a unit conversion identical for every player, so a 2.4-last-hit gap and a
0.06-share gap are comparable **without ranking one player against another**.

### 4.4 The seven eligible dimensions

| dimension | actionability | scale `s_d` | gap sign share | median gap | wins slots |
|---|---:|---:|---:|---:|---:|
| `last_hits_at_ten` | 0.95 | 13.257 | 0.9466 | −2.367 last hits | **135** |
| `deaths_alone_share` | 0.90 | 0.239 | 0.6340 | +0.0099 share | 17 |
| `first_real_item_time` | 0.85 | 158.223 | 0.6566 | +5.42 s | 17 |
| `first_ward_time` | 0.80 | 363.229 | 0.5800 | +8.55 s | 29 |
| `lane_vs_jungle_share` | 0.75 | 0.135 | 0.6868 | +0.0090 share | 43 |
| `vision_coverage` | 0.60 | 0.233 | 0.5321 | −0.0012 share | 10 |
| `spike_usage` | 0.45 | 168.209 | 0.8415 | +21.8 s | 14 |

265 of 276 players receive exactly one; **none receive zero**.

Copy and verification strings are fixed in
`services/api/app/player_analysis_v7/research/recommendation.py` and are the canonical wording:

- `last_hits_at_ten` — "For five games, care about nothing but last hits until minute 10." / verified by `last_hits_per_minute` cumulated to minute 10
- `deaths_alone_share` — "Do not cross the river without a teammate on screen."
- `first_real_item_time` — "Buy your first big item before your damage item."
- `first_ward_time` — "Place your first ward before the horn."
- `lane_vs_jungle_share` — "Take the lane creeps when they are there."
- `vision_coverage` — "Replace your ward the moment the old one expires."
- `spike_usage` — "When your item finishes, go and use it."

### 4.5 Eligibility: two rules, both design-time

**Rule 1 — upstream of the result.** A dimension must be a behaviour the player
*emits*, not a result they *receive*. Excluded: `lane_to_map` (net worth at 20
is a scoreboard), `closer_vs_comeback` (win rate given a lead is the result),
`lead_retention` (a team outcome received).

**Rule 2 — not tracking the outcome.** Measured, not judged: **a personal gap
should vary in sign across people.** A gap running the same way for essentially
everybody restates the match result. The cut is a modal-sign share of **0.95**,
fixed before the shares were computed.

Both are recorded as design-time flags, and **the runner re-measures every
dimension and raises if a recorded flag disagrees with the corpus** — the only
way a design-time property cannot drift.

### 4.6 Dimensions excluded for contamination

| dimension | modal-sign share | why |
|---|---:|---|
| `fight_conversion` | **1.0000** | Runs the same way for all 262 players without exception. Passes rule 1 — going to the tower after a won fight *is* the player's decision — and fails rule 2: across a whole match, "you converted fights into towers less" in a game you lost restates that you lost. Before the rule existed it won 168 of 265 slots on the second-lowest actionability weight. |
| `death_clustering` | **0.9886** | Same way for 260 of 263 players. |

Both still ship as **Findings** (§3.5). A dimension can be a legitimate
observation and an illegitimate instruction.

### 4.7 The `last_hits_at_ten` sensitivity — carried forward explicitly

`last_hits_at_ten` sits at **0.9466**, four thousandths under the 0.95 cut, and
wins **51%** of all recommendation slots. At a cut of 0.94 it would be excluded
and the recommendation loses its strongest, most actionable dimension.

It is also the one dimension structurally protected from this failure mode,
being measured entirely inside a window that closes at minute 10, before most
games are decided. The owner reviewed this and kept 0.95 (D3), asking that the
sensitivity be carried rather than absorbed. **It is not a settled comfortable
margin.**

### 4.8 Minimum support and refusal

`MIN_PER_ARM = 15` — a dimension needs 15 wins **and** 15 losses on that
dimension before a gap is offered at all. Owner decision D7, settled by the
DISCOVERY sweep: raising it from 10 to 30 moves median gap reliability from
0.981966 to 0.982515 — five ten-thousandths — while coverage falls 265 → 258.
**Fifteen stands because the curve is flat, not because fifteen was fitted.**

Refusal: no eligible dimension has a denominator → no recommendation. Between 10
and 24 player-dimension pairs per dimension are refused this way in research.

### 4.9 What the recommendation means, and what it does not

**It means:** across this player's own matches, context-adjusted for hero,
position, role, lane, patch and mode, this behaviour differs between the games
they won and the games they lost.

**It does not mean:** that the behaviour caused the losses, or that changing it
will raise their win rate. The model's constraint 5 is explicit — whether acting
on a recommendation improves results is a cohort question this data cannot
answer.

> **Design-critical distinction.** "Behaviour associated with this player's wins
> and losses" ≠ "advice guaranteed to improve win rate". The `verification`
> field exists precisely so the player can test it themselves.

Duration and side are deliberately **not** context controls here: duration is
downstream of the outcome (a stomped loss is short), so controlling for it would
absorb the gap rather than a confounder of it.

### 4.10 Runners-up — Tier A

Two retained, ordered by the same deterministic tie-break (priority, then
actionability, then sample size, then key). Available for a deeper experience.
Selection is order-independent by construction.

---

## 5. D — Archetype

### 5.1 What it is — Tier A

A **playful identity label**, explicitly *not* a Finding and *not* a scientific
classification. The narrative document licenses this section as "for fun, not
for science"; the axes are nonetheless computed from data and nothing here feeds
the ranking model — which is what stops a label acquiring the authority of a
measurement.

### 5.2 Payload

| field | type | meaning |
|---|---|---|
| `tempo` | `"early" \| "mid" \| "late"` | when in a game your impact lands |
| `fight_style` | `"frontliner" \| "opportunist" \| "ghost"` | how you show up to fights |
| `modifier` | `"metronome" \| "streaky"` | how consistent your sessions are |
| `label` | `str` | one of 18 grid labels |
| `is_special` | `bool` | whether a special override fired |
| `special_label` | `str \| None` | `"The Lighthouse"` or `"The Closer"` |
| `stratum` | `"STANDARD" \| "TURBO"` | **the population the label was cut against** |

`stratum` is not decoration. "Mid tempo" means mid *among players who mostly
queue this mode*. Dropping it lets two labels that were never comparable be read
side by side.

### 5.3 Coverage

262 of 276 joinable players receive an archetype — 99 Standard, 163 Turbo. All
**18 grid cells are occupied**; the largest holds 9.6%. Specials fire on 13
players (7 Lighthouse, 6 Closer).

Axis levels: tempo early 85 / mid 88 / late 89; fight style frontliner 119 /
opportunist 59 / ghost 84; modifier metronome 143 / streaky 119.

### 5.4 The 18 grid labels

| | metronome | streaky |
|---|---|---|
| **early · frontliner** | The Alarm Clock | The Opening Act |
| **early · opportunist** | The Early Bird | The Ambusher |
| **early · ghost** | The Quiet Start | The Slow Burn |
| **mid · frontliner** | The Engine Room | The Brawler |
| **mid · opportunist** | The Timekeeper | The Pickpocket |
| **mid · ghost** | The Understudy | The Wildcard |
| **late · frontliner** | The Last Word | The Overtime |
| **late · opportunist** | The Long Game | The Closer's Apprentice |
| **late · ghost** | The Patient One | The Late Bloomer |

### 5.5 Tempo axis

**Definition:** mean, across matches in the dominant stratum, of when the
player's kills and assists occur as a fraction of match duration. Cut at
population terciles **within the stratum**.

**Caveat, and it is the important one.** Tempo is reliably measured (split-half
`r = 0.970`) and **tightly packed**: within a stratum the terciles sit
**0.015–0.018 apart** on a p5–p95 range of about **0.075**. The ordering is
real; the gap between "early" and "mid" separates players who are genuinely
close.

> **FE must present tempo as a relative tendency within the player's dominant
> mode, never as a large behavioural difference.** This is the copy constraint
> the owner attached to D5.

**Mode stratification is load-bearing.** A mode-blind version of this axis —
impact share before a fixed 15 minutes — correlates **0.889** with how much
Turbo a player queues. It was a game-mode detector, not a tempo axis. Turbo is
63% of the Pass-2 corpus.

### 5.6 Fight-style axis

Two measured quantities: **participation** (share of the match's fight minutes
in which the player recorded a kill, assist *or* death — showing up and dying is
still showing up) and **deaths per fight minute**.

| level | definition |
|---|---|
| **ghost** | participation below the stratum's 33rd-percentile cut, whatever the deaths |
| **frontliner** | not a ghost, and deaths per fight minute **at or above** the stratum median |
| **opportunist** | not a ghost, and deaths per fight minute **below** the stratum median |

Stratum cuts differ materially: participation tercile 0.405 Standard vs 0.492
Turbo; deaths median 0.177 vs 0.224. Participation alone correlates 0.585 with
turbo share, which is why the stratification exists.

`ghost` is a low-participation descriptor, **not** a judgement of effort or
skill. Copy must not read as an accusation.

### 5.7 Modifier axis

**Definition:** observed between-session spread in win rate divided by what
independent games at the player's own rate would produce.
`ratio > 1.0` → **streaky**; otherwise **metronome**.

The ratio, not the raw variance, is used deliberately: variance is largest at
p = 0.5, so a raw-variance cut would label every average player streaky.

**The cut is absolute (1.0), not a population median** — splitting the
population at its own median would make half of everyone streaky by
construction, turning a description into a ranking.

**Remaining caveat:** the population median sits at **0.976**, slightly below
1.0. The player's own rate `p` is estimated from the same data, a known small
downward bias in a dispersion ratio, and it is **not corrected**. Treat
near-1.0 values as genuinely ambiguous rather than as evidence of consistency.

(A larger bias was found and fixed: the estimator used population variance
rather than sample variance, biasing the modifier ≈12% toward "metronome" at the
eight-session minimum.)

Not stratified by mode, on purpose: it is a property of how the player's nights
go, and splitting a year of sessions by mode would break the sessions it
measures.

### 5.8 Specials — provisional

| label | fires when |
|---|---|
| **The Lighthouse** | vision coverage at or above the stratum's 98th percentile |
| **The Closer** | win rate from a 10k lead at or above the stratum's 98th percentile |

Both are strengths by design, because a share card must not be an insult. If
both qualify, Lighthouse takes precedence.

> **The 98th-percentile cut is PROVISIONAL for the pilot.** It is
> corpus-relative and will drift as the player base changes. It is refreshed
> from real pilot data, **not** from a reserved split — no reserved data is
> spent on it now. This is the only provisional value left in V7.

### 5.9 Refusal

An archetype is **refused entirely** rather than defaulted when any axis lacks
support. An archetype assembled from two measured axes and one default is a
guess wearing the same clothes as a measurement.

Research refusals among 276: `no_dominant_mode_stratum` 4, `impact_centroid` 4,
`fight_participation` 4, `session_dispersion` 14 (sets overlap; 14 players total
receive nothing).

---

## 6. G — Refusal, null and partial states

The complete matrix. **Do not invent fallback content the backend does not
provide.**

| capability | unavailable when | reason | other capabilities still available? | suggested FE handling |
|---|---|---|---|---|
| Dominant mode stratum | neither stratum reaches 20 matches | `no_dominant_mode_stratum` | Findings and recommendation yes; **archetype no** | omit archetype entirely |
| Tempo axis | < 20 matches in dominant stratum, or no kill/assist events | insufficient event support | others yes | **refuse whole archetype** |
| Fight-style axis | < 20 matches with fight minutes | insufficient event support | others yes | **refuse whole archetype** |
| Modifier axis | < 8 sessions of ≥ 3 matches, or win rate exactly 0 or 1 | insufficient sessions | others yes | **refuse whole archetype** |
| Archetype (whole) | any axis missing | composite | Findings, recommendation yes | omit; never substitute a default label |
| Special archetype | below the 98th-percentile cut | not special — the normal case | grid label still available | show the grid label |
| A Finding dimension | dimension's own support rule unmet | per-dimension | other dimensions yes | omit that Finding |
| A Finding dimension | `τ = 0` for the dimension | no between-player signal | others yes | **dimension does not exist**; never surface |
| Finding slate | fewer than 3 qualified dimensions | too few dimensions | recommendation/archetype may still work | show what exists — 8 of 543 have 1–2 |
| Finding slate | no dimension qualifies | no opportunities | others may work | omit the Findings surface |
| Recommendation | no eligible dimension has ≥ 15 wins **and** ≥ 15 losses | insufficient wins/losses per arm | Findings/archetype yes | omit; **do not substitute a Finding as advice** |
| Recommendation | all eligible dimensions lack support | no valid opportunities | others yes | omit |
| Pass-2 capabilities | account anonymous/private, or no parsed matches | `skipped_anonymous`, `no_valid_opportunities` | Pass-1 Findings yes | degrade to history-only Findings |
| Rank display | not collected or disabled | absent by design | everything else | omit silently |
| Everything | acquisition failed for the account | acquisition failure | none | explain, do not fabricate |

**Two rules that matter most for UX:**

1. **A refusal is never an archetype.** There is no "unclassified" label and no
   default. If the archetype is refused, there is no archetype.
2. **A missing Finding is never a substituted Finding.** Do not promote a
   recommendation, an archetype axis, or a raw statistic into a Finding slot.

---

## 7. F — Acquisition, persistence, and the free/paid boundary

### 7.1 Owner decision D9: full depth for everyone — Tier A (policy), Tier B (storage)

`services/api/app/player_analysis_v7/acquisition_policy.py`:

| constant | value | meaning |
|---|---|---|
| `FULL_DEPTH_MATCHES` | 500 | acquired per pilot user, **every tier** |
| `MATCHES_PER_REQUEST` | 8 | deep matches per provider request |
| `MEASURED_REQUESTS_PER_ACCOUNT` | 45 | measured, not modelled |
| `PAID_MAY_ACQUIRE_MORE_THAN_FREE` | **False** | asserted by test |
| `STORED_MATCH_TTL_DAYS` | `None` | a played match never goes stale |

`depth_for_tier("free") == depth_for_tier("paid") == 500`.

> **Free and paid must not imply different analytical evidence depth during the
> pilot.** Paid differentiation, if any, comes from product interpretation and
> features — never from secretly stronger evidence. A tier that acquired more
> would make an upgrade retroactively change what the free report could have
> said.

Capacity is a **consequence, not an input**: ≈ 333 first-time reports per day at
the 15,000/day ceiling, ≈ 33 per hour. Repeat reports cost nothing, so real
throughput exceeds this by however much of the audience returns.

### 7.2 Persistence — requirements exist, wiring does not

`plan()` is implemented and tested: given an account's candidate matches and
what storage already holds, it returns what to fetch, and **returns nothing when
storage already covers the request**.

`PERSISTENCE_REQUIREMENTS` states five guarantees the storage layer must meet:
raw payloads stored per match so a match is fetched at most once; derived
features stored and keyed by feature version so a version bump recomputes rather
than refetches; **zero provider calls** for an account with no new matches;
account creation and payment reuse the existing analysis; paid output generated
from the same stored matches.

> **Tier B.** The policy decides; the storage wiring that carries a plan to the
> STRATZ client and a result into `app.storage` **is not built**. It lands with
> the V7 report pipeline.

### 7.3 Material that could support a deeper experience

Not a paid-tier design — an inventory: the two recommendation runners-up; all 16
dimension estimates including those outside the 5-slot slate; per-dimension
reliability and intervals; both archetype axis raw values; per-match series
behind every Pass-2 dimension; the win/loss arm values behind every eligible
recommendation dimension.

---

## 8. H — Provenance and versioning the payload must carry

Required so cached output can be interpreted later. `ReportProvenance` currently
carries four of these; the rest are **required additions**.

| field | current value | in contract? |
|---|---|---|
| `generated_at` | ISO-8601 | ✅ |
| `corpus_digest` / provider snapshot | manifest digest | ✅ |
| `feature_version` | `v7-luna-b-features-1.0.0` | ✅ |
| `ranking_model_version` | `v7-luna-f-ranking-1.0.0` | ✅ |
| `inference_version` | `v7-luna-c-inference-1.0.0` | ❌ add |
| `pass2_feature_version` | `v7-pass2-features-1` | ❌ add |
| `pass2_observation_version` | `v7-pass2-observations-1.0.0` | ❌ add |
| `recommendation_version` | `v7-improvement-recommendation-1.0.0` | ❌ add |
| `archetype_version` | `v7-archetype-axes-1.0.0` | ❌ add |
| `acquisition_policy_version` | `v7-acquisition-policy-1.0.0` | ❌ add |
| `owner_decisions_version` | `v7-owner-decisions-2026-09-06b` | ❌ add |
| `report_contract_version` | — none exists | ❌ **add; the contract is unversioned** |
| `data_window` | `{days, start, end}` | ❌ add |
| `acquisition_depth` | 500 | ❌ add |
| `parsed_match_count` | int | ❌ add |
| `validation_status` | `"development"` until sealed validation | ❌ add |

This is a documented contract requirement, not built here.

---

## 9. NOT available from the V7 backend

| not available | why |
|---|---|
| Strength bands (slight / moderate / pronounced) | Removed under D2 — 65.2% of Findings would carry an unsupported band |
| Percentiles, "top X%", grades | The backend produces no percentile. `z` and `score` are not percentiles |
| `transfer_risk`, `transfer_activity`, `lane_to_map`, `lane_recovery_participation` | τ = 0 — no between-player signal |
| `side_sensitivity` | Negative control; must never be surfaced |
| Causal claims | No causal identification anywhere in V7 |
| Rank/MMR as analytical input | Fenced, and the fence is enforced at runtime and in CI |
| A default archetype on refusal | Refusal is refusal; there is no fallback label |
| Recommendations from `fight_conversion`, `death_clustering` | Outcome-contaminated (§4.6) |
| Recommendations from `lane_to_map`, `closer_vs_comeback`, `lead_retention` | Downstream of the result |
| Cross-mode archetype comparison | Cuts are stratum-specific |
| Confidence percentages from reliability | Reliability is a shrinkage weight, not a confidence level |
| Assembled `ReportPayload` | No producer exists (§0.2) |
| Anything from `CALIBRATION_RESERVED` / `SEALED_VALIDATION` | Untouched by instruction |
| `actionsPerMinute` | Quarantined as a hidden skill proxy pending review |
| `roleBasic`, IMP, awards, behaviour scores, provider predictions | Forbidden surfaces |

---

## 10. Sources

`services/api/app/player_analysis_v7/research/{ranking,recommendation,archetype,rank_fence,owner_decisions,pass2_observations,pass2_features,features,inference}.py`;
`scripts/{v7_finding_pipeline,v7_recommendation_selection,v7_archetype_axes,v7_calibrate_cut_points}.py`;
`services/api/app/player_analysis_v7/{report_contract,acquisition_policy}.py`;
`tests/unit/test_v7_{owner_decisions,rank_fence,report_contract,research_*}.py`;
and evidence documents `v7-finding-pipeline-2026-09-05`,
`v7-recommendation-selection-2026-09-06`, `v7-archetype-axes-2026-09-06`,
`v7-cut-point-calibration-dry-run-2026-09-06`, `v7-owner-decisions-2026-09-06`,
`v7-phase-close-qa-2026-09-06`.

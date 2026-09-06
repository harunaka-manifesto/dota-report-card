# V7 content catalog for design

**For a design agent working with the owner in Figma.** You do not need to read
the statistics repository. This file is the complete set of ingredients the V7
backend can supply, described as designable content atoms.

**Your job is to help the owner compose a story from these. This document
deliberately does not contain a story, a screen order, or a card sequence.**
Where an atom lists "suitable for", those are *affordances* — things it could
work as — not a recommendation about where it goes.

```text
STATUS: development capability, measured and owner-approved
NOT YET: production-certified — final validation has not been run
```

---

## How to read an atom

Every atom below has the same fields. Two matter most:

- **Conditionality** — whether it is always there. Many atoms can be *absent*
  for a real user. Design for the absent case.
- **Claims to avoid** — copy that the data does not support. These are not
  stylistic preferences; they are the difference between a true report and a
  false one.

**Illustrative vs canonical.** Example *values* are illustrative — realistic
shapes for mock-ups, not real users. Text marked **canonical copy** is fixed
backend wording and should be used verbatim. Everything else is yours to write.

---

## 1. Quick matrix — every atom

| Atom | Always? | Analytical? | Share-safe? | Numeric? | Can refuse? | Tone |
|---|---|---|---|---|---|---|
| `report_window` | yes | no | yes | yes | no | neutral |
| `match_counts` | yes | no | yes | yes | no | neutral |
| `dominant_mode` | no | no | yes | no | **yes** | neutral |
| `rank_display` | no | **no — display only** | caution | no | yes | neutral |
| `finding` (×5 max) | no | **yes** | depends on direction | yes | **yes** | varies |
| `finding_estimate` | with finding | yes | usually | yes | inherits | neutral |
| `finding_interval` | with finding | yes | no — too technical | yes | inherits | neutral |
| `finding_score` | with finding | yes | **no** | yes | inherits | neutral |
| `finding_sample` | with finding | no | yes | yes | inherits | neutral |
| `recommendation` | no | **yes** | **no** | yes | **yes** | constructive |
| `recommendation_gap` | with rec | yes | no | yes | inherits | potentially negative |
| `recommendation_verification` | with rec | yes | no | no | inherits | neutral |
| `recommendation_runner_up` (×2) | no | yes | no | yes | yes | constructive |
| `archetype_label` | no | **no — playful** | **yes** | no | **yes** | positive/neutral |
| `archetype_tempo` | with archetype | no | yes | no | inherits | neutral |
| `archetype_fight_style` | with archetype | no | caution (`ghost`) | no | inherits | neutral |
| `archetype_modifier` | with archetype | no | yes | no | inherits | neutral |
| `archetype_special` | rare (~5%) | no | **yes** | no | yes | **positive** |
| `provenance` | yes | no | no | no | no | neutral |

## 2. Quick matrix — capability to possible UI affordances

Affordances only. Not a sequence.

| Backend capability | Possible UI uses |
|---|---|
| Archetype label + special | identity card, share-card ingredient, hero moment, profile badge |
| Strongest Finding | hero stat, headline, share-card ingredient |
| Finding slate (up to 5) | supporting cards, comparison cards, expandable detail |
| Finding estimate + interval | detail view, evidence row, tooltip |
| Finding sample size | footer/context, evidence caption |
| Recommendation | recommendation moment, single call-to-action, detail view |
| Recommendation verification | "how you'll know", follow-up hook, detail view |
| Recommendation runners-up | expandable detail, deeper-analysis surface |
| Dominant mode | context caption, qualifier on archetype output |
| Match counts / window | footer/context, credibility line |
| Rank display | history/context only — **never explanatory** |
| Provenance | hidden metadata, debug, cache key |

---

## 3. Metadata atoms

### `report_window`
- **Name:** Your year in Dota
- **Category:** metadata
- **Means:** the span of play the report covers
- **Example:** `{ days: 365, first_match: "2025-09-08", last_match: "2026-09-04" }`
- **Text ingredients:** "the last 365 days", "your 2026 season"
- **Numbers:** days, first/last dates
- **Tone:** neutral · **Treat as:** metadata · **Share-safe:** yes
- **Suitable for:** footer/context, opening context, credibility line
- **Conditionality:** always
- **Avoid:** implying this is the player's entire career

### `match_counts`
- **Name:** Games we looked at
- **Category:** metadata
- **Means:** how many matches the analysis rests on, and how many had full
  event detail
- **Example:** `{ total: 1474, analysed: 1180, with_full_detail: 493 }`
- **Tone:** neutral · **Treat as:** factual measurement · **Share-safe:** yes
- **Suitable for:** footer/context, evidence caption, hero stat if the number is striking
- **Conditionality:** always
- **Avoid:** presenting the full-detail count as a quality score or completeness percentage

### `dominant_mode`
- **Name:** The mode you actually play
- **Category:** metadata (and the frame for every archetype atom)
- **Means:** whether most of their games are Standard or Turbo
- **Example:** `"TURBO"`
- **Text ingredients:** "mostly Turbo", "a Standard player"
- **Tone:** neutral · **Treat as:** metadata · **Share-safe:** yes
- **Suitable for:** context caption, qualifier next to archetype output
- **Conditionality:** **absent** when neither mode reaches 20 matches
- **Refusal:** `no_dominant_mode_stratum` → the whole archetype is also absent
- **Copy constraint:** every archetype statement should be readable as
  "…for a Turbo player", because that is literally what it means
- **Avoid:** comparing a Turbo player to a Standard player on any archetype axis

### `rank_display`
- **Name:** Where you finished
- **Category:** metadata — **display only**
- **Means:** rank at the start and end of the window
- **Example:** `{ start: "Legend 3", end: "Ancient 1", direction: "positive" }`
- **Tone:** neutral · **Treat as:** metadata · **Share-safe:** with caution
- **Suitable for:** history/context surface only
- **Conditionality:** absent when not collected
- **Avoid — important:** never use rank to explain, cause, or contextualise any
  Finding, recommendation or archetype. Rank is fenced from the analysis at the
  code level. "You're Ancient, so you…" is not a sentence this data supports.

---

## 4. Finding atoms

A **Finding** is a pattern in the player's own year, ranked against how much
other players vary on the same measure. Up to five per report.

### `finding` — the object

```jsonc
// ILLUSTRATIVE — realistic shape, invented values
{
  "dimension": "vision_coverage",
  "section": "what_is_good",
  "direction": "positive",
  "estimate": { "point": 0.34, "interval_low": 0.29, "interval_high": 0.39 },
  "score": 1.82,
  "reliability": 0.985,
  "sample_size": 493,
  "display_concept": "You keep more of the map lit than most players do."
}
```

- **Category:** analytical measurement (ranked)
- **Tone:** varies by dimension and direction — see §4.3
- **Treat as:** factual measurement, **comparison-framed**
- **Suitable for:** hero stat (the top one), supporting card, comparison card, expandable detail
- **Share-safe:** depends on direction and dimension — see §7
- **Conditionality:** a player receives 5, 4, or 3; a few receive 1–2. Zero is possible.
- **Numbers available:** `estimate.point` (in the dimension's own units),
  interval bounds, `score`, `reliability`, `sample_size`
- **Directional variants:** every dimension has two opposite readings. `positive`
  and `negative` are *different Findings from the same dimension* and need
  different copy — not one string with a sign flipped.

### 4.1 What each number means, in plain terms

| number | plain meaning | safe copy | unsafe copy |
|---|---|---|---|
| `estimate.point` | the player's own value, in that dimension's units | "about 34% of minutes" | — |
| `interval_low/high` | the range the true value plausibly sits in | "roughly 29–39%" | a precision claim tighter than the interval |
| `score` | how strongly this shows up **for this player, relative to their other Findings** | used to order their own Findings | "top 5%", any percentile, any grade |
| `reliability` | how much of the measure is signal vs noise | internal; gate what you show | "98.5% confident" |
| `sample_size` | matches behind it | "across 493 games" | — |

### 4.2 Backend selection behaviour you can rely on

Not a screen order — just what the array contains:

- The backend already protects **one Finding per section** before filling by
  score, so a player's slate covers as many of the three topics as they have
  material for.
- A slate holds **at least three** Findings where three dimensions exist.
- Slots four and five appear only if they clear a quality line.
- The array arrives ordered strongest-first by `score`.

**520 of 543 development players covered all three sections; 400 got all five.**

### 4.3 The 16 available dimensions

Every dimension is one *possible* Finding. A given user gets at most five.
"Reliability" is how well-measured the dimension is across players — use it to
decide how much weight a design gives a dimension, not as a number to show.

| dimension | display concept | units | topic | reliability | tone |
|---|---|---|---|---|---|
| `vision_coverage` | How much of the map your wards keep lit | share of minutes | good | 0.99 | positive |
| `duration_tempo` | Whether your games run long or short | log duration | good | 0.98 | neutral |
| `death_clustering` | Dying again soon after you died | share of gaps ≤90s | costing | 0.92 | **negative** |
| `lane_vs_jungle_share` | Farming jungle vs lane | share of creep gold | good | 0.92 | neutral |
| `purchase_tempo` | When your build comes online | game progress | good | 0.92 | neutral |
| `deaths_alone_share` | Dying away from your team | share of deaths | costing | 0.89 | **negative** |
| `spike_usage` | Using your item window | seconds | good | 0.89 | neutral |
| `position_flexibility` | Switching roles between games | probability | good | 0.83 | neutral |
| `fight_timing_centroid` | When in a game you show up | game progress | good | 0.81 | neutral |
| `hero_novelty` | Trying heroes you have not played | rate | good | 0.74 | positive |
| `closer_vs_comeback` | Closing leads vs coming back | win-rate difference | response | 0.65 | neutral |
| `post_loss_session_continuation` | Playing on after a loss | probability difference | response | 0.54 | neutral |
| `lead_retention` | Holding a lead | win-rate difference | costing | 0.48 | neutral |
| `post_loss_hero_switch` | Changing hero after a loss | probability difference | response | 0.46 | neutral |
| `post_loss_requeue_latency` | How fast you requeue after a loss | log minutes | response | 0.38 | neutral |
| `fight_conversion` | Turning won fights into towers | rate | costing | 0.26 | neutral |

**Tone is not fixed by the dimension alone** — direction flips it. Low
`deaths_alone_share` is a strength. High `hero_novelty` reads as curiosity; low
reads as loyalty to a pool, which is also fine. Never write a dimension as
inherently good or bad.

### 4.4 The three topics

`what_is_good`, `what_is_costing_you`, `response_to_a_loss`. These are
**topical placements, not verdicts** — a Finding sits under the question it
answers, and its `direction` decides whether it reads as a strength or a cost.
A Finding in `what_is_costing_you` with a favourable direction is good news.

---

## 5. Recommendation atoms

### `recommendation`

```jsonc
// ILLUSTRATIVE shape; recommendation_text and verification are CANONICAL COPY
{
  "dimension": "last_hits_at_ten",
  "observation": { "win_value": 61.2, "loss_value": 58.8, "gap": -2.4 },
  "direction": "negative",
  "recommendation_text": "For five games, care about nothing but last hits until minute 10.",
  "verification": "last_hits_per_minute cumulated to minute 10",
  "sample_wins": 214, "sample_losses": 198,
  "actionability_weight": 0.95,
  "priority_score": 0.34
}
```

- **Category:** recommendation
- **Means:** one behaviour that differs between this player's own wins and their
  own losses — chosen as the single most actionable such difference
- **Tone:** constructive; the underlying gap can read as negative
- **Treat as:** recommendation — **not** a factual claim about cause
- **Share-safe:** **no.** This is the most personal, least flattering atom.
- **Suitable for:** recommendation moment, single call-to-action, detail view
- **Conditionality:** absent when no eligible dimension has ≥15 wins **and** ≥15 losses
- **Exactly one ships.** Never present several as equals.

**`recommendation_text` and `verification` are canonical backend copy.** Use them
verbatim, or design around them — do not paraphrase into a stronger claim.

### The seven possible recommendations — canonical copy

| dimension | canonical text | verification |
|---|---|---|
| `last_hits_at_ten` | "For five games, care about nothing but last hits until minute 10." | last hits cumulated to minute 10 |
| `deaths_alone_share` | "Do not cross the river without a teammate on screen." | share of death minutes with no team kill activity |
| `first_real_item_time` | "Buy your first big item before your damage item." | time of first real-item purchase |
| `first_ward_time` | "Place your first ward before the horn." | time of first observer ward |
| `lane_vs_jungle_share` | "Take the lane creeps when they are there." | share of creep gold from neutrals |
| `vision_coverage` | "Replace your ward the moment the old one expires." | share of minutes with a ward alive |
| `spike_usage` | "When your item finishes, go and use it." | seconds from first item to next kill/assist |

In development, `last_hits_at_ten` won **51%** of all recommendations — design
for it being the most common by a wide margin.

### `recommendation_gap`
- **Means:** the player's own win value, loss value, and the difference
- **Example:** 61.2 last hits in wins vs 58.8 in losses — a gap of 2.4
- **Suitable for:** the evidence beside the recommendation, comparison card
- **Tone:** potentially negative — it is literally "here is what is different when you lose"
- **Avoid:** "this is why you lose". It is an association, not a cause.

### `recommendation_verification`
- **Means:** the exact measurement that will confirm or refute the
  recommendation next time
- **Suitable for:** a "how you'll know it worked" moment, follow-up hook
- **This is the atom that makes the recommendation testable rather than advice.**
  It is worth surfacing.

### `recommendation_runner_up` (×2)
- Two further recommendations, retained but not selected
- **Suitable for:** expandable detail, deeper-analysis surface
- **Avoid:** presenting them alongside the main one as equals — the design
  deliberately ships one

### What the recommendation does and does not mean

| it means | it does not mean |
|---|---|
| Across this player's own games, adjusted for hero, role, lane, patch and mode, this behaviour differs between their wins and losses | That the behaviour caused the losses |
| It is the most actionable such difference we can measure | That changing it will raise their win rate |
| They can test it themselves next game | That it is a diagnosis |

> **This is the single most important copy boundary in the whole report.**
> "Behaviour associated with your wins and losses" ≠ "do this and you will win".

---

## 6. Archetype atoms

**Playful identity, not a Finding and not a diagnosis.** The axes are computed
from data, but nothing here feeds the analysis, and the backend treats it as
"for fun, not for science".

### `archetype_label`

```jsonc
// ILLUSTRATIVE
{
  "label": "The Alarm Clock",
  "tempo": "early", "fight_style": "frontliner", "modifier": "metronome",
  "dominant_mode": "TURBO",
  "is_special": false, "special_label": null
}
```

- **Category:** playful label
- **Tone:** positive/neutral by design · **Share-safe:** **yes** — the most share-safe atom
- **Suitable for:** identity card, share-card ingredient, hero moment, profile badge
- **Conditionality:** absent when any axis lacks support (14 of 276 in development)
- **Refusal:** there is **no default label**. Absent means absent.

**All 18 labels:**

| | metronome | streaky |
|---|---|---|
| early · frontliner | The Alarm Clock | The Opening Act |
| early · opportunist | The Early Bird | The Ambusher |
| early · ghost | The Quiet Start | The Slow Burn |
| mid · frontliner | The Engine Room | The Brawler |
| mid · opportunist | The Timekeeper | The Pickpocket |
| mid · ghost | The Understudy | The Wildcard |
| late · frontliner | The Last Word | The Overtime |
| late · opportunist | The Long Game | The Closer's Apprentice |
| late · ghost | The Patient One | The Late Bloomer |

All 18 occur in real data; the most common holds under 10% of players.

### `archetype_tempo` — early / mid / late
- **Means:** when in a game your kills and assists tend to land, relative to
  other players **who mostly play your mode**
- **Copy constraint — required:** present as a *relative tendency within your
  mode*, never as a large behavioural difference. The three groups are real but
  **sit very close together**.
- Safe: "You tend to show up a little earlier than most Turbo players."
- **Unsafe:** "You're an early-game player and they're a late-game player" —
  overstates a narrow gap.

### `archetype_fight_style` — ghost / frontliner / opportunist
- **frontliner:** shows up to fights and dies in them at or above the median rate for their mode
- **opportunist:** shows up to fights and dies less than the median
- **ghost:** appears in fewer of the game's fight minutes than most players in their mode
- **Copy constraint:** `ghost` is a low-participation descriptor, **not** a
  judgement of effort, skill or contribution. Do not write it as an accusation.
- Fight participation counts a kill, an assist *or* a death — showing up and dying still counts as showing up.

### `archetype_modifier` — metronome / streaky
- **Means:** whether their good and bad nights cluster more than chance would
  produce, given their own win rate
- **streaky:** sessions swing more than independent games would
- **metronome:** sessions look about as varied as chance
- **Caveat:** the measure sits slightly low overall, so values near the boundary
  are genuinely ambiguous. Do not write "metronome" as proven consistency.

### `archetype_special`
- **The Lighthouse** — vision coverage in the top 2% for their mode
- **The Closer** — win rate from a big lead in the top 2% for their mode
- **Conditionality:** rare — about 5% of players (13 of 262 in development)
- **Tone:** **positive** · **Share-safe:** yes — designed to be
- **Suitable for:** hero moment, share card, badge
- **Provisional:** the 2% threshold is a pilot value and will be refreshed from
  real pilot data. Do not build UI that depends on an exact rarity.
- If both qualify, The Lighthouse wins.

---

## 7. Share-safe ingredients

**The share card is not designed here.** This is the set of atoms that could
legally be used in a public context, and the set that must not.

**Share-safe:** archetype label; special archetype; dominant mode; match counts
and window; a Finding whose direction is favourable, phrased as a tendency; a
positive factual statistic.

**Not share-safe:**

| atom | why |
|---|---|
| The recommendation | It is "here is what is different when you lose" — private by nature |
| `recommendation_gap` | Same |
| An unfavourable Finding | "You die alone more than most" is not something anyone shares |
| `finding_score`, `z`, `reliability` | Meaningless out of context and easily misread as a grade |
| `rank_display` | The player's choice, not a default |
| Any internal id or pseudonym | Never leaves the backend |

The backend already applies this principle to the archetype: **both specials are
strengths**, because a share card must be true and must not be an insult.

---

## 8. WHAT THE DESIGN AGENT MUST NOT INVENT

Each of these was either measured and rejected, or is unsupported by the data.

1. **Do not convert `score` into a percentile.** No percentile exists. No "top 5%", no "better than 80% of players", no letter grade, no 0–100 rating.
2. **Do not resurrect slight / moderate / pronounced.** Strength bands were removed after measurement showed two-thirds of Findings would carry a band the data cannot support. Do not re-derive them from `score`.
3. **Do not turn association into causation.** No Finding or recommendation identifies a cause. "This is why you lose" is never supported.
4. **Do not claim a recommendation guarantees wins.** It is a hypothesis with a stated verification.
5. **Do not present archetypes as scientific diagnoses.** They are playful identity labels.
6. **Do not compare Standard and Turbo players on archetype axes.** The thresholds are different per mode. A "ghost" in Turbo is not a "ghost" in Standard.
7. **Do not use rank or MMR as an analytical explanation.** Rank is display-only and fenced in code.
8. **Do not fabricate a missing Finding**, and do not substitute a statistic, an archetype axis, or a recommendation into an empty Finding slot.
9. **Do not turn a refusal into a default archetype.** There is no "unclassified" label.
10. **Do not read `reliability` as a confidence level.** 0.98 does not mean 98% confident.
11. **Do not expose pseudonyms or internal research identifiers.**
12. **Do not invent metrics rejected in research** — see §9.
13. **Do not imply free and paid users get different evidence.** Every pilot user gets the same acquisition depth.
14. **Do not state a Finding whose interval spans zero as settled fact.** Phrase as a tendency.
15. **Do not overstate tempo differences.** The three levels are close together.

---

## 9. NOT available from the V7 backend

Design nothing that needs these.

| Not available | Note |
|---|---|
| Strength bands / grades / ratings | Removed after measurement |
| Percentiles, "top X%" | Never computed |
| Findings on hero transfer, lane-to-map, lane recovery | No measurable between-player signal |
| A "side preference" Finding | Deliberate placebo; must never surface |
| Causal explanations | Not identified anywhere |
| Rank-driven analytical claims | Fenced |
| A default archetype | Refusal has no fallback |
| Recommendations about winning fights or dying repeatedly | Excluded — they restate the match result |
| Cross-mode archetype comparisons | Thresholds are mode-specific |
| Per-match review, matchup advice, draft analysis | Not in V7 |
| Confidence percentages | Not produced |
| Anything about other players by name, or population leaderboards | Not produced |

---

## 10. Availability summary

| Development coverage | Figure |
|---|---|
| Players with at least one Finding | 543 of 600 |
| Players with all three topics covered | 520 |
| Players with a full five-Finding slate | 400 |
| Players with a recommendation | 265 of 276 |
| Players with an archetype | 262 of 276 |
| Archetype grid cells occurring | 18 of 18 |
| Players with a special archetype | ~5% |

Every one of these can be absent for an individual user. **Design the absent
state for each atom, not just the populated one.**

---

## 11. Status

Everything here is **development capability**: measured on research data and
approved by the owner. It is **not production-certified** — the final
end-to-end validation has not been run.

Additionally, some atoms exist as agreed data *shapes* with no code producing
them yet — notably the history statistics, hero-level contrasts and death
profile referenced in earlier product drafts. Those are **not** in this catalog,
because a design agent should not build UI for data the backend cannot currently
return. Everything catalogued above is computed today. See
`docs/product/v7-backend-capability-manifest.md` §0.1.

# Match Detail — Design Requirements

Derived from [`SSOT.md`](SSOT.md) and [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md).

---

## 1. Page role

Match Detail is where a single game gets looked at properly. It holds two different things at once: **how the player performed against a fair expectation**, and **what was notable about the match itself**.

The player should leave able to say what they did well or badly *independently of whether they won*, and with at most a couple of genuinely interesting facts about the game. They should not leave with a grade.

---

## 2. Primary JTBD / user needs

**Primary**

- After a game, I want to know whether I played to my usual standard, so I can tell a bad game from a bad result.
- When I under- or over-performed, I want to know what the app is measuring me against, so I can trust the verdict.
- I want to see anything notable about the match I might have missed, so I learn something I couldn't see while playing.

**Secondary**

- When the app got my role wrong, I want to fix it, so my history stays correct.
- When something isn't available, I want to know that it's missing rather than zero, so I don't misread my own game.

---

## 3. Questions this page must answer

- What happened in this match? (hero, role, mode, result, when, how long)
- How did I personally perform, metric by metric?
- Compared with what — and is that comparison fair given what I played and who I laned against?
- What was unusual about this match?
- What was context versus my own execution?
- Does this match count toward my progress? If not, why?
- Did I set a record here?
- Is my role right?

---

## 4. Entry points & exits

**Entry**
- Home → today's single match
- Home → Last 5 Matches
- History → any row
- Push notification for a READY match
- Profile / Progress → a PB's source match, or a point in a metric series

**Exit**
- → back to where they came from
- → Edit Role (and back, after a rebuild)
- → Retry (action-required / unavailable)
- → Progress for this role (if the design offers it)
- → an explainer for the adjusted expectation

---

## 5. Proposed information architecture

```text
P0 — match identity and result (hero, role, mode, when, duration, win/loss)
P0 — personal performance: per-metric value + its expectation + state
P1 — matchup context (one badge on the lane-metric group)
P1 — match diagnosis: 0–3 insight cards
P1 — PB state where it applies
P2 — progression eligibility and reason, when it doesn't count
P2 — role correction affordance
P2 — explainer / provenance ("what is an adjusted expectation?")
```

Two groupings are **semantically required**:

1. **Personal performance and match diagnosis are separate groups.** They may share a screen; they must not read as one verdict, and must not interleave.
2. **The matchup badge belongs to the lane-metric group**, once per match — not per metric, not in the header next to the result.

Within the insight cards, **order is the engine's output** and must not be changed. Everything else about arrangement is open.

Result placement is genuinely delicate: it belongs to identity, not to performance. Wherever it sits, it must not become the frame the performance layer is read through.

---

## 6. Content & data available

| Content / datum | Meaning | Availability | Notes |
|---|---|---|---|
| Hero, result, mode, date/time, duration | Match identity | Always | Result is a match fact, never a verdict |
| Effective role | Carry / Mid / Offlane / Support | Once classified | Editable here |
| Metric value | The achieved number (raw/display form) | Per metric | May be a legitimate **0** |
| N/A + reason | Metric not meaningfully calculable | Per metric | **Must not look like 0** |
| Personal baseline ("your usual") | Median of the last ≤20 same role+mode+metric | After 5 priors | The comparison for class-A/D metrics and all Turbo |
| Adjusted expectation | Baseline + hero + matchup adjustment | Standard, selected metrics | Explain-on-tap; the adjustment amounts are **hidden from the user** |
| Performance state | Above / In line / Below / Not ready | Whenever the baseline is ready | The per-metric verdict |
| Matchup context | Difficult / Typical / Favourable / unavailable | Standard × Carry/Mid/Offlane only | ~20/60/20. Unavailable ⇒ **render nothing** |
| Baseline-building | Not enough priors yet | Per metric | Countable ("needs 5") |
| PB ownership | This match currently holds the record | After the gate | Ties are not PBs |
| NEW_PB | One-time celebration | Live matches only | Never for imports/backfill |
| Insight cards | 0–3 deterministic cards | **~40% of matches have ≥1** | See below |
| Card content | Facts, times, counts, scoped history ("across your last 34 Standard Mid matches") | Per card | Sequence only, never cause |
| Card enrichment | One optional secondary line | Rare | Never creates a card |
| Eligibility + reason | "Doesn't count toward progression" | When applicable | Reason mandatory |
| Lifecycle state | Six states | When not READY | |

**Card families you may see (never more than 3):** Match Lead Story (comeback, lost from ahead, lead flip, close game, even-then-separated, lead eroded, deficit recovered, late reversal — **at most one of these**), Lane Story (your lane vs your usual; opponent's start vs your history), Hidden Enemy Activity (stacking, quick ward clears, region sweep, smoke volume, early-rich enemy hero), Power Spikes & Item Timings (your fast item; enemy's early key item).

**Card frequency, locked:** about **57–61% of matches show no card at all**. Two cards: 7–9%. Three: 1–2%. Supports see nothing about 66% of the time. **The zero-card state is the majority experience and needs to be designed as a real state, not a fallback.**

**Not available here:** trend states (they're `progress/`), rank/MMR, teammate quality, any overall score, any reason the match was won or lost, any visibility claim from ward data, the numeric size of the hero/matchup adjustments.

---

## 7. Core flows

```text
Open Match Detail
→ understand match identity and result
→ read personal performance metric by metric
→ read notable match insights
→ (optionally) correct the role
```

```text
See a "Below" state that feels unfair
→ open the expectation explainer
→ understand baseline + hero + matchup
→ accept or dispute
```

```text
Notice the role is wrong
→ Edit Role
→ pick the right one
→ metrics, expectations and PB state rebuild for the new role
```

---

## 8. Required states

| State | Product meaning |
|---|---|
| **Just finished — basics available, deeper read still coming** | **The default state for a match the player just played.** The full factual record is here: result, hero, role, duration, the whole scoreboard, items, draft. The deeper sections are still arriving. **Not a loading screen. Not degraded. This is a real, designed state that the player will see often.** |
| **Deeper read arrives while the screen is open** | Sections become available in place. Nothing already on screen moves, reloads or disappears. Needs a legible arrival, not a silent swap. |
| **Deeper read will never arrive** | Terminal. Said **once**, plainly, and then left alone. Not an error, not an apology, not a retry button, not a spinner. The rest of the match is complete and worth reading. |
| **Ready, full** | Everything available. The best case. |
| **Ready, some metrics N/A** | Normal and common (short matches lose the 20:00 checkpoints; a missing replay removes the timeline-derived metrics). Not degraded. |
| **Baseline building** | This metric doesn't have 5 priors in this role+mode yet. Value shows; verdict doesn't. Countable. |
| **Matchup context unavailable** | Show **nothing**. Never a neutral "Typical" chip. |
| **No insight cards** | **The majority case.** A designed, legitimate, non-apologetic state. |
| **1–3 insight cards** | Special-insight state. |
| **Doesn't count toward progression** | Viewable, with reason. No comparisons, no PB evaluation. |
| **Processing** | Analysis is running. The factual record stays fully usable underneath. |
| **Waiting for an earlier match** | The analysis is done; its place in history isn't settled. Explicitly **not an error**. |
| **Needs action** | One Retry. |
| **Unavailable** | Data never arrived. Visible, explained, retryable. |
| **Turbo** | No matchup badge; comparisons against "your usual" rather than an adjusted expectation. |
| **Support** | No matchup badge. Support-specific metric set. |
| **Role correction in progress** | Metrics rebuilding. Needs an honest transitional state. |
| **Correction unavailable** | Telemetry no longer supports a rebuild. Explained, not hidden. |
| **New PB** | One-time moment on a freshly processed match. |
| **Holds a PB (returning visit)** | Current ownership only — quieter than the celebration. |
| **Historic match** | Comparison is "your usual **before this match**", not today's. |

---

## 9. User actions

Open a metric's explainer · edit role · retry a failed match · share a PB · navigate to this role's progression · navigate back · (optionally) expand a card's detail.

---

## 9A. The page arrives in two waves

This is the single biggest thing to design correctly on this page, and it is a design problem, not a loading problem.

**What the player experiences.** They finish a game, open the app a couple of minutes later, and the match is there. They can see what happened — result, hero, their whole scoreboard line, everyone else's, their items, the draft. A few minutes after that, the deeper read arrives: laning, the gold and XP story, item timings, wards, and whatever the app has noticed about the match.

**What that means for design.**

- **The first wave is a real page, not a skeleton.** Design it as something worth opening on its own. A player who never scrolls to the second wave should still feel they got something. Avoid ghost boxes, shimmer placeholders and greyed-out sections standing in for content that has not arrived — they make a complete page look broken.
- **The second wave adds; it never rearranges.** When the deeper read lands, nothing already on screen may jump, reflow or reload. The player may be mid-read.
- **Make the arrival noticeable but not disruptive.** They should understand that something appeared. They should not lose their place.
- **Waiting must be bounded and quiet.** No endless spinner, no progress bar, no ETA, no percentage. The wait has an end, and the design should feel unworried about it.
- **The never-arriving case is a settled fact.** Say it once, in the sections it affects, and move on. It is not an error state and should not borrow error styling. Some matches just do not have a replay.
- **Never name the plumbing.** No provider names, no "parse", no "queue", no "job". The player does not need to know the app gets its data from anywhere in particular, and should never be asked to care.
- **Never show a missing number as zero.** A metric with no evidence is N/A and must look unmistakably different from a real zero.

**Two states worth prototyping explicitly**, because they are common and easy to get wrong: *basics here, deeper read coming*, and *deeper read will never come*.

---

## 10. Experience requirements / guardrails

- **MUST** be fully usable and worth reading before the deeper analysis arrives.
- **MUST NOT** replace, reflow or invalidate content already on screen when the deeper analysis lands.
- **MUST NOT** use an endless spinner, a progress bar, a percentage or an ETA for the deeper sections.
- **MUST** present a permanently unavailable deeper analysis as a settled fact stated once — never as an error, an apology or a retry prompt.
- **MUST NOT** name a data provider or use backend vocabulary anywhere on the page.
- **MUST NOT** let win/loss visually masquerade as personal performance, or frame the performance layer.
- **MUST NOT** merge the personal-performance layer and the insight cards into one verdict or one ranked list.
- **MUST NOT** imply a difficult matchup caused the loss, or soften a "Below" because the matchup was difficult. `Difficult + Below` must read exactly like `Typical + Below`.
- **MUST NOT** put the matchup label and the match result in the same sentence or claim.
- **MUST NOT** compose performance state and matchup context into one string. Relate them in layout if needed.
- **MUST** render N/A visually distinct from a real 0.
- **MUST** render unavailable matchup context as *nothing* — never as "Typical".
- **MUST NOT** judge a Support with Carry expectations, or compare any metric across roles.
- **MUST** make a historical comparison read as time-relative ("your usual before this match").
- **MUST** pair "doesn't count" with its reason.
- **MUST NOT** pad the insight area, add a filler card, or apologise for zero cards.
- **MUST** preserve the engine's card order.
- **MUST NOT** show the numeric hero or matchup adjustment. The user sees value, expectation and state — not the arithmetic.
- Card copy claims sequence, never cause: "after", "within", "followed by" — never "because", "led to", "cost you", "threw", "outplayed".
- Vision counts are lower bounds and must carry "at least".
- History claims must show their sample ("across your last 34 Standard Mid matches"), never "ever" or "all-time".

---

## 11. Design freedom

Open: whether performance metrics are cards, rows, a table or something else; how expectation vs achieved is expressed (bar, delta, position marker, words only, or no chart at all); how the four performance states are differentiated; where and how the matchup badge sits on the lane group; whether insight cards are stacked, paged, expandable or inline; the entire design of the zero-card state; progressive disclosure of the explainer; how N/A and 0 are distinguished; how role correction is entered and how the rebuild transition reads; PB celebration treatment vs quiet ownership; typography, color, density, motion, haptics; whether identity is a header, a hero image, or a strip.

---

## 12. UX success metrics

| Metric | Why it matters | Observable |
|---|---|---|
| Performance-vs-outcome comprehension | The core product claim lives or dies here | Research: after viewing a `FAVOURABLE + BELOW + WIN` match, can the user separate "I won" from "I played below my usual"? |
| Expectation comprehension | "Adjusted expectation" is the hardest concept in the product | Research: can users explain what they're being compared against, with and without the explainer? |
| Role-correction success | A promised behaviour that rebuilds real history | Analytics: corrections started → completed; correction rate by confidence bucket |
| Zero-card satisfaction | The majority state must not feel broken | Research: shown a no-card match, do users report the app "found nothing" vs "nothing unusual happened"? |
| Match dwell / scroll depth | Whether the page is read or bounced | Analytics: time on page and depth, split by card count |

Instrumented: correction completion, explainer opens, dwell/depth, retry success. Research-only: performance-vs-outcome comprehension, expectation comprehension, zero-card interpretation, N/A vs 0 discrimination.

---

## 13. UX risks / questions to test

- Does "adjusted expectation" make sense without explanation? Does one tap fix it?
- Do players read the matchup badge as an excuse, despite the copy rules?
- Do players confuse **matchup difficulty** (a draft property) with **match difficulty** (what happened)?
- Can users separate personal performance from match outcome when the two disagree?
- Does the page become too analytics-heavy — 5–6 metrics plus cards plus badge?
- Does the zero-card state read as "nothing notable happened" or as "the app failed"?
- Do users trust a verdict whose arithmetic is hidden?
- Does a first-time user understand "baseline building", or does it read as broken?
- Does `WAITING_FOR_PRIOR_MATCH` read as an error?
- Does a hidden adjustment that makes the verdict *harsher* feel unfair?

---

## 14. Out of scope

- **Match diagnosis does not decide personal performance.** They are separate systems that share only a match ID.
- Trend states belong to Progress — no Improving/Declining on this page.
- No overall match score, grade or composite verdict, ever.
- V1 does not estimate teammate quality and never mentions a teammate's contribution.
- The page never explains why the match was won or lost.
- Ward data never supports a claim about what anyone could see.
- Long-term identity (signature heroes, role shape) is Profile.
- Browsing and finding matches is History.

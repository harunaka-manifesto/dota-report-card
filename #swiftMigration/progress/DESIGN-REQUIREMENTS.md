# Progress — Design Requirements

Derived from [`SSOT.md`](SSOT.md) and [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md).

---

## 1. Page role

Progress is where a player goes to find out whether they are actually getting better at a specific role, in a specific mode — measured against themselves, not a rank.

They should leave knowing **which of their measured behaviours are moving, in which direction, and how confident the app is** — and knowing that no single number summarises it.

---

## 2. Primary JTBD / user needs

**Primary**

- When I've been grinding a role, I want to know whether anything I do has actually changed, so I know if the effort is landing.
- When I want to improve, I want to see which specific parts of my game are moving and which aren't, so I know where to look.

**Secondary**

- When the app says something is improving, I want to see the evidence, so I believe it.
- When I've beaten my own record, I want to find it and know what it was.
- When there isn't enough data yet, I want to know how much more is needed.

---

## 3. Questions this page must answer

- Am I getting better at this role, in this mode — and at *what*, specifically?
- What is my normal for this metric right now?
- What does this metric even measure?
- How much of my history is behind this claim?
- What's my best ever, and in which game?
- What's still warming up, and how much longer?
- Why do some of my metrics disagree with each other?

---

## 4. Entry points & exits

**Entry**
- Home → a role progression summary
- History → a trend or metric reference
- Profile → "Right now" runs, and PBs
- Main navigation

**Exit**
- → Match Detail (any observation; any PB's source match)
- → a metric explainer ("what is Fight Presence?")
- → another role or the other mode bucket

---

## 5. Proposed information architecture

```text
P0 — the scope: which role, which mode (must be unmistakable)
P0 — per-metric trend state
P1 — per-metric current baseline ("your usual") and recent observations
P1 — readiness: what's building, and how much is left
P2 — per-metric PB with its source match
P2 — metric definitions and limitations
P2 — role activity context (eligible matches, recency)
```

Grouping rules:

- Everything on the page belongs to **one role and one mode** at a time. Scope is not decoration.
- Metrics are **parallel and independent**. They must not read as components of a total, or be ordered in a way that implies weighting.
- Readiness belongs with the metric it gates, not in a separate "problems" area.

No vertical order is semantically required.

---

## 6. Content & data available

| Content / datum | Meaning | Availability | Notes |
|---|---|---|---|
| Role metric set | 6 Carry / 5 Mid / 4 Offlane / 5 Support | Always | Fixed per role. Support Control does not exist. |
| Observation series | Chronological measured values for one metric | Once any history exists | May contain N/A gaps |
| Raw vs comparison value | e.g. ward count vs wards-per-10; healing vs healing-per-10 | Per metric | Baseline and PB use the **comparison** value. Display may use either — but not interchangeably. |
| Current baseline | Median of the last ≤20 eligible observations | After 5 priors | "Your usual" for this metric+role+mode |
| Trend state | Improving / Stable / Declining / Insufficient History | Needs 10 eligible trend points | **Per metric only.** No role-level roll-up exists. |
| Metric polarity | Higher-better or lower-better | Always | Dead time and level-6 time are lower-better |
| Baseline-building count | e.g. "3 of 5" | Always | Countable, honest, temporary |
| N/A point + reason | Not calculable for that match | Per observation | **Never zero**; excluded from baseline and trend |
| Current PB | Value, hero, date, role, mode, source match | After the gate | Ties are not PBs. Current ownership only. |
| Eligible match count | How much history this track has | Always | |
| Role recency | Last time this role was played | Always | A fact, not a verdict |
| Metric limitation | What the metric does *not* measure | Always (static) | Contracted per metric — see foundation §7.3 |

**Not available here:** matchup context, adjusted expectations, hero/lane adjustments (all Match Detail), any composite role score, win rate, MMR, percentile, cross-role comparison, insight cards.

A concrete consequence worth designing around: a player may legitimately see `CS @10 — Improving`, `Farming — Stable`, `Survival — Declining`, `Healing — Insufficient History` **at the same time**. That is the product's truth, not a rendering problem to smooth over.

---

## 7. Core flows

```text
Open Progress for a role
→ scan which metrics are moving
→ open one metric
→ see its history and what it means
→ open a specific match behind it
```

```text
Open Progress
→ switch mode bucket
→ compare nothing across them, but see each honestly
```

```text
Open Progress
→ find a PB
→ open the match that set it
```

---

## 8. Required states

| State | Product meaning |
|---|---|
| **Track never played** | This role has no history in this mode. Unstarted — not zero, not a flat line. |
| **Baseline building** | Fewer than 5 priors. Values may show; no comparison yet. "3 of 5". |
| **Baseline ready, trend insufficient** | Fewer than 10 eligible trend points. `Insufficient History`. **Must not read as decline.** |
| **Improving / Stable / Declining** | The three real trend states. `Stable` must not read as failure. |
| **Metric N/A at a point** | Gap in the series. Never plotted as zero. |
| **Metric with many N/A points** | Common for checkpoint metrics in short games. Honest, not degraded. |
| **Sparse activity** | Long calendar gaps. No decay, no penalty. Recency shown separately if at all. |
| **Entitlement reduced** | Less history exposed; trend may regress to `Insufficient History`. **Not decline, not data loss.** |
| **Rebuilding** | After a role correction or methodology change. No mixed math shown. |
| **No PB yet** | Gate not met, or no qualifying source. Unavailable, not zero. |
| **Offline / sync error** | Known progress stays accurate and readable. |
| **Turbo** | Fully supported; identical methodology; a separate world. |

---

## 9. User actions

Select role · switch mode bucket · open a metric · open an observation's match · open a PB's source match · open a metric explainer · apply a calendar view (if offered) · share a PB.

---

## 10. Experience requirements / guardrails

- **MUST NOT** create a role-level trend, progress score, grade, rating, percentage, or any composite of metrics — including implicitly, by arranging metrics as parts of a whole.
- **MUST NOT** merge Standard and Turbo, or two roles, into one series.
- **MUST** make the selected role and mode unmistakable at all times.
- **MUST** respect metric polarity — a downward line can be `Improving`.
- **MUST NOT** style `Insufficient History` as a negative result, or `Stable` as stagnation.
- **MUST NOT** plot, interpolate across, or otherwise absorb N/A points as zero.
- **MUST NOT** show a matchup badge, adjusted expectation, or hero/lane adjustment. Progress runs on the raw personal baseline.
- **MUST NOT** let a calendar filter imply it changed the trend. The filter is a view.
- **MUST NOT** present an entitlement-driven regression as decline.
- **MUST** keep the raw observation series available — the baseline must not replace or hide it.
- **MUST NOT** present win/loss or a win-rate curve as progression.
- Historical match comparisons used the baseline at *that* time; the current baseline shown here is a different thing and must not be worded as if it were the same.

---

## 11. Design freedom

Open: whether metrics are cards, rows, or a single scrolling detail; whether to chart at all, and which chart form (line, dot, band, sparkline, distribution) — the data meaning only requires that N/A is not zero and polarity is honest; how the four trend states are expressed (word, glyph, color, position); how "your usual" is shown relative to observations; how readiness counts are expressed; where the mode toggle and role selector live; whether metric explainers are inline, on tap, or on a separate layer; PB presentation; density and typography; motion and transitions; how the page handles four metrics disagreeing.

---

## 12. UX success metrics

| Metric | Why it matters | Observable |
|---|---|---|
| Trend comprehension | The page's single job is conveying direction honestly | Research: shown a mixed set of metric states, can the user say what's moving and resist inventing an overall verdict? |
| Polarity comprehension | A lower-better metric improving downward is the classic misread | Research: shown `Survival — Improving` with a falling line, does the user read it correctly? |
| Depth of exploration | Whether the page rewards going past the summary | Analytics: metric detail opens per Progress session; observation → Match Detail rate |
| Return after a gate is met | Whether readiness counts motivate | Analytics: return rate among users who saw "needs N more" and later crossed it |

Instrumented: metric opens, match navigations, PB opens, mode/role switches. Research-only: trend comprehension, polarity comprehension, `Insufficient History` interpretation, composite-verdict invention.

---

## 13. UX risks / questions to test

- Do users invent an overall role verdict anyway when four metrics disagree?
- Is `Insufficient History` read as a bad result?
- Is `Stable` read as "I've stopped improving"?
- Does a lower-is-better metric read correctly, or does a falling line always feel bad?
- Do users understand why a raw number (12 wards) and the compared number (wards per 10) differ?
- Does a series with many N/A gaps look broken?
- Do users expect Turbo and Standard to add up — and feel cheated that they don't?
- Is a countable gate ("3 of 5") motivating or discouraging at the very start?
- Does the absence of the matchup badge here, after seeing it on Match Detail, feel inconsistent?

---

## 14. Out of scope

- Progress is not Match Detail — no per-match verdicts, matchup context, adjusted expectations or insight cards.
- Progress is not History — it does not browse matches chronologically across roles.
- Progress is not Profile — it measures, it does not conclude who the player is.
- No overall progress score, skill rating, percentile, or MMR relationship, ever.
- No cross-role or cross-mode comparison.
- No causal explanation of why a metric moved.
- Achievements, medals, challenges and reports are not contracted in V1.

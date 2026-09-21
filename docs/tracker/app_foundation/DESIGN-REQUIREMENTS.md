# App Foundation — Design Requirements

Cross-cutting brief. Read once; every other feature brief assumes it.
Derived from [`SSOT.md`](SSOT.md). Nothing here is a visual specification.

---

## 1. Page role

Not a screen. This is the shared semantic layer every screen inherits: how the app talks about data it has, data it lacks, the player's role, their history, and the difference between what they did and what happened to them.

A player should leave any screen in this app knowing **which parts of this are about me, which parts are about the match, and how confident the app is**.

---

## 2. Primary JTBD / user needs

Cross-product, so these sit behind every feature's own needs.

| | Need |
|---|---|
| **P1** | When I look at anything in this app, I want to know whether it's judging *me* or describing *the match*, so I don't take a loss personally or a win as proof I played well. |
| **P2** | When the app doesn't know something, I want it to say so plainly, so I can trust the numbers it does show. |
| **P3** | When I've only just started, I want to understand what's still warming up and roughly when it unlocks, so the empty app doesn't feel broken. |
| **S1** | When something about my data changes (I corrected a role, my subscription lapsed), I want to understand why the numbers moved without thinking the app is unreliable. |

---

## 3. Questions every surface must be able to answer

- Is this about my performance, or about the match?
- Which role and which mode is this number about?
- Is this measured, or is it unavailable?
- Compared with what — my recent usual, an adjusted expectation, or my all-time best?
- Is there enough of my history for this to mean anything yet?
- Why did this change?

---

## 4. Entry points & exits

Not applicable as a surface. The shared behaviours that cross every boundary:

- **Pull-to-refresh / app open / app resume** triggers discovery from anywhere that shows match data.
- **Any match reference** anywhere (Home, History, Profile, a PB) leads to Match Detail.
- **Any role/metric reference** can lead to that role's progression view.
- **Any "Why?" / explainer affordance** must be able to show the definition, window, sample size and contributing matches behind a claim.

---

## 5. Proposed information architecture

The priority order that holds across the app when several of these compete for attention:

```text
P0 — what is this (identity: match / role / mode / hero / date)
P0 — the one thing this surface exists to say
P1 — the personal-performance layer (me vs my own expectation)
P1 — the match-context layer (what happened, matchup context)
P2 — supporting raw values
P2 — provenance and explainers ("Why am I seeing this?")
P3 — navigation onward
```

Two hard groupings, everywhere:

1. **Personal performance** and **match diagnosis** are different groups. They may sit on the same screen; they must not read as one verdict.
2. **Stable truth** (identity, baselines, PBs) and **current/temporary signals** (recent runs, this week) are different groups. Temporary items must always carry their window.

---

## 6. Content & data available

Designer-relevant primitives the whole app can produce. Every feature brief draws from this vocabulary.

| Content / datum | Meaning | Availability | Notes |
|---|---|---|---|
| Match identity | Hero, result, date/time, duration, mode | Always for a retained match | Result is a match fact, never a performance verdict |
| Effective role | Carry / Mid / Offlane / Support | Always once classified | P4 and P5 are both "Support". Editable. |
| Role confidence | high / low | Always | Only **low** surfaces a prompt; never shown as a number |
| Mode bucket | Standard / Turbo | Always | Two separate worlds; never merge their histories |
| Lifecycle state | waiting / analyzing / waiting-for-prior / action-required / ready / unavailable | Always | Six states; needs six meanings, not one spinner |
| Sync state | idle / checking / up-to-date / sync-error | Always | Account-level; never overrides per-match state |
| Metric value | 20 role metrics; raw and comparison forms | Conditional | May be a legitimate 0 or an N/A — different states |
| Personal baseline ("your usual") | Median of last ≤20 same role+mode+metric | After 5 prior measured observations | Per metric, per role, per mode. Not global. |
| Adjusted expectation | Baseline + hero + matchup adjustment | Standard only; selected metrics only | Turbo and some metrics compare to raw "your usual" instead |
| Performance state | Above / In line / Below / Not ready | Whenever the baseline is ready | The per-metric verdict |
| Matchup context | Difficult / Typical / Favourable / unavailable | Standard × Carry/Mid/Offlane only; ~20/60/20 split | One badge per match, on the lane-metric group. Unavailable ⇒ show nothing. |
| Trend state | Improving / Stable / Declining / Insufficient History | Needs 10 eligible trend points | Per metric. Never per role, never overall. |
| Current PB | Best value + hero + date + source match | After the 5-prior gate | Ties are not PBs. Current ownership only. |
| NEW_PB event | One-time celebration | Live matches only | Never retroactive for imports/backfill |
| Insight cards | 0–3 deterministic match-pattern cards | ~40% of matches have ≥1 | Sparse by design; 0 cards is the majority case |
| Progression eligibility + reason | Whether the match counts | Always | Ineligible matches stay visible and explain why |
| Profile claims | Durable identity statements with receipts | Maturity-gated | See `profile/` |
| Entitlement | Free / Pro, and entitled history depth | Always | Changes history *depth*, never accuracy |

**What the app cannot give you, ever:** overall score, grade, rating, percentile, MMR, rank, skill radar, teammate quality, a reason the match was lost, a composite role verdict.

---

## 7. Core flows

```text
Open app → cached state is usable immediately → discovery runs in background → new results appear
```

```text
See a role that looks wrong → Edit Role → confirm → affected history rebuilds → numbers update
```

```text
Hit a claim you don't believe → "Why?" → definition + window + sample + contributing matches
```

---

## 8. Required states

Design these once as a system; every feature reuses them.

| State | Product meaning |
|---|---|
| **Ready** | Everything applicable concluded. May still contain N/A values. |
| **Processing** | Work is in progress. Six distinguishable causes exist (see §6); at minimum, "waiting on data" and "analyzing" must be tellable apart from "needs you". |
| **Waiting for an earlier match** | Correct and temporary. Not an error. The result is fine; its *position in history* isn't settled. |
| **Action required** | Automatic attempts are exhausted. One Retry action. |
| **Unavailable** | Trustworthy data never arrived. Still retryable. Not deleted, not hidden. |
| **Sync error** | The *account's last check* failed. Everything already known stays usable and accurate. |
| **Offline** | Cached content remains fully usable; freshness is in question, correctness isn't. |
| **N/A value** | Cannot be meaningfully calculated. Must be visually distinct from a real zero. |
| **Baseline building** | Not enough of *your* history for this metric+role+mode yet. Honest, temporary, countable ("needs 5"). |
| **Insufficient history (trend)** | Fewer than 10 eligible points. Not a decline. |
| **Not eligible** | Match doesn't count toward progression, with a reason. Still viewable. |
| **No Steam linked** | The app works; tracking doesn't. |
| **Data access blocked** | Steam is linked but match data is private. Recoverable, with guidance. |
| **Free** | Coherent and complete within entitled history. Never framed as broken or degraded truth. |
| **Pro** | More history depth. Never framed as more accurate. |
| **Entitlement changed** | History depth moved. Must not read as performance change. |
| **Empty / nothing unusual** | A legitimate, reassuring outcome — not a failure. |

---

## 9. User actions

Connect Steam · refresh / retry · edit role · open a match · switch mode bucket (Standard/Turbo) · switch role context · open an explainer ("Why?") · share a PB or profile card · manage subscription · manage notifications.

---

## 10. Experience requirements / guardrails

- **MUST NOT** let win/loss visually masquerade as personal performance, or sit inside the same verdict as it.
- **MUST NOT** imply a difficult matchup caused a loss, or soften a "Below" state because the matchup was difficult. `Difficult + Below` reads exactly as `Typical + Below`.
- **MUST NOT** compose matchup context, performance state and trend into one sentence. If they must be related, relate them in layout.
- **MUST NOT** render N/A as zero, or an unavailable matchup as "Typical". Unavailable means *show nothing*.
- **MUST NOT** judge a Support using Carry expectations, or compare any metric across roles.
- **MUST** keep Standard and Turbo distinguishable wherever their histories differ.
- **MUST** make a historical comparison read as time-relative ("your usual before this match"), never as today's baseline.
- **MUST** pair "doesn't count toward progression" with its reason.
- **MUST** show a window label on anything temporary ("last 10 Carry matches").
- **MUST NOT** fill an empty slot with a lower-value fact to avoid whitespace. Absence is a designed state.
- Language for matchup context describes the **draft on paper**, not the lane that was played. Never "your lane was easy".

---

## 11. Design freedom

Everything below is yours unless a guardrail above is engaged:

- layout, grouping, and vertical order (except where sequence is semantically required);
- card vs non-card, list vs grid, sectioning, density;
- progressive disclosure and where explainers live;
- visual hierarchy technique, typography, color, iconography, spacing;
- chart form and whether to chart at all;
- how the six processing states are visually differentiated;
- how N/A and zero are distinguished (only *that* they must be);
- motion, transitions, microinteractions, haptics;
- how Free/Pro boundaries are surfaced;
- navigation patterns, tab structure, and where the mode toggle lives.

---

## 12. UX success metrics

| Metric | Why it matters | Observable |
|---|---|---|
| Comprehension of performance vs outcome | The core product claim fails if users read a loss as "I played badly" | Research: after viewing a match, can the user say what the app said about their play vs the match? |
| N/A vs zero discrimination | A misread N/A is a trust-destroying error | Research: shown both, can users tell them apart and say which is which? |
| Recovery from problem states | Unavailable / action-required / no-Steam must be exitable | Analytics: retry and connect-Steam success rate from each state |
| Role-correction success | Correction is a promised behaviour and it rebuilds real history | Analytics: corrections started → completed; post-correction confusion in research |

Instrumented: retry success, correction completion, connect-Steam completion. Research-only: comprehension, N/A discrimination, perceived trustworthiness.

---

## 13. UX risks / questions to test

- Does "adjusted expectation" mean anything to a player without the explainer? Does the explainer land?
- Do players read "Difficult matchup" as an excuse, despite the copy rules?
- Can players distinguish "the app has no data" from "I scored zero"?
- Does "Baseline building" read as *temporary* or as *broken*?
- Do players understand that Standard and Turbo don't share progress — or do they read it as data loss?
- Does "Insufficient history" get read as a negative result?
- Is a mostly-empty insight area (the majority case) acceptable, or does it read as a failure?

---

## 14. Out of scope

- This is not a screen and must not become one; there is no "foundation" surface.
- No design here decides feature-level IA — that lives in each feature brief.
- Metric formulas, thresholds, classifier constants and parameter derivation are engineering concerns; the designer needs the *meaning*, in §6.
- Reports, recaps, achievements, challenges and medals are not contracted in V1.

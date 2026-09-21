# Home — SSOT

**Status:** ACTIVE — feature contract. Core content set by owner direction (2026-09-20).
**Scope:** The default authenticated surface: today's state, the Challenge slot, role progression summaries, recent matches, and the routing rules out of Home.
**Inherits:** [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md).

## Architecture dependencies

| Concern | Authoritative source |
|---|---|
| Evidence readiness; when a match becomes acknowledgeable | [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §4A · [`../architecture/MATCH-INGESTION-AND-LIFECYCLE.md`](../architecture/MATCH-INGESTION-AND-LIFECYCLE.md) §3 |
| Which Home blocks need which evidence class | [`../architecture/FEATURE-DATA-DEPENDENCY-MATRIX.md`](../architecture/FEATURE-DATA-DEPENDENCY-MATRIX.md) §5 |
| Degradation behaviour behind Home's states | [`../architecture/SCALING-RELIABILITY-AND-OPERATIONS.md`](../architecture/SCALING-RELIABILITY-AND-OPERATIONS.md) §6 |

---

## 1. Purpose

Home answers, in one screen:

> Has anything happened since I last looked, and is anything about my Dota moving?

It is the daily entry point and the routing hub. It is **not** a condensed version of every other screen. It summarises and hands off.

Home must be usable immediately from cached state on every open, before discovery completes.

---

## 2. Locked core content

Owner direction fixes **what** Home contains and **what each item leads to**. It fixes nothing about layout, component type, or arrangement.

| # | Element | Condition | Leads to |
|---|---|---|---|
| 1a | **Today's Focus** | No match has been played today (no match discovered with today's local date) | Open — see §4 |
| 1b | **Today's Matches** | At least one of today's matches exists | **One** match → may lead directly to Match Detail. **Multiple** → may lead to the relevant History view. |
| 2 | **Challenge** | Always present as a slot | Challenge surface (not contracted in V1 — see §5) |
| 3 | **Role progression / trend summaries** — Carry, Mid, Offlane, Support | Always present | Deeper role analysis in `progress/` for that role |
| 4 | **Last 5 Matches** | Always present | `history/` |

Elements 1a and 1b are **mutually exclusive**. Element 1 is a single slot with two modes.

This list is the V1 Home content set. Additional content MUST NOT be added to Home without an explicit owner decision.

---

## 3. Today's Matches

### 3.1 Definition

"Today" means matches whose chronology places them in the user's current local day. A match qualifies once it is **discovered**, regardless of lifecycle state.

Today's Matches spans **both** progression buckets — it is a chronological view, not a progression calculation, so mixing Standard and Turbo here is permitted. Each match MUST carry its own mode.

**Home MUST acknowledge a completed match as soon as summary-class evidence exists** (`SUMMARY_READY`, foundation §4A). It MUST NOT wait for replay-derived analysis before showing that the match happened. A match played today is part of the user's day whether or not its deep analysis has landed.

### 3.2 What a today's-match entry may express

Per match, Home MAY show any of the following once available:

- match identity (hero, result, mode, time, duration);
- effective role;
- lifecycle state when not READY (see foundation §4.3);
- progression ineligibility with its reason;
- the number of insight cards available (0–3), if useful;
- readiness of the personal-performance layer.

Home MUST NOT reproduce the full Match Detail analysis. Per-metric values, performance states, matchup context and insight card content belong to `match_detail/`.

### 3.2a Readiness behaviour (normative)

1. **A match appears at `SUMMARY_READY`.** It is never withheld pending deep analysis.
2. **Navigation into Match Detail is always available** from a today's-match entry, at any readiness. Match Detail is useful from Stage 1 (see [`../match_detail/SSOT.md`](../match_detail/SSOT.md) §3A.1).
3. **Readiness MAY be indicated subtly** — a quiet marker that the deeper read is still coming, or that it is ready. It MUST be subordinate to the match itself, never the entry's headline.
4. **Home updates when readiness advances.** A match acknowledged earlier in the day reflects its finalized state once analysis persists, without the user re-triggering anything.
5. **An entry never disappears or regresses.** A match acknowledged at Stage 1 stays acknowledged.
6. **Readiness is expressed in plain language, never in backend terms.** Home MUST NOT name a provider or use pipeline vocabulary — the user does not need to know what a replay parse is, and Home is the surface where that temptation is strongest. See foundation §4A.5.
7. **A match whose deep analysis will never arrive is not an error on Home.** It is an ordinary completed match. Home MAY show nothing unusual about it at all; the explanation belongs on Match Detail.

### 3.3 Routing

- Exactly one match today → Home MAY route straight into Match Detail.
- More than one → Home MAY route to the relevant History view.

"May" is deliberate: the route is permitted, not mandated. The designer may also route every case through an intermediate.

---

## 4. Today's Focus

### 4.1 Status

**The slot is locked; its content is OPEN.** This is a genuine, owner-level product gap (§10).

### 4.2 What is contracted now

- It occupies element slot 1 when today has no matches.
- It is a single, forward-looking prompt — one thing, not a list of suggestions.
- It MUST be derived only from state this product already contracts: baseline readiness counts, trend states, role activity recency, PB state, challenge state, entitlement state, sync/lifecycle state.
- It MUST NOT fabricate a goal, a coaching recommendation, a target number, or a prediction.
- It MUST NOT tell the user what to play, which hero to pick, or which role to queue.
- It MUST NOT imply a performance verdict.
- If nothing honest qualifies, the slot renders an honest neutral state or nothing. Padding it is forbidden.

### 4.3 Explicitly not decided

Which signals are eligible, their priority, the copy model, whether it is dismissible, and whether it changes within a day.

---

## 5. Challenge

### 5.1 Status

**The slot is locked by owner direction; the Challenge feature is NOT contracted for V1.**

Challenge/mission mechanics are listed as deferred in the foundation SSOT §19. No challenge definition, eligibility rule, progress model, reward model or completion semantics exists in any locked document.

### 5.2 Consequences

- Home reserves the slot.
- No SSOT in this repository can currently specify what a Challenge is. A `challenges/` feature folder is deliberately **not** created, because doing so would manufacture a contract that does not exist.
- Any Challenge that ships MUST inherit the foundation invariants: no composite score, no win/loss-based progression, no teammate attribution, no causal claims, Standard/Turbo isolation, and N/A ≠ zero.
- Until the feature is contracted, Home MUST be designable with the slot in an "unavailable / coming" or absent state without the rest of Home breaking.

### 5.3 Readiness constraints on any future Challenge

Recorded now so a future contract does not have to rediscover them. These constrain the shape of a Challenge; they do **not** invent one.

1. **Each challenge is classified by its own evidence requirement** ([`../architecture/FEATURE-DATA-DEPENDENCY-MATRIX.md`](../architecture/FEATURE-DATA-DEPENDENCY-MATRIX.md) §7). A challenge counting final last hits resolves from summary-class evidence; a challenge counting ward timing needs replay-class evidence.
2. **A single generic "match processing" flag MUST NOT gate all challenges.** Different evidence, different gate — otherwise a scoreboard-only challenge waits for a replay it never needed.
3. **A challenge is never declared failed because its required evidence has not arrived.** The states are **pending**, **resolved** and **unavailable**. Pending is not failure.
4. **A challenge whose evidence will never arrive becomes `unavailable`**, terminally and understandably — not failed, and not permanently pending.
5. The same three-state rule applies to any achievement requiring a replay-derived event.

---

## 6. Role progression summaries

### 6.1 Contract

Four summaries: **Carry, Mid, Offlane, Support** — one per role, for the **selected mode bucket**.

Each summary MAY express:

- the role;
- the role's canonical per-metric trend states, or an honest reduction of them (see §6.2);
- baseline-building / insufficient-history status;
- recency of activity in that role;
- entry to the role's deeper analysis in `progress/`.

### 6.2 Hard constraint on summarisation

There is **no composite role trend, role score, role grade, or overall role verdict** (foundation §11.2). A role summary MUST NOT invent one.

Permitted reductions are **evidence-bound and metric-named**, for example:

- listing the role's metric states;
- naming the metrics that are Improving and those that are Declining;
- stating that a role has insufficient history.

Forbidden:

```text
"Your Carry is improving."
"Carry: 78"
"3 of 4 metrics improved, so Carry is trending up."
```

### 6.3 Empty and unready roles

A role with no eligible history in the selected bucket is shown in an explicit empty/unstarted state, or omitted — never as zero, and never as a neutral/flat trend. A role with history but fewer than 10 eligible trend points for a metric shows `Insufficient History` for that metric, which is **not** a decline.

### 6.4 Mode

Role summaries are progression calculations, so they are **strictly per bucket**. Home MUST make the selected bucket unambiguous wherever role summaries appear, and MUST NOT merge Standard and Turbo into one summary.

Which bucket Home defaults to, and whether Home exposes a toggle, is open to design, subject to the disambiguation requirement.

---

## 7. Last 5 Matches

- The **5 most recent retained matches** for the active Steam profile, in reverse chronological order.
- Spans both buckets (chronological, not a progression calculation). Each entry carries its mode.
- Includes progression-ineligible and non-READY matches. They are part of what the player played.
- Each entry MAY carry: hero, result, mode, effective role, relative time, lifecycle state when not READY, ineligibility reason when applicable.
- Entries route into Match Detail. The section routes to `history/`.
- An entry MUST NOT become a miniature Match Detail (foundation §16; see `history/SSOT.md` §4).
- Fewer than five retained matches → show what exists. Zero → an explicit empty state, distinguished from `NO_STEAM_LINKED`.

---

## 8. Home-level states

| State | Meaning |
|---|---|
| Not linked (`NO_STEAM_LINKED`) | Home is navigable. Match-dependent content is in a dedicated unlinked state, not a zeroed one. |
| Bootstrap unsettled | Home is usable. Facts appear progressively; history-dependent content stays pending per mode. |
| Data access blocked | Home surfaces the recovery route. Existing known data remains visible and truthful. |
| Checking | Discovery running. Cached content stays usable and correct. |
| Sync error / offline | Cached content remains fully usable. Home MUST NOT claim the account is empty or up to date. |
| Up to date, nothing new today | Today's Focus mode. A legitimate, complete state. |
| Today has matches, still processing | Today's Matches mode with lifecycle states per match. Every entry is navigable. |
| Today has matches, deep analysis pending | Normal. Matches are acknowledged and openable; readiness may be shown subtly. **Not a degraded state.** |
| Today has matches, deep analysis will never arrive | Normal. The match is an ordinary completed match on Home. |
| Today has matches, one is `ACTION_REQUIRED` | The Retry affordance must be reachable from Home or from the match it belongs to. |
| Free | Complete within entitled history. Never framed as degraded truth. |
| Pro | Greater history depth. Never framed as more accurate. |
| Entitlement just changed | Derived content may legitimately have moved. It MUST NOT read as performance change. |

---

## 9. Hard invariants

- Home's V1 content set is exactly the four elements in §2.
- Today's Focus and Today's Matches never appear together.
- Home never shows a composite role trend, role score, player score, grade, rating or percentage.
- Home never merges Standard and Turbo inside a progression calculation.
- Home never reproduces Match Detail's per-metric analysis, matchup context, or insight card content.
- Home never presents win/loss as personal performance.
- Home never explains why a match was won or lost.
- Home never fills the Today's Focus or Challenge slot with fabricated content.
- Home never renders N/A as zero, or an unready state as a neutral value.
- Home is usable from cache on every open, before discovery completes.
- Home never blocks on provider availability.
- Home acknowledges a completed match as soon as summary-class evidence exists, and never waits for deep analysis to do so.
- Home never withholds navigation into Match Detail because deep analysis is pending.
- Home never names a data provider or uses pipeline vocabulary.
- Home never presents a pending or permanently unavailable deep analysis as an error, a warning or a failed match.

---

## 10. Product gaps recorded here

| Gap | Status |
|---|---|
| Today's Focus content model | **Open — owner decision required.** The slot is locked; its eligible signals, priority and copy model are undefined. |
| Challenge feature | **Open — not contracted.** Slot locked; the feature itself has no SSOT anywhere in this repository. |
| Default mode bucket on Home | **Open — design may choose**, provided the selected bucket is unambiguous. A reasonable default is the bucket with more eligible matches recently; this is not locked. |

Neither gap blocks designing Home: both are slots with defined boundaries and defined failure states.

---

## 11. Acceptance rules

- [ ] Home renders usable cached state before discovery completes.
- [ ] A match finished minutes ago appears in Today's Matches before its deep analysis exists, and is openable.
- [ ] Home reflects the finalized state once analysis persists, without the user re-triggering anything.
- [ ] An acknowledged match never disappears or regresses as readiness advances.
- [ ] No Home string names a provider or uses pipeline vocabulary.
- [ ] Element 1 shows Today's Matches when today has matches, otherwise Today's Focus — never both.
- [ ] A single today's match may route straight to Match Detail; multiple route to History.
- [ ] Role summaries exist for all four roles, scoped to one unambiguous bucket, with no composite verdict.
- [ ] A role with insufficient trend history shows `Insufficient History`, never a flat or declining state.
- [ ] Last 5 Matches includes ineligible and non-READY matches, each carrying its mode.
- [ ] No Home element reproduces per-metric performance states, matchup context, or insight card content.
- [ ] `NO_STEAM_LINKED`, bootstrap-unsettled, sync-error and offline states are all representable without implying an empty account.
- [ ] The Challenge slot degrades cleanly when the feature is absent.
- [ ] Today's Focus renders an honest neutral state rather than fabricated content when nothing qualifies.

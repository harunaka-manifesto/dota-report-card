# Profile — SSOT

**Status:** ACTIVE — feature contract, with **provisional thresholds** (§12) and **open owner decisions** (§13).
**Scope:** The long-term player-identity surface: identity line, role map, hero identity, durable claims, current-form strip, Personal Bests, change ledger, share card.
**Inherits:** [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md).
**Provenance:** consolidated from the Living Dota Player Profile research and contract, now archived at [`../_archive/superseded_ssots/living-player-profile-v1.md`](../_archive/superseded_ssots/living-player-profile-v1.md).

---

## 1. Purpose

Profile answers:

> What kind of Dota player am I over the long term?

In one line for the team:

> **Progression measures. Post-match notices. The Profile concludes.**

The Profile is **a short list of claims about the player that keep being true — each with receipts — plus a clearly separate strip showing what is moving right now.**

It is a page of *sentences about you*, each tappable to the matches that made it true. It is not a page of numbers about you.

---

## 2. What the Profile is

1. **Role-first.** Dota players describe themselves by position. Effective role mix is the strongest, cheapest, most defensible identity signal available. The Profile opens there.
2. **Hero-shaped.** Heroes are the second thing players recognise instantly — but "most played" is only one of several hero relationships players distinguish. The Profile separates them rather than collapsing them.
3. **Slow by design.** Identity claims move only when evidence moves decisively, with enter/exit hysteresis. One odd match never changes who you are.
4. **Self-relative before population-relative.** V1 claims compare the player with their own history and describe the structure of their own play. Claims needing "compared with other Carry players" wait for a validated reference population (P1).
5. **Evidence-trailed.** Every claim carries its definition, window, sample and contributing matches. **If a claim cannot produce a "Why am I seeing this?" panel, it does not ship.**
6. **Refusal is a valid state.** A new player sees facts and an honest "still getting to know your Dota", never a manufactured personality.

## 3. What the Profile is not

- **Not a stats dashboard.** Repeating KDA/GPM/win rate is table stakes; other sites already do the inventory better.
- **Not a skill grade.** No overall score, no 0–100 skill radar, no good/bad grades, no rank-derived labels. Rank stays fenced.
- **Not a personality test.** No "resilient", "tilted", "brave", "selfish". No live archetype label in V1.
- **Not a second Progress screen.** The Profile never re-displays a metric delta that Progress already shows. It summarises state and links there.
- **Not a single-match analysis screen.** No per-match analytics are copied here.
- **Not an annual report that updates.** The Profile says what currently appears to be true, and keeps a frozen history of how that changed.

---

## 4. Structure

```text
PROFILE (bucket selector: Standard | Turbo)
├── 1. HEADER
├── 2. IDENTITY  (identity line + role map)
├── 3. YOUR HEROES
├── 4. WHAT KEEPS SHOWING UP   (≤ 3 confirmed claims)
├── 5. RIGHT NOW               (≤ 2 items)
├── 6. PERSONAL BESTS
├── 7. CHANGES
└── Action: SHARE CARD
```

Seven sections. This is a **content hierarchy, not a layout**. Section order above reflects priority, not a mandated vertical sequence — except that identity precedes current form (§9.1).

The bucket selector is visible only when **both** buckets have ≥ 30 eligible matches; otherwise the minor bucket is reachable but not foregrounded. Default bucket: the one with more eligible matches in the last 90 days.

### 4.1 Header

**Shown:** display name and avatar; bucket phrase ("Mostly Standard" when the selected bucket holds ≥ 70% of eligible matches in the last 90 days, otherwise "Standard and Turbo"); "{n} matches since {Mon YYYY}" for the selected bucket; "Last played {relative}".

**Below 10 matches:** "Getting to know your Dota · {n} matches".

**Private/anonymous provider profile:** a refusal state explaining how to make match data public. **No fabricated content.**

### 4.2 Identity

**Identity line** — one deterministic sentence composed from the player's Role Shape state and the Hero Shape of their top role:

| Role Shape | Hero Shape of top role | Template |
|---|---|---|
| SPECIALIST | NARROW | "{Role} specialist with a narrow pool." |
| SPECIALIST | ROTATION | "{Role} specialist with a steady rotation." |
| SPECIALIST | WIDE | "{Role} specialist with a wide pool." |
| SPECIALIST | unconfirmed | "{Role} specialist." |
| ANCHORED | any | "{Role} first, {Role2} second." |
| DUAL | any | "{Role} and {Role2}, almost evenly." |
| FLEXIBLE | any | "Covers {k} roles regularly." |
| NO_CLEAR_SHAPE | any | "No single role, no clear favourite." |

Role names are Carry, Mid, Offlane, Support. "Pos 1" wording is not used in the line.

**Insufficient confidence:** Role Shape unconfirmed and n ≥ 10 → "Mostly {top role} so far." (if top role ≥ 50%) or "A bit of everything so far." Below 10 matches → **no line**. Never a default archetype.

**Role map** — four rows (Carry, Mid, Offlane, Support) for the selected bucket: share of the identity window, count, and role tier chip. A footnote surfaces matches without a resolved role as a correction affordance ("{k} matches without a role — set roles").

Role tiers: **Anchor** (top role, ≥ 50%) · **Regular** (≥ 20%) · **Occasional** (5–20%) · **Rare** (< 5%), with ±3 pp hysteresis.

**Below 30 matches:** counts only — no tiers, no percentages.

**If more than 20% of the identity window lacks a resolved role, Role Shape is withheld.**

### 4.3 Your heroes

For the top role: up to three hero portraits, each with **exactly one tag** and one fact line. A role switcher shows the same for other roles with ≥ 10 role matches.

Tag priority on the Profile: **Go-to → Rising → Longtime → Favourite**.

| Tag | Player meaning | Basis |
|---|---|---|
| **Go-to** | The hero you play most in this role | Highest share of the role window, with replacement hysteresis |
| **Longtime** | Has been in your rotation for ages | Sustained presence across many blocks of role history, **and** played recently |
| **Rising** | A hero taking over lately | Substantial recent share against near-absence before; expires if it does not become Go-to or Longtime |
| **Favourite** | The hero you love | **Player-pinned only. Never inferred. Never used in analytics.** |

Candidate floor: a hero needs a minimum number of matches **and** a minimum share of the role window to be taggable.

**Below 10 role matches:** "Most played so far" with counts, no tags.

Everything is computed **per bucket × effective role**. A Carry Go-to and a Support Go-to are different facts. No hero tag is ever computed across roles or across buckets.

### 4.4 What keeps showing up

Up to **three CONFIRMED claims**, each with one sentence and a "Why?" evidence sheet (window, counts, dates, state-since).

P0 claim catalog:

| Claim | Player meaning | Scope |
|---|---|---|
| **Role Shape** | How your games spread across the four roles | Account × bucket |
| **Hero Shape** | Whether you go deep on a few heroes in a role or spread wide | Role × bucket |
| **Exploration** | How often you pick a hero you haven't played recently | Role × bucket |
| **Role-Pool Contrast** | You treat your roles differently: deep in one, broad in another | Two roles × bucket |
| **Mode-Split Identity** | You are a different player in Turbo than in Standard | Across buckets, compared without pooling |
| **Role Migration** | Your role mix has shifted | Account × bucket, two windows |
| **Pool Turnover** | How much your hero pool in a role has changed | Role × bucket, two windows |
| **Go-to ≠ Longtime contrast** | Most played isn't longest-running | Role × bucket |

Claim priority for the reserved first-screen slot and for ordering:

1. Mode Split → 2. Role-Pool Contrast → 3. Role Migration (while active) → 4. Go-to-vs-Longtime → 5. Pool Turnover → 6. Exploration contrast across two roles → 7. Exploration (single role).

Ties break to the more recently confirmed. **No rotation for novelty's sake** — a claim holds its slot until a higher-priority claim is confirmed or it retires. Stability builds trust; Right now and Changes supply motion.

**No claim confirmed → the section is hidden.** A maturity hint is allowed only at n ≥ 30 ("More reads unlock as you play — next: your Carry hero pool at 30 Carry matches").

### 4.5 Right now

Up to **two** items, each carrying its window label:

- **Current-Form Run** (up-run preferred first): a registered role metric consistently above or below the player's own usual across the last 10 role matches;
- **Rising hero arrival**, mirrored from the hero section during its first period;
- **PB Momentum**: several PBs within the last 20 eligible role matches;
- **"Lately: mostly {role}"** when the last 10 eligible matches are heavily a role that is not the Anchor;
- **Down-run** — never first, never shared.

Items link to Progress for the numbers. Profile never re-derives them.

**Nothing qualifies:** "Nothing unusual lately — you're playing to your usual." A legitimate, reassuring state.
**Progression not ready for any metric:** the section is hidden.
**Stale:** an item whose latest observation is older than a staleness bound is hidden.

Does **not** belong in Right now: win/loss streaks, recent KDA, rank movement, "hot/cold" labels without a metric, any metric outside the role metric registry.

### 4.6 Personal Bests

For the selected bucket: the three most recent PB celebrations (date, role, metric, value) and an "All PBs" list grouped by role showing current best-known records.

PB semantics are the foundation's (§12). Profile displays; it does not redefine.

**Insufficient:** "Personal bests start after 5 measured matches in a role."

### 4.7 Changes

A reverse-chronological ledger of **confirmed identity changes**, with the cause recorded (ordinary play; a role correction that changed displayed state; an import that changed displayed state). Superseded events are marked as updated after a correction, not deleted.

Changes are the Profile's honesty mechanism: it tells the player when their identity genuinely moved — **and refuses to move when it hasn't**.

**Empty:** "Your profile will note changes here as they happen."

### 4.8 Share card

Generated server-side from a **whitelisted public projection** of the header, identity and heroes. The app previews the exact image.

- Unavailable when no identity line is confirmed (hero-card fallback only).
- Only up-runs and PB momentum are share-eligible from Right now, opt-in. **Down-runs are never shared.**
- A share is a timestamped snapshot; later changes do not retroactively alter it.

---

## 5. Claim lifecycle

```text
CANDIDATE  → enter condition met once
CONFIRMED  → persistence satisfied; visible
FADING     → exit condition met once; still visible, marked "less clear lately"
RETIRED    → exit persistence satisfied; removed, change event written
```

A candidate that fails its enter condition before persistence is discarded **silently** — no change event, no user-visible trace.

**Persistence rule:** a claim changes state only when the new state's *enter* condition holds at two evaluations separated by a minimum number of newly eligible matches in the claim's scope. Leaving a state uses a looser *exit* condition under the same persistence rule (hysteresis).

Claims are evaluated after each READY eligible match in their scope.

**Every visible claim carries an evidence payload:** claim ID and version, bucket, scope, window definition, n, the aggregate values, the thresholds crossed, state-since (match and date), and representative match references.

---

## 6. Eligibility, windows and scope

- **Eligible match:** a READY match with progression classification `STANDARD` or `TURBO` and a resolved effective role — the *same* eligibility as progression, so every Profile number reconciles with Progress. `NONE(reason)` matches are counted in the header as tracked but **never feed claims**.
- **Bucket:** every aggregate and claim is per bucket. **No claim mixes buckets** except Mode-Split, which compares two bucket-level results without pooling their matches.
- **Identity window:** the most recent 200 eligible matches in the bucket, excluding matches older than 24 months (provisional — §12).
- **Role window:** the most recent 100 eligible matches in the bucket with that effective role, same age cap (provisional).
- **Chronology:** the canonical key.
- **Effective sample:** matches cluster in sessions and hero/role choices autocorrelate, so confidence intervals use a design-effect discount rather than raw n (provisional).

Matches without a resolved effective role are excluded from every role claim and counted visibly in the role-map footnote. This converts classifier gaps into a **correction affordance** rather than silent bias.

---

## 7. Role and hero rules

- Effective role is **consumed, never recomputed**. A user correction triggers a deterministic rebuild of every Profile aggregate in the affected bucket.
- Positions 4 and 5 are one Support role. The Profile does not split them in V1.
- Standard and Turbo are separate; one bucket is shown at a time.
- **No combined all-role score, anywhere.** The identity line is a sentence, not a score.
- Specialist and Flexible are presented as **equal identities**. Neither is praise.
- The Profile never compares a metric across roles.
- Role-scoped current form and PBs come from Progression; the Profile never re-derives them.

The hero section never says:

- "your best hero" (a P1 "Best record" tag, if it ships, is labelled *best record*, never *best hero*);
- "your comfort pick" as a claim about feelings;
- anything computed across roles or across buckets.

---

## 8. Maturity

There is **no profile-wide level** ("Learning → Emerging → Established"). Maturity differs by bucket and role — 2,000 Standard matches and 6 Turbo; 300 Carry and 12 Mid — so a global level misleads.

Instead **every claim carries its own readiness**, and the page uses one gentle header phrase only below 30 eligible matches. Unavailable claims are **omitted, not teased**, except for one line inviting play ("Your hero pool read unlocks after 30 Carry matches").

Approximate ladder, for one bucket, for a player concentrated in one role:

| Eligible matches | Honestly available | Withheld |
|---|---|---|
| ~5 | Header facts; heroes played with counts; roles seen with counts; baseline-building status | Every claim, every tag, form, PBs |
| ~20 | Role lean in counts; most-played heroes; first PBs possible | Role Shape, Hero Shape, tags, form, exploration |
| ~50 | Role Shape if strong; Hero Shape for a role with enough matches; Go-to; current-form runs in the main role; PB list | Longtime, Rising, Exploration, Migration, Pool Turnover, Mode Split |
| ~200 | Every P0 claim | P1 claims until their prerequisites ship |
| ~2,000 | The same Profile, on the most recent 200; richer Longtime heroes; History screen becomes valuable | **Nothing extra is inferred from volume. Volume is not a trait.** |

Imported history counts toward maturity immediately once admitted, but **never creates celebration or change events** for the period before import.

---

## 9. Identity versus current form

### 9.1 Content rules

| Stable identity | Current form |
|---|---|
| A sentence; no window label needed on the face (window lives in "Why?") | **Every item carries its window** ("last 10 Carry matches", "since 3 Sep") |
| Changes rarely; a change writes a Change event | Changes often; writes no Change events |
| Presented as solid | Must read as temporary |
| Share-eligible | Only up-runs and PB momentum, opt-in |
| Never shows a decline on the first screen | Down-runs appear in the list, never first, never shared |

A **window label is mandatory** on every Right-now item. This is a content rule, not a visual specification.

### 9.2 Rebuild semantics

- A role correction rebuilds every affected Profile aggregate in that bucket. Where displayed state changed, a Change event records the correction as the cause.
- An import that changes displayed state is recorded likewise, and never generates retroactive celebrations.
- Rebuilds are deterministic and idempotent and make no provider calls.

---

## 10. Rejected content (do not revive)

Measured and rejected, or structurally unsupportable:

- A single living archetype or personality label on the Profile.
- "You fall off outside your comfort heroes", "you recover well after bad lanes", "you perform strongly even in losses" — all measured at **zero** between-player signal.
- Aggressive/conservative, clutch/closer, early/late-game player, streaky/steady, team-oriented, initiator.
- Tilt and post-loss behaviour.
- Skill radars, overall scores, strength bands, percentiles, "top X%".
- "Strongest hero" from raw cross-hero metrics (raw comparisons measure hero kits, not the player); computed pocket picks.
- Solo vs party, time of day, Radiant/Dire.
- Provider impact scores, awards, behaviour scores, and anything rank-derived.
- An LLM that reads a year of matches and writes who the player is.

**Not on the first screen, deliberately:** win rate, KDA, GPM, rank, match graphs, archetype, weaknesses, recommendations, records, the full PB list.

---

## 11. Hard invariants

- The Profile concludes; it does not measure. It never re-derives a Progress number.
- Every visible claim has receipts. No claim ships without a "Why?" panel.
- Claims move slowly, with hysteresis and persistence. One match never changes identity.
- Refusal is a valid state. Below the gates, the Profile shows facts and an honest phrase — never a manufactured personality.
- No overall score, grade, rating, percentile, radar, or rank-derived label.
- Specialist and Flexible are equal identities.
- Every aggregate is per bucket; only Mode-Split compares buckets, and it never pools their matches.
- Hero tags are per bucket × role, never across either.
- Favourite is player-pinned, never inferred, never analytic.
- Matches without a resolved role are excluded from role claims and surfaced as a correction affordance.
- Role Shape is withheld when more than 20% of the identity window lacks a role.
- Every Right-now item carries its window label.
- Down-runs are never first and never shared.
- Volume alone infers nothing. Volume is not a trait.
- Imported history never creates retroactive celebrations or change events.
- No single-match analytics are copied onto the Profile.

---

## 12. Provisional parameters

Every numeric threshold in this document — role-shape and hero-shape cut points, exploration/migration/turnover thresholds, tier boundaries, window sizes, hysteresis margins, the persistence gap, the design-effect discount, and the form-run magnitude gate — is **PROVISIONAL** and MUST be calibrated on the development corpus before release against two targets:

1. **Non-degeneracy:** no state holds more than 80% or fewer than 3% of established players, unless the behaviour genuinely is that concentrated (record which).
2. **Churn:** quarterly churn for established players with stable play is under 10%, measured by replaying chronology.

Calibration changes parameters, not product meaning. It does **not** reopen the decisions in this document.

---

## 13. Open owner decisions

Recorded honestly. **None blocks design**, because each has a defensible default and a defined failure state.

| # | Decision | Recommended default |
|---|---|---|
| 1 | Identity window 200 / role window 100 / 24-month cap | Adopt as provisional; calibrate per §12 |
| 2 | Profile eligibility equals progression eligibility, with ineligible matches counted only in the header | Adopt — it is what makes Profile and Progress reconcile |
| 3 | Random-assigned picks excluded from hero shape and tags | Exclude |
| 4 | Down-runs visible on the self Profile | Yes — never first, never shared |
| 5 | Profile change events in-app only in V1; whether READY notification copy may mention a profile change | In-app only |
| 6 | Descriptive Position 4 vs 5 sub-label | Not in V1 |
| 7 | A dated annual-archetype badge on the Profile | P1, not V1 |
| 8 | Other-player visibility defaults | Private until a social feature ships |
| 9 | Rank label opt-in on share cards | Off by default; explicit per-share opt-in |
| 10 | A user-declared "preferred role" | P1, not V1 |

Additional validation still owed (research, not product decisions): whether players actually recognise themselves — a moderated test of the identity line and signature findings, measuring recognition ("that's me" / "that's wrong" / "so what") before release.

---

## 14. Acceptance rules

- [ ] The identity line is composed only from confirmed Role Shape and Hero Shape states, or an honest "so far" fallback, or nothing.
- [ ] Below 10 matches there is no identity line; below 30 the role map shows counts only.
- [ ] Role Shape is withheld when over 20% of the identity window lacks a resolved role.
- [ ] Every visible claim can produce its evidence panel with window, n, thresholds and contributing matches.
- [ ] A claim never appears before its persistence gap is satisfied, and never disappears without its exit condition.
- [ ] A discarded candidate leaves no user-visible trace.
- [ ] At most three claims and at most two Right-now items are shown.
- [ ] Every Right-now item carries a window label; down-runs are never first.
- [ ] Hero tags are scoped to one bucket and one role; Favourite is only ever player-set.
- [ ] Mode-Split compares two buckets without pooling their matches; no other claim crosses buckets.
- [ ] No composite score, grade, rating, radar or percentile appears anywhere.
- [ ] Specialist and Flexible are presented as equal identities.
- [ ] A role correction rebuilds Profile aggregates in that bucket and records a Change event where displayed state changed.
- [ ] An import changes displayed state without creating celebrations or backdated change events.
- [ ] The share card is built from the whitelisted projection only, and is unavailable without a confirmed identity line.
- [ ] A private provider profile produces a refusal state, never fabricated content.

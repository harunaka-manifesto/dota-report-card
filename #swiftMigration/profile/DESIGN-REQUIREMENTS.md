# Profile — Design Requirements

Derived from [`SSOT.md`](SSOT.md) and [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md).

---

## 1. Page role

The Profile is the app's answer to "what kind of Dota player am I?" — a short list of claims that keep being true, each with receipts, plus a clearly separate strip of what's moving right now.

A player should leave thinking **"yeah, that's me"**, and ideally **"huh, I didn't know that"**. They should not leave with a score.

The one-line frame for the whole page: **Progression measures. Post-match notices. The Profile concludes.**

---

## 2. Primary JTBD / user needs

**Primary**

- When I want to see myself as a player, I want the app to tell me what I actually am, so I can recognise it or argue with it.
- When I'm curious about my own habits, I want to learn something I hadn't noticed, so the app earns its place over a stats site.
- When I want to show someone who I am in Dota, I want something compact and true, so sharing it isn't embarrassing.

**Secondary**

- When my play has genuinely changed, I want the app to tell me, so I can see my own evolution.
- When the app claims something about me, I want to check its working, so I trust the rest of it.

---

## 3. Questions this page must answer

- What kind of Dota player am I, in one sentence?
- Which roles do I actually play — not which I think I play?
- Which heroes define me, and in what different senses?
- What are my long-term tendencies?
- How am I changing?
- What's moving right now — and is that the same as who I am?
- How sure is the app, and on what evidence?

---

## 4. Entry points & exits

**Entry**
- Main navigation
- A change notification / the change feed
- A shared card opened by the player themselves

**Exit**
- → a claim's evidence ("Why am I seeing this?") and the matches behind it
- → Progress (any Right-now item, for the numbers)
- → Match Detail (a PB's source match; a claim's example match)
- → History (a claim's contributing matches)
- → Share card
- → Role correction, via the "matches without a role" affordance

---

## 5. Proposed information architecture

```text
P0 — header: whose Dota, and how much of it we know
P0 — identity line
P0 — role map
P0 — your heroes (up to 3, one meaning-tag each)
P0 — the single highest-priority confirmed claim
P1 — the remaining confirmed claims (≤ 3 total)
P1 — right now (≤ 2 items, visibly temporary)
P2 — personal bests
P2 — changes ledger
—    share card (an action, not a section)
```

Two orderings are **semantically required**:

1. **Identity before current form.** If a recent run is the most prominent thing on the page, the page has become a form dashboard.
2. **Scope before claim.** The header's "how much we know" framing must be available before the claims it qualifies.

The first screen should fit on a phone without scrolling and read in about ten seconds. It carries five things and nothing else: header, identity line, role map, heroes, one claim — plus, visually separated, one Right-now item. Everything else is below.

Deliberately **not** on the first screen: win rate, KDA, GPM, rank, match graphs, archetype, weaknesses, recommendations, records, the full PB list.

---

## 6. Content & data available

| Content / datum | Meaning | Availability | Notes |
|---|---|---|---|
| Display name, avatar | Identity | Always | From the provider profile |
| Bucket phrase | "Mostly Standard" / "Standard and Turbo" | Always | Based on the last 90 days |
| Matches tracked + since | Scope and trust | Always | Per selected bucket |
| Last played | Recency | Always | A fact, not a judgment |
| Identity line | One deterministic sentence | Needs confirmed role shape (~30+ matches) | 9 templates. Falls back to "Mostly Carry so far", then to nothing. |
| Role map | 4 roles: share, count, tier | Counts always; shares/tiers at 30+ | Tiers: Anchor / Regular / Occasional / Rare |
| Unassigned matches | Matches with no resolved role | When present | **A correction affordance, not an error** |
| Hero + tag | Up to 3 per role, one tag each | Tags at 10+ role matches | Go-to / Rising / Longtime / Favourite |
| Favourite | Player-pinned hero | Only if set | **Never inferred** |
| Confirmed claims | Up to 3 durable statements | Maturity-gated | Each has a "Why?" payload |
| Claim evidence | Window, n, thresholds, dates, example matches | Always for a visible claim | **No claim ships without this** |
| Claim state | Confirmed / Fading | Visible claims only | "Fading" = less clear lately |
| Current-form run | A metric consistently above/below your usual over the last 10 role matches | Needs ~15 measured observations | **Window label mandatory** |
| PB momentum | Several PBs recently | Needs the PB gate | |
| "Lately: mostly {role}" | Recent role skew away from your Anchor | Always computable | |
| Recent PBs | 3 most recent celebrations | After the gate | |
| All PBs | Current records grouped by role | After the gate | |
| Changes ledger | Confirmed identity changes, with cause | Append-only | Corrections and imports are recorded causes |
| Share projection | Whitelisted public subset | Needs a confirmed identity line | Hero-card fallback otherwise |

**Not available, by design:** overall score, skill radar, percentile, rank, win rate on the first screen, KDA/GPM, archetype/personality label, "your best hero", tilt or post-loss behaviour, solo-vs-party, time of day, anything comparing the player to other players (that's P1, pending a validated reference population), any per-match analytics.

**The "I didn't know that" layer** comes from contrasts, never bare numbers: your Support pool is three times wider than your Carry pool · you're a Support in Standard and a Mid in Turbo · your go-to isn't your longest-running hero · Support went from 8% to 31% of your games · only one of your top five Carry heroes from 100 games ago is still there · you rarely try new Carry heroes but one Support game in three is someone new.

---

## 7. Core flows

```text
Open Profile
→ read the identity line
→ check it against the role map
→ recognise (or dispute) it
```

```text
See a claim
→ "Why am I seeing this?"
→ window, sample, thresholds, example matches
→ believe it (or correct a role)
```

```text
Open Profile
→ notice something is moving in Right now
→ Progress for the actual numbers
```

```text
Open Profile → Share card → preview → share
```

---

## 8. Required states

| State | Product meaning |
|---|---|
| **Under 10 matches** | "Getting to know your Dota." Facts and counts only. No line, no tags, no claims. **A designed state, not a placeholder.** |
| **10–29 matches** | Role lean in counts ("Mostly Carry so far"), most-played heroes. Still no tiers, tags or claims. |
| **30–199 matches** | Identity line appears; role tiers; Go-to; first current-form runs; PBs. Most claims still locked. |
| **200+ matches** | The complete V1 Profile. |
| **No claim confirmed** | The claims section is **hidden**, not teased — with at most one line inviting play. |
| **Claim fading** | Still visible, marked "less clear lately". Honest transition. |
| **Right now empty** | "Nothing unusual lately — you're playing to your usual." **Reassuring, not a failure.** |
| **Progression not ready** | Right now is hidden entirely. |
| **Down-run present** | Visible in the list, never first, never shared. |
| **Matches without a role** | Surfaced as a fixable footnote. |
| **Role shape withheld** | Too many unassigned roles (>20%). Explained, not blank. |
| **Private provider profile** | Refusal state with the fix. **No fabricated content.** |
| **Turbo vs Standard** | One bucket at a time; toggle only when both have ≥ 30 matches. |
| **Profile just changed** | A change event exists; the ledger has something new. |
| **Post-correction rebuild** | Aggregates recomputing; superseded change events marked as updated. |
| **Share unavailable** | No confirmed identity line → hero-card fallback only. |

---

## 9. User actions

Switch mode bucket · switch role (hero section) · open a claim's evidence · pin a Favourite hero · open a PB's source match · open Progress from a Right-now item · fix unassigned roles · open the changes ledger · generate and share a card · opt in to sharing a run or PB.

---

## 10. Experience requirements / guardrails

- **MUST NOT** show an overall score, grade, rating, radar, percentile or "top X%".
- **MUST NOT** present a personality or archetype label.
- **MUST NOT** copy single-match analytics onto the Profile, or re-display a Progress number instead of linking to it.
- **MUST** keep stable identity and current form visibly distinct — **every Right-now item carries its window label**; identity does not need one on its face.
- **MUST NOT** put a decline on the first screen. Down-runs are never first and never shared.
- **MUST** make every visible claim tappable to its evidence. A claim without receipts does not ship.
- **MUST NOT** present Specialist as better than Flexible, or vice versa. They are equal identities.
- **MUST NOT** fill empty claim slots with win rate, KDA, or any filler fact. **The moment the empty slots get filled with stats, this becomes the fourth stats site.**
- **MUST NOT** rotate claims for novelty. A claim holds its slot; motion comes from Right now and Changes.
- **MUST NOT** mix Standard and Turbo in any aggregate. Only the Mode-Split claim compares them, and it compares results, not pooled matches.
- **MUST** treat "matches without a role" as an invitation to correct, not as an error or a data problem.
- **MUST NOT** infer a Favourite hero. It is pinned or absent.
- **MUST NOT** let volume imply anything. 3,000 matches is not a trait.
- Hero tags are per role and per mode — never claim a hero "defines you" across contexts.

---

## 11. Design freedom

Open: everything visual. Whether the identity line is a headline, a card, or set in the header; how the role map is drawn (bars, rows, dots, a shape, or nothing graphical); hero presentation — portraits, sizes, how the single tag reads; how "solid identity vs temporary form" is expressed (the contract requires only that form carries its window and reads as temporary); how claims are presented and how "Why?" opens; whether Changes is a feed, a list, or a timeline; share-card composition and aspect ratio; how locked/maturity states look; density, type, color, motion; where the bucket toggle lives; whether the first screen is one scroll or a designed viewport.

---

## 12. UX success metrics

| Metric | Why it matters | Observable |
|---|---|---|
| **Recognition** | The page's entire purpose | Research: shown their Profile, do players say "that's me", "that's wrong", or "so what"? Target the first, and treat "so what" as the real failure. |
| **Surprise value** | The differentiator over stats sites | Research: can players name one thing they learned about themselves? |
| Evidence engagement | Whether claims are trusted or ignored | Analytics: "Why?" opens per Profile session |
| Share rate | The clearest signal the page is flattering-by-recognition | Analytics: share cards generated and shared |
| Return after a change event | Whether "your profile changed" is a real reason to come back | Analytics: change notification → Profile open |

Instrumented: evidence opens, share generation, Right-now → Progress navigation, change-event returns. Research-only: recognition, surprise, and whether Specialist/Flexible reads as praise or criticism.

---

## 13. UX risks / questions to test

- Does the identity line land as "that's me", or as a generic horoscope?
- Does "Covers three roles regularly" feel like an identity or like a shrug?
- Does Specialist read as praise and Flexible as indecision (or the reverse)?
- Do players believe a claim without opening its evidence — and does opening it help or confuse?
- Is a mostly-locked early Profile motivating ("I'll unlock this") or disappointing?
- Do players read a current-form down-run as an identity statement despite the window label?
- Does "Fading" read as honest, or as the app hedging?
- Does the app refusing to change when nothing changed read as broken?
- Is a Profile with no win rate anywhere felt as a gap?
- Would a player actually share this card — and what stops them?

---

## 14. Out of scope

- **Profile is not a single-match analysis screen.** No per-match analytics, matchup context, insight cards or performance states.
- Profile is not a second Progress screen — it summarises state and links out for numbers.
- Profile is not a stats dashboard — no KDA, GPM, win rate on the first screen, no inventory of numbers.
- Profile is not account settings. Steam, subscription and deletion are `settings_account/`.
- No rank, MMR, bracket or percentile.
- No comparison to other players in V1 (needs a validated reference population).
- No other-player profile view in V1 — but the data model keeps it possible.
- No archetype or personality label.
- Records, History/Eras and per-role style claims are P1, not V1.

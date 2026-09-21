# Home — Design Requirements

Derived from [`SSOT.md`](SSOT.md) and [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md).

---

## 1. Page role

Home is the daily check-in. A player opens it after a session, or between sessions, to find out whether anything happened and whether anything is moving.

They should leave knowing **whether there's something new worth opening**, and with a rough sense of **which of their roles is going anywhere** — then go somewhere else. Home is a hub, not a destination.

---

## 2. Primary JTBD / user needs

**Primary**

- After playing Dota, I want to quickly see how today's games went, so I know whether anything meaningful changed.
- When I open the app between sessions, I want to know whether anything is moving in my play, so I don't have to go looking.
- When I do see something interesting, I want to get to the detail in one step.

**Secondary**

- When I haven't played today, I want the app to still feel like it has something for me, so opening it isn't wasted.
- When I'm partway through something (a challenge, a baseline filling up), I want to see where I stand.

---

## 3. Questions this page must answer

- Did I play today, and how did those games go at a glance?
- Is there anything new I haven't looked at?
- Is anything about my play going up or down right now?
- Which role should I be paying attention to?
- What's the app currently doing (still fetching? stuck? up to date?)
- Where do I go next?

---

## 4. Entry points & exits

**Entry**
- App launch and resume (default surface)
- Push notification for a READY match — may land here or directly on the match
- Back from any other surface

**Exit**
- → Match Detail (one match today; any Last-5 entry)
- → History (multiple matches today; "Last 5" section)
- → Progress, per role (any role summary)
- → Challenge (when that feature exists)
- → Connect Steam (unlinked state)
- → Data-access recovery (blocked state)

---

## 5. Proposed information architecture

Owner direction fixes the content set and the routing, not the arrangement.

```text
P0 — today: either today's matches, or today's focus (one slot, two modes)
P0 — challenge
P0 — role progression summaries (Carry, Mid, Offlane, Support)
P1 — last 5 matches
P1 — app state when it isn't nominal (syncing, offline, blocked, unlinked)
```

Grouping rules:

- Today's slot and Last 5 are both *match* content but at different urgency; they should not read as one list.
- The four role summaries are one group — they are parallel, comparable, and belong to one selected mode.
- The mode context (Standard / Turbo) must be unambiguous wherever role summaries sit. Where that indicator lives is open.

Ordering is **not** semantically fixed beyond this: the today slot is the reason the page exists today, so it should be reachable without work.

---

## 6. Content & data available

| Content / datum | Meaning | Availability | Notes |
|---|---|---|---|
| Today's matches | Matches from the current local day | Conditional | Spans Standard + Turbo; each carries its mode |
| Match identity | Hero, result, mode, time, duration | Always for a retained match | Result is a match fact, not a verdict |
| Effective role | Carry / Mid / Offlane / Support | Once classified | Editable, but not from Home |
| Lifecycle state | Six states (see foundation) | Always | Only needs surfacing when *not* READY |
| Ineligibility + reason | "Doesn't count toward progression" | When applicable | Reason is mandatory if shown |
| Insight card count | 0–3 | After READY | Majority of matches have 0 — design for that |
| Per-role trend states | Per metric: Improving / Stable / Declining / Insufficient History | Needs 10 eligible trend points per metric | **No composite role verdict exists.** You get metric-level states or nothing. |
| Baseline-building status | Per metric × role × mode | Always | Countable ("needs 5 prior") |
| Role recency | Last time this role was played | Always | Must not be translated into a trend |
| Last 5 matches | Most recent retained matches | Always (may be fewer) | Includes ineligible and processing matches |
| Sync state | idle / checking / up-to-date / sync-error | Always | Account-level |
| Entitlement | Free / Pro | Always | Affects history depth only |
| Challenge state | — | **Not contracted** | Design the slot to degrade to absent/unavailable |
| Today's Focus content | — | **Not contracted** | Slot is locked; eligible signals are an open decision |

**Explicitly not available on Home:** per-metric values, performance states (Above/In line/Below), matchup context, insight card content, adjusted expectations. Those are Match Detail.

---

## 7. Core flows

```text
Open Home after a session
→ see today's matches
→ open the one that looks interesting
→ Match Detail
```

```text
Open Home on a day with no games
→ today's focus
→ (optionally) challenge or a role summary
```

```text
Open Home
→ notice a role summary is moving
→ Progress for that role
```

---

## 8. Required states

| State | Product meaning |
|---|---|
| **Nominal, matches today** | Today's Matches mode. The common post-session case. |
| **Nominal, no matches today** | Today's Focus mode. A complete, legitimate state — not an empty one. |
| **First open of the day, checking** | Cached content is already correct and usable; a check is running. |
| **Sync error / offline** | Everything known stays accurate. Only *freshness* is in doubt. Must not read as "no matches". |
| **Not linked** | Match-dependent areas in a dedicated unlinked state, with a route to connect. Never zeros. |
| **Bootstrap unsettled** | Usable; history-dependent content pending per mode. |
| **Data access blocked** | Recovery route surfaced; existing data still shown truthfully. |
| **Match just finished, deeper read still coming** | **The normal case right after a session.** The match is acknowledged and openable; the deeper read is on its way. Any indication of that is quiet and subordinate to the match itself. **Not a warning, not a spinner, not a headline.** |
| **Deeper read lands while Home is open** | Home reflects the finished state without the player doing anything. No jarring reshuffle. |
| **Match will never get a deeper read** | An ordinary match on Home. Nothing unusual shown; the explanation belongs on Match Detail. |
| **Match processing** | One or more of today's matches not yet READY. Needs a resolvable, non-alarming treatment. |
| **Match needs action** | `ACTION_REQUIRED` — a Retry must be reachable. |
| **Match unavailable** | Data never arrived. Visible, retryable, not hidden. |
| **Role with no history** | Explicit unstarted state or omitted. Never zero, never flat. |
| **Role with insufficient trend history** | `Insufficient History`. Not a decline. |
| **No matches at all** | Empty account, distinct from unlinked. |
| **Challenge unavailable** | The slot degrades without breaking the page. |
| **Today's Focus has nothing honest to say** | Neutral state or nothing. Never padded. |
| **Free / Pro** | Depth differs; accuracy never does. |

---

## 9. User actions

Refresh · open a match · open History · open a role's progression · open the Challenge · retry a failed match · connect Steam · fix data access · switch mode bucket (if the design exposes one here).

---

## 10. Experience requirements / guardrails

- **MUST** acknowledge a just-finished match as soon as its basics exist, and **MUST** let the player open it. Home is where they come straight after a game; making them wait for the deeper read is the one thing this page cannot do.
- **MUST NOT** use backend vocabulary anywhere. The player never learns what a replay parse is, and Home is where that temptation is strongest.
- **MUST NOT** treat a pending or permanently absent deeper read as a warning, an error or a failed match.
- **MUST NOT** display a composite role trend, role score, grade, rating or percentage. Only metric-level states exist. If four Carry metrics disagree, that disagreement is the truth.
- **MUST NOT** present win/loss as personal performance, or as the headline of a match entry's "how it went".
- **MUST NOT** merge Standard and Turbo inside a role summary. Chronological lists (today, last 5) may mix modes if each entry shows its own.
- **MUST** make the selected mode bucket unambiguous wherever role summaries appear.
- **MUST NOT** turn a Last-5 row or a today's-match row into a miniature Match Detail.
- **MUST NOT** render an unstarted role, an N/A, or an insufficient-history trend as a zero or a flat line.
- **MUST NOT** pad Today's Focus or Challenge with invented content when nothing qualifies.
- **MUST** keep Home fully readable from cache when offline or sync has failed, without claiming to be up to date.
- **MUST NOT** let one urgent state (a failed match) suppress the rest of Home.
- Role recency is a fact, not a judgment — "haven't played Mid in 3 weeks" must not read as decline.

---

## 11. Design freedom

Open: whether elements are cards, sections, rows or something else; vertical order beyond the today-slot's prominence; whether the four role summaries are a row, a grid, a list, or a single switchable view; whether trend is expressed as text, glyph, sparkline, or something else (or not charted at all); how the mode bucket is selected and displayed; whether Last 5 is a carousel, list, or strip; how the six lifecycle states are visually differentiated; whether Today's Focus is visually distinct from Today's Matches or the same slot re-skinned; density, typography, color, motion, pull-to-refresh treatment; how Free/Pro depth is signalled, if at all.

---

## 12. UX success metrics

| Metric | Why it matters | Observable |
|---|---|---|
| Match-open rate from Home | Home's main job is routing to the thing worth seeing | Analytics: Home sessions → Match Detail opens |
| Return frequency | A hub only works if people come back between sessions | Analytics: Home opens per active week, including no-match days |
| Role-summary → Progress rate | Tests whether the role summaries are informative enough to pull | Analytics: role summary taps → Progress sessions |
| Composite-verdict misreading | The biggest correctness risk on this page | Research: after viewing a role summary, do users report a single "my Carry is good/bad" verdict? |

Instrumented: match-open rate, return frequency, role-summary taps, refresh usage. Research-only: whether the no-match-today state feels worth opening; whether metric-level states are read as a combined verdict.

---

## 13. UX risks / questions to test

- Does a day with no matches feel worth opening, or does Home feel dead?
- Do users collapse four metric-level trend states into one "my Carry is improving" verdict anyway?
- Does the Last-5 strip cannibalise History, or drive it?
- Is one today's match → straight to Match Detail delightful or disorienting (no chance to see context first)?
- Can users tell which mode they're looking at, and do they notice when it switches?
- Does a processing match on Home create anxiety, or read as normal?
- Does the Challenge slot feel like a hole when the feature isn't there?

---

## 14. Out of scope

- Home is not a full History screen — browsing, filtering and long-range scanning are `history/`.
- Home is not a Match Detail — no per-metric values, performance states, matchup context or insight cards.
- Home is not a Progress screen — no metric timelines, no baseline charts.
- Home does not host role correction.
- Home does not define what a Challenge is; the feature is uncontracted.
- Home does not define Today's Focus content; only its boundaries and its honest-empty behaviour.

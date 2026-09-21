# History — Design Requirements

Derived from [`SSOT.md`](SSOT.md) and [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md).

---

## 1. Page role

History is the complete, honest record of what this account has played. It exists to be **scanned and navigated**, not studied.

A player should leave able to **find the match they were thinking of**, and with a sense of the **shape of their recent play** — which roles, which modes, how often.

---

## 2. Primary JTBD / user needs

**Primary**

- When I remember a specific game, I want to find it quickly, so I can look at it properly.
- When I want to see what I've been playing lately, I want to scan my recent games, so I can spot patterns in roles, heroes and modes myself.

**Secondary**

- When a match didn't process or doesn't count, I want to see it anyway with an explanation, so I don't think the app lost it.
- When I want to look further back, I want to move through my history without losing my place.

---

## 3. Questions this page must answer

- What have I played recently?
- Which roles and modes have I actually been playing?
- Where is that specific match?
- Did everything get processed, or is something stuck?
- Which matches don't count, and why?
- How far back does my history go?

---

## 4. Entry points & exits

**Entry**
- Home → "Last 5 Matches"
- Home → today's matches, when there is more than one
- Profile → a claim's receipts ("show me the matches behind this")
- Progress → a point in a metric series
- Main navigation

**Exit**
- → Match Detail (any row)
- → Progress (if trend/metric content is surfaced here)
- → Retry (for an action-required or unavailable match)

---

## 5. Proposed information architecture

```text
P0 — the chronological list itself
P0 — per-row identity: hero, result, role, mode, when
P1 — per-row status when it isn't normal (processing, needs action, unavailable, doesn't count)
P1 — scoping controls (mode / role / time), if the design has them
P2 — composition of recent play (role and mode mix over the visible span)
P2 — entry into deeper per-role progression
```

Chronological order is **semantically required** — it is the page's organising principle and the only ordering the product defines. Everything else is open.

Grouping rule: identity and status belong together on a row; analysis does not belong on a row at all.

---

## 6. Content & data available

| Content / datum | Meaning | Availability | Notes |
|---|---|---|---|
| Hero | Hero played | Always for a retained match | |
| Result | Win / loss | Always | A match fact. Must not read as performance. |
| Mode | Standard / Turbo | Always | Mandatory per row — the list mixes modes |
| Effective role | Carry / Mid / Offlane / Support | Once classified | May change after a correction |
| Date/time, duration | When and how long | Always | Canonical chronology |
| Lifecycle state | Six states | Always | Only surfaces when not READY |
| Ineligibility + reason | "Doesn't count toward progression" | When applicable | Reason mandatory if shown |
| PB ownership marker | This match currently owns a PB | After the 5-prior gate | At most a minimal marker here |
| Insight availability | Whether cards exist (0–3) | After READY | Count only, never content |
| Role/mode composition | Counts and shares across the visible span | Always | Descriptive only — never a verdict |
| Per-metric trend state | Improving / Stable / Declining / Insufficient History | Needs 10 eligible points | Strictly one bucket + one role + one metric |
| Entitlement boundary | How far back this account can see | Always | Presented as scope, not as loss |

**Not available as a History row:** metric values, performance states, matchup context, adjusted expectations, insight card content. Those require their full framing and belong to Match Detail.

---

## 7. Core flows

```text
Open History
→ scan recent matches
→ recognise one
→ open Match Detail
```

```text
Open History
→ narrow to a role or mode
→ scan the pattern
→ open Progress for that role
```

```text
Open History
→ see a match that never processed
→ retry it
```

---

## 8. Required states

| State | Product meaning |
|---|---|
| Populated | Normal. |
| Loading / paginating | Older history arriving; the top of the list stays usable. |
| Empty — no matches | The account genuinely has nothing retained. |
| Empty — no Steam linked | Different cause, different fix. Must not look the same as the above. |
| Empty — filter matched nothing | Recoverable by changing the filter. Distinct from both. |
| Offline / sync error | Everything known is still correct and usable. Only freshness is in doubt. |
| Bootstrap unsettled | Matches appearing progressively; not an incomplete-forever state. |
| Entitlement-limited | The list has a floor. Honest scope, not data loss, not a performance statement. |
| Row: basics available, deeper read coming | **The normal state for a recent match.** The row is complete for scanning and fully openable. Marked minimally, if at all. |
| Row: deeper read will never arrive | An ordinary row. No warning, no badge of failure. The explanation lives on Match Detail. |
| Row: processing | Normal, temporary. |
| Row: waiting for an earlier match | Correct and temporary — its result is fine, its position isn't settled. |
| Row: needs action | A single Retry. |
| Row: unavailable | Data never arrived. Visible, explained, retryable. |
| Row: doesn't count | Visible, with a reason. Not a failure. |
| Row: role recently corrected | Reflects the new role once the rebuild finishes. |

---

## 9. User actions

Scroll / paginate · scope by mode, role or time (if offered) · open a match · retry a failed match · refresh · jump into a role's progression.

---

## 10. Experience requirements / guardrails

- **MUST NOT** turn a row into a mini Match Detail. No performance states, no matchup context, no insight content, no metric numbers.
- **MUST NOT** turn History into a status dashboard. No progress bars, percentages, ETAs, retry counts, queue positions or backend vocabulary. If a readiness marker draws more attention than the match, it is too loud.
- **MUST** list a match as soon as its basics exist, and **MUST** keep it listed while its deeper read is pending or permanently absent. A row that vanishes and returns reads as data loss.
- **MUST** keep every row openable at every readiness — Match Detail is worth opening before the deeper read arrives.
- **MUST** show every retained match, including ones that don't count and ones that failed. Hiding them looks like data loss.
- **MUST** pair "doesn't count" with its reason.
- **MUST** show mode on every row — the list mixes Standard and Turbo.
- **MUST NOT** compute any progression across modes or across roles. A "Carry" filter over both buckets may *list* matches, but any number derived from it must be bucket-scoped.
- **MUST NOT** present win/loss streaks or a win-rate curve as progression.
- **MUST NOT** present an entitlement floor as data loss, or as a reason history looks worse.
- **MUST** keep chronological order authoritative — a recovered old match appears where it belongs, not at the top.
- **MUST NOT** claim an empty account when the real cause is offline, unlinked, or a filter.
- Result and role must not be composed into a single glanceable judgment.

---

## 11. Design freedom

Open: row anatomy and density; whether rows group by day/week/session; list vs sectioned vs timeline presentation; whether scoping is chips, tabs, a sheet, or a search field, and which scopes exist at all; whether role/mode composition is charted, listed, or omitted; how the six lifecycle states are visually differentiated; how a PB marker (if any) looks; pagination vs infinite scroll; empty-state art and copy; how the entitlement floor is communicated; motion, swipe actions, and whether Retry is inline.

---

## 12. UX success metrics

| Metric | Why it matters | Observable |
|---|---|---|
| Successful match-finding | The primary task: locate a remembered game | Research: time and success rate finding a described match |
| History → Match Detail rate | History's job is routing into depth | Analytics: History sessions → Match Detail opens |
| Scan depth | Whether people actually browse, or bounce | Analytics: rows viewed per session; pagination rate |
| Failed-state recovery | Stuck matches must be exitable from here | Analytics: retries initiated from History → success |

Instrumented: match-open rate, scan depth, filter usage, retry success. Research-only: find-a-match task success, whether empty states are correctly attributed.

---

## 13. UX risks / questions to test

- With only hero, result, role and mode on a row, can users still find the match they mean?
- Does a row *without* performance information feel incomplete — and does adding it start recreating Match Detail?
- Do users read a run of losses in the list as "I'm getting worse"?
- Are the three empty states (no matches / no Steam / no filter results) distinguishable in practice?
- Does an "unavailable" row read as an app bug?
- Does mixing Standard and Turbo in one list confuse, or is per-row mode enough?
- Is "how has my recent play evolved" better served here, or should it push entirely to Progress?

---

## 14. Out of scope

- History is not Match Detail — no per-metric analysis, matchup context or insight cards in a row.
- History is not Progress — metric timelines and baseline analysis live there.
- History is not Profile — it shows what was played, not who the player is.
- Role correction does not happen here.
- History defines no retention of its own; how far back the list goes is an entitlement question.

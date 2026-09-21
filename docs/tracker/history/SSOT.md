# History — SSOT

**Status:** ACTIVE — feature contract
**Scope:** The chronological record of retained matches: browsing, scanning, filtering, and navigating into individual matches.
**Inherits:** [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md).

## Architecture dependencies

| Concern | Authoritative source |
|---|---|
| Evidence readiness; when a match enters the record | [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §4A · [`../architecture/MATCH-INGESTION-AND-LIFECYCLE.md`](../architecture/MATCH-INGESTION-AND-LIFECYCLE.md) §3 |
| Which History blocks need which evidence class | [`../architecture/FEATURE-DATA-DEPENDENCY-MATRIX.md`](../architecture/FEATURE-DATA-DEPENDENCY-MATRIX.md) §5 |
| Why rows are driven by persisted records | [ADR 0001](../architecture/decisions/0001-provider-independent-hybrid-ingestion.md) — the client reads persisted state, never a provider |

---

## 1. Purpose

History answers:

> What have I played, and how has my recent play evolved?

It is the place to browse the chronological match record and move into any match. It is the only surface that shows **everything the account has played**, including matches that do not count toward progression.

History is a **record**, not an analysis. Deep per-metric analysis lives in `match_detail/`; long-range role progression lives in `progress/`; durable identity lives in `profile/`.

---

## 2. What History contains

The retained match record for the **active Steam profile**, in reverse-chronological order by the canonical chronology key `(provider_started_at, provider_source_match_id)`.

Every retained match appears, including:

- progression-eligible READY matches;
- progression-**ineligible** READY matches (`NONE(reason)`), with their reason;
- matches still processing (`WAITING_FOR_PROVIDER`, `ANALYZING`, `WAITING_FOR_PRIOR_MATCH`);
- matches in `ACTION_REQUIRED`;
- matches that are `UNAVAILABLE`.

A match is never hidden because it failed, because it doesn't count, or because it is unavailable. `UNAVAILABLE` is not deletion.

### 2.1 History is driven by persisted records

History renders from Dota Tracker's own persisted match records. Opening, scrolling, filtering or refreshing History **MUST NOT** trigger a provider call anywhere in the stack.

### 2.2 When a match appears, and when it stays

1. **A match appears once summary-class evidence exists** (`SUMMARY_READY`, foundation §4A). It is never withheld pending deep analysis.
2. **A match never disappears because deep analysis is pending, delayed or permanently unavailable.** Readiness changes what a row can say; it never changes whether the row exists.
3. **Row navigation is always valid**, at every readiness. Every row opens Match Detail, which is useful from Stage 1.
4. **A row updates in place** as readiness advances. Its chronological position never changes.
5. **A match whose deep analysis will never arrive is an ordinary row.** It is not marked as failed, and it carries no warning.

### 2.3 History is not a status dashboard

A row MAY carry a **minimal** readiness signal where it genuinely helps scanning. It MUST NOT become a pipeline-status display:

- no provider names, no pipeline vocabulary (foundation §4A.5);
- no progress bars, percentages, ETAs, retry counts or queue positions;
- no per-row diagnostic detail about why deep analysis is outstanding.

If a row's readiness signal would draw more attention than the match itself, it is too loud.

---

## 3. Chronology and mode

- Ordering is **strictly chronological**, never discovery order, notification order, or worker-completion order.
- A recovered or late-admitted historical match is inserted at its **true chronology position**, never appended.
- The list MAY span both progression buckets, because it is a chronological record, not a progression calculation. Every entry MUST carry its own mode.
- Any *calculation* shown in History (a rate, a share, a comparison, an aggregate) remains strictly per-bucket and per-role under foundation §6–§11. A combined "all" view MUST show separated tracks or evidence; it MUST NOT silently compute a merged curve.

---

## 4. Row content boundary

**A History row is an identity row, not a miniature Match Detail.**

A row MAY carry:

- hero;
- result;
- mode (Standard / Turbo);
- effective role;
- date/time and duration;
- lifecycle state when not READY;
- progression ineligibility with its reason;
- a minimal signal that per-match detail exists (for example, that insight cards are present).

A row MUST NOT carry:

- per-metric values or performance states (Above / In line / Below);
- matchup context (Difficult / Typical / Favourable);
- adjusted expectations or baseline comparisons;
- insight card content;
- PB claims beyond, at most, a minimal marker that the match currently owns a PB.

Rationale: the per-metric layer is only meaningful with its expectation, its role framing and its unavailability semantics attached. Fragmenting it into a list row reintroduces exactly the single-glance verdict the product forbids.

---

## 5. "How has my recent play evolved?"

History carries an **evolution** job alongside browsing. It is satisfied only through content this product actually contracts:

Permitted:

- chronological structure itself (what was played, in what order, in which roles and modes);
- role/mode composition over a selected span (counts and shares of matches by role and bucket);
- per-metric canonical trend states, scoped to one bucket and one role, sourced from `progress/`;
- per-metric chronological observation series, scoped to one bucket, role and metric;
- recency facts.

Forbidden:

- any composite, cross-role, cross-metric or cross-bucket progression curve;
- any overall progress score, grade, rating or percentage;
- win/loss streaks or win-rate curves presented as progression;
- any aggregation that merges Standard and Turbo, or two roles, into one progression signal;
- any causal explanation of a result.

If History offers this depth at all, it is a **presentation window over canonical Progress data** (foundation §11.3). A calendar filter MUST NOT redefine baseline or trend math.

---

## 6. Filtering and scoping

Filters are a presentation concern; their existence is optional and their set is open to design. Whatever exists MUST obey:

1. A filter never changes canonical baseline, trend or PB math.
2. A mode filter changes which matches are listed; it never merges or re-derives progression across buckets.
3. A role filter lists matches by **effective role**, which may change after a correction.
4. A calendar filter (30D / 90D / All / monthly) is a view, not a retention rule and not an analytical window.
5. An empty filter result is an explicit "no matches match this filter" state, distinct from an empty account and from a sync error.

History has **no retention cutoff of its own**. It shows the history exposed by the current entitlement (foundation §13). A reduced entitlement removes matches from view; this MUST NOT be presented as data loss or as a performance change, and retained-but-unentitled history MUST NOT be shown as zero or as absent-because-you-played-badly.

---

## 7. Navigation

- Every row routes into `match_detail/` for that match, including ineligible, processing, action-required and unavailable matches.
- History is the destination for Home's "Last 5 Matches" and for Home's multi-match today case.
- History MAY route into `progress/` when it surfaces trend or metric-series content.
- Role correction is **not** performed in History. It is a Match Detail action (foundation §5.5). History MAY reflect a corrected role after the rebuild.

---

## 8. Correction and rebuild effects

After a role correction on match M:

- M's row reflects the new **effective role** immediately once the rebuild completes;
- M's position in chronology does not change;
- other rows do not change their identity content;
- any role- or metric-scoped aggregate shown in History recomputes for the affected role(s) within the affected bucket only;
- delivered celebrations and notifications are untouched.

After a methodology or parameter-set migration, any derived content History displays is rebuilt coherently. History MUST NOT display a mixed timeline where earlier entries use old math and later entries use new math.

---

## 9. States

| State | Meaning |
|---|---|
| Populated | Normal. |
| Loading first page | Cached content, where present, remains usable. |
| Paginating | Older history loading. Never blocks the top of the list. |
| Empty — no matches | The account has no retained matches. |
| Empty — no Steam linked | Distinct from an empty account. |
| Empty — filter result | Distinct from both of the above. |
| Sync error / offline | Known history remains fully usable and accurate; only freshness is in doubt. History MUST NOT claim the account is empty. |
| Bootstrap unsettled | Matches appear progressively; history-dependent content pends per mode. |
| Entitlement-limited | Visible history is bounded by entitlement. Shown honestly; never as loss or as poor performance. |
| Row processing | Per-match lifecycle state, not an error. |
| Row summary-available, deep pending | The common state for a recent match. Row present, openable, minimally marked at most. **Not an error, not a warning.** |
| Row deep ready | Normal. |
| Row deep permanently unavailable | An ordinary row. Marked only if it genuinely helps scanning; the explanation lives on Match Detail. |
| Row action-required | Retry reachable from the row or from its Match Detail. |
| Row unavailable | Visible, explained, still manually retryable. Reserved for matches whose summary-class truth never arrived. |
| Row ineligible | Visible, marked as not counting, with its reason. |

---

## 10. Hard invariants

- Every retained match is visible, including ineligible, failed and unavailable matches.
- History renders from persisted records; no History interaction triggers a provider call.
- A match appears once summary-class evidence exists, and never disappears because deep analysis is pending or permanently unavailable.
- Row navigation into Match Detail is valid at every readiness.
- History is never a provider-status dashboard: no provider names, no pipeline vocabulary, no progress bars, ETAs, retry counts or queue positions.
- Ordering is by canonical chronology; late-recovered matches are inserted at their true position.
- Each entry carries its own mode; no progression calculation crosses buckets or roles.
- A History row never becomes a miniature Match Detail.
- No composite progression curve, score, grade, rating or percentage appears in History.
- Win/loss is never presented as progression.
- Filters never redefine canonical baseline, trend or PB math.
- History has no retention cutoff of its own.
- Entitlement limits are presented as scope, never as loss or performance.
- N/A is never rendered as zero; an unready state is never rendered as a neutral value.
- Role correction does not happen here.
- No causal explanation of any result appears here.

---

## 11. Acceptance rules

- [ ] A match finished minutes ago is listed and openable before its deep analysis exists.
- [ ] A row with pending deep analysis does not disappear when the user refreshes, filters or returns later.
- [ ] A row whose deep analysis is permanently unavailable is not marked as failed and carries no warning.
- [ ] No row shows a progress bar, percentage, ETA, retry count, queue position, provider name or pipeline term.
- [ ] Ineligible, processing, action-required and unavailable matches are all listed and openable.
- [ ] A recovered historical match appears at its true chronological position, not at the end.
- [ ] Every row shows its mode; no aggregate mixes Standard and Turbo.
- [ ] No row exposes per-metric performance state, matchup context, or insight content.
- [ ] An ineligible row states that it does not count and gives the reason.
- [ ] A calendar or mode filter changes what is listed without changing any canonical calculation.
- [ ] Empty-account, unlinked and empty-filter states are visually and semantically distinct.
- [ ] Offline/sync-error preserves the full known history and never claims emptiness.
- [ ] A reduced entitlement removes matches from view without implying data loss or decline.
- [ ] After a role correction, the corrected row shows the new role and affected aggregates recompute within that bucket only.

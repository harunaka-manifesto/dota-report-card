# Activity Heatmap — SSOT

A GitHub-style calendar of how much a player played each role. It sits on the role screen beside
the Role Mastery level. The backend contract is `activity-heatmap-v1`; iOS design is pending.

Cross-product rules come from [`app_foundation/SSOT.md`](../app_foundation/SSOT.md). This
document only projects them onto the heatmap.

## 1. Owner decisions (2026-09-29)

| Question | Decision |
|---|---|
| Cell | One **local calendar day**, at every zoom level from week to year. The client zooms locally. |
| Value | **Match count**. It is not XP, playtime, win/loss or a performance signal. |
| Counted matches | `READY` only, **Standard and Turbo combined**, with no mode filter. Unsupported-mode, `UNAVAILABLE`, `ACTION_REQUIRED` and in-flight matches are not counted. |
| Series | `ALL`, `CARRY`, `MID`, `OFFLANE`, `SUPPORT`, in one response. `ALL` is the sum of the four roles. |
| Day boundary | The client sends an IANA `time_zone` on each request, as Home does. No time zone is stored. |
| Window | By default, the trailing 365 local days ending today. Older data is paged by **calendar year** (`year=2025` covers 1 Jan–31 Dec; the current year ends today). |
| Crop | The grid starts on the first local day holding a counted, visible match. Days before that are not drawn. |
| Levels | Computed by the server as `heatmap-levels-v1`: 1 match = level 1, 2–3 = 2, 4–5 = 3, 6+ = 4. Days without a match are omitted, which means level 0. |
| Totals | `total_matches` per series only. No active-day count, busiest day or streak. |
| Week start | Up to the client. The server returns ISO dates only. |
| Entitlement | The existing entitled-history scope only (ADR 0004). Free sees its permanent history, including earlier years it owns; Pro also sees recovered backfill. There is no heatmap-specific gate. |
| Drill-in | Tapping a cell opens that day's matches through `/history` with `local_date`, `time_zone` and `ready_only=true`, plus `role` for a role series. The list length equals the cell count. |

## 2. Guardrails

- **Presentation only.** The calendar window never feeds baselines, trends, PBs, mastery or any
  progression state (foundation §11.3).
- **No streaks, no decay, no trend.** Gaps are not penalties, and the heatmap never implies
  improvement or decline (foundation §11.1, §11.3).
- **Coverage is stated.** The grid is cropped to the first counted day. When bootstrap matches
  are visible and no pre-link Pro backfill is, the span from the first bootstrap day to the local
  link date is returned as `partial_ranges` with reason `BOOTSTRAP_SAMPLE`, because bootstrap
  imports at most 30 matches per mode ([onboarding](../onboarding/SSOT.md)). The client should mark that span as
  partial, never as "played little".
- **Provider-free.** A render reads persisted data only. It never starts backfill or a provider
  call (foundation §13.2).
- **Retroactive truth.** Role corrections, late finalization and scope changes move counts
  silently on the next read. The body ETag changes with them, and nothing is celebrated.

## 3. Data

Counts are computed on read from `tracker_account_matches`, using `provider_started_at` and
`effective_role`. The application buckets local days with the same IANA zone rules as `/history`
and `/hero-pool`, never PostgreSQL's `timezone()`, which reads names such as `CET` as fixed-offset
abbreviations and ships its own tz database. Only tz database names are accepted. Dates before 2011
or after local today are never counted or advertised in `available_years`. There is no
materialized table. Materializing waits for measured read load
([DATA-CONTRACTS-AND-VERSIONING](../architecture/DATA-CONTRACTS-AND-VERSIONING.md)).

## 4. API

`GET /mobile/v1/activity?time_zone=<IANA>[&year=YYYY]`. See the [API](../api/README.md#activity-heatmap-activity-heatmap-v1).

## 5. History drill-in

`GET /mobile/v1/history?local_date=YYYY-MM-DD&time_zone=<IANA>&ready_only=true[&role=…]`.
`local_date` requires `time_zone`; `time_zone` alone is ignored. Cursors are bound to the day filter.

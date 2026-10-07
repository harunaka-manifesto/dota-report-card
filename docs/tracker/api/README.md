# Mobile API (v1)

The iOS client's only backend boundary. It is a separate FastAPI application mounted at
`/mobile/v1` with its own OpenAPI document. The process root serves only `/health*` and the
`/store` and `/internal/tracker` sub-applications beside it. Resource design and state projections are specified in
[MOBILE-API-DRAFT](../architecture/MOBILE-API-DRAFT.md); product meaning in the
[feature SSOTs](../README.md).

- Contract: [`mobile-openapi-v1.json`](mobile-openapi-v1.json), exported with
  `make tracker-openapi`. `tests/tracker/test_mobile_golden.py` fails when the live schema drifts
  from this file, lints it structurally and scans it for pipeline/provider vocabulary.
- Golden responses: `tests/fixtures/tracker/mobile-v1/` — one file per seeded persona, covering
  every state the goal lists (bootstrap outcomes, Stage 1/2, failures, N/A beside zero, trends,
  roles, Free/Pro, switch cooldown, deletion, data access, sync error). They are compared, never
  overwritten; a contract change adds a new versioned directory. Item-timing responses belong in
  `tests/fixtures/tracker/mobile-v1-item-timings-v1/`; preserve the existing goldens.
  The current core-chart response belongs in
  `tests/fixtures/tracker/mobile-v1-core-graphs-v1/`; preserve earlier versions.
  The directory the golden test compares today is
  `tests/fixtures/tracker/mobile-v1-viewer-row-v1/`. Earlier directories are historical records
  and may carry retired metric ids (for example `support.healing.v1`); clients should build
  fixtures from the current directory.
- Local data: `make seed-demo` creates the same personas without provider calls.

## Conventions

| Concern | Rule |
|---|---|
| Authentication | Bearer access token from `/auth/apple` or `/auth/google`; rotating refresh tokens (`/sessions/refresh`). Email is unavailable until its mechanism is decided. |
| Isolation | Every resource is scoped to the caller's account and active Steam profile; match references are opaque UUIDs. Foreign references return 404. |
| Mutations | Every mutating POST requires `Idempotency-Key`; a replay returns the first result, a different body with the same key returns `409 IDEMPOTENCY_CONFLICT`. |
| Errors | `application/problem+json` with a stable `code` and a `request_id`. No upstream text or private identifiers. |
| Time | UTC RFC 3339. Home takes an IANA `time_zone` for "today" and an explicit `mode`; Activity and the History day filter take the same `time_zone`. |
| Pagination | Opaque signed cursors bound to profile, filters and revision (`/history`). |
| Incremental refresh | Body ETags with `If-None-Match` → 304 on every JSON GET; `GET /changes?after=` returns changed match refs or `full_refresh`. Push stays READY-only. |
| Enums | Closed. Swift should keep unknown values and show a neutral unsupported state, never interpret them as success, zero or evidence. |
| Missing values | Nullable with a reason; a measured zero stays zero. Every block carries its own readiness. |
| Text | Insight cards and claims are template IDs plus typed slots. Insight history lines are versioned annex wording and always state N. |

## Role metric charts (`role-metric-history-v1`)

`GET /mobile/v1/progress/roles/{role}?mode=STANDARD|TURBO&window=LAST_7_DAYS|LAST_30_DAYS|LAST_365_DAYS|ALL_TIME&time_zone=<IANA>[&cursor=…][&limit=1..500]`
bundles the selected role's four canonical metric charts. Product rules are in
[`progress/SSOT.md` §6A](../progress/SSOT.md#6a-role-metric-charts-owner-decision-2026-10-03).
`role` is `CARRY|MID|OFFLANE|SUPPORT`. `mode`, `window` and `time_zone` are required;
`limit` defaults to 200 and counts matches, not metric observations.

```text
RoleProgressView
  contract_version: "role-metric-history-v1"
  role, mode, window, time_zone
  start_date: date | null                // all-time: earliest eligible track day, or null
  end_date: date                         // today in time_zone; inclusive local-day bounds
  scope: FREE|PRO
  scope_revision: integer
  state: STEAM_LINK_REQUIRED|UNSTARTED|AVAILABLE|REBUILDING
  selected_window_match_count: integer | null // null while rebuilding
  metrics: RoleProgressMetricView[]      // always the role's four metric IDs, sorted
  next_cursor: string | null
RoleProgressMetricView
  metric_id, metric_version
  unit: GOLD|COUNT|FRACTION|COUNT_PER_10_MINUTES
  measured_count, unavailable_count: integer // whole selected window
  latest: RoleProgressPoint | null       // latest measured point in the whole selected window
  baseline: {state: BUILDING|READY|NOT_AVAILABLE, value: number | null, prior_count}
  trend: {state: IMPROVING|STABLE|DECLINING|INSUFFICIENT_HISTORY | null,
          reason: CALIBRATION_UNAVAILABLE | null, point_count}
  personal_best: {match_ref, value, hero_id, achieved_at} | null
  points: RoleProgressPoint[]
RoleProgressPoint
  match_ref, started_at, hero_id
  state: MEASURED|NOT_AVAILABLE
  raw_value, comparison_value: number | null
  unavailable_reason: string | null
  baseline: {state: BUILDING|READY|NOT_AVAILABLE, value: number | null, prior_count}
```

- Swift Charts uses `started_at` for x and `comparison_value` for y. `FRACTION` is a fraction
  (0.25 means 25%); `COUNT_PER_10_MINUTES` already contains the normalized rate. Never derive
  a value from `raw_value`, use zero for N/A, or turn a negative gold advantage into zero.
- `latest` supplies the card number and its source match even if its point is on an older page.
  `baseline`, `trend` and `personal_best` at metric level describe **full entitled history**;
  `points[].baseline` describes that individual match's previous-only comparison context.
- Pages select newest matches first and return points ascending, tied by stable match order.
  Prepend older pages and merge by `match_ref`. Keep a loading/partial state until `next_cursor`
  is null; pagination never silently downsamples or aggregates the per-match line.
- Cursors reject profile/filter/period/scope/history changes with `400 CURSOR_INVALID`.
  Refetch the first page after that error. A local midnight that changes the resolved window
  also invalidates pagination. Unknown timezone names return `400 TIME_ZONE_INVALID`;
  invalid enum values or limits return the standard validation problem (422).
- Every period is available on Free and Pro; `scope` is the currently coherent active history
  scope, which may remain Free while Pro history imports. All-time is known entitled data.
  Neither a calendar gap nor inaccessible history produces a fabricated zero observation.
- Mixed/outdated methodology or incomplete metric rows return `REBUILDING`, empty points,
  unavailable baseline/PB/latest, and a null window count. An empty selected window on an
  established track is `AVAILABLE` with count 0 and null latest values.
- Uses persisted data only, one consistent database snapshot, account/profile isolation and
  standard ETag/304 behavior. The original `/progress` endpoint is unchanged. New response
  fixtures are in `tests/fixtures/tracker/role-metric-history-v1/`.

## Role Mastery

`GET /mobile/v1/mastery` is reusable by Home, Profile and Progress. With the approved parameter set registered (migration `0017`), a fresh database serves `AVAILABLE` once a profile's entitled finalized matches have awards, and `BACKFILLING` while the one-time quiet backfill runs; the client should render `BACKFILLING` as a neutral "calculating" state. A parameter refresh never changes existing awards; totals change only through new matches, late replay bonuses, role corrections and entitlement display caps. It returns `STEAM_LINK_REQUIRED`, `CALIBRATION_PENDING`, `BACKFILLING`, or `AVAILABLE`; when available it has four role summaries and live in-app level milestones. A role is `UNSTARTED` before its first award. Free caps the visible level at 5, omits total XP, and hides within-level XP at the cap. Pro receives earned level and total XP.

`GET /mobile/v1/mastery/{role}/awards` returns signed XP ledger entries under the current rule (`role-mastery-v2`) with mode, kind, structured reason (`LIVE_FINALIZATION`, `RECOVERY`, `HISTORICAL_IMPORT`, `METHODOLOGY_REBUILD`, `LATE_REPLAY`, `ROLE_CORRECTION`), qualifying Above and PB metric IDs (only the role's four canonical metrics), source versions, and an entitled opaque match reference. Superseded-rule audit rows are never returned. It uses profile/role/revision-bound signed cursors. Entries for Pro-only history are omitted from Free responses. Neither endpoint starts provider work. See [`role_mastery/SSOT.md`](../role_mastery/SSOT.md).

## Activity heatmap (`activity-heatmap-v1`)

`GET /mobile/v1/activity?time_zone=<IANA>[&year=YYYY]` returns per-day counts of READY Standard and Turbo matches for `ALL` and each role, in one response. Product rules are in [`activity/SSOT.md`](../activity/SSOT.md).

```text
ActivityView
  contract_version: "activity-heatmap-v1"
  levels_version: "heatmap-levels-v1"   // 1 | 2–3 | 4–5 | 6+ matches → level 1–4
  time_zone: string
  today: date                            // local
  window: {start_date, end_date} | null  // cropped to the first counted day; null if none
  available_years: integer[]             // requestable local years (2011..today) with ≥1 counted match, newest first
  partial_ranges: {start_date, end_date, reason: BOOTSTRAP_SAMPLE}[]
  series: {role: ALL|CARRY|MID|OFFLANE|SUPPORT, total_matches, days: {date, count, level}[]}[]
```

- Without `year`, the window is the trailing 365 local days ending today. `year` selects a calendar year, and the current year ends today. A year before 2011 or after the local current year returns `400 YEAR_INVALID`. A name outside the tz database (including `posixrules`) returns `400 TIME_ZONE_INVALID` on every route that takes `time_zone`.
- `days` is sparse and ascending: omitted dates mean zero, inside `window`. Series are always present, even when empty.
- The route reads persisted data only. It uses the entitled-history scope, has no mode filter, and gets the standard body ETag.
- Cell drill-in: `GET /history?local_date=YYYY-MM-DD&time_zone=<IANA>&ready_only=true[&role=…]`. `local_date` requires `time_zone` (`400 TIME_ZONE_REQUIRED`); `time_zone` alone is ignored. The signed cursor is bound to the day filter.

## Matches (`matches-list-v1`)

`GET /mobile/v1/matches?time_zone=<IANA>[&q=…][&hero=…&hero=…][&role=…][&mode=STANDARD|TURBO][&from=YYYY-MM-DD][&to=YYYY-MM-DD][&cursor=…][&limit=1..50]` returns entitled Standard and Turbo matches, newest first, grouped into play sessions. Product rules are in [`matches/SSOT.md`](../matches/SSOT.md). It replaces `/history` for the Matches page; `/history` is unchanged until iOS migrates.

```text
MatchListView
  contract_version: "matches-list-v1"
  time_zone: string
  has_matches: boolean                   // any listed match before filters and search
  sessions: PlaySessionView[]            // only sessions on this page, newest first
  next_cursor: string | null
PlaySessionView
  session_ref: string                    // ref of the session's first match
  name: string                           // custom, or the placeholder in time_zone
  name_is_custom: boolean
  local_date: date                       // local day of the first match
  started_at, ended_at: datetime         // first start, latest end
  wins, losses, match_count: integer     // whole session, ignoring filters
  matches: {ref, mode, started_at, duration_seconds | null, hero_id, role | null, won | null,
            kills | null, deaths | null, assists | null, lifecycle, progression, progression_reason,
            has_insight_cards, owns_personal_best}[]
```

- A session can continue on the next page. The client merges pages by `session_ref`. Header fields describe the whole session, so they never change with filters.
- `q` is at most 100 characters. Every term must match the row's hero, role, mode or result, or the session's displayed name. `hero` repeats up to 10 times (`400 HERO_INVALID` for an id outside 1–999). `from`/`to` are inclusive local days (`400 DATE_RANGE_INVALID` when `from` > `to`). An unknown zone returns `400 TIME_ZONE_INVALID`.
- The signed cursor is bound to the profile, its revision and every filter, search and time-zone value. Any change returns `400 CURSOR_INVALID`.
- Reads persisted data only, uses the entitled-history scope, and gets the standard body ETag. Tapping a row opens `GET /matches/{ref}`.

`POST /mobile/v1/matches/sessions/{session_ref}/name?time_zone=<IANA>` with `{"name": string | null}` and `Idempotency-Key` names a session, or restores its placeholder with `null`. The name is trimmed, internal whitespace is collapsed, and it must be 1–40 printable characters (`422` otherwise). It returns the session header without `matches`. A ref that is not the first match of a visible session returns `404 SESSION_NOT_FOUND`. With no linked profile it returns `409 STEAM_LINK_REQUIRED`.

## Hero pool (`hero-pool-v1`)

`GET /mobile/v1/hero-pool?time_zone=<IANA>` returns each role's most played heroes over trailing 7, 30 and 365 local days, in one response. Product rules are in [`hero_pool/SSOT.md`](../hero_pool/SSOT.md).

```text
HeroPoolView
  contract_version: "hero-pool-v1"
  time_zone: string
  today: date                            // local
  partial_ranges: {start_date, end_date, reason: BOOTSTRAP_SAMPLE}[]  // clipped to the 365-day window
  roles: {role: CARRY|MID|OFFLANE|SUPPORT,
          windows: {window: LAST_7_DAYS|LAST_30_DAYS|LAST_365_DAYS, start_date, end_date,
                    total_matches, heroes: {hero_id, matches}[]}[]}[]
```

- Windows end today inclusive. `heroes` holds at most 10 entries ordered by matches, then most recent play, then `hero_id`; `total_matches` counts every hero. Roles and windows are always present, even when empty. An unknown zone returns `400 TIME_ZONE_INVALID`.
- It counts the same READY Standard and Turbo matches as Activity, reads persisted data only, uses the entitled-history scope, and gets the standard body ETag.

## Match Detail: the viewer's own row

`GET /matches/{match_ref}` carries `hero_id` and `player_slot` for the signed-in player.
`player_slot` is the canonical slot (Radiant 0–4, Dire 5–9) of the account's own row and is
also that row's index in `players[]`, which is always the ten-player roster ordered by slot;
`hero_id` equals `players[player_slot].hero_id`. Both come from the stored account-match link,
so they are present in every lifecycle, including before READY. They are null only when the
stored roster has no row at the link's slot, which the storage constraints do not allow today;
treat null as "viewer unknown", never as a guess.

## Match Detail: item timings

`GET /mobile/v1/matches/{match_ref}` adds `item_timings`; no other route includes this block. It is a structured, localized-copy-free snapshot. The complete algorithm and item taxonomy live in the [item-timings annex](../match_detail/ITEM-TIMINGS-V1.md).

```text
ItemTimingsView
  state: AVAILABLE | PENDING | UNAVAILABLE
  contract_version: "item-timings-v1" | null
  reason: string | null
  reference_digest: string | null
  items: ItemTimingView[]

ItemTimingView
  item_id: integer
  item_key: string
  item_name: string
  purchase_time_seconds: integer
  key_item_order: integer
  comparison: ItemTimingComparisonView | null

ItemTimingComparisonView
  kind: POPULATION_USUAL | PERSONAL_PREVIOUS_BEST | PERSONAL_USUAL
  baseline_seconds: integer
  delta_seconds: integer
  sample_size: integer
  cohort_patch: string
```

- `PENDING` means match analysis has not finished. `UNAVAILABLE` means purchase evidence, the match itself, or a compatible analysis is absent (`reason` distinguishes `MODE`, `SOURCE_EVIDENCE`, `MATCH_<lifecycle>` and `ANALYSIS_VERSION`). `AVAILABLE` means purchase evidence exists, including an empty `items` array when no key item was bought.
- Items are ordered by purchase second, then item ID. `key_item_order` is one-based and match-local — it is a fact about this match only, never a baseline key.
- Every role can receive factual timing rows. Support comparisons are always `null`; Carry, Mid and Offlane receive a comparison only when its exact hero × core-role × mode × item reference or personal-history gates qualify.
- `delta_seconds` is the positive number of seconds earlier than the stated baseline. `sample_size` is the population reference's `purchase_count` (the hero/role/mode/item cohort's first-purchase count) for population evidence, or the strictly prior comparable personal-match count for personal evidence. `cohort_patch` is the reference artifact's major patch for population evidence (references pool unaffected earlier lettered updates) and the major-patch cohort for personal history.
- Item names come from backend catalog data. Localized headings, comparison sentences and evidence lines live in the content bank, not this response.

## Match Detail: offlane laning and detected fights

`GET /mobile/v1/matches/{match_ref}` adds `offlane_context` for the effective Offlane role;
other roles receive `null`. The block is frozen in the finalized analysis and reads make no
provider requests. Role correction rebuilds it from retained evidence.

```text
OfflaneContextView
  contract_version: "offlane-context-v2"
  enemy_carry_hero_id: integer | null
  net_worth: OfflanePanelView
  xp: OfflanePanelView
  fights: OfflaneFightsView

OfflanePanelView
  state: AVAILABLE | PENDING | UNAVAILABLE
  reason: string | null
  points: OfflaneMinuteView[]

OfflaneMinuteView
  time_seconds: integer        // 0, 60, …, 600
  you: integer
  enemy_carry: integer
  difference: integer          // you - enemy_carry

OfflaneFightsView
  state: AVAILABLE | PENDING | UNAVAILABLE
  reason: string | null
  segments: OfflaneFightSegmentView[]

OfflaneFightSegmentView
  segment_index: integer       // one-based source order
  start_seconds: integer
  end_seconds: integer
  offlaner_damage: integer
  allied_damage_total: integer
  damage_share: number | null  // 0..1; null if allied total is zero
  damage_participated: boolean // offlaner_damage > 0
  offlaner_kills: integer
  offlaner_deaths: integer
  allied_hero_deaths: integer
  enemy_hero_deaths: integer
  death_trade: FAVORABLE | EVEN | UNFAVORABLE
```

The two API panels have independent readiness. Net worth is the value at the stated minute; XP is
earned since 0:00. A positive difference means the offlaner is ahead. Points are exact and
may be partial for a short match or missing evidence; no interpolation is permitted. An
ambiguous enemy Carry makes both panels unavailable. The client uses a fixed 0–10 minute X
axis with one-minute snapping and fits each Y axis symmetrically about zero. Historical batches
from version 1.4 request minute XP in the existing call; older retained evidence may leave
only the XP panel unavailable. A minute chart with fewer than 3 real minutes after 0:00, or under
80% of its expected minute marks, is `UNAVAILABLE` with reason `TRAJECTORY_INCOMPLETE`; this
applies to every Offlane, Mid and Carry minute chart.

Detected fights use valid segments in an already stored OpenDota replay. A valid empty array is
`AVAILABLE` with zero segments; missing or malformed data is `UNAVAILABLE` independently of the
two laning panels. Fights starting before 0:00 are dropped (segments renumber from 1), and a
fight window running past match end is cut at the match end. Overlapping windows are retained. Per-player deaths determine the death trade;
the provider's fight-header death count is ignored. `FAVORABLE` means fewer allied hero deaths,
not that the fight was won. Zero damage does not establish absence, and detected segments are not
every engagement. The future client plots segment start over the full-match X axis and damage
share on a 0–100% Y axis; a null share has no Y marker. Match Detail reads make no provider call.
Historical STRATZ-only matches do not trigger an OpenDota fetch for this panel.
The iOS client contract uses only the net-worth panel as Offlane's first visible chart; `xp` and `fights`
remain here for compatible clients. The shared fight chart reads `core_fights` below.

### Item insight cards

`ENEMY_HERO_ITEM` and `OWN_HERO_ITEM` are the two item insight-card template IDs, both under the
single `post-match-insights 2.0.0` contract shared with every other card family — there is no
separate versioning for item cards. Both read the same frozen `item_timings` snapshot: `OWN_HERO_ITEM`
is the viewer's own best-qualifying purchase (population or previous-best), and `ENEMY_HERO_ITEM`
is the best-qualifying population purchase among enemy positions 1–3. See
[`ITEM-TIMINGS-V1.md`](../match_detail/ITEM-TIMINGS-V1.md) for full card-eligibility rules.

### Match achievements (`match-achievements-v1`)

- `GET /achievements?locale=en|id` returns the 24-entry collection (default `en`); `GET /achievements/{id}` returns one entry or 404 `ACHIEVEMENT_NOT_FOUND`. Both are account-scoped and read the same entitled-history scope as every other list: Free→Pro→Free changes what is *visible* and counted, never what is retained.
- An entry carries `key`/`asset_key`, role scope, localized name, description, general hint (no exact thresholds), proof template, `earned_count`, and the latest earning match. `order` (1–24, the display order of the final catalog; `id` stays the stable machine identifier) is always present. `rarity` (frozen `tier`, corpus `rate` at freeze or null for #1/#2/#4/#30, `version` `badge-tiers-v1`, `provisional: false`) appears only after the first earn. The tier is static data and never changes with live earn rates. #4 and #30 alone expose `progress` (`current`/`target`, computed from all visible current analyses, never from the latest match) while unearned. Match Detail `achievement_state` is `UNAVAILABLE` for a match that is not progression-eligible, and `PENDING` while an analysis awaits the quiet rebuild. An unknown `locale` falls back to English.
- Proof templates name stored proof keys; `{feat_name}` (#30) is resolved by the client from the proof's `feat_id` through the collection entry, so no internal numbering is shown. Match Detail adds `achievement_state`, `achievements` (id + factual proof) and `achievement_unavailable` (`id` + `reason` ∈ `EVIDENCE_MISSING`, `MATCH_TOO_SHORT`, `INSUFFICIENT_HISTORY`). An unavailable badge is not an empty earned list. `PENDING` means the analysis predates the rule version and is awaiting the quiet methodology rebuild.
- Awards are computed inside the single READY finalization transaction from retained evidence only (no provider or parse call). Collection `state` is `BACKFILLING` while any visible Standard analysis lacks the `achievements` object.
- Historical imports and methodology rebuilds award quietly: no per-match alert, and `MATCH_READY` never replays. A live READY notification (and its coalesced bundle) carries `achievement_ids` (each badge once, rarest first), `achievement_count` (total awards across the bundle), `achievement_top_id` (the badge to name; the client localizes it) and `achievement_more`.
- These match medals are separate from Role Mastery/progression medals; the Free Level-5 display cap does not apply here.
- Tiers (Common 1, Rare 9, Epic 10, Legendary 4) are frozen in `BADGE_TIERS`. Rules, thresholds and the #30 repeat list are frozen in `services/api/app/tracker/achievement_rules.py` (digest pinned in `tests/tracker/test_achievements.py`); copy, asset keys and the corpus rate references are in `achievement_catalog.py`. Golden: `tests/fixtures/tracker/mobile-v1-match-achievements-v1/` (now superseded by `mobile-v1-viewer-row-v1/`).

The checked-in `mobile-openapi-v1.json` is regenerated with `make tracker-openapi`; the contract golden test guards the exported schema. The `/mobile/v1` version stays fixed because these Match Detail additions carry their own `item-timings-v1`, `offlane-context-v2`, `carry-context-v1`, `mid-context-v1`, and `core-fights-v1` contract versions.

## Push notifications (`MATCH_READY`)

Push is READY-only and coalesced per account: while a bundle waits to be sent, later live READY
matches join it. The payload is:

| Key | Meaning |
|---|---|
| `kind` | Always `MATCH_READY`. |
| `count` | Matches in the bundle. |
| `match_ref` | Present only when `count == 1`: the same opaque reference `GET /matches/{match_ref}` takes. Absent for a coalesced bundle; the client then refreshes (`GET /changes`) and lands on Home. |
| `achievement_awards`, `achievement_ids`, `achievement_count`, `achievement_top_id`, `achievement_more` | See [Match achievements](#match-achievements-match-achievements-v1). |

Historical imports, bootstrap and rebuilds never push. The reference follows the same isolation
rule as every other read: another account gets 404 for it.

Server-to-server routes (`/store/app-store/notifications`) and the operations readout
(`/internal/tracker`) are separate applications without a mobile OpenAPI entry.

## Match Detail: Carry context

`GET /mobile/v1/matches/{match_ref}` includes `carry_context` for the effective Carry role and
`null` for other roles. It is frozen in the analysis and provider-free on read. The viewer's
item markers are the existing `item_timings.items`; the block adds enemy key-item markers.

```text
CarryContextView
  contract_version: "carry-context-v1"
  enemy_carry_hero_id: integer | null
  net_worth: OfflanePanelView
  hero_damage: OfflanePanelView
  enemy_key_items: CarryItemMarkersView
  you_kills: CarryKillsView
  enemy_carry_kills: CarryKillsView

OfflanePanelView.points[]
  time_seconds: integer       // exact complete minute, 0, 60, ...
  you: integer
  enemy_carry: integer
  difference: integer         // you - enemy_carry

CarryItemMarkersView
  state: AVAILABLE | PENDING | UNAVAILABLE
  reason: string | null
  items: {item_id, item_key, item_name, purchase_time_seconds, key_item_order}[]

CarryKillsView
  state: AVAILABLE | PENDING | UNAVAILABLE
  reason: string | null
  events: {time_seconds: integer}[]
```

Net worth is an exact checkpoint; hero damage is cumulative since 0:00, including lane harass.
Only complete-minute samples appear. Each panel and annotation stream has its own state; an
empty available stream means zero observed events. An unambiguous enemy Carry is required.
Missing samples are omitted, never interpolated. The client retains its own selected time
across tabs and shows the latest measured value with its actual sample timestamp.
Before finalization, all five streams are `PENDING`. A terminal unavailable match reports
`MATCH_UNAVAILABLE` or `MATCH_ACTION_REQUIRED`; an older analysis reports
`ANALYSIS_VERSION`. With a current analysis, reasons are `CARRY_UNCLEAR`,
`SOURCE_DISAGREEMENT`, `TRAJECTORY_UNAVAILABLE`, `TRAJECTORY_INCOMPLETE`, `ITEMS_UNAVAILABLE`, and
`KILLS_UNAVAILABLE`. A valid empty item or kill stream is `AVAILABLE` with `[]`.
Raw snapshot IDs, provider, query version, translation version, and digest stay in
the stored feature and analysis provenance. The public block exposes only its
contract version. Existing historical snapshots remain valid, but missing minute
damage stays unavailable; a later import of an already-finalized match does not refresh it.
The iOS client displays `net_worth` as Carry's whole-match first chart with its existing
item and kill markers. `hero_damage` stays available in the API but is not a visible chart.

## Match Detail: Mid net worth and shared detected fights

`GET /mobile/v1/matches/{match_ref}` includes `mid_context` only for the effective Mid role,
and `core_fights` for effective Carry, Mid and Offlane; other roles receive `null`. Both blocks
are frozen in the analysis and independently ready. Older analyses missing either block return
its `UNAVAILABLE` view with reason `ANALYSIS_VERSION` until a retained-data rebuild.

```text
MidContextView
  contract_version: "mid-context-v1"
  enemy_mid_hero_id: integer | null
  net_worth: MidPanelView

MidPanelView
  state: AVAILABLE | PENDING | UNAVAILABLE
  reason: string | null
  points: {time_seconds, you, enemy_mid, difference}[]

CoreFightsView
  contract_version: "core-fights-v1"
  state: AVAILABLE | PENDING | UNAVAILABLE
  reason: string | null
  segments: CoreFightSegmentView[]

CoreFightSegmentView
  segment_index: integer
  start_seconds: integer
  end_seconds: integer
  player_damage: integer
  allied_damage_total: integer
  damage_share: number | null
  damage_participated: boolean
  player_kills: integer
  player_deaths: integer
  allied_hero_deaths: integer
  enemy_hero_deaths: integer
  death_trade: FAVORABLE | EVEN | UNFAVORABLE
```

Mid net worth compares exact complete-minute points from 0:00 to 10:00 against one uniquely
identified enemy Mid. Missing or disputed points are omitted without interpolation; an unclear
opponent withholds only this comparison. `core_fights` reuses Offlane's validated fight measure
over the full match, with role-neutral player field names. An OpenDota replay with a valid empty
fight array returns `AVAILABLE` and `[]`; STRATZ-only history returns `UNAVAILABLE` without a
new OpenDota request. A null damage share has no plotted Y marker but remains a factual row.

The native client contract has exactly two charts for each core role: the role's net-worth chart and the
shared **Detected fights** chart. It retains selected time across them. Selecting a fight uses
the exact fight start; the 0–10 minute lane charts show no selected point beyond that window.
The backend exposes timestamps and stores no cursor state. Native iOS rendering and interaction
verification are pending.

## Swift code generation

No Swift OpenAPI generator is installed in this environment, so a generation dry run has not
been performed. The checked-in document is the intended generator input.

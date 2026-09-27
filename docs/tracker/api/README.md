# Mobile API (v1)

The iOS client's only backend boundary. It is a separate FastAPI application mounted at
`/mobile/v1` with its own OpenAPI document; the legacy `/v1` report API, its generated client
and its CI diff check are untouched. Resource design and state projections are specified in
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
- Local data: `make seed-demo` creates the same personas without provider calls.

## Conventions

| Concern | Rule |
|---|---|
| Authentication | Bearer access token from `/auth/apple` or `/auth/google`; rotating refresh tokens (`/sessions/refresh`). Email is unavailable until its mechanism is decided. |
| Isolation | Every resource is scoped to the caller's account and active Steam profile; match references are opaque UUIDs. Foreign references return 404. |
| Mutations | Every mutating POST requires `Idempotency-Key`; a replay returns the first result, a different body with the same key returns `409 IDEMPOTENCY_CONFLICT`. |
| Errors | `application/problem+json` with a stable `code` and a `request_id`. No upstream text or private identifiers. |
| Time | UTC RFC 3339. Home takes an IANA `time_zone` for "today" and an explicit `mode`. |
| Pagination | Opaque signed cursors bound to profile, filters and revision (`/history`). |
| Incremental refresh | Body ETags with `If-None-Match` → 304 on every JSON GET; `GET /changes?after=` returns changed match refs or `full_refresh`. Push stays READY-only. |
| Enums | Closed. Swift should keep unknown values and show a neutral unsupported state, never interpret them as success, zero or evidence. |
| Missing values | Nullable with a reason; a measured zero stays zero. Every block carries its own readiness. |
| Text | Insight cards and claims are template IDs plus typed slots. Insight history lines are versioned annex wording and always state N. |

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
only the XP panel unavailable.

Detected fights use valid segments in an already stored OpenDota replay. A valid empty array is
`AVAILABLE` with zero segments; missing or malformed data is `UNAVAILABLE` independently of the
two laning panels. Overlapping windows are retained. Per-player deaths determine the death trade;
the provider's fight-header death count is ignored. `FAVORABLE` means fewer allied hero deaths,
not that the fight was won. Zero damage does not establish absence, and detected segments are not
every engagement. The future client plots segment start over the full-match X axis and damage
share on a 0–100% Y axis; a null share has no Y marker. Match Detail reads make no provider call.
Historical STRATZ-only matches do not trigger an OpenDota fetch for this panel.
The iOS client uses only the net-worth panel as Offlane's first visible chart; `xp` and `fights`
remain here for compatible clients. The shared fight chart reads `core_fights` below.

### Item insight cards

`ENEMY_HERO_ITEM` and `OWN_HERO_ITEM` are the two item insight-card template IDs, both under the
single `post-match-insights 2.0.0` contract shared with every other card family — there is no
separate versioning for item cards. Both read the same frozen `item_timings` snapshot: `OWN_HERO_ITEM`
is the viewer's own best-qualifying purchase (population or previous-best), and `ENEMY_HERO_ITEM`
is the best-qualifying population purchase among enemy positions 1–3. See
[`ITEM-TIMINGS-V1.md`](../match_detail/ITEM-TIMINGS-V1.md) for full card-eligibility rules.

The checked-in `mobile-openapi-v1.json` is regenerated with `make tracker-openapi`; the contract golden test guards the exported schema. The `/mobile/v1` version stays fixed because these Match Detail additions carry their own `item-timings-v1`, `offlane-context-v2`, `carry-context-v1`, `mid-context-v1`, and `core-fights-v1` contract versions.

Server-to-server routes (`/store/app-store/notifications`) and the operations readout
(`/internal/tracker`) are separate applications without a mobile OpenAPI entry.

## Match Detail: Carry graphs

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
`SOURCE_DISAGREEMENT`, `TRAJECTORY_UNAVAILABLE`, `ITEMS_UNAVAILABLE`, and
`KILLS_UNAVAILABLE`. A valid empty item or kill stream is `AVAILABLE` with `[]`.
Raw snapshot IDs, provider, query version, translation version, and digest stay in
the stored feature and analysis provenance. The public block exposes only its
contract version. Existing historical snapshots remain valid, but missing minute
damage stays unavailable until a newly retained source is deliberately processed.
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

The client shows exactly two charts for each core role: the role's net-worth chart and the
shared **Detected fights** chart. It retains selected time across them. Selecting a fight uses
the exact fight start; the 0–10 minute lane charts show no selected point beyond that window.
The backend exposes timestamps and stores no cursor state.

## Swift code generation

No Swift OpenAPI generator is installed in this environment, so a generation dry run has not
been performed. The checked-in document is the intended generator input.

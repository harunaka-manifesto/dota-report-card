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

### Item insight cards

`ENEMY_HERO_ITEM` and `OWN_HERO_ITEM` are the two item insight-card template IDs, both under the
single `post-match-insights 2.0.0` contract shared with every other card family — there is no
separate versioning for item cards. Both read the same frozen `item_timings` snapshot: `OWN_HERO_ITEM`
is the viewer's own best-qualifying purchase (population or previous-best), and `ENEMY_HERO_ITEM`
is the best-qualifying population purchase among enemy positions 1–3. See
[`ITEM-TIMINGS-V1.md`](../match_detail/ITEM-TIMINGS-V1.md) for full card-eligibility rules.

The checked-in `mobile-openapi-v1.json` is regenerated with `make tracker-openapi`; the contract golden test guards the exported schema. The `/mobile/v1` version stays fixed because this is an additive Match Detail field with its own `item-timings-v1` contract version.

Server-to-server routes (`/store/app-store/notifications`) and the operations readout
(`/internal/tracker`) are separate applications without a mobile OpenAPI entry.

## Swift code generation

No Swift OpenAPI generator is installed in this environment, so a generation dry run has not
been performed. The checked-in document is the intended generator input.

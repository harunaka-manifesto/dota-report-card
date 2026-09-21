# Mobile API resource draft

Status: **Implementation design draft**. This is not a new product contract or an accepted ADR.
The [feature SSOTs](../README.md) own meaning; the [dependency matrix](FEATURE-DATA-DEPENDENCY-MATRIX.md)
owns block readiness. This draft selects transport names before schema implementation.

## Boundary and conventions

Mount a FastAPI sub-application at `/mobile/v1`, with its own `/openapi.json` and typed DTOs.
Legacy `/v1` routes and their OpenAPI remain unchanged. Reads use persisted state only.
Provider adapters, work scheduling, raw source payloads and internal position assignments
are never mobile resources. Internal operations and the App Store notification endpoint live
outside the mobile application and require separate authentication.

- Product account/session bearer credentials; authorize every resource against the current
  account and active Steam profile. Opaque references do not replace authorization.
- UTC RFC 3339 timestamps; Home requires an IANA `time_zone` and an explicit `mode`.
- Mutating POSTs require `Idempotency-Key`, scoped to account and operation, with a body digest.
  Reuse with different content returns `409 IDEMPOTENCY_CONFLICT`. Identity callbacks use
  server-created, one-use state and verified assertions, never a client-supplied identity alone.
- Lists use opaque cursors bound to account, filters, chronology and visible revision.
  History sorts by canonical start time and match reference, not discovery time.
- GET responses carry ETag and a coherent `revision`. Conditional reads return 304. A changes
  cursor is invalidated by account/profile changes; a stale cursor asks the client to refresh.
- Errors use `application/problem+json`: `type`, `title`, `status`, stable `code`, safe `detail`,
  and `request_id`. No upstream response text or private identifiers in errors.
- Closed enums in v1. Adding an enum value requires a reviewed contract version change.
  Swift should preserve unknown values and show a neutral unsupported state; it must never
  interpret an unknown value as success, zero, a role, or analytical evidence.
- Numbers are finite. Missing values are nullable with a reason; zero remains a measured value.
  Stable Pydantic objects replace untyped dictionaries in mobile responses.
- Insight cards and Profile claims use versioned template IDs with typed, card-specific slots
  and receipt references. Renderable text, if returned, comes only from that same template set.

## Resource inventory

All paths below are relative to `/mobile/v1`. A route's existence does not imply that its
implementation or acceptance tests are complete.

| Methods and path | Resource / behavior | Product authority |
|---|---|---|
| POST `/auth/apple`, `/auth/google`, `/auth/email` | Verified sign-in; email remains unavailable until its mechanism is decided (test fake supported). | [Onboarding §3](../onboarding/SSOT.md) |
| POST `/sessions/refresh`, `/sessions/logout` | Rotating sessions; revocation distinct from deletion. | [Foundation §3](../app_foundation/SSOT.md) |
| GET `/account`; GET/POST `/account/identities` | App identity and attached login methods; collision blocked, never merged. | [Settings §2](../settings_account/SSOT.md) |
| POST `/steam/links`; POST `/steam/links/complete` | Start and verify server-bound Steam ownership. | [Onboarding §4](../onboarding/SSOT.md) |
| PUT/DELETE `/devices/{device_ref}` | Push registration and permission state; never gates tracking. | [Settings §6](../settings_account/SSOT.md) |
| POST `/sync`; GET `/readiness`; GET `/changes?after=…` | Request a refresh, read independent account/match states, poll changed opaque references. No provider calls from reads. | [Foundation §4](../app_foundation/SSOT.md) |
| GET `/bootstrap`; GET `/coverage?mode=…` | Independent per-mode searches and outcomes, observed intervals and known gaps. | [Onboarding §5](../onboarding/SSOT.md) |
| GET `/home?mode=…&time_zone=…` | Today, focus, challenge slot, role summaries and last five matches. | [Home](../home/SSOT.md) |
| GET `/history?mode=…&role=…&hero=…&cursor=…` | Filtered history and period claims with explicit coverage. | [History](../history/SSOT.md) |
| GET `/matches/{match_ref}` | Facts plus separately ready performance, context and insight blocks. | [Match Detail](../match_detail/SSOT.md) |
| POST `/matches/{match_ref}/role`; POST `/matches/{match_ref}/retry` | Append authoritative role correction; one retry action resumes valid work. Correction uses expected revision. | [Match Detail §6](../match_detail/SSOT.md) |
| GET `/progress?mode=…&role=…&metric_id=…` | Observations, baseline snapshots, trend, current PB and scope. | [Progress](../progress/SSOT.md) |
| GET `/profile?mode=…`; POST `/profile/favourite-hero` | Identity/roles/heroes/claims/Right now/PBs/change receipts; favourite is explicit user choice. | [Profile](../profile/SSOT.md) |
| POST `/shares`; GET `/shares/{share_ref}` | Immutable privacy-safe Profile/PB projection; public sharing never reveals private account or match identifiers. | [Profile §10](../profile/SSOT.md) |
| GET/PATCH `/settings` | Notification preferences and permitted display preferences. | [Settings](../settings_account/SSOT.md) |
| POST `/steam/switch-preflight`; POST `/steam/switch` | Verified target, cooldown and import/rebuild checks; atomic active profile replacement. | [Settings §3](../settings_account/SSOT.md) |
| GET `/subscription`; POST `/subscription/transactions` | Store-verified entitlement and coherent activation status. Steam required before purchase. | [Settings §5](../settings_account/SSOT.md) |
| POST `/data-access/confirm`; GET `/history-operation` | Restore data access, expose import/rebuild status and coverage without moving the original entitlement anchor. | [Onboarding §8](../onboarding/SSOT.md) |
| GET `/recovery`; DELETE `/account` | Blocked/collision recovery boundary; immediate deletion fence and Steam release. No invented recovery verification flow. | [Settings §4, §7](../settings_account/SSOT.md) |

No follow API, achievement API, XP algorithm, challenge mechanics, or periodic report content is contracted.

## State projections

Transport aliases below preserve locked product meanings. They do not alter the internal
lifecycle or add product outcomes. Tests must enforce these mappings and forbid operational
vocabulary in both the mobile OpenAPI and fixtures.

| Concept | Public enum / shape | Source |
|---|---|---|
| Mode | `STANDARD`, `TURBO` | Foundation §6 |
| Role | `CARRY`, `MID`, `OFFLANE`, `SUPPORT`; nullable when unresolved | Foundation §5 |
| Sync | `IDLE`, `CHECKING`, `UP_TO_DATE`, `SYNC_ERROR` | Foundation §4.2 |
| Match lifecycle | `WAITING_FOR_DATA`, `ANALYZING`, `WAITING_FOR_PRIOR_MATCH`, `ACTION_REQUIRED`, `READY`, `UNAVAILABLE` | Foundation §4.3; `WAITING_FOR_DATA` projects internal `WAITING_FOR_PROVIDER` |
| Independent facts/detail readiness | `PENDING`, `AVAILABLE`, `UNAVAILABLE`, with a typed reason when unavailable | Foundation §4A; matrix §4. Summary facts can be available while analysis is pending. |
| Role source | `INFERRED`, `USER_CONFIRMED`; confidence flag and correction availability separate | Foundation §5; Match Detail §6 |
| Progression | `STANDARD`, `TURBO`, or `NONE` with reason; null before finalization | Foundation §6; an acquisition failure is never successful `NONE` |
| Metric value | `PENDING`, `MEASURED`, `NOT_AVAILABLE`; nullable value and reason | Foundation §8; `MEASURED` accepts zero |
| Baseline | `BUILDING`, `READY`, `NOT_AVAILABLE`; prior count and nullable median | Foundation §9; independently per metric/version/role/mode |
| Performance | `ABOVE`, `IN_LINE`, `BELOW`, `NOT_READY`; absent for N/A and diagnostic-only metrics | Foundation §10 |
| Trend | `IMPROVING`, `STABLE`, `DECLINING`, `INSUFFICIENT_HISTORY`; nullable with `CALIBRATION_UNAVAILABLE` reason | Foundation §11 and open calibration decision; no fifth trend state |
| Lane context | `DIFFICULT`, `TYPICAL`, `FAVOURABLE`, `UNAVAILABLE` | Match Detail §4.3; unavailable renders nothing |
| Insights | Independently pending or settled, then zero to three typed cards | Match Detail §5; zero cards is normal |
| Bootstrap | Non-terminal status separate from nullable outcome: `NO_STEAM_LINKED`, `DATA_ACCESS_BLOCKED`, `NO_MATCHES_FOUND`, `NO_ELIGIBLE_MATCHES`, `READY`, `READY_WITH_GAPS` | Onboarding §5.4; per mode |
| Coverage | Intervals, observed start/end, known gaps, and capability labels `MATCH_FACTS` / `DETAILED_METRICS` | Foundation §4A.6; matrix §5 |
| Subscription | Store lifecycle separate from effective `FREE`/`PRO` history scope, import/rebuild status and coherent revision | Settings §5; purchase alone cannot expose a partial Pro state |
| Profile claims | Visible `CONFIRMED` and `FADING` claims with receipts; fading marked less clear lately; candidates/retired omitted | Profile §5–§9; no teased candidates |
| Focus/challenge slots | `UNAVAILABLE`, reason `NOT_CONTRACTED`; no generated advice | Home §4–§5 |
| Deletion | `ACTIVE`, `DELETION_PENDING`; revoked credentials cannot read prior state | Foundation §3.3; Settings §7 |

A match response contains independently ready `facts`, `raw_metrics`, `performance`,
`matchup_context`, `insights`, and `role_correction` objects. A finalized comparison and PB
never appear in Stage 1. Raw achieved values may appear while the baseline/history comparison
is deferred. Retry metadata never becomes a durable lifecycle enum.

## Open gates and verification

Trend calibration, Profile calibration, email auth mechanism, recovery verification, Pro depth
ceiling and uncontracted content remain explicit owner gates in the [ledger](IMPLEMENTATION-LEDGER.md).
No production default fills those gaps. Test-only calibration is visibly marked and cannot load
as an approved production artifact.

Phase G must export OpenAPI and versioned golden fixtures for every state required by the goal,
including null versus zero, summary-ready matches, unavailable detail, wait ordering, all six
bootstrap outcomes, per-mode differences, entitlement transitions, deletion and unlinked users.
The local seed makes those states usable without live provider calls. Contract tests must exercise
account isolation, coherent revisions, vocabulary/role boundaries and read-path isolation.

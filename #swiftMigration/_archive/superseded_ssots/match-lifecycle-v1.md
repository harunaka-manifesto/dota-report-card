# Match Lifecycle V1 — ACTIVE SSOT

Status: ACTIVE SSOT
Scope: Match discovery, source validation, analysis, progression ordering,
readiness, retries, recovery, correction, and lifecycle notifications
Last audited: 2026-09-13

This document is the authoritative product contract for how a known match moves
from discovery to a final, visible result. It keeps analytical truth
backstage—validated, reproducible, versioned, and bounded—while allowing the
client to show a clear personal state. It does not prescribe a database,
provider query, queue, API, or Swift architecture.

The [Role Metrics & Personal Baselines V1](role-metrics-and-baselines-v1.md)
SSOT remains authoritative for metric definitions, measured versus N/A/zero
semantics, progression eligibility inputs, rolling baselines, comparisons, and
Personal Bests. This document is authoritative for when those outputs are
available, ordered, frozen, retried, corrected, or notified.

## 1. Purpose and authority

The lifecycle answers:

> What does the product know about this match now, what still needs to happen,
> and when is its result safe to treat as final?

The lifecycle must preserve a useful cached experience without claiming that an
unknown or unvalidated result is complete. A result can be complete even when
one or more applicable metrics are legitimately N/A; READY does not mean that
every metric is numeric.

Authority order:

1. locked decisions in this SSOT and its change history;
2. the Role Metrics & Personal Baselines V1 SSOT for metric meaning;
3. validated immutable provider/source evidence;
4. deterministic processing and acceptance tests;
5. older planning or research documents.

Older material is evidence, not a competing lifecycle contract. If an
implementation contradicts a locked rule, record and fix the contradiction; do
not silently redefine the product.

## 2. Scope

In scope:

- discovery triggers and the promise for missed matches;
- account sync state and per-match lifecycle state;
- durable source checkpoints and provider waiting;
- analysis completion, N/A output, and progression finalization;
- Standard/Turbo bucket isolation and chronological blocking;
- bounded automatic retry, ACTION_REQUIRED, and UNAVAILABLE;
- idempotency, duplicate discovery, concurrent refresh, and account isolation;
- explicit role correction and late provider recovery;
- READY immutability and the distinction between current derived truth and
  append-only celebration events;
- lifecycle push-notification eligibility and acknowledgement behavior; and
- release acceptance behavior for the above.

## 3. Out of scope

This SSOT does not define:

- UI layout, screen architecture, copy, animation, or navigation details;
- Swift or mobile-client architecture, generated DTOs, or local storage design;
- database tables, migrations, queue technology, worker topology, or API routes;
- provider authentication, quotas, vendor-specific pagination mechanics, or
  unvalidated provider enum meanings;
- metric formulas, thresholds, baselines, PB comparison direction, or metric
  versions (see the metrics SSOT);
- subscription, entitlement, or paywall behavior;
- the role-resolution algorithm; or
- the presentation contract for current best-known Personal Records versus the
  append-only celebration history (that belongs in a future Personal Records
  SSOT).

The contract may name an external dependency when its semantic result is
required, but it does not prescribe that dependency's implementation.

## 4. Terms

- **Account** — the product owner scope for one player. Every cursor, batch,
  match entry, progression history, acknowledgement, and notification is
  account-scoped.
- **Provider namespace** — the name/versioned identity space of an upstream
  match source. It prevents IDs from different providers colliding.
- **Provider source match ID** — the provider's stable identifier for one match.
- **Logical source match** — one match identified by
  `provider_namespace + provider_source_match_id`, regardless of how many
  discovery attempts or workers observed it.
- **Account/participant entry** — the account-specific view of a logical source
  match, including the tracked participant and confirmed role intent.
- **Discovery attempt** — one request to find matches not yet known to the
  account. V1 starts attempts on app open, resume, or explicit refresh.
- **Discovery batch** — metadata grouping one discovery attempt and its
  discovered source identities. It is not a match identity and never determines
  progression order.
- **Provider checkpoint** — validated, immutable source evidence sufficient to
  resume or complete a stage. A checkpoint preserves source provenance and
  cannot be replaced by older or less-complete evidence.
- **Chronology key** — `(provider_started_at, provider_source_match_id)`. The
  provider start time is primary; the provider source match ID is the tie-break.
  Missing or untrustworthy chronology is not guessed.
- **Progression bucket** — `STANDARD` for ranked or unranked All Pick, or
  `TURBO` for Turbo. Buckets are separate progression worlds.
- **Effective role** — upstream role input: Carry, Mid, Offlane, or Support.
  Confirmed user intent is authoritative; lifecycle does not infer or override
  it.
- **Applicable output** — an output the current source, mode, role, metric
  version, and match context make applicable. An applicable output must conclude
  as measured or N/A with a legitimate reason before READY.
- **Measured** — a valid measured metric, including a valid numeric zero.
- **N/A** — a metric that cannot be meaningfully calculated from trustworthy
  evidence. N/A is not zero and is not fabricated to hide a processing failure.
- **Lifecycle state** — the durable per-match processing state in Section 7.
- **Retry activity** — attempt count, next-attempt time, failure class, and
  similar metadata layered on WAITING_FOR_PROVIDER or ANALYZING. `RETRYING` is
  not a separate durable lifecycle state.
- **Progression classification** — `STANDARD`, `TURBO`, or `NONE(reason)`.
  Classification is orthogonal to lifecycle state; NONE is not a processing
  failure.
- **Progression-ineligible** — a visible match classification that must not
  contribute to baselines, PBs, or progression ordering, with an explanatory
  reason.
- **Finalized snapshot** — the published derived result for a READY match,
  including the source checkpoint and metric versions used. It is immutable to
  passive enrichment.
- **Current best-known record/index** — the current derived PB/index after
  admitted evidence and explicit corrections. It is distinct from events the
  user has already been shown.
- **Celebration event** — an append-only record that a PB/result celebration was
  emitted or delivered. It is not rewritten when current derived truth changes.
- **Terminal-at-rest** — ACTION_REQUIRED or UNAVAILABLE. Neither retries
  automatically forever; both remain visible and can be manually retried.
- **Acknowledgement** — account-level knowledge that a ready result set has been
  viewed or handled. It survives reinstall/new device; device permission does
  not.

## 5. Invariants

1. **Discovery is bounded.** V1 discovers on app open, app resume, or explicit
   refresh. It makes no always-running or real-time/live-polling promise.
2. **Cached state is useful.** After mandatory splash prerequisites, show the
   cached/home state. Do not block usable prior state on STRATZ availability.
3. **All missed matches are the unit of discovery.** A successful attempt must
   durably record all pages/items before advancing the authoritative cursor.
4. **Chronology is deterministic.** New known matches are ordered oldest to
   newest by the chronology key. Never guess a missing/untrustworthy start time
   or use discovery order as a substitute.
5. **States are orthogonal.** Account sync state, per-match lifecycle state,
   and progression classification are separate dimensions. There is no mega-
   enum and no partial-ready lifecycle state.
6. **READY is complete, not necessarily numeric.** Every applicable output must
   deterministically conclude as measured or legitimate N/A(reason). A match
   can be READY with N/A outputs and can be READY with progression
   classification NONE(reason).
7. **Provider evidence is immutable by provenance.** Before READY, only
   validated newer or more-complete evidence may advance a checkpoint. A stale
   response cannot regress a sufficient checkpoint. After READY, passive
   enrichment is ignored.
8. **Buckets are completely isolated.** STANDARD and TURBO use identical V1
   role/metric definitions and rules, but never share observations, baselines,
   PB indexes, queues, blockers, or progression finalization. Notification
   bundling may span buckets because it does not affect progression truth.
9. **Progression dependencies are chronological per bucket.** A later match may
   finish computation and wait for an earlier unresolved match, but no bucket
   waits on the other bucket.
10. **Failures fail closed.** Unknown provider semantics, malformed or
    insufficient evidence, missing chronology, withdrawn truth, and integrity
    uncertainty never become fabricated values or eligibility.
11. **Retries are bounded.** Transient failures retry automatically only within
    a bounded period. At rest the result is ACTION_REQUIRED or UNAVAILABLE.
12. **At-least-once work has exactly-once observed effects.** Retries, refreshes,
    workers, and notification attempts may repeat internally, but they must not
    duplicate logical history rows, progression observations, PB events, or
    notifications.
13. **Account isolation is absolute.** No account may read or mutate another
    account's cursor, batch, match effect, progression, acknowledgement, or
    notification.
14. **Finalization is reproducible.** READY uses frozen validated source data
    and original metric versions. Passive enrichment cannot change it.
15. **Correction is the explicit exception.** A confirmed role correction may
    replace unpublished derived truth and rebuild affected same-bucket outputs,
    while already-delivered celebration events remain immutable and auditable.
16. **Unknown matches remain unknown.** Matches played while the app is closed
    may remain undiscovered until the next trigger. They do not generate push
    notifications before discovery.
17. **Notifications are lifecycle effects, not processing inputs.** Permission,
    device token, and OS delivery state never affect discovery, analysis,
    progression, or readiness.

## 6. Triggers and discovery

### 6.1 Trigger contract

| Trigger | Required lifecycle behavior |
|---|---|
| App open | Restore cached/home state after mandatory splash prerequisites, then begin an account discovery attempt. |
| App resume | Restore cached state immediately, then begin an idempotent discovery attempt. |
| Explicit refresh | Begin one account/source-coalesced discovery attempt; repeated taps do not create duplicate work. |
| App closed | Continue processing already-known matches on the server. No real-time discovery promise exists. |
| Offline open/resume | Show cached state; mark the latest sync attempt SYNC_ERROR/offline when discovery cannot run. Known server work may continue. |
| Reconnect | Run an idempotent discovery attempt. Do not claim UP_TO_DATE until that attempt establishes it. |

The client may display a simple lifecycle status, but copy/layout are outside
this document. A sync error never rewrites known per-match states or claims
that no matches exist.

### 6.2 Discovering all missed matches

Discovery means finding all source matches missed since the durable account
cursor or equivalent authoritative boundary. The semantic contract is:

1. request or receive a page of source items;
2. validate each item and map it to the composite source identity;
3. durably record every page/item with an accepted, rejected, or terminal
   validation outcome and its resume position;
4. repeat until the provider's authoritative end is reached; and only then
5. advance the authoritative discovery cursor.

An interruption before step 5 resumes from the last durable position and
re-observes items safely. Cursor advancement must never make an unrecorded page
look discovered. Provider pagination style is implementation policy.

### 6.3 Discovery outcomes

Discovery success means the account's attempt reached the authoritative end and
every page/item has a durable accepted, rejected, or terminal validation
outcome. An unresolved malformed or unknown item prevents cursor advancement
and yields `SYNC_ERROR`. `UP_TO_DATE` means the account is caught up to that
completed discovery boundary, whether or not the attempt found new matches; it
does not mean that a future match cannot exist. Offline, timeout, provider
error, or incomplete pagination yields `SYNC_ERROR`, not UP_TO_DATE.

Unknown or malformed source items are not silently accepted as matches. They
follow provider validation/retry rules and remain visible only when a logical
entry can be established without guessing identity.

## 7. Batching and concurrency

- A discovery batch is an operational grouping only. It must never be used as a
  match identity, chronology key, progression key, baseline key, or PB key.
- One provider namespace plus source match ID maps to one logical source match,
  and each account has at most one account/participant entry for that source.
- Concurrent refreshes and manual retries are coalesced or serialized per
  account/source identity. Repeated taps do not add attempts or effects beyond
  the one logical work item.
- Overlapping discovery batches merge by source identity. Batch metadata may
  retain all contributing batch IDs for audit, but the match remains one entry.
- Multiple pending batches still obey per-bucket chronology. A newer batch does
  not jump an older known match merely because it completed first.
- At-least-once internal dispatch is allowed. Every externally observed effect
  is guarded by the logical identity and stable dedupe key appropriate to that
  effect.

## 8. Orthogonal state model

### 8.1 Account sync state

The sync state describes the latest discovery attempt only. It does not
summarize or overwrite known match lifecycle states.

| State | Meaning | Ownership/transition |
|---|---|---|
| `IDLE` | No discovery attempt is currently active or awaiting a result. Cached data may exist. | Account sync controller; initial/resting state. |
| `CHECKING` | An app-open/resume/refresh/reconnect discovery attempt is in progress. | Account sync controller enters on a trigger and leaves on success/failure. |
| `UP_TO_DATE` | The latest complete discovery attempt reached its authoritative end and the account is caught up to that boundary, whether or not it found new matches. | Account sync controller sets only after complete durable discovery. |
| `SYNC_ERROR` | The latest discovery attempt failed, was offline, or did not complete its authoritative pagination. | Account sync controller; known match states remain unchanged. |

`SYNC_ERROR` does not mean no matches exist. It does not turn a READY match
into waiting, hide an ACTION_REQUIRED match, or claim the account is empty.

Nominal account transitions:

| From | Trigger/result | To |
|---|---|---|
| `IDLE`, `UP_TO_DATE`, or `SYNC_ERROR` | open/resume/refresh/reconnect begins | `CHECKING` |
| `CHECKING` | complete discovery reaches end | `UP_TO_DATE` |
| `CHECKING` | offline/error/interrupted/incomplete discovery | `SYNC_ERROR` |
| `SYNC_ERROR` | no trigger yet | `SYNC_ERROR` (cached state remains usable) |

### 8.2 Per-match lifecycle state

| State | Meaning | Allowed retry activity |
|---|---|---|
| `WAITING_FOR_PROVIDER` | No sufficient validated provider checkpoint is available for the next unresolved provider stage, or a bounded transient provider attempt is pending. | `RETRYING` metadata may be layered here. |
| `ANALYZING` | Validated source data is being processed through deterministic analysis or released progression finalization. | `RETRYING` metadata may be layered here. |
| `WAITING_FOR_PRIOR_MATCH` | This match's applicable outputs are computed, but its same-bucket predecessor dependency is unresolved. | No provider retry is implied; a retry may still be recorded if an independent unresolved stage exists. |
| `ACTION_REQUIRED` | Automation exhausted a retryable system/stage failure. User Retry is the next action. | No automatic retry while at rest. |
| `READY` | All applicable outputs deterministically concluded as measured or legitimate N/A(reason), and progression finalization is complete or explicitly ineligible. | Passive provider enrichment cannot reopen it. Explicit correction may reopen affected derived work. |
| `UNAVAILABLE` | The provider/source never supplied trustworthy analyzable truth, withdrew the match, or remained invalid/insufficient through the bounded window. | No automatic retry while at rest; manual Retry may reopen it. |

`RETRYING` is activity/attempt metadata, never a seventh durable state. A
manual Retry reopens ACTION_REQUIRED or UNAVAILABLE at the earliest unresolved
stage and reuses every valid completed checkpoint and completed stage.

### 8.3 Progression classification

| Classification | Meaning | Processing consequence |
|---|---|---|
| `STANDARD` | Ranked or unranked All Pick. | Eligible only for the STANDARD progression bucket when all metrics-SSOT eligibility rules pass. |
| `TURBO` | Turbo. | Eligible only for the TURBO progression bucket when all metrics-SSOT eligibility rules pass. |
| `NONE(reason)` | Unsupported/unknown mode, missing role, integrity-invalid, abandoned/unfinished, or another explicit progression-ineligible reason. | Not a processing failure. It never contributes to progression, but the match can be READY once every applicable output concludes. |

The mode mapping is exact: Standard and Turbo are both eligible and use the
same roles, metric definitions/versions, previous-20 median, five-prior gate,
PB comparison rules, N/A/zero semantics, `duration_seconds >= 600` rule, and
fail-closed integrity policy. The buckets remain entirely isolated.

### 8.4 Ownership

| Concern | Owner of the truth | Must not own |
|---|---|---|
| Account sync | Latest discovery attempt | Known per-match lifecycle or progression history |
| Provider checkpoint | Validated source/provenance boundary | Metric meaning or UI readiness copy |
| Per-match lifecycle | Provider waiting, analysis, retry, terminal state, READY | Cross-account state or metric formulas |
| Progression | Bucket classification, chronology, dependency release, metric SSOT outputs | Other-bucket blockers or notification dispatch |
| Correction | Confirmed effective-role intent and affected derived rebuild | Passive provider enrichment or event retraction |
| Notification | Ready-event eligibility, dedupe, dispatch, acknowledgement | Processing success, permission-dependent analysis, or source truth |

## 9. State transitions

The transition table is semantic; exact worker/queue decomposition is
implementation policy.

| From | Event/condition | To | Required effect |
|---|---|---|---|
| New logical entry | Source identity and account participant are accepted | `WAITING_FOR_PROVIDER` | Retain source identity and begin/resume provider acquisition. |
| `WAITING_FOR_PROVIDER` | Sufficient validated checkpoint is available | `ANALYZING` | Analyze from the earliest unresolved stage; do not refetch completed provider truth. |
| `WAITING_FOR_PROVIDER` | Transient provider failure within bound | `WAITING_FOR_PROVIDER` + retry metadata | Schedule bounded retry and show simple status. |
| `WAITING_FOR_PROVIDER` | No trustworthy source after bound, withdrawal, invalid/insufficient truth, or untrustworthy chronology | `UNAVAILABLE` | Preserve explanation; stop automatic retries; keep manual Retry. |
| `ANALYZING` | Deterministic stage work is running | `ANALYZING` | Repeated stage effects remain idempotent. |
| `ANALYZING` | Transient system/stage failure within bound | `ANALYZING` + retry metadata | Retry earliest failed stage and reuse completed stages. |
| `ANALYZING` | Automation exhausts retryable system/stage failure or a deterministic processing defect is encountered | `ACTION_REQUIRED` | Preserve checkpoint/stage evidence; user Retry is next action. |
| `ANALYZING` | Outputs conclude but same-bucket predecessor is unresolved | `WAITING_FOR_PRIOR_MATCH` | Retain computed outputs and queue chronology dependency. |
| `ANALYZING` | Outputs conclude and no predecessor blocks, or classification is NONE | `READY` | Finalize the bucket snapshot with measured/N/A outputs and progression result. |
| `WAITING_FOR_PRIOR_MATCH` | Predecessor becomes READY or progression-ineligible | `ANALYZING` | Release/finalize oldest to newest in the bucket. |
| `WAITING_FOR_PRIOR_MATCH` | Predecessor becomes UNAVAILABLE and is excluded from the chain | `ANALYZING` | Release/finalize oldest to newest, excluding that predecessor. |
| `ACTION_REQUIRED` | User selects Retry | Earliest unresolved state | Reuse completed checkpoints/stages; do not create a duplicate entry/effect. |
| `UNAVAILABLE` | User selects Retry | Earliest unresolved state | Manual retry may reopen provider or analysis; automatic retry remains bounded. |
| `READY` | Passive provider enrichment | `READY` | Ignore enrichment; do not mutate the finalized snapshot or celebration history. |
| Any pre-READY state | Confirmed role correction | Earliest affected state | Invalidate only unpublished affected outputs and recompute from frozen source/version. |
| `READY` | Confirmed role correction | Reopened affected work, then `READY` | Rebuild same-bucket old/new-role downstream truth; preserve delivered event ledger. |

There is no partial-ready transition. A UI may show progress while a match is
waiting or analyzing, but lifecycle truth is not READY until the full
applicable-output requirement is met.

## 10. Provider waiting and source checkpoints

### 10.1 Checkpoint advancement

Before READY, a provider response can advance the source checkpoint only when it
is validated for the expected account/participant and is newer or more complete
than the retained checkpoint. A stale or older response cannot regress a
sufficient checkpoint. A valid provider checkpoint is retained as immutable
source evidence for downstream retries.

After READY, passive enrichment is ignored. The finalized source checkpoint,
metric versions, progression snapshot, and celebration history remain stable.
An explicit confirmed role correction is a separate, authorized exception.

### 10.2 Provider outcomes

- Missing, malformed, insufficient, withdrawn, or semantically unknown upstream
  data retries within the bounded provider window, then becomes UNAVAILABLE.
- Unknown provider semantics fail closed; the lifecycle never guesses a mode,
  role, chronology, integrity flag, or metric input to reach READY.
- Missing or untrustworthy chronology follows provider retry then UNAVAILABLE.
  The product never invents a timestamp or tie-break.
- When provider acquisition succeeds but internal analysis fails, preserve the
  validated immutable checkpoint and retry analysis from its earliest failed
  stage. Never refetch provider truth solely because downstream analysis failed.
- Stage writes and finalization are idempotent. A repeated provider response or
  worker attempt cannot duplicate a logical observation or result.

### 10.3 Provider success is not readiness

A validated provider checkpoint only makes analysis possible. READY requires all
applicable outputs to conclude as measured or legitimate N/A(reason), then
requires progression finalization or an explicit progression-ineligible
classification. Provider success plus a downstream defect is ACTION_REQUIRED,
not READY and not an excuse to refetch.

## 11. Analysis and readiness

- Independent match analyses may run in parallel. Parallelism must not reorder
  progression finalization or let a later same-bucket snapshot read a missing
  predecessor as if it were final.
- Analysis stages are deterministic against the frozen source checkpoint and
  metric versions. Completed work is reusable after a retry.
- For every applicable metric, emit a measured value or N/A with a legitimate
  reason. A metric may be N/A because a checkpoint, denominator, or required
  telemetry is unavailable; missing information is never converted to zero.
- A valid numeric zero remains zero. N/A observations never enter role/bucket
  baselines, PB indexes, or history counts under the metrics SSOT.
- Unknown/unsupported mode or integrity-invalid source is a visible entry with
  `NONE(reason)`. It may still reach READY when all applicable outputs conclude.
- Abandoned, unfinished, or integrity-invalid matches remain visible with an
  explanatory progression-ineligible reason and never contribute to
  progression.

## 12. Bucket ordering and dependency release

### 12.1 Bucket contract

| Bucket | Included modes | Isolation rule |
|---|---|---|
| `STANDARD` | Ranked All Pick and unranked All Pick | Own chronology, role/metric/version histories, baselines, PB indexes, blockers, and finalization. |
| `TURBO` | Turbo | Own chronology, role/metric/version histories, baselines, PB indexes, blockers, and finalization. |

Both buckets use the identical V1 definitions from the metrics SSOT: Carry 6,
Mid 5, Offlane 4, Support 5; Position 4/5 merged into Support; no Support
Control; previous 20 eligible measured observations; median; five-prior gate;
all-known PB history; strict tie behavior; raw/comparison value semantics;
N/A/zero; `>= 600` seconds; and fail-closed integrity. Only the bucket differs.

The progression identity is:

```text
progression_bucket + effective_role + metric_id + metric_version
```

No identity may omit the bucket. Standard never blocks, updates, or compares
against Turbo; Turbo never blocks, updates, or compares against Standard.

### 12.2 Chronological queue

Within each bucket, sort by `(provider_started_at, provider_source_match_id)`.
An earlier known match that is not yet final can block later matches in that
bucket. Later matches may finish provider acquisition and metric computation,
then remain WAITING_FOR_PRIOR_MATCH. They must not publish a progression
snapshot that depends on an unresolved predecessor.

When the predecessor becomes READY or progression-ineligible, release and
finalize the waiting queue oldest to newest. When a predecessor becomes
UNAVAILABLE, exclude it from the chain and release/finalize oldest to newest.
Cross-bucket work never waits.

### 12.3 Late recovery boundary

A manual recovery of a later-unavailable match follows the late-recovery rule in
Section 14. It is not a reason to reopen already-finalized later matches.

## 13. Retry, ACTION_REQUIRED, and UNAVAILABLE

### 13.1 Retry policy

Transient provider, network, or system failures may retry automatically during
a bounded period. Exact backoff, attempt count, and timing are implementation
policy. The user sees a simple status, not an unbounded retry stream.

After automatic attempts are exhausted:

- use **ACTION_REQUIRED** when the failure is a retryable system or processing
  stage failure and user Retry is the next action;
- use **UNAVAILABLE** when trustworthy analyzable provider/source truth never
  arrived, was withdrawn, or remained invalid/insufficient through the bound.

Both states remain visible. Neither retries automatically forever. One user
Retry action reopens the earliest unresolved stage, reuses valid completed
work, and is coalesced with concurrent retries. UNAVAILABLE may be manually
reopened; it is not a permanent deletion or hidden match.

### 13.2 Failure classification

| Failure | During bound | At rest |
|---|---|---|
| Transient provider/network failure | `WAITING_FOR_PROVIDER` + retry metadata | `UNAVAILABLE` only if trustworthy source never arrives; otherwise continue provider retry. |
| Provider malformed/insufficient/withdrawn/unknown semantics | Provider retry while evidence may recover | `UNAVAILABLE`; no fabricated output. |
| Missing/untrustworthy chronology | Provider retry | `UNAVAILABLE`; never guess ordering. |
| Internal deterministic stage failure after valid checkpoint | `ANALYZING` + retry metadata | `ACTION_REQUIRED`; retain checkpoint and completed stages. |
| Retry request on ACTION_REQUIRED | Resume earliest failed analysis/provider stage | Not a new logical match. |
| Retry request on UNAVAILABLE | Reopen earliest unresolved provider/analysis stage | Not an automatic retry loop. |

## 14. Finalization, immutability, correction, and late recovery

### 14.1 READY and immutable derived truth

READY means:

1. every applicable output deterministically concludes as measured or legitimate
   N/A(reason);
2. the progression classification is recorded, including NONE(reason) where
   applicable;
3. same-bucket chronology dependencies are resolved or explicitly excluded;
4. the finalized snapshot records the source checkpoint and metric versions;
   and
5. all effects are idempotently persisted.

READY is immutable to later passive provider enrichment and future metric
versions. A later metric release does not silently upgrade an old snapshot. An
explicit user role correction is the exception described below and uses the
same frozen source plus the same original metric versions.

### 14.2 Explicit role correction

The latest confirmed role intent is authoritative at finalization. If a
correction arrives after role-dependent analysis but before READY, invalidate
only the unpublished affected outputs and recompute from the frozen source and
original metric versions. If downstream matches are blocked, keep or release
them only after the corrected predecessor finalizes in bucket order. Repeating
the same correction is idempotent.

For a correction such as Support → Carry:

- operate only in the affected progression bucket;
- remove the match from old-role metric histories and PB paths;
- add valid new-role observations supported by the frozen source;
- rebuild chronologically later affected progression snapshots and current PB
  indexes for the old and new roles only;
- leave the other bucket, other roles, and unaffected matches unchanged; and
- preserve the original metric definitions/versions and never fabricate missing
  telemetry.

Already-delivered celebrations and notifications are an immutable append-only
event ledger. They are not retracted and are not re-sent after correction. If
the product exposes event audit, mark affected events superseded/auditable;
current derived UI truth must not continue displaying invalid old truth.

### 14.3 Edge A/L late recovery

For an earlier match A and later matches B/C in one bucket:

1. If A becomes UNAVAILABLE, it ceases blocking the bucket. B/C may finalize
   after their own outputs are complete, excluding A from the progression chain.
2. If A later succeeds through manual recovery, insert A into visible history at
   its actual chronology position.
3. Do not recompute B/C, mutate their baseline/comparison snapshots, or mutate
   historical PB celebration events solely because A recovered late.
4. A's trustworthy eligible observations are evidence for matches finalized
   after its recovery and may update the current best-known record/index when
   their comparison values warrant it.
5. A late recovery never erases, relabels, or backdates a PB celebration the
   user already saw, and never emits a retroactive/backdated celebration.

The future Personal Records SSOT must define how presentation distinguishes the
current best-known record/index from the append-only celebration history. This
does not reopen lifecycle finalization.

### 14.4 Imported or recovered history

All trustworthy eligible imported or recovered historical observations may
contribute to the current best-known PB/index and future comparisons once
admitted under the metrics SSOT. Imports/recoveries never create retroactive
celebration events and never rewrite already-finalized match snapshots.

## 15. N/A and progression-ineligible history

- N/A is a concluded metric state with a reason, not a retry failure and not a
  numeric zero.
- A legitimate zero is retained as numeric zero when inputs and opportunity are
  valid.
- Missing metric telemetry, malformed events, unavailable checkpoints, invalid
  denominators, or invalid metric identity produce N/A for that metric when the
  match itself remains a valid analyzable context.
- Unknown/unsupported mode, missing effective role, abandon/unfinished status,
  or failed integrity produces `NONE(reason)`. NONE is not an error state and
  can coexist with READY.
- A match that is visible but progression-ineligible never contributes to a
  baseline, PB history, current progression index, or dependency chain.
- Provider/source failure that prevents trustworthy analysis is UNAVAILABLE;
  it must not be relabeled as a successful NONE merely to reach READY.
- Missing chronology prevents progression finalization and follows provider
  retry → UNAVAILABLE. The chronology key is never guessed.

## 16. Idempotency and account isolation

### 16.1 Idempotency keys

At minimum, use these logical identities:

| Effect | Identity boundary |
|---|---|
| Logical source match | `provider_namespace + provider_source_match_id` |
| Account participant entry | `account_id + provider_namespace + provider_source_match_id + participant_identity` |
| Progression observation | account participant + progression identity + source match identity |
| PB/current index update | account + `progression_bucket + effective_role + metric_id + metric_version` + source observation |
| Celebration event | account + stable event identity for the source observation/version/effect |
| Ready notification | account + stable dedupe key for the coalesced ready set/batch |

Exact retries, refreshes, overlapping workers, and notification dispatches may
be at-least-once internally. They must produce no duplicate history row,
progression observation, PB event, or logical notification. V1 does not fuzzy-
dedupe distinct provider IDs; distinct IDs remain distinct unless the provider
itself supplies a stable alias contract.

### 16.2 Account isolation

Discovery cursors, batches, source checkpoints, participant entries, lifecycle
states, progression queues, baselines, PB indexes, corrections,
acknowledgements, and notifications are account-scoped. A shared provider match
may have multiple account/participant entries, but one account's role intent,
history, readiness, or notification effect cannot leak into another account.

## 17. Push notifications

V1 push notification is a READY lifecycle effect only.

- Do not notify for transient retries, ANALYZING, WAITING_FOR_PROVIDER,
  WAITING_FOR_PRIOR_MATCH, ACTION_REQUIRED, or UNAVAILABLE.
- A READY-after-pending result may notify when the app is no longer actively
  viewing that result; while foregrounded, update the app directly instead.
- For a discovery batch or coalesced unacknowledged ready set, create at most
  one logical ready notification containing the relevant match IDs and a stable
  dedupe key. Do not intentionally enqueue duplicate or stale notifications.
- In the foreground, update the app directly; a push is not required to show a
  newly READY result.
- If the user foregrounds and views or acknowledges the included result(s)
  before dispatch/delivery, suppress or cancel the notification best effort.
- Recheck relevance when the user opens a delivered notification. OS delivery
  races are possible, but the product must not intentionally re-enqueue a
  duplicate/stale result.
- Permission, token, device, and OS delivery state never affect processing or
  readiness. Account-level readiness and acknowledgement survive reinstall and
  a new device; notification permission remains device-local.
- Matches still unknown because the app was closed cannot emit a V1 push. They
  become eligible for discovery only at the next open/resume/refresh trigger.

## 18. Races and edge cases

| Scenario | Required behavior |
|---|---|
| Offline open with cached READY matches | Render cached state; set latest sync attempt SYNC_ERROR/offline; keep known match states and server work unchanged. |
| Reconnect after offline | Idempotent discovery; UP_TO_DATE only after complete discovery reaches the end. |
| Two refresh taps | Coalesce/serialize per account/source; one logical discovery effect. |
| Refresh overlaps manual Retry | Merge by source identity; resume earliest unresolved stage; no duplicate match/effect. |
| Discovery interrupted mid-pagination | Keep recorded pages/items; resume without duplicate effects; do not advance authoritative cursor early. |
| Stale provider response before READY | Ignore if older/less complete than the validated checkpoint; never regress readiness. |
| Provider success, analysis defect | Keep immutable checkpoint; retry analysis only; after bound ACTION_REQUIRED. |
| Provider never supplies trustworthy truth | Retry while bounded, then UNAVAILABLE; manual Retry remains possible. |
| Unknown provider enum/semantics | Fail closed; retry if recoverable, otherwise UNAVAILABLE or explicit NONE only where the match is otherwise analyzable. |
| Missing chronology | Retry provider; then UNAVAILABLE; never sort by arrival or guessed time. |
| Later match finishes before earlier match | Later match may compute, then waits in WAITING_FOR_PRIOR_MATCH within its bucket. |
| Earlier predecessor READY | Release/finalize oldest-to-newest in that bucket. |
| Earlier predecessor progression-ineligible | Release/finalize oldest-to-newest; predecessor never enters the chain. |
| Earlier predecessor UNAVAILABLE | Exclude it from the chain and release/finalize oldest-to-newest. |
| Earlier match late recovery | Insert it at actual time; do not rewrite later snapshots/events; use it for future admitted comparisons/current index. |
| Role correction during analysis | Latest confirmed role wins; invalidate unpublished affected outputs and recompute from frozen source/version. |
| Role correction after READY | Same-bucket old/new-role downstream rebuild; other bucket/roles unaffected; events immutable/superseded if exposed. |
| Repeated identical correction | No additional work/effects beyond the first logical correction. |
| Standard and Turbo overlap | Independent queues, histories, baselines, PBs, and finalization; no cross-bucket waiting. |
| Unknown/unsupported mode | Visible entry with NONE(reason); can be READY when applicable outputs conclude; never contributes. |
| Abandoned/unfinished/integrity-invalid match | Visible with explanatory progression-ineligible reason; never contributes. |
| App closed when a new match is played | Match may remain unknown until next trigger; no real-time discovery or push promise. |
| Push race with foreground view | Best-effort suppress/cancel; recheck relevance on open; no intentional duplicate. |
| Device notification permission denied | Continue all server processing and account readiness; no notification effect. |
| Same provider match seen for two accounts | Separate account/participant entries and effects; no contamination. |

## 19. Cross-feature dependencies

| Dependency | Lifecycle contract |
|---|---|
| Role Metrics & Personal Baselines V1 | Supplies metric definitions/versions, effective-role boundary, bucket-scoped identity, eligibility, baselines, PB comparisons, N/A/zero rules, and imported/recovered-history behavior. |
| Upstream role resolution | Supplies effective_role; confirmed user role is authoritative. Lifecycle does not independently classify roles. |
| Provider/source adapter | Supplies validated immutable checkpoints, source IDs, chronology, integrity evidence, and provenance. Unknown semantics fail closed. |
| Account/participant ownership | Scopes discovery, correction, progression, acknowledgements, and notifications. UUID/ID knowledge alone is not a substitute for ownership. |
| Persisted report/history consumers | Must treat READY snapshots and prior versioned outputs as contracts; lifecycle does not silently rewrite them for passive enrichment. |
| Future Personal Records SSOT | Defines presentation of current best-known record/index versus append-only celebration history. Lifecycle supplies the immutability boundary. |
| Notification system/OS | Dispatches READY-only logical notifications. Permission/token/device state cannot influence processing. |

No dependency authorizes a provider refetch merely for UI validation, a metric
recalculation under a new version, or a production deployment.

## 20. Acceptance matrix

The following are product acceptance cases. “Contract; test pending” records
the required evidence without claiming that runtime implementation already
exists.

| Acceptance case | Expected behavior | Status |
|---|---|---|
| App open/resume | Cached/home state is usable after mandatory splash prerequisites, then discovery begins. | Contract; test pending |
| Explicit refresh | Discovery runs once per coalesced account/source work item. | Contract; test pending |
| No always-running promise | A match played while the app is closed may remain unknown until the next trigger; no push for unknown matches. | Contract; test pending |
| Offline open | Cached state remains visible; sync is SYNC_ERROR/offline, never falsely UP_TO_DATE. | Contract; test pending |
| Account sync error | SYNC_ERROR does not rewrite known match states or claim no matches exist. | Contract; test pending |
| Complete discovery | All pages/items are durably recorded before cursor advancement; interruption resumes idempotently. | Contract; test pending |
| Duplicate source identity | Same provider namespace + source ID yields one logical match and one account participant entry. | Contract; test pending |
| Standard/Turbo mapping | Ranked/unranked All Pick → STANDARD; Turbo → TURBO; both eligible and isolated. | Contract; test pending |
| Bucket isolation | Standard never blocks/updates/compares against Turbo, and Turbo never blocks/updates/compares against Standard. | Contract; test pending |
| Orthogonal states | Sync state, lifecycle state, and progression classification are independently representable; no mega-enum. | Contract; test pending |
| Retry activity | RETRYING appears only as metadata on WAITING_FOR_PROVIDER or ANALYZING, never as durable truth. | Contract; test pending |
| No partial-ready | READY waits for every applicable measured/N/A output; a numeric value is not required for every metric. | Contract; test pending |
| Legitimate zero/N/A | Valid zero remains zero; missing/invalid metric evidence is N/A(reason), never coerced to zero. | Contract; test pending |
| NONE classification | Unknown mode, invalid integrity, abandon/unfinished, or missing role is visible NONE(reason), not a processing failure; it may still be READY. | Contract; test pending |
| Missing chronology | Retry provider, then UNAVAILABLE; never guess ordering. | Contract; test pending |
| Later match blocked | Later computation may finish but remains WAITING_FOR_PRIOR_MATCH until its same-bucket predecessor resolves. | Contract; test pending |
| Predecessor READY/ineligible | Release/finalize oldest-to-newest in the bucket. | Contract; test pending |
| Predecessor UNAVAILABLE | Exclude predecessor from chain and release/finalize oldest-to-newest. | Contract; test pending |
| Provider success/internal failure | Preserve immutable checkpoint and retry earliest analysis stage; no provider refetch solely for downstream failure. | Contract; test pending |
| Stale provider response | Older/less-complete response cannot regress a validated checkpoint before READY; passive enrichment after READY is ignored. | Contract; test pending |
| Retry exhaustion | Retryable system/stage failure → ACTION_REQUIRED; never-ending auto retries are forbidden. | Contract; test pending |
| Untrustworthy provider truth | Missing/withdrawn/invalid/insufficient truth through bound → UNAVAILABLE; manual Retry remains possible. | Contract; test pending |
| Manual Retry | ACTION_REQUIRED/UNAVAILABLE resumes earliest unresolved stage and reuses completed work; repeated taps are idempotent. | Contract; test pending |
| Role correction during processing | Latest confirmed role intent wins; unpublished affected outputs recompute from frozen source/original versions. | Contract; test pending |
| Role correction Support→Carry | Same-bucket old/new-role histories, later snapshots, and current PB indexes rebuild; other buckets/roles stay unchanged. | Contract; test pending |
| Correction event history | Delivered celebrations/notifications are not retracted or re-sent; current derived truth reflects correction and events may be superseded/audited. | Contract; test pending |
| Late A recovery | Insert A at actual time; do not rewrite B/C snapshots or prior celebrations; A can inform future comparisons/current index without retro celebration. | Contract; test pending |
| Imported/recovered history | Trustworthy admitted observations update current best-known PB/index and future comparisons, never finalized snapshots or retroactive events. | Contract; test pending |
| At-least-once effects | Duplicate workers/refreshes/retries create no duplicate history, progression observation, PB event, or logical notification. | Contract; test pending |
| Account isolation | Cursors, batches, lifecycle, progression, acknowledgements, and notifications cannot cross accounts. | Contract; test pending |
| READY push trigger | Only READY results may create one coalesced logical notification per ready set/batch; retry/action/unavailable states never notify. | Contract; test pending |
| Foreground/notification race | Foreground updates directly; best-effort suppress/cancel before delivery; relevance is rechecked on notification open. | Contract; test pending |
| Notification permission | Denied/missing token/device state does not affect processing; acknowledgement survives reinstall/new device. | Contract; test pending |

## 21. Minimal feature-only development batches

Each batch is a product slice for lifecycle behavior only. It must use stored,
sanitized, deterministic fixtures and no provider calls for acceptance.

### Batch A — Discovery and identity

- Implement trigger semantics, account sync states, durable all-pages-before-
  cursor behavior, source identity, account/participant identity, and
  concurrent refresh coalescing.
- Prove offline/cache behavior, interruption/resume, duplicate discovery, and
  account isolation.
- Out of scope: analysis formulas, UI architecture, subscriptions, and
  notification dispatch.

### Batch B — Orthogonal lifecycle and bounded retry

- Implement the three-dimensional state model, checkpoint waiting, retry
  metadata, earliest-stage resume, ACTION_REQUIRED, and UNAVAILABLE.
- Prove provider success/internal failure, stale response, unknown semantics,
  missing chronology, bounded retry, manual Retry, and no partial-ready state.

### Batch C — Analysis and readiness

- Consume frozen validated source checkpoints and the metrics SSOT; finalize
  measured/N/A outputs, NONE(reason), and visible progression-ineligible
  entries.
- Prove legitimate zero/N/A, unsupported/integrity-invalid handling, and
  deterministic stage idempotency.

### Batch D — Bucket ordering and finalization

- Add STANDARD/TURBO mapping, independent chronology queues, predecessor
  blocking/release, and oldest-to-newest finalization.
- Prove later computation waiting, predecessor READY/ineligible/UNAVAILABLE,
  cross-bucket independence, and READY immutability.

### Batch E — Correction, late recovery, and derived truth

- Add confirmed-role correction during processing and after READY, same-bucket
  old/new-role downstream rebuild, late recovery, imported/recovered evidence,
  current PB/index updates, and immutable event-ledger handling.
- Prove Support→Carry, repeated corrections, Edge A/L, no snapshot rewrite,
  no retraction/resend, and account isolation.

### Batch F — READY-only notification effect

- Add coalesced READY notification identity, dedupe, acknowledgement, best-
  effort suppression, foreground behavior, relevance recheck, and device-local
  permission handling.
- Prove no retry/action/unavailable/unknown-match notifications and no duplicate
  logical notification under at-least-once dispatch.

### Batch G — Lifecycle acceptance gate

- Run every acceptance row with current and historical production-shaped report
  state where a report consumer is involved, plus deterministic lifecycle
  fixtures for all other rows.
- No provider or OpenDota calls are required for lifecycle validation.

## 22. Open decisions

No lifecycle product decision remains open.

Exact retry backoff, attempt count, retention, pagination transport, persistence
technology, provider query shape, and OS scheduling are implementation policy,
not product ambiguity. The future Personal Records SSOT owns presentation of
current best-known records versus append-only celebration history; the lifecycle
immutability rule is already locked.

## 23. Change control

This file must be updated before code when a change affects discovery triggers,
state meaning, readiness, ordering, retry terminality, source checkpoint
semantics, correction/recovery, idempotency, account isolation, or lifecycle
notifications. Changes that affect metric formulas, eligibility, baseline/PB
identity, or metric versions must also update the metrics SSOT and follow its
versioning rules.

Every change must state whether it changes:

- account sync semantics;
- per-match lifecycle states or transitions;
- progression bucket/order/finalization;
- provider/source truth or chronology;
- correction/recovery and event immutability;
- notification eligibility/dedupe; or
- only implementation policy.

Do not use a new client, provider response, batch ID, or metric release to
silently rewrite a persisted READY snapshot. Do not treat a green local test,
an HTTP 200, or a newly generated match as proof that historical lifecycle
contracts remain compatible.

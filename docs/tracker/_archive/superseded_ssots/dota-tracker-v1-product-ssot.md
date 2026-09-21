# Dota Tracker — V1 Product SSOT

**Status:** LOCKED — consolidated product contract

**Scope:** Dota Tracker account, match lifecycle, role resolution, progression, history, Personal Records, Match Detail, and Free/Pro semantics

**Authority:** This document consolidates the seven locked product-concept SSOTs in Asana project `Dota Progression — Product Concepting`, section `Locked — SSOT Final`.

Consolidated source tasks: Match Lifecycle; Onboarding & Cold Start; Role Resolution & Correction; Progress & History; Personal Records; Latest Match Experience; and Free vs Pro Boundary.

This document governs product meaning and user-visible semantic guarantees. It does not define database schemas, API routes, queue topology, provider query shape, mobile architecture, UI layout, or implementation schedules. Existing metric definitions and provider-evidence contracts remain authoritative for the metric registry and formulas; this document governs how those outputs participate in the product.

## 1. Purpose and Scope

Dota Tracker is an ongoing personal-performance tracker for competitive games, starting with Dota. Its core promise is:

> Help the player see themselves and their progression.

The product must preserve analytical rigor backstage and present an understandable personal experience onstage. It measures a player against their own attributable history; it does not reduce performance to a universal score or treat win/loss as a proxy for personal progression.

This SSOT governs:

- app-account and Steam-identity boundaries;
- discovery, processing, readiness, retry, and notification semantics;
- classifier-first effective-role resolution and correction;
- Standard/Turbo history isolation;
- progression observations, baselines, trends, and Personal Bests;
- historical Match Detail semantics;
- Free and Pro entitlement behavior; and
- deterministic rebuild and event-history behavior across features.

It deliberately does not govern:

- screen layout, navigation, visual design, animation, or final copy;
- database, API, queue, storage, or mobile architecture;
- provider request/pagination mechanics or retry timings;
- metric formulas, registry contents, classifier weights, or calibrated thresholds;
- pricing, paywall presentation, or a complete premium feature catalog; or
- higher-order findings/report eligibility beyond the explicitly locked report direction.

## 2. Product Invariants

The following rules are normative and apply across every feature.

1. **Personal progression is separate from win/loss.** The product MUST NOT use outcome, KDA, or an overall score as a substitute for role-specific progression.
2. **No opaque judgment.** V1 MUST NOT present an overall match score, letter grade, composite performance score, arbitrary good/bad-player judgment, or opaque AI verdict.
3. **Standard and Turbo are separate progression worlds.** They MAY use identical metric methodology, but MUST NOT share baselines, trends, PBs, progression observations, queues, blockers, or progression histories.
4. **Progression is role-specific.** Every successfully classified retained match resolves to exactly one of Carry, Mid, Offlane, or Support. Position 4 and Position 5 both map to Support. There is no Unknown progression role.
5. **Classifier-first processing.** Processing MUST NOT wait for role confirmation. A user assertion is authoritative when present; classifier output is authoritative only when no user assertion exists.
6. **No fabricated certainty.** Missing, malformed, unavailable, or insufficient evidence MUST be represented as N/A, an explicit unavailable state, or an explicit ineligible reason. It MUST NOT be silently converted to zero or a synthetic comparison.
7. **Historical comparisons are time-relative.** Match Detail MUST use the same-role, same-mode baseline that existed before that match. A later match MUST NOT make an old historical comparison silently drift.
8. **Canonical methodology is singular.** A canonical history MUST NOT mix incompatible baseline, trend, calibration, or metric definitions. Approved methodology migrations rebuild compatible retained history deterministically.
9. **Current truth and past events are distinct.** Current PB ownership and derived history MAY change after an authorized rebuild; delivered celebrations and notifications remain append-only, auditable events and are not retracted or replayed.
10. **Subscription does not change measurement truth.** Free and Pro use the same canonical processing and methodology for the history each tier is entitled to inspect. Pro adds historical depth, synthesis, progression/achievement exposure, and engagement value—not better accuracy.
11. **Account isolation is absolute.** Cursors, match entries, role assertions, histories, derived state, acknowledgements, and notifications are scoped to the app account and active Steam profile.
12. **Implementation status is not product status.** A locked contract MUST NOT be reported as shipped merely because it is documented; implementation and release status remain separate.

## 3. Core Domain Model

These are product concepts, not a prescribed storage schema.

### 3.1 App account and Steam identity

- **App account:** the persistent product owner scope. Authentication is required before Home; V1 has no guest or local-only progression mode.
- **Authentication method:** Apple, Google, or email may authenticate the same app account. V1 MUST NOT automatically merge accounts or move their subscriptions, purchases, Steam linkage, or progression.
- **Steam identity:** the linked Dota data source, separate from app authentication. An authenticated user MAY explore without Steam, but tracking and Pro purchase require a valid linked Steam ID.
- **Active Steam profile:** an app account has at most one active Steam ID. A Steam ID is normally linked to at most one app account. Former profiles may remain archived, but their analytical state does not carry into a different active profile.

### 3.2 Match and lifecycle concepts

- **Retained match:** a source match stored for the account with enough identity/context to remain visible. A retained match may be progression-eligible, progression-ineligible, processing, or unavailable.
- **Discovery/sync state:** account-level state describing the latest discovery attempt: `IDLE`, `CHECKING`, `UP_TO_DATE`, or `SYNC_ERROR`.
- **Per-match lifecycle state:** processing state: `WAITING_FOR_PROVIDER`, `ANALYZING`, `WAITING_FOR_PRIOR_MATCH`, `ACTION_REQUIRED`, `READY`, or `UNAVAILABLE`.
- **Retry activity:** attempt metadata layered on provider waiting or analysis. `RETRYING` is not a durable lifecycle state.
- **Progression classification:** an independent classification of `STANDARD`, `TURBO`, or `NONE(reason)`. `NONE(reason)` is not a processing failure.
- **READY:** all applicable outputs have concluded as measured or legitimate N/A, and progression finalization is complete or the match is explicitly ineligible. READY does not require every metric to be numeric.

### 3.3 Role and progression concepts

- **Detected role:** the classifier's output and confidence metadata, preserved for QA/calibration.
- **Effective role:** the role used by the product for the match: Carry, Mid, Offlane, or Support. The latest explicit user assertion overrides detected role.
- **Progression bucket:** Standard or Turbo. Each bucket has independent role/metric histories.
- **Metric observation:** one factual, versioned metric result for one retained match, mode bucket, effective role, and metric. A legitimate numeric zero is measured; N/A is not a measured zero.
- **Progression eligibility:** whether the match contributes to its mode × effective role × metric histories. A READY match may be ineligible.
- **History entitlement:** the set of retained eligible observations currently available to a tier or active Steam profile. Free and Pro can derive different current state from different entitled scopes without using different math.

### 3.4 Derived progression concepts

- **Baseline:** the canonical rolling previous-20 median of eligible, measured, same-mode, same-role observations available before the current match, subject to the metric contract's minimum prior-history gate.
- **Baseline at the time:** the baseline used for a historical match's finalized comparison. It is not the user's current baseline.
- **Trend:** a metric-level state derived from movement across the most recent 10 eligible same-mode, same-role observations. States are `Improving`, `Stable`, `Declining`, and `Insufficient History`.
- **Personal Best (PB):** the current best qualifying observation for an eligible role metric within the user's current entitled history and canonical methodology. A PB points to its qualifying source match.
- **Celebration event:** an append-only record that a newly processed match triggered a PB celebration or notification. It is not the PB state itself.

## 4. Match Lifecycle

### 4.1 Discovery and account sync

V1 checks for new matches on app open, app resume, or explicit refresh. It does not promise constant polling or real-time discovery. Matches played while the app is closed MAY remain undiscovered until the next trigger and MUST NOT generate an unknown-match notification.

The account sync state is separate from every known match:

| State | Meaning |
|---|---|
| `IDLE` | No discovery attempt is active. Cached state MAY exist. |
| `CHECKING` | An open/resume/refresh discovery attempt is active. |
| `UP_TO_DATE` | A complete discovery reached its durable boundary, whether or not it found matches. |
| `SYNC_ERROR` | Discovery was offline, interrupted, incomplete, or failed. Known match state remains usable. |

Discovery MUST:

1. find all missed source items in the relevant discovery scope;
2. validate and durably record every item with an accepted, rejected, or terminal outcome;
3. resume interrupted pagination without gaps or duplicate effects; and
4. advance the authoritative cursor only after the durable boundary is reached.

Missing or untrustworthy chronology MUST NOT be guessed. Discovery order MUST NOT substitute for match chronology.

### 4.2 Per-match lifecycle states

| State | Product meaning |
|---|---|
| `WAITING_FOR_PROVIDER` | Sufficient validated provider/source truth is not yet available for the next unresolved stage. |
| `ANALYZING` | Deterministic analysis or released progression finalization is in progress. |
| `WAITING_FOR_PRIOR_MATCH` | Analysis is complete, but an older unresolved match in the same progression bucket must settle first. |
| `ACTION_REQUIRED` | Bounded automatic retries exhausted a retryable internal/stage failure; the user's single Retry action is next. |
| `READY` | All applicable outputs are final as measured or legitimate N/A, and progression is finalized or explicitly ineligible. |
| `UNAVAILABLE` | Trustworthy analyzable provider/source truth never arrived, remained invalid, was withdrawn, or could not support a final result within the bounded process. |

There is no partial-READY lifecycle state. A match remains pending until full applicable analysis is complete. A READY match MAY have legitimate N/A metrics and MAY be progression-ineligible.

### 4.3 Ordering, concurrency, and idempotency

- All missed matches are discovered and processed chronologically oldest to newest for progression correctness.
- Analysis MAY run concurrently. Progression finalization MUST be ordered independently within Standard and Turbo.
- A later same-bucket match waits in `WAITING_FOR_PRIOR_MATCH` until the predecessor is READY, progression-ineligible, or definitively excluded as UNAVAILABLE. The other mode bucket never blocks it.
- One provider source identity plus one account/participant maps to one logical match entry. Overlapping discovery, retries, and worker execution MUST merge rather than duplicate.
- At-least-once internal work MUST have exactly-once logical effects: no duplicate history entry, observation, PB event, or logical notification.

### 4.4 Retry and terminal behavior

- Automatic retries are bounded. Retry timing/backoff is implementation policy, not product meaning.
- A user-facing Retry is one action. It resumes from the earliest failed or unresolved stage and reuses valid completed checkpoints/work.
- `ACTION_REQUIRED` and `UNAVAILABLE` stop automatic retry while at rest but remain manually retryable.
- Manual retry after `UNAVAILABLE` MAY reopen provider or analysis without creating a second match.
- Provider checkpoints are provenance-bound and monotonic before READY. Stale responses MUST NOT regress them.
- A provider success followed by internal failure resumes analysis without unnecessary refetch.

### 4.5 Progression classification and READY

Progression classification is orthogonal to lifecycle state:

- `STANDARD` covers the supported Standard/All Pick progression context.
- `TURBO` covers Turbo progression.
- `NONE(reason)` covers unsupported or unknown modes, abandon/unfinished matches, invalid integrity, missing required classification inputs, or another explicit ineligibility reason.

`NONE(reason)` remains visible and may reach READY once applicable factual outputs conclude. It never contributes a baseline, trend, PB, or progression observation. Provider/source failure that prevents trustworthy analysis MUST remain a processing failure (`ACTION_REQUIRED` or `UNAVAILABLE`), not be relabeled as successful NONE merely to reach READY.

### 4.6 Finalization and notifications

Passive provider enrichment and future routine formula changes MUST NOT silently mutate a finalized READY snapshot. An approved canonical methodology migration or deterministic correction rebuild is the explicit path for recomputing current derived history.

V1 lifecycle push notifications are READY-only:

- no notification for transient retry, `WAITING_FOR_PRIOR_MATCH`, `ACTION_REQUIRED`, or `UNAVAILABLE`;
- a ready set discovered/finished while the app is closed MAY produce one bundled/coalesced logical notification, including matches across buckets;
- foreground updates directly and SHOULD suppress/cancel an undelivered redundant push best effort;
- dedupe is stable across retries, restarts, devices, and overlapping batches; and
- notification permission, token, or device delivery state MUST never affect processing or readiness.

## 5. Onboarding & Cold Start

### 5.1 Entry and account identity

- Brand-new users may see three value-proposition screens. They appear only for brand-new users and are not replayed for returning, reinstalled, logged-out, or Steam-switching users.
- Authentication is required before Home. V1 has no guest mode.
- Apple, Google, and email are multiple methods for one app account. V1 does not automatically merge colliding accounts or move their Steam linkage, subscription, purchases, history, or progression.
- Steam is optional for product exploration, required for actual Dota tracking, and required before Pro purchase.

### 5.2 Steam linking and switching

V1 enforces:

```text
1 app account → 1 active Steam ID
1 Steam ID → 1 app account
```

There is no normal standalone unlink. A user keeps the active Steam profile or switches to another valid target. A successful switch has a 90-day cooldown, including switching back to a previously used identity. Failed validation attempts do not reset the cooldown.

Before switching, the target Steam ID MUST be authenticated and linkable. A Steam ID actively owned by another app account is blocked from normal switching and routed to the separate recovery boundary. Switching is blocked while a historical import or rebuild is non-terminal.

On successful switch:

1. the old Steam profile/history becomes archived;
2. the new Steam ID becomes active;
3. no PB, baseline, achievement, role history, match history, cursor, correction, notification state, or other analytical state carries across;
4. a new Free bootstrap starts; and
5. active Pro entitlement remains attached to the app account, while any new Pro historical acquisition is scoped to the new Steam profile.

### 5.3 Free History and bootstrap

Free History is the permanent base dataset for the linked Steam profile:

```text
Free History = initial bootstrap + every eligible post-link match
```

At first Steam link, bootstrap searches independently within the 90 days before the link date for:

- up to 30 eligible Standard matches; and
- up to 30 eligible Turbo matches.

The cap is per mode, not shared. Standard and Turbo bootstrap searches, histories, baselines, PBs, and minimum-history requirements remain separate.

Bootstrap is server-owned and durable. It continues through app closure, force quit, logout, restart, or reinstall; signing into the same app account resumes the same state. The overall bootstrap becomes terminal only after both mode searches finish and each discovered match is successfully processed or reaches terminal failure. Coverage gaps remain recorded separately.

Product-level bootstrap outcomes MUST distinguish at least:

`NO_STEAM_LINKED`, `DATA_ACCESS_BLOCKED`, `NO_MATCHES_FOUND`, `NO_ELIGIBLE_MATCHES`, `READY`, and `READY_WITH_GAPS`.

These are data/acquisition outcomes, not replacements for per-match lifecycle states, and may differ by mode.

### 5.4 Cold-start presentation semantics

The product MAY render usable Home/history state while bootstrap is unsettled. Processed facts and raw metrics MAY appear progressively. Baseline-dependent state waits for the relevant observations.

A live match arriving while its mode's Free bootstrap is unsettled MAY expose identity, hero, result, effective role when available, raw metrics, and other non-history-dependent facts. Its baseline comparison, PB, achievement consequence, and other history-dependent progression state MUST wait until that mode's Free bootstrap settles, then finalize once in chronological order.

Imported/bootstrap matches MUST NOT produce per-match notification, PB, achievement, baseline-ready, or celebration spam. One idempotent bootstrap-completion event MAY be eligible after the overall bootstrap settles, subject to READY/READY_WITH_GAPS and notification-permission semantics.

### 5.5 Notification timing, data-access recovery, and account deletion

Notification permission is requested only after the user reaches Home and there is contextual value. It is not requested during value-proposition onboarding, authentication, Steam linking, or bootstrap start. Declining permission does not affect tracking or readiness, and a missed bootstrap-completion push is not queued for retroactive delivery after permission is later granted.

If linked Steam data is blocked, retain the link, show a dedicated recovery state, and do not shift the original Free entitlement boundary. After access is restored, recovery is anchored to the original Steam-link date and attempts to restore the original 30 Standard + 30 Turbo bootstrap entitlement plus eligible post-link Free history. Unrecoverable coverage gaps remain explicit.

If access is lost while Pro is active, do not revoke Pro or wipe retained Pro history. Keep the last coherent active state visible, mark new acquisition as blocked, provide recovery guidance, and resume acquisition when access returns. This is a data-freshness problem, not an entitlement change.

Account deletion is a true deletion boundary, distinct from logout, Pro cancellation, switching, or recovery detachment. It invalidates/cancels background work where possible, prevents late results from restoring state, releases Steam linkage, removes account/history/derived state subject to separate retention requirements, and stops future subscription renewal without a prorated refund. A verified recovery flow MAY reclaim a Steam ID from an inaccessible account, but MUST NOT silently merge accounts, subscriptions, purchases, history, PBs, baselines, achievements, or progression.

## 6. Role Resolution & Correction

### 6.1 Effective-role contract

Every retained match that successfully completes classification MUST immediately resolve to exactly one of:

- Carry;
- Mid;
- Offlane; or
- Support, including Position 4 and Position 5.

There is no Unknown, Unresolved, or fifth progression role. Only a structurally unprocessable match may fail classification; that failure belongs to lifecycle/data processing and MUST NOT create an Unknown role.

Classification is classifier-first. Sparse or conflicting evidence that is still sufficient to classify produces the best role with lower confidence rather than waiting for confirmation. Role evidence is behavior-first: lane/early-map position and farm/resource priority are primary; lane relationship supports the decision; support behaviors strengthen Support; hero identity is a weak prior/tiebreaker. Win/loss, KDA, and match outcome MUST NOT influence role classification.

Only low-confidence results proactively ask the user to confirm or correct. The prompt is a shortcut into the same correction flow and is not a prerequisite for finalization. High-confidence results process silently by default.

### 6.2 User assertion precedence

The latest explicit user role assertion is authoritative whether it confirms the classifier's role or changes it:

```text
latest user assertion > classifier output
classifier output, if no user assertion exists → effective_role
```

Classifier reruns MAY update detected-role/confidence metadata but MUST NOT overwrite a user-confirmed effective role. A later user edit replaces the prior assertion.

Every retained match exposes a persistent Edit Role action on Match Detail while sufficient source telemetry remains available for recalculation. If source telemetry is no longer sufficient, the product MUST explain that correction is unavailable rather than fabricating a rebuild.

### 6.3 Correction rebuild

A role correction deterministically rebuilds the corrected match and affected chronologically later histories, baselines, comparisons, and current PB indexes for the old and new roles within the same mode bucket, using frozen source data and the original applicable metric versions. Unrelated roles, metrics, and the other mode bucket remain unchanged.

Corrections during processing use the latest confirmed role, invalidate only unpublished affected work, and preserve bucket ordering. Re-running the same correction over the same corrected match set MUST produce the same result. Delivered celebrations and notifications remain append-only/auditable; they are not retracted or re-sent.

## 7. Progress & History

### 7.1 Scope and isolation

Progression is tracked independently by:

```text
mode bucket × effective role × metric
```

The four roles never share a progression history. Standard and Turbo never share a progression history. A general match feed MAY be chronological across roles, but progression views, metric timelines, baselines, trends, and role summaries MUST use only the matching role and mode bucket.

V1 has no combined all-role progression curve, composite role trend, overall player progress score, grade, rating, percentage, or hidden cross-metric weighting.

### 7.2 Raw observations and baseline

Raw eligible-match observations are the canonical factual record and remain inspectable in chronological order. The canonical baseline is the rolling median of the previous 20 eligible, measured observations for the same metric, effective role, and mode bucket, using only observations before the current match and the active canonical methodology/version.

The metric contract's minimum prior-history gate applies. In the locked V1 contract, at least five prior measured observations are required before a later observation receives a comparable baseline. N/A observations do not enter the baseline window or count toward the gate; legitimate numeric zeroes do.

The current match MUST NOT contribute to its own baseline. A baseline is contextual reference and MUST NOT replace, hide, or normalize away the raw match value.

### 7.3 Trend

The canonical trend horizon is the most recent 10 eligible observations for the same effective role, metric, and mode bucket. A trend state exists only with a complete 10-point window; otherwise the state is `Insufficient History`.

Once eligible, trend states are exactly:

- `Improving`;
- `Stable`;
- `Declining`; or
- `Insufficient History`.

Trend direction is derived from movement of the canonical rolling baseline across the horizon and respects metric polarity. It is not derived from win/loss, isolated recent games, or a raw win streak. Exact meaningful-change thresholds are calibration/versioning policy.

Calendar filters such as 30D, 90D, or monthly reports MAY change what is displayed, but MUST NOT redefine the canonical trend or underlying progression history.

### 7.4 Inactivity, retention, and methodology

Progression is match-based. Time decay, inactivity reset, hard trend expiry, and a separate Progress retention cutoff do not exist in V1. A long break does not weaken history, reset the previous-20 baseline, or alter the 10-match trend horizon. Recency MAY be shown separately without performance meaning.

Progress consumes all progression-eligible observations available under the user's current history entitlement. Free vs Pro owns the entitlement boundary; Progress does not introduce another cutoff.

There is one canonical progression methodology at a time. When an approved baseline, trend, calculation, or materially revised metric definition changes, compatible retained raw observations and derived state are deterministically rebuilt so the canonical history is internally consistent. Historical raw source observations are not rewritten merely because derived calculations changed. If required source telemetry is unavailable for a revised metric, that point becomes unavailable/N/A for the current definition rather than preserving obsolete and current calculations in one canonical trend.

Past celebrations and notifications remain append-only/auditable even when current Progress views reflect a rebuilt methodology.

## 8. Personal Records

### 8.1 Current PB state

Personal Records V1 exposes only the current canonical PB for each eligible role metric. It does not expose a user-facing lineage of every historical PB.

A PB is scoped to the user's current history entitlement and canonical methodology:

- Free users calculate PBs from Free-entitled history;
- Pro may introduce an older recoverable match that becomes the current PB; and
- Pro expiry deterministically falls back to the best qualifying Free-scope source/value.

If no qualifying source remains, the PB is unavailable. A PB always points to the qualifying source match that currently owns it.

The current PB preserves enough context to identify and trace it: achieved value, hero, match date/time, effective role, mode, and source match. The source match is openable when accessible under the current entitlement.

### 8.2 Celebrations and rebuilds

A newly processed eligible match MAY emit one `NEW_PB` event only when it genuinely beats the canonical entitled record immediately preceding that match, using the applicable strict improvement/polarity/tie rules in the metric contract.

Initial bootstrap, historical import, Pro backfill, recovery, role correction, entitlement change, and deterministic methodology rebuilds MAY establish or change current PB state but MUST NOT emit retroactive PB celebrations or notifications. The current PB state and historical celebration/audit events are distinct.

If role correction, entitlement change, late history recovery, or compatible methodology migration changes PB ownership, the current PB updates silently to the best qualifying source. A prior celebration is never retracted or re-sent.

### 8.3 Sharing and interpretation

The current canonical PB is shareable in V1. A share is a timestamped snapshot of the PB as valid under the entitlement and canonical methodology at generation time, including metric/value and lightweight source context. Later corrections, entitlement changes, methodology rebuilds, or PB ownership changes do not retroactively alter or invalidate an already generated share.

PBs MUST NOT imply percentile rank, comparative rank judgment, a composite score, or unsupported causal meaning.

## 9. Latest Match Experience

Match Detail is a factual, metric-level review of one processed match. It is not an overall evaluation.

### 9.1 Minimum semantic contract

For a retained processed match, Match Detail MUST support, where applicable:

- match context;
- the effective role;
- the applicable fixed role/hero metric set;
- each achieved value, including legitimate zeroes;
- baseline-at-the-time comparison for eligible metrics when a valid prior baseline exists;
- an explicit `Baseline Not Established` state when comparison history is insufficient;
- current PB ownership state and any relevant one-time NEW_PB event distinction;
- progression eligibility and a clear reason when the match does not count;
- a persistent Edit Role action while correction is supported; and
- explicit unavailable/N/A states for unavailable individual facts or metrics.

This is a minimum semantic contract, not an exhaustive schema. Additional factual STRATZ-derived context, metrics, or highlights MAY be added later if they do not violate this SSOT. On later visits, PB labeling reflects only whether the match currently owns the canonical PB; a replaced PB does not retain a user-facing “PB at the time” label in V1.

### 9.2 Historical baseline semantics

Each eligible metric compares against the canonical same-role, same-mode baseline immediately preceding that match. Historical wording MUST make this time-relative meaning clear, using terms such as “baseline at the time” or “baseline before this match.” “Current baseline” is reserved for present-day Progress/Home contexts and MUST NOT be used ambiguously for an old Match Detail comparison.

Later matches MUST NOT change the finalized historical comparison. An authorized role correction, canonical methodology migration, or deterministic history rebuild MAY recompute it.

### 9.3 Ineligible READY matches

A READY match may still be progression-ineligible. It remains viewable as a factual match record and shows trustworthy available data. Its unavailable values use explicit N/A states.

An ineligible match MUST clearly indicate that it does not count and why. It receives no baseline comparison, PB evaluation, or progression observation. Exact layout and UI treatment are deferred.

### 9.4 Prohibited interpretation

Match Detail MUST NOT introduce an overall match score, letter grade, composite performance score, arbitrary good/bad judgment, or opaque AI verdict. Effective role is the user-facing role; raw detected role and classifier confidence are not required Match Detail content in V1. After correction, affected role-dependent outputs refresh from the deterministic rebuild; transition/loading UX is deferred.

## 10. Free vs Pro Boundary

### 10.1 Locked Free value

Free is a coherent, useful, ongoing personal-performance tracker. For Free-entitled history, Free includes:

- ongoing tracking of eligible matches;
- the locked bootstrap entitlement plus eligible post-link history;
- role-specific metric histories;
- canonical baselines;
- 10-match metric trends;
- current PBs;
- match-level baseline-at-the-time comparisons;
- separate Standard and Turbo progression;
- a monthly report based on Free-entitled data; and
- achievement display up to the universal Free cap of Level 5.

Free achievement qualification continues underneath the visible Level 5 cap. The cap is an entitlement/display boundary, not a claim that qualification stops.

### 10.2 Locked/directional Pro value

Pro expands the same canonical truth with additional entitled history and richer product value. The current directional list includes:

- deeper historical context and recovered backfill;
- deeper monthly reporting;
- approximately year-scale pattern analysis;
- uncapped achievement levels from the active Pro history;
- weekly recaps;
- challenges or missions;
- richer factual Match Detail highlights/recommendations;
- medals;
- cosmetic or motivational experiences; and
- additional premium synthesis and engagement.

This list is intentionally non-exhaustive and is not a permanent feature matrix. The exact catalog, cadence, packaging, naming, recommendation design, and which directional experiences ship remain open.

### 10.3 Governing monetization principles

1. Free and Pro use identical canonical match processing, role resolution, metric definitions, eligibility rules, baseline/PB calculations, and progression methodology for any match within the applicable entitled history.
2. Pro MUST NOT be framed as more accurate, more trustworthy, or a superior measurement engine.
3. Pro History is Free History plus recoverable historical backfill; there is no separate Pro progression algorithm.
4. On Pro expiry, active Progress, baselines, trends, PBs, records, entitlement-dependent achievement display, and historical views fall back atomically and deterministically to Free-entitled history.
5. Pro-acquired historical data MAY be retained and reused on resubscription. Retention of data does not keep it active in a Free-derived state.
6. A Free match MUST remain a truthful Free-history record even when the user is not subscribed.

## 11. Cross-Feature Rebuild & Entitlement Semantics

### 11.1 Two kinds of state

The product MUST distinguish:

- **Canonical current truth:** the currently derived PB indexes, baselines, comparisons, trends, records, achievements, and entitled historical views.
- **Append-only historical events:** previously emitted/delivered NEW_PB celebrations, lifecycle notifications, bootstrap-completion events, and audit records.

Canonical current truth MAY be rebuilt. Historical events MUST NOT be fabricated, duplicated, retracted, or replayed solely because current truth changed.

### 11.2 Required rebuild behavior

| Trigger | Canonical current truth | Historical event behavior |
|---|---|---|
| Role correction | Rebuild the corrected match and affected later old/new-role histories within the same mode bucket, including baselines, comparisons, trends, and current PB indexes. | Preserve delivered celebrations/notifications; do not re-send or retract. |
| Methodology/metric migration | Recompute compatible retained history under one current methodology; use N/A where required source telemetry is missing. | Preserve prior events as audit history; do not generate retroactive celebrations. |
| Pro activation/backfill | Keep coherent Free state active while import/rebuild runs; activate Pro-derived history, baselines, trends, PBs, records, achievements, and views atomically at a coherent cutoff. | Historical backfill does not create one event per imported match/PB/achievement. At most one product-level Pro-history-ready communication may be eligible under its own rules. |
| Pro expiry | Atomically derive active state from Free-entitled history. Pro-only stored data remains retained but inactive. | No negative PB or downgrade celebration is generated. |
| Pro resubscription | Reuse retained historical data plus newer Free matches; rebuild and activate Pro state atomically. Fetch again only if coverage is genuinely incomplete or recovery requires it. | No retroactive celebration spam. |
| Historical backfill/recovery | Add trustworthy recovered observations at their actual chronology; update current canonical history at the approved coherent checkpoint. | No retroactive PB, achievement, or match-ready events. |
| Previously unavailable history becomes available | The recovered match MAY affect current best-known PBs and future comparisons according to its actual match time. Later already-finalized snapshots remain frozen unless an explicit authorized rebuild applies. | Previously delivered celebrations remain unchanged; no retroactive celebration. |
| Steam switch | Start a new profile-scoped Free bootstrap and separate Pro acquisition; old profile state is archived and does not carry over. | Old profile events remain tied to that profile; new profile has an independent bootstrap lifecycle. |

### 11.3 Atomicity and coherence

When entitlement or historical coverage changes, the product MUST prefer one coherent activation/deactivation checkpoint over exposing progressively mixed state. New live matches may continue processing against the currently active coherent scope while a rebuild runs; they are incorporated into the next deterministic cutoff.

## 12. Canonical UX Semantics

These semantic distinctions must survive visual redesign:

- **“Baseline at the time” / “baseline before this match”** means the historical comparison reference that existed before the match. **“Current baseline”** means the present-day Progress/Home reference.
- **“Does not count toward progression”** MUST be paired with the applicable reason for a READY but ineligible match.
- **N/A** means unavailable or not meaningfully calculable. It is not zero. A legitimate measured zero remains zero.
- **Current PB** means present canonical PB ownership under current entitlement and methodology. **NEW_PB** means a one-time event emitted when a newly processed eligible match set a record against the preceding canonical entitled history.
- **READY** means complete factual processing, not necessarily progression eligibility and not necessarily numeric values for every metric.
- **Free vs Pro** MUST be framed as different history depth, synthesis, achievement exposure, or engagement—not different measurement accuracy.
- **Role** shown to the player is effective role, with Edit Role available while retained source data supports correction. A low-confidence prompt does not mean processing was blocked.
- **Progression** is a set of role/metric signals, not a single overall player judgment.

## 13. Deferred Decisions

The following are intentionally not locked by this V1 SSOT:

- exact Pro historical acquisition mechanism, lifetime/economic ceiling, and coverage economics;
- exact account-recovery verification, fraud controls, support escalation, and exceptional ownership handling;
- automatic account merge or history/subscription migration behavior;
- exact achievement XP, milestone, and qualification definitions beyond the Level 5 Free display cap;
- exact Pro feature catalog, pricing, packaging, paywall UI, report content/cadence beyond the locked Free monthly direction, and additional Free value;
- challenge/mission mechanics, recommendation design, medals, cosmetics, and motivational systems;
- exact UI layout, navigation, copy, animation, and visual treatment of loading, N/A, ineligible, and coverage-gap states;
- classifier scoring weights, calibration, and low-confidence thresholds;
- per-metric meaningful-change thresholds for Improving/Stable/Declining;
- implementation policy such as retry backoff, storage, API/provider query shape, pagination transport, queueing, and OS scheduling;
- career-history visualization and higher-order findings/report eligibility; and
- any metric formula or eligibility change not explicitly locked in the applicable metric contract.

Deferred items MUST NOT be filled by inference merely to make a screen or implementation appear complete.

## 14. Acceptance / Consistency Rules

Future Product, Design, Data, FE, BE, and AI-agent work remains compliant only if all applicable checks below pass.

- [ ] Standard history never changes a Turbo baseline, trend, PB, queue, or progression history, and Turbo never changes Standard equivalents.
- [ ] Every successfully classified retained match has exactly one effective role: Carry, Mid, Offlane, or Support; P4/P5 are Support.
- [ ] A classifier rerun never overwrites the latest explicit user role assertion.
- [ ] Processing does not wait for role confirmation; low-confidence prompting is corrective only.
- [ ] A retained match with sufficient source telemetry always exposes Edit Role.
- [ ] A role correction deterministically moves the match between same-bucket role histories and rebuilds affected downstream state without changing unrelated roles/buckets.
- [ ] Discovery records all discovered items before advancing its cursor and resumes without gaps or duplicate logical effects.
- [ ] Later same-bucket matches cannot finalize baseline/PB comparisons ahead of an older unresolved predecessor; the other bucket is never blocked.
- [ ] READY has no partial-ready variant and may coexist with N/A metrics or `NONE(reason)` progression classification.
- [ ] A provider/source failure is not relabeled as progression ineligibility merely to obtain READY.
- [ ] Automatic retries are bounded; manual Retry resumes the earliest unresolved stage and does not duplicate the match or its effects.
- [ ] A historical Match Detail never silently compares against today's current baseline.
- [ ] A missing baseline produces an explicit Baseline Not Established state, not a synthetic comparison.
- [ ] A READY but progression-ineligible match remains viewable, says that it does not count, and gives the reason.
- [ ] Progress uses previous-20 same-role/same-mode baseline semantics and a complete 10-observation trend horizon.
- [ ] No time decay, inactivity reset, Progress-specific retention cutoff, composite role trend, or overall progress score is introduced in V1.
- [ ] A current PB always points to its qualifying source match under the current entitlement and methodology.
- [ ] Imports, backfills, recovery, entitlement changes, and rebuilds never generate retroactive PB celebrations or notification spam.
- [ ] Pro expiry can change current PBs and trends when their source history is outside Free entitlement, but it does so deterministically and atomically.
- [ ] Free and Pro do not calculate the same match differently merely because of subscription tier.
- [ ] Historical recovery may affect current best-known records and future comparisons, but prior finalized snapshots and delivered events remain frozen unless an explicit authorized rebuild applies.
- [ ] Notification permission/device state never gates processing, readiness, progression, or account state.
- [ ] No product surface introduces a score, grade, composite judgment, or opaque AI verdict prohibited by this SSOT.

## Open SSOT Conflict

None identified after reconciling the seven locked Asana SSOTs and the directly referenced lifecycle, onboarding, and metrics contracts. Older repository wording that conflicts with the locked Asana decisions defers to this master SSOT and the applicable current metric contract.

# Onboarding & Cold Start V1

**Status:** LOCKED — PRODUCT CONTRACT  
**Scope:** Account entry, authentication, Steam linking, initial Free bootstrap, historical access, Pro history activation/deactivation, notification timing, Steam switching, data-access recovery, and account-recovery boundary.

This document is the authoritative V1 contract for Onboarding & Cold Start.

It inherits and must not contradict:

- **Match Lifecycle V1 SSOT**
- **Metrics & Baselines V1 SSOT**

Where those documents define lifecycle, chronology, retry, role correction, progression, metric eligibility, baseline calculations, PB rules, or notification readiness, those definitions remain authoritative.

---

# 1. Core principles

Onboarding must get the player into the product quickly without fabricating analytical certainty.

The system must:

- allow users to understand the product before linking Steam;
- require a persistent app account;
- separate app identity from Steam identity;
- begin useful tracking as soon as Steam is linked;
- bootstrap enough recent history to avoid a completely empty starting experience;
- preserve Standard and Turbo as completely isolated progression buckets;
- distinguish data availability from analytical readiness;
- avoid blocking the product while historical data is being acquired;
- never invent comparisons when insufficient history exists;
- keep subscription entitlement separate from the underlying match facts stored by the system;
- prefer coherent atomic recalculation over exposing partially rebuilt historical state.

---

# 2. Onboarding entry

## 2.1 Brand-new users

A brand-new user sees:

```text
Value Proposition 1
→ Value Proposition 2
→ Value Proposition 3
→ Authentication
```

The exact UI/content of those three screens is outside this contract.

The screens may be completed or skipped.

## 2.2 Onboarding completion

Onboarding is considered complete once the brand-new user finishes or skips the value-proposition screens and reaches authentication/product entry.

The following are separate states and are **not** requirements for onboarding completion:

- app-account creation;
- Steam linking;
- bootstrap start;
- bootstrap completion;
- baseline readiness.

Do not create one global `ONBOARDING_COMPLETE` state that implies all of these have happened.

## 2.3 Returning users

The three value-proposition screens appear only for brand-new users.

They are not replayed for:

- returning users;
- logged-out existing users;
- reinstalled users;
- users switching Steam accounts.

Returning users go directly to the appropriate authentication or product state.

---

# 3. App account

## 3.1 Authentication is mandatory

There is no guest account and no local-only progression mode.

A persistent app account is required before entering Home or other normal product surfaces.

## 3.2 Supported authentication methods

The app may support:

- Sign in with Apple;
- Google;
- email.

These are authentication methods for the **same underlying app account**, not separate account types.

A user may attach multiple authentication methods to one app account for login and recovery.

Example:

```text
App Account A
├── Apple identity
├── Google identity
└── email credential
```

## 3.3 Login-method collision

If a user attempts to attach an authentication identity that is already attached to another app account:

- block the attachment;
- do not automatically merge accounts;
- do not automatically move Steam linkage;
- do not move subscription entitlement;
- do not move purchases;
- do not move progression/history.

Route the user toward the separate account-recovery/support boundary.

Automatic account merging is forbidden in V1.

---

# 4. Steam identity

App identity and Steam identity are separate concepts.

```text
App account
    ↓ links
Steam identity
    ↓ provides
Dota match history
```

Steam is a game-data connection, not the primary app login identity.

## 4.1 Steam is optional for product exploration

An authenticated user may enter Home and navigate the product without Steam linked.

Product surfaces use dedicated unlinked states and may explain/nudge the value of connecting Steam.

The exact unlinked UI is outside this contract.

## 4.2 Steam is required for tracking

Actual Dota tracking cannot begin until Steam is linked.

Linking Steam starts Free bootstrap acquisition.

## 4.3 Steam is required before purchasing Pro

Users cannot purchase Pro until a valid Steam ID has been linked.

An app account with no Steam identity may explore the product but cannot start a Pro subscription.

---

# 5. Steam ownership cardinality

V1 enforces:

```text
1 app account → 1 active Steam ID
1 Steam ID → 1 app account
```

An app account may retain previously linked Steam profiles as archived profiles, but only one may be active.

A Steam ID already actively linked to another app account is not linkable through the normal linking/switching flow.

---

# 6. No normal Steam unlinking

After a Steam identity has been linked, the normal product does **not** expose a standalone “Unlink Steam” action.

Users may:

- keep the existing Steam ID; or
- switch to another Steam ID under the switching contract.

Detaching a Steam ID without replacement exists only inside the dedicated account-recovery flow.

This prevents:

```text
Steam A
→ unlink
→ immediately attach Steam B
```

from bypassing switching controls.

New app accounts that have never linked Steam may naturally remain in the no-Steam state.

---

# 7. Free History

Free History is the permanent base dataset for a linked Steam profile.

It consists of:

```text
initial Free bootstrap
+
all eligible matches from Steam-link date onward
```

Free History remains available regardless of subscription status.

---

# 8. Initial Free bootstrap

## 8.1 Bootstrap scope

At first Steam link, search independently for:

```text
Standard:
up to 30 eligible matches
within up to 90 days before Steam-link date

Turbo:
up to 30 eligible matches
within up to 90 days before Steam-link date
```

The limits are independent.

Maximum intended bootstrap:

```text
30 Standard
+
30 Turbo
```

not 30 shared between them.

## 8.2 Search behavior

For each mode bucket:

```text
start at Steam-link date
→ search backward
→ stop when 30 eligible matches are found
OR
→ stop at 90-day lookback boundary
```

Example:

```text
Standard:
30 eligible matches found within 12 days
→ stop

Turbo:
7 eligible matches found across 90 days
→ bootstrap contains 7 Turbo matches
```

## 8.3 Standard and Turbo isolation

Standard and Turbo:

- use identical progression semantics;
- are completely isolated from one another;
- never share baselines;
- never share PB histories;
- never satisfy one another's minimum-history requirements.

---

# 9. Baseline cold start

Bootstrap history is replayed chronologically.

Baseline readiness remains defined by the Metrics & Baselines SSOT.

V1 onboarding relies on the existing rule that comparison readiness is established independently for:

```text
mode bucket
× role
× metric
× metric version
```

Five valid prior observations are required before a later observation can be compared.

There is no global:

```text
"player has 5 matches"
```

baseline rule.

Example:

```text
Standard Carry metric → READY
Standard Support metric → BUILDING 3/5
Turbo Carry metric → READY
Turbo Support metric → no history
```

All may coexist.

---

# 10. No onboarding role questionnaire

Do not ask users to choose:

- their main role;
- their preferred role;
- their primary role;
- the role they intend to improve.

Roles change over time.

Role assignment comes from actual match data under the role-classification contract.

User role correction remains authoritative where supported by Match Lifecycle.

No onboarding preference may affect analytical role classification or baseline membership.

---

# 11. No onboarding goals questionnaire

V1 does not ask users whether they want to:

- improve;
- climb ranked;
- track records;
- focus on a role;
- receive challenges;
- select metrics.

Initial personalization comes from actual match history.

Challenge/focus preferences belong to their own future product contracts.

---

# 12. Bootstrap presentation semantics

The product does not need to wait for the entire bootstrap before rendering.

During bootstrap:

- Home and other pages remain usable;
- empty/building states may be shown;
- processed match facts may appear as they become available;
- valid raw metrics may populate progressively;
- baseline-building state may populate progressively;
- historical imported matches do not trigger notification spam or historical celebration spam.

UI composition is outside this contract.

---

# 13. Live match during initial bootstrap

A newly played match may become available while its mode's initial bootstrap is still unsettled.

The match itself must not be hidden.

The system may expose immediately:

- match identity;
- hero;
- result;
- effective role when available;
- raw metrics;
- non-history-dependent match details.

However, history-dependent progression for that live match must wait until the **relevant mode's Free bootstrap** reaches terminal state.

History-dependent progression includes at minimum:

- baseline comparison;
- PB determination;
- achievement consequences;
- history-dependent celebration/recognition.

Example:

```text
Standard bootstrap still running
+
new Standard match arrives
→ show match/raw data
→ defer Standard history-dependent finalization

Turbo bootstrap state is irrelevant
```

Once the relevant mode bootstrap settles:

```text
replay settled prior chronology
→ finalize waiting live match once
→ create authoritative comparison/PB/achievement state
→ READY-only notification/celebration may become eligible
```

This avoids provisional false PBs and unnecessary rewriting of finalized live-match snapshots.

---

# 14. Bootstrap terminal state

Overall initial bootstrap becomes terminal only when:

1. the Standard search has finished;
2. the Turbo search has finished; and
3. every discovered bootstrap match is either:
   - successfully processed; or
   - in a terminal failure state.

Temporary retries keep the bootstrap non-terminal.

A terminal failure does not prevent bootstrap completion.

Coverage gaps are persisted separately.

Example:

```text
Standard
29 READY
1 terminal unavailable

Turbo
17 READY

→ bootstrap may finish
→ coverage gap remains recorded
```

“Bootstrap finished” means the acquisition operation settled.

It does **not** mean every historical match was recoverable.

---

# 15. Bootstrap operational ownership

Bootstrap and historical imports are server-owned.

They continue independently of:

- app closure;
- force quit;
- logout;
- device restart;
- reinstall.

Client loss of state must not:

- cancel the job;
- restart the job;
- create duplicate jobs;
- reset discovery cursors.

Signing back into the same app account resumes the same server-side state.

---

# 16. Product-level bootstrap outcome semantics

Operational retry/provider states and product data states are separate.

Temporary provider errors remain lifecycle/job states and should not prematurely become permanent product empty states.

The product must distinguish at minimum:

## `NO_STEAM_LINKED`

The authenticated app account has no linked Steam identity.

## `DATA_ACCESS_BLOCKED`

Steam is linked, but required match data cannot currently be accessed.

This is the state that may trigger guidance around Dota's **Expose Public Match Data** setting.

## `NO_MATCHES_FOUND`

Data access works, but no matches exist in the relevant bootstrap search scope.

## `NO_ELIGIBLE_MATCHES`

Matches were found, but none qualify for the supported progression buckets/rules.

Example:

```text
recent history contains only unsupported/custom/event modes
```

## `READY`

The relevant bootstrap scope settled without a known coverage gap.

## `READY_WITH_GAPS`

The relevant bootstrap scope settled, but one or more known history/data gaps exist.

These outcomes may exist per mode.

Example:

```text
Standard = READY
Turbo = NO_MATCHES_FOUND
```

The account remains usable.

---

# 17. Data-access blocked recovery

If Steam is linked but Dota match data appears inaccessible:

- keep the account linked;
- expose a dedicated recovery state;
- guide the user to enable public match-data exposure in Dota where appropriate;
- do not assume that historical recovery is guaranteed.

After the user confirms access has been restored, recovery is anchored to the **original Steam-link date**.

Attempt to recover:

### A. Original bootstrap entitlement

```text
up to 30 Standard
+
up to 30 Turbo
within the 90 days preceding original Steam-link date
```

### B. Ongoing Free History

```text
every eligible match
from original Steam-link date
through access restoration
```

Ingest whatever the provider actually exposes.

Record unrecoverable coverage gaps.

Then resume normal tracking.

Do not shift the Free-history entitlement boundary forward merely because data access was initially blocked.

---

# 18. Free History after bootstrap

After Steam linking, every eligible supported match from the Steam-link date onward belongs permanently to Free History.

Thus:

```text
Free History
=
bootstrap entitlement
+
post-link eligible history
```

Canceling Pro never removes these matches from Free History.

---

# 19. Pro History

Pro History expands the active dataset beyond Free History.

Conceptually:

```text
Pro History
=
Free History
+
historical backfill from before Steam linking
```

The intended product direction is recoverable historical/lifetime backfill.

The exact provider/economic acquisition ceiling may be configured separately without changing the entitlement semantics defined here.

Historical data successfully acquired for Pro is retained in the database so it does not need to be repeatedly fetched on every resubscription.

---

# 20. Three progression concepts

The product must distinguish:

## 20.1 Free History

```text
bootstrap
+
all eligible post-link matches
```

Used by:

- Free metrics;
- rolling baselines;
- Free PBs;
- Free records;
- Free achievement calculation.

## 20.2 Pro History

```text
Free History
+
historical backfill
```

Used while Pro entitlement is active for:

- expanded historical calculations;
- Pro-derived PBs;
- Pro-derived baselines/metrics where applicable;
- historical views;
- full-history achievement calculation.

## 20.3 Achievement entitlement

Achievement qualification and subscription entitlement are separate.

Eligible matches continue contributing to mathematical achievement progression even when the user is Free.

Subscription controls how much of that progression is exposed.

---

# 21. Achievement entitlement

## 21.1 Universal Free cap

Free achievement display/progression is capped at:

```text
Level 5
```

This entitlement rule is universal across achievements.

Individual achievements may have different:

- XP requirements;
- milestone definitions;
- names;
- qualification logic.

But Free entitlement does not expose achievement levels above Level 5.

## 21.2 Underlying progression continues

The Level 5 cap does **not** stop qualification.

Example:

```text
Free-history mathematical achievement level = 12
Free-visible achievement level = 5
```

The system retains the underlying progress.

## 21.3 Pro removes the cap

When Pro is active:

```text
visible achievement level
=
uncapped level derived from active Pro History
```

Historical backfill may therefore increase the achievement substantially on first Pro activation.

## 21.4 Subscription gaps do not erase earning

Matches played while unsubscribed continue to contribute to the user's Free-history mathematical achievement progression.

When Pro is later reactivated, those matches may contribute to the recomputed uncapped achievement level.

Subscription gates **access/display**, not whether valid play happened.

---

# 22. PB and metric truth versus entitlement

PBs, baselines, metrics, and achievements are derived separately from the currently active history scope.

Example:

```text
Free History PB = 68
Pro History PB = 81
```

While Pro:

```text
active PB = 81
```

After Pro expiry:

```text
active PB = 68
historical Pro state remains stored but inactive
```

If a later Free match produces 82:

```text
Free PB = 82
```

On future Pro activation:

```text
full-history PB also becomes at least 82
```

Entitlement must never prevent newly played Free matches from becoming truthful Free-history records.

---

# 23. Pro purchase and first activation

A linked Steam ID is required before purchasing Pro.

When Pro is purchased:

1. current coherent Free state remains active;
2. Pro historical acquisition begins;
3. historical data is processed separately;
4. live tracking continues;
5. no partially rebuilt Pro state leaks into active product state.

---

# 24. Atomic Pro activation

Historical backfill/recalculation must activate atomically.

While the historical import is running:

- keep the current coherent Free-derived state visible;
- allow new live matches to continue normal Free processing;
- do not progressively rewrite active PBs;
- do not progressively rewrite active baselines;
- do not progressively expose historical achievement jumps;
- do not partially activate historical views.

Before activation, the Pro rebuild must catch up through a deterministic cutoff including relevant new matches that arrived during acquisition.

Then switch together:

```text
PBs
baselines
achievements
historical metrics/views
other Pro history-derived state
```

at one coherent checkpoint.

---

# 25. Concurrent Free bootstrap and first Pro backfill

A user may purchase Pro soon after linking Steam, before Free bootstrap finishes.

Free bootstrap and Pro historical backfill may run concurrently.

Overlapping acquisition must deduplicate shared matches rather than blindly fetching/processing them twice.

The activation sequence is:

```text
UNSETTLED FREE FOUNDATION
↓
coherent Free bootstrap state established
↓
COHERENT FREE STATE / PRO IMPORTING
↓
coherent Pro rebuild ready
↓
COHERENT PRO STATE
```

Even if the historical acquisition finishes before Free bootstrap, first Pro activation waits until the Free foundation is coherent.

Invariant:

> First Pro activation requires both a coherent Free foundation and a coherent Pro historical rebuild.

---

# 26. Partial Pro historical coverage

Pro activation does not require provably complete lifetime history.

If only partial historical coverage can be recovered:

- activate Pro using all recovered history;
- persist coverage/completeness metadata;
- do not claim the data is complete lifetime history unless that can be proven;
- do not block Pro solely because older periods are missing.

If additional history becomes recoverable later:

```text
acquire additional history
→ rebuild Pro-derived state
→ atomically activate revised state
```

---

# 27. Pro completion communication

Historical imports must not generate one notification/celebration per historical PB, achievement, or match.

After atomic Pro activation, the product may produce:

- one Pro-history-ready notification, if notification rules permit;
- one in-app summary explaining that historical state changed.

Example content may summarize:

- PBs discovered;
- achievement levels updated;
- additional history recovered.

Exact copy and UI are outside this contract.

---

# 28. Pro cancellation and expiry

Canceling subscription renewal does not immediately change active entitlement.

Pro remains active until the paid billing entitlement actually expires.

At entitlement expiry, execute an **atomic Pro deactivation**.

---

# 29. Atomic Pro deactivation

At expiry, active state switches coherently from Pro History back to Free History.

Recalculate/activate together:

- active PBs;
- active baselines;
- metrics/state dependent on history scope;
- records;
- achievement state;
- historical views.

Pro-only historical/career surfaces become locked.

Backfilled historical data remains stored.

Do not delete the historical dataset simply because Pro expired.

---

# 30. Resubscription

Resubscription does not repeat the historical backfill if the historical dataset is already retained.

Instead:

```text
stored Pro historical dataset
+
Free-history matches accumulated since expiry
→ recompute Pro-derived state
→ atomic Pro activation
```

Keep showing coherent Free state while this rebuild occurs.

Do not require another full provider historical fetch unless retained coverage is genuinely incomplete or a separate recovery operation requires it.

---

# 31. Loss of Steam data access while Pro is active

If the linked Steam account becomes inaccessible/private after Pro activation:

- do not revoke Pro;
- do not wipe Pro history;
- keep the last coherent active state visible;
- mark new acquisition as blocked;
- expose recovery guidance;
- resume acquisition when access is restored.

This is a **data freshness/acquisition problem**, not an entitlement problem.

Recovered missing data may trigger the appropriate coherent rebuild before changing historical calculations.

---

# 32. Steam switching

Users may switch the active Steam identity.

There is no normal unlink-only operation.

## 32.1 Cooldown

A successful Steam switch starts a:

```text
90-day cooldown
```

The cooldown applies regardless of Free/Pro status.

Switching back to a previously used Steam identity also counts as a switch.

Failed linking/validation attempts do not reset the cooldown.

## 32.2 Linkability validation

Before any switch, the target Steam ID must:

- authenticate successfully;
- be currently linkable;
- not already be linked to another app account.

If the Steam ID is already owned by another app account, normal switching is blocked.

Do not steal or silently transfer ownership.

Route the case to account recovery.

## 32.3 Switching blocked during rebuilds/imports

Steam switching is blocked while a historical import or rebuild is non-terminal.

Switching becomes available only after the active import/rebuild reaches a terminal state.

---

# 33. Successful Steam switch

When a switch succeeds:

1. old Steam profile/history becomes archived;
2. new Steam ID becomes active immediately;
3. no state from the old Steam profile carries into the new profile;
4. new Free bootstrap starts;
5. Pro entitlement, if active, remains attached to the app account;
6. new Pro historical backfill starts for the new Steam profile when applicable.

Separate completely:

- PBs;
- baselines;
- achievements;
- role history;
- match history;
- discovery cursors;
- notification state;
- corrections;
- historical coverage.

Old Steam data remains bound to the old archived Steam profile.

---

# 34. Pro user after Steam switch

If the app account currently has Pro:

- show the new Steam profile's Free/bootstrap state first;
- old Steam Pro-derived state remains archived and inaccessible;
- new Steam Pro historical acquisition runs separately;
- activate the new Pro-derived state atomically only after its coherent checkpoint is ready.

Never temporarily display old Steam analytical state for the new Steam identity.

---

# 35. Notification-permission timing

Do not request notification permission during:

- value-proposition onboarding;
- authentication;
- Steam linking;
- bootstrap start.

Notification permission is requested only after the user has reached Home and there is a clear contextual benefit.

Examples:

- a READY match has appeared;
- bootstrap has completed.

If the user declines notification permission:

- normal product behavior is unaffected;
- tracking continues;
- the app remains fully usable.

---

# 36. Match notification inheritance

Normal match notifications inherit the Match Lifecycle V1 rule:

> Only READY state may trigger a match-ready notification.

Onboarding must not weaken or bypass this rule.

---

# 37. Bootstrap completion notification

## 37.1 One completion event

There is one idempotent Free-bootstrap completion event per Steam-profile bootstrap.

Do not send:

- one Standard completion push;
- one Turbo completion push;
- one push per imported match.

The overall event becomes eligible only when the overall bootstrap terminal-state condition is satisfied.

## 37.2 Eligible outcomes

Normally eligible:

```text
READY
READY_WITH_GAPS
```

Normally not eligible for success-style completion push:

```text
NO_MATCHES_FOUND
NO_ELIGIBLE_MATCHES
DATA_ACCESS_BLOCKED
```

Those states instead update the relevant in-app experience.

## 37.3 Imported-match notification suppression

Imported historical matches do not produce individual:

- match-ready pushes;
- PB pushes;
- achievement pushes;
- baseline-ready pushes;
- historical celebration pushes.

Historical state may still appear normally inside the product.

## 37.4 Permission requirement

If notification permission already exists when bootstrap completes, one bootstrap-ready push may be sent.

If permission does not exist:

- do not queue the completion push for later;
- do not send it retroactively after permission is granted.

Bootstrap completion may instead become the contextual moment for explaining the value of future notifications.

## 37.5 Foreground suppression

If the user is actively using the app and sees the state update directly, the completion push may be suppressed.

## 37.6 Idempotency

Retries, server restarts, reinstall, reopening, or recomputing the same bootstrap must never create duplicate completion notifications.

A legitimate Steam switch creates a new Steam-profile bootstrap and therefore a new independent completion lifecycle.

---

# 38. No findings requirement from bootstrap

The initial 30+30 bootstrap exists to establish useful recent tracking state.

It does not guarantee enough evidence for higher-order findings, behavioral reports, or deep interpretations.

Do not fabricate a finding merely because onboarding completed.

Finding/report eligibility belongs to its own analytical contract.

---

# 39. Account deletion

Account deletion is a true deletion boundary.

It is not equivalent to:

- logging out;
- canceling Pro;
- Steam switching;
- Steam recovery detachment.

Deleting the app account initiates removal of:

- authentication identities;
- active Steam linkage;
- archived Steam profiles;
- retained Free History;
- retained Pro History;
- derived PB/baseline/achievement state;
- notification state;
- recovery metadata;

subject to whatever legal/operational retention requirements are separately defined.

---

# 40. Account deletion and subscription

If the account is deleted while Pro is active:

- account access ends immediately;
- the subscription must be set not to renew at the next billing date;
- the user receives no prorated refund for unused time;
- no further renewal charge should occur after the current billing period.

The exact store/platform mechanism may differ, but the product outcome is fixed.

Deleting the account must not require waiting until the end of the paid period.

---

# 41. Account deletion during background jobs

Account deletion is allowed immediately even while any of the following are running:

- Free bootstrap;
- Pro historical backfill;
- historical rebuild;
- Steam data recovery.

Deletion must:

- mark the account deletion-pending immediately;
- cancel jobs where possible;
- otherwise invalidate their right to commit;
- prevent race-condition late results from restoring deleted state;
- release the Steam linkage as part of the deletion flow.

Deletion outranks background analytical work.

---

# 42. Account-recovery boundary

Detailed account recovery is **not** part of Onboarding & Cold Start V1.

However, V1 defines the boundary it must respect.

## 42.1 Why recovery exists

Because:

```text
1 Steam ID → 1 app account
```

a user who loses access to the app account holding their Steam ID needs a legitimate way to reclaim it.

## 42.2 Recovery capability

A dedicated verified recovery flow may:

- prove ownership of the Steam identity and/or app identity;
- detach a Steam ID from an inaccessible old app account;
- make that Steam ID linkable to the recovered/correct app account.

Recovery is not the normal Steam-switching path.

A verified recovery operation may bypass normal switching restrictions where necessary because it restores ownership rather than changing the player's intended identity.

## 42.3 Recovery must not automatically merge accounts

Recovery must not automatically merge:

- app accounts;
- Steam histories;
- subscriptions;
- purchases;
- PBs;
- baselines;
- achievements;
- progression.

Any future merge/migration behavior requires its own explicit contract.

## 42.4 Out of scope for this SSOT

Not defined here:

- exact identity-verification methods;
- support escalation;
- fraud checks;
- cooldown/waiting periods specific to recovery;
- recovery UI;
- manual-support tooling;
- evidence requirements;
- exceptional ownership disputes.

These require a separate Account Recovery SSOT.

---

# 43. Explicit V1 invariants

The following must remain true:

```text
Authentication is required before Home.
Steam is optional for exploration but required for tracking.
Steam is required before Pro purchase.

Free History =
bootstrap + all eligible post-link matches.

Pro History =
Free History + historical backfill.

Standard and Turbo never contaminate each other.

Baseline readiness is per mode × role × metric × version.

A live match during initial bootstrap may appear,
but history-dependent finalization waits for its mode bootstrap.

Free bootstrap is the permanent Free foundation.

Historical Pro activation is atomic.
Historical Pro deactivation is atomic.

Free achievement visible cap = Level 5.
Underlying achievement qualification continues beyond Level 5.
Pro removes the display cap and uses Pro History.

Subscription controls entitlement, not whether valid matches happened.

No normal Steam unlink exists.
Steam switching is subject to a 90-day cooldown.
One Steam ID belongs to one app account at a time.

No account is automatically merged with another.

Imports are server-owned and survive logout/reinstall.

Temporary provider failure is not a permanent empty-state conclusion.

Historical imports do not spam historical notifications.

Account deletion outranks all background work.
```

---

# 44. Explicitly deferred

The following remain outside this V1 lock:

- exact visual design of onboarding;
- exact value-proposition copy;
- exact login/linking screen UI;
- exact empty-state UI;
- exact Dota public-data instructional UI;
- animation/progress treatment during imports;
- detailed Account Recovery flow;
- fraud/recovery verification mechanisms;
- account-merge product;
- exact historical acquisition economics/cost ceiling;
- whether historical acquisition is literally unlimited lifetime or constrained by a future provider/economic safety ceiling;
- Pro historical trend visualization;
- “all-time baseline” / career-progression visualization;
- Challenge onboarding;
- detailed Achievement definitions and XP curves;
- detailed subscription/paywall UI;
- higher-order Finding/report eligibility.

Changes to any locked behavior above require an explicit SSOT revision before implementation changes land.

---

# 45. Definition of Done for this product contract

Onboarding & Cold Start V1 is considered product-locked when implementation can represent and deterministically test:

1. brand-new versus returning onboarding;
2. mandatory app authentication;
3. multi-method authentication on one account;
4. no automatic account merges;
5. Steam-linked/unlinked product state;
6. independent 30 Standard + 30 Turbo / 90-day bootstrap;
7. Steam-link-date Free-history boundary;
8. per-mode bootstrap terminal state;
9. meaningful empty/access outcomes;
10. live-match deferral during unsettled Free bootstrap;
11. durable server-owned imports;
12. public-data recovery;
13. atomic Pro activation;
14. partial-history Pro activation;
15. concurrent Free-bootstrap + Pro-backfill behavior;
16. atomic Pro expiry fallback;
17. stored-history resubscription;
18. Free achievement Level-5 cap with continued underlying qualification;
19. Steam switching, cooldown, and linkability validation;
20. archived-profile isolation;
21. Pro behavior after Steam switching;
22. contextual notification permission;
23. idempotent bootstrap-completion notification behavior;
24. immediate deletion overriding in-flight jobs;
25. the account-recovery boundary.

No additional Onboarding & Cold Start V1 product decision is required unless implementation reveals a concrete contradiction with Match Lifecycle V1 or Metrics & Baselines V1.
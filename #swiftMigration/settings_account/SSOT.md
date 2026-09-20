# Settings, Account & Subscription — SSOT

**Status:** ACTIVE — feature contract
**Scope:** Ongoing account management after the first successful setup: authentication methods, Steam switching, data-access recovery, subscription purchase/cancellation/expiry/resubscription, notification permission management, account deletion, and the account-recovery boundary.
**Inherits:** [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md).
**Boundary:** first-time authentication, first Steam link and initial bootstrap belong to [`../onboarding/SSOT.md`](../onboarding/SSOT.md).

---

## 1. Purpose

This surface answers:

> Who am I signed in as, which Dota account am I tracking, what am I paying for, and how do I change or end any of it?

It is where irreversible and semi-irreversible actions live. Its defining product requirement is that **every consequence is stated before it happens**.

---

## 2. Authentication methods

- Apple, Google and email are methods attached to **one** app account. Several may be attached for login and recovery.
- Attaching an identity already attached to another app account is **blocked**. V1 MUST NOT merge accounts or move Steam linkage, subscription, purchases, history or progression. The case routes to the account-recovery boundary.
- Automatic account merging is **forbidden** in V1.

---

## 3. Steam identity management

### 3.1 Cardinality and unlinking

```text
1 app account → 1 active Steam ID
1 Steam ID    → 1 app account
```

There is **no normal standalone "Unlink Steam" action**. A user either keeps the active Steam profile or **switches** to another valid target. Detaching without replacement exists only inside the dedicated account-recovery flow.

This prevents `Steam A → unlink → immediately attach Steam B` from bypassing switching controls.

An app account may retain previously linked Steam profiles as **archived** profiles. Only one is active.

### 3.2 Switching preconditions

Before any switch, the target Steam ID MUST:

1. authenticate successfully;
2. be currently linkable;
3. **not** already be linked to another app account.

A Steam ID actively owned by another app account is **blocked** from normal switching and routed to account recovery. Ownership is never stolen or silently transferred.

Switching is **blocked while a historical import or rebuild is non-terminal**. It becomes available only after the active import/rebuild reaches a terminal state.

### 3.3 Cooldown

A **successful** switch starts a **90-day cooldown**, regardless of Free/Pro status. Switching back to a previously used Steam identity also counts as a switch. **Failed linking or validation attempts do not reset the cooldown.**

### 3.4 Consequences of a successful switch

1. the old Steam profile and its history become **archived**;
2. the new Steam ID becomes active immediately;
3. **no state from the old profile carries into the new one** — not PBs, baselines, achievements, role history, match history, discovery cursors, notification state, corrections, or coverage records;
4. a new Free bootstrap starts for the new profile;
5. active Pro entitlement remains attached to the **app account**;
6. new Pro historical backfill starts for the new Steam profile where applicable.

For a Pro user after a switch: show the new profile's Free/bootstrap state first; the old profile's Pro-derived state stays archived and inaccessible; new Pro historical acquisition runs separately; the new Pro-derived state activates atomically only at its coherent checkpoint.

**Old analytical state MUST NEVER be displayed for the new Steam identity, even temporarily.**

---

## 4. Data-access recovery

If the linked Steam account becomes inaccessible or private:

- **keep the link.** Do not unlink, do not revoke anything.
- expose a dedicated recovery state with guidance toward Dota's public match-data setting.
- mark new acquisition as blocked.
- keep the last coherent active state visible and truthful.
- resume acquisition when access is restored.

If Pro is active when access is lost: **do not revoke Pro and do not wipe Pro history.** This is a data-freshness/acquisition problem, **not an entitlement problem**.

Recovery re-anchors to the **original Steam-link date** and attempts to restore the original bootstrap entitlement plus eligible post-link history (see `../onboarding/SSOT.md` §8). The Free-history entitlement boundary MUST NOT shift forward. Unrecoverable coverage gaps remain explicit. Recovered data triggers the appropriate coherent rebuild before changing historical calculations.

---

## 5. Subscription

### 5.1 Purchase

- A **linked Steam ID is required** before purchasing Pro. An app account with no Steam identity may explore but cannot subscribe.
- On purchase: the current coherent Free state remains active; Pro historical acquisition begins; historical data processes separately; live tracking continues; **no partially rebuilt Pro state leaks into active product state**.
- Activation is **atomic**: PBs, baselines, achievement display, historical metrics/views and other Pro-derived state switch together at one coherent checkpoint, after the rebuild has caught up through a deterministic cutoff including matches that arrived during acquisition.
- Partial historical coverage does **not** block activation. Activate with all recovered history, persist coverage metadata, and do not claim completeness that cannot be proven.
- After activation the product MAY produce one Pro-history-ready notification (subject to notification rules) and one in-app summary explaining that historical state changed. It MUST NOT emit one event per historical PB, achievement or match.

### 5.2 Cancellation and expiry

- Cancelling renewal does **not** immediately change entitlement. Pro remains active until the paid billing entitlement actually expires.
- At expiry, execute an **atomic Pro deactivation**: active PBs, baselines, history-scope-dependent state, records, achievement state and historical views all recalculate and switch together to Free History.
- Pro-only historical/career surfaces become locked. **Backfilled historical data remains stored** — it is not deleted because Pro expired.
- **No negative PB or downgrade celebration** is ever generated.
- A PB whose source lies outside Free entitlement legitimately reverts to the best qualifying Free-scope value. This MUST be presented as a change of **scope**, never as a loss of achievement or a decline in performance.

### 5.3 Resubscription

Resubscription does **not** repeat the historical backfill when the dataset is already retained:

```text
stored Pro historical dataset
+ Free-history matches accumulated since expiry
→ recompute Pro-derived state
→ atomic Pro activation
```

Coherent Free state stays visible during the rebuild. A full provider historical fetch is required only if retained coverage is genuinely incomplete or a separate recovery operation demands it.

### 5.4 Framing

Pro MUST be framed as **more history depth, synthesis, achievement exposure and engagement** — never as more accurate, more trustworthy, or a better measurement engine. Free MUST NOT be framed as broken, degraded or incomplete truth.

---

## 6. Notification management

- Permission is first requested only at Home with contextual value (see `../onboarding/SSOT.md` §9). This surface manages it afterwards.
- Declining or revoking permission MUST NOT affect tracking, processing, readiness, progression or account state.
- A missed bootstrap-completion push is **not** queued for retroactive delivery after permission is later granted.
- Account-level readiness and acknowledgement survive reinstall and a new device. **Notification permission is device-local.**
- V1 push notifications are READY-only; there is no per-event notification catalog to configure beyond the platform permission itself.

---

## 7. Account deletion

Account deletion is a **true deletion boundary**, distinct from logout, Pro cancellation, Steam switching and recovery detachment.

Deletion initiates removal of: authentication identities, the active Steam linkage, archived Steam profiles, retained Free History, retained Pro History, derived PB/baseline/achievement state, notification state and recovery metadata — subject to separately defined legal/operational retention.

**Deletion outranks all background analytical work.** It is allowed immediately even while Free bootstrap, Pro backfill, a historical rebuild or Steam data recovery is running. Deletion MUST:

- mark the account deletion-pending immediately;
- cancel jobs where possible, and otherwise invalidate their right to commit;
- prevent race-condition late results from restoring deleted state;
- release the Steam linkage as part of the flow.

If Pro is active at deletion:

- account access ends **immediately**;
- the subscription is set not to renew at the next billing date;
- the user receives **no prorated refund** for unused time;
- no further renewal charge occurs after the current billing period;
- deletion MUST NOT require waiting until the end of the paid period.

The exact store/platform mechanism may differ; the product outcome is fixed.

---

## 8. Account-recovery boundary

Because one Steam ID belongs to one app account, a user who loses access to the app account holding their Steam ID needs a legitimate way to reclaim it.

A dedicated **verified** recovery flow MAY: prove ownership of the Steam and/or app identity; detach a Steam ID from an inaccessible old app account; make that Steam ID linkable to the correct app account. A verified recovery MAY bypass normal switching restrictions, because it restores ownership rather than changing the player's intended identity.

Recovery MUST NOT automatically merge app accounts, Steam histories, subscriptions, purchases, PBs, baselines, achievements or progression. Any future merge or migration behaviour requires its own explicit contract.

**Not defined in V1:** identity-verification methods, support escalation, fraud checks, recovery-specific cooldowns, recovery UI, manual-support tooling, evidence requirements, and exceptional ownership disputes. These require a separate Account Recovery contract.

---

## 9. States

| State | Meaning |
|---|---|
| Signed in, Steam linked, Free | The common state. |
| Signed in, Steam linked, Pro active | Deeper entitled history. |
| Signed in, no Steam | Exploration only. Tracking and Pro purchase unavailable. |
| Auth identity collision | Blocked, with a route to recovery. Never merged. |
| Switch available | Cooldown elapsed, no non-terminal import/rebuild. |
| Switch blocked — cooldown | Days remaining must be knowable. |
| Switch blocked — import/rebuild running | Temporary; resolves on terminal state. |
| Switch blocked — target owned elsewhere | Routes to recovery. Ownership is never taken. |
| Switching in progress | Old profile archiving, new bootstrap starting. |
| Data access blocked | Link retained, acquisition blocked, guidance shown, Pro untouched. |
| Pro purchasing / importing | Free state stays active and coherent. |
| Pro activating | Atomic switch at a coherent checkpoint. |
| Pro active, partial coverage | Legitimate. Completeness is not claimed. |
| Pro cancelled, still active | Entitlement runs to the paid end date. |
| Pro expired | Atomic fallback to Free-entitled state; Pro data retained but inactive. |
| Resubscribing | Rebuild from retained data; coherent Free state visible meanwhile. |
| Notifications allowed / denied | No effect on processing or readiness. |
| Deletion pending | Immediate; jobs cancelled or invalidated. |

---

## 10. Hard invariants

- One active Steam ID per app account; one app account per Steam ID.
- No normal unlink action exists.
- A successful switch starts a 90-day cooldown; failed attempts do not reset it.
- Switching is blocked during a non-terminal import or rebuild, and blocked when the target is owned by another account.
- No analytical state crosses a Steam switch, and old-profile state is never shown for the new identity.
- Pro entitlement belongs to the app account; Pro-derived **history** is scoped to the Steam profile.
- Pro activation and deactivation are atomic; no partially rebuilt state is exposed.
- Losing Steam data access never revokes Pro or wipes Pro history.
- Pro expiry generates no negative or downgrade celebration; scope change is never presented as performance change.
- Pro historical data is retained after expiry and reused on resubscription.
- Pro is never framed as more accurate.
- Notification permission never gates processing, readiness or account state.
- Account deletion is immediate, outranks background work, releases the Steam link, and cancels renewal without a prorated refund.
- Accounts are never automatically merged, by any path including recovery.

---

## 11. Acceptance rules

- [ ] Attaching a colliding auth identity is blocked and routed to recovery, never merged.
- [ ] No standalone unlink action exists anywhere in the product.
- [ ] A switch attempt is blocked with a clear cause for each of: cooldown, non-terminal rebuild, target owned elsewhere, validation failure.
- [ ] A failed switch attempt leaves the cooldown timer unchanged.
- [ ] After a successful switch, no PB, baseline, achievement, role history, match history, cursor, correction or notification state from the old profile is visible.
- [ ] A Pro user after a switch sees the new profile's Free/bootstrap state first, never the old profile's analytics.
- [ ] Data-access loss retains the link, retains Pro, blocks acquisition, and shows recovery guidance.
- [ ] Recovery re-anchors to the original Steam-link date and records unrecoverable gaps.
- [ ] Pro cannot be purchased without a linked Steam ID.
- [ ] Pro activation and expiry switch all dependent state together, with no mixed intermediate visible.
- [ ] Pro expiry that changes a PB presents it as entitlement scope, not as a lost record.
- [ ] Resubscription reuses retained history without a full refetch when coverage is complete.
- [ ] Declining notifications changes nothing about tracking or readiness.
- [ ] Deletion is available during any running job, takes effect immediately, and prevents late results from restoring state.
- [ ] Deletion while Pro is active ends access immediately, stops renewal, and grants no prorated refund.
- [ ] Every irreversible action states its consequences before it is confirmed.

---

## 12. Deferred

- Account-recovery verification methods, fraud controls, support escalation and ownership disputes.
- Any account-merge or history/subscription-migration product.
- Paywall presentation, pricing, packaging and the exact Pro feature catalog.
- Exact Pro historical-acquisition economics and whether backfill is lifetime or capped.
- Per-notification-type preferences beyond the platform permission.

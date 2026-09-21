# Onboarding & Cold Start — SSOT

**Status:** ACTIVE — feature contract
**Scope:** First entry, value proposition, authentication, Steam linking, initial Free bootstrap, cold-start presentation, data-access recovery, notification-permission timing, first Pro activation.
**Inherits:** [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) — identity model, lifecycle, baselines, entitlement, rebuild semantics. This document does not redefine them.
**Boundary:** Ongoing account management after the first successful link (Steam switching, subscription changes, deletion, recovery flows) belongs to [`../settings_account/SSOT.md`](../settings_account/SSOT.md).

## Architecture dependencies

| Concern | Authoritative source |
|---|---|
| Evidence classes and readiness | [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §4A |
| Historical acquisition, the replay horizon, coverage | [`../architecture/MATCH-INGESTION-AND-LIFECYCLE.md`](../architecture/MATCH-INGESTION-AND-LIFECYCLE.md) §3.4, §8 |
| Bootstrap is not a tier-conditional pipeline | [ADR 0004](../architecture/decisions/0004-entitlement-above-the-data-foundation.md) |

---

## 1. Purpose

Get the player into a usable product quickly, without fabricating analytical certainty.

Onboarding must:

- let users understand the product before linking Steam;
- require a persistent app account;
- keep app identity and Steam identity separate;
- begin tracking as soon as Steam is linked;
- bootstrap enough recent history to avoid a completely empty start;
- keep Standard and Turbo isolated from the first match;
- distinguish **data availability** from **analytical readiness**;
- never block the product while history is being acquired;
- never invent a comparison when history is insufficient.

---

## 2. Entry sequence

```text
Value Proposition 1 → 2 → 3 → Authentication
```

- The three value-proposition screens appear **only for brand-new users**. They may be completed or skipped.
- They are **not replayed** for returning users, logged-out existing users, reinstalled users, or users switching Steam accounts. Those users go directly to the appropriate authentication or product state.
- Onboarding is complete once a brand-new user finishes or skips the value-proposition screens and reaches authentication/product entry.

**There MUST NOT be one global `ONBOARDING_COMPLETE` state** implying that account creation, Steam linking, bootstrap start, bootstrap completion or baseline readiness have happened. Those are separate states.

---

## 3. Authentication

- Authentication is **mandatory before Home**. No guest mode, no local-only progression.
- Apple, Google and email are methods for one app account; several may attach to one account for login and recovery.
- If an identity already belongs to another app account: **block the attachment**, do not merge, do not move Steam linkage / subscription / purchases / history / progression. Route to the account-recovery boundary. Automatic merging is forbidden in V1.

---

## 4. Steam linking

- Steam is **optional for exploration**: an authenticated user may enter Home and navigate the product with no Steam linked. Product surfaces use dedicated unlinked states and may explain the value of connecting.
- Steam is **required for tracking**. Linking starts Free bootstrap acquisition.
- Steam is **required before purchasing Pro**.
- Cardinality and the absence of a normal unlink action are defined in the foundation SSOT §3.2.

---

## 5. Initial Free bootstrap

### 5.1 Scope

At first Steam link, search **independently** per mode:

```text
Standard: up to 30 eligible matches, within up to 90 days before the Steam-link date
Turbo:    up to 30 eligible matches, within up to 90 days before the Steam-link date
```

The caps are **per mode, not shared**. Maximum intended bootstrap is 30 + 30, never 30 split between them.

Search behaviour per bucket: start at the Steam-link date, search backward, stop at 30 eligible matches **or** at the 90-day boundary, whichever comes first. A mode may legitimately end up with fewer (7 Turbo matches across 90 days is a valid result).

### 5.2 Ownership and durability

Bootstrap and historical imports are **server-owned**. They continue through app closure, force quit, logout, device restart and reinstall. Client state loss MUST NOT cancel the job, restart it, create duplicates, or reset discovery cursors. Signing back into the same app account resumes the same server-side state.

### 5.3 Terminal state

Overall bootstrap becomes terminal only when:

1. the Standard search has finished, **and**
2. the Turbo search has finished, **and**
3. every discovered bootstrap match is either successfully processed or in a terminal failure state.

Temporary retries keep bootstrap non-terminal. A terminal failure does **not** prevent bootstrap completion. Coverage gaps are persisted separately.

"Bootstrap finished" means the acquisition operation settled. It does **not** mean every historical match was recoverable.

### 5.4 Product-level outcomes

Operational retry/provider states and product data states are separate. A temporary provider error MUST NOT prematurely become a permanent empty state.

| Outcome | Meaning |
|---|---|
| `NO_STEAM_LINKED` | The authenticated account has no linked Steam identity. |
| `DATA_ACCESS_BLOCKED` | Steam is linked, but required match data cannot currently be accessed. This is the state that may guide the user to Dota's **Expose Public Match Data** setting. |
| `NO_MATCHES_FOUND` | Data access works; no matches exist in the bootstrap search scope. |
| `NO_ELIGIBLE_MATCHES` | Matches exist, but none qualify for the supported progression buckets/rules (e.g. only custom/event modes). |
| `READY` | The scope settled with no known coverage gap. |
| `READY_WITH_GAPS` | The scope settled, but one or more known history/data gaps exist. |

These outcomes exist **per mode**. `Standard = READY` with `Turbo = NO_MATCHES_FOUND` is a valid, usable account state.

### 5.5 Bootstrap evidence classes

Bootstrap acquires matches in two evidence classes, and they do **not** have the same reach ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §4A).

| # | Rule |
|---|---|
| BE-1 | Bootstrap MUST acquire **summary-class** evidence for every match in scope. This is what makes the account non-empty, gives every match a hero, result, role and scoreboard, and lets History and Home work immediately. |
| BE-2 | Bootstrap MUST attempt **replay-class** evidence for matches in scope. It is **not optional**: fourteen of the twenty role metrics are replay-class, so a summary-only bootstrap produces a history in which most metrics are N/A, no baseline reaches its 5-prior gate, and no trend reaches its 10-point window. |
| BE-3 | **The fresh-match enrichment route cannot serve the whole bootstrap window.** Bootstrap looks back up to 90 days; replay availability for on-demand processing expires earlier, and its exact edge is **UNKNOWN** ([`../architecture/PROVIDER-CAPABILITIES-AND-ROUTING.md`](../architecture/PROVIDER-CAPABILITIES-AND-ROUTING.md) §7.3, open test T-2). Replay-class evidence for older bootstrap matches must come from a historical source that already holds it. |
| BE-4 | Bootstrap matches for which replay-class evidence cannot be obtained are `REPLAY_UNAVAILABLE`. They are **valid, complete, viewable matches** with their replay-class metrics as N/A. They are **not** failures and **not** coverage-blocking on their own. |
| BE-5 | Replay-class coverage gaps in the bootstrap window MUST be recorded as **coverage gaps** (§5.3, §4A.6), which is what `READY_WITH_GAPS` exists to express. They MUST NOT be silently treated as "the player did not play then". |
| BE-6 | Bootstrap acquisition is **identical for Free and Pro**. Pro may extend historical **depth** beyond the Free window; it does not change how the Free window is acquired ([ADR 0004](../architecture/decisions/0004-entitlement-above-the-data-foundation.md)). |
| BE-7 | Bootstrap is **background, low-priority work**. It MUST NOT delay any user's newly completed match, including the bootstrapping user's own ([`../architecture/SCALING-RELIABILITY-AND-OPERATIONS.md`](../architecture/SCALING-RELIABILITY-AND-OPERATIONS.md) §2). |
| BE-8 | Bootstrap MUST NOT block onboarding. The product is navigable throughout (§6). |

**Product consequence worth stating plainly:** a freshly bootstrapped account may reach baseline readiness at **different times for different metrics**, because the six summary-class metrics have complete coverage while the fourteen replay-class ones may not. This is an honest outcome shown through the existing baseline-building states — it is not a defect, and it MUST NOT be explained to the user in backend terms.

---

## 6. Cold-start presentation semantics

- The product does **not** wait for the whole bootstrap before rendering. Home and other pages remain usable during bootstrap.
- Processed match facts and valid raw metrics MAY populate progressively. Baseline-building state MAY populate progressively.
- Baseline-dependent state waits for the relevant observations. Baseline readiness is per `mode × role × metric × version` — never global.
- Imported/bootstrap matches MUST NOT produce per-match notification, PB, achievement, baseline-ready or celebration spam.

### 6.1 Live match during unsettled bootstrap

A newly played match may arrive while its mode's bootstrap is still unsettled. **The match MUST NOT be hidden.**

The product MAY immediately expose: match identity, hero, result, effective role when available, raw metrics, and other non-history-dependent facts.

> This rule is the original instance of the pattern now generalised as the two-stage contract in [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §4A.3: **show the facts immediately, defer the history-dependent finalization.** A live match during an unsettled bootstrap has *two* reasons to defer — its own evidence may still be arriving, and its mode's history has not settled. Both must be satisfied before it finalizes.

History-dependent progression for that match MUST wait until **that mode's** Free bootstrap reaches terminal state. History-dependent includes at minimum: baseline comparison, adjusted expectation and performance state, PB determination, achievement consequences, and history-dependent celebration.

The other mode's bootstrap state is irrelevant to it.

Once the relevant bootstrap settles: replay the settled prior chronology, finalize the waiting live match **once**, create authoritative comparison/PB/achievement state, and only then allow a READY-only notification or celebration.

This avoids provisional false PBs and avoids rewriting finalized live-match snapshots.

---

## 7. No onboarding questionnaires

V1 MUST NOT ask the user to declare:

- their main / preferred / primary role, or the role they intend to improve;
- whether they want to improve, climb ranked, track records, focus on a role, receive challenges, or select metrics.

Roles come from actual match data under the role-classification contract; user correction remains authoritative. No onboarding preference may affect analytical role classification or baseline membership. Initial personalization comes from actual match history.

(A user-declared preferred role is a deferred P1 decision — see `../profile/SSOT.md`.)

---

## 8. Data-access blocked recovery

If Steam is linked but Dota match data appears inaccessible:

- keep the account linked;
- expose a dedicated recovery state;
- guide the user to enable public match-data exposure where appropriate;
- do not assume historical recovery is guaranteed.

After the user confirms access is restored, recovery is anchored to the **original Steam-link date**, and attempts to recover:

1. the original bootstrap entitlement (up to 30 Standard + 30 Turbo within the 90 days preceding the original link date), and
2. every eligible match from the original Steam-link date through access restoration.

Ingest whatever the provider actually exposes; record unrecoverable coverage gaps; then resume normal tracking.

**The Free-history entitlement boundary MUST NOT shift forward** merely because data access was initially blocked.

---

## 9. Notification permission timing

Permission MUST NOT be requested during value-proposition onboarding, authentication, Steam linking, or bootstrap start.

It is requested only **after the user has reached Home and there is clear contextual benefit** — for example a READY match has appeared, or bootstrap has completed.

If the user declines: normal product behaviour is unaffected, tracking continues, the app remains fully usable.

---

## 10. Bootstrap completion event

- There is **one idempotent** Free-bootstrap completion event per Steam-profile bootstrap. Never one per mode, never one per imported match.
- It becomes eligible only when the overall bootstrap terminal condition is satisfied.
- Normally eligible outcomes: `READY`, `READY_WITH_GAPS`.
- Normally **not** eligible for a success-style push: `NO_MATCHES_FOUND`, `NO_ELIGIBLE_MATCHES`, `DATA_ACCESS_BLOCKED`. Those update the in-app experience instead.
- If notification permission does not exist at completion, the push MUST NOT be queued or sent retroactively after permission is later granted. Bootstrap completion MAY instead be the contextual moment to explain the value of notifications.
- If the user is actively in the app and sees the update directly, the push MAY be suppressed.
- Retries, server restarts, reinstalls, reopening and recomputation MUST NOT create duplicate completion notifications. A legitimate Steam switch starts a new profile bootstrap and therefore a new independent completion lifecycle.

---

## 11. First Pro activation from a cold start

A user may purchase Pro soon after linking, before Free bootstrap finishes.

- Free bootstrap and Pro historical backfill MAY run concurrently; overlapping acquisition MUST deduplicate shared matches.
- While historical import runs: keep the current coherent Free-derived state visible; let new live matches continue normal Free processing; do **not** progressively rewrite active PBs, baselines, achievement levels or historical views.
- Activation sequence:

```text
UNSETTLED FREE FOUNDATION
→ coherent Free bootstrap state established
→ COHERENT FREE STATE / PRO IMPORTING
→ coherent Pro rebuild ready
→ COHERENT PRO STATE
```

**Invariant:** first Pro activation requires both a coherent Free foundation **and** a coherent Pro historical rebuild, even if the historical acquisition finishes first.

- Pro activation does **not** require provably complete lifetime history. Activate with all recovered history, persist coverage metadata, do not claim completeness that cannot be proven, and do not block Pro because older periods are missing.
- After atomic activation the product MAY produce one Pro-history-ready notification (if notification rules permit) and one in-app summary explaining that historical state changed. It MUST NOT emit one event per historical PB, achievement or match.

---

## 12. No findings requirement from bootstrap

The 30+30 bootstrap exists to establish useful recent tracking state. It does **not** guarantee enough evidence for higher-order findings, behavioural reports or deep interpretation. A finding MUST NOT be fabricated merely because onboarding completed.

---

## 13. Cold-start maturity expectations

What a new linked account can honestly show, by eligible-match count in one bucket (see `../profile/SSOT.md` for the full maturity ladder):

| Eligible matches | Honest content |
|---|---|
| ~5 | Header facts; heroes played with counts; roles seen with counts; baseline-building status. No claims, no tags, no form, no PBs. |
| ~20 | Role lean in counts ("Mostly Carry so far"); most-played heroes; first PBs possible on frequently measured metrics. |
| ~30–50 | Role shape and hero-pool reads become possible; first trends once 10 eligible trend points exist. |

A freshly bootstrapped account (30 per bucket) will frequently **not** reach the sample gates that history-dependent insight cards require. That is expected, not a defect.

---

## 14. Edge cases

| Case | Required behaviour |
|---|---|
| User skips all value-prop screens | Proceed to authentication. Skipping is not a failure state. |
| User authenticates, never links Steam | Full navigation with `NO_STEAM_LINKED` states. Pro purchase blocked. |
| Bootstrap finds 30 Standard, 0 Turbo | `Standard = READY`, `Turbo = NO_MATCHES_FOUND`. Account fully usable. |
| Bootstrap finds only custom/event modes | `NO_ELIGIBLE_MATCHES`. Not an error, not an empty account. |
| One bootstrap match terminally fails | Bootstrap may still complete; coverage gap recorded separately. |
| App killed during bootstrap | Server job continues; reopening resumes the same state; no duplicate job. |
| New match arrives mid-bootstrap | Show the match and its raw facts; defer its history-dependent finalization to that mode only. |
| Data access blocked at first link | `DATA_ACCESS_BLOCKED` recovery state; link retained; entitlement boundary unchanged. |
| Permission declined at Home | No effect on tracking, readiness or account state. |
| Pro purchased during bootstrap | Concurrent acquisition with dedupe; Pro activates only after both foundations are coherent. |

---

## 15. Hard invariants

- Authentication is required before Home; there is no guest mode.
- Steam is optional for exploration, required for tracking, required before Pro purchase.
- Bootstrap caps are 30 Standard **and** 30 Turbo, independent, within 90 days before the link date.
- Standard and Turbo never satisfy one another's minimum-history requirements.
- Free History = bootstrap + all eligible post-link matches, permanently.
- A live match during unsettled bootstrap appears immediately but defers history-dependent finalization for its own mode only.
- Imports never produce per-match notifications, PBs, achievements, baseline-ready events or celebrations.
- There is exactly one idempotent bootstrap-completion event per Steam-profile bootstrap.
- Notification permission is requested only at Home, with contextual value.
- No role or goals questionnaire exists.
- Temporary provider failure is never presented as a permanent empty-state conclusion.
- The Free-history entitlement boundary is anchored to the original Steam-link date and never shifts forward.
- Bootstrap acquires both summary-class and replay-class evidence; it is not a summary-only import.
- Replay-class coverage gaps in the bootstrap window are recorded as coverage gaps, never as matches not played.
- A bootstrap match without replay-class evidence is a valid match with N/A replay metrics, never a failure.
- Bootstrap acquisition is identical for Free and Pro; Pro extends depth, not mechanism.
- Bootstrap never delays any user's newly completed match, including the bootstrapping user's own.
- Metric-level baseline readiness may legitimately differ by evidence class, and is never explained to the user in backend terms.

---

## 16. Explicitly deferred

- Exact value-proposition copy and content; exact visual design of onboarding, login, linking, empty states and the public-data instructions.
- Progress/animation treatment during imports.
- Detailed account-recovery flow, verification methods and fraud controls.
- Account-merge product.
- Exact historical-acquisition economics and whether Pro backfill is literally lifetime or capped.
- Paywall UI and subscription presentation.
- Challenge onboarding; achievement definitions and XP curves.

---

## 17. Acceptance rules

- [ ] Value-proposition screens appear for brand-new users only and are never replayed.
- [ ] No single `ONBOARDING_COMPLETE` flag conflates account, Steam, bootstrap and baseline readiness.
- [ ] A colliding auth identity is blocked, never merged.
- [ ] An authenticated user with no Steam can reach and navigate Home.
- [ ] Bootstrap searches 30 Standard and 30 Turbo independently within 90 days.
- [ ] Bootstrap survives force quit, logout, restart and reinstall without duplicating or resetting.
- [ ] Bootstrap is terminal only after both searches finish and every discovered match is processed or terminally failed.
- [ ] All six product-level bootstrap outcomes are representable, per mode.
- [ ] Bootstrap attempts replay-class evidence, not only summary-class.
- [ ] A bootstrap match whose replay evidence is unobtainable is viewable, counted, and shows N/A — not zero — for its replay-derived metrics.
- [ ] Replay-coverage gaps inside the bootstrap window produce `READY_WITH_GAPS`, not `NO_MATCHES_FOUND`.
- [ ] A Free and a Pro account bootstrap the same Free window by the same mechanism.
- [ ] A large bootstrap never delays a freshly completed match for any user.
- [ ] A live match during unsettled bootstrap shows its facts and defers only its history-dependent state, for its own mode.
- [ ] No per-match notification/PB/celebration is emitted for imported matches.
- [ ] Exactly one idempotent bootstrap-completion event exists, and it is not queued for later permission grants.
- [ ] Notification permission is never requested before Home.
- [ ] No role or goals questionnaire is presented.
- [ ] Data-access recovery re-anchors to the original Steam-link date and records unrecoverable gaps.
- [ ] First Pro activation waits for a coherent Free foundation and activates atomically.

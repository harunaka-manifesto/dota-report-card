# Settings, Account & Subscription — Design Requirements

Derived from [`SSOT.md`](SSOT.md) and [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md).

---

## 1. Page role

This is where the player manages who they are to the app, which Dota account it watches, and what they pay for. Almost everything here is consequential and some of it is irreversible.

A player should leave able to **make the change they came for**, having **understood what it costs them** — or able to walk away knowing why they can't do it yet.

---

## 2. Primary JTBD / user needs

**Primary**

- When I need to change which Dota account is tracked, I want to understand exactly what I'll lose before I commit, so I don't destroy my history by accident.
- When I'm deciding about Pro, I want to know what it actually adds, so I'm not paying for a vague promise.
- When I want to leave, I want to delete my account without a fight.

**Secondary**

- When the app can't read my match data, I want to know how to fix it.
- When something I expected has changed (my records moved, my history got shorter), I want to know it was my subscription and not my play.

---

## 3. Questions this page must answer

- Which app account am I signed in as, and how?
- Which Steam account is being tracked?
- Can I change it? If not, why not, and when can I?
- What exactly happens to my data if I switch?
- What am I paying for, and what changes if I stop?
- Why did my records/history change?
- Why can't the app see my matches?
- How do I delete everything?

---

## 4. Entry points & exits

**Entry**
- Main navigation / Profile header
- A blocked action elsewhere ("connect Steam to buy Pro")
- A data-access-blocked state on Home or History
- A Pro-gated surface

**Exit**
- → Steam switch flow
- → data-access recovery guidance
- → purchase / manage subscription (platform)
- → account-recovery boundary
- → account deletion confirmation
- → back, unchanged

---

## 5. Proposed information architecture

```text
P0 — current state: app account, auth methods, Steam account, subscription
P0 — Steam identity management (switch, and why it's blocked when it is)
P0 — subscription state and management
P1 — data-access health and recovery
P1 — notifications
P2 — legal / support / about
P2 — account deletion (present, findable, not hidden — but not adjacent to routine settings)
```

Two rules:

- **State before action.** What is true now precedes what can be changed.
- **Destructive actions are separated** from routine ones. Findable, never accidental.

Nothing else about order is fixed.

---

## 6. Content & data available

| Content / datum | Meaning | Availability | Notes |
|---|---|---|---|
| App account + auth methods | Apple / Google / email attached | Always | Multiple methods, one account |
| Active Steam identity | The tracked Dota account | When linked | One active at a time |
| Archived Steam profiles | Previously linked profiles | When any exist | Inaccessible analytically |
| Switch availability | Can I switch right now? | Always | Four distinct blocking causes |
| Cooldown remaining | Days until switching is allowed | When on cooldown | 90 days from the last **successful** switch |
| Data-access state | Can we read Dota matches? | Always | The one state with a concrete user fix |
| Coverage gaps | Known unrecoverable holes | When any exist | Honest, not alarming |
| Subscription state | Free / Pro active / cancelled-but-active / expired | Always | Cancelled ≠ expired |
| Paid-through date | When Pro actually ends | When cancelled | Entitlement runs to this date |
| Pro import state | Historical backfill progress | During activation | Free state stays active meanwhile |
| Pro coverage completeness | How much history was recovered | After activation | Completeness is **not** claimed if unproven |
| Notification permission | Device-local | Always | Never affects tracking |
| Deletion | True deletion boundary | Always | Immediate; outranks background jobs |

**Not available here:** anything analytical. This surface never shows metrics, trends, baselines or claims. It may *explain* that entitlement changed what they cover.

---

## 7. Core flows

```text
Switch Steam
→ see what switching costs (everything analytical, archived)
→ authenticate the target
→ validation (may block: owned elsewhere / rebuild running / cooldown)
→ confirm
→ old profile archived, new bootstrap starts
```

```text
Data access blocked
→ guidance to the Dota privacy setting
→ user changes it
→ confirm restored
→ recovery re-anchors to the original link date
```

```text
Subscribe
→ understand what Pro adds (depth, not accuracy)
→ purchase
→ Free state stays live while history imports
→ atomic activation
```

```text
Cancel → Pro stays active to the paid-through date → expiry → atomic fallback to Free
```

```text
Delete account → consequences stated plainly → confirm → immediate
```

---

## 8. Required states

| State | Product meaning |
|---|---|
| Free, linked | The common state. **Complete, not degraded.** |
| Pro active | More history depth. |
| Pro cancelled, still active | Runs to the paid-through date. Must be clearly different from expired. |
| Pro expired | Fallback complete; Pro data retained but inactive. |
| Pro importing | Free state remains live and coherent. |
| Pro active, partial coverage | Legitimate. Completeness not claimed. |
| Resubscribing | Rebuilding from retained data; no refetch needed. |
| No Steam linked | Tracking and Pro purchase unavailable, with a route to fix. |
| Switch available | Ready. |
| Switch blocked — cooldown | Remaining time must be knowable. |
| Switch blocked — rebuild running | Temporary; resolves on its own. |
| Switch blocked — target owned elsewhere | Routes to recovery. Ownership is never taken. |
| Switch validation failed | Cooldown **unchanged**. Must not read as a used-up attempt. |
| Switching in progress | Archiving old, bootstrapping new. |
| Data access blocked | Link retained, Pro untouched, guidance shown. |
| Coverage gaps | Known holes, stated honestly. |
| Auth identity collision | Blocked, routed to recovery, never merged. |
| Notifications denied | Zero effect on tracking. Must be said. |
| Deletion pending | Immediate, irreversible. |

---

## 9. User actions

Add or manage an auth method · switch Steam account · start data-access recovery · confirm access restored · purchase Pro · manage/cancel subscription · resubscribe · manage notification permission · open account recovery · delete account.

---

## 10. Experience requirements / guardrails

- **MUST** state the full consequence of a Steam switch before it is confirmed: **nothing analytical carries over** — records, baselines, achievements, role history, match history, corrections. The old profile is archived, not merged.
- **MUST** distinguish the four switch-blocking causes. "You can't switch" without a cause is a dead end.
- **MUST** make clear that a **failed** switch attempt does not consume or reset the cooldown.
- **MUST NOT** offer any unlink-without-replacement action.
- **MUST NOT** present Pro as more accurate, or Free as broken, degraded or incomplete truth.
- **MUST** distinguish "cancelled" from "expired" — entitlement continues to the paid-through date.
- **MUST** present an entitlement-driven change in records or history as a change of **scope**, never as lost achievement or declining performance.
- **MUST NOT** celebrate or mourn a downgrade. No negative PB events.
- **MUST** make clear that losing Steam data access does **not** revoke Pro or delete history.
- **MUST** make deletion findable and completable without obstruction, and state plainly: immediate access loss, renewal stops, **no prorated refund**, and that it does not require waiting for the billing period to end.
- **MUST NOT** place deletion where it can be hit by accident.
- **MUST NOT** imply that accounts can be merged, in any flow including recovery.
- **MUST** state that declining notifications changes nothing about tracking.

---

## 11. Design freedom

Open: list vs grouped-sections vs cards; how account and Steam identity are represented (avatars, IDs, both); how the cooldown is expressed (date, countdown, plain sentence); how switch consequences are presented (a screen, a sheet, a checklist, a typed confirmation) as long as they're stated; subscription presentation, comparison format, and whether a Pro/Free comparison table exists at all; how the data-access fix is instructed (text, screenshots, deep link); the deletion confirmation pattern; where recovery entry points live; density, typography, tone, motion.

---

## 12. UX success metrics

| Metric | Why it matters | Observable |
|---|---|---|
| Steam-switch regret | The most destructive action in the product | Research: after a simulated switch, can users state what they lost? Analytics: support contacts about lost history after a switch. |
| Data-access recovery rate | The only hard dead end in the product | Analytics: blocked → access restored |
| Cancellation comprehension | "Cancelled" vs "expired" is the classic billing misread | Research: after cancelling, can users say when Pro ends and what changes? |
| Deletion completability | An obstructed deletion is a trust and compliance failure | Analytics: deletions started → completed, and drop-off points |
| Entitlement-change misattribution | Records moving must not read as getting worse | Research: after a simulated Pro expiry, do users attribute the change to subscription or to their play? |

Instrumented: recovery rate, deletion funnel, switch attempts vs completions, subscription funnel. Research-only: switch-consequence comprehension, cancellation comprehension, entitlement-change attribution.

---

## 13. UX risks / questions to test

- Do users understand that switching Steam accounts destroys their analytical history — before they do it?
- Is a 90-day cooldown understood as a policy, or experienced as a bug?
- Does a failed switch attempt feel like it "used one up"?
- Do users grasp that Pro buys *depth*, not better measurement — or do they assume Free numbers are less accurate?
- When a PB reverts after expiry, do users read it as "I lost my record"?
- Can users actually complete the Dota privacy-setting change from our instructions, unaided?
- Does "no standalone unlink" feel like being trapped?
- Is deletion easy enough to feel respectful, without being easy enough to hit by accident?

---

## 14. Out of scope

- First-time authentication, first Steam link and initial bootstrap — those are `onboarding/`.
- Any analytical content. This surface shows no metrics, trends, baselines or claims.
- The exact Pro feature catalog, pricing and paywall presentation — not contracted in V1.
- Account-recovery verification, fraud controls and support escalation — a separate contract.
- Account merging — forbidden in V1, and not a design problem here.
- Per-notification-type preferences — V1 has only READY notifications and the platform permission.

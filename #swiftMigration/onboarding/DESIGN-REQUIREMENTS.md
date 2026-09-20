# Onboarding & Cold Start — Design Requirements

Derived from [`SSOT.md`](SSOT.md) and [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md).

---

## 1. Page role

Onboarding earns two things in sequence: a reason to care, then a Steam connection. Everything after that is about keeping a nearly-empty app honest and alive while history arrives.

The user should leave onboarding **connected, with something real about their own Dota already on screen, and an accurate sense of what is still warming up**.

---

## 2. Primary JTBD / user needs

**Primary**

- When I first open this app, I want to understand what it actually tells me about my Dota, so I can decide whether it's worth signing up for.
- When I'm ready to start, I want to connect my Dota account with as little friction as possible, so I can see my own data instead of a demo.
- When I've just connected, I want to see something true about *me* quickly, so the app feels like it worked.

**Secondary**

- When something is still loading or not yet possible, I want to know what it is and roughly when I'll get it, so I don't assume the app is broken or empty.
- When my match data is private and the app can't read it, I want to know exactly what to change, so I'm not stuck at a dead end.

---

## 3. Questions this must answer

- What does this app do that Dotabuff/STRATZ/the client doesn't?
- What do you need from me, and why?
- Am I connected? To which Steam account?
- What have you already got from my history?
- What's missing, and is that a problem or just early?
- If nothing is showing — is that me, my privacy settings, or the app?

---

## 4. Entry points & exits

**Entry**
- First launch (brand new user only → value proposition)
- Returning / reinstalled / logged-out user → straight to authentication or product state
- "Connect Steam" from any unlinked state elsewhere in the app

**Exit**
- → Home, authenticated, with or without Steam
- → Home, linked, bootstrap in progress
- → Data-access recovery state
- → Account recovery boundary (auth identity collision)

Note: value-proposition screens are never replayed. A returning user must never re-enter the top of this funnel.

---

## 5. Proposed information architecture

**Value proposition (3 screens, skippable)**
```text
P0 — what the app tells you about yourself that you can't get elsewhere
P0 — that it measures you against you, not against a rank
P1 — that it separates how you played from whether you won
P2 — anything else
```

**Authentication**
```text
P0 — the sign-in methods
P1 — reassurance that this is an app account, not a Dota login
```

**Steam linking**
```text
P0 — what connecting gives you
P0 — the connect action
P1 — that it's optional to look around, required to track
P2 — privacy/what's read
```

**Cold-start (post-link) — the hard one**
```text
P0 — what we already have ("30 Standard, 7 Turbo matches found")
P0 — the first real, honest fact about the user
P1 — what is still being fetched
P1 — what unlocks later and roughly when (count-based, not time-based)
P2 — everything else
```

Sequence genuinely matters only inside the funnel itself (value → auth → link). Within the cold-start state, ordering is open.

---

## 6. Content & data available

| Content / datum | Meaning | Availability | Notes |
|---|---|---|---|
| Value-prop content | Marketing/explanatory | Brand-new users only | Content and copy are open; not contracted |
| Auth methods | Apple / Google / email | Always | All three feed one app account |
| Auth collision | Identity belongs to another account | Rare | Blocked, routed to recovery. Never merged. |
| Steam link state | linked / not linked | Always | One active Steam ID per account |
| Bootstrap progress | Per-mode acquisition progress | During bootstrap | Server-owned; survives app kill |
| Bootstrap outcome per mode | 6 distinct outcomes (§5.4 of SSOT) | On settle | Standard and Turbo can differ |
| Matches found | Counts per mode | Progressively | Up to 30 + 30, within 90 days |
| Coverage gaps | Known unrecoverable holes | On settle | `READY_WITH_GAPS` is a real, acceptable outcome |
| Raw match facts | Hero, result, role, raw metrics | As matches process | Available before any baseline exists |
| Baseline-building status | Per metric × role × mode | Always | Countable: "needs 5 prior Carry matches" |
| Data-access blocked guidance | Dota "Expose Public Match Data" | On that outcome | The one actionable fix |
| Notification permission prompt | OS prompt | Only at Home, with context | Never during the funnel |
| Pro purchase availability | Requires linked Steam | Always | Blocked before linking |

**Not available at cold start:** trends (need 10 eligible points), adjusted expectations and performance states (need 5 priors per metric+role+mode), most insight cards (history-dependent ones need 20 priors), profile claims (need 30+), PBs (need the 5-prior gate).

---

## 7. Core flows

```text
First launch → value proposition → authenticate → link Steam → bootstrap starts → Home (usable, filling in)
```

```text
Authenticate → skip Steam → explore Home in unlinked state → connect Steam later from any prompt
```

```text
Link Steam → data access blocked → guidance → user changes Dota setting → confirm → recovery anchored to original link date
```

---

## 8. Required states

| State | Product meaning |
|---|---|
| Brand-new | Has never onboarded. Only this user sees the value proposition. |
| Returning / reinstalled / logged-out | Skip straight to auth or product. Never re-run the funnel. |
| Authenticating | Standard. |
| Auth identity collision | Blocked, with a route to recovery. Not an error the user caused. |
| Authenticated, no Steam | Product is navigable; tracking is not running. Persistent, legitimate state. |
| Linking | In progress. |
| Bootstrap running | Home is usable. Facts appear progressively. Per-mode. |
| Bootstrap `READY` | Settled, no known gaps. |
| Bootstrap `READY_WITH_GAPS` | Settled with known holes. Honest, not a failure. |
| `NO_MATCHES_FOUND` | Access works, nothing in scope. |
| `NO_ELIGIBLE_MATCHES` | Matches exist but none qualify (custom/event modes only). |
| `DATA_ACCESS_BLOCKED` | The one state with a concrete user fix. Highest-value recovery design. |
| Mixed per-mode outcome | e.g. Standard ready, Turbo empty. Must be representable simultaneously. |
| Live match during unsettled bootstrap | Match visible with raw facts; comparisons explicitly pending for that mode. |
| Baseline building | Per metric+role+mode, countable. |
| Bootstrap complete | One moment; also the natural place to explain notifications. |
| Pro purchased pre-settle | Free state stays visible; Pro activates later, atomically. |

---

## 9. User actions

Skip value proposition · sign in (Apple / Google / email) · connect Steam · skip connecting · retry a failed link · open data-access guidance · confirm access restored · allow/decline notifications (at Home) · purchase Pro (only when linked).

---

## 10. Experience requirements / guardrails

- **MUST NOT** request notification permission anywhere in this funnel.
- **MUST NOT** ask the user to declare a main role, preferred role, or goals. Roles come from match data.
- **MUST NOT** present an unsettled bootstrap as a finished empty account, or a temporary provider failure as "you have no matches".
- **MUST** keep Home usable throughout bootstrap.
- **MUST** show a newly played match during bootstrap, with its raw facts, while marking its comparison as pending — and only for its own mode.
- **MUST** express readiness gates in **match counts**, not time estimates ("5 more Carry matches", not "about a week").
- **MUST** treat `READY_WITH_GAPS` as a normal successful result, not a warning.
- **MUST NOT** let one mode's empty result make the account read as empty.
- **MUST NOT** imply merging accounts is possible on an auth collision.
- Steam is a *data connection*, not the login — the design must not make it read as a second sign-in.
- The 30+30 bootstrap is a floor for tracking, not a promise of analysis. Don't let the "we found 37 matches" moment imply insights are ready.

---

## 11. Design freedom

Open: value-proposition format, count-within-three, content and copy, illustration/motion/video; auth screen layout and method ordering; how the Steam connection is explained and where trust signals sit; whether cold start is a dedicated screen, a Home state, or a dismissible strip; how per-mode progress is visualised (or whether it is at all); how "unlocks at N matches" is expressed; empty-state art and tone; the data-access recovery layout and instruction format; whether bootstrap completion is a moment, a toast, a card, or silent.

---

## 12. UX success metrics

| Metric | Why it matters | Observable |
|---|---|---|
| Steam-link completion rate | The single gate on the product working at all | Analytics: authenticated accounts → linked, and time to link |
| Cold-start retention | Whether a nearly-empty app survives the first session | Analytics: return within 7 days among newly linked accounts |
| Data-access recovery rate | This state is the only hard dead end | Analytics: `DATA_ACCESS_BLOCKED` → access restored |
| "Is it broken?" comprehension | An honest empty app must read as early, not broken | Research: shown a bootstrapping/empty state, can users say what's happening and what to do? |

Instrumented: link completion, funnel drop-off per step, recovery rate. Research-only: comprehension of empty/building states, perceived value from the value proposition.

---

## 13. UX risks / questions to test

- Do three value-prop screens earn their place, or does one do it better?
- Does connecting Steam feel like handing over credentials? Where does trust break?
- Does "we found 30 Standard and 7 Turbo matches" read as success or as a shortfall?
- Does a cold-start Home read as *early* or as *empty and pointless*?
- Is count-based unlocking ("after 5 more Carry matches") motivating or discouraging?
- Can a user actually complete the Dota privacy-setting change from our instructions, unaided?
- Does a user with only Turbo history understand why their Standard side is empty?

---

## 14. Out of scope

- Ongoing account management — Steam switching, subscription changes, deletion, recovery flows — is `settings_account/`.
- What Home actually shows once populated is `home/`.
- Paywall and pricing presentation are not contracted in V1.
- Onboarding does not configure anything analytical. No preference set here may influence role classification or baselines.

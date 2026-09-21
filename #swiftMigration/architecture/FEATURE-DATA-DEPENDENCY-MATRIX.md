# Feature ↔ Data Dependency Matrix

**Status:** ACTIVE — authoritative for readiness classification
**Last updated:** 2026-09-20
**Scope:** For every product block, the minimum evidence that must exist before it can be considered ready, what it does while waiting, and what it does when that evidence will never arrive.
**Depends on:** [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) §3 · [`PROVIDER-CAPABILITIES-AND-ROUTING.md`](PROVIDER-CAPABILITIES-AND-ROUTING.md) §4

---

## 1. Plain-English summary

**What is this?** A lookup table answering one question: *what has to exist before this part of the app can show something real?*

**Why did we choose it?** Because "the match is still loading" is not one thing. Some parts of a match report need only the final scoreboard. Most need the replay. A few need history we may not have imported yet. Treating them as one flag would make the app either slower than it needs to be or dishonest.

**What does it mean for the user?** Parts of the app that can be ready early **are** ready early. Parts that cannot are honest about it instead of blocking everything else.

**What should future agents not break?** This matrix is at the **capability** level. It is not an API-endpoint matrix, and it must never become one.

---

## 2. How to read it

**Readiness classes** (from [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) §3):

| Class | Meaning |
|---|---|
| **Summary** | Needs summary-class evidence for this match. Available from `SUMMARY_READY`. |
| **Replay** | Needs replay-class evidence for this match. Available from `REPLAY_READY`. |
| **Final** | Needs the single finalisation point — deterministic analysis has run and persisted ([`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) §5.2). Reached from **either** terminal evidence state. |
| **History** | Needs a prior history of eligible observations in the relevant track, beyond this one match. |
| **Coverage** | Needs historical backfill coverage for the account, at a stated evidence class. |

**Provider-specific?** answers whether the block creates a real vendor dependency. For nearly everything the answer is **no** — see [`PROVIDER-CAPABILITIES-AND-ROUTING.md`](PROVIDER-CAPABILITIES-AND-ROUTING.md) §4.3 for the short list where it is yes.

---

## 3. Role metrics by evidence class

**This is the most consequential table in this document.** Fourteen of the twenty V1 role metrics need replay-class evidence. That single fact drives most of the product's readiness behaviour.

Metric definitions are owned by [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §7.2. This table adds only the evidence classification.

| Metric | Class | Why |
|---|---|---|
| `carry.hero_damage_share.v1` | **Summary** | Final hero damage for player and team. |
| `carry.tower_damage_share.v1` | **Summary** | Final tower damage for player and team. |
| `mid.tower_damage_share.v1` | **Summary** | Same. |
| `offlane.fight_presence.v1` | **Summary** | Whole-match credited ratio from the final scoreboard. |
| `support.fight_presence.v1` | **Summary** | Same. |
| `support.healing.v1` | **Summary** | Final healing ÷ duration. |
| `carry.last_hits_at_10.v1` | **Replay** | Needs the per-minute last-hit series. |
| `carry.cs_10_to_20.v1` | **Replay** | Same series, two checkpoints. |
| `carry.net_worth_at_20.v1` | **Replay** | Needs the net-worth checkpoint. |
| `carry.dead_time.v1` | **Replay** | Needs complete death-interval telemetry. |
| `mid.lane_net_worth_advantage_at_10.v1` | **Replay** | Needs the checkpoint **and** unique identification of the opposing Mid. |
| `mid.level_6_time.v1` | **Replay** | Needs level timestamps. |
| `mid.early_fight_presence.v1` | **Replay** | Needs kill-event timing to bound it at 15:00. |
| `mid.net_worth_at_20.v1` | **Replay** | Checkpoint. |
| `offlane.lane_net_worth_advantage_at_10.v1` | **Replay** | Checkpoint + opposing-Carry identification. |
| `offlane.net_worth_at_10.v1` | **Replay** | Checkpoint. |
| `offlane.objective_involvement.v1` | **Replay** | Needs objectives with timestamps and proximity credit. |
| `support.observer_wards_placed.v1` | **Replay** | Needs the ward placement stream. |
| `support.vision_denial.v1` | **Replay** | Needs the ward destruction stream. |
| `support.camps_stacked.v1` | **Replay** | Needs the cumulative series at exactly 20:00 — a final total is **not** a substitute ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §7.2). |

**Consequences, normative:**

1. A `REPLAY_UNAVAILABLE` match produces **N/A with a reason** for its replay-class metrics. Never zero, never omitted silently, never substituted ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §8).
2. Such a match is **still a valid, viewable, potentially progression-eligible match.** `MATCH_ELIGIBLE != EVERY_METRIC_AVAILABLE` is already locked ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §6.3) and this is exactly the case it covers.
3. N/A observations never enter a baseline, rolling window, trend count or PB history. A history of summary-only matches therefore builds baselines **only** for the six summary-class metrics.
4. Because baselines gate at 5 priors and trends at 10 points, **replay-class coverage of historical matches directly determines how much of the product works for a new user.** That is why §5 treats deep historical acquisition as a functional requirement.

---

## 4. Per-match blocks

| Block | Owning SSOT | Min readiness | Provider-specific? | Partial render? | While waiting | Terminal fallback |
|---|---|---|---|---|---|---|
| Match identity: hero, result, mode, date, duration | [`match_detail`](../match_detail/SSOT.md) | **Summary** | no | n/a | n/a | n/a |
| Full ten-player scoreboard | [`match_detail`](../match_detail/SSOT.md) | **Summary** | no | n/a | n/a | n/a |
| Draft | [`match_detail`](../match_detail/SSOT.md) | **Summary** | no | n/a | n/a | n/a |
| Final items and ability build | [`match_detail`](../match_detail/SSOT.md) | **Summary** | no | n/a | n/a | n/a |
| Effective role (displayed) | [`app_foundation`](../app_foundation/SSOT.md) §5 | **Summary** | **no** — see §6 | n/a | n/a | n/a |
| Raw achieved value, summary-class metrics | [`match_detail`](../match_detail/SSOT.md) §4.1 | **Summary** | no | yes | value shows | n/a |
| Raw achieved value, replay-class metrics | [`match_detail`](../match_detail/SSOT.md) §4.1 | **Replay** | no | yes | pending affordance | **N/A with reason** |
| Baseline-at-the-time comparison | [`match_detail`](../match_detail/SSOT.md) §4.2 | **Final** + **History** | no | no | not shown | baseline-not-established, or N/A if the metric is N/A |
| Context-adjusted expectation + performance state | [`app_foundation`](../app_foundation/SSOT.md) §10 | **Final** + **History** | no (population data: **yes**, cached) | no | not shown | `NOT_READY`, or absent for N/A metrics |
| Matchup context badge | [`match_detail`](../match_detail/SSOT.md) §4.3 | **Final** (needs lane assignment) | no | no | not shown | `UNAVAILABLE` → **renders nothing** |
| Personal Best state and `NEW_PB` | [`app_foundation`](../app_foundation/SSOT.md) §12 | **Final** + **History** | no | no | not shown | no PB evaluation for N/A metrics |
| Progression eligibility + reason | [`app_foundation`](../app_foundation/SSOT.md) §6 | **Final** | no | no | not shown | stated with reason |
| Insight cards (all 17 types) | [`match_detail`](../match_detail/SSOT.md) §5 | **Replay** → **Final** | no | no | pending affordance | **the normal no-card state** |
| Edit Role action | [`match_detail`](../match_detail/SSOT.md) §6 | **Summary** | no | n/a | available | "correction unavailable" if retained data no longer supports a rebuild |

**Note on insight cards.** Every V1 card family — lead story, lane story, hidden enemy activity, power spikes and item timings, structure contradiction — is derived from replay-class evidence. A `REPLAY_UNAVAILABLE` match therefore renders the **normal, no-special-insight state**, which the product already defines as the majority experience ([`../match_detail/SSOT.md`](../match_detail/SSOT.md) §5.2). It is not an error and needs no special copy.

---

## 5. Cross-match and account-level blocks

| Block | Owning SSOT | Min readiness | Provider-specific? | Partial render? | While waiting | Terminal fallback |
|---|---|---|---|---|---|---|
| Today's Matches entry | [`home`](../home/SSOT.md) §3 | **Summary** | no | yes | entry present, readiness indicated | remains; never removed |
| Today's Focus | [`home`](../home/SSOT.md) §4 | varies by signal — **content model is OPEN** | no | n/a | honest neutral state | honest neutral state |
| Home role progression summaries | [`home`](../home/SSOT.md) §6 | **History** per metric | no | yes | `Insufficient History` per metric | per-metric, never a role verdict |
| Last 5 Matches | [`home`](../home/SSOT.md) §7 | **Summary** | no | yes | entry present | remains |
| History row | [`history`](../history/SSOT.md) §4 | **Summary** | no | yes | row present | row **never disappears** |
| History evolution content | [`history`](../history/SSOT.md) §5 | **History**, sourced from Progress | no | yes | `Insufficient History` | per-metric |
| Progress observation series | [`progress`](../progress/SSOT.md) §3 | **Final** per point | no | yes | fewer points | N/A points shown as N/A, never zero |
| Progress rolling baseline | [`progress`](../progress/SSOT.md) §5 | **History** ≥ 5 priors | no | no | baseline-building, countable | stays building |
| Progress trend state | [`progress`](../progress/SSOT.md) §4 | **History** — complete 10-point window | no | no | `Insufficient History` | `Insufficient History` — **never a decline** |
| Progress Personal Bests | [`progress`](../progress/SSOT.md) §7 | **History** | no | yes | absent | "unavailable", never zero |
| Profile identity line + role map | [`profile`](../profile/SSOT.md) §4.2 | **Final** × N matches + **Coverage (summary)** | no | yes | honest "so far" or nothing | withheld, never a default archetype |
| Profile hero tags | [`profile`](../profile/SSOT.md) §4.3 | **Final** × N role matches + **Coverage (summary)** | no | yes | counts only | counts only |
| Profile confirmed claims | [`profile`](../profile/SSOT.md) §4.4 | **Final** × window + **Coverage (summary)** | no | no | section hidden | hidden — **never teased into existence** |
| Profile "Right now" (form runs, PB momentum) | [`profile`](../profile/SSOT.md) §4.5 | **History** on replay-class metrics + **Coverage (replay)** | no | yes | section hidden | hidden |
| Profile Personal Bests | [`profile`](../profile/SSOT.md) §4.6 | **History** | no | yes | insufficient message | unavailable |
| Monthly / periodic report | [`app_foundation`](../app_foundation/SSOT.md) §13.2 | **Coverage** over the period | no | yes | coverage stated honestly | states its coverage; **never triggers a synchronous backfill** |
| Free bootstrap outcome | [`onboarding`](../onboarding/SSOT.md) §5.4 | **Coverage** per mode | no | n/a | non-terminal | `READY_WITH_GAPS` records real gaps |
| Pro historical state | [`settings_account`](../settings_account/SSOT.md) §5.1 | **Coverage (replay)** where the feature needs it | **yes** for beyond-horizon history | no | coherent Free state stays visible | activates with recovered history; **completeness is never claimed** |
| Challenge evaluation | *no SSOT exists* | per challenge — see §7 | depends | depends | **pending**, never failed | unavailable, never failed |

---

## 6. Role resolution

Role resolution deserves its own row because it is easy to get wrong.

| Aspect | Classification |
|---|---|
| Effective role available | **Summary** — the classifier must produce a role from summary-class evidence ([`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) §6, rule R-1). |
| Classifier confidence | May improve at **Replay**. A re-run before finalisation is not a correction (R-4). |
| Low-confidence correction prompt | **Final** — raise it from the classifier's last run, so the user is asked once (R-7). |
| Provider-specific? | **No.** A native provider role label is class C and explicitly not required ([`PROVIDER-CAPABILITIES-AND-ROUTING.md`](PROVIDER-CAPABILITIES-AND-ROUTING.md) §4.3). |
| Edit Role availability | **Summary** — available on every retained match while retained data supports a rebuild. |
| User assertion precedence | Absolute, at every readiness. A classifier re-run never overwrites it. |

---

## 7. Classifying a block that is not listed here

Any new UI block, achievement, challenge or report must be classified before it is designed. Four questions:

1. **Can it be computed from the final scoreboard and match header alone?** → **Summary**.
2. **Does it need anything from the match timeline — a checkpoint, an event, a timing, a placement, a lane assignment?** → **Replay**.
3. **Does it compare against the player's own history?** → add **History**, and state the sample gate.
4. **Does it make a claim about a period longer than the imported history?** → add **Coverage**, and state what it is based on.

**Then answer two more:**

5. **What does it show while waiting?** — bounded and honest, never an endless spinner.
6. **What does it show when the evidence will never arrive?** — a terminal, explained state. Never zero. Never a permanent pending.

**Worked examples, from the locked direction:**

- A Personal Best determinable from summary-class data → **Summary + Final + History**. It **MUST NOT** wait for replay processing.
- An achievement requiring a replay event (a ward at a time, a stack, an objective) → **Replay**. It stays **pending** until the evidence exists, and becomes **unavailable** if the evidence is terminal — **never failed**.
- A challenge counting final last hits → **Summary**. Resolvable at Stage 1.
- A challenge counting ward placement timing → **Replay**. Pending until Stage 2.

**Normative:** a single generic "match processing" flag **MUST NOT** be used to gate blocks with different evidence requirements. Different evidence, different gate. A challenge that only needed the scoreboard must not sit behind the replay gate, and an achievement that needs a replay event must not be declared failed because the replay has not arrived yet.

---

## 8. Product/SSOT dependents

| Document | What to re-check when this document changes |
|---|---|
| [`../match_detail/SSOT.md`](../match_detail/SSOT.md) | §3A two-stage content split. |
| [`../home/SSOT.md`](../home/SSOT.md) | §3 Today's Matches readiness. |
| [`../history/SSOT.md`](../history/SSOT.md) | §4 row content boundary; §9 row states. |
| [`../progress/SSOT.md`](../progress/SSOT.md) | §3A metric evidence classes and recompute triggers. |
| [`../profile/SSOT.md`](../profile/SSOT.md) | §6A coverage honesty. |
| [`../onboarding/SSOT.md`](../onboarding/SSOT.md) | §5.5 bootstrap evidence classes. |
| [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) | §7.2 note on metric evidence class; §12 PB readiness. |

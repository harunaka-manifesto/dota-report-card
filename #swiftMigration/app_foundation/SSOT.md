# App Foundation — SSOT

**Status:** ACTIVE — authoritative cross-product contract
**Scope:** The semantics every Dota Tracker surface inherits: identity, match lifecycle, role resolution, metrics, baselines, context-adjusted expectation, progression methodology, Personal Bests, Standard/Turbo isolation, Free/Pro entitlement, rebuild and versioning, data-state vocabulary.
**Authority:** This document is the single authoritative definition of every rule below. Feature SSOTs (`home/`, `history/`, `match_detail/`, `progress/`, `profile/`, `onboarding/`, `settings_account/`) may summarise these rules for their own readability, but MUST NOT redefine them. Where a feature SSOT and this document disagree, this document wins.

Keywords MUST, MUST NOT, SHOULD, MAY are used as in RFC 2119.

---

## 1. Product purpose and philosophy

Dota Tracker is an ongoing personal-performance tracker. Its promise is:

> Help players improve and understand the parts of Dota reasonably under their control.

It is explicitly **not** promising "this app will make you win."

Three consequences bind every surface:

1. **Personal performance is distinct from match outcome.** Win/loss is a fact about the match, never a measure of the player.
2. **Progression is never defined by MMR, win/loss, or a universal composite score.** It is a set of role-specific, metric-level signals measured against the player's own history.
3. **Rigor backstage, legibility onstage.** The product may compute carefully; it must present honestly and without fabricated certainty.

---

## 2. Product invariants

These apply to every feature without exception.

1. **No opaque judgment.** V1 MUST NOT present an overall match score, letter grade, composite performance score, player rating, percentile, arbitrary good/bad-player judgment, or opaque AI verdict.
2. **No fabricated certainty.** Missing, malformed, unavailable, or insufficient evidence MUST be represented as N/A, an explicit unavailable state, or an explicit ineligible reason. It MUST NOT be silently converted to zero or to a synthetic comparison.
3. **N/A is not zero.** A legitimate measured zero remains zero. These are different states and MUST be distinguishable everywhere they appear.
4. **Standard and Turbo are separate progression worlds.** They MAY use identical methodology, but MUST NOT share baselines, trends, Personal Bests, observations, queues, blockers, or progression histories.
5. **Progression is role-specific.** Every successfully classified retained match resolves to exactly one of Carry, Mid, Offlane, Support. Position 4 and Position 5 both map to Support. There is no Unknown progression role.
6. **Historical comparisons are time-relative.** A historical match compares against the same-role, same-mode baseline that existed *before* that match. A later match MUST NOT make an old comparison silently drift.
7. **Canonical methodology is singular.** One methodology at a time. Approved migrations rebuild compatible retained history deterministically; old and new math never coexist in one canonical timeline.
8. **Current truth and past events are distinct.** Derived current truth (PBs, baselines, trends, comparisons) MAY be rebuilt. Delivered celebrations and notifications are append-only, auditable, and are never retracted or replayed.
9. **Subscription does not change measurement truth.** Free and Pro use identical processing and methodology for whatever history each tier is entitled to inspect. Pro adds depth, synthesis and engagement — never better accuracy.
10. **Account isolation is absolute.** Cursors, match entries, role assertions, histories, derived state, acknowledgements and notifications are scoped to the app account and the active Steam profile.
11. **No teammate attribution.** V1 MUST NOT estimate, score, label, or imply teammate quality, and MUST NOT attach any coefficient, adjustment or copy to a teammate's behaviour or hero.
12. **No causal explanation of the match result.** No surface may claim why a match was won or lost.
13. **Implementation status is not product status.** A locked contract is not shipped merely because it is documented.

---

## 3. Identity model

### 3.1 App account

- The persistent product owner scope. Authentication is required before Home; V1 has **no guest or local-only mode**.
- Apple, Google and email are authentication *methods* for one app account, not separate account types. Multiple methods MAY attach to one account.
- If an authentication identity already belongs to another app account, attachment is **blocked**. V1 MUST NOT automatically merge accounts, or move Steam linkage, subscription, purchases, history or progression. The case routes to the account-recovery boundary.

### 3.2 Steam identity

App identity and Steam identity are separate concepts. Steam is the game-data connection, not the login.

```text
1 app account → 1 active Steam ID
1 Steam ID    → 1 app account
```

- An authenticated user MAY explore the product without Steam linked.
- Steam linkage is **required** for actual tracking and **required before Pro purchase**.
- An app account MAY retain previously linked Steam profiles as **archived** profiles; only one is active. Archived analytical state never carries into a different active profile.
- There is **no normal standalone "Unlink Steam"** action. A user keeps the active profile or switches to another valid target. Detaching without replacement exists only inside account recovery.

### 3.3 Account deletion

Account deletion is a true deletion boundary, distinct from logout, Pro cancellation, Steam switching, and recovery detachment. It:

- takes effect immediately, even while bootstrap, backfill, rebuild or recovery jobs are running;
- cancels or invalidates background work so late results cannot restore deleted state;
- releases the Steam linkage;
- removes authentication identities, active and archived Steam profiles, Free and Pro history, derived PB/baseline/achievement state, notification state and recovery metadata, subject to separately defined legal/operational retention;
- stops future subscription renewal with **no prorated refund**, and does not require waiting until the end of the paid period.

Deletion outranks all background analytical work.

---

## 4. Match lifecycle

### 4.1 Discovery

V1 checks for new matches on **app open, app resume, or explicit refresh**. There is no always-running, real-time or live-polling promise. Matches played while the app is closed MAY remain undiscovered until the next trigger and MUST NOT generate a notification before discovery.

Discovery MUST:

1. find all missed source items in scope;
2. durably record every item with an accepted, rejected or terminal outcome;
3. resume interrupted pagination without gaps or duplicate effects; and
4. advance the authoritative cursor **only after** the durable boundary is reached.

Missing or untrustworthy chronology MUST NOT be guessed. Discovery order MUST NOT substitute for match chronology.

### 4.2 Account sync state

Describes only the latest discovery attempt. It never summarises or overwrites known per-match state.

| State | Meaning |
|---|---|
| `IDLE` | No discovery attempt active. Cached state may exist. |
| `CHECKING` | An open/resume/refresh/reconnect attempt is in progress. |
| `UP_TO_DATE` | A complete discovery reached its authoritative boundary, whether or not it found matches. |
| `SYNC_ERROR` | Discovery was offline, interrupted, incomplete or failed. Known match state remains usable. |

`SYNC_ERROR` MUST NOT mean "no matches exist", MUST NOT hide an `ACTION_REQUIRED` match, and MUST NOT turn a READY match back into waiting.

### 4.3 Per-match lifecycle state

| State | Product meaning |
|---|---|
| `WAITING_FOR_PROVIDER` | Sufficient validated source truth is not yet available for the next unresolved stage. |
| `ANALYZING` | Deterministic analysis or progression finalization is in progress. |
| `WAITING_FOR_PRIOR_MATCH` | Analysis is complete, but an older unresolved match in the **same** progression bucket must settle first. |
| `ACTION_REQUIRED` | Bounded automatic retries exhausted a retryable internal/stage failure. The user's single Retry is the next action. |
| `READY` | All applicable outputs concluded as measured or legitimate N/A, and progression is finalized or explicitly ineligible. |
| `UNAVAILABLE` | Trustworthy analyzable source truth never arrived, remained invalid, or was withdrawn within the bounded process. |

`RETRYING` is **attempt metadata** layered on `WAITING_FOR_PROVIDER` or `ANALYZING`. It is never a durable state.

There is **no partial-READY state**. A READY match MAY have legitimate N/A metrics and MAY be progression-ineligible.

### 4.4 Ordering and idempotency

- Missed matches are processed **chronologically oldest to newest** within each progression bucket. Chronology key: `(provider_started_at, provider_source_match_id)`.
- Analysis MAY run concurrently; progression finalization MUST be ordered per bucket. The other bucket never blocks.
- A later same-bucket match waits in `WAITING_FOR_PRIOR_MATCH` until its predecessor is READY, progression-ineligible, or definitively excluded as UNAVAILABLE.
- One source identity plus one account/participant maps to one logical match entry. Overlapping discovery, retries and workers MUST merge, not duplicate.
- At-least-once internal work MUST have exactly-once observable effects: no duplicate history row, observation, PB event or logical notification.

### 4.5 Retry and terminal behaviour

- Automatic retries are bounded. Backoff and attempt counts are implementation policy, not product meaning.
- A user-facing **Retry is one action**. It resumes from the earliest failed or unresolved stage and reuses valid completed work.
- `ACTION_REQUIRED` and `UNAVAILABLE` stop automatic retry at rest but remain manually retryable. `UNAVAILABLE` is not deletion and not a hidden match.
- A provider success followed by internal failure retries analysis only; it MUST NOT refetch source truth.
- Provider checkpoints are provenance-bound and monotonic before READY. Stale responses MUST NOT regress them.

### 4.6 Progression classification

Orthogonal to lifecycle state.

| Classification | Meaning |
|---|---|
| `STANDARD` | Ranked or unranked All Pick. |
| `TURBO` | Turbo. |
| `NONE(reason)` | Unsupported/unknown mode, missing role, abandon/unfinished, integrity-invalid, or another explicit ineligibility reason. |

`NONE(reason)` is **not a processing failure**. It stays visible and can reach READY. A provider/source failure MUST remain a processing failure (`ACTION_REQUIRED` / `UNAVAILABLE`); it MUST NOT be relabelled as a successful `NONE` merely to reach READY.

### 4.7 Finalization and notifications

- Passive provider enrichment after READY MUST be ignored. It never mutates a finalized snapshot.
- V1 push notifications are **READY-only**. No push for transient retry, `WAITING_FOR_PRIOR_MATCH`, `ACTION_REQUIRED` or `UNAVAILABLE`.
- A ready set discovered or finished while the app is closed MAY produce **one bundled/coalesced logical notification**, which MAY span both buckets.
- In the foreground, update the app directly and suppress/cancel a redundant push best effort. Recheck relevance when a delivered notification is opened.
- Dedupe is stable across retries, restarts, devices and overlapping batches.
- Notification permission, token or device delivery state MUST NEVER affect processing, readiness, progression or account state.

---

## 5. Role resolution and correction

### 5.1 The four roles

Every successfully classified match resolves to exactly one of **Carry, Mid, Offlane, Support**. Positions 4 and 5 normalise to Support.

The following MUST NOT be created: Unknown, Unresolved, Flex, Roamer, Position 4, Position 5.

A match that is *structurally unprocessable* (invalid identity, missing required classification inputs) is a **Match Lifecycle failure**, not an Unknown role.

### 5.2 Classifier-first

1. A successfully classified match receives the classifier's best role **immediately**.
2. Role-dependent processing proceeds without waiting for user confirmation.
3. A low-confidence result is still a real role, used immediately.

Evidence hierarchy: **primary** — lane/early-map position, farm priority, lane relationship; **supporting** — support behaviours (vision, stacks, consumables); **weak** — hero identity, as a prior or tiebreaker only.

Win/loss, KDA, match outcome and performance quality MUST NOT influence role classification. Unusual hero/role combinations are valid when behaviour supports them.

### 5.3 Confidence and prompting

Confidence is a product-level bucket: **high** or **low**. Low confidence means evidence conflicts, is sparse, or leaves several roles plausible — not that no role exists.

- Only **low-confidence** results proactively ask the user to confirm or correct.
- The prompt is **corrective, not blocking**. The match has already processed with the classifier role.
- High-confidence matches receive no routine proactive prompt.
- The prompt is a shortcut into the same Edit Role flow; it is not a second correction system.

### 5.4 User assertion precedence

```text
latest user role assertion > classifier output
```

- A user **confirmation** of the suggested role is itself an authoritative assertion.
- A later assertion replaces the earlier one.
- Classifier reruns MAY update detected role, confidence and version metadata, but MUST NEVER overwrite a user-asserted effective role.
- With no assertion, classifier output is the source of effective role; a rerun that changes it follows the correction rebuild contract.

### 5.5 Persistent correction access

Every retained match exposes a persistent **Edit Role** action on Match Detail, for low- and high-confidence matches, old and recent alike. Availability follows **retained data**, not age or recency. If source telemetry is no longer sufficient to recalculate, the product MUST say correction is unavailable rather than fabricate a rebuild.

Edit Role accepts only the four V1 roles.

### 5.6 Correction rebuild

A confirmed role change deterministically, idempotently:

1. removes the match's observations from the old-role histories and PB indexes;
2. re-evaluates the match with the new role's metric set, using **frozen source data and the original applicable metric versions**;
3. inserts valid observations (or legitimate N/A) into the new-role histories at the match's original chronology position;
4. replays affected old- and new-role baselines, comparisons, trends, current PB indexes, context adjustments and lane context **from that position forward**, within the **same** mode bucket only;
5. leaves every other bucket, role, metric and unaffected match unchanged.

If a metric required by the corrected role cannot be computed from retained data, it is **N/A** — never fabricated, substituted, or coerced to zero. Delivered celebrations and notifications remain append-only; they are not retracted or re-sent. Original classifier provenance survives correction.

A rebuild makes **no provider calls**.

---

## 6. Progression buckets and eligibility

### 6.1 Buckets

| Bucket | Included modes |
|---|---|
| `STANDARD` | Ranked All Pick, Unranked All Pick |
| `TURBO` | Turbo |

Ability Draft, Captain's Mode and other structurally different or special modes are **excluded** from progression and receive an explicit ineligible classification.

Both buckets use identical V1 roles, metric definitions and versions, baseline rule, gates, PB rules and N/A semantics. Only the history namespace and ordering differ.

### 6.2 Match-level progression eligibility

A progression-eligible match satisfies **all** of:

1. supported bucket (`STANDARD` or `TURBO`);
2. `duration_seconds >= 600` (599 s is ineligible; 600 s passes);
3. the tracked player did not abandon;
4. an `effective_role` is available;
5. available evidence does not indicate an invalid or non-competitive match;
6. required telemetry exists for each metric actually measured.

**Competitive integrity fails closed.** If the backend cannot confidently establish that a remake, safe-to-leave, abandon-like or otherwise abnormal match is a normal competitive match, progression is ineligible. Ambiguity is ineligibility.

### 6.3 Match eligibility ≠ metric availability

`MATCH_ELIGIBLE != EVERY_METRIC_AVAILABLE`. A valid 18-minute All Pick may be progression-eligible while Net Worth @20 and Camps Stacked @20 are N/A because the match ended before the checkpoint. Earlier and full-match metrics still participate.

---

## 7. Role metrics

### 7.1 Progression identity

Every observation, baseline, PB index and comparison is keyed by:

```text
progression_bucket + effective_role + metric_id + metric_version
```

No key may read another key's data. **Heroes never split a role track** — Luna Carry, Phantom Assassin Carry and Slark Carry all update the same Carry history. The same formula in two roles is still two tracks (Carry and Mid Tower Damage Share are separate).

There are **eight independent progression tracks**: Standard × {Carry, Mid, Offlane, Support} and Turbo × {Carry, Mid, Offlane, Support}.

### 7.2 Canonical registry (20 active metrics)

Carry 6, Mid 5, Offlane 4, Support 5. Support **Control** is UNSUPPORTED in V1 and MUST NOT be represented through any proxy (cast counts, action counts, damage, K/A).

| Metric ID | Display meaning | Direction | Comparison value | N/A when |
|---|---|---|---|---|
| `carry.last_hits_at_10.v1` | CS at 10:00 | higher better | same count | match ends before 10:00; trajectory missing/malformed |
| `carry.cs_10_to_20.v1` | CS gained 10:00–20:00 | higher better | same count | match ends before 20:00; coverage missing |
| `carry.net_worth_at_20.v1` | Net Worth at 20:00 | higher better | same gold | match ends before 20:00; checkpoint absent/malformed |
| `carry.dead_time.v1` | Time Spent Dead | **lower** better | `total_dead_seconds / match_duration_seconds` | duration or complete dead-interval telemetry missing |
| `carry.hero_damage_share.v1` | Hero Damage Share | higher better | player / team hero damage | team hero damage is 0; inputs unavailable |
| `carry.tower_damage_share.v1` | Tower Damage Share | higher better | player / team tower damage | team tower damage is 0; inputs unavailable |
| `mid.lane_net_worth_advantage_at_10.v1` | Mid Lane NW Advantage | higher better | own NW@10 − opposing Mid NW@10 | checkpoint missing; opposing Position 2 not uniquely identified |
| `mid.level_6_time.v1` | Time Reaching Level 6 | **lower** better | seconds | fewer than six valid level timestamps |
| `mid.early_fight_presence.v1` | Early Fight Presence (to 15:00) | higher better | credited ratio | team credited kills = 0; event data missing/invalid |
| `mid.net_worth_at_20.v1` | Mid Net Worth at 20:00 | higher better | same gold | as Carry NW@20 |
| `mid.tower_damage_share.v1` | Tower Damage Share | higher better | player / team tower damage | team tower damage is 0 |
| `offlane.lane_net_worth_advantage_at_10.v1` | Offlane Lane Pressure | higher better | own NW@10 − opposing Carry NW@10 | checkpoint missing; opposing Position 1 not unique |
| `offlane.net_worth_at_10.v1` | Offlane Economy | higher better | same gold | match ends before 10:00 |
| `offlane.fight_presence.v1` | Fight Presence (whole match) | higher better | credited ratio | team credited kills = 0 |
| `offlane.objective_involvement.v1` | Objective Involvement | higher better | credited towers / enemy towers destroyed | no enemy towers; tower report or proximity events missing |
| `support.fight_presence.v1` | Fight Presence | higher better | credited ratio | team credited kills = 0; incomplete scoreboard |
| `support.observer_wards_placed.v1` | Wards Placed | higher better | observer wards per 10 min | ward stream missing/malformed; non-positive duration |
| `support.vision_denial.v1` | Vision Denial | higher better | dewards per 10 min | destruction stream missing/malformed |
| `support.camps_stacked.v1` | Camps Stacked | higher better | cumulative count at **exactly 20:00** | match ends before 20:00; series missing/malformed/non-monotonic; 20:00 checkpoint unavailable |
| `support.healing.v1` | Healing | higher better | healing per 10 min | healing missing/malformed; non-positive duration |

Notes that carry product meaning:

- **Camps Stacked is the count at 20:00**, never the final-match total. If it is 3 at 20:00 and 6 at match end, the value is **3**.
- **Raw ≠ comparison.** The product may display a raw amount (ward count, healing amount, dead seconds, player damage) while the baseline, delta and PB use the declared comparison value (per-10 rate, share, rate). A UI MUST NOT invent its own conversion.
- Every metric definition is **versioned**. Any change to formula, inputs, boundary, denominator, direction, zero/N/A rule, normalization, or PB basis requires a new metric version or an explicit migration.
- A Dota patch alone does not reset a role history.

### 7.3 Metric limitations (product-level honesty)

These are contract, not copy suggestions. Each metric measures an **observable act**, never its quality, intent, or consequence:

- Last hits measure resource acquisition, not accuracy or lane quality.
- Net worth includes kills, deaths, items and team allocation, not only farming.
- Damage/tower share is contribution share, never proof of causing a kill or a structure falling.
- Fight presence is observable credit, not fight quality or timing.
- Wards/dewards count placement and destruction, never useful vision, coverage or information denial.
- Camps stacked is an act; ally consumption, safety and opportunity cost are unobserved.
- Time dead is not a judgment about cause, sacrifice or positioning.
- Level 6 earlier is not automatically better if it came from taking ally resources.

Measurements MUST NOT become judgments, causal claims, or a global score.

---

## 8. N/A versus zero

| State | Use when | Examples |
|---|---|---|
| `0` | Inputs are valid, the required opportunity/denominator exists, and the measured numerator is genuinely zero. | 0 healing; 0 wards with a valid ward stream; 0% tower damage share while team tower damage is positive. |
| `N/A` | The metric cannot be meaningfully calculated. | Match ended before the checkpoint; zero team kills for Fight Presence; zero team tower damage for a share; required telemetry missing. |

N/A observations **never** enter a baseline, a rolling-window count, a trend count, or PB history. Legitimate zeros do. A missing field, malformed event, absent checkpoint, or zero denominator MUST NOT be coerced to zero.

---

## 9. Personal baseline

### 9.1 Definition

For a measured observation, the canonical baseline is:

> the **median** of the latest **20 previous** eligible measured observations sharing `progression_bucket + effective_role + metric_id + metric_version`, after a minimum of **5** prior measured observations.

- The current match **never** contributes to its own baseline.
- Previous-only, ordered by the chronology key.
- Fewer than 20 priors is fine once the 5-prior gate is met; the available history is used, up to 20.
- The statistic is the **median**, not the mean.
- Fewer than 5 priors → `BASELINE_BUILDING`. At 5 or more → `BASELINE_READY`. The first generally comparable observation is the **sixth** eligible measured observation in that identity.
- Baseline readiness is per `mode × role × metric × version`. There is **no** global "player has 5 matches" rule. Standard Carry CS can be ready while Standard Support healing is building and Turbo Support has no history at all.

A baseline is contextual reference. It MUST NOT replace, hide or normalise away the raw match value, and MUST NOT be presented as an independent skill score.

### 9.2 Baseline at the time

The **match comparison baseline** is the rolling baseline snapshot that existed immediately before that specific match. Match Detail uses it. Later matches MUST NOT change a finalized historical comparison. Only an authorized role correction, methodology migration or deterministic rebuild may recompute it.

---

## 10. Context-adjusted expectation

Owner-approved architecture. Context modifies **what the value is measured against** — never the verdict, never the outcome.

### 10.1 Model

```text
context_adjusted_expectation
  = personal rolling baseline
  + own-hero adjustment        (selective, per metric)
  + lane-opponent adjustment   (opponents only, where applicable)
```

Both adjustments are **window-relative**: each is the current match's population term minus the median of that same term across the baseline window. A player who always plays the same hero into the same kind of lane is therefore adjusted by ≈ 0 — correctly.

Population terms are read from provider aggregate endpoints (hero level at position; lane-opponent effect). No corpus is built, no model is fitted, **no ML and no LLM** run at any time.

### 10.2 Hard boundaries

- **No lane-partner / teammate term.** Dropped from V1 deliberately: it is the only teammate-attribution surface in the system, and it is worth a negligible amount of explanatory power.
- **No realised teammate or opponent behaviour.** Every input is fixed at the horn (drafted heroes, positions, lanes, side). Nothing that happened during the match may enter the adjustment.
- **No exact matchup matrix.** Pooled opponent effects only; exact hero-vs-hero pairs were measured as adding nothing.
- **Forbidden inputs (normative):** any trajectory or event from this match; the metric being scored at any timestamp; lane-outcome fields; tower deaths; net-worth/experience lead series; first-blood time; provider analysis/awards/behaviour/impact scores; win/loss; rank, bracket, MMR, party; **the lane partner's hero**; anything about what any other player actually did after the horn.
- Adjustments are **capped**. An uncapped hero term can reach implausible magnitudes; caps are part of the shipped model, not optional polish.
- **No per-hero and no per-context personal baselines** are created. Baseline keying is unchanged.

### 10.3 Per-metric application (context classes)

Adjustment is applied **selectively per metric**, never globally.

| Class | Meaning |
|---|---|
| **A** | Personal baseline only. |
| **B** | + own-hero adjustment. |
| **C** | + own-hero adjustment + lane-environment adjustment. |
| **C\*** | + lane-environment adjustment + a *paired* hero term (for metrics that are already a difference between two players). |
| **D** | Never adjusted, by product decision. Still scored. |
| **E** | Not reliably interpretable — displayed as a diagnostic, never scored. |

| Metric | Class | Scored? |
|---|---|---|
| `carry.last_hits_at_10.v1` | C | yes |
| `carry.cs_10_to_20.v1` | B | yes |
| `carry.net_worth_at_20.v1` | B | yes |
| `carry.dead_time.v1` | **D** | yes, unadjusted |
| `carry.hero_damage_share.v1` | B | yes |
| `carry.tower_damage_share.v1` | B | yes |
| `mid.lane_net_worth_advantage_at_10.v1` | C\* | yes |
| `mid.level_6_time.v1` | C | yes |
| `mid.early_fight_presence.v1` | B | yes |
| `mid.net_worth_at_20.v1` | B | yes |
| `mid.tower_damage_share.v1` | B | yes |
| `offlane.lane_net_worth_advantage_at_10.v1` | C\* | yes |
| `offlane.net_worth_at_10.v1` | C | yes |
| `offlane.fight_presence.v1` | A | yes |
| `offlane.objective_involvement.v1` | **E** | **no — diagnostic only** |
| `support.fight_presence.v1` | A | yes |
| `support.observer_wards_placed.v1` | A | yes |
| `support.vision_denial.v1` | A | yes |
| `support.camps_stacked.v1` | A | yes |
| `support.healing.v1` | B | yes |

**Floor rule (normative):** a metric whose baseline-window median sits at or near the metric's floor MUST NOT receive a population adjustment. Adjusting near-zero counts measurably degrades output.

**Deaths, dead time and objective involvement are never lane-adjusted.**

Scope: lane context and lane adjustment apply to `STANDARD` × {Carry, Mid, Offlane} only. Own-hero adjustment additionally applies to Support and to the whole-match class-B metrics above. **Turbo receives neither** and renders on the raw personal baseline.

### 10.4 Performance state

```text
PerformanceState : ABOVE | IN_LINE | BELOW | NOT_READY
```

- Derived from the residual between the measured comparison value and the context-adjusted expectation, honouring the metric's direction.
- Thresholds are frozen per metric in the parameter set — never computed at runtime.
- `NOT_READY` when the baseline gate is unmet.
- A class-A or class-D metric is compared against the raw personal baseline ("your usual") rather than an adjusted expectation; the four states still apply.

**Context adjustment is not a discount.** The hero term frequently makes a verdict *harsher*. Performance state MUST NOT be suppressed, softened or upgraded because of lane context.

### 10.5 Lane context

```text
LaneContext : DIFFICULT | TYPICAL | FAVOURABLE | UNAVAILABLE
```

- A property of the **draft**, computed from the drafted lane opponents alone. It never reads the residual, the outcome, or anything realised.
- Bands are frozen absolute thresholds at roughly the population 20th/80th percentile — roughly 20% DIFFICULT / 60% TYPICAL / 20% FAVOURABLE.
- One label per match, attached to the lane-metric group — **not** per metric.
- User-facing terminology MUST be **"Difficult matchup" / "Typical matchup" / "Favourable matchup"** (or the equivalent lane phrasing already locked as `Difficult lane` / `Typical lane` / `Favourable lane`). The term describes **on-paper opponent context**, not what actually happened in the lane, and MUST NOT assert that the lane itself was objectively easy or hard.
- `UNAVAILABLE` renders **nothing**. It MUST NEVER be drawn as "Typical".

`UNAVAILABLE` occurs when: the lane shape is asymmetric (2v1, 1v2, tri-lane, solo core in a side lane); no opponent resolves to the viewer's lane; the viewer's lane is Jungle/Roaming/Unknown; lane or position is null for any participant; any lane opponent is missing from the parameter set (never partial-sum); or an unknown enum appears. **Fail closed.**

The lane badge MAY still render when the baseline is not ready — it needs no history.

### 10.6 Semantic guardrails (normative)

1. Lane context is an input to *expectation*. It is never an input to, explanation of, or modifier of outcome.
2. No string, card or badge may place lane context and the match result in the same sentence, claim, or causal frame.
3. **Forbidden copy:** "not your fault", "you lost because", "unwinnable", "your support was bad", any teammate-quality claim, any causal explanation of the match result, and any softening of `BELOW` because the matchup was `DIFFICULT`.
4. `PerformanceState`, `LaneContext` and `TrendState` MUST NOT be composed into one sentence. Composition, if needed, belongs to layout — not copy.
5. The four "contradictory" combinations — DIFFICULT+ABOVE+LOSS, FAVOURABLE+BELOW+WIN, DIFFICULT+BELOW+WIN, FAVOURABLE+ABOVE+LOSS — are **expected, correct output**, not defects.
6. The product MUST NOT imply the expectation explains the match. Most laning variance remains unexplained after both corrections.

### 10.7 Computation and rebuild

Computed **once** at match processing, after `effective_role` resolves. Recomputed only on role correction, metric-version bump, or parameter-set-version bump. Never at read time. A rebuild reads only stored data and makes **no provider calls**. Same inputs and versions always produce identical output.

---

## 11. Trend

### 11.1 Definition

```text
TrendState : Improving | Stable | Declining | Insufficient History
```

- A **trend point** is a baseline-ready observation paired with the rolling baseline that existed before it.
- The canonical **trend window** is the most recent **10** eligible trend points for one `bucket + role + metric + version`.
- A trend state exists **only** with a complete 10-point window. Otherwise the state is `Insufficient History`.
- Direction is derived from the movement of the rolling baseline across the window, respecting the metric's declared polarity. A numerically lower value can be `Improving` for a lower-is-better metric.
- Trend is **match-based**, never calendar-based, and never derived from win/loss, a streak, or a single hot match.
- N/A points are skipped, not zeroed. If skipping leaves fewer than 10 points, the state is `Insufficient History`.

`Insufficient History` is **not** a claim of decline. `Stable` does **not** mean nothing happened.

Exact meaningful-movement thresholds are a versioned calibration dependency. Implementations MUST NOT invent a number, use a generic cutoff, or publish a fifth state. The calibration carries one binding constraint: **the meaningful-movement threshold MUST sit above the measured hero-mix noise floor**, so that a hero-pool change is not reported as a skill change.

### 11.2 Trend is metric-level only

Each metric has its own state. The set of metric states does **not** imply a role-level state. V1 has no combined all-role curve, composite role trend, role score, player score, grade, rating, percentage, or cross-metric weighting.

The following are **not** canonical V1 behaviour:

```text
"Your Carry performance is improving."
"Carry Score: 78."
"3 of 4 metrics improved, therefore your Carry is trending up."
```

A content layer MAY describe metric-level evidence ("Laning and scaling are moving up while survival has slipped") when each statement is directly traceable to a named metric state. It MUST NOT manufacture a composite verdict, hidden weighting, or causal explanation.

### 11.3 Inactivity

Progression is match-based. V1 has **no** time decay, inactivity penalty, hard trend expiry, season reset, or Progress-owned retention cutoff. A three-month break contributes no observation and no penalty; baseline and trend history are not reset or weakened. Recency MAY be shown separately and MUST NOT be translated into a trend direction.

Calendar filters (30D, 90D, monthly) are presentation windows. They MUST NOT redefine canonical baseline or trend math.

---

## 12. Personal Bests

### 12.1 Definition

A **PB** is the current best qualifying observation for an eligible role metric within the user's current entitled history and canonical methodology.

- Scoped by `progression_bucket + effective_role + metric_id + metric_version`.
- PB history is **all** eligible measured prior observations currently known for that identity — **not** limited to the 20-observation baseline window. A value can be above the recent baseline and still not be a PB.
- PB uses the **comparison value**, not the raw/display value. A raw value can be higher while its normalized comparison value is below the existing PB; that is not a PB.
- Requires the same 5-prior gate as comparison.
- **Strict inequality only.** An exact tie is not a new PB; the earliest record/source match is retained.
- Direction honours metric polarity (lower dead-time rate is better).
- A PB always points to its qualifying **source match**, openable when accessible under the current entitlement.
- The PB preserves enough context to trace it: achieved value, hero, match date/time, effective role, mode, source match.
- If no qualifying source remains, the PB is **unavailable**.

V1 exposes only the **current** PB per eligible role metric. There is no user-facing lineage of every historical PB. V1 has Personal Best only — no Season Best.

### 12.2 Celebrations

- A newly processed eligible match MAY emit **one** `NEW_PB` event, only when it genuinely beats the canonical entitled record immediately preceding that match.
- Initial bootstrap, historical import, Pro backfill, recovery, role correction, entitlement change and methodology rebuilds MAY change current PB state but MUST NOT emit retroactive celebrations or notifications.
- If ownership changes for any of those reasons, the current PB updates **silently** to the best qualifying source. A prior celebration is never retracted or re-sent.
- On later visits, PB labelling reflects only whether the match **currently** owns the PB. V1 has no "PB at the time" label.

### 12.3 Sharing

The current PB is shareable. A share is a **timestamped snapshot** valid under the entitlement and methodology at generation time. Later corrections, entitlement changes, rebuilds or ownership changes do not retroactively alter or invalidate an already generated share.

PBs MUST NOT imply percentile rank, comparative ranking, a composite score, or unsupported causal meaning.

---

## 13. Free / Pro entitlement

### 13.1 History definitions

```text
Free History = initial bootstrap + every eligible match from the Steam-link date onward
Pro History  = Free History + recoverable historical backfill from before Steam linking
```

Free History is **permanent** for the linked Steam profile and survives Pro cancellation.

### 13.2 Locked Free value

For Free-entitled history: ongoing tracking, role-specific metric histories, canonical baselines, 10-match metric trends, current PBs, match-level baseline-at-the-time comparisons, separate Standard and Turbo progression, a monthly report, and achievement display up to the universal **Level 5** cap.

Free achievement **qualification continues** underneath the visible cap. The cap is an entitlement/display boundary, not a claim that earning stops.

### 13.3 Directional Pro value

Deeper historical context and recovered backfill; deeper monthly reporting; approximately year-scale pattern analysis; uncapped achievement levels from active Pro history; weekly recaps; challenges/missions; richer factual Match Detail highlights; medals; cosmetic or motivational experiences; additional premium synthesis.

This list is **non-exhaustive and not a permanent feature matrix**. Exact catalog, cadence, packaging, naming and pricing remain open.

### 13.4 Governing principles

1. Free and Pro use identical processing, role resolution, metric definitions, eligibility, baseline/PB calculation and methodology for any match in the applicable entitled history.
2. Pro MUST NOT be framed as more accurate, more trustworthy, or a superior measurement engine.
3. There is no separate Pro progression algorithm.
4. Pro activation and expiry are **atomic**: PBs, baselines, trends, records, achievement display and historical views switch together at one coherent checkpoint. No progressively mixed state is exposed.
5. Pro-acquired historical data is retained and reused on resubscription; retention does not keep it active in a Free-derived state.
6. A Free match remains a truthful Free-history record whether or not the user is subscribed.
7. An entitlement reduction MUST NOT masquerade as performance change. A trend may legitimately become `Insufficient History`; that is not `Declining`.

---

## 14. Rebuild and versioning

### 14.1 Two kinds of state

| Canonical current truth | Append-only historical events |
|---|---|
| Current PB indexes, baselines, comparisons, trends, records, achievements, context adjustments, entitled historical views. | Delivered `NEW_PB` celebrations, lifecycle notifications, bootstrap-completion events, audit records. |
| **MAY be rebuilt.** | **MUST NOT be fabricated, duplicated, retracted or replayed** because current truth changed. |

### 14.2 Rebuild triggers and behaviour

| Trigger | Canonical current truth | Events |
|---|---|---|
| Role correction | Rebuild the corrected match and affected later old/new-role histories in the same bucket. | Preserve delivered events; do not re-send or retract. |
| Metric-version or methodology migration | Recompute compatible retained history under **one** current methodology; use N/A where required telemetry is missing under the new definition. | Preserve prior events as audit history; no retroactive celebrations. |
| Parameter-set version bump (context model) | Deterministic replay from stored data; no provider calls. | None. |
| Pro activation / backfill | Keep coherent Free state active during import; activate Pro-derived state atomically at a coherent cutoff. | At most one product-level Pro-history-ready communication. Never one event per imported match. |
| Pro expiry | Atomically derive active state from Free-entitled history. Pro-only data stays retained but inactive. | No negative PB or downgrade celebration. |
| Pro resubscription | Reuse retained data plus newer Free matches; rebuild and activate atomically. Refetch only if coverage is genuinely incomplete. | No retroactive celebration spam. |
| Historical backfill / recovery | Insert at the true chronology position; update current truth at the approved coherent checkpoint. | No retroactive PB, achievement or match-ready events. |
| Previously unavailable history becomes available | MAY affect current best-known PBs and future comparisons per its actual match time. Already-finalized snapshots remain frozen unless an explicit authorized rebuild applies. | Previously delivered celebrations unchanged. |
| Steam switch | Start a new profile-scoped bootstrap; old profile state is archived and does not carry over. | Old profile events stay with that profile. |

### 14.3 Migration rules

- One canonical methodology at a time. Consumers MUST NOT observe a mixture where earlier points use old math and later points use new math.
- An incomplete migration keeps the previous coherent state or remains unavailable to the affected consumer. It MUST NOT publish a partial mixed timeline.
- Immutable raw source evidence is never rewritten because derived calculations changed.
- If required telemetry is unavailable for a revised metric definition, that point becomes N/A under the current definition rather than retaining an obsolete value.
- Rebuild scope is the **smallest dependency closure**. "Rebuild everything" is not a substitute for identifying the affected metric, track, bucket and chronology boundary. An unrelated role or bucket is never rebuilt because another track changed.
- Rebuilds are **deterministic and idempotent**: running twice produces no additional observations, PB events or notifications.
- Migration is not a season reset, inactivity reset, or new progression epoch.

---

## 15. Canonical vocabulary

These distinctions must survive any visual redesign.

| Term | Meaning |
|---|---|
| **Baseline at the time** / **baseline before this match** | The comparison reference that existed before that match. Used in historical Match Detail. |
| **Current baseline** | The present-day reference used on Progress and Home. MUST NOT be used ambiguously for an old match's comparison. |
| **Your usual** | The personal rolling-baseline median. Used only for the player's own metrics, never for population data. |
| **Adjusted expectation** | Baseline plus the selective hero and lane-opponent adjustments. An expectation — not a prediction, not a win probability, not a judgment. |
| **N/A** | Unavailable or not meaningfully calculable. **Not zero.** |
| **Does not count toward progression** | Must always be paired with the applicable reason for a READY but ineligible match. |
| **Current PB** | Present canonical PB ownership under the current entitlement and methodology. |
| **NEW_PB** | A one-time event emitted when a newly processed eligible match set a record against the preceding entitled history. |
| **READY** | Complete factual processing. Not necessarily progression eligibility, and not necessarily numeric values for every metric. |
| **Effective role** | The role shown to the player, with Edit Role available while retained data supports correction. |
| **Difficult / Typical / Favourable matchup** | On-paper drafted opponent context. **Not** a statement about what happened in the lane, and never a reason for a result. |
| **Free vs Pro** | Different history depth, synthesis and engagement — never different measurement accuracy. |
| **Progression** | A set of role/metric signals. Never a single overall player judgment. |

---

## 16. Forbidden behaviour (cross-product)

No surface may:

- present an overall match score, letter grade, composite performance score, player rating, skill radar, percentile or "top X%";
- present a combined all-role progression curve or composite role trend;
- use win/loss, MMR or KDA as a proxy for personal progression;
- explain *why* a match was won or lost;
- attribute anything to a teammate, or imply teammate quality;
- imply a difficult matchup caused a loss, or soften a below-expectation verdict because of context;
- render N/A as zero, or an unavailable state as a neutral/typical default;
- imply causality where only sequence is observed;
- claim rank, bracket, MMR, behaviour score, or any provider-derived impact/award score;
- invent content to keep a chart, card or slot populated;
- present Pro as more accurate;
- fabricate a comparison when history is insufficient.

---

## 17. Cross-feature ownership

| Concern | Authoritative owner |
|---|---|
| Identity, lifecycle, roles, metrics, baselines, context adjustment, trend, PB, entitlement, rebuild, vocabulary | **This document** |
| First-time account creation, Steam linking, bootstrap, cold-start data outcomes | `onboarding/SSOT.md` |
| Daily entry surface, Today's Focus/Matches, role summaries, Last 5 | `home/SSOT.md` |
| Chronological match browsing and navigation | `history/SSOT.md` |
| Single-match review, personal performance presentation, insight cards, role correction entry | `match_detail/SSOT.md` |
| Role progression deep-dive, metric timelines, trend presentation | `progress/SSOT.md` |
| Long-term player identity, claims, hero identity, current-form strip, PB display | `profile/SSOT.md` |
| Ongoing account management, Steam switching, subscription, notification permission, deletion | `settings_account/SSOT.md` |
| Post-match insight card algorithms, thresholds, ladders, classifier constants | `_archive/engine_specs/POST-MATCH-INSIGHTS-SSOT.md` + its JSON contract (engineering-normative, subordinate to `match_detail/SSOT.md` for product meaning) |
| Context-adjustment parameter derivation, coefficients, caps, validation evidence | `_archive/engine_specs/CONTEXT-ADJUSTED-PERFORMANCE-V1.md` (same subordination) |

---

## 18. Product-level acceptance rules

- [ ] Standard history never changes a Turbo baseline, trend, PB, queue or history, and vice versa.
- [ ] Every successfully classified retained match has exactly one effective role; P4/P5 are Support.
- [ ] A classifier rerun never overwrites the latest explicit user role assertion.
- [ ] Processing never waits for role confirmation; low-confidence prompting is corrective only.
- [ ] Every retained match with sufficient telemetry exposes Edit Role.
- [ ] A role correction rebuilds only the same-bucket old/new-role dependency closure, deterministically and idempotently, with no provider calls.
- [ ] Discovery records all items before advancing its cursor and resumes without gaps or duplicate effects.
- [ ] A later same-bucket match cannot finalize ahead of an older unresolved predecessor; the other bucket is never blocked.
- [ ] READY has no partial variant and may coexist with N/A metrics or `NONE(reason)`.
- [ ] A provider/source failure is never relabelled as progression ineligibility to obtain READY.
- [ ] Automatic retries are bounded; manual Retry resumes the earliest unresolved stage without duplicating the match or its effects.
- [ ] A historical Match Detail never silently compares against today's baseline.
- [ ] A missing baseline produces an explicit baseline-building state, never a synthetic comparison.
- [ ] A READY but ineligible match remains viewable, states that it does not count, and gives the reason.
- [ ] Baseline is the previous-20 **median** after a 5-prior gate; trend needs a complete 10-point window.
- [ ] No time decay, inactivity reset, Progress-specific retention cutoff, composite role trend, or overall progress score exists.
- [ ] A current PB always points to its qualifying source match under the current entitlement and methodology; ties are not PBs.
- [ ] PB comparison uses the comparison value and all known eligible history, not the 20-observation window.
- [ ] Imports, backfills, recovery, entitlement changes and rebuilds never generate retroactive celebrations or notification spam.
- [ ] Context adjustment reads no realised in-match behaviour, no teammate hero, and no outcome.
- [ ] Lane context never appears in the same claim as the match result, and never softens a BELOW state.
- [ ] `UNAVAILABLE` lane context renders nothing and is never drawn as `Typical`.
- [ ] `offlane.objective_involvement.v1` emits no performance state.
- [ ] A metric whose baseline median sits at its floor receives no population adjustment.
- [ ] Notification permission or device state never gates processing, readiness, progression or account state.
- [ ] No surface introduces a score, grade, composite judgment, causal result explanation, teammate claim, or opaque AI verdict.

---

## 19. Deferred decisions

Intentionally not locked. These MUST NOT be filled by inference merely to make a screen or implementation look complete.

- Exact Pro historical acquisition mechanism, lifetime ceiling and coverage economics.
- Account-recovery verification, fraud controls, support escalation, ownership disputes; any account-merge product.
- Achievement XP curves, milestone and qualification definitions beyond the Free Level-5 display cap.
- Challenge / mission mechanics, recommendation design, medals, cosmetics and motivational systems.
- Exact Pro feature catalog, pricing, packaging, paywall UI, and report content/cadence beyond the locked Free monthly direction.
- Classifier scoring weights, calibration and low-confidence thresholds.
- Per-metric meaningful-movement thresholds for Improving/Stable/Declining (subject to the hero-mix noise floor constraint in §11.1).
- Implementation policy: retry backoff, storage, API/provider query shape, pagination, queueing, OS scheduling.
- Career-history visualization and higher-order findings/report eligibility.
- All UI layout, navigation, copy, animation and visual treatment.

---

## 20. Known production conditions

The context-adjustment model carries three mechanical production-validation conditions, inherited from its approved research. They are engineering obligations, not open product questions:

1. The provider's CS-count field semantics are undocumented; the empirical relationship MUST be frozen with a regression test that fails if it drifts.
2. The lane-opponent parameter pool MUST cover ≥ 97% of lane opponents; one week of data is insufficient, so production MUST pool a rolling multi-week window and verify coverage before publishing a parameter set.
3. Adjustment caps MUST ship with the model.

A failed parameter validation keeps the previous artefact and degrades to zero adjustment — never to a wrong number.

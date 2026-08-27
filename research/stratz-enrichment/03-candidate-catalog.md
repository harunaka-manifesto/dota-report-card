# Candidate catalog

> **Eligible-population caveat, applied everywhere below.** V6.1 excludes only
> `_MATERIAL_ABANDON_STATUSES = {2,3,4,5}`. STRATZ returns a `LeaverStatusEnum`
> string and the mapping of `DISCONNECTED` onto that integer contract is
> **BLOCKED** (`05-blocked-and-queries.md`). On the specimen the two readings
> give **49** eligible matches (`DISCONNECTED` → 1, not material) or **45**
> (`DISCONNECTED` → 2..5, material) — a 365-day extrapolation of **293** or
> **269**. Figures below use the **49 / 293** reading, which is the one V6.1's
> rule most likely produces, and every derived number carries that dependency.

---

## 0. The cost cliff that organizes everything

Before ranking, one structural fact that the brief did not anticipate and that
changes what "expensive" means.

`position`, `role`, `lane` and `gameVersionId` are fields on `MatchPlayerType`
and `MatchType` — they are returned **by the history pull itself**. The
specimen proves it: `Q3_ParityPage` is one request per 100 matches and it
carries `position` at 91%, `role` at 93%, `lane` at 93%, `gameVersionId` at 100%.

Everything else parsed — `stats`, per-minute arrays, event timestamps, item
purchases, wards, runes, lane outcomes, lead curves — lives under
`match(id:)` or `MatchPlayerType.stats`, and costs **one request per match**.

| tier of evidence | requests per player-year | vs V6.1 today |
|---|---|---|
| V6.1 today (OpenDota) | 1 | 1× |
| STRATZ history pull (`take: 100`, ~597 matches) | ~6 | 6× |
| STRATZ history + role/patch fields | ~6 (**same requests**) | 6× |
| + per-match parsed on eligible matches (~293) | ~299 | **~300×** |
| + playback | ~299 requests, ≥1.3 GB | prohibitive |

Against a **10,000/day** ceiling the history tier supports ~1,600 reports/day
and the per-match parsed tier ~33. **That ceiling is quoted from the brief
(§"Verified STRATZ capabilities"), not measured by this research** — no payload,
response header or probe artifact in `.local/stratz-probe/` records a rate
limit. Recording observed rate-limit headers is on the corpus protocol's list
precisely because of this. The *ratio* between tiers is measured; the absolute
reports/day figures inherit the brief's number.

**This is the single most important number in this research.** It means the
first STRATZ-native analytical generation should be built almost entirely from
the history tier — where role becomes visible at 91% for zero marginal cost —
and per-match parsed evidence should be treated as a second, separately
justified investment.

One unknown could collapse the cliff: `PlayerMatchesRequestType.matchIds:
[Long]` accepts a list. If N parsed matches can be batched into one request
under the 310,000 complexity ceiling, per-match parsed cost drops by roughly N×.
**This is the highest-value blocked question in the whole document** — see
`05-blocked-and-queries.md` C1.

---

## 1. Raw candidates

Fifty-two, grouped by domain. Each names a **behaviour**, the verified STRATZ
path that would evidence it, and a first-pass A–G classification. `[H]` =
computable from the history pull (no marginal request cost). `[M]` = needs a
per-match parsed query. `[P]` = needs playback.

### Role identity — `players[].position`, `players[].role` `[H]`

1. Plays more than one role habitually — `role` distribution entropy — **C**
2. Has a role the hero pool does not predict — `role` × `heroId` — **C**
3. Role mix changed across the year — `role` × `startDateTime` thirds — **C**
4. Plays the same hero in different roles — `heroId` × `position` — **C**
5. Role breadth is narrower than hero breadth — `role` vs `heroId` entropy — **C**
6. Hero pool is role-partitioned (distinct heroes per role) — `heroId` × `role` — **C**
7. Support games and core games have different hero-pool shapes — **C**
8. Switches role after a loss — `role` × prior `isVictory` — **C**
9. Off-role games cluster in specific sessions — `role` × `session_id` — **C**
10. Role stretch vs hero stretch as separate transfer frontiers — **C**

### Lane assignment and lane outcome — `lane`, `*LaneOutcome` `[H]`/`[M]`

11. Lane assignment stability within a role — `lane` × `role` `[H]` — **E**
12. Wins or loses lane — `*LaneOutcome` × player `lane`+`isRadiant` `[M]` — **C**
13. Lane outcome and match outcome disagree — as above + `isVictory` `[M]` — **C**
14. Plays from behind after a lost lane — `*LaneOutcome` + `radiantNetworthLeads` `[M]` — **C**
15. Roams (assigned lane ≠ occupied lane) — `lane` vs `playerUpdatePositionEvents` `[P]` — **G** (playback cost)
16. Jungle assignment frequency — `lane == JUNGLE` `[H]` — **G** (n=1 in specimen)

### Farm, XP, net worth trajectory — per-minute arrays `[M]`

17. Farm rate rises or falls across the game — `lastHitsPerMinute` — **C**
18. Net worth curve shape vs hero/role baseline — `networthPerMinute` — **C**
19. XP timing: reaches key levels early or late — `stats.level` timestamps — **C**
20. Level-up cadence flattens mid-game — `stats.level` gaps — **C**
21. Farms through the lull or fights through it — `lastHitsPerMinute` vs `heroDamagePerMinute` — **C**
22. Gold efficiency: earns vs spends — `goldSpent` vs `networth` — **E**
23. Recovers economy after death — `networthPerMinute` around `deathEvents` — **C**
24. Stacks camps — `campStack` — **C** (role-conditional)
25. Fountain trips as a tempo signal — `tripsFountainPerMinute` — **G** (semantics unclear)

### Combat participation and timing — event arrays + match kill series `[M]`

26. Share of team kills participated in — `killEvents`+`assistEvents` ÷ `radiantKills`/`direKills` — **B**
27. Participation is front-loaded or back-loaded — participation instants × time — **C**
28. Kills cluster (teamfights) vs spread (pickoffs) — `killEvents` inter-arrival — **C**
29. Deaths cluster or spread — `deathEvents` inter-arrival — **C**
30. Deaths concentrate in a game phase — `deathEvents` × time bucket — **C**
31. Dies while team is ahead vs behind — `deathEvents` × `radiantNetworthLeads` — **C**
32. Damage taken vs dealt ratio over time — `heroDamageReceivedPerMinute` (cumulative) vs `heroDamagePerMinute` — **C**
33. Present in the first fight — `firstBloodTime` vs `killEvents`/`assistEvents` — **E**
34. Late-game participation holds or fades — participation × final third — **C**

### Item behaviour — `stats.itemPurchases` `[M]`

35. Buys the same core items in the same order — `itemPurchases` sequence — **C**
36. Build order varies by opponent draft — `itemPurchases` × enemy `heroId` — **D** (new family)
37. Buys a defensive item earlier after a bad lane — `itemPurchases` × `*LaneOutcome` — **C**
38. Consumable spend rate — `itemPurchases` consumable ids — **E**
39. Buys back — `buyBackEvents` `[P]` or inferred from `networthPerMinute` drop — **C**
40. Final inventory converges regardless of build path — `item0..5Id` `[H]` — **G** (`M12` rejection stands)

### Skill build — `abilityLearnEvents` `[P]`

41. Same skill order every game on a hero — `abilityLearnEvents` — **C**
42. Skill order adapts to lane outcome — as above × `*LaneOutcome` — **C**

### Vision and support economy — `stats.wards` `[M]`

43. Wards consistently, or in bursts — `wards{time}` — **C** (role-conditional)
44. Ward placement concentrates in a map region — `wards{positionX,positionY}` — **C** (role-conditional)
45. Warding survives a losing game state — `wards` × `radiantNetworthLeads` — **C**
46. Dewards — `wardDestruction` — **BLOCKED** (shape unknown)

### Rune and objective behaviour `[M]`

47. Contests bounty runes on schedule — `runes{time, rune}` — **C**
48. Rune type mix — `runes.rune` — **E**
49. Present for tower kills — `towerDamagePerMinute` + `match.towerDeaths` — **BLOCKED** (shape unknown)
50. Roshan participation — `playbackData.roshanEvents` — **G** (field returned empty on a 60-min game; unreliable)

### Match context and team `[H]`/`[M]`

51. Plays with a party or solo — `partyId` `[H]` — **G** (8% coverage; null semantics unestablished)
52. Team tempo as a confounder control — `radiantKills`+`direKills` `[M]` — **E**

---

## 2. Deduplication and correlation clustering

Fifty-two raw ideas are not fifty-two hypotheses. Collapsing:

| cluster | absorbs | one hypothesis because |
|---|---|---|
| **Role Shape** | 1, 2, 5, 6, 7, 11 | All are functions of the same `role`×`heroId` contingency table. Ten variations on "how is this player's role mix distributed" is one question. |
| **Role Migration** | 3, 9 | Both are role mix × time. |
| **Role/Hero Transfer Split** | 4, 10 | Same core/stretch machinery, split on a new axis. |
| **Result-Shaped Role** | 8 | Distinct — it is a *transition* denominator, not a match denominator. Stays separate. |
| **Kill Participation** | 26, 27, 33, 34 | All are the participation series read at different resolutions. |
| **Death Structure** | 29, 30, 31 | All are the death-time series read differently. |
| **Economy Trajectory** | 17, 18, 20, 21, 22, 23 | Heavily correlated: farm rate, net worth curve, level cadence and gold efficiency are near-restatements of one economic tempo. **This is the single most over-generated cluster** — the temptation is to ship six charts of the same fact. |
| **XP Timing** | 19 | Kept separate from Economy Trajectory *only* because `stats.level` timestamps are a genuinely different measurement (event times, not rates). If it correlates > 0.8 with net worth curve in the corpus, merge it. |
| **Lane Outcome** | 12, 13, 14 | One measurement, three framings. |
| **Item Signature** | 35, 37, 38 | Build order and build timing are one behaviour. |
| **Vision Behaviour** | 43, 44, 45 | One behaviour, role-conditional. |
| **Adaptation** | 36, 42 | Both are "does the player change plan in response to context". |

**Unclustered remainder — stated rather than quietly dropped.** The table above
absorbs 36 of the 52 raw ideas. The other 16 fall into three groups:

- **Blocked, so unclusterable:** 46 (`wardDestruction`), 49 (`towerDeaths`) —
  shapes unknown, no letter can be defended yet.
- **Rejected outright** (see §7): 15, 16, 25, 40, 50, 51 — seven ideas whose
  disposition is `G` and which therefore consume no multiplicity budget.
- **Standalone, carried but unranked in this pass:** 24 (`campStack` — the field
  is `UNDETERMINED` per field-inventory §2.2), 28 (kill clustering), 32 (damage
  taken vs dealt), 39 (buybacks), 41 (skill order), 47 (bounty runes), 52 (team
  tempo as a control), 8 (`Result-Shaped Role`, which is a *transition*
  denominator and does not share the match denominator of the role cluster).
  These are real candidates that did not make the ranked shortlist; they are
  recorded here so a later pass does not have to rediscover them.

**52 raw → 12 clusters + 8 standalone + 2 blocked + 6 rejected.** The **12
clusters plus the 8 standalone = 20 live hypotheses**, and 20 — not 52, and not
12 — is the number that must enter any family/branch FDR structure if all of
them are ever pursued at once. The ranked shortlist below deliberately pursues
far fewer.

**Note on the ranked table:** it scores the 11 clusters that produce a
player-facing claim, plus `Post-loss control upgrade`, which is not one of the
52 raw ideas at all — it is an *enhancement to existing machinery* surfaced by
the reassessment rather than a new behaviour. It is scored alongside them so the
tiering can compare like with like.

---

## 3. Ranking model

Twelve criteria, weights summing to 100. Each candidate scored 1–5.

| criterion | weight | why this weight |
|---|---|---|
| Analytical defensibility | **20** | The highest single weight, because this is the one property that cannot be recovered later. A shareable finding that is wrong damages the product permanently; a defensible finding that is dull can be re-presented next quarter. |
| Role fairness | **14** | Second-highest, because it is the specific failure mode this dataset invites. Every economy signal flatters cores; every vision signal flatters supports. On the specimen 41% of eligible matches (20/49) are supports — a core-biased metric would misdescribe two games in five for this player. |
| Sample availability | **14** | Equal to role fairness. A finding that fires for 4% of players is a research result, not a product. Opportunity count, not match count. |
| Player resonance | **12** | The lead onstage criterion — does a Dota player recognise themselves. |
| Identity value | **10** | Distinct from resonance: does it say something *stable* about who they are, rather than what happened. |
| Patch robustness | **7** | Meaningful but recoverable — a patch-fragile finding can be re-gated later. |
| Novelty | **5** | Deliberately low. "Nobody else shows this" is worth little if it is not also true and legible. |
| Shareability | **5** | Deliberately equal to novelty and a quarter of defensibility. Shareability is an amplifier, not a source of value. |
| Visualization potential | **4** | |
| Actionability | **4** | Low on purpose. This is an identity product, not a coaching product; "here is who you are" does not need a fix attached. |
| Implementation complexity (inverted) | **3** | |
| STRATZ query cost (inverted) | **2** | Low **as a scoring weight** because it is a one-time engineering economics question — but the §0 cost cliff is handled structurally through tiering instead, which is a stronger control than a 2-point score. |

Defensibility + role fairness + sample availability = **48**. Resonance +
identity + shareability + visualization + actionability = **35**. That ratio is
the "pharma backstage, Wrapped onstage" principle expressed as arithmetic:
truth-properties outweigh presentation-properties, but not overwhelmingly,
because a true finding nobody feels is also a failure.

### Scores

| candidate | def | fair | samp | res | ident | patch | nov | share | viz | act | impl | cost | **score** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Role Shape | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 5 | 5 | 3 | 4 | 5 | **96.8** |
| Role/Hero Transfer Split | 4 | 5 | 4 | 5 | 5 | 4 | 5 | 4 | 4 | 3 | 3 | 5 | **87.2** |
| Role Migration | 4 | 5 | 3 | 5 | 5 | 4 | 4 | 5 | 5 | 2 | 4 | 5 | **85.0** |
| Kill Participation | 4 | 4 | 4 | 5 | 4 | 4 | 3 | 4 | 4 | 3 | 3 | 1 | **78.8** |
| Post-loss control upgrade | 5 | 5 | 4 | 3 | 3 | 5 | 2 | 2 | 2 | 2 | 5 | 5 | **77.6** |
| Lane Outcome | 4 | 4 | 4 | 5 | 3 | 3 | 4 | 5 | 4 | 3 | 3 | 1 | **77.4** |
| Item Signature | 3 | 3 | 3 | 5 | 4 | 2 | 4 | 5 | 4 | 3 | 2 | 1 | **67.8** |
| XP Timing | 3 | 3 | 4 | 4 | 3 | 2 | 5 | 4 | 4 | 2 | 3 | 1 | **66.0** |
| Death Structure | 3 | 3 | 4 | 4 | 3 | 3 | 3 | 3 | 4 | 2 | 3 | 1 | **64.4** |
| Adaptation | 2 | 3 | 2 | 5 | 5 | 2 | 5 | 5 | 3 | 3 | 1 | 1 | **62.6** |
| Vision Behaviour | 3 | 2 | 2 | 4 | 4 | 3 | 4 | 4 | 5 | 2 | 3 | 1 | **60.8** |
| Economy Trajectory | 2 | 2 | 4 | 4 | 3 | 2 | 2 | 3 | 4 | 2 | 3 | 1 | **55.2** |

Scores are `sum(weight * score) / 5`, computed in `analyze.py`-style arithmetic
rather than by hand.

### Where the score is deliberately overridden

The ranking is an input, not the decision. Two overrides:

**The three role candidates are correlated, and the score cannot see it.**
Role Shape (96.8), Role/Hero Transfer Split (87.2) and Role Migration (85.0) are
all functions of the same `role` field on the same matches. They rank 1-2-3
because they share the same virtues — free, role-fair, high-resonance — not
because they are three discoveries. Shipping them together would triple the
role-based multiplicity load for one underlying finding and would make the
report's onstage story repetitive ("you play several roles", "you play several
roles over time", "you stretch across roles"). **Role Shape is the parent and
goes first. The other two are gated on it validating**, and are specified in
Tier 1-adjacent rather than shipped alongside.

**Post-loss control upgrade ranks 5th and is still Tier 1**, because it is the
only candidate in the catalog that **costs zero multiplicity budget**. It adds
no hypothesis, no branch, no copy and no family. The additive score has no
column for "makes existing published findings more trustworthy without asking
for anything", and that property is worth more than the 0.2 points separating
it from Lane Outcome.

## 4. Tier 1

Two candidates, both `[H]` — computable from the history pull at **zero
marginal request cost**. That is not a coincidence; it is the §0 cliff doing
its job. One is the highest-scoring candidate in the catalog; the other is the
only one that asks for nothing.

### T1-A · Role Shape

**Opportunity classification: C. NEW_SUBFINDING** under `pool_shape`.

Defended: it is a new behaviour under an existing family, not a new family.
`pool_shape` already asks "what is the shape of what this player chooses";
role mix is a second axis of the same question. It is not `D. NEW_FAMILY`
because it shares the family's null structure, opportunity unit and copy
register — spinning up a sixth family would expand the BH denominator from 5 to
6 and dilute every existing family's power for no conceptual gain.

#### Product

- **Question answered:** "Do I play one role or several, and does my hero pool
  agree with my role pool?"
- **Why a player cares:** role identity is the most-discussed, least-measured
  thing in Dota self-description. Every player has a story about what they play;
  almost none have a measurement.
- **Identity resonance:** very high, and *stable* — role mix moves slowly.
- **Actionability:** low by design. This is identity, not advice.
- **Shareability:** high; it is a single sentence with a number.
- **Example headline:** "Three roles, one pool."
- **Example explanation:** "Across 49 reviewed matches you played a core role in
  29 and a support role in 20 — but only two of your eighteen heroes appear on
  both sides. You switch roles by switching heroes."
- **Grounded in the specimen, not invented:** 2 of 18 eligible-set heroes are
  played in both a core and a support role (heroes 136 and 105); the other
  sixteen are role-exclusive. The overlap term is *small* on this player, and
  that is the finding — a role-partitioned pool is as interesting as a shared
  one. **Do not assume overlap is the interesting direction**; the copy must
  read both ways.
- **Visualization:** hero pool as a set, coloured by role share per hero;
  the degree of partition is the finding.

#### Data

- **Paths:** `player.matches[].players[].role`,
  `player.matches[].players[].position`, `player.matches[].players[].heroId`,
  `player.matches[].startDateTime`.
- **Source object:** `MatchPlayerType` — returned by the history query.
- **Replay-parsed dependency:** yes — `role`/`position` are null on unparsed
  matches (A4). Coverage 93%/91% on the specimen.
- **Request cost:** **zero marginal**. Already in the ~6-request history pull.
- **`playbackData` needed:** no.
- **Derived feature:**
  ```
  eligible          = matches passing V6.1 eligibility AND role IS NOT NULL
  role_bucket(m)    = "core" if role == CORE else "support"
                      (POSITION_4/5 distinguished only in evidence, never in copy)
  role_effective    = exp(H(role distribution over eligible))       # 1.0 .. 3.0
  hero_effective    = exp(H(heroId distribution over eligible))
  role_hero_overlap = sum over heroes of min(core_share_h, support_share_h) * 2
  ```
  `role_effective` uses `role` (3 levels), not `position` (5 levels), because
  `position` is 2pp sparser and because five-level copy collides with
  `FORBIDDEN_FREE_TERMS`.

#### Statistical design

- **Unit of analysis:** the match. **Clustering: match → session → player.**
- **Opportunity definition:** an eligible match with non-null `role`.
- **Minimum opportunities:** 30, matching `MIN_ELIGIBLE_MATCHES`. Additionally
  ≥8 independent sessions.
- **Repeated measures:** heroes recur; sessions recur. Resample **complete
  sessions**, consistent with `clustered_bootstrap`.
- **Confounders:** game mode (Turbo excluded already); parsed availability
  (§below); hero (a one-hero player has role mix determined by that hero);
  patch (`gameVersionId`) — role meta shifts.
- **Role normalization:** not applicable — role *is* the measurement. This is
  the only candidate in the catalog with no role-fairness exposure at all,
  which is why it scores 5.
- **Hero normalization:** required for the overlap term. A player who only
  plays flexible heroes (hero 136 appears as `CORE`, `LIGHT_SUPPORT` and
  `HARD_SUPPORT` across 17 eligible matches) will show overlap for reasons of hero choice, not role identity.
  Control by comparing observed overlap against the overlap expected from the
  hero pool's own role distribution in the baseline corpus.
- **Duration normalization:** not applicable.
- **Effect definition:** `role_effective` against a population baseline;
  overlap against its hero-conditional expectation.
- **Uncertainty:** clustered bootstrap over complete sessions, 2000 iterations.
- **Stability:** zone classification stable in ≥90% of replicates for `high`
  confidence, per `MetricThreshold.supports_confidence`.
- **Multiplicity family:** `pool_shape`. Adds branches to an existing family;
  does **not** add a sixth family root.
- **Negative control:** shuffle `role` labels within player, holding the hero
  sequence fixed. `role_effective` must collapse toward the null and the
  overlap term must lose significance. If it does not, the statistic is reading
  hero pool, not role identity.
- **Publication criteria:** family q ≤ 0.05 after BH over five families; branch
  q ≤ 0.05 within a qualified family; ≥30 role-eligible matches; ≥8 sessions.
- **Invalidation:** role coverage < 0.80 in the reviewed window; a single hero
  accounting for > 60% of eligible matches.

#### Product safety

- **Outcome leakage:** none. `isVictory` is not an input.
- **Causality overstatement:** low risk; the claim is descriptive.
- **Role bias:** none — this is the candidate that *fixes* role bias.
- **Core/support fairness:** symmetric by construction.
- **Hero-specific bias:** real, handled by the overlap control above.
- **Sparse-data risk:** a single-role player yields `role_effective ≈ 1.0`,
  which is a valid and interesting result, not an abstention.
- **Patch fragility:** low. Role identity is more stable than any metric.
- **Privacy:** none beyond what V6.1 already handles.

#### Validation

- Development corpus per `04-corpus-lineage-roadmap.md`; role mix must be a stratifier.
- Calibration: `role_effective` population distribution, derived on the
  development split only.
- Backtest: recompute on existing OpenDota-derived reports — expected to be
  **impossible**, which is itself the confirmation that this is genuinely new.
- Sealed holdout: **fresh**. The existing V6.1 holdout under
  `.local/calibration/v61/release-recovery-7df38e6/sealed-holdout/` must not be
  touched.
- Dota-player manual review: required. Show ten players their role shape and ask
  whether it matches their self-description.
- Regression: none — additive branch under an existing family.

### T1-B · Post-loss control matching upgrade

**Opportunity classification: A. ENHANCE_EXISTING.**

Defended: no formula, opportunity definition, claim or copy changes. Only the
*control set* changes, because the context keys it matches on become populated.
It is not `B. REPLACE_PROXY` because no proxy is being replaced — the same
matching rule simply starts working.

#### Product

Nothing changes onstage. `one_loss_runback`, `two_loss_switch`,
`result_shaped_pool` and `result_invariant_response` keep their headlines and
explanations. What changes is how often they can be said, and how honestly.

#### Data

- **Paths:** `match.gameVersionId`, `players[].role`, `players[].position`,
  plus the existing K/D/A and duration fields.
- **Request cost:** **zero marginal.**
- **Derived feature:** `_same_comparable_context` (`post_loss.py:72-80`)
  currently backs off through
  `patch+lane_context+hero_function` → `patch+lane_context` → `patch` → anything.
  Under OpenDota, `patch` ≈ 2.5% and `lane_context` ≈ 2.5%, so **matching
  degrades to "anything" on essentially every transition.** With
  `gameVersionId` at 100% and `role` at 93%, level-0 matching becomes
  achievable for the first time.

- **Derived feature:**
  ```
  context_key(m, level) =
      0: (gameVersionId, role, hero_function)
      1: (gameVersionId, role)
      2: (gameVersionId,)
      3: ()                       # unchanged four-level backoff
  # the ONLY change: lane_context <- role (93%), patch <- gameVersionId (100%)
  # formula, effect, ROPE, opportunity rule and copy are all untouched
  ```

#### Statistical design

- **Unit:** the loss→next transition. **Clustering: transition → session → player.**
- **Opportunity:** adjacent same-session pairs where the previous match was a
  loss. `min_transitions = 30`, `min_sessions = 12`, `min_coverage = 0.50` —
  all unchanged.
- **Confounders:** this candidate *is* confounder control. Its risk is the
  opposite one — **matching too tightly shrinks the control pool** and inflates
  variance. Mitigation: keep the four-level backoff and *record the level used*
  per transition, then publish the fallback-level distribution as evidence.
- **Effect:** unchanged — after-loss minus matched-control, per component.
- **Uncertainty:** unchanged.
- **Multiplicity:** unchanged. **No new hypothesis is created.** This is the
  only candidate in the catalog that costs zero multiplicity budget.
- **Negative control:** re-run with the control matcher forced to level 3
  ("anything"). Any effect that survives tight matching but vanishes under loose
  matching, or vice versa, is a matching artifact.
- **Publication:** unchanged.
- **Invalidation:** if level-0 match rate stays below 30% of transitions, the
  upgrade has not delivered and should not be claimed as one.

#### Product safety

- **Outcome leakage:** the family is *about* outcome transitions; this is
  existing, accepted design, not new exposure.
- **Role bias:** improved — controls now match on role, so a post-loss role
  switch is no longer silently compared against a core-heavy control pool.
- All other axes: unchanged from V6.1.

#### Validation

- Backtest is meaningful here and should be run: recompute `post_loss_response`
  on the development corpus with and without the upgraded matcher, and report
  the change in qualification rate and in effect size. **If effect sizes move
  materially, that is evidence the current published findings were confounded** —
  which is a finding the owner needs before any release decision.
- Fresh sealed holdout required.

---

## 4b. Tier 1-adjacent — gated on T1-A validating

Both are `[H]`, both outscore everything in Tier 2, and both are held back only
because they are correlated with T1-A (see §3). If Role Shape validates on the
development corpus and survives Dota-player review, these promote immediately
and cheaply. If Role Shape does *not* validate, both die with it — which is
exactly why they should not be built in parallel.

### T1-C · Role/Hero Transfer Split — **C. NEW_SUBFINDING** (`transfer`)

V6.1's `transfer` compares a familiar hero band against a stretch band. With
`role` observed, "new hero, same role" and "same hero, new role" separate — and
they are different experiences to a player.

**Frequency is the open question, and the specimen argues *against* the
optimistic reading.** 20 of 49 eligible matches are supports, so role variety is
high — but only **2 of 18 heroes** are played in both a core and a support role.
This player changes role by changing hero, which means same-hero role-stretch
events may be rare. The corpus must measure the rate of same-hero role change
before this candidate is promoted; if it is rare, T1-C collapses into T1-A and
should not ship separately.

Derived feature:
```
core_heroes    = existing 60%-mass frozen core set          # unchanged
role_mode(h)   = most frequent role for hero h in-window
band(m) = "familiar"      if hero in core_heroes and role == role_mode(hero)
          "hero_stretch"  if hero not in core_heroes and role == role_mode(hero)
          "role_stretch"  if hero in core_heroes and role != role_mode(hero)
          "both"          otherwise      # excluded, not double-counted
```
Paths: `players[].role`, `players[].heroId`, plus the existing outcome/activity/
survival components. Zero marginal request cost. Unit: the match; clustering
match → session → player. Opportunity denominator: matches, minimum 12 per band
(matching `continuous_transfer`'s existing band-support rule). Hero bias:
inherits `transfer`'s existing hero controls. Version impact: `findings`,
`semantic_outcomes`, `recommendations` and `copy` all **changed**. It splits `clean_transfer`, which carries
`recommendation_key = "verify_transfer"` — so the five-game verification
contract splits with it, and that is the main implementation cost.

Chief risk: the two bands are not independent. A player stretching to a new hero
*in* a new role contributes to both. Assignment must be pre-declared and
exclusive, not computed twice.

### T1-D · Role Migration — **C. NEW_SUBFINDING** (`pool_shape`)

Role mix across the three exact chronological thirds `pool_shape` already uses.
"You became a support this year" is a strong identity claim and V6.1 cannot
make it.

Derived feature: `role_dist(third_i)` = normalized `role` histogram over the
i-th chronological third; effect = Jensen-Shannon divergence between thirds 1
and 3, reusing `pool_shape`'s existing JSD machinery. Paths: `players[].role`,
`match.startDateTime`. Zero marginal cost. Unit: the match, bucketed into
thirds; clustering match → session → player. Opportunity denominator is matches,
minimum 30, with ≥8 matches in each third — thirds with too few matches must
abstain rather than report a swing. Confounders: patch (role meta moves), hero
availability, and the player's own activity rate across the year. Hero bias:
a player who acquires one flexible hero mid-year will show role migration for a
hero-pool reason; control against the hero-conditional expectation as in T1-A.
Version impact: `findings`, `semantic_outcomes`, `copy` **changed**.

Chief risk: **this is a trend claim on a single time series**, which is where
spurious structure lives. It must reuse `pool_shape`'s existing
Jensen-Shannon movement machinery and its 0.06 ROPE rather than introducing a
new test, and the ROPE must be re-derived against observed roles rather than
inherited from the taxonomy-job calibration.

## 5. Tier 2

Both need per-match parsed queries and therefore sit behind the §0 cost cliff
and the C1 batching question.

### T2-A · Kill Participation Share — **B. REPLACE_PROXY** (`combat_expression`)

**What would have to be true to promote it:** (1) C1 resolves such that parsed
matches can be batched, bringing cost within budget; (2) the participation
denominator proves role-fairer than `(K+A)/min` on the development corpus.

- **Paths:** `match.radiantKills`, `match.direKills`,
  `players[].stats.killEvents{time}`, `players[].stats.assistEvents{time}`,
  `players[].isRadiant`.
- **Verified computable.** On A2: 21 kills + 22 assists = 43 distinct
  participation instants; the player's team recorded 68 kills; share = **63.2%**.
- **Critical semantics:** `radiantKills`/`direKills` count **opposing hero
  deaths**, not scoreboard kills (field inventory §2.3). On A2 the Dire array
  sums to 68 while Dire scoreboard kills sum to 67 — one radiant death credited
  to no player. Use the array as the denominator (it is the true count of
  killable events the player could have been present for), and **document the
  discrepancy**, or the share is silently inflated in matches with tower/creep
  deaths.
- **Unit:** the match. **Clustering: event → match → session → player.** Forty-three
  participation instants in one match are one observation, not forty-three.
- **Opportunity:** an eligible parsed match with ≥1 team kill.
- **Why it replaces rather than enhances:** `involvement` is
  `(kills+assists)/minute`. Two players with identical behaviour in a
  high-tempo and a low-tempo game get different `involvement`. Participation
  share removes team tempo and game duration from the measurement entirely.
  That changes what the number *means* → new lineage, and it touches
  `combat_expression`, `involvement_boundary`,
  `involvement_holds_exposure_moves` and `exposure_holds_involvement_moves`.
- **Residual role exposure:** a farming carry is genuinely absent from more
  kills than a roaming support. Participation share does not remove that
  gradient — it removes *tempo* and *duration*, not role. Role-conditional
  baselines (now possible, T1-A) are a prerequisite, not an optional extra.
- **Negative control:** compute participation share against a *randomly
  time-shifted* team-kill series. The statistic must collapse.
- **Hero bias:** real. Split-push and jungle-oriented heroes are structurally
  absent from teamfights. Requires hero-conditional baselines; without them the
  finding reads as "you play split-pushers" dressed as a behavioural claim.
- **Version impact:** `elements` **changed** (`involvement` re-based),
  `findings` **changed** (`combat_expression`), `semantic_outcomes` **changed**
  (`involvement_boundary`, `involvement_holds_exposure_moves`,
  `exposure_holds_involvement_moves`), `context_baseline` **changed**,
  `thresholds` **changed** (the 0.08 involvement ROPE is calibrated against a
  rate, not a share, and must be re-derived).

### T2-B · Lane Outcome Record — **C. NEW_SUBFINDING** (`combat_expression`)

**What would have to be true:** (1) C1 resolves; (2) `laneReport` (Pack B `B2`)
proves richer than the three coarse enums, or the coarse enums prove sufficient;
(3) the finding survives an outcome-leakage review.

- **Paths:** `match.bottomLaneOutcome`, `midLaneOutcome`, `topLaneOutcome`,
  `players[].lane`, `players[].isRadiant`, `match.radiantNetworthLeads`.
- **Verified present.** A5: `TIE` / `RADIANT_VICTORY` / `RADIANT_VICTORY`.
- **The framing matters more than the measurement.** "You win your lane 60% of
  the time" reduces to "you won more" and must be rejected on the brief's own
  rule. The publishable version is the **disagreement**: matches where the
  player's lane outcome and the match outcome diverge — playing from behind, or
  winning lane and losing the game. That is a behaviour, not a result.
- **Mapping risk, unresolved:** lane→side mapping (Radiant offlane is bottom;
  Dire offlane is top) must be derived and tested, not assumed. A sign error
  inverts the entire finding and would be invisible in aggregate.
- **Unit:** the match. **Clustering: match → session → player.**
- **Opportunity:** an eligible parsed match with a non-null outcome for the
  player's lane. `JUNGLE` assignment has no lane outcome — on the specimen that
  is 1 of 91 rows, so the loss is small but must be declared.
- **Role exposure:** high and asymmetric. `POSITION_4`/`POSITION_5` share a lane
  with a core, so "their" lane outcome is substantially not theirs. This
  candidate may be **core-only**, and if so it must say so — a role-specific
  candidate that pretends to be universal is exactly the failure mode the brief
  warns about.
- **Hero bias:** moderate. Lane outcome is partly a matchup property. Control by
  comparing against the hero's own lane-outcome rate in the corpus, not against
  a global rate.
- **Derived feature:**
  ```
  side(m)        = "radiant" if isRadiant else "dire"
  lane_field(m)  = map(players[].lane, side)   # BLOCKED: see 05, lane->side mapping
  won_lane(m)    = lane_field(m) resolves to this player's side
  disagreement   = mean over eligible parsed matches of
                   [ won_lane(m) XOR isVictory(m) ]
  ```
- **Version impact:** `findings` **changed** (new `combat_expression` branch),
  `semantic_outcomes` **changed** (new branch + copy + alternatives),
  `copy` **changed**. `elements` **unchanged**.

---

## 6. Tier 3 — experimental

| experiment | question it answers | why not higher |
|---|---|---|
| **XP Timing Curve** (`stats.level` timestamps) | Is level-timing a distinct axis from net worth, or a restatement of it? | Depends on the `stats.level` length rule (BLOCKED, Pack B `B3`) and on a correlation measurement that requires the corpus. Genuinely novel if it separates. |
| **Item Signature** (`itemPurchases`) | Do players have a reproducible build fingerprint independent of hero? | Highest resonance in the whole catalog; also the most patch-fragile and it collides with the `item timing` language guard. Research it before designing copy. |
| **Vision Behaviour** (`wards`) | Is warding a stable behavioural trait or a role artifact? | Verified role-conditional: A2 core = **1 ward**, A3 support = **27 wards**. Any cross-role comparison here is meaningless. Support-only candidate at best, and support-only halves the addressable population. |
| **Death Structure** (`deathEvents` × `radiantNetworthLeads`) | Do deaths concentrate in a game state? | Attractive and dangerous: it sits one inference away from `death quality`, which is banned. Study it backstage; do not design copy for it yet. |
| **Adaptation** (`itemPurchases`/`abilityLearnEvents` × draft) | Does the player change plan in response to the enemy draft? | The most interesting idea in the catalog and the least ready. Needs ten-player context plus per-match parsed plus a draft model. Tier 3 for years, not months. |

---

## 7. Rejected

This section is load-bearing: it exists so the next reader does not re-propose
these.

| idea | classification | reason |
|---|---|---|
| Anything using `roleBasic` | **G** | Defaults to `CORE` on unparsed matches *and* collapses `POSITION_4`/`POSITION_5` to one token on parsed ones (A6). Rejected on sight. |
| Anything using `imp`, `impPerMinute`, `averageImp`, `award`, `behavior`, `streakPrediction` | **G** | Proprietary opaque scores. Importing them makes our findings a function of an unversioned external model. |
| Anything using `analysisOutcome`, `predictedOutcomeWeight`, `winRates`, `predictedWinRates` | **G** | Model outputs, not observations. `analysisOutcome` is additionally *reconstructible* from `radiantNetworthLeads` — so using it buys nothing and costs provenance. |
| Anything using `actualRank`, `averageRank`, `rank`, `bracket`, `seasonRank`, `behaviorScore` | **G** | Forbidden analytical inputs. `rank_or_mmr_used: False` is an audited assertion. |
| `intentionalFeeding` | **G** | A moral judgment about a player. No tier, no research use. |
| Solo vs party analysis (`partyId`) | **G** | 8% coverage on the specimen and the null semantics are unestablished — "solo" and "unknown" are indistinguishable. Revisit only if the semantics resolve. |
| Local-time-of-day behaviour (`regionId`/`clusterId` + UTC) | **G** | `M10` stands. Region is not timezone; the inference remains an inference. |
| Patch causality (`gameVersionId`) | **G** | `M11` stands. Patch *stratification* is now possible; patch *causality* is not identifiable and never was. Do not let the coverage improvement blur these. |
| Item-build identity from final inventory (`item0..5Id`) | **G** | `M12` stands as written — final inventory is not a build. But note the *reason* is now obsolete: `itemPurchases` gives the real build. The rejection should be rewritten, not deleted. |
| Roshan participation (`roshanEvents`) | **G** | Returned length 0 on a 59.8-minute game. The field is not trustworthy; treating empty as "no Roshan" would fabricate a finding. |
| Map movement / region occupancy (`playerUpdatePositionEvents`) | **G** at product tier | 473 KB per player per match; ~4.6 MB for ten players. ~1.2 GB per player-year. Also collides with the `positioning` guard. Research instrument only. |
| Chat behaviour (`chatEvents`, `allTalks`, `chatWheels`) | **G** | Player-authored text about identifiable people. The privacy cost is real, the analytical value is low, and it is far outside what this product promises. |
| Adding a sixth finding family for role | **G** | Would expand the BH denominator from 5 to 6 and dilute all five existing families. Role belongs as branches under `pool_shape` and `transfer`. |
| Any per-minute "breakpoint" search | **G** | A 59-element series has enough degrees of freedom to find a breakpoint in noise. `predeclared_breakpoint` already exists for the session case and already requires pre-declaration. Do not open a within-match version. |
| Turbo inclusion to raise sample size | **G** | Turbo distorts every rate and economy measure. Measured on the specimen: `breadth` over the 49 eligible matches is **10.60** effective heroes; over all 100 matches (i.e. with Turbo admitted) it is **12.35** — a **+1.75** swing for reasons that have nothing to do with the player. Sample size bought this way is not power. |

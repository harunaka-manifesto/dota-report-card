# Post-Match Insight Decisions V1

> **This document is retained as the decision history. For normative implementation behavior, see [`POST-MATCH-INSIGHTS-SSOT.md`](../engine_specs/POST-MATCH-INSIGHTS-SSOT.md).** All owner calls are resolved (2026-09-17, §26). Where text below says "pending", "recommendation" or "owner confirmation", read it as the historical state at the time; §26 records the final outcome.

**Project:** Dota Tracker  
**Area:** Deterministic Post-Match Intelligence  
**Status:** DECISION HISTORY — all owner calls resolved 2026-09-17 (§26). Normative contract: `POST-MATCH-INSIGHTS-SSOT.md`.  
**Date:** 2026-09-16  
**Workspace:** `#swiftMigration/`

---

## 0. Purpose of this document

This document records the **owner-locked product decisions** for the V1 deterministic post-match insight system up to this point.

It exists to prevent future agents, engineers, content writers, and designers from accidentally treating older research recommendations as current product direction.

This is deliberately different from the research reports:

- Research documents answer **what the data can support**.
- This document answers **what the product has decided to ship, reject, or keep pending**.
- Older research candidates are **not approved merely because they scored well statistically**.
- When this document conflicts with an older research recommendation, **this document wins for product direction**.
- Exact implementation details that are still being validated are marked clearly rather than guessed.

This was **not** the final SSOT; the final SSOT is now `POST-MATCH-INSIGHTS-SSOT.md`. Three system-wide areas were open at an earlier checkpoint:

1. exact threshold-based cross-candidate ranking,
2. exact history eligibility / comparator / wording rules,
3. final player-context audit across all surviving Tier A and Tier B candidates.

**Update 2026-09-16:** the final research pass for all three is complete — see `POST-MATCH-FINAL-RANKING-HISTORY-PLAYER-AUDIT.md` and `post-match-final-audit-data/final-candidate-contract.json`. Its results are recorded in §13 (history), §14 (ranking) and §15 (player-context audit). The earlier text is kept as an audit trail.

The remaining owner actions before promoting this checkpoint to the final engineering/content SSOT are listed in §22:

- confirm or reject two audit changes to previously locked items: Dramatic Lane removal, and Smoke Volume becoming Standard-only;
- lock or reject the Smoke→Kills enrichment;
- acknowledge the revised no-insight coverage (§18).

---

# 1. Product goal

The post-match experience should surface a small number of facts that make the player think something like:

> “Oh. That explains what that game felt like.”

or:

> “I didn’t realize they were doing that.”

or:

> “Yeah, that really was an unusual game for me.”

The goal is **not** to produce a conventional stat dump, scoreboard recap, or generic coaching verdict.

The strongest cards should be:

- personalized,
- contextual,
- genuinely notable,
- sometimes hidden from the player during the game,
- easy to understand,
- deterministic,
- defensible from the data,
- useful without pretending the system knows why something happened.

The intended feeling is closer to a good sports recap or a strong “Wrapped” observation than a spreadsheet.

---

# 2. Normative system principles

## 2.1 Production analysis is deterministic

**LOCKED**

No LLM analyzes individual production matches.

Every production insight must be generated from deterministic inputs:

- explicit STRATZ fields,
- validated derived metrics,
- deterministic eligibility rules,
- deterministic thresholds,
- deterministic ranking,
- predefined semantic/copy templates.

LLMs and external research may be used **offline** to:

- discover candidate insight shapes,
- test statistical rules,
- review examples,
- challenge assumptions,
- design copy templates,
- validate player usefulness.

They are not part of the runtime reasoning path for an individual match.

---

## 2.2 Maximum three insight cards

**LOCKED**

A post-match recap may show **up to three** special insight cards.

Three is a **maximum**, not a target.

Valid outputs include:

- 3 cards,
- 2 cards,
- 1 card,
- 0 cards.

The system must **never force-fill** weak cards simply to make the UI look complete.

---

## 2.3 “No special insight” is an acceptable result

**LOCKED**

Current combined validation suggests roughly:

- Tier A alone covers about two-thirds of eligible viewpoints,
- Tier A + Tier B brings useful deterministic coverage to approximately **82–85%**,
- therefore roughly **13–17%** may legitimately have no special insight worth showing. *(Superseded 2026-09-17: with the final pool and guards the accepted expectation is ~57–61% no special card — §18, §26.)*

That is acceptable.

The product will later define a different generic/contextual post-match treatment for those cases.

The ranking system must **not lower standards merely to eliminate blank coverage**.

---

## 2.4 Candidate quality comes before candidate score

**LOCKED**

The governing principle is:

> **Not-boring wins.**

A candidate can be mathematically unusual and still be a poor product insight.

The system therefore has two separate stages:

1. **Candidate-type validation**
   - Is this kind of fact actually worth showing?
   - Is it understandable?
   - Is it non-obvious?
   - Is it non-misleading?
   - Does it answer a useful question?

2. **Occurrence ranking**
   - If the candidate type is approved and fires in this match, how strongly should this occurrence rank against the other eligible cards?

A large numerical score must **never rescue a fundamentally boring or misleading candidate type**.

This principle is the reason several statistically strong research candidates were removed from the product pool.

---

## 2.5 Tier A does not automatically outrank Tier B

**LOCKED**

Tier A means the insight is more anomaly-like, exceptional, hidden, or high-signal.

Tier B means the insight describes a useful match shape/context that may not be rare enough to qualify as a Tier A anomaly.

These labels are **not display priority classes**.

A strong Tier B match story is allowed to outrank a weaker Tier A observation.

There is no rule like:

> “Fill Tier A first, then Tier B.”

The best eligible cards should win.

---

## 2.6 Do not balance own-side and enemy-side insights

**LOCKED**

There is no requirement for:

- one positive card,
- one negative card,
- one own-team card,
- one enemy card,
- one “balanced” recap.

If the most interesting things in the match are all enemy-side, the recap may show multiple enemy-side observations.

The system must not suppress a valid insight merely because:

- the user lost,
- several cards describe the enemy,
- the recap feels “negative,”
- the enemy performed unusually well.

The card itself still needs to be factual, non-blaming, and non-causal.

---

## 2.7 No generic merge/redundancy engine

**LOCKED / REJECTED IDEA**

Earlier discussion considered generic mechanisms such as:

- redundancy groups,
- merge systems,
- composite cards,
- forcing category diversity,
- suppressing cards from the same story family.

The owner does **not** want that complexity in V1.

Therefore:

- no generic card-merging engine,
- no generic composite-insight engine,
- no hard “one card per family” rule,
- no hard diversity quota,
- no automatic suppression merely because two cards feel related.

If two independently valid cards deserve two of the three slots, they may both appear.

Only add a **specific combination guard** later if the final player-context audit finds a repeated, clearly bad user experience.

---

## 2.8 No unsupported causality

**LOCKED**

The data can support:

- before,
- after,
- during,
- while,
- within X seconds,
- within X minutes,
- followed by,
- was ahead / behind,
- was destroyed,
- was purchased,
- was used.

The product must not imply causality where the data only establishes sequence.

Avoid claims such as:

- “because,”
- “caused,”
- “cost you the game,”
- “won them the game,”
- “punished,”
- “led to” when the causal relationship is not identified,
- “they did X to counter you” when intent is not observed.

This is especially important for:

- fights → objectives,
- dewards → deaths,
- Smoke → kills,
- item timing → game outcome,
- stacking → farm lead,
- lane result → match result.

---

# 3. Data interpretation principles

## 3.1 Standard and Turbo stay separate

**LOCKED PRINCIPLE**

Standard and Turbo are different analytical buckets.

Do not mix their thresholds, distributions, history comparators, or expected timing.

Many validated thresholds differ dramatically between the two modes.

---

## 3.2 Role context matters only when the metric actually depends on role

**LOCKED PRINCIPLE**

Use the user's effective role when the metric is role-dependent.

Do **not** unnecessarily scope team-level enemy behavior by the user's role.

Reason:

- role-scoped personal history becomes sparse very quickly,
- enemy-team metrics such as Smoke volume or stacking do not inherently become different because the user happened to play Mid versus Offlane.

The final history pass will lock the exact cohort keys.

---

## 3.3 Playback is enrichment, not a dependable foundation

**LOCKED PRINCIPLE**

Playback has repeatedly been operationally unavailable or `null`.

Therefore:

- a playback-only fact may exist as an optional enrichment,
- core V1 post-match coverage must not depend on playback,
- empty playback event arrays must not be interpreted as “zero events” unless playback completeness has been validated,
- playback-dependent headlines need explicit availability guards.

Current examples:

- Smoke → Kills is playback-enriched.
- Exact ward lifetimes are playback-derived, although vision research found a promising stats-only reconstruction.
- Playback can make a card more precise, but the product cannot assume it exists.

---

## 3.4 Visibility is not observable

**LOCKED**

Do not make literal claims about:

- what a team could see,
- what percentage of the map was visible,
- whether the enemy “saw” a rotation,
- whether a death happened “because you had no vision.”

Ward proximity and geometric circles are not equivalent to actual Dota fog-of-war visibility because of:

- terrain,
- trees,
- elevation,
- ward placement geometry,
- hero vision,
- true sight,
- other mechanics.

This is an explicit prohibited interpretation.

---

# 4. Tier model

## 4.1 Tier A

Tier A contains the most notable candidate types:

- dramatic anomalies,
- unusual personal-history comparisons,
- hidden enemy activity,
- major game-state reversals,
- unusual power-spike timing.

Tier A is not automatically ranked above Tier B.

---

## 4.2 Tier B

Tier B is a deterministic fallback layer that describes the **shape of the game** when no sufficiently strong Tier A anomaly dominates.

Tier B is not a collection of weaker anomalies.

It answers questions like:

- Was this close for most of the game?
- Was it even until one team separated?
- Did a large lead erode?
- Did a team recover most of a deficit?
- Was there a legitimate very-late comeback win?

Tier B exists to provide useful context without inventing drama.

---

# 5. Tier B — locked product decisions

## 5.1 `CLOSE_MOST_OF_GAME`

**STATUS: KEEP**

Previously named `CLOSE_THROUGHOUT`.

The old name was rejected because “throughout” overstates what the rule actually establishes.

### Product meaning

The game remained genuinely competitive for a meaningful majority of the relevant analysis window, without a sustained major advantage.

Validated V2 work used an approximate basis such as:

- no sustained meaningful edge,
- at least roughly 60% of analyzed minutes qualifying as close,
- a sustained/3-minute gap below roughly the tuned close threshold.

The exact final math remains subordinate to the final ranking/player-audit pass if that pass refines the threshold.

### Safe semantic direction

> “The game stayed close for most of the match.”

### Do not say

> “The game was even the entire time.”

unless the rule genuinely supports that stronger claim.

### Why it survives

Player review found the concept predominantly useful/non-boring, unlike generic one-sided/steady-edge narration.

---

## 5.2 `EVEN_THEN_SEPARATED`

**STATUS: KEEP**

### Product meaning

The game is genuinely competitive for a meaningful stretch, then one side establishes a sustained meaningful advantage.

It answers:

> “When did this stop being an even game?”

### Safe semantic direction

> “The game stayed close until around 24:00, then Dire opened a sustained lead.”

### Do not say

> “That moment won them the game.”

The rule describes the transition in game state, not the cause.

---

## 5.3 `LEAD_ERODED`

**STATUS: KEEP**

### Product meaning

A team held a meaningful sustained advantage, then lost a substantial portion of that advantage.

The game does **not** need to fully flip.

This is intentionally weaker than the major Tier A lead-reversal concepts.

### Important guard

The erosion must represent a **real absolute reduction** in the lead.

Do not create an erosion story from a misleading percentage artifact caused by a much larger late-game total economy.

### Safe semantic direction

> “Your 11k lead had fallen to 2.5k by 34:00.”

### Do not imply

> “You threw the game.”

---

## 5.4 `DEFICIT_RECOVERED`

**STATUS: KEEP**

### Product meaning

A team had a meaningful deficit and substantially recovered toward a competitive/even state, without necessarily completing a comeback.

### Safe semantic direction

> “You cut a 10k deficit to under 2k.”

### Important distinction

This is **not** the same as saying the team completed a comeback.

If the team recovered and later lost, the copy must remain accurate to that sequence.

---

## 5.5 `LATE_REVERSAL`

**STATUS: KEEP — WINNER ONLY**

This is a special outcome-aware Tier B shape.

### Required meaning

The team:

- was meaningfully behind for most/late in the relevant game window,
- reverses the state very late,
- **actually wins the match**.

### Explicitly rejected case

Behind → tiny/brief late lead → still loses

must **not** be described as a comeback.

Likewise, a trivial last-minute net-worth wiggle should not qualify.

### Reason for the winner-only rule

A “comeback” is an outcome-sensitive player concept. Briefly crossing zero late is not sufficient.

---

## 5.6 Structure contradiction

**STATUS: SUPPORTING ENRICHMENT ONLY**

Rare structure countertrend cases may enrich another match-shape card, for example:

- meaningful gold lead while losing several structures,
- substantial lead with little structure conversion.

Do not make broad structure alignment/structure burst a standalone Tier B card.

The broad versions were too common and not useful enough.

---

## 5.7 `STEADY_EDGE`

**STATUS: REMOVE FROM USER-FACING PRODUCT**

Reason:

- player review found it boring too often,
- “one side had a steady modest edge” does not earn one of only three cards.

It may exist internally only if an engineering calculation needs it.

It should not be preserved merely for taxonomy completeness.

---

## 5.8 `ONE_SIDED`

**STATUS: REMOVE**

Reason:

- almost universally boring in review,
- “one team was ahead all game” is normally obvious,
- it adds little post-match value.

Do not show a generic stomp card simply because the match was one-sided.

---

## 5.9 `LEAD_SWAPPED`

**STATUS: REMOVE AS TIER B**

Meaningful large lead swaps belong in Tier A's major lead-story logic.

Minor swaps are not worth a card.

Do not retain a separate weak Tier B swap concept.

---

## 5.10 `UNCLEAR`

**STATUS: REMOVE**

`UNCLEAR` is not a user-facing insight.

If no approved shape fits, the correct output is simply no Tier B card.

---

# 6. Tier A — final product-selection decisions

Tier A candidate selection is now considered **wrapped**.

The remaining work is ranking, exact history contract, and the final player-context audit—not reopening every rejected candidate.

---

# 7. Tier A — Lane Story

## 7.1 Dramatic Lane Lead Path / Lane Reversal

**STATUS: REMOVED — owner-confirmed 2026-09-17.** (Earlier: KEEP, dramatic cases only; the final audit recommended REMOVE.)

> **Final audit finding (2026-09-16):** the dramatic case this card was kept for does not occur at the lane checkpoints.
>
> - **No reversals.** 0 of 5,202 core lanes (2,812 Standard, 2,390 Turbo) had an early lead of at least p75 that became an opposite gap of at least p50 by 10:00.
> - **What actually fired was ordinary.**
>   - Blowouts: 0 GOOD / 4 ACCEPTABLE / 25 BORING / 1 MISLEADING in 30 reviewed.
>   - Separations and reversals: 0 GOOD in a 40-example census.
>   - Reviewed "reversals" were swings of about ±300 gold, or role-norm effects (an offlaner falling behind a carry).
> - **The personal lane story is already covered** by Own Lane vs Usual and Opponent Start vs History, which rated much better.
>
> The audit therefore recommends **REMOVE**. Because this reverses an owner KEEP, it stays marked for explicit owner confirmation. Until then, engineering must not build it. Evidence: `POST-MATCH-FINAL-RANKING-HISTORY-PLAYER-AUDIT.md` §7.

The ordinary version of the original Lane Lead Path is rejected.

### Rejected ordinary interpretation

> “You were ahead in lane.”

or:

> “You lost your lane.”

The player usually already knows this.

### Approved product value

The card earns a slot only when the trajectory itself is sufficiently dramatic, such as:

- large early lead becoming a large deficit,
- large deficit becoming a large lead,
- unusually severe separation,
- a genuine major lane reversal.

The product decision is:

> **ordinary lane narration is out; genuinely dramatic lane trajectory is in.**

The final ranking/player-context pass may refine the exact “dramatic” gate, but it must not weaken this product principle.

### Safe semantic form

> “You were +1.6k on their Mid at 5:00, but −1.4k by 10:00.”

### Avoid

> “You lost lane because…”

No causal explanation of why the lane changed is available.

---

## 7.2 Own Lane vs Your Usual

**STATUS: KEEP — HISTORY REQUIRED**

This is one of the clearest forms of personalization.

### Product question

> “How unusual was this lane for me?”

### Example semantic direction

> “Your Offlane was +1.9k at 10:00 — one of your strongest Standard Offlane starts recently.”

### Why it survives

The same raw lane score becomes much more meaningful when anchored to the player's own comparable history.

### Comparator principle

Use an appropriate mode + effective-role history cohort.

The exact minimum N, history horizon, and wording levels were pending the final history pass *(resolved in §13.6)*.

Older research used `>=10` prior comparable matches, but that number is not yet considered the final owner-locked history contract.

---

## 7.3 Extreme Opponent Start vs Your History

**STATUS: KEEP — HISTORY REQUIRED FOR THE USER-FACING VERSION**

The original raw candidate was:

> “Their Carry had 67 CS at 10:00.”

That is not sufficient by itself for this card.

The approved version is contextualized against the kinds of opponents the user has actually faced.

### Example

> “That was the strongest opposing Carry start across your last 22 comparable Standard matches.”

### Product value

This can reframe a difficult lane:

not merely “I was behind,” but:

> “That opponent had an unusually extreme start relative to what I normally face.”

### Important decision

For **this lane candidate**, history is required.

This is different from `Enemy Early-Rich Hero`, where non-historical match context is useful enough by itself.

---

## 7.4 Support Lane Pair

**STATUS: REMOVE**

The research version could objectively describe the combined net-worth result of the two lane pairs.

The owner rejected it as a standalone card because the player can generally feel whether their own lane pair is winning or losing.

It does not earn one of three scarce recap slots.

Do not resurrect it simply to provide Support lane coverage.

---

## 7.5 CS-vs-Gold Split

**STATUS: REMOVE**

This candidate was statistically interesting and rare.

The owner judged it:

> “not useful.”

That product decision overrides the research novelty.

Do not ship it merely because it is counterintuitive or statistically clean.

---

## 7.6 Level-6 Race

**STATUS: REMOVE**

Even where statistically unusual—particularly Mid—the level-6 timing difference is generally too visible/obvious during play to justify a post-match insight slot.

Do not ship it as a standalone Tier A card.

---

# 8. Tier A — Match Lead Story

The product direction is to treat the important lead-reversal shapes as one coherent **Match Lead Story** family rather than a collection of overlapping, weakly differentiated research candidates.

This does **not** mean a complex runtime merge engine.

It means the product taxonomy recognizes a small set of deterministic lead-story subtypes.

---

## 8.1 `COMEBACK_WIN`

**STATUS: KEEP**

### Meaning

The user's team was behind by a genuinely major amount and ultimately won.

The result must agree with the comeback claim.

Earlier validation for the original comeback/lost-lead concept used approximately:

- Standard: major deficit around the validated p90 level (~12.3k),
- Turbo: major deficit around the validated p90 level (~18.3k).

The final audit may refine implementation guards, but the concept is locked.

### Safe semantic direction

> “You came back from a 14k deficit to win.”

This is outcome-aware and factual.

---

## 8.2 `LOST_FROM_AHEAD`

**STATUS: KEEP**

### Meaning

The user's team held a genuinely major advantage and eventually lost.

### Safe semantic direction

> “You led by 13k before the game turned and Dire won.”

### Do not say

> “You threw a 13k lead.”

“Throw” is an evaluative/causal interpretation, not a neutral match-state fact.

---

## 8.3 `MAJOR_SUSTAINED_LEAD_FLIP`

**STATUS: KEEP**

### Meaning

There was a major, sustained change in which side held the advantage after the lane phase.

This captures substantial lead reversals that may not cleanly be described as an outcome-defined comeback/lost-from-ahead.

Earlier validation for sustained lead flips required opposite-sign runs and meaningful peaks on both sides.

The exact final implementation belongs in the ranking/player-context pass.

### Important distinction

A tiny sign crossing is not enough.

A meaningful lead flip must be:

- large enough,
- sustained enough,
- contextually real.

---

## 8.4 Generic unrestricted Swing Window

**STATUS: REMOVE**

The earlier generic “largest swing” candidate was rejected because a large share of statistically extreme windows merely described a stomp getting worse.

That does not make for useful storytelling.

Do not surface:

> “The biggest swing was +8k more toward the team that was already stomping.”

unless it qualifies under an approved lead-story shape.

---

## 8.5 Structures Lost While You Were Dead

**STATUS: REMOVE FROM FINAL TIER A POOL**

This candidate was statistically valid and personal.

However, it was removed during the product selection pass.

Do not include it in the final Tier A user-facing pool.

Any future reconsideration would need new product evidence, not just the old validation result.

---

# 9. Tier A — Hidden Enemy Activity

The key product value of this family is information the player may **not have been able to perceive clearly while playing**.

Hiddenness alone is not enough; the information must still be interesting.

---

## 9.1 Enemy Stacking Edge

**STATUS: KEEP — STANDARD ONLY**

### Meaning

The enemy performed an unusually large amount of stacking relative to the match / user's team.

This is classic “invisible work”:

the opposing team may create significant farm resources without the user seeing the setup.

### Standard

Keep.

Earlier validation found the Standard signal meaningful.

### Turbo

Remove.

The meaningful-floor Turbo version was too rare/trivial.

Do not show weak cards such as:

> “They stacked 3 camps to your 1.”

merely because it is technically above a distributional threshold.

---

## 9.2 Vision system — raw deward count

**STATUS: REMOVE AS A HEADLINE**

The original concept:

> “They destroyed 10 of your wards.”

was challenged with:

> “So what?”

Focused vision research confirmed the concern.

Raw deward count is:

- heavily entangled with normal support play,
- affected by match length/context,
- disproportionately common in losses,
- not sufficiently explanatory by itself.

The product decision is therefore to **replace the raw headline with concrete vision patterns**.

---

## 9.3 Vision Quick Clears

**STATUS: KEEP — PRODUCT CONCEPT LOCKED**

### Product question

> “Were our observers repeatedly found almost immediately?”

### Latest focused research shape

The research recommendation was approximately:

- Standard: at least 4 quick clears,
- Turbo: at least 3 quick clears,
- destroyed within 90 seconds of placement,
- at least 25% of the team's observers affected.

Example:

> “8 of your 26 observers were destroyed within 90 seconds; 5 lasted under a minute.”

### Why it is useful

This tells the player something more concrete than total deward volume:

their team's observers were repeatedly being found very quickly.

### Technical caveat

Exact lifetime requires knowing which placed observer corresponds to a later deward.

Focused vision research found a promising stats-only reconstruction. *(Resolved: validated on a fresh holdout and approved for V1 — §9.5.)*

See §9.5.

---

## 9.4 Vision Region Sweep

**STATUS: KEEP — PRODUCT CONCEPT LOCKED**

### Product question

> “Did the enemy systematically clear one area?”

### Latest focused research shape

The research recommendation was approximately:

- at least 3 observers,
- in one map region,
- destroyed within a 5-minute window,
- optionally supported by enemy Sentry placements in the same region.

Example:

> “Three observers in your top jungle were cleared within five minutes; the enemy placed four Sentries there.”

### Why it survives

This transforms “they dewarded a lot” into a concrete spatial pattern.

It is useful because it identifies **where** the vision battle was concentrated.

### Required guards from focused research

For Region Sweep:

- skip sweeps in the final 5 minutes,
- skip sweeps that start when the team is already approximately 10k+ behind, unless later validation produces a better rule.

Reason:

- final pushes can create fake “sweeps,”
- a stomp can make normal end-game cleanup look strategically meaningful.

The final player-context pass may refine those exact guards.

> **Final guards (2026-09-16 audit):**
>
> - the first clear is at or after 5:00 (no rune-ward clears in the laning phase);
> - the last clear is before the final 5 minutes;
> - the absolute team lead at the first clear is under 10,000, in either direction;
> - the median lifetime of the swept wards is at most 180 s (no "sweeps" of wards that were about to expire);
> - at least 3 observers in one region within 5 minutes.
>
> Quick Clears now needs at least 4 observers cleared within 90 s in **both** modes (Turbo 3 was boring in short stomps), at least 25% of placed observers, and clears before the final 5 minutes. Counts are lower bounds and copy says "at least".
>
> Region Sweep ranks in the lowest ranking class (§14.4).

---

## 9.5 Vision reconstruction method

**STATUS: PRODUCT CONCEPTS LOCKED; RECONSTRUCTION METHOD VALIDATED ON FRESH HOLDOUT (2026-09-16)**

> **Fresh holdout result.** Playback returned data again on 2026-09-16: 34 of 110 recent matches (about 31%). The method was re-tested on 33 matches (66 team units) that were not used to tune it.
>
> | Measure | Result |
> |---|---:|
> | Deward identity precision | **99.1%** (sentry rule 99.0%, single-candidate fallback 100%) |
> | Coverage | 79% |
> | Region correct | 99.1% |
> | ≤90 s classification agreement | 99.5% |
> | Quick-clear count error | 0.41 mean absolute |
>
> **Rule agreement:**
>
> | Rule | Hits | Misses | False fires |
> |---|---:|---:|---:|
> | Quick Clears | 3 | 2 | 0 |
> | Region Sweep | 3 | 1 | 0 |
>
> The method is conservative — it misses some sweeps but invents none — and is **approved for production**. Displayed counts are lower bounds. Re-check after any patch that changes ward or Sentry mechanics.
>
> The original, same-set evidence is kept below as an audit trail.

Focused research found an important workaround:

enemy Sentry placements close to an observer during its life can help identify which placed ward corresponds to a historical deward event.

Reported results on the available playback truth set:

- approximately 95% of cleared observers had an enemy Sentry within ~640 units during their life,
- approximately 3% of naturally expired wards did,
- tuned reconstruction reached roughly:
  - 92% deward identity precision,
  - 76% deward coverage,
  - 99% map-region correctness.

This is promising enough to continue.

However:

> the method was tuned and evaluated on the same small set of approximately 18 playback matches.

At that time, the product concepts were locked but the stats-only identity reconstruction was **not yet validated for production** *(resolved by the fresh holdout above)*.

Required next step:

- fresh playback holdout once playback is available again,
- confirm the reconstruction generalizes.

Do not describe the reported 92% as production-certified yet. *(Superseded: the fresh-holdout figures above are the production numbers.)*

---

## 9.6 Rejected vision interpretations

### Literal map visibility percentage

**REJECT**

Do not say:

> “Your team only had 18% map visibility.”

Focused research found that geometric observer circles are a poor stand-in for actual Dota visibility.

### Deward → death story

**REJECT AS A HEADLINE**

Research found deaths after dewards only weakly above matched baseline and heavily confounded by fights already happening in the area.

Do not say:

> “They dewarded the area, which caused your deaths.”

### Deward → tower / net-worth consequence

**REJECT**

No sufficiently useful/clean signal.

### “No ward standing” gaps

**REJECT AS ENEMY-ACTION STORY**

Many gaps begin because observers naturally expire.

Using them as an enemy-pressure headline would misattribute the cause.

### Ward-age inference from deward bounty

**REJECT**

The deward gold field did not reliably encode observer age.

---

## 9.7 Enemy Smoke Volume

**STATUS: KEEP — STANDARD ONLY, ENEMY ≥ 4 SMOKES AHEAD — owner-confirmed 2026-09-17.** Turbo Smoke Volume is removed.

> **Final audit finding (2026-09-16).**
>
> - **Turbo:** 0 GOOD across 24 reviewed cards (14 in round 1, 10 in the holdout). Counts of 3–5 in 20-minute games read as "so what".
> - **Standard:** cards with small gaps (for example 8 vs 6) were boring.
>
> Recommended final rule:
>
> - Standard only;
> - enemy Smoke rate ≥ 1.60 per 10 minutes;
> - enemy at least 4 Smokes;
> - enemy at least **4** more than your team.
>
> Result in Standard: 11 GOOD / 7 ACCEPTABLE / 0 BORING across the retained round-1 examples and the holdout.
>
> The mode change narrows an owner-locked "Standard + Turbo" item, so it needs owner confirmation. Evidence: `POST-MATCH-FINAL-RANKING-HISTORY-PLAYER-AUDIT.md` §7.

This remains one of the clearest hidden-enemy candidates.

### Why it survives

Smoke of Deceit activity is intentionally hidden during play.

The player often does not know:

- how many times the enemy smoked,
- how much more the enemy smoked than their own team.

That is interesting even before proving what each Smoke accomplished.

### Validated base rule

The current validated H3 concept uses:

- Smoke uses per 10 minutes at a high/extreme threshold,
- minimum count:
  - Standard: at least 4,
  - Turbo: at least 3,
- enemy at least 2 uses above the user's team.

Earlier validation produced roughly:

- Standard ~6% tuned fire,
- Turbo ~8% tuned fire.

### Product principle

Do **not** conflate:

> “interesting hidden behavior”

with:

> “behavior proven to have caused something.”

Enemy Smoke Volume is useful on its own.

---

## 9.8 Smoke → Kills enrichment

**STATUS: LOCKED KEEP (optional enrichment on Standard Smoke Volume, modified rule) — owner-locked 2026-09-17.**

> **Fresh replication (2026-09-16):** 66 new team units, where playback Smoke counts matched stats counts in every unit.
>
> - **Rule fires:** 15 units (23%).
> - **Fired units:** 62 Smoke windows were followed by a kill, against 38.2 expected at matched ordinary moments (×1.6).
> - **Suppressed units with ≥3 Smokes:** 47 vs 49.7 expected (chance).
> - **Base rate:** a kill followed within a minute at ordinary moments 55.6% of the time; after a Smoke, 67.6%.
>
> This matches the original study's direction (44 vs 27.3), so the rule separates real Smoke-follow patterns from coincidence. **Recommendation: lock.**
>
> Because the base Smoke card is Standard-only (§9.7, owner-confirmed), the enrichment applies only to Standard. The 70% and f ≥ 2 cut points stay provisional (100 units in total).

This is **not a separate card**.

If retained, it upgrades the existing Enemy Smoke Volume card when playback is complete.

The old provisional rule:

- >=3 Smokes,
- >=50% followed by a same-team kill within 60 seconds,

**should be discarded**.

The focused Smoke validation found that the old rule was too permissive.

### Critical base-rate finding

At matched ordinary moments from the same match/team/phase:

- team kill within the next 60 seconds: approximately **58%**.

After a Smoke:

- team kill within the next 60 seconds: approximately **65%**.

That is only around:

- +7.6 percentage points,
- ~1.13× lift,
- with uncertainty large enough that the interval included zero in the available sample.

Therefore:

> “a kill happened within a minute of Smoke”

is common enough that it cannot be treated as inherently impressive.

The old rule fired far too often and still fired frequently when real Smoke timestamps were replaced with ordinary matched moments.

### Important mechanics finding

Current Smoke duration is around 45 seconds.

The focused analysis found the useful excess kill activity concentrated roughly in the 15–45 second region.

Longer windows mostly added coincidence.

### `killEvent.isSmoke`

The focused analysis revised the earlier interpretation.

The previous low-recall result was partly an artifact of treating many coincidental 60-second follow-up kills as the reference set.

In the new review:

- `isSmoke` was strongly associated with actual recent team Smoke usage,
- it is useful as a **confirmation gate**,
- it should not replace playback timing for the number displayed.

### Recommended modified V1 enrichment rule

Research recommendation:

1. Base H3 Enemy Smoke Volume fires.
2. Playback is genuinely usable:
   - item-use events are present,
   - playback Smoke count matches the historical stats Smoke count.
3. For each Smoke, its attribution window ends at:
   - 60 seconds, or
   - the team's next Smoke,
   - whichever comes first.
4. At least 3 Smokes.
5. At least 3 Smoke windows are followed by a same-team kill.
6. At least 70% of Smoke windows are followed by a same-team kill.
7. At least 2 of those windows contain a kill with `killEvent.isSmoke == true`.

Reason for 70%:

- 67% admitted multiple bad cases in manual review,
- including a team whose Smoke-window result was not actually better than its own normal fight-heavy baseline.

### Manual review result for the proposed rule

Available sample:

- 34 team units total,
- 9 final-rule fires,
- review:
  - 5 good,
  - 3 acceptable,
  - 1 boring,
  - 0 misleading.

The sample is small.

Threshold confidence remains **low-to-medium**, even though event-data confidence is high.

### Safe wording

> “5 of their 7 Smokes were followed by a kill within a minute.”

### Do not say

- “5 successful Smokes,”
- “5 Smokes resulted in kills,”
- “they ganked you successfully 5 times,”
- “their Smokes caused 5 kills.”

### Playback availability

Still very poor operationally at the time of the latest validation.

The enrichment must remain optional.

### Open research branch

The latest report asked whether a separate **stats-only `isSmoke` line** should exist while playback is unavailable.

That branch has **not been validated** and is not part of the product decision yet.

Do not invent it.

---

## 9.9 Enemy Early-Rich Hero

> **Final guards (2026-09-16 audit):**
>
> - your team also reached the net-worth goal — otherwise the card only restates a stomp;
> - the match lasted at least 8 more minutes after the enemy reached it;
> - the hero is not Alchemist, whose economy profile is not an anomaly.
>
> Holdouts: 16 GOOD / 14 ACCEPTABLE / 2 BORING / 0 MISLEADING. History is an optional secondary line only (N ≥ 20, §13.6).

**STATUS: KEEP — HISTORY NOT REQUIRED**

This was explicitly distinguished from the history-only lane opponent card.

### Product value

Even without historical comparison, the fact can contextualize why a game felt unusually accelerated or snowbally.

Example semantic direction:

> “Their Luna reached 10k several minutes before anyone on your team.”

or a mode-appropriate validated economy target.

### Current validated research shape

Earlier validation used approximately:

- Standard: enemy reaches 10k by ~18:00 or earlier,
- Turbo: enemy reaches 15k by ~12:00 or earlier,
- and at least 3 minutes before the user's team's first comparable hero.

### Important product decision

History can enrich this card, but history is **not required**.

The match-level timing itself can be useful.

---

## 9.10 Enemy Barely Warded

**STATUS: REMOVE**

Although statistically unusual and hidden, it was removed during the product selection pass.

It does not provide enough reliable “so what?” value for the limited card budget.

Do not ship it in V1.

---

## 9.11 Enemy Boss Control

**STATUS: REMOVE**

The research version scored well statistically.

The owner rejected it because major Roshan/Tormentor control is generally visible enough to the player during the game.

The insight does not earn one of three recap slots simply by recounting known objectives.

Do not resurrect it based on the old STRONG label.

---

# 10. Tier A — Power Spikes & Item Timings

The family name is now:

> **Power Spikes & Item Timings**

Do not use the older product label:

> “Item Execution & Power Spikes”

Reason:

the “execution” half of the research largely failed product validation.

---

## 10.1 Enemy Core Early Key Item

> **Final guards (2026-09-16 audit).** Before the guards this was the weakest surviving card: 0 GOOD / 9 ACCEPTABLE / 20 BORING / 1 MISLEADING.
>
> **What the problem was.** Hero-typical rushes were *not* the main issue: 87% of fires were already in the hero's own fastest 10%. The real problems were:
> - margins of only 0–2% below p5;
> - farming or hero-specific items (Midas, Aghanim's);
> - copy with no reference point.
>
> **Final rule.**
> - Item list: BKB, Blink, Manta, Battle Fury, Radiance, Desolator, Maelstrom, Orchid.
> - Purchase time ≤ 0.90 × the core p5 timing.
> - Copy includes the typical core timing ("about 11 minutes earlier than a typical core BKB").
> - Copy says "bought", never "finished" or "completed".
>
> Holdout after the guards: 7 GOOD / 13 ACCEPTABLE / 0 BORING. The card ranks in the lowest ranking class (§14.4).

**STATUS: KEEP — HISTORY NOT REQUIRED**

### Product question

> “Did an enemy core hit an unusually early item spike?”

### Current validated item set

The earlier validation included items such as:

- BKB,
- Blink,
- Radiance,
- Hand of Midas,
- Manta,
- Desolator,
- Battle Fury,
- Maelstrom,
- Aghanim's,
- Orchid,

with the strongest subset concentrated around major timing-sensitive spike items such as:

- BKB,
- Blink,
- Radiance,
- Battle Fury,
- Manta.

The final item allow-list may still be cleaned up during SSOT work.

### Research result

Original candidate:

- enemy P1–P3 first purchase at or before the item/role p5 timing,
- ~18% broad fire rate,
- ~11% stronger subset.

### Product decision

Keep even without history.

Reason:

the player may notice that an enemy is strong without realizing **how early** a meaningful item arrived.

That timing can explain why the game suddenly felt different.

### History

Optional enrichment.

Example:

> “Earliest enemy BKB across your recent Standard games.”

But history is not required for eligibility.

### Copy semantics

Purchase events do not always prove semantic “completion” in the way a player may interpret it.

Use:

- “bought” when that is what the data proves,
- “finished” only when the item/event semantics genuinely support that wording.

Never infer:

> “they counter-built you”

or:

> “they rushed this because of your hero.”

Intent is unobserved.

---

## 10.2 Own Key Item Timing vs Your History

> **Final contract (2026-09-16 audit).**
>
> - **Fastest direction only.** Slowest-record cards were 12 of 14 BORING, mostly long games or situational late purchases.
> - **Margin:** beat the previous record by ≥ 60 s (Standard) / ≥ 30 s (Turbo).
> - **Comparator:** bucket + effective role + item + same major patch. Support and core BKB timings differ by a median of 4.5–8 minutes, and BKB timing moved about +2 minutes between 7.39 and 7.40.
> - **History:** N ≥ 20; window is the last ≤ 50 comparable purchases.
>
> Fresh holdout: 10 GOOD / 2 ACCEPTABLE.

**STATUS: KEEP — HISTORY REQUIRED**

This is the final Tier A candidate the owner explicitly kept before wrapping Tier A selection.

### Product question

> “Was this item timing unusual for me?”

### Example

> “Your 18:40 BKB was your fastest across your last 16 comparable Offlane matches.”

### Why it survives

This is:

- personal,
- specific,
- easy to understand,
- difficult to remember accurately from play,
- naturally suited to historical comparison.

### Previous research rule

The old validation used:

- same item,
- relevant bucket,
- at least 10 prior comparable purchases,
- record-fast or record-slow.

The exact final sample-size and wording contract was then pending the dedicated history pass *(resolved in §10.2 / §13.6: N ≥ 20, fastest only)*.

Do not treat `10` as the final universal rule until that work is completed.

---

## 10.3 Unused Active Item

**STATUS: REMOVE**

The raw version was misleading.

The strict version became too rare after proper inventory/usage guards and was dominated by awkward item semantics.

Do not ship it merely as a “rare delight.”

---

## 10.4 Activation-rate extremes

**STATUS: REMOVE**

High activation-rate examples often reduced to hero-mechanics trivia.

Low activation-rate examples were too rare or ambiguous.

Do not ship.

---

## 10.5 Lane Item Race

**STATUS: REMOVE**

The unrestricted comparison generated nonsensical extremes.

The restricted version became too rare.

Do not ship.

---

## 10.6 Spike cluster / spike-before-turn variants

**STATUS: REMOVE AS STANDALONE CARDS**

These were too common, redundant, or not independently valuable enough.

If a later content system uses item timing as supporting context inside another card, that would require a specific decision.

Do not revive them as standalone V1 candidates.

---

# 11. Final Tier A user-facing pool

At this checkpoint the approved Tier A pool is:

| Family | Candidate | Status | History required? | Playback required? | Mode |
|---|---|---:|---:|---:|---|
| Lane Story | ~~Dramatic Lane Lead Path / Reversal~~ | **REMOVED** (owner, 2026-09-17) | – | – | – |
| Lane Story | Own Lane vs Your Usual | KEEP | Yes | No | Standard + Turbo |
| Lane Story | Extreme Opponent Start vs Your History | KEEP | Yes | No | Standard + Turbo |
| Match Lead Story | Comeback Win | KEEP | No | No | Standard + Turbo |
| Match Lead Story | Lost From Ahead | KEEP | No | No | Standard + Turbo |
| Match Lead Story | Major Sustained Lead Flip | KEEP | No | No | Standard + Turbo |
| Hidden Enemy | Enemy Stacking Edge | KEEP | No | No | Standard only |
| Hidden Enemy / Vision | Vision Quick Clears | KEEP (reconstruction validated) | No | No | Standard + Turbo |
| Hidden Enemy / Vision | Vision Region Sweep | KEEP (reconstruction validated) | No | No | Standard + Turbo |
| Hidden Enemy | Enemy Smoke Volume | KEEP | No | No | **Standard only** (owner, 2026-09-17) |
| Hidden Enemy | Smoke → Kills | **LOCKED** enrichment (owner, 2026-09-17) | No | Yes | Follows base card (Standard) |
| Hidden Enemy | Enemy Early-Rich Hero | KEEP | No | No | Standard + Turbo |
| Power Spikes & Item Timings | Enemy Core Early Key Item | KEEP | No | No | Standard + Turbo |
| Power Spikes & Item Timings | Own Key Item Timing vs Your History | KEEP | Yes | No | Standard + Turbo |

The full guarded Tier A + Tier B pool — eligibility, severity ladders, guards and verdicts — is in §15.3 and in `POST-MATCH-FINAL-RANKING-HISTORY-PLAYER-AUDIT.md` §11.

---

# 12. Final Tier A rejected / superseded pool

These candidates should not be revived simply because older research documents marked them STRONG:

| Candidate | Product status | Why |
|---|---|---|
| Ordinary Lane Lead Path | REMOVE | Too obvious unless dramatic |
| Support Lane Pair | REMOVE | Player already feels own lane result |
| CS-vs-Gold Split | REMOVE | Owner judged it not useful |
| Level-6 Race | REMOVE | Too visible/obvious |
| Generic unrestricted Swing Window | REMOVE | Mostly narrated stomps extending |
| Structures Lost While You Were Dead | REMOVE | Removed during final Tier A selection |
| Raw Vision Cleared count | REMOVE / REPLACED | “So what?”; replaced by Quick Clears / Region Sweep |
| Enemy Barely Warded | REMOVE | Not useful enough for scarce slots |
| Enemy Boss Control | REMOVE | Usually known from match |
| Literal map visibility % | PROHIBITED | Data does not support real visibility |
| Deward → deaths consequence | REMOVE | Confounded; base rate too high |
| Unused Active Item | REMOVE | Strict signal too rare / raw misleading |
| Activation-rate extremes | REMOVE | Trivia / weak |
| Lane Item Race | REMOVE | Nonsensical or too rare |
| Enemy Spike Cluster | REMOVE | Too common / boring |
| Other item execution experiments | REMOVE | Did not survive |

---

# 13. History principles and final history contract

The principles in §13.1–13.5 were locked before the final pass. The **final history contract** from the 2026-09-16 research is in §13.6.

## 13.1 History is candidate-specific

History is not required for the whole post-match system.

Some cards are valuable as intra-match facts.

Some cards become valuable only when personalized against history.

---

## 13.2 History-required candidates

Currently:

1. Own Lane vs Your Usual
2. Extreme Opponent Start vs Your History
3. Own Key Item Timing vs Your History

Without sufficient history:

- these candidates simply do not fire,
- the system does not invent a “personal baseline.”

---

## 13.3 History-optional candidates

History may enrich but must not gate:

- Enemy Early-Rich Hero
- Enemy Core Early Key Item
- Enemy Stacking Edge
- Enemy Smoke Volume
- other enemy-team behavior where a bucket-level personal comparator is meaningful.

---

## 13.4 Do not over-segment history

Previous research demonstrated that role-scoped history becomes sparse quickly.

Therefore:

- use role when the metric is role-dependent,
- avoid adding role/hero dimensions to team-level enemy behavior without evidence,
- do not create cohorts so narrow that the feature almost never becomes eligible.

The final history research pass is explicitly testing this.

---

## 13.5 Do not say “ever” casually

Even if a current match is the fastest in the locally retained sample, the product must not say:

> “your fastest ever”

unless the app truly has complete lifetime comparable history.

Prefer scoped claims such as:

> “your fastest across your last 18 comparable Standard Offlane matches.”

Exact wording thresholds remain pending. *(Resolved in §13.6.)*

---

## 13.6 Final history contract

**STATUS: FINAL RESEARCH RECOMMENDATION (2026-09-16)**

Evidence: 31 real account histories (9,930 eligible matches) replayed chronologically. Stability was measured against each account's own 60-match reference (40 for items). Details: `POST-MATCH-FINAL-RANKING-HISTORY-PLAYER-AUDIT.md` §4–6.

### Claim levels

N = the number of comparable prior matches in the window.

| N | Allowed |
|---|---|
| < 10 | No historical wording at all |
| 10–19 | Median-only secondary line ("about 2 minutes earlier than your usual across your last 14"). **Never a card on its own.** |
| ≥ 20 | Record wording: "your fastest / best / worst / highest / most across your last N {mode} {role} [item] …". History-required cards become eligible. |
| ≥ 30 | "one of your 3 fastest / best across your last N"; "top 10% of your last N"; "unusually early for you". Continuous metrics only (not stacks or whole minutes). |
| Never, in insight cards | "ever", "all-time", "personal record", "PB", exact percentiles |

**Why these cut-offs.** A "record across your last N" is still in the top 5% of the account's longer reference:

| N | Share of records that hold up |
|---:|---|
| 3 | 19–27% |
| 10 | 51–63% |
| 20 | **80–90%** |
| 30 | 91–100% |

- The chance of a record by luck alone is 1/(N+1): 4.8% at N = 20, and 4.6–4.9% was measured.
- Rarity claims ("top 3", "top 10%", "unusual") reach at least 80% precision only at N = 30.
- At N = 20, role cohorts are available for 69% of evaluations; enemy-team cohorts for 89–91%.

**Rules for the wording.**
- N is always shown.
- "Your usual" always means the window median.
- A record must beat the previous record by the card's margin; an exact tie is not a record.

### Window, recency and patch

- **Window:** the **most recent 50 comparable eligible matches** in the user's currently entitled retained history. There is no calendar limit. Beyond 50, precision saturates and mostly old patches are added.
- **Item timings** (own and enemy) also require the **same major patch** (7.xx; lettered sub-patches count as the same). BKB timing moved about +2:10 within accounts between 7.39 and 7.40. Lane gap, opponent CS, stacks, Smoke rate and goal minutes did not drift materially, so they carry no patch scope.
- **Recompute:** history results are recomputed deterministically when the methodology or entitlement changes, matching the existing progress-history rule.

### Comparator keys

| Card | Key | Min N | Extra rules |
|---|---|---:|---|
| Own Lane vs Usual | mode bucket + effective role | 20 | **Cores only** — support lane gaps were 0 of 8 GOOD. Record must beat the previous one by ≥ 100 (Standard) / 200 (Turbo) gold. |
| Opponent Start vs History | mode bucket + effective role | 20 | **Cores only.** Counterpart CS must also be ≥ the population p90 for that position, and a strict window maximum. |
| Own Key Item vs History | bucket + role + item + major patch | 20 | Fastest only; margin ≥ 60 s / 30 s. Hero is not part of the key (only 11.5% availability). |
| Enemy Early-Rich / Early Item / Stacking / Smoke (enrichment) | bucket (+ item and major patch for item timing) | 20 | Secondary line only; never changes eligibility or band. Enemy metrics do not depend on the user's role, so role is not part of the key. |

### Sparse history and new users

- History-required cards simply do not appear below N = 20.
- Enemy cards render without the history line.
- No population number is ever presented as "your usual".
- **Free bootstrap:** 30 matches per bucket at link time.
  - Role cohorts reach N ≥ 20 in only 0–34% of evaluations (Turbo offlane 0%); item cohorts in 8–19%.
  - History cards therefore mostly appear once post-link matches accumulate. This is expected behaviour, not a defect.

### Relation to the Personal Best system

Insight cards never make "ever" claims. The existing Personal Best system keeps its own rules. Nothing in this contract changes PB or progress-history methodology.

---

# 14. Ranking direction and final ranking rule

§14.1–14.3 record the architecture that was locked first. The **final rule** from the 2026-09-16 research is in §14.4.

## 14.1 Reject giant universal percentile infrastructure for V1

**LOCKED**

A theoretically elegant universal cross-candidate percentile ranker would require a larger reference-distribution project.

The owner does not want to spend another multi-day collection effort just to create that infrastructure.

Therefore V1 ranking should reuse the already validated candidate-specific thresholds.

This is a pragmatic V1 architecture decision, not a claim that percentile ranking is statistically inferior.

---

## 14.2 Threshold-based V1

**LOCKED DIRECTION**

Each candidate has its own:

- eligibility threshold,
- relevant magnitude/severity measurement,
- mode/role/history guard.

The remaining open question is the **simple common ordering rule** across those candidate types.

That is currently being researched. *(Resolved in §14.4.)*

---

## 14.3 Ranking constraints already fixed

Whatever final ranker is chosen, it must preserve all of these:

- deterministic,
- max 3 cards,
- no forced fill,
- Tier A not automatically above Tier B,
- no own-team/enemy-team balancing,
- no generic diversity quota,
- no generic merge engine,
- candidate type must already be product-approved,
- unreliable/pending candidates cannot outrank reliable cards merely due to magnitude.

---

## 14.4 Final threshold-based ranking rule

**STATUS: FINAL RESEARCH RECOMMENDATION (2026-09-16)**

### Pipeline

1. **Global eligibility and the feeding guard.** If any player has ≥ 8 deaths before 10:00 (Standard) / 8:00 (Turbo), the match gets no cards.
2. **Candidate eligibility and guards** (§15.3).
3. **Severity.** Each card gets a band — NOTABLE (1), STRONG (2) or EXTREME (3) — from its own validated ladder (qualify / strong / extreme), plus a level within the band:

   ```text
   level = (v − q) / (s − q)                  NOTABLE
         = 1 + (v − s) / (e − s)              STRONG
         = min(3, 2 + (v − e) / (e − s))      EXTREME
   ```

   - Tier B shape cards and history cards use the categorical bands defined in the report (§2.2).
4. **Match-story guard.** Keep at most **one** card from the Match Lead Story family, choosing the first eligible card in this order:
   1. Comeback Win
   2. Lost From Ahead
   3. Close Most of Game
   4. Even Then Separated
   5. Lead Flip
   6. Lead Eroded
   7. Deficit Recovered
   8. Late Reversal
5. **Sort** by:
   1. rank class (ascending):
      - **1** = Comeback Win, Lost From Ahead;
      - **3** = Enemy Early Key Item, Vision Region Sweep;
      - **2** = everything else;
   2. band (descending);
   3. level (descending);
   4. fixed tie order.
6. **Show** the first min(3, n) cards. n may be 0. Never fill.

**Tie order** (used only when class, band and level are exactly equal):

Comeback Win > Lost From Ahead > Even Then Separated > Own Lane vs Usual > Enemy Smoke Volume > Enemy Stacking > Lead Eroded > Own Item vs History > Quick Clears > Close Most of Game > Lead Flip > Deficit Recovered > Enemy Early-Rich > Opponent Start vs History > Late Reversal > Enemy Early Item > Region Sweep

### Why this and not severity alone

Test set: 120 manually ranked real multi-card recaps (332 cards).

| Rule | Pairwise agreement | Top-1 agreement |
|---|---:|---:|
| Severity bands + normalized exceedance only (the originally proposed simple rule) | 57–58% | – |
| Same, with the story guard | 64–66% | 54–57% |
| Random order | 50% | – |
| **Final rule** | **83%** | **80%** |
| Final rule, class learned on half the data (cross-validated) | 79% | 75% |

- **The reason:** card *type* matters more than distance past a threshold. A p99 early item is still less interesting than a p90 comeback.
- **What was tested and not adopted:**
  - A Tier A tie-break made results worse.
  - "EXTREME jumps a class" made results worse.
  - Additive scores and a two-class version were no better.

### Why the story guard is allowed

It is a **specific combination guard, not a generic redundancy engine**:
- It applies to one family that is already defined as a single match-lead story.
- It fires on a measured, repeated harmful pattern: same-story duplicates in 43% of multi-card recaps.
  - Lost + Lead Flip: 280
  - Comeback + Lead Flip: 274
  - Comeback + Late Reversal: 219
  - Comeback + Deficit Recovered: 117
  - Lost + Lead Eroded: 107
- It also removes the only contradictory recaps found, Close Most of Game + Lead Flip (56 cases).
- 52 of the 61 cards it removed in the test set had been independently marked as duplicates.

No other combination guard was justified.

### Unchanged principles

All §14.3 constraints hold:
- Tier A is not above Tier B;
- no side, result or diversity balancing;
- no forced fill.

The rank classes were derived from the manual review and stayed stable under cross-validation. They are not a free-form weight vector.

### Missing data

- Missing wards → vision cards ineligible.
- Lane counterpart unresolved → lane history cards ineligible.
- History below the gate → history card ineligible, and the enemy card renders without its line.
- Playback null or mismatched → Smoke→Kills enrichment absent.
- Tier B shape confidence < 0.7 → no Tier B card.

---

# 15. Player-context audit — completed 2026-09-16

§15.1 keeps the original audit brief. The results are in §15.2–15.4.

## 15.1 Original audit brief

The owner explicitly postponed the full player-context audit until the candidate pool was stable.

Tier A selection is now wrapped, and Tier B is locked enough for that audit to proceed.

The final audit must challenge every surviving candidate against real Dota context.

Questions include:

- Is the fact technically true but misleading?
- Did the player obviously already know it?
- Does it produce a “so what?” reaction?
- Does the wording contradict the actual outcome?
- Is the comparison nonsensical for the user's role?
- Is Turbo producing fake extremes?
- Is a short stomp generating false significance?
- Is the final push creating a fake “pattern”?
- Is the card implying causality?
- Is a hero's natural economy profile creating fake anomaly?
- Does a history sample look more authoritative than it is?
- Do individually good cards produce a stupid recap when combined?

This audit should be aggressive.

A candidate that repeatedly fails real player sense should be:

- guarded,
- rewritten semantically,
- or removed.

Coverage is secondary to quality.

---

## 15.2 Audit result summary

**Scale:** about 1,100 real-match ratings in total, on the scale GOOD / ACCEPTABLE / BORING / MISLEADING.

| Round | What was rated |
|---|---|
| Round 1 | 30 per candidate |
| Fresh holdouts | three rounds after guard changes |
| Recaps | 60 full selected recaps |
| Ranking | 120 multi-card recaps |

| Candidate | Before guards (G / A / B / M) | Fresh evidence under final rule | Verdict |
|---|---|---|---|
| Dramatic Lane Path | 0 / 4 / 25 / 1 | – | **REMOVE** (owner confirmation, §7.1) |
| Own Lane vs Usual | 15 / 14 / 1 / 0 (supports 0 of 8 GOOD) | cores 5 / 3 / 0 / 0 | KEEP WITH GUARD |
| Opponent Start vs History | 16 / 11 / 3 / 0 (cores 14 / 5 / 0 / 0) | – | KEEP WITH GUARD (cores only) |
| Comeback Win | 23 / 6 / 0 / 1 | 15 / 5 / 0 / 0 | KEEP WITH GUARD |
| Lost From Ahead | 22 / 8 / 0 / 0 | 14 / 6 / 0 / 0 | KEEP |
| Major Sustained Lead Flip | 16 / 11 / 1 / 2 | 10 / 10 / 0 / 0 | KEEP WITH GUARD |
| Enemy Stacking (Standard) | 12 / 15 / 3 / 0 | 7 / 12 / 1 / 0 | KEEP |
| Vision Quick Clears | 12 / 14 / 4 / 0 | 8 / 12 / 0 / 0 | KEEP WITH GUARD |
| Vision Region Sweep | 7 / 12 / 11 / 0 | 8 / 20 / 4 / 0 | KEEP WITH GUARD |
| Enemy Smoke Volume | 6 / 13 / 11 / 0 (Turbo 0 GOOD) | Standard 5 / 5 / 0 / 0 | KEEP WITH GUARD (Standard only, §9.7) |
| Smoke → Kills | 5 / 3 / 1 / 0 | replicated ×1.6 over chance | enrichment; recommend lock |
| Enemy Early-Rich Hero | 9 / 18 / 3 / 0 | 16 / 14 / 2 / 0 | KEEP WITH GUARD |
| Enemy Early Key Item | 0 / 9 / 20 / 1 | 7 / 13 / 0 / 0 | KEEP WITH GUARD |
| Own Key Item vs History | 7 / 8 / 15 / 0 | 10 / 2 / 0 / 0 | KEEP WITH GUARD (fastest only) |
| Close Most of Game | 13 / 9 / 5 / 3 | 27 / 16 / 0 / 1 | KEEP WITH GUARD |
| Even Then Separated | 6 / 7 / 9 / 8 | 20 / 4 / 0 / 0 | KEEP WITH GUARD |
| Lead Eroded | 4 / 10 / 3 / **13** | 6 / 6 / 0 / 0 | KEEP WITH GUARD |
| Deficit Recovered | 6 / 21 / 3 / 0 | 7 / 5 / 0 / 0 | KEEP WITH GUARD |
| Late Reversal | 11 / 5 / 0 / 0 | 12 / 4 / 0 / 0 | KEEP |
| Structure contradiction | natural in all 6 seen | – | KEEP (enrichment) |

**Recap audit:** 60 selected recaps rated 36 GOOD / 21 ACCEPTABLE / 3 WEAK. All three weak recaps were Close Most of Game + Lead Flip contradictions, which the story guard now removes. Complementary pairs read fine and are **not** guarded:
- early-rich + early item on the same hero;
- worst own lane + opponent-start record;
- quick clears + sweep;
- enemy-heavy recaps in losses.

---

## 15.3 Final guards

| Candidate | Exact guard |
|---|---|
| All | Feeding guard (≥ 8 deaths before 10:00 / 8:00 → no cards) |
| Match Lead Story family | At most one card (§14.4) |
| Comeback Win / Lost From Ahead | Maximum deficit or lead measured excluding the final 3 minutes. Copy states the result; "won despite trailing" if still behind at the end. |
| Lead Flip | Curve without its last 3 minutes; show the **latest** qualifying flip; ladder 7.9 / 12.1 / 21.9k (Standard), 14.2 / 19.4 / 27.5k (Turbo) |
| Lead Eroded / Deficit Recovered | Peak ≥ floor (5k Standard / **10k Turbo**); peak ≥ 6 min after window start; end value on the original side, or within max(½ floor, ¼ peak) for "recovered"; no interim opposite lead beyond 2 × floor. Copy uses actual minute values and states the result. |
| Close Most of Game | Close share ≥ 0.75; window ≥ 20 min (Standard) / 16 (Turbo); confidence ≥ 0.7; wording "most of", never "throughout" |
| Even Then Separated | Largest single-minute gap before separation ≤ 7,500; window ≥ 18 / 20 min; the separating side is the winner |
| Late Reversal | Winner-only (unchanged) |
| Enemy Stacking | Standard only (unchanged); enemy ≥ 7 by 20:00; gap ≥ 4 |
| Vision Quick Clears / Region Sweep | §9.4 |
| Enemy Smoke Volume | §9.7 |
| Enemy Early-Rich Hero | §9.9 |
| Enemy Early Key Item | §10.1 |
| Own Lane vs Usual / Opponent Start vs History | Cores only; margins and population gate as in §13.6 |
| Own Key Item vs History | §10.2 |
| Tier B shapes | shape_confidence ≥ 0.7 |

The machine-readable version of every rule and ladder is `post-match-final-audit-data/final-candidate-contract.json`.

---

## 15.4 Safe claims (summary)

Each card states only observed facts:
- values;
- times;
- counts;
- the match result;
- "across your last N …".

Card-specific DO-NOT-SAY lists are in `POST-MATCH-FINAL-RANKING-HISTORY-PLAYER-AUDIT.md` §10. New items confirmed by the audit:

- Lost From Ahead: no "threw".
- Deficit Recovered: no "comeback" in a loss.
- Early Item: no "finished" or "completed" (purchase only).
- Quick Clears: always "at least N".
- Smoke→Kills: no "successful".
- History: no "ever" or exact percentiles.

---

# 16. Latest focused vision research — product interpretation

The focused vision study materially changed the product decision.

## What the study disproved

It did **not** find enough evidence to support:

- literal map-visibility percentages,
- death-after-deward as a strong causal/consequence story,
- tower/NW aftermath as a useful vision headline,
- “no standing observer” gaps as enemy-created pressure.

## What it found useful

Two concrete patterns:

1. repeated **Quick Clears**,
2. concentrated **Region Sweeps**.

This is why the product now treats vision as:

> a pattern of enemy clearing behavior,

not:

> a raw count of wards destroyed.

That is the current product model.

---

# 17. Latest focused Smoke research — product interpretation

The focused Smoke analysis produced an important correction:

> “kill within 60 seconds of Smoke” is not automatically impressive.

Dota is fight-heavy enough that ordinary moments frequently have kills shortly afterward.

Therefore the enrichment must be more selective.

The latest research supports a **modified, strongly gated enrichment** rather than the old simple 50% rule.

At the time of this checkpoint:

- base Smoke Volume is fully locked,
- playback Smoke→Kills enrichment has a recommended deterministic rule,
- the owner has not yet explicitly given the final “lock it” response,
- so the decision status remains:
  **research-validated recommendation, pending owner lock** *(resolved 2026-09-17: LOCKED)*.

If the owner locks it later, this document should be updated by changing only that status and preserving the rule/evidence.

**2026-09-16:** the rule replicated on 66 fresh team units (§9.8). **2026-09-17: owner locked it.**

---

# 18. Coverage philosophy

The product does not optimize for “a card in every match.”

Important accepted observations:

- Tier A alone is insufficient for every match.
- Tier B improves useful coverage substantially.
- A remaining no-insight rate around 13–17% is acceptable.
- The app can later use a different generic post-match headline/state when no special card exists.
- Do not weaken unusualness thresholds simply to increase coverage.

This is a core product decision and should survive future optimization.

### Coverage update from the final audit (2026-09-16) — ACCEPTED by owner 2026-09-17

The 13–17% no-insight figure was measured on the **earlier, larger pool**, which still included candidates the owner later removed: Support Lane Pair, Boss Control, Steady Edge, the moderate Tier B signals, CS-vs-Gold, and others.

With the locked pool plus the final guards, the no-insight rate is:

| Population | No special card | Standard | Turbo | Win | Loss |
|---|---:|---:|---:|---:|---:|
| Tuning corpus (886 matches; no history; with vision) | **57%** | 49% | 67% | 62% | 53% |
| Established accounts (fresh matches; with history; no vision data) | **61%** | 51% | 72% | 66% | 57% |

**Where the coverage went** (any-card coverage):

| Stage | Coverage |
|---|---:|
| Locked pool before the audit | 69% |
| After all audit guards | 43% |

Every slice the guards removed was rated majority BORING or MISLEADING. The largest losses were:
- Enemy Early Item guard: −5 points;
- Even Then Separated guard: −5 points;
- Close Most of Game guard: −4 points;
- Smoke changes: −3 points.

**How often a recap has more than one card** (share of viewpoints): ≥ 2 cards 7–9%; ≥ 3 cards 1–2%.

Per the principle above, the thresholds were **not** loosened. The generic no-insight post-match state is now the **majority experience** and should be designed as such. Details: `POST-MATCH-FINAL-RANKING-HISTORY-PLAYER-AUDIT.md` §12.

---

# 19. Copy / semantic contract already established

Final copy templates are not written yet, but the semantic boundaries are.

## Allowed language

- “was”
- “reached”
- “bought”
- “used”
- “destroyed”
- “followed by”
- “within”
- “after”
- “before”
- “while”
- “across your last N comparable matches”
- “one of your strongest”
- “earlier than”
- “cut the deficit”
- “the game stayed close for most of…”

## Dangerous or prohibited without stronger evidence

- “because”
- “caused”
- “resulted in”
- “successful” when it implies causal success
- “cost you”
- “won them the game”
- “punished”
- “outplayed”
- “should have”
- “counter-built”
- “they saw you”
- “you had no vision”
- “map control” when inferred only from ward statistics
- “throw” as a neutral analytical label
- “ever” without complete lifetime scope

---

# 20. Superseded architecture ideas

Future agents should treat the following as explicitly rejected unless the owner reopens them:

1. **Tier A always outranks Tier B.**
2. **Exactly three cards per match.**
3. **Lower thresholds until every match has something.**
4. **Balance positive and negative cards.**
5. **Limit enemy-side cards.**
6. **Force one card from different families.**
7. **Generic merge/composite insight engine.**
8. **Generic redundancy-group suppression.**
9. **Universal percentile ranker requiring a large new corpus for V1.**
10. **Raw deward-count headline.**
11. **Literal map-visibility percentage.**
12. **Raw boss-control recap.**
13. **Ordinary lane-result recap.**
14. **User-facing `STEADY_EDGE`.**
15. **User-facing `ONE_SIDED`.**
16. **User-facing `UNCLEAR`.**
17. **Weak `LEAD_SWAPPED` Tier B card.**
18. **Item-execution family as a major V1 pillar.**

---

# 21. Current decision registry

Legend:

- **LOCKED** — product decision made.
- **KEEP** — candidate belongs in the product pool.
- **REMOVE** — candidate does not belong in V1.
- **PENDING VALIDATION** — product concept may be locked, implementation still needs evidence.
- **PENDING OWNER LOCK** — research recommends it, but owner has not yet explicitly locked it.
- **NOT YET DECIDED** — system-level contract still in research.

| Area | Decision | Status |
|---|---|---|
| Runtime analysis | Deterministic; no LLM per match | LOCKED |
| Card count | Up to 3, never forced | LOCKED |
| No-insight state | Acceptable | LOCKED |
| Candidate philosophy | “Not boring wins” | LOCKED |
| Tier priority | No automatic Tier A > Tier B | LOCKED |
| Side balance | No own/enemy balancing | LOCKED |
| Generic merge engine | Do not build | LOCKED |
| Causality | Sequence only unless proven | LOCKED |
| V1 ranker architecture | Threshold-based | LOCKED |
| Exact cross-candidate ordering | Story-family guard + 3 rank classes (1 first) → band → level → tie order (§14.4) | **FINAL** |
| Exact history contract | Last ≤50 comparable; N≥10 median line, N≥20 record/card, N≥30 rarity; no "ever"; item timing same major patch (§13.6) | **FINAL** |
| Final player-context audit | Completed; guards in §15.3 | **FINAL** |
| Tier B Close Most of Game | Keep | LOCKED |
| Tier B Even Then Separated | Keep | LOCKED |
| Tier B Lead Eroded | Keep | LOCKED |
| Tier B Deficit Recovered | Keep | LOCKED |
| Tier B Late Reversal | Keep, winner-only | LOCKED |
| Tier B Steady Edge | Remove | LOCKED |
| Tier B One Sided | Remove | LOCKED |
| Tier B Lead Swapped | Remove as Tier B | LOCKED |
| Tier B Unclear | Remove | LOCKED |
| Dramatic Lane Path | Remove (§7.1) | **LOCKED REMOVE** (2026-09-17) |
| Own Lane vs Usual | Keep; cores only (audit guard) | LOCKED |
| Opponent Extreme Start vs History | Keep; cores only (audit guard) | LOCKED |
| Support Lane Pair | Remove | LOCKED |
| CS-vs-Gold Split | Remove | LOCKED |
| Level-6 Race | Remove | LOCKED |
| Comeback Win | Keep | LOCKED |
| Lost From Ahead | Keep | LOCKED |
| Major Sustained Lead Flip | Keep | LOCKED |
| Structures While Dead | Remove | LOCKED |
| Enemy Stacking | Keep Standard only | LOCKED |
| Vision Quick Clears | Keep concept | LOCKED |
| Vision Region Sweep | Keep concept | LOCKED |
| Vision stats-only ward identity reconstruction | Fresh holdout passed (99.1% precision, 0 false rule fires); canonical V1 method | **VALIDATED** |
| Raw vision-cleared count | Remove | LOCKED |
| Enemy Smoke Volume | Keep; Standard only; enemy ≥ 4 Smokes ahead (§9.7) | **LOCKED** (2026-09-17) |
| Smoke → Kills optional enrichment | Modified rule; replicated on fresh data | **LOCKED KEEP** (2026-09-17) |
| Enemy Early-Rich Hero | Keep | LOCKED |
| Enemy Barely Warded | Remove | LOCKED |
| Enemy Boss Control | Remove | LOCKED |
| Enemy Early Key Item | Keep | LOCKED |
| Own Key Item vs History | Keep; fastest only (audit guard) | LOCKED |
| Unused Active Item | Remove | LOCKED |
| Activation extremes | Remove | LOCKED |
| Lane Item Race | Remove | LOCKED |
| Coverage expectation | ~57–61% no special card with final pool (§18) | **ACCEPTED** (2026-09-17) |

---

# 22. Open work before final SSOT

**Update 2026-09-17: ALL RESOLVED.** §22.5 and §22.6 were decided by the owner (§26). The final SSOT is `POST-MATCH-INSIGHTS-SSOT.md`.

**Update 2026-09-16:** §22.1–22.4 are resolved by research. What remains is owner confirmation (§22.5–22.6), then promotion to the final SSOT, followed by copy templates written within §15.4 and the report's §10.

## 22.1 Final threshold-based ranking rule

**RESOLVED → §14.4.**

A high-effort research pass has been commissioned to determine:

- exact cross-candidate ordering,
- simple common severity levels if viable,
- tie-break logic,
- how to compare Tier A and Tier B fairly,
- how to avoid arbitrary weights,
- how well the rule matches human/player ranking of real multi-candidate matches.

The target is a rule engineering can implement without interpretation.

---

## 22.2 Final history rules

**RESOLVED → §13.6.**

The same research pass is determining:

- minimum N,
- stability by sample size,
- comparator cohort,
- role/mode/item/hero segmentation,
- recency horizon,
- patch handling,
- record language,
- “one of your fastest” language,
- “unusual for you” language,
- percentile language,
- sparse-history fallback.

Do not finalize content templates for historical claims before this lands.

---

## 22.3 Final player-context audit

**RESOLVED → §15.** Two results change owner-locked items and need confirmation (§22.6).

The surviving Tier A + Tier B pool will be tested against:

- real match examples,
- Standard/Turbo,
- win/loss,
- role,
- match length,
- stomp cases,
- borderline thresholds,
- hero-specific behavior,
- end-game distortion,
- outcome contradictions,
- copy overclaim.

The audit is allowed to add targeted guards or remove a candidate if real player context proves it poor.

It should not reintroduce candidates merely for coverage.

---

## 22.4 Vision fresh holdout

**RESOLVED → §9.5.** Validated on 33 fresh matches; approved for Quick Clears and Region Sweep.

When STRATZ playback is operational again:

- test the stats-only ward identity reconstruction on fresh unseen matches,
- measure precision/coverage/region accuracy,
- decide whether Quick Clears and Region Sweep can safely use it historically.

The product concepts are already locked.

---

## 22.5 Smoke enrichment owner lock

**RESOLVED → LOCKED KEEP (2026-09-17).**

The focused Smoke study is complete enough to make a product decision.

The current research recommendation is the modified rule described in §9.8.

The remaining product action is simply:

- lock that rule,
- or keep Smoke Volume without the playback enrichment.

Do not revert to the old >=50% rule.

**2026-09-16:** replicated on fresh data (§9.8). Research recommendation: **lock**, applied to Standard, the base card's mode.

---

## 22.6 Owner confirmations required by the final audit

**RESOLVED (2026-09-17):** 1 → REMOVE confirmed; 2 → Standard only with edge ≥ 4 confirmed; 3 → accepted.

1. **Dramatic Lane Lead Path / Reversal → REMOVE** (§7.1). The dramatic case does not occur, and what fired was boring.
2. **Enemy Smoke Volume → Standard only, gap ≥ 4** (§9.7). Turbo was 0 GOOD in 24 reviewed cards.
3. **Acknowledge the no-insight rate of about 57–61%** (§18) and design the generic post-match state for it. Thresholds were not loosened.

*(Historical:)* until the owner answered, engineering was to treat items 1–2 as not buildable in their old form.

---

# 23. Supporting research basis

This checkpoint should be read together with the research under `#swiftMigration/`, especially:

- `post-match-intelligence-deep-research-v2.md`
- `post-match-deterministic-candidate-validation-v1.md`
- `VISION-INSIGHT-ENRICHMENT-RESEARCH.md`
- `SMOKE-TO-KILLS-VALIDATION.md`
- candidate validation data / research code
- Tier B match-shape validation materials
- `POST-MATCH-FINAL-RANKING-HISTORY-PLAYER-AUDIT.md` (final ranking / history / player-context audit, 2026-09-16) and `post-match-final-audit-data/` (contract JSON, ratings, review sheets, code)

Important research facts already incorporated here include:

- candidate validation across 886 eligible parsed matches,
- 8,860 player viewpoints,
- 1,772 team units,
- chronological history replay across real account histories,
- validated all-ten-player STRATZ stats access,
- exact/near-exact reconciliation for key event families,
- operational playback unreliability,
- historical history sparsity,
- tuned candidate fire rates,
- real-example review,
- focused vision reconstruction research,
- focused Smoke base-rate analysis.

Older documents remain useful evidence, but their candidate recommendation tables are **not the current product menu**.

---

# 24. Handoff guidance for future agents

Any agent continuing this work should:

1. Read `POST-MATCH-INSIGHTS-SSOT.md` first; use this file for decision history.
2. Treat `KEEP` / `REMOVE` decisions here as normative.
3. Use research files to obtain exact metrics and evidence.
4. Do not reopen rejected candidates casually.
5. Do not invent unresolved ranking/history rules.
6. Preserve the “not boring wins” standard.
7. Prefer fewer strong cards over comprehensive coverage.
8. Never add causal or visibility claims the data cannot support.
9. Keep Standard and Turbo analytically separate.
10. Use `POST-MATCH-INSIGHTS-SSOT.md` for history, ranking and guards. §22.6 is resolved.

---

# 25. Current end state in one paragraph

The V1 post-match system is now conceptually narrow and intentional: it may show at most three deterministic cards, selected from a curated Tier A + Tier B pool, with no forced fill, no side balancing, no generic merge engine, and no unsupported causal storytelling. Tier A is centered on personal-history lane/item records (the dramatic-lane card was later removed), meaningful match lead reversals, hidden enemy stacking/vision/Smoke/economy behavior, and early power spikes. Tier B provides useful match-shape context such as close games, separation after an even period, eroded leads, recovered deficits, and genuine winner-only late reversals. Raw or obvious recaps—ordinary lane results, boss counts, one-sided games, raw deward totals, trivial item usage, and similar “so what?” facts—have been explicitly removed. The remaining work is no longer broad candidate ideation: it is to finalize the ranking contract, the history contract, the player-context guards, validate the vision reconstruction on a fresh holdout, and make the final owner call on the newly validated Smoke→Kills enrichment.

The V1 deterministic post-match system is a guarded pool of Tier A and Tier B facts. It has three layers, all specified exactly and backed by real-match validation:
- **Ranking:** at most one match-lead story card, three rank classes, then each card's own severity band and level, showing up to three cards (§14.4).
- **History:** scoped, stability-gated claims — the last ≤ 50 comparable matches, records only from N ≥ 20, rarity wording only from N ≥ 30, never "ever" (§13.6).
- **Guards:** player-context guards that removed the boring and misleading slices found in about 1,100 real-match ratings (§15).

Stats-only vision reconstruction is validated. *(2026-09-17: Smoke→Kills locked; Dramatic Lane removed; Smoke Volume Standard-only; ~57–61% no-insight accepted. Post-match is closed — see §26 and `POST-MATCH-INSIGHTS-SSOT.md`.)*

---

# 26. Final owner resolution (2026-09-17)

All remaining owner calls are made. Post-Match Insights is closed; engineering and UI build against `POST-MATCH-INSIGHTS-SSOT.md` and `post-match-final-audit-data/final-candidate-contract.json` (version 1.0.0).

| Item | Resolution |
|---|---|
| Dramatic Lane Lead Path / Reversal | **REMOVED** |
| Enemy Smoke Volume | **KEEP — Standard only**; enemy ≥ 4 Smokes ahead, rate ≥ 1.60 / 10 min; Turbo Smoke Volume removed |
| Smoke → Kills | **LOCKED KEEP** as optional enrichment with the modified rule (n ≥ 3, k ≥ 3, k ≥ 70% of n, f ≥ 2 `isSmoke`-confirmed windows, 60 s window truncated at the next Smoke, playback count-matched); temporal wording only |
| ~57–61% no-card coverage | **ACCEPTED**; not an engine failure; no loosening |
| Ranking | **FINAL** — story suppression (max one), class 1 → 2 → 3, band, level, tie order, top 0–3 |
| History | **FINAL** — last ≤ 50 comparable; N ≥ 10 median line; N ≥ 20 record/card; N ≥ 30 rarity; never "ever"; same major patch for item timings only |
| Player-context audit | **FINAL** — all guards transcribed into the SSOT |
| Vision stats-only reconstruction | **VALIDATED** — canonical V1 method for Quick Clears and Region Sweep |

Final shipping pool: 17 card types (Tier A 12, Tier B 5) plus two enrichments (Smoke → Kills, structure contradiction).

# Smoke → Kill Enrichment — Validation Spike

Date: 2026-09-16 · Scope: only the optional playback enrichment on the accepted H3 Enemy Smoke Volume card.
Workspace: `.local/stratz-probe/smoke-kills-2026-09-16/` (`build.py`, `analyze.py`, `grid.py`, `final.py`, `rule.py`, `review.txt`, `threshold-grid.csv`, `tables.json`).

**Corpus:** every cached match that has both playback item events and ten-player stats. That is 18 matches: 7 full playback files and 11 lean `pbwin` files. One Standard match was excluded for a leaver, which leaves **17 matches** (8 Standard, 9 Turbo). Each match gives two teams, so there are **34 team units**, 26 of them with ≥3 Smokes. There are **170 Smoke activations** and 1,362 hero-credited kills.

**New STRATZ requests: 5.**
- 1 player-recent-matches lookup.
- 3 playback probes. One returned HTTP 403 ("different IP Addresses"); one retry was made after it.
- 1 lean stats batch for 4 older playback matches. It turned out to be unusable because those files contain no `itemUsedEvents`.

No bulk collection was run.

---

# 1. Verdict

**KEEP WITH MODIFIED RULE**

In plain English:

- **The base rate is high.** A random comparable moment in a Dota match is followed by a kill for that team within 60 s **~58%** of the time (phase-matched). The global figures are 51% in Standard and 59% in Turbo.
  - After a Smoke, the figure is **65%**. That is only **+7.6 pp (×1.13)**, and the 95% confidence interval includes zero.
  - So "a kill happened within 60 s of a Smoke" is mostly what Dota does anyway.
- **The old rule does not work.** It required ≥3 Smokes and ≥50% followed by a kill within 60 s.
  - It fires for **50%** of team units.
  - When the real Smoke times are replaced with ordinary moments from the same game phase, it still fires for **29%**. About 60% of its fires are what chance alone would produce.
  - It fires on teams whose Smokes were followed by kills *less* often than their ordinary moments were.
- **The sentence is still worth keeping, under two conditions:**
  1. The success share must be clearly above the base rate: **≥70%**.
  2. The sequence must be confirmed by STRATZ's own `killEvent.isSmoke` flag in **≥2 windows**.
- **New evidence changes how `isSmoke` should be used.**
  - `isSmoke` is tightly bound to Smoke timing. **0 of 1,037** kills more than 120 s from that team's last Smoke carry the flag. 91 of 96 flagged kills land 6–57 s after a team Smoke, which matches the 45 s Smoke buff plus the engage.
  - The earlier "41% recall" was measured against 60 s windows that we now know are mostly coincidental kills. It overstated how weak the flag is.
  - `isSmoke` therefore works as a **confirmation gate**. It does not replace playback timing.
- **Results with the modified rule:**
  - Fires for 9 of 34 team units (9 of 26 with ≥3 Smokes).
  - Manual review: 0 misleading and 1 boring.
  - The 9 fired teams had **44** Smoke windows followed by a kill against **27.3** expected at matched ordinary moments (×1.6).
  - The 17 teams it suppressed had 59 against 62.1 expected, which is no better than chance.

---

# 2. Event-source validation

## Exact fields

| Purpose | Field |
|---|---|
| Smoke activation | `match.players[].playbackData.itemUsedEvents { time itemId attacker target }` with `itemId == 188` (`item_smoke_of_deceit`) |
| Team | the player row's `isRadiant` |
| Activator | the player row. `attacker` equals that row's `heroId` in 188/188 cases; `target` is always null |
| Count check | `players[].stats.itemUsed { itemId count }` |
| Kill time | `players[].stats.deathEvents { time target attacker timeDead }` on the victim team. `attacker` is a heroId |
| Kill flag | `players[].stats.killEvents { time target isSmoke }` on the killer, joined on `(target, time)` |

## Correctness

| Check | Result |
|---|---|
| Playback Smoke events vs stats `itemUsed` Smoke count, per player | **180/180 player rows exact; 188 = 188 events** |
| Duplicate events (same player, ≤2 s apart) | 0 |
| Cross-player duplicates (same team, ≤2 s apart; would mean one activation is logged for the whole party) | 0. Only the activator is logged. Smallest same-team gap is 30 s at the 5th percentile, and 8 gaps are ≤30 s; these are real double-Smokes |
| Hero deaths with a matching `killEvents` row | 1,444 / 1,501. The remaining 56 have a non-hero attacker (creeps, tower, neutrals) and 1 is a deny |
| Duplicate death rows | 0 |

**Excluded source.** The four `pbwin_old_*` playback files have `itemUsedEvents` empty for **every** item: 0 events against 3,654 stats uses. They cannot be used. Production must treat a playback payload with no item events at all as "playback unavailable", not as "0 Smokes".

**Kill definition.** A team kill is an opposing-hero death whose `attacker` is a hero on the Smoking team. Creep, tower and neutral kills are excluded. Including them changes almost nothing (1,444 vs 1,500 kills).

## Confidence

**High.** One activation equals one event, attributed to the activator, with an exact count match.

---

# 3. Smoke → kill distributions

"Followed" means at least one kill by the same team in (t, t+X], counted only when the window is fully inside the match.

The matched control:
- uses every 5 s grid point in the **same match and same team, within ±5 min** of the Smoke;
- excludes any point within 120 s of any same-team Smoke.

"Alive-matched" additionally requires the same own-team and enemy-team alive counts (5 / 4 / ≤3).

The 95% confidence intervals come from a bootstrap that resamples whole matches (2,000 resamples).

## All (17 matches)

| Window | Smokes | % followed by kill | Matched control | Abs. lift [95% CI] | Rel. lift | Alive-matched control | Abs. lift |
|---|---|---|---|---|---|---|---|
| 30 s | 157 | 42.7% | 34.0% | **+8.7 pp** [+1.7, +16.1] | ×1.26 | 34.6% | +8.1 pp [+0.7, +16.9] |
| 45 s | 157 | 54.8% | 47.5% | +7.3 pp [−3.0, +16.5] | ×1.15 | 48.7% | +6.1 pp |
| **60 s** | 155 | **65.2%** | **57.6%** | **+7.6 pp** [−2.0, +16.7] | **×1.13** | 58.3% | +6.8 pp [−2.6, +16.5] |
| 90 s | 154 | 72.1% | 69.1% | +2.9 pp [−8.5, +12.5] | ×1.04 | 69.7% | +2.4 pp |
| 120 s | 152 | 78.9% | 75.9% | +3.1 pp [−5.9, +10.7] | ×1.04 | 77.8% | +1.1 pp |

## Standard vs Turbo (60 s)

| Mode | Smokes | Followed | Control | Abs. | Rel. |
|---|---|---|---|---|---|
| Standard (8 matches) | 115 | 64.3% | 56.2% | +8.1 pp [−4.6, +19.8] | ×1.14 |
| Turbo (9 matches) | 40 | 67.5% | 61.5% | +6.0 pp [−2.9, +18.7] | ×1.10 |

In Turbo, 45 s, 90 s and 120 s windows all show **zero or negative** lift. Turbo's base rate is higher, so 60 s means less there.

## Phase (60 s)

Phase boundaries:
- Standard: early <15 min, mid 15–35, late ≥35.
- Turbo: early <10 min, mid 10–20, late ≥20.

| Phase | Smokes | Followed | Control | Abs. |
|---|---|---|---|---|
| Early | 37 | 64.9% | 65.3% | −0.4 pp |
| **Mid** | 62 | **79.0%** | 61.1% | **+17.9 pp** [+6.4, +27.6] |
| Late | 56 | 50.0% | 48.5% | +1.5 pp |

Only mid-game Smokes clearly beat the base rate. Early Smokes are often lane-fight Smokes, and late games are full of fights anyway. This is not a reason to make the rule phase-specific (see §8). It is a reason to require confirmation.

## When the extra kills happen

Probability of ≥1 kill in each 15 s bin after the moment:

| Seconds after | 0–15 | 15–30 | 30–45 | 45–60 | 60–75 | 75–90 | 90–105 |
|---|---|---|---|---|---|---|---|
| Smoke | 20.2% | **29.5%** | 25.3% | 23.0% | 15.3% | 13.6% | 13.6% |
| Control | 19.4% | 20.6% | 22.2% | 21.4% | 19.6% | 18.6% | 17.4% |
| Ratio | 1.04 | **1.43** | 1.14 | 1.08 | 0.78 | 0.73 | 0.78 |

- **The extra kills fall at 15–45 s**, which fits the 45 s Smoke buff (current 7.41e values: 45 s duration, broken within 1025 range of an enemy hero or tower).
- **After 60 s the rate is *below* baseline**, likely because the team regroups or resets. Windows longer than 60 s only add coincidental kills.
- **Kills in the first 15 s show no lift.**

Other per-Smoke figures:
- Mean kills in a 60 s window: 1.33 after a Smoke vs 1.06 at a control moment. 38% of Smoke windows contain ≥2 kills.
- The activator got kill or assist credit on ≥1 window kill in 91 of 107 successful Smokes.
- Party membership is not observable, so no claim about who was in the Smoke is possible.

---

# 4. Threshold grid

Terms used in the grid:
- **Fire rate:** share of the 34 team units the rule fires on.
- **Null:** mean fires over 400 simulations in which each real Smoke time is replaced by a random phase-matched ordinary moment.
- **Chance share:** null ÷ fires, the portion of fires that ordinary moments would produce.

The full grid is in `threshold-grid.csv`. Selected rows:

| Rule (window truncated at next same-team Smoke) | Fires | Null | Chance share | GOOD / ACC / BORING / MISL. | Verdict |
|---|---|---|---|---|---|
| **Old:** n≥3, k≥3, share≥50%, 60 s | 17 (50%) | 10.2 | **60%** | 5 / 5 / 5 / 2 | **Reject** |
| n≥2, share≥50%, 60 s | 19 (56%) | 12.3 | 65% | — | Reject |
| n≥3, share≥50%, 45 s | 16 (47%) | 8.7 | 54% | — | Reject |
| n≥3, share≥50%, 90 s | 22 (65%) | 16.1 | 73% | — | Reject |
| n≥3, k≥3, share≥67%, 60 s | 11 (32%) | 3.3 | 30% | 5 / 4 / 2 / 0 | Better, still chance-prone |
| n≥3, k≥3, share≥67%, kill must be >10 s after, 60 s | 11 (32%) | 1.8 | 16% | same set | Marginal gain; hurts literal copy |
| n≥5, k≥3, share≥67%, 60 s | 5 (15%) | 1.6 | 32% | — | Too few Turbo teams qualify |
| n≥3, k≥3, share≥75%, 60 s | 9 (26%) | 3.1 | 34% | — | No better than 67% |
| n≥3, share≥67%, 30 s | 1 (3%) | 0.8 | — | — | Too rare |
| n≥3, share≥67%, 90 s | 14 (41%) | 6.1 | 44% | — | Reject |
| n≥3, ≥3 windows with an `isSmoke` kill (no share) | 10 (29%) | ≈0 | ≈0 | — | Display number would not match the sentence |
| **Chosen:** n≥3, k≥3, share≥70%, ≥2 `isSmoke`-confirmed windows, 60 s | **9 (26%)** | ≈0 on the confirmation leg; ~3 on the share leg alone | — | **5 / 3 / 1 / 0** | **Keep** |

Sensitivity of the chosen rule (fires out of 34):

| Change | Fires | Effect |
|---|---|---|
| Chosen rule | 9 | — |
| isSmoke-confirmed windows ≥0 or ≥1 | 11 | Adds 8998108566 Radiant (boring) and 8998108566 Dire (acceptable) |
| isSmoke-confirmed windows ≥3 | 6 | Drops 3 acceptable teams |
| Share ≥2/3 | 11 | Adds 6/9 (below base) and 4/6 (constant fighting). Both are bad, which is why the cut is 70% |
| Share ≥75% | 7 | — |
| 45 s window | 3 | — |
| 90 s window | 12 | — |
| n≥4 | 8 | — |

**Base-card interaction.** Among units meeting the H3 count floor (≥4 Standard / ≥3 Turbo), the chosen rule passes **6/15 Standard and 3/11 Turbo**, and 4/12 wins vs 5/14 losses, so it is not win/loss-skewed. H3 itself fired for only 4 of these 34 units; the enrichment passed 2 of those 4. H3 alone cannot give a reliable combined rate at this sample size.

**Robustness is low.** 34 units from 17 matches is a small sample. Treat the numeric cuts as provisional, but the *direction* is not provisional: a 50% share is uninformative against a 58% base rate.

---

# 5. Base-rate / coincidence analysis (mandatory)

**"If I choose a random comparable moment in a Dota match, how often does this team get a kill in the next 60 seconds?"**

| Moment | 30 s | 45 s | 60 s | 90 s | 120 s |
|---|---|---|---|---|---|
| Random minute, whole game, Standard | 31.0% | 41.7% | **51.1%** | 65.7% | 76.0% |
| Random minute, whole game, Turbo | 35.9% | 48.5% | **58.8%** | 72.9% | 81.9% |
| Same match, same team, ±5 min, no Smoke nearby | 34.0% | 47.5% | **57.6%** | 69.1% | 75.9% |
| Same, also alive-state matched | 34.6% | 48.7% | **58.3%** | 69.7% | 77.8% |
| **Smoke activation** | 42.7% | 54.8% | **65.2%** | 72.1% | 78.9% |

**Answer: more often than not.** Phase-matched, a team gets a kill in the next 60 s at **~58%** of ordinary moments. A Smoke raises that to **65%**.

What that means for the example sentence, "5 of 7 Smokes were followed by a kill within 60 s":
- At a 58% base rate, a team with 7 ordinary moments has a **~37% chance** of 5 or more. That example is exactly what chance produces.
- For 3 of 4 (≥75%), the chance is ~44%.

Two things separate a real pattern from coincidence:
1. **Share well above base (≥70%)**, *and*
2. **STRATZ's `isSmoke` flag** on the kills that follow. It never appears on kills away from a Smoke: 0 of 1,037.

For the 9 fired teams, observed windows were **44 vs 27.3 expected**. For the 17 suppressed teams, **59 vs 62.1**.

---

# 6. Edge cases (deterministic handling)

| Case | Evidence | Rule |
|---|---|---|
| **Overlapping Smokes / one kill after multiple Smokes** | 16 of 170 Smokes have another same-team Smoke within 60 s, and 14 kills fall in more than one Smoke's window. Example: 8965203762 Radiant, Smokes at 22:33 and 22:56 both "claim" the 23:03 four-kill fight. | **Each Smoke's window ends at min(t+60, next same-team Smoke time).** A kill counts only for the most recent Smoke. Flips 3 Smokes. Displayed N becomes conservative (never double-counted). |
| **Multi-kill sequence** | 38% of successful windows contain ≥2 kills. | Count **Smokes followed by ≥1 kill**, never kills. A 5-kill fight equals 1. |
| **Kill after the buff realistically ended** | Buff lasts 45 s. The kill-rate lift sits at 15–45 s, and the rate is below baseline after 60 s. 91/96 `isSmoke` kills are ≤57 s after a Smoke; the rest are 67–102 s. | **Window = 60 s** (45 s buff plus engage). Longer windows only add coincidence; 45 s cuts real engages (3 fires). |
| **Immediate kill (Smoke used during a fight already starting)** | 19 Smokes have a kill ≤10 s later, 9 of them with a kill or death in the prior 20 s. No lift in the 0–15 s bin. Examples: 8984212155 Dire Windranger 24:10 (+2 s) and Axe 34:28 (+3 s); 8987623192 Radiant Ringmaster 35:22 (+1 s). The earliest `isSmoke` kill is 6 s after a Smoke. | **No minimum delay in the counted number** (it would make the sentence under-report). Protection comes from the 70% share and the `isSmoke` gate, which removed the Dire-8984212155 case. Revisit a >10 s delay only if copy changes to non-literal. |
| **Game ends inside the window** | 5 Smokes. Example: 8996369573 Dire Smokes at 21:16 and 21:17 in a game that ended at 21:21. | Keep them in N (total uses) and count a kill only if one happened. This is conservative. |
| **Pre-horn Smokes** | 9 Smokes before 0:00 (e.g. −2:35). Kills before 0:00 do occur. | Treat like any other Smoke. |
| **Turbo** | Higher base rate (59% global at 60 s). Lift is ×1.10 at 60 s and ≤1.0 at 45/90/120 s. Chosen rule passes 3/11 Turbo units vs 6/15 Standard. | Same rule, no Turbo-specific window. The `isSmoke` gate carries the Turbo filtering. |
| **Repeated Smoke use / long games** | 80-minute games have 11–12 Smokes and constant fighting, so every ordinary moment has a high kill rate. | Share ≥70% plus confirmation. H3's per-10-minute rate gate already handles volume. |
| **Playback payload present but item events empty** | `pbwin_old` files have 0 events against 3,654 stats uses. | If Σ playback item-use events is 0 while Σ stats `itemUsed` > 0, treat as **no playback**. Also require the playback Smoke count to equal the stats Smoke count for the team; otherwise skip the enrichment. |

---

# 7. Real examples

"Exp" is the expected number of followed windows at matched ordinary moments. "isSmoke-conf." is the number of windows containing a kill flagged `isSmoke`.

## Excellent (chosen rule fires; GOOD)

1. **8974636369 Radiant, Standard, loss.** Lion Smoked 7 times; 5 were followed by a kill within 60 s (exp 3.4, isSmoke-conf. 4). There were Smokes at 15:32, 20:01, 22:43, 27:10 and 34:50, and Grimstroke died after four of them.
2. **8965203762 Dire, Standard, loss.** 6 Smokes, 5 followed (exp **0.9**, isSmoke-conf. 3). The team had only 27 kills in the game, and Sand King died after the 30:43, 34:13 and 37:32 Smokes.
3. **8987623192 Dire, Standard, loss.** 4 Smokes, 3 followed (exp **0.8**, isSmoke-conf. 3). A 15-kill team; its Smokes at 7:51, 15:51 and 23:18 each preceded a kill of Ogre Magi, Lina or Spectre.
4. **8975958401 Dire, Standard, win.** 11 Smokes, 8 followed (exp 4.7, isSmoke-conf. 4). Late Lion Smokes at 59:46 and 65:42 were each followed by two kills.
5. **8987623192 Radiant, Standard, win, H3 fires.** 6 Smokes, 5 followed (exp 3.7, isSmoke-conf. 3). Night Stalker Smokes at 10:26 and 17:14 each preceded 2–3 kills.

## Borderline / boring

1. **8984212155 Radiant, Turbo, win. Fires; BORING.** 4 Smokes, 3 followed, but exp 2.7. One success is a pre-horn Smoke; one kill came 51 s later with no flag.
2. **8965006124 Radiant, Standard, loss, 80 min. Fires; ACCEPTABLE.** 12 Smokes, 9 followed, exp 7.1, isSmoke-conf. 6. This is a real Smoke-gank team (Mirana and Shadow Shaman), but in a very kill-heavy game.
3. **8932986016 Dire, Turbo, loss. Fires; ACCEPTABLE.** 3 of 3 followed (exp 1.8, isSmoke-conf. 2). Two of those Smokes were used right after skirmishes.
4. **8998108566 Radiant, Turbo, win. Suppressed; BORING.** 3/4 followed but exp 3.3. It was a stomp and 72–93% of ordinary moments were followed by kills. Only 1 flagged kill. Correctly blocked.
5. **8975958401 Radiant, Standard, loss. Suppressed at 64%; ACCEPTABLE miss.** 7/11 followed, exp 5.3, isSmoke-conf. 3.
6. **8994374994 Radiant, Turbo, loss, H3 fires.** 4 Smokes in 4 minutes, 1 followed. The enrichment correctly stays off; the base card is still valid.

## Misleading or dangerous (the old rule or naive counting would fire)

1. **8984212155 Dire, Turbo, loss.** The old rule fires with 3/5. Two of the three "successes" are Smokes activated **2–3 s before kills in fights already running** (Windranger 24:10, Axe 34:28, each with kills or deaths in the prior 20 s). It implies hidden ganks that did not happen. *Blocked by the chosen rule* (share 60%, isSmoke-conf. 1).
2. **8965203762 Radiant, Standard, win.** Naive counting gives 5 of 6. Two Smokes 23 s apart (22:33 and 22:56) both claim the same 4-kill fight, and ordinary moments in 22–33 min were followed by kills **100%** of the time. *Blocked*: truncation gives 4/6 = 67% < 70%.
3. **8974636369 Dire, Standard, win, H3 fires.** The old rule fires with 6/9, but **exp 7.0**: this team got kills after its Smokes *less* often than after ordinary moments. Upgrading the H3 card here would be a false story. *Blocked* (67% < 70%).
4. **8984234793 Radiant, Standard, win.** The old rule fires with 4/8, against **exp 5.4**. *Blocked.*
5. **8965006124 Dire, Standard, win, 80 min.** The old rule fires with 7/12. Three of the seven successes are early-lane Smokes already inside skirmishes (5:36, 7:35, 10:33; control 53–100%), and only 1 kill is flagged. *Blocked* (58%, isSmoke-conf. 0).
6. **Per-Smoke caution inside a GOOD team.** 8987623192 Radiant, Ringmaster 35:22: the kill came 1 s after the Smoke, in the middle of a fight. The chosen rule still counts it. This is why copy must not describe individual Smokes as ganks.

---

# 8. Recommended deterministic rule (V1)

**Eligible if all of the following hold:**

1. The base **H3 Enemy Smoke Volume** card fires for the enemy team.
2. **Playback is usable for the match:**
   - playback is non-null;
   - the playback item events are not empty across all players;
   - the enemy team's playback Smoke event count (`itemUsedEvents`, `itemId = 188`) **equals** its stats `itemUsed` Smoke count.
3. Let enemy Smoke activations be t₁ < t₂ < … < tₙ, with **n ≥ 3**.
4. **Window for Smoke i:** (tᵢ, min(tᵢ + 60 s, tᵢ₊₁)]. The last Smoke's window is (tₙ, tₙ + 60].
5. **k** = number of Smokes whose window contains ≥1 death of *your team's* hero where `deathEvents.attacker` is an enemy hero.
6. **f** = number of Smokes whose window contains ≥1 such kill whose joined `killEvents.isSmoke == true`.
7. **Fire when** k ≥ 3 **and** k ≥ 0.70 × n **and** f ≥ 2.

**What the card shows:** n and k.

**Explicit non-rules:**
- No minimum delay.
- No phase-specific or Turbo-specific window.
- No kill counting; the unit is Smokes.
- No use of `isSmoke` in the displayed number.

---

# 9. Exact supported claim

**SAFE TO SAY**
- "They used Smoke {n} times; {k} were followed by a kill within 60 seconds."
- "{k} of their {n} Smokes were followed by a kill within a minute."

Rendering B reads most naturally. A is fine. C ("After 5 of them, they found a kill") is acceptable but "found" leans toward intent.

Notes on these sentences:
- {k} is a conservative count: when two Smokes share a window, the kill belongs to the later Smoke.
- Player-sense result: when the chosen rule fires, the sentence mostly lands as "oh, that's what they were doing" (5 GOOD, 3 ACCEPTABLE, 1 BORING, 0 MISLEADING out of 9). Under the old rule, 7 of 17 fires were "okay… kills happen" or false.

**DO NOT SAY**
- "{k} of their Smokes resulted in / led to / produced kills."
- "successful Smokes" or "Smoke ganks worked." This is too causal: 58% of ordinary moments are also followed by a kill, and one counted Smoke came 1 s before a kill in a running fight.
- "They ganked you {k} times with Smoke."
- "Their Smokes killed {hero}" or any hero-specific victim claim. It can be computed but is not validated.
- "{activating hero} led the Smokes / was in the gank." Party membership is unobservable.
- "Smoke kills" or "{f} kills came out of Smoke" as displayed text. `isSmoke` is used as a gate only; its exact STRATZ definition is undocumented.
- Anything comparing to "normal" rates, such as "more than usual after Smokes." The base-rate comparison was not validated per match.
- Any window other than 60 s in copy.

---

# 10. Confidence

| Area | Rating | Basis |
|---|---|---|
| Smoke timing source (`itemUsedEvents`) | **High** | 188/188 exact vs stats, 0 duplicates, only the activator is logged |
| Kill timing source (`deathEvents` / `killEvents`) | **High** | 1,444/1,444 hero kills join; timestamps to the second |
| Sequence calculation (windows, truncation, `isSmoke` join) | **High** | Deterministic; edge cases enumerated |
| Threshold robustness | **Low–Medium** | 34 team units from 17 matches (8 Standard, 9 Turbo); only 4 H3 fires. Confidence intervals are wide. The direction is solid (50% share is uninformative; the confirmation gate removes coincidence), but the 70% / f≥2 cut points are provisional |
| Player usefulness | **Medium** | Manual review of all 26 teams with ≥3 Smokes: 0 misleading fires under the chosen rule. The raw per-Smoke lift is modest (×1.13), so value depends on the gate |
| Playback availability | **Very low (currently ~0%)** | 2026-09-14: available for matches ≤90 days old. 2026-09-15: 90/90 null. 2026-09-16: 4/4 null, including match 8998108566, which returned full playback on 09-14, and a 4-day-old match. One HTTP 403 (IP binding) seen today. Earlier corpus eligibility: 1.9% |

**Data reliability and availability reliability are separate.** When playback exists, the sequence is exact. Getting playback is currently unreliable, so the enrichment will rarely or never render until STRATZ playback returns. The base H3 card is unaffected.

---

# 11. Owner decision

The evidence settles whether to ship: ship the enrichment **only with the modified rule in §8**, and retire the old ≥50% rule.

The one remaining decision is one this spike did not test.

`isSmoke` is historical (stats) and turned out to be tightly Smoke-bound. In the 886-match stats corpus, 55% of team units have ≥1 flagged kill and 18% have ≥4.

**Question:** should a stats-only variant replace this playback enrichment, given that playback is currently unavailable? An example would be an H3 sub-line built from `isSmoke`.

- It would need its own copy validation, because the flag's definition is undocumented.
- It is outside the scope of this spike.
- If the answer is no, the playback enrichment above stands as specified and simply renders whenever playback is back.

Sources for Smoke mechanics: [dotacoach.gg — Smoke of Deceit (7.41e)](https://dotacoach.gg/en/items/smoke-of-deceit), [Liquipedia — Smoke of Deceit](https://liquipedia.net/dota2/Smoke_of_Deceit).

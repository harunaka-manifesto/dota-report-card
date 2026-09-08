# V7 report narrative and the data it requires — 2026-09-04

The owner has redefined a Finding. This document does two things: it works out,
from a player's point of view, what each section of the report should actually
say, and it derives from that the exact provider fields a second collection pass
must fetch. The field names below are **verified against live specimens already
captured** in `.local/stratz-probe/enrichment/`, not guessed from the schema.

```text
PHASE: V7_REPORT_NARRATIVE_AND_DATA_REQUIREMENTS
STATUS: DESIGN — no collection performed
NEW STRATZ CALLS THIS PHASE: 0
CALIBRATION_RESERVED / SEALED_VALIDATION TOUCHED: NO
```

## 0. The redefinition, and what it changes

The old rule was *"tell the player something only if they are statistically
unusual against the population."* Under that rule most players get nothing,
because most players are near average — that is arithmetic, not a data problem.
The owner's rule is different and better:

> A Finding is something you would not know without looking at your whole year.
> Rank my own patterns by how strongly they show up **in my own data**. I do not
> need to be unusual to be told what I am.

Three consequences, and one thing that does not change.

1. **Reach stops being the binding constraint.** Coverage becomes "do we have
   enough of your games to measure this", which is 84–90% of accounts at a
   100-match bar. The 15%-versus-80% shortfall in the portfolio analysis was an
   artefact of the old rule and does not carry forward.
2. **Level statistics are readmitted.** Work already done pruned "how involved
   in fights you are", "how much risk you take", "how long your games run" as
   *population percentiles rather than Findings*. Under the new rule they are
   legitimate, and they are among the most reliable measurements in the corpus
   (split-half stability +0.95 and above).
3. **Ranking replaces gating.** The product needs a per-player ordering of
   "how loudly does this pattern show up in me", not a per-player pass/fail
   against the population.
4. **What does not change:** a pattern still has to be *real rather than noise*.
   Stability and honest uncertainty still decide whether a pattern is yours or
   an accident of 40 games. And a scoreboard is still not an insight — see §1.1.

## 1. What actually helps a Dota player

Two rules govern every section below.

### 1.1 A number is not an insight; a contrast is

"Your GPM is 520" tells a player nothing they cannot see on their profile.
"On Juggernaut your GPM is 610 in wins and 470 in losses, and the gap is already
open at minute 10" tells them where their games are decided. Every Finding in
this report is a comparison: wins against losses, this hero against your others,
after a loss against after a win, you now against you in January.

### 1.2 The diagnosis has to sit upstream of the result

"You lose when you die more" is circular and useless. The player already knows.
What helps is the thing that happens *before* the deaths: the 25 last hits they
were behind at ten minutes, the item that landed seven minutes late, the fact
that they were alone. A report that only describes outcomes is a scoreboard
with extra steps.

## 2. Section design

### Section 1 — History: your year on the record

Not Findings. Receipts, with the emotional hooks that make someone keep
scrolling: hours played converted to days, total kills, longest game, longest
win streak, distinct heroes, busiest month, first and last match of the year,
the hero you could not put down and what you actually did with it.

Most-purchased item excluding starters, plus your average timing for it —
requires an item vocabulary and an explicit consumable/starter exclusion list.

> **Rank is a problem.** "Rank gained" is on the wish list, and it is available
> from the provider. The V7 rules currently prohibit rank and MMR entirely, and
> that prohibition was written for a reason: rank leaking into analysis turns
> every Finding into a skill proxy. Showing a player their *own* rank movement
> as a descriptive fact is a different act from using rank as an analytical
> input. **This needs an explicit owner decision**, and if it is allowed it must
> be fenced: displayable in section 1, never a feature, never a context factor,
> never a cohort filter. Recommendation: keep it out of pass 2 until decided,
> because a field that exists in the corpus is a field that leaks.

### Section 2 — The wins: what you are actually doing right

Take the heroes the player has real volume on, and contrast their wins against
their losses **on the same hero, in the same position** — so hero strength and
role cancel out and what is left is them.

*If the hero is a core:*

| what | from | why a player cares |
|---|---|---|
| last hits and denies at 10 minutes | `lastHitsPerMinute`, `deniesPerMinute` cumulated | the single most coachable number in the game |
| lane outcome | `bottomLaneOutcome` / `midLaneOutcome` / `topLaneOutcome` + own `lane` | did you actually win the lane, or just farm |
| net worth at 10 / 15 / 20 / 25 | `networthPerMinute` | where the game forks |
| key item timing | `itemPurchases{time,itemId}` + item tiering | "your BKB is seven minutes later in losses" |
| tower damage and when | `towerDamage`, `towerDamagePerMinute` | do you convert a won lane into a map |
| fight presence | own `killEvents`/`assistEvents` against `radiantKills`/`direKills` | are you there when it matters |

*If the hero is a support:*

| what | from | why a player cares |
|---|---|---|
| first ward time, wards per game | `wards{time,type,positionX,positionY}` | the cheapest habit to fix |
| ward spread | variance of ward `positionX/Y` | warding the same two spots every game is legible and fixable |
| stacks | `campStack` | invisible work that decides games |
| healing and save timing | `healPerMinute`, save-item purchases | support impact that is not assists |
| deaths avoided while participating | `deathEvents` against participation | the real support skill |
| rune and bounty control | `runes{time,rune}` | early tempo |

*What your team does in your wins* needs the other nine players — a slim
projection, scalars only. In wins, do your cores actually get farm? Are kills
spread or concentrated? Do you win two lanes of three?

*The telling sign the game is going your way* is the best structural Finding
available and is fully derivable: sweep `radiantNetworthLeads` and
`radiantExperienceLeads` minute by minute and find the minute at which the lead
starts predicting **this player's** result. "Your games are decided at minute
18. Ahead at 18 you win 79%. Before that it is a coin flip." That is personal,
true, and it changes how someone plays minute 15.

### Section 3 — The losses, and how you die

Same contrast inverted, plus the death analysis, which is where the most
actionable material in the whole report lives.

- **When** you die: death times by minute band and by share of game elapsed.
- **In what state**: cross `deathEvents` against your own net-worth lead curve.
  Dying while ahead is a different disease from dying while behind — one is
  throwing, the other is already lost.
- **Alone or in a fight** — the strongest single insight available, and it needs
  nothing beyond what we can fetch: for each death minute, check whether your
  team scored or conceded kills in that same minute. No team kill activity means
  you died alone. *"61% of your deaths happen in minutes when nobody else on
  your team is fighting. You are getting picked off, not losing fights."*
- **Right before your spike**: deaths clustered in the two or three minutes
  before a key item lands, from `itemPurchases` times.
- **Where on the map**: **not available.** `deathEvents` carries only `time`.
  Position would need `playbackData`, which is a prohibited surface and is also
  enormous. `stats.locationReport` may offer a coarse substitute and has never
  been probed. Treat "where you die" as out of scope unless a probe says
  otherwise.

### Section 4 — How you respond to a loss

Existing research already established the between-match half of this and it is
the most reliable material in the corpus: whether you keep playing (split-half
stability +0.79), whether you switch hero (+0.90), how fast you re-queue
(+0.80), each measurable for 92–95% of eligible accounts.

The second pass adds the in-game half, which is new: after a loss, do your first
ten minutes get *worse*? Do your last hits drop, do you die earlier, do you
switch to Turbo? That is tilt, measured inside the game rather than inferred
from the schedule.

### Section 5 — What to improve

Three rules, or this section becomes horoscope.

1. It comes from **the player's own gap** — their losses against their own wins,
   never against a population average.
2. It is **one thing**. A list of six is a list of zero.
3. It is **checkable in the next game**, by us, from the same fields.

Worked examples, each fully derivable from the fields specified below:

| trigger in their data | the recommendation | how we verify it next time |
|---|---|---|
| losses average 22 fewer last hits at 10 min | "For five games, care about nothing but last hits until minute 10." | `lastHitsPerMinute` cumulated to 10 |
| 61% of deaths in no-team-fight minutes | "Do not cross the river without a teammate on screen." | death minutes against team kill minutes |
| BKB at 31 min in losses, 24 in wins | "Buy BKB before your damage item." | `itemPurchases` ordering and time |
| first ward at minute 4 | "Place your first ward before the horn." | `wards[0].time` |
| deaths spike 20–25 min while ahead | "When you are ahead at 20, take the tower instead of the fight." | death times against net-worth lead |

### Section 6 — Archetype (for fun, not for science)

Two primary axes plus a modifier, which yields a memorable grid rather than a
personality-test sprawl:

- **Tempo** — where your impact peaks: Early / Mid / Late
- **Fight style** — Frontliner (dies in fights, high participation) / Opportunist
  (low deaths, picks moments) / Ghost (low participation either way)
- **Modifier** — Metronome or Streaky, from across-session variance

3 × 3 × 2 = 18 combinations, plus two rare specials for genuine outliers = 20.
Every axis is computed from data, and the label is allowed to be unserious.

### Section 7 — Share cards

One headline number, the archetype, one contrast stat. Constraint: a share card
must be true and must not be an insult. Nobody shares "you die alone."

### Section 8 — Bridge to paid

The honest boundary. Free tells you what you are across a year. Paid does what a
year-level report structurally cannot: per-match review, matchup-specific
reads, opponent-aware analysis, and — the real product — tracking whether the
one recommendation actually changed anything.

### Section 9 — End

Recap, and the one thing.

## 2.10 Additions — insights the outline did not ask for

The nine sections describe a shape. These are the specific Findings I would
build inside it, chosen because each one is a **contrast**, sits **upstream of
the result**, and needs nothing beyond the field set in §3. Ordered by how much
I think they would change a player's next game.

### A. Do you convert a won fight into a map? — the biggest one

Your team wins a fight at minute 23: two or more kills, nobody dead on your
side. What happens in the next two minutes? A tower, or everyone walks back to
their jungle.

```text
signal   minutes with >=2 own-team kills and 0 own deaths
follow   towerDamagePerMinute in the next 2 minutes
```

*"When you win a fight, a tower falls within two minutes 64% of the time in
your wins and 21% of the time in your losses. You are winning fights and buying
nothing with them."* This is the most common mistake in the game below the very
top, it is invisible without a season of data, and it is one sentence to fix.

### B. Do you use your spike, or just buy it?

Your Blink lands at minute 22. Some players are in a fight 90 seconds later;
some farm for six more minutes.

```text
signal   time of a key item purchase
follow   own kill/assist events and own net-worth lead over the next 3 minutes
```

*"Your Blink Dagger lands at 22 minutes. In your wins you fight within two
minutes of buying it; in your losses you farm for another six."* Needs the item
vocabulary.

### C. Do you go back in too fast?

Not how many times you die — whether deaths come in runs. Two deaths inside 90
seconds usually means walking back into the same fight.

```text
signal   gaps between consecutive deathEvents
```

*"A third of your deaths come within 90 seconds of the previous one."* Derivable
from death timings alone, which makes it one of the cheapest strong Findings
available.

### D. Does winning your lane actually mean anything?

A very common and very frustrating pattern: you win the lane and the game is
level by minute 20 anyway.

```text
signal   lane outcome + own last-hit lead at 10 minutes
follow   own net worth and team lead at 20 minutes; tower damage between 10 and 20
```

*"You win your lane 58% of the time, and your team's lead at 20 minutes is the
same whether you won it or not."*

### E. Closer or comeback player?

This replaces the provider's opaque `COMEBACK` label with something we compute
ourselves and can explain.

```text
signal   own net-worth lead crossing +/-10k, and the eventual result
```

*"You close 91% of games where you go 10k up — but at 5k down you fold, well
below your own baseline."* Two numbers, both memorable, and they say something
real about temperament rather than skill.

### F. Your worst minute

Sweep the net-worth lead curve for the window where your position most
consistently slips relative to your own average.

*"Minutes 18 to 22 are where your games go wrong."* Legible, and it gives the
recommendation in section 5 a place to point.

### G. Vision coverage and vision predictability — for supports

Two separate ideas, both from `wards{time,type,positionX,positionY}`.

- **Coverage**: share of game minutes with at least one of your observers
  plausibly alive. *"Your vision covers 41% of the game; your wins average 58%."*
- **Predictability**: spread of your ward positions. *"78% of your wards go in
  three spots."* Wards in the same three places every game get killed, and this
  is the single most fixable support habit.

### H. Do you carry a TP scroll?

Once the item vocabulary exists: TP purchases per game, contrasted with deaths
that happen far from your team's activity. *"You buy three TP scrolls a game in
wins and one in losses."* Old-fashioned coaching, and it is measurable.

### I. Do you adapt your build, or run the same one?

Compare item purchase sequences across your games on the same hero.

*"You build the same first three items on Juggernaut in 89% of games."*
Adaptivity is a genuine axis and nobody can see it about themselves.

### J. Farm while alive, not farm overall

Last hits per minute **of time alive**, from last-hit trajectories and death
timings. Two players with identical GPM are different players if one of them is
dead a fifth of the game. It separates "farms badly" from "dies a lot", which
the raw number cannot.

### K. Session drift, measured inside the game

Earlier research rejected session drift because it was measured on match
outcomes, where nothing survived. In-game it is a different question and worth
re-testing: across a session, do your last hits at ten minutes decline? Do your
deaths move earlier? Match results are far too noisy to see fatigue. Laning
numbers are not.

### What none of these need

No field beyond §3, and no playback. Items B, H and I depend on the item
vocabulary; G depends on ward positions, which the specimens confirm are
returned. That is a useful check on the spec: the additions did not widen it.

## 3. What the second pass must fetch

Every field below appears in a **live specimen already captured** in
`.local/stratz-probe/enrichment/`, so availability is established, not assumed.

### 3.1 Own player, full detail — per parsed match

```text
scalars    kills, deaths, assists, numLastHits, numDenies, goldPerMinute,
           experiencePerMinute, networth, level, gold, goldSpent, heroDamage,
           towerDamage, heroHealing, isRandom, leaverStatus,
           lane, position, role, roleBasic,
           item0Id..item5Id, backpack0Id..backpack2Id, neutral0Id

stats      networthPerMinute, goldPerMinute, experiencePerMinute,
           lastHitsPerMinute, deniesPerMinute, heroDamagePerMinute,
           towerDamagePerMinute, healPerMinute, heroDamageReceivedPerMinute,
           campStack,
           killEvents{time}, deathEvents{time}, assistEvents{time},
           itemPurchases{time,itemId},
           wards{time,type,positionX,positionY},
           runes{time,rune}
```

Of these, only `killEvents`, `assistEvents` and `itemPurchases` are in the
current corpus. **`deathEvents` and every per-minute trajectory are missing, and
they are what sections 2, 3 and 5 are built on.**

### 3.2 Match level

```text
id, didRadiantWin, durationSeconds, startDateTime, endDateTime,
gameMode, lobbyType, gameVersionId, regionId, parsedDateTime,
firstBloodTime,
towerStatusRadiant, towerStatusDire, barracksStatusRadiant, barracksStatusDire,
radiantKills, direKills, radiantNetworthLeads, radiantExperienceLeads,
bottomLaneOutcome, midLaneOutcome, topLaneOutcome
```

`radiantExperienceLeads` and the tower/barracks status fields are new.

### 3.3 All ten players, slim — scalars only

```text
playerSlot, isRadiant, isVictory, heroId, position, role, lane,
kills, deaths, assists, numLastHits, numDenies,
goldPerMinute, experiencePerMinute, networth,
heroDamage, towerDamage, heroHealing
```

This is what "what your team does in your winning games" requires. It must stay
**scalars only**: the specimen that requested trajectories for all ten players
was rejected by the provider at a complexity of 6,159,595 against a ceiling of
310,000.

Other players' account identifiers must not be retained. Only the sampled
player is pseudonymised into the corpus; the other nine are context, not
subjects.

### 3.4 Must not be requested

```text
imp, award, behavior, intentionalFeeding, streakPrediction,
actualRank, averageRank, averageImp, rank, bracket,
analysisOutcome, predictedOutcomeWeight, winRates, predictedWinRates,
chatEvents, allTalks, chatWheels,
playbackData (either level), steamAccount identity blocks, dotaPlus
```

`analysisOutcome` is tempting — the provider will hand back `COMEBACK` for a
match — and it is exactly the kind of opaque derived label the rules exclude. We
can compute comeback ourselves from the net-worth lead curve, transparently.

### 3.5 Item identity — already collected, no fix needed

An earlier draft of this document reported that normalisation had dropped
`itemId` and that all 211,428 purchases read null. **That was wrong**, and the
error was mine: I probed the canonical table for a camel-case `itemId` when the
canonical schema uses `item_id`. The field is present and complete —
422,726 purchases scanned across 30 accounts, **262 distinct item ids, zero
nulls**. Nothing needs recovering and nothing needs repairing before pass 2.

What *is* still missing is the vocabulary: we have ids, not meanings. Id 43 is
the most-purchased id in the corpus at 57,015 purchases, which is almost
certainly a consumable rather than anything a report should celebrate. An item
reference table (id → name, tier, consumable/starter flag) is required before
any item-timing Finding ships, and the capability atlas already rates item
semantics as unverified for exactly this reason. That table is static reference
data, fetched once, and is not player data.

## 4. What pass 2 costs

From the existing request ledger: 7.0 history calls per account, and 71.2
parsed-batch calls per parsed account at eight matches per call. The observed
provider ceiling is 15,000 calls per day.

The pass-2 query is substantially heavier. Two things must be measured before
committing to a plan, and both are cheap:

1. **A complexity microprobe** — a handful of calls to find the largest batch
   size that stays under the 310,000 complexity ceiling with own-player full
   stats plus the ten-player slim projection. If the batch drops from eight to
   four, every estimate below doubles.
2. **A depth decision** — full parsed detail for all 900 research accounts at a
   batch of four is roughly 112,000 calls, about eight days of continuous
   collection. Restricting to ~300 DISCOVERY accounts is roughly 37,000 calls,
   about two and a half days.

Recommendation: microprobe first, then DISCOVERY depth, then CANDIDATE_TEST to
match. `CALIBRATION_RESERVED` and `SEALED_VALIDATION` stay untouched, and the
frozen cohort must not be topped up, replaced, or adaptively reselected — the
split manifest is already frozen and digested.

## 5. Owner decisions — settled 2026-09-04

### 5.1 Rank: display-only, and fenced in code

Decision: collect and show rank progression in section 1 as history. It is
**never** an analytical input.

"Show it but do not use it" is not a policy, it is a hope, unless the code
enforces it. The enforcement mirrors the reserved-split control that already
exists: rank lands in a separate display-only table that the research reader
cannot return, and the forbidden-field gate keeps failing closed on every
canonical research table and derived feature. Analysis code physically cannot
reach it; the report renderer can. Without that fence the field leaks into a
context projection within a month and every Finding quietly becomes a skill
proxy.

### 5.2 Depth: 300 accounts — enough for the decision

Yes. The question is how precisely we can estimate, across players, how
reliable and how heterogeneous each candidate is, because that is what ranks
candidates against each other.

| accounts | SE of a reliability of 0.7 | relative SE on `tau` |
|---:|---:|---:|
| 116 (today) | 0.048 | 6.6% |
| **300** | **0.030** | **4.1%** |
| 600 | 0.021 | 2.9% |
| 900 | 0.017 | 2.4% |

At 300 accounts, two candidates whose reliability differs by 0.10 separate at
about 2.4 standard errors. That is the actual decision being made, and it is
comfortably supported. For calibration: the parsed work already completed used
**116** accounts and still separated candidates unambiguously, from I² 0.236 to
0.969. Tripling that is not a close call.

What 300 does **not** buy, and should not be claimed later:

- population percentiles in narrow cells — "position 5 supports, Turbo, patch
  182" thins out fast across players, even though it stays fine at match level;
- reference statistics for rare heroes;
- a confirmation pass. These 300 are DISCOVERY. `CANDIDATE_TEST` needs its own
  depth before anything is confirmed, and `CALIBRATION_RESERVED` and
  `SEALED_VALIDATION` stay untouched.

Depth per account matters more than account count here, and it is already
strong: a median of 526 product-context matches per account across a year.

### 5.3 Where you die: probe `stats.locationReport`

`deathEvents` carries `time` only. `stats.locationReport` has never been
requested and its shape is unknown; it is the only route to a map answer that
does not touch playback. The microprobe adds it as a single field on a handful
of matches and reports the shape and the complexity cost. If it returns a
usable grid, "where you die" and "where you ward" both become answerable and
several Findings in §2.10 get sharper. If it does not, the report is scoped to
*when* and *in what state*, which is where the actionable material lives anyway.

## 6. Order of work

1. **Complexity microprobe** — a handful of calls. Find the largest match batch
   that stays under the 310,000 complexity ceiling with own-player full stats
   plus the ten-player slim projection, and establish `locationReport`'s shape
   and cost. Everything downstream is sized by its answer.
2. **Item vocabulary** — static reference data, fetched once. Without it,
   §2.10 B, H and I cannot ship and "most-purchased item" reports a consumable.
3. **Pass-2 collection** — 300 DISCOVERY accounts, full parsed detail, resumable
   from the existing runner and checkpoint, driven from the owner's terminal.
4. **Re-normalise and re-atlas** against the widened schema.
5. **Re-score the candidate universe under the new definition** — ranking rather
   than gating, with the level families readmitted.

The frozen cohort and split manifest are already digested and must not be
topped up, replaced, or adaptively reselected.

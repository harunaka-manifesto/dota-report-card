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

## 5. Open decisions for the owner

1. **Rank in section 1** — display-only, or keep it out entirely. Recommendation:
   out of pass 2 until decided, because a collected field leaks.
2. **Parsed depth** — 300 accounts or 900. This is days of collection, not a
   research question.
3. **Where you die** — accept "when and in what state" only, or authorise a
   probe of `stats.locationReport` to see whether a coarse map answer exists
   without touching playback.

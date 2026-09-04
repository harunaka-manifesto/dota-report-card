# The V7 improvement-recommendation model — 2026-09-05

Section 5 of the report ("what can be improved") needs a different computation
from the Finding ranking. This specifies it.

```text
PHASE: V7_IMPROVEMENT_RECOMMENDATION_MODEL
STATUS: DESIGN
NEW PROVIDER CALLS: 0
```

## 1. Why it cannot reuse the Finding ranking

The Finding ranking answers *what is most distinctively you*
(`docs/evidence/v7-finding-ranking-model-2026-09-05.md`). Distinctiveness is not
actionability. The most distinctive thing about a player may be the thing they
should keep doing.

A recommendation has to satisfy three properties the ranking does not:

1. it comes from **the player's own gap** — their losses against their own wins,
   never against a population average;
2. it is **one thing**, because a list of six is a list of zero;
3. it is **checkable in their next game**, by us, from the same fields.

## 2. The estimand

For player `p` and actionable dimension `d`, with the player's own matches split
into their wins and their losses:

```text
gap_pd = E[d | p, loss] - E[d | p, win]
```

The gap is context-adjusted exactly as the Findings are — hero, position, role,
lane, patch, game mode — so that "you lose more on harder heroes" cannot present
itself as a behavioural gap. It is standardized by the population spread of the
same dimension, so gaps on different dimensions are comparable:

```text
g_pd = gap_pd / tau_d
```

and weighted by reliability, on the same dependence-corrected definition:

```text
priority_pd = |g_pd| * r_pd * A_d
```

`A_d` is a fixed **actionability weight** in `[0, 1]`, assigned per dimension by
design and never fitted to data. It encodes how directly a player can change the
thing in their next game. Laning last hits at ten minutes is highly actionable;
whether your team wins a fight is not.

## 3. The upstream rule

A recommendation must sit **upstream of the result**. "You lose when you die
more" is circular: the player already knows, and it names an outcome rather than
a cause.

Concretely, a dimension is eligible only if it is a *behaviour the player emits*,
not a *result they receive*. Deaths-alone share is eligible — it describes how
they move. Net-worth lead at twenty minutes is not — it is a scoreboard.

This is a design-time property of each dimension, recorded in the registry
alongside `A_d`, and it is not negotiable at ranking time.

## 4. What the recommendation carries

For the single selected dimension:

```text
observation      the player's own win value, loss value, and the gap
direction        which way the gap runs
recommendation   one sentence, imperative, doable in the next game
verification     the exact measurement that will show whether it changed
sample           how many of their wins and losses the gap is computed from
```

The verification field is what makes this different from advice. Every
recommendation names the measurement that will confirm or refute it next time,
computed from fields already collected.

Worked examples, all derivable from the Pass-2 corpus:

| trigger in their own data | recommendation | verification |
|---|---|---|
| last hits at 10 min: 61 in wins, 39 in losses | "For five games, care about nothing but last hits until minute 10." | `last_hits_per_minute` cumulated to minute 10 |
| deaths in no-team-fight minutes: 61% | "Do not cross the river without a teammate on screen." | death minutes against team kill minutes |
| first real item at 24 min in wins, 31 in losses | "Buy your first big item before your damage item." | `item_purchases` filtered to real items |
| first ward at minute 4 | "Place your first ward before the horn." | `wards[0].time` |
| jungle gold share 41% in losses, 22% in wins | "Take the lane creeps when they are there." | farm distribution lane vs neutral |

## 5. Honesty constraints

1. **A gap that is not measured well is not a recommendation.** The same
   reliability weight applies; a noisy gap cannot be promoted to advice.
2. **No recommendation without a denominator.** Fewer than a stated minimum of
   wins *and* losses on the dimension, and it is not offered at all.
3. **Never present a population comparison as a personal gap.** The player is
   compared to themselves. `tau_d` sets the scale only.
4. **We do not claim causality.** The copy says what changed alongside their
   losses, not what caused them. A recommendation is a hypothesis the player can
   test, and the verification field is how they test it.
5. **"Helps me improve" is not measurable from this data.** Whether acting on a
   recommendation improves results is a question for a later cohort study, not a
   claim this report can make. The report may say *this is where your losses
   differ*; it may not say *this will make you win*.

## 6. Selection

Exactly one recommendation ships in section 5, chosen as the highest
`priority_pd` among eligible dimensions. Ties break toward the higher
actionability weight, then toward the larger sample.

Two runners-up are computed and retained for the paid tier, which is the natural
home for a longer list — see report section 8.

## 7. What this does not decide

```text
DECIDES: how the single improvement is chosen, and what it must carry
DOES NOT DECIDE: the actionability weights themselves, the minimum sample, or
         any copy
```

The weights are a design table to be filled in with the dimension registry; the
minimum sample is calibration and belongs to a later phase.

# The V7 improvement-recommendation model — 2026-09-05

Section 5 of the report ("what can be improved") needs a different computation
from the Finding ranking. This specifies it.

```text
PHASE: V7_IMPROVEMENT_RECOMMENDATION_MODEL
STATUS: DESIGN — AMENDED 2026-09-06 after the first run against the corpus
NEW PROVIDER CALLS: 0
```

> **Amended 2026-09-06.** Running this model over DISCOVERY falsified two
> parts of it. Section 2's standardization by `tau_d` silences section 5
> completely, and section 3's eligibility rule is not sufficient on its own.
> Both corrections, with the measurements that forced them, are in
> `docs/evidence/v7-recommendation-selection-2026-09-06.md`, and section 2 and
> section 3 below carry the amended text. The rest of the model stands as
> written.

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

**Amended: `tau_d` is the wrong denominator, and the corpus says so.**
`tau_d` is the *between-player spread of gaps*. Measured consistently it is
exactly zero on every dimension: for last hits at minute 10 the between-player
variance of the gap is 3.19 against a dependence-inflated measurement variance
of 5.55. Dividing by it makes every priority zero and ships no recommendation
at all.

The gaps themselves are not in doubt — the median player takes 2.4 fewer last
hits by minute 10 in their losses, and 248 of 262 players have a negative gap.
What is unmeasurable is how much players *differ* in it. Standardizing by
`tau_d` therefore asks "is your gap unusual", which section 5 constraint 3
forbids in as many words, and which is the same mistake the Finding model was
already corrected for: if everybody's last hits drop in their losses, each
player should still be told that theirs do.

The denominator is instead `s_d`, the dimension's own pooled match-to-match
residual spread — a unit conversion, identical for every player, which makes a
2.4-last-hit gap and a 0.06-share gap comparable without ranking one player
against another:

```text
g_pd = gap_pd / s_d
r_pd = s_d^2 / (s_d^2 + SE_pd^2 * D_d)
```

`r_pd` keeps the same functional form and the same dependence correction, so
constraint 1 still holds: a noisy gap cannot be promoted to advice.

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

**Amended: the upstream rule is necessary but not sufficient.** It asks
whether a dimension is a behaviour the player emits. The *gap* estimand needs
a second question the *level* estimand does not: is the measurement tracking
the match result?

`fight_conversion` passes the first and fails the second. Going to the tower
after a won fight is genuinely the player's own decision, which is why it
stays a legitimate Finding. But measured across a whole match, "you converted
fights into towers less" in a game you lost is close to restating that you
lost — and before the second rule existed it won 168 of 265 single slots while
carrying the second-lowest actionability weight in the table.

The second rule is measured, not judged. **A personal gap should vary in sign
across people.** A gap that runs the same way for essentially everybody is not
describing the player. The screen is the share of players carrying the modal
sign, cut at 0.95, fixed before the shares were computed:

| dimension | modal-sign share | verdict |
|---|---:|---|
| fight_conversion | 1.0000 | contaminated |
| death_clustering | 0.9886 | contaminated |
| last_hits_at_ten | 0.9466 | eligible |
| spike_usage | 0.8415 | eligible |
| lane_vs_jungle_share | 0.6868 | eligible |
| first_real_item_time | 0.6566 | eligible |
| deaths_alone_share | 0.6340 | eligible |
| first_ward_time | 0.5800 | eligible |
| vision_coverage | 0.5321 | eligible |

The screen also overturned a hand-classification of my own: `spike_usage` had
been excluded by the same verbal argument as `fight_conversion`, and 42 of 265
players show the opposite sign, so it is describing players rather than
results. The measurement settles it, not the argument.

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

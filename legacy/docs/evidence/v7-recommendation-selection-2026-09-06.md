# Section 5 improvement selection, measured — 2026-09-06

```text
PHASE: V7_RECOMMENDATION_SELECTION
STATUS: MEASURED — full run over DISCOVERY
NEW PROVIDER CALLS: 0
CORPUS READ: YES — Pass-2 DISCOVERY only
CANDIDATE_TEST READ: NO
```

Artifacts: `services/api/app/player_analysis_v7/research/recommendation.py`,
`scripts/v7_recommendation_selection.py`,
`docs/evidence/v7-recommendation-selection-2026-09-06.json`.

Running the model falsified two parts of it. Both are amended in
`docs/evidence/v7-improvement-recommendation-model-2026-09-05.md`; this
document is the evidence.

## 1. Result

**265 of 276 Pass-2 players receive exactly one recommendation. None receive
zero.** 247 of them carry the full set of seven eligible candidates.

| chosen dimension | players | actionability |
|---|---:|---:|
| last hits at minute 10 | 135 | 0.95 |
| lane versus jungle share | 43 | 0.75 |
| first ward time | 29 | 0.80 |
| deaths-alone share | 17 | 0.90 |
| first real item time | 17 | 0.85 |
| spike usage | 14 | 0.45 |
| vision coverage | 10 | 0.60 |

Every eligible dimension wins the slot for someone. Last hits takes the
plurality at 51%, which is the intended behaviour rather than a defect: it
carries the highest actionability weight by design, and it is the one
dimension measured entirely inside a window that closes before most games are
decided.

Chosen priority: median 0.216, p5 0.109, p95 0.427.

## 2. The first correction: `tau_d` silences the section

The model standardized the personal gap by `tau_d`, the between-player spread
of gaps. Measured consistently, **`tau_d` is exactly zero on every
dimension**, so every priority is zero and no recommendation ships.

For last hits at minute 10, over 262 players:

```text
var(gap)          = 3.19
mean(SE^2 * D)    = 5.55      D = 2.40 at batch length 50
tau^2 = max(0, 3.19 - 5.55) = 0
```

The gaps themselves are not in doubt. The median player takes **2.4 fewer last
hits by minute 10 in their losses**, and 248 of 262 players have a negative
gap. What is unmeasurable is how much players *differ* in that gap.

Dividing by `tau_d` therefore asks "is your gap unusual" — which constraint 3
of the model forbids in as many words, and which is the same mistake the
Finding model was already corrected for. If everybody's last hits drop in
their losses, each player should still be told that theirs do.

The denominator is now `s_d`, the dimension's own pooled match-to-match
residual spread. It is a unit conversion, identical for every player, so it
makes a 2.4-last-hit gap comparable with a 0.06-share gap without ever ranking
one player against another. Reliability keeps the same functional form and the
same dependence correction, so a noisy gap still cannot become advice.

| dimension | scale `s_d` | `tau_d` | reliability (median) |
|---|---:|---:|---:|
| last_hits_at_ten | 13.257 | 0.000 | 0.981 |
| first_ward_time | 363.229 | 0.000 | 0.965 |
| spike_usage | 168.209 | 0.000 | 0.985 |
| first_real_item_time | 158.223 | 0.000 | 0.969 |
| deaths_alone_share | 0.239 | 0.000 | 0.987 |
| vision_coverage | 0.233 | 0.015 | 0.992 |
| lane_vs_jungle_share | 0.135 | 0.008 | 0.976 |

## 3. A wiring error found on the way

The first run also passed `arm_family=True` to `inference.build_matrix`, which
encodes the win/loss arm as a context factor and projects the *population*
win/loss effect out. That is right for a Finding — a shared population
response is not personal identity — and wrong here, because it makes every
estimate a deviation from how the average player differs between wins and
losses. That is a population comparison wearing the clothes of a personal gap.

`build_personal_contrast_matrix` now projects context out (hero, position,
role, lane, patch, mode) while leaving the arm alone, so "you lose more on
harder heroes" still cannot present itself as a behavioural gap. Duration and
side are deliberately *not* controls: duration is downstream of the outcome, a
stomped loss being short, so controlling for it would absorb the gap rather
than a confounder of it.

## 4. The second correction: the upstream rule is not sufficient

The model's eligibility rule asks whether a dimension is a behaviour the
player emits rather than a result they receive. That is necessary and it is
not enough for a *gap*.

`fight_conversion` passes it. Going to the tower after a won fight is
genuinely the player's own decision, which is why it remains a legitimate
Finding. But measured across a whole match, "you converted fights into towers
less" in a game you lost is close to restating that you lost. Before the
second rule existed, **`fight_conversion` won 168 of 265 single slots on the
second-lowest actionability weight in the table**, and its gap was negative for
every single one of 262 players without exception.

The second rule is measured, not judged. A personal gap should vary in sign
across people: some players ward later in their losses, some earlier. A gap
running the same way for essentially everybody is describing the outcome. The
screen is the modal-sign share, cut at 0.95, **fixed before the shares were
computed**:

| dimension | positive | negative | modal-sign share | verdict |
|---|---:|---:|---:|---|
| fight_conversion | 0 | 262 | 1.0000 | contaminated |
| death_clustering | 260 | 3 | 0.9886 | contaminated |
| last_hits_at_ten | 14 | 248 | 0.9466 | eligible |
| spike_usage | 223 | 42 | 0.8415 | eligible |
| lane_vs_jungle_share | 182 | 83 | 0.6868 | eligible |
| first_real_item_time | 174 | 91 | 0.6566 | eligible |
| deaths_alone_share | 168 | 97 | 0.6340 | eligible |
| first_ward_time | 145 | 105 | 0.5800 | eligible |
| vision_coverage | 124 | 141 | 0.5321 | eligible |

The screen overturned a hand-classification of mine. `spike_usage` had been
excluded by the same verbal argument as `fight_conversion` — whether a kill
follows is not the player's alone — and 42 of 265 players carry the opposite
sign, so it is describing players, not results. The measurement settles it,
not the argument. It is reinstated.

The exclusions are recorded as design-time flags on each dimension, as the
model requires eligibility to be. The runner re-measures every dimension,
including the excluded ones, and **raises if a recorded flag disagrees with the
corpus** — the only way a design-time property cannot drift silently.

## 5. Known limits

- **`last_hits_at_ten` sits just under the screen at 0.9466** and takes 51% of
  the slots. It is kept, and it is also the dimension structurally most
  protected from this failure mode. If the cut were 0.94 it would be excluded
  and the section would lose its strongest recommendation, so the sensitivity
  is worth stating rather than burying.
- **The 0.95 cut and the minimum of 15 matches per arm are working values.**
  The model defers both to calibration against the reserved split.
- **Actionability weights are design values, never fitted**, as the model
  requires. They order the tie-breaks and scale the priorities, and nothing in
  this run tuned them.
- **No causal claim is made or implied.** The report may say this is where the
  player's losses differ; it may not say changing it will make them win. That
  is a cohort question this corpus cannot answer, and the verification field
  is what lets the player test it themselves.
- **Recommendations need Pass-2 parsed data**, so in research they cover the
  276-player subset. In production the report fetches parsed matches for the
  single player it is about.

# Section 6 archetype axes, measured — 2026-09-06

```text
PHASE: V7_ARCHETYPE_AXES
STATUS: MEASURED — full run over DISCOVERY, both corpora
NEW PROVIDER CALLS: 0
CORPUS READ: YES — DISCOVERY only
CANDIDATE_TEST READ: NO
```

Artifacts: `scripts/v7_research/archetype.py`,
`scripts/v7_archetype_axes.py`, `docs/evidence/v7-archetype-axes-2026-09-06.json`.

The narrative document calls this section "for fun, not for science". That is
the reason to audit it rather than the reason not to: a playful label is
exactly the output nobody checks.

## 1. The axes

| axis | measure | levels |
|---|---|---|
| Tempo | mean, across matches, of when the player's kills and assists happen as a fraction of match duration | early / mid / late, at population terciles |
| Fight style | share of the match's fight minutes the player appears in (kill, assist *or* death), and deaths per fight minute | ghost below the participation tercile; otherwise frontliner at or above the median deaths per fight minute, else opportunist |
| Modifier | between-session win-rate spread over what independent games at the player's own rate predict | streaky above 1.0, else metronome |

Two rare specials bypass the grid, both cut at the 98th percentile and both
strengths — section 7 turns the archetype into a share card, and a share card
"must be true and must not be an insult": **The Lighthouse** (vision coverage)
and **The Closer** (win rate from a 10k lead).

The axes are deliberately not Findings. A Finding is ranked against the
population spread and carries a reliability; an archetype is a label. Nothing
in `archetype.py` feeds the ranking model, which is what stops a label
acquiring the authority of a measurement.

## 2. The mode confound, which was real

Turbo is **63% of the Pass-2 corpus** (63,750 of 101,581 matches) and its games
are shorter and bloodier. A mode-blind axis therefore measures mode
composition:

| candidate tempo axis | split-half `r` | p5–p95 spread | correlation with the player's turbo share |
|---|---:|---:|---:|
| impact share before a fixed 15 minutes | 0.985 | 0.334 | **0.889** |
| duration-normalised centroid | 0.970 | 0.074 | −0.213 |
| share before 35% of duration | 0.973 | 0.098 | — |
| share before 50% of duration | 0.947 | 0.110 | — |

The fixed-window axis looked best on both stability and spread, and it is
almost entirely a turbo detector. Its apparent spread *was* the mode mix. Even
the duration-normalised centroid moved: measured on all matches versus
non-turbo only, the two versions correlate just 0.520. Fight participation is
0.585 correlated with turbo share on its own, and deaths per fight minute
0.335.

**Fix:** every axis is measured and cut inside the player's dominant mode
stratum. A turbo player is called "early" relative to other turbo players.
That is both the honest claim and the one a reader assumes is being made.

The stratum cuts confirm the confound was worth removing:

| cut | STANDARD | TURBO |
|---|---:|---:|
| participation tercile | 0.405 | 0.492 |
| deaths per fight minute, median | 0.177 | 0.224 |
| tempo terciles | 0.564 / 0.582 | 0.549 / 0.564 |

A player at 0.45 participation is a ghost in turbo and is not in standard. The
mode-blind version would have labelled them by the queue they picked.

## 3. Coverage and spread

262 of 276 joinable players receive an archetype — 99 standard, 163 turbo. The
14 without one are refused rather than defaulted: 4 have no dominant mode
stratum, 4 lack event support, and 14 lack the eight sessions the modifier
needs (the sets overlap). An archetype assembled from two measured axes and
one default is a guess wearing the same clothes as a measurement.

| axis | levels |
|---|---|
| tempo | early 85 / mid 88 / late 89 |
| fight style | frontliner 119 / opportunist 59 / ghost 84 |
| modifier | metronome 143 / streaky 119 |

**All 18 grid cells are occupied.** The largest holds 9.6% of players (24 of
250 non-special), against 13.6% before stratification — removing the mode
confound spread the grid out rather than collapsing it. Specials fire on 13
players: 7 Lighthouse, 6 Closer.

| label | n | | label | n |
|---|---:|---|---|---:|
| The Alarm Clock | 24 | | The Engine Room | 24 |
| The Late Bloomer | 22 | | The Opening Act | 22 |
| The Patient One | 19 | | The Brawler | 18 |
| The Last Word | 14 | | The Long Game | 13 |
| The Timekeeper | 13 | | The Overtime | 11 |
| The Pickpocket | 11 | | The Quiet Start | 11 |
| The Understudy | 11 | | The Wildcard | 11 |
| The Early Bird | 8 | | The Ambusher | 7 |
| The Slow Burn | 6 | | The Closer's Apprentice | 4 |

## 4. A second defect: the modifier was biased toward "metronome"

Session dispersion first used the *population* variance of session win rates.
The session rates are a sample from the player's own process, so dividing by
`k` rather than `k - 1` biases the observed spread down by `(k - 1) / k` —
around 12% at the eight-session minimum, enough on its own to push a genuinely
coin-flip player below the 1.0 line and call them a metronome. Corrected to the
sample variance, the population median moved 0.965 to 0.976 and the split is
143 / 119.

The remaining shortfall below 1.0 is expected and not corrected: the player's
own rate `p` is estimated from the same data, which is a known small downward
bias in a dispersion ratio.

## 5. Known limits

- **Tempo is reliably measured but tightly packed.** Within a stratum the
  terciles sit 0.015–0.018 apart on a p5–p95 range of about 0.075. Split-half
  stability is 0.970, so the ordering is real rather than noise, but the
  boundary between "early" and "mid" separates players who are genuinely
  close. The label is a ranking within a narrow band, not a gulf, and section 6
  copy should not imply otherwise.
- **The modifier is not stratified by mode**, on purpose: it is a property of
  how the player's nights go, and splitting a year of sessions by mode would
  break the sessions it measures.
- **Archetype needs both corpora.** In research that means the 276-player
  Pass-2 subset; in production the report fetches parsed matches for the one
  player it is about, so the constraint is a research artifact.
- **The 98th-percentile special cuts are corpus-relative** and will need
  refreshing against the reserved split alongside the strength-band cut points.

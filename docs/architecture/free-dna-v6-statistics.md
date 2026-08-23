# Free DNA v6 statistics

Free DNA v6 is a summary-only, player-centric analysis path. Stable identity
uses equal eligible-match weighting; recency is optional context, never a
threshold input. Rank and MMR are excluded from baselines, thresholds, copy,
and recommendations.

## Estimates and context

Breadth and Toolkit are Shannon effective counts. Toolkit is match-weighted
across reviewed hero-job labels and requires 80% taxonomy coverage. Involvement
is `(kills + assists) / minutes`; Finishing is `kills / (kills + assists)` with
zero-event matches excluded; Death Exposure is `deaths / minutes * 10`.

Each baseline-dependent metric resolves a per-match context cell using the
frozen hierarchy:

```text
patch+hero+lane → patch+hero-function+lane → patch+hero → patch+lane → patch → overall
```

Only cells with at least 200 matches and 50 distinct players resolve. Missing
cells remove that observation from the metric and lower coverage; they do not
receive a pseudo-baseline. Artifact validation rejects rank/MMR dimensions,
duplicate cells, non-finite values, and unsupported hierarchy levels.

## Session authority

Every interval uses seeded clustered bootstrap over independent sessions, with
2,000 production iterations and a 95% interval. Bootstrap replicates recompute
the statistic from resampled session rows; Transfer keeps the full-history
core/stretch hero split fixed. Consistency uses robust session dispersion and
requires 12 usable sessions. Session Drift uses completed sessions with at least
four matches, compares early versus late buckets, and excludes the middle match
for odd-sized sessions. Duration is supporting context only.

Transfer compares core versus stretch outcome, context-adjusted activity, and
survival-oriented `-death exposure`; two-of-three agreement is required.
Post-Loss Response builds adjacent same-session loss→next-match transitions,
compares them with hierarchical context controls, and requires 30 transitions,
12 qualifying sessions, and 50% coverage. Its Familiarity and Tempo measures
are supporting evidence. Opposing components remain mixed rather than being
averaged into a neutral story.

## Qualification and FDR

Thresholds are metric-specific artifacts. Moderate stability is 0.75 and high
stability is 0.90. High confidence additionally requires the 95% interval to
clear the practical-equivalence region or reported zone boundary. The five
family p-values are assembled from finite-sample directional or population-zone
tests and corrected together with Benjamini–Hochberg at `q ≤ 0.05`. Missing or
neutral evidence has p=1.0. Ranking happens only after q-value qualification,
with at most three published families.

The calibration workflow validates the private corpus, freezes a deterministic
player-exclusive 70/30 split stratified by annual volume, pool concentration,
lobby mix, and region, and derives all 19 full/A/B point estimates without
running bootstrap during training. Practical margins are P90 odd/even-session
noise divided by two. Breadth/Toolkit and Consistency use training Q33/Q67 with
the approved median±margin fallback.

Synthetic and sealed-holdout evaluation are independent, resumable commands.
The aggregate evaluation derives every gate value and remains fail-closed when
evidence or external approval is missing. Evaluation and release manifests are
audit evidence; only the baseline and threshold artifacts are runtime analysis
inputs.
